# Claude 動作ルール — pawapro-scout

## プロジェクト概要

**pawapro-scout** は MLB 選手の統計データを複数ソースから取得し、パワプロの能力査定ロジックに基づいて自動的に能力値を算定するツール。

- **目的**: MLB 選手データ → パワプロ 6段階グレード + 特殊能力
- **入力**: `input/players.csv`（シーズン・選手名・MLB_ID など）
- **出力**: 
  - `output/{season}/rating/{player}.txt` - グレード・特殊能力
  - `output/{season}/raw/{player}.xlsx` - 統計データ（検証用）
- **Python**: 3.13+（uv で依存管理）

---

## ディレクトリ構造

```
pawapro-scout/
├── pyproject.toml              # 依存・メタデータ・CLI エントリ定義
├── uv.lock                     # 依存ロック（uv 管理）
├── .python-version             # Python 3.13
├── README.md                   # 概要（日本語）
├── CLAUDE.md                   # 本ファイル
├── input/
│   └── players.csv             # 入力選手リスト
├── output/{season}/
│   ├── rating/{name}.txt       # グレード・特殊能力（最終出力）
│   └── raw/{name}.xlsx         # 統計データ（検証用）
├── cache/{season}/             # parquet キャッシュ
│   └── players/{mlbam_id}/{name}.parquet
├── src/pawapro_scout/
│   ├── __init__.py
│   ├── __main__.py             # python -m エントリ
│   ├── cli.py                  # argparse + main()
│   ├── pipeline.py             # Pipeline.run() オーケストレーション
│   ├── models.py               # 全データクラス
│   ├── config.py               # ブレークポイント・URL・キャッシュ設定
│   ├── fetch/
│   │   ├── base.py             # BaseFetcher（HTTP retry, _cached_fetch）
│   │   ├── pybaseball_fetcher.py
│   │   ├── savant_leaderboard.py
│   │   ├── savant_search.py
│   │   ├── fangraphs_leaderboard.py
│   │   └── fangraphs_splits.py
│   ├── aggregate/
│   │   ├── batter_aggregator.py
│   │   └── pitcher_aggregator.py
│   ├── assess/
│   │   ├── batter/
│   │   │   ├── basic.py / rank_abilities.py
│   │   │   └── blue_special.py / gold_special.py / red_special.py
│   │   └── pitcher/
│   │       ├── basic.py / rank_abilities.py / pitch_classifier.py
│   │       └── blue_special.py / gold_special.py / red_special.py
│   ├── output/
│   │   ├── formatter.py        # TXT 出力
│   │   └── excel_exporter.py   # XLSX 出力
│   └── cache/
│       └── store.py            # CacheStore (parquet)
└── tests/                      # pytest スイート
    ├── test_aggregate_batter.py / test_aggregate_pitcher.py
    ├── test_assess_batter.py / test_assess_pitcher.py
    ├── test_fetch_*.py（5 ファイル）
    ├── test_cache_store.py / test_cli.py / test_config.py / test_models.py
    └── TEST_PLAN_PHASE2.md
```

---

## アーキテクチャ

### 全体フロー

```
players.csv
    ↓
fetch/ (Baseball Savant, FanGraphs, Pybaseball から取得)
    ↓ (キャッシュ: cache/{season}/ に parquet 保存)
    ↓
aggregate/ (複数ソースのデータを 1 つの stats 集約 / ID 統一)
    ↓
assess/ (stats → パワプログレード + 特殊能力判定)
    ↓
output/ ({season}/raw/{name}.xlsx + {season}/rating/{name}.txt)
```

### レイヤー構成

1. **fetch** - 外部 API/スクレイピング層（共通基底: `BaseFetcher`）
2. **aggregate** - データ統合層（mlbam_id, fangraphs_id, BR mlbID の ID 統一）
3. **assess** - ロジック層（グレード・特殊能力算定）
4. **output** - 出力層（Excel, TXT 形式化）
5. **cache** - 全レイヤーの共通キャッシング層

---

## モジュール一覧と役割

### fetch/（データ取得層）

- `src/pawapro_scout/fetch/base.py`
  - `BaseFetcher` - HTTP セッション + tenacity retry + `_cached_fetch()`
- `src/pawapro_scout/fetch/pybaseball_fetcher.py`
  - pybaseball ラッパー。Statcast、期待値、パーセンタイル、sprint speed、OAA
- `src/pawapro_scout/fetch/savant_leaderboard.py`
  - Savant 投手リーダーボード（pitch arsenal RV/100、active spin 等）
- `src/pawapro_scout/fetch/savant_search.py`
  - Statcast Search 集計 API（ゾーン別、カウント別、イニング別 xwOBA）
