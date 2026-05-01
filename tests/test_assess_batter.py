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
        xbt_percent=33.0,
        risp_avg=0.260,
        season_avg=0.260,
        vs_lhp_woba=0.330,
        vs_rhp_woba=0.330,
        barrel_percentile=80,
        xba_percentile=80,
        pull_hr_pct=0.50,
        oppo_hr_count=3,
        multi_hit_game_count=10,
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
        s = make_stats(xba=1.0, whiff_percent=0.0)
        assert _assess_meet(s) == "S"

    def test_s_rank_at_boundary(self):
        """score >= 303 → S. xBA=0.8, whiff=0 -> 340"""
        s = make_stats(xba=0.8, whiff_percent=0.0)
        assert _assess_meet(s) == "S"

    def test_a_rank(self):
        """score 287~302 → A. xBA=0.7, whiff=20 -> 290"""
        s = make_stats(xba=0.7, whiff_percent=20.0)
        assert _assess_meet(s) == "A"

    def test_g_rank_low_score(self):
        """xBA=0.1, whiff=80 -> 50 → G"""
        s = make_stats(xba=0.1, whiff_percent=80.0)
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
            "ケガしにくさ", "走塁", "盗塁", "対左投手", "対変化球", "送球", "キャッチャー"
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

    def test_steal_gold_at_50(self):
        s = make_stats(sb=50)
        assert assess_rank_abilities(s, "OF")["盗塁"] == "金"

    def test_steal_s_rank(self):
        s = make_stats(sb=36)
        assert assess_rank_abilities(s, "OF")["盗塁"] == "S"

    def test_steal_g_rank(self):
        s = make_stats(sb=0)
        assert assess_rank_abilities(s, "OF")["盗塁"] == "G"

    def test_vs_lhp_gold(self):
        s = make_stats(vs_lhp_woba=0.420, vs_rhp_woba=0.330)
        assert assess_rank_abilities(s, "OF")["対左投手"] == "金"

    def test_vs_lhp_s_rank(self):
        """diff = 0.070 -> S"""
        s = make_stats(vs_lhp_woba=0.400, vs_rhp_woba=0.330)
        assert assess_rank_abilities(s, "OF")["対左投手"] == "S"

    def test_vs_lhp_c_rank(self):
        s = make_stats(vs_lhp_woba=0.330, vs_rhp_woba=0.330)
        assert assess_rank_abilities(s, "OF")["対左投手"] == "C"

    def test_vs_lhp_zero_woba_returns_c(self):
        s = make_stats(vs_lhp_woba=0.0, vs_rhp_woba=0.330)
        assert assess_rank_abilities(s, "OF")["対左投手"] == "C"

    def test_vs_breaking_low_k_s_rank(self):
        s = make_stats(k_percent=7.0)
        assert assess_rank_abilities(s, "OF")["対変化球"] == "S"

    def test_vs_breaking_mid_k_c_rank(self):
        """VS_BREAKING_BREAKPOINTS[3]=20.0 → k<=20 はC。k=20.0 → C"""
        s = make_stats(k_percent=20.0)
        assert assess_rank_abilities(s, "OF")["対変化球"] == "C"

    def test_vs_breaking_mid_k_d_rank(self):
        """20 < k <= 24 → D。k=22.0 → D"""
        s = make_stats(k_percent=22.0)
        assert assess_rank_abilities(s, "OF")["対変化球"] == "D"

    def test_vs_breaking_high_k_g_rank(self):
        s = make_stats(k_percent=35.0)
        assert assess_rank_abilities(s, "OF")["対変化球"] == "G"

    def test_catcher_framing_s_rank(self):
        s = make_stats()
        s.framing_runs = 12.0
        assert assess_rank_abilities(s, "C")["キャッチャー"] == "S"

    def test_catcher_framing_none_returns_c(self):
        s = make_stats()
        s.framing_runs = None
        assert assess_rank_abilities(s, "C")["キャッチャー"] == "C"

    def test_baserunning_s_rank(self):
        s = make_stats(xbt_percent=56.0)
        assert assess_rank_abilities(s, "OF")["走塁"] == "S"

    def test_sending_of_position(self):
        s = make_stats(arm_strength_mph=100.0)
        assert assess_rank_abilities(s, "CF")["送球"] == "S"

    def test_sending_none_returns_c(self):
        s = make_stats()
        s.arm_strength_mph = None
        assert assess_rank_abilities(s, "OF")["送球"] == "C"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 金特
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestGoldSpecial:
    def test_aachisuto_at_99(self):
        s = make_stats(barrel_percentile=99)
        assert "アーチスト" in assess_gold_special(s)

    def test_aachisuto_below_99(self):
        s = make_stats(barrel_percentile=98)
        assert "アーチスト" not in assess_gold_special(s)

    def test_hit_machine_at_99(self):
        s = make_stats(xba_percentile=99)
        assert "安打製造機" in assess_gold_special(s)

    def test_hit_machine_below_99(self):
        s = make_stats(xba_percentile=98)
        assert "安打製造機" not in assess_gold_special(s)

    def test_no_gold_on_neutral_stats(self):
        s = make_stats()
        assert assess_gold_special(s) == []

    def test_both_gold_simultaneously(self):
        s = make_stats(barrel_percentile=99, xba_percentile=99)
        result = assess_gold_special(s)
        assert "アーチスト" in result
        assert "安打製造機" in result


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 青特
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestBlueSpecial:
    def test_chance_maru_triggers(self):
        s = make_stats(risp_avg=0.320, season_avg=0.260)
        assert "チャンス◯" in assess_blue_special(s)

    def test_chance_maru_just_below_threshold(self):
        s = make_stats(risp_avg=0.309, season_avg=0.260)
        assert "チャンス◯" not in assess_blue_special(s)

    def test_chance_maru_zero_avg_skipped(self):
        s = make_stats(risp_avg=0.0, season_avg=0.260)
        assert "チャンス◯" not in assess_blue_special(s)

    def test_vs_lhp_maru_triggers(self):
        s = make_stats(vs_lhp_woba=0.380, vs_rhp_woba=0.330)
        assert "対左投手◯" in assess_blue_special(s)

    def test_vs_lhp_maru_just_below_threshold(self):
        s = make_stats(vs_lhp_woba=0.369, vs_rhp_woba=0.330)
        assert "対左投手◯" not in assess_blue_special(s)

    def test_vs_lhp_maru_zero_skipped(self):
        s = make_stats(vs_lhp_woba=0.0, vs_rhp_woba=0.330)
        assert "対左投手◯" not in assess_blue_special(s)

    def test_pull_hitter_triggers(self):
        s = make_stats(pull_hr_pct=0.65)
        assert "プルヒッター" in assess_blue_special(s)

    def test_pull_hitter_just_below(self):
        s = make_stats(pull_hr_pct=0.59)
        assert "プルヒッター" not in assess_blue_special(s)

    def test_koukauku_triggers(self):
        s = make_stats(oppo_hr_count=5)
        assert "広角打法" in assess_blue_special(s)

    def test_koukauku_just_below(self):
        s = make_stats(oppo_hr_count=4)
        assert "広角打法" not in assess_blue_special(s)

    def test_katamari_uchi_triggers(self):
        s = make_stats(multi_hit_game_count=15)
        assert "固め打ち" in assess_blue_special(s)

    def test_katamari_uchi_just_below(self):
        s = make_stats(multi_hit_game_count=14)
        assert "固め打ち" not in assess_blue_special(s)

    def test_infield_hit_maru_triggers(self):
        s = make_stats(bolts=10)
        assert "内野安打◯" in assess_blue_special(s)

    def test_infield_hit_maru_just_below(self):
        s = make_stats(bolts=9)
        assert "内野安打◯" not in assess_blue_special(s)

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

    def test_chance_batsu_triggers(self):
        s = make_stats(risp_avg=0.190, season_avg=0.260)
        assert "チャンス×" in assess_red_special(s)

    def test_chance_batsu_at_exact_threshold(self):
        """差がちょうど -0.060 → チャンス×"""
        s = make_stats(risp_avg=0.200, season_avg=0.260)
        assert "チャンス×" in assess_red_special(s)

    def test_chance_batsu_just_above_threshold(self):
        """差が -0.059 → 付与しない"""
        s = make_stats(risp_avg=0.201, season_avg=0.260)
        assert "チャンス×" not in assess_red_special(s)

    def test_chance_batsu_zero_avg_skipped(self):
        s = make_stats(risp_avg=0.0, season_avg=0.260)
        assert "チャンス×" not in assess_red_special(s)

    def test_no_red_on_neutral_stats(self):
        """デフォルト中立値ではいかなる赤特も付与されない"""
        s = make_stats()
        assert assess_red_special(s) == []

    def test_furikun_and_chance_batsu_coexist(self):
        """扇風機とチャンス×は同時に付与できる"""
        s = make_stats(k_percent=35.0, risp_avg=0.190, season_avg=0.260)
        result = assess_red_special(s)
        assert "扇風機" in result
        assert "チャンス×" in result
