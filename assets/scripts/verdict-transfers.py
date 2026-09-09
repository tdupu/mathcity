#!/usr/bin/env python3
"""Does a review verdict still hold across a rebase? (#201 rule 1)

MEASURED COST, from #201: `feat/182-dispatch-verbs` was reviewed and approved
FOUR times across SEVEN SHAs. Hashing the AST of `work.py` with docstrings
stripped:

    1cf074d   3ec63b7f726e
    b6d494a   3ec63b7f726e     IDENTICAL

Not one byte of executable content changed across six rebases. Every one was
`main` moving under a finished branch. The author did six rebases and waited on
four re-verdicts for a branch that was correct at the first.

WHAT THIS ANSWERS, precisely: "is the executable content of these paths
identical between two commits?" It does NOT answer "is this branch still
correct" -- a verdict rests on more than one file's AST, and a rebase can change
behaviour through a dependency this never reads.

So the honest use is NARROW: it can say a re-review is UNNECESSARY, and it can
never say one is unnecessary for reasons beyond the paths it was given. When it
cannot parse a file it says so and refuses, rather than reporting a hash of
nothing -- an unparseable file is exactly when a diff is most likely to matter.

Exit codes (P6.2):
    0  every path's executable content is IDENTICAL -- the verdict transfers
    1  something changed -- re-review, and the changed paths are named
    2  could not compare (unreadable, unparseable, bad ref) -- NOT "identical"
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import subprocess
import sys


def show(ref: str, path: str) -> str | None:
    proc = subprocess.run(["git", "show", f"{ref}:{path}"],
                          capture_output=True, text=True)
    return proc.stdout if proc.returncode == 0 else None


def code_hash(src: str) -> str:
    """AST hash with docstrings stripped.

    Docstrings are stripped because a rebase that only reflows prose is exactly
    the case this tool exists to forgive. Comments never reach the AST at all.
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef, ast.Module)):
            continue
        body = getattr(node, "body", None)
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(getattr(body[0], "value", None), ast.Constant)
                and isinstance(body[0].value.value, str)):
            node.body = body[1:]
    return hashlib.sha256(ast.dump(tree).encode()).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser(
        description="does a verdict transfer across a rebase? (#201 rule 1)")
    ap.add_argument("old_ref")
    ap.add_argument("new_ref")
    ap.add_argument("paths", nargs="+", help="the .py paths the verdict rested on")
    args = ap.parse_args()

    changed, unreadable = [], []
    for path in args.paths:
        old_src, new_src = show(args.old_ref, path), show(args.new_ref, path)
        if old_src is None or new_src is None:
            missing = args.old_ref if old_src is None else args.new_ref
            unreadable.append((path, f"not present at {missing}"))
            continue
        try:
            old_h, new_h = code_hash(old_src), code_hash(new_src)
        except SyntaxError as exc:
            unreadable.append((path, f"unparseable: {exc}"))
            continue
        mark = "IDENTICAL" if old_h == new_h else "CHANGED"
        print(f"  {path:<48} {old_h}  {new_h}  {mark}")
        if old_h != new_h:
            changed.append(path)

    print()
    if unreadable:
        for path, why in unreadable:
            print(f"  CANNOT COMPARE  {path}: {why}", file=sys.stderr)
        print("VERDICT_TRANSFER: UNDECIDABLE -- an unparseable or missing file is "
              "NOT evidence of sameness; it is when a diff is most likely to "
              "matter.", file=sys.stderr)
        return 2

    if changed:
        print(f"VERDICT_TRANSFER: NO -- {len(changed)} path(s) changed "
              f"executable content. Re-review: {', '.join(changed)}")
        return 1

    print(f"VERDICT_TRANSFER: YES -- executable content identical across "
          f"{args.old_ref}..{args.new_ref} for {len(args.paths)} path(s).")
    print("Scope: this says the GIVEN PATHS are unchanged. It cannot speak for "
          "behaviour that moved through a dependency it was not given.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
