"""
tests/test_assess_pitcher.py
投手査定 (basic / pitch_classifier / rank_abilities / gold / blue / red) のテスト。
外部データ不要 — PitcherStats と PitchAggregated のスタブのみ使用。
"""

import pytest
from dataclasses import replace

from pawapro_scout.assess.pitcher.basic import (
    assess_basic,
    _assess_velocity,
    _assess_control,
    _assess_stamina,
)
from pawapro_scout.assess.pitcher.pitch_classifier import (
    classify_pitches,
    _classify,
    _calc_henka,
)
from pawapro_scout.assess.pitcher.rank_abilities import assess_rank_abilities
from pawapro_scout.assess.pitcher.gold_special import assess_gold_special
from pawapro_scout.assess.pitcher.blue_special import assess_blue_special
from pawapro_scout.assess.pitcher.red_special import assess_red_special
from pawapro_scout.models import PitchAggregated, PitchEntry, PitcherStats


# ──────────────────────────────────────────────
# スタブ生成ヘルパー
# ──────────────────────────────────────────────

def make_stats(**kwargs) -> PitcherStats:
    defaults = dict(
        max_velocity_mph=97.0,
        pitches=[],
        k_percent=26.0,
        bb_percent=7.0,
        k_percentile=85,
        bb_percentile=60,
        avg_pitches_per_game=95.0,
        games=30,
        ip=170.0,
        games_started=28,
        exit_vel_percentile=75,
        hard_hit_percent=35.0,
        extension_percentile=80,
        active_spin_4seam=None,
        lob_percent=72.0,
        hr_per_9=1.0,
        wpa=2.0,
        ir_stranded_pct=None,
        risp_xwoba=0.310,
        season_xwoba=0.320,
        vs_lhp_xwoba=0.300,
        vs_rhp_xwoba=0.330,
        high_lev_xwoba=0.310,
        inning1_xwoba=0.310,
        inning7plus_xwoba=0.300,
        pitch_100plus_rv=0.0,
        low_zone_pct=35.0,
        heart_zone_pct=25.0,
        release_x_stddev=0.3,
        release_z_stddev=0.3,
        pickoffs=2,
        p_oaa=1,
        sb_against=15,
        cs_against=5,
    )
    defaults.update(kwargs)
    return PitcherStats(**defaults)


def make_pitch(pt="FF", usage=50.0, vel=96.0, whiff=25.0, hb=-8.0, ivb=14.0, dv=0.0, rv=-1.0):
    return PitchAggregated(
        pitch_type=pt,
        usage_pct=usage,
        velocity_avg=vel,
        whiff_pct=whiff,
        horizontal_break=hb,
        induced_vertical_break=ivb,
        delta_v_from_fastball=dv,
        rv_per_100=rv,
    )


# ══════════════════════════════════════════════
# 1. basic.py
# ══════════════════════════════════════════════

class TestBasicVelocity:
    def test_mph_to_kmh_conversion(self):
        assert _assess_velocity(97.0) == round(97.0 * 1.60934)

    def test_common_value(self):
        # 97 mph ≈ 156 km/h
        assert _assess_velocity(97.0) == 156

    def test_100mph(self):
        # 100 mph ≈ 161 km/h
        assert _assess_velocity(100.0) == 161


class TestBasicControl:
    """コントロール = Zone% + (15 - BB%)。BREAKPOINTS=[65,60,55,50,45,40,35]"""

    def test_s_rank(self):
        # zone=55, bb=4 → 55+11=66 >= 65 → S
        assert _assess_control(55.0, 4.0) == "S"

    def test_a_rank(self):
        # zone=50, bb=5 → 50+10=60 >= 60 → A
        assert _assess_control(50.0, 5.0) == "A"

    def test_b_rank(self):
        # zone=45, bb=5 → 45+10=55 >= 55 → B
        assert _assess_control(45.0, 5.0) == "B"

    def test_c_rank(self):
        # zone=40, bb=5 → 40+10=50 >= 50 → C
        assert _assess_control(40.0, 5.0) == "C"

    def test_g_rank_high_bb(self):
        # zone=30, bb=20 → 30-5=25 < 35 → G
        assert _assess_control(30.0, 20.0) == "G"

    def test_boundary_s_a(self):
        # zone=50, bb=0 → 50+15=65 → S (境界ちょうど)
        assert _assess_control(50.0, 0.0) == "S"
        # zone=50, bb=0.1 → 64.9 → A
        assert _assess_control(50.0, 0.1) == "A"


