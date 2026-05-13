"""
tests/test_aggregate_pitcher.py
PitcherAggregator のテスト。
スタブ DataFrame を渡して PitcherStats / PitchAggregated が正しく設定されるか検証する。
"""

import pytest
import pandas as pd
import numpy as np

from pawapro_scout.aggregate.pitcher_aggregator import PitcherAggregator
from pawapro_scout.config import MIN_PITCH_USAGE_PCT
from pawapro_scout.models import PitchAggregated, PitcherStats

MLBAM = 660271
FG_ID = 19755


# ──────────────────────────────────────────────
# スタブ生成ヘルパー
# ──────────────────────────────────────────────

def make_percentile(player_id=MLBAM, **kwargs):
    d = {
        "player_id": [player_id],
        "k_percent":          [92],
        "bb_percent":         [65],
        "exit_velocity_avg":  [80],
        "pitch_hand_speed":   [85],
    }
    d.update({k: [v] for k, v in kwargs.items()})
    return pd.DataFrame(d)


def make_pitching_fg(fg_id=FG_ID, **kwargs):
    d = {
        "IDfg": [fg_id],
        "K%":   [0.310],   # 31.0 %
        "BB%":  [0.060],   # 6.0 %
        "G":    [30],
        "GS":   [25],
        "IP":   [160.2],
        "WPA":  [2.8],
        "LOB%": [0.740],
        "HR/9": [1.1],
        "Hard%": [0.350],
        "Pitches": [3100],
    }
    d.update({k: [v] for k, v in kwargs.items()})
    return pd.DataFrame(d)


def make_pitching_bref(mlbam_id=MLBAM, **kwargs):
    d = {
        "mlbID": [mlbam_id],
        "G":  [30],
        "GS": [25],
        "IP": [160.2],
        "PO": [3],
        "SB": [10],
        "CS": [4],
    }
    d.update({k: [v] for k, v in kwargs.items()})
    return pd.DataFrame(d)


def make_pitcher_fielding(player_id=MLBAM, oaa=2):
    return pd.DataFrame({"player_id": [player_id], "outs_above_average": [oaa]})


def make_pitch_arsenal(player_id=MLBAM):
    return pd.DataFrame({
        "player_id":        [player_id, player_id, player_id],
        "pitch_type":       ["FF",   "SL",  "CH"],
        "run_value_per100": [-1.5,   -3.2,  -0.8],
    })


