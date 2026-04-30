"""
fetch/savant_leaderboard.py
Baseball Savant の専用リーダーボード (pybaseballに存在しないもの) を取得する。

対象エンドポイント (7種):
  catcher_framing / catcher_blocking / catcher_throwing
  pitcher_fielding / pitch_arsenal / outfielder_throws / fielding_run_value

全て GET ?year=<season>&csv=true で CSV が取得できる。
"""

from __future__ import annotations

import logging

import pandas as pd

from pawapro_scout.cache.store import CacheStore
from pawapro_scout.config import SAVANT_LEADERBOARD_BASE, SAVANT_LEADERBOARD_SLUGS
from pawapro_scout.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)


class SavantLeaderboardFetcher(BaseFetcher):
    """Savant リーダーボードを CSV で取得するFetcher。"""

    def __init__(self, season: int, cache: CacheStore) -> None:
        super().__init__(cache)
        self.season = season

    # ──────────────────────────────────────────────
    # 内部共通メソッド
    # ──────────────────────────────────────────────

    def _fetch_leaderboard(self, slug_key: str, extra_params: dict | None = None) -> pd.DataFrame:
        """
        指定スラッグのリーダーボードを取得してキャッシュする。

        Args:
            slug_key: SAVANT_LEADERBOARD_SLUGS のキー名
            extra_params: URL に追加するクエリパラメータ
        """
        slug = SAVANT_LEADERBOARD_SLUGS[slug_key]
        cache_key = f"league/savant__{slug_key}"
        url = f"{SAVANT_LEADERBOARD_BASE}/{slug}"
        params = {"year": self.season, "csv": "true", **(extra_params or {})}

        def fetch() -> pd.DataFrame:
            logger.info(f"Savant leaderboard 取得: {slug} (season={self.season})")
            df = self._get_csv(url, params=params)
            return df

        return self._cached_fetch(cache_key, fetch)

    # ──────────────────────────────────────────────
    # 公開メソッド (7エンドポイント)
    # ──────────────────────────────────────────────

    def get_catcher_framing(self) -> pd.DataFrame:
        """
        捕手 Framing リーダーボード。
        主要列: player_id, framing_runs (フレーミング貢献度)
        査定用途: ささやき戦術・キャッチャー金特
        """
        return self._fetch_leaderboard("catcher_framing")

    def get_catcher_blocking(self) -> pd.DataFrame:
        """
        捕手 Blocking リーダーボード。
        主要列: player_id, blocks_above_average
        査定用途: 鉄の壁 金特
        """
        return self._fetch_leaderboard("catcher_blocking")

    def get_catcher_throwing(self) -> pd.DataFrame:
        """
        捕手 Throwing リーダーボード。
        主要列: player_id, pop_time_2b, pop_time_3b, arm_strength
        査定用途: バズーカ送球 金特, 肩力
        """
        return self._fetch_leaderboard("catcher_throwing")

    def get_pitcher_fielding(self) -> pd.DataFrame:
        """
        投手 Fielding (P-OAA) リーダーボード。
        主要列: player_id, outs_above_average
        査定用途: 打球反応◯ 青特
        """
        return self._fetch_leaderboard("pitcher_fielding")

    def get_pitch_arsenal(self) -> pd.DataFrame:
        """
        Pitch Arsenal Stats (球種別 Run Value) リーダーボード。
        主要列: player_id, pitch_type, run_value_per_100, whiff_percent
        査定用途: 変化球変化量決定, 対変化球ランク制
        """
        return self._fetch_leaderboard("pitch_arsenal")

    def get_outfielder_throws(self) -> pd.DataFrame:
        """
        外野手 Arm Strength リーダーボード。
        主要列: player_id, arm_value, max_throw_speed
        査定用途: 肩力 (外野手)
        """
        return self._fetch_leaderboard("outfielder_throws")

    def get_fielding_run_value(self) -> pd.DataFrame:
        """
        Fielding Run Value リーダーボード (全ポジション)。
        主要列: player_id, position, frv, throwing_frv, errors
        査定用途: 捕球, エラー赤特, 送球ランク制
        """
        return self._fetch_leaderboard("fielding_run_value")

    # ──────────────────────────────────────────────
    # 全リーダーボードをまとめて取得
    # ──────────────────────────────────────────────

    def fetch_all(self) -> dict[str, pd.DataFrame]:
        """
        全7リーダーボードを取得して辞書で返す。
        失敗したエンドポイントは空DataFrameを格納してスキップする。
        """
        results: dict[str, pd.DataFrame] = {}
        methods = {
            "catcher_framing": self.get_catcher_framing,
            "catcher_blocking": self.get_catcher_blocking,
            "catcher_throwing": self.get_catcher_throwing,
            "pitcher_fielding": self.get_pitcher_fielding,
            "pitch_arsenal": self.get_pitch_arsenal,
            "outfielder_throws": self.get_outfielder_throws,
            "fielding_run_value": self.get_fielding_run_value,
        }
        for name, method in methods.items():
            try:
                results[name] = method()
            except Exception as e:
                logger.error(f"Savant leaderboard 取得失敗: {name} → {e}")
                results[name] = pd.DataFrame()
        return results
