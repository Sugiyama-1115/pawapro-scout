"""
tests/test_cache_store.py
CacheStore の読み書き・get_or_fetch・force_refresh テスト。
一時ディレクトリを使うため本番 cache/ に影響しない。
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import MagicMock, patch

from pawapro_scout.cache.store import CacheStore


@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    """一時ディレクトリを使う CacheStore を返す"""
    monkeypatch.setattr("pawapro_scout.cache.store.CACHE_DIR", tmp_path)
    return CacheStore(season=2025)


@pytest.fixture
def sample_df():
    return pd.DataFrame({"player_id": [660271, 592450], "sprint_speed": [30.5, 27.1]})


class TestCacheStoreBasics:
    def test_initial_no_cache(self, tmp_store):
        assert not tmp_store.exists("league/sprint_speed")

    def test_set_and_get(self, tmp_store, sample_df):
        tmp_store.set("league/sprint_speed", sample_df)
        result = tmp_store.get("league/sprint_speed")
        assert result is not None
        assert list(result.columns) == ["player_id", "sprint_speed"]
        assert len(result) == 2

    def test_get_nonexistent_returns_none(self, tmp_store):
        assert tmp_store.get("league/nonexistent") is None

    def test_exists_after_set(self, tmp_store, sample_df):
        tmp_store.set("league/sprint_speed", sample_df)
        assert tmp_store.exists("league/sprint_speed")

    def test_invalidate(self, tmp_store, sample_df):
        tmp_store.set("league/sprint_speed", sample_df)
        tmp_store.invalidate("league/sprint_speed")
        assert not tmp_store.exists("league/sprint_speed")

    def test_invalidate_nonexistent_is_safe(self, tmp_store):
        # 存在しないキーを invalidate してもエラーにならない
        tmp_store.invalidate("league/nonexistent")

    def test_nested_key_creates_dirs(self, tmp_store, sample_df):
        tmp_store.set("players/660271/statcast_batter", sample_df)
        assert tmp_store.exists("players/660271/statcast_batter")


class TestGetOrFetch:
    def test_calls_fetch_fn_when_no_cache(self, tmp_store, sample_df):
        fetch_fn = MagicMock(return_value=sample_df)
        result = tmp_store.get_or_fetch("league/sprint_speed", fetch_fn)
        fetch_fn.assert_called_once()
        assert len(result) == 2

    def test_uses_cache_when_exists(self, tmp_store, sample_df):
        # 先にキャッシュを作る
        tmp_store.set("league/sprint_speed", sample_df)
        fetch_fn = MagicMock(return_value=sample_df)
        result = tmp_store.get_or_fetch("league/sprint_speed", fetch_fn)
        fetch_fn.assert_not_called()   # キャッシュ hit → fetch_fn は呼ばれない
        assert len(result) == 2

    def test_force_refresh_ignores_cache(self, tmp_path, monkeypatch, sample_df):
        monkeypatch.setattr("pawapro_scout.cache.store.CACHE_DIR", tmp_path)
        store = CacheStore(season=2025, force_refresh=True)
        # キャッシュを作っておく
        store.set("league/sprint_speed", sample_df)
        new_df = pd.DataFrame({"player_id": [999], "sprint_speed": [25.0]})
        fetch_fn = MagicMock(return_value=new_df)
        result = store.get_or_fetch("league/sprint_speed", fetch_fn)
        fetch_fn.assert_called_once()   # force_refresh → fetch_fn が呼ばれる
        assert result["player_id"].iloc[0] == 999

    def test_fetch_fn_result_is_cached(self, tmp_store, sample_df):
        fetch_fn = MagicMock(return_value=sample_df)
        tmp_store.get_or_fetch("league/sprint_speed", fetch_fn)
        # 2回目はキャッシュを使う
        tmp_store.get_or_fetch("league/sprint_speed", fetch_fn)
        assert fetch_fn.call_count == 1


class TestPlayerKey:
    def test_player_key_format(self, tmp_store):
        key = tmp_store.player_key(660271, "statcast_batter")
        assert key == "players/660271/statcast_batter"

    def test_player_key_different_players(self, tmp_store):
        k1 = tmp_store.player_key(660271, "statcast_batter")
        k2 = tmp_store.player_key(592450, "statcast_batter")
        assert k1 != k2
