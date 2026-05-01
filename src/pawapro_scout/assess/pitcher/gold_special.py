"""
assess/pitcher/gold_special.py
投手の金特殊能力を査定する。

金特    判定指標
ドクターK       k_percentile >= 99
怪物球威        exit_vel_percentile >= 99 (被打球速度が最小クラス)
変幻自在        全球種の最速-最遅 >= 20mph
怪童            いずれかの球種の abs(IVB) >= 20in
"""

from __future__ import annotations

from pawapro_scout.config import (
    GOLD_IVB_KAIDO_MIN,
    GOLD_PERCENTILE,
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

    return result


# ──────────────────────────────────────────────
# 各金特の判定
# ──────────────────────────────────────────────

def _is_doctor_k(stats: PitcherStats) -> bool:
    """ドクターK: 三振パーセンタイルが 99 以上。"""
    return stats.k_percentile >= GOLD_PERCENTILE


def _is_monster_stuff(stats: PitcherStats) -> bool:
    """怪物球威: 被打球速度パーセンタイルが 99 以上（打者が強い打球を打てない）。"""
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
    怪童: いずれかの球種の IVB が 20in 以上。
    IVB は induced vertical break (正 = 浮き上がり / ライズ方向)。
    """
    return any(abs(p.induced_vertical_break) >= GOLD_IVB_KAIDO_MIN for p in pitches)
