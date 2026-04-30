"""
tests/test_fetch_savant_leaderboard.py
SavantLeaderboardFetcher のテスト。requests をモックして
正しいURL・パラメータで呼ばれるか / キャッシュが機能するか を検証する。
"""

import pytest
import pandas as pd

from pawapro_scout.cache.store import CacheStore
from pawapro_scout.config import SAVANT_LEADERBOARD_BASE, SAVANT_LEADERBOARD_SLUGS
from pawapro_scout.fetch.savant_leaderboard import SavantLeaderboardFetcher


# ──────────────────────────────────────────────
# フィクスチャ
# ──────────────────────────────────────────────

CSV_TEXT = "player_id,value\n660271,12.5\n592450,8.3\n"


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr("pawapro_scout.cache.store.CACHE_DIR", tmp_path)
    return CacheStore(season=2025)


@pytest.fixture
def fetcher(tmp_store):
    return SavantLeaderboardFetcher(season=2025, cache=tmp_store)


# ──────────────────────────────────────────────
# 各エンドポイントのパラメータ・URL テスト
# ──────────────────────────────────────────────

class TestUrlConstruction:
    """GET URL が正しく組み立てられているか検証する"""

    @pytest.mark.parametrize("slug_key", list(SAVANT_LEADERBOARD_SLUGS.keys()))
    def test_url_contains_correct_slug(self, slug_key, fetcher, requests_mock):
        slug = SAVANT_LEADERBOARD_SLUGS[slug_key]
        expected_url = f"{SAVANT_LEADERBOARD_BASE}/{slug}"
        requests_mock.get(expected_url, text=CSV_TEXT)

        # メソッドを動的に呼び出す
        method_name = f"get_{slug_key}"
        getattr(fetcher, method_name)()

        assert requests_mock.call_count == 1
        assert requests_mock.last_request.url.startswith(expected_url)

    @pytest.mark.parametrize("slug_key", list(SAVANT_LEADERBOARD_SLUGS.keys()))
    def test_params_include_year(self, slug_key, fetcher, requests_mock):
        slug = SAVANT_LEADERBOARD_SLUGS[slug_key]
        url = f"{SAVANT_LEADERBOARD_BASE}/{slug}"
        requests_mock.get(url, text=CSV_TEXT)

        method_name = f"get_{slug_key}"
        getattr(fetcher, method_name)()

        assert "year=2025" in requests_mock.last_request.url

    @pytest.mark.parametrize("slug_key", list(SAVANT_LEADERBOARD_SLUGS.keys()))
    def test_params_include_csv_true(self, slug_key, fetcher, requests_mock):
        slug = SAVANT_LEADERBOARD_SLUGS[slug_key]
        url = f"{SAVANT_LEADERBOARD_BASE}/{slug}"
        requests_mock.get(url, text=CSV_TEXT)

        method_name = f"get_{slug_key}"
        getattr(fetcher, method_name)()

        assert "csv=true" in requests_mock.last_request.url


# ──────────────────────────────────────────────
# 返り値テスト
# ──────────────────────────────────────────────

class TestReturnTypes:
    def test_get_catcher_framing_returns_dataframe(self, fetcher, requests_mock):
        url = f"{SAVANT_LEADERBOARD_BASE}/catcher-framing"
        requests_mock.get(url, text=CSV_TEXT)
        result = fetcher.get_catcher_framing()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_get_catcher_blocking_returns_dataframe(self, fetcher, requests_mock):
        url = f"{SAVANT_LEADERBOARD_BASE}/catcher-blocking"
        requests_mock.get(url, text=CSV_TEXT)
        result = fetcher.get_catcher_blocking()
        assert isinstance(result, pd.DataFrame)

    def test_get_outfielder_throws_returns_dataframe(self, fetcher, requests_mock):
        url = f"{SAVANT_LEADERBOARD_BASE}/outfielder-throws"
        requests_mock.get(url, text=CSV_TEXT)
        result = fetcher.get_outfielder_throws()
        assert isinstance(result, pd.DataFrame)


# ──────────────────────────────────────────────
# キャッシュキーテスト
# ──────────────────────────────────────────────

class TestCacheKeys:
    @pytest.mark.parametrize("slug_key", list(SAVANT_LEADERBOARD_SLUGS.keys()))
    def test_cache_key_format(self, slug_key, fetcher, tmp_store, requests_mock):
        slug = SAVANT_LEADERBOARD_SLUGS[slug_key]
        url = f"{SAVANT_LEADERBOARD_BASE}/{slug}"
        requests_mock.get(url, text=CSV_TEXT)

        method_name = f"get_{slug_key}"
        getattr(fetcher, method_name)()

        expected_key = f"league/savant__{slug_key}"
        assert tmp_store.exists(expected_key)

    def test_cache_hit_does_not_re_request(self, fetcher, requests_mock):
        url = f"{SAVANT_LEADERBOARD_BASE}/catcher-framing"
        requests_mock.get(url, text=CSV_TEXT)

        fetcher.get_catcher_framing()
        fetcher.get_catcher_framing()  # 2回目

        assert requests_mock.call_count == 1  # HTTPリクエストは1回のみ


# ──────────────────────────────────────────────
# fetch_all テスト
# ──────────────────────────────────────────────

class TestFetchAll:
    def test_fetch_all_returns_7_keys(self, fetcher, requests_mock):
        for slug_key, slug in SAVANT_LEADERBOARD_SLUGS.items():
            url = f"{SAVANT_LEADERBOARD_BASE}/{slug}"
            requests_mock.get(url, text=CSV_TEXT)

        result = fetcher.fetch_all()
        assert len(result) == 7
        assert set(result.keys()) == set(SAVANT_LEADERBOARD_SLUGS.keys())

    def test_fetch_all_values_are_dataframes(self, fetcher, requests_mock):
        for slug_key, slug in SAVANT_LEADERBOARD_SLUGS.items():
            url = f"{SAVANT_LEADERBOARD_BASE}/{slug}"
            requests_mock.get(url, text=CSV_TEXT)

        result = fetcher.fetch_all()
        for key, df in result.items():
            assert isinstance(df, pd.DataFrame), f"{key} is not a DataFrame"

    def test_fetch_all_skip_on_error(self, fetcher, requests_mock):
        """1エンドポイントが失敗しても他は正常に返る"""
        for slug_key, slug in SAVANT_LEADERBOARD_SLUGS.items():
            url = f"{SAVANT_LEADERBOARD_BASE}/{slug}"
            if slug_key == "catcher_framing":
                requests_mock.get(url, status_code=500)  # このエンドポイントだけ失敗
            else:
                requests_mock.get(url, text=CSV_TEXT)

        result = fetcher.fetch_all()

        # 失敗したキーは空DataFrame
        assert result["catcher_framing"].empty
        # 他のキーは正常
        for key in SAVANT_LEADERBOARD_SLUGS.keys():
            if key != "catcher_framing":
                assert len(result[key]) == 2, f"{key} should have 2 rows"