class TestBasicStamina:
    """1試合あたりの平均投球数 (avg_pitches_per_game) で先発・救援を統一評価する。
    breakpoints: [95, 85, 75, 65, 45, 0] → S, A, B, C, D, E
    """

    def test_s_rank_high_pitch_count(self):
        # 100 球/試合 → S
        stats = make_stats(avg_pitches_per_game=100.0)
        assert _assess_stamina(stats) == "S"

    def test_a_rank(self):
        # 90 球/試合 → A
        stats = make_stats(avg_pitches_per_game=90.0)
        assert _assess_stamina(stats) == "A"

    def test_b_rank(self):
        # 80 球/試合 → B
        stats = make_stats(avg_pitches_per_game=80.0)
        assert _assess_stamina(stats) == "B"

    def test_c_rank(self):
        # 70 球/試合 → C
        stats = make_stats(avg_pitches_per_game=70.0)
        assert _assess_stamina(stats) == "C"

    def test_d_rank(self):
        # 50 球/試合 → D
        stats = make_stats(avg_pitches_per_game=50.0)
        assert _assess_stamina(stats) == "D"

    def test_e_rank_low_pitch_count(self):
        # 30 球/試合 → E (救援投手の典型値)
        stats = make_stats(avg_pitches_per_game=30.0)
        assert _assess_stamina(stats) == "E"

    def test_boundary_s_a(self):
        # 95.0 → S (= threshold)
        assert _assess_stamina(make_stats(avg_pitches_per_game=95.0)) == "S"
        # 94.9 → A
        assert _assess_stamina(make_stats(avg_pitches_per_game=94.9)) == "A"

    def test_boundary_d_e(self):
        # 45.0 → D (= threshold)
        assert _assess_stamina(make_stats(avg_pitches_per_game=45.0)) == "D"
        # 44.9 → E
        assert _assess_stamina(make_stats(avg_pitches_per_game=44.9)) == "E"

    def test_none_defaults_to_c(self):
        stats = make_stats(avg_pitches_per_game=None)
        assert _assess_stamina(stats) == "C"

    def test_zero_or_negative_defaults_to_c(self):
        # データなし扱い → C
        assert _assess_stamina(make_stats(avg_pitches_per_game=0.0)) == "C"

    def test_reliever_uses_same_logic(self):
        # 救援投手 (games_started=0) でも avg_pitches_per_game で評価される
        # 20 球/試合 → E (救援は通常 E グレード)
        stats = make_stats(avg_pitches_per_game=20.0, games=70, games_started=0)
        assert _assess_stamina(stats) == "E"

    def test_assess_basic_returns_pitcher_basic(self):
        from pawapro_scout.models import PitcherBasic
        stats = make_stats()
        result = assess_basic(stats)
        assert isinstance(result, PitcherBasic)


# ══════════════════════════════════════════════
# 2. pitch_classifier.py
# ══════════════════════════════════════════════

