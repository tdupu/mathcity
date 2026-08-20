#!/usr/bin/env python3
"""Render the beadless-brief materialisation plan. Reads; never writes.

The one subprocess this script runs is the frozen `BD_READ_ARGV` below -- the
same read-only listing `mctl_core.beads` uses. No other `bd` verb appears
anywhere in this file, and `tests/mctl/test_materialize_plan.py` asserts it.

    python3 assets/scripts/plan_beadless_briefs.py --city ~/gt --format markdown
    python3 assets/scripts/plan_beadless_briefs.py --city ~/gt --format json
    python3 assets/scripts/plan_beadless_briefs.py --city ~/gt --format commands
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mctl_core.materialize_plan import (  # noqa: E402
    STORE_BY_PREFIX,
    build_plan,
    commands_for,
    rollback_commands,
    summarise,
)

#: The ONLY bd invocation this tool makes. Frozen as a tuple so a reader can
#: confirm at a glance that no create/update/close/dep verb is reachable.
BD_READ_ARGV = ("bd", "list", "--json", "--status", "all", "--limit", "200000")


def read_store(rig_root: Path) -> list[dict]:
    result = subprocess.run(
        ["bd", "-C", str(rig_root), *BD_READ_ARGV[1:]],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    return json.loads(result.stdout)


def build_index(city: Path) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for store in sorted(set(STORE_BY_PREFIX.values())):
        rig_root = city if store == "gt" else city / store
        if not (rig_root / ".beads").is_dir():
            continue
        for bead in read_store(rig_root):
            bead["_store"] = store
            index.setdefault(bead["id"], bead)
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", required=True, type=Path)
    parser.add_argument(
        "--format", choices=("markdown", "json", "commands", "summary"), default="summary"
    )
    args = parser.parse_args()

    city = args.city.expanduser().resolve()
    stack = city / ".beads" / "briefs" / "stack"
    texts = {path.name: path.read_text(encoding="utf-8", errors="replace")
             for path in sorted(stack.glob("*.md"))}
    rows = build_plan(texts, build_index(city))

    if args.format == "summary":
        print(json.dumps(summarise(rows), indent=2, sort_keys=True))
    elif args.format == "json":
        print(json.dumps([row.to_dict() for row in rows], indent=2, sort_keys=True))
    elif args.format == "commands":
        for row in rows:
            for line in commands_for(row):
                print(line)
        print()
        print("# rollback")
        for line in rollback_commands(rows):
            print(f"# {line}")
    else:
        print("| # | file | artifact | resolves | target rig | artifact type "
              "| proposed title | status | verdict | classes |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for number, row in enumerate(rows, start=1):
            print(
                f"| {number} | `{row.name}` | `{row.artifact_raw or '(absent)'}` "
                f"| {'yes' if row.resolves else 'no'} | {row.target_store} "
                f"| {'/'.join(row.artifact_types) or '—'} | {row.title} | {row.status} "
                f"| {row.verdict or '—'} | {', '.join(row.problem_classes) or '—'} |"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
