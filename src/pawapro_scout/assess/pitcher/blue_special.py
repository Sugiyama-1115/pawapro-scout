"""
assess/pitcher/blue_special.py
投手の青特殊能力を査定する。

青特                判定指標
キレ◯              変化球/オフスピードの Whiff% >= 35%
奪三振              k_percent >= 30%
球速安定            4seam の (最速 - 平均) <= 3mph
リリース◯           release_stddev <= 0.5in
緩急◯              全球種の速度差 >= 15mph (変幻自在 = 20mph 以上は除く)
球持ち◯            extension_percentile >= 90
緊急登板◯           ir_stranded_pct >= 80%
低め◯              low_zone_pct >= 40%
逃げ球              heart_zone_pct <= 20%
ナチュラルシュート   4seam HB >= 10in (腕側方向)
ジャイロボール       4seam Active Spin <= 70%
対ランナー◯        risp_xwoba - season_xwoba <= -0.030
立ち上がり◯        inning1_xwoba - season_xwoba <= -0.040
尻上がり            inning7plus_xwoba - season_xwoba <= -0.020
要所◯              high_lev_xwoba - season_xwoba <= -0.050
"""

from __future__ import annotations

from pawapro_scout.config import (
    BLUE_4SEAM_SPEED_DIFF_MAX,
    BLUE_EXT_PERCENTILE,
    BLUE_FIRST_INN_XWOBA_IMPROVE,
    BLUE_GYROBALL_SPIN_MAX,
    BLUE_HEART_ZONE_PCT_MAX,
    BLUE_HIGH_LEV_XWOBA_IMPROVE,
    BLUE_IR_STRAND_MIN,
    BLUE_K_PCT_MIN,
    BLUE_KIRE_BREAKING_WHIFF_MIN,
    BLUE_LATE_XWOBA_IMPROVE,
    BLUE_LOW_ZONE_PCT_MIN,
    BLUE_NATURAL_HB_MIN,
    BLUE_ON_RUNNER_XWOBA_IMPROVE,
    BLUE_RELEASE_STDDEV_MAX,
    BLUE_SPEED_DIFF_MIN,
    GOLD_SPEED_DIFF_MAX,
)
from pawapro_scout.models import PitchAggregated, PitcherStats

# Statcast 変化球 / オフスピード family
_BREAKING_OFFSPEED_FAMILIES = {"slider_family", "splitter_family", "changeup", "curveball"}


def assess_blue_special(stats: PitcherStats) -> list[str]:
    """PitcherStats から獲得する青特リストを返す。"""
    result: list[str] = []

    if _is_kire_maru(stats.pitches):
        result.append("キレ◯")

    if _is_datsusansen(stats):
        result.append("奪三振")

    if _is_release_maru(stats):
        result.append("リリース◯")

    if _is_kankyuu_maru(stats.pitches):
        result.append("緩急◯")

    if _is_tamamochichu(stats):
        result.append("球持ち◯")

    if _is_emergency_maru(stats):
        result.append("緊急登板◯")

    if _is_low_zone_maru(stats):
        result.append("低め◯")

    if _is_nigeball(stats):
        result.append("逃げ球")

    if _is_natural_shoot(stats.pitches):
        result.append("ナチュラルシュート")

    if _is_gyroball(stats):
        result.append("ジャイロボール")

    if _is_runner_maru(stats):
        result.append("対ランナー◯")

    if _is_tachiagarimaru(stats):
        result.append("立ち上がり◯")

    if _is_jiriagari(stats):
        result.append("尻上がり")

    if _is_yodokoro_maru(stats):
        result.append("要所◯")

    return result


# ──────────────────────────────────────────────
# 各青特の判定
# ──────────────────────────────────────────────

def _is_kire_maru(pitches: list[PitchAggregated]) -> bool:
    """キレ◯: 変化球・オフスピードの Whiff% (加重平均) >= 35%。"""
    from pawapro_scout.config import PITCH_FAMILY_MAP
    breaking = [p for p in pitches if PITCH_FAMILY_MAP.get(p.pitch_type, "") in _BREAKING_OFFSPEED_FAMILIES]
    if not breaking:
        return False
    total_usage = sum(p.usage_pct for p in breaking)
    if total_usage == 0:
        return False
    weighted_whiff = sum(p.whiff_pct * p.usage_pct for p in breaking) / total_usage
    return weighted_whiff >= BLUE_KIRE_BREAKING_WHIFF_MIN