- `src/pawapro_scout/fetch/fangraphs_leaderboard.py`
  - FanGraphs REST API（K%, BB%, WPA, OPS+, LOB% など）
- `src/pawapro_scout/fetch/fangraphs_splits.py`
  - FanGraphs splits（RISP、vs LHP/RHP、対上位投手）

### aggregate/（データ統合層）

- `src/pawapro_scout/aggregate/batter_aggregator.py`
  - `BatterAggregator` → `BatterStats`（40+ 指標）
  - ID 統一: MLBAM / FanGraphs IDfg / Baseball Reference mlbID
- `src/pawapro_scout/aggregate/pitcher_aggregator.py`
  - `PitcherAggregator` → `PitcherStats` + `pitch_aggregated: list[PitchAggregated]`

### assess/（ロジック層）

打者: `src/pawapro_scout/assess/batter/`
- `basic.py` - 7 基本能力（弾道・ミート・パワー・走力・肩力・守備・捕球）
- `rank_abilities.py` - ランク能力（ケガしにくさ・走塁・盗塁・対左 等）
- `blue_special.py` / `gold_special.py` / `red_special.py` - 特殊能力判定

投手: `src/pawapro_scout/assess/pitcher/`
- `basic.py` - 3 基本能力（球速・コントロール・スタミナ）
- `pitch_classifier.py` - 球種名・ムーブメント等級（1-7）
- `rank_abilities.py` / `blue_special.py` / `gold_special.py` / `red_special.py`

### output/（出力層）

- `src/pawapro_scout/output/formatter.py`
  - TXT 形式化 → `output/{season}/rating/{name}.txt`
- `src/pawapro_scout/output/excel_exporter.py`
  - 多シート XLSX → `output/{season}/raw/{name}.xlsx`

### cache/（キャッシング層）

- `src/pawapro_scout/cache/store.py`
  - `CacheStore` - `cache/{season}/{key}.parquet`
  - メソッド: `get()`, `set()`, `exists()`, `invalidate()`, `get_or_fetch()`
  - プレイヤーキー命名: `players/{mlbam_id}/{name}`

---

## データモデル

すべて `src/pawapro_scout/models.py` に定義

**入力側**
- `PlayerInput` - CSV から読み込み（season, team, name_jp, mlbam_id, position, role）

**集約側**
- `BatterStats` - 打者統計（40+ 指標）
- `PitcherStats` - 投手統計 + `pitch_aggregated: list[PitchAggregated]`
- `PitchAggregated` - 球種別統計（球速・ブレーク・使用率・Run Value）

**評価側**
- `BatterBasic` / `PitcherBasic` - 基本能力（グレード S-G）
- `BatterRating` / `PitcherRating` - 最終査定（基本 + ランク + 特殊能力）

**出力側**
- `PlayerRecord` - 最終出力単位

---

## 入出力と設定

### 入力
- `input/players.csv`
  - カラム: `season, team, name_jp, mlbam_id, position, role`
  - `role` は `batter` / `pitcher` / `both`

### 出力
- `output/{season}/rating/{name_jp}.txt` - グレード + 特殊能力（人間可読）
- `output/{season}/raw/{name_jp}.xlsx` - 多シート Excel（検証用）

### キャッシュ
- `cache/{season}/{key}.parquet`
- 例: `cache/2025/players/660271/Shohei_Ohtani.parquet`

### 設定
- `src/pawapro_scout/config.py`
  - グレード閾値（POWER_BREAKPOINTS, ARM_OF_BREAKPOINTS など）
  - URL 定数、キャッシュ・retry 設定
- `pyproject.toml`
  - 依存: pybaseball, pandas, pyarrow, openpyxl, requests, tenacity, rich
  - dev: pytest, pytest-mock, requests-mock, ruff
  - CLI エントリ: `pawapro-scout` コマンド

---

## エントリーポイント

### CLI
```bash
pawapro-scout --season 2025 --player "選手名" --force-refresh
python -m pawapro_scout --season 2025 --output-dir ./output
```

CLI 引数（`src/pawapro_scout/cli.py`）:
- `--season`（必須） - シーズン年
- `--player` - 名前部分一致 or MLBAM ID で絞り込み
- `--force-refresh` - キャッシュ無視
- `--input` - デフォルト `input/players.csv`
- `--output-dir` - デフォルト `output/`

### プログラマティック
```python
from pawapro_scout.pipeline import Pipeline
from pawapro_scout.models import PlayerInput

pipeline = Pipeline(season=2025, output_dir="./output")
player = PlayerInput(season=2025, team="LAD", name_jp="...", mlbam_id=12345, role="batter")
result = pipeline.run(player)
```

