"""
assess/pitcher/rank_abilities.py
投手のランク制能力 (6種) を r1 絶対評価基準で査定する。

| 能力名     | 判定指標                       | 金 (絶対閾値)     | A (絶対閾値) | D (標準) | F (絶対閾値) |
|-----------|--------------------------------|------------------|-------------|---------|-------------|
| 打たれ強さ | LOB% (残塁率)                  | 不屈の魂 85%以上 | 80%以上     | 72%前後 | 64%以下     |
| ノビ       | IVB (垂直ホップ量) インチ      | 怪童 21インチ以上| 19インチ以上| 16インチ| 13インチ以下|
| 対ピンチ   | ΔxwOBA (得点圏 - 通常)         | 強心臓 -.060改善 | -.040改善   | 差±.010 | +.040悪化   |
| 対左打者   | ΔxwOBA (対左 - 対右)           | 左キラー -.070改善| -.050改善   | 差±.015 | +.050悪化   |
| 回復       | G / IP                         | ガソリンタンク 80G/210IP | 70G/180IP | 50G/140IP | 30G/100IP以下 |
| クイック   | Pop Time (秒)                  | 走者釘付 1.20秒以下 | 1.25秒以下| 1.40秒前後| 1.60秒以上|

ランクは パワプロ標準の S/A/B/C/D/E/F/G の 8段階 (+金特相当の "金") で返す。
"""

from __future__ import annotations

from pawapro_scout.config import (
    # r1 仕様の絶対閾値 (新)
    PITCHER_DURABILITY_GOLD, PITCHER_DURABILITY_A, PITCHER_DURABILITY_D, PITCHER_DURABILITY_F,
    PITCHER_NOBI_GOLD, PITCHER_NOBI_A, PITCHER_NOBI_D, PITCHER_NOBI_F,
    PITCHER_CLUTCH_GOLD, PITCHER_CLUTCH_A, PITCHER_CLUTCH_D, PITCHER_CLUTCH_F,
    PITCHER_VS_LHB_GOLD, PITCHER_VS_LHB_A, PITCHER_VS_LHB_D, PITCHER_VS_LHB_F,
    PITCHER_RECOVERY_G_GOLD, PITCHER_RECOVERY_G_A, PITCHER_RECOVERY_G_D, PITCHER_RECOVERY_G_F,
    PITCHER_RECOVERY_IP_GOLD, PITCHER_RECOVERY_IP_A, PITCHER_RECOVERY_IP_D, PITCHER_RECOVERY_IP_F,
    PITCHER_QUICK_GOLD, PITCHER_QUICK_A, PITCHER_QUICK_D, PITCHER_QUICK_F,
)
from pawapro_scout.models import PitchAggregated, PitcherStats

# 先発/救援の境界
_SP_THRESHOLD_RATIO = 0.5


def assess_rank_abilities(stats: PitcherStats) -> dict[str, str | None]:
    """PitcherStats から6種のランク制能力を返す。"""
    return {
        "打たれ強さ": _打たれ強さ(stats),
        "ノビ":       _ノビ(stats),
        "対ピンチ":   _対ピンチ(stats),
        "対左打者":   _対左打者(stats),
        "回復":       _回復(stats),
        "クイック":   _クイック(stats),
    }


# ──────────────────────────────────────────────
# 高位指標 → 8段階ランク 補間関数
# ──────────────────────────────────────────────

def _to_8grade(value: float, gold: float, a: float, d: float, f: float, lower_is_better: bool = False) -> str:
    """
    4基準点 (金/A/D/F) と value から 8段階 (金/S/A/B/C/D/E/F/G) を補間する。

    - lower_is_better=False (高いほど良い): 金>A>D>F
    - lower_is_better=True (低いほど良い):  金<A<D<F

    Args:
        value: 評価対象の値
        gold/a/d/f: r1 仕様の基準点
        lower_is_better: True なら値が小さいほど良い指標

    Returns:
        グレード文字列 ("金" or "S" or "A" or "B" or "C" or "D" or "E" or "F" or "G")
    """
    # 線形補間用に閾値を構築
    # 高いほど良い: 金=gold, S=(gold+a)/2, A=a, B=(a+d)*2/3+(d/3), C=(a+d)/2, D=d, E=(d+f)/2, F=f, G以下=else
    if lower_is_better:
        if value <= gold:
            return "金"
        if value <= (gold + a) / 2:
            return "S"
        if value <= a:
            return "A"
        if value <= a + (d - a) * 0.33:
            return "B"
        if value <= a + (d - a) * 0.66:
            return "C"
        if value <= d:
            return "D"
        if value <= (d + f) / 2:
            return "E"
        if value <= f:
            return "F"
        return "G"
    else:
        if value >= gold:
            return "金"
        if value >= (gold + a) / 2:
            return "S"
        if value >= a:
            return "A"
        if value >= a + (d - a) * 0.33:
            return "B"
        if value >= a + (d - a) * 0.66:
            return "C"
        if value >= d:
            return "D"
        if value >= (d + f) / 2:
            return "E"
        if value >= f:
            return "F"
        return "G"


