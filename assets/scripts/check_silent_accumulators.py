#!/usr/bin/env python3
"""Find pools that cannot staff the work aimed at them.

THE DEFECT THIS DETECTS (kolchin, 2026-08-24 .. 2026-09-10). `brief-shuffle`
was poured into rigs whose pool sat at max_active_sessions=0. Nothing ever
claimed the work, so the formula's clean-exit path was never reached and the
workflow roots simply stayed open -- 14 of them, 13 still open 17 days later.

It produced NO diagnostic at any layer. Not an order failure (the order fired
successfully). Not a stuck-bead hit (the beads carry gc.routed_to and read as
ordinary routed work). Not a `gc doctor` failure. Silent by construction,
which is why it took 17 days and a hand audit to surface.

The invariant: a pool capped at 0 must not be any enabled order's target.
Either the cap is wrong or the order is. Neither announces itself.

ORDER ROOTS ARE ENUMERATED, NEVER GUESSED. A first version of this check
scanned only `<city>/**/orders/` and reported OK on the very city the incident
happened in -- kolchin's orders resolve from the source checkout and the
import cache, not from ~/HQ/orders. It read zero files and rendered that as a
pass: the exact P6.2 failure the check exists to catch. An empty sweep is now
`CANNOT VERIFY` (exit 2), never OK.

BOTH cap blocks are read. kolchin carried TWO blocks named
`mathcity.brief-operator` -- one city-level, one rig-scoped (`dir = "mathcity"`)
-- with separate justifications. Reading only the first sent an earlier repair
at the wrong entry.

Read-only. Reports; repairs nothing.

Usage:  check_silent_accumulators.py [city-root] [--root DIR ...]
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

OK, FOUND, CANNOT_VERIFY = 0, 1, 2


def capped_pools(city_toml: Path):
    """Every pool block declaring max 0, with its scope. City- and rig-level."""
    try:
        data = tomllib.loads(city_toml.read_text())
    except (OSError, tomllib.TOMLDecodeError) as exc:
        print(f"I'm sorry, I can't do that -- {city_toml} is unreadable: {exc}",
              file=sys.stderr)
        raise SystemExit(CANNOT_VERIFY)

    out = []

    def walk(node):
        if isinstance(node, dict):
            name = node.get("name")
            mx = node.get("max_active_sessions", node.get("max"))
            if isinstance(name, str) and mx == 0:
                out.append((name, node.get("dir") or "(city)"))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return sorted(set(out))


def order_roots(city_root: Path, extra, data=None):
    """City's own orders, plus the orders dir of every DECLARED import.

    Roots come from `city.toml`'s import `source` paths, not from a glob over
    the home directory. An earlier version globbed `~/repos/*/orders` and
    swallowed unrelated checkouts into the sweep -- which both inflated real
    runs and made fixtures meaningless. If the city does not declare it, this
    check does not read it.
    """
    roots = [city_root / "orders"]

    sources = []

    def walk(node):
        if isinstance(node, dict):
            src = node.get("source")
            if isinstance(src, str) and src:
                sources.append(src)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    if data:
        walk(data)

    for src in sources:
        sp = Path(src).expanduser()
        if not sp.is_absolute():
            sp = (city_root / sp).resolve()
        roots.append(sp / "orders")

    # gc materializes remote imports here; these ARE declared, just cached.
    roots += sorted((Path.home() / ".gc" / "cache" / "repos").glob("*/orders"))
    roots += sorted(city_root.glob("*/orders"))
    roots += [Path(e).expanduser() for e in extra]

    seen, uniq = set(), []
    for r in roots:
        k = str(r)
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq


def order_targets(roots):
    """(pool, order-file) for every ENABLED order that names a pool."""
    hits, nfiles = [], 0
    for root in roots:
        if not root.is_dir():
            continue
        for f in sorted(root.glob("*.toml")):
            nfiles += 1
            try:
                o = (tomllib.loads(f.read_text()) or {}).get("order", {}) or {}
            except (OSError, tomllib.TOMLDecodeError):
                continue
            if o.get("enabled") is False:
                continue
            pool = o.get("pool")
            if isinstance(pool, str) and pool:
                hits.append((pool, f.name))
    return hits, nfiles


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    extra = [argv[i + 1] for i, a in enumerate(argv) if a == "--root" and i + 1 < len(argv)]
    city_root = Path(args[0]).expanduser() if args else Path.home() / "HQ"

    if not (city_root / "city.toml").is_file():
        print(f"I'm sorry, I can't do that -- no city.toml at {city_root}.",
              file=sys.stderr)
        print("Pass the city root as the first argument.", file=sys.stderr)
        return CANNOT_VERIFY

    capped = capped_pools(city_root / "city.toml")
    try:
        city_data = tomllib.loads((city_root / "city.toml").read_text())
    except Exception:
        city_data = {}
    roots = order_roots(city_root, extra, city_data)
    targets, nfiles = order_targets(roots)

    if nfiles == 0:
        print("SILENT_ACCUMULATORS: CANNOT VERIFY -- no order files found.",
              file=sys.stderr)
        print("\nRoots searched:", file=sys.stderr)
        for r in roots:
            print(f"    {r}", file=sys.stderr)
        print("\nThis is NOT a pass. A sweep that read nothing cannot clear "
              "anything.\nPass the correct city root, or add --root DIR.",
              file=sys.stderr)
        return CANNOT_VERIFY

    print(f"SILENT_ACCUMULATORS: swept {nfiles} order file(s) "
          f"across {sum(1 for r in roots if r.is_dir())} root(s); "
          f"{len(capped)} pool block(s) capped at 0.")

    if not capped:
        print("SILENT_ACCUMULATORS: OK -- no pool is capped at 0, so nothing "
              "can strand this way.")
        return OK

    bad = [(p, scope, sorted({f for pl, f in targets if pl == p}))
           for p, scope in capped
           if any(pl == p for pl, _ in targets)]

    if not bad:
        print("SILENT_ACCUMULATORS: OK -- capped pools exist, but no enabled "
              "order targets them.")
        return OK

    print("\nSILENT_ACCUMULATORS: FOUND -- enabled orders are aimed at pools "
          "capped at 0.", file=sys.stderr)
    print("\nWork poured here is never claimed, never fails, and never reports.",
          file=sys.stderr)
    print("It accumulates as open workflow roots until someone audits by hand.\n",
          file=sys.stderr)
    for pool, scope, files in bad:
        print(f"    pool {pool}  [scope: {scope}]  max=0", file=sys.stderr)
        for f in files:
            print(f"        <- {f}", file=sys.stderr)
    print("\nEither the cap is wrong or the order is. Do NOT resolve this by "
          "lifting\nthe cap reflexively -- see docs/policy/post-incident-cleanup.md "
          "Rule 3:\na live operator claiming stranded work turns it into WRONG work.",
          file=sys.stderr)
    return FOUND


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
