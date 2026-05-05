"""
assess/batter/gold_special.py
野手の金特殊能力を査定する。

金特        判定指標
アーチスト   Barrel% >= 20% AND 平均打球角度 15〜20度
安打製造機   xBA >= .310 AND Whiff% <= 15%
"""

from __future__ import annotations

from pawapro_scout.config import (
    GOLD_ARCHIST_BARREL_MIN,
    GOLD_ARCHIST_LA_MAX,
    GOLD_ARCHIST_LA_MIN,
    GOLD_HIT_MACHINE_WHIFF_MAX,
    GOLD_HIT_MACHINE_XBA_MIN,
)
from pawapro_scout.models import BatterStats


def assess_gold_special(stats: BatterStats) -> list[str]:
    """BatterStats から獲得する金特リストを返す。"""
    result: list[str] = []

    if _is_aachisuto(stats):
        result.append("アーチスト")

    if _is_hit_machine(stats):
        result.append("安打製造機")

    return result


# ──────────────────────────────────────────────
# 各金特の判定
# ──────────────────────────────────────────────

def _is_aachisuto(stats: BatterStats) -> bool:
    """アーチスト: Barrel% >= 20% AND 平均打球角度 15〜20度。"""
    return (
        stats.barrel_percent >= GOLD_ARCHIST_BARREL_MIN
        and GOLD_ARCHIST_LA_MIN <= stats.avg_launch_angle <= GOLD_ARCHIST_LA_MAX
    )


def _is_hit_machine(stats: BatterStats) -> bool:
    """安打製造機: xBA >= .310 AND Whiff% <= 15%。"""
    return (
        stats.xba >= GOLD_HIT_MACHINE_XBA_MIN
        and stats.whiff_percent <= GOLD_HIT_MACHINE_WHIFF_MAX
    )
