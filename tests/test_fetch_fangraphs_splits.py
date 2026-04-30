"""
tests/test_fetch_fangraphs_splits.py
FangraphsSplitsFetcher のテスト。requests をモックして
ペイロード構築・レスポンス解析・キャッシュキー を検証する。
"""

import pytest
import pandas as pd
from unittest.mock import patch

from pawapro_scout.cache.store import CacheStore
from pawapro_scout.config import FANGRAPHS_SPLIT_IDS, FANGRAPHS_SPLITS_URL
from pawapro_scout.fetch.fangraphs_splits import FangraphsSplitsFetcher


# ──────────────────────────────────────────────
# フィクスチャ
# ──────────────────────────────────────────────

MLBAM_ID = 660271
FG_ID = 19755


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr("pawapro_scout.cache.store.CACHE_DIR", tmp_path)
    return CacheStore(season=2025)


@pytest.fixture
def fetcher(tmp_store):
    return FangraphsSplitsFetcher(season=2025, cache=tmp_store)


# ──────────────────────────────────────────────
# _build_payload テスト
# ──────────────────────────────────────────────

class TestBuildPayload:
    def test_pitcher_position_and_type(self, fetcher):
        payload = fetcher._build_payload(FG_ID, split_id=5, is_pitcher=True)
        assert payload["strPosition"] == "P"
        assert payload["strType"] == "1"

    def test_batter_position_and_type(self, fetcher):
        payload = fetcher._build_payload(FG_ID, split_id=5, is_pitcher=False)
        assert payload["strPosition"] == "B"
        assert payload["strType"] == "0"

    def test_player_id_as_string(self, fetcher):
        payload = fetcher._build_payload(FG_ID, split_id=5, is_pitcher=True)
        assert payload["strPlayerId"] == str(FG_ID)

    def test_split_arr_single_id(self, fetcher):
        vs_lhp_id = FANGRAPHS_SPLIT_IDS["vs_lhp"]  # 5
        payload = fetcher._build_payload(FG_ID, split_id=vs_lhp_id, is_pitcher=False)
        assert payload["strSplitArr"] == [vs_lhp_id]

    def test_start_date(self, fetcher):
        payload = fetcher._build_payload(FG_ID, split_id=5, is_pitcher=False)
        assert payload["strStartDate"] == "2025-03-01"

    def test_end_date(self, fetcher):
        payload = fetcher._build_payload(FG_ID, split_id=5, is_pitcher=False)
        assert payload["strEndDate"] == "2025-11-30"


# ──────────────────────────────────────────────
# APIレスポンス解析テスト
# ──────────────────────────────────────────────

class TestResponseParsing:
    def test_response_dict_with_data_key(self, fetcher, requests_mock):
        """{"data": [...]} 形式のレスポンスを正しく解析する"""
        requests_mock.post(
            FANGRAPHS_SPLITS_URL,
            json={"data": [{"wOBA": 0.350, "AVG": 0.280}, {"wOBA": 0.310, "AVG": 0.250}]},
        )
        result = fetcher.get_vs_lhp(MLBAM_ID, FG_ID, is_pitcher=False)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_response_list_directly(self, fetcher, requests_mock):
        """レスポンスが直接リストの場合も動作する"""
        requests_mock.post(
            FANGRAPHS_SPLITS_URL,
            json=[{"wOBA": 0.350}, {"wOBA": 0.310}],
        )
        result = fetcher.get_vs_rhp(MLBAM_ID, FG_ID, is_pitcher=False)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_response_empty_data(self, fetcher, requests_mock):
        """{"data": []} のとき空 DataFrame を返す"""
        requests_mock.post(FANGRAPHS_SPLITS_URL, json={"data": []})
        result = fetcher.get_risp(MLBAM_ID, FG_ID, is_pitcher=False)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_response_split_data_key(self, fetcher, requests_mock):
        """{"splitData": [...]} キーも正しく解析する"""
        requests_mock.post(
            FANGRAPHS_SPLITS_URL,
            json={"splitData": [{"wOBA": 0.320}]},
        )
        result = fetcher.get_bases_empty(MLBAM_ID, FG_ID, is_pitcher=False)
        assert len(result) == 1


# ──────────────────────────────────────────────
# キャッシュキーテスト
# ──────────────────────────────────────────────

