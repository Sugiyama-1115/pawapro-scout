# /resolve-players

MLB選手の日本語名（カタカナ/漢字）を英語名に変換し、MLBAM ID を解決して `input/players.csv` に書き戻す。

## 手順

1. `input/players.csv` を読み込む
2. `mlbam_id` が空（または 0）の行をリストアップする
3. 各行について、`name_jp` と `team` から英語名（姓・名）を推測して提示する
4. ユーザーに確認を求め、承認・修正を受け取る
5. 確認済みの英語名を使って `pybaseball.playerid_lookup` で MLBAM ID を取得する
6. `players.csv` の対象行に `name_en_last`・`name_en_first`・`mlbam_id` を書き込む
7. 完了後、解決済み選手の一覧を表示する

## 実行イメージ

```
未解決の選手が 3 名見つかりました。

[1/3] 大谷翔平 (LAD)
  → 推測: Shohei Ohtani
  承認しますか？ [Y/n/修正]: Y

[2/3] 山本由伸 (LAD)
  → 推測: Yoshinobu Yamamoto
  承認しますか？ [Y/n/修正]: Y

[3/3] アーロン・ジャッジ (NYY)
  → 推測: Aaron Judge
  承認しますか？ [Y/n/修正]: Y

MLBAM ID を取得中...
  大谷翔平     → 660271
  山本由伸     → 808967
  アーロン・ジャッジ → 592450

players.csv を更新しました。
```

## 注意事項

- `pybaseball.playerid_lookup` で複数ヒットした場合は `team` と `season` でフィルタする
- それでも絞り込めない場合はユーザーに候補を提示して選択してもらう
- ID 取得に失敗した場合は空のまま残し、次回の `/resolve-players` 実行で再試行できるようにする
- すでに `mlbam_id` が入力されている行はスキップする

## MLBAM ID 取得コマンド（参考）

```python
from pybaseball import playerid_lookup
result = playerid_lookup("Ohtani", "Shohei")
mlbam_id = result["key_mlbam"].iloc[0]
```
