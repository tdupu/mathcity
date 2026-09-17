#!/usr/bin/env python3
"""Find commits claimed by closed beads that no ref can reach.

THE FINDING (QUIMBY 71, ritt, 2026-09-17). Of 62 commit claims made by beads
closed 2026-09-10..09-17 in mathcity, **50 are held by no ref at all**. The
four classed "in main" are all the same base commit, recorded by steps titled
"Implement owned work". Zero commits claimed by any bead closed in that window
are reachable as new work on main. B3.1 was satisfied throughout: those closes
cite acceptance truthfully. B3.1 asks whether acceptance was verified; it never
asks whether the artifact is REACHABLE.

THREE-VALUED, NOT TWO, and this is load-bearing. `git branch --contains` is
blind to `refs/salvage/`. A two-valued sweep therefore re-reports every commit
it has already anchored, every tick, forever -- a catch rate that can never
reach zero. A detector that cannot succeed is the same family as a check that
cannot fail (P6.2), and the obvious design had exactly that bug.

    reachable  a branch contains it                      -- fine
    anchored   any ref contains it (tags, salvage, ...)  -- PRESERVED, not a finding
    stranded   the object exists, no ref holds it        -- counts
    absent     no such object here                       -- may be foreign, not stranded

TWO FIGURES THAT NEVER MERGE. Once anchored, stranded commits go quiet while
NONE has landed. A single number would report zero while fifty sit preserved
and unlanded -- B2.13 committed by the remedy itself. So:

    new this period          must reach zero before enforcement is licensed
    anchored-not-landed      falls ONLY when a commit truly reaches a branch

They are never summed. `report()` deliberately omits a `total` key so a caller
cannot present one by accident.

Read-only. Reports; anchors nothing, prunes nothing.

Usage:  check_unreachable_closes.py <repo> [--since YYYY-MM-DD] [--store DIR]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

OK, FOUND, CANNOT_VERIFY = 0, 1, 2

#: metadata keys under which a bead may record the commit that implemented it.
COMMIT_KEYS = (
    "gc.work_commit", "gc.implementation.commit", "gc.verified_commit",
    "gc.build.implementation_commit", "gc.implementation_commit",
    "gc.implementation.head_sha", "gc.worktree_commit", "gc.verified.commit",
    "code_review.fix_commit",
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True)


def classify(repo: Path, sha: str) -> str:
    """One of: reachable | anchored | stranded | absent."""
    if _git(repo, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
        return "absent"
    if _git(repo, "branch", "-a", "--contains", sha).stdout.strip():
        return "reachable"
    # EVERY namespace, not just heads -- tags, notes, stash, refs/salvage/...
    out = _git(repo, "for-each-ref", "--contains", sha, "--format=%(refname)").stdout
    return "anchored" if out.strip() else "stranded"


def report(repo: Path, pairs) -> dict:
    """Classify (bead, sha) pairs. Returns counts and the stranded detail.

    Deliberately carries NO `total`: the two figures answer different questions
    and summing them hides preserved-but-unlanded work behind a zero.
    """
    counts = {"reachable": 0, "anchored": 0, "stranded": 0, "absent": 0}
    stranded, anchored = [], []
    for bead, sha in pairs:
        k = classify(repo, sha)
        counts[k] += 1
        if k == "stranded":
            stranded.append((bead, sha))
        elif k == "anchored":
            anchored.append((bead, sha))
    return {
        "reachable": counts["reachable"],
        "anchored_not_landed": counts["anchored"],
        "stranded": counts["stranded"],
        "absent": counts["absent"],
        "stranded_detail": stranded,
        "anchored_detail": anchored,
    }


def claims_from_store(store: Path, since: str):
    """(bead, sha) pairs claimed by beads closed on/after `since`."""
    r = subprocess.run(
        ["bd", "list", "--all", "--limit", "0", "--json", "--readonly"],
        cwd=store, capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    rows = data if isinstance(data, list) else data.get("issues", [])
    pairs = set()
    for row in rows:
        if str(row.get("status", "")).lower() != "closed":
            continue
        if str(row.get("updated_at") or "")[:10] < since:
            continue
        md = row.get("metadata") or {}
        for k in COMMIT_KEYS:
            v = md.get(k)
            if isinstance(v, str) and len(v.strip()) >= 7:
                pairs.add((row.get("id"), v.strip()))
    return sorted(pairs)


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("repo")
    ap.add_argument("--since", default="2026-09-10")
    ap.add_argument("--store", default=None,
                    help="bead store to read claims from (default: repo)")
    a = ap.parse_args(argv[1:])

    repo = Path(a.repo).expanduser()
    if _git(repo, "rev-parse", "--git-dir").returncode != 0:
        print(f"I'm sorry, I can't do that -- {repo} is not a git repository.",
              file=sys.stderr)
        return CANNOT_VERIFY

    store = Path(a.store).expanduser() if a.store else repo
    pairs = claims_from_store(store, a.since)
    if pairs is None:
        print(f"UNREACHABLE_CLOSES: CANNOT VERIFY -- could not read the bead "
              f"store at {store}.\nThis is NOT a pass.", file=sys.stderr)
        return CANNOT_VERIFY

    rep = report(repo, pairs)
    print(f"UNREACHABLE_CLOSES: {len(pairs)} commit claim(s) from beads closed "
          f"since {a.since}")
    print(f"  reachable                 : {rep['reachable']}")
    print(f"  absent (may be foreign)   : {rep['absent']}")
    print()
    print(f"  NEW THIS PERIOD (stranded): {rep['stranded']}"
          "    <- must reach 0 before enforcement is licensed")
    print(f"  ANCHORED-NOT-LANDED       : {rep['anchored_not_landed']}"
          "    <- falls only when a commit reaches a branch")
    print("  (these two are never summed -- see module docstring)")

    if not pairs:
        print("\n  No claims found. That is NOT a clean bill: it means these "
              "beads record no commit, so reachability cannot be asked.",
              file=sys.stderr)
        return CANNOT_VERIFY

    if rep["stranded"]:
        print("\nSTRANDED -- no ref holds these; they die at the next gc:",
              file=sys.stderr)
        for bead, sha in rep["stranded_detail"][:20]:
            print(f"    {bead}  {sha[:12]}", file=sys.stderr)
        return FOUND
    return OK


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
