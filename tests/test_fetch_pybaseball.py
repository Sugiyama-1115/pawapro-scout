"""
tests/test_fetch_pybaseball.py
PybaseballFetcher のテスト。pybaseball 関数をモックして
正しい引数で呼ばれているか / キャッシュキーが正しいか を検証する。
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from pawapro_scout.cache.store import CacheStore
from pawapro_scout.fetch.pybaseball_fetcher import PybaseballFetcher


# ──────────────────────────────────────────────
# フィクスチャ
# ──────────────────────────────────────────────

@pytest.fixture
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr("pawapro_scout.cache.store.CACHE_DIR", tmp_path)
    return CacheStore(season=2025)


@pytest.fixture
def fetcher(tmp_store):
    return PybaseballFetcher(season=2025, cache=tmp_store)


def make_df(**kwargs):
    """スタブ DataFrame を生成するヘルパー"""
    return pd.DataFrame({"player_id": [660271], **kwargs})


# ──────────────────────────────────────────────
# 日付範囲テスト
# ──────────────────────────────────────────────

class TestDateRange:
    def test_start_date_format(self, fetcher):
        assert fetcher._start_dt == "2025-03-01"

    def test_end_date_format(self, fetcher):
        assert fetcher._end_dt == "2025-11-30"

    def test_different_season(self, tmp_store):
        f = PybaseballFetcher(season=2024, cache=tmp_store)
        assert f._start_dt == "2024-03-01"
        assert f._end_dt == "2024-11-30"


# ──────────────────────────────────────────────
# league-wide メソッドのテスト
# (パターン: 正しい引数で呼ばれる / キャッシュ hit で呼ばれない)
# ──────────────────────────────────────────────

class TestLeagueWide:

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_batter_expected_stats")
    def test_get_batter_expected_stats_args(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(xba=[0.300])
        fetcher.get_batter_expected_stats()
        mock_fn.assert_called_once_with(2025)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_batter_expected_stats")
    def test_get_batter_expected_stats_cache(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(xba=[0.300])
        fetcher.get_batter_expected_stats()
        fetcher.get_batter_expected_stats()
        assert mock_fn.call_count == 1  # 2回目はキャッシュ

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_pitcher_expected_stats")
    def test_get_pitcher_expected_stats_args(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(xera=[3.50])
        fetcher.get_pitcher_expected_stats()
        mock_fn.assert_called_once_with(2025)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_batter_percentile_ranks")
    def test_get_batter_percentile_ranks_args(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(xba=[95])
        fetcher.get_batter_percentile_ranks()
        mock_fn.assert_called_once_with(2025)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_pitcher_percentile_ranks")
    def test_get_pitcher_percentile_ranks_args(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(k_percent=[90])
        fetcher.get_pitcher_percentile_ranks()
        mock_fn.assert_called_once_with(2025)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_sprint_speed")
    def test_get_sprint_speed_uses_year_kwarg(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(sprint_speed=[30.5])
        fetcher.get_sprint_speed()
        mock_fn.assert_called_once_with(year=2025)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_outs_above_average")
    def test_get_outs_above_average_pos_all(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(outs_above_average=[5])
        fetcher.get_outs_above_average()
        mock_fn.assert_called_once_with(year=2025, pos="all")

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_catcher_poptime")
    def test_get_catcher_poptime_args(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(pop_time=[1.88])
        fetcher.get_catcher_poptime()
        mock_fn.assert_called_once_with(year=2025)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_pitcher_spin_dir_comp")
    def test_get_pitcher_active_spin_args(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(active_spin=[95.0])
        fetcher.get_pitcher_active_spin()
        mock_fn.assert_called_once_with(year=2025)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.batting_stats")
    def test_get_batting_stats_fg_qual(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(AVG=[0.290])
        fetcher.get_batting_stats_fg()
        mock_fn.assert_called_once_with(2025, qual=1)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.pitching_stats")
    def test_get_pitching_stats_fg_qual(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(ERA=[3.50])
        fetcher.get_pitching_stats_fg()
        mock_fn.assert_called_once_with(2025, qual=1)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.batting_stats_bref")
    def test_get_batting_stats_bref_args(self, mock_fn, fetcher, mocker):
        mock_fn.return_value = make_df(SB=[20])
        mocker.patch("pawapro_scout.fetch.base.time.sleep")  # bref sleep をスキップ
        fetcher.get_batting_stats_bref()
        mock_fn.assert_called_once_with(2025)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.batting_stats_bref")
    def test_get_batting_stats_bref_sleeps(self, mock_fn, fetcher, mocker):
        mock_fn.return_value = make_df(SB=[20])
        mock_sleep = mocker.patch("pawapro_scout.fetch.base.time.sleep")
        fetcher.get_batting_stats_bref()
        mock_sleep.assert_called_once()

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.pitching_stats_bref")
    def test_get_pitching_stats_bref_args(self, mock_fn, fetcher, mocker):
        mock_fn.return_value = make_df(IP=[180.0])
        mocker.patch("pawapro_scout.fetch.base.time.sleep")
        fetcher.get_pitching_stats_bref()
        mock_fn.assert_called_once_with(2025)


# ──────────────────────────────────────────────
# player-specific メソッドのテスト
# ──────────────────────────────────────────────

class TestPlayerSpecific:

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_batter")
    def test_get_statcast_batter_args(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(launch_speed=[108.0])
        fetcher.get_statcast_batter(mlbam_id=660271)
        mock_fn.assert_called_once_with("2025-03-01", "2025-11-30", player_id=660271)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_batter")
    def test_get_statcast_batter_cache_key(self, mock_fn, fetcher, tmp_store):
        mock_fn.return_value = make_df(launch_speed=[108.0])
        fetcher.get_statcast_batter(mlbam_id=660271)
        expected_key = "players/660271/statcast_batter"
        assert tmp_store.exists(expected_key)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_pitcher")
    def test_get_statcast_pitcher_args(self, mock_fn, fetcher):
        mock_fn.return_value = make_df(release_speed=[97.5])
        fetcher.get_statcast_pitcher(mlbam_id=660271)
        mock_fn.assert_called_once_with("2025-03-01", "2025-11-30", player_id=660271)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_pitcher")
    def test_get_statcast_pitcher_cache_key(self, mock_fn, fetcher, tmp_store):
        mock_fn.return_value = make_df(release_speed=[97.5])
        fetcher.get_statcast_pitcher(mlbam_id=660271)
        expected_key = "players/660271/statcast_pitcher"
        assert tmp_store.exists(expected_key)

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_batter")
    def test_different_players_different_cache_keys(self, mock_fn, fetcher, tmp_store):
        mock_fn.return_value = make_df(launch_speed=[108.0])
        fetcher.get_statcast_batter(mlbam_id=660271)
        fetcher.get_statcast_batter(mlbam_id=592450)
        assert tmp_store.exists("players/660271/statcast_batter")
        assert tmp_store.exists("players/592450/statcast_batter")
        assert mock_fn.call_count == 2


# ──────────────────────────────────────────────
# resolve_ids テスト
# ──────────────────────────────────────────────

class TestResolveIds:

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.playerid_reverse_lookup")
    def test_returns_dict_with_required_keys(self, mock_fn, fetcher):
        mock_fn.return_value = pd.DataFrame({
            "key_mlbam": [660271],
            "key_fangraphs": [19755],
            "key_bbref": ["ohtansh01"],
        })
        result = fetcher.resolve_ids(660271)
        assert "key_mlbam" in result
        assert "key_fangraphs" in result
        assert "key_bbref" in result

    @patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.playerid_reverse_lookup")
    def test_caches_in_memory(self, mock_fn, fetcher):
        PybaseballFetcher._id_cache.clear()  # 他テストの汚染をリセット
        mock_fn.return_value = pd.DataFrame({
            "key_mlbam": [660271],
            "key_fangraphs": [19755],
            "key_bbref": ["ohtansh01"],
        })
        fetcher.resolve_ids(660271)
        fetcher.resolve_ids(660271)  # 2回目
        assert mock_fn.call_count == 1  # 1回しか呼ばれない

    def test_empty_result_sets_none(self, fetcher):
        # モジュール内の _id_cache をリセット
        PybaseballFetcher._id_cache.clear()
        with patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.playerid_reverse_lookup") as mock_lookup:
            mock_lookup.return_value = pd.DataFrame()  # 空
            result = fetcher.resolve_ids(999999)
            assert result["key_fangraphs"] is None
            assert result["key_bbref"] is None
