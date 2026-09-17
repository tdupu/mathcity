#!/usr/bin/env python3
"""Detect hand-edits to `city.toml` — P1.2 — and unbounded backup growth.

THE FINDING (2026-09-17 QC audit, kolchin). `~/HQ` holds 22 `city.toml.bak-*`
files. Four came from `provider_set`'s typed write path. EIGHTEEN predate it,
dated Sep 6-8, each named for the hand-edit that produced it:

    bak-poolraise   bak-poolraise2   bak-poolcap     bak-poolzero
    bak-agexswitch  bak-providerfix  bak-fixsession  bak-latchlivelock
    bak-srccheckout bak-rigpath      bak-preplin     bak-briefopcap ...

P1.2 says: "Changes to city behavior go through `gc import add` / `[imports.*]`
entries + `gc import install` -- never a one-off hand-edit to `city.toml`."

**Nothing enforces P1.2.** That is why eighteen violations accumulated in plain
sight over three days without anyone stopping. The backup trail is a forensic
record of them, left by agents doing the responsible thing (backing up) while
doing the forbidden thing.

WHY THE TRAIL AND NOT JUST THE MTIME. Two signals answering different
questions:

    mtime    city.toml newer than the last import install -> a write happened
             outside the import path. Answers "is it dirty NOW".
    trail    bak-* count and names -> the HISTORY, including edits since
             overwritten. Answers "how often does this happen".

A detector reading only mtime would have reported ONE violation where there
were eighteen. The trail is what made the pattern visible.

TYPED WRITES ARE NOT VIOLATIONS. `provider_set` writes `bak-provider-*` through
the mctl surface, which is the compliant path P1.2 asks for. Counting those as
hand-edits would defame the fix and inflate the number -- the shape this whole
audit is about.

RETENTION. Even compliant writes accumulate: one backup per apply, nothing
reaps them. Unbounded growth eventually buries the signal the trail carries.
This reports what it WOULD reap and never deletes -- a detector that mutates is
not a detector.

Read-only. Usage:  check_config_handedits.py <city> [--retention N]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

OK, FOUND, CANNOT_VERIFY = 0, 1, 2

#: backups written by the mctl typed surface, not by hand.
TYPED_PREFIXES = ("provider-",)


def classify_backups(city: Path):
    """(typed, hand_edited) backup paths, newest first."""
    baks = sorted(city.glob("city.toml.bak-*"),
                  key=lambda p: p.stat().st_mtime, reverse=True)
    typed, hand = [], []
    for b in baks:
        suffix = b.name[len("city.toml.bak-"):]
        (typed if suffix.startswith(TYPED_PREFIXES) else hand).append(b)
    return typed, hand


def last_import_install(city: Path):
    """Best available marker for when imports were last installed."""
    for name in ("packs.lock", "pack.toml"):
        p = city / name
        if p.is_file():
            return p.stat().st_mtime
    return None


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("city")
    ap.add_argument("--retention", type=int, default=None,
                    help="report backups beyond the newest N (reaps nothing)")
    a = ap.parse_args(argv[1:])

    city = Path(a.city).expanduser()
    cfg = city / "city.toml"
    if not cfg.is_file():
        print(f"CONFIG_HANDEDITS: CANNOT VERIFY -- no city.toml at {city}.\n"
              "This is NOT a pass: absence of a city is not a compliant city.",
              file=sys.stderr)
        return CANNOT_VERIFY

    typed, hand = classify_backups(city)
    install = last_import_install(city)
    dirty_now = install is not None and cfg.stat().st_mtime > install

    print(f"CONFIG_HANDEDITS: {city}")
    print(f"  backups, typed (compliant, mctl write path) : {len(typed)}")
    print(f"  backups, HAND-EDITED (P1.2 violations)      : {len(hand)}")
    if install is not None:
        print(f"  city.toml newer than last import install    : "
              f"{'YES' if dirty_now else 'no'}")

    if a.retention is not None:
        excess = (typed + hand)[a.retention:]
        print(f"  would reap beyond newest {a.retention}               : "
              f"{len(excess)} (reaps nothing; read-only)")

    if not hand and not dirty_now:
        print("CONFIG_HANDEDITS: OK -- no hand-edit trail, no uncommitted drift.")
        return OK

    if hand:
        print(f"\nHAND-EDIT TRAIL -- {len(hand)} P1.2 violation(s) recorded on disk:",
              file=sys.stderr)
        for b in hand[:20]:
            print(f"    {b.name}", file=sys.stderr)
        print("\nP1.2: city.toml changes come from pack updates, not hand-edits.\n"
              "Each of these is a write that bypassed `gc import install`.",
              file=sys.stderr)
    if dirty_now:
        print("\ncity.toml is NEWER than the last import install -- a write "
              "happened outside the import path.", file=sys.stderr)
    return FOUND


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
