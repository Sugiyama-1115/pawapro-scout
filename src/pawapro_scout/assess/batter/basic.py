"""
assess/batter/basic.py
野手の基礎能力（弾道/ミート/パワー/走力/肩力/守備力/捕球）を査定する。

能力       指標
弾道       avg_launch_angle → 1/2/3/4  (sweet_spot% >= 35% なら最低3)
ミート     xBA → S/A/B/C/D/E/F/G
パワー     max_exit_velocity (mph) → S/A/B/C/D/E/F/G
走力       sprint_speed (ft/sec) → S/A/B/C/D/E/F/G
肩力       外野=arm_strength_mph / 内野=arm_strength_mph / 捕手=pop_time
守備力     oaa_percentile → S/A/B/C/D/E/F/G
捕球       fielding_run_value → S/A/B/C/D/E/F/G
"""

from __future__ import annotations

from pawapro_scout.config import (
    ARM_IF_BREAKPOINTS,
    ARM_OF_BREAKPOINTS,
    CATCH_FRV_BREAKPOINTS,
    FIELDING_PERCENTILE_BREAKPOINTS,
    MEET_BREAKPOINTS,
    POP_TIME_BREAKPOINTS,
    POWER_BREAKPOINTS,
    SPEED_BREAKPOINTS,
    SWEET_SPOT_MIN_FOR_3,
    TRAJECTORY_BREAKPOINTS,
    percentile_to_grade,
    score_to_grade,
)
from pawapro_scout.models import BatterBasic, BatterStats

_OF_POSITIONS = {"LF", "CF", "RF", "OF"}
_CATCHER = "C"


def assess_basic(stats: BatterStats, position: str = "OF") -> BatterBasic:
    """BatterStats から基礎能力を返す。"""
    return BatterBasic(
        弾道=_assess_trajectory(stats),
        ミート=_assess_meet(stats),
        パワー=_assess_power(stats),
        走力=_assess_speed(stats),
        肩力=_assess_arm(stats, position),
        守備力=_assess_fielding(stats),
        捕球=_assess_catch(stats),
    )


# ──────────────────────────────────────────────
# 各基礎能力の判定
# ──────────────────────────────────────────────

def _assess_trajectory(stats: BatterStats) -> int:
    """
    弾道: avg_launch_angle → 1-4。
    TRAJECTORY_BREAKPOINTS = [18.1, 12.1, 5.0] → 4 / 3 / 2 / (else 1)
    sweet_spot% >= 35% なら最低3を保証。
    """
    la = stats.avg_launch_angle
    if la > TRAJECTORY_BREAKPOINTS[0]:       # > 18.1 → 4
        grade = 4
    elif la >= TRAJECTORY_BREAKPOINTS[1]:    # 12.1 ~ 18.1 → 3
        grade = 3
    elif la >= TRAJECTORY_BREAKPOINTS[2]:    # 5.0 ~ 12.0 → 2
        grade = 2
    else:                                    # < 5.0 → 1
        grade = 1

    if stats.sweet_spot_percent >= SWEET_SPOT_MIN_FOR_3:
        grade = max(grade, 3)

    return grade


def _assess_meet(stats: BatterStats) -> str:
    """ミート: xBA 直接値 (.300以上=S, .280-.299=A, ...)"""
    return score_to_grade(stats.xba, MEET_BREAKPOINTS)


def _assess_power(stats: BatterStats) -> str:
    """パワー: Max Exit Velocity (mph)"""
    return score_to_grade(stats.max_exit_velocity, POWER_BREAKPOINTS)


def _assess_speed(stats: BatterStats) -> str:
    """走力: Sprint Speed (ft/sec)"""
    return score_to_grade(stats.sprint_speed, SPEED_BREAKPOINTS)


def _assess_arm(stats: BatterStats, position: str) -> str:
    """肩力: ポジションにより判定指標を切り替え。"""
    pos = position.upper()
    if pos == _CATCHER:
        return _arm_catcher(stats)
    if pos in _OF_POSITIONS:
        if stats.arm_strength_mph is None:
            return "C"
        return score_to_grade(stats.arm_strength_mph, ARM_OF_BREAKPOINTS)
    # 内野手 / DH
    if stats.arm_strength_mph is None:
        return "C"
    return score_to_grade(stats.arm_strength_mph, ARM_IF_BREAKPOINTS)


def _arm_catcher(stats: BatterStats) -> str:
    """捕手の肩力: pop_time (秒, 小さいほど良い)。"""
    if stats.pop_time is None:
        return "C"
    for threshold, grade in zip(POP_TIME_BREAKPOINTS, ["S", "A", "B", "C", "D", "E", "F"]):
        if stats.pop_time <= threshold:
            return grade
    return "G"


def _assess_fielding(stats: BatterStats) -> str:
    """守備力: OAA パーセンタイル → グレード。"""
    return percentile_to_grade(stats.oaa_percentile, FIELDING_PERCENTILE_BREAKPOINTS)


def _assess_catch(stats: BatterStats) -> str:
    """捕球: Fielding Run Value → グレード。"""
    return score_to_grade(stats.fielding_run_value, CATCH_FRV_BREAKPOINTS)
