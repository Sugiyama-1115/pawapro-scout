"""
fetch/pybaseball_fetcher.py
pybaseball ライブラリ経由でデータを取得するFetcher。

league-wide (シーズン1回): 12関数
player-specific: statcast_batter / statcast_pitcher
"""

from __future__ import annotations

import logging

import pandas as pd
import pybaseball

from pawapro_scout.cache.store import CacheStore
from pawapro_scout.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# pybaseball の内部キャッシュも有効化（本プロジェクトのparquetキャッシュで管理するが念のため）
pybaseball.cache.enable()


class PybaseballFetcher(BaseFetcher):
    """
    pybaseball ライブラリのラッパー。
    全メソッドは CacheStore を通じてparquetにキャッシュされる。
    """

    def __init__(self, season: int, cache: CacheStore) -> None:
        super().__init__(cache)
        self.season = season
        self._start_dt = f"{season}-03-01"
        self._end_dt = f"{season}-11-30"

    # ──────────────────────────────────────────────
    # League-wide データ (シーズン1回)
    # ──────────────────────────────────────────────

    def get_batter_expected_stats(self) -> pd.DataFrame:
        """Savant 期待値統計 (野手): xBA, sweet_spot_percent, barrel等"""
        return self._cached_fetch(
            "league/pybaseball__batter_expected_stats",
            lambda: pybaseball.statcast_batter_expected_stats(self.season),
        )

    def get_pitcher_expected_stats(self) -> pd.DataFrame:
        """Savant 期待値統計 (投手): xERA, xFIP等"""
        return self._cached_fetch(
            "league/pybaseball__pitcher_expected_stats",
            lambda: pybaseball.statcast_pitcher_expected_stats(self.season),
        )

    def get_batter_percentile_ranks(self) -> pd.DataFrame:
        """Savant パーセンタイルランク (野手): xba, barrel, sprint_speed等"""
        return self._cached_fetch(
            "league/pybaseball__batter_percentile_ranks",
            lambda: pybaseball.statcast_batter_percentile_ranks(self.season),
        )

    def get_pitcher_percentile_ranks(self) -> pd.DataFrame:
        """Savant パーセンタイルランク (投手): k_percent, bb_percent, exit_velocity等"""
        return self._cached_fetch(
            "league/pybaseball__pitcher_percentile_ranks",
            lambda: pybaseball.statcast_pitcher_percentile_ranks(self.season),
        )

    def get_sprint_speed(self) -> pd.DataFrame:
        """Sprint Speed リーダーボード: sprint_speed, bolts"""
        return self._cached_fetch(
            "league/pybaseball__sprint_speed",
            lambda: pybaseball.statcast_sprint_speed(year=self.season),
        )

    def get_outs_above_average(self) -> pd.DataFrame:
        """OAA (Outs Above Average) リーダーボード"""
        return self._cached_fetch(
            "league/pybaseball__outs_above_average",
            lambda: pybaseball.statcast_outs_above_average(year=self.season, pos="all"),
        )

    def get_catcher_poptime(self) -> pd.DataFrame:
        """捕手 Pop Time リーダーボード"""
        return self._cached_fetch(
            "league/pybaseball__catcher_poptime",
            lambda: pybaseball.statcast_catcher_poptime(year=self.season),
        )

    def get_pitcher_active_spin(self) -> pd.DataFrame:
        """投手 Active Spin (球種別スピン効率)"""
        return self._cached_fetch(
            "league/pybaseball__pitcher_active_spin",
            lambda: pybaseball.statcast_pitcher_active_spin(year=self.season),
        )

    def get_batting_stats_fg(self) -> pd.DataFrame:
        """FanGraphs 打撃成績: K%, BB%, wOBA, WPA, LOB%等"""
        return self._cached_fetch(
            "league/pybaseball__batting_stats_fg",
            lambda: pybaseball.batting_stats(self.season, qual=1),
        )

    def get_pitching_stats_fg(self) -> pd.DataFrame:
        """FanGraphs 投球成績: K%, BB%, LOB%, HR/9, IR-S%等"""
        return self._cached_fetch(
            "league/pybaseball__pitching_stats_fg",
            lambda: pybaseball.pitching_stats(self.season, qual=1),
        )

    def get_batting_stats_bref(self) -> pd.DataFrame:
        """Baseball Reference 打撃成績: SB, CS, GDP, SH, G, XBT%等"""
        self._sleep_for_bref()
        return self._cached_fetch(
            "league/pybaseball__batting_stats_bref",
            lambda: pybaseball.batting_stats_bref(self.season),
        )

    def get_pitching_stats_bref(self) -> pd.DataFrame:
        """Baseball Reference 投球成績: G, IP, PO(牽制死)等"""
        self._sleep_for_bref()
        return self._cached_fetch(
            "league/pybaseball__pitching_stats_bref",
            lambda: pybaseball.pitching_stats_bref(self.season),
        )

    # ──────────────────────────────────────────────
    # Player-specific データ
    # ──────────────────────────────────────────────

    def get_statcast_batter(self, mlbam_id: int) -> pd.DataFrame:
        """
        pitch-level 野手データ (打球イベント全件)。
        launch_angle, launch_speed, hc_x, pfx_x等を含む。
        """
        key = self.cache.player_key(mlbam_id, "statcast_batter")
        return self._cached_fetch(
            key,
            lambda: pybaseball.statcast_batter(
                self._start_dt, self._end_dt, player_id=mlbam_id
            ),
        )

    def get_statcast_pitcher(self, mlbam_id: int) -> pd.DataFrame:
        """
        pitch-level 投手データ (全投球)。
        release_speed, pfx_x, pfx_z, release_pos_x, release_pos_z等を含む。
        """
        key = self.cache.player_key(mlbam_id, "statcast_pitcher")
        return self._cached_fetch(
            key,
            lambda: pybaseball.statcast_pitcher(
                self._start_dt, self._end_dt, player_id=mlbam_id
            ),
        )

    # ──────────────────────────────────────────────
    # ID 解決ユーティリティ
    # ──────────────────────────────────────────────

    # モジュールレベルのID変換キャッシュ (1run内で再利用)
    _id_cache: dict[int, dict] = {}

    def resolve_ids(self, mlbam_id: int) -> dict:
        """
        MLBAM ID → {key_mlbam, key_fangraphs, key_bbref} を返す。
        結果はメモリキャッシュに保存して再利用する。
        """
        if mlbam_id in self._id_cache:
            return self._id_cache[mlbam_id]

        result = pybaseball.playerid_reverse_lookup([mlbam_id], key_type="mlbam")
        if result.empty:
            logger.warning(f"MLBAM ID {mlbam_id} の解決に失敗しました")
            ids = {"key_mlbam": mlbam_id, "key_fangraphs": None, "key_bbref": None}
        else:
            row = result.iloc[0]
            ids = {
                "key_mlbam": mlbam_id,
                "key_fangraphs": row.get("key_fangraphs"),
                "key_bbref": row.get("key_bbref"),
            }

        self._id_cache[mlbam_id] = ids
        return ids
