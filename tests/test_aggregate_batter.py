"""
tests/test_aggregate_batter.py
BatterAggregator のテスト。
スタブ DataFrame を渡して BatterStats の各フィールドが正しく設定されるか検証する。
"""

import pytest
import pandas as pd
import numpy as np

from pawapro_scout.aggregate.batter_aggregator import BatterAggregator
from pawapro_scout.models import BatterStats

MLBAM = 660271
FG_ID = 19755


# ──────────────────────────────────────────────
# スタブ生成ヘルパー
# ──────────────────────────────────────────────

def make_expected(player_id=MLBAM, **kwargs):
    defaults = {
        "player_id": [player_id],
        "xba": [0.300],
        "sweet_spot_percent": [38.5],
        "whiff_percent": [22.0],
        "barrel_batted_rate": [8.5],
        "hard_hit_percent": [42.0],
    }
    defaults.update({k: [v] for k, v in kwargs.items()})
    return pd.DataFrame(defaults)


def make_percentile(player_id=MLBAM, **kwargs):
    defaults = {
        "player_id": [player_id],
        "xba": [90],
        "barrel": [85],
        "sprint_speed": [75],
        "outs_above_average": [80],
    }
    defaults.update({k: [v] for k, v in kwargs.items()})
    return pd.DataFrame(defaults)


def make_sprint(player_id=MLBAM, sprint_speed=29.5, bolts=15):
    return pd.DataFrame({"player_id": [player_id], "sprint_speed": [sprint_speed], "bolts": [bolts]})


def make_oaa(player_id=MLBAM, outs_above_average=8):
    return pd.DataFrame({"player_id": [player_id], "outs_above_average": [outs_above_average]})


def make_batting_fg(fg_id=FG_ID, **kwargs):
    defaults = {
        "IDfg": [fg_id],
        "K%": [0.220],   # 22.0 % として小数で格納
        "BB%": [0.095],  # 9.5 %
        "WPA": [3.5],
        "LOB%": [0.750], # 75.0 %
        "AVG": [0.298],
        "OPS+": [158],
        "GS": [25],
        "G": [30],
        "IP": [150.1],
        "Pitches": [3200],
    }
    defaults.update({k: [v] for k, v in kwargs.items()})
    return pd.DataFrame(defaults)


def make_batting_bref(mlbam_id=MLBAM, **kwargs):
    defaults = {
        "mlbID": [mlbam_id],
        "G": [120],
        "SB": [20],
        "CS": [5],
        "GDP": [8],
        "SH": [0],
    }
    defaults.update({k: [v] for k, v in kwargs.items()})
    return pd.DataFrame(defaults)


def make_frv(player_id=MLBAM, **kwargs):
    defaults = {
        "player_id": [player_id],
        "frv": [5.5],
        "errors": [3],
    }
    defaults.update({k: [v] for k, v in kwargs.items()})
    return pd.DataFrame(defaults)


def make_statcast_batter(n=50):
    """シンプルな pitch-level スタブ"""
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "player_id":    [MLBAM] * n,
        "game_date":    ["2025-04-01"] * 20 + ["2025-04-02"] * 20 + ["2025-04-03"] * 10,
        "game_pk":      [1001] * 20 + [1002] * 20 + [1003] * 10,
        "events":       ["single"] * 10 + ["home_run"] * 5 + [None] * 35,
        "launch_speed": rng.uniform(85, 115, n),
        "launch_angle": rng.uniform(-10, 40, n),
        "hc_x":         rng.uniform(80, 170, n),
        "stand":        ["R"] * n,
        "description":  ["hit_into_play"] * 20 + ["swinging_strike"] * 10 + ["ball"] * 20,
    })


def build(statcast=None, **kwargs):
    agg = BatterAggregator(mlbam_id=MLBAM, fg_id=FG_ID, bref_id=MLBAM)
    return agg.build(
        statcast_batter    = statcast if statcast is not None else make_statcast_batter(),
        batter_expected    = kwargs.get("batter_expected",    make_expected()),
        batter_percentile  = kwargs.get("batter_percentile",  make_percentile()),
        sprint_speed       = kwargs.get("sprint_speed",       make_sprint()),
        outs_above_average = kwargs.get("outs_above_average", make_oaa()),
        batting_stats_fg   = kwargs.get("batting_stats_fg",   make_batting_fg()),
        batting_stats_bref = kwargs.get("batting_stats_bref", make_batting_bref()),
        fielding_run_value = kwargs.get("fielding_run_value", make_frv()),
    )


