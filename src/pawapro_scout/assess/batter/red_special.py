"""
assess/batter/red_special.py
野手の赤特殊能力（マイナス能力）を査定する。

赤特        判定指標
扇風機      K% >= 33%  (三振より重い上位互換)
三振        27% <= K% < 33%
エラー      Fielding Run Value (Error) <= -5
併殺        Sprint Speed <= 26.0 ft/sec AND GIDP >= 15
ムード✕     WPA <= -3.0

※ チャンス× はランク制「チャンス」のFランクに統合されたため削除
"""

from __future__ import annotations

from pawapro_scout.config import (
    RED_ERROR_RV_MAX,
    RED_FURI_K_PCT_MIN,
    RED_GDP_MIN,
    RED_GDP_SPEED_MAX,
    RED_K_PCT_MIN,
    RED_MOOD_WPA_MAX,
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

    if _is_error(stats):
        result.append("エラー")

    if _is_heisatsu(stats):
        result.append("併殺")

    if _is_mood_batsu(stats):
        result.append("ムード✕")

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


def _is_error(stats: BatterStats) -> bool:
    """エラー: Fielding Run Value (Error) <= -5。"""
    if stats.error_run_value is None:
        return False
    return stats.error_run_value <= RED_ERROR_RV_MAX


def _is_heisatsu(stats: BatterStats) -> bool:
    """併殺: Sprint Speed <= 26.0 AND GIDP >= 15。"""
    return stats.sprint_speed <= RED_GDP_SPEED_MAX and stats.gdp >= RED_GDP_MIN


def _is_mood_batsu(stats: BatterStats) -> bool:
    """ムード✕: WPA <= -3.0。"""
    return stats.wpa <= RED_MOOD_WPA_MAX
