"""
assess/batter/gold_special.py
野手の金特殊能力を査定する（新基準 r1 - 34種 + 捕手専用4種）。

判定指標は config.py の GOLD_* 定数に集約。
データ未取得の指標は付与しない（return False）。
"""

from __future__ import annotations

from pawapro_scout.config import (
    GOLD_ACE_KILLER_XBA_MIN,
    GOLD_ARCHIST_BARREL_MIN,
    GOLD_ARCHIST_LA_MAX,
    GOLD_ARCHIST_LA_MIN,
    GOLD_BASES_LOADED_XSLG_MIN,
    GOLD_BAZOOKA_POP_TIME_MAX,
    GOLD_CATCHER_BRAIN_FRV_MIN,
    GOLD_DENKOSEKKA_SB_MIN,
    GOLD_DENKOSEKKA_SPEED_MIN,
    GOLD_FAST_BASERUN_XBT_MIN,
    GOLD_FAST_LASER_ARM_MIN,
    GOLD_FIRST_PITCH_XBA_MIN,
    GOLD_FIRST_PITCH_XSLG_MIN,
    GOLD_GYAKUSHU_XBA_IMPROVE,
    GOLD_HEATUP_XBA_MIN,
    GOLD_HEATUP_XSLG_MIN,
    GOLD_HIT_MACHINE_WHIFF_MAX,
    GOLD_HIT_MACHINE_XBA_MIN,
    GOLD_IRON_GAMES_MIN,
    GOLD_IRON_IL_MAX,
    GOLD_IRON_WALL_BLOCKING_MIN,
    GOLD_KAJIBA_XSLG_MIN,
    GOLD_KESSHODA_XBA_MIN,
    GOLD_KIHAKU_INFIELD_HITS_MIN,
    GOLD_KIHAKU_SPEED_MIN,
    GOLD_LEADOFF_OBP_MIN,
    GOLD_LEGEND_WALKOFF_MIN,
    GOLD_LHP_KILLER_DIFF,
    GOLD_LHP_KILLER_XBA_MIN,
    GOLD_MAGICIAN_OAA_MIN,
    GOLD_METTA_GAMES_MIN,
    GOLD_OPPO_ART_HITS_MIN,
    GOLD_OPPO_ART_XBA_MIN,
    GOLD_OPPO_HR_KING_HR_MIN,
    GOLD_OPPO_HR_KING_XSLG_MIN,
    GOLD_PILLAR_WPA_MIN,
    GOLD_PINCH_HIT_GOD_HR_MIN,
    GOLD_PINCH_HIT_GOD_XBA_MIN,
    GOLD_PULL_KING_HR_PCT_MIN,
    GOLD_PULL_KING_XSLG_MIN,
    GOLD_ROCKET_START_TIME_MAX,
    GOLD_SHOBUSHI_DIFF_MIN,
    GOLD_SHOBUSHI_XBA_MIN,
    GOLD_STRIKE_THROW_ARM_RV_MIN,
    GOLD_TANK_SCORE_RATE_MIN,
    GOLD_TANK_SPEED_MIN,
    GOLD_TRICKSTER_BSR_MIN,
    GOLD_TRICKSTER_SB_PCT_MIN,
    GOLD_UPSET_CLUTCH_EV_MIN,
    GOLD_UPSET_POWER_MAX_MEV,
    GOLD_VETERAN_AGE_MIN,
    GOLD_WHISPER_FRAMING_MIN,
    GOLD_ZONE_HITTER_XBA_MIN,
    GOLD_ZONE_HITTER_XSLG_MIN,
)
from pawapro_scout.models import BatterStats


