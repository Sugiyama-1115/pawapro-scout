"""
assess/batter/blue_special.py
野手の青特殊能力を査定する（新基準 r1 - 43種）。

判定指標は config.py の BLUE_*/POWER_/AVG_/PULL_/OPPO_ 定数に集約。
データ未取得の指標は付与しない（return False）。
"""

from __future__ import annotations

from pawapro_scout.config import (
    AVG_HITTER_XBA_MIN,
    BLUE_BASES_LOADED_AVG_MIN,
    BLUE_BREAKING_RV_MIN,
    BLUE_BUNT_MARU_MIN,
    BLUE_BUNT_MASTER_MIN,
    BLUE_CHANCE_MAKER_OBP_MIN,
    BLUE_DAMEOSHI_WOBA_MIN,
    BLUE_FASTBALL_RV_MIN,
    BLUE_FIELDING_OAA_MIN,
    BLUE_GYAKKYO_AVG_MIN,
    BLUE_HATSU_OPS_MIN,
    BLUE_HATSU_WOBA_MIN,
    BLUE_HOME_DEFEND_BLOCKING_MIN,
    BLUE_HOME_RUSH_SPEED_MIN,
    BLUE_IBUSHIGIN_XBA_MIN,
    BLUE_INFIELD_HIT_TIME_MAX,
    BLUE_KYUCHI_WOBA_MIN,
    BLUE_LASER_BEAM_ARM_MIN,
    BLUE_LOWER_HR_MIN,
    BLUE_MULTI_HR_GAMES_MIN,
    BLUE_NAGASHI_PCT_MIN,
    BLUE_NEBARI_WHIFF_MAX,
    BLUE_PINCH_HIT_AVG_MIN,
    BLUE_PRESSURE_RUN_SPEED_MIN,
    BLUE_REVENGE_WOBA_IMPROVE,
    BLUE_VS_ACE_XBA_MIN,
    BLUE_WALKOFF_MIN,
    BLUE_ZONE_HITTER_XBA_MIN,
    BLUE_ZONE_HITTER_XSLG_MIN,
    HEADSLI_SPEED_MIN,
    INITIAL_BALL_O_AVG_DIFF,
    LINEDRIVE_PCT_MIN,
    MULTI_HIT_GAME_MIN,
    OPPO_HR_MIN,
    POWER_HITTER_BARREL_MIN,
    POWER_HITTER_HR_MIN,
    PULL_HR_PCT_MIN,
)
from pawapro_scout.models import BatterStats


def assess_blue_special(stats: BatterStats) -> list[str]:
    """BatterStats から獲得する青特リストを返す（新基準 r1 - 43種）。"""
    result: list[str] = []

    if _is_shokyu(stats):
        result.append("初球◯")
    if _is_nebari(stats):
        result.append("粘り打ち")
    if _is_cut_uchi(stats):
        result.append("カット打ち")
    if _is_katamari_uchi(stats):
        result.append("固め打ち")
    if _is_dameoshi(stats):
        result.append("ダメ押し")
    if _is_outcourse_hitter(stats):
        result.append("アウトコースヒッター")
    if _is_incourse_hitter(stats):
        result.append("インコースヒッター")
    if _is_vs_ace(stats):
        result.append("対エース◯")
    if _is_headsli(stats):
        result.append("ヘッドスライディング")
    if _is_igaisei(stats):
        result.append("意外性")
    if _is_kyuchi(stats):
        result.append("窮地◯")
    if _is_vs_fastball(stats):
        result.append("対ストレート◯")
    if _is_multi_dan(stats):
        result.append("マルチ弾")
    if _is_bunt_maru(stats):
        result.append("バント◯")
    if _is_bunt_master(stats):
        result.append("バント職人")
    if _is_fast_charge(stats):
        result.append("高速チャージ")
    if _is_nagashi_uchi(stats):
        result.append("流し打ち")
    if _is_avg_hitter(stats):
        result.append("アベレージヒッター")
    if _is_laser_beam(stats):
        result.append("レーザービーム")
    if _is_power_hitter(stats):
        result.append("パワーヒッター")
    if _is_pull_hitter(stats):
        result.append("プルヒッター")
    if _is_line_drive(stats):
        result.append("ラインドライブ")
    if _is_high_ball_hitter(stats):
        result.append("ハイボールヒッター")
    if _is_gyakkyo(stats):
        result.append("逆境◯")
    if _is_ibushigin(stats):
        result.append("いぶし銀")
    if _is_fielding_pro(stats):
        result.append("守備職人")
    if _is_kakuran(stats):
        result.append("かく乱")
    if _is_revenge(stats):
        result.append("リベンジ")
    if _is_pressure_batter(stats):
        result.append("威圧感")
    if _is_chance_maker(stats):
        result.append("チャンスメーカー")
    if _is_home_rush(stats):
        result.append("ホーム突入")
    if _is_infield_hit_maru(stats):
        result.append("内野安打◯")
    if _is_pinch_hit_maru(stats):
        result.append("代打◯")
    if _is_low_ball_hitter(stats):
        result.append("ローボールヒッター")
    # 35. 決勝打: 6回以降・決勝場面の安打数がリーグ上位15% → closing_hits_top15 フラグで判定
    if _is_kesshoda(stats):
        result.append("決勝打")
    if _is_pressure_run(stats):
        result.append("プレッシャーラン")
    if _is_vs_breaking(stats):
        result.append("対変化球◯")
    if _is_home_defend(stats):
        result.append("ホーム死守")
    if _is_sayonara(stats):
        result.append("サヨナラ男")
    if _is_bases_loaded(stats):
        result.append("満塁男")
    if _is_zekkocho(stats):
        result.append("絶好調男")
    if _is_mood_maru(stats):
        result.append("ムード◯")
    if _is_koukauku(stats):
        result.append("広角打法")

    return result


