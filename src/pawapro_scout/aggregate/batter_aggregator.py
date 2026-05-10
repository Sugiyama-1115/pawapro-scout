"""
aggregate/batter_aggregator.py
複数のデータソース (DataFrame) から BatterStats を生成するアグリゲーター。

入力データの ID 体系が異なる点を吸収する:
  - Statcast / Savant: player_id (MLBAM)
  - FanGraphs stats  : IDfg
  - Baseball Reference: mlbID (MLBAM と同値)
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from pawapro_scout.models import BatterStats

logger = logging.getLogger(__name__)

# ── 打撃判定用 description セット ──────────────────────
_SWING_DESC = frozenset([
    "swinging_strike", "swinging_strike_blocked",
    "foul", "foul_tip", "foul_bunt", "missed_bunt",
    "hit_into_play", "hit_into_play_score", "hit_into_play_no_out",
])
_WHIFF_DESC = frozenset([
    "swinging_strike", "swinging_strike_blocked",
])
_HIT_EVENTS = frozenset([
    "single", "double", "triple", "home_run",
])


def _row(df: pd.DataFrame, col: str, val) -> pd.Series | None:
    """DataFrame から指定 ID 列の値が val に一致する最初の行を返す。未発見は None。"""
    if df is None or df.empty or col not in df.columns:
        return None
    mask = df[col].astype(str) == str(int(val)) if isinstance(val, (int, float)) else df[col].astype(str) == str(val)
    sub = df[mask]
    return sub.iloc[0] if not sub.empty else None


def _get(row: pd.Series | None, *cols, default=0.0):
    """行 Series から最初に見つかった列の値を返す。存在しない or NaN なら default。"""
    if row is None:
        return default
    for c in cols:
        if c in row.index and pd.notna(row[c]):
            v = row[c]
            return float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v
    return default


def _pct(row: pd.Series | None, *cols, default: float = 0.0) -> float:
    """
    FanGraphs 等の割合列を 0〜100 のパーセント値で返す。
    pybaseball は K% 等を小数 (0.25) で返すため、2.0 未満なら ×100 する。
    """
    v = _get(row, *cols, default=default)
    if isinstance(v, float) and 0.0 < v < 2.0:
        return v * 100.0
    return float(v)


class BatterAggregator:
    """
    野手の各種データを受け取り BatterStats に集約する。

    Args:
        mlbam_id: MLBAM プレーヤー ID
        fg_id:    FanGraphs プレーヤー ID (IDfg)
        bref_id:  Baseball Reference ID (mlbID は整数; 不明なら None)
    """

    def __init__(self, mlbam_id: int, fg_id: int | None, bref_id: int | None) -> None:
        self.mlbam_id = mlbam_id
        self.fg_id = fg_id
        self.bref_id = bref_id

    # ──────────────────────────────────────────────
    # 公開メソッド
    # ──────────────────────────────────────────────

    def build(
        self,
        statcast_batter: pd.DataFrame,
        batter_expected: pd.DataFrame,
        batter_percentile: pd.DataFrame,
        sprint_speed: pd.DataFrame,
        outs_above_average: pd.DataFrame,
        batting_stats_fg: pd.DataFrame,
        batting_stats_bref: pd.DataFrame,
        fielding_run_value: pd.DataFrame,
        outfielder_throws: pd.DataFrame | None = None,
        catcher_poptime: pd.DataFrame | None = None,
        catcher_framing: pd.DataFrame | None = None,
        catcher_blocking: pd.DataFrame | None = None,
        splits: dict[str, pd.DataFrame] | None = None,
    ) -> BatterStats:
        """全データソースを統合して BatterStats を返す。"""
        sp = splits or {}

        # ── 各ソースの選手行を取得 ───────────────────────
        row_exp  = _row(batter_expected,   "player_id", self.mlbam_id)
        row_pct  = _row(batter_percentile, "player_id", self.mlbam_id)
        row_spd  = _row(sprint_speed,      "player_id", self.mlbam_id)
        row_oaa  = _row(outs_above_average,"player_id", self.mlbam_id)
        row_fg   = _row(batting_stats_fg,  "IDfg",      self.fg_id)   if self.fg_id else None
        row_bref = _row(batting_stats_bref,"mlbID",     self.mlbam_id)
        row_frv  = _row(fielding_run_value,"id",         self.mlbam_id)  # 新FRV CSVは "id" 列
        row_of   = _row(outfielder_throws, "player_id", self.mlbam_id) if outfielder_throws is not None else None
        row_pop  = _row(catcher_poptime,   "player_id", self.mlbam_id) if catcher_poptime  is not None else None
        row_frm  = _row(catcher_framing,   "player_id", self.mlbam_id) if catcher_framing  is not None else None
        row_blk  = _row(catcher_blocking,  "player_id", self.mlbam_id) if catcher_blocking is not None else None

        # ── Statcast pitch-level 集計 ─────────────────────
        sc = self._statcast_metrics(statcast_batter)

        # ── bref フォールバック (Statcast events) ──────────
        sc_sb, sc_cs, sc_g = self._statcast_bref_fallback(statcast_batter)

        # ── FanGraphs Splits ──────────────────────────────
        risp_row  = sp.get("risp",       pd.DataFrame())
        lhp_row   = sp.get("vs_lhp",    pd.DataFrame())
        rhp_row   = sp.get("vs_rhp",    pd.DataFrame())

        def split_woba(df: pd.DataFrame) -> float:
            # FanGraphs 列名 → Statcast Search 列名 の順で探索
            for col in (
                "wOBA", "xwOBA",                         # FanGraphs
                "estimated_woba_using_speedangle",        # Statcast xwOBA
                "woba_value",                             # Statcast wOBA
                "OBP",                                    # fallback
            ):
                if col in df.columns and not df.empty and pd.notna(df.iloc[0].get(col)):
                    return float(df.iloc[0][col])
            return 0.0

        return BatterStats(
            # 弾道
            avg_launch_angle   = sc["avg_launch_angle"],
            sweet_spot_percent = _get(row_exp, "sweet_spot_percent"),

            # ミート
            xba           = _get(row_exp, "xba", "est_ba"),
            whiff_percent = _get(row_exp, "whiff_percent"),

            # パワー
            max_exit_velocity  = sc["max_exit_velocity"],
            avg_exit_velocity  = sc["avg_exit_velocity"],
            barrel_percent     = _get(row_exp, "barrel_batted_rate", "barrel_percent"),
            barrel_percentile  = int(_get(row_pct, "barrel", default=0)),
            hard_hit_percent   = _get(row_exp, "hard_hit_percent"),

            # 走力
            sprint_speed = _get(row_spd, "sprint_speed"),
            bolts        = int(_get(row_spd, "bolts", default=0)),

            # 肩力 (arm-strength CSV: max_arm_strength, arm_overall / 旧: max_throw_speed)
            arm_strength_mph = _get(row_of, "max_arm_strength", "arm_overall", "max_throw_speed", default=None),
            pop_time         = _get(row_pop, "pop_time_2b_sba_all", "pop_time", default=None),

            # 守備力
            oaa            = int(_get(row_oaa, "outs_above_average", default=0)),
            oaa_percentile = int(_get(row_pct, "outs_above_average", default=50)),

            # 捕球 (新FRV CSV: total_runs / 旧: frv)
            fielding_run_value = _get(row_frv, "total_runs", "frv", "fielding_run_value"),
            error_count        = int(_get(row_frv, "errors", default=0)),  # 新CSVに errors 列なし → 0

            # FanGraphs 打撃
            k_percent   = _pct(row_fg, "K%"),
            bb_percent  = _pct(row_fg, "BB%"),
            wpa         = _get(row_fg, "WPA"),
            lob_percent = _pct(row_fg, "LOB%"),
            ops_plus    = int(_get(row_fg, "OPS+", default=0)),

            # Baseball Reference (Statcast events でフォールバック)
            sb    = int(_get(row_bref, "SB",  default=sc_sb)),
            cs    = int(_get(row_bref, "CS",  default=sc_cs)),
            gdp   = int(_get(row_bref, "GDP", default=0)),
            sh    = int(_get(row_bref, "SH",  default=0)),
            games = int(_get(row_bref, "G",   default=sc_g)),

            # パーセンタイル
            xba_percentile = int(_get(row_pct, "xba", default=0)),

            # スプリット
            risp_avg    = split_woba(risp_row),
            season_avg  = _get(row_fg, "AVG"),
            vs_lhp_woba = split_woba(lhp_row),
            vs_rhp_woba = split_woba(rhp_row),

            # 捕手系 Savant
            framing_runs  = _get(row_frm, "runs_extra_strikes", "framing_runs", default=None),
            blocking_runs = _get(row_blk, "blocks_above_average", default=None),

            # Statcast 打球方向
            pull_hr_pct          = sc["pull_hr_pct"],
            oppo_hr_count        = sc["oppo_hr_count"],
            multi_hit_game_count = sc["multi_hit_game_count"],
        )

    # ──────────────────────────────────────────────
    # 内部: bref 代替 (Statcast events)
    # ──────────────────────────────────────────────

    @staticmethod
    def _statcast_bref_fallback(df: pd.DataFrame) -> tuple[int, int, int]:
        """
        pitch-level DataFrame から SB / CS / G を推定する。
        bref が取得できなかった場合のフォールバック。

        Returns:
            (sb, cs, games)
        """
        if df is None or df.empty or "events" not in df.columns:
            return 0, 0, 0

        _SB_EVENTS = frozenset(["stolen_base_2b", "stolen_base_3b", "stolen_base_home"])
        _CS_EVENTS = frozenset(["caught_stealing_2b", "caught_stealing_3b", "caught_stealing_home"])

        ev = df["events"].dropna()
        sb = int(ev.isin(_SB_EVENTS).sum())
        cs = int(ev.isin(_CS_EVENTS).sum())

        group_col = "game_pk" if "game_pk" in df.columns else "game_date"
        games = int(df[group_col].nunique()) if group_col in df.columns else 0

        return sb, cs, games

    # ──────────────────────────────────────────────
    # 内部: Statcast pitch-level 集計
    # ──────────────────────────────────────────────

    def _statcast_metrics(self, df: pd.DataFrame) -> dict:
        """pitch-level DataFrame から野手用指標を計算する。"""
        defaults = {
            "avg_launch_angle": 0.0,
            "max_exit_velocity": 0.0,
            "avg_exit_velocity": 0.0,
            "pull_hr_pct": 0.0,
            "oppo_hr_count": 0,
            "multi_hit_game_count": 0,
        }
        if df is None or df.empty:
            return defaults

        # 打球 (launch_speed が存在する行)
        batted = df[df["launch_speed"].notna()] if "launch_speed" in df.columns else df.iloc[0:0]
        la_col = "launch_angle" if "launch_angle" in df.columns else None

        avg_la  = float(batted[la_col].mean())      if la_col and not batted.empty else 0.0
        max_ev  = float(batted["launch_speed"].max()) if not batted.empty else 0.0
        avg_ev  = float(batted["launch_speed"].mean()) if not batted.empty else 0.0

        # HR の引っ張り / 逆方向
        pull_hr_pct, oppo_hr_count = self._hr_direction_metrics(df)

        # 1試合マルチヒット (3安打以上)
        multi = self._multi_hit_games(df)

        return {
            "avg_launch_angle": avg_la,
            "max_exit_velocity": max_ev,
            "avg_exit_velocity": avg_ev,
            "pull_hr_pct": pull_hr_pct,
            "oppo_hr_count": oppo_hr_count,
            "multi_hit_game_count": multi,
        }

    def _hr_direction_metrics(self, df: pd.DataFrame) -> tuple[float, int]:
        """
        HR の引っ張り割合と逆方向 HR 数を返す。
        hc_x 座標がない場合はデフォルト (0.0, 0) を返す。
        """
        if "events" not in df.columns or "hc_x" not in df.columns:
            return 0.0, 0

        hr = df[df["events"] == "home_run"]
        if hr.empty:
            return 0.0, 0

        stand = df["stand"].iloc[0] if "stand" in df.columns else "R"
        # Statcast 座標: hc_x は左翼方向が小さい (< 125 が左方向)
        # 右打者の引っ張り = 左翼 (hc_x < 125)
        # 左打者の引っ張り = 右翼 (hc_x > 125)
        if stand == "R":
            pull_mask = hr["hc_x"] < 125
            oppo_mask = hr["hc_x"] > 165
        else:
            pull_mask = hr["hc_x"] > 125
            oppo_mask = hr["hc_x"] < 85

        pull_hr_pct  = pull_mask.sum() / len(hr) if len(hr) > 0 else 0.0
        oppo_hr_count = int(oppo_mask.sum())
        return float(pull_hr_pct), oppo_hr_count

    def _multi_hit_games(self, df: pd.DataFrame) -> int:
        """1試合に3安打以上を記録したゲーム数を返す。"""
        if "events" not in df.columns or "game_date" not in df.columns:
            return 0

        hit_df = df[df["events"].isin(_HIT_EVENTS)]
        if hit_df.empty:
            return 0

        group_col = "game_pk" if "game_pk" in df.columns else "game_date"
        hits_per_game = hit_df.groupby(group_col).size()
        return int((hits_per_game >= 3).sum())
