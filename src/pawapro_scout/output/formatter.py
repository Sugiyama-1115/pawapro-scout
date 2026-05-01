"""
output/formatter.py
PlayerRecord dataclass を JSON 文字列に変換する。
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

from pawapro_scout.models import PlayerRecord


def _to_dict(obj: Any) -> Any:
    """dataclass / list / dict / primitive を再帰的に dict 化する。"""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


def to_json(record: PlayerRecord, indent: int = 2) -> str:
    """PlayerRecord を整形済み JSON 文字列で返す。"""
    return json.dumps(_to_dict(record), ensure_ascii=False, indent=indent)


def save_json(record: PlayerRecord, path) -> None:
    """PlayerRecord を JSON ファイルに書き出す。"""
    from pathlib import Path
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(to_json(record), encoding="utf-8")
