#!/usr/bin/env python3
"""Enforce the BP4 reaping rules that had no enforcement anywhere (#238).

POLICY-beads.md states BP4.2(b), BP4.2(c) and BP4.4(d); nothing checked them.
The sharpest consequence #238 records is a CIRCULAR DUPLICATE COLLAPSE -- beads
closed as duplicates of each other, leaving a live item with no open survivor.
Both halves of that are mechanical, so both are checked here:

  BP4.2(c) a duplicate closure names the SURVIVING bead, and a survivor that is
           itself closed is not a survivor. If every bead named in the close
           reason is also closed, the work has silently left the board.
  BP4.2(b) a supersede/absorb closure must NAME the absorbing bead. A reason
           that says "superseded" and names nothing cannot be verified by
           anyone, which is the state BP4.5 ("doubt defers") exists to prevent.
  BP4.4(d) decision beads are never reaped -- adjudication history is permanent
           (B2.2). A decision bead closed with a REAPING reason is the
           violation; a decision bead closed on an adjudicated verdict is
           normal and is not flagged.

WHAT THIS DOES NOT DO. It does not reopen anything. Reversing a closure is a
data repair with its own blast radius and belongs to a human with the context
for each bead; #238's own audit recorded its verdicts as non-destructive
`bd comment` notes for exactly that reason. This reports.

Exit codes (P6.2): 0 clean, 1 violations (each named), 2 store unreadable.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter

BEAD_ID = re.compile(r'\b([a-z]{2,4}-(?=[a-z0-9]*\d)[a-z0-9]{3,9})\b')

#: Reasons that assert another bead carries the work forward. Matched on the
#: reason text because that is where the sweep records its criterion; BP4.3(3)
#: requires the criterion to appear there.
DUPLICATE_RE = re.compile(r'\bduplicate|\bdupe?\b', re.I)
SUPERSEDE_RE = re.compile(r'supersed|absorb|subsumed|folded into|rolled into', re.I)
#: An AUTOMATED reaping closure. BP4.4(d) forbids REAPING a decision bead; it
#: does not forbid a human adjudicating one closed.
#:
#: NARROWED after this check produced two false positives on its first live run
#: against the kolchin mathcity rig:
#:
#:   mc-wg331  "REJECTED by Taylor 2026-08-27 18:46 EDT. Candidate 1 ... is
#:              refuted at source and must not ship: ..."
#:   mc-kjot0  "Superseded by mc-y88p0 (P0), which revises the same mc-67snh
#:              and carries a finding this one lacked: ..."
#:
#: Both are ADJUDICATIONS. The first is a verdict with an authorizer and a
#: date; the second supersedes one decision with a newer one and names it.
#: B2.2 makes adjudication history permanent -- it does not make a decision
#: bead unclosable. The old pattern matched the word "supersed" anywhere in
#: the reason, so any reasoned human verdict that used the word was reported
#: as a policy violation.
#:
#: So this now matches only the literal close reasons an automated sweep
#: writes. gascity's reaper has exactly one
#: (reaper.sh:68 WORKFLOW_ROOT_CLOSE_REASON), and it is unambiguous.
#: A sweep that grows a new signature must be added here -- which is a smaller
#: and more honest failure mode than guessing from prose.
REAP_RE = re.compile(
    r'stale inactive workflow root auto-closed by reaper'
    r'|auto-closed by reaper'
    r'|old.useless bead',
    re.I,
)


def close_reason(bead: dict) -> str:
    md = bead.get("metadata") or {}
    return str(bead.get("close_reason") or md.get("mctl_close_reason") or "")


def main() -> int:
    ap = argparse.ArgumentParser(description="BP4 reaping-rule audit")
    ap.add_argument("--rig-root", required=True)
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

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
        print(f"BP4_AUDIT: UNREADABLE -- {exc}", file=sys.stderr)
        return 2

    state = {r["id"]: str(r.get("status", "")).lower() for r in rows}
    closed_at = {r["id"]: str(r.get("closed_at") or "") for r in rows}

    def survived_at(survivor: str, when: str) -> bool:
        """Was `survivor` still open when a duplicate of it was closed at `when`?

        BP4.2(c) governs the state AT CLOSE TIME, not today. Checking today's
        state instead over-reports badly: a survivor that was open when the
        duplicate was reaped and closed LATER because the work actually got
        finished is the rule working, not a violation. Measured on hecke, 2 of
        4 sampled "violations" were exactly that --

            he-z5f83 closed 2026-07-10T18:52:08Z
              he-w38gm closed 2026-07-12T10:27:25Z   <- survivor outlived it: fine
            he-0rk2.8 closed 2026-07-04T05:12:43Z
              he-0rk2  closed 2026-07-01T05:29:46Z   <- ALREADY closed: violation

        Unknown timestamps resolve to "survived": a missing date is not
        evidence of a violation, and inventing one manufactures findings.
        """
        if state.get(survivor) in ("open", "in_progress"):
            return True
        their_close = closed_at.get(survivor, "")
        if not their_close or not when:
            return True
        return their_close > when
    closed = [r for r in rows if str(r.get("status", "")).lower() in ("closed", "done")]

    no_survivor, unnamed_supersede, reaped_decisions = [], [], []
    counts: Counter = Counter()

    for bead in closed:
        reason = close_reason(bead)
        if not reason:
            continue
        # Ids named in the reason, excluding the bead's own id -- "duplicate of
        # itself" is noise, not a survivor.
        named = [b for b in BEAD_ID.findall(reason) if b != bead["id"]]

        if DUPLICATE_RE.search(reason):
            counts["duplicate_closures"] += 1
            if not named:
                counts["duplicate_without_named_survivor"] += 1
                no_survivor.append((bead["id"], "names no survivor", reason))
            elif not any(survived_at(b, closed_at.get(bead["id"], "")) for b in named):
                # Every named survivor was ALREADY closed when this bead was
                # reaped: the work left the board with nothing carrying it.
                counts["duplicate_all_survivors_closed_first"] += 1
                mine = closed_at.get(bead["id"], "?")
                shown = ", ".join(
                    f"{b}(closed {closed_at.get(b, '?')[:10]})" for b in named[:3]
                )
                no_survivor.append((
                    bead["id"],
                    f"reaped {mine[:10]}; every named survivor was already closed: {shown}",
                    reason,
                ))

        if SUPERSEDE_RE.search(reason) and not DUPLICATE_RE.search(reason):
            counts["supersede_closures"] += 1
            if not named:
                unnamed_supersede.append((bead["id"], reason))

        if str(bead.get("issue_type", "")).lower() == "decision" and REAP_RE.search(reason):
            reaped_decisions.append((bead["id"], reason))

    report = {
        "closed_total": len(closed),
        "counts": dict(counts),
        "bp4_2c_no_open_survivor": [{"bead": b, "why": w} for b, w, _ in no_survivor],
        "bp4_2b_supersede_names_nothing": [{"bead": b} for b, _ in unnamed_supersede],
        "bp4_4d_reaped_decision_beads": [{"bead": b} for b, _ in reaped_decisions],
        "rig_root": args.rig_root,
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"BP4_AUDIT: {len(closed)} closed beads, {dict(counts)}")
        if no_survivor:
            print(f"BP4_AUDIT: BP4.2(c) -- {len(no_survivor)} duplicate closure(s) "
                  f"with NO OPEN SURVIVOR (the work has left the board):")
            for bid, why, _ in no_survivor[:40]:
                print(f"    {bid:<12} {why}")
            if len(no_survivor) > 40:
                print(f"    ... and {len(no_survivor) - 40} more "
                      f"(--json for the full list; not truncated there)")
        if unnamed_supersede:
            print(f"BP4_AUDIT: BP4.2(b) -- {len(unnamed_supersede)} supersede/absorb "
                  f"closure(s) naming no absorbing bead:")
            for bid, _ in unnamed_supersede[:20]:
                print(f"    {bid}")
        if reaped_decisions:
            print(f"BP4_AUDIT: BP4.4(d) -- {len(reaped_decisions)} DECISION bead(s) "
                  f"closed with a reaping reason (B2.2: adjudication is permanent):")
            for bid, _ in reaped_decisions[:20]:
                print(f"    {bid}")
        if not (no_survivor or unnamed_supersede or reaped_decisions):
            print("BP4_AUDIT: OK -- no BP4.2(b), BP4.2(c) or BP4.4(d) violation found.")

    return 1 if (no_survivor or unnamed_supersede or reaped_decisions) else 0


if __name__ == "__main__":
    raise SystemExit(main())
