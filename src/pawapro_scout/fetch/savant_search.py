"""
fetch/savant_search.py
Baseball Savant の Statcast Search 集計エンドポイントを使って
ゾーン別 / カウント別 / イニング別 の集計データを取得する。

pitch-level の生データは取得せず、サーバー側で集計した CSV を受け取るため軽量。
エンドポイント: GET https://baseballsavant.mlb.com/statcast_search/csv
"""

from __future__ import annotations

import logging

import pandas as pd

from pawapro_scout.cache.store import CacheStore
from pawapro_scout.config import SAVANT_STATCAST_CSV_URL
from pawapro_scout.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# 2ストライクカウント一覧 (粘り打ち / 奪三振系に使用)
TWO_STRIKE_COUNTS = "02|12|22|32"

# ゾーン番号:
#   1-9: ストライクゾーン (1=左上 〜 9=右下)
#   11-14: ボールゾーン (Shadow)
# 下段3ゾーン: 7,8,9  / Heart Zone: 5
LOW_ZONES = "7|8|9"
HEART_ZONE = "5"
INNER_ZONES_RHB = "1|4|7"   # 右打者内角


class SavantSearchFetcher(BaseFetcher):
    """
    Statcast Search の集計エンドポイントで
    ゾーン別・カウント別・イニング別の集計を取得する。
    """

    def __init__(self, season: int, cache: CacheStore) -> None:
        super().__init__(cache)
        self.season = season

    # ──────────────────────────────────────────────
    # 内部共通メソッド
    # ──────────────────────────────────────────────

    def _base_params(self, mlbam_id: int, is_pitcher: bool) -> dict:
        """Statcast Search の共通クエリパラメータを返す。"""
        params: dict = {
            "all": "true",
            "hfSea": f"{self.season}|",
            "hfGT": "R|",           # Regular Season
            "min_pitches": "0",
            "min_results": "0",
            "type": "details",
            "player_event_sort": "api_p_release_speed",
            "sort_order": "desc",
        }
        if is_pitcher:
            params["pitchers_lookup[]"] = str(mlbam_id)
            params["group_by"] = "name-pitcher"
        else:
            params["batters_lookup[]"] = str(mlbam_id)
            params["group_by"] = "name-batter"
        return params

    def _fetch_aggregate(
        self,
        cache_key: str,
        mlbam_id: int,
        is_pitcher: bool,
        extra_params: dict,
    ) -> pd.DataFrame:
        """集計CSVを取得してキャッシュする。"""

        def fetch() -> pd.DataFrame:
            params = {**self._base_params(mlbam_id, is_pitcher), **extra_params}
            logger.info(f"Savant Search 取得: {cache_key}")
            return self._get_csv(SAVANT_STATCAST_CSV_URL, params=params)

        return self._cached_fetch(cache_key, fetch)

    # ──────────────────────────────────────────────
    # 投手用 集計
    # ──────────────────────────────────────────────

    def get_pitcher_pitch_type(self, mlbam_id: int) -> pd.DataFrame:
        """
        投手の球種別集計。
        usage%, velocity_avg, whiff_pct, run_value_per_100 等を含む。
        """
        key = self.cache.player_key(mlbam_id, "savant__pitch_type")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=True,
            extra_params={"group_by": "name-pitcher,pitch_type"},
        )

    def get_pitcher_zone(self, mlbam_id: int) -> pd.DataFrame:
        """
        投手のゾーン別集計。
        低め◯ (zone 7-9)、逃げ球 (zone 5) の算出に使う。
        """
        key = self.cache.player_key(mlbam_id, "savant__zone")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=True,
            extra_params={"group_by": "name-pitcher,zone"},
        )

    def get_pitcher_inning(self, mlbam_id: int, innings: str) -> pd.DataFrame:
        """
        投手のイニング別集計。
        立ち上がり◯ (inning=1), 尻上がり (inning=7+) 等に使う。

        Args:
            innings: パイプ区切りのイニング番号 (例: "1|" または "7|8|9|10|11|")
        """
        inning_label = innings.replace("|", "_").strip("_")
        key = self.cache.player_key(mlbam_id, f"savant__inning_{inning_label}")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=True,
            extra_params={"hfInn": innings},
        )

    def get_pitcher_high_pitch_count(self, mlbam_id: int, min_pitch: int = 100) -> pd.DataFrame:
        """
        投球数 N球以降の集計 (ド根性・根性◯・完全燃焼 等に使用)。
        Statcast Search の pitch_number_appearance フィルタを使う。

        Note: hfPit パラメータではなく、取得後にpitch-levelで集計が必要なケースもある。
        ここでは group_by=name-pitcher で全体集計を返す。
        """
        key = self.cache.player_key(mlbam_id, f"savant__highpitch_{min_pitch}")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=True,
            extra_params={"hfPitN": f"{min_pitch}|"},  # 投球数フィルタ
        )

    # ──────────────────────────────────────────────
    # 野手用 集計
    # ──────────────────────────────────────────────

    def get_batter_pitch_type(self, mlbam_id: int) -> pd.DataFrame:
        """
        野手の被球種別集計。
        対変化球ランク制 (Breaking Run Value) の算出に使う。
        """
        key = self.cache.player_key(mlbam_id, "savant__batter_pitch_type")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=False,
            extra_params={"group_by": "name-batter,pitch_type"},
        )

    def get_batter_two_strike(self, mlbam_id: int) -> pd.DataFrame:
        """
        野手の2ストライク後集計 (粘り打ち青特)。
        """
        key = self.cache.player_key(mlbam_id, "savant__batter_2strike")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=False,
            extra_params={"hfC": TWO_STRIKE_COUNTS},
        )

    def get_batter_count(self, mlbam_id: int, counts: str) -> pd.DataFrame:
        """
        野手の特定カウント集計 (初球◯ 等)。

        Args:
            counts: パイプ区切りのカウント (例: "00|10|20|30" = 0ストライク)
        """
        count_label = counts.replace("|", "_").strip("_")
        key = self.cache.player_key(mlbam_id, f"savant__batter_count_{count_label}")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=False,
            extra_params={"hfC": counts},
        )

    # ──────────────────────────────────────────────
    # 野手 スプリット (FanGraphs Splits 代替)
    # ──────────────────────────────────────────────

    def get_batter_vs_lhp(self, mlbam_id: int) -> pd.DataFrame:
        """
        野手の対左投手成績。
        FanGraphs Splits (vs_lhp) の代替。
        主要列: estimated_woba_using_speedangle (xwOBA), woba_value
        """
        key = self.cache.player_key(mlbam_id, "savant__batter_vs_lhp")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=False,
            extra_params={"pitcher_throws": "L"},
        )

    def get_batter_vs_rhp(self, mlbam_id: int) -> pd.DataFrame:
        """
        野手の対右投手成績。
        FanGraphs Splits (vs_rhp) の代替。
        """
        key = self.cache.player_key(mlbam_id, "savant__batter_vs_rhp")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=False,
            extra_params={"pitcher_throws": "R"},
        )

    def get_batter_risp(self, mlbam_id: int) -> pd.DataFrame:
        """
        野手の得点圏 (RISP) 成績。
        FanGraphs Splits (risp) の代替。
        hfPR=risp| = 2塁または3塁にランナーがいる場面。
        """
        key = self.cache.player_key(mlbam_id, "savant__batter_risp")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=False,
            extra_params={"hfPR": "risp|"},
        )

    # ──────────────────────────────────────────────
    # 投手 スプリット (FanGraphs Splits 代替)
    # ──────────────────────────────────────────────

    def get_pitcher_vs_lhb(self, mlbam_id: int) -> pd.DataFrame:
        """
        投手の対左打者成績。
        FanGraphs Splits (vs_lhp キー: 投手視点では左打者) の代替。
        """
        key = self.cache.player_key(mlbam_id, "savant__pitcher_vs_lhb")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=True,
            extra_params={"batter_stands": "L"},
        )

    def get_pitcher_vs_rhb(self, mlbam_id: int) -> pd.DataFrame:
        """
        投手の対右打者成績。
        FanGraphs Splits (vs_rhp キー) の代替。
        """
        key = self.cache.player_key(mlbam_id, "savant__pitcher_vs_rhb")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=True,
            extra_params={"batter_stands": "R"},
        )

    def get_pitcher_risp(self, mlbam_id: int) -> pd.DataFrame:
        """
        投手の得点圏 (RISP) 成績。
        FanGraphs Splits (risp) の代替。
        """
        key = self.cache.player_key(mlbam_id, "savant__pitcher_risp")
        return self._fetch_aggregate(
            key, mlbam_id, is_pitcher=True,
            extra_params={"hfPR": "risp|"},
        )
