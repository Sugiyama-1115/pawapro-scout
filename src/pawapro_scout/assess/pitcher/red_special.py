"""
assess/pitcher/red_special.py
投手の赤特殊能力（マイナス能力）を査定する（新基準 r1 - 11種）。

判定指標は config.py の RED_* 定数に集約。
データ未取得の指標は付与しない（return False）。
"""

from __future__ import annotations

from pawapro_scout.config import (
    RED_BB_PCT_MIN,
    RED_DISORDER_BB_PCT_MIN,
    RED_DISORDER_CONTROL_MIN,
    RED_HARD_HIT_MIN,
    RED_HR_PER_9_MIN,
    RED_RUN_SUPPORT_MAX,
    RED_SHOOT_HB_MIN,
    RED_SLOW_START_XWOBA,
    RED_VELO_UNSTABLE_DIFF_MPH,
)
from pawapro_scout.models import PitchAggregated, PitcherStats


def assess_red_special(stats: PitcherStats) -> list[str]:
    """PitcherStats から付与される赤特リストを返す（新基準 r1）。"""
    result: list[str] = []

    if _is_ippatsu(stats):
        result.append("一発")
    if _is_shikyu(stats):
        result.append("四球")
    if _is_karui_tama(stats):
        result.append("軽い球")
    if _is_slow_starter(stats):
        result.append("スロースターター")
    if _is_chikara_kubari(stats):
        result.append("力配り")
    if _is_sunzen(stats):
        result.append("寸前")
    if _is_ranchou(stats):
        result.append("乱調")
    if _is_makeun(stats):
        result.append("負け運")
    if _is_tanki(stats):
        result.append("短気")
    if _is_velo_unstable(stats):
        result.append("球速安定✕")
    if _is_shoot_rotation(stats.pitches):
        result.append("シュート回転")

    return result


# ──────────────────────────────────────────────
# 各赤特の判定
# ──────────────────────────────────────────────

def _is_ippatsu(stats: PitcherStats) -> bool:
    """一発: HR/9 >= 1.5。"""
    return stats.hr_per_9 >= RED_HR_PER_9_MIN


def _is_shikyu(stats: PitcherStats) -> bool:
    """四球: BB% >= 11.0%。"""
    return stats.bb_percent >= RED_BB_PCT_MIN


def _is_karui_tama(stats: PitcherStats) -> bool:
    """軽い球: Hard Hit% >= 45.0%。"""
    return stats.hard_hit_percent >= RED_HARD_HIT_MIN


def _is_slow_starter(stats: PitcherStats) -> bool:
    """スロースターター: 1回 xwOBA - 通算 >= +.060。"""
    if stats.season_xwoba <= 0.0 or stats.inning1_xwoba <= 0.0:
        return False
    return (stats.inning1_xwoba - stats.season_xwoba) >= RED_SLOW_START_XWOBA


def _is_chikara_kubari(stats: PitcherStats) -> bool:
    """力配り: 対下位打線 xwOBA > 対上位打線 xwOBA（手抜き的傾向）。"""
    if stats.upper_lineup_xwoba <= 0.0 or stats.lower_lineup_xwoba <= 0.0:
        return False
    return stats.lower_lineup_xwoba > stats.upper_lineup_xwoba


def _is_sunzen(stats: PitcherStats) -> bool:
    """寸前: 5回または9回（勝利目前）の被xwOBA上昇。"""
    return stats.inning5_or_9_xwoba_increase > 0.030


def _is_ranchou(stats: PitcherStats) -> bool:
    """乱調: Control 70以上 + BB% >= 10%。

    Control 指標は Zone% + (15 - BB%) の複合値で算出 (config.py のコントロール基準と同じ)。
    """
    if stats.bb_percent < RED_DISORDER_BB_PCT_MIN:
        return False
    # 複合コントロール指標
    control_index = stats.zone_percent + (15.0 - stats.bb_percent)
    return control_index >= RED_DISORDER_CONTROL_MIN


def _is_makeun(stats: PitcherStats) -> bool:
    """負け運: RS/9 <= 3.0。"""
    if stats.run_support is None:
        return False
    return stats.run_support <= RED_RUN_SUPPORT_MAX


def _is_tanki(stats: PitcherStats) -> bool:
    """短気: 被安打直後の Hard Hit% が通算より +10% 以上上昇。"""
    return stats.post_hit_hard_hit_increase >= 10.0


def _is_velo_unstable(stats: PitcherStats) -> bool:
    """球速安定✕: 最大-平均球速の差が 5km/h（約3.1mph）以上。"""
    if stats.max_velocity_mph <= 0.0 or stats.avg_velocity_mph <= 0.0:
        return False
    diff = stats.max_velocity_mph - stats.avg_velocity_mph
    return diff >= RED_VELO_UNSTABLE_DIFF_MPH


def _is_shoot_rotation(pitches: list[PitchAggregated]) -> bool:
    """シュート回転: FB HB が制御不能な利き手側方向へ 12インチ以上。"""
    ff = next((p for p in pitches if p.pitch_type in ("FF", "FA")), None)
    if ff is None:
        return False
    return abs(ff.horizontal_break) >= RED_SHOOT_HB_MIN