class TestPitchClassify:
    # ── fastball ──
    def test_ff_is_straight(self):
        assert _classify(make_pitch("FF")) == "ストレート"

    def test_fa_is_straight(self):
        assert _classify(make_pitch("FA")) == "ストレート"

    # ── slider family ──
    def test_sl_small_hb_is_v_slider(self):
        # abs(HB) < 4 → Vスライダー
        p = make_pitch("SL", hb=3.0, ivb=5.0, dv=8.0)
        assert _classify(p) == "Vスライダー"

    def test_st_large_hb_is_sweeper(self):
        # abs(HB) >= 15 AND HB > |IVB| → スイーパー
        p = make_pitch("ST", hb=16.0, ivb=5.0, dv=10.0)
        assert _classify(p) == "スイーパー"

    def test_sl_low_dv_is_h_slider(self):
        # abs(HB) >= 4, HB < 15, ΔV <= 5
        p = make_pitch("SL", hb=8.0, ivb=3.0, dv=4.0)
        assert _classify(p) == "Hスライダー"

    def test_sl_normal_is_slider(self):
        p = make_pitch("SL", hb=8.0, ivb=3.0, dv=8.0)
        assert _classify(p) == "スライダー"

    # ── sinker family ──
    def test_si_low_dv_small_hb_is_two_seam(self):
        p = make_pitch("SI", hb=8.0, dv=1.5)
        assert _classify(p) == "ツーシーム"

    def test_si_low_dv_large_hb_is_highspeed_sinker(self):
        p = make_pitch("SI", hb=12.0, dv=3.5)
        assert _classify(p) == "高速シンカー"

    def test_si_large_dv_is_sinker(self):
        p = make_pitch("SI", hb=10.0, dv=5.0)
        assert _classify(p) == "シンカー"

    # ── splitter family ──
    def test_fs_small_dv_is_sff(self):
        p = make_pitch("FS", dv=5.0)
        assert _classify(p) == "SFF"

    def test_fs_large_dv_is_fork(self):
        p = make_pitch("FS", dv=9.0)
        assert _classify(p) == "フォーク"

    # ── changeup ──
    def test_ch_large_hb_is_circle_change(self):
        p = make_pitch("CH", hb=12.0)
        assert _classify(p) == "サークルチェンジ"

    def test_ch_small_hb_is_changeup(self):
        p = make_pitch("CH", hb=7.0)
        assert _classify(p) == "チェンジアップ"

    # ── cutter ──
    def test_fc_small_hb_is_cutball(self):
        p = make_pitch("FC", hb=4.0)
        assert _classify(p) == "カットボール"

    def test_fc_large_hb_is_h_slider(self):
        p = make_pitch("FC", hb=7.0)
        assert _classify(p) == "Hスライダー"

    # ── curveball / knuckleball ──
    def test_cu_is_curve(self):
        assert _classify(make_pitch("CU")) == "カーブ"

    def test_kc_is_curve(self):
        assert _classify(make_pitch("KC")) == "カーブ"

    def test_kn_is_knuckle(self):
        assert _classify(make_pitch("KN")) == "ナックル"

    # ── unknown ──
    def test_un_is_fume(self):
        assert _classify(make_pitch("UN")) == "不明"


class TestCalcHenka:
    def test_high_whiff_base_7(self):
        p = make_pitch(whiff=50.0, rv=-3.0)
        assert _calc_henka(p) == 7  # base=7, bonus+1 → clamp 7

    def test_high_whiff_no_bonus(self):
        p = make_pitch(whiff=46.0, rv=0.0)
        assert _calc_henka(p) == 7  # base=7, no adj

    def test_mid_whiff_base_5(self):
        p = make_pitch(whiff=38.0, rv=0.0)
        assert _calc_henka(p) == 5

    def test_low_whiff_base_3(self):
        p = make_pitch(whiff=22.0, rv=0.0)
        assert _calc_henka(p) == 3

    def test_very_low_whiff_base_1(self):
        p = make_pitch(whiff=10.0, rv=0.0)
        assert _calc_henka(p) == 1

    def test_rv_bonus_adds_1(self):
        p = make_pitch(whiff=22.0, rv=-3.0)  # base=3, bonus+1 → 4
        assert _calc_henka(p) == 4

    def test_rv_penalty_subtracts_1(self):
        p = make_pitch(whiff=22.0, rv=3.0)  # base=3, penalty-1 → 2
        assert _calc_henka(p) == 2

    def test_clamped_minimum_1(self):
        p = make_pitch(whiff=10.0, rv=3.0)  # base=1, penalty → clamp to 1
        assert _calc_henka(p) == 1

    def test_clamped_maximum_7(self):
        p = make_pitch(whiff=50.0, rv=-5.0)  # base=7, bonus → clamp 7
        assert _calc_henka(p) == 7


