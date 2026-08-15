#!/usr/bin/env python3
"""Proof 5: no non-terminal manifest row is preserved into invisibility.

Under B2.10, decisions-track is a legacy/migration fallback, not a normal
presentation lane. A manifest row with a real file and a status that is not
confidently terminal must therefore migrate to the unified pile. Preserving it
would leave it unreachable from the stack-first presentation path.

Usage:
  proof5_no_nonterminal_unmapped.py <inventory.jsonl>

Exit 0 = PASS. Exit 1 = FAIL.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path
from typing import Any


TERMINAL_PREFIXES = (
    "adjudicated",
    "rescinded",
    "auto-dispatched",
    "moot",
    "superseded",
)


def status_text(row: dict[str, Any]) -> str:
    value = row.get("manifest_status")
    if value is None:
        value = row.get("file_status")
    return str(value or "").strip().lower()


def is_terminal(row: dict[str, Any]) -> bool:
    status = status_text(row)
    return any(status.startswith(prefix) for prefix in TERMINAL_PREFIXES)


def is_preserved_presentable_manifest_row(row: dict[str, Any]) -> bool:
    if row.get("kind") != "manifest_row":
        return False
    action = str(row.get("migration_action") or "")
    if not action.startswith("preserve"):
        return False
    # Missing-file rows cannot be copied into pile by this file-only migration.
    return action != "preserve_missing_file"


def main(path: str) -> int:
    rows = [
        json.loads(line)
        for line in Path(path).read_text(errors="replace").splitlines()
        if line.strip()
    ]
    offenders = [
        row
        for row in rows
        if is_preserved_presentable_manifest_row(row) and not is_terminal(row)
    ]

    print(f"inventory rows            : {len(rows)}")
    print(
        "preserved manifest rows   : "
        f"{sum(1 for row in rows if is_preserved_presentable_manifest_row(row))}"
    )
    print(f"non-terminal preserved    : {len(offenders)}   <-- must be 0")

    if offenders:
        print()
        print("OFFENDERS:")
        counts = collections.Counter(status_text(row) for row in offenders)
        for status, count in counts.most_common():
            print(f"  {count:3d}x status={status[:80]}")
        print()
        for row in offenders[:20]:
            print(
                "  "
                f"n={str(row.get('legacy_n')):>5} "
                f"unlock={str(row.get('unlock_count')):>3} "
                f"action={str(row.get('migration_action'))[:28]:28} "
                f"status={status_text(row)[:52]:52} "
                f"slug={str(row.get('legacy_slug'))[:40]}"
            )
        print()
        print("PROOF 5: FAIL - non-terminal manifest rows would be stranded.")
        return 1

    print()
    print("PROOF 5: PASS - every non-terminal manifest row is migration-visible.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: proof5_no_nonterminal_unmapped.py <inventory.jsonl>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
