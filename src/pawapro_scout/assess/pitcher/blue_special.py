"""
assess/pitcher/blue_special.py
投手の青特殊能力を査定する（新基準 r1 - 28種）。

判定指標は config.py の BLUE_* 定数に集約。
データ未取得の指標は付与しない（return False）。
"""

from __future__ import annotations

from pawapro_scout.config import (
    BLUE_CLOSER_XWOBA_MAX,
    BLUE_CROSS_CANNON_WHIFF_MIN,
    BLUE_CUTTER_HB_MIN,
    BLUE_ESCAPE_HR_PER_9_MAX,
    BLUE_EXTENSION_FT_MIN,
    BLUE_FIRST_INN_XWOBA_MAX,
    BLUE_GYROBALL_SPIN_MAX,
    BLUE_HEAVY_HARD_HIT_MAX,
    BLUE_INSIDE_SHADOW_PCT_MIN,
    BLUE_IR_STRAND_MIN,
    BLUE_KIRE_BREAKING_WHIFF_MIN,
    BLUE_KONJO_VELO_DECLINE_MAX,
    BLUE_K_PCT_MIN,
    BLUE_LATE_XWOBA_IMPROVE,
    BLUE_LOW_ZONE_PCT_MIN,
    BLUE_MULTI_PITCH_TYPES_MIN,
    BLUE_NATURAL_HB_MIN,
    BLUE_P_FIELDING_RV_MIN,
    BLUE_PITCH_USAGE_THRESHOLD,
    BLUE_RELEASE_STDDEV_MAX,
    BLUE_RELIEF_AVG_INNINGS_MIN,
    BLUE_SPEED_DIFF_MIN,
    BLUE_VS_TOP_HITTERS_RV_MIN,
    BLUE_WIN_LUCK_RS9_MIN,
    BLUE_WIN_PCT_MIN,
    GOLD_SPEED_DIFF_MAX,
    PITCH_FAMILY_MAP,
)
from pawapro_scout.models import PitchAggregated, PitcherStats

_BREAKING_OFFSPEED_FAMILIES = {"slider_family", "splitter_family", "changeup", "curveball"}


def assess_blue_special(stats: PitcherStats) -> list[str]:
    """PitcherStats から獲得する青特リストを返す（新基準 r1）。"""
    result: list[str] = []

    if _is_datsusansen(stats):
        result.append("奪三振")
    if _is_kire_maru(stats.pitches):
        result.append("キレ◯")
    if _is_dakyu_hanno(stats):
        result.append("打球反応◯")
    if _is_low_zone_maru(stats):
        result.append("低め◯")
    if _is_tamamochichu(stats):
        result.append("球持ち◯")
    if _is_omoi_tama(stats):
        result.append("重い球")
    if _is_nigeball(stats):
        result.append("逃げ球")
    if _is_release_maru(stats):
        result.append("リリース◯")
    if _is_kankyuu_maru(stats.pitches):
        result.append("緩急◯")
    if _is_gyroball(stats):
        result.append("ジャイロボール")
    if _is_inside_attack(stats):
        result.append("内角攻め")
    if _is_emergency_maru(stats):
        result.append("緊急登板◯")
    if _is_pressure(stats):
        result.append("威圧感")
    if _is_winning_luck(stats):
        result.append("勝ち運")
    if _is_konjo_maru(stats):
        result.append("根性◯")
    if _is_cross_cannon(stats):
        result.append("クロスキャノン")
    if _is_jiriagari(stats):
        result.append("尻上がり")
    if _is_vs_top_hitters(stats):
        result.append("対強打者◯")
    if _is_innings_relief(stats):
        result.append("回またぎ◯")
    if _is_multi_pitch_types(stats.pitches):
        result.append("球種多◯")
    if _is_pickoff_maru(stats):
        result.append("牽制◯")
    if _is_first_inning_maru(stats):
        result.append("立ち上がり◯")
    if _is_winning_streak(stats):
        result.append("勝ちまくり")
    if _is_natural_shoot(stats.pitches):
        result.append("ナチュシュ")
    if _is_cut_slider(stats.pitches):
        result.append("真っスラ")

    return result


