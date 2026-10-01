#!/usr/bin/env python3
"""Analyse the Mayor session catalog's objectives_eval corpus.

Read-only.  Never writes the catalog.  Pure stdlib.

Answers one question: given how objectives have ACTUALLY gone across the
recorded sessions, how should the next charge be sized and ORDERED?

Design note, because it is the whole point of the skill:
  * The POSITION effect is measured WITHIN a session (which slot of the same
    charge got done), so it is not confounded by era, seat quality, or how hard
    that session's work happened to be.
  * The COUNT effect is measured BETWEEN sessions, so it IS confounded by era.
    It is reported with that warning attached and must not be quoted bare.
"""
import json, os, re, sys
from collections import defaultdict, Counter


def find_catalog(explicit=None):
    if explicit:
        return explicit
    env = os.environ.get("MAYOR_STATE_DIR")
    if env:
        return os.path.join(env, "session-catalog.json")
    city = os.environ.get("CITY_ROOT") or os.path.expanduser("~/HQ")
    return os.path.join(city, "mathcity-mayor", "session-catalog.json")


def norm_completed(v):
    v = str(v).strip().lower()
    if v.startswith("y"):
        return "yes"
    if v.startswith("p"):
        return "partial"
    if v.startswith("n"):
        return "no"
    return "unknown"


# A STANDING CHORE is an objective that recurs every session by construction —
# writing the handoff, the run-log shard, the catalog entry.  It is small,
# mandatory, and gets done wherever it sits.  Mixing chores in with work
# objectives HIDES the position effect: in this corpus the whole position-6
# anomaly was one chore ("Keep the K-chain alive") completing 4/4 in the last
# slot, while WORK objectives at position 6 completed 0/2.
CHORE_RE = re.compile(r"k-?chain|hand-?off|run-?log|catalog|continuity", re.I)


def is_chore(text):
    return bool(CHORE_RE.search(text or ""))


