"""
pipeline.py
全レイヤー (fetch / aggregate / assess / output) を接続するオーケストレーター。

処理フロー:
  1. league-wide データを lazy fetch (シーズン1回)
  2. MLBAM ID → FanGraphs ID を解決
  3. 選手別データを fetch
  4. アグリゲーター → BatterStats / PitcherStats
  5. 査定 → BatterRating / PitcherRating
  6. Excel (生データ) + JSON (査定結果) を出力
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from rich.console import Console

from pawapro_scout.aggregate.batter_aggregator import BatterAggregator
from pawapro_scout.aggregate.pitcher_aggregator import PitcherAggregator
from pawapro_scout.assess.batter.basic import assess_basic as assess_batter_basic
from pawapro_scout.assess.batter.rank_abilities import assess_rank_abilities as assess_batter_rank
from pawapro_scout.assess.batter.gold_special import assess_gold_special as assess_batter_gold
from pawapro_scout.assess.batter.blue_special import assess_blue_special as assess_batter_blue
from pawapro_scout.assess.batter.red_special import assess_red_special as assess_batter_red
from pawapro_scout.assess.pitcher.basic import assess_basic as assess_pitcher_basic
from pawapro_scout.assess.pitcher.pitch_classifier import classify_pitches
from pawapro_scout.assess.pitcher.rank_abilities import assess_rank_abilities as assess_pitcher_rank
from pawapro_scout.assess.pitcher.gold_special import assess_gold_special as assess_pitcher_gold
from pawapro_scout.assess.pitcher.blue_special import assess_blue_special as assess_pitcher_blue
from pawapro_scout.assess.pitcher.red_special import assess_red_special as assess_pitcher_red
from pawapro_scout.cache.store import CacheStore
from pawapro_scout.config import CACHE_DIR
from pawapro_scout.fetch.fangraphs_leaderboard import FangraphsLeaderboardFetcher
from pawapro_scout.fetch.fangraphs_splits import FangraphsSplitsFetcher
from pawapro_scout.fetch.pybaseball_fetcher import PybaseballFetcher
from pawapro_scout.fetch.savant_leaderboard import SavantLeaderboardFetcher
from pawapro_scout.fetch.savant_search import SavantSearchFetcher
from pawapro_scout.models import (
    BatterRating,
    BatterStats,
    PlayerInput,
    PlayerRecord,
    PitcherRating,
    PitcherStats,
)
from pawapro_scout.output.excel_exporter import export_excel
from pawapro_scout.output.formatter import save_txt

logger = logging.getLogger(__name__)
console = Console()


class Pipeline:
    """
    1選手分の処理を行うパイプライン。
    league-wide データはインスタンス内でキャッシュして再利用する。
    """

    def __init__(
        self,
        season: int,
        output_dir: Path,
        force_refresh: bool = False,
    ) -> None:
        self.season = season
        self.output_dir = Path(output_dir)
        cache = CacheStore(CACHE_DIR / str(season), force_refresh=force_refresh)
        self.pyb = PybaseballFetcher(season, cache)
        self.savant_lb = SavantLeaderboardFetcher(season, cache)
        self.savant_search = SavantSearchFetcher(season, cache)
        self.fg = FangraphsSplitsFetcher(season, cache)
        self.fg_lb = FangraphsLeaderboardFetcher(season, cache)  # 新 REST API
        self._league: dict | None = None  # lazy-loaded

    # ──────────────────────────────────────────────
    # パブリック API
    # ──────────────────────────────────────────────

    def run(self, player: PlayerInput) -> PlayerRecord:
        """1選手分のフルパイプラインを実行して PlayerRecord を返す。"""
        console.rule(f"[bold cyan]{player.name_jp}[/bold cyan]")

        self._ensure_league()
        L = self._league

        # FanGraphs ID 解決
        ids = self.pyb.resolve_ids(player.mlbam_id)
        fg_id = _safe_int(ids.get("key_fangraphs"))

        batter_rating: BatterRating | None = None
        pitcher_rating: PitcherRating | None = None
        player_batter: dict | None = None
        player_pitcher: dict | None = None

        # ── 野手パス ──────────────────────────────
        if player.role in ("batter", "both"):
            console.print("[cyan]  野手データ取得中...[/cyan]")
            player_batter = self._fetch_batter_data(player.mlbam_id, fg_id)
            console.print("[cyan]  野手集計中...[/cyan]")
            b_stats = self._aggregate_batter(player, L, player_batter, fg_id)
            console.print("[cyan]  野手査定中...[/cyan]")
            batter_rating = self._assess_batter(b_stats, player.position)

        # ── 投手パス ──────────────────────────────
        if player.role in ("pitcher", "both"):
            console.print("[cyan]  投手データ取得中...[/cyan]")
            player_pitcher = self._fetch_pitcher_data(player.mlbam_id, fg_id)
            console.print("[cyan]  投手集計中...[/cyan]")
            p_stats = self._aggregate_pitcher(player, L, player_pitcher, fg_id)
            console.print("[cyan]  投手査定中...[/cyan]")
            pitcher_rating = self._assess_pitcher(p_stats)

        record = PlayerRecord(
            player=player.name_jp,
            season=player.season,
            type=player.role,
            batter=batter_rating,
            pitcher=pitcher_rating,
        )

        # ── 出力 ──────────────────────────────────
        self._save_txt(record, player)
        self._save_excel(player, L, player_batter, player_pitcher)

        console.print(f"[green]  [OK] {player.name_jp} 完了[/green]")
        return record

    # ──────────────────────────────────────────────
    # League-wide データ (lazy)
    # ──────────────────────────────────────────────

    def _ensure_league(self) -> None:
        if self._league is not None:
            return
        console.print("[cyan]リーグデータを取得中...[/cyan]")

        def _safe(name: str, fn) -> pd.DataFrame:
            """取得失敗時は警告のみ出して空DataFrameを返す。"""
            try:
                return fn()
            except Exception as e:
                logger.warning(f"{name} 取得失敗（空DataFrameで継続）: {e}")
                return pd.DataFrame()

        def _safe_fallback(name1: str, fn1, name2: str, fn2) -> pd.DataFrame:
            """fn1 を試し、空DataFrameなら fn2 にフォールバックする。"""
            df = _safe(name1, fn1)
            return df if not df.empty else _safe(name2, fn2)

        lb = _safe("savant_leaderboards", self.savant_lb.fetch_all)
        if not isinstance(lb, dict):
            lb = {}

        self._league = {
            "batter_expected":     _safe("batter_expected_stats",    self.pyb.get_batter_expected_stats),
            "pitcher_expected":    _safe("pitcher_expected_stats",   self.pyb.get_pitcher_expected_stats),
            "batter_percentile":   _safe("batter_percentile_ranks",  self.pyb.get_batter_percentile_ranks),
            "pitcher_percentile":  _safe("pitcher_percentile_ranks", self.pyb.get_pitcher_percentile_ranks),
            "sprint_speed":        _safe("sprint_speed",             self.pyb.get_sprint_speed),
            "outs_above_average":  _safe("outs_above_average",       self.pyb.get_outs_above_average),
            "catcher_poptime":     _safe("catcher_poptime",          self.pyb.get_catcher_poptime),
            "pitcher_active_spin": _safe("pitcher_active_spin",      self.pyb.get_pitcher_active_spin),
            # FanGraphs: 新 REST API を優先、空なら pybaseball にフォールバック
            "batting_stats_fg":  _safe_fallback(
                "batting_stats_fg(new)", self.fg_lb.get_batting_stats,
                "batting_stats_fg(pyb)", self.pyb.get_batting_stats_fg,
            ),
            "pitching_stats_fg": _safe_fallback(
                "pitching_stats_fg(new)", self.fg_lb.get_pitching_stats,
                "pitching_stats_fg(pyb)", self.pyb.get_pitching_stats_fg,
            ),
            "batting_stats_bref":  _safe("batting_stats_bref",       self.pyb.get_batting_stats_bref),
            "pitching_stats_bref": _safe("pitching_stats_bref",      self.pyb.get_pitching_stats_bref),
            # Savant leaderboards (7種)
            **lb,
        }
        console.print("[green]  [OK] リーグデータ取得完了[/green]")

    # ──────────────────────────────────────────────
    # 選手別データ取得
    # ──────────────────────────────────────────────

    def _fetch_batter_data(self, mlbam_id: int, fg_id: int | None) -> dict:
        splits: dict = {}
        if fg_id is not None:
            try:
                splits = self.fg.get_all_splits(
                    mlbam_id, fg_id, is_pitcher=False
                )
            except Exception as e:
                logger.warning(f"FanGraphs batter splits 取得失敗: {e}")

        # FG splits が全て空なら Statcast Search でフォールバック (⑥)
        if not any(not df.empty for df in splits.values()):
            logger.info("Statcast splits にフォールバック (batter)")
            splits = self._fetch_statcast_batter_splits(mlbam_id)

        return {
            "statcast_batter": self.pyb.get_statcast_batter(mlbam_id),
            "splits": splits,
        }

    def _fetch_statcast_batter_splits(self, mlbam_id: int) -> dict[str, pd.DataFrame]:
        """Statcast Search で野手スプリットを取得する (FG Splits 代替)。"""
        result: dict[str, pd.DataFrame] = {}
        targets = {
            "vs_lhp": self.savant_search.get_batter_vs_lhp,
            "vs_rhp": self.savant_search.get_batter_vs_rhp,
            "risp":   self.savant_search.get_batter_risp,
        }
        for key, method in targets.items():
            try:
                result[key] = method(mlbam_id)
            except Exception as e:
                logger.warning(f"Statcast batter split {key} 取得失敗: {e}")
                result[key] = pd.DataFrame()
        return result

    def _fetch_pitcher_data(self, mlbam_id: int, fg_id: int | None) -> dict:
        splits: dict = {}
        if fg_id is not None:
            try:
                splits = self.fg.get_all_splits(
                    mlbam_id, fg_id, is_pitcher=True
                )
            except Exception as e:
                logger.warning(f"FanGraphs pitcher splits 取得失敗: {e}")

        # FG splits が全て空なら Statcast Search でフォールバック (⑥)
        if not any(not df.empty for df in splits.values()):
            logger.info("Statcast splits にフォールバック (pitcher)")
            splits = self._fetch_statcast_pitcher_splits(mlbam_id)

        return self._fetch_pitcher_data_impl(mlbam_id, splits)

    def _fetch_statcast_pitcher_splits(self, mlbam_id: int) -> dict[str, pd.DataFrame]:
        """Statcast Search で投手スプリットを取得する (FG Splits 代替)。"""
        result: dict[str, pd.DataFrame] = {}
        targets = {
            "vs_lhp": self.savant_search.get_pitcher_vs_lhb,  # 投手視点: vs 左打者
            "vs_rhp": self.savant_search.get_pitcher_vs_rhb,  # 投手視点: vs 右打者
            "risp":   self.savant_search.get_pitcher_risp,
        }
        for key, method in targets.items():
            try:
                result[key] = method(mlbam_id)
            except Exception as e:
                logger.warning(f"Statcast pitcher split {key} 取得失敗: {e}")
                result[key] = pd.DataFrame()
        return result

    def _fetch_pitcher_inning_zone(self, mlbam_id: int) -> tuple:
        """投手のイニング別・ゾーン別データを取得する。"""
        savant_inning1 = savant_inning7plus = savant_zone = None
        try:
            savant_inning1 = self.savant_search.get_pitcher_inning(mlbam_id, "1|")
        except Exception as e:
            logger.warning(f"Savant inning1 取得失敗: {e}")
        try:
            savant_inning7plus = self.savant_search.get_pitcher_inning(
                mlbam_id, "7|8|9|10|11|12|"
            )
        except Exception as e:
            logger.warning(f"Savant inning7plus 取得失敗: {e}")
        try:
            savant_zone = self.savant_search.get_pitcher_zone(mlbam_id)
        except Exception as e:
            logger.warning(f"Savant zone 取得失敗: {e}")
        return savant_inning1, savant_inning7plus, savant_zone

    def _fetch_pitcher_data_impl(self, mlbam_id: int, splits: dict) -> dict:
        """投手データ取得の本体 (イニング/ゾーンも含む)。"""
        savant_inning1, savant_inning7plus, savant_zone = \
            self._fetch_pitcher_inning_zone(mlbam_id)
        return {
            "statcast_pitcher": self.pyb.get_statcast_pitcher(mlbam_id),
            "splits": splits,
            "savant_inning1": savant_inning1,
            "savant_inning7plus": savant_inning7plus,
            "savant_zone": savant_zone,
        }

    # ──────────────────────────────────────────────
    # アグリゲーター
    # ──────────────────────────────────────────────

    def _aggregate_batter(
        self,
        player: PlayerInput,
        L: dict,
        bd: dict,
        fg_id: int | None,
    ) -> BatterStats:
        agg = BatterAggregator(player.mlbam_id, fg_id, None)
        return agg.build(
            statcast_batter   = bd["statcast_batter"],
            batter_expected   = L["batter_expected"],
            batter_percentile = L["batter_percentile"],
            sprint_speed      = L["sprint_speed"],
            outs_above_average= L["outs_above_average"],
            batting_stats_fg  = L["batting_stats_fg"],
            batting_stats_bref= L["batting_stats_bref"],
            fielding_run_value= L.get("fielding_run_value", pd.DataFrame()),
            outfielder_throws  = L.get("outfielder_throws"),
            catcher_poptime   = L.get("catcher_poptime"),
            catcher_framing   = L.get("catcher_framing"),
            catcher_blocking  = L.get("catcher_blocking"),
            splits            = bd.get("splits"),
        )

    def _aggregate_pitcher(
        self,
        player: PlayerInput,
        L: dict,
        pd_data: dict,
        fg_id: int | None,
    ) -> PitcherStats:
        agg = PitcherAggregator(player.mlbam_id, fg_id, None)
        return agg.build(
            statcast_pitcher  = pd_data["statcast_pitcher"],
            pitcher_expected  = L["pitcher_expected"],
            pitcher_percentile= L["pitcher_percentile"],
            pitching_stats_fg = L["pitching_stats_fg"],
            pitching_stats_bref=L["pitching_stats_bref"],
            pitcher_fielding  = L.get("pitcher_fielding", pd.DataFrame()),
            pitch_arsenal     = L.get("pitch_arsenal", pd.DataFrame()),
            pitcher_active_spin=L.get("pitcher_active_spin", pd.DataFrame()),
            splits            = pd_data.get("splits"),
            savant_inning1    = pd_data.get("savant_inning1"),
            savant_inning7plus= pd_data.get("savant_inning7plus"),
            savant_zone       = pd_data.get("savant_zone"),
        )

    # ──────────────────────────────────────────────
    # 査定
    # ──────────────────────────────────────────────

    def _assess_batter(self, stats: BatterStats, position: str, age: int = 0) -> BatterRating:
        return BatterRating(
            basic          = assess_batter_basic(stats, position),
            rank_abilities = assess_batter_rank(stats, position),
            gold_special   = assess_batter_gold(stats, age=age, position=position),
            blue_special   = assess_batter_blue(stats),
            red_special    = assess_batter_red(stats),
        )

    def _assess_pitcher(self, stats: PitcherStats) -> PitcherRating:
        return PitcherRating(
            basic          = assess_pitcher_basic(stats),
            pitches        = classify_pitches(stats.pitches),
            rank_abilities = assess_pitcher_rank(stats),
            gold_special   = assess_pitcher_gold(stats),
            blue_special   = assess_pitcher_blue(stats),
            red_special    = assess_pitcher_red(stats),
        )

    # ──────────────────────────────────────────────
    # 出力
    # ──────────────────────────────────────────────

    def _save_txt(self, record: PlayerRecord, player: PlayerInput) -> None:
        path = self.output_dir / str(player.season) / "rating" / f"{player.name_jp}.txt"
        save_txt(record, path, team=player.team)
        console.print(f"  [green]TXT : {path}[/green]")

    def _save_excel(
        self,
        player: PlayerInput,
        L: dict,
        player_batter: dict | None,
        player_pitcher: dict | None,
    ) -> None:
        path = self.output_dir / str(player.season) / "raw" / f"{player.name_jp}.xlsx"
        try:
            export_excel(path, L, player_batter, player_pitcher)
            console.print(f"  [green]Excel: {path}[/green]")
        except Exception as e:
            logger.warning(f"Excel 出力失敗 ({player.name_jp}): {e}")


# ──────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────

def _safe_int(val) -> int | None:
    """NaN / None / 空文字 → None、それ以外は int に変換。"""
    if val is None:
        return None
    try:
        import math
        f = float(val)
        if math.isnan(f):
            return None
        return int(f)
    except (TypeError, ValueError):
        return None
