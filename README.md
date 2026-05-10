# pawapro-scout

メジャーリーガーの指標を Baseball Savant などで取得し、パワプロの能力査定を実施するプロジェクト。

## セットアップ

```bash
# 依存パッケージのインストール
uv sync

# または Python 3.13+ を使用
pip install -e .
```

## 使用方法

### CLI

```bash
# 基本的な実行
pawapro-scout --season 2025

# 特定の選手を指定
pawapro-scout --season 2025 --player "大谷翔平"

# MLBAM ID で指定
pawapro-scout --season 2025 --player 660271

# キャッシュを無視して再取得
pawapro-scout --season 2025 --force-refresh

# 出力先を指定
pawapro-scout --season 2025 --output-dir ./my_output
```

**主な引数:**
- `--season` (必須) - シーズン年（例：2025）
- `--player` - 選手名または MLBAM ID で絞り込み（指定しない場合は全員）
- `--force-refresh` - キャッシュを無視して最新データを取得
- `--input` - 入力 CSV ファイルのパス（デフォルト：`input/players.csv`）
- `--output-dir` - 出力ディレクトリ（デフォルト：`output/`）

### 入力ファイル

`input/players.csv` の形式:

```csv
season,team,name_jp,mlbam_id,position,role
2025,LAD,大谷翔平,660271,DH,both
2025,NYY,Aaron Judge,592450,RF,batter
2025,HOU,Justin Verlander,434378,P,pitcher
```

- `season` - シーズン年
- `team` - チーム名（任意）
- `name_jp` - 選手の日本語名
- `mlbam_id` - MLB Statcast ID
- `position` - ポジション（参考用）
- `role` - `batter` / `pitcher` / `both`

### 出力ファイル

```
output/
├── 2025/
│   ├── rating/
│   │   ├── 大谷翔平.txt          # グレード・特殊能力
│   │   └── Aaron Judge.txt
│   └── raw/
│       ├── 大谷翔平.xlsx         # 統計データ（検証用）
│       └── Aaron Judge.xlsx
```

- **rating/*.txt** - グレード + 特殊能力（人間可読形式）
- **raw/*.xlsx** - 取得した全統計データ（多シート Excel）

### プログラマティックな使用

```python
from pawapro_scout.pipeline import Pipeline
from pawapro_scout.models import PlayerInput

# Pipeline の初期化
pipeline = Pipeline(season=2025, output_dir="./output")

# 選手の能力査定を実行
player = PlayerInput(
    season=2025,
    team="LAD",
    name_jp="大谷翔平",
    mlbam_id=660271,
    role="both"
)

result = pipeline.run(player)
```

## テスト実行

```bash
# 全テストを実行
pytest

# 特定のテストファイルを実行
pytest tests/test_assess_batter.py

# 詳細出力
pytest -v

# カバレッジを表示
pytest --cov=src/pawapro_scout
```

## 処理フロー

```
players.csv
    ↓
fetch/  (Baseball Savant, FanGraphs, Pybaseball から取得)
    ↓
aggregate/  (複数ソースのデータを統合)
    ↓
assess/  (パワプロ能力値 + 特殊能力を算定)
    ↓
output/  (TXT・XLSX ファイルを生成)
```

## データソース

- **Baseball Savant** - Statcast データ、ピッチャーのアーセナル
- **FanGraphs** - 高度な分析指標（K%, BB%, WPA など）
- **Pybaseball** - 期待値、パーセンタイル、スプリントスピード
- **Baseball Reference** - レガシーデータ補完

## キャッシュ

取得データは `cache/{season}/` に parquet 形式で自動保存されます。
`--force-refresh` オプションで再取得できます。

## トラブルシューティング

**外部 API の接続エラーが出た場合**
- インターネット接続を確認
- `--force-refresh` で再度実行
- API サイトの状態を確認（Baseball Savant, FanGraphs）

**キャッシュが古い場合**
```bash
pawapro-scout --season 2025 --force-refresh
```

**特定の選手の処理に失敗した場合**
- MLBAM ID を確認
- ログメッセージで詳細なエラーを確認
