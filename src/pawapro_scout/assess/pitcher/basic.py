"""
assess/pitcher/basic.py
投手の基礎能力（球速 / コントロール / スタミナ）を査定する。
"""

from __future__ import annotations

from pawapro_scout.config import (
    CONTROL_BREAKPOINTS,
    GRADES,
    STAMINA_SP_BREAKPOINTS,
    score_to_grade,
)
from pawapro_scout.models import PitcherBasic, PitcherStats

# 救援投手スタミナ: 登板ゲーム数 基準 (先発除く)
_STAMINA_RP_BREAKPOINTS = [65.0, 60.0, 55.0, 50.0, 40.0, 30.0, 15.0]

# 先発/救援の境界: GS が G の半数以上なら先発
_SP_THRESHOLD_RATIO = 0.5


def assess_basic(stats: PitcherStats) -> PitcherBasic:
    """PitcherStats から PitcherBasic を生成する。"""
    return PitcherBasic(
        球速=_assess_velocity(stats.max_velocity_mph),
        コントロール=_assess_control(stats.bb_percent),
        スタミナ=_assess_stamina(stats),
    )


# ──────────────────────────────────────────────
# 球速
# ──────────────────────────────────────────────

def _assess_velocity(mph: float) -> int:
    """mph → km/h に変換して返す (四捨五入)。"""
    return round(mph * 1.60934)


# ──────────────────────────────────────────────
# コントロール
# ──────────────────────────────────────────────

def _assess_control(bb_pct: float) -> str:
    """
    BB% が小さいほど良い → CONTROL_BREAKPOINTS (昇順) と比較して返す。
    breakpoints: [3.5, 5.0, 6.6, 8.6, 10.6, 12.6, 14.6]
    """
    for threshold, grade in zip(CONTROL_BREAKPOINTS, GRADES):
        if bb_pct <= threshold:
            return grade
    return "G"


# ──────────────────────────────────────────────
# スタミナ
# ──────────────────────────────────────────────

def _assess_stamina(stats: PitcherStats) -> str:
    """先発 / 救援を判定してスタミナグレードを返す。"""
    is_starter = _is_starter(stats)

    if is_starter:
        return _stamina_sp(stats.avg_pitches_per_game)
    else:
        return _stamina_rp(stats.games)


def _is_starter(stats: PitcherStats) -> bool:
    """GS / G の比率で先発か救援かを判定する。"""
    if stats.games == 0:
        return False
    return (stats.games_started / stats.games) >= _SP_THRESHOLD_RATIO


def _stamina_sp(avg_pitches: float | None) -> str:
    """先発: 平均投球数 → グレード。データがない場合は C を返す。"""
    if avg_pitches is None or avg_pitches <= 0:
        return "C"
    return score_to_grade(avg_pitches, STAMINA_SP_BREAKPOINTS)


def _stamina_rp(games: int) -> str:
    """救援: 登板ゲーム数 → グレード。"""
    return score_to_grade(float(games), _STAMINA_RP_BREAKPOINTS)