### pipeline.py（`src/pawapro_scout/pipeline.py`）
- `Pipeline.run(player)` - 1 選手の全処理（fetch → aggregate → assess → output）
- league-wide data（期待値、パーセンタイル等）は lazy-load + キャッシュ
- batter は FanGraphs splits 失敗時に Statcast Search にフォールバック
- 個別 fetch 失敗はログ警告のみで継続（pipeline 全体は止まらない）

---

## テスト実行後のレポート形式

`pytest` を実行したあとは、必ず以下の形式でレポートを出力すること。
ターミナルの生ログをそのまま貼るのは禁止。必ず要約・整形して提示する。

---

### レポート構成

#### 1. サマリー

```
## テスト結果サマリー
- 実行ファイル: <対象ファイル or "全テスト">
- 合計: X passed / Y failed / Z error  （所要時間: N秒）
- 判定: ✅ 全パス  /  ❌ 失敗あり
```

#### 2. テスト一覧（クラス・グループ単位でまとめる）

各テストファイル・クラスごとに以下の表を出す。

```
### <ファイル名> — <テスト対象クラス/モジュール>

| テスト名 | 何を検証するか | 結果 |
|---|---|---|
| test_xxx | ○○が△△になることを確認 | ✅ |
| test_yyy | ○○がエラーを raise することを確認 | ❌ |
```

#### 3. 失敗・エラーの詳細（失敗があった場合のみ）

失敗した各テストについて以下を記載する。

```
### ❌ 失敗詳細: <テスト名>

**なぜ失敗したか**
（エラーメッセージの意味を日本語で説明。生ログの貼り付けは不可）

**修正方針**
（何をどう直すか。コード・設定・テスト自体のどこを変えるか）
```

#### 4. 修正後の再実行結果（修正を行った場合）

修正内容を簡潔にまとめ、再実行後のサマリーを同じ形式で出す。

---

### 運用ルール

- テストを実行するたびに必ずこの形式でレポートを出す
- 「全パス」の場合でも一覧表は省略しない
- エラー内容は **平易な日本語** で説明する（英語スタックトレースの丸投げ禁止）
- 修正を行った場合は「何を・なぜ・どう直したか」を必ず記載する

---

## コマンド実行時のルール

ツール実行・コマンド実行などでユーザーに承認を求める前に、必ず以下を **Claude のチャット上で先に説明**すること：

1. **実施内容**: 何をするコマンドか（例：「〇〇フォルダを削除します」）
2. **実現できること**: 実行後にどうなるか・何が目的か（例：「不要なスキルファイルが消え、環境がクリーンになります」）
3. **読み取り専用か変更を伴うか**: 変更・削除・作成を伴う場合は明示する

---

## プロジェクト固有のコーディング規約

### データ変換

- **FanGraphs の K%/BB% 等のパーセント値** は `_pct()` ヘルパー経由で取得する。
  APIによって小数（`0.25`）と%値（`25.0`）が混在するため、`< 2.0` なら ×100 する。
- **`horizontal_break` の符号** は `PitchAggregated` では保持したまま格納し、
  ピッチ分類器内では `abs()` を使って判定する（符号は投手の利き手依存）。
- **`score_to_grade`** は降順ブレークポイント前提。
  「低いほど良い」指標（BB% など）は降順変換せず、専用のロジックを実装する。
- **Optional フィールドの型変換前** に必ず `if v is None: return None` を入れる。
  `float(None)` はクラッシュするため、明示的な None ガードを省略しない。

---

## テスト設計規約

- **クラス変数のキャッシュ汚染防止**: `_id_cache` 等のクラス変数を使うフェッチャーのテストでは、
  テスト開始時に必ず `ClassName._id_cache.clear()` を呼ぶ。
  前のテストの副作用で call_count がずれる原因になる。
- **`make_stats()` のデフォルト値は中立値にする**: フィクスチャのデフォルト値は
  どの特殊能力も発動しない値にする。デフォルト値が閾値を超えていると
  「何も付与されない」テストが意図せず失敗する。
- **グレード境界値は `config.py` の実際の閾値から書く**: 想定値をテストに書かず、
  必ず `config.py` のブレークポイントを参照して期待値を決める。

---

## 外部ライブラリ利用規約

- **pybaseball の関数名は実装前に存在確認する**:
  ドキュメントや計画に記載された関数名でも実際には存在しない場合がある（例: `statcast_pitcher_active_spin`）。
  実装前に `dir(pybaseball)` またはソースで確認する。
- **Baseball Reference へのアクセスは必ず `time.sleep(3)` を挟む**:
  スクレイピング制限への対応として設計済みだが、コードレビュー時にも省略されていないか確認する。
