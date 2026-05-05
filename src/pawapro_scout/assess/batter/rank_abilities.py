"""
assess/batter/rank_abilities.py
野手のランク制能力 (7種) を査定する。

能力名       指標                               ランク範囲
ケガしにくさ  出場試合数                          金/S/A/B/C/D/E/F/G
走塁         Baserunning Run Value (累積)        金/S/A/B/C/D/E/F/G
盗塁         SB数 + 成功率                       金/S/A/B/C/D/E/F/G
チャンス     RISP打率 - 通常打率 (差分)           金/S/A/B/C/D/E/F/G
対左投手     vs LHP wOBA - vs RHP wOBA (差分)   金/S/A/B/C/D/E/F/G
送球         Fielding Run Value (Arm, 累積)      金/S/A/B/C/D/E/F/G
キャッチャー  framing_runs と blocking_runs の min 金/S/A/B/C/D/E/F/G (捕手のみ, 他は None)
"""

from __future__ import annotations

from pawapro_scout.config import (
    ARM_RV_BREAKPOINTS,
    ARM_RV_GOLD,
    BATTER_VS_LHP_BREAKPOINTS,
    BATTER_VS_LHP_GOLD_MIN,
    BASERUNNING_RV_BREAKPOINTS,
    BASERUNNING_RV_GOLD,
    CATCHER_RANK_BREAKPOINTS,
    CATCHER_RANK_GOLD,
    CHANCE_BREAKPOINTS,
    CHANCE_GOLD_MIN,
    DURABILITY_BREAKPOINTS,
    DURABILITY_GOLD_MIN,
    STEAL_A_MIN,
    STEAL_A_RATE,
    STEAL_D_RATE,
    STEAL_F_RATE,
    STEAL_GOLD_MIN,
    STEAL_GOLD_RATE,
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
        "チャンス":     _チャンス(stats),
        "対左投手":     _対左投手(stats),
        "送球":         _送球(stats),
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
    """Baserunning Run Value (累積) → グレード。データ未取得時は C。"""
    if stats.baserunning_run_value is None:
        return "C"
    rv = stats.baserunning_run_value
    if rv >= BASERUNNING_RV_GOLD:
        return "金"
    return score_to_grade(rv, BASERUNNING_RV_BREAKPOINTS)


def _盗塁(stats: BatterStats) -> str:
    """
    SB数 + 盗塁成功率 でランクを決定する。
    金: 40盗塁以上 AND 成功率 >= 90%
    A:  20盗塁以上 AND 成功率 >= 85%
    D:  成功率 ~75%
    F:  成功率 <= 60%
    """
    total = stats.sb + stats.cs
    rate = stats.sb / total if total > 0 else 0.0

    if stats.sb >= STEAL_GOLD_MIN and rate >= STEAL_GOLD_RATE:
        return "金"
    if stats.sb >= STEAL_A_MIN and rate >= STEAL_A_RATE:
        return "A"
    # 成功率のみでB〜G を決定
    if rate >= 0.85:
        return "B"
    if rate >= 0.80:
        return "C"
    if rate >= STEAL_D_RATE:
        return "D"
    if rate >= 0.65:
        return "E"
    if rate >= STEAL_F_RATE:
        return "F"
    return "G"


def _チャンス(stats: BatterStats) -> str:
    """
    RISP打率 - 通常打率 → グレード。差が正 = 得点圏で強い。
    金: diff >= 0.080 / G: diff < -0.060 (旧チャンス× 相当)
    データ未取得 (0.0) の場合は C を返す。
    """
    if stats.risp_avg == 0.0 or stats.season_avg == 0.0:
        return "C"
    diff = stats.risp_avg - stats.season_avg
    if diff >= CHANCE_GOLD_MIN:
        return "金"
    return score_to_grade(diff, CHANCE_BREAKPOINTS)


def _対左投手(stats: BatterStats) -> str:
    """
    vs LHP wOBA - vs RHP wOBA → グレード。差が正 = 左投手得意。
    金: diff >= 0.100
    """
    if stats.vs_lhp_woba == 0.0 or stats.vs_rhp_woba == 0.0:
        return "C"
    diff = stats.vs_lhp_woba - stats.vs_rhp_woba
    if diff >= BATTER_VS_LHP_GOLD_MIN:
        return "金"
    return score_to_grade(diff, BATTER_VS_LHP_BREAKPOINTS)


def _送球(stats: BatterStats) -> str:
    """
    Fielding Run Value (Arm, 累積) → グレード。
    arm_run_value 未取得時は C を返す。
    """
    if stats.arm_run_value is None:
        return "C"
    rv = stats.arm_run_value
    if rv >= ARM_RV_GOLD:
        return "金"
    return score_to_grade(rv, ARM_RV_BREAKPOINTS)


def _キャッチャー(stats: BatterStats) -> str:
    """
    捕手: framing_runs と blocking_runs の min (両方の水準が求められる)。
    どちらかが None の場合は framing のみで判定。
    """
    framing = stats.framing_runs
    blocking = stats.blocking_runs

    if framing is None:
        return "C"

    # 両指標あれば min を使用
    effective = min(framing, blocking) if blocking is not None else framing

    if effective >= CATCHER_RANK_GOLD:
        return "金"
    return score_to_grade(effective, CATCHER_RANK_BREAKPOINTS)
