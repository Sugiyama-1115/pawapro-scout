"""
config.py
全プロジェクト共通の定数・閾値・URL定義。
アセッサーにマジックナンバーを書かず、すべてここから参照する。
"""

from pathlib import Path

# ────────────────────────────────────────────────
# パス
# ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent.parent  # pawapro-scout/
CACHE_DIR = PROJECT_ROOT / "cache"
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"

# ────────────────────────────────────────────────
# データソース URL
# ────────────────────────────────────────────────
SAVANT_STATCAST_CSV_URL = "https://baseballsavant.mlb.com/statcast_search/csv"
SAVANT_LEADERBOARD_BASE = "https://baseballsavant.mlb.com/leaderboard"
FANGRAPHS_SPLITS_URL = "https://www.fangraphs.com/api/leaders/splits/splits-leaders"

# Savant リーダーボード スラッグ
SAVANT_LEADERBOARD_SLUGS = {
    "catcher_framing": "catcher-framing",
    "catcher_blocking": "catcher-blocking",
    "catcher_throwing": "catcher-throwing",
    "pitcher_fielding": "pitcher-fielding",
    "pitch_arsenal": "pitch-arsenal-stats",
    "outfielder_throws": "arm-strength",          # 旧: outfielder-throws (404)
    "fielding_run_value": "fielding-run-value",
}

# FanGraphs Splits ID
FANGRAPHS_SPLIT_IDS = {
    "vs_lhp": 5,
    "vs_rhp": 6,
    "risp": 7,
    "bases_empty": 8,
    "high_lev": 11,
}

# ────────────────────────────────────────────────
# ネットワーク設定
# ────────────────────────────────────────────────
REQUEST_TIMEOUT = 60          # 秒
RETRY_MAX_ATTEMPTS = 4
RETRY_WAIT_MIN = 2            # 秒
RETRY_WAIT_MAX = 30           # 秒
BREF_SLEEP_SEC = 3            # bref へのリクエスト間隔

# ────────────────────────────────────────────────
# グレード共通ユーティリティ
# ────────────────────────────────────────────────
GRADES = ["S", "A", "B", "C", "D", "E", "F", "G"]


def score_to_grade(value: float, breakpoints: list[float]) -> str:
    """
    breakpoints (降順) と GRADES を対応させてランクを返す。
    例: score_to_grade(0.300, [0.310, 0.290, 0.270, 0.250, 0.230, 0.210, 0.190])
    """
    for threshold, grade in zip(breakpoints, GRADES):
        if value >= threshold:
            return grade
    return "G"


def percentile_to_grade(pct: int, breakpoints: list[int] | None = None) -> str:
    """パーセンタイル → グレード (デフォルト: OAA等の標準変換)"""
    bp = breakpoints or [99, 90, 75, 50, 35, 20, 5]
    return score_to_grade(float(pct), [float(b) for b in bp])


# ────────────────────────────────────────────────
# 野手 基礎能力 閾値
# ────────────────────────────────────────────────

# 弾道: 平均打球角度 (度)
TRAJECTORY_BREAKPOINTS = [18.1, 12.1, 5.0]          # → 4, 3, 2, 1
SWEET_SPOT_MIN_FOR_3 = 35.0                          # sweet_spot% がこれ以上なら弾道は最低3

# ミート: xBA 直接値（.300 以上=S, .280-.299=A, .260-.279=B, .240-.259=C, .220-.239=D, .200-.219=E, .190-.199=F, .189 以下=G）
MEET_BREAKPOINTS = [0.300, 0.280, 0.260, 0.240, 0.220, 0.200, 0.190]

# パワー: Max Exit Velocity (mph)
POWER_BREAKPOINTS = [118.0, 112.0, 108.0, 104.0, 100.0, 96.0, 90.0]

# 走力: Sprint Speed (ft/sec)
SPEED_BREAKPOINTS = [30.0, 29.0, 28.0, 27.0, 26.0, 25.0, 24.0]

# 肩力 外野手 (mph)
ARM_OF_BREAKPOINTS = [98.0, 93.0, 88.0, 83.0, 78.0, 73.0, 68.0]

# 肩力 内野手 SS/3B (mph)
ARM_IF_BREAKPOINTS = [93.0, 88.0, 83.0, 78.0, 73.0, 68.0, 63.0]

# 捕手 Pop Time (秒, 小さいほど良い → 逆変換して使う)
# pop_time <= 1.85 → S, >= 2.05 → E以下
POP_TIME_BREAKPOINTS = [1.85, 1.90, 1.95, 2.00, 2.05, 2.10, 2.20]  # 昇順(秒)
POP_TIME_GRADES = ["S", "A", "B", "C", "D", "E", "F", "G"]

# 守備力: OAA パーセンタイル
FIELDING_PERCENTILE_BREAKPOINTS = [99, 90, 75, 50, 35, 20, 5]

