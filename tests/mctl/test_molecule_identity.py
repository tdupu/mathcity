"""Molecule identity (#109).

The design is `<city-root>/docs/D1-molecule-identity-proposal.md`, verified
against three live beads before it was written. These tests pin the part that
was got wrong twice in prose, so it cannot be got wrong a third time in code.

THE ERROR THESE TESTS EXIST TO PREVENT. The handoff defines a molecule as "a
workflow root bead *carrying* `gc.root_bead_id`". That has the pointer
backwards: the root does NOT carry it. Steps carry it and point AT the root.
Anyone implementing from that sentence builds the edge in the wrong direction,
and `beads.Bead.workflow_root_id` documented it backwards too.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import molecules as mol  # noqa: E402
from mctl_core.beads import Bead  # noqa: E402


def _bead(bead_id: str, title: str = "t", metadata: dict | None = None, **kw) -> Bead:
    return Bead(
        id=bead_id,
        title=title,
        status=kw.pop("status", "open"),
        issue_type=kw.pop("issue_type", "task"),
        labels=(),
        source_dependencies=(),
        created_at="2026-08-05T17:35:17Z",
        updated_at="2026-08-05T17:35:36Z",
        raw={"metadata": dict(metadata or {})},
        **kw,
    )


# The three live beads the design was read off, reduced to their signatures.
ROOT = _bead(
    "gsp-q31ot8",
    "build-basic-briefed",
    {
        "gc.kind": "workflow",
        "gc.formula_name": "build-basic-briefed",
        "gc.formula_contract": "graph.v2",
        "gc.root_store_ref": "rig:gascity-packs",
        "gc.routed_to": "gascity-packs/gc.run-operator",
        "gc.session_name": "gc__task-decomposer-gt-x6dasj",
        "gc.var.artifact_root": "<city-root>/gascity-packs/.gc-builds/gsp-gdu8gi",
        "gc.var.convoy_id": "gsp-weuhku",
        "gc.build.plan_path": "<city-root>/.gc-builds/gsp-gdu8gi/gsp-q31ot8/implementation-plan.md",
        "gc.build.requirements_path": "<city-root>/.gc-builds/gsp-gdu8gi/requirements.md",
    },
)
STEP = _bead(
    "gsp-bo0q6i",
    "Finalize workflow",
    {"gc.kind": "workflow-finalize", "gc.root_bead_id": "gsp-q31ot8"},
)
ORDINARY = _bead("gsp-1nwt8", "manifest-triage-filter", {})


class TestThePredicateDiscriminates:
    def test_a_workflow_root_is_a_molecule_root(self):
        assert mol.is_molecule_root(ROOT)

    def test_a_step_is_not_a_molecule_root(self):
        assert not mol.is_molecule_root(STEP)

    def test_an_ordinary_bead_is_not_a_molecule_root(self):
        assert not mol.is_molecule_root(ORDINARY)

    def test_the_root_predicate_is_an_exact_match_not_a_prefix(self):
        """`workflow-finalize` startswith `workflow`. A prefix test would call
        every step a root, which is the whole population inverted."""
        assert not mol.is_molecule_root(
            _bead("x", metadata={"gc.kind": "workflow-implement"})
        )


class TestTheEdgePointsAtTheRoot:
    """The backwards-definition regression. Named so the failure explains itself."""

    def test_the_ROOT_does_not_carry_gc_root_bead_id(self):
        assert "gc.root_bead_id" not in ROOT.raw["metadata"]

    def test_the_STEP_carries_it_and_names_the_root(self):
        assert STEP.raw["metadata"]["gc.root_bead_id"] == ROOT.id

    def test_a_step_is_identified_by_the_pointer_not_by_the_kind_vocabulary(self):
        """`gc.kind` step values are a namespaced family that is NOT enumerated.
        Keying on the pointer cannot go stale as new kinds are added."""
        unknown_kind = _bead(
            "y", metadata={"gc.kind": "workflow-some-future-step", "gc.root_bead_id": "r"}
        )
        assert mol.is_step(unknown_kind)

    def test_steps_of_uses_the_reverse_index(self):
        found = mol.steps_of(ROOT.id, [ROOT, STEP, ORDINARY])
        assert [b.id for b in found] == [STEP.id]

    def test_a_root_is_never_its_own_step(self):
        assert ROOT not in mol.steps_of(ROOT.id, [ROOT, STEP])


class TestTheFieldMap:
    def test_identity_is_the_root_bead_id(self):
        assert mol.describe(ROOT)["id"] == "gsp-q31ot8"

    def test_the_formula_and_worker_come_off_the_root(self):
        d = mol.describe(ROOT)
        assert d["formula"] == "build-basic-briefed"
        assert d["worker"] == "gc__task-decomposer-gt-x6dasj"

    def test_the_rig_ref_is_parsed_not_assumed_bare(self):
        """`gc.root_store_ref` is prefixed `rig:<name>`."""
        assert mol.describe(ROOT)["rig"] == "gascity-packs"

    def test_stage_artifacts_are_collected_from_the_build_namespace(self):
        assert set(mol.describe(ROOT)["artifacts"]) == {"plan_path", "requirements_path"}

    def test_describe_refuses_a_non_root(self):
        with pytest.raises(ValueError):
            mol.describe(STEP)


class TestTheTrapsThatBiteImplementers:
    def test_three_distinct_ids_are_not_conflated(self):
        """One root carries the molecule id, the artifact-root scope, and the
        convoy id -- and the artifact paths nest two of them."""
        d = mol.describe(ROOT)
        assert d["id"] == "gsp-q31ot8"
        assert d["convoy"] == "gsp-weuhku"
        assert "gsp-gdu8gi" in d["artifact_root"]
        assert d["id"] != d["convoy"] != d["artifact_root"]

    def test_the_title_is_the_formula_name_and_is_not_an_identifier(self):
        """All 45 live roots in gascity-packs share the title
        `build-basic-briefed`. A row label taken from the title labels nothing."""
        other = _bead(
            "gsp-8eqb3o",
            "build-basic-briefed",
            {"gc.kind": "workflow", "gc.formula_name": "build-basic-briefed"},
        )
        assert other.title == ROOT.title
        assert mol.describe(other)["id"] != mol.describe(ROOT)["id"]


class TestDeclaredGaps:
    def test_state_is_not_claimed(self):
        """#109 defines the noun, not its health. advancing/stalled/stranded
        need #115's evidence chain, which is BLOCKED. A molecule row showing a
        state it cannot derive is a plausible-empty-result failure."""
        assert "state" not in mol.describe(ROOT)

    def test_a_root_missing_optional_metadata_reports_none_not_a_guess(self):
        bare = _bead("z", metadata={"gc.kind": "workflow"})
        d = mol.describe(bare)
        assert d["formula"] is None and d["worker"] is None and d["rig"] is None
