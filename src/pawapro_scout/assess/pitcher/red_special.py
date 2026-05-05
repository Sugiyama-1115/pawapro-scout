"""
assess/pitcher/red_special.py
投手の赤特殊能力（マイナス能力）を査定する。

赤特               判定指標
四球               bb_percent >= 11%
軽い球             hard_hit_percent >= 45%
一発               hr_per_9 >= 1.5
シュート回転       4seam HB (利き手側) >= 12in
短気               lob_percent <= 65%
負け運             run_support <= 3.5
抜け球             release_stddev >= 1.0in
スロースターター   inning1_xwoba - season_xwoba >= +0.050
対ランナー×        risp_xwoba - season_xwoba >= +0.030
"""

from __future__ import annotations

from pawapro_scout.config import (
    RED_BB_PCT_MIN,
    RED_HARD_HIT_MIN,
    RED_HR_PER_9_MIN,
    RED_LOB_SHORT_MAX,
    RED_ON_RUNNER_BAD,
    RED_RELEASE_STDDEV_BAD,
    RED_RUN_SUPPORT_MAX,
    RED_SHOOT_HB_MIN,
    RED_SLOW_START_XWOBA,
)
from pawapro_scout.models import PitchAggregated, PitcherStats


def assess_red_special(stats: PitcherStats) -> list[str]:
    """PitcherStats から付与される赤特リストを返す。"""
    result: list[str] = []

    if _is_shikyu(stats):
        result.append("四球")

    if _is_karui_tama(stats):
        result.append("軽い球")

    if _is_ippatsu(stats):
        result.append("一発")

    if _is_shoot_rotation(stats.pitches):
        result.append("シュート回転")

    if _is_tankiki(stats):
        result.append("短気")

    if _is_makeun(stats):
        result.append("負け運")

    if _is_nukeball(stats):
        result.append("抜け球")

    if _is_slow_starter(stats):
        result.append("スロースターター")

    if _is_runner_bad(stats):
        result.append("対ランナー×")

    return result


# ──────────────────────────────────────────────
# 各赤特の判定
# ──────────────────────────────────────────────

def _is_shikyu(stats: PitcherStats) -> bool:
    """四球: BB% >= 11%。"""
    return stats.bb_percent >= RED_BB_PCT_MIN


def _is_karui_tama(stats: PitcherStats) -> bool:
    """軽い球: 被Hard Hit% >= 45% (打者に強い打球を打たれやすい)。"""
    return stats.hard_hit_percent >= RED_HARD_HIT_MIN


def _is_ippatsu(stats: PitcherStats) -> bool:
    """一発: HR/9 >= 1.5。"""
    return stats.hr_per_9 >= RED_HR_PER_9_MIN


def _is_shoot_rotation(pitches: list[PitchAggregated]) -> bool:
    """
    シュート回転: 4seam (FF/FA) の水平変化が利き手側に 12in 以上。
    horizontal_break の絶対値で判定 (ナチュラルシュートの閾値を超えた重症版)。
    """
    ff = next((p for p in pitches if p.pitch_type in ("FF", "FA")), None)
    if ff is None:
        return False
    return abs(ff.horizontal_break) >= RED_SHOOT_HB_MIN


def _is_tankiki(stats: PitcherStats) -> bool:
    """短気: LOB% <= 65% (粘れずランナーを返してしまう)。"""
    if stats.lob_percent <= 0.0:
        return False
    return stats.lob_percent <= RED_LOB_SHORT_MAX


def _is_makeun(stats: PitcherStats) -> bool:
    """負け運: Run Support <= 3.5。"""
    if stats.run_support is None:
        return False
    return stats.run_support <= RED_RUN_SUPPORT_MAX


def _is_nukeball(stats: PitcherStats) -> bool:
    """抜け球: リリースポイントの標準偏差 (x, z 平均) >= 1.0in。"""
    avg_std = (stats.release_x_stddev + stats.release_z_stddev) / 2.0
    return avg_std >= RED_RELEASE_STDDEV_BAD


def _is_slow_starter(stats: PitcherStats) -> bool:
    """スロースターター: 1回 xwOBA - 通常 xwOBA >= +0.050 (立ち上がりが悪い)。"""
    if stats.season_xwoba == 0.0 or stats.inning1_xwoba == 0.0:
        return False
    return (stats.inning1_xwoba - stats.season_xwoba) >= RED_SLOW_START_XWOBA


def _is_runner_bad(stats: PitcherStats) -> bool:
    """対ランナー×: RISP xwOBA - 通常 xwOBA >= +0.030 (得点圏で打たれやすい)。"""
    if stats.season_xwoba == 0.0 or stats.risp_xwoba == 0.0:
        return False
    return (stats.risp_xwoba - stats.season_xwoba) >= RED_ON_RUNNER_BAD