# ────────────────────────────────────────────────
# 投手 基礎能力 閾値
# ────────────────────────────────────────────────

# コントロール: Zone% + (15 - BB%) の複合指標 (降順)
# S>=65 / A>=60 / B>=55 / C>=50 / D>=45 / E>=40 / F>=35 / G<35
CONTROL_BREAKPOINTS = [65.0, 60.0, 55.0, 50.0, 45.0, 40.0, 35.0]

# スタミナ: 1試合あたりの平均投球数 (pitch_count / p_game) — 先発・救援共通
# S: 95+, A: 85-94, B: 75-84, C: 65-74, D: 45-64, E: 0-44
STAMINA_PITCHERS_BREAKPOINTS = [95.0, 85.0, 75.0, 65.0, 45.0, 0.0]

# ────────────────────────────────────────────────
# 変化球 分類
# ────────────────────────────────────────────────

# Statcast pitch_type コード → family
PITCH_FAMILY_MAP: dict[str, str] = {
    "FF": "fastball",
    "FA": "fastball",
    "SI": "sinker_family",
    "FT": "sinker_family",
    "SL": "slider_family",
    "ST": "slider_family",   # Sweeper (Statcast 2023+)
    "SV": "slider_family",   # Slurve
    "FC": "cutter",
    "FS": "splitter_family",
    "FO": "splitter_family",
    "CH": "changeup",
    "CU": "curveball",
    "CS": "curveball",
    "KC": "curveball",
    "KN": "knuckleball",
    "EP": "eephus",
    "SC": "screwball",
    "UN": "unknown",
    "PO": "unknown",         # Pitch-out
}

# 変化量 (1-7) の Whiff% 閾値
WHIFF_TO_HENKA_BREAKPOINTS = [45.0, 35.0, 20.0, 15.0]  # 以上でそれぞれ 7, 5, 3, 1
WHIFF_TO_HENKA_VALUES = [7, 5, 3, 1]

# Run Value/100 による変化量 ±1 補正
# rv_per_100 は Savant 基準: 負 = 打者有利(投手にとって悪い球), 正 = 投手有利
# 基準書の RV/100 正 = 良い (投手視点) に合わせ、補正閾値を更新
RV_HENKA_BONUS_THRESHOLD = -2.5    # RV/100 < -2.5 → +1 (打者に強い良い球)
RV_HENKA_PENALTY_THRESHOLD = 1.6   # RV/100 > +1.6 → -1 (投手に不利な球)

# 球種採用基準
MIN_PITCH_USAGE_PCT = 5.0           # usage% がこれ未満の球種は採用しない

# スライダー系 分岐閾値
SLIDER_VH_HB_MAX = 4.0             # HB < 4.0 → Vスライダー
SLIDER_SWEEPER_HB_MIN = 15.0       # HB >= 15.0 かつ HB > |IVB| → スイーパー
SLIDER_H_DV_MAX = 5.0              # ΔV <= 5.0 → Hスライダー

# シンカー系 分岐閾値
SINKER_TS_DV_MAX = 2.0             # ΔV <= 2.0 かつ HB < 10 → ツーシーム
SINKER_TS_HB_MAX = 10.0
SINKER_HS_DV_MAX = 4.0             # ΔV <= 4.0 かつ HB >= 10 → 高速シンカー
SINKER_HS_HB_MIN = 10.0

# スプリット系 分岐閾値
SPLITTER_SFF_DV_MAX = 7.0          # ΔV < 7 → SFF, else フォーク

# チェンジアップ系 分岐閾値
CH_CIRCLE_DHB_MIN = 10.0           # |ΔHB| >= 10 → サークルチェンジ

# カッター 分岐閾値
CUTTER_BALL_HB_MAX = 5.0           # HB <= 5 → カットボール, else Hスライダー

# ────────────────────────────────────────────────
# 野手 特殊能力 閾値（新基準 r1）
# ────────────────────────────────────────────────

# 共通
INITIAL_BALL_O_AVG_DIFF = 0.050     # 初球◯: 0ストライク時打率 - 通算 >= +.050
MULTI_HIT_GAME_MIN = 6              # 固め打ち（青）: 3安打試合 >= 6回
PULL_HR_PCT_MIN = 0.55              # プルヒッター（青）: 引っ張りHR% >= 55%
OPPO_HR_MIN = 4                     # 広角打法（青）: 逆方向HR >= 4本

# パワーヒッター（青）: HR >= 22 + Barrel% >= 12%
POWER_HITTER_HR_MIN = 22
POWER_HITTER_BARREL_MIN = 12.0
POWER_HITTER_LA_MIN = 12.0          # （旧基準互換のため残置）
POWER_HITTER_LA_MAX = 18.0

