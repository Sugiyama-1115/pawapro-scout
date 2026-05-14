"""
models.py
プロジェクト全体で使うデータクラス定義。
"""

from __future__ import annotations
from dataclasses import dataclass, field


# ────────────────────────────────────────────────
# 入力
# ────────────────────────────────────────────────

@dataclass
class PlayerInput:
    """players.csv の1行に対応"""
    season: int
    team: str                   # チーム略称 (LAD, NYY 等)
    name_jp: str                # カタカナ or 漢字
    name_en_last: str = ""      # /resolve-players Skill が補完
    name_en_first: str = ""
    mlbam_id: int = 0           # 0 = 未解決
    position: str = "OF"        # C/1B/2B/3B/SS/LF/CF/RF/DH/SP/RP
    role: str = "batter"        # batter / pitcher / both


# ────────────────────────────────────────────────
# 統計集計済みデータ（アグリゲーター出力）
# ────────────────────────────────────────────────

@dataclass
class PitchAggregated:
    """球種ごとの集計データ"""
    pitch_type: str                     # Statcastコード (FF, SL, CH 等)
    usage_pct: float                    # 使用率 (%)
    velocity_avg: float                 # 平均球速 (mph)
    whiff_pct: float                    # 空振り率 (%)
    horizontal_break: float             # 水平変化 pfx_x * 12 (in) 符号保持
    induced_vertical_break: float       # 垂直変化 pfx_z * 12 (in)
    delta_v_from_fastball: float        # FF平均球速 - 各球種平均球速 (mph)
    rv_per_100: float                   # Run Value per 100 pitches