def assess_gold_special(stats: BatterStats, *, age: int = 0, position: str = "") -> list[str]:
    """BatterStats から獲得する金特リストを返す（新基準 r1）。

    age と position はオプション。
    age は ささやき戦術用、position は捕手/内野手/外野手の判定に使う。
    """
    result: list[str] = []

    if _is_one_pitch_soul(stats):
        result.append("一球入魂")
    if _is_metta(stats):
        result.append("メッタ打ち")
    if _is_outside_hit(stats):
        result.append("外角必打")
    if _is_inside_hit(stats):
        result.append("内角必打")
    if _is_ace_killer(stats):
        result.append("エースキラー")
    if _is_kihaku_head(stats):
        result.append("気迫ヘッド")
    if _is_legend_walkoff(stats):
        result.append("伝説のサヨナラ男")
    if _is_upset(stats):
        result.append("大番狂わせ")
    if _is_heatup(stats):
        result.append("ヒートアップ")
    if _is_oppo_art(stats):
        result.append("芸術的流し打ち")
    if _is_hit_machine(stats):
        result.append("安打製造機")
    if _is_iron_man(stats):
        result.append("鉄人")
    if _is_fast_laser(stats, position):
        result.append("高速レーザー")
    if _is_archist(stats):
        result.append("アーチスト")
    if _is_pull_king(stats):
        result.append("引っ張り屋")
    if _is_high_hit(stats):
        result.append("高球必打")
    if _is_lhp_killer(stats):
        result.append("左腕キラー")
    if _is_kajiba(stats):
        result.append("火事場の馬鹿力")
    if _is_magician(stats, position):
        result.append("魔術師")
    if _is_trickster(stats):
        result.append("トリックスター")
    if _is_gyakushu(stats):
        result.append("逆襲")
    if _is_leadoff(stats):
        result.append("切り込み隊長")
    if _is_fast_baserun(stats):
        result.append("高速ベースラン")
    if _is_strike_throw(stats):
        result.append("ストライク送球")
    if _is_rocket_start(stats):
        result.append("ロケットスタート")
    if _is_pinch_hit_god(stats):
        result.append("代打の神様")
    if _is_low_hit(stats):
        result.append("低球必打")
    if _is_denkosekka(stats):
        result.append("電光石火")
    if _is_kesshoda_gold(stats):
        result.append("渾身の決勝打")
    if _is_shobushi(stats):
        result.append("勝負師")
    if _is_juusensha(stats):
        result.append("重戦車")
    if _is_bases_loaded_man(stats):
        result.append("恐怖の満塁男")
    if _is_pillar(stats):
        result.append("精神的支柱")
    if _is_oppo_hr_king(stats):
        result.append("広角砲")

    # 捕手専用金特
    if position == "C":
        if _is_catcher_brain(stats):
            result.append("球界の頭脳")
        if _is_whisper(stats, age):
            result.append("ささやき戦術")
        if _is_iron_wall(stats):
            result.append("鉄の壁")
        if _is_bazooka(stats):
            result.append("バズーカ送球")

    return result


# ──────────────────────────────────────────────
# 各金特の判定
# ──────────────────────────────────────────────

def _is_one_pitch_soul(stats: BatterStats) -> bool:
    """一球入魂: 0ストライク xBA >= .340 or xSLG >= .630。"""
    return (
        stats.count0_xba >= GOLD_FIRST_PITCH_XBA_MIN
        or stats.count0_xslg >= GOLD_FIRST_PITCH_XSLG_MIN
    )


def _is_metta(stats: BatterStats) -> bool:
    """メッタ打ち: 3安打試合 >= 10回。"""
    return stats.multi_hit_game_count >= GOLD_METTA_GAMES_MIN


def _is_outside_hit(stats: BatterStats) -> bool:
    """外角必打: 外角 xBA >= .315 + xSLG >= .530。"""
    return (
        stats.outside_xba >= GOLD_ZONE_HITTER_XBA_MIN
        and stats.outside_xslg >= GOLD_ZONE_HITTER_XSLG_MIN
    )


