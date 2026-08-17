"""Event and trace file helpers for mctl."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping


def append_jsonl(path: Path, row: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(row), sort_keys=True) + "\n")
