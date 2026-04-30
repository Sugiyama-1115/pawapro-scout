"""
tests/test_config.py
config.py の定数・ユーティリティ関数のテスト。
"""

import pytest
from pawapro_scout.config import (
    score_to_grade,
    percentile_to_grade,
    MEET_BREAKPOINTS,
    POWER_BREAKPOINTS,
    SPEED_BREAKPOINTS,
    CONTROL_BREAKPOINTS,
    TRAJECTORY_BREAKPOINTS,
    GRADES,
)


class TestScoreToGrade:
    """score_to_grade の境界値テスト"""

    def test_s_rank_at_boundary(self):
        # ミート: xBA=0.310, Whiff=15% → スコア = 0.310*300 + (100-15) = 93+85 = 178
        # MEET_BREAKPOINTS の最高値 (S境界) で S になること
        assert score_to_grade(MEET_BREAKPOINTS[0], MEET_BREAKPOINTS) == "S"

    def test_a_rank(self):
        # S境界未満, A境界以上
        val = MEET_BREAKPOINTS[1]  # A境界ちょうど
        assert score_to_grade(val, MEET_BREAKPOINTS) == "A"

    def test_g_rank_below_all(self):
        # 全閾値を下回る → G
        assert score_to_grade(0.0, MEET_BREAKPOINTS) == "G"

    def test_each_grade_boundary(self):
        # 各閾値ちょうどで対応するグレードになること
        for threshold, expected_grade in zip(MEET_BREAKPOINTS, GRADES):
            assert score_to_grade(threshold, MEET_BREAKPOINTS) == expected_grade

    def test_power_s_rank(self):
        # パワー: max EV >= 118 mph → S
        assert score_to_grade(118.0, POWER_BREAKPOINTS) == "S"
        assert score_to_grade(120.0, POWER_BREAKPOINTS) == "S"

    def test_power_g_rank(self):
        # パワー: max EV < 90 mph → G
        assert score_to_grade(89.9, POWER_BREAKPOINTS) == "G"

    def test_speed_s_rank(self):
        # 走力: Sprint Speed >= 30.0 → S
        assert score_to_grade(30.0, SPEED_BREAKPOINTS) == "S"
        assert score_to_grade(31.5, SPEED_BREAKPOINTS) == "S"

    def test_speed_c_rank_mlb_average(self):
        # 走力: MLB平均 27.0 ft/sec → C
        assert score_to_grade(27.0, SPEED_BREAKPOINTS) == "C"


class TestPercentileToGrade:
    """percentile_to_grade のテスト"""

    def test_99th_is_s(self):
        assert percentile_to_grade(99) == "S"

    def test_90th_is_a(self):
        assert percentile_to_grade(90) == "A"

    def test_50th_is_c(self):
        assert percentile_to_grade(50) == "C"

    def test_0th_is_g(self):
        assert percentile_to_grade(0) == "G"

    def test_custom_breakpoints(self):
        # キャッチャー用カスタム閾値
        assert percentile_to_grade(95, [99, 90, 75, 50, 35, 20, 5]) == "A"
        assert percentile_to_grade(75, [99, 90, 75, 50, 35, 20, 5]) == "B"


class TestControlGrade:
    """コントロール (BB%) 閾値の方向性テスト"""

    def test_control_breakpoints_are_ascending(self):
        # BB% の閾値は昇順（低いBB%ほど良い → 逆変換が必要）
        for i in range(len(CONTROL_BREAKPOINTS) - 1):
            assert CONTROL_BREAKPOINTS[i] < CONTROL_BREAKPOINTS[i + 1]

    def test_trajectory_breakpoints_are_descending(self):
        # 弾道の閾値は降順
        for i in range(len(TRAJECTORY_BREAKPOINTS) - 1):
            assert TRAJECTORY_BREAKPOINTS[i] > TRAJECTORY_BREAKPOINTS[i + 1]