# ──────────────────────────────────────────────
# 各青特の判定
# ──────────────────────────────────────────────

def _is_datsusansen(stats: PitcherStats) -> bool:
    """奪三振: K% >= 27.0%。"""
    return stats.k_percent >= BLUE_K_PCT_MIN


def _is_kire_maru(pitches: list[PitchAggregated]) -> bool:
    """キレ◯: 主要変化球の Whiff% (加重平均) >= 35.0%。"""
    breaking = [p for p in pitches if PITCH_FAMILY_MAP.get(p.pitch_type, "") in _BREAKING_OFFSPEED_FAMILIES]
    if not breaking:
        return False
    total_usage = sum(p.usage_pct for p in breaking)
    if total_usage == 0:
        return False
    weighted_whiff = sum(p.whiff_pct * p.usage_pct for p in breaking) / total_usage
    return weighted_whiff >= BLUE_KIRE_BREAKING_WHIFF_MIN


def _is_dakyu_hanno(stats: PitcherStats) -> bool:
    """打球反応◯: Fielding Run Value (P) >= +3。"""
    return stats.p_fielding_rv >= BLUE_P_FIELDING_RV_MIN


def _is_low_zone_maru(stats: PitcherStats) -> bool:
    """低め◯: Low Zone% >= 50%。"""
    return stats.low_zone_pct >= BLUE_LOW_ZONE_PCT_MIN


def _is_tamamochichu(stats: PitcherStats) -> bool:
    """球持ち◯: Extension >= 6.7ft。"""
    return stats.extension_ft >= BLUE_EXTENSION_FT_MIN


def _is_omoi_tama(stats: PitcherStats) -> bool:
    """重い球: Hard Hit% <= 33.0%。データなしは付与しない。"""
    if stats.hard_hit_percent <= 0.0:
        return False
    return stats.hard_hit_percent <= BLUE_HEAVY_HARD_HIT_MAX


def _is_nigeball(stats: PitcherStats) -> bool:
    """逃げ球: HR/9 <= 0.8。データなしは付与しない。"""
    if stats.hr_per_9 <= 0.0:
        return False
    return stats.hr_per_9 <= BLUE_ESCAPE_HR_PER_9_MAX


def _is_release_maru(stats: PitcherStats) -> bool:
    """リリース◯: release stddev (x,z 平均) <= 0.5in。"""
    avg_std = (stats.release_x_stddev + stats.release_z_stddev) / 2.0
    return 0 < avg_std <= BLUE_RELEASE_STDDEV_MAX


def _is_kankyuu_maru(pitches: list[PitchAggregated]) -> bool:
    """緩急◯: 最大球速差 >= 15mph かつ 有効球種が 2つ以上 (変幻自在 = 20mph 以上は除く)。"""
    effective = [p for p in pitches if p.usage_pct >= BLUE_PITCH_USAGE_THRESHOLD and p.velocity_avg > 0]
    if len(effective) < 2:
        return False
    vels = [p.velocity_avg for p in effective]
    diff = max(vels) - min(vels)
    return BLUE_SPEED_DIFF_MIN <= diff < GOLD_SPEED_DIFF_MAX


def _is_gyroball(stats: PitcherStats) -> bool:
    """ジャイロボール: 4seam Active Spin <= 75%。"""
    if stats.active_spin_4seam is None:
        return False
    return stats.active_spin_4seam <= BLUE_GYROBALL_SPIN_MAX


def _is_inside_attack(stats: PitcherStats) -> bool:
    """内角攻め: Inside Shadow Zone% >= 25%。"""
    return stats.inside_shadow_pct >= BLUE_INSIDE_SHADOW_PCT_MIN


def _is_emergency_maru(stats: PitcherStats) -> bool:
    """緊急登板◯: IRS% >= 75%。"""
    if stats.ir_stranded_pct is None:
        return False
    return stats.ir_stranded_pct >= BLUE_IR_STRAND_MIN


def _is_pressure(stats: PitcherStats) -> bool:
    """威圧感: クローザー役割時 xwOBA <= .280。"""
    if not stats.is_closer or stats.closer_xwoba <= 0.0:
        return False
    return stats.closer_xwoba <= BLUE_CLOSER_XWOBA_MAX