@dataclass
class BatterStats:
    """野手の査定に必要な全指標"""
    # 弾道
    avg_launch_angle: float = 0.0
    sweet_spot_percent: float = 0.0

    # ミート
    xba: float = 0.0
    xslg: float = 0.0
    woba: float = 0.0
    obp: float = 0.0
    whiff_percent: float = 0.0

    # パワー
    max_exit_velocity: float = 0.0
    avg_exit_velocity: float = 0.0
    barrel_percent: float = 0.0
    barrel_percentile: int = 0
    hard_hit_percent: float = 0.0
    home_runs: int = 0

    # 走力
    sprint_speed: float = 0.0
    bolts: int = 0                      # 30 ft/sec超の回数
    home_to_first_sec: float | None = None    # 1塁到達タイム (秒)

    # 肩力
    arm_strength_mph: float | None = None   # 外野/内野 (汎用)
    arm_strength_of_mph: float | None = None  # 外野手専用
    pop_time: float | None = None           # 捕手

    # 守備力
    oaa: int = 0
    oaa_percentile: int = 50
    oaa_coming_in: int | None = None        # 内野 Coming In OAA (高速チャージ用)

    # 捕球
    fielding_run_value: float = 0.0
    error_count: int = 0

    # FanGraphs 打撃
    k_percent: float = 0.0
    bb_percent: float = 0.0
    wpa: float = 0.0
    lob_percent: float = 0.0
    ops_plus: int = 0
    ops: float = 0.0

    # Baseball Reference
    sb: int = 0
    cs: int = 0
    gdp: int = 0
    sh: int = 0                        # 犠打成功数
    games: int = 0
    xbt_percent: float = 0.0           # Extra Bases Taken % (旧走塁指標)
    baserunning_run_value: float | None = None   # Baserunning Run Value 走塁ランク用
    arm_run_value: float | None = None           # Fielding Run Value (Arm) 送球ランク用
    error_run_value: float | None = None         # Fielding Run Value (Error) エラー赤特用
    il_count_2y: int = 0               # 過去2年間のIL入り回数 (鉄人)

    # xBA パーセンタイル
    xba_percentile: int = 0

    # スプリット (FanGraphs)
    risp_avg: float = 0.0
    risp_xba: float = 0.0              # 得点圏 xBA
    season_avg: float = 0.0
    vs_lhp_woba: float = 0.0
    vs_rhp_woba: float = 0.0
    vs_lhp_xba: float = 0.0
    vs_rhp_xba: float = 0.0
    vs_ace_xba: float = 0.0            # 対エース級投手 xBA
    pinch_hit_pa: int = 0              # 代打打席数
    pinch_hit_xba: float = 0.0         # 代打 xBA
    pinch_hit_avg: float = 0.0         # 代打打率
    pinch_hit_hr: int = 0              # 代打本塁打

    # Savant 捕手系
    framing_runs: float | None = None
    blocking_runs: float | None = None

    # 打球方向 (Statcast pitch-level から算出)
    pull_hr_pct: float = 0.0           # 引っ張り方向HRの割合
    pull_xslg: float = 0.0             # 引っ張り xSLG
    oppo_hr_count: int = 0             # 逆方向HR数
    oppo_hits: int = 0                 # 逆方向への安打数
    oppo_hits_pct: float = 0.0         # 逆方向安打割合
    oppo_xba: float = 0.0              # 逆方向 xBA
    oppo_xslg: float = 0.0             # 逆方向 xSLG
    multi_hit_game_count: int = 0      # 1試合3安打以上の回数
    multi_hr_games: int = 0            # 2HR以上の試合

    # ゾーン別
    outside_xba: float = 0.0           # 外角 xBA
    outside_xslg: float = 0.0          # 外角 xSLG
    inside_xba: float = 0.0            # 内角 xBA
    inside_xslg: float = 0.0           # 内角 xSLG
    high_xba: float = 0.0              # 高め xBA
    high_xslg: float = 0.0             # 高め xSLG
    low_xba: float = 0.0               # 低め xBA
    low_xslg: float = 0.0              # 低め xSLG

    # カウント別
    count0_xba: float = 0.0            # 0ストライク xBA
    count0_xslg: float = 0.0           # 0ストライク xSLG
    count0_avg: float = 0.0            # 0ストライク打率
    count2_xba: float = 0.0            # 2ストライク xBA
    count2_xslg: float = 0.0           # 2ストライク xSLG
    count2_whiff: float = 0.0          # 2ストライク Whiff%
    count2_woba: float = 0.0           # 2ストライク wOBA

    # 状況別
    walk_off_hits: int = 0             # サヨナラ打数
    late_losing_avg: float = 0.0       # 7回以降・負け状況打率
    late_losing_xslg: float = 0.0      # 7回以降・負け状況 xSLG
    late_close_xba: float = 0.0        # 終盤・得点圏・1点差 xBA
    closing_inning_xba: float = 0.0    # 6回以降決勝場面 xBA
    closing_hits_top15: bool = False   # 6回以降決勝場面安打数 リーグ上位15%
    bases_loaded_xslg: float = 0.0     # 満塁時 xSLG
    bases_loaded_avg: float = 0.0      # 満塁時打率
    bases_empty_obp: float = 0.0       # 走者なし OBP
    lower_lineup_hr: int = 0           # 下位打線HR
    big_lead_late_woba: float = 0.0    # 4点リード時・終盤 wOBA
    clutch_max_ev: float = 0.0         # 接戦時の Max EV

    # Run Value
    fastball_run_value: float = 0.0    # 対ストレート Run Value
    breaking_run_value: float = 0.0    # 対変化球 Run Value

    # その他
    infield_hits: int = 0              # 内野安打数
    foul_pct_top15: bool = False       # Foul% リーグ上位15%
    linedrive_pct: float = 0.0         # 打球角度 8〜14度 の打球割合
    is_team_woba_leader: bool = False  # チーム内 wOBA 1位
    is_team_wpa_leader: bool = False   # チーム内 WPA 1位
    is_team_wpa_worst: bool = False    # チーム内 WPA 最下位
    same_pitcher_2nd_xba_improve: float = 0.0   # 同一投手 2打席目以降 xBA 改善
    same_game_next_pa_woba_improve: float = 0.0  # 同一試合次打席 wOBA 改善
    home_running_score_rate: float = 0.0  # 本塁突入時生還率
    stolen_base_pct: float = 0.0       # 盗塁成功率 (0.0〜1.0)
    inside_shadow_whiff: float = 0.0   # （投手用と区別） 投手側で利用