def _is_inside_hit(stats: BatterStats) -> bool:
    """内角必打: 内角 xBA >= .315 + xSLG >= .530。"""
    return (
        stats.inside_xba >= GOLD_ZONE_HITTER_XBA_MIN
        and stats.inside_xslg >= GOLD_ZONE_HITTER_XSLG_MIN
    )


def _is_ace_killer(stats: BatterStats) -> bool:
    """エースキラー: 対上位投手 xBA >= .295。"""
    if stats.vs_ace_xba <= 0.0:
        return False
    return stats.vs_ace_xba >= GOLD_ACE_KILLER_XBA_MIN


def _is_kihaku_head(stats: BatterStats) -> bool:
    """気迫ヘッド: Sprint Speed >= 29.0 + 内野安打 >= 12。"""
    return (
        stats.sprint_speed >= GOLD_KIHAKU_SPEED_MIN
        and stats.infield_hits >= GOLD_KIHAKU_INFIELD_HITS_MIN
    )


def _is_legend_walkoff(stats: BatterStats) -> bool:
    """伝説のサヨナラ男: サヨナラ打 >= 2回。"""
    return stats.walk_off_hits >= GOLD_LEGEND_WALKOFF_MIN


def _is_upset(stats: BatterStats) -> bool:
    """大番狂わせ: 基礎パワー C以下 + 接戦時 Max EV >= 111mph。"""
    return (
        stats.max_exit_velocity > 0
        and stats.max_exit_velocity <= GOLD_UPSET_POWER_MAX_MEV
        and stats.clutch_max_ev >= GOLD_UPSET_CLUTCH_EV_MIN
    )


def _is_heatup(stats: BatterStats) -> bool:
    """ヒートアップ: 2ストライク xBA >= .265 + xSLG >= .470。"""
    return (
        stats.count2_xba >= GOLD_HEATUP_XBA_MIN
        and stats.count2_xslg >= GOLD_HEATUP_XSLG_MIN
    )


def _is_oppo_art(stats: BatterStats) -> bool:
    """芸術的流し打ち: 逆方向安打 >= 40 + Oppo xBA >= .325。"""
    return (
        stats.oppo_hits >= GOLD_OPPO_ART_HITS_MIN
        and stats.oppo_xba >= GOLD_OPPO_ART_XBA_MIN
    )


def _is_hit_machine(stats: BatterStats) -> bool:
    """安打製造機: 通算 xBA >= .300 + Whiff% <= 19.0%。"""
    return (
        stats.xba >= GOLD_HIT_MACHINE_XBA_MIN
        and 0 < stats.whiff_percent <= GOLD_HIT_MACHINE_WHIFF_MAX
    )


def _is_iron_man(stats: BatterStats) -> bool:
    """鉄人: 155試合以上 + IL入り過去2年 <= 1回。"""
    return (
        stats.games >= GOLD_IRON_GAMES_MIN
        and stats.il_count_2y <= GOLD_IRON_IL_MAX
    )


def _is_fast_laser(stats: BatterStats, position: str) -> bool:
    """高速レーザー: 外野手 Arm Strength >= 96mph。"""
    if position not in ("LF", "CF", "RF", "OF"):
        return False
    arm = stats.arm_strength_of_mph or stats.arm_strength_mph
    if arm is None:
        return False
    return arm >= GOLD_FAST_LASER_ARM_MIN


def _is_archist(stats: BatterStats) -> bool:
    """アーチスト: Barrel% >= 16.5% + 平均打球角度 13〜23度。"""
    return (
        stats.barrel_percent >= GOLD_ARCHIST_BARREL_MIN
        and GOLD_ARCHIST_LA_MIN <= stats.avg_launch_angle <= GOLD_ARCHIST_LA_MAX
    )


def _is_pull_king(stats: BatterStats) -> bool:
    """引っ張り屋: Pull xSLG >= .830 + 本塁打の7割以上 Pull。"""
    return (
        stats.pull_xslg >= GOLD_PULL_KING_XSLG_MIN
        and stats.pull_hr_pct >= GOLD_PULL_KING_HR_PCT_MIN
    )


