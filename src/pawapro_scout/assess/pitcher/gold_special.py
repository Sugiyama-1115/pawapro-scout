"""
assess/pitcher/gold_special.py
投手の金特殊能力を査定する（新基準 r1 - 27種）。

判定指標は config.py の GOLD_* 定数に集約。
データ未取得の指標は付与しない（return False）。
"""

from __future__ import annotations

from pawapro_scout.config import (
    GOLD_ABARE_BB_MIN,
    GOLD_ABARE_IVB_MIN,
    GOLD_AVG_EV_MAX,
    GOLD_BURNOUT_WHIFF_DIFF,
    GOLD_CROSS_CANNON_WHIFF_MIN,
    GOLD_DOKONJO_RV_IMPROVE,
    GOLD_FUKUTSU_HARD_HIT_MAX,
    GOLD_GAS_TANK_G_MIN,
    GOLD_GAS_TANK_IP_MIN,
    GOLD_GEAR_CHANGE_DIFF,
    GOLD_HIGH_SPIN_GYRO_SPIN_MAX,
    GOLD_HIGH_SPIN_GYRO_VEL_MIN,
    GOLD_INSIDE_MUSO_WHIFF_MIN,
    GOLD_IVB_KAIDO_MIN,
    GOLD_KIREAJI_WHIFF_MIN,
    GOLD_KYOSHINZO_XWOBA_MAX,
    GOLD_K_PCT_MIN,
    GOLD_LATE_XWOBA_MAX,
    GOLD_LEFT_KILLER_DIFF,
    GOLD_NO_HR_HR9_MAX,
    GOLD_PERCENTILE,
    GOLD_PRECISION2_BB_MAX,
    GOLD_PRECISION2_EDGE_MIN,
    GOLD_PRECISION_BB_MAX,
    GOLD_PRECISION_EDGE_MIN,
    GOLD_RUNNER_KUGI_POP_MAX,
    GOLD_RUNNER_KUGI_SB_RATE_MAX,
    GOLD_SPEED_DIFF_MAX,
    GOLD_TETSUWAN_RV_STDDEV_MAX,
    GOLD_TOP_GEAR_XWOBA_MAX,
    GOLD_TOP_KILLER_XWOBA_MAX,
    GOLD_TOUKON_ER9_MAX,
    GOLD_TOUKON_LOB_MIN,
    GOLD_WIN_STAR_RS9_MIN,
    GOLD_YOSHO_XWOBA_MAX,
)
from pawapro_scout.models import PitchAggregated, PitcherStats


def assess_gold_special(stats: PitcherStats) -> list[str]:
    """PitcherStats から獲得する金特リストを返す（新基準 r1）。"""
    result: list[str] = []

    if _is_doctor_k(stats):
        result.append("ドクターK")
    if _is_toukon(stats):
        result.append("闘魂")
    if _is_seimitsu_kikai(stats):
        result.append("精密機械")
    if _is_high_spin_gyro(stats):
        result.append("ハイスピンジャイロ")
    if _is_kaido(stats.pitches):
        result.append("怪童")
    if _is_abare_ball(stats):
        result.append("暴れ球")
    if _is_top_killer(stats):
        result.append("主砲キラー")
    if _is_monster_stuff(stats):
        result.append("怪物球威")
    if _is_left_killer(stats):
        result.append("左キラー")
    if _is_no_hr(stats):
        result.append("本塁打厳禁")
    if _is_dokonjo(stats):
        result.append("ド根性")
    if _is_late_force(stats):
        result.append("終盤力")
    if _is_top_gear(stats):
        result.append("トップギア")
    if _is_gear_change(stats):
        result.append("ギアチェンジ")
    if _is_hengenjizai(stats.pitches):
        result.append("変幻自在")
    if _is_cross_cannon_gold(stats):
        result.append("クロスキャノン")
    if _is_tetsuwan(stats):
        result.append("鉄腕")
    if _is_gas_tank(stats):
        result.append("ガソリンタンク")
    if _is_win_star(stats):
        result.append("勝利の星")
    if _is_fukutsu(stats):
        result.append("不屈の魂")
    if _is_kyoshinzo(stats):
        result.append("強心臓")
    if _is_runner_kugi(stats):
        result.append("走者釘付")
    if _is_kireaji(stats):
        result.append("驚異の切れ味")
    if _is_seimitsu_kikai_v2(stats):
        # 精密機械が二重定義のため重複排除
        if "精密機械" not in result:
            result.append("精密機械")
    if _is_burnout(stats):
        result.append("完全燃焼")
    if _is_inside_muso(stats):
        result.append("内角無双")
    if _is_yosho_maru(stats):
        result.append("要所◯")

    return result


# ──────────────────────────────────────────────
# 各金特の判定
# ──────────────────────────────────────────────

