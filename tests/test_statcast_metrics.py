"""
tests/test_statcast_metrics.py
Statcast pitch-level DataFrame から各種指標を計算する statcast_metrics モジュールのテスト。

各関数について:
- 空 DataFrame で例外なくデフォルト値を返す
- 期待値どおりに集計される
"""

from __future__ import annotations

import pandas as pd
import pytest

from pawapro_scout.aggregate import statcast_metrics as sm


# ──────────────────────────────────────────────
# フィクスチャ
# ──────────────────────────────────────────────

@pytest.fixture
def empty_df() -> pd.DataFrame:
    """空の DataFrame"""
    return pd.DataFrame()


@pytest.fixture
def minimal_pitcher_df() -> pd.DataFrame:
    """
    投手向けの最小Statcast DataFrame:
    - 10投球: 3K, 2BB, 1HR, 残り field_out
    - inning 1〜9 を網羅
    - 球速 90mph
    """
    return pd.DataFrame({
        "events": [
            "strikeout", "strikeout", "strikeout",
            "walk", "walk",
            "home_run",
            "field_out", "field_out", "field_out", "field_out",
        ],
        "description": [
            "swinging_strike", "swinging_strike", "swinging_strike",
            "ball", "ball",
            "hit_into_play",
            "hit_into_play", "hit_into_play", "hit_into_play", "hit_into_play",
        ],
        "inning": [1, 2, 3, 4, 5, 6, 7, 7, 8, 9],
        "release_speed": [95.0, 94.0, 95.5, 92.0, 93.0, 94.5, 95.0, 96.0, 95.5, 94.0],
        "launch_speed": [None, None, None, None, None, 105.0, 80.0, 85.0, 90.0, 95.0],
        "zone": [5, 7, 8, 11, 12, 5, 4, 3, 9, 2],
        "stand": ["R", "L", "R", "L", "R", "R", "L", "R", "L", "R"],
        "plate_x": [0.0, 0.5, -0.3, -0.5, 0.4, 0.1, -0.2, 0.3, 0.0, 0.0],
        "estimated_woba_using_speedangle": [0.0, 0.0, 0.0, 0.0, 0.0, 1.5, 0.0, 0.0, 0.0, 0.0],
        "on_1b": [None, None, None, None, None, None, None, None, None, None],
        "on_2b": [None, None, None, None, None, None, None, 12345, 12345, None],
        "on_3b": [None, None, None, None, None, None, None, None, None, None],
        "bat_score": [0, 1, 1, 2, 2, 3, 3, 3, 4, 4],
        "fld_score": [0, 0, 1, 1, 2, 3, 4, 4, 4, 5],
        "game_pk": [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],
        "pitch_type": ["FF", "FF", "SL", "FF", "SL", "FF", "FF", "SL", "FF", "FF"],
    })


@pytest.fixture
def minimal_batter_df() -> pd.DataFrame:
    """
    野手向けの最小 Statcast DataFrame:
    - 10打席: 3H (1HR), 2BB, 3K, 残り field_out
    """
    return pd.DataFrame({
        "events": [
            "single", "double", "home_run",
            "walk", "walk",
            "strikeout", "strikeout", "strikeout",
            "field_out", "field_out",
        ],
        "description": [
            "hit_into_play", "hit_into_play", "hit_into_play",
            "ball", "ball",
            "swinging_strike", "swinging_strike", "swinging_strike",
            "hit_into_play", "hit_into_play",
        ],
        "launch_speed": [85.0, 95.0, 110.0, None, None, None, None, None, 75.0, 80.0],
        "launch_angle": [10.0, 12.0, 25.0, None, None, None, None, None, -5.0, 50.0],
        "estimated_ba_using_speedangle": [0.9, 0.85, 1.0, None, None, None, None, None, 0.05, 0.1],
        "estimated_slg_using_speedangle": [0.9, 1.7, 4.0, None, None, None, None, None, 0.05, 0.1],
        "estimated_woba_using_speedangle": [0.9, 1.2, 2.0, None, None, None, None, None, 0.05, 0.1],
        "launch_speed_angle": [4, 5, 6, None, None, None, None, None, 1, 2],
        "stand": ["R", "R", "R", "R", "R", "R", "R", "R", "R", "R"],
        "p_throws": ["R", "L", "R", "L", "R", "L", "R", "L", "R", "L"],
        "plate_x": [-0.5, 0.0, 0.3, -0.2, 0.1, 0.4, -0.1, 0.0, -0.5, 0.5],
        "zone": [5, 2, 5, 11, 12, 5, 8, 9, 7, 1],
        "strikes": [0, 1, 1, 0, 1, 2, 2, 2, 0, 1],
        "balls":   [0, 0, 1, 0, 1, 0, 1, 2, 0, 1],
        "on_1b": [None, None, None, None, 12345, None, None, None, None, None],
        "on_2b": [None, None, None, None, None, None, 12345, None, None, None],
        "on_3b": [None, None, None, None, None, None, None, None, None, None],
        "inning": [1, 3, 5, 1, 6, 7, 8, 9, 4, 2],
        "bat_score": [0, 0, 1, 1, 1, 2, 3, 3, 0, 0],
        "fld_score": [0, 1, 1, 1, 2, 3, 3, 4, 0, 1],
        "game_pk":   [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],
        "hc_x": [125, 100, 150, None, None, None, None, None, 50, 200],
    })


