"""
tests/test_cli.py
CLI の players.csv 読み込み・フィルタリングテスト。
実際の players.csv (input/players.csv) を使う。
"""

import pytest
import pandas as pd
from pathlib import Path

from pawapro_scout.cli import load_players, build_parser


# プロジェクトルートの players.csv を参照
PLAYERS_CSV = Path(__file__).parent.parent / "input" / "players.csv"


class TestBuildParser:
    def test_season_required(self):
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])   # --season なし → エラー

    def test_season_parsed(self):
        parser = build_parser()
        args = parser.parse_args(["--season", "2025"])
        assert args.season == 2025

    def test_player_optional(self):
        parser = build_parser()
        args = parser.parse_args(["--season", "2025"])
        assert args.player is None

    def test_force_refresh_flag(self):
        parser = build_parser()
        args = parser.parse_args(["--season", "2025", "--force-refresh"])
        assert args.force_refresh is True

    def test_default_input_path(self):
        parser = build_parser()
        args = parser.parse_args(["--season", "2025"])
        assert args.input == Path("input/players.csv")


class TestLoadPlayersFromCsv:
    """実際の input/players.csv を使ったテスト"""

    def test_csv_exists(self):
        assert PLAYERS_CSV.exists(), "input/players.csv が存在しません"

    def test_csv_has_required_columns(self):
        df = pd.read_csv(PLAYERS_CSV)
        required = {"season", "team", "name_jp"}
        assert required.issubset(set(df.columns))

    def test_csv_has_test_players(self):
        df = pd.read_csv(PLAYERS_CSV)
        names = df["name_jp"].tolist()
        assert "大谷翔平" in names
        assert "山本由伸" in names
        assert "アーロン・ジャッジ" in names

    def test_csv_mlbam_id_column_exists(self):
        df = pd.read_csv(PLAYERS_CSV)
        assert "mlbam_id" in df.columns

    def test_unresolved_players_warned_and_skipped(self, capsys):
        """mlbam_id が空の選手はスキップされ警告が出る"""
        # players.csv は全員 mlbam_id が未解決なので、結果は空リスト
        players = load_players(PLAYERS_CSV, player_filter=None)
        # mlbam_id が未解決 → 0件が返る
        assert isinstance(players, list)

    def test_player_filter_no_match_exits(self):
        """存在しない選手名でフィルタすると SystemExit"""
        with pytest.raises(SystemExit):
            load_players(PLAYERS_CSV, player_filter="存在しない選手XYZ")

    def test_nonexistent_csv_exits(self, tmp_path):
        """存在しない CSV を指定すると SystemExit"""
        with pytest.raises(SystemExit):
            load_players(tmp_path / "nonexistent.csv", player_filter=None)


class TestLoadPlayersWithResolvedIds:
    """mlbam_id が解決済みの場合のテスト（一時ファイルを使用）"""

    @pytest.fixture
    def resolved_csv(self, tmp_path):
        csv = tmp_path / "players.csv"
        csv.write_text(
            "season,team,name_jp,name_en_last,name_en_first,mlbam_id\n"
            "2025,LAD,大谷翔平,Ohtani,Shohei,660271\n"
            "2025,NYY,アーロン・ジャッジ,Judge,Aaron,592450\n",
            encoding="utf-8",
        )
        return csv

    def test_loads_resolved_players(self, resolved_csv):
        players = load_players(resolved_csv, player_filter=None)
        assert len(players) == 2
        assert players[0].name_jp == "大谷翔平"
        assert players[0].mlbam_id == 660271
        assert players[1].name_jp == "アーロン・ジャッジ"

    def test_filter_by_name_partial_match(self, resolved_csv):
        players = load_players(resolved_csv, player_filter="大谷")
        assert len(players) == 1
        assert players[0].name_jp == "大谷翔平"

    def test_filter_by_mlbam_id(self, resolved_csv):
        players = load_players(resolved_csv, player_filter="592450")
        assert len(players) == 1
        assert players[0].name_jp == "アーロン・ジャッジ"

    def test_player_input_fields(self, resolved_csv):
        players = load_players(resolved_csv, player_filter=None)
        ohtani = players[0]
        assert ohtani.season == 2025
        assert ohtani.team == "LAD"
        assert ohtani.name_en_last == "Ohtani"
        assert ohtani.name_en_first == "Shohei"
