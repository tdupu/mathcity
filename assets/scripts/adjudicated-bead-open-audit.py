#!/usr/bin/env python3
"""Find briefs the human ADJUDICATED whose bead never closed (#72).

"Decided but never started" was undetectable. `lost-bead-filter.py` validates
lost-bead classification RECORDS that something else already produced -- it is a
schema validator, not a discoverer -- so a decision that simply never became
work produced no record for it to validate, and nothing else looked. #72
measured 18 such briefs on 2026-08-19, the oldest open 41 days.

Re-measured on ~/gt/.beads/briefs (2026-09-09):

    stack briefs                              98
    adjudicated                               24
      naming a resolvable bead                20
        bead CLOSED                           15   <- decision became work
        bead still OPEN                        3   <- the #72 condition, live
        bead NOT FOUND in its store            2   <- a different lost shape
      naming no resolvable bead                 4

Most of the original 18 were resolved by hand since. The CLASS is what persists:
nothing detects the next one.

TWO FAILURE SHAPES, REPORTED SEPARATELY. An adjudicated brief whose bead is open
is stalled work. An adjudicated brief whose bead is absent from its store is a
broken reference. Merging them into one "lost" count would hide that the second
needs a different repair, and inflates a number people act on.

BEAD IDS ARE MATCHED STRICTLY. A loose `[a-z]+-[a-z]+` pattern harvests English
from filenames -- an earlier pass of this audit reported `vs-session` and
`in-steps` (from "...crons-durable-VS-SESSION-brief.md" and
"...shell-commands-IN-STEPS-brief.md") as bead ids, overcounting resolvable
beads by 10%. Real ids carry a digit in the suffix; the pattern requires one.

Exit codes (P6.2):

    0  no adjudicated brief has an open or missing bead
    1  at least one does -- every one named, grouped by shape
    2  a store could not be read: NOT the same as "nothing found"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

#: Real bead ids carry a digit in the suffix. See the module docstring for the
#: concrete overcount a looser pattern produced.
#:
#: ANCHORED -- for validating a whole candidate string with .match(). Using it
#: with .findall() over a blob silently returns [] for every input, because the
#: anchors can never hold mid-string. That bug made the inventory scan below
#: match nothing at all while reporting success; BEAD_SCAN exists so the two
#: uses cannot be confused again.
BEAD_ID = re.compile(r'^[a-z]{2,4}-(?=[a-z0-9]*\d)[a-z0-9]{3,9}$')

#: UNANCHORED -- for pulling candidates OUT of a slug or path, then validated
#: with BEAD_ID. The suffix floor is 3, not 4: gsp-eu2 (#72's headline case) has
#: a three-character suffix, and a floor of 4 excluded the one bead the
#: inventory scan was added to find.
BEAD_SCAN = re.compile(r'\b([a-z]{2,4}-(?=[a-z0-9]*\d)[a-z0-9]{3,9})\b')

ADJUDICATED_STATUSES = {"adjudicated", "decided", "approved"}
OPEN_STATUSES = {"open", "in_progress"}


def brief_bead_id(path: Path, text: str) -> str | None:
    """Frontmatter first, filename second -- never prose.

    Frontmatter is the declared source; the filename is a fallback for briefs
    that predate the field. Prose is deliberately not searched: a brief that
    MENTIONS a bead is not a brief ABOUT it.
    """
    m = re.search(r'^(?:source_bead|bead|bead_id):\s*["\']?([a-z0-9-]+)', text, re.M)
    if m and BEAD_ID.match(m.group(1)):
        return m.group(1)
    for cand in re.findall(r'([a-z]{2,4}-[a-z0-9]{4,9})', path.name):
        if BEAD_ID.match(cand):
            return cand
    return None


def load_store(root: str, timeout: int) -> dict[str, str]:
    proc = subprocess.run(
        ["bd", "list", "--all", "--limit", "0", "--json", "--readonly"],
        cwd=root, capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"bd list in {root} failed: {proc.stderr.strip()[:300]}")
    data = json.loads(proc.stdout)
    rows = data if isinstance(data, list) else data.get("issues", [])
    return {r["id"]: str(r.get("status", "")).lower() for r in rows}


def main() -> int:
    ap = argparse.ArgumentParser(description="adjudicated-brief / open-bead audit")
    ap.add_argument("--brief-root", required=True)
    ap.add_argument("--store", action="append", default=[], metavar="PREFIX=PATH",
                    help="bead-prefix to store root, repeatable (e.g. gt=$HOME/gt)")
    ap.add_argument("--inventory", action="append", default=[], metavar="PATH",
                    help="migration inventory JSONL to scan in addition to brief "
                         "lanes; repeatable. Rows carry no bead id -- it is "
                         "recovered from legacy_slug/legacy_file.")
    ap.add_argument("--lane", action="append",
                    default=None, metavar="NAME",
                    help="brief lane under --brief-root to scan; repeatable "
                         "(default: stack, archive, decisions-track)")
    ap.add_argument("--timeout", type=int, default=300)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    # argparse `append` with a list default would ACCUMULATE onto the default
    # rather than replace it, so --lane x would silently scan x plus all three.
    if not args.lane:
        args.lane = ["stack", "archive", "decisions-track"]

    # A prefix may name SEVERAL stores, and repeating --store for one prefix
    # ADDS rather than replaces. This is not a convenience -- it prevents a
    # whole class of false finding that this tool produced on its first live
    # run. Many rigs exist twice (~/repos/X and its gascity twin ~/gt/X) and
    # the bead may live in either. Pointed at ~/repos/hecke alone, the audit
    # reported he-0xr5b, he-i2k91 and he-z2kko as "bead NOT IN its store" --
    # a broken-reference finding someone would go chase. All three are CLOSED
    # in ~/gt/hecke. The beads were fine; the mapping was a guess.
    #
    # So NOT-FOUND now means "absent from every store given for this prefix",
    # which is the only form of that claim the tool can actually support.
    stores: dict[str, list[str]] = {}
    for spec in args.store:
        if "=" not in spec:
            print(f"--store expects PREFIX=PATH, got: {spec}", file=sys.stderr)
            return 2
        prefix, path = spec.split("=", 1)
        stores.setdefault(prefix, []).append(os.path.expanduser(path))

    root = Path(os.path.expanduser(args.brief_root))
    # SCANS EVERY LANE, not just `stack`, and RECURSIVELY -- `archive/` is one
    # directory per brief, so a non-recursive glob silently contributed zero
    # files while reporting the lane as scanned.
    #
    # ALSO READS MIGRATION INVENTORIES (--inventory), because brief FILES are
    # not the only place an adjudication is recorded. #72's headline case
    # proved it: gsp-eu2 is adjudicated and still OPEN (created 2026-07-09), and
    # a brief-file-only scan reported OK for exactly the bead the issue was
    # filed about -- its brief was migrated out of the decisions-track lane and
    # survives only as `.pile/*.bak` plus a row in
    # `migrations/2026-08-15-decisions-track-inventory.jsonl`:
    #
    #     legacy_slug      specialist-agents-gsp-eu2
    #     file_status      adjudicated
    #     migration_action preserve_terminal
    #
    # Those rows carry NO bead id field; the id is recoverable from
    # `legacy_slug`/`legacy_file`, which is why they are parsed rather than
    # read for a key that does not exist.
    lanes = [name for name in args.lane if (root / name).is_dir()]
    if not lanes:
        print(f"ADJ_AUDIT: UNREADABLE -- none of {args.lane} exist under {root}",
              file=sys.stderr)
        return 2

    briefs = sorted(
        (path for lane in lanes for path in (root / lane).rglob("*.md")),
        key=lambda p: p.name,
    )

    adjudicated = []
    for path in briefs:
        text = path.read_text(errors="replace")[:6000]
        status = re.search(r'^status:\s*(\S+)', text, re.M)
        if not status or status.group(1).strip().lower() not in ADJUDICATED_STATUSES:
            continue
        adjudicated.append((path, status.group(1).strip(), brief_bead_id(path, text)))

    # Inventory rows join the same population as brief files, so one bead named
    # by both is deduplicated -- reporting it twice would inflate the count.
    seen_beads = {bid for _, _, bid in adjudicated if bid}
    for inv_path in args.inventory:
        path = Path(os.path.expanduser(inv_path))
        if not path.is_file():
            print(f"ADJ_AUDIT: inventory not found, NOT scanned: {path}", file=sys.stderr)
            continue
        for line in path.read_text(errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            status = str(row.get("file_status") or row.get("manifest_status") or "")
            # Statuses here are free-text and highly decorated -- e.g.
            # "adjudicated:approve-b(push=false)". Prefix-matching is what makes
            # those count; an equality test against "adjudicated" would score
            # 122 rows as adjudicated and silently drop ~30 decorated ones.
            low = status.lower()
            if not (low.startswith("adjudicated") or low.startswith("approved")):
                continue
            blob = f"{row.get('legacy_slug') or ''} {row.get('legacy_file') or ''}"
            found = None
            for cand in BEAD_SCAN.findall(blob):
                if BEAD_ID.match(cand):
                    found = cand
            if not found or found in seen_beads:
                continue
            seen_beads.add(found)
            adjudicated.append((Path(f"{path.name}:{row.get('legacy_slug') or '?'}"),
                                status, found))

    loaded: dict[str, dict[str, str]] = {}
    unreadable: dict[str, str] = {}
    stalled, missing, unresolvable, no_store = [], [], [], []
    counts: Counter = Counter()

    for path, brief_status, bead_id in adjudicated:
        if not bead_id:
            unresolvable.append(path.name)
            continue
        prefix = bead_id.split("-")[0]
        roots = [r for r in stores.get(prefix, []) if os.path.isdir(r)]
        if not roots:
            no_store.append((bead_id, path.name, prefix))
            continue
        for root in roots:
            if root in loaded or root in unreadable:
                continue
            try:
                loaded[root] = load_store(root, args.timeout)
            except Exception as exc:
                unreadable[root] = str(exc)
        readable = [r for r in roots if r in loaded]
        if not readable:
            continue
        # First store that KNOWS the bead wins. A bead absent everywhere is the
        # only case that earns NOT-FOUND.
        state = "NOT-FOUND"
        for root in readable:
            found = loaded[root].get(bead_id)
            if found is not None:
                state = found
                break
        counts[state] += 1
        if state in OPEN_STATUSES:
            stalled.append((bead_id, brief_status, path.name, state))
        elif state == "NOT-FOUND":
            missing.append((bead_id, brief_status, path.name))

    report = {
        "adjudicated": len(adjudicated),
        "bead_states": dict(counts),
        "brief_root": str(args.brief_root),
        "missing_bead": [{"bead": b, "brief": n} for b, _, n in missing],
        "no_store_for_prefix": sorted({p for *_, p in no_store}),
        "lanes_scanned": lanes,
        "briefs_scanned": len(briefs),
        "stalled": [{"bead": b, "brief": n, "state": s} for b, _, n, s in stalled],
        "unreadable_stores": unreadable,
        "unresolvable_bead_id": unresolvable,
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"ADJ_AUDIT: {report['briefs_scanned']} briefs "
              f"across {'+'.join(lanes)}, "
              f"{len(adjudicated)} adjudicated, states={dict(counts)}")
        if stalled:
            print(f"ADJ_AUDIT: {len(stalled)} adjudicated brief(s) whose bead is "
                  f"STILL OPEN -- decided but never finished:")
            for bead, brief_status, name, state in stalled:
                print(f"    {bead:<12} bead={state:<12} brief={brief_status:<12} {name[:50]}")
        if missing:
            print(f"ADJ_AUDIT: {len(missing)} adjudicated brief(s) naming a bead "
                  f"NOT IN its store -- broken reference, a different repair:")
            for bead, brief_status, name in missing:
                print(f"    {bead:<12} brief={brief_status:<12} {name[:50]}")
        if unresolvable:
            print(f"ADJ_AUDIT: {len(unresolvable)} adjudicated brief(s) name no "
                  f"resolvable bead id (not scored either way)")
        if no_store:
            print(f"ADJ_AUDIT: no --store given for prefix(es): "
                  f"{', '.join(sorted({p for *_, p in no_store}))} -- NOT scored")
        if not stalled and not missing:
            print("ADJ_AUDIT: OK -- every adjudicated brief's bead is closed.")

    if unreadable:
        # A store that would not open cannot be reported as clean.
        for prefix, err in unreadable.items():
            print(f"ADJ_AUDIT: UNREADABLE store for '{prefix}': {err}", file=sys.stderr)
        return 2
    return 1 if (stalled or missing) else 0


if __name__ == "__main__":
    raise SystemExit(main())