# ラインドライブ（青）: 8〜14度の打球割合が一定以上
LINEDRIVE_LA_MIN = 8.0
LINEDRIVE_LA_MAX = 14.0
LINEDRIVE_PCT_MIN = 25.0            # ラインドライブ割合 >= 25%
LINE_DRIVE_LA_MIN = 10.0            # （旧基準互換）
LINE_DRIVE_LA_MAX = 15.0
LINE_DRIVE_HARD_HIT_MIN = 45.0

# アベレージヒッター（青）: 通算 xBA >= .285
AVG_HITTER_XBA_MIN = 0.285
AVG_HITTER_WHIFF_MAX = 20.0         # （旧基準互換、複合条件側は外す）

# ヘッドスライディング（青）: Sprint Speed >= 28.5
HEADSLI_SPEED_MIN = 28.5
BOLT_MIN_FOR_INFIELD = 10

# 粘り打ち（青）: 2ストライク Whiff% <= 22.0%
BLUE_NEBARI_WHIFF_MAX = 22.0
# カット打ち（青）: Foul% リーグ上位15%
# ダメ押し（青）: 4点リード時 終盤 wOBA >= .380
BLUE_DAMEOSHI_WOBA_MIN = 0.380
# アウト/インコースヒッター（青）: 該当ゾーン xBA >= .290 AND xSLG >= .500
BLUE_ZONE_HITTER_XBA_MIN = 0.290
BLUE_ZONE_HITTER_XSLG_MIN = 0.500
# 対エース◯（青）: 対エース級 xBA >= .270
BLUE_VS_ACE_XBA_MIN = 0.270
# 意外性（青）: 下位打線HR >= 6本
BLUE_LOWER_HR_MIN = 6
# 窮地◯（青）: 2ストライク wOBA >= .320
BLUE_KYUCHI_WOBA_MIN = 0.320
# 対ストレート◯（青）: Fastball Run Value >= +10
BLUE_FASTBALL_RV_MIN = 10.0
# マルチ弾（青）: 2HR以上の試合 >= 3回
BLUE_MULTI_HR_GAMES_MIN = 3
# バント◯ / バント職人（青）: SH >= 3 / >= 6
BLUE_BUNT_MARU_MIN = 3
BLUE_BUNT_MASTER_MIN = 6
# 流し打ち（青）: 逆方向への安打割合 >= 33%
BLUE_NAGASHI_PCT_MIN = 33.0
# レーザービーム（青）: 外野送球速度 >= 93mph
BLUE_LASER_BEAM_ARM_MIN = 93.0
# ハイ/ローボールヒッター（青）: 該当ゾーン xBA >= .290 AND xSLG >= .500 （ZONE_HITTER 共用）
# 逆境◯（青）: 7回以降・負け状況打率 >= .290
BLUE_GYAKKYO_AVG_MIN = 0.290
# いぶし銀（青）: 終盤・得点圏・1点差 xBA >= .320
BLUE_IBUSHIGIN_XBA_MIN = 0.320
# 守備職人（青）: OAA >= +7
BLUE_FIELDING_OAA_MIN = 7
# 威圧感（野手, 青）: OPS >= .950 or wOBA >= .400
BLUE_HATSU_OPS_MIN = 0.950
BLUE_HATSU_WOBA_MIN = 0.400
# チャンスメーカー（青）: 走者なし OBP >= .360
BLUE_CHANCE_MAKER_OBP_MIN = 0.360
# ホーム突入（青）: Sprint Speed >= 28.0
BLUE_HOME_RUSH_SPEED_MIN = 28.0
# 内野安打◯（青）: Home to First <= 4.25秒
BLUE_INFIELD_HIT_TIME_MAX = 4.25
# 代打◯（青）: 代打打率 >= .270
BLUE_PINCH_HIT_AVG_MIN = 0.270
# プレッシャーラン（青）: Sprint Speed >= 28.5
BLUE_PRESSURE_RUN_SPEED_MIN = 28.5
# 対変化球◯（青）: Breaking/Offspeed Run Value >= +8
BLUE_BREAKING_RV_MIN = 8.0
# ホーム死守（青, 捕手）: Blocks Above Average >= +5
BLUE_HOME_DEFEND_BLOCKING_MIN = 5.0
# サヨナラ男（青）: サヨナラ打 >= 1回
BLUE_WALKOFF_MIN = 1
# 満塁男（青）: 満塁時打率 >= .320
BLUE_BASES_LOADED_AVG_MIN = 0.320
# 同一試合次打席 wOBA 改善 リベンジ（青）
BLUE_REVENGE_WOBA_IMPROVE = 0.050

