#!/usr/bin/env python3
"""B3.1 audit: re-examine closures for verifiable acceptance (#233).

`mctl` can close a bead on a verdict without reading acceptance criteria, and
until this script NOTHING re-examined the closure afterwards. #233's two halves
are separate: `bead_close` now CAPTURES acceptance and advises when it is absent
(76c84cb), but capture at write time says nothing about the closures already on
record, and an advisory is non-blocking by design.

WHY THIS IS SCOPED BY DATE RATHER THAN AUDITING EVERYTHING. Measured on the live
rig (~/gt/mathcity, 1687 beads):

    closed            640
      with acceptance   0
      with reason     393
      neither         247

Auditing all 640 would fail permanently and identically on every run, which is
the definition of a check nobody reads. `mctl_close_acceptance` did not exist
before 76c84cb, so a closure predating it could not have carried the field --
scoring it as a violation measures the field's age, not the closure's quality.
The default cutoff is that commit's date; everything earlier is reported as
GRANDFATHERED and named as such, never silently dropped.

Exit codes (mathcity POLICY P6.2 -- a check that could not have failed must not
render as a check that passed):

    0  every in-scope closure carries acceptance (or none are in scope yet)
    1  in-scope closures lack acceptance -- each one named
    2  the bead store could not be read: a DIFFERENT outcome from "clean", and
       must never be reported as one
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

#: Date `mctl_close_acceptance` began being written (76c84cb). A closure before
#: this could not have carried the field. Bump this only when the capture
#: mechanism itself changes -- not to quiet a failing run.
ACCEPTANCE_CAPTURE_SINCE = "2026-09-09"


def load_beads(rig_root: str, timeout: int) -> list[dict]:
    proc = subprocess.run(
        ["bd", "list", "--all", "--limit", "0", "--json", "--readonly"],
        cwd=rig_root, capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"bd list failed (exit {proc.returncode}): {proc.stderr.strip()[:400]}"
        )
    data = json.loads(proc.stdout)
    return data if isinstance(data, list) else data.get("issues", [])


def acceptance_of(bead: dict) -> str:
    md = bead.get("metadata") or {}
    return str(md.get("mctl_close_acceptance") or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="B3.1 closure acceptance audit")
    ap.add_argument("--rig-root", required=True)
    ap.add_argument("--since", default=ACCEPTANCE_CAPTURE_SINCE,
                    help="YYYY-MM-DD; closures on/after this date are in scope")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--json", action="store_true", help="machine-readable report")
    args = ap.parse_args()

    try:
        beads = load_beads(args.rig_root, args.timeout)
    except Exception as exc:
        # Exit 2, NOT 1: "I could not look" is not "I looked and it was clean",
        # and it is not "I looked and found violations" either.
        report = {"error": str(exc), "outcome": "unreadable", "rig_root": args.rig_root}
        print(json.dumps(report, indent=2, sort_keys=True) if args.json
              else f"B31_AUDIT: UNREADABLE -- {exc}", file=sys.stderr)
        return 2

    closed = [b for b in beads
              if str(b.get("status", "")).lower() in ("closed", "done")]

    in_scope, grandfathered, undated = [], [], []
    for bead in closed:
        closed_at = str(bead.get("closed_at") or "")
        if not closed_at:
            # No closure date: cannot be placed on either side of the cutoff.
            # Reported in its own bucket rather than being assumed old (which
            # would hide real violations) or assumed new (which would
            # manufacture them).
            undated.append(bead)
        elif closed_at[:10] >= args.since:
            in_scope.append(bead)
        else:
            grandfathered.append(bead)

    missing = [b for b in in_scope if not acceptance_of(b)]

    report = {
        "closed_total": len(closed),
        "grandfathered_before_cutoff": len(grandfathered),
        "in_scope": len(in_scope),
        "in_scope_missing_acceptance": len(missing),
        "in_scope_with_acceptance": len(in_scope) - len(missing),
        "missing_ids": sorted(b["id"] for b in missing),
        "since": args.since,
        "undated_closures": len(undated),
        "undated_ids": sorted(b["id"] for b in undated),
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"B31_AUDIT: {len(closed)} closed, {len(in_scope)} in scope "
              f"since {args.since} ({len(grandfathered)} grandfathered, "
              f"{len(undated)} undated)")
        if missing:
            print(f"B31_AUDIT: {len(missing)} in-scope closure(s) with NO "
                  f"recorded B3.1 acceptance:")
            for bead in missing:
                print(f"    {bead['id']}  {str(bead.get('title',''))[:64]}")
            print("Record which acceptance limb was satisfied and where the "
                  "evidence is: bead_close(..., acceptance=...)")
        else:
            print("B31_AUDIT: OK -- every in-scope closure carries acceptance.")

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