@dataclass
class PitcherStats:
    """投手の査定に必要な全指標"""
    # 基礎
    max_velocity_mph: float = 0.0
    avg_velocity_mph: float = 0.0        # 平均球速 (球速安定✕用)
    pitches: list[PitchAggregated] = field(default_factory=list)

    # コントロール
    k_percent: float = 0.0
    bb_percent: float = 0.0
    zone_percent: float = 0.0          # ストライクゾーン投球率 (コントロール複合指標用)
    edge_percent: float = 0.0          # 境界線投球率 (精密機械用)
    k_percentile: int = 50
    bb_percentile: int = 50

    # スタミナ
    avg_pitches_per_game: float | None = None   # 先発のみ
    games: int = 0
    ip: float = 0.0
    games_started: int = 0
    avg_relief_innings: float = 0.0    # 救援平均消化イニング (回またぎ用)
    wins: int = 0
    losses: int = 0
    win_pct: float = 0.0               # 勝率
    er_per_9: float = 0.0              # 自責点/9 (闘魂補助)

    # 球威
    exit_vel_percentile: int = 50
    avg_ev_against: float = 0.0        # 被打球速度平均 mph (怪物球威用)
    hard_hit_percent: float = 0.0
    risp_hard_hit_pct: float = 0.0     # ピンチ（得点圏）での被ハードヒット率

    # ムーブメント
    extension_percentile: int = 50
    extension_ft: float = 0.0          # Extension (ft, 絶対値)
    active_spin_4seam: float | None = None   # Active Spin %

    # 守備
    p_fielding_rv: float = 0.0          # 投手の Fielding Run Value (P)

    # LOB / 援護
    lob_percent: float = 0.0
    run_support: float | None = None    # RS/9
    hr_per_9: float = 0.0
    wpa: float = 0.0

    # FanGraphs Splits
    risp_xwoba: float = 0.0
    season_xwoba: float = 0.0
    vs_lhp_xwoba: float = 0.0
    vs_rhp_xwoba: float = 0.0
    high_lev_xwoba: float = 0.0
    closer_xwoba: float = 0.0           # クローザー役割時 xwOBA (威圧感用)
    is_closer: bool = False             # クローザー判定

    # Savant Statcast Search
    inning1_xwoba: float = 0.0
    inning2_xwoba: float = 0.0          # 2回 xwOBA (トップギア用)
    inning7plus_xwoba: float = 0.0
    pitch_100plus_rv: float = 0.0       # 100球超のRun Value
    pitch_100plus_rv_improve: float = 0.0  # 100球超 RV 改善幅 (ド根性用)
    pitch_100plus_velo_decline: float = 0.0  # 100球後球速低下 mph (根性◯用)
    low_zone_pct: float = 0.0           # 下段3ゾーン投球率
    heart_zone_pct: float = 0.0         # ど真ん中ゾーン投球率
    inside_shadow_pct: float = 0.0      # Inside Shadow Zone% (内角攻め)
    inside_whiff_pct: float = 0.0       # 内角 Whiff% (内角無双)
    cross_shadow_whiff_pct: float = 0.0  # 対角線 Shadow Zone Whiff% (クロスキャノン)
    breaking_offspeed_whiff_pct: float = 0.0  # 変化球全般 Whiff% (驚異の切れ味)
    late_pitch_whiff_diff: float = 0.0  # 80球目以降 Whiff% 上昇 (完全燃焼)
    xwoba_vs_top_hitters: float = 0.0   # 対上位10%打者 xwOBA (主砲キラー)
    rv_vs_top_hitters: float = 0.0      # 対強打者◯ (上位打者への RV)
    upper_lineup_xwoba: float = 0.0     # 上位打線 xwOBA (力配り用)
    lower_lineup_xwoba: float = 0.0     # 下位打線 xwOBA (力配り用)
    inning5_or_9_xwoba_increase: float = 0.0  # 5/9回直前xwOBA上昇 (寸前用)
    post_hit_hard_hit_increase: float = 0.0   # 被安打直後 Hard Hit% 上昇 (短気用)
    monthly_rv_stddev: float = 0.0      # 月別 Run Value 標準偏差 (鉄腕用)

    # リリースポイント安定性 (statcast pitch-levelから)
    release_x_stddev: float = 0.0
    release_z_stddev: float = 0.0

    # Inherited Runners Stranded % (FanGraphs)
    ir_stranded_pct: float | None = None

    # 牽制 (bref)
    pickoffs: int = 0
    pickoff_top10pct: bool = False      # 牽制リーグトップ10%

    # P-OAA (Savant pitcher-fielding)
    p_oaa: int | None = None

    # 被盗塁成功率 (クイック)
    sb_against: int = 0
    cs_against: int = 0
    pop_time: float | None = None       # 投手版 Pop Time (走者釘付用)


# ────────────────────────────────────────────────
# 査定結果
# ────────────────────────────────────────────────

@dataclass
class PitchEntry:
    """変化球1球種の査定結果"""
    名称: str
    変化量: int     # 1 ~ 7


@dataclass
class BatterBasic:
    弾道: int       # 1 ~ 4
    ミート: str     # S/A/B/C/D/E/F/G
    パワー: str
    走力: str
    肩力: str
    守備力: str
    捕球: str


@dataclass
class PitcherBasic:
    球速: int       # km/h
    コントロール: str
    スタミナ: str


@dataclass
class BatterRating:
    basic: BatterBasic
    rank_abilities: dict[str, str | None]   # 能力名 → 金/A/B/C/D/E/F/G or None
    gold_special: list[str]
    blue_special: list[str]
    red_special: list[str]


@dataclass
class PitcherRating:
    basic: PitcherBasic
    pitches: list[PitchEntry]
    rank_abilities: dict[str, str | None]
    gold_special: list[str]
    blue_special: list[str]
    red_special: list[str]


@dataclass
class PlayerRecord:
    """1選手の最終出力"""
    player: str                         # name_jp
    season: int
    type: str                           # "batter" | "pitcher" | "both"
    batter: BatterRating | None = None
    pitcher: PitcherRating | None = None
