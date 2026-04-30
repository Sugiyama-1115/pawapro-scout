"""
tests/test_fetch_savant_search.py
SavantSearchFetcher のテスト。requests をモックして
正しいパラメータで呼ばれているか / キャッシュキーが正しいか を検証する。
"""

import pytest
import pandas as pd

from pawapro_scout.cache.store import CacheStore
from pawapro_scout.config import SAVANT_STATCAST_CSV_URL
from pawapro_scout.fetch.savant_search import SavantSearchFetcher, TWO_STRIKE_COUNTS


# ──────────────────────────────────────────────
# フィクスチャ
# ──────────────────────────────────────────────

CSV_TEXT = "pitch_type,pitches\nFF,120\nSL,80\n"
MLBAM_ID = 660271


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr("pawapro_scout.cache.store.CACHE_DIR", tmp_path)
    return CacheStore(season=2025)


@pytest.fixture
def fetcher(tmp_store):
    return SavantSearchFetcher(season=2025, cache=tmp_store)


# ──────────────────────────────────────────────
# _base_params テスト
# ──────────────────────────────────────────────

class TestBaseParams:
    def test_pitcher_lookup_param(self, fetcher):
        params = fetcher._base_params(mlbam_id=MLBAM_ID, is_pitcher=True)
        assert params.get("pitchers_lookup[]") == str(MLBAM_ID)
        assert "batters_lookup[]" not in params

    def test_batter_lookup_param(self, fetcher):
        params = fetcher._base_params(mlbam_id=MLBAM_ID, is_pitcher=False)
        assert params.get("batters_lookup[]") == str(MLBAM_ID)
        assert "pitchers_lookup[]" not in params

    def test_season_param(self, fetcher):
        params = fetcher._base_params(mlbam_id=MLBAM_ID, is_pitcher=True)
        assert params["hfSea"] == "2025|"

    def test_regular_season_param(self, fetcher):
        params = fetcher._base_params(mlbam_id=MLBAM_ID, is_pitcher=True)
        assert params["hfGT"] == "R|"


# ──────────────────────────────────────────────
# 投手メソッドのテスト
# ──────────────────────────────────────────────

class TestPitcherMethods:
    def test_get_pitcher_pitch_type_group_by(self, fetcher, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_pitcher_pitch_type(mlbam_id=MLBAM_ID)
        assert "group_by=name-pitcher%2Cpitch_type" in requests_mock.last_request.url \
            or "group_by=name-pitcher,pitch_type" in requests_mock.last_request.url

    def test_get_pitcher_pitch_type_cache_key(self, fetcher, tmp_store, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_pitcher_pitch_type(mlbam_id=MLBAM_ID)
        expected_key = f"players/{MLBAM_ID}/savant__pitch_type"
        assert tmp_store.exists(expected_key)

    def test_get_pitcher_zone_group_by(self, fetcher, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_pitcher_zone(mlbam_id=MLBAM_ID)
        assert "name-pitcher%2Czone" in requests_mock.last_request.url \
            or "name-pitcher,zone" in requests_mock.last_request.url

    def test_get_pitcher_inning_hfinn_param(self, fetcher, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_pitcher_inning(mlbam_id=MLBAM_ID, innings="1|")
        assert "hfInn=1%7C" in requests_mock.last_request.url \
            or "hfInn=1|" in requests_mock.last_request.url

    def test_get_pitcher_inning_cache_key_contains_label(self, fetcher, tmp_store, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_pitcher_inning(mlbam_id=MLBAM_ID, innings="1|")
        # "1|" → label "1" が含まれるキー
        expected_key = f"players/{MLBAM_ID}/savant__inning_1"
        assert tmp_store.exists(expected_key)

    def test_get_pitcher_inning_multi_innings_cache_key(self, fetcher, tmp_store, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_pitcher_inning(mlbam_id=MLBAM_ID, innings="7|8|9|")
        expected_key = f"players/{MLBAM_ID}/savant__inning_7_8_9"
        assert tmp_store.exists(expected_key)

    def test_get_pitcher_high_pitch_count_hfpitn_param(self, fetcher, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_pitcher_high_pitch_count(mlbam_id=MLBAM_ID, min_pitch=100)
        assert "hfPitN=100%7C" in requests_mock.last_request.url \
            or "hfPitN=100|" in requests_mock.last_request.url


# ──────────────────────────────────────────────
# 野手メソッドのテスト
# ──────────────────────────────────────────────

class TestBatterMethods:
    def test_get_batter_two_strike_hfc_param(self, fetcher, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_batter_two_strike(mlbam_id=MLBAM_ID)
        # TWO_STRIKE_COUNTS = "02|12|22|32" が URL に含まれる
        url = requests_mock.last_request.url
        assert "hfC=" in url
        # 少なくとも "02" が含まれているか確認
        assert "02" in url

    def test_get_batter_two_strike_cache_key(self, fetcher, tmp_store, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_batter_two_strike(mlbam_id=MLBAM_ID)
        expected_key = f"players/{MLBAM_ID}/savant__batter_2strike"
        assert tmp_store.exists(expected_key)

    def test_get_batter_count_hfc_param(self, fetcher, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_batter_count(mlbam_id=MLBAM_ID, counts="00|")
        assert "hfC=00%7C" in requests_mock.last_request.url \
            or "hfC=00|" in requests_mock.last_request.url

    def test_get_batter_count_cache_key_contains_label(self, fetcher, tmp_store, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_batter_count(mlbam_id=MLBAM_ID, counts="00|10|20|30|")
        expected_key = f"players/{MLBAM_ID}/savant__batter_count_00_10_20_30"
        assert tmp_store.exists(expected_key)

    def test_get_batter_pitch_type_lookup_param(self, fetcher, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_batter_pitch_type(mlbam_id=MLBAM_ID)
        assert str(MLBAM_ID) in requests_mock.last_request.url

    def test_get_batter_pitch_type_cache_key(self, fetcher, tmp_store, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_batter_pitch_type(mlbam_id=MLBAM_ID)
        expected_key = f"players/{MLBAM_ID}/savant__batter_pitch_type"
        assert tmp_store.exists(expected_key)


# ──────────────────────────────────────────────
# キャッシュ動作テスト
# ──────────────────────────────────────────────

class TestCaching:
    def test_second_call_does_not_re_request(self, fetcher, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_pitcher_pitch_type(mlbam_id=MLBAM_ID)
        fetcher.get_pitcher_pitch_type(mlbam_id=MLBAM_ID)
        assert requests_mock.call_count == 1

    def test_different_players_different_cache_keys(self, fetcher, tmp_store, requests_mock):
        requests_mock.get(SAVANT_STATCAST_CSV_URL, text=CSV_TEXT)
        fetcher.get_pitcher_pitch_type(mlbam_id=660271)
        fetcher.get_pitcher_pitch_type(mlbam_id=592450)
        assert tmp_store.exists("players/660271/savant__pitch_type")
        assert tmp_store.exists("players/592450/savant__pitch_type")
        assert requests_mock.call_count == 2
