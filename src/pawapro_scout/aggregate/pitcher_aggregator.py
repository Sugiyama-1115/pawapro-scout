"""
aggregate/pitcher_aggregator.py
複数のデータソース (DataFrame) から PitcherStats / PitchAggregated を生成する。

球種集計は statcast_pitcher (pitch-level) を基本とし、
Savant Pitch Arsenal (league-wide) の RV/100 で補完する。
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from pawapro_scout.config import MIN_PITCH_USAGE_PCT
from pawapro_scout.models import PitchAggregated, PitcherStats

logger = logging.getLogger(__name__)

# ── 空振り判定 description ─────────────────────────────
_SWING_DESC = frozenset([
    "swinging_strike", "swinging_strike_blocked",
    "foul", "foul_tip", "foul_bunt", "missed_bunt",
    "hit_into_play", "hit_into_play_score", "hit_into_play_no_out",
])
_WHIFF_DESC = frozenset([
    "swinging_strike", "swinging_strike_blocked",
])

# ── ゾーン番号: 低め (7/8/9) とハート (5) ────────────────
_LOW_ZONES   = {7, 8, 9}
_HEART_ZONES = {5}


def _row(df: pd.DataFrame, col: str, val) -> pd.Series | None:
    if df is None or df.empty or col not in df.columns:
        return None
    mask = df[col].astype(str) == str(int(val)) if isinstance(val, (int, float)) else df[col].astype(str) == str(val)
    sub = df[mask]
    return sub.iloc[0] if not sub.empty else None


def _get(row: pd.Series | None, *cols, default=0.0):
    if row is None:
        return default
    for c in cols:
        if c in row.index and pd.notna(row[c]):
            v = row[c]
            return float(v) if isinstance(v, (int, float, np.integer, np.floating)) else v
    return default


def _pct(row: pd.Series | None, *cols, default=0.0):
    """
    小数 (0.25) または パーセント (25.0) のどちらでも 0〜100 に正規化して返す。
    default=None が渡された場合は None をそのまま返す。
    """
    v = _get(row, *cols, default=default)
    if v is None:
        return None
    if isinstance(v, float) and 0.0 < v < 2.0:
        return v * 100.0
    return float(v)


class PitcherAggregator:
    """
    投手の各種データを受け取り PitcherStats に集約する。

    Args:
        mlbam_id:   MLBAM プレーヤー ID
        fg_id:      FanGraphs ID (IDfg)
        bref_id:    Baseball Reference の mlbID (整数) or None
    """

    def __init__(self, mlbam_id: int, fg_id: int | None, bref_id: int | None) -> None:
        self.mlbam_id = mlbam_id
        self.fg_id    = fg_id
        self.bref_id  = bref_id

    # ──────────────────────────────────────────────
    # 公開メソッド
    # ──────────────────────────────────────────────

    def build(
        self,
        statcast_pitcher: pd.DataFrame,
        pitcher_expected: pd.DataFrame,
        pitcher_percentile: pd.DataFrame,
        pitching_stats_fg: pd.DataFrame,
        pitching_stats_bref: pd.DataFrame,
        pitcher_fielding: pd.DataFrame,
        pitch_arsenal: pd.DataFrame,
        pitcher_active_spin: pd.DataFrame,
        splits: dict[str, pd.DataFrame] | None = None,
        savant_inning1: pd.DataFrame | None = None,
        savant_inning7plus: pd.DataFrame | None = None,
        savant_zone: pd.DataFrame | None = None,
        savant_highpitch: pd.DataFrame | None = None,
    ) -> PitcherStats:
        """全データソースを統合して PitcherStats を返す。"""
        sp = splits or {}

        # ── league-wide の選手行を取得 ──────────────────────
        row_pct  = _row(pitcher_percentile, "player_id", self.mlbam_id)
        row_fg   = _row(pitching_stats_fg,  "IDfg",      self.fg_id)   if self.fg_id else None
        row_bref = _row(pitching_stats_bref,"mlbID",     self.mlbam_id)
        row_pfd  = _row(pitcher_fielding,   "player_id", self.mlbam_id)
        row_spin = _row(pitcher_active_spin,"player_id", self.mlbam_id)

        # ── Statcast pitch-level 集計 ─────────────────────
        sc = self._statcast_metrics(statcast_pitcher)

        # ── 球種リスト (PitchAggregated) ─────────────────
        pitches = self._build_pitches(statcast_pitcher, pitch_arsenal)

        # ── FanGraphs Splits ──────────────────────────────
        def xwoba_from_split(df: pd.DataFrame) -> float:
            for col in ("xwOBA", "wOBA", "xFIP"):
                if df is not None and not df.empty and col in df.columns:
                    v = df.iloc[0].get(col)
                    if pd.notna(v):
                        return float(v)
            return 0.0

        # ── Savant Search ゾーン集計 ─────────────────────
        low_zone_pct, heart_zone_pct = self._zone_metrics(savant_zone)

        # ── 100球超 Run Value ─────────────────────────────
        pitch_100_rv = self._highpitch_rv(savant_highpitch)

        # ── スタミナ: 平均投球数 ──────────────────────────
        avg_p_per_g = self._avg_pitches_per_game(statcast_pitcher, row_fg)

        # ── リリースポイント安定性 ────────────────────────
        rel_x_std, rel_z_std = self._release_stddev(statcast_pitcher)

        # ── 4seam Active Spin ─────────────────────────────
        active_spin = _get(row_spin, "active_spin_4seam", "active_spin", default=None)

        return PitcherStats(
            # 基礎
            max_velocity_mph = sc["max_velocity_mph"],
            pitches          = pitches,

            # コントロール
            k_percent   = _pct(row_fg,  "K%"),
            bb_percent  = _pct(row_fg,  "BB%"),
            k_percentile  = int(_get(row_pct, "k_percent",  default=50)),
            bb_percentile = int(_get(row_pct, "bb_percent", default=50)),

            # スタミナ
            avg_pitches_per_game = avg_p_per_g,
            games         = int(_get(row_fg, "G",  default=0)),
            ip            = _get(row_fg, "IP", default=0.0),
            games_started = int(_get(row_fg, "GS", default=0)),

            # 球威
            exit_vel_percentile = int(_get(row_pct, "exit_velocity_avg", default=50)),
            hard_hit_percent    = _pct(row_fg, "Hard%", "HardHit%"),

            # ムーブメント
            extension_percentile = int(_get(row_pct, "pitch_hand_speed", "extension", default=50)),
            active_spin_4seam    = float(active_spin) if active_spin is not None else None,

            # LOB / 援護
            lob_percent  = _pct(row_fg, "LOB%"),
            hr_per_9     = _get(row_fg, "HR/9"),
            wpa          = _get(row_fg, "WPA"),
            ir_stranded_pct = _pct(row_fg, "IR-S%", default=None) or None,  # type: ignore

            # FanGraphs Splits
            risp_xwoba     = xwoba_from_split(sp.get("risp")),
            vs_lhp_xwoba   = xwoba_from_split(sp.get("vs_lhp")),
            vs_rhp_xwoba   = xwoba_from_split(sp.get("vs_rhp")),
            high_lev_xwoba = xwoba_from_split(sp.get("high_lev")),

            # Savant Statcast Search
            inning1_xwoba    = self._xwoba_from_search(savant_inning1),
            inning7plus_xwoba= self._xwoba_from_search(savant_inning7plus),
            pitch_100plus_rv = pitch_100_rv,
            low_zone_pct     = low_zone_pct,
            heart_zone_pct   = heart_zone_pct,

            # リリースポイント
            release_x_stddev = rel_x_std,
            release_z_stddev = rel_z_std,

            # bref
            pickoffs   = int(_get(row_bref, "PO", default=0)),
            sb_against = int(_get(row_bref, "SB", default=0)),
            cs_against = int(_get(row_bref, "CS", default=0)),

            # P-OAA
            p_oaa = int(_get(row_pfd, "outs_above_average", default=0)) or None,

            season_xwoba = 0.0,  # 全体 xwOBA は pitcher_expected から別途設定可
        )

    # ──────────────────────────────────────────────
    # 球種リスト構築
    # ──────────────────────────────────────────────

    def _build_pitches(
        self,
        df: pd.DataFrame,
        pitch_arsenal: pd.DataFrame,
    ) -> list[PitchAggregated]:
        """
        statcast pitch-level データから PitchAggregated のリストを作る。
        usage% が MIN_PITCH_USAGE_PCT 未満の球種は除外する。
        """
        if df is None or df.empty or "pitch_type" not in df.columns:
            return []

        total = len(df)

        # 4seam 平均球速 (delta_v の基準)
        ff_mask = df["pitch_type"].isin(["FF", "FA"])
        ff_avg  = float(df.loc[ff_mask, "release_speed"].mean()) if ff_mask.any() else 0.0

        results: list[PitchAggregated] = []

        for pt, grp in df.groupby("pitch_type"):
            if not isinstance(pt, str) or pt in ("", "UN", "PO"):
                continue

            usage_pct = len(grp) / total * 100.0
            if usage_pct < MIN_PITCH_USAGE_PCT:
                continue

            vel_avg = float(grp["release_speed"].mean()) if "release_speed" in grp else 0.0

            # 空振り率
            if "description" in grp.columns:
                swings = grp["description"].isin(_SWING_DESC).sum()
                whiffs = grp["description"].isin(_WHIFF_DESC).sum()
                whiff_pct = whiffs / swings * 100.0 if swings > 0 else 0.0
            else:
                whiff_pct = 0.0

            # 変化量 (pfx 単位 = feet → inches)
            hb  = float(grp["pfx_x"].mean()) * 12.0 if "pfx_x" in grp.columns else 0.0
            ivb = float(grp["pfx_z"].mean()) * 12.0 if "pfx_z" in grp.columns else 0.0

            delta_v = ff_avg - vel_avg if ff_avg > 0 else 0.0

            # RV/100 from Savant pitch arsenal
            rv100 = self._rv_per_100(pitch_arsenal, str(pt))

            results.append(PitchAggregated(
                pitch_type             = str(pt),
                usage_pct              = round(usage_pct, 1),
                velocity_avg           = round(vel_avg, 1),
                whiff_pct              = round(whiff_pct, 1),
                horizontal_break       = round(hb, 2),
                induced_vertical_break = round(ivb, 2),
                delta_v_from_fastball  = round(delta_v, 1),
                rv_per_100             = round(rv100, 2),
            ))

        return sorted(results, key=lambda p: p.usage_pct, reverse=True)

    # ──────────────────────────────────────────────
    # 内部: Statcast pitch-level 集計
    # ──────────────────────────────────────────────

    def _statcast_metrics(self, df: pd.DataFrame) -> dict:
        defaults = {"max_velocity_mph": 0.0}
        if df is None or df.empty:
            return defaults

        ff_mask = df["pitch_type"].isin(["FF", "FA"]) if "pitch_type" in df.columns else pd.Series(True, index=df.index)
        max_v = float(df.loc[ff_mask, "release_speed"].max()) if "release_speed" in df.columns and ff_mask.any() else 0.0
        return {"max_velocity_mph": max_v}

    def _release_stddev(self, df: pd.DataFrame) -> tuple[float, float]:
        if df is None or df.empty:
            return 0.0, 0.0
        x_std = float(df["release_pos_x"].std()) if "release_pos_x" in df.columns else 0.0
        z_std = float(df["release_pos_z"].std()) if "release_pos_z" in df.columns else 0.0
        return x_std, z_std

    def _avg_pitches_per_game(
        self,
        df: pd.DataFrame,
        row_fg: pd.Series | None,
    ) -> float | None:
        """
        先発のみ平均投球数を返す。
        FanGraphs に Pitches / GS があればそちらを優先。
        """
        # FanGraphs から計算
        if row_fg is not None:
            total_p = _get(row_fg, "Pitches", default=0.0)
            gs      = _get(row_fg, "GS",      default=0.0)
            if gs > 0 and total_p > 0:
                return round(total_p / gs, 1)

        # Statcast から計算 (先発ゲーム = 1イニング目から投げた)
        if df is None or df.empty or "game_pk" not in df.columns:
            return None
        pitches_per_game = df.groupby("game_pk").size()
        if pitches_per_game.empty:
            return None
        # 先発登板 = 50球以上を投げた試合のみ (救援登板を除外)
        sp_games = pitches_per_game[pitches_per_game >= 50]
        return round(float(sp_games.mean()), 1) if not sp_games.empty else None

    def _zone_metrics(self, savant_zone: pd.DataFrame | None) -> tuple[float, float]:
        """Savant Search ゾーン別集計から低め投球率・ハート率を算出する。"""
        if savant_zone is None or savant_zone.empty or "zone" not in savant_zone.columns:
            return 0.0, 0.0

        total_p = savant_zone["pitches"].sum() if "pitches" in savant_zone.columns else 0
        if total_p == 0:
            return 0.0, 0.0

        low_p   = savant_zone[savant_zone["zone"].isin(_LOW_ZONES)]["pitches"].sum()  if "pitches" in savant_zone.columns else 0
        heart_p = savant_zone[savant_zone["zone"].isin(_HEART_ZONES)]["pitches"].sum() if "pitches" in savant_zone.columns else 0

        return round(low_p / total_p * 100, 1), round(heart_p / total_p * 100, 1)

    def _highpitch_rv(self, savant_highpitch: pd.DataFrame | None) -> float:
        """100球超のRun Valueを返す (存在する場合)。"""
        if savant_highpitch is None or savant_highpitch.empty:
            return 0.0
        for col in ("run_value", "rv", "estimated_woba_using_speedangle"):
            if col in savant_highpitch.columns:
                v = savant_highpitch[col].sum()
                return round(float(v), 2)
        return 0.0

    def _xwoba_from_search(self, df: pd.DataFrame | None) -> float:
        """Savant Search 集計 DataFrame から xwOBA / wOBA を取り出す。"""
        if df is None or df.empty:
            return 0.0
        for col in ("estimated_woba_using_speedangle", "xwOBA", "woba_value"):
            if col in df.columns:
                v = df[col].mean()
                if pd.notna(v):
                    return round(float(v), 3)
        return 0.0

    def _rv_per_100(self, pitch_arsenal: pd.DataFrame, pitch_type: str) -> float:
        """
        Savant Pitch Arsenal leaderboard から球種別 RV/100 を取得する。
        player_id と pitch_type_name (または pitch_type) で絞り込む。
        """
        if pitch_arsenal is None or pitch_arsenal.empty:
            return 0.0

        # player_id でフィルタ
        pa = pitch_arsenal[pitch_arsenal["player_id"].astype(str) == str(self.mlbam_id)] \
            if "player_id" in pitch_arsenal.columns else pitch_arsenal

        # pitch_type 列で絞り込み
        for col in ("pitch_type", "pitch_type_name", "pitch_hand_type"):
            if col in pa.columns:
                sub = pa[pa[col].astype(str) == pitch_type]
                if not sub.empty:
                    for rv_col in ("run_value_per100", "rv_per_100", "run_value"):
                        if rv_col in sub.columns:
                            return round(float(sub.iloc[0][rv_col]), 2)

        return 0.0