# 赤特
RED_K_PCT_MIN = 27.0               # 三振: K% >= 27%
RED_FURI_K_PCT_MIN = 33.0          # 扇風機: K% >= 33%
RED_ERROR_RV_MAX = -5.0            # エラー: Fielding Run Value (Error) <= -5
RED_GDP_MIN = 15                   # 併殺: GIDP >= 15
RED_GDP_SPEED_MAX = 26.0           # 併殺: Sprint Speed <= 26.0 ft/sec
RED_MOOD_WPA_MAX = -3.0            # ムード✕: WPA <= -3.0

# ────────────────────────────────────────────────
# 野手 金特 閾値（新基準 r1）
# ────────────────────────────────────────────────
GOLD_PERCENTILE = 99               # 汎用 金特付与パーセンタイル

# 1. 一球入魂: 0ストライク xBA >= .340 or xSLG >= .630
GOLD_FIRST_PITCH_XBA_MIN = 0.340
GOLD_FIRST_PITCH_XSLG_MIN = 0.630
# 2. メッタ打ち: 3安打試合 >= 10回
GOLD_METTA_GAMES_MIN = 10
# 3. 外角必打 / 4. 内角必打 / 16. 高球必打 / 27. 低球必打: xBA >= .315 AND xSLG >= .530
GOLD_ZONE_HITTER_XBA_MIN = 0.315
GOLD_ZONE_HITTER_XSLG_MIN = 0.530
# 5. エースキラー: 対上位投手 xBA >= .295
GOLD_ACE_KILLER_XBA_MIN = 0.295
# 6. 気迫ヘッド: Sprint Speed >= 29.0 + 内野安打 >= 12
GOLD_KIHAKU_SPEED_MIN = 29.0
GOLD_KIHAKU_INFIELD_HITS_MIN = 12
# 7. 伝説のサヨナラ男: サヨナラ打 >= 2回
GOLD_LEGEND_WALKOFF_MIN = 2
# 8. 大番狂わせ: 基礎パワー C以下 + 接戦時 Max EV >= 111mph
GOLD_UPSET_POWER_MAX_MEV = 108.0   # パワー C 相当の Max EV 閾値 (= POWER_BREAKPOINTS[2])
GOLD_UPSET_CLUTCH_EV_MIN = 111.0
# 9. ヒートアップ: 2ストライク xBA >= .265 + xSLG >= .470
GOLD_HEATUP_XBA_MIN = 0.265
GOLD_HEATUP_XSLG_MIN = 0.470
# 10. 芸術的流し打ち: 逆方向安打 >= 40 + Oppo xBA >= .325
GOLD_OPPO_ART_HITS_MIN = 40
GOLD_OPPO_ART_XBA_MIN = 0.325
# 11. 安打製造機: 通算 xBA >= .300 + Whiff% <= 19.0%
GOLD_HIT_MACHINE_XBA_MIN = 0.300
GOLD_HIT_MACHINE_WHIFF_MAX = 19.0
# 12. 鉄人: 155試合以上 + IL入り過去2年 <= 1回
GOLD_IRON_GAMES_MIN = 155
GOLD_IRON_IL_MAX = 1
# 13. 高速レーザー: 外野手 Arm Strength >= 96mph
GOLD_FAST_LASER_ARM_MIN = 96.0
# 14. アーチスト: Barrel% >= 16.5% + 平均打球角度 13〜23度
GOLD_ARCHIST_BARREL_MIN = 16.5
GOLD_ARCHIST_LA_MIN = 13.0
GOLD_ARCHIST_LA_MAX = 23.0
# 15. 引っ張り屋: Pull xSLG >= .830 + 本塁打の7割以上 Pull
GOLD_PULL_KING_XSLG_MIN = 0.830
GOLD_PULL_KING_HR_PCT_MIN = 0.70
# 17. 左腕キラー: 対左 xBA - 対右 xBA >= .055 + 対左 xBA >= .310
GOLD_LHP_KILLER_DIFF = 0.055
GOLD_LHP_KILLER_XBA_MIN = 0.310
# 18. 火事場の馬鹿力: 7回以降・負け状況 xSLG >= .640
GOLD_KAJIBA_XSLG_MIN = 0.640
# 19. 魔術師: 内野手 OAA >= +12
GOLD_MAGICIAN_OAA_MIN = 12
# 20. トリックスター: Baserunning RV >= +4 + 盗塁成功率 >= 88%
GOLD_TRICKSTER_BSR_MIN = 4.0
GOLD_TRICKSTER_SB_PCT_MIN = 0.88
# 21. 逆襲: 同一投手 2打席目以降 xBA 改善 >= +.060
GOLD_GYAKUSHU_XBA_IMPROVE = 0.060
# 22. 切り込み隊長: 走者なし OBP >= .385
GOLD_LEADOFF_OBP_MIN = 0.385
# 23. 高速ベースラン: XBT% >= 58%
GOLD_FAST_BASERUN_XBT_MIN = 58.0
# 24. ストライク送球: Fielding Run Value (Arm) >= +4
GOLD_STRIKE_THROW_ARM_RV_MIN = 4.0
# 25. ロケットスタート: Home to First タイム <= 4.15秒
GOLD_ROCKET_START_TIME_MAX = 4.15
# 26. 代打の神様: 代打 xBA >= .340 + 代打HR >= 2本
GOLD_PINCH_HIT_GOD_XBA_MIN = 0.340
GOLD_PINCH_HIT_GOD_HR_MIN = 2
# 28. 電光石火: Sprint Speed >= 29.8 + 盗塁数 >= 35
GOLD_DENKOSEKKA_SPEED_MIN = 29.8
GOLD_DENKOSEKKA_SB_MIN = 35
# 29. 渾身の決勝打: 6回以降・決勝場面 xBA >= .340
GOLD_KESSHODA_XBA_MIN = 0.340
# 30. 勝負師: 得点圏 xBA - 通常 xBA >= +.065 + 得点圏 xBA >= .325
GOLD_SHOBUSHI_DIFF_MIN = 0.065
GOLD_SHOBUSHI_XBA_MIN = 0.325
# 31. 重戦車: 本塁突入時 生還率 >= 95% + Sprint Speed >= 28.5
GOLD_TANK_SCORE_RATE_MIN = 0.95
GOLD_TANK_SPEED_MIN = 28.5
# 32. 恐怖の満塁男: 満塁時 xSLG >= .880
GOLD_BASES_LOADED_XSLG_MIN = 0.880
# 33. 精神的支柱 / 41. 絶好調男（青）: チーム内 WPA 1位 + WPA >= +4.0
GOLD_PILLAR_WPA_MIN = 4.0
# 34. 広角砲: 逆方向 HR >= 10 + Oppo xSLG >= .580
GOLD_OPPO_HR_KING_HR_MIN = 10
GOLD_OPPO_HR_KING_XSLG_MIN = 0.580

