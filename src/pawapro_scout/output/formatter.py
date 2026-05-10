"""
output/formatter.py
PlayerRecord を人が読みやすいテキスト形式に変換して保存する。
"""

from __future__ import annotations

from pathlib import Path

from pawapro_scout.models import BatterRating, PitcherRating, PlayerRecord

_SEP = "━" * 55


def _special(items: list[str], label: str) -> str:
    value = "、".join(items) if items else "なし"
    return f"  {label}: {value}"


def _rank_abilities(d: dict[str, str | None]) -> str:
    parts = [f"{k}={v}" for k, v in d.items() if v is not None]
    if not parts:
        return "  ランク制: なし"
    # 3 項目ごとに改行
    lines = []
    for i in range(0, len(parts), 3):
        lines.append("    " + ", ".join(parts[i : i + 3]))
    return "  ランク制:\n" + "\n".join(lines)


def _pitcher_section(p: PitcherRating) -> str:
    b = p.basic
    header = f"  球速: {b.球速}km/h  /  コントロール: {b.コントロール}  /  スタミナ: {b.スタミナ}"

    # 球種（名称列を揃える）
    max_len = max((len(e.名称) for e in p.pitches), default=4)
    pitch_lines = []
    for e in p.pitches:
        pad = "　" * (max_len - len(e.名称))  # 全角スペースで桁揃え
        pitch_lines.append(f"    {e.名称}{pad} (変化量: {e.変化量})")

    return "\n".join([
        "【投手】",
        header,
        "",
        "  球種:",
        *pitch_lines,
        "",
        _rank_abilities(p.rank_abilities),
        "",
        _special(p.gold_special, "金特"),
        _special(p.blue_special, "青特"),
        _special(p.red_special,  "赤特"),
    ])


def _batter_section(b: BatterRating) -> str:
    bs = b.basic
    header = (
        f"  弾道: {bs.弾道}  /  ミート: {bs.ミート}  /  パワー: {bs.パワー}  /  "
        f"走力: {bs.走力}  /  肩力: {bs.肩力}  /  守備力: {bs.守備力}  /  捕球: {bs.捕球}"
    )
    return "\n".join([
        "【野手】",
        header,
        "",
        _rank_abilities(b.rank_abilities),
        "",
        _special(b.gold_special, "金特"),
        _special(b.blue_special, "青特"),
        _special(b.red_special,  "赤特"),
    ])


def to_text(record: PlayerRecord, team: str = "") -> str:
    """PlayerRecord を整形済みテキスト文字列で返す。"""
    team_str = f" / {team}" if team else ""
    title = f"{record.player} ({record.season}{team_str})"

    sections: list[str] = [_SEP, title, _SEP]

    if record.pitcher is not None:
        sections.append(_pitcher_section(record.pitcher))

    if record.batter is not None:
        if record.pitcher is not None:
            sections.append("")  # 二刀流の区切り
        sections.append(_batter_section(record.batter))

    sections.append(_SEP)
    return "\n".join(sections) + "\n"


def save_txt(record: PlayerRecord, path: Path | str, team: str = "") -> None:
    """PlayerRecord をテキストファイルに書き出す。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(to_text(record, team=team), encoding="utf-8")
