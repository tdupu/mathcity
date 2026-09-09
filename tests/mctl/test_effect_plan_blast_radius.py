"""EffectPlan.to_dict() carries the blast-radius classification (#163).

The capability shipped in mctl_core/blast_radius.py with 17 passing tests and
was reachable by NO caller: absent from every typed tool and from
EffectPlan.to_dict(). Tests passing on an unreachable capability is the exact
shape that let it close.

These tests pin REACHABILITY, and deliberately do not assert that anything is
refused. `classify` fails closed, and the registry classifies 3 of the 13
operations EffectPlans carry, so refusing on `gate` today would refuse 10 of 13
mutations including the whole close/hold/release path. Surfacing the
classification is what makes that gap visible; closing it is a separate,
per-operation safety judgment.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.effects import EffectPlan, _classify_operation  # noqa: E402


def _plan(operation: str) -> EffectPlan:
    return EffectPlan(
        trace_id="t",
        operation=operation,
        target_brief_id="b",
        preconditions=(),
        bead_updates=(),
        cache_updates=(),
        event_writes=(),
        trace_writes=(),
    )


def test_to_dict_carries_blast_radius_for_a_classified_operation():
    d = _plan("briefs.create").to_dict()
    assert "blast_radius" in d, "the key #163 reported missing"
    assert d["blast_radius"]["blast_radius"] == "medium"
    assert d["blast_radius"]["gate"] is None
    assert "reversible by closing the bead" in d["blast_radius"]["blast_radius_reason"]


def test_to_dict_surfaces_unclassified_rather_than_omitting_it():
    """An unclassified operation must SAY so, not present as absent.

    This is the half that makes the coverage gap visible: before, an operation
    outside the registry was indistinguishable from one that had been reviewed
    and found harmless.
    """
    d = _plan("bead.close").to_dict()
    assert d["blast_radius"]["gate"] == "unclassified"
    assert d["blast_radius"]["blast_radius"] is None
    assert "blast_radius.toml" in d["blast_radius"]["blast_radius_reason"]


def test_classification_never_raises_out_of_to_dict():
    """A classifier failure must not make a plan unserializable.

    Reporting is not worth turning into an outage, so the helper reports
    `classifier-error` rather than propagating.
    """
    out = _classify_operation("\x00 not a real operation \x00")
    assert out["gate"] in {"unclassified", "classifier-error"}


def test_registry_coverage_is_reported_not_assumed():
    """Pins the 3-of-13 measurement the enforcement decision rests on.

    If someone classifies more operations this test should be UPDATED, not
    deleted -- the number is the input to whether the ladder can be switched on.
    """
    classified = [
        op for op in (
            "briefs.adjudicate", "briefs.create", "briefs.defer",
            "bead.close", "bead.hold", "bead.release", "bead_comment",
            "create_defect_bead", "create_github_issue", "create_issue_bead",
            "molecule.cancel", "standardize_github_issue", "work.dispatch_event",
        )
        if _classify_operation(op)["gate"] != "unclassified"
    ]
    assert sorted(classified) == ["briefs.adjudicate", "briefs.create", "briefs.defer"]