# ──────────────────────────────────────────────
# 各能力の査定関数
# ──────────────────────────────────────────────

def _打たれ強さ(stats: PitcherStats) -> str:
    """LOB% (残塁率) → ランク。高いほど良い。 金: >= 85%"""
    lob = stats.lob_percent
    if lob <= 0.0:
        return "C"
    return _to_8grade(
        lob,
        gold=PITCHER_DURABILITY_GOLD,
        a=PITCHER_DURABILITY_A,
        d=PITCHER_DURABILITY_D,
        f=PITCHER_DURABILITY_F,
        lower_is_better=False,
    )


def _ノビ(stats: PitcherStats) -> str:
    """4シーム IVB (インチ) → ランク。高いほど良い。 金 (怪童): >= 21in"""
    ivb = _get_4seam_ivb(stats.pitches)
    if ivb is None:
        return "C"
    return _to_8grade(
        ivb,
        gold=PITCHER_NOBI_GOLD,
        a=PITCHER_NOBI_A,
        d=PITCHER_NOBI_D,
        f=PITCHER_NOBI_F,
        lower_is_better=False,
    )


def _対ピンチ(stats: PitcherStats) -> str:
    """ΔxwOBA (得点圏 - 通常) → ランク。負ほど良い。 金 (強心臓): <= -0.060"""
    if stats.season_xwoba == 0.0 or stats.risp_xwoba == 0.0:
        return "C"
    diff = stats.risp_xwoba - stats.season_xwoba
    return _to_8grade(
        diff,
        gold=PITCHER_CLUTCH_GOLD,
        a=PITCHER_CLUTCH_A,
        d=PITCHER_CLUTCH_D,
        f=PITCHER_CLUTCH_F,
        lower_is_better=True,
    )


def _対左打者(stats: PitcherStats) -> str:
    """ΔxwOBA (対左 - 対右) → ランク。負ほど良い。 金 (左キラー): <= -0.070"""
    lhb = stats.vs_lhb_xwoba or stats.vs_lhp_xwoba
    rhb = stats.vs_rhb_xwoba or stats.vs_rhp_xwoba
    if lhb <= 0.0 or rhb <= 0.0:
        return "C"
    diff = lhb - rhb
    return _to_8grade(
        diff,
        gold=PITCHER_VS_LHB_GOLD,
        a=PITCHER_VS_LHB_A,
        d=PITCHER_VS_LHB_D,
        f=PITCHER_VS_LHB_F,
        lower_is_better=True,
    )


def _回復(stats: PitcherStats) -> str:
    """
    G または IP → ランク。多いほど良い。
    先発 (GS/G >= 0.5): IP ベース判定
    救援:              G ベース判定
    金 (ガソリンタンク): 80G or 210IP
    """
    is_starter = stats.games > 0 and (stats.games_started / stats.games) >= _SP_THRESHOLD_RATIO

    if is_starter:
        return _to_8grade(
            stats.ip,
            gold=PITCHER_RECOVERY_IP_GOLD,
            a=PITCHER_RECOVERY_IP_A,
            d=PITCHER_RECOVERY_IP_D,
            f=PITCHER_RECOVERY_IP_F,
            lower_is_better=False,
        )
    else:
        return _to_8grade(
            float(stats.games),
            gold=float(PITCHER_RECOVERY_G_GOLD),
            a=float(PITCHER_RECOVERY_G_A),
            d=float(PITCHER_RECOVERY_G_D),
            f=float(PITCHER_RECOVERY_G_F),
            lower_is_better=False,
        )


def _クイック(stats: PitcherStats) -> str:
    """Pop Time (秒) → ランク。小さいほど良い。 金 (走者釘付): <= 1.20s"""
    pop = stats.pop_time
    if pop is None or pop <= 0.0:
        return "C"
    return _to_8grade(
        pop,
        gold=PITCHER_QUICK_GOLD,
        a=PITCHER_QUICK_A,
        d=PITCHER_QUICK_D,
        f=PITCHER_QUICK_F,
        lower_is_better=True,
    )


# ──────────────────────────────────────────────
# 内部ユーティリティ
# ──────────────────────────────────────────────

def _get_4seam_ivb(pitches: list[PitchAggregated]) -> float | None:
    """4シーム (FF/FA) の IVB を返す。存在しない場合は None。"""
    ff = next((p for p in pitches if p.pitch_type in ("FF", "FA")), None)
    if ff is None:
        return None
    return abs(ff.induced_vertical_break)
