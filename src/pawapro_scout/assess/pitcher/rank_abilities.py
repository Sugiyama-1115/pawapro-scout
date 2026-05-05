"""
assess/pitcher/rank_abilities.py
投手のランク制能力 (6種) を査定する。

能力名       指標                         ランク範囲
打たれ強さ   LOB% (残塁率)               金/S/A/B/C/D/E/F/G
回復         IP (先発) / G (救援)         金/S/A/B/C/D/E/F/G
クイック     被盗塁成功率 (低いほど良い)  金/S/A/B/C/D/E/F/G
対ピンチ     RISP xwOBA vs 通常 xwOBA    金/A/B/C/D/E/F/G
対左打者     vs LHP xwOBA vs vs RHP      金/S/A/B/C/D/E/F/G
ノビ         4seam IVB (インチ)           金/S/A/B/C/D/E/F/G
"""

from __future__ import annotations

from pawapro_scout.config import (
    LOB_NOBITARESOSA_BREAKPOINTS,
    LOB_NOBITARESOSA_GOLD,
    NOBI_IVB_BREAKPOINTS,
    NOBI_IVB_GOLD,
    QUICK_CS_RATE_BREAKPOINTS,
    QUICK_GOLD_CS_RATE,
    RECOVERY_BREAKPOINTS_G,
    RECOVERY_BREAKPOINTS_IP,
    RECOVERY_GOLD_G,
    RECOVERY_GOLD_IP,
    VS_LHP_PITCHER_XWOBA_GOLD,
    score_to_grade,
)
from pawapro_scout.models import PitchAggregated, PitcherStats

# 先発/救援の境界
_SP_THRESHOLD_RATIO = 0.5

# 対ピンチ / xwOBA 差 → グレード (差分が負ほど良い)
# 金(強心臓): diff <= -0.060 / A: <= -0.040 / D: <= 0.010 / F: <= 0.040
_CLUTCH_BREAKPOINTS = [
    (-0.060, "金"),
    (-0.040, "A"),
    (-0.020, "B"),
    (-0.005, "C"),
    ( 0.010, "D"),
    ( 0.025, "E"),
    ( 0.040, "F"),
]

# 対左打者 差分 → グレード (vs_lhp - vs_rhp, 負が良い)
# 金は絶対値 (vs_lhp_xwoba <= 0.230) で別判定
_VS_LHP_PITCHER_BREAKPOINTS = [
    (-0.060, "S"),
    (-0.040, "A"),
    (-0.020, "B"),
    (-0.005, "C"),
    ( 0.015, "D"),
    ( 0.030, "E"),
    ( 0.040, "F"),
]


def assess_rank_abilities(stats: PitcherStats) -> dict[str, str | None]:
    """PitcherStats から6種のランク制能力を返す。"""
    return {
        "打たれ強さ": _打たれ強さ(stats),
        "回復":       _回復(stats),
        "クイック":   _クイック(stats),
        "対ピンチ":   _対ピンチ(stats),
        "対左打者":   _対左打者(stats),
        "ノビ":       _ノビ(stats),
    }


# ──────────────────────────────────────────────
# 各能力の査定関数
# ──────────────────────────────────────────────

def _打たれ強さ(stats: PitcherStats) -> str:
    """
    LOB% (残塁率) → グレード。高いほど良い。
    金特（不屈の魂）: LOB% >= 85%
    """
    lob = stats.lob_percent
    if lob <= 0.0:
        return "C"
    if lob >= LOB_NOBITARESOSA_GOLD:
        return "金"
    return score_to_grade(lob, LOB_NOBITARESOSA_BREAKPOINTS)


def _回復(stats: PitcherStats) -> str:
    """
    先発: 投球回 (IP) / 救援: 登板数 (G) → グレード。
    金特（ガソリンタンク）: IP >= 210 or G >= 80
    """
    is_starter = stats.games > 0 and (stats.games_started / stats.games) >= _SP_THRESHOLD_RATIO

    if is_starter:
        ip = stats.ip
        if ip >= RECOVERY_GOLD_IP:
            return "金"
        return score_to_grade(ip, [float(b) for b in RECOVERY_BREAKPOINTS_IP])
    else:
        g = stats.games
        if g >= RECOVERY_GOLD_G:
            return "金"
        return score_to_grade(float(g), [float(b) for b in RECOVERY_BREAKPOINTS_G])


def _クイック(stats: PitcherStats) -> str:
    """
    被盗塁阻止率 CS / (SB + CS) → グレード。高いほど良い。
    金特（走者釘付）: CS率 >= 60% (= 被盗塁成功率 <= 40%)
    """
    total = stats.sb_against + stats.cs_against
    if total == 0:
        return "C"
    cs_rate = stats.cs_against / total
    if cs_rate >= QUICK_GOLD_CS_RATE:
        return "金"
    return score_to_grade(cs_rate, QUICK_CS_RATE_BREAKPOINTS)


def _対ピンチ(stats: PitcherStats) -> str:
    """
    RISP xwOBA - 通常 xwOBA → グレード。差が負 (得点圏で抑える) ほど良い。
    金特（強心臓）: diff <= -0.060
    """
    if stats.season_xwoba == 0.0:
        return "C"
    diff = stats.risp_xwoba - stats.season_xwoba
    return _xwoba_diff_to_grade(diff, _CLUTCH_BREAKPOINTS)


def _対左打者(stats: PitcherStats) -> str:
    """
    vs LHP xwOBA - vs RHP xwOBA → グレード。差が負 (左打者を抑える) ほど良い。
    金特（左キラー）: vs LHP xwOBA <= 0.230 (絶対閾値)
    """
    if stats.vs_lhp_xwoba <= 0.0 or stats.vs_rhp_xwoba <= 0.0:
        return "C"
    if stats.vs_lhp_xwoba <= VS_LHP_PITCHER_XWOBA_GOLD:
        return "金"
    diff = stats.vs_lhp_xwoba - stats.vs_rhp_xwoba
    return _xwoba_diff_to_grade(diff, _VS_LHP_PITCHER_BREAKPOINTS)


def _ノビ(stats: PitcherStats) -> str:
    """
    4シームの Induced Vertical Break (IVB, インチ) → グレード。高いほど良い。
    金特（怪童）: IVB >= 20インチ
    """
    ivb = _get_4seam_ivb(stats.pitches)
    if ivb is None:
        return "C"
    if ivb >= NOBI_IVB_GOLD:
        return "金"
    return score_to_grade(ivb, NOBI_IVB_BREAKPOINTS)


# ──────────────────────────────────────────────
# 内部ユーティリティ
# ──────────────────────────────────────────────

def _xwoba_diff_to_grade(diff: float, breakpoints: list[tuple[float, str]]) -> str:
    """xwOBA 差分 → グレード (breakpoints は (閾値, グレード) のリスト, 差が小さいほど良い)。"""
    for threshold, grade in breakpoints:
        if diff <= threshold:
            return grade
    return "G"


def _get_4seam_ivb(pitches: list[PitchAggregated]) -> float | None:
    """4シーム (FF/FA) の IVB を返す。存在しない場合は None。"""
    ff = next((p for p in pitches if p.pitch_type in ("FF", "FA")), None)
    if ff is None:
        return None
    return abs(ff.induced_vertical_break)
