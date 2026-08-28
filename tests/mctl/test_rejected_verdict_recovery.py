"""Report the human verdicts already stranded in `.pile/.rejected/` (mc-8ehd0).

The guard in `brief-shuffle-fast-drain.py` stops new losses. It does not return
what is already lost: measured 2026-08-28, 8 of 24 rejected briefs carry a
verdict (7 approve + 1 reject). This module finds them.

READ-ONLY by design, and the control below is why: a rejected brief with NO
verdict is the gate working correctly (16 of the 24), and a recovery pass that
swept those up too would undo the gate rather than repair it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import rejected_recovery  # noqa: E402


def _write(root: Path, slug: str, body: str) -> None:
    d = root / slug
    d.mkdir(parents=True)
    (d / "brief.md").write_text(body, encoding="utf-8")


def test_finds_a_rejected_brief_that_carries_a_verdict(tmp_path: Path) -> None:
    _write(tmp_path, "lost", "---\nslug: lost\nverdict: approve\nadjudicated_by: Taylor\n---\n")
    found = rejected_recovery.scan(tmp_path)
    assert [e["slug"] for e in found] == ["lost"]
    assert found[0]["verdict"] == "approve"


def test_ignores_a_rejected_brief_with_no_verdict(tmp_path: Path) -> None:
    """Control: a gate-rejected undecided brief is the gate WORKING."""
    _write(tmp_path, "fine", "---\nslug: fine\nstatus: ready\n---\n")
    assert rejected_recovery.scan(tmp_path) == ()


def test_an_absent_directory_is_empty_not_an_error(tmp_path: Path) -> None:
    assert rejected_recovery.scan(tmp_path / "nope") == ()


def test_a_status_adjudicated_brief_with_no_verdict_key_is_found(tmp_path: Path) -> None:
    """All 8 live losses carry `status: adjudicated`; a reject is a loss too."""
    _write(tmp_path, "refused", "---\nslug: refused\nstatus: adjudicated\nverdict: reject\n---\n")
    found = rejected_recovery.scan(tmp_path)
    assert [e["verdict"] for e in found] == ["reject"]


def test_an_unreadable_brief_is_raised_never_skipped(tmp_path: Path) -> None:
    """P6.1 fail loud. That file may BE a lost verdict.

    Swallowing the error is how a recovery pass under-reports and still looks
    complete -- the caller would believe the list is exhaustive when it is not.
    """
    _write(tmp_path, "ok", "---\nslug: ok\nverdict: approve\n---\n")
    unreadable = tmp_path / "broken"
    unreadable.mkdir()
    (unreadable / "brief.md").mkdir()  # a directory where a file must be
    with pytest.raises(rejected_recovery.RecoveryReadError):
        rejected_recovery.scan(tmp_path)