# ──────────────────────────────────────────────
# 各青特の判定
# ──────────────────────────────────────────────

def _is_shokyu(stats: BatterStats) -> bool:
    """初球◯: 0ストライク時の打率 - 通算打率 >= +.050。"""
    if stats.count0_avg <= 0.0 or stats.season_avg <= 0.0:
        return False
    return (stats.count0_avg - stats.season_avg) >= INITIAL_BALL_O_AVG_DIFF


def _is_nebari(stats: BatterStats) -> bool:
    """粘り打ち: 2ストライク Whiff% <= 22.0%。"""
    if stats.count2_whiff <= 0.0:
        return False
    return stats.count2_whiff <= BLUE_NEBARI_WHIFF_MAX


def _is_cut_uchi(stats: BatterStats) -> bool:
    """カット打ち: Foul% リーグ上位15%以内。"""
    return stats.foul_pct_top15


def _is_katamari_uchi(stats: BatterStats) -> bool:
    """固め打ち: 1試合3安打以上の試合 >= 6回。"""
    return stats.multi_hit_game_count >= MULTI_HIT_GAME_MIN


def _is_dameoshi(stats: BatterStats) -> bool:
    """ダメ押し: 4点リード時・終盤 wOBA >= .380。"""
    if stats.big_lead_late_woba <= 0.0:
        return False
    return stats.big_lead_late_woba >= BLUE_DAMEOSHI_WOBA_MIN


def _is_outcourse_hitter(stats: BatterStats) -> bool:
    """アウトコースヒッター: 外角 xBA >= .290 + xSLG >= .500。"""
    return (
        stats.outside_xba >= BLUE_ZONE_HITTER_XBA_MIN
        and stats.outside_xslg >= BLUE_ZONE_HITTER_XSLG_MIN
    )


def _is_incourse_hitter(stats: BatterStats) -> bool:
    """インコースヒッター: 内角 xBA >= .290 + xSLG >= .500。"""
    return (
        stats.inside_xba >= BLUE_ZONE_HITTER_XBA_MIN
        and stats.inside_xslg >= BLUE_ZONE_HITTER_XSLG_MIN
    )


def _is_vs_ace(stats: BatterStats) -> bool:
    """対エース◯: 対エース級投手 xBA >= .270。"""
    if stats.vs_ace_xba <= 0.0:
        return False
    return stats.vs_ace_xba >= BLUE_VS_ACE_XBA_MIN


def _is_headsli(stats: BatterStats) -> bool:
    """ヘッドスライディング: Sprint Speed >= 28.5。"""
    return stats.sprint_speed >= HEADSLI_SPEED_MIN


