#!/usr/bin/env python3
"""#201 rule 2: run a registry's guard before the SHA that touched it is offered.

git's conflict detection is blind to ordering and uniqueness. Two branches can
each insert into the same registry, merge textually clean, and produce a
duplicate or an out-of-order entry. Measured on #182:

    558f686   merged clean WITHOUT the registry test  -> 4 tests red, merge aborted
    1cf074d   ran the registry test first             -> clean merge

The registries and their guards live in `assets/mctl/ordered-registries.toml`,
hand-maintained because grepping the test tree names twenty incidental
references and not the one guard (`gates.toml` is mentioned by 18 test files).

Exit codes (P6.2):
    0  no registry touched, or every touched registry's guard passed
    1  a guard FAILED -- do not offer this SHA
    2  could not determine: git failed, the register is unreadable, or a
       registry was touched that this register does not name

2 is deliberately NOT 0. An unregistered registry in the diff is exactly the
case where a human has added a new ordered file and not yet declared its guard,
which is when this check is most needed and least able to answer. Reporting
"clean" there would forgive the merge this exists to catch.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tomllib
from pathlib import Path

REGISTER_RELPATH = Path("assets/mctl/ordered-registries.toml")


def repo_root(start: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip())


def load_register(path: Path) -> list[dict] | None:
    try:
        with path.open("rb") as handle:
            return list(tomllib.load(handle).get("registry", []))
    except Exception:
        return None


def changed_paths(root: Path, ref: str | None, staged: bool) -> list[str] | None:
    """Repo-relative paths in the diff.

    Default compares against the merge base with `origin/main`, because rule 2
    is about what a BRANCH touches, not what one commit touched: six rebases
    can leave a registry edit several commits back while `HEAD~1` shows none.
    """
    if staged:
        cmd = ["git", "diff", "--cached", "--name-only"]
    elif ref:
        cmd = ["git", "diff", "--name-only", f"{ref}...HEAD"]
    else:
        base = subprocess.run(
            ["git", "merge-base", "HEAD", "origin/main"],
            cwd=root, capture_output=True, text=True,
        )
        if base.returncode != 0:
            return None
        cmd = ["git", "diff", "--name-only", f"{base.stdout.strip()}..HEAD"]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if proc.returncode != 0:
        return None
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def run_guard(root: Path, guard: str) -> tuple[int, str]:
    target = root / guard
    if not target.exists():
        return 2, f"guard not found: {guard}"
    if guard.endswith(".sh"):
        if not os.access(target, os.X_OK):
            cmd = ["sh", str(target)]
        else:
            cmd = [str(target)]
    else:
        cmd = [sys.executable, "-m", "pytest", guard, "-q"]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    tail = (proc.stdout + proc.stderr).strip().splitlines()
    return proc.returncode, (tail[-1] if tail else "")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", default=".", help="repo to inspect (default: cwd)")
    ap.add_argument("--ref", default=None,
                    help="compare against this ref instead of the origin/main merge base")
    ap.add_argument("--staged", action="store_true",
                    help="use the staged diff -- the pre-commit case")
    ap.add_argument("--list", action="store_true",
                    help="print the register and exit 0 without running anything")
    args = ap.parse_args()

    root = repo_root(Path(args.repo).expanduser().resolve())
    if root is None:
        print("REGISTRY_GATE: UNDETERMINED -- not a git repository", file=sys.stderr)
        return 2
    # Say which repo this read (#273): a gate that names no root is
    # unfalsifiable by the reader, and this one is run from several checkouts.
    print(f"REGISTRY_GATE: reading {root}", file=sys.stderr)

    register = load_register(root / REGISTER_RELPATH)
    if register is None:
        print(f"REGISTRY_GATE: UNDETERMINED -- cannot read {REGISTER_RELPATH}",
              file=sys.stderr)
        return 2
    by_path = {str(entry.get("path", "")): entry for entry in register if entry.get("path")}
    print(f"REGISTRY_GATE: {len(by_path)} registries declared", file=sys.stderr)

    if args.list:
        for path, entry in sorted(by_path.items()):
            guards = ", ".join(entry.get("guards", [])) or "NO GUARD DECLARED"
            print(f"  {path}\n      semantics: {entry.get('semantics','?')}\n      guards: {guards}")
        return 0

    changed = changed_paths(root, args.ref, args.staged)
    if changed is None:
        print("REGISTRY_GATE: UNDETERMINED -- git diff failed (no origin/main?)",
              file=sys.stderr)
        return 2

    touched = [p for p in changed if p in by_path]
    # A registry-shaped file that the register does not name. Not clean: see
    # the module docstring on why this is 2 rather than 0.
    unknown = [
        p for p in changed
        if p not in by_path
        and p.endswith(".toml")
        and ("assets/mctl/" in p or "assets/brief-pipeline/" in p)
    ]

    if not touched and not unknown:
        print(f"REGISTRY_GATE: OK -- no declared registry in {len(changed)} changed file(s).")
        return 0

    failures: list[str] = []
    undetermined: list[str] = []
    for path in touched:
        entry = by_path[path]
        guards = entry.get("guards") or []
        if not guards:
            undetermined.append(f"{path} -- declared with NO guard")
            continue
        for guard in guards:
            code, tail = run_guard(root, guard)
            label = f"{path} -> {guard}"
            if code == 0:
                print(f"REGISTRY_GATE: PASS  {label}", file=sys.stderr)
            elif code == 2 and tail.startswith("guard not found"):
                undetermined.append(f"{label} -- {tail}")
            else:
                failures.append(f"{label} -- exit {code}: {tail}")

    for path in unknown:
        undetermined.append(
            f"{path} -- an assets registry this register does not name; "
            "declare it in ordered-registries.toml (or record there why it is out of scope)"
        )

    if failures:
        print("REGISTRY_GATE: FAILED -- do not offer this SHA:")
        for item in failures:
            print(f"    {item}")
        return 1
    if undetermined:
        print("REGISTRY_GATE: UNDETERMINED -- cannot clear this SHA:")
        for item in undetermined:
            print(f"    {item}")
        return 2
    print(f"REGISTRY_GATE: OK -- {len(touched)} registry/registries guarded and green.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
