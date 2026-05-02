"""
fetch/fangraphs_leaderboard.py
FanGraphs の新しい REST API からリーグ全体の打撃・投球成績を取得する。

エンドポイント:
  GET https://www.fangraphs.com/api/leaders/major-league/data
  ?pos=all&stats=bat|pit&lg=all&qual=y&season=YYYY&season1=YYYY
  &pageitems=2000000&type=8&ind=0

旧 pybaseball の batting_stats() / pitching_stats() が使う
leaders-legacy.aspx (403) の代替実装。

返すDataFrame の ID 列:
  playerid (FanGraphs 内部ID) → "IDfg" にリネームして
  既存 aggregator の _row(df, "IDfg", fg_id) と互換にする。
"""

from __future__ import annotations

import logging

import pandas as pd

from pawapro_scout.cache.store import CacheStore
from pawapro_scout.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)

# FanGraphs 新 REST API
_FG_LEADERBOARD_URL = "https://www.fangraphs.com/api/leaders/major-league/data"

# type=8 はダッシュボード統計 (K%/BB%/WPA/LOB%等を含む)
_FG_TYPE = 8


class FangraphsLeaderboardFetcher(BaseFetcher):
    """
    FanGraphs の新しい JSON REST API からリーグ全体統計を取得する。

    pybaseball の batting_stats() / pitching_stats() が使う
    leaders-legacy.aspx (403) の代替として使う。
    """

    def __init__(self, season: int, cache: CacheStore) -> None:
        super().__init__(cache)
        self.season = season

    # ──────────────────────────────────────────────
    # 公開メソッド
    # ──────────────────────────────────────────────

    def get_batting_stats(self) -> pd.DataFrame:
        """
        FanGraphs 打撃成績 (全選手, 1打席以上)。
        主要列: IDfg, K%, BB%, WPA, AVG, G
        ※ batting type=8 には LOB% が含まれないため 0.0 になる。
        """
        return self._cached_fetch(
            "league/fg_new__batting_stats",
            lambda: self._fetch("bat", qual="y"),
        )

    def get_pitching_stats(self) -> pd.DataFrame:
        """
        FanGraphs 投球成績 (全選手, 1登板以上)。
        主要列: IDfg, K%, BB%, WPA, LOB%, HR/9, G, GS, IP, Pitches, Hard%
        """
        return self._cached_fetch(
            "league/fg_new__pitching_stats",
            lambda: self._fetch("pit", qual="1"),
        )

    # ──────────────────────────────────────────────
    # 内部実装
    # ──────────────────────────────────────────────

    def _fetch(self, stats: str, qual: str = "y") -> pd.DataFrame:
        """
        FanGraphs 新 REST API を呼び出して DataFrame を返す。

        Args:
            stats: "bat" (打撃) または "pit" (投球)
            qual:  最低出場基準 ("y" = FG 既定, "1" = 1登板以上)
        """
        params = {
            "pos":       "all",
            "stats":     stats,
            "lg":        "all",
            "qual":      qual,
            "season":    self.season,
            "season1":   self.season,
            "pageitems": 2_000_000,
            "pagenum":   1,
            "type":      _FG_TYPE,
            "ind":       0,
        }
        logger.info(
            f"FanGraphs leaderboard 取得: stats={stats} season={self.season}"
        )
        data = self._get_json(_FG_LEADERBOARD_URL, params=params)

        # レスポンスは {"data": [...]} 形式
        records = data.get("data", []) if isinstance(data, dict) else data
        df = pd.DataFrame(records)

        if df.empty:
            logger.warning(f"FanGraphs leaderboard: 空レスポンス (stats={stats})")
            return df

        # playerid → IDfg にリネーム (aggregator との互換性)
        if "playerid" in df.columns:
            df = df.rename(columns={"playerid": "IDfg"})

        logger.info(
            f"FanGraphs leaderboard 取得完了: stats={stats}, {len(df)} 選手"
        )
        return df
