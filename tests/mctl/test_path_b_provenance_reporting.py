"""Absent provenance has two causes; they must not read the same (#178).

Path-B dispatch (a raw `gc sling`, e.g. from a formula) writes its run and its
provenance non-atomically, so a run can exist whose provenance never landed.
`work_provenance` reported that identically to a source that was never
dispatched at all -- "an absent record and an absent event are indistinguishable
to every reader".

They ARE distinguishable, because an open child workflow is observable
independently of any provenance record. That is already why a path-B run cannot
be re-dispatched (`_source_dispatchable` checks the two signals separately,
widened for #228). This turns the same observation into a positive statement.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import work as work_mod  # noqa: E402


def test_the_two_causes_have_different_codes():
    """The whole point: one code for each cause, not one for both."""
    src = (REPO_ROOT / "assets" / "scripts" / "mctl_core" / "work.py").read_text()
    assert "MWRK_PROVENANCE_ABSENT_RUN_EXISTS" in src
    # and it is reached only when a run was found
    idx = src.index("MWRK_PROVENANCE_ABSENT_RUN_EXISTS")
    guard = src[max(0, idx - 900):idx]
    assert "_open_child_workflow" in guard, (
        "the path-B code must be guarded by an observed run; unguarded it would "
        "relabel every never-dispatched source as a path-B run"
    )


def test_the_never_dispatched_path_is_preserved():
    """Positive control: the original error must still be raised when NO run
    exists, or the new code has simply replaced one conflation with another."""
    src = (REPO_ROOT / "assets" / "scripts" / "mctl_core" / "work.py").read_text()
    idx = src.index("MWRK_PROVENANCE_ABSENT_RUN_EXISTS")
    after = src[idx:idx + 1400]
    assert "raise WorkError(error.diagnostic) from error" in after, (
        "the no-run branch must still raise the original provenance error"
    )


def test_the_message_names_the_run():
    """A report that says 'dispatched outside mctl' without naming the run is
    unactionable -- the reader cannot go look at it."""
    src = (REPO_ROOT / "assets" / "scripts" / "mctl_core" / "work.py").read_text()
    idx = src.index("MWRK_PROVENANCE_ABSENT_RUN_EXISTS")
    block = src[idx:idx + 700]
    assert "run.id" in block