# 捕手専用金特
# 球界の頭脳: Fielding Run Value (Catcher) >= +10
GOLD_CATCHER_BRAIN_FRV_MIN = 10.0
# ささやき戦術: 33歳以上 + Catcher Framing >= +8
GOLD_VETERAN_AGE_MIN = 33
GOLD_WHISPER_FRAMING_MIN = 8.0
# 鉄の壁: Blocks Above Average >= +8
GOLD_IRON_WALL_BLOCKING_MIN = 8.0
# バズーカ送球: Pop Time (2B) <= 1.88秒
GOLD_BAZOOKA_POP_TIME_MAX = 1.88

# ────────────────────────────────────────────────
# 投手 特殊能力 閾値（新基準 r1）
# ────────────────────────────────────────────────

# 青特
BLUE_K_PCT_MIN = 27.0              # 奪三振: K% >= 27.0%
BLUE_KIRE_BREAKING_WHIFF_MIN = 35.0  # キレ◯: 主要変化球 Whiff% >= 35.0%
BLUE_P_FIELDING_RV_MIN = 3.0       # 打球反応◯: Fielding Run Value (P) >= +3
BLUE_LOW_ZONE_PCT_MIN = 50.0       # 低め◯: Low Zone % >= 50%
BLUE_EXTENSION_FT_MIN = 6.7        # 球持ち◯: Extension >= 6.7ft
BLUE_HEAVY_HARD_HIT_MAX = 33.0     # 重い球: Hard Hit% <= 33.0%
BLUE_ESCAPE_HR_PER_9_MAX = 0.8     # 逃げ球: HR/9 <= 0.8
BLUE_RELEASE_STDDEV_MAX = 0.5      # リリース◯: release stddev <= 0.5in
BLUE_SPEED_DIFF_MIN = 15.0         # 緩急◯: 最大球速差 >= 15mph + 有効球種2つ以上
BLUE_GYROBALL_SPIN_MAX = 75.0      # ジャイロボール: Active Spin <= 75%
BLUE_INSIDE_SHADOW_PCT_MIN = 25.0  # 内角攻め: Inside Shadow Zone% >= 25%
BLUE_IR_STRAND_MIN = 75.0          # 緊急登板◯: IRS% >= 75%
BLUE_CLOSER_XWOBA_MAX = 0.280      # 威圧感: クローザー時 xwOBA <= .280
BLUE_WIN_LUCK_RS9_MIN = 6.0        # 勝ち運: RS/9 >= 6.0
BLUE_KONJO_VELO_DECLINE_MAX = 1.0  # 根性◯: 100球超の球速低下が 1.0mph 以内
BLUE_CROSS_CANNON_WHIFF_MIN = 40.0 # クロスキャノン: 対角線 Shadow Whiff% >= 40%
BLUE_LATE_XWOBA_IMPROVE = -0.030   # 尻上がり: 7イニング目以降の被xwOBA 改善 -0.030
BLUE_VS_TOP_HITTERS_RV_MIN = 0.0   # 対強打者◯: 上位打者への Pitching RV > 0
BLUE_RELIEF_AVG_INNINGS_MIN = 1.2  # 回またぎ◯: 救援平均消化 >= 1.2 イニング
BLUE_MULTI_PITCH_TYPES_MIN = 5     # 球種多◯: 投球割合 5% 以上の球種 >= 5つ
BLUE_PITCH_USAGE_THRESHOLD = 5.0   # 球種多◯ 用 投球割合閾値
# 牽制◯: pickoff_top10pct フラグ
BLUE_FIRST_INN_XWOBA_MAX = 0.250   # 立ち上がり◯: 1イニング目 xwOBA <= .250
BLUE_WIN_PCT_MIN = 0.750           # 勝ちまくり: 勝率 >= .750
BLUE_NATURAL_HB_MIN = 8.0          # ナチュシュ: FB HB >= +8インチ（利き手側）
BLUE_CUTTER_HB_MIN = 2.0           # 真っスラ: FB HB がカット方向へ >= 2インチ

