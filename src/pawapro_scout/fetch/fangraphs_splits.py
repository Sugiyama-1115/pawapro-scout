"""
fetch/fangraphs_splits.py
FanGraphs Splits Leaderboard (非公式API) から
対左右・RISP・High Leverage 等のスプリット成績を取得する。

エンドポイント: POST https://www.fangraphs.com/api/leaders/splits/splits-leaders
FanGraphs独自のplayer IDが必要なため、pybaseball.playerid_reverse_lookup で解決する。
"""

from __future__ import annotations

import logging

import pandas as pd

from pawapro_scout.cache.store import CacheStore
from pawapro_scout.config import FANGRAPHS_SPLIT_IDS, FANGRAPHS_SPLITS_URL
from pawapro_scout.fetch.base import BaseFetcher

logger = logging.getLogger(__name__)


class FangraphsSplitsFetcher(BaseFetcher):
    """
    FanGraphs Splits Leaderboard を取得するFetcher。

    Note:
        FanGraphs は MLBAM ID でなく独自の key_fangraphs を使う。
        PybaseballFetcher.resolve_ids() で変換してから渡すこと。
    """

    def __init__(self, season: int, cache: CacheStore) -> None:
        super().__init__(cache)
        self.season = season

    # ──────────────────────────────────────────────
    # 内部共通メソッド
    # ──────────────────────────────────────────────

    def _build_payload(
        self,
        fg_player_id: int | str,
        split_id: int,
        is_pitcher: bool,
    ) -> dict:
        """FanGraphs Splits API の POST ペイロードを組み立てる。"""
        return {
            "strPlayerId": str(fg_player_id),
            "strSplitArr": [split_id],
            "strGroup": "season",
            "strPosition": "P" if is_pitcher else "B",
            "strType": "1" if is_pitcher else "0",
            "strStartDate": f"{self.season}-03-01",
            "strEndDate": f"{self.season}-11-30",
            "strSplitTeams": False,
            "dctFilters": [],
            "strStatType": "player",
            "strAutoPt": "false",
            "arrPlayerId": [],
            "strSplitTeamsJoin": False,
        }

    def _fetch_split(
        self,
        mlbam_id: int,
        fg_player_id: int | str,
        split_name: str,
        split_id: int,
        is_pitcher: bool,
    ) -> pd.DataFrame:
        """単一スプリットを取得してキャッシュする。"""
        key = self.cache.player_key(mlbam_id, f"fangraphs__splits__{split_name}")

        def fetch() -> pd.DataFrame:
            payload = self._build_payload(fg_player_id, split_id, is_pitcher)
            logger.info(
                f"FanGraphs Splits 取得: {split_name} "
                f"(fg_id={fg_player_id}, season={self.season})"
            )
            data = self._post_json(FANGRAPHS_SPLITS_URL, payload)

            # レスポンスは {"data": [...]} または直接リスト の場合がある
            if isinstance(data, dict):
                records = data.get("data") or data.get("splitData") or []
            elif isinstance(data, list):
                records = data
            else:
                records = []

            return pd.DataFrame(records)

        return self._cached_fetch(key, fetch)

    # ──────────────────────────────────────────────
    # 公開メソッド
    # ──────────────────────────────────────────────

    def get_all_splits(
        self,
        mlbam_id: int,
        fg_player_id: int | str,
        is_pitcher: bool,
    ) -> dict[str, pd.DataFrame]:
        """
        全5種のスプリットをまとめて取得する。

        Returns:
            {
                "vs_lhp": DataFrame,
                "vs_rhp": DataFrame,
                "risp":   DataFrame,
                "bases_empty": DataFrame,
                "high_lev": DataFrame,
            }
        """
        results: dict[str, pd.DataFrame] = {}
        for split_name, split_id in FANGRAPHS_SPLIT_IDS.items():
            try:
                results[split_name] = self._fetch_split(
                    mlbam_id, fg_player_id, split_name, split_id, is_pitcher
                )
            except Exception as e:
                logger.error(
                    f"FanGraphs Splits 取得失敗: {split_name} "
                    f"(fg_id={fg_player_id}) → {e}"
                )
                results[split_name] = pd.DataFrame()
        return results

    def get_vs_lhp(self, mlbam_id: int, fg_player_id: int | str, is_pitcher: bool) -> pd.DataFrame:
        """対左投手 (野手) / 対左打者 (投手) のスプリット"""
        return self._fetch_split(
            mlbam_id, fg_player_id, "vs_lhp", FANGRAPHS_SPLIT_IDS["vs_lhp"], is_pitcher
        )

    def get_vs_rhp(self, mlbam_id: int, fg_player_id: int | str, is_pitcher: bool) -> pd.DataFrame:
        """対右投手 (野手) / 対右打者 (投手) のスプリット"""
        return self._fetch_split(
            mlbam_id, fg_player_id, "vs_rhp", FANGRAPHS_SPLIT_IDS["vs_rhp"], is_pitcher
        )

    def get_risp(self, mlbam_id: int, fg_player_id: int | str, is_pitcher: bool) -> pd.DataFrame:
        """得点圏 (RISP) のスプリット"""
        return self._fetch_split(
            mlbam_id, fg_player_id, "risp", FANGRAPHS_SPLIT_IDS["risp"], is_pitcher
        )

    def get_bases_empty(self, mlbam_id: int, fg_player_id: int | str, is_pitcher: bool) -> pd.DataFrame:
        """無走者のスプリット"""
        return self._fetch_split(
            mlbam_id, fg_player_id, "bases_empty", FANGRAPHS_SPLIT_IDS["bases_empty"], is_pitcher
        )

    def get_high_leverage(self, mlbam_id: int, fg_player_id: int | str, is_pitcher: bool) -> pd.DataFrame:
        """High Leverage 場面のスプリット"""
        return self._fetch_split(
            mlbam_id, fg_player_id, "high_lev", FANGRAPHS_SPLIT_IDS["high_lev"], is_pitcher
        )
