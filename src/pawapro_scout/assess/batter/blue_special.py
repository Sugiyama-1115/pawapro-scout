"""
assess/batter/blue_special.py
野手の青特殊能力を査定する。

青特            判定指標
チャンス◯       RISP打率 - 通常打率 >= +0.050
対左投手◯       vs LHP wOBA - vs RHP wOBA >= +0.040
プルヒッター    引っ張り方向HR% >= 60%
広角打法        逆方向HR >= 5本
固め打ち        1試合3安打以上の試合 >= 15試合
内野安打◯       ボルト (30ft/sec超) >= 10回
"""

from __future__ import annotations

from pawapro_scout.config import (
    BOLT_MIN_FOR_INFIELD,
    CHANCE_O_RISP_DIFF,
    MULTI_HIT_GAME_MIN,
    OPPO_HR_MIN,
    PULL_HR_PCT_MIN,
    VS_LHP_O_WOBA_DIFF,
)
from pawapro_scout.models import BatterStats


def assess_blue_special(stats: BatterStats) -> list[str]:
    """BatterStats から獲得する青特リストを返す。"""
    result: list[str] = []

    if _is_chance_maru(stats):
        result.append("チャンス◯")

    if _is_vs_lhp_maru(stats):
        result.append("対左投手◯")

    if _is_pull_hitter(stats):
        result.append("プルヒッター")

    if _is_koukauku(stats):
        result.append("広角打法")

    if _is_katamari_uchi(stats):
        result.append("固め打ち")

    if _is_infield_hit_maru(stats):
        result.append("内野安打◯")

    return result


# ──────────────────────────────────────────────
# 各青特の判定
# ──────────────────────────────────────────────

def _is_chance_maru(stats: BatterStats) -> bool:
    """チャンス◯: RISP打率 - 通常打率 >= +0.050。"""
    if stats.season_avg == 0.0 or stats.risp_avg == 0.0:
        return False
    return (stats.risp_avg - stats.season_avg) >= CHANCE_O_RISP_DIFF


def _is_vs_lhp_maru(stats: BatterStats) -> bool:
    """対左投手◯: vs LHP wOBA - vs RHP wOBA >= +0.040。"""
    if stats.vs_lhp_woba == 0.0 or stats.vs_rhp_woba == 0.0:
        return False
    return (stats.vs_lhp_woba - stats.vs_rhp_woba) >= VS_LHP_O_WOBA_DIFF


def _is_pull_hitter(stats: BatterStats) -> bool:
    """プルヒッター: 引っ張り方向HR% >= 60%。"""
    return stats.pull_hr_pct >= PULL_HR_PCT_MIN


def _is_koukauku(stats: BatterStats) -> bool:
    """広角打法: 逆方向HR >= 5本。"""
    return stats.oppo_hr_count >= OPPO_HR_MIN


def _is_katamari_uchi(stats: BatterStats) -> bool:
    """固め打ち: 1試合3安打以上の試合 >= 15試合。"""
    return stats.multi_hit_game_count >= MULTI_HIT_GAME_MIN


def _is_infield_hit_maru(stats: BatterStats) -> bool:
    """内野安打◯: ボルト (30 ft/sec超) >= 10回。"""
    return stats.bolts >= BOLT_MIN_FOR_INFIELD
