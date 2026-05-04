"""
assess/pitcher/gold_special.py
投手の金特殊能力を査定する。

金特            判定指標
ドクターK       K% >= 35.0% (絶対値)
怪物球威        被打球平均速度 <= 85.0 mph (絶対値)
変幻自在        全球種の最速-最遅 >= 20mph
怪童            4seam の IVB >= 20in
精密機械        Low Zone% >= 45% AND BB% <= 4.0%
ハイスピンジャイロ 4seam Active Spin <= 70% AND 球速 >= 97mph
"""

from __future__ import annotations

from pawapro_scout.config import (
    GOLD_AVG_EV_MAX,
    GOLD_HIGH_SPIN_GYRO_SPIN_MAX,
    GOLD_HIGH_SPIN_GYRO_VEL_MIN,
    GOLD_IVB_KAIDO_MIN,
    GOLD_K_PCT_MIN,
    GOLD_PRECISION_BB_MAX,
    GOLD_PRECISION_LOWZONE_MIN,
    GOLD_SPEED_DIFF_MAX,
)
from pawapro_scout.models import PitchAggregated, PitcherStats


def assess_gold_special(stats: PitcherStats) -> list[str]:
    """PitcherStats から獲得する金特リストを返す。"""
    result: list[str] = []

    if _is_doctor_k(stats):
        result.append("ドクターK")

    if _is_monster_stuff(stats):
        result.append("怪物球威")

    if _is_hengenjizai(stats.pitches):
        result.append("変幻自在")

    if _is_kaido(stats.pitches):
        result.append("怪童")

    if _is_seimitsu_kikai(stats):
        result.append("精密機械")

    if _is_high_spin_gyro(stats):
        result.append("ハイスピンジャイロ")

    return result


# ──────────────────────────────────────────────
# 各金特の判定
# ──────────────────────────────────────────────

def _is_doctor_k(stats: PitcherStats) -> bool:
    """ドクターK: K% >= 35.0% (絶対閾値)。"""
    return stats.k_percent >= GOLD_K_PCT_MIN


def _is_monster_stuff(stats: PitcherStats) -> bool:
    """怪物球威: 被打球平均速度 <= 85.0 mph。データ未取得時はパーセンタイルで代替。"""
    if stats.avg_ev_against > 0.0:
        return stats.avg_ev_against <= GOLD_AVG_EV_MAX
    # avg_ev_against 未取得時のフォールバック: パーセンタイル 99 以上
    from pawapro_scout.config import GOLD_PERCENTILE
    return stats.exit_vel_percentile >= GOLD_PERCENTILE


def _is_hengenjizai(pitches: list[PitchAggregated]) -> bool:
    """
    変幻自在: 全球種の最高球速 - 最低球速 >= 20mph。
    球種が2種以上必要。
    """
    if len(pitches) < 2:
        return False
    vels = [p.velocity_avg for p in pitches if p.velocity_avg > 0]
    if len(vels) < 2:
        return False
    return (max(vels) - min(vels)) >= GOLD_SPEED_DIFF_MAX


def _is_kaido(pitches: list[PitchAggregated]) -> bool:
    """
    怪童: 4seam の IVB が 20in 以上。
    IVB は induced vertical break (絶対値で判定)。
    """
    ff = next((p for p in pitches if p.pitch_type in ("FF", "FA")), None)
    if ff is None:
        return False
    return abs(ff.induced_vertical_break) >= GOLD_IVB_KAIDO_MIN


def _is_seimitsu_kikai(stats: PitcherStats) -> bool:
    """精密機械: Low Zone% >= 45% AND BB% <= 4.0%。"""
    return (
        stats.low_zone_pct >= GOLD_PRECISION_LOWZONE_MIN
        and stats.bb_percent <= GOLD_PRECISION_BB_MAX
    )


def _is_high_spin_gyro(stats: PitcherStats) -> bool:
    """ハイスピンジャイロ: 4seam Active Spin <= 70% AND 最高球速 >= 97mph。"""
    if stats.active_spin_4seam is None:
        return False
    return (
        stats.active_spin_4seam <= GOLD_HIGH_SPIN_GYRO_SPIN_MAX
        and stats.max_velocity_mph >= GOLD_HIGH_SPIN_GYRO_VEL_MIN
    )