# 既存基準のため残置
BLUE_4SEAM_SPEED_DIFF_MAX = 3.0    # 球速安定: Max - Avg <= 3mph (旧)
BLUE_HEART_ZONE_PCT_MAX = 20.0     # 逃げ球: Heart Zone% <= 20% (旧)
BLUE_EXT_PERCENTILE = 90           # 球持ち◯ 旧基準
BLUE_ON_RUNNER_XWOBA_IMPROVE = -0.030  # 対ランナー◯ 旧基準 (削除)
BLUE_FIRST_INN_XWOBA_IMPROVE = -0.040  # （旧） 立ち上がり◯ 差分基準
BLUE_HIGH_LEV_XWOBA_IMPROVE = -0.050   # （旧） 要所◯ 差分基準 → 金特へ移行

# 赤特
RED_BB_PCT_MIN = 11.0              # 四球: BB% >= 11%
RED_HARD_HIT_MIN = 45.0            # 軽い球: Hard Hit% >= 45%
RED_HR_PER_9_MIN = 1.5             # 一発: HR/9 >= 1.5
RED_SHOOT_HB_MIN = 12.0            # シュート回転: FB HB >= 12in (利き手側)
RED_RUN_SUPPORT_MAX = 3.0          # 負け運: RS/9 <= 3.0
RED_SLOW_START_XWOBA = 0.060       # スロースターター: 1回 - 通算 >= +.060
RED_DISORDER_BB_PCT_MIN = 10.0     # 乱調: BB% >= 10% + Control(複合) 70以上
RED_DISORDER_CONTROL_MIN = 70.0    # 乱調: 複合コントロール指標 >= 70
RED_VELO_UNSTABLE_DIFF_KPH = 5.0   # 球速安定✕: Max-Avg >= 5km/h (約3.1mph)
RED_VELO_UNSTABLE_DIFF_MPH = 3.1   # 球速安定✕（mph換算）

# 既存基準のため残置（赤特/旧）
RED_LOB_SHORT_MAX = 65.0           # 短気: LOB% <= 65% (新基準では「被安打直後HardHit上昇」だが旧基準も残置)
RED_RELEASE_STDDEV_BAD = 1.0       # 抜け球（旧）
RED_ON_RUNNER_BAD = 0.030          # 対ランナー×（旧）

# ────────────────────────────────────────────────
# 投手 金特 閾値（新基準 r1）
# ────────────────────────────────────────────────