def _is_doctor_k(stats: PitcherStats) -> bool:
    """ドクターK: K% >= 35.0%。"""
    return stats.k_percent >= GOLD_K_PCT_MIN


def _is_toukon(stats: PitcherStats) -> bool:
    """闘魂: LOB% >= 85% + 自責点抑制（ER/9 <= 3.50）。"""
    if stats.lob_percent <= 0.0:
        return False
    if stats.lob_percent < GOLD_TOUKON_LOB_MIN:
        return False
    # ER/9 が利用可能なら追加条件、未取得なら LOB% のみで判定
    if stats.er_per_9 > 0.0:
        return stats.er_per_9 <= GOLD_TOUKON_ER9_MAX
    return True


def _is_seimitsu_kikai(stats: PitcherStats) -> bool:
    """精密機械: BB% <= 3.0% + Edge% >= 48%。"""
    if stats.bb_percent <= 0.0:
        return False
    return (
        stats.bb_percent <= GOLD_PRECISION_BB_MAX
        and stats.edge_percent >= GOLD_PRECISION_EDGE_MIN
    )


def _is_seimitsu_kikai_v2(stats: PitcherStats) -> bool:
    """精密機械(別定義): Edge% >= 50% + BB% <= 2.5%。"""
    if stats.bb_percent <= 0.0:
        return False
    return (
        stats.edge_percent >= GOLD_PRECISION2_EDGE_MIN
        and stats.bb_percent <= GOLD_PRECISION2_BB_MAX
    )


def _is_high_spin_gyro(stats: PitcherStats) -> bool:
    """ハイスピンジャイロ: Active Spin <= 70% + Max Velocity >= 98mph。"""
    if stats.active_spin_4seam is None:
        return False
    return (
        stats.active_spin_4seam <= GOLD_HIGH_SPIN_GYRO_SPIN_MAX
        and stats.max_velocity_mph >= GOLD_HIGH_SPIN_GYRO_VEL_MIN
    )


def _is_kaido(pitches: list[PitchAggregated]) -> bool:
    """怪童: 4seam IVB >= 21.0インチ。"""
    ff = next((p for p in pitches if p.pitch_type in ("FF", "FA")), None)
    if ff is None:
        return False
    return abs(ff.induced_vertical_break) >= GOLD_IVB_KAIDO_MIN


def _is_abare_ball(stats: PitcherStats) -> bool:
    """暴れ球: 4seam IVB >= 20.0 + BB% >= 12.0%。"""
    ff = next((p for p in stats.pitches if p.pitch_type in ("FF", "FA")), None)
    if ff is None:
        return False
    return (
        abs(ff.induced_vertical_break) >= GOLD_ABARE_IVB_MIN
        and stats.bb_percent >= GOLD_ABARE_BB_MIN
    )


def _is_top_killer(stats: PitcherStats) -> bool:
    """主砲キラー: 対 xwOBA上位10% 打者 被xwOBA <= .220。"""
    if stats.xwoba_vs_top_hitters <= 0.0:
        return False
    return stats.xwoba_vs_top_hitters <= GOLD_TOP_KILLER_XWOBA_MAX


def _is_monster_stuff(stats: PitcherStats) -> bool:
    """怪物球威: 被打球平均速度 <= 85.0 mph。データ未取得はパーセンタイル代替。"""
    if stats.avg_ev_against > 0.0:
        return stats.avg_ev_against <= GOLD_AVG_EV_MAX
    return stats.exit_vel_percentile >= GOLD_PERCENTILE


def _is_left_killer(stats: PitcherStats) -> bool:
    """左キラー: 対左 xwOBA - 通常 xwOBA <= -.070。"""
    if stats.season_xwoba <= 0.0 or stats.vs_lhp_xwoba <= 0.0:
        return False
    return (stats.vs_lhp_xwoba - stats.season_xwoba) <= GOLD_LEFT_KILLER_DIFF


def _is_no_hr(stats: PitcherStats) -> bool:
    """本塁打厳禁: HR/9 <= 0.40 (規定投球回以上)。"""
    if stats.ip < 162.0:  # 規定投球回 (簡易)
        return False
    if stats.hr_per_9 <= 0.0:
        return False
    return stats.hr_per_9 <= GOLD_NO_HR_HR9_MAX


def _is_dokonjo(stats: PitcherStats) -> bool:
    """ド根性: 100球超え後の Pitching RV 改善幅 >= +.050。"""
    return stats.pitch_100plus_rv_improve >= GOLD_DOKONJO_RV_IMPROVE


def _is_late_force(stats: PitcherStats) -> bool:
    """終盤力: 7回以降 xwOBA <= .220。"""
    if stats.inning7plus_xwoba <= 0.0:
        return False
    return stats.inning7plus_xwoba <= GOLD_LATE_XWOBA_MAX


