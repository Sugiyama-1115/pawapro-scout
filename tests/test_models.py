"""
tests/test_models.py
models.py の dataclass 生成・デフォルト値テスト。
"""

import pytest
from pawapro_scout.models import (
    PlayerInput,
    BatterStats,
    PitcherStats,
    PitchAggregated,
    PitchEntry,
    BatterBasic,
    PitcherBasic,
    BatterRating,
    PitcherRating,
    PlayerRecord,
)


class TestPlayerInput:
    def test_minimal_creation(self):
        p = PlayerInput(season=2025, team="LAD", name_jp="大谷翔平")
        assert p.season == 2025
        assert p.team == "LAD"
        assert p.name_jp == "大谷翔平"
        assert p.mlbam_id == 0       # 未解決のデフォルト
        assert p.name_en_last == ""
        assert p.name_en_first == ""

    def test_full_creation(self):
        p = PlayerInput(
            season=2025,
            team="LAD",
            name_jp="大谷翔平",
            name_en_last="Ohtani",
            name_en_first="Shohei",
            mlbam_id=660271,
        )
        assert p.mlbam_id == 660271
        assert p.name_en_last == "Ohtani"

    def test_unresolved_player_has_zero_id(self):
        p = PlayerInput(season=2025, team="NYY", name_jp="アーロン・ジャッジ")
        assert p.mlbam_id == 0


class TestBatterStats:
    def test_default_values(self):
        s = BatterStats()
        assert s.avg_launch_angle == 0.0
        assert s.xba == 0.0
        assert s.sprint_speed == 0.0
        assert s.oaa_percentile == 50   # デフォルトは平均
        assert s.arm_strength_mph is None
        assert s.pop_time is None

    def test_custom_values(self):
        s = BatterStats(
            avg_launch_angle=18.5,
            xba=0.315,
            whiff_percent=14.0,
            max_exit_velocity=119.2,
            sprint_speed=30.5,
        )
        assert s.avg_launch_angle == 18.5
        assert s.xba == 0.315


class TestPitcherStats:
    def test_default_values(self):
        s = PitcherStats()
        assert s.max_velocity_mph == 0.0
        assert s.pitches == []
        assert s.k_percent == 0.0
        assert s.exit_vel_percentile == 50

    def test_with_pitches(self):
        pitch = PitchAggregated(
            pitch_type="FF",
            usage_pct=55.0,
            velocity_avg=97.5,
            whiff_pct=22.0,
            horizontal_break=8.0,
            induced_vertical_break=16.0,
            delta_v_from_fastball=0.0,
            rv_per_100=-1.5,
        )
        s = PitcherStats(pitches=[pitch])
        assert len(s.pitches) == 1
        assert s.pitches[0].pitch_type == "FF"


class TestPitchAggregated:
    def test_creation(self):
        p = PitchAggregated(
            pitch_type="SL",
            usage_pct=25.0,
            velocity_avg=86.0,
            whiff_pct=38.0,
            horizontal_break=-4.5,
            induced_vertical_break=3.0,
            delta_v_from_fastball=12.0,
            rv_per_100=-2.8,
        )
        assert p.pitch_type == "SL"
        assert p.whiff_pct == 38.0
        # 符号保持の確認
        assert p.horizontal_break < 0


class TestRatingModels:
    def test_batter_rating(self):
        basic = BatterBasic(
            弾道=4,
            ミート="S",
            パワー="S",
            走力="A",
            肩力="B",
            守備力="C",
            捕球="B",
        )
        rating = BatterRating(
            basic=basic,
            rank_abilities={"ケガしにくさ": "金", "走塁": "A"},
            gold_special=["安打製造機", "アーチスト"],
            blue_special=["初球◯"],
            red_special=[],
        )
        assert rating.basic.弾道 == 4
        assert rating.basic.ミート == "S"
        assert "安打製造機" in rating.gold_special
        assert rating.red_special == []

    def test_pitcher_rating(self):
        basic = PitcherBasic(球速=165, コントロール="B", スタミナ="E")
        rating = PitcherRating(
            basic=basic,
            pitches=[PitchEntry(名称="ストレート", 変化量=5)],
            rank_abilities={"ノビ": "金"},
            gold_special=["ドクターK"],
            blue_special=["キレ◯"],
            red_special=[],
        )
        assert rating.basic.球速 == 165
        assert rating.pitches[0].名称 == "ストレート"

    def test_player_record_batter_only(self):
        basic = BatterBasic(弾道=3, ミート="B", パワー="C", 走力="C", 肩力="C", 守備力="C", 捕球="C")
        batter_rating = BatterRating(
            basic=basic,
            rank_abilities={},
            gold_special=[],
            blue_special=[],
            red_special=[],
        )
        record = PlayerRecord(
            player="テスト選手",
            season=2025,
            type="batter",
            batter=batter_rating,
        )
        assert record.type == "batter"
        assert record.pitcher is None

    def test_player_record_both(self):
        record = PlayerRecord(
            player="大谷翔平",
            season=2025,
            type="both",
        )
        assert record.type == "both"
        assert record.batter is None   # まだ未設定
        assert record.pitcher is None
