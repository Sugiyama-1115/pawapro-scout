# Phase 2 テスト計画

## 基本方針

fetch/ 層は **全て外部APIに依存** するため、本番APIを叩かずに以下の手法でテストする。

- `unittest.mock.patch` / `pytest-mock` で pybaseball 関数・requests をモック
- 実レスポンスの代わりに **スタブ DataFrame** を使う
- キャッシュ動作は Phase 1 の `test_cache_store.py` で検証済みのため、
  ここでは「fetch_fn が正しい引数で呼ばれているか」と
  「結果が正しくキャッシュキーで保存されるか」に集中する

---

## test_fetch_base.py

### テスト対象: `BaseFetcher`

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_get_csv_calls_session` | `_get_csv` が `session.get()` を正しいURLで呼ぶ | `session.get` が1回呼ばれ、URL/params が一致 |
| `test_get_csv_parses_csv` | レスポンステキストが DataFrame に変換される | 列名・行数が一致 |
| `test_get_csv_raises_on_http_error` | 4xx/5xx で例外が上がる | `requests.HTTPError` が raise される |
| `test_post_json_sends_payload` | `_post_json` が JSON を POST する | `session.post` が1回呼ばれ、payload が一致 |
| `test_retry_on_connection_error` | 接続エラー時にリトライする | `session.get` が `RETRY_MAX_ATTEMPTS` 回呼ばれ最終的に例外 |
| `test_cached_fetch_delegates_to_store` | `_cached_fetch` が `CacheStore.get_or_fetch` に委譲する | `store.get_or_fetch` が正しい key と fetch_fn で呼ばれる |

---

## test_fetch_pybaseball.py

### テスト対象: `PybaseballFetcher`

#### 共通パターン
各メソッドについて以下の2点を確認:
1. **キャッシュ miss 時** → pybaseball の対応関数が正しい引数で1回呼ばれる
2. **キャッシュ hit 時** → pybaseball の対応関数は呼ばれない

#### league-wide メソッド

| テスト名 | pybaseball 関数 | キャッシュキー | OK の条件 |
|---|---|---|---|
| `test_get_batter_expected_stats` | `statcast_batter_expected_stats(2025)` | `league/pybaseball__batter_expected_stats` | 関数が `season=2025` で呼ばれる |
| `test_get_pitcher_expected_stats` | `statcast_pitcher_expected_stats(2025)` | `league/pybaseball__pitcher_expected_stats` | 同上 |
| `test_get_batter_percentile_ranks` | `statcast_batter_percentile_ranks(2025)` | `league/pybaseball__batter_percentile_ranks` | 同上 |
| `test_get_pitcher_percentile_ranks` | `statcast_pitcher_percentile_ranks(2025)` | `league/pybaseball__pitcher_percentile_ranks` | 同上 |
| `test_get_sprint_speed` | `statcast_sprint_speed(year=2025)` | `league/pybaseball__sprint_speed` | `year=2025` で呼ばれる |
| `test_get_outs_above_average` | `statcast_outs_above_average(year=2025, pos="all")` | `league/pybaseball__outs_above_average` | `pos="all"` が渡される |
| `test_get_catcher_poptime` | `statcast_catcher_poptime(year=2025)` | `league/pybaseball__catcher_poptime` | 同上 |
| `test_get_pitcher_active_spin` | `statcast_pitcher_active_spin(year=2025)` | `league/pybaseball__pitcher_active_spin` | 同上 |
| `test_get_batting_stats_fg` | `batting_stats(2025, qual=1)` | `league/pybaseball__batting_stats_fg` | `qual=1` が渡される |
| `test_get_pitching_stats_fg` | `pitching_stats(2025, qual=1)` | `league/pybaseball__pitching_stats_fg` | 同上 |
| `test_get_batting_stats_bref` | `batting_stats_bref(2025)` | `league/pybaseball__batting_stats_bref` | bref sleep が呼ばれる |
| `test_get_pitching_stats_bref` | `pitching_stats_bref(2025)` | `league/pybaseball__pitching_stats_bref` | 同上 |

#### player-specific メソッド

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_get_statcast_batter` | `statcast_batter(start, end, player_id=660271)` が呼ばれる | キャッシュキーが `players/660271/statcast_batter` |
| `test_get_statcast_pitcher` | `statcast_pitcher(start, end, player_id=660271)` が呼ばれる | キャッシュキーが `players/660271/statcast_pitcher` |
| `test_date_range_format` | `_start_dt` / `_end_dt` が正しい書式 | `"2025-03-01"` / `"2025-11-30"` |

#### resolve_ids

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_resolve_ids_returns_dict` | 返り値に `key_mlbam`, `key_fangraphs`, `key_bbref` が含まれる | dict のキーが揃っている |
| `test_resolve_ids_cached_in_memory` | 同じ mlbam_id を2回呼んでも `playerid_reverse_lookup` は1回しか呼ばれない | mock の call_count == 1 |
| `test_resolve_ids_empty_result` | lookup が空 DataFrame を返したとき None が入る | `key_fangraphs is None` |

---

## test_fetch_savant_leaderboard.py

### テスト対象: `SavantLeaderboardFetcher`

#### 共通テスト (全7メソッド共通パターン)

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_url_construction_<slug>` | GET URL が `SAVANT_LEADERBOARD_BASE/<slug>` になる | url が一致 |
| `test_params_include_year_and_csv` | `year=2025&csv=true` がクエリに含まれる | params に `year` と `csv` が存在 |
| `test_result_is_dataframe` | 返り値が DataFrame である | `isinstance(result, pd.DataFrame)` |
| `test_cache_key_<slug>` | キャッシュキーが `league/savant__<slug_key>` になる | `store.set` の第1引数が一致 |

