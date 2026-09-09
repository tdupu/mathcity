"""A `bd link` TIMEOUT is UNKNOWN, not "nothing was written" (#252, P6.3).

`_apply_bd_create_with_sources` is deliberately recoverable (#192): it creates
the bead already marked `commission_incomplete=true`, links each source, and
only then clears the marker -- "the commit that ends the transaction". A retry
adopts the partial and relinks only what is missing.

The gap was in REPORTING, not recovery. `_run_bd_command` collapsed
`subprocess.TimeoutExpired` and `OSError` into one `BeadWriteError`, so a client
-side deadline that elapsed while `bd link` was SUCCEEDING was reported to the
caller as a failure -- "nothing was written" -- while a complete bead sat in the
store marked incomplete.

That is the #181 lesson one module over: a timeout means WE STOPPED WAITING, not
that the work failed. The caller must be told the bead id so the partial is
findable, and told that a retry adopts it.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import beads as beads_mod  # noqa: E402
from mctl_core.beads import BeadWriteError  # noqa: E402


def test_a_timeout_raises_a_distinguishable_error(tmp_path):
    """A timeout must not be indistinguishable from a hard failure."""
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="bd link", timeout=30)

    original = beads_mod.subprocess.run
    beads_mod.subprocess.run = boom
    try:
        with pytest.raises(BeadWriteError) as caught:
            beads_mod._run_bd_command(tmp_path, ["bd", "link", "a", "b"], 30, "Could not link")
    finally:
        beads_mod.subprocess.run = original

    assert isinstance(caught.value, beads_mod.BeadWriteTimeout), (
        "a timeout raises the same type as a hard failure, so no caller can "
        "distinguish 'we stopped waiting' from 'it failed'"
    )


def test_a_hard_failure_is_NOT_a_timeout(tmp_path):
    """Positive control: OSError must stay an ordinary BeadWriteError, or the
    distinction above is vacuous."""
    def boom(*a, **k):
        raise OSError("bd not found")

    original = beads_mod.subprocess.run
    beads_mod.subprocess.run = boom
    try:
        with pytest.raises(BeadWriteError) as caught:
            beads_mod._run_bd_command(tmp_path, ["bd", "link", "a", "b"], 30, "Could not link")
    finally:
        beads_mod.subprocess.run = original

    assert not isinstance(caught.value, beads_mod.BeadWriteTimeout)


def test_the_timeout_message_names_the_bead_and_the_recovery():
    """The caller must be able to FIND the partial, and know a retry adopts it."""
    err = beads_mod.BeadWriteTimeout(
        "Could not link bead mc-abc to source mc-src: timed out"
    )
    text = str(err)
    assert "mc-abc" in text
