#!/usr/bin/env python3
"""Repair a malformed bead-data remote, in place, after verifying the target (P1.11).

WHY A SCRIPT RATHER THAN AN INSTRUCTION

Every bead store in the fleet configures its dolt remote with a `/./` segment
GitHub rejects as an invalid repository name, so no store can push. The fix is
mechanical, but it is NOT one edit: the remote lives in two places that disagree.

    bd dolt remote list   reads .beads/config.yaml   (and is what a human greps)
    bd dolt show          queries the running Dolt server's registered remotes

Correcting `config.yaml` alone left `bd` still using the old URL on this laptop,
because the remote was registered in the Dolt database. Correcting only the
database leaves the file wrong for the next reader. A repair that fixes one and
reports success is the failure mode this script exists to remove — which is why
`dolt-remote-check.py` reads from `bd` rather than the file.

It also cannot be shipped as config. `.gitignore` excludes `.beads/*` (correctly:
P1.10 keeps machine-specific values out of pack content), so a corrected
`config.yaml` cannot propagate through the code repo. A script in the pack CAN,
via the pin — so a machine this agent cannot write to needs one command rather
than a hand-edit performed from a description.

SAFETY

Dry run by default, like every mctl mutation. The target is verified BEFORE
anything is written: it must resolve, and it must be PRIVATE, because P1.11
allows bead data only on a verified-private `<repo>-dolt` target and the code
repo beside it is public. A repair that pointed bead data at a public repo would
be worse than the breakage it fixes.

Exit codes (P6.2): 0 nothing to do or repaired, 1 refused (unsafe or unverifiable
target), 2 could not determine.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

#: A `/.` or `/..` segment is DROPPED (leaving the following slash); a run of
#: slashes is COLLAPSED to one. Two rules, not one: substituting `//` with the
#: empty string deletes both slashes and joins the path segments --
#: `tdupu//mathcity-dolt` became `tdupumathcity-dolt`, which is a different
#: repository name and would have been written as the repair. Caught by
#: `test_normalize_strips_non_canonical_segments`.
_DOT_SEGMENT = re.compile(r"/\.{1,2}(?=/)")
_SLASH_RUN = re.compile(r"//+")


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 60):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, 127, "", f"{cmd[0]}: not found")
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, 124, "", "timed out")


def configured(root: Path) -> tuple[str | None, str]:
    proc = run(["bd", "dolt", "remote", "list"], cwd=root)
    if proc.returncode != 0 and not proc.stdout.strip():
        return None, (proc.stderr or proc.stdout).strip()[:200]
    for line in proc.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "origin":
            return parts[1], ""
    return None, "no remote named `origin`"


def _clean_path(tail: str) -> str:
    return _SLASH_RUN.sub("/", _DOT_SEGMENT.sub("", tail))


def normalize(url: str) -> str:
    """Drop non-canonical path segments, leaving the scheme's own `//` alone.

    The scheme is split off FIRST so `://` is never a candidate for slash
    collapsing -- otherwise the repair would rewrite the transport.
    """
    head, sep, tail = url.partition("://")
    if not sep:
        return _clean_path(url)
    return f"{head}://{_clean_path(tail)}"


def owner_repo(url: str) -> str | None:
    tail = url.split("://", 1)[-1].split("@", 1)[-1]
    parts = [p for p in tail.split("/") if p not in ("", ".", "..")]
    if len(parts) < 3:
        return None
    repo = parts[-1][: -len(".git")] if parts[-1].endswith(".git") else parts[-1]
    return f"{parts[-2]}/{repo}"


def verify_target(url: str, target: str) -> list[str]:
    """Refusals. Checked BEFORE any write -- an unverified target is not repaired to."""
    refusals: list[str] = []
    if not re.search(r"-dolt(\.git)?$", url.rstrip("/")):
        refusals.append(
            f"{target} is not a `<repo>-dolt` target; P1.11 allows bead data only on a "
            "dedicated dolt repository, never the code repo"
        )
    proc = run(["git", "ls-remote", url.replace("git+", "", 1)])
    if proc.returncode in (124, 127):
        refusals.append(f"cannot reach the target: {proc.stderr.strip()[:120]}")
    elif proc.returncode != 0:
        refusals.append(
            "corrected URL still does not resolve: "
            f"{(proc.stderr.strip().splitlines() or ['?'])[-1][:140]}"
        )
    proc = run(["gh", "repo", "view", target, "--json", "isPrivate"])
    if proc.returncode != 0:
        refusals.append(f"cannot read visibility of {target}: {(proc.stderr or proc.stdout).strip()[:120]}")
    else:
        try:
            if json.loads(proc.stdout).get("isPrivate") is not True:
                refusals.append(
                    f"{target} is NOT private -- refusing to point bead data at it (P1.11)"
                )
        except json.JSONDecodeError as exc:
            refusals.append(f"unparseable gh output: {exc}")
    return refusals


def patch_config(root: Path, bad: str, good: str, apply: bool) -> str:
    cfg = root / ".beads" / "config.yaml"
    if not cfg.is_file():
        return f"no {cfg} (nothing to patch; the DB registration may still need it)"
    text = cfg.read_text(encoding="utf-8")
    if bad not in text:
        return f"{cfg}: already correct or names a different remote"
    if apply:
        cfg.write_text(text.replace(bad, good), encoding="utf-8")
        return f"{cfg}: rewrote {text.count(bad)} occurrence(s)"
    return f"{cfg}: WOULD rewrite {text.count(bad)} occurrence(s)"


def reregister(root: Path, good: str, apply: bool) -> str:
    """Re-point the remote registered in the Dolt DB.

    Two commands, because `bd dolt remote` has add/remove and no set-url. A
    `remove` of an absent remote is harmless, so this is safe on a store whose DB
    has none registered -- which is kolchin's measured state.
    """
    if not apply:
        return f"bd dolt remote: WOULD remove origin and add {good}"
    run(["bd", "dolt", "remote", "remove", "origin"], cwd=root)
    proc = run(["bd", "dolt", "remote", "add", "origin", good], cwd=root)
    if proc.returncode != 0:
        return f"bd dolt remote add FAILED: {(proc.stderr or proc.stdout).strip()[:200]}"
    return f"bd dolt remote: origin -> {good}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rig-root", default=".", help="store to repair (default: cwd)")
    ap.add_argument("--apply", action="store_true", help="write; omit for a dry run")
    args = ap.parse_args()

    root = Path(args.rig_root).expanduser().resolve()
    # Say which store this touched (#273): the fleet has several and they disagree.
    print(f"DOLT_REPAIR: {'APPLY' if args.apply else 'DRY RUN'} on {root}", file=sys.stderr)

    url, why = configured(root)
    if url is None:
        print(f"DOLT_REPAIR: UNDETERMINED -- {why}")
        return 2
    good = normalize(url)
    print(f"DOLT_REPAIR: configured  {url}", file=sys.stderr)
    if good == url:
        print("DOLT_REPAIR: OK -- the configured remote has no non-canonical segment.")
        return 0
    print(f"DOLT_REPAIR: corrected   {good}", file=sys.stderr)

    target = owner_repo(good)
    if target is None:
        print(f"DOLT_REPAIR: UNDETERMINED -- cannot parse owner/repo from {good!r}")
        return 2

    refusals = verify_target(good, target)
    if refusals:
        print("DOLT_REPAIR: REFUSED -- target not verified, nothing written:")
        for item in refusals:
            print(f"    {item}")
        return 1
    print(f"DOLT_REPAIR: verified    {target} resolves and is private", file=sys.stderr)

    print(f"    {patch_config(root, url, good, args.apply)}")
    print(f"    {reregister(root, good, args.apply)}")
    if not args.apply:
        print("DOLT_REPAIR: dry run -- re-run with --apply to write.")
        return 0
    after, _ = configured(root)
    if after != good:
        print(f"DOLT_REPAIR: FAILED -- after repair bd still reports {after!r}")
        return 1
    print(f"DOLT_REPAIR: repaired -- bd now reports {after}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
