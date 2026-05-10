"""
tests/test_assess_batter.py
野手査定層 (assess/batter/) のユニットテスト
"""
import pytest

from pawapro_scout.models import BatterStats
from pawapro_scout.assess.batter.basic import (
    assess_basic,
    _assess_trajectory,
    _assess_meet,
    _assess_power,
    _assess_speed,
    _assess_arm,
    _assess_fielding,
    _assess_catch,
)
from pawapro_scout.assess.batter.rank_abilities import assess_rank_abilities
from pawapro_scout.assess.batter.gold_special import assess_gold_special
from pawapro_scout.assess.batter.blue_special import assess_blue_special
from pawapro_scout.assess.batter.red_special import assess_red_special


def make_stats(**kwargs) -> BatterStats:
    """どの特殊能力も発動しない中立なデフォルト値で BatterStats を生成する。"""
    defaults = dict(
        avg_launch_angle=10.0,
        sweet_spot_percent=25.0,
        xba=0.240,
        whiff_percent=22.0,
        max_exit_velocity=105.0,
        sprint_speed=27.0,
        arm_strength_mph=83.0,
        pop_time=2.00,
        oaa_percentile=50,
        fielding_run_value=0.0,
        k_percent=20.0,
        bb_percent=8.0,
        sb=3,
        cs=1,
        games=100,
        risp_avg=0.260,
        season_avg=0.260,
        vs_lhp_woba=0.330,
        vs_rhp_woba=0.330,
        barrel_percent=5.0,
        barrel_percentile=80,
        xba_percentile=80,
        pull_hr_pct=0.50,
        oppo_hr_count=3,
        multi_hit_game_count=5,   # 固め打ち閾値8未満 → 中立
        bolts=5,
    )
    defaults.update(kwargs)
    return BatterStats(**defaults)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 弾道
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestBasicTrajectory:
    def test_grade_1_very_low_angle(self):
        """打球角度 < 5 → 弾道1"""
        s = make_stats(avg_launch_angle=4.0, sweet_spot_percent=0.0)
        assert _assess_trajectory(s) == 1

    def test_grade_2_low_angle(self):
        """5 <= 打球角度 < 12.1 → 弾道2"""
        s = make_stats(avg_launch_angle=8.0, sweet_spot_percent=0.0)
        assert _assess_trajectory(s) == 2

    def test_grade_3_medium_angle(self):
        """12.1 <= 打球角度 <= 18.1 → 弾道3"""
        s = make_stats(avg_launch_angle=15.0, sweet_spot_percent=0.0)
        assert _assess_trajectory(s) == 3

    def test_grade_4_high_angle(self):
        """打球角度 > 18.1 → 弾道4"""
        s = make_stats(avg_launch_angle=20.0, sweet_spot_percent=0.0)
        assert _assess_trajectory(s) == 4

    def test_sweet_spot_upgrades_grade1_to_3(self):
        """sweet_spot_percent >= 35 なら弾道1でも最低3になる"""
        s = make_stats(avg_launch_angle=2.0, sweet_spot_percent=36.0)
        assert _assess_trajectory(s) == 3

    def test_sweet_spot_upgrades_grade2_to_3(self):
        """sweet_spot_percent >= 35 なら弾道2でも3になる"""
        s = make_stats(avg_launch_angle=8.0, sweet_spot_percent=35.0)
        assert _assess_trajectory(s) == 3

    def test_sweet_spot_does_not_downgrade_4(self):
        """sweet_spot_percent があっても弾道4は4のまま"""
        s = make_stats(avg_launch_angle=20.0, sweet_spot_percent=36.0)
        assert _assess_trajectory(s) == 4

    def test_boundary_at_18_1_is_grade3(self):
        """18.1 は弾道3（> 18.1 が条件）"""
        s = make_stats(avg_launch_angle=18.1, sweet_spot_percent=0.0)
        assert _assess_trajectory(s) == 3

    def test_boundary_above_18_1_is_grade4(self):
        """18.2 は弾道4"""
        s = make_stats(avg_launch_angle=18.2, sweet_spot_percent=0.0)
        assert _assess_trajectory(s) == 4


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ミート
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestBasicMeet:
    def test_s_rank_high_score(self):
        """xBA=0.350 → S（S 範囲内）"""
        s = make_stats(xba=0.350)
        assert _assess_meet(s) == "S"

    def test_s_rank_at_boundary(self):
        """xBA=0.300 → S（S 境界値）"""
        s = make_stats(xba=0.300)
        assert _assess_meet(s) == "S"

    def test_a_rank(self):
        """xBA=0.280 → A（A の下限）"""
        s = make_stats(xba=0.280)
        assert _assess_meet(s) == "A"

    def test_g_rank_low_score(self):
        """xBA=0.180 → G（最低グレード）"""
        s = make_stats(xba=0.180)
        assert _assess_meet(s) == "G"

    def test_j_soto_equivalent(self):
        """J・ソト相当: xBA=0.288 → A グレード"""
        s = make_stats(xba=0.288)
        assert _assess_meet(s) == "A"

    def test_xba_boundary_260_is_b_rank(self):
        """xBA=0.260 は B グレード下限"""
        s = make_stats(xba=0.260)
        assert _assess_meet(s) == "B"

    def test_xba_boundary_180_is_g_rank(self):
        """xBA=0.180 は G グレード"""
        s = make_stats(xba=0.180)
        assert _assess_meet(s) == "G"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# パワー
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestBasicPower:
    def test_s_rank(self):
        s = make_stats(max_exit_velocity=119.0)
        assert _assess_power(s) == "S"

    def test_s_rank_at_boundary(self):
        s = make_stats(max_exit_velocity=118.0)
        assert _assess_power(s) == "S"

    def test_a_rank(self):
        s = make_stats(max_exit_velocity=113.0)
        assert _assess_power(s) == "A"

    def test_c_rank(self):
        s = make_stats(max_exit_velocity=105.0)
        assert _assess_power(s) == "C"

    def test_g_rank(self):
        s = make_stats(max_exit_velocity=80.0)
        assert _assess_power(s) == "G"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 走力
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestBasicSpeed:
    def test_s_rank(self):
        s = make_stats(sprint_speed=30.5)
        assert _assess_speed(s) == "S"

    def test_s_rank_at_boundary(self):
        s = make_stats(sprint_speed=30.0)
        assert _assess_speed(s) == "S"

    def test_b_rank(self):
        s = make_stats(sprint_speed=28.5)
        assert _assess_speed(s) == "B"

    def test_c_rank(self):
        s = make_stats(sprint_speed=27.0)
        assert _assess_speed(s) == "C"

    def test_g_rank(self):
        s = make_stats(sprint_speed=22.0)
        assert _assess_speed(s) == "G"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 肩力
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestBasicArm:
    def test_of_strong(self):
        s = make_stats(arm_strength_mph=100.0)
        assert _assess_arm(s, "OF") == "S"

    def test_of_cf_position(self):
        s = make_stats(arm_strength_mph=60.0)
        assert _assess_arm(s, "CF") == "G"

    def test_if_strong(self):
        s = make_stats(arm_strength_mph=95.0)
        assert _assess_arm(s, "SS") == "S"

    def test_if_b_rank(self):
        """ARM_IF_BREAKPOINTS: 83 <= arm < 88 → B"""
        s = make_stats(arm_strength_mph=84.0)
        assert _assess_arm(s, "3B") == "B"

    def test_if_c_rank(self):
        """ARM_IF_BREAKPOINTS: 78 <= arm < 83 → C"""
        s = make_stats(arm_strength_mph=80.0)
        assert _assess_arm(s, "3B") == "C"

    def test_none_arm_of_returns_c(self):
        s = make_stats()
        s.arm_strength_mph = None
        assert _assess_arm(s, "OF") == "C"

    def test_none_arm_if_returns_c(self):
        s = make_stats()
        s.arm_strength_mph = None
        assert _assess_arm(s, "SS") == "C"

    def test_catcher_s_rank(self):
        """pop_time <= 1.85 → S"""
        s = make_stats()
        s.pop_time = 1.80
        assert _assess_arm(s, "C") == "S"

    def test_catcher_a_rank(self):
        """1.85 < pop_time <= 1.90 → A"""
        s = make_stats()
        s.pop_time = 1.88
        assert _assess_arm(s, "C") == "A"

    def test_catcher_g_rank(self):
        """pop_time > 2.20 → G"""
        s = make_stats()
        s.pop_time = 2.30
        assert _assess_arm(s, "C") == "G"

    def test_catcher_none_poptime_returns_c(self):
        s = make_stats()
        s.pop_time = None
        assert _assess_arm(s, "C") == "C"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 守備力・捕球
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestBasicFieldingAndCatch:
    def test_fielding_s_rank(self):
        s = make_stats(oaa_percentile=99)
        assert _assess_fielding(s) == "S"

    def test_fielding_c_rank(self):
        s = make_stats(oaa_percentile=50)
        assert _assess_fielding(s) == "C"

    def test_fielding_g_rank(self):
        s = make_stats(oaa_percentile=3)
        assert _assess_fielding(s) == "G"

    def test_catch_s_rank(self):
        s = make_stats(fielding_run_value=12.0)
        assert _assess_catch(s) == "S"

    def test_catch_a_rank(self):
        s = make_stats(fielding_run_value=6.0)
        assert _assess_catch(s) == "A"

    def test_catch_c_rank(self):
        s = make_stats(fielding_run_value=-1.0)
        assert _assess_catch(s) == "C"

    def test_catch_g_rank(self):
        s = make_stats(fielding_run_value=-20.0)
        assert _assess_catch(s) == "G"

    def test_assess_basic_returns_batter_basic(self):
        from pawapro_scout.models import BatterBasic
        s = make_stats()
        result = assess_basic(s, "OF")
        assert isinstance(result, BatterBasic)
        assert result.弾道 in [1, 2, 3, 4]
        assert result.ミート in ["S", "A", "B", "C", "D", "E", "F", "G"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ランク制能力
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestRankAbilities:
    def test_returns_all_seven_keys(self):
        s = make_stats()
        result = assess_rank_abilities(s, "OF")
        assert set(result.keys()) == {
            "ケガしにくさ", "走塁", "盗塁", "チャンス", "対左投手", "送球", "キャッチャー"
        }

    def test_catcher_is_none_for_non_catcher(self):
        s = make_stats()
        assert assess_rank_abilities(s, "LF")["キャッチャー"] is None

    def test_catcher_not_none_for_catcher(self):
        s = make_stats()
        s.framing_runs = 5.0
        assert assess_rank_abilities(s, "C")["キャッチャー"] is not None

    def test_durability_gold_at_162(self):
        s = make_stats(games=162)
        assert assess_rank_abilities(s, "OF")["ケガしにくさ"] == "金"

    def test_durability_s_rank(self):
        s = make_stats(games=156)
        assert assess_rank_abilities(s, "OF")["ケガしにくさ"] == "S"

    def test_durability_g_rank(self):
        s = make_stats(games=30)
        assert assess_rank_abilities(s, "OF")["ケガしにくさ"] == "G"

    # ── 盗塁 ──
    def test_steal_gold(self):
        # sb=40, cs=4 → total=44, rate=40/44=91% >= 90%, sb >= 40 → 金
        s = make_stats(sb=40, cs=4)
        assert assess_rank_abilities(s, "OF")["盗塁"] == "金"

    def test_steal_a_rank(self):
        # sb=20, cs=3 → rate=87% >= 85%, sb >= 20 → A
        s = make_stats(sb=20, cs=3)
        assert assess_rank_abilities(s, "OF")["盗塁"] == "A"

    def test_steal_g_rank(self):
        s = make_stats(sb=0, cs=1)
        assert assess_rank_abilities(s, "OF")["盗塁"] == "G"

    # ── チャンス ──
    def test_chance_gold(self):
        # diff = +0.080 → 金
        s = make_stats(risp_avg=0.340, season_avg=0.260)
        assert assess_rank_abilities(s, "OF")["チャンス"] == "金"

    def test_chance_c_rank_neutral(self):
        # diff = 0.0 → C
        s = make_stats(risp_avg=0.260, season_avg=0.260)
        assert assess_rank_abilities(s, "OF")["チャンス"] == "C"

    def test_chance_g_rank(self):
        # diff = -0.070 < -0.060 → G
        s = make_stats(risp_avg=0.190, season_avg=0.260)
        assert assess_rank_abilities(s, "OF")["チャンス"] == "G"

    def test_chance_zero_risp_returns_c(self):
        s = make_stats(risp_avg=0.0, season_avg=0.260)
        assert assess_rank_abilities(s, "OF")["チャンス"] == "C"

    # ── 対左投手 ──
    def test_vs_lhp_gold(self):
        # diff = 0.105 → 金 (BATTER_VS_LHP_GOLD_MIN=0.100, float精度確保)
        s = make_stats(vs_lhp_woba=0.435, vs_rhp_woba=0.330)
        assert assess_rank_abilities(s, "OF")["対左投手"] == "金"

    def test_vs_lhp_s_rank(self):
        # diff = 0.077 >= 0.075 → S
        s = make_stats(vs_lhp_woba=0.407, vs_rhp_woba=0.330)
        assert assess_rank_abilities(s, "OF")["対左投手"] == "S"

    def test_vs_lhp_c_rank(self):
        # diff ≈ 0.025 → C (>0.015 かつ <0.030)
        s = make_stats(vs_lhp_woba=0.355, vs_rhp_woba=0.330)
        assert assess_rank_abilities(s, "OF")["対左投手"] == "C"

    def test_vs_lhp_zero_woba_returns_c(self):
        s = make_stats(vs_lhp_woba=0.0, vs_rhp_woba=0.330)
        assert assess_rank_abilities(s, "OF")["対左投手"] == "C"

    # ── 走塁 ──
    def test_baserunning_s_rank(self):
        # BASERUNNING_RV_BREAKPOINTS[0]=8.0 → S
        s = make_stats(baserunning_run_value=8.0)
        assert assess_rank_abilities(s, "OF")["走塁"] == "S"

    def test_baserunning_none_returns_c(self):
        s = make_stats()  # baserunning_run_value=None by default
        assert assess_rank_abilities(s, "OF")["走塁"] == "C"

    # ── 送球 ──
    def test_sending_s_rank(self):
        # ARM_RV_BREAKPOINTS[0]=4.0 → S
        s = make_stats(arm_run_value=4.0)
        assert assess_rank_abilities(s, "OF")["送球"] == "S"

    def test_sending_none_returns_c(self):
        s = make_stats()  # arm_run_value=None by default
        assert assess_rank_abilities(s, "OF")["送球"] == "C"

    # ── キャッチャー ──
    def test_catcher_framing_s_rank(self):
        # framing=8.0, blocking=None → effective=8.0. CATCHER_RANK_BREAKPOINTS[0]=8.0 → S
        s = make_stats()
        s.framing_runs = 8.0
        assert assess_rank_abilities(s, "C")["キャッチャー"] == "S"

    def test_catcher_framing_none_returns_c(self):
        s = make_stats()
        s.framing_runs = None
        assert assess_rank_abilities(s, "C")["キャッチャー"] == "C"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 金特
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestGoldSpecial:
    def test_aachisuto_triggers(self):
        # Barrel% >= 20% AND 平均打球角度 15〜20度
        s = make_stats(barrel_percent=20.0, avg_launch_angle=17.0)
        assert "アーチスト" in assess_gold_special(s)

    def test_aachisuto_barrel_just_below(self):
        # Barrel% = 19.9 → 付与しない
        s = make_stats(barrel_percent=19.9, avg_launch_angle=17.0)
        assert "アーチスト" not in assess_gold_special(s)

    def test_aachisuto_angle_out_of_range(self):
        # 打球角度 14.9 → 付与しない
        s = make_stats(barrel_percent=20.0, avg_launch_angle=14.9)
        assert "アーチスト" not in assess_gold_special(s)

    def test_hit_machine_triggers(self):
        # xBA >= .310 AND Whiff% <= 15%
        s = make_stats(xba=0.310, whiff_percent=15.0)
        assert "安打製造機" in assess_gold_special(s)

    def test_hit_machine_xba_just_below(self):
        # xBA = 0.309 → 付与しない
        s = make_stats(xba=0.309, whiff_percent=15.0)
        assert "安打製造機" not in assess_gold_special(s)

    def test_hit_machine_whiff_too_high(self):
        # Whiff% = 15.1 → 付与しない
        s = make_stats(xba=0.310, whiff_percent=15.1)
        assert "安打製造機" not in assess_gold_special(s)

    def test_no_gold_on_neutral_stats(self):
        s = make_stats()
        assert assess_gold_special(s) == []

    def test_both_gold_simultaneously(self):
        s = make_stats(barrel_percent=20.0, avg_launch_angle=17.0,
                       xba=0.310, whiff_percent=15.0)
        result = assess_gold_special(s)
        assert "アーチスト" in result
        assert "安打製造機" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 青特
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestBlueSpecial:
    def test_katamari_uchi_triggers(self):
        # 1試合3安打以上の試合 >= 8試合
        s = make_stats(multi_hit_game_count=8)
        assert "固め打ち" in assess_blue_special(s)

    def test_katamari_uchi_just_below(self):
        s = make_stats(multi_hit_game_count=7)
        assert "固め打ち" not in assess_blue_special(s)

    def test_pull_hitter_triggers(self):
        # 引っ張り方向HR% >= 80%
        s = make_stats(pull_hr_pct=0.80)
        assert "プルヒッター" in assess_blue_special(s)

    def test_pull_hitter_just_below(self):
        s = make_stats(pull_hr_pct=0.79)
        assert "プルヒッター" not in assess_blue_special(s)

    def test_koukauku_triggers(self):
        s = make_stats(oppo_hr_count=5)
        assert "広角打法" in assess_blue_special(s)

    def test_koukauku_just_below(self):
        s = make_stats(oppo_hr_count=4)
        assert "広角打法" not in assess_blue_special(s)

    def test_headsli_triggers(self):
        # Sprint Speed >= 29.0 AND bolts >= 10
        s = make_stats(sprint_speed=29.0, bolts=10)
        assert "ヘッドスライディング" in assess_blue_special(s)

    def test_headsli_requires_speed(self):
        # sprint_speed < 29.0 → 付与しない
        s = make_stats(sprint_speed=28.9, bolts=10)
        assert "ヘッドスライディング" not in assess_blue_special(s)

    def test_headsli_requires_bolts(self):
        # bolts < 10 → 付与しない
        s = make_stats(sprint_speed=29.0, bolts=9)
        assert "ヘッドスライディング" not in assess_blue_special(s)

    def test_power_hitter_triggers(self):
        # Barrel% >= 12% AND 平均打球角度 12〜18度
        s = make_stats(barrel_percent=12.0, avg_launch_angle=15.0)
        assert "パワーヒッター" in assess_blue_special(s)

    def test_power_hitter_barrel_just_below(self):
        s = make_stats(barrel_percent=11.9, avg_launch_angle=15.0)
        assert "パワーヒッター" not in assess_blue_special(s)

    def test_power_hitter_angle_out_of_range(self):
        s = make_stats(barrel_percent=12.0, avg_launch_angle=11.9)
        assert "パワーヒッター" not in assess_blue_special(s)

    def test_line_drive_triggers(self):
        # 平均打球角度 10〜15度 AND Hard Hit% >= 45%
        s = make_stats(avg_launch_angle=12.0, hard_hit_percent=45.0)
        assert "ラインドライブ" in assess_blue_special(s)

    def test_line_drive_hard_hit_just_below(self):
        s = make_stats(avg_launch_angle=12.0, hard_hit_percent=44.9)
        assert "ラインドライブ" not in assess_blue_special(s)

    def test_avg_hitter_triggers(self):
        # xBA >= .280 AND Whiff% <= 20%
        s = make_stats(xba=0.280, whiff_percent=20.0)
        assert "アベレージヒッター" in assess_blue_special(s)

    def test_avg_hitter_xba_just_below(self):
        s = make_stats(xba=0.279, whiff_percent=20.0)
        assert "アベレージヒッター" not in assess_blue_special(s)

    def test_no_blue_on_neutral_stats(self):
        """デフォルト中立値ではいかなる青特も付与されない"""
        s = make_stats()
        assert assess_blue_special(s) == []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 赤特
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestRedSpecial:
    def test_sansen_at_lower_boundary(self):
        """K% = 27.0 → 三振"""
        s = make_stats(k_percent=27.0)
        assert "三振" in assess_red_special(s)

    def test_sansen_just_below_furikun(self):
        """K% = 32.9 → 三振（扇風機ではない）"""
        s = make_stats(k_percent=32.9)
        result = assess_red_special(s)
        assert "三振" in result
        assert "扇風機" not in result

    def test_furikun_at_boundary(self):
        """K% = 33.0 → 扇風機（三振ではない）"""
        s = make_stats(k_percent=33.0)
        result = assess_red_special(s)
        assert "扇風機" in result
        assert "三振" not in result

    def test_furikun_high_k(self):
        s = make_stats(k_percent=40.0)
        result = assess_red_special(s)
        assert "扇風機" in result
        assert "三振" not in result

    def test_no_k_red_below_threshold(self):
        s = make_stats(k_percent=26.9)
        result = assess_red_special(s)
        assert "三振" not in result
        assert "扇風機" not in result

    # ── エラー ──
    def test_error_triggers(self):
        """Fielding Run Value (Error) <= -5 → エラー"""
        s = make_stats(error_run_value=-5.0)
        assert "エラー" in assess_red_special(s)

    def test_error_just_above(self):
        s = make_stats(error_run_value=-4.9)
        assert "エラー" not in assess_red_special(s)

    def test_error_none_skipped(self):
        s = make_stats()  # error_run_value=None by default
        assert "エラー" not in assess_red_special(s)

    # ── 併殺 ──
    def test_heisatsu_triggers(self):
        """Sprint Speed <= 26.0 AND GIDP >= 15 → 併殺"""
        s = make_stats(sprint_speed=26.0, gdp=15)
        assert "併殺" in assess_red_special(s)

    def test_heisatsu_requires_low_speed(self):
        """Sprint Speed > 26.0 → 付与しない"""
        s = make_stats(sprint_speed=26.1, gdp=15)
        assert "併殺" not in assess_red_special(s)

    def test_heisatsu_requires_gdp(self):
        """GIDP < 15 → 付与しない"""
        s = make_stats(sprint_speed=26.0, gdp=14)
        assert "併殺" not in assess_red_special(s)

    # ── ムード✕ ──
    def test_mood_batsu_triggers(self):
        """WPA <= -3.0 → ムード✕"""
        s = make_stats(wpa=-3.0)
        assert "ムード✕" in assess_red_special(s)

    def test_mood_batsu_just_above(self):
        s = make_stats(wpa=-2.9)
        assert "ムード✕" not in assess_red_special(s)

    def test_no_red_on_neutral_stats(self):
        """デフォルト中立値ではいかなる赤特も付与されない"""
        s = make_stats()
        assert assess_red_special(s) == []

    def test_furikun_and_heisatsu_coexist(self):
        """扇風機と併殺は同時に付与できる"""
        s = make_stats(k_percent=35.0, sprint_speed=25.0, gdp=20)
        result = assess_red_special(s)
        assert "扇風機" in result
        assert "併殺" in result