def _is_datsusansen(stats: PitcherStats) -> bool:
    """奪三振: K% >= 30%。"""
    return stats.k_percent >= BLUE_K_PCT_MIN


def _is_release_maru(stats: PitcherStats) -> bool:
    """リリース◯: リリースポイントの標準偏差 (x, z の平均) が小さい。"""
    avg_std = (stats.release_x_stddev + stats.release_z_stddev) / 2.0
    return 0 < avg_std <= BLUE_RELEASE_STDDEV_MAX


def _is_kankyuu_maru(pitches: list[PitchAggregated]) -> bool:
    """緩急◯: 球速差が 15mph 以上 (変幻自在 = 20mph 以上は除く)。"""
    if len(pitches) < 2:
        return False
    vels = [p.velocity_avg for p in pitches if p.velocity_avg > 0]
    if len(vels) < 2:
        return False
    diff = max(vels) - min(vels)
    return BLUE_SPEED_DIFF_MIN <= diff < GOLD_SPEED_DIFF_MAX


def _is_tamamochichu(stats: PitcherStats) -> bool:
    """球持ち◯: Extension パーセンタイル >= 90。"""
    return stats.extension_percentile >= BLUE_EXT_PERCENTILE


def _is_emergency_maru(stats: PitcherStats) -> bool:
    """緊急登板◯: IR-S% >= 80%。"""
    if stats.ir_stranded_pct is None:
        return False
    return stats.ir_stranded_pct >= BLUE_IR_STRAND_MIN


def _is_low_zone_maru(stats: PitcherStats) -> bool:
    """低め◯: 低めゾーン (7/8/9) 投球率 >= 40%。"""
    return stats.low_zone_pct >= BLUE_LOW_ZONE_PCT_MIN


def _is_nigeball(stats: PitcherStats) -> bool:
    """逃げ球: ハートゾーン (5) 投球率 <= 20%。データがない場合は付与しない。"""
    if stats.heart_zone_pct == 0.0:
        return False
    return stats.heart_zone_pct <= BLUE_HEART_ZONE_PCT_MAX


def _is_natural_shoot(pitches: list[PitchAggregated]) -> bool:
    """
    ナチュラルシュート: 4seam (FF/FA) の水平変化が腕側に 10in 以上。
    horizontal_break の絶対値で判定 (符号は利き手によって異なる)。
    """
    ff = next((p for p in pitches if p.pitch_type in ("FF", "FA")), None)
    if ff is None:
        return False
    return abs(ff.horizontal_break) >= BLUE_NATURAL_HB_MIN


def _is_gyroball(stats: PitcherStats) -> bool:
    """ジャイロボール: 4seam の Active Spin (回転効率) <= 70%。"""
    if stats.active_spin_4seam is None:
        return False
    return stats.active_spin_4seam <= BLUE_GYROBALL_SPIN_MAX


def _is_runner_maru(stats: PitcherStats) -> bool:
    """対ランナー◯: RISP xwOBA - 通常 xwOBA <= -0.030。"""
    if stats.season_xwoba == 0.0 or stats.risp_xwoba == 0.0:
        return False
    return (stats.risp_xwoba - stats.season_xwoba) <= BLUE_ON_RUNNER_XWOBA_IMPROVE


def _is_tachiagarimaru(stats: PitcherStats) -> bool:
    """立ち上がり◯: 1回の xwOBA - 通常 xwOBA <= -0.040。"""
    if stats.season_xwoba == 0.0 or stats.inning1_xwoba == 0.0:
        return False
    return (stats.inning1_xwoba - stats.season_xwoba) <= BLUE_FIRST_INN_XWOBA_IMPROVE


def _is_jiriagari(stats: PitcherStats) -> bool:
    """尻上がり: 7回以降 xwOBA - 通常 xwOBA <= -0.020。"""
    if stats.season_xwoba == 0.0 or stats.inning7plus_xwoba == 0.0:
        return False
    return (stats.inning7plus_xwoba - stats.season_xwoba) <= BLUE_LATE_XWOBA_IMPROVE


def _is_yodokoro_maru(stats: PitcherStats) -> bool:
    """要所◯: High Leverage xwOBA - 通常 xwOBA <= -0.050。"""
    if stats.season_xwoba == 0.0 or stats.high_lev_xwoba == 0.0:
        return False
    return (stats.high_lev_xwoba - stats.season_xwoba) <= BLUE_HIGH_LEV_XWOBA_IMPROVE
