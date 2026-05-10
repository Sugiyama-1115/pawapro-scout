"""
assess/pitcher/basic.py
投手の基礎能力（球速 / コントロール / スタミナ）を査定する。
"""

from __future__ import annotations

from pawapro_scout.config import (
    CONTROL_BREAKPOINTS,
    STAMINA_PITCHERS_BREAKPOINTS,
    score_to_grade,
)
from pawapro_scout.models import PitcherBasic, PitcherStats


def assess_basic(stats: PitcherStats) -> PitcherBasic:
    """PitcherStats から PitcherBasic を生成する。"""
    return PitcherBasic(
        球速=_assess_velocity(stats.max_velocity_mph),
        コントロール=_assess_control(stats.zone_percent, stats.bb_percent),
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

def _assess_control(zone_pct: float, bb_pct: float) -> str:
    """
    指標値 = Zone% + (15 - BB%) で算出した複合指標でランクを決定する。
    Zone%とBB%が未取得 (0.0) の場合は BB% のみで暫定評価する。
    breakpoints (降順): [65, 60, 55, 50, 45, 40, 35]
    """
    if zone_pct > 0.0:
        score = zone_pct + (15.0 - bb_pct)
    else:
        # Zone% 未取得時のフォールバック: BB% 逆変換
        score = (15.0 - bb_pct) + 50.0  # Zone% を平均 50% と仮定
    return score_to_grade(score, CONTROL_BREAKPOINTS)


# ──────────────────────────────────────────────
# スタミナ
# ──────────────────────────────────────────────

def _assess_stamina(stats: PitcherStats) -> str:
    """
    1試合あたりの平均投球数 (pitch_count / p_game) でグレード判定。
    先発・救援を問わず統一基準で評価する。
    データなしは C をデフォルトとする。
    """
    avg_pitches = stats.avg_pitches_per_game
    if avg_pitches is None or avg_pitches <= 0:
        return "C"
    return score_to_grade(float(avg_pitches), STAMINA_PITCHERS_BREAKPOINTS)
