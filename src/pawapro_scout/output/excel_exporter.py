"""
output/excel_exporter.py
取得した生データを Excel の複数シートに書き出す（目視確認用）。

出力先: output/<season>/raw/<name_jp>.xlsx
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def export_excel(
    path: Path,
    league: dict[str, pd.DataFrame],
    player_batter: dict[str, Any] | None = None,
    player_pitcher: dict[str, Any] | None = None,
) -> None:
    """
    生データを Excel の複数シートに書き出す。

    Args:
        path: 出力先 xlsx ファイルパス
        league: league-wide DataFrame の辞書
        player_batter: 野手用 player-specific データ辞書 (None = 野手データなし)
        player_pitcher: 投手用 player-specific データ辞書 (None = 投手データなし)
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    sheets: dict[str, pd.DataFrame] = {}

    # ── league-wide ────────────────────────────────
    _add(sheets, "期待値_野手",     league, "batter_expected")
    _add(sheets, "期待値_投手",     league, "pitcher_expected")
    _add(sheets, "パーセンタイル_野手", league, "batter_percentile")
    _add(sheets, "パーセンタイル_投手", league, "pitcher_percentile")
    _add(sheets, "SprintSpeed",    league, "sprint_speed")
    _add(sheets, "OAA",            league, "outs_above_average")
    _add(sheets, "FG_打撃",        league, "batting_stats_fg")
    _add(sheets, "FG_投球",        league, "pitching_stats_fg")
    _add(sheets, "Bref_打撃",      league, "batting_stats_bref")
    _add(sheets, "Bref_投球",      league, "pitching_stats_bref")
    _add(sheets, "FRV",            league, "fielding_run_value")
    _add(sheets, "外野肩力",        league, "outfielder_throws")
    _add(sheets, "捕手Pop",         league, "catcher_throwing")
    _add(sheets, "捕手Framing",     league, "catcher_framing")
    _add(sheets, "捕手Blocking",    league, "catcher_blocking")
    _add(sheets, "投手守備",        league, "pitcher_fielding")
    _add(sheets, "球種RV",          league, "pitch_arsenal")
    _add(sheets, "投手スピン",      league, "pitcher_active_spin")

    # ── 野手 player-specific ──────────────────────
    if player_batter:
        _add(sheets, "Statcast_打撃", player_batter, "statcast_batter")
        splits_b = player_batter.get("splits") or {}
        for split_name, df in splits_b.items():
            _add_df(sheets, f"FG_Split_{split_name}", df)

    # ── 投手 player-specific ──────────────────────
    if player_pitcher:
        _add(sheets, "Statcast_投球", player_pitcher, "statcast_pitcher")
        _add(sheets, "ゾーン別",      player_pitcher, "savant_zone")
        _add(sheets, "1回xwOBA",      player_pitcher, "savant_inning1")
        _add(sheets, "7回以降xwOBA",  player_pitcher, "savant_inning7plus")
        splits_p = player_pitcher.get("splits") or {}
        for split_name, df in splits_p.items():
            _add_df(sheets, f"FG_Split_P_{split_name}", df)

    if not sheets:
        logger.warning("書き出すシートがありません")
        return

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for sheet_name, df in sheets.items():
            if df is not None and not df.empty:
                # シート名は31文字以内
                safe_name = sheet_name[:31]
                df.to_excel(writer, sheet_name=safe_name, index=False)

    logger.info(f"Excel 出力: {path} ({len(sheets)} シート)")


def _add(
    sheets: dict[str, pd.DataFrame],
    sheet_name: str,
    data_dict: dict,
    key: str,
) -> None:
    """辞書から DataFrame を取得してシートに追加する。"""
    df = data_dict.get(key)
    _add_df(sheets, sheet_name, df)


def _add_df(
    sheets: dict[str, pd.DataFrame],
    sheet_name: str,
    df,
) -> None:
    if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
        sheets[sheet_name] = df