class TestClassifyPitches:
    def test_returns_list_of_pitch_entry(self):
        pitches = [make_pitch("FF"), make_pitch("SL", hb=8.0, dv=8.0)]
        result = classify_pitches(pitches)
        assert all(isinstance(e, PitchEntry) for e in result)

    def test_unknown_excluded(self):
        pitches = [make_pitch("FF"), make_pitch("UN")]
        result = classify_pitches(pitches)
        names = [e.名称 for e in result]
        assert "不明" not in names
        assert "ストレート" in names

    def test_empty_input(self):
        assert classify_pitches([]) == []


# ══════════════════════════════════════════════
# 3. rank_abilities.py
# ══════════════════════════════════════════════

class TestRankAbilities:
    def test_returns_6_keys(self):
        result = assess_rank_abilities(make_stats())
        assert set(result.keys()) == {"打たれ強さ", "回復", "クイック", "対ピンチ", "対左打者", "ノビ"}

    def test_打たれ強さ_gold_at_lob85(self):
        # LOB% >= 85 → 金
        stats = make_stats(lob_percent=85.0)
        assert assess_rank_abilities(stats)["打たれ強さ"] == "金"

    def test_打たれ強さ_a_at_lob80(self):
        # LOB_NOBITARESOSA_BREAKPOINTS[1]=80.0 → A
        stats = make_stats(lob_percent=80.0)
        assert assess_rank_abilities(stats)["打たれ強さ"] == "A"

    def test_ノビ_gold_on_high_ivb(self):
        # r1 仕様: 4seam IVB >= 21in → 金 (怪童)
        stats = make_stats(pitches=[make_pitch("FF", ivb=21.0)])
        assert assess_rank_abilities(stats)["ノビ"] == "金"

    def test_対ピンチ_gold_on_great_diff(self):
        # risp - season = -0.090 → 金
        stats = make_stats(risp_xwoba=0.230, season_xwoba=0.320)
        assert assess_rank_abilities(stats)["対ピンチ"] == "金"

    def test_対ピンチ_g_on_bad_diff(self):
        # risp - season = +0.100 → G
        stats = make_stats(risp_xwoba=0.420, season_xwoba=0.320)
        assert assess_rank_abilities(stats)["対ピンチ"] == "G"

    def test_クイック_gold_on_low_pop_time(self):
        # r1 仕様: Pop Time <= 1.20s → 金 (走者釘付)
        stats = make_stats(pop_time=1.20)
        assert assess_rank_abilities(stats)["クイック"] == "金"

    def test_クイック_default_c_on_no_data(self):
        stats = make_stats(pop_time=None)
        assert assess_rank_abilities(stats)["クイック"] == "C"

    def test_回復_c_on_155ip(self):
        # 先発 (GS=28/G=30): IP=155 → RECOVERY_BREAKPOINTS_IP[3]=155 → C
        stats = make_stats(ip=155.0, games=30, games_started=28)
        assert assess_rank_abilities(stats)["回復"] == "C"

    def test_回復_s_on_195ip(self):
        # 先発: IP=195 → RECOVERY_BREAKPOINTS_IP[0]=195 → S
        stats = make_stats(ip=195.0, games=30, games_started=28)
        assert assess_rank_abilities(stats)["回復"] == "S"


# ══════════════════════════════════════════════
# 4. gold_special.py
# ══════════════════════════════════════════════

