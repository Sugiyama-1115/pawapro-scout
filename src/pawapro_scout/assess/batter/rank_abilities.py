"""
assess/batter/rank_abilities.py
野手のランク制能力 (7種) を査定する。

能力名       指標                         ランク範囲
ケガしにくさ  出場試合数                    金/S/A/B/C/D/E/F/G
走塁         xbt_percent (XBT%)           S/A/B/C/D/E/F/G
盗塁         SB 数                         金/S/A/B/C/D/E/F/G
対左投手     vs_lhp_woba - vs_rhp_woba    金/S/A/B/C/D/E/F/G
対変化球     K% (低いほど良い)             S/A/B/C/D/E/F/G
送球         arm_strength_mph (位置依存)   S/A/B/C/D/E/F/G
キャッチャー  framing_runs                 S/A/B/C/D/E/F/G (捕手のみ, 他は None)
"""

from __future__ import annotations

from pawapro_scout.config import (
    ARM_IF_BREAKPOINTS,
    ARM_OF_BREAKPOINTS,
    BATTER_VS_LHP_BREAKPOINTS,
    BATTER_VS_LHP_GOLD_MIN,
    BASERUNNING_BREAKPOINTS,
    CATCHER_RANK_BREAKPOINTS,
    DURABILITY_BREAKPOINTS,
    DURABILITY_GOLD_MIN,
    STEAL_BREAKPOINTS,
    STEAL_GOLD_MIN,
    VS_BREAKING_BREAKPOINTS,
    score_to_grade,
)
from pawapro_scout.models import BatterStats

_OF_POSITIONS = {"LF", "CF", "RF", "OF"}
_CATCHER = "C"


def assess_rank_abilities(stats: BatterStats, position: str = "OF") -> dict[str, str | None]:
    """BatterStats から7種のランク制能力を返す。"""
    pos = position.upper()
    return {
        "ケガしにくさ": _ケガしにくさ(stats),
        "走塁":         _走塁(stats),
        "盗塁":         _盗塁(stats),
        "対左投手":     _対左投手(stats),
        "対変化球":     _対変化球(stats),
        "送球":         _送球(stats, pos),
        "キャッチャー": _キャッチャー(stats) if pos == _CATCHER else None,
    }


# ──────────────────────────────────────────────
# 各能力の査定関数
# ──────────────────────────────────────────────

def _ケガしにくさ(stats: BatterStats) -> str:
    if stats.games >= DURABILITY_GOLD_MIN:
        return "金"
    return score_to_grade(float(stats.games), [float(b) for b in DURABILITY_BREAKPOINTS])


def _走塁(stats: BatterStats) -> str:
    return score_to_grade(stats.xbt_percent, BASERUNNING_BREAKPOINTS)


def _盗塁(stats: BatterStats) -> str:
    if stats.sb >= STEAL_GOLD_MIN:
        return "金"
    return score_to_grade(float(stats.sb), [float(b) for b in STEAL_BREAKPOINTS])


def _対左投手(stats: BatterStats) -> str:
    if stats.vs_lhp_woba == 0.0 or stats.vs_rhp_woba == 0.0:
        return "C"
    diff = stats.vs_lhp_woba - stats.vs_rhp_woba
    if diff >= BATTER_VS_LHP_GOLD_MIN:
        return "金"
    return score_to_grade(diff, BATTER_VS_LHP_BREAKPOINTS)


def _対変化球(stats: BatterStats) -> str:
    """K% が低いほど良い → 昇順ブレークポイントで判定。"""
    k = stats.k_percent
    for threshold, grade in zip(VS_BREAKING_BREAKPOINTS, ["S", "A", "B", "C", "D", "E", "F"]):
        if k <= threshold:
            return grade
    return "G"


def _送球(stats: BatterStats, position: str) -> str:
    if stats.arm_strength_mph is None:
        return "C"
    bp = ARM_OF_BREAKPOINTS if position in _OF_POSITIONS else ARM_IF_BREAKPOINTS
    return score_to_grade(stats.arm_strength_mph, bp)


def _キャッチャー(stats: BatterStats) -> str:
    """捕手のフレーミング → グレード。データなしは C。"""
    if stats.framing_runs is None:
        return "C"
    return score_to_grade(stats.framing_runs, CATCHER_RANK_BREAKPOINTS)
