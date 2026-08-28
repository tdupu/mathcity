"""#245: `bead_comment` could write to a bead the surface could not read.

The typed surface has had an append-only correction path for individual beads
(`bead_comment`, mc-ilia) for some time, addressed by bead id. It has never had
a way to FETCH that bead. So an agent could add a correction to a record it was
unable to inspect first, which is the wrong way round.

`beads_show` closes that asymmetry. It must return the verdict metadata
verbatim, because the question that exposed this whole gap -- "can you see my
adjudications?" -- is answered by `verdict_reason`, which is where the owner's
actual reasoning lives.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.beads import Bead  # noqa: E402
from mctl_core.bead_reads import beads_show_payload  # noqa: E402


def _store() -> tuple[Bead, ...]:
    return (
        Bead(
            id="mc-tbucy",
            title="How do we clear the B2.10 gate?",
            status="closed",
            issue_type="decision",
            labels=(),
            source_dependencies=("mc-5wdje",),
            created_at="2026-08-27T00:00:00Z",
            updated_at="2026-08-27T20:17:11Z",
            raw={
                "id": "mc-tbucy",
                "metadata": {
                    "verdict": "approve",
                    "verdict_option": "C",
                    "verdict_reason": "C + D, both. C: scope the gate to the writes it protects.",
                    "adjudicated_by": "Taylor Dupuy",
                    "adjudicated_at": "2026-08-27T20:17:09Z",
                },
            },
        ),
    )


def test_show_returns_the_verdict_reasoning_verbatim():
    """`verdict_reason` is the adjudicator's own words and must survive intact."""
    payload = beads_show_payload(_store(), "mc-tbucy")

    bead = payload["bead"]
    assert bead["id"] == "mc-tbucy"
    assert bead["status"] == "closed"
    assert bead["verdict"] == "approve"
    assert bead["adjudicated_by"] == "Taylor Dupuy"
    assert bead["metadata"]["verdict_option"] == "C"
    assert "scope the gate to the writes it protects" in bead["metadata"]["verdict_reason"]


def test_a_missing_bead_is_null_not_an_empty_object():
    """Absent must be distinguishable from present-but-blank.

    Returning `{}` for a bead that does not exist is the same class of error as
    returning rows with no scope: it reads as an answer when it is an absence.
    """
    payload = beads_show_payload(_store(), "mc-nope")

    assert payload["bead"] is None
    assert payload["found"] is False
