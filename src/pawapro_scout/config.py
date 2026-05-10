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
# 野手 特殊能力 閾値
# ────────────────────────────────────────────────

# 青特
INITIAL_BALL_O_AVG_DIFF = 0.070    # 初球打率 - 通常打率 >= 0.070
MULTI_HIT_GAME_MIN = 8             # 固め打ち: 1試合3安打以上の試合 >= 8試合 (旧15)
PULL_HR_PCT_MIN = 0.80             # プルヒッター: Pull方向HR >= 80% (旧60%)
OPPO_HR_MIN = 5                    # 広角打法: 逆方向HR >= 5本

# パワーヒッター: Barrel% >= 12% AND 平均打球角度 12〜18度
POWER_HITTER_BARREL_MIN = 12.0
POWER_HITTER_LA_MIN = 12.0
POWER_HITTER_LA_MAX = 18.0

# ラインドライブ: 平均打球角度 10〜15度 AND Hard Hit% >= 45%
LINE_DRIVE_LA_MIN = 10.0
LINE_DRIVE_LA_MAX = 15.0
LINE_DRIVE_HARD_HIT_MIN = 45.0

# アベレージヒッター: xBA >= .280 AND Whiff% <= 20%
AVG_HITTER_XBA_MIN = 0.280
AVG_HITTER_WHIFF_MAX = 20.0

# ヘッドスライディング: Sprint Speed >= 29.0 AND bolts >= 10
HEADSLI_SPEED_MIN = 29.0
BOLT_MIN_FOR_INFIELD = 10

# 赤特
RED_K_PCT_MIN = 27.0               # 三振: K% >= 27%
RED_FURI_K_PCT_MIN = 33.0          # 扇風機: K% >= 33%
RED_ERROR_RV_MAX = -5.0            # エラー: Fielding Run Value (Error) <= -5
RED_GDP_MIN = 15                   # 併殺: GIDP >= 15
RED_GDP_SPEED_MAX = 26.0           # 併殺: Sprint Speed <= 26.0 ft/sec
RED_MOOD_WPA_MAX = -3.0            # ムード✕: WPA <= -3.0

# 金特
GOLD_PERCENTILE = 99               # 汎用 金特付与パーセンタイル

# ────────────────────────────────────────────────
# 投手 特殊能力 閾値
# ────────────────────────────────────────────────

# 青特
BLUE_K_PCT_MIN = 30.0              # 奪三振: K% >= 30%
BLUE_KIRE_BREAKING_WHIFF_MIN = 35.0  # キレ◯: 変化球/オフスピードの Whiff% >= 35%
BLUE_RELEASE_STDDEV_MAX = 0.5      # リリース◯: release_pos stddev <= 0.5 インチ
BLUE_SPEED_DIFF_MIN = 15.0         # 緩急◯: 最速-最遅 >= 15mph
BLUE_EXT_PERCENTILE = 90          # 球持ち◯: Extension 90th以上
BLUE_IR_STRAND_MIN = 80.0          # 緊急登板◯: IR-S% >= 80%
BLUE_4SEAM_SPEED_DIFF_MAX = 3.0   # 球速安定: Max - Avg <= 3mph
BLUE_LOW_ZONE_PCT_MIN = 40.0       # 低め◯: 下段3ゾーン投球率 >= 40%
BLUE_HEART_ZONE_PCT_MAX = 20.0     # 逃げ球: Heart Zone% <= 20%
BLUE_NATURAL_HB_MIN = 10.0         # ナチュラルシュート: 4seam HB >= 10in (利き手側)
BLUE_GYROBALL_SPIN_MAX = 70.0      # ジャイロボール: 4seam Active Spin <= 70%

# 青特 xwOBA 差分
BLUE_ON_RUNNER_XWOBA_IMPROVE = -0.030  # 対ランナー◯: 走者あり - 通常 <= -0.030
BLUE_FIRST_INN_XWOBA_IMPROVE = -0.040  # 立ち上がり◯: 1回 - 通算 <= -0.040
BLUE_LATE_XWOBA_IMPROVE = -0.020       # 尻上がり: 7回以降が優秀
BLUE_HIGH_LEV_XWOBA_IMPROVE = -0.050   # 要所◯: High Lev - 通常 <= -0.050

# 赤特
RED_BB_PCT_MIN = 11.0              # 四球: BB% >= 11%
RED_HARD_HIT_MIN = 45.0            # 軽い球: Hard Hit% >= 45%
RED_HR_PER_9_MIN = 1.5             # 一発: HR/9 >= 1.5
RED_SHOOT_HB_MIN = 12.0            # シュート回転: 4seam HB (利き手側) >= 12in
RED_LOB_SHORT_MAX = 65.0           # 短気: LOB% <= 65%
RED_RUN_SUPPORT_MAX = 3.5          # 負け運: Run Support <= 3.5
RED_RELEASE_STDDEV_BAD = 1.0       # 抜け球: release stddev >= 1.0
RED_SLOW_START_XWOBA = 0.050       # スロースターター: 1回 - 通算 >= +0.050
RED_ON_RUNNER_BAD = 0.030          # 対ランナー×: 走者あり - 通常 >= +0.030

# 金特
GOLD_K_PCT_MIN = 35.0              # ドクターK: K% >= 35%
GOLD_AVG_EV_MAX = 85.0             # 怪物球威: 被打球平均速度 <= 85.0 mph
GOLD_IVB_KAIDO_MIN = 20.0          # 怪童: IVB >= 20インチ (ノビ金特と共用)
GOLD_SPEED_DIFF_MAX = 20.0         # 変幻自在: 球速差 >= 20mph
GOLD_PRECISION_LOWZONE_MIN = 45.0  # 精密機械: Low Zone% >= 45%
GOLD_PRECISION_BB_MAX = 4.0        # 精密機械: BB% <= 4.0%
GOLD_HIGH_SPIN_GYRO_SPIN_MAX = 70.0   # ハイスピンジャイロ: Active Spin <= 70%
GOLD_HIGH_SPIN_GYRO_VEL_MIN = 97.0    # ハイスピンジャイロ: 球速 >= 97mph

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

# 野手 金特 閾値
GOLD_ARCHIST_BARREL_MIN = 20.0     # アーチスト: Barrel% >= 20%
GOLD_ARCHIST_LA_MIN = 15.0         # アーチスト: 平均打球角度 >= 15度
GOLD_ARCHIST_LA_MAX = 20.0         # アーチスト: 平均打球角度 <= 20度
GOLD_HIT_MACHINE_XBA_MIN = 0.310   # 安打製造機: xBA >= .310
GOLD_HIT_MACHINE_WHIFF_MAX = 15.0  # 安打製造機: Whiff% <= 15%

# チャンス: RISP打率 - 通常打率 (差が正ほど良い, 降順)
CHANCE_GOLD_MIN = 0.080
CHANCE_BREAKPOINTS = [0.060, 0.040, 0.020, -0.010, -0.030, -0.050, -0.060]