# 1. ドクターK: K% >= 35.0%
GOLD_K_PCT_MIN = 35.0
# 2. 闘魂: LOB% >= 85% + 自責点抑制能力 (ER/9 <= 3.50)
GOLD_TOUKON_LOB_MIN = 85.0
GOLD_TOUKON_ER9_MAX = 3.50
# 3. 精密機械: BB% <= 3.0% + Edge% >= 48%
GOLD_PRECISION_BB_MAX = 3.0
GOLD_PRECISION_EDGE_MIN = 48.0
GOLD_PRECISION_LOWZONE_MIN = 45.0  # 旧基準残置
# 4. ハイスピンジャイロ: Active Spin <= 70% + Max Velocity >= 98mph
GOLD_HIGH_SPIN_GYRO_SPIN_MAX = 70.0
GOLD_HIGH_SPIN_GYRO_VEL_MIN = 98.0
# 5. 怪童: IVB >= 21.0インチ
GOLD_IVB_KAIDO_MIN = 21.0
# 6. 暴れ球: IVB >= 20.0 + BB% >= 12.0%
GOLD_ABARE_IVB_MIN = 20.0
GOLD_ABARE_BB_MIN = 12.0
# 7. 主砲キラー: 対上位10%打者 被 xwOBA <= .220
GOLD_TOP_KILLER_XWOBA_MAX = 0.220
# 8. 怪物球威: 被打球平均速度 <= 85.0 mph
GOLD_AVG_EV_MAX = 85.0
# 9. 左キラー: 対左 - 通常 xwOBA <= -.070
GOLD_LEFT_KILLER_DIFF = -0.070
# 10. 本塁打厳禁: HR/9 <= 0.40
GOLD_NO_HR_HR9_MAX = 0.40
# 11. ド根性: 100球超の Pitching Run Value 改善 >= +.050
GOLD_DOKONJO_RV_IMPROVE = 0.050
# 12. 終盤力: 7回以降 xwOBA <= .220
GOLD_LATE_XWOBA_MAX = 0.220
# 13. トップギア: 1-2イニング目 xwOBA <= .200
GOLD_TOP_GEAR_XWOBA_MAX = 0.200
# 14. ギアチェンジ: 得点圏 xwOBA - 通常 <= -.080
GOLD_GEAR_CHANGE_DIFF = -0.080
# 15. 変幻自在: 最大球速差 >= 20mph + 全球種 Run Value がプラス
GOLD_SPEED_DIFF_MAX = 20.0
# 16. クロスキャノン(金): 対角線 Shadow Whiff% >= 45%
GOLD_CROSS_CANNON_WHIFF_MIN = 45.0
# 17. 鉄腕: 月別 RV 標準偏差 極小
GOLD_TETSUWAN_RV_STDDEV_MAX = 0.5
# 18. ガソリンタンク: 80登板 or 210イニング
GOLD_GAS_TANK_G_MIN = 80
GOLD_GAS_TANK_IP_MIN = 210.0
# 19. 勝利の星: RS/9 >= 7.5
GOLD_WIN_STAR_RS9_MIN = 7.5
# 20. 不屈の魂: 得点圏 被ハードヒット率 <= 25%
GOLD_FUKUTSU_HARD_HIT_MAX = 25.0
# 21. 強心臓: 得点圏 xwOBA <= .200
GOLD_KYOSHINZO_XWOBA_MAX = 0.200
# 22. 走者釘付: 被盗塁成功率 <= 50% + Pop Time 1.20s 以下
GOLD_RUNNER_KUGI_SB_RATE_MAX = 0.50
GOLD_RUNNER_KUGI_POP_MAX = 1.20
# 23. 驚異の切れ味: 変化球全般 Whiff% >= 45%
GOLD_KIREAJI_WHIFF_MIN = 45.0
# 24. 精密機械(別): Edge% >= 50% + BB% <= 2.5%
GOLD_PRECISION2_EDGE_MIN = 50.0
GOLD_PRECISION2_BB_MAX = 2.5
# 25. 完全燃焼: 80球目以降の Whiff% が +5% 以上上昇
GOLD_BURNOUT_WHIFF_DIFF = 5.0
# 26. 内角無双: 内角 Whiff% >= 45%
GOLD_INSIDE_MUSO_WHIFF_MIN = 45.0
# 27. 要所◯(金): High Leverage 被xwOBA <= .210
GOLD_YOSHO_XWOBA_MAX = 0.210

# ────────────────────────────────────────────────
# 野手 基礎能力 追加閾値
# ────────────────────────────────────────────────

# 捕球: Fielding Run Value (降順)
CATCH_FRV_BREAKPOINTS = [10.0, 5.0, 1.0, -2.0, -5.0, -10.0, -15.0]

# ────────────────────────────────────────────────
# 野手 ランク制能力 閾値
# ────────────────────────────────────────────────

# ケガしにくさ: 出場試合数
DURABILITY_GOLD_MIN = 162
DURABILITY_BREAKPOINTS = [155, 145, 135, 120, 100, 80, 60]

# 走塁: Baserunning Run Value (累積, 降順)
BASERUNNING_RV_GOLD = 10.0
BASERUNNING_RV_BREAKPOINTS = [8.0, 5.0, 2.0, 0.5, -0.5, -2.0, -5.0]

# 盗塁: SB 数 + 成功率
STEAL_GOLD_MIN = 40                # 金特: SB >= 40
STEAL_GOLD_RATE = 0.90             # 金特: 成功率 >= 90%
STEAL_A_MIN = 20                   # A: SB >= 20
STEAL_A_RATE = 0.85                # A: 成功率 >= 85%
STEAL_D_RATE = 0.75                # D 基準成功率
STEAL_F_RATE = 0.60                # F 以下の成功率

# 対左投手: vs LHP wOBA - vs RHP wOBA (差が正 = 左投手得意, 降順)
BATTER_VS_LHP_GOLD_MIN = 0.100
BATTER_VS_LHP_BREAKPOINTS = [0.075, 0.050, 0.030, 0.015, -0.015, -0.035, -0.050]

