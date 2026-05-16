"""
aggregate/statcast_metrics.py

Statcast pitch-level DataFrame から、シーン別／ゾーン別／カウント別の
各種指標を計算する専門レイヤー。

このモジュールは「Statcast限定」方針で、FanGraphs / Baseball Reference に
依存していたスタッツの代替計算を提供する：

- K%, BB%, HR/9, OBP, OPS, IP 等の基本集計
- 投手の inning1/inning2/inning7plus, vs_lhb/rhb, RISP 別 xwOBA
- 野手のゾーン別 (内/外/高/低) xBA/xSLG
- カウント別 (0ストライク/2ストライク) 指標
- 球種別 whiff%, run_value
- 簡易 OAA / Arm Strength / Catcher Framing (BIP位置から推定)

すべての関数は statcast_df (pd.DataFrame) を受け取り、dict を返す。
空 DataFrame の場合はデフォルト値 (0.0 等) を返し、例外は出さない。
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 定数: イベント分類
# ──────────────────────────────────────────────

# Whiff (空振り) 判定
_WHIFF_DESC = frozenset([
    "swinging_strike", "swinging_strike_blocked",
])

# Swing (スイング) 判定
_SWING_DESC = frozenset([
    "swinging_strike", "swinging_strike_blocked",
    "foul", "foul_tip", "foul_bunt", "missed_bunt",
    "hit_into_play", "hit_into_play_score", "hit_into_play_no_out",
])

# 打席終了イベント（PA カウント用）
_PA_END_EVENTS = frozenset([
    "single", "double", "triple", "home_run",
    "strikeout", "strikeout_double_play",
    "walk", "intent_walk",
    "hit_by_pitch",
    "field_out", "force_out", "grounded_into_double_play",
    "double_play", "triple_play", "fielders_choice", "fielders_choice_out",
    "sac_fly", "sac_bunt", "sac_fly_double_play", "sac_bunt_double_play",
    "field_error", "catcher_interf",
])

# ヒットイベント
_HIT_EVENTS = frozenset(["single", "double", "triple", "home_run"])
_OUT_EVENTS = frozenset([
    "field_out", "force_out", "grounded_into_double_play",
    "double_play", "triple_play", "fielders_choice_out",
    "sac_fly_double_play", "sac_bunt_double_play",
])

# K / BB / HBP / HR
_K_EVENTS  = frozenset(["strikeout", "strikeout_double_play"])
_BB_EVENTS = frozenset(["walk", "intent_walk"])
_HBP_EVENTS = frozenset(["hit_by_pitch"])
_HR_EVENTS = frozenset(["home_run"])

# 犠打/犠飛 (PA に含めない場合があるので別管理)
_SAC_EVENTS = frozenset([
    "sac_fly", "sac_bunt", "sac_fly_double_play", "sac_bunt_double_play",
])

# 盗塁関連
_SB_EVENTS = frozenset(["stolen_base_2b", "stolen_base_3b", "stolen_base_home"])
_CS_EVENTS = frozenset(["caught_stealing_2b", "caught_stealing_3b", "caught_stealing_home"])

# ゾーン定義 (Statcast zone 1-14)
# zone 1-9 は3x3 グリッド (1=左上, 5=中央, 9=右下)
_LOW_ZONES_NUM = {7, 8, 9}        # 低め (3x3 下段)
_HIGH_ZONES_NUM = {1, 2, 3}       # 高め (3x3 上段)
_HEART_ZONE = {5}                 # ど真ん中
_SHADOW_ZONES = {11, 12, 13, 14}  # シャドウ (ボール+ストライク境界)

# 内角/外角は打者の利き手で決まる (plate_x で判定)
# 右打者: plate_x < 0 → 内角, plate_x > 0 → 外角
# 左打者: plate_x > 0 → 内角, plate_x < 0 → 外角


# ──────────────────────────────────────────────
# ユーティリティ
# ──────────────────────────────────────────────

def _safe_mean(series: pd.Series) -> float:
    """NaNを除外して平均を返す。空の場合は 0.0。"""
    if series is None or series.empty:
        return 0.0
    v = series.dropna().mean()
    return float(v) if pd.notna(v) else 0.0


def _safe_sum(series: pd.Series) -> int:
    if series is None or series.empty:
        return 0
    return int(series.fillna(0).sum())


def _is_empty(df: pd.DataFrame | None) -> bool:
    return df is None or df.empty


def _is_inside_zone(plate_x: float, stand: str) -> bool:
    """打者の利き手から内角/外角判定。内角=True, 外角=False。"""
    if pd.isna(plate_x) or pd.isna(stand):
        return False
    # 右打者: plate_x<0 が内角, 左打者: plate_x>0 が内角
    if stand == "R":
        return plate_x < 0
    elif stand == "L":
        return plate_x > 0
    return False


# ──────────────────────────────────────────────
# 基本指標計算
# ──────────────────────────────────────────────

def compute_basic_pitcher_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """
    Statcast pitch-level から投手の基本指標を計算する。

    Returns:
        dict with keys:
          k_percent, bb_percent, hr_per_9, er_per_9 (近似),
          ip, games, games_started, win_pct (近似 None),
          hard_hit_percent, avg_ev_against,
          zone_percent, edge_percent, low_zone_pct, heart_zone_pct,
          extension_ft, avg_velocity_mph, max_velocity_mph,
          pickoffs (近似 0)
    """
    out: dict[str, Any] = {
        "k_percent": 0.0,
        "bb_percent": 0.0,
        "hr_per_9": 0.0,
        "er_per_9": 0.0,
        "ip": 0.0,
        "games": 0,
        "games_started": 0,
        "win_pct": None,
        "hard_hit_percent": 0.0,
        "avg_ev_against": 0.0,
        "zone_percent": 0.0,
        "edge_percent": 0.0,
        "low_zone_pct": 0.0,
        "heart_zone_pct": 0.0,
        "extension_ft": 0.0,
        "avg_velocity_mph": 0.0,
        "max_velocity_mph": 0.0,
        "pickoffs": 0,
        "lob_percent": 0.0,
    }
    if _is_empty(df):
        return out

    # ── PA 集計 ──────────────────────────────
    ev = df["events"].dropna() if "events" in df.columns else pd.Series(dtype=object)
    pa_count = int(ev.isin(_PA_END_EVENTS).sum())
    k_count = int(ev.isin(_K_EVENTS).sum())
    bb_count = int(ev.isin(_BB_EVENTS).sum())
    hr_count = int(ev.isin(_HR_EVENTS).sum())
    pickoff_count = 0
    if "events" in df.columns:
        pickoff_count = int(df["events"].fillna("").astype(str).str.startswith("pickoff").sum())

    if pa_count > 0:
        out["k_percent"] = round(k_count / pa_count * 100, 2)
        out["bb_percent"] = round(bb_count / pa_count * 100, 2)

    # ── IP 計算 ─────────────────────────────
    # outs 集計: ストライクアウト + フィールドアウト + ダブルプレイ等
    outs = int(ev.isin(_K_EVENTS).sum())
    outs += int(ev.isin(_OUT_EVENTS).sum())
    # ダブルプレイは +1 追加カウント
    dp_events = ev.isin(["grounded_into_double_play", "double_play"]).sum()
    outs += int(dp_events)
    tp_events = ev.isin(["triple_play"]).sum()
    outs += int(tp_events) * 2
    # 犠打/犠飛もアウト
    outs += int(ev.isin(_SAC_EVENTS).sum())
    ip = round(outs / 3.0, 1)
    out["ip"] = ip

    if ip > 0:
        out["hr_per_9"] = round(hr_count / ip * 9, 3)

    # ── games / games_started ────────────────
    if "game_pk" in df.columns:
        games_set = df["game_pk"].dropna().astype(int).unique()
        out["games"] = int(len(games_set))
        # games_started: 各 game_pk で 1回 inning_topbot ごとに最初の投球をした投手か判定するのは難しい
        # 簡易: 1回 (inning==1) に投げた game_pk 数を GS とする
        if "inning" in df.columns:
            first_inn = df[df["inning"] == 1]
            if not first_inn.empty and "game_pk" in first_inn.columns:
                gs_set = first_inn["game_pk"].dropna().astype(int).unique()
                out["games_started"] = int(len(gs_set))

    # ── 球威指標 ────────────────────────────
    if "launch_speed" in df.columns:
        ls = df["launch_speed"].dropna()
        if not ls.empty:
            hard_hit = int((ls >= 95.0).sum())
            bip = int(len(ls))
            if bip > 0:
                out["hard_hit_percent"] = round(hard_hit / bip * 100, 2)
            out["avg_ev_against"] = round(float(ls.mean()), 2)

    # ── ゾーン指標 ──────────────────────────
    if "zone" in df.columns:
        z = df["zone"].dropna().astype(int)
        total_p = len(z)
        if total_p > 0:
            in_zone = int(z.between(1, 9).sum())
            edge = int(z.isin(_SHADOW_ZONES).sum())
            low_p = int(z.isin(_LOW_ZONES_NUM).sum())
            heart_p = int(z.isin(_HEART_ZONE).sum())
            out["zone_percent"] = round(in_zone / total_p * 100, 2)
            out["edge_percent"] = round(edge / total_p * 100, 2)
            out["low_zone_pct"] = round(low_p / total_p * 100, 2)
            out["heart_zone_pct"] = round(heart_p / total_p * 100, 2)

    # ── 球速 / Extension ───────────────────
    if "release_speed" in df.columns:
        rs = df["release_speed"].dropna()
        if not rs.empty:
            out["avg_velocity_mph"] = round(float(rs.mean()), 2)
            out["max_velocity_mph"] = round(float(rs.max()), 2)
    if "release_extension" in df.columns:
        re = df["release_extension"].dropna()
        if not re.empty:
            out["extension_ft"] = round(float(re.mean()), 2)

    out["pickoffs"] = pickoff_count

    # LOB% 簡易計算: 残塁者 / 出塁者
    if "on_1b" in df.columns or "on_2b" in df.columns or "on_3b" in df.columns:
        # 各打席終了時の走者状態から推定
        # 詳細実装は別関数 compute_pitcher_lob_pct で
        out["lob_percent"] = compute_pitcher_lob_pct(df)

    return out


def compute_pitcher_lob_pct(df: pd.DataFrame) -> float:
    """
    Statcast pitch-level から投手の LOB% (残塁率) を近似計算する。

    LOB% = (H + BB + HBP - R) / (H + BB + HBP - 1.4*HR)

    Statcast には R (失点) が直接ないため、events と post_runners 情報から推定。
    """
    if _is_empty(df) or "events" not in df.columns:
        return 0.0

    ev = df["events"].dropna()
    h = int(ev.isin(_HIT_EVENTS).sum())
    bb = int(ev.isin(_BB_EVENTS).sum())
    hbp = int(ev.isin(_HBP_EVENTS).sum())
    hr = int(ev.isin(_HR_EVENTS).sum())

    # R (失点) 推定: post_bat_score - bat_score
    r = 0
    if "post_bat_score" in df.columns and "bat_score" in df.columns:
        pa_end_df = df[df["events"].isin(_PA_END_EVENTS)]
        diff = (pa_end_df["post_bat_score"] - pa_end_df["bat_score"]).dropna()
        r = int(diff.sum())

    denom = h + bb + hbp - 1.4 * hr
    if denom <= 0:
        return 0.0
    lob = (h + bb + hbp - r) / denom * 100
    return round(lob, 2)


def compute_basic_batter_metrics(df: pd.DataFrame) -> dict[str, Any]:
    """
    Statcast pitch-level から野手の基本指標を計算する。

    Returns:
        dict with keys:
          k_percent, bb_percent, home_runs, sb, cs, sh,
          xba, xslg, woba (近似), obp, ops,
          whiff_percent, hard_hit_percent, barrel_percent,
          max_exit_velocity, avg_exit_velocity,
          avg_launch_angle, sweet_spot_percent
    """
    out: dict[str, Any] = {
        "k_percent": 0.0,
        "bb_percent": 0.0,
        "home_runs": 0,
        "sb": 0,
        "cs": 0,
        "sh": 0,
        "games": 0,
        "xba": 0.0,
        "xslg": 0.0,
        "woba": 0.0,
        "obp": 0.0,
        "ops": 0.0,
        "whiff_percent": 0.0,
        "hard_hit_percent": 0.0,
        "barrel_percent": 0.0,
        "max_exit_velocity": 0.0,
        "avg_exit_velocity": 0.0,
        "avg_launch_angle": 0.0,
        "sweet_spot_percent": 0.0,
    }
    if _is_empty(df):
        return out

    # PA 集計
    ev = df["events"].dropna() if "events" in df.columns else pd.Series(dtype=object)
    pa_count = int(ev.isin(_PA_END_EVENTS).sum())
    k_count = int(ev.isin(_K_EVENTS).sum())
    bb_count = int(ev.isin(_BB_EVENTS).sum())
    hbp_count = int(ev.isin(_HBP_EVENTS).sum())
    hr_count = int(ev.isin(_HR_EVENTS).sum())
    sb_count = int(ev.isin(_SB_EVENTS).sum())
    cs_count = int(ev.isin(_CS_EVENTS).sum())
    sac_count = int(ev.isin(["sac_bunt", "sac_bunt_double_play"]).sum())
    h_count = int(ev.isin(_HIT_EVENTS).sum())
    single_count = int(ev.isin(["single"]).sum())
    double_count = int(ev.isin(["double"]).sum())
    triple_count = int(ev.isin(["triple"]).sum())

    out["home_runs"] = hr_count
    out["sb"] = sb_count
    out["cs"] = cs_count
    out["sh"] = sac_count

    if pa_count > 0:
        out["k_percent"] = round(k_count / pa_count * 100, 2)
        out["bb_percent"] = round(bb_count / pa_count * 100, 2)

        # OBP = (H + BB + HBP) / (PA - SAC)
        denom_obp = pa_count - sac_count
        if denom_obp > 0:
            out["obp"] = round((h_count + bb_count + hbp_count) / denom_obp, 3)

        # SLG
        ab = pa_count - bb_count - hbp_count - sac_count
        if ab > 0:
            total_bases = single_count + 2 * double_count + 3 * triple_count + 4 * hr_count
            slg = total_bases / ab
            ba = h_count / ab
            out["ops"] = round(slg + out["obp"], 3)

    # xBA / xSLG / xwOBA (BIP のみ集計)
    if "estimated_ba_using_speedangle" in df.columns:
        xba_series = df["estimated_ba_using_speedangle"].dropna()
        if not xba_series.empty:
            out["xba"] = round(float(xba_series.mean()), 3)
    if "estimated_slg_using_speedangle" in df.columns:
        xslg_series = df["estimated_slg_using_speedangle"].dropna()
        if not xslg_series.empty:
            out["xslg"] = round(float(xslg_series.mean()), 3)
    if "estimated_woba_using_speedangle" in df.columns:
        xwoba_series = df["estimated_woba_using_speedangle"].dropna()
        if not xwoba_series.empty:
            out["woba"] = round(float(xwoba_series.mean()), 3)

    # Whiff%
    if "description" in df.columns:
        desc = df["description"].dropna()
        swings = int(desc.isin(_SWING_DESC).sum())
        whiffs = int(desc.isin(_WHIFF_DESC).sum())
        if swings > 0:
            out["whiff_percent"] = round(whiffs / swings * 100, 2)

    # 球威指標
    if "launch_speed" in df.columns:
        ls = df["launch_speed"].dropna()
        if not ls.empty:
            out["max_exit_velocity"] = round(float(ls.max()), 2)
            out["avg_exit_velocity"] = round(float(ls.mean()), 2)
            hard = int((ls >= 95.0).sum())
            out["hard_hit_percent"] = round(hard / len(ls) * 100, 2)

    if "launch_angle" in df.columns:
        la = df["launch_angle"].dropna()
        if not la.empty:
            out["avg_launch_angle"] = round(float(la.mean()), 2)
            sweet = int(la.between(8, 32).sum())
            out["sweet_spot_percent"] = round(sweet / len(la) * 100, 2)

    # Barrel%
    if "launch_speed_angle" in df.columns:
        lsa = df["launch_speed_angle"].dropna()
        bip = int(len(lsa))
        if bip > 0:
            barrel = int((lsa == 6).sum())  # Statcast: lsa==6 が Barrel
            out["barrel_percent"] = round(barrel / bip * 100, 2)

    # games
    if "game_pk" in df.columns:
        out["games"] = int(df["game_pk"].dropna().nunique())

    return out


# ──────────────────────────────────────────────
# シーン別 xwOBA 計算
# ──────────────────────────────────────────────

def compute_pitcher_scene_xwoba(df: pd.DataFrame) -> dict[str, float]:
    """
    投手のシーン別 xwOBA を計算する。

    Returns:
        {
            "season": ..,
            "inning1": ..,
            "inning2": ..,
            "inning7plus": ..,
            "risp": ..,
            "vs_lhb": ..,
            "vs_rhb": ..,
            "high_lev": ..,    # high leverage (8回以降+1点差以内 近似)
            "closer": ..,      # 9回以降の登板
        }
    """
    keys = ["season", "inning1", "inning2", "inning7plus", "risp",
            "vs_lhb", "vs_rhb", "high_lev", "closer", "upper_lineup",
            "lower_lineup"]
    out = {k: 0.0 for k in keys}
    if _is_empty(df) or "estimated_woba_using_speedangle" not in df.columns:
        return out

    xw_col = "estimated_woba_using_speedangle"
    out["season"] = round(_safe_mean(df[xw_col]), 3)

    if "inning" in df.columns:
        out["inning1"] = round(_safe_mean(df[df["inning"] == 1][xw_col]), 3)
        out["inning2"] = round(_safe_mean(df[df["inning"] == 2][xw_col]), 3)
        out["inning7plus"] = round(_safe_mean(df[df["inning"] >= 7][xw_col]), 3)
        # closer: 9回以降の登板
        out["closer"] = round(_safe_mean(df[df["inning"] >= 9][xw_col]), 3)

    # RISP (Runners In Scoring Position): on_2b または on_3b
    if "on_2b" in df.columns and "on_3b" in df.columns:
        risp_mask = df["on_2b"].notna() | df["on_3b"].notna()
        out["risp"] = round(_safe_mean(df[risp_mask][xw_col]), 3)

    if "stand" in df.columns:
        out["vs_lhb"] = round(_safe_mean(df[df["stand"] == "L"][xw_col]), 3)
        out["vs_rhb"] = round(_safe_mean(df[df["stand"] == "R"][xw_col]), 3)

    # High Leverage: 7回以降 + 同点 or 1点差以内
    if "inning" in df.columns and "bat_score" in df.columns and "fld_score" in df.columns:
        hl_mask = (df["inning"] >= 7) & (abs(df["bat_score"] - df["fld_score"]) <= 1)
        out["high_lev"] = round(_safe_mean(df[hl_mask][xw_col]), 3)

    # 打順別: 1-3=upper, 7-9=lower (Statcastにbat_orderが必要)
    if "at_bat_number" in df.columns:
        # 1試合あたりの at_bat_number で簡易推定は難しいので skip
        pass

    return out


def compute_batter_scene_xwoba(df: pd.DataFrame) -> dict[str, float]:
    """
    野手のシーン別 xwOBA を計算する。

    Returns:
        {
            "season": .., "risp": ..,
            "vs_lhp": .., "vs_rhp": ..,
            "late_close": ..,    # 7回以降 + 1点差以内
        }
    """
    keys = ["season", "risp", "vs_lhp", "vs_rhp", "late_close"]
    out = {k: 0.0 for k in keys}
    if _is_empty(df) or "estimated_woba_using_speedangle" not in df.columns:
        return out

    xw_col = "estimated_woba_using_speedangle"
    out["season"] = round(_safe_mean(df[xw_col]), 3)

    if "on_2b" in df.columns and "on_3b" in df.columns:
        risp_mask = df["on_2b"].notna() | df["on_3b"].notna()
        out["risp"] = round(_safe_mean(df[risp_mask][xw_col]), 3)

    if "p_throws" in df.columns:
        out["vs_lhp"] = round(_safe_mean(df[df["p_throws"] == "L"][xw_col]), 3)
        out["vs_rhp"] = round(_safe_mean(df[df["p_throws"] == "R"][xw_col]), 3)

    if "inning" in df.columns and "bat_score" in df.columns and "fld_score" in df.columns:
        lc_mask = (df["inning"] >= 7) & (abs(df["bat_score"] - df["fld_score"]) <= 1)
        out["late_close"] = round(_safe_mean(df[lc_mask][xw_col]), 3)

    return out


def compute_batter_scene_xba_xslg(df: pd.DataFrame) -> dict[str, float]:
    """
    野手のシーン別 xBA / xSLG を計算する。

    Returns:
        {
            "season_xba": .., "season_xslg": ..,
            "risp_xba": .., "risp_xslg": ..,
            "vs_lhp_xba": .., "vs_lhp_xslg": ..,
            "vs_rhp_xba": .., "vs_rhp_xslg": ..,
        }
    """
    out = {
        "season_xba": 0.0, "season_xslg": 0.0,
        "risp_xba": 0.0, "risp_xslg": 0.0,
        "vs_lhp_xba": 0.0, "vs_lhp_xslg": 0.0,
        "vs_rhp_xba": 0.0, "vs_rhp_xslg": 0.0,
    }
    if _is_empty(df):
        return out

    xba_col = "estimated_ba_using_speedangle" if "estimated_ba_using_speedangle" in df.columns else None
    xslg_col = "estimated_slg_using_speedangle" if "estimated_slg_using_speedangle" in df.columns else None
    if not xba_col and not xslg_col:
        return out

    if xba_col:
        out["season_xba"] = round(_safe_mean(df[xba_col]), 3)
    if xslg_col:
        out["season_xslg"] = round(_safe_mean(df[xslg_col]), 3)

    if "on_2b" in df.columns and "on_3b" in df.columns:
        risp = df["on_2b"].notna() | df["on_3b"].notna()
        if xba_col:
            out["risp_xba"] = round(_safe_mean(df[risp][xba_col]), 3)
        if xslg_col:
            out["risp_xslg"] = round(_safe_mean(df[risp][xslg_col]), 3)

    if "p_throws" in df.columns:
        lhp = df["p_throws"] == "L"
        rhp = df["p_throws"] == "R"
        if xba_col:
            out["vs_lhp_xba"] = round(_safe_mean(df[lhp][xba_col]), 3)
            out["vs_rhp_xba"] = round(_safe_mean(df[rhp][xba_col]), 3)
        if xslg_col:
            out["vs_lhp_xslg"] = round(_safe_mean(df[lhp][xslg_col]), 3)
            out["vs_rhp_xslg"] = round(_safe_mean(df[rhp][xslg_col]), 3)

    return out


# ──────────────────────────────────────────────
# ゾーン別指標
# ──────────────────────────────────────────────

def compute_zone_metrics_batter(df: pd.DataFrame) -> dict[str, float]:
    """
    野手のゾーン別 xBA / xSLG を計算する。

    内角/外角は打者の利き手 (stand) + plate_x から判定。
    高め/低めは zone 番号 (1-3/7-9) から判定。

    Returns:
        outside_xba, outside_xslg, inside_xba, inside_xslg,
        high_xba, high_xslg, low_xba, low_xslg
    """
    out = {
        "outside_xba": 0.0, "outside_xslg": 0.0,
        "inside_xba": 0.0,  "inside_xslg": 0.0,
        "high_xba": 0.0,    "high_xslg": 0.0,
        "low_xba": 0.0,     "low_xslg": 0.0,
    }
    if _is_empty(df):
        return out

    xba_col = "estimated_ba_using_speedangle" if "estimated_ba_using_speedangle" in df.columns else None
    xslg_col = "estimated_slg_using_speedangle" if "estimated_slg_using_speedangle" in df.columns else None
    if not xba_col and not xslg_col:
        return out

    # ── 内角/外角 (plate_x + stand) ──────────
    if "plate_x" in df.columns and "stand" in df.columns:
        # ベクトル化判定: 右打者 stand=R で plate_x<0 が内角, 左打者は plate_x>0 が内角
        inside_mask = (
            ((df["stand"] == "R") & (df["plate_x"] < 0)) |
            ((df["stand"] == "L") & (df["plate_x"] > 0))
        )
        outside_mask = (
            ((df["stand"] == "R") & (df["plate_x"] > 0)) |
            ((df["stand"] == "L") & (df["plate_x"] < 0))
        )
        if xba_col:
            out["inside_xba"]  = round(_safe_mean(df[inside_mask][xba_col]),  3)
            out["outside_xba"] = round(_safe_mean(df[outside_mask][xba_col]), 3)
        if xslg_col:
            out["inside_xslg"]  = round(_safe_mean(df[inside_mask][xslg_col]),  3)
            out["outside_xslg"] = round(_safe_mean(df[outside_mask][xslg_col]), 3)

    # ── 高め/低め (zone) ──────────────────────
    if "zone" in df.columns:
        z = df["zone"].dropna().astype(int)
        high_mask = df["zone"].isin(_HIGH_ZONES_NUM)
        low_mask = df["zone"].isin(_LOW_ZONES_NUM)
        if xba_col:
            out["high_xba"] = round(_safe_mean(df[high_mask][xba_col]), 3)
            out["low_xba"]  = round(_safe_mean(df[low_mask][xba_col]),  3)
        if xslg_col:
            out["high_xslg"] = round(_safe_mean(df[high_mask][xslg_col]), 3)
            out["low_xslg"]  = round(_safe_mean(df[low_mask][xslg_col]),  3)

    return out


def compute_zone_metrics_pitcher(df: pd.DataFrame) -> dict[str, float]:
    """
    投手のゾーン別指標を計算する。

    Returns:
        low_zone_pct, heart_zone_pct, edge_percent, zone_percent,
        inside_shadow_pct, inside_whiff_pct, cross_shadow_whiff_pct,
        breaking_offspeed_whiff_pct, inside_xwoba
    """
    out = {
        "low_zone_pct": 0.0,
        "heart_zone_pct": 0.0,
        "edge_percent": 0.0,
        "zone_percent": 0.0,
        "inside_shadow_pct": 0.0,
        "inside_whiff_pct": 0.0,
        "cross_shadow_whiff_pct": 0.0,
        "breaking_offspeed_whiff_pct": 0.0,
    }
    if _is_empty(df) or "zone" not in df.columns:
        return out

    z = df["zone"].dropna().astype(int)
    total_p = len(z)
    if total_p == 0:
        return out

    in_zone = int(z.between(1, 9).sum())
    edge_p = int(z.isin(_SHADOW_ZONES).sum())
    low_p = int(z.isin(_LOW_ZONES_NUM).sum())
    heart_p = int(z.isin(_HEART_ZONE).sum())
    out["zone_percent"] = round(in_zone / total_p * 100, 2)
    out["edge_percent"] = round(edge_p / total_p * 100, 2)
    out["low_zone_pct"] = round(low_p / total_p * 100, 2)
    out["heart_zone_pct"] = round(heart_p / total_p * 100, 2)

    # 内角シャドウ: plate_x が打者の内角側 + zone in [11,12,13,14]
    if "plate_x" in df.columns and "stand" in df.columns:
        inside_mask = (
            ((df["stand"] == "R") & (df["plate_x"] < 0)) |
            ((df["stand"] == "L") & (df["plate_x"] > 0))
        )
        shadow_mask = df["zone"].isin(_SHADOW_ZONES)
        inside_shadow = df[inside_mask & shadow_mask]
        out["inside_shadow_pct"] = round(len(inside_shadow) / total_p * 100, 2)

        # 内角Whiff%
        if "description" in df.columns:
            inside_all = df[inside_mask & df["zone"].between(1, 9)]
            if not inside_all.empty:
                swings = int(inside_all["description"].isin(_SWING_DESC).sum())
                whiffs = int(inside_all["description"].isin(_WHIFF_DESC).sum())
                if swings > 0:
                    out["inside_whiff_pct"] = round(whiffs / swings * 100, 2)

        # 対角線 (cross) シャドウ: 内角シャドウ + 外角シャドウのどちらか + Whiff
        if "description" in df.columns:
            cross_mask = shadow_mask
            cross_df = df[cross_mask]
            if not cross_df.empty:
                swings = int(cross_df["description"].isin(_SWING_DESC).sum())
                whiffs = int(cross_df["description"].isin(_WHIFF_DESC).sum())
                if swings > 0:
                    out["cross_shadow_whiff_pct"] = round(whiffs / swings * 100, 2)

    # 変化球 Whiff%
    if "pitch_type" in df.columns and "description" in df.columns:
        breaking_types = {"SL", "ST", "SV", "CU", "CS", "KC", "FC", "CH", "FS", "FO", "KN", "SC"}
        breaking_df = df[df["pitch_type"].isin(breaking_types)]
        if not breaking_df.empty:
            swings = int(breaking_df["description"].isin(_SWING_DESC).sum())
            whiffs = int(breaking_df["description"].isin(_WHIFF_DESC).sum())
            if swings > 0:
                out["breaking_offspeed_whiff_pct"] = round(whiffs / swings * 100, 2)

    return out


# ──────────────────────────────────────────────
# カウント別指標 (野手)
# ──────────────────────────────────────────────

def compute_count_metrics_batter(df: pd.DataFrame) -> dict[str, float]:
    """
    カウント別の打撃指標を計算する。

    Returns:
        count0_xba, count0_xslg, count0_avg (0ストライク開始時),
        count2_xba, count2_xslg, count2_whiff, count2_woba (2ストライク追い込まれ時)
    """
    out = {
        "count0_xba": 0.0, "count0_xslg": 0.0, "count0_avg": 0.0,
        "count2_xba": 0.0, "count2_xslg": 0.0, "count2_whiff": 0.0, "count2_woba": 0.0,
    }
    if _is_empty(df) or "strikes" not in df.columns:
        return out

    xba_col = "estimated_ba_using_speedangle" if "estimated_ba_using_speedangle" in df.columns else None
    xslg_col = "estimated_slg_using_speedangle" if "estimated_slg_using_speedangle" in df.columns else None
    xw_col = "estimated_woba_using_speedangle" if "estimated_woba_using_speedangle" in df.columns else None

    # 0ストライク (count start: strikes==0)
    c0 = df[df["strikes"] == 0]
    if not c0.empty:
        if xba_col:
            out["count0_xba"] = round(_safe_mean(c0[xba_col]), 3)
        if xslg_col:
            out["count0_xslg"] = round(_safe_mean(c0[xslg_col]), 3)
        # count0_avg: 0ストライクで打席を終了した場合の打率
        if "events" in c0.columns:
            ev = c0["events"].dropna()
            ev_pa = ev.isin(_PA_END_EVENTS)
            ab_mask = ev_pa & ~ev.isin(_BB_EVENTS) & ~ev.isin(_HBP_EVENTS) & ~ev.isin(_SAC_EVENTS)
            ab = int(ab_mask.sum())
            h = int(ev.isin(_HIT_EVENTS).sum())
            if ab > 0:
                out["count0_avg"] = round(h / ab, 3)

    # 2ストライク (strikes==2)
    c2 = df[df["strikes"] == 2]
    if not c2.empty:
        if xba_col:
            out["count2_xba"] = round(_safe_mean(c2[xba_col]), 3)
        if xslg_col:
            out["count2_xslg"] = round(_safe_mean(c2[xslg_col]), 3)
        if xw_col:
            out["count2_woba"] = round(_safe_mean(c2[xw_col]), 3)
        # 2ストライク Whiff%
        if "description" in c2.columns:
            desc = c2["description"].dropna()
            swings = int(desc.isin(_SWING_DESC).sum())
            whiffs = int(desc.isin(_WHIFF_DESC).sum())
            if swings > 0:
                out["count2_whiff"] = round(whiffs / swings * 100, 2)

    return out


# ──────────────────────────────────────────────
# 球種別指標 (投手)
# ──────────────────────────────────────────────

def compute_pitch_metrics_pitcher(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    """
    投手の球種別指標を計算する。

    Returns:
        {
            "FF": {
                "usage_pct": 45.0,
                "velocity_avg": 95.5,
                "whiff_pct": 22.5,
                "horizontal_break": -2.1,
                "induced_vertical_break": 17.3,
                "rv_per_100": 1.2,
                "active_spin": 88.5,
                "extension_ft": 6.5,
                "xwoba": 0.310,
            },
            ...
        }
    """
    out: dict[str, dict[str, float]] = {}
    if _is_empty(df) or "pitch_type" not in df.columns:
        return out

    total = len(df)
    ff_mask = df["pitch_type"].isin(["FF", "FA"])
    ff_avg = float(df.loc[ff_mask, "release_speed"].mean()) if ff_mask.any() else 0.0

    for pt, grp in df.groupby("pitch_type"):
        if not isinstance(pt, str) or pt in ("", "UN", "PO"):
            continue
        usage_pct = len(grp) / total * 100.0
        d = {
            "usage_pct": round(usage_pct, 2),
            "velocity_avg": 0.0,
            "whiff_pct": 0.0,
            "horizontal_break": 0.0,
            "induced_vertical_break": 0.0,
            "rv_per_100": 0.0,
            "active_spin": 0.0,
            "extension_ft": 0.0,
            "xwoba": 0.0,
            "delta_v_from_fastball": 0.0,
        }
        if "release_speed" in grp.columns:
            d["velocity_avg"] = round(_safe_mean(grp["release_speed"]), 2)
        if "description" in grp.columns:
            swings = int(grp["description"].isin(_SWING_DESC).sum())
            whiffs = int(grp["description"].isin(_WHIFF_DESC).sum())
            if swings > 0:
                d["whiff_pct"] = round(whiffs / swings * 100, 2)
        if "pfx_x" in grp.columns:
            d["horizontal_break"] = round(_safe_mean(grp["pfx_x"]) * 12, 2)
        if "pfx_z" in grp.columns:
            d["induced_vertical_break"] = round(_safe_mean(grp["pfx_z"]) * 12, 2)
        if "release_extension" in grp.columns:
            d["extension_ft"] = round(_safe_mean(grp["release_extension"]), 2)
        if "estimated_woba_using_speedangle" in grp.columns:
            d["xwoba"] = round(_safe_mean(grp["estimated_woba_using_speedangle"]), 3)
        # delta_v: 4seam平均球速 - 球種平均
        if ff_avg > 0 and d["velocity_avg"] > 0:
            d["delta_v_from_fastball"] = round(ff_avg - d["velocity_avg"], 2)
        # Active spin (Spin Direction + Movement から推定)
        # スピン軸と回転方向から計算する必要がある。実装簡略化のため
        # spin_axis があるなら使う、なければ 0.0
        if "spin_axis" in grp.columns:
            # 簡易: spin_axis を 0-100 にスケール (正しい計算ではないが代替)
            d["active_spin"] = 0.0  # TODO: 正確な計算

        out[str(pt)] = d

    return out


# ──────────────────────────────────────────────
# 簡易 OAA (守備力)
# ──────────────────────────────────────────────

def compute_simplified_oaa(
    statcast_all_df: pd.DataFrame,
    fielder_id: int,
) -> dict[str, Any]:
    """
    Statcast pitch-level (リーグ全体) から、対象野手の簡易OAA を計算する。

    アルゴリズム:
    1. BIP (hit_into_play) のうち、当該野手のポジション領域に来た打球を抽出
    2. グリッド分割 (10x10) で各セルの out% (リーグ平均) を計算
    3. 当該野手のセル別出場時の out% との差分 × プレイ数 = OAA

    注意: pybaseball.statcast() のレスポンスには通常 "fielder_X" 列が
    含まれない場合がある。その場合は近似計算を行う。

    Returns:
        {"oaa_simplified": int, "oaa_coming_in": int}
    """
    out = {"oaa_simplified": 0, "oaa_coming_in": 0}
    if _is_empty(statcast_all_df):
        return out

    # Statcast pitch-level に fielder_2 〜 fielder_9 列があれば使用
    fielder_cols = [c for c in statcast_all_df.columns if c.startswith("fielder_")]
    if not fielder_cols:
        return out

    # 当該選手が守備に就いた pitch を抽出
    mask = pd.Series(False, index=statcast_all_df.index)
    for col in fielder_cols:
        try:
            mask |= statcast_all_df[col].astype(float).fillna(0).astype(int) == fielder_id
        except (TypeError, ValueError):
            continue

    player_df = statcast_all_df[mask]
    if player_df.empty:
        return out

    # BIP (hit_into_play) のみ
    if "description" in player_df.columns:
        bip = player_df[player_df["description"].str.startswith("hit_into_play", na=False)]
    else:
        bip = player_df

    if bip.empty or "hc_x" not in bip.columns or "hc_y" not in bip.columns:
        return out

    # 結果が out かどうか
    if "events" not in bip.columns:
        return out

    bip_with_loc = bip.dropna(subset=["hc_x", "hc_y", "events"])
    if bip_with_loc.empty:
        return out

    is_out = bip_with_loc["events"].isin(_OUT_EVENTS | _K_EVENTS).astype(int)

    # ─── 全リーグの該当位置の out% を計算 ───
    all_bip = statcast_all_df
    if "description" in all_bip.columns:
        all_bip = all_bip[all_bip["description"].str.startswith("hit_into_play", na=False)]
    all_bip = all_bip.dropna(subset=["hc_x", "hc_y", "events"]) if "hc_x" in all_bip.columns else all_bip
    if all_bip.empty:
        return out

    # グリッド分割
    x_bins = np.linspace(all_bip["hc_x"].min(), all_bip["hc_x"].max() + 1, 11)
    y_bins = np.linspace(all_bip["hc_y"].min(), all_bip["hc_y"].max() + 1, 11)

    all_bip = all_bip.copy()
    all_bip["x_cell"] = pd.cut(all_bip["hc_x"], bins=x_bins, labels=False, include_lowest=True)
    all_bip["y_cell"] = pd.cut(all_bip["hc_y"], bins=y_bins, labels=False, include_lowest=True)
    all_bip["is_out"] = all_bip["events"].isin(_OUT_EVENTS | _K_EVENTS).astype(int)

    cell_outpct = all_bip.groupby(["x_cell", "y_cell"])["is_out"].mean().reset_index()
    cell_outpct.columns = ["x_cell", "y_cell", "league_out_pct"]

    bip_with_loc = bip_with_loc.copy()
    bip_with_loc["x_cell"] = pd.cut(bip_with_loc["hc_x"], bins=x_bins, labels=False, include_lowest=True)
    bip_with_loc["y_cell"] = pd.cut(bip_with_loc["hc_y"], bins=y_bins, labels=False, include_lowest=True)
    bip_with_loc["is_out"] = is_out

    merged = bip_with_loc.merge(cell_outpct, on=["x_cell", "y_cell"], how="left")
    merged["league_out_pct"] = merged["league_out_pct"].fillna(0.0)

    # OAA = sum(actual_out - league_avg_out)
    oaa_value = float((merged["is_out"] - merged["league_out_pct"]).sum())
    out["oaa_simplified"] = int(round(oaa_value))

    # coming_in: 内野手が前進守備で処理した打球
    # 近似: hc_y が小さい (内野前進エリア) かつ launch_angle が低い
    if "launch_angle" in bip_with_loc.columns:
        coming_in_mask = (bip_with_loc["hc_y"] < bip_with_loc["hc_y"].quantile(0.3)) & \
                         (bip_with_loc["launch_angle"] < 10)
        coming_in_df = merged[coming_in_mask]
        if not coming_in_df.empty:
            ci_value = float((coming_in_df["is_out"] - coming_in_df["league_out_pct"]).sum())
            out["oaa_coming_in"] = int(round(ci_value))

    return out


# ──────────────────────────────────────────────
# 簡易 Arm Strength (外野手)
# ──────────────────────────────────────────────

def compute_arm_strength_metrics(
    statcast_all_df: pd.DataFrame,
    fielder_id: int,
    position: str = "OF",
) -> dict[str, float]:
    """
    Statcast pitch-level から、外野手の簡易 Arm Strength (mph) を計算する。

    アルゴリズム:
    1. 当該野手が守備した BIP のうち、フライ/ライナーを抽出
    2. hit_distance_sc (打球飛距離 ft) と hang_time を取得
    3. 飛距離 / hang_time でおおよその送球速度を推定 (mph)
       実際の Arm Strength は別だが、参考値として扱う

    Returns:
        {"arm_strength_mph": float | None}
    """
    out = {"arm_strength_mph": None}
    if _is_empty(statcast_all_df):
        return out

    fielder_cols = [c for c in statcast_all_df.columns if c.startswith("fielder_")]
    if not fielder_cols:
        return out

    mask = pd.Series(False, index=statcast_all_df.index)
    for col in fielder_cols:
        try:
            mask |= statcast_all_df[col].astype(float).fillna(0).astype(int) == fielder_id
        except (TypeError, ValueError):
            continue

    player_df = statcast_all_df[mask]
    if player_df.empty or "hit_distance_sc" not in player_df.columns:
        return out

    # フライ系 BIP
    if "bb_type" in player_df.columns:
        fly_df = player_df[player_df["bb_type"].isin(["fly_ball", "line_drive"])]
    else:
        fly_df = player_df

    if fly_df.empty:
        return out

    dist = fly_df["hit_distance_sc"].dropna()
    if dist.empty:
        return out

    # 平均飛距離をベースに簡易換算
    # OF平均飛距離 ~ 300ft, 強肩 ~ 350ft+
    # 距離分布から arm strength を逆算 (300ft ≈ 85mph, 350ft ≈ 96mph)
    avg_dist = float(dist.mean())
    # 線形マッピング: 300ft → 85mph, 350ft → 96mph
    mph = 85.0 + (avg_dist - 300.0) * (11.0 / 50.0)
    mph = max(60.0, min(110.0, mph))  # 60〜110に clamp
    out["arm_strength_mph"] = round(mph, 2)

    return out


# ──────────────────────────────────────────────
# 簡易 Catcher Framing / Blocking
# ──────────────────────────────────────────────

def compute_catcher_metrics(
    statcast_all_df: pd.DataFrame,
    catcher_id: int,
) -> dict[str, float]:
    """
    Statcast pitch-level から、捕手の簡易 Framing/Blocking を計算する。

    Framing: シャドウゾーン (zone 11-14) でのストライクコール率 - リーグ平均
    Blocking: パスボール/暴投の頻度

    Returns:
        {"framing_runs": float, "blocking_runs": float, "pop_time": float | None}
    """
    out = {"framing_runs": 0.0, "blocking_runs": 0.0, "pop_time": None}
    if _is_empty(statcast_all_df):
        return out

    # fielder_2 が捕手
    if "fielder_2" not in statcast_all_df.columns:
        return out

    try:
        cat_mask = statcast_all_df["fielder_2"].astype(float).fillna(0).astype(int) == catcher_id
    except (TypeError, ValueError):
        return out

    cat_df = statcast_all_df[cat_mask]
    if cat_df.empty or "description" not in cat_df.columns or "zone" not in cat_df.columns:
        return out

    # ── Framing: シャドウゾーンでの called_strike 率 ──
    shadow_df = cat_df[cat_df["zone"].isin(_SHADOW_ZONES)]
    if not shadow_df.empty:
        cs_count = int((shadow_df["description"] == "called_strike").sum())
        called_count = int(shadow_df["description"].isin(["called_strike", "ball"]).sum())
        if called_count > 0:
            framing_rate = cs_count / called_count
            # リーグ平均 ~ 0.45 (近似)
            framing_diff = (framing_rate - 0.45) * called_count
            # 1コール ~ 0.125 run と換算
            out["framing_runs"] = round(framing_diff * 0.125, 2)

    # ── Blocking: パスボール/暴投の数 ──
    # description に "blocked" が含まれるピッチが少ない = blocking が良い
    if "events" in cat_df.columns:
        wp_count = int((cat_df["events"] == "wild_pitch").sum())
        pb_count = int((cat_df["events"] == "passed_ball").sum())
        # 1 wp/pb ~ -0.3 run
        out["blocking_runs"] = round(-(wp_count + pb_count) * 0.3, 2)

    return out


# ──────────────────────────────────────────────
# 状況別指標 (野手)
# ──────────────────────────────────────────────

def compute_situational_metrics_batter(df: pd.DataFrame) -> dict[str, Any]:
    """
    野手の状況別 (満塁、走者なし、終盤、サヨナラ等) 指標を計算する。

    Returns:
        bases_loaded_xslg, bases_loaded_avg,
        bases_empty_obp,
        late_losing_avg, late_losing_xslg,
        late_close_xba, closing_inning_xba,
        big_lead_late_woba, clutch_max_ev,
        walk_off_hits, multi_hit_game_count, multi_hr_games,
        infield_hits, lower_lineup_hr
    """
    out = {
        "bases_loaded_xslg": 0.0, "bases_loaded_avg": 0.0,
        "bases_empty_obp": 0.0,
        "late_losing_avg": 0.0, "late_losing_xslg": 0.0,
        "late_close_xba": 0.0, "closing_inning_xba": 0.0,
        "big_lead_late_woba": 0.0, "clutch_max_ev": 0.0,
        "walk_off_hits": 0, "multi_hit_game_count": 0, "multi_hr_games": 0,
        "infield_hits": 0, "lower_lineup_hr": 0,
    }
    if _is_empty(df):
        return out

    xba_col = "estimated_ba_using_speedangle" if "estimated_ba_using_speedangle" in df.columns else None
    xslg_col = "estimated_slg_using_speedangle" if "estimated_slg_using_speedangle" in df.columns else None
    xw_col = "estimated_woba_using_speedangle" if "estimated_woba_using_speedangle" in df.columns else None

    # 満塁 (on_1b, on_2b, on_3b 全て埋まる)
    if all(c in df.columns for c in ["on_1b", "on_2b", "on_3b"]):
        bl_mask = df["on_1b"].notna() & df["on_2b"].notna() & df["on_3b"].notna()
        bl_df = df[bl_mask]
        if not bl_df.empty:
            if xslg_col:
                out["bases_loaded_xslg"] = round(_safe_mean(bl_df[xslg_col]), 3)
            if "events" in bl_df.columns:
                ev = bl_df["events"].dropna()
                ab = int(ev.isin(_PA_END_EVENTS).sum()) - int(ev.isin(_BB_EVENTS | _HBP_EVENTS | _SAC_EVENTS).sum())
                h = int(ev.isin(_HIT_EVENTS).sum())
                if ab > 0:
                    out["bases_loaded_avg"] = round(h / ab, 3)

        # 走者なし
        be_mask = df["on_1b"].isna() & df["on_2b"].isna() & df["on_3b"].isna()
        be_df = df[be_mask]
        if not be_df.empty and "events" in be_df.columns:
            ev = be_df["events"].dropna()
            pa = int(ev.isin(_PA_END_EVENTS).sum())
            h = int(ev.isin(_HIT_EVENTS).sum())
            bb = int(ev.isin(_BB_EVENTS).sum())
            hbp = int(ev.isin(_HBP_EVENTS).sum())
            sac = int(ev.isin(_SAC_EVENTS).sum())
            denom = pa - sac
            if denom > 0:
                out["bases_empty_obp"] = round((h + bb + hbp) / denom, 3)

    # 終盤(7回以降) + 負け状況
    if all(c in df.columns for c in ["inning", "bat_score", "fld_score"]):
        late_losing = df[(df["inning"] >= 7) & (df["bat_score"] < df["fld_score"])]
        if not late_losing.empty:
            if xslg_col:
                out["late_losing_xslg"] = round(_safe_mean(late_losing[xslg_col]), 3)
            if "events" in late_losing.columns:
                ev = late_losing["events"].dropna()
                ab = int(ev.isin(_PA_END_EVENTS).sum()) - int(ev.isin(_BB_EVENTS | _HBP_EVENTS | _SAC_EVENTS).sum())
                h = int(ev.isin(_HIT_EVENTS).sum())
                if ab > 0:
                    out["late_losing_avg"] = round(h / ab, 3)

        # 終盤・1点差以内・得点圏 (late_close)
        if all(c in df.columns for c in ["on_2b", "on_3b"]):
            lc_mask = (df["inning"] >= 7) & \
                      (abs(df["bat_score"] - df["fld_score"]) <= 1) & \
                      (df["on_2b"].notna() | df["on_3b"].notna())
            lc_df = df[lc_mask]
            if not lc_df.empty and xba_col:
                out["late_close_xba"] = round(_safe_mean(lc_df[xba_col]), 3)

        # 6回以降決勝場面 (1点差以内+リード狙い): inning>=6 + 1点差以内
        ci_mask = (df["inning"] >= 6) & (abs(df["bat_score"] - df["fld_score"]) <= 1)
        ci_df = df[ci_mask]
        if not ci_df.empty and xba_col:
            out["closing_inning_xba"] = round(_safe_mean(ci_df[xba_col]), 3)

        # 4点リード時・終盤 wOBA
        big_lead_late = df[(df["inning"] >= 7) & (df["bat_score"] - df["fld_score"] >= 4)]
        if not big_lead_late.empty and xw_col:
            out["big_lead_late_woba"] = round(_safe_mean(big_lead_late[xw_col]), 3)

        # 接戦時 (5回以降, 3点差以内) max EV
        clutch = df[(df["inning"] >= 5) & (abs(df["bat_score"] - df["fld_score"]) <= 3)]
        if not clutch.empty and "launch_speed" in clutch.columns:
            ls = clutch["launch_speed"].dropna()
            if not ls.empty:
                out["clutch_max_ev"] = round(float(ls.max()), 2)

    # サヨナラ打: 9回裏(以降) + 同点/負け状態でヒット → 勝ち
    if all(c in df.columns for c in ["inning", "inning_topbot", "events", "bat_score", "fld_score", "post_bat_score", "post_fld_score"]):
        walkoff_mask = (df["inning"] >= 9) & (df["inning_topbot"] == "Bot") & \
                       (df["bat_score"] <= df["fld_score"]) & \
                       (df["post_bat_score"] > df["post_fld_score"]) & \
                       (df["events"].isin(_HIT_EVENTS))
        out["walk_off_hits"] = int(walkoff_mask.sum())

    # マルチヒット試合数 / 2HR以上試合数
    if "game_pk" in df.columns and "events" in df.columns:
        ev_df = df[df["events"].notna()]
        if not ev_df.empty:
            h_by_game = ev_df[ev_df["events"].isin(_HIT_EVENTS)].groupby("game_pk").size()
            hr_by_game = ev_df[ev_df["events"].isin(_HR_EVENTS)].groupby("game_pk").size()
            out["multi_hit_game_count"] = int((h_by_game >= 3).sum())
            out["multi_hr_games"] = int((hr_by_game >= 2).sum())

    # 内野安打: bb_type==ground_ball + single
    if all(c in df.columns for c in ["events", "bb_type"]):
        infield_mask = (df["events"] == "single") & (df["bb_type"] == "ground_ball")
        # かつ hc_y が内野範囲 (近似)
        if "hit_distance_sc" in df.columns:
            infield_mask &= df["hit_distance_sc"] < 130
        out["infield_hits"] = int(infield_mask.sum())

    return out


# ──────────────────────────────────────────────
# 状況別指標 (投手)
# ──────────────────────────────────────────────

def compute_situational_metrics_pitcher(df: pd.DataFrame) -> dict[str, Any]:
    """
    投手の状況別指標を計算する。

    Returns:
        risp_hard_hit_pct,                       # 得点圏被ハードヒット率
        pitch_100plus_rv, pitch_100plus_velo_decline, pitch_100plus_rv_improve,
        late_pitch_whiff_diff,                  # 80球目以降 Whiff% 上昇
        upper_lineup_xwoba, lower_lineup_xwoba,
        post_hit_hard_hit_increase,
        is_closer,
        avg_relief_innings,
        win_pct, run_support,
        monthly_rv_stddev,
        inning5_or_9_xwoba_increase,
        xwoba_vs_top_hitters, rv_vs_top_hitters
    """
    out = {
        "risp_hard_hit_pct": 0.0,
        "pitch_100plus_rv": 0.0,
        "pitch_100plus_velo_decline": 0.0,
        "pitch_100plus_rv_improve": 0.0,
        "late_pitch_whiff_diff": 0.0,
        "upper_lineup_xwoba": 0.0,
        "lower_lineup_xwoba": 0.0,
        "post_hit_hard_hit_increase": 0.0,
        "is_closer": False,
        "avg_relief_innings": 0.0,
        "win_pct": None,
        "run_support": None,
        "monthly_rv_stddev": 0.0,
        "inning5_or_9_xwoba_increase": 0.0,
        "xwoba_vs_top_hitters": 0.0,
        "rv_vs_top_hitters": 0.0,
        "inning1_xwoba": 0.0,
        "inning2_xwoba": 0.0,
        "inning7plus_xwoba": 0.0,
        "closer_xwoba": 0.0,
        "high_lev_xwoba": 0.0,
    }
    if _is_empty(df):
        return out

    xw_col = "estimated_woba_using_speedangle" if "estimated_woba_using_speedangle" in df.columns else None

    # ── RISP Hard Hit% ──
    if "on_2b" in df.columns and "on_3b" in df.columns and "launch_speed" in df.columns:
        risp_mask = df["on_2b"].notna() | df["on_3b"].notna()
        risp_df = df[risp_mask]
        ls = risp_df["launch_speed"].dropna()
        if not ls.empty:
            hard = int((ls >= 95.0).sum())
            out["risp_hard_hit_pct"] = round(hard / len(ls) * 100, 2)

    # ── 100球超 ──
    if "pitch_number_appearance" in df.columns or "pitch_number" in df.columns:
        col = "pitch_number_appearance" if "pitch_number_appearance" in df.columns else "pitch_number"
        late = df[df[col] >= 100]
        early = df[df[col] < 100]
        if not late.empty and not early.empty:
            # 100球超RV
            if xw_col:
                early_xw = _safe_mean(early[xw_col])
                late_xw = _safe_mean(late[xw_col])
                # RV ≈ -(xwoba - 0.310) * PA (低いほど良い)
                out["pitch_100plus_rv"] = round((0.310 - late_xw) * len(late) / 100, 3)
                # 改善幅: 100球前後の RV 差 (正なら改善)
                out["pitch_100plus_rv_improve"] = round(((0.310 - late_xw) - (0.310 - early_xw)) * 100 / max(len(early), 1), 3)
            # 球速低下
            if "release_speed" in df.columns:
                e_vel = _safe_mean(early["release_speed"])
                l_vel = _safe_mean(late["release_speed"])
                if e_vel > 0 and l_vel > 0:
                    out["pitch_100plus_velo_decline"] = round(e_vel - l_vel, 2)

    # ── 80球目以降 Whiff% 上昇 ──
    if ("pitch_number_appearance" in df.columns or "pitch_number" in df.columns) and "description" in df.columns:
        col = "pitch_number_appearance" if "pitch_number_appearance" in df.columns else "pitch_number"
        late80 = df[df[col] >= 80]
        early80 = df[df[col] < 80]
        if not late80.empty and not early80.empty:
            def _whiff(d):
                desc = d["description"].dropna()
                sw = int(desc.isin(_SWING_DESC).sum())
                wh = int(desc.isin(_WHIFF_DESC).sum())
                return wh / sw * 100 if sw > 0 else 0
            out["late_pitch_whiff_diff"] = round(_whiff(late80) - _whiff(early80), 2)

    # ── イニング別 xwOBA ──
    if "inning" in df.columns and xw_col:
        out["inning1_xwoba"] = round(_safe_mean(df[df["inning"] == 1][xw_col]), 3)
        out["inning2_xwoba"] = round(_safe_mean(df[df["inning"] == 2][xw_col]), 3)
        out["inning7plus_xwoba"] = round(_safe_mean(df[df["inning"] >= 7][xw_col]), 3)
        out["closer_xwoba"] = round(_safe_mean(df[df["inning"] >= 9][xw_col]), 3)
        # 5回または9回直前 (5回終了時, 9回終了時の xwOBA 上昇)
        in5_or_9 = df[df["inning"].isin([5, 9])]
        in_other = df[~df["inning"].isin([5, 9])]
        if not in5_or_9.empty and not in_other.empty:
            out["inning5_or_9_xwoba_increase"] = round(_safe_mean(in5_or_9[xw_col]) - _safe_mean(in_other[xw_col]), 3)

    # High Lev xwOBA
    if all(c in df.columns for c in ["inning", "bat_score", "fld_score"]) and xw_col:
        hl_mask = (df["inning"] >= 7) & (abs(df["bat_score"] - df["fld_score"]) <= 1)
        out["high_lev_xwoba"] = round(_safe_mean(df[hl_mask][xw_col]), 3)

    # is_closer: 9回以降の登板 / 全登板 が 70%以上
    if "inning" in df.columns and "game_pk" in df.columns:
        total_games = df["game_pk"].nunique()
        if total_games > 0:
            closer_games = df[df["inning"] >= 9]["game_pk"].nunique()
            out["is_closer"] = (closer_games / total_games) >= 0.7

    # 救援平均消化イニング: GS != 0 のゲームを除外
    if "game_pk" in df.columns and "inning" in df.columns:
        per_game = df.groupby("game_pk")["inning"].nunique()
        if not per_game.empty:
            out["avg_relief_innings"] = round(float(per_game.mean()), 2)

    # 月別 RV 標準偏差
    if "game_date" in df.columns and xw_col:
        try:
            d = pd.to_datetime(df["game_date"], errors="coerce")
            df = df.copy()
            df["_month"] = d.dt.month
            monthly = df.groupby("_month")[xw_col].mean()
            if len(monthly) >= 2:
                out["monthly_rv_stddev"] = round(float(monthly.std()), 3)
        except Exception:
            pass

    # 被安打直後 Hard Hit% 上昇
    if "events" in df.columns and "launch_speed" in df.columns:
        df_pa = df[df["events"].isin(_PA_END_EVENTS)].copy().sort_values(["game_pk", "at_bat_number"]) \
            if all(c in df.columns for c in ["game_pk", "at_bat_number"]) else df[df["events"].isin(_PA_END_EVENTS)]
        df_pa["prev_was_hit"] = df_pa["events"].shift(1).isin(_HIT_EVENTS)
        ls_all = df_pa["launch_speed"].dropna()
        ls_post_hit = df_pa[df_pa["prev_was_hit"]]["launch_speed"].dropna()
        if not ls_all.empty and not ls_post_hit.empty:
            avg_hh = (ls_all >= 95.0).mean() * 100
            post_hh = (ls_post_hit >= 95.0).mean() * 100
            out["post_hit_hard_hit_increase"] = round(post_hh - avg_hh, 2)

    return out


# ──────────────────────────────────────────────
# 投手 - 球種・リリースポイント
# ──────────────────────────────────────────────

def compute_release_stddev(df: pd.DataFrame) -> dict[str, float]:
    """投手の リリースポイント標準偏差 (in)。"""
    out = {"release_x_stddev": 0.0, "release_z_stddev": 0.0}
    if _is_empty(df):
        return out
    if "release_pos_x" in df.columns:
        out["release_x_stddev"] = round(float(df["release_pos_x"].std() * 12), 3) if df["release_pos_x"].notna().sum() > 1 else 0.0
    if "release_pos_z" in df.columns:
        out["release_z_stddev"] = round(float(df["release_pos_z"].std() * 12), 3) if df["release_pos_z"].notna().sum() > 1 else 0.0
    return out


# ──────────────────────────────────────────────
# 打球方向 (野手)
# ──────────────────────────────────────────────

def compute_spray_metrics_batter(df: pd.DataFrame, batter_stand: str = "R") -> dict[str, Any]:
    """
    野手の打球方向別指標を計算する。

    Pull = 引っ張り (右打者なら左中間方向, 左打者なら右中間)
    Oppo = 逆方向

    Returns:
        pull_hr_pct, pull_xslg,
        oppo_hr_count, oppo_hits, oppo_hits_pct, oppo_xba, oppo_xslg,
        linedrive_pct (8-14度), avg_launch_angle
    """
    out = {
        "pull_hr_pct": 0.0, "pull_xslg": 0.0,
        "oppo_hr_count": 0, "oppo_hits": 0, "oppo_hits_pct": 0.0,
        "oppo_xba": 0.0, "oppo_xslg": 0.0,
        "linedrive_pct": 0.0,
    }
    if _is_empty(df):
        return out

    # Statcastの hc_x, hc_y から spray angle を計算
    # hc_x ~ 125 がセンター方向、左打者と右打者で Pull が反転
    if "hc_x" not in df.columns:
        return out

    # ── Pull/Oppo 判定 ──
    # 右打者: hc_x < 125 が Pull, > 125 が Oppo
    # 左打者: hc_x > 125 が Pull, < 125 が Oppo
    if batter_stand == "R":
        pull_mask = df["hc_x"] < 125
        oppo_mask = df["hc_x"] > 125
    else:
        pull_mask = df["hc_x"] > 125
        oppo_mask = df["hc_x"] < 125

    xslg_col = "estimated_slg_using_speedangle" if "estimated_slg_using_speedangle" in df.columns else None
    xba_col = "estimated_ba_using_speedangle" if "estimated_ba_using_speedangle" in df.columns else None

    # Pull
    pull_df = df[pull_mask]
    if not pull_df.empty:
        if xslg_col:
            out["pull_xslg"] = round(_safe_mean(pull_df[xslg_col]), 3)
        if "events" in pull_df.columns:
            pull_hr = int(pull_df["events"].isin(_HR_EVENTS).sum())
            total_hr = int(df["events"].isin(_HR_EVENTS).sum())
            if total_hr > 0:
                out["pull_hr_pct"] = round(pull_hr / total_hr, 3)

    # Oppo
    oppo_df = df[oppo_mask]
    if not oppo_df.empty:
        if xba_col:
            out["oppo_xba"] = round(_safe_mean(oppo_df[xba_col]), 3)
        if xslg_col:
            out["oppo_xslg"] = round(_safe_mean(oppo_df[xslg_col]), 3)
        if "events" in oppo_df.columns:
            out["oppo_hr_count"] = int(oppo_df["events"].isin(_HR_EVENTS).sum())
            out["oppo_hits"] = int(oppo_df["events"].isin(_HIT_EVENTS).sum())
            total_hits = int(df["events"].isin(_HIT_EVENTS).sum())
            if total_hits > 0:
                out["oppo_hits_pct"] = round(out["oppo_hits"] / total_hits * 100, 2)

    # ライナー (打球角 8-14度)
    if "launch_angle" in df.columns:
        la = df["launch_angle"].dropna()
        bip = int(len(la))
        if bip > 0:
            ld = int(la.between(8, 14).sum())
            out["linedrive_pct"] = round(ld / bip * 100, 2)

    return out


def compute_clutch_metrics_pitcher(df: pd.DataFrame) -> dict[str, float]:
    """
    投手のクラッチ場面 (得点圏, 終盤等) の指標。

    Returns:
        risp_xwoba, risp_xba,
        closer_xwoba (9回以降), is_closer
    """
    out = {
        "risp_xwoba": 0.0,
        "closer_xwoba": 0.0,
        "is_closer": False,
    }
    if _is_empty(df):
        return out

    xw_col = "estimated_woba_using_speedangle" if "estimated_woba_using_speedangle" in df.columns else None
    if xw_col:
        # RISP
        if "on_2b" in df.columns and "on_3b" in df.columns:
            risp_mask = df["on_2b"].notna() | df["on_3b"].notna()
            out["risp_xwoba"] = round(_safe_mean(df[risp_mask][xw_col]), 3)
        # closer
        if "inning" in df.columns:
            out["closer_xwoba"] = round(_safe_mean(df[df["inning"] >= 9][xw_col]), 3)
            if "game_pk" in df.columns:
                total = df["game_pk"].nunique()
                closer_g = df[df["inning"] >= 9]["game_pk"].nunique()
                out["is_closer"] = total > 0 and (closer_g / total) >= 0.7

    return out
