"""
assess/batter/blue_special.py
野手の青特殊能力を査定する。

青特                  判定指標
固め打ち              1試合3安打以上の試合 >= 8試合
プルヒッター          引っ張り方向HR% >= 80%
広角打法              逆方向HR >= 5本
ヘッドスライディング  Sprint Speed >= 29.0 AND bolts >= 10
パワーヒッター        Barrel% >= 12% AND 平均打球角度 12〜18度
ラインドライブ        平均打球角度 10〜15度 AND Hard Hit% >= 45%
アベレージヒッター    xBA >= .280 AND Whiff% <= 20%

※ チャンス◯・対左投手◯ はランク制能力へ移行のため削除
"""

from __future__ import annotations

from pawapro_scout.config import (
    AVG_HITTER_WHIFF_MAX,
    AVG_HITTER_XBA_MIN,
    BOLT_MIN_FOR_INFIELD,
    HEADSLI_SPEED_MIN,
    LINE_DRIVE_HARD_HIT_MIN,
    LINE_DRIVE_LA_MAX,
    LINE_DRIVE_LA_MIN,
    MULTI_HIT_GAME_MIN,
    OPPO_HR_MIN,
    POWER_HITTER_BARREL_MIN,
    POWER_HITTER_LA_MAX,
    POWER_HITTER_LA_MIN,
    PULL_HR_PCT_MIN,
)
from pawapro_scout.models import BatterStats


def assess_blue_special(stats: BatterStats) -> list[str]:
    """BatterStats から獲得する青特リストを返す。"""
    result: list[str] = []

    if _is_katamari_uchi(stats):
        result.append("固め打ち")

    if _is_pull_hitter(stats):
        result.append("プルヒッター")

    if _is_koukauku(stats):
        result.append("広角打法")

    if _is_headsli(stats):
        result.append("ヘッドスライディング")

    if _is_power_hitter(stats):
        result.append("パワーヒッター")

    if _is_line_drive(stats):
        result.append("ラインドライブ")

    if _is_avg_hitter(stats):
        result.append("アベレージヒッター")

    return result


# ──────────────────────────────────────────────
# 各青特の判定
# ──────────────────────────────────────────────

def _is_katamari_uchi(stats: BatterStats) -> bool:
    """固め打ち: 1試合3安打以上の試合 >= 8試合。"""
    return stats.multi_hit_game_count >= MULTI_HIT_GAME_MIN


def _is_pull_hitter(stats: BatterStats) -> bool:
    """プルヒッター: 引っ張り方向HR% >= 80%。"""
    return stats.pull_hr_pct >= PULL_HR_PCT_MIN


def _is_koukauku(stats: BatterStats) -> bool:
    """広角打法: 逆方向HR >= 5本。"""
    return stats.oppo_hr_count >= OPPO_HR_MIN


def _is_headsli(stats: BatterStats) -> bool:
    """ヘッドスライディング: Sprint Speed >= 29.0 AND bolts >= 10。"""
    return stats.sprint_speed >= HEADSLI_SPEED_MIN and stats.bolts >= BOLT_MIN_FOR_INFIELD


def _is_power_hitter(stats: BatterStats) -> bool:
    """パワーヒッター: Barrel% >= 12% AND 平均打球角度 12〜18度。"""
    return (
        stats.barrel_percent >= POWER_HITTER_BARREL_MIN
        and POWER_HITTER_LA_MIN <= stats.avg_launch_angle <= POWER_HITTER_LA_MAX
    )


def _is_line_drive(stats: BatterStats) -> bool:
    """ラインドライブ: 平均打球角度 10〜15度 AND Hard Hit% >= 45%。"""
    return (
        LINE_DRIVE_LA_MIN <= stats.avg_launch_angle <= LINE_DRIVE_LA_MAX
        and stats.hard_hit_percent >= LINE_DRIVE_HARD_HIT_MIN
    )


def _is_avg_hitter(stats: BatterStats) -> bool:
    """アベレージヒッター: xBA >= .280 AND Whiff% <= 20%。"""
    return (
        stats.xba >= AVG_HITTER_XBA_MIN
        and stats.whiff_percent <= AVG_HITTER_WHIFF_MAX
    )
