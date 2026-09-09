#!/usr/bin/env python3
"""Decision beads whose §4 options may have been overtaken by later material (#235).

#235: a brief's `§4 — Options` is a static text block that can be invalidated by
measurement taken AFTER deposit, and nothing detects it. `decision_options()`
reads two sources in B2.4/B2.8 order -- the bead description, then the markdown
cache -- and NEVER the bead's notes or comments. So a CORRECTION appended after
deposit leaves the adjudicator's §4 unchanged and the stale option still
selectable by `--option`.

Its worked example: brief `he-99eqp6`, whose option (A) was invalidated by a
later patch-id measurement, with the correction recorded as a note nothing reads.

WHAT THIS REPORTS, AND WHAT IT DOES NOT. It reports a SIGNAL, not a verdict:
a decision bead that has comments AND was updated after it was created has
material that arrived after its options were written. That material may be a
correction that invalidates an option, or it may be routine discussion. **This
tool cannot tell those apart and does not pretend to** -- reading the comment
text and judging it is the adjudicator's job, and the point is that today
nothing even raises a hand.

Measured on ~/gt/mathcity when this was written: 43 decision beads carry
comments; 40 of those were updated after creation.

Exit codes (P6.2):
    0  no decision bead has post-deposit material
    1  some do -- each named, with its comment count
    2  the store could not be read: NOT the same as "none found"
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from mctl_limits import resolve as _resolve_limit  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="stale §4 options signal (#235)")
    ap.add_argument("--rig-root", required=True)
    ap.add_argument("--open-only", action="store_true",
                    help="only beads still open -- a closed decision's options "
                         "can no longer be selected, so it cannot be the harm "
                         "#235 describes")
    ap.add_argument("--timeout", type=int, default=None,
                    help="seconds; 0 = no deadline. Default from "
                         "assets/mctl/limits.toml [bead_store_read_seconds].")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    args.timeout, source = _resolve_limit("bead_store_read_seconds", args.timeout)
    if source == "fallback":
        print(f"NOTE: limits.toml unreadable; using built-in {args.timeout}s",
              file=sys.stderr)

    try:
        proc = subprocess.run(
            ["bd", "list", "--all", "--limit", "0", "--json", "--readonly"],
            cwd=args.rig_root, capture_output=True, text=True, timeout=args.timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip()[:300])
        data = json.loads(proc.stdout)
        rows = data if isinstance(data, list) else data.get("issues", [])
    except Exception as exc:
        print(f"STALE_OPTIONS: UNREADABLE -- {exc}", file=sys.stderr)
        return 2

    flagged, decisions = [], 0
    for bead in rows:
        if str(bead.get("issue_type", "")) != "decision":
            continue
        if args.open_only and str(bead.get("status", "")).lower() not in ("open", "in_progress"):
            continue
        decisions += 1
        comments = int(bead.get("comment_count") or 0)
        created = str(bead.get("created_at") or "")
        updated = str(bead.get("updated_at") or "")
        # BOTH conditions, deliberately. comment_count alone catches routine
        # discussion on an untouched bead; updated_at alone moves for reasons
        # that have nothing to do with new material (a label, a status change).
        # Together they mean: something arrived, and the bead changed after its
        # options were written.
        if comments > 0 and created and updated and updated > created:
            flagged.append((bead["id"], comments, str(bead.get("status", "")),
                            str(bead.get("title", ""))[:46]))

    report = {
        "decision_beads": decisions,
        "flagged": [{"bead": b, "comments": c, "status": s} for b, c, s, _ in flagged],
        "open_only": args.open_only,
        "rig_root": args.rig_root,
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"STALE_OPTIONS: {decisions} decision bead(s) examined"
              f"{' (open only)' if args.open_only else ''}")
        if flagged:
            print(f"STALE_OPTIONS: {len(flagged)} carry material that arrived AFTER "
                  f"their options were written:")
            for bead, comments, status, title in flagged[:40]:
                print(f"    {bead:<11} comments={comments:<3} {status:<8} {title}")
            if len(flagged) > 40:
                print(f"    ... and {len(flagged) - 40} more (--json for all)")
            print()
            print("This is a SIGNAL, not a verdict. `decision_options()` reads the "
                  "bead description and the markdown cache, never the notes, so a "
                  "correction recorded after deposit cannot reach §4. Read the "
                  "comments before selecting an option on these.")
        else:
            print("STALE_OPTIONS: OK -- no decision bead has post-deposit material.")

    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
