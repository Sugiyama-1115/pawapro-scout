"""
assess/pitcher/red_special.py
投手の赤特殊能力（マイナス能力）を査定する。

赤特               判定指標
四球               bb_percent >= 11%
軽い球             hard_hit_percent >= 45%
抜け球             release_stddev >= 1.0in
スロースターター   inning1_xwoba - season_xwoba >= +0.050
対ランナー×        risp_xwoba - season_xwoba >= +0.030
"""

from __future__ import annotations

from pawapro_scout.config import (
    RED_BB_PCT_MIN,
    RED_HARD_HIT_MIN,
    RED_ON_RUNNER_BAD,
    RED_RELEASE_STDDEV_BAD,
    RED_SLOW_START_XWOBA,
)
from pawapro_scout.models import PitcherStats


def assess_red_special(stats: PitcherStats) -> list[str]:
    """PitcherStats から付与される赤特リストを返す。"""
    result: list[str] = []

    if _is_shikyu(stats):
        result.append("四球")

    if _is_karui_tama(stats):
        result.append("軽い球")

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
