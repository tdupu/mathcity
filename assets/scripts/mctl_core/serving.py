"""What commit did THIS process import, captured once at startup?

`#210`/`#172`. A running `mctl mcp serve` keeps serving the code it imported at
startup; Python imports `mctl_core` once per process, and a merge to `main` does
not reach an already-running server. `create_github_issue` landed at `b7d7a50`
and was reachable from no running session, and nothing in any response named the
stale revision -- so a caller verifying a fix through the MCP got a confident
false negative (`#172`).

This module removes the silence. It captures, **once, at import**, the commit
the pack was at when this process started, and hands it to `mcp_server` for the
`initialize` and `tools/list` responses. A caller compares it to current
`origin/main` and DECIDES whether to deliberately rebind. It restarts nothing:
saying what you are serving is not a decision with a blast radius; restarting is,
and `#210` rejects hot-reload precisely because a silent contract swap mid-
session is worse than a visible stale one.

The capture MUST be at import, not per request. A stale process must report its
OWN startup commit -- that drift is the whole signal. A fresh `git rev-parse`
per call would instead always return the checkout's current HEAD and mask
exactly the staleness this exists to expose.

`P6.2` governs the read itself, the same rule `mctl_dashboard.staleness` obeys
one layer up: when the commit cannot be read (no git, detached tree, timeout),
`SERVING_COMMIT` is `None` and `serving_info()` reports `known: False`. It never
substitutes a placeholder, which would eventually be compared against
`origin/main` as though it were a real revision -- this module's own defect, one
level up.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess

#: The pack root: `assets/scripts/mctl_core/serving.py` -> up three to the pack.
#: This is the tree whose commit the running code came from.
PACK_ROOT = Path(__file__).resolve().parents[3]

#: Kept short: this runs once, at import, and a hung git must not stall server
#: startup. A checkout that cannot answer in this budget reports `unknown`,
#: which is a true statement, rather than blocking the process from serving.
HEAD_READ_TIMEOUT_SECONDS = 2.0


def read_commit(repo: Path, *, timeout: float = HEAD_READ_TIMEOUT_SECONDS) -> str | None:
    """The short HEAD of `repo`, or `None` if it cannot be read.

    `None` rather than an exception or a placeholder: a caller that cannot tell
    must report `unknown`, and any sentinel string here would eventually be
    displayed, or compared against `origin/main`, as if it were a commit.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


#: Captured ONCE, here, at import. Because `mctl_core` is imported once per
#: process, this freezes at process start and does not move under a caller --
#: it names the code the process is actually running. See the module docstring
#: for why a per-request read would defeat the purpose.
SERVING_COMMIT: str | None = read_commit(PACK_ROOT)

#: Also captured once, at import: an approximate process-start timestamp, so a
#: caller can say not just *which* commit but *how long* it has been serving it
#: (`#172` asks for both). ISO 8601, UTC.
SERVER_STARTED_AT: str = datetime.now(timezone.utc).isoformat()


def serving_info() -> dict[str, object]:
    """The serving-commit block for the `initialize` / `tools/list` envelope.

    Reads the module globals (not a fresh git call), so it reflects the process
    and stays patchable in tests. `known` is the `P6.2` honesty flag: `False`
    means the read failed and `commit` is `None`, never a placeholder.
    """
    return {
        "commit": SERVING_COMMIT,
        "known": SERVING_COMMIT is not None,
        "started_at": SERVER_STARTED_AT,
    }
