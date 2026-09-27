#!/usr/bin/env python3
"""P1.11: the bead-data remote must reach a verified-private `<repo>-dolt` target.

WHY THIS EXISTS -- the observed failure, not a hypothetical one

Every mathcity clone configured its dolt remote as:

    git+ssh://git@github.com/./tdupu/mathcity-dolt.git
                             ^^^

GitHub rejects it outright -- `./tdupu/mathcity-dolt is not a valid repository
name` -- so bead data had NO reachable target, on either machine. The cost was
not a loud failure. It was read as "the kolchin ma replica is a flattened,
diverged replica that cannot sync", written into `city.toml` as the
justification for capping five agent pools at zero, which is why the city could
not do any routed work at all (tdupu/mathcity#274).

Two beads upstream let it through and both are worth naming, because they are
why a human reading the URL did not catch it either:

  `beads/internal/doltremote/remote.go:57-60` converts SCP-style
  `git@host:path` to `git+ssh://git@host/path` by string concatenation, so a
  `./`-prefixed path is carried through verbatim.

  `beads/internal/remotecache/url.go:150` validates the `git+ssh` scheme by
  checking only that the HOST is non-empty. `github.com` is non-empty, so the
  URL validates, is stored, and fails at the transport -- where the error names
  the repository, not the config.

INVARIANT (P1.17): a remote that does not resolve, is not private, or is not a
`<repo>-dolt` target now fails a check instead of being read as a property of
the replica. The failure mode this closes is not "a bad URL" -- it is "a bad URL
misdiagnosed as a broken database".

Exit codes (P6.2): 0 clean, 1 violation, 2 could not determine.

2 is not 0. An unreachable network, a missing `gh`, or an unparseable config
means the check did not run -- and "I could not look" is not "the remote is
fine". That distinction is the whole reason this defect survived: every symptom
read as a clean answer about something else.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

#: Schemes bd accepts for a git-backed dolt remote (`doltremote.NativeSchemes`).
GIT_BACKED = ("git+ssh://", "git+https://", "git+http://", "git+file://")

#: A path segment that is legal in a URL and not a repository name. `/./` is the
#: measured case; `/../` is the same class and would resolve somewhere else
#: entirely, which is worse than failing.
NON_CANONICAL = ("/./", "/../", "//")


def _run(cmd: list[str], timeout: int) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{' '.join(cmd)}: timed out after {timeout}s"
    return proc.returncode, proc.stdout, proc.stderr


def configured_remote(rig_root: Path, timeout: int) -> tuple[str | None, str]:
    """The remote bd will actually use, read from bd rather than from a file.

    Deliberately NOT parsed out of `.beads/config.yaml`. The two disagree: on
    this laptop `config.yaml` was corrected and `bd dolt remote list` kept
    reporting the old value, because the remote is registered INSIDE the Dolt
    database. A check that read the file would have called the fix a success
    while bd still used the broken URL.
    """
    code, out, err = _run(["bd", "dolt", "remote", "list"], timeout)
    if code != 0 and not out.strip():
        return None, f"`bd dolt remote list` failed: {(err or out).strip()[:200]}"
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "origin":
            return parts[1], ""
    return None, "no remote named `origin` is registered"


def check_shape(url: str) -> list[str]:
    findings: list[str] = []
    if not url.startswith(GIT_BACKED):
        findings.append(
            f"scheme is not a git-backed dolt remote (expected one of {', '.join(GIT_BACKED)})"
        )
    for bad in NON_CANONICAL:
        # Skip the scheme's own `//`.
        tail = url.split("://", 1)[-1]
        if bad in tail:
            findings.append(
                f"path contains {bad!r}, which is not part of a repository name; "
                "GitHub rejects it as an invalid repository name"
            )
            break
    if not re.search(r"/[^/]+-dolt(\.git)?/?$", url):
        findings.append(
            "target does not end in `<repo>-dolt` -- P1.11 allows bead data only "
            "on a dedicated dolt repository, never the code repo"
        )
    return findings


def owner_repo(url: str) -> str | None:
    tail = url.split("://", 1)[-1]
    tail = tail.split("@", 1)[-1]
    parts = [p for p in tail.split("/") if p not in ("", ".", "..")]
    if len(parts) < 3:
        return None
    repo = parts[-1]
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]
    return f"{parts[-2]}/{repo}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rig-root", default=".", help="rig whose bd config to read")
    ap.add_argument("--timeout", type=int, default=60, help="seconds per probe; 0 = no deadline")
    ap.add_argument("--skip-network", action="store_true",
                    help="shape checks only; reachability and privacy are reported as UNDETERMINED")
    args = ap.parse_args()
    timeout = args.timeout or None

    root = Path(args.rig_root).expanduser().resolve()
    # Say which rig this read (#273): this check runs from several checkouts and
    # the two stores disagree, so a finding that names no root is unfalsifiable.
    print(f"DOLT_REMOTE: reading {root}", file=sys.stderr)

    url, why = configured_remote(root, timeout or 60)
    if url is None:
        print(f"DOLT_REMOTE: UNDETERMINED -- {why}")
        return 2
    print(f"DOLT_REMOTE: origin = {url}", file=sys.stderr)

    findings = check_shape(url)

    target = owner_repo(url)
    if target is None:
        findings.append(f"cannot parse an owner/repo out of {url!r}")

    undetermined: list[str] = []
    if args.skip_network:
        undetermined.append("--skip-network: reachability and privacy not probed")
    elif not findings:
        # Only probe when the shape is sane; a malformed URL's network failure
        # would report the same thing twice and bury the actionable finding.
        code, _out, err = _run(["git", "ls-remote", url.replace("git+", "", 1)], timeout or 60)
        if code == 127 or code == 124:
            undetermined.append(err.strip()[:200])
        elif code != 0:
            findings.append(f"remote does not resolve: {err.strip().splitlines()[-1][:160]}")

        if target:
            code, out, err = _run(
                ["gh", "repo", "view", target, "--json", "isPrivate"], timeout or 60
            )
            if code != 0:
                undetermined.append(f"cannot read visibility of {target}: {(err or out).strip()[:160]}")
            else:
                try:
                    if json.loads(out).get("isPrivate") is not True:
                        findings.append(
                            f"{target} is NOT private -- P1.11 requires a verified-private "
                            "target, and bead data on a public repo is the case CLAUDE.md "
                            "forbids outright"
                        )
                except json.JSONDecodeError as exc:
                    undetermined.append(f"unparseable gh output for {target}: {exc}")

    if findings:
        print("DOLT_REMOTE: FAILED -- bead data has no valid target (P1.11):")
        for item in findings:
            print(f"    {item}")
        print(f"    configured: {url}")
        return 1
    if undetermined:
        print("DOLT_REMOTE: UNDETERMINED -- shape is valid, but the target was not verified:")
        for item in undetermined:
            print(f"    {item}")
        return 2
    print(f"DOLT_REMOTE: OK -- origin resolves and {target} is private.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
