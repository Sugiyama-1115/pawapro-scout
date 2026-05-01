"""
cli.py
コマンドラインインターフェース定義。
"""

from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

from rich.console import Console

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

console = Console()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pawapro-scout",
        description="MLB選手の指標を取得してパワプロ能力を自動査定します",
    )
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="参照シーズン (例: 2025)",
    )
    parser.add_argument(
        "--player",
        type=str,
        default=None,
        help="選手名の部分一致 (name_jp) または MLBAM ID (省略時は全選手)",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="キャッシュを無視してデータを再取得する",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("input/players.csv"),
        help="players.csv のパス (デフォルト: input/players.csv)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="出力先ディレクトリ (デフォルト: output/)",
    )
    return parser


def load_players(csv_path: Path, player_filter: str | None):
    """
    players.csv を読み込み、mlbam_id が解決済みの行のみ返す。
    player_filter が指定された場合は name_jp の部分一致でフィルタする。
    """
    import pandas as pd
    from pawapro_scout.models import PlayerInput

    if not csv_path.exists():
        console.print(f"[red]エラー: {csv_path} が見つかりません[/red]")
        sys.exit(1)

    df = pd.read_csv(csv_path, dtype={"mlbam_id": "Int64"})

    # 未解決の選手を警告
    unresolved = df[df["mlbam_id"].isna()]
    if not unresolved.empty:
        console.print(
            f"[yellow]警告: {len(unresolved)} 件の選手で mlbam_id が未解決です。"
            " /resolve-players を実行してください。[/yellow]"
        )
        df = df[df["mlbam_id"].notna()]

    if player_filter:
        # 数値なら MLBAM ID 直接指定
        if player_filter.isdigit():
            df = df[df["mlbam_id"] == int(player_filter)]
        else:
            df = df[df["name_jp"].str.contains(player_filter, na=False)]

        if df.empty:
            console.print(f"[red]エラー: '{player_filter}' に一致する選手が見つかりません[/red]")
            sys.exit(1)

    players = [
        PlayerInput(
            season=int(row["season"]),
            team=str(row["team"]),
            name_jp=str(row["name_jp"]),
            name_en_last=str(row.get("name_en_last", "")),
            name_en_first=str(row.get("name_en_first", "")),
            mlbam_id=int(row["mlbam_id"]),
            position=str(row.get("position", "OF") or "OF"),
            role=str(row.get("role", "batter") or "batter"),
        )
        for _, row in df.iterrows()
    ]
    return players


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    console.print(
        f"[bold cyan]pawapro-scout[/bold cyan] season={args.season}"
        + (f" player={args.player}" if args.player else "")
    )

    players = load_players(args.input, args.player)
    if not players:
        console.print("[yellow]処理対象の選手がいません。players.csv を確認してください。[/yellow]")
        sys.exit(0)

    console.print(f"対象選手: {len(players)} 名")

    from pawapro_scout.pipeline import Pipeline

    pipeline = Pipeline(
        season=args.season,
        output_dir=args.output_dir,
        force_refresh=args.force_refresh,
    )

    errors: list[str] = []
    for player in players:
        try:
            pipeline.run(player)
        except Exception as e:
            console.print(f"[red]✗ {player.name_jp} 失敗: {e}[/red]")
            errors.append(player.name_jp)
            logger.exception(f"{player.name_jp} 処理中にエラー")

    if errors:
        console.print(f"\n[red]失敗した選手: {', '.join(errors)}[/red]")
        sys.exit(1)
    else:
        console.print("\n[bold green]全選手の処理が完了しました ✓[/bold green]")
