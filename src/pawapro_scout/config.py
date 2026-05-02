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

# ミート: xBA*300 + (100 - Whiff%)
MEET_BREAKPOINTS = [303.0, 287.0, 271.0, 255.0, 239.0, 223.0, 207.0]

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

# コントロール: BB%
CONTROL_BREAKPOINTS = [3.5, 5.0, 6.6, 8.6, 10.6, 12.6, 14.6]  # 以下(未満)でランクアップ

# スタミナ: 先発の平均投球数 P/G
STAMINA_SP_BREAKPOINTS = [100.0, 95.0, 90.0, 85.0, 75.0, 60.0, 30.0]

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
RV_HENKA_BONUS_THRESHOLD = -2.0    # RV/100 < -2 → +1
RV_HENKA_PENALTY_THRESHOLD = 2.0   # RV/100 >  2 → -1

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
CHANCE_O_RISP_DIFF = 0.050         # RISP打率 - 通常打率 >= 0.050
VS_LHP_O_WOBA_DIFF = 0.040         # 対左wOBA - 対右wOBA >= 0.040
INITIAL_BALL_O_AVG_DIFF = 0.070    # 初球打率 - 通常打率 >= 0.070
PULL_HR_PCT_MIN = 0.60             # Pull方向HRが全HRの60%以上
OPPO_HR_MIN = 5                    # 逆方向HR 5本以上
MULTI_HIT_GAME_TOP_PCT = 0.10      # 1試合3安打以上が上位10%

# 赤特
RED_K_PCT_MIN = 27.0               # 三振: K% >= 27%
RED_FURI_K_PCT_MIN = 33.0          # 扇風機: K% >= 33%
RED_CHANCE_X_AVG_DIFF = -0.060     # チャンス×: RISP - 通常 <= -0.060

# 金特 パーセンタイル基準
GOLD_PERCENTILE = 99               # 金特付与パーセンタイル

# ────────────────────────────────────────────────
# 投手 特殊能力 閾値
# ────────────────────────────────────────────────

# 青特
BLUE_K_PCT_MIN = 28.0              # 奪三振: K% >= 28%
BLUE_RELEASE_STDDEV_MAX = 0.5      # リリース◯: release_pos stddev <= 0.5 インチ
BLUE_SPEED_DIFF_MIN = 15.0         # 緩急◯: 最速-最遅 >= 15mph
BLUE_EXT_PERCENTILE = 90          # 球持ち◯: Extension 90th以上
BLUE_IR_STRAND_MIN = 80.0          # 緊急登板◯: IR-S% >= 80%
BLUE_4SEAM_SPEED_DIFF_MAX = 3.0   # 球速安定: Max - Avg <= 3mph
BLUE_LOW_ZONE_PCT_MIN = 40.0       # 低め◯: 下段3ゾーン投球率 >= 40%
BLUE_HEART_ZONE_PCT_MAX = 20.0     # 逃げ球: Heart Zone% <= 20%
BLUE_NATURAL_HB_MIN = 10.0         # ナチュラルシュート: 4seam HB >= 10in (利き手側)

# 青特 xwOBA 差分
BLUE_ON_RUNNER_XWOBA_IMPROVE = -0.030  # 対ランナー◯: 走者あり - 通常 <= -0.030
BLUE_FIRST_INN_XWOBA_IMPROVE = -0.040  # 立ち上がり◯: 1回 - 通算 <= -0.040
BLUE_LATE_XWOBA_IMPROVE = -0.020       # 尻上がり: 7回以降が優秀
BLUE_HIGH_LEV_XWOBA_IMPROVE = -0.050   # 要所◯: High Lev - 通常 <= -0.050

# 赤特
RED_BB_PCT_MIN = 11.0              # 四球: BB% >= 11%
RED_HARD_HIT_MIN = 45.0            # 軽い球: Hard Hit% >= 45%
RED_RELEASE_STDDEV_BAD = 1.0       # 抜け球: release stddev >= 1.0
RED_SLOW_START_XWOBA = 0.050       # スロースターター: 1回 - 通算 >= +0.050
RED_ON_RUNNER_BAD = 0.030          # 対ランナー×: 走者あり - 通常 >= +0.030
RED_LOB_WORST_PCT = 10             # 短気: LOB% ワースト10%

# 金特
GOLD_IVB_KAIDO_MIN = 20.0          # 怪童: IVB >= 20インチ
GOLD_SPEED_DIFF_MAX = 20.0         # 変幻自在: 球速差 >= 20mph

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
DURABILITY_BREAKPOINTS = [155, 145, 130, 115, 95, 75, 55]

# 走塁: Extra Bases Taken % (降順)
BASERUNNING_BREAKPOINTS = [55.0, 47.0, 40.0, 33.0, 26.0, 19.0, 12.0]

# 盗塁: SB 数
STEAL_GOLD_MIN = 50
STEAL_BREAKPOINTS = [35, 25, 15, 8, 4, 2, 1]

# 対左投手: vs LHP wOBA - vs RHP wOBA (差が正 = 左投手得意, 降順)
BATTER_VS_LHP_GOLD_MIN = 0.080
BATTER_VS_LHP_BREAKPOINTS = [0.060, 0.040, 0.020, 0.000, -0.020, -0.040, -0.060]

# 対変化球: K% (低いほど良い → 昇順ブレークポイント)
VS_BREAKING_BREAKPOINTS = [8.0, 12.0, 16.0, 20.0, 24.0, 28.0, 32.0]

# キャッチャー: framing_runs (降順)
CATCHER_RANK_BREAKPOINTS = [10.0, 7.0, 4.0, 1.0, -2.0, -5.0, -8.0]

# ────────────────────────────────────────────────
# 野手 青特 追加閾値
# ────────────────────────────────────────────────

# 固め打ち: 1試合3安打以上の試合数
MULTI_HIT_GAME_MIN = 15

# 内野安打◯: ボルト (30ft/sec超) の回数
BOLT_MIN_FOR_INFIELD = 10