def make_statcast_pitcher(n_ff=100, n_sl=60, n_ch=30, player_id=MLBAM):
    """FF / SL / CH の3球種スタブ"""
    rng = np.random.default_rng(0)
    rows = []
    for pt, n, v_base, pfx_x_base, pfx_z_base in [
        ("FF", n_ff, 96.5, -0.8, 1.1),
        ("SL", n_sl, 86.0,  1.2, 0.2),
        ("CH", n_ch, 87.0, -1.0, 0.5),
    ]:
        rows.append(pd.DataFrame({
            "player_id":    [player_id] * n,
            "game_pk":      list(range(1, n + 1)),
            "pitch_type":   [pt] * n,
            "release_speed": rng.uniform(v_base - 1, v_base + 1, n),
            "release_pos_x": rng.normal(0, 0.3, n),
            "release_pos_z": rng.normal(6, 0.2, n),
            "pfx_x":         rng.normal(pfx_x_base, 0.1, n),
            "pfx_z":         rng.normal(pfx_z_base, 0.1, n),
            "description":   ["swinging_strike"] * (n // 3) + ["ball"] * (n - n // 3),
        }))
    return pd.concat(rows, ignore_index=True)


def build(statcast=None, **kwargs):
    agg = PitcherAggregator(mlbam_id=MLBAM, fg_id=FG_ID, bref_id=MLBAM)
    return agg.build(
        statcast_pitcher    = statcast if statcast is not None else make_statcast_pitcher(),
        pitcher_expected    = kwargs.get("pitcher_expected",    pd.DataFrame()),
        pitcher_percentile  = kwargs.get("pitcher_percentile",  make_percentile()),
        pitching_stats_fg   = kwargs.get("pitching_stats_fg",   make_pitching_fg()),
        pitching_stats_bref = kwargs.get("pitching_stats_bref", make_pitching_bref()),
        pitcher_fielding    = kwargs.get("pitcher_fielding",    make_pitcher_fielding()),
        pitch_arsenal       = kwargs.get("pitch_arsenal",       make_pitch_arsenal()),
        pitcher_active_spin = kwargs.get("pitcher_active_spin", pd.DataFrame()),
    )


# ──────────────────────────────────────────────
# 返り値型テスト
# ──────────────────────────────────────────────

class TestReturnType:
    def test_returns_pitcher_stats(self):
        result = build()
        assert isinstance(result, PitcherStats)

    def test_pitches_are_list_of_pitch_aggregated(self):
        result = build()
        assert isinstance(result.pitches, list)
        for p in result.pitches:
            assert isinstance(p, PitchAggregated)

    def test_empty_statcast_returns_empty_pitches(self):
        result = build(statcast=pd.DataFrame())
        assert result.pitches == []


# ──────────────────────────────────────────────
# 球速
# ──────────────────────────────────────────────

class TestVelocity:
    def test_max_velocity_from_statcast(self):
        sc = make_statcast_pitcher()
        # FF の最大値を強制設定
        ff_mask = sc["pitch_type"] == "FF"
        sc.loc[ff_mask, "release_speed"] = 97.0
        sc.loc[sc[ff_mask].index[0], "release_speed"] = 100.2
        result = build(statcast=sc)
        assert result.max_velocity_mph == pytest.approx(100.2)

    def test_max_velocity_zero_if_no_statcast(self):
        result = build(statcast=pd.DataFrame())
        assert result.max_velocity_mph == 0.0


# ──────────────────────────────────────────────
# 球種集計 (PitchAggregated)
# ──────────────────────────────────────────────

class TestPitchAggregated:
    def test_pitch_count_matches_usage_threshold(self):
        """usage% < MIN_PITCH_USAGE_PCT の球種は含まれない"""
        result = build()
        # FF:100, SL:60, CH:30 → 計190球  CH=30/190≈15.8% > 5% → 含まれる
        pitch_types = {p.pitch_type for p in result.pitches}
        assert "FF" in pitch_types
        assert "SL" in pitch_types
        assert "CH" in pitch_types

    def test_low_usage_pitch_excluded(self):
        """使用率が MIN_PITCH_USAGE_PCT 未満の球種は除外される"""
        # KN を1球だけ追加 (全体に対してほぼ 0%)
        sc = make_statcast_pitcher(n_ff=200, n_sl=100, n_ch=50)
        extra = pd.DataFrame({
            "player_id":    [MLBAM],
            "game_pk":      [9999],
            "pitch_type":   ["KN"],
            "release_speed": [68.0],
            "release_pos_x": [0.0],
            "release_pos_z": [6.0],
            "pfx_x":         [0.0],
            "pfx_z":         [0.0],
            "description":   ["ball"],
        })
        sc = pd.concat([sc, extra], ignore_index=True)
        result = build(statcast=sc)
        pitch_types = {p.pitch_type for p in result.pitches}
        assert "KN" not in pitch_types  # 1/351 ≈ 0.28% < 5%

    def test_pitches_sorted_by_usage_descending(self):
        result = build()
        usages = [p.usage_pct for p in result.pitches]
        assert usages == sorted(usages, reverse=True)

    def test_velocity_avg_is_reasonable(self):
        result = build()
        ff = next(p for p in result.pitches if p.pitch_type == "FF")
        assert 94.0 < ff.velocity_avg < 99.0

    def test_whiff_pct_calculated(self):
        result = build()
        ff = next(p for p in result.pitches if p.pitch_type == "FF")
        # swinging_strike / (swinging_strike + ball) = 33/100 ≈ 33%
        assert 0.0 <= ff.whiff_pct <= 100.0

    def test_horizontal_break_in_inches(self):
        """pfx_x は feet → × 12 で inches に変換される"""
        result = build()
        ff = next(p for p in result.pitches if p.pitch_type == "FF")
        # pfx_x_base ≈ -0.8 feet → -9.6 inches 前後
        assert abs(ff.horizontal_break) < 20.0   # 物理的に合理的な範囲

    def test_delta_v_positive_for_offspeed(self):
        """オフスピード球の delta_v は正 (FF より遅い)"""
        result = build()
        ch = next(p for p in result.pitches if p.pitch_type == "CH")
        assert ch.delta_v_from_fastball > 0.0

    def test_rv_per_100_from_arsenal(self):
        """pitch_arsenal から RV/100 が正しく取れる"""
        result = build()
        sl = next(p for p in result.pitches if p.pitch_type == "SL")
        assert sl.rv_per_100 == pytest.approx(-3.2)


# ──────────────────────────────────────────────
# コントロール
# ──────────────────────────────────────────────

class TestControl:
    def test_k_percent_converted(self):
        result = build(pitching_stats_fg=make_pitching_fg(**{"K%": 0.310}))
        assert result.k_percent == pytest.approx(31.0)

    def test_bb_percent_converted(self):
        result = build(pitching_stats_fg=make_pitching_fg(**{"BB%": 0.060}))
        assert result.bb_percent == pytest.approx(6.0)

    def test_k_percentile_from_percentile(self):
        result = build(pitcher_percentile=make_percentile(k_percent=95))
        assert result.k_percentile == 95

    def test_bb_percentile_from_percentile(self):
        result = build(pitcher_percentile=make_percentile(bb_percent=70))
        assert result.bb_percentile == 70


# ──────────────────────────────────────────────
# スタミナ
# ──────────────────────────────────────────────

class TestStamina:
    def test_games_from_fg(self):
        result = build(pitching_stats_fg=make_pitching_fg(G=32))
        assert result.games == 32

    def test_ip_from_fg(self):
        result = build(pitching_stats_fg=make_pitching_fg(IP=175.0))
        assert result.ip == pytest.approx(175.0)

    def test_avg_pitches_per_game_calculated_from_fg(self):
        """FanGraphs の Pitches / G (全試合) から算出される (先発)"""
        result = build(pitching_stats_fg=make_pitching_fg(Pitches=3000, G=30))
        assert result.avg_pitches_per_game == pytest.approx(100.0)

    def test_avg_pitches_per_game_for_reliever(self):
        """救援投手 (GS=0) でも G で割って算出される"""
        # 救援 70 登板で 1890 球 → 27 球/試合
        result = build(pitching_stats_fg=make_pitching_fg(Pitches=1890, G=70, GS=0))
        assert result.avg_pitches_per_game == pytest.approx(27.0)

    def test_avg_pitches_none_if_no_data(self):
        """G = 0 かつ Statcast も空のとき avg_pitches_per_game は None"""
        result = build(
            pitching_stats_fg=make_pitching_fg(G=0, Pitches=0),
            statcast=pd.DataFrame(),
        )
        assert result.avg_pitches_per_game is None


# ──────────────────────────────────────────────
# bref / P-OAA
# ──────────────────────────────────────────────

class TestBrefAndFielding:
    def test_pickoffs_from_bref(self):
        result = build(pitching_stats_bref=make_pitching_bref(PO=5))
        assert result.pickoffs == 5

    def test_sb_against_from_bref(self):
        result = build(pitching_stats_bref=make_pitching_bref(SB=12))
        assert result.sb_against == 12

    def test_p_oaa_from_pitcher_fielding(self):
        result = build(pitcher_fielding=make_pitcher_fielding(oaa=4))
        assert result.p_oaa == 4

    def test_p_oaa_none_when_zero(self):
        result = build(pitcher_fielding=make_pitcher_fielding(oaa=0))
        assert result.p_oaa is None


# ──────────────────────────────────────────────
# FanGraphs Splits
# ──────────────────────────────────────────────

class TestSplits:
    def test_splits_xwoba(self):
        splits = {
            "risp":    pd.DataFrame({"xwOBA": [0.310]}),
            "vs_lhp":  pd.DataFrame({"xwOBA": [0.280]}),
            "vs_rhp":  pd.DataFrame({"xwOBA": [0.340]}),
            "high_lev": pd.DataFrame({"xwOBA": [0.295]}),
        }
        agg = PitcherAggregator(mlbam_id=MLBAM, fg_id=FG_ID, bref_id=MLBAM)
        result = agg.build(
            statcast_pitcher=make_statcast_pitcher(),
            pitcher_expected=pd.DataFrame(),
            pitcher_percentile=make_percentile(),
            pitching_stats_fg=make_pitching_fg(),
            pitching_stats_bref=make_pitching_bref(),
            pitcher_fielding=make_pitcher_fielding(),
            pitch_arsenal=make_pitch_arsenal(),
            pitcher_active_spin=pd.DataFrame(),
            splits=splits,
        )
        assert result.risp_xwoba     == pytest.approx(0.310)
        assert result.vs_lhp_xwoba   == pytest.approx(0.280)
        assert result.vs_rhp_xwoba   == pytest.approx(0.340)
        assert result.high_lev_xwoba == pytest.approx(0.295)

    def test_empty_splits_returns_zero(self):
        result = build()
        assert result.risp_xwoba == 0.0
        assert result.high_lev_xwoba == 0.0


# ──────────────────────────────────────────────
# リリースポイント安定性
# ──────────────────────────────────────────────

class TestReleaseStddev:
    def test_release_stddev_calculated(self):
        result = build()
        # make_statcast_pitcher で release_pos_x の std ≈ 0.3
        assert result.release_x_stddev > 0.0
        assert result.release_z_stddev > 0.0

    def test_release_stddev_zero_on_empty_df(self):
        result = build(statcast=pd.DataFrame())
        assert result.release_x_stddev == 0.0
        assert result.release_z_stddev == 0.0
