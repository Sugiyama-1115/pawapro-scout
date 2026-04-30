"""
tests/test_fetch_base.py
BaseFetcher の HTTP・リトライ・_cached_fetch のテスト。
"""

import io
import pytest
import requests
import pandas as pd
from unittest.mock import MagicMock, patch, call

from pawapro_scout.cache.store import CacheStore
from pawapro_scout.fetch.base import BaseFetcher
from pawapro_scout.config import RETRY_MAX_ATTEMPTS


# ──────────────────────────────────────────────
# フィクスチャ
# ──────────────────────────────────────────────

@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr("pawapro_scout.cache.store.CACHE_DIR", tmp_path)
    return CacheStore(season=2025)


@pytest.fixture
def fetcher(tmp_store):
    return BaseFetcher(cache=tmp_store)


CSV_TEXT = "player_id,sprint_speed\n660271,30.5\n592450,27.1\n"


# ──────────────────────────────────────────────
# _get_csv テスト
# ──────────────────────────────────────────────

class TestGetCsv:
    def test_calls_session_get_with_correct_url(self, fetcher, requests_mock):
        url = "https://example.com/data.csv"
        requests_mock.get(url, text=CSV_TEXT)
        fetcher._get_csv(url)
        assert requests_mock.call_count == 1
        assert requests_mock.last_request.url.startswith(url)

    def test_passes_params_to_request(self, fetcher, requests_mock):
        url = "https://example.com/data.csv"
        requests_mock.get(url, text=CSV_TEXT)
        fetcher._get_csv(url, params={"year": 2025, "csv": "true"})
        assert "year=2025" in requests_mock.last_request.url
        assert "csv=true" in requests_mock.last_request.url

    def test_returns_dataframe(self, fetcher, requests_mock):
        url = "https://example.com/data.csv"
        requests_mock.get(url, text=CSV_TEXT)
        result = fetcher._get_csv(url)
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["player_id", "sprint_speed"]
        assert len(result) == 2

    def test_raises_on_http_error(self, fetcher, requests_mock):
        url = "https://example.com/data.csv"
        requests_mock.get(url, status_code=404)
        with pytest.raises(requests.HTTPError):
            fetcher._get_csv(url)

    def test_raises_on_server_error(self, fetcher, requests_mock):
        url = "https://example.com/data.csv"
        requests_mock.get(url, status_code=500)
        with pytest.raises(requests.HTTPError):
            fetcher._get_csv(url)


# ──────────────────────────────────────────────
# _post_json テスト
# ──────────────────────────────────────────────

class TestPostJson:
    def test_sends_json_payload(self, fetcher, requests_mock):
        url = "https://example.com/api"
        requests_mock.post(url, json={"data": [{"woba": 0.350}]})
        result = fetcher._post_json(url, payload={"strPlayerId": "660271"})
        assert requests_mock.last_request.json() == {"strPlayerId": "660271"}

    def test_returns_parsed_json(self, fetcher, requests_mock):
        url = "https://example.com/api"
        requests_mock.post(url, json={"data": [{"woba": 0.350}]})
        result = fetcher._post_json(url, payload={})
        assert result == {"data": [{"woba": 0.350}]}

    def test_raises_on_http_error(self, fetcher, requests_mock):
        url = "https://example.com/api"
        requests_mock.post(url, status_code=403)
        with pytest.raises(requests.HTTPError):
            fetcher._post_json(url, payload={})


# ──────────────────────────────────────────────
# リトライテスト
# ──────────────────────────────────────────────

class TestRetry:
    def test_retries_on_connection_error(self, fetcher):
        """接続エラー時に RETRY_MAX_ATTEMPTS 回試みて最終的に例外を raise する"""
        call_count = 0

        def failing_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise requests.ConnectionError("接続失敗")

        fetcher.session.get = failing_get

        with pytest.raises(requests.ConnectionError):
            fetcher._get_csv("https://example.com/data.csv")

        assert call_count == RETRY_MAX_ATTEMPTS

    def test_succeeds_after_transient_error(self, fetcher, requests_mock):
        """一時的なエラー後に成功する場合、正常に結果を返す"""
        url = "https://example.com/data.csv"
        # 1回目は 500、2回目は成功
        requests_mock.get(
            url,
            [
                {"status_code": 500},
                {"text": CSV_TEXT, "status_code": 200},
            ],
        )
        result = fetcher._get_csv(url)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2


# ──────────────────────────────────────────────
# _cached_fetch テスト
# ──────────────────────────────────────────────

class TestCachedFetch:
    def test_delegates_to_store_get_or_fetch(self, fetcher, tmp_store):
        """_cached_fetch が CacheStore.get_or_fetch に委譲する"""
        sample_df = pd.DataFrame({"a": [1]})
        fetch_fn = MagicMock(return_value=sample_df)

        result = fetcher._cached_fetch("league/test_key", fetch_fn)

        fetch_fn.assert_called_once()
        assert len(result) == 1

    def test_returns_cached_result_on_second_call(self, fetcher, tmp_store):
        """2回目の呼び出しでは fetch_fn は呼ばれない"""
        sample_df = pd.DataFrame({"a": [1]})
        fetch_fn = MagicMock(return_value=sample_df)

        fetcher._cached_fetch("league/test_key", fetch_fn)
        fetcher._cached_fetch("league/test_key", fetch_fn)

        assert fetch_fn.call_count == 1

    def test_force_refresh_always_calls_fetch_fn(self, tmp_path, monkeypatch):
        """force_refresh=True のとき常に fetch_fn が呼ばれる"""
        monkeypatch.setattr("pawapro_scout.cache.store.CACHE_DIR", tmp_path)
        store = CacheStore(season=2025, force_refresh=True)
        fetcher = BaseFetcher(cache=store)

        sample_df = pd.DataFrame({"a": [1]})
        fetch_fn = MagicMock(return_value=sample_df)

        fetcher._cached_fetch("league/test_key", fetch_fn)
        fetcher._cached_fetch("league/test_key", fetch_fn)

        assert fetch_fn.call_count == 2


# ──────────────────────────────────────────────
# bref スリープテスト
# ──────────────────────────────────────────────

class TestSleepForBref:
    def test_sleep_is_called(self, fetcher, mocker):
        mock_sleep = mocker.patch("pawapro_scout.fetch.base.time.sleep")
        fetcher._sleep_for_bref()
        mock_sleep.assert_called_once()

    def test_sleep_duration(self, fetcher, mocker):
        from pawapro_scout.config import BREF_SLEEP_SEC
        mock_sleep = mocker.patch("pawapro_scout.fetch.base.time.sleep")
        fetcher._sleep_for_bref()
        mock_sleep.assert_called_once_with(BREF_SLEEP_SEC)