def _is_high_hit(stats: BatterStats) -> bool:
    """高球必打: 高め xBA >= .315 + xSLG >= .530。"""
    return (
        stats.high_xba >= GOLD_ZONE_HITTER_XBA_MIN
        and stats.high_xslg >= GOLD_ZONE_HITTER_XSLG_MIN
    )


def _is_lhp_killer(stats: BatterStats) -> bool:
    """左腕キラー: 対左 xBA - 対右 xBA >= +.055 + 対左 xBA >= .310。"""
    if stats.vs_lhp_xba <= 0.0 or stats.vs_rhp_xba <= 0.0:
        return False
    return (
        (stats.vs_lhp_xba - stats.vs_rhp_xba) >= GOLD_LHP_KILLER_DIFF
        and stats.vs_lhp_xba >= GOLD_LHP_KILLER_XBA_MIN
    )


def _is_kajiba(stats: BatterStats) -> bool:
    """火事場の馬鹿力: 7回以降・負け状況 xSLG >= .640。"""
    if stats.late_losing_xslg <= 0.0:
        return False
    return stats.late_losing_xslg >= GOLD_KAJIBA_XSLG_MIN


def _is_magician(stats: BatterStats, position: str) -> bool:
    """魔術師: 内野手 OAA >= +12。"""
    if position not in ("1B", "2B", "3B", "SS", "IF"):
        return False
    return stats.oaa >= GOLD_MAGICIAN_OAA_MIN


def _is_trickster(stats: BatterStats) -> bool:
    """トリックスター: Baserunning RV >= +4 + 盗塁成功率 >= 88%。"""
    if stats.baserunning_run_value is None:
        return False
    total = stats.sb + stats.cs
    if total == 0:
        return False
    sb_pct = stats.sb / total
    return (
        stats.baserunning_run_value >= GOLD_TRICKSTER_BSR_MIN
        and sb_pct >= GOLD_TRICKSTER_SB_PCT_MIN
    )


def _is_gyakushu(stats: BatterStats) -> bool:
    """逆襲: 同一投手 2打席目以降の xBA 改善 >= +.060。"""
    return stats.same_pitcher_2nd_xba_improve >= GOLD_GYAKUSHU_XBA_IMPROVE


def _is_leadoff(stats: BatterStats) -> bool:
    """切り込み隊長: 走者なし OBP >= .385。"""
    if stats.bases_empty_obp <= 0.0:
        return False
    return stats.bases_empty_obp >= GOLD_LEADOFF_OBP_MIN


def _is_fast_baserun(stats: BatterStats) -> bool:
    """高速ベースラン: XBT% >= 58%。"""
    return stats.xbt_percent >= GOLD_FAST_BASERUN_XBT_MIN


def _is_strike_throw(stats: BatterStats) -> bool:
    """ストライク送球: Fielding Run Value (Arm) >= +4。"""
    if stats.arm_run_value is None:
        return False
    return stats.arm_run_value >= GOLD_STRIKE_THROW_ARM_RV_MIN


def _is_rocket_start(stats: BatterStats) -> bool:
    """ロケットスタート: Home to First タイム <= 4.15秒。"""
    if stats.home_to_first_sec is None:
        return False
    return stats.home_to_first_sec <= GOLD_ROCKET_START_TIME_MAX


def _is_pinch_hit_god(stats: BatterStats) -> bool:
    """代打の神様: 代打 xBA >= .340 + 代打HR >= 2本。"""
    if stats.pinch_hit_pa < 20:
        return False
    return (
        stats.pinch_hit_xba >= GOLD_PINCH_HIT_GOD_XBA_MIN
        and stats.pinch_hit_hr >= GOLD_PINCH_HIT_GOD_HR_MIN
    )


