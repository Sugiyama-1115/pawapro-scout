"""
assess/batter/gold_special.py
野手の金特殊能力を査定する。

金特        判定指標
アーチスト   barrel_percentile >= 99
安打製造機   xba_percentile >= 99
"""

from __future__ import annotations

from pawapro_scout.config import GOLD_PERCENTILE
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
    """アーチスト: バレルパーセンタイル >= 99。"""
    return stats.barrel_percentile >= GOLD_PERCENTILE


def _is_hit_machine(stats: BatterStats) -> bool:
    """安打製造機: xBA パーセンタイル >= 99。"""
    return stats.xba_percentile >= GOLD_PERCENTILE