# 送球: Fielding Run Value (Arm, 累積, 降順)
ARM_RV_GOLD = 5.0
ARM_RV_BREAKPOINTS = [4.0, 2.0, 1.0, 0.0, -1.0, -2.0, -3.0]

# キャッチャー: framing_runs と blocking_runs の min (両方 >= 閾値が条件)
CATCHER_RANK_GOLD = 10.0
CATCHER_RANK_BREAKPOINTS = [8.0, 5.0, 2.5, 0.5, -0.5, -2.0, -3.0]

# ────────────────────────────────────────────────
# 投手 ランク制能力 閾値
# ────────────────────────────────────────────────

# 打たれ強さ: LOB% (残塁率, 高いほど良い, 降順)
LOB_NOBITARESOSA_GOLD = 85.0
LOB_NOBITARESOSA_BREAKPOINTS = [83.0, 80.0, 77.0, 74.0, 71.0, 68.0, 65.0]

# 回復: 先発=IP / 救援=G 基準
RECOVERY_GOLD_IP = 210.0
RECOVERY_GOLD_G = 80
RECOVERY_BREAKPOINTS_IP = [195.0, 180.0, 165.0, 155.0, 140.0, 110.0, 80.0]
RECOVERY_BREAKPOINTS_G = [75, 70, 60, 55, 50, 40, 30]

# クイック: 盗塁阻止率 CS/(SB+CS) (高いほど良い)
QUICK_GOLD_CS_RATE = 0.60          # 金: CS率 >= 60% (被盗塁成功率 <= 40%)
QUICK_CS_RATE_BREAKPOINTS = [0.50, 0.40, 0.33, 0.27, 0.22, 0.15, 0.10]

# ノビ: 4シームの Induced Vertical Break (インチ, 高いほど良い)
NOBI_IVB_GOLD = 20.0
NOBI_IVB_BREAKPOINTS = [19.0, 18.0, 17.5, 16.5, 16.0, 14.5, 13.0]

# 対左打者: 金特の絶対閾値 (vs LHP xwOBA の絶対値)
VS_LHP_PITCHER_XWOBA_GOLD = 0.230

# チャンス: RISP打率 - 通常打率 (差が正ほど良い, 降順)
CHANCE_GOLD_MIN = 0.080
CHANCE_BREAKPOINTS = [0.060, 0.040, 0.020, -0.010, -0.030, -0.050, -0.060]

# ────────────────────────────────────────────────
# 投手 数値有能力 r1 仕様 絶対閾値
# ────────────────────────────────────────────────

# 打たれ強さ (LOB%): 金=85, A=80, D=72, F=64
PITCHER_DURABILITY_GOLD = 85.0
PITCHER_DURABILITY_A = 80.0
PITCHER_DURABILITY_D = 72.0
PITCHER_DURABILITY_F = 64.0

# ノビ (IVB インチ): 金=21, A=19, D=16, F=13
PITCHER_NOBI_GOLD = 21.0
PITCHER_NOBI_A = 19.0
PITCHER_NOBI_D = 16.0
PITCHER_NOBI_F = 13.0

# 対ピンチ (得点圏 xwOBA - 通常 xwOBA, 負の値ほど良い)
PITCHER_CLUTCH_GOLD = -0.060  # 強心臓 -.060 改善
PITCHER_CLUTCH_A = -0.040
PITCHER_CLUTCH_D = 0.010
PITCHER_CLUTCH_F = 0.040

# 対左打者 (対左 xwOBA - 対右 xwOBA, 負の値ほど良い)
PITCHER_VS_LHB_GOLD = -0.070  # 左キラー -.070 改善
PITCHER_VS_LHB_A = -0.050
PITCHER_VS_LHB_D = 0.015
PITCHER_VS_LHB_F = 0.050

# 回復 (登板数 / 投球回): 金=80G or 210IP, A=70G or 180IP, D=50G or 140IP, F=30G or 100IP
PITCHER_RECOVERY_G_GOLD = 80
PITCHER_RECOVERY_G_A = 70
PITCHER_RECOVERY_G_D = 50
PITCHER_RECOVERY_G_F = 30
PITCHER_RECOVERY_IP_GOLD = 210.0
PITCHER_RECOVERY_IP_A = 180.0
PITCHER_RECOVERY_IP_D = 140.0
PITCHER_RECOVERY_IP_F = 100.0

# クイック (Pop Time 秒, 小さいほど良い): 金=1.20, A=1.25, D=1.40, F=1.60
PITCHER_QUICK_GOLD = 1.20
PITCHER_QUICK_A = 1.25
PITCHER_QUICK_D = 1.40
PITCHER_QUICK_F = 1.60