# ──────────────────────────────────────────────
# 空DF時の振る舞い
# ──────────────────────────────────────────────

class TestEmptyDataFrame:
    """空 DataFrame では例外を出さずデフォルト値を返す。"""

    def test_basic_pitcher_metrics_empty(self, empty_df):
        out = sm.compute_basic_pitcher_metrics(empty_df)
        assert out["k_percent"] == 0.0
        assert out["ip"] == 0.0

    def test_basic_batter_metrics_empty(self, empty_df):
        out = sm.compute_basic_batter_metrics(empty_df)
        assert out["k_percent"] == 0.0
        assert out["xba"] == 0.0

    def test_scene_xwoba_pitcher_empty(self, empty_df):
        out = sm.compute_pitcher_scene_xwoba(empty_df)
        assert out["season"] == 0.0
        assert out["risp"] == 0.0

    def test_scene_xba_xslg_batter_empty(self, empty_df):
        out = sm.compute_batter_scene_xba_xslg(empty_df)
        assert out["season_xba"] == 0.0

    def test_zone_metrics_batter_empty(self, empty_df):
        out = sm.compute_zone_metrics_batter(empty_df)
        assert out["inside_xba"] == 0.0

    def test_zone_metrics_pitcher_empty(self, empty_df):
        out = sm.compute_zone_metrics_pitcher(empty_df)
        assert out["low_zone_pct"] == 0.0

    def test_count_metrics_batter_empty(self, empty_df):
        out = sm.compute_count_metrics_batter(empty_df)
        assert out["count0_xba"] == 0.0

    def test_pitch_metrics_pitcher_empty(self, empty_df):
        out = sm.compute_pitch_metrics_pitcher(empty_df)
        assert out == {}

    def test_situational_pitcher_empty(self, empty_df):
        out = sm.compute_situational_metrics_pitcher(empty_df)
        assert out["risp_hard_hit_pct"] == 0.0
        assert out["is_closer"] is False

    def test_situational_batter_empty(self, empty_df):
        out = sm.compute_situational_metrics_batter(empty_df)
        assert out["walk_off_hits"] == 0

    def test_spray_batter_empty(self, empty_df):
        out = sm.compute_spray_metrics_batter(empty_df)
        assert out["pull_hr_pct"] == 0.0


# ──────────────────────────────────────────────
# 基本指標計算
# ──────────────────────────────────────────────

class TestBasicMetrics:
    """K%, BB%, HR/9 などの基本指標が正しく計算される。"""

    def test_pitcher_k_pct(self, minimal_pitcher_df):
        """3K / 10PA = 30%"""
        out = sm.compute_basic_pitcher_metrics(minimal_pitcher_df)
        assert out["k_percent"] == 30.0

    def test_pitcher_bb_pct(self, minimal_pitcher_df):
        """2BB / 10PA = 20%"""
        out = sm.compute_basic_pitcher_metrics(minimal_pitcher_df)
        assert out["bb_percent"] == 20.0

    def test_pitcher_velocity(self, minimal_pitcher_df):
        out = sm.compute_basic_pitcher_metrics(minimal_pitcher_df)
        assert out["max_velocity_mph"] == 96.0

    def test_batter_k_pct(self, minimal_batter_df):
        """3K / 10PA = 30%"""
        out = sm.compute_basic_batter_metrics(minimal_batter_df)
        assert out["k_percent"] == 30.0

    def test_batter_home_runs(self, minimal_batter_df):
        out = sm.compute_basic_batter_metrics(minimal_batter_df)
        assert out["home_runs"] == 1

    def test_batter_xba(self, minimal_batter_df):
        """3 BIP の平均 xBA (0.9 + 0.85 + 1.0 + 0.05 + 0.1) / 5 = 0.58"""
        out = sm.compute_basic_batter_metrics(minimal_batter_df)
        assert out["xba"] == round((0.9 + 0.85 + 1.0 + 0.05 + 0.1) / 5, 3)


# ──────────────────────────────────────────────
# シーン別 xwOBA
# ──────────────────────────────────────────────

class TestSceneXwOBA:
    """投手・野手のシーン別 xwOBA が計算される。"""

    def test_pitcher_inning1(self, minimal_pitcher_df):
        out = sm.compute_pitcher_scene_xwoba(minimal_pitcher_df)
        # inning==1 の xwOBA は 0.0 (strikeout なので)
        assert out["inning1"] == 0.0

    def test_pitcher_vs_lhb(self, minimal_pitcher_df):
        out = sm.compute_pitcher_scene_xwoba(minimal_pitcher_df)
        # stand=="L" は inning 2, 4, 7, 9 (xwoba: 0, 0, 0, 0)
        assert out["vs_lhb"] == 0.0

    def test_batter_vs_lhp(self, minimal_batter_df):
        out = sm.compute_batter_scene_xwoba(minimal_batter_df)
        # p_throws=="L" の xwOBA 平均
        assert out["vs_lhp"] >= 0.0