def _is_igaisei(stats: BatterStats) -> bool:
    """意外性: 下位打線でのHR >= 6本。"""
    return stats.lower_lineup_hr >= BLUE_LOWER_HR_MIN


def _is_kyuchi(stats: BatterStats) -> bool:
    """窮地◯: 2ストライク wOBA >= .320。"""
    if stats.count2_woba <= 0.0:
        return False
    return stats.count2_woba >= BLUE_KYUCHI_WOBA_MIN


def _is_vs_fastball(stats: BatterStats) -> bool:
    """対ストレート◯: Fastball Run Value >= +10。"""
    return stats.fastball_run_value >= BLUE_FASTBALL_RV_MIN


def _is_multi_dan(stats: BatterStats) -> bool:
    """マルチ弾: 2HR以上の試合が 3回以上。"""
    return stats.multi_hr_games >= BLUE_MULTI_HR_GAMES_MIN


def _is_bunt_maru(stats: BatterStats) -> bool:
    """バント◯: 犠打成功 3本以上 6本未満。"""
    return BLUE_BUNT_MARU_MIN <= stats.sh < BLUE_BUNT_MASTER_MIN


def _is_bunt_master(stats: BatterStats) -> bool:
    """バント職人: 犠打成功 6本以上。"""
    return stats.sh >= BLUE_BUNT_MASTER_MIN


def _is_fast_charge(stats: BatterStats) -> bool:
    """高速チャージ: 内野手 OAA (Coming In) 評価が優秀 (+3 以上)。"""
    if stats.oaa_coming_in is None:
        return False
    return stats.oaa_coming_in >= 3


def _is_nagashi_uchi(stats: BatterStats) -> bool:
    """流し打ち: 逆方向への安打割合 >= 33%。"""
    if stats.oppo_hits_pct <= 0.0:
        return False
    return stats.oppo_hits_pct >= BLUE_NAGASHI_PCT_MIN


def _is_avg_hitter(stats: BatterStats) -> bool:
    """アベレージヒッター: 通算 xBA >= .285。"""
    return stats.xba >= AVG_HITTER_XBA_MIN


def _is_laser_beam(stats: BatterStats) -> bool:
    """レーザービーム: 外野送球速度 >= 93mph。"""
    if stats.arm_strength_of_mph is None:
        return False
    return stats.arm_strength_of_mph >= BLUE_LASER_BEAM_ARM_MIN


def _is_power_hitter(stats: BatterStats) -> bool:
    """パワーヒッター: HR >= 22 + Barrel% >= 12%。"""
    return (
        stats.home_runs >= POWER_HITTER_HR_MIN
        and stats.barrel_percent >= POWER_HITTER_BARREL_MIN
    )


def _is_pull_hitter(stats: BatterStats) -> bool:
    """プルヒッター: 引っ張り方向 HR% >= 55%。"""
    return stats.pull_hr_pct >= PULL_HR_PCT_MIN


def _is_line_drive(stats: BatterStats) -> bool:
    """ラインドライブ: 打球角度 8〜14度 の打球割合 >= 25%。データ未取得時は付与しない。"""
    if stats.linedrive_pct <= 0.0:
        return False
    return stats.linedrive_pct >= LINEDRIVE_PCT_MIN


def _is_high_ball_hitter(stats: BatterStats) -> bool:
    """ハイボールヒッター: 高め xBA >= .290 + xSLG >= .500。"""
    return (
        stats.high_xba >= BLUE_ZONE_HITTER_XBA_MIN
        and stats.high_xslg >= BLUE_ZONE_HITTER_XSLG_MIN
    )


def _is_gyakkyo(stats: BatterStats) -> bool:
    """逆境◯: 7回以降・負け状況打率 >= .290。"""
    if stats.late_losing_avg <= 0.0:
        return False
    return stats.late_losing_avg >= BLUE_GYAKKYO_AVG_MIN


def _is_ibushigin(stats: BatterStats) -> bool:
    """いぶし銀: 終盤・得点圏・1点差 xBA >= .320。"""
    if stats.late_close_xba <= 0.0:
        return False
    return stats.late_close_xba >= BLUE_IBUSHIGIN_XBA_MIN


