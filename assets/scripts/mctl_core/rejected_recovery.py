"""Find human verdicts sitting in `.pile/.rejected/` (mc-8ehd0).

READ-ONLY. This module reports; it moves nothing. Recovery is a human decision
per brief, because a verdict recorded against a brief that has since changed
may no longer apply, and re-promoting it silently would assert a judgement
nobody made about the current text -- the same manufactured-adjudication
failure `MBRF021` produced and this repo is still cleaning up after.

Measured 2026-08-28 against the live city: 24 rejected slug directories, 8 of
them carrying a verdict (7 `approve`, 1 `reject`). The other 16 are the gate
working correctly and this module deliberately does not report them.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .fields import read_frontmatter
from .verdicts import is_adjudicated


class RecoveryReadError(RuntimeError):
    """One or more rejected briefs could not be read. Never silent (P6.1)."""


def scan(rejected_root: Path) -> tuple[Mapping[str, Any], ...]:
    """Every rejected brief that carries a verdict.

    An absent root is an empty result rather than an error: a city that has
    never rejected anything has nothing to recover. An UNREADABLE brief under
    a root that does exist is the opposite case and raises -- that file may BE
    a lost human verdict, and skipping it silently is how a recovery pass
    under-reports and still looks complete.
    """
    if not rejected_root.is_dir():
        return ()
    found: list[Mapping[str, Any]] = []
    unreadable: list[Mapping[str, Any]] = []
    for path in sorted(rejected_root.rglob("*.md")):
        try:
            front = read_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        except OSError as error:
            unreadable.append({"path": str(path), "error": str(error)})
            continue
        if not is_adjudicated(front):
            continue
        found.append(
            {
                "slug": str(front.get("slug") or path.parent.name),
                "path": str(path),
                "verdict": str(front.get("verdict") or "").strip(),
                "adjudicated_by": str(front.get("adjudicated_by") or "").strip(),
            }
        )
    if unreadable:
        # Raised AFTER the full walk, not on first failure: a caller that must
        # be told the list is incomplete is also better served knowing how many
        # files are affected than only which one failed first.
        raise RecoveryReadError(unreadable)
    return tuple(found)