class TestGoldSpecial:
    def test_doctor_k_at_35pct(self):
        # K% >= 35.0 → ドクターK
        stats = make_stats(k_percent=35.0)
        assert "ドクターK" in assess_gold_special(stats)

    def test_doctor_k_not_below_35pct(self):
        # K% = 34.9 → 付与しない
        stats = make_stats(k_percent=34.9)
        assert "ドクターK" not in assess_gold_special(stats)

    def test_monster_stuff_at_99th(self):
        stats = make_stats(exit_vel_percentile=99)
        assert "怪物球威" in assess_gold_special(stats)

    def test_hengenjizai_large_speed_range(self):
        # 新基準: 速度差 >= 20mph + 全球種 RV/100 >= 0 (使用率 5% 以上)
        pitches = [
            make_pitch("FF", vel=98.0, rv=2.0),
            make_pitch("CH", vel=75.0, rv=1.0),  # 差 23mph >= 20
        ]
        stats = make_stats(pitches=pitches)
        assert "変幻自在" in assess_gold_special(stats)

    def test_hengenjizai_not_on_small_range(self):
        pitches = [
            make_pitch("FF", vel=97.0),
            make_pitch("SL", vel=88.0),  # 差 9mph < 20
        ]
        stats = make_stats(pitches=pitches)
        assert "変幻自在" not in assess_gold_special(stats)

    def test_kaido_on_high_ivb(self):
        # 新基準: IVB >= 21.0
        pitches = [make_pitch("FF", ivb=22.0)]
        stats = make_stats(pitches=pitches)
        assert "怪童" in assess_gold_special(stats)

    def test_kaido_not_on_normal_ivb(self):
        pitches = [make_pitch("FF", ivb=14.0)]
        stats = make_stats(pitches=pitches)
        assert "怪童" not in assess_gold_special(stats)

    def test_no_gold_on_average_stats(self):
        result = assess_gold_special(make_stats())
        assert result == []


# ══════════════════════════════════════════════
# 5. blue_special.py
# ══════════════════════════════════════════════