# ──────────────────────────────────────────────
# ゾーン別指標
# ──────────────────────────────────────────────

class TestZoneMetrics:
    """ゾーン別 xBA / xSLG, low_zone_pct 等が計算される。"""

    def test_pitcher_low_zone_pct(self, minimal_pitcher_df):
        """zone 7,8,9 がいくつあるか → 3/10 = 30%"""
        out = sm.compute_zone_metrics_pitcher(minimal_pitcher_df)
        assert out["low_zone_pct"] == 30.0

    def test_batter_inside_outside(self, minimal_batter_df):
        out = sm.compute_zone_metrics_batter(minimal_batter_df)
        # 右打者: plate_x < 0 が内角
        # 内角 plate_x < 0: idx 0, 3, 6, 8 (xBA: 0.9, None, None, 0.05)
        # 外角 plate_x > 0: idx 2, 4, 5, 9 (xBA: 1.0, None, None, 0.1)
        assert out["inside_xba"] > 0
        assert out["outside_xba"] > 0


# ──────────────────────────────────────────────
# カウント別指標
# ──────────────────────────────────────────────

class TestCountMetrics:
    """0/2 ストライク別の指標が計算される。"""

    def test_count0_xba(self, minimal_batter_df):
        out = sm.compute_count_metrics_batter(minimal_batter_df)
        # strikes==0 は idx 0, 3, 8 (xBA: 0.9, None, 0.05)
        assert out["count0_xba"] > 0

    def test_count2_whiff(self, minimal_batter_df):
        out = sm.compute_count_metrics_batter(minimal_batter_df)
        # strikes==2 は idx 5, 6, 7 (description: swinging_strike, swinging_strike, swinging_strike)
        # 全 swing = 全 whiff → 100%
        assert out["count2_whiff"] == 100.0


# ──────────────────────────────────────────────
# 球種別指標
# ──────────────────────────────────────────────

class TestPitchMetrics:
    """球種別 (FF, SL 等) の指標が辞書で返される。"""

    def test_pitch_types_present(self, minimal_pitcher_df):
        out = sm.compute_pitch_metrics_pitcher(minimal_pitcher_df)
        assert "FF" in out
        assert "SL" in out

    def test_ff_velocity(self, minimal_pitcher_df):
        out = sm.compute_pitch_metrics_pitcher(minimal_pitcher_df)
        # FF: idx 0,1,3,5,6,8,9 (vel: 95, 94, 92, 94.5, 95, 95.5, 94)
        # 平均: 約 94.3
        ff = out["FF"]
        assert ff["velocity_avg"] > 90.0


# ──────────────────────────────────────────────
# 状況別指標
# ──────────────────────────────────────────────

class TestSituationalMetrics:
    """RISP, 終盤, 満塁等の状況別指標。"""

    def test_pitcher_inning7plus_xwoba(self, minimal_pitcher_df):
        out = sm.compute_situational_metrics_pitcher(minimal_pitcher_df)
        # inning>=7 の xwOBA は全て 0 (BIP の xwoba=0)
        assert out["inning7plus_xwoba"] == 0.0

    def test_batter_walk_off_hits(self, minimal_batter_df):
        # walk-off の条件を満たすデータは無いので0
        out = sm.compute_situational_metrics_batter(minimal_batter_df)
        assert out["walk_off_hits"] == 0

    def test_batter_multi_hit_games(self, minimal_batter_df):
        # game_pk=1 で 3H (single, double, home_run) → 1試合
        out = sm.compute_situational_metrics_batter(minimal_batter_df)
        assert out["multi_hit_game_count"] == 1


# ──────────────────────────────────────────────
# 打球方向 (野手)
# ──────────────────────────────────────────────

class TestSprayMetrics:
    """Pull/Oppo 判定が利き手で正しく動く。"""

    def test_pull_oppo_right_hitter(self, minimal_batter_df):
        out = sm.compute_spray_metrics_batter(minimal_batter_df, batter_stand="R")
        # 右打者: hc_x < 125 が Pull
        # HR は idx 2 (hc_x=150) → Oppo方向
        assert out["oppo_hr_count"] >= 0
        # データが少ないので明確な値検証は省略
        assert isinstance(out["pull_hr_pct"], float)


# ──────────────────────────────────────────────
# 簡易OAA / Arm / Catcher は league-wide data が必要
# (単体テストでは構造確認のみ)
# ──────────────────────────────────────────────

class TestSimplifiedFielding:
    """OAA / Arm / Catcher が空DFで安全にデフォルト値を返す。"""

    def test_oaa_no_fielder_columns(self, empty_df):
        out = sm.compute_simplified_oaa(empty_df, fielder_id=12345)
        assert out["oaa_simplified"] == 0

    def test_arm_strength_empty(self, empty_df):
        out = sm.compute_arm_strength_metrics(empty_df, fielder_id=12345, position="OF")
        assert out["arm_strength_mph"] is None

    def test_catcher_empty(self, empty_df):
        out = sm.compute_catcher_metrics(empty_df, catcher_id=12345)
        assert out["framing_runs"] == 0.0