#### 固有テスト

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_fetch_all_returns_7_keys` | `fetch_all()` が7キーの dict を返す | `len(result) == 7` |
| `test_fetch_all_skip_on_error` | 1エンドポイントが失敗しても他は返る | 失敗キーは空 DataFrame、他は正常 |

---

## test_fetch_savant_search.py

### テスト対象: `SavantSearchFetcher`

#### 共通テスト

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_base_params_pitcher` | `pitchers_lookup[]` が mlbam_id になる | params に `pitchers_lookup[]` = `"660271"` |
| `test_base_params_batter` | `batters_lookup[]` が mlbam_id になる | params に `batters_lookup[]` = `"660271"` |
| `test_base_params_season` | `hfSea` が `"2025|"` になる | params の `hfSea` が一致 |
| `test_base_params_regular_season` | `hfGT` が `"R|"` (レギュラーシーズン) になる | params の `hfGT` が `"R|"` |

#### 投手メソッド

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_get_pitcher_pitch_type_cache_key` | キャッシュキーが `players/660271/savant__pitch_type` | `store.get_or_fetch` の引数一致 |
| `test_get_pitcher_zone_group_by` | `group_by=name-pitcher,zone` がパラメータに含まれる | params の `group_by` が一致 |
| `test_get_pitcher_inning_hfinn_param` | `hfInn="1|"` のとき params に反映される | params の `hfInn` が `"1|"` |
| `test_get_pitcher_inning_cache_key` | inning ラベルがキャッシュキーに含まれる | key に `"1"` が含まれる |

#### 野手メソッド

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_get_batter_two_strike_hfc_param` | `hfC` が2ストライクカウント文字列になる | params の `hfC` が `TWO_STRIKE_COUNTS` と一致 |
| `test_get_batter_count_hfc_param` | 指定カウントが `hfC` に渡される | params の `hfC` が引数と一致 |
| `test_get_batter_count_cache_key` | カウントラベルがキャッシュキーに含まれる | key に count ラベルが含まれる |

---

## test_fetch_fangraphs_splits.py

### テスト対象: `FangraphsSplitsFetcher`

#### payload 構築テスト

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_payload_pitcher` | `strPosition="P"`, `strType="1"` | payload のキーが一致 |
| `test_payload_batter` | `strPosition="B"`, `strType="0"` | payload のキーが一致 |
| `test_payload_player_id` | `strPlayerId` が fg_player_id の文字列 | `"12345"` になっている |
| `test_payload_split_arr` | `strSplitArr` が単一IDのリスト | `[5]` (vs_lhp の場合) |
| `test_payload_date_range` | `strStartDate` / `strEndDate` が正しい | `"2025-03-01"` / `"2025-11-30"` |

#### APIレスポンス解析テスト

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_response_dict_with_data_key` | `{"data": [...]}` 形式を正しく解析 | DataFrame の行数が一致 |
| `test_response_list_directly` | レスポンスが直接リストの場合も動作する | DataFrame に変換される |
| `test_response_empty` | `{"data": []}` のとき空 DataFrame を返す | `df.empty == True` |

#### get_all_splits テスト

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_get_all_splits_returns_5_keys` | 5種のキーが返る | `set(result.keys()) == {"vs_lhp", "vs_rhp", "risp", "bases_empty", "high_lev"}` |
| `test_get_all_splits_calls_correct_split_ids` | 各スプリットで正しい split_id が POST される | FG_SPLIT_IDS の値と一致 |
| `test_get_all_splits_skip_on_error` | 1スプリットが失敗しても他は返る | 失敗キーは空 DataFrame |

#### キャッシュキーテスト

| テスト名 | 検証内容 | OK の条件 |
|---|---|---|
| `test_cache_key_format` | `players/<mlbam_id>/fangraphs__splits__<name>` の形式 | key が一致 |
| `test_different_splits_have_different_keys` | vs_lhp と vs_rhp で別のキーになる | key が異なる |

---

## テストを実装する際の注意点

### モックの書き方

```python
# pybaseball 関数のモック例
@patch("pawapro_scout.fetch.pybaseball_fetcher.pybaseball.statcast_sprint_speed")
def test_get_sprint_speed(mock_fn, tmp_store):
    mock_fn.return_value = pd.DataFrame({"player_id": [1], "sprint_speed": [30.0]})
    fetcher = PybaseballFetcher(season=2025, cache=tmp_store)
    result = fetcher.get_sprint_speed()
    mock_fn.assert_called_once_with(year=2025)
    assert len(result) == 1
```

```python
# requests.Session のモック例 (SavantLeaderboard等)
def test_get_catcher_framing(tmp_store, requests_mock):
    url = "https://baseballsavant.mlb.com/leaderboard/catcher-framing"
    requests_mock.get(url, text="player_id,framing_runs\n660271,12.5\n")
    fetcher = SavantLeaderboardFetcher(season=2025, cache=tmp_store)
    result = fetcher.get_catcher_framing()
    assert result["player_id"].iloc[0] == 660271
```

### 使用するモックライブラリ
- `unittest.mock.patch` (標準)
- `pytest-mock` (`mocker` フィクスチャ)
- `requests-mock` (HTTP モック) → `pip install requests-mock` が必要

### 実APIを叩くテスト (integration テスト)
- `tests/integration/` に分離して `@pytest.mark.integration` マークをつける
- CI では skip、手動確認時のみ実行: `pytest -m integration`
- 実行時は実際に 2025年 大谷翔平 (660271) のデータが返ることを確認する
