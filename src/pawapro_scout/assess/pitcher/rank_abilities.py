"""
assess/pitcher/rank_abilities.py
投手のランク制能力 (6種) を査定する。

能力名       指標                    ランク範囲
打たれ強さ   exit_vel_percentile     金/S/A/B/C/D/E/F/G
回復         ir_stranded_pct         S/A/B/C/D/E/F/G
クイック     被盗塁阻止率            S/A/B/C/D/E/F/G
対ピンチ     risp_xwoba vs 通常      金/S/A/B/C/D/E/F/G
対左打者     vs_lhp vs 通常 xwOBA   金/S/A/B/C/D/E/F/G
ノビ         k_percentile            金/S/A/B/C/D/E/F/G
"""

from __future__ import annotations

from pawapro_scout.config import GOLD_PERCENTILE, percentile_to_grade
from pawapro_scout.models import PitcherStats

# 金ランク付与の xwOBA 改善幅
_GOLD_XWOBA_DIFF = -0.080
# 金ランク付与の CS率
_GOLD_CS_RATE = 0.45

# 対ピンチ / 対左打者: xwOBA 差 → グレード (差分が負ほど良い)
_CLUTCH_BREAKPOINTS = [
    (-0.060, "金"),
    (-0.040, "S"),
    (-0.020, "A"),
    ( 0.010, "B"),
    ( 0.020, "C"),
    ( 0.040, "D"),
    ( 0.060, "E"),
    ( 0.080, "F"),
]

# 回復 (IR-S%): 高いほど良い
_IR_STRAND_BREAKPOINTS = [90.0, 85.0, 80.0, 70.0, 60.0, 50.0, 40.0]

# クイック (CS率): 高いほど良い
_CS_RATE_BREAKPOINTS = [0.45, 0.35, 0.28, 0.22, 0.16, 0.10, 0.05]


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
    打球速度パーセンタイル → グレード。
    Savant では exit_vel_percentile が高い投手 = 被打球が弱い = 良い投手。
    """
    pct = stats.exit_vel_percentile
    if pct >= GOLD_PERCENTILE:
        return "金"
    return percentile_to_grade(pct)


def _回復(stats: PitcherStats) -> str:
    """
    IR-S% (Inherited Runners Stranded%) → グレード。
    データがない場合は C を返す。
    """
    if stats.ir_stranded_pct is None:
        return "C"
    from pawapro_scout.config import score_to_grade
    return score_to_grade(stats.ir_stranded_pct, _IR_STRAND_BREAKPOINTS)


def _クイック(stats: PitcherStats) -> str:
    """
    被盗塁阻止率 (CS / (SB + CS)) → グレード。
    データがない場合は C を返す。
    """
    total = stats.sb_against + stats.cs_against
    if total == 0:
        return "C"
    cs_rate = stats.cs_against / total
    if cs_rate >= _GOLD_CS_RATE:
        return "金"
    from pawapro_scout.config import score_to_grade
    return score_to_grade(cs_rate, _CS_RATE_BREAKPOINTS)


def _対ピンチ(stats: PitcherStats) -> str:
    """
    RISP xwOBA - 通常 xwOBA → グレード。
    差が負 (得点圏で抑える) ほど良い。
    """
    if stats.season_xwoba == 0.0:
        return "C"
    diff = stats.risp_xwoba - stats.season_xwoba
    return _xwoba_diff_to_grade(diff)


def _対左打者(stats: PitcherStats) -> str:
    """
    対左打者 xwOBA - 通常 xwOBA → グレード。
    差が負 (左打者を抑える) ほど良い。
    """
    if stats.season_xwoba == 0.0:
        return "C"
    diff = stats.vs_lhp_xwoba - stats.season_xwoba
    return _xwoba_diff_to_grade(diff)


def _ノビ(stats: PitcherStats) -> str:
    """
    三振パーセンタイル → グレード。
    ノビ = 直球の被空振り能力の象徴として K パーセンタイルを使用。
    """
    pct = stats.k_percentile
    if pct >= GOLD_PERCENTILE:
        return "金"
    return percentile_to_grade(pct)


# ──────────────────────────────────────────────
# 内部ユーティリティ
# ──────────────────────────────────────────────

def _xwoba_diff_to_grade(diff: float) -> str:
    """
    xwOBA 差分 (負 = 良い) をグレードに変換する。
    非常に優秀 (diff <= -0.060) → 金
    """
    for threshold, grade in _CLUTCH_BREAKPOINTS:
        if diff <= threshold:
            return grade
    return "G"