# ──────────────────────────────────────────────
# 返り値型テスト
# ──────────────────────────────────────────────

class TestReturnType:
    def test_returns_batter_stats(self):
        result = build()
        assert isinstance(result, BatterStats)

    def test_missing_player_in_all_sources_returns_defaults(self):
        """どのデータにも選手が存在しない場合はデフォルト値で埋まる"""
        agg = BatterAggregator(mlbam_id=999999, fg_id=None, bref_id=None)
        result = agg.build(
            statcast_batter=pd.DataFrame(),
            batter_expected=make_expected(),
            batter_percentile=make_percentile(),
            sprint_speed=make_sprint(),
            outs_above_average=make_oaa(),
            batting_stats_fg=make_batting_fg(),
            batting_stats_bref=make_batting_bref(),
            fielding_run_value=make_frv(),
        )
        assert result.xba == 0.0
        assert result.sprint_speed == 0.0
        assert result.sb == 0


# ──────────────────────────────────────────────
# ミート / パワー
# ──────────────────────────────────────────────

class TestMeetAndPower:
    def test_xba_from_expected_stats(self):
        result = build(batter_expected=make_expected(xba=0.320))
        assert result.xba == pytest.approx(0.320)

    def test_sweet_spot_from_expected_stats(self):
        result = build(batter_expected=make_expected(sweet_spot_percent=40.0))
        assert result.sweet_spot_percent == pytest.approx(40.0)

    def test_whiff_percent_from_expected(self):
        result = build(batter_expected=make_expected(whiff_percent=25.5))
        assert result.whiff_percent == pytest.approx(25.5)

    def test_max_exit_velocity_from_statcast(self):
        sc = make_statcast_batter()
        sc["launch_speed"] = 110.0
        sc.loc[0, "launch_speed"] = 118.5  # 最大値
        result = build(statcast=sc)
        assert result.max_exit_velocity == pytest.approx(118.5)

    def test_barrel_percentile_from_percentile(self):
        result = build(batter_percentile=make_percentile(barrel=95))
        assert result.barrel_percentile == 95


# ──────────────────────────────────────────────
# 走力
# ──────────────────────────────────────────────

class TestSpeed:
    def test_sprint_speed(self):
        result = build(sprint_speed=make_sprint(sprint_speed=30.2))
        assert result.sprint_speed == pytest.approx(30.2)

    def test_bolts(self):
        result = build(sprint_speed=make_sprint(bolts=22))
        assert result.bolts == 22


# ──────────────────────────────────────────────
# 守備力
# ──────────────────────────────────────────────

class TestDefense:
    def test_oaa_from_outs_above_average(self):
        result = build(outs_above_average=make_oaa(outs_above_average=12))
        assert result.oaa == 12

    def test_oaa_percentile_from_percentile(self):
        result = build(batter_percentile=make_percentile(outs_above_average=92))
        assert result.oaa_percentile == 92

    def test_fielding_run_value(self):
        result = build(fielding_run_value=make_frv(frv=7.2))
        assert result.fielding_run_value == pytest.approx(7.2)

    def test_error_count(self):
        result = build(fielding_run_value=make_frv(errors=5))
        assert result.error_count == 5


# ──────────────────────────────────────────────
# FanGraphs 成績
# ──────────────────────────────────────────────