class TestCacheKeys:
    @pytest.mark.parametrize("split_name", list(FANGRAPHS_SPLIT_IDS.keys()))
    def test_cache_key_format(self, split_name, fetcher, tmp_store, requests_mock):
        requests_mock.post(FANGRAPHS_SPLITS_URL, json={"data": [{"wOBA": 0.300}]})
        fetcher._fetch_split(MLBAM_ID, FG_ID, split_name, FANGRAPHS_SPLIT_IDS[split_name], False)
        expected_key = f"players/{MLBAM_ID}/fangraphs__splits__{split_name}"
        assert tmp_store.exists(expected_key)

    def test_different_splits_have_different_keys(self, fetcher, tmp_store, requests_mock):
        requests_mock.post(FANGRAPHS_SPLITS_URL, json={"data": [{"wOBA": 0.300}]})
        fetcher.get_vs_lhp(MLBAM_ID, FG_ID, is_pitcher=False)
        fetcher.get_vs_rhp(MLBAM_ID, FG_ID, is_pitcher=False)
        assert tmp_store.exists(f"players/{MLBAM_ID}/fangraphs__splits__vs_lhp")
        assert tmp_store.exists(f"players/{MLBAM_ID}/fangraphs__splits__vs_rhp")

    def test_cache_hit_does_not_re_post(self, fetcher, requests_mock):
        requests_mock.post(FANGRAPHS_SPLITS_URL, json={"data": [{"wOBA": 0.300}]})
        fetcher.get_vs_lhp(MLBAM_ID, FG_ID, is_pitcher=False)
        fetcher.get_vs_lhp(MLBAM_ID, FG_ID, is_pitcher=False)  # 2回目
        assert requests_mock.call_count == 1


# ──────────────────────────────────────────────
# get_all_splits テスト
# ──────────────────────────────────────────────

class TestGetAllSplits:
    def test_returns_5_keys(self, fetcher, requests_mock):
        requests_mock.post(FANGRAPHS_SPLITS_URL, json={"data": [{"wOBA": 0.300}]})
        result = fetcher.get_all_splits(MLBAM_ID, FG_ID, is_pitcher=False)
        assert len(result) == 5
        expected_keys = {"vs_lhp", "vs_rhp", "risp", "bases_empty", "high_lev"}
        assert set(result.keys()) == expected_keys

    def test_calls_correct_split_ids(self, fetcher, requests_mock):
        """各スプリットで POST body に正しい split_id が含まれる"""
        posted_split_ids = []

        def capture_request(request, context):
            body = request.json()
            posted_split_ids.extend(body.get("strSplitArr", []))
            return {"data": [{"wOBA": 0.300}]}

        requests_mock.post(FANGRAPHS_SPLITS_URL, json=capture_request)
        fetcher.get_all_splits(MLBAM_ID, FG_ID, is_pitcher=True)

        expected_ids = list(FANGRAPHS_SPLIT_IDS.values())
        assert sorted(posted_split_ids) == sorted(expected_ids)

    def test_skip_on_error(self, fetcher, requests_mock):
        """1スプリットが失敗しても他は正常に返る"""
        call_count = 0

        def maybe_fail(request, context):
            nonlocal call_count
            call_count += 1
            body = request.json()
            if body.get("strSplitArr") == [FANGRAPHS_SPLIT_IDS["vs_lhp"]]:
                context.status_code = 500
                return {}
            return {"data": [{"wOBA": 0.300}]}

        requests_mock.post(FANGRAPHS_SPLITS_URL, json=maybe_fail)
        result = fetcher.get_all_splits(MLBAM_ID, FG_ID, is_pitcher=False)

        # 失敗したキーは空DataFrame
        assert result["vs_lhp"].empty
        # 他のキーは正常
        for key in ["vs_rhp", "risp", "bases_empty", "high_lev"]:
            assert not result[key].empty, f"{key} should have data"

    def test_all_values_are_dataframes(self, fetcher, requests_mock):
        requests_mock.post(FANGRAPHS_SPLITS_URL, json={"data": [{"wOBA": 0.300}]})
        result = fetcher.get_all_splits(MLBAM_ID, FG_ID, is_pitcher=True)
        for key, df in result.items():
            assert isinstance(df, pd.DataFrame), f"{key} is not a DataFrame"