def _is_low_hit(stats: BatterStats) -> bool:
    """低球必打: 低め xBA >= .315 + xSLG >= .530。"""
    return (
        stats.low_xba >= GOLD_ZONE_HITTER_XBA_MIN
        and stats.low_xslg >= GOLD_ZONE_HITTER_XSLG_MIN
    )


def _is_denkosekka(stats: BatterStats) -> bool:
    """電光石火: Sprint Speed >= 29.8 + 盗塁数 >= 35。"""
    return (
        stats.sprint_speed >= GOLD_DENKOSEKKA_SPEED_MIN
        and stats.sb >= GOLD_DENKOSEKKA_SB_MIN
    )


def _is_kesshoda_gold(stats: BatterStats) -> bool:
    """渾身の決勝打: 6回以降・決勝場面 xBA >= .340。"""
    if stats.closing_inning_xba <= 0.0:
        return False
    return stats.closing_inning_xba >= GOLD_KESSHODA_XBA_MIN


def _is_shobushi(stats: BatterStats) -> bool:
    """勝負師: 得点圏 xBA - 通常 xBA >= +.065 + 得点圏 xBA >= .325。"""
    if stats.risp_xba <= 0.0 or stats.xba <= 0.0:
        return False
    return (
        (stats.risp_xba - stats.xba) >= GOLD_SHOBUSHI_DIFF_MIN
        and stats.risp_xba >= GOLD_SHOBUSHI_XBA_MIN
    )


def _is_juusensha(stats: BatterStats) -> bool:
    """重戦車: 本塁突入時の生還率 >= 95% + Sprint Speed >= 28.5。"""
    return (
        stats.home_running_score_rate >= GOLD_TANK_SCORE_RATE_MIN
        and stats.sprint_speed >= GOLD_TANK_SPEED_MIN
    )


def _is_bases_loaded_man(stats: BatterStats) -> bool:
    """恐怖の満塁男: 満塁時 xSLG >= .880。"""
    if stats.bases_loaded_xslg <= 0.0:
        return False
    return stats.bases_loaded_xslg >= GOLD_BASES_LOADED_XSLG_MIN


def _is_pillar(stats: BatterStats) -> bool:
    """精神的支柱: チーム内 WPA 1位 + WPA >= +4.0。"""
    return (
        stats.is_team_wpa_leader
        and stats.wpa >= GOLD_PILLAR_WPA_MIN
    )


def _is_oppo_hr_king(stats: BatterStats) -> bool:
    """広角砲: 逆方向 HR >= 10 + Oppo xSLG >= .580。"""
    return (
        stats.oppo_hr_count >= GOLD_OPPO_HR_KING_HR_MIN
        and stats.oppo_xslg >= GOLD_OPPO_HR_KING_XSLG_MIN
    )


# ──────────────────────────────────────────────
# 捕手専用金特
# ──────────────────────────────────────────────

def _is_catcher_brain(stats: BatterStats) -> bool:
    """球界の頭脳: Fielding Run Value (Catcher) >= +10。"""
    return stats.fielding_run_value >= GOLD_CATCHER_BRAIN_FRV_MIN


def _is_whisper(stats: BatterStats, age: int) -> bool:
    """ささやき戦術: 33歳以上 + Catcher Framing >= +8。"""
    if age < GOLD_VETERAN_AGE_MIN or stats.framing_runs is None:
        return False
    return stats.framing_runs >= GOLD_WHISPER_FRAMING_MIN


def _is_iron_wall(stats: BatterStats) -> bool:
    """鉄の壁: Blocks Above Average >= +8。"""
    if stats.blocking_runs is None:
        return False
    return stats.blocking_runs >= GOLD_IRON_WALL_BLOCKING_MIN


def _is_bazooka(stats: BatterStats) -> bool:
    """バズーカ送球: Pop Time (2B) <= 1.88秒。"""
    if stats.pop_time is None:
        return False
    return stats.pop_time <= GOLD_BAZOOKA_POP_TIME_MAX
