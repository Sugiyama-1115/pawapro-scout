"""
assess/pitcher/pitch_classifier.py
Statcast pitch_type コードから パワプロ球種名 と 変化量(1-7) を決定する。

分類アルゴリズムは計画書の通り。
HB (horizontal_break) は符号付きインチ (pfx_x * 12)。
閾値の比較には abs(HB) を使う。
"""

from __future__ import annotations

from pawapro_scout.config import (
    CH_CIRCLE_DHB_MIN,
    CUTTER_BALL_HB_MAX,
    RV_HENKA_BONUS_THRESHOLD,
    RV_HENKA_PENALTY_THRESHOLD,
    SINKER_HS_DV_MAX,
    SINKER_HS_HB_MIN,
    SINKER_TS_DV_MAX,
    SINKER_TS_HB_MAX,
    SLIDER_H_DV_MAX,
    SLIDER_SWEEPER_HB_MIN,
    SLIDER_VH_HB_MAX,
    SPLITTER_SFF_DV_MAX,
    WHIFF_TO_HENKA_BREAKPOINTS,
    WHIFF_TO_HENKA_VALUES,
)
from pawapro_scout.models import PitchAggregated, PitchEntry


def classify_pitches(pitches: list[PitchAggregated]) -> list[PitchEntry]:
    """
    PitchAggregated のリストを受け取り、PitchEntry (名称 + 変化量) のリストを返す。
    unknown / eephus は除外する。
    """
    results: list[PitchEntry] = []
    for p in pitches:
        name = _classify(p)
        if name in ("", "不明"):
            continue
        henka = _calc_henka(p)
        results.append(PitchEntry(名称=name, 変化量=henka))
    return results


# ──────────────────────────────────────────────
# 球種名の分類
# ──────────────────────────────────────────────

def _classify(p: PitchAggregated) -> str:
    """pitch_type コードから日本語球種名を返す。"""
    pt = p.pitch_type.upper()
    hb  = abs(p.horizontal_break)         # 符号なし水平変化 (inches)
    ivb = p.induced_vertical_break         # 垂直変化 (signed, inches)
    dv  = p.delta_v_from_fastball          # FF との速度差 (mph, 正 = 遅い)

    if pt in ("FF", "FA"):
        return "ストレート"

    if pt in ("SL", "ST", "SV"):
        return _classify_slider(hb, ivb, dv)

    if pt in ("SI", "FT"):
        return _classify_sinker(hb, dv)

    if pt in ("FS", "FO"):
        return "SFF" if dv < SPLITTER_SFF_DV_MAX else "フォーク"

    if pt == "CH":
        return "サークルチェンジ" if hb >= CH_CIRCLE_DHB_MIN else "チェンジアップ"

    if pt == "FC":
        return "カットボール" if hb <= CUTTER_BALL_HB_MAX else "Hスライダー"

    if pt in ("CU", "CS", "KC"):
        return "カーブ"

    if pt == "KN":
        return "ナックル"

    # EP / SC / UN / PO 等
    return "不明"


def _classify_slider(hb: float, ivb: float, dv: float) -> str:
    """スライダー系 (SL/ST/SV) を細分類する。"""
    if hb < SLIDER_VH_HB_MAX:
        return "Vスライダー"
    if hb >= SLIDER_SWEEPER_HB_MIN and hb > abs(ivb):
        return "スイーパー"
    if dv <= SLIDER_H_DV_MAX:
        return "Hスライダー"
    return "スライダー"


def _classify_sinker(hb: float, dv: float) -> str:
    """シンカー系 (SI/FT) を細分類する。"""
    if dv <= SINKER_TS_DV_MAX and hb < SINKER_TS_HB_MAX:
        return "ツーシーム"
    if dv <= SINKER_HS_DV_MAX and hb >= SINKER_HS_HB_MIN:
        return "高速シンカー"
    return "シンカー"


# ──────────────────────────────────────────────
# 変化量 (1-7) の計算
# ──────────────────────────────────────────────

def _calc_henka(p: PitchAggregated) -> int:
    """
    Whiff% をベースに変化量を決定し、RV/100 で ±1 補正する。
    結果は 1〜7 にクランプする。
    """
    # Whiff% → ベース変化量
    base = _whiff_to_base(p.whiff_pct)

    # RV/100 補正
    if p.rv_per_100 < RV_HENKA_BONUS_THRESHOLD:
        base += 1
    elif p.rv_per_100 > RV_HENKA_PENALTY_THRESHOLD:
        base -= 1

    return max(1, min(7, base))


def _whiff_to_base(whiff_pct: float) -> int:
    """Whiff% からベース変化量 (1/3/5/7) を返す。"""
    for threshold, value in zip(WHIFF_TO_HENKA_BREAKPOINTS, WHIFF_TO_HENKA_VALUES):
        if whiff_pct >= threshold:
            return value
    # whiff_pct < 15 → base=1 (WHIFF_TO_HENKA_VALUES[-1] = 1)
    return WHIFF_TO_HENKA_VALUES[-1]