class TestBlueSpecial:
    def test_datsusansen_on_high_k(self):
        # 新基準: K% >= 27.0%
        stats = make_stats(k_percent=27.0)
        assert "奪三振" in assess_blue_special(stats)

    def test_datsusansen_not_on_low_k(self):
        stats = make_stats(k_percent=24.0)
        assert "奪三振" not in assess_blue_special(stats)

    def test_release_maru_on_small_std(self):
        stats = make_stats(release_x_stddev=0.2, release_z_stddev=0.2)
        assert "リリース◯" in assess_blue_special(stats)

    def test_release_maru_not_on_large_std(self):
        stats = make_stats(release_x_stddev=0.8, release_z_stddev=0.8)
        assert "リリース◯" not in assess_blue_special(stats)

    def test_kankyuu_maru_on_sufficient_diff(self):
        # 新基準: 速度差 >= 15mph + 有効球種 (usage >= 5%) 2 つ以上
        pitches = [
            make_pitch("FF", vel=97.0, usage=60.0),
            make_pitch("CH", vel=80.0, usage=20.0),
        ]
        stats = make_stats(pitches=pitches)
        assert "緩急◯" in assess_blue_special(stats)

    def test_kankyuu_maru_not_when_hengenjizai(self):
        # 20mph以上 → 変幻自在で 緩急◯ は付かない
        pitches = [
            make_pitch("FF", vel=98.0, usage=60.0),
            make_pitch("CH", vel=75.0, usage=20.0),
        ]
        stats = make_stats(pitches=pitches)
        assert "緩急◯" not in assess_blue_special(stats)

    def test_tamamochichu_on_high_extension(self):
        # 新基準: Extension >= 6.7ft
        stats = make_stats(extension_ft=6.7)
        assert "球持ち◯" in assess_blue_special(stats)

    def test_emergency_maru_on_high_ir(self):
        # 新基準: IRS% >= 75%
        stats = make_stats(ir_stranded_pct=75.0)
        assert "緊急登板◯" in assess_blue_special(stats)

    def test_low_zone_maru(self):
        # 新基準: Low Zone% >= 50%
        stats = make_stats(low_zone_pct=50.0)
        assert "低め◯" in assess_blue_special(stats)

    def test_nigeball(self):
        # 新基準: HR/9 <= 0.8
        stats = make_stats(hr_per_9=0.7)
        assert "逃げ球" in assess_blue_special(stats)

    def test_nigeball_not_when_zero(self):
        # データなし (0.0) → 付与しない
        stats = make_stats(hr_per_9=0.0)
        assert "逃げ球" not in assess_blue_special(stats)

    def test_natural_shoot_on_ff_large_hb(self):
        # 新基準: FB HB >= 8インチ (ナチュシュに名称変更)
        pitches = [make_pitch("FF", hb=12.0)]
        stats = make_stats(pitches=pitches)
        assert "ナチュシュ" in assess_blue_special(stats)

    def test_jiriagari(self):
        # 新基準: 7回以降 xwOBA - 1回 xwOBA <= -0.030
        stats = make_stats(inning7plus_xwoba=0.260, inning1_xwoba=0.300)
        assert "尻上がり" in assess_blue_special(stats)

    def test_tachiagarimaru(self):
        # 新基準: 1回 xwOBA <= .250
        stats = make_stats(inning1_xwoba=0.250)
        assert "立ち上がり◯" in assess_blue_special(stats)

    def test_no_blue_on_poor_conditions(self):
        # データなし・閾値未達の stats → 文脈依存の青特は付かない
        stats = make_stats(
            k_percent=24.0,           # 奪三振: 27%未満 → 付かない
            extension_ft=6.0,         # 球持ち◯: 6.7ft未満 → 付かない
            ir_stranded_pct=None,     # 緊急登板◯: データなし → 付かない
            low_zone_pct=30.0,        # 低め◯: 50%未満 → 付かない
            hr_per_9=0.0,             # 逃げ球: データなし → 付かない
            inning1_xwoba=0.320,      # 立ち上がり◯: .250超 → 付かない
        )
        result = assess_blue_special(stats)
        assert "奪三振" not in result
        assert "球持ち◯" not in result
        assert "緊急登板◯" not in result
        assert "低め◯" not in result
        assert "立ち上がり◯" not in result


# ══════════════════════════════════════════════
# 6. red_special.py
# ══════════════════════════════════════════════

class TestRedSpecial:
    def test_shikyu_on_high_bb(self):
        stats = make_stats(bb_percent=11.0)
        assert "四球" in assess_red_special(stats)

    def test_shikyu_not_on_low_bb(self):
        stats = make_stats(bb_percent=7.0)
        assert "四球" not in assess_red_special(stats)

    def test_karui_tama_on_high_hard_hit(self):
        stats = make_stats(hard_hit_percent=48.0)
        assert "軽い球" in assess_red_special(stats)

    def test_slow_starter(self):
        # 新基準: inning1 - season >= +0.060
        stats = make_stats(inning1_xwoba=0.380, season_xwoba=0.320)
        assert "スロースターター" in assess_red_special(stats)

    def test_ippatsu_on_high_hr9(self):
        stats = make_stats(hr_per_9=1.5)
        assert "一発" in assess_red_special(stats)

    def test_makeun_on_low_rs(self):
        # 新基準: RS/9 <= 3.0
        stats = make_stats(run_support=3.0)
        assert "負け運" in assess_red_special(stats)

    def test_velo_unstable_on_diff(self):
        # 球速安定✕: Max - Avg >= 3.1mph
        stats = make_stats(max_velocity_mph=98.0, avg_velocity_mph=94.0)
        assert "球速安定✕" in assess_red_special(stats)

    def test_no_red_on_good_stats(self):
        stats = make_stats(
            bb_percent=5.0,
            hard_hit_percent=35.0,
            inning1_xwoba=0.300,
            season_xwoba=0.320,
            hr_per_9=0.7,
        )
        assert assess_red_special(stats) == []
