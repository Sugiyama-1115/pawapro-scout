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
    whiff_percent: float = 0.0

    # パワー
    max_exit_velocity: float = 0.0
    avg_exit_velocity: float = 0.0
    barrel_percent: float = 0.0
    barrel_percentile: int = 0
    hard_hit_percent: float = 0.0

    # 走力
    sprint_speed: float = 0.0
    bolts: int = 0                      # 30 ft/sec超の回数

    # 肩力
    arm_strength_mph: float | None = None   # 外野/内野
    pop_time: float | None = None           # 捕手

    # 守備力
    oaa: int = 0
    oaa_percentile: int = 50

    # 捕球
    fielding_run_value: float = 0.0
    error_count: int = 0

    # FanGraphs 打撃
    k_percent: float = 0.0
    bb_percent: float = 0.0
    wpa: float = 0.0
    lob_percent: float = 0.0
    ops_plus: int = 0

    # Baseball Reference
    sb: int = 0
    cs: int = 0
    gdp: int = 0
    sh: int = 0
    games: int = 0
    xbt_percent: float = 0.0           # Extra Bases Taken %

    # xBA パーセンタイル
    xba_percentile: int = 0

    # スプリット (FanGraphs)
    risp_avg: float = 0.0
    season_avg: float = 0.0
    vs_lhp_woba: float = 0.0
    vs_rhp_woba: float = 0.0
    pinch_hit_pa: int = 0              # 代打打席数

    # Savant 捕手系
    framing_runs: float | None = None
    blocking_runs: float | None = None

    # 打球方向 (Statcast pitch-level から算出)
    pull_hr_pct: float = 0.0           # 引っ張り方向HRの割合
    oppo_hr_count: int = 0             # 逆方向HR数
    multi_hit_game_count: int = 0      # 1試合3安打以上の回数


@dataclass
class PitcherStats:
    """投手の査定に必要な全指標"""
    # 基礎
    max_velocity_mph: float = 0.0
    pitches: list[PitchAggregated] = field(default_factory=list)

    # コントロール
    k_percent: float = 0.0
    bb_percent: float = 0.0
    k_percentile: int = 50
    bb_percentile: int = 50

    # スタミナ
    avg_pitches_per_game: float | None = None   # 先発のみ
    games: int = 0
    ip: float = 0.0
    games_started: int = 0

    # 球威
    exit_vel_percentile: int = 50
    hard_hit_percent: float = 0.0

    # ムーブメント
    extension_percentile: int = 50
    active_spin_4seam: float | None = None   # Active Spin %

    # LOB / 援護
    lob_percent: float = 0.0
    run_support: float | None = None
    hr_per_9: float = 0.0
    wpa: float = 0.0

    # FanGraphs Splits
    risp_xwoba: float = 0.0
    season_xwoba: float = 0.0
    vs_lhp_xwoba: float = 0.0
    vs_rhp_xwoba: float = 0.0
    high_lev_xwoba: float = 0.0

    # Savant Statcast Search
    inning1_xwoba: float = 0.0
    inning7plus_xwoba: float = 0.0
    pitch_100plus_rv: float = 0.0       # 100球超のRun Value
    low_zone_pct: float = 0.0           # 下段3ゾーン投球率
    heart_zone_pct: float = 0.0         # ど真ん中ゾーン投球率

    # リリースポイント安定性 (statcast pitch-levelから)
    release_x_stddev: float = 0.0
    release_z_stddev: float = 0.0

    # Inherited Runners Stranded % (FanGraphs)
    ir_stranded_pct: float | None = None

    # 牽制 (bref)
    pickoffs: int = 0

    # P-OAA (Savant pitcher-fielding)
    p_oaa: int | None = None

    # 被盗塁成功率 (クイック)
    sb_against: int = 0
    cs_against: int = 0


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
