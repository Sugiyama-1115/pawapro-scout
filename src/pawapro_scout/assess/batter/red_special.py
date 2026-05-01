"""
assess/batter/red_special.py
野手の赤特殊能力（マイナス能力）を査定する。

赤特        判定指標
扇風機      K% >= 33%  (三振より重い上位互換)
三振        27% <= K% < 33%
チャンス×   RISP打率 - 通常打率 <= -0.060
"""

from __future__ import annotations

from pawapro_scout.config import (
    RED_CHANCE_X_AVG_DIFF,
    RED_FURI_K_PCT_MIN,
    RED_K_PCT_MIN,
)
from pawapro_scout.models import BatterStats


def assess_red_special(stats: BatterStats) -> list[str]:
    """BatterStats から付与される赤特リストを返す。"""
    result: list[str] = []

    # 扇風機と三振は排他。K% が高い方（扇風機）を優先
    if _is_furikun(stats):
        result.append("扇風機")
    elif _is_sansen(stats):
        result.append("三振")

    if _is_chance_batsu(stats):
        result.append("チャンス×")

    return result


# ──────────────────────────────────────────────
# 各赤特の判定
# ──────────────────────────────────────────────

def _is_furikun(stats: BatterStats) -> bool:
    """扇風機: K% >= 33%。三振より重い。"""
    return stats.k_percent >= RED_FURI_K_PCT_MIN


def _is_sansen(stats: BatterStats) -> bool:
    """三振: 27% <= K% < 33%。"""
    return RED_K_PCT_MIN <= stats.k_percent < RED_FURI_K_PCT_MIN


def _is_chance_batsu(stats: BatterStats) -> bool:
    """チャンス×: RISP打率 - 通常打率 <= -0.060。"""
    if stats.season_avg == 0.0 or stats.risp_avg == 0.0:
        return False
    return (stats.risp_avg - stats.season_avg) <= RED_CHANCE_X_AVG_DIFF