class TestFanGraphs:
    def test_k_percent_converted_to_percentage(self):
        """K% = 0.220 (小数) → 22.0 に変換される"""
        result = build(batting_stats_fg=make_batting_fg(**{"K%": 0.220}))
        assert result.k_percent == pytest.approx(22.0)

    def test_bb_percent_converted_to_percentage(self):
        result = build(batting_stats_fg=make_batting_fg(**{"BB%": 0.095}))
        assert result.bb_percent == pytest.approx(9.5)

    def test_wpa(self):
        result = build(batting_stats_fg=make_batting_fg(WPA=4.2))
        assert result.wpa == pytest.approx(4.2)

    def test_season_avg(self):
        result = build(batting_stats_fg=make_batting_fg(AVG=0.305))
        assert result.season_avg == pytest.approx(0.305)

    def test_ops_plus(self):
        result = build(batting_stats_fg=make_batting_fg(**{"OPS+": 160}))
        assert result.ops_plus == 160

    def test_no_fg_id_skips_fg(self):
        """fg_id が None のとき FanGraphs 指標はデフォルト 0"""
        agg = BatterAggregator(mlbam_id=MLBAM, fg_id=None, bref_id=MLBAM)
        result = agg.build(
            statcast_batter=pd.DataFrame(),
            batter_expected=make_expected(),
            batter_percentile=make_percentile(),
            sprint_speed=make_sprint(),
            outs_above_average=make_oaa(),
            batting_stats_fg=make_batting_fg(),
            batting_stats_bref=make_batting_bref(),
            fielding_run_value=make_frv(),
        )
        assert result.k_percent == 0.0


# ──────────────────────────────────────────────
# Baseball Reference
# ──────────────────────────────────────────────

class TestBref:
    def test_sb(self):
        result = build(batting_stats_bref=make_batting_bref(SB=30))
        assert result.sb == 30

    def test_cs(self):
        result = build(batting_stats_bref=make_batting_bref(CS=8))
        assert result.cs == 8

    def test_gdp(self):
        result = build(batting_stats_bref=make_batting_bref(GDP=12))
        assert result.gdp == 12


# ──────────────────────────────────────────────
# Statcast pitch-level 集計
# ──────────────────────────────────────────────

class TestStatcastMetrics:
    def test_avg_launch_angle_calculated(self):
        sc = make_statcast_batter()
        sc["launch_angle"] = 15.0
        result = build(statcast=sc)
        assert result.avg_launch_angle == pytest.approx(15.0)

    def test_multi_hit_game_count(self):
        """1試合3安打以上のゲーム数を正しくカウントする"""
        sc = pd.DataFrame({
            "player_id":  [MLBAM] * 10,
            "game_pk":    [1001] * 5 + [1002] * 5,
            "game_date":  ["2025-04-01"] * 5 + ["2025-04-02"] * 5,
            "events":     ["single"] * 4 + ["home_run"] + ["single"] * 2 + [None] * 3,
            "launch_speed": [95.0] * 10,
            "launch_angle": [20.0] * 10,
            "hc_x":       [130.0] * 10,
            "stand":      ["R"] * 10,
            "description": ["hit_into_play"] * 10,
        })
        result = build(statcast=sc)
        # game_pk=1001 は5安打 (≥3) → カウント
        # game_pk=1002 は2安打 (<3) → カウントしない
        assert result.multi_hit_game_count == 1


# ──────────────────────────────────────────────
# FanGraphs Splits
# ──────────────────────────────────────────────

class TestSplits:
    def test_vs_lhp_woba_from_splits(self):
        splits = {
            "vs_lhp": pd.DataFrame({"wOBA": [0.380]}),
            "vs_rhp": pd.DataFrame({"wOBA": [0.310]}),
        }
        agg = BatterAggregator(mlbam_id=MLBAM, fg_id=FG_ID, bref_id=MLBAM)
        result = agg.build(
            statcast_batter=pd.DataFrame(),
            batter_expected=make_expected(),
            batter_percentile=make_percentile(),
            sprint_speed=make_sprint(),
            outs_above_average=make_oaa(),
            batting_stats_fg=make_batting_fg(),
            batting_stats_bref=make_batting_bref(),
            fielding_run_value=make_frv(),
            splits=splits,
        )
        assert result.vs_lhp_woba == pytest.approx(0.380)
        assert result.vs_rhp_woba == pytest.approx(0.310)

    def test_empty_splits_returns_zero(self):
        result = build()
        assert result.vs_lhp_woba == 0.0
        assert result.risp_avg == 0.0
