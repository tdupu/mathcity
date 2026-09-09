#!/usr/bin/env python3
"""Find spec beads whose root convoy is gone (#5).

`stuck-bead-watch` covers ROUTED WORK -- beads carrying `gc.routed_to`,
`gc.run_target` or `gc.execution_routed_to`. Measured on kolchin ~/HQ, that is
31 of 96 open beads, and the 65 it does not cover break down as:

    57  no gc.* metadata at all      ordinary unrouted backlog
     5  gc.kind: spec                "Step spec for X", carrying gc.root_bead_id
     3  session                      lifecycle records
     0  gc.exclusive_drain_reservation

The 57 are backlog and the 3 are not work. #5 asked whether the rest should be
covered, and the answer for spec beads is YES BUT NOT AS STUCK WORK:

  - A spec bead DESCRIBES a step. Nothing claims it, so it can never be "idle
    without a live worker" -- feeding it to stuck-bead-watch would produce a
    permanent false positive per spec.
  - But a spec whose ROOT CONVOY is closed or absent is genuinely orphaned:
    it describes work that will never run, and no other detector looks for it.

Different condition, different remedy, so: different detector. That is the
distinction #5 asks the detector contract to draw.

Exit codes (P6.2): 0 none found, 1 orphaned specs found (each named), 2 the
store could not be read -- distinct from "found nothing".
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from mctl_limits import resolve as _resolve_limit  # noqa: E402

OPEN_STATUSES = {"open", "in_progress"}


def main() -> int:
    ap = argparse.ArgumentParser(description="orphaned spec-bead detector (#5)")
    ap.add_argument("--rig-root", required=True)
    ap.add_argument("--timeout", type=int, default=None,
                    help="seconds; 0 = no deadline. Default from "
                         "assets/mctl/limits.toml [bead_store_read_seconds].")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    args.timeout, source = _resolve_limit("bead_store_read_seconds", args.timeout)
    if source == "fallback":
        print(f"NOTE: limits.toml unreadable; using built-in {args.timeout}s",
              file=sys.stderr)

    # WHICH STORE DID THIS ACTUALLY READ? (#273)
    # Every rig has two stores -- ~/repos/X and ~/gt/X -- and they diverge by up
    # to 16x (gascity-packs: 598 vs 9,895). Running an audit against the wrong
    # one produces a clean, plausible, wrong answer: on 2026-09-09 that nearly
    # became a data-loss report on a store that was fine. A findings header that
    # does not name its root is unfalsifiable by the reader.
    print(f"SPEC_WATCH: reading {os.path.abspath(os.path.expanduser(args.rig_root))}", file=sys.stderr)

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
        print(f"SPEC_WATCH: UNREADABLE -- {exc}", file=sys.stderr)
        return 2

    status = {r["id"]: str(r.get("status", "")).lower() for r in rows}

    orphaned, rootless = [], []
    specs = 0
    for bead in rows:
        md = bead.get("metadata") or {}
        if str(md.get("gc.kind", "")).lower() != "spec":
            continue
        if status.get(bead["id"]) not in OPEN_STATUSES:
            continue  # a closed spec is finished bookkeeping, not an orphan
        specs += 1
        root = str(md.get("gc.root_bead_id") or "").strip()
        if not root:
            # A spec naming no root cannot be checked either way. Reported in
            # its own bucket rather than assumed orphaned -- inventing a root
            # would manufacture findings.
            rootless.append((bead["id"], str(bead.get("title", ""))[:56]))
            continue
        root_state = status.get(root)
        if root_state is None:
            orphaned.append((bead["id"], root, "root ABSENT from this store",
                             str(bead.get("title", ""))[:48]))
        elif root_state not in OPEN_STATUSES:
            orphaned.append((bead["id"], root, f"root {root_state}",
                             str(bead.get("title", ""))[:48]))

    report = {
        "open_spec_beads": specs,
        "orphaned": [{"spec": s, "root": r, "why": w} for s, r, w, _ in orphaned],
        "rootless": [{"spec": s} for s, _ in rootless],
        "rig_root": args.rig_root,
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"SPEC_WATCH: {specs} open spec bead(s)")
        if orphaned:
            print(f"SPEC_WATCH: {len(orphaned)} ORPHANED -- the convoy that would "
                  f"have run these is finished or gone:")
            for spec, root, why, title in orphaned:
                print(f"    {spec:<12} root={root:<12} {why:<26} {title}")
            print("These describe work that will never run. They are NOT stuck "
                  "work -- nothing was ever going to claim them.")
        if rootless:
            print(f"SPEC_WATCH: {len(rootless)} spec(s) name no root "
                  f"(not scored either way):")
            for spec, title in rootless[:10]:
                print(f"    {spec:<12} {title}")
        if not orphaned:
            print("SPEC_WATCH: OK -- every open spec has a live root.")

    return 1 if orphaned else 0


if __name__ == "__main__":
    raise SystemExit(main())