def _is_winning_luck(stats: PitcherStats) -> bool:
    """勝ち運: RS/9 >= 6.0。"""
    if stats.run_support is None:
        return False
    return stats.run_support >= BLUE_WIN_LUCK_RS9_MIN


def _is_konjo_maru(stats: PitcherStats) -> bool:
    """根性◯: 100球超え後の平均球速低下が 1.0mph 以内 (= 低下値 <= 1.0)。"""
    if stats.pitch_100plus_velo_decline <= 0.0:
        # 低下なし (データなしか、低下無し)
        return False
    return stats.pitch_100plus_velo_decline <= BLUE_KONJO_VELO_DECLINE_MAX


def _is_cross_cannon(stats: PitcherStats) -> bool:
    """クロスキャノン: 対角線 (Shadow Zone) Whiff% >= 40%。"""
    return stats.cross_shadow_whiff_pct >= BLUE_CROSS_CANNON_WHIFF_MIN


def _is_jiriagari(stats: PitcherStats) -> bool:
    """尻上がり: 7イニング目以降の被xwOBA - 序盤 (1回) <= -0.030。"""
    if stats.inning1_xwoba <= 0.0 or stats.inning7plus_xwoba <= 0.0:
        return False
    return (stats.inning7plus_xwoba - stats.inning1_xwoba) <= BLUE_LATE_XWOBA_IMPROVE


def _is_vs_top_hitters(stats: PitcherStats) -> bool:
    """対強打者◯: xwOBA上位打者への Pitching RV がプラス。"""
    return stats.rv_vs_top_hitters > BLUE_VS_TOP_HITTERS_RV_MIN


def _is_innings_relief(stats: PitcherStats) -> bool:
    """回またぎ◯: 救援での年間平均消化イニング >= 1.2。"""
    if stats.games_started >= stats.games or stats.games == 0:
        # 先発のみは対象外
        return False
    return stats.avg_relief_innings >= BLUE_RELIEF_AVG_INNINGS_MIN


def _is_multi_pitch_types(pitches: list[PitchAggregated]) -> bool:
    """球種多◯: 投球割合 5%以上の球種が 5つ以上。"""
    qualifying = [p for p in pitches if p.usage_pct >= BLUE_PITCH_USAGE_THRESHOLD]
    return len(qualifying) >= BLUE_MULTI_PITCH_TYPES_MIN


def _is_pickoff_maru(stats: PitcherStats) -> bool:
    """牽制◯: Pickoff回数がリーグトップ10%以内。"""
    return stats.pickoff_top10pct


def _is_first_inning_maru(stats: PitcherStats) -> bool:
    """立ち上がり◯: 1イニング目 被xwOBA <= .250。"""
    if stats.inning1_xwoba <= 0.0:
        return False
    return stats.inning1_xwoba <= BLUE_FIRST_INN_XWOBA_MAX


def _is_winning_streak(stats: PitcherStats) -> bool:
    """勝ちまくり: シーズン勝率 >= .750 (規定投球回以上)。"""
    if stats.wins + stats.losses == 0:
        return False
    win_pct = stats.win_pct if stats.win_pct > 0 else stats.wins / (stats.wins + stats.losses)
    return win_pct >= BLUE_WIN_PCT_MIN


def _is_natural_shoot(pitches: list[PitchAggregated]) -> bool:
    """ナチュシュ: FB Horizontal Break が利き手側に +8インチ以上。"""
    ff = next((p for p in pitches if p.pitch_type in ("FF", "FA")), None)
    if ff is None:
        return False
    return abs(ff.horizontal_break) >= BLUE_NATURAL_HB_MIN


def _is_cut_slider(pitches: list[PitchAggregated]) -> bool:
    """真っスラ: FB Horizontal Break がカット方向（利き手と逆）に -2インチ以上。"""
    ff = next((p for p in pitches if p.pitch_type in ("FF", "FA")), None)
    if ff is None:
        return False
    # カット方向は利き手と逆の符号。簡略化のため絶対値が小さい OR 反転の HB を判定
    # 通常右投手は HB+（シュート方向）、カット方向は負値となる
    return ff.horizontal_break <= -BLUE_CUTTER_HB_MIN