def _is_top_gear(stats: PitcherStats) -> bool:
    """トップギア: 1-2イニング目 xwOBA <= .200。"""
    inn1 = stats.inning1_xwoba
    inn2 = stats.inning2_xwoba
    valid = [x for x in (inn1, inn2) if x > 0.0]
    if not valid:
        return False
    avg = sum(valid) / len(valid)
    return avg <= GOLD_TOP_GEAR_XWOBA_MAX


def _is_gear_change(stats: PitcherStats) -> bool:
    """ギアチェンジ: 得点圏 xwOBA - 通常 <= -.080。"""
    if stats.season_xwoba <= 0.0 or stats.risp_xwoba <= 0.0:
        return False
    return (stats.risp_xwoba - stats.season_xwoba) <= GOLD_GEAR_CHANGE_DIFF


def _is_hengenjizai(pitches: list[PitchAggregated]) -> bool:
    """変幻自在: 最大球速差 >= 20mph + 全球種 Run Value がプラス。"""
    if len(pitches) < 2:
        return False
    vels = [p.velocity_avg for p in pitches if p.velocity_avg > 0]
    if len(vels) < 2:
        return False
    speed_diff_ok = (max(vels) - min(vels)) >= GOLD_SPEED_DIFF_MAX
    # 投手目線の rv_per_100 が正 = 投手有利。全球種が プラスである必要
    all_positive = all(p.rv_per_100 >= 0.0 for p in pitches if p.usage_pct >= 5.0)
    return speed_diff_ok and all_positive


def _is_cross_cannon_gold(stats: PitcherStats) -> bool:
    """クロスキャノン(金): 対角線 Shadow Whiff% >= 45%。"""
    return stats.cross_shadow_whiff_pct >= GOLD_CROSS_CANNON_WHIFF_MIN


def _is_tetsuwan(stats: PitcherStats) -> bool:
    """鉄腕: 月別 RV 標準偏差が極小。"""
    if stats.monthly_rv_stddev <= 0.0:
        return False
    return stats.monthly_rv_stddev <= GOLD_TETSUWAN_RV_STDDEV_MAX


def _is_gas_tank(stats: PitcherStats) -> bool:
    """ガソリンタンク: 80登板以上 OR 210イニング以上。"""
    return stats.games >= GOLD_GAS_TANK_G_MIN or stats.ip >= GOLD_GAS_TANK_IP_MIN


def _is_win_star(stats: PitcherStats) -> bool:
    """勝利の星: RS/9 >= 7.5。"""
    if stats.run_support is None:
        return False
    return stats.run_support >= GOLD_WIN_STAR_RS9_MIN


def _is_fukutsu(stats: PitcherStats) -> bool:
    """不屈の魂: ピンチ（得点圏）被ハードヒット率 <= 25%。"""
    if stats.risp_hard_hit_pct <= 0.0:
        return False
    return stats.risp_hard_hit_pct <= GOLD_FUKUTSU_HARD_HIT_MAX


def _is_kyoshinzo(stats: PitcherStats) -> bool:
    """強心臓: 得点圏 xwOBA <= .200。"""
    if stats.risp_xwoba <= 0.0:
        return False
    return stats.risp_xwoba <= GOLD_KYOSHINZO_XWOBA_MAX


def _is_runner_kugi(stats: PitcherStats) -> bool:
    """走者釘付: 被盗塁成功率 <= 50% + Pop Time <= 1.20秒。"""
    total = stats.sb_against + stats.cs_against
    if total == 0 or stats.pop_time is None:
        return False
    sb_rate = stats.sb_against / total
    return sb_rate <= GOLD_RUNNER_KUGI_SB_RATE_MAX and stats.pop_time <= GOLD_RUNNER_KUGI_POP_MAX


def _is_kireaji(stats: PitcherStats) -> bool:
    """驚異の切れ味: 変化球全般 Whiff% >= 45%。"""
    return stats.breaking_offspeed_whiff_pct >= GOLD_KIREAJI_WHIFF_MIN


def _is_burnout(stats: PitcherStats) -> bool:
    """完全燃焼: 80球目以降の Whiff% が +5% 以上上昇。"""
    return stats.late_pitch_whiff_diff >= GOLD_BURNOUT_WHIFF_DIFF


def _is_inside_muso(stats: PitcherStats) -> bool:
    """内角無双: 内角 Whiff% >= 45%。"""
    return stats.inside_whiff_pct >= GOLD_INSIDE_MUSO_WHIFF_MIN


def _is_yosho_maru(stats: PitcherStats) -> bool:
    """要所◯(金): High Leverage 被xwOBA <= .210。"""
    if stats.high_lev_xwoba <= 0.0:
        return False
    return stats.high_lev_xwoba <= GOLD_YOSHO_XWOBA_MAX