def _is_fielding_pro(stats: BatterStats) -> bool:
    """守備職人: OAA >= +7。"""
    return stats.oaa >= BLUE_FIELDING_OAA_MIN


def _is_kakuran(stats: BatterStats) -> bool:
    """かく乱: 盗塁企図数が多い (簡略: SB + CS >= 25)。"""
    return (stats.sb + stats.cs) >= 25


def _is_revenge(stats: BatterStats) -> bool:
    """リベンジ: 同一試合次打席の wOBA が前打席より大幅改善。"""
    return stats.same_game_next_pa_woba_improve >= BLUE_REVENGE_WOBA_IMPROVE


def _is_pressure_batter(stats: BatterStats) -> bool:
    """威圧感（野手）: OPS >= .950 or wOBA >= .400。"""
    return stats.ops >= BLUE_HATSU_OPS_MIN or stats.woba >= BLUE_HATSU_WOBA_MIN


def _is_chance_maker(stats: BatterStats) -> bool:
    """チャンスメーカー: 走者なし OBP >= .360。"""
    if stats.bases_empty_obp <= 0.0:
        return False
    return stats.bases_empty_obp >= BLUE_CHANCE_MAKER_OBP_MIN


def _is_home_rush(stats: BatterStats) -> bool:
    """ホーム突入: Sprint Speed >= 28.0。"""
    return stats.sprint_speed >= BLUE_HOME_RUSH_SPEED_MIN


def _is_infield_hit_maru(stats: BatterStats) -> bool:
    """内野安打◯: Home to First タイム <= 4.25秒。"""
    if stats.home_to_first_sec is None:
        return False
    return stats.home_to_first_sec <= BLUE_INFIELD_HIT_TIME_MAX


def _is_pinch_hit_maru(stats: BatterStats) -> bool:
    """代打◯: 代打打率 >= .270。"""
    if stats.pinch_hit_pa < 20 or stats.pinch_hit_avg <= 0.0:
        return False
    return stats.pinch_hit_avg >= BLUE_PINCH_HIT_AVG_MIN


def _is_low_ball_hitter(stats: BatterStats) -> bool:
    """ローボールヒッター: 低め xBA >= .290 + xSLG >= .500。"""
    return (
        stats.low_xba >= BLUE_ZONE_HITTER_XBA_MIN
        and stats.low_xslg >= BLUE_ZONE_HITTER_XSLG_MIN
    )


def _is_kesshoda(stats: BatterStats) -> bool:
    """決勝打: 6回以降・決勝場面の安打数がリーグ上位15%。"""
    return stats.closing_hits_top15


def _is_pressure_run(stats: BatterStats) -> bool:
    """プレッシャーラン: Sprint Speed >= 28.5。"""
    return stats.sprint_speed >= BLUE_PRESSURE_RUN_SPEED_MIN


def _is_vs_breaking(stats: BatterStats) -> bool:
    """対変化球◯: Breaking/Offspeed Run Value >= +8。"""
    return stats.breaking_run_value >= BLUE_BREAKING_RV_MIN


def _is_home_defend(stats: BatterStats) -> bool:
    """ホーム死守: Blocks Above Average >= +5 (捕手)。"""
    if stats.blocking_runs is None:
        return False
    return stats.blocking_runs >= BLUE_HOME_DEFEND_BLOCKING_MIN


def _is_sayonara(stats: BatterStats) -> bool:
    """サヨナラ男: サヨナラ打 >= 1回。"""
    return stats.walk_off_hits >= BLUE_WALKOFF_MIN


def _is_bases_loaded(stats: BatterStats) -> bool:
    """満塁男: 満塁時打率 >= .320。"""
    if stats.bases_loaded_avg <= 0.0:
        return False
    return stats.bases_loaded_avg >= BLUE_BASES_LOADED_AVG_MIN


def _is_zekkocho(stats: BatterStats) -> bool:
    """絶好調男: チーム内 wOBA 1位。"""
    return stats.is_team_woba_leader


def _is_mood_maru(stats: BatterStats) -> bool:
    """ムード◯: チーム貢献度(WPA)がプラス。"""
    return stats.wpa > 0.0


def _is_koukauku(stats: BatterStats) -> bool:
    """広角打法: 逆方向HR >= 4本。"""
    return stats.oppo_hr_count >= OPPO_HR_MIN