def load(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except json.JSONDecodeError as e:
        sys.exit(f"catalog is not valid JSON: {path}\n  {e}")
    except OSError as e:
        sys.exit(f"cannot read catalog: {path}\n  {e}")


def extract(catalog):
    """Return (rows, defects).  Normalises the two key spellings and records
    every entry the schema does not actually match."""
    rows, defects = [], []
    for s in catalog:
        k = s.get("mayor_session")
        ev = s.get("objectives_eval")
        if ev is None:
            continue
        if not isinstance(ev, list):
            defects.append((k, f"objectives_eval is {type(ev).__name__}, not a list"))
            continue
        structured = [o for o in ev if isinstance(o, dict)]
        for o in ev:
            if not isinstance(o, dict):
                defects.append((k, f"objectives_eval contains a bare {type(o).__name__}"))
        for i, o in enumerate(structured):
            if "improvement" in o and "improve" not in o:
                defects.append((k, "row uses key 'improvement'; the handoff spec says 'improve'"))
            rows.append({
                "session": k,
                "pos": i + 1,
                "of": len(structured),
                "completed": norm_completed(o.get("completed")),
                "objective": str(o.get("objective", "")),
                "improve": str(o.get("improve") or o.get("improvement") or ""),
                "chore": is_chore(str(o.get("objective", ""))),
            })
    return rows, defects


def pct(a, b):
    return f"{100.0 * a / b:3.0f}%" if b else "  n/a"


def report_defects(defects):
    """Always printed, INCLUDING when there is nothing left to analyse — an
    exclusion the reader cannot see is indistinguishable from an empty corpus."""
    print("\n== CORPUS SCHEMA DEFECTS ==")
    if not defects:
        print("  none.")
        return
    agg = Counter(d[1] for d in defects)
    for msg, n in agg.most_common():
        ks = sorted({d[0] for d in defects if d[1] == msg})
        print(f"  {n:3d}x  {msg}")
        print(f"        sessions: {ks}")
    print("  Rows with a drifted KEY are NORMALISED above, not dropped. Entries whose")
    print("  objectives_eval is PRESENT but not a list CANNOT be read at all and are")
    print("  excluded from every denominator; their sessions are named above.")
    print("  Entries whose objectives_eval key is ABSENT are NOT defects and are NOT")
    print("  listed here — see CORPUS COVERAGE, which names them. Before that section")
    print("  existed this report claimed every exclusion was named, and 20 of 28 were")
    print("  not.")


def report_coverage(catalog, rows):
    """Which sessions contribute rows, and which contribute NOTHING and why.

    `report_defects` names only entries whose `objectives_eval` is PRESENT but
    malformed.  `extract` skips an entry whose key is ABSENT with a bare
    `continue`, so those sessions were excluded from every denominator with no
    trace — which is precisely the failure this script exists to prevent,
    occurring inside this script.  Printed before the tables so the denominators
    below are read against the coverage that produced them."""
    have = {r["session"] for r in rows}
    contributing, absent, unreadable = [], [], []
    for s in catalog:
        k = s.get("mayor_session")
        if k in have:
            contributing.append(k)
        elif s.get("objectives_eval") is None:
            absent.append(k)
        else:
            unreadable.append(k)

    print("\n== CORPUS COVERAGE ==")
    print(f"  catalog entries      : {len(catalog)}")
    print(f"  CONTRIBUTING         : {len(contributing)}  {sorted(contributing)}")
    print(f"  contributing NOTHING : {len(absent) + len(unreadable)}")
    if absent:
        print(f"    objectives_eval ABSENT     : {len(absent):3d}  {sorted(absent)}")
    if unreadable:
        print(f"    objectives_eval UNREADABLE : {len(unreadable):3d}  {sorted(unreadable)}")

    if not contributing:
        return
    missing = [k for k in range(min(contributing), max(contributing) + 1)
               if k not in have]
    if not missing:
        return
    best = cur = [missing[0], missing[0]]
    for k in missing[1:]:
        if k == cur[1] + 1:
            cur[1] = k
        else:
            if cur[1] - cur[0] > best[1] - best[0]:
                best = cur
            cur = [k, k]
    if cur[1] - cur[0] > best[1] - best[0]:
        best = cur
    print(f"  LONGEST CONTIGUOUS GAP : K{best[0]}-K{best[1]} "
          f"({best[1] - best[0] + 1} sessions)")
    print("  => The COUNT table is BETWEEN-session and is drawn from a corpus with")
    print("     that hole in it, so it is era-confounded on coverage grounds alone,")
    print("     independently of the warning printed with it. The POSITION table is")
    print("     WITHIN-session and is unaffected by the gap.")


def main():
    path = find_catalog(sys.argv[1] if len(sys.argv) > 1 else None)
    if not os.path.exists(path):
        sys.exit(f"catalog not found: {path}\nPass a path, or set MAYOR_STATE_DIR / CITY_ROOT.")
    catalog = load(path)
    rows, defects = extract(catalog)

    print(f"CHECK-MAYOR-OBJECTIVES  —  {path}")
    print(f"catalog entries: {len(catalog)}")
    if not rows:
        # Report the defects FIRST: "nothing to analyse" plus a silent exclusion
        # reads as "the corpus is empty", which is a different fact.
        report_defects(defects)
        sys.exit("\nNo readable objectives_eval rows. Nothing to analyse."
                 + (" Every entry was excluded for the reason(s) above."
                    if defects else ""))

    sessions = sorted({r["session"] for r in rows})
    print(f"structured objective rows: {len(rows)} across {len(sessions)} sessions "
          f"(K{sessions[0]}–K{sessions[-1]})")
    report_coverage(catalog, rows)

    # ---- headline completion -------------------------------------------------
    c = Counter(r["completed"] for r in rows)
    print("\n== COMPLETION ==")
    for k in ("yes", "partial", "no", "unknown"):
        if c[k]:
            print(f"  {k:8s} {c[k]:3d}  {pct(c[k], len(rows))}")

    # ---- position effect (WITHIN-session; the robust one) --------------------
    bypos = defaultdict(list)
    bywork = defaultdict(list)
    bychore = defaultdict(list)
    for r in rows:
        ok = r["completed"] == "yes"
        bypos[r["pos"]].append(ok)
        (bychore if r["chore"] else bywork)[r["pos"]].append(ok)

    print("\n== POSITION IN THE CHARGE vs COMPLETION  (within-session: NOT era-confounded) ==")
    print("  WORK objectives (standing chores excluded — see below for why):")
    for p in sorted(bywork):
        v = bywork[p]
        flag = "" if len(v) >= 5 else "   <- small n, indicative only"
        print(f"    position {p}: {sum(v):2d}/{len(v):<2d} = {pct(sum(v), len(v))}{flag}")

    chore_rows = [x for v in bychore.values() for x in v]
    if chore_rows:
        print("  STANDING CHORES (handoff / run-log / catalog / continuity):")
        for p in sorted(bychore):
            v = bychore[p]
            print(f"    position {p}: {sum(v):2d}/{len(v):<2d} = {pct(sum(v), len(v))}")
        print(f"    overall: {sum(chore_rows)}/{len(chore_rows)} = "
              f"{pct(sum(chore_rows), len(chore_rows))}  REGARDLESS of position")
        print("    => Chores are small and mandatory, so they complete wherever they sit.")
        print("       Do NOT read a chore in the last slot as evidence that the last slot")
        print("       is safe. Separating them is what makes the work-objective decay")
        print("       visible at all.")

    print("  ALL rows combined (for reference — the mixed view that hides the effect):")
    for p in sorted(bypos):
        v = bypos[p]
        print(f"    position {p}: {sum(v):2d}/{len(v):<2d} = {pct(sum(v), len(v))}")

    first, last = [], []
    for k in sessions:
        sr = sorted([r for r in rows if r["session"] == k and not r["chore"]],
                    key=lambda r: r["pos"])
        if len(sr) >= 3:
            first.append(sr[0]["completed"] == "yes")
            last.append(sr[-1]["completed"] == "yes")
    if first:
        print(f"\n  FIRST-listed: {sum(first)}/{len(first)} = {pct(sum(first), len(first))}")
        print(f"  LAST-listed : {sum(last)}/{len(last)} = {pct(sum(last), len(last))}")
        delta = 100.0 * (sum(first) / len(first) - sum(last) / len(last))
        print(f"  gap: {delta:+.0f} points in favour of being listed FIRST")
        if delta > 10:
            print("  => ORDER IS LOAD-BEARING. An objective you actually want done goes FIRST.")
            print("     An objective that has survived several charges unattempted is not")
            print("     'unimportant' and is not necessarily 'too large' — it may simply")
            print("     never have been placed where a seat reaches it. Move it, or strike it.")

    # ---- count effect (BETWEEN-session; confounded) --------------------------
    bycount = defaultdict(list)
    persess = {}
    for k in sessions:
        sr = [r for r in rows if r["session"] == k]
        y = sum(1 for r in sr if r["completed"] == "yes")
        persess[k] = (len(sr), y)
        bycount[len(sr)].append(y / len(sr))
    print("\n== OBJECTIVE COUNT vs COMPLETION  (between-session: ERA-CONFOUNDED) ==")
    for n in sorted(bycount):
        a = bycount[n]
        ks = [k for k in sessions if persess[k][0] == n]
        print(f"  charged {n}: {len(a)} session(s), mean {pct(sum(a), len(a))}   sessions={ks}")
    print("  WARNING: these are between-session comparisons. A block of consecutive")
    print("  sessions that shared a count also shared an era, a backlog and a seat")
    print("  quality. Do NOT quote a count rule from this table alone — check whether")
    print("  the sessions behind a row are contiguous before believing it.")

    # ---- per-session ---------------------------------------------------------
    print("\n== PER SESSION ==")
    for k in sessions:
        n, y = persess[k]
        print(f"  K{k:<4} {y}/{n}  {'#' * y}{'.' * (n - y)}  {pct(y, n)}")

    # ---- carried objectives --------------------------------------------------
    print("\n== OBJECTIVES THAT RECUR ACROSS SESSIONS ==")
    seen = defaultdict(list)
    for r in rows:
        key = " ".join(re.sub(r"[^a-z0-9 ]", "", r["objective"].lower()).split()[:6])
        if key:
            seen[key].append((r["session"], r["completed"], r["pos"], r["of"]))
    rec = [(k, v) for k, v in seen.items() if len(v) > 1]
    if not rec:
        print("  none detected by leading-text match.")
    for k, v in sorted(rec, key=lambda x: -len(x[1])):
        print(f"  {len(v)}x  {k[:56]}")
        for (sess, comp, p, of) in v:
            print(f"        K{sess}: {comp:7s} (position {p} of {of})")
    print("  NOTE: matching is on the first six words of the objective text, so")
    print("  rephrasing between sessions hides a recurrence. A LOW count here is")
    print("  weak evidence of no carrying, not evidence of none.")

    # ---- schema defects ------------------------------------------------------
    report_defects(defects)

    # ---- recommendation ------------------------------------------------------
    print("\n== RECOMMENDATION FOR THE NEXT CHARGE ==")
    if first and 100.0 * (sum(first) / len(first) - sum(last) / len(last)) > 10:
        print("  1. Put the objective you most want done in POSITION 1. The position")
        print("     table above is the evidence, and it is within-session.")
        print("  2. Any objective carried unattempted for 3+ charges: either move it to")
        print("     position 1 for exactly one session as a test, or STRIKE it. Carrying")
        print("     a dead objective costs every future seat the read and teaches the")
        print("     chain that the charge is partly decorative.")
    tail = [p for p in sorted(bywork) if len(bywork[p]) >= 5]
    if tail:
        worst = min(tail, key=lambda p: sum(bywork[p]) / len(bywork[p]))
        print(f"  3. Completion is weakest at position {worst} "
              f"({pct(sum(bywork[worst]), len(bywork[worst]))}). Treat everything at or")
        print("     below that slot as aspirational, and do not charge anything there")
        print("     that a later session will be blocked on.")
    print("  4. Re-run this after every handoff. It is cheap and the corpus grows by")
    print("     one session each time; a rule that held at n=13 may not at n=20.")


if __name__ == "__main__":
    main()
