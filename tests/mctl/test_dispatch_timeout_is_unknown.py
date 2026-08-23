"""#184 — a timed-out dispatch reports UNKNOWN, not "no dispatch was recorded".

`work.py` caught `OSError` and `subprocess.TimeoutExpired` in one handler and
emitted one message: *"The dispatch command could not be run, so no dispatch was
recorded."*

Those are opposite worlds. `OSError` means the command never started, and the
message is true. `TimeoutExpired` is raised only after the child has run for the
full timeout — it demonstrably started, and whether it finished its work before
being killed is unknowable from here.

It is not hypothetical. Trace `515ba38a` timed out and the city event log shows
`execution.work_associated` 1 ms in and four beads created 35 s in. The dispatch
was recorded; the tool said it was not. A caller who believes `applied: false`
retries, and the retry double-dispatches.

These tests assert the DISTINCTION via a distinct diagnostic code, not via
message prose — prose can be reworded without anyone noticing the semantics
moved.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.work import (  # noqa: E402
    DISPATCH_TIMEOUT_CODE,
    DISPATCH_UNRUNNABLE_CODE,
    classify_dispatch_subprocess_error,
)


def test_a_command_that_never_started_is_a_hard_failure():
    """`OSError` — the process could not be spawned. Nothing ran, nothing landed."""
    verdict = classify_dispatch_subprocess_error(OSError("No such file or directory"))
    assert verdict.code == DISPATCH_UNRUNNABLE_CODE
    assert verdict.applied is False


def test_a_timed_out_command_reports_unknown_not_false():
    """The load-bearing case.

    `TimeoutExpired` means the command RAN. Whether its dispatch landed is
    unknown, and `applied: False` would be a claim about the world derived from
    how long we were willing to wait.
    """
    verdict = classify_dispatch_subprocess_error(
        subprocess.TimeoutExpired(cmd=["gc", "sling"], timeout=120)
    )
    assert verdict.code == DISPATCH_TIMEOUT_CODE
    assert verdict.applied is None, "a timeout cannot know whether the dispatch landed"


def test_the_two_failures_do_not_share_a_code():
    """If one code covers both, the caller cannot tell them apart."""
    assert DISPATCH_TIMEOUT_CODE != DISPATCH_UNRUNNABLE_CODE


def test_the_timeout_verdict_tells_the_caller_not_to_blindly_retry():
    """A retry after a timeout may double-dispatch, so the guidance must say so."""
    verdict = classify_dispatch_subprocess_error(
        subprocess.TimeoutExpired(cmd=["gc", "sling"], timeout=120)
    )
    assert verdict.may_have_dispatched is True
    assert "retry" in (verdict.suggested_next_command or "").lower() or \
           "check" in (verdict.suggested_next_command or "").lower()


def test_an_unrunnable_command_is_safe_to_retry():
    """The whole point of separating them: one is safe to retry, one is not."""
    verdict = classify_dispatch_subprocess_error(OSError("boom"))
    assert verdict.may_have_dispatched is False
