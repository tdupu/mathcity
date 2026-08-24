"""#115 -- the evidence core, buildable slice only.

The issue owner measured the live event log and ruled the full five-link
chain (`claimed -> agent_active -> commit -> artifact -> step_closed`) NOT
BUILDABLE: four of five links have no emitter. Building a positional
`broken_at` regardless would blame link 1 on every healthy step -- the exact
defect inverted (P6.2's mirror: a check that could not have failed must not
render as passed).

This file pins the buildable core instead:

  1. a reader for the `gc.expected_artifacts.v1` declaration (#142's keystone),
  2. `is_complete` derived THREE-VALUED from declared-vs-actual artifacts,
     NEVER from bead status,
  3. the five evidence links represented honestly: `not_recorded` for the
     three links with no emitter (never named as a break), `recorded` /
     `not_yet` for the two that have one.

WHAT THESE TESTS EXIST TO CATCH. An implementation that (a) falls back to
bead status when there is no declaration, (b) treats malformed JSON as an
empty declaration (reads as `complete` instead of `unknown`), or (c) lets
`broken_at` name `claimed` -- the inversion the issue was filed to prevent.
"""
from __future__ import annotations

import sys
from pathlib import Path

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


ROOT = _bead(
    "gsp-root1",
    "build-basic-briefed",
    {"gc.kind": "workflow", "gc.formula_name": "build-basic-briefed"},
)


# ---------------------------------------------------------------------------
# 1. the declaration reader
# ---------------------------------------------------------------------------


class TestTheDeclarationReader:
    def test_a_declared_step_parses_the_json_array(self):
        step = _bead(
            "gsp-s1",
            metadata={
                "gc.kind": "workflow-finalize",
                "gc.root_bead_id": ROOT.id,
                "gc.expected_artifacts.v1": '["/city/.pile/brief.md"]',
            },
        )
        assert mol._expected_artifacts_of(step.raw["metadata"]) == ["/city/.pile/brief.md"]

    def test_an_undeclared_step_reads_as_none_not_an_empty_list(self):
        """None ("no declaration") must not collapse into `[]` ("declared
        zero artifacts") -- the two mean different things downstream."""
        step = _bead("gsp-s2", metadata={"gc.kind": "workflow-finalize", "gc.root_bead_id": ROOT.id})
        assert mol._expected_artifacts_of(step.raw["metadata"]) is None

    def test_malformed_json_reads_as_undeclared_not_a_crash(self):
        step = _bead(
            "gsp-s3",
            metadata={
                "gc.kind": "workflow-finalize",
                "gc.root_bead_id": ROOT.id,
                "gc.expected_artifacts.v1": "{not valid json",
            },
        )
        assert mol._expected_artifacts_of(step.raw["metadata"]) is None

    def test_a_json_value_that_is_not_an_array_of_strings_reads_as_undeclared(self):
        step = _bead(
            "gsp-s4",
            metadata={"gc.expected_artifacts.v1": '{"a": 1}'},
        )
        assert mol._expected_artifacts_of(step.raw["metadata"]) is None

        step2 = _bead(
            "gsp-s5",
            metadata={"gc.expected_artifacts.v1": '["ok", 4]'},
        )
        assert mol._expected_artifacts_of(step2.raw["metadata"]) is None

    def test_a_blank_declaration_reads_as_undeclared(self):
        step = _bead("gsp-s6", metadata={"gc.expected_artifacts.v1": "   "})
        assert mol._expected_artifacts_of(step.raw["metadata"]) is None


# ---------------------------------------------------------------------------
# 2. is_complete, three-valued, never from bead status
# ---------------------------------------------------------------------------


class TestIsCompleteThreeValued:
    def test_declared_and_fully_produced_is_complete(self):
        step = _bead(
            "gsp-c1",
            metadata={
                "gc.expected_artifacts.v1": '["/a/brief.md"]',
                "gc.build.brief": "/a/brief.md",
            },
        )
        completion = mol._completion_of(step.raw["metadata"])
        assert completion["is_complete"] == mol.IS_COMPLETE_COMPLETE
        assert completion["declared"] == ["/a/brief.md"]
        assert completion["present"] == ["/a/brief.md"]
        assert completion["missing"] == []

    def test_declared_and_partially_missing_is_incomplete(self):
        step = _bead(
            "gsp-c2",
            metadata={
                "gc.expected_artifacts.v1": '["/a/brief.md", "/a/pile.md"]',
                "gc.build.brief": "/a/brief.md",
            },
        )
        completion = mol._completion_of(step.raw["metadata"])
        assert completion["is_complete"] == mol.IS_COMPLETE_INCOMPLETE
        assert completion["missing"] == ["/a/pile.md"]
        assert completion["present"] == ["/a/brief.md"]

    def test_no_declaration_is_unknown_not_false(self):
        """The whole point: an undeclared step must not read as incomplete
        (which would look like failed work) or complete (a guess)."""
        step = _bead("gsp-c3", metadata={"gc.build.brief": "/a/brief.md"})
        completion = mol._completion_of(step.raw["metadata"])
        assert completion["is_complete"] == mol.IS_COMPLETE_UNKNOWN
        assert completion["declared"] is None

    def test_is_complete_never_reads_bead_closed_status(self):
        """A CLOSED bead with no declaration is still `unknown` -- bead status
        is exactly the self-reported signal #115 exists to stop trusting."""
        step = _bead("gsp-c4", status="closed", metadata={})
        completion = mol._completion_of(step.raw["metadata"])
        assert completion["is_complete"] == mol.IS_COMPLETE_UNKNOWN

        # And the mirror: an OPEN bead with a satisfied declaration is
        # complete, even though bead status alone would have said otherwise.
        open_but_done = _bead(
            "gsp-c5",
            status="open",
            metadata={
                "gc.expected_artifacts.v1": '["/a/x.md"]',
                "gc.build.x": "/a/x.md",
            },
        )
        assert (
            mol._completion_of(open_but_done.raw["metadata"])["is_complete"]
            == mol.IS_COMPLETE_COMPLETE
        )

    def test_malformed_declaration_is_unknown_not_complete(self):
        """A malformed declaration must not silently become 'declared zero
        artifacts', which would report complete for a step that just failed
        to author its metadata correctly."""
        step = _bead("gsp-c6", metadata={"gc.expected_artifacts.v1": "not json"})
        completion = mol._completion_of(step.raw["metadata"])
        assert completion["is_complete"] == mol.IS_COMPLETE_UNKNOWN


# ---------------------------------------------------------------------------
# 3. evidence links, honest tri-state
# ---------------------------------------------------------------------------


class TestEvidenceLinks:
    def test_the_three_unrecorded_links_are_not_recorded_never_not_yet(self):
        """claimed/agent_active/commit have NO emitter in the city today.
        `not_yet` would claim an emitter exists and simply has not fired --
        a stronger, false claim."""
        links = {
            link["link"]: link
            for link in mol._evidence_links({}, "open", {})
        }
        for name in ("claimed", "agent_active", "commit"):
            assert links[name]["status"] == mol.LINK_NOT_RECORDED
            assert links[name]["status"] != mol.LINK_NOT_YET

    def test_artifact_link_is_recorded_when_gc_build_has_an_entry(self):
        links = {
            link["link"]: link
            for link in mol._evidence_links({}, "open", {"brief": "/a/x.md"})
        }
        assert links["artifact"]["status"] == mol.LINK_RECORDED

    def test_artifact_link_is_not_yet_when_gc_build_is_empty(self):
        links = {link["link"]: link for link in mol._evidence_links({}, "open", {})}
        assert links["artifact"]["status"] == mol.LINK_NOT_YET

    def test_step_closed_link_is_recorded_for_a_closed_bead(self):
        links = {link["link"]: link for link in mol._evidence_links({}, "closed", {})}
        assert links["step_closed"]["status"] == mol.LINK_RECORDED

    def test_step_closed_link_is_not_yet_for_an_open_bead(self):
        links = {link["link"]: link for link in mol._evidence_links({}, "open", {})}
        assert links["step_closed"]["status"] == mol.LINK_NOT_YET

    def test_every_link_carries_a_reason(self):
        for link in mol._evidence_links({}, "open", {}):
            assert link["reason"], link["link"]


class TestBrokenAt:
    def test_broken_at_never_names_an_unrecorded_link(self):
        """The exact inversion #115 exists to prevent: blaming link 1
        (`claimed`) on every healthy step because it has no recorder."""
        completion = mol._completion_of({"gc.expected_artifacts.v1": '["/a/x.md"]'})
        broken = mol._broken_at("open", completion)
        assert broken["broken_at"] not in ("claimed", "agent_active", "commit")

    def test_a_healthy_in_flight_step_is_not_a_break(self):
        """An advancing step -- declared, artifact not yet produced, bead
        still open -- must NOT render a false finding. `not_yet` means "not
        reached yet", not "broken here": with no staleness signal,
        "advancing" and "stalled" are indistinguishable from a bare
        `not_yet`, so a merely-not-yet link is never named as the break.
        This is the exact positional-blame defect #115 exists to prevent,
        which an earlier draft of this function reintroduced by naming the
        first `not_yet` link regardless of step status.
        """
        completion = mol._completion_of({"gc.expected_artifacts.v1": '["/a/x.md"]'})
        assert mol._broken_at("open", completion)["broken_at"] is None

        # And the step_closed-not-yet case, with the artifact already there.
        completion2 = mol._completion_of(
            {"gc.expected_artifacts.v1": '["/a/x.md"]', "gc.build.x": "/a/x.md"}
        )
        assert mol._broken_at("open", completion2)["broken_at"] is None

    def test_a_closed_step_with_a_missing_declared_artifact_is_the_genuine_break(self):
        """The ONE checkable break: bead status closed (`step_closed`
        recorded) but a declared artifact was never produced -- completion
        self-reported without producing the declared output."""
        completion = mol._completion_of({"gc.expected_artifacts.v1": '["/a/x.md"]'})
        broken = mol._broken_at("closed", completion)
        assert broken["broken_at"] == "artifact"
        assert "closed" in broken["broken_at_reason"].lower()
        assert "missing" in broken["broken_at_reason"].lower()

    def test_a_closed_step_with_no_declaration_is_not_a_break(self):
        """Nothing was declared, so there is nothing to check -- closing the
        bead is not itself evidence of anything here."""
        completion = mol._completion_of({})
        assert mol._broken_at("closed", completion)["broken_at"] is None

    def test_broken_at_is_null_with_a_reason_when_nothing_checkable_is_broken(self):
        """A closed step whose declared artifact IS present. This is NOT a
        claim the whole chain is healthy -- three links remain unrecorded
        and unassessed."""
        completion = mol._completion_of(
            {"gc.expected_artifacts.v1": '["/a/x.md"]', "gc.build.x": "/a/x.md"}
        )
        broken = mol._broken_at("closed", completion)
        assert broken["broken_at"] is None
        assert broken["broken_at_reason"]


# ---------------------------------------------------------------------------
# integration: describe_with_steps carries all of it, per step
# ---------------------------------------------------------------------------


class TestDescribeWithStepsCarriesEvidence:
    def test_a_step_with_no_declaration_renders_unknown(self):
        step = _bead(
            "gsp-i1", "Finalize", {"gc.kind": "workflow-finalize", "gc.root_bead_id": ROOT.id}
        )
        out = mol.describe_with_steps(ROOT, [ROOT, step])
        row = out["steps"][0]
        assert row["is_complete"] == mol.IS_COMPLETE_UNKNOWN
        assert row["expected_artifacts"] is None

    def test_a_step_with_a_satisfied_declaration_renders_complete(self):
        step = _bead(
            "gsp-i2",
            "Submit",
            {
                "gc.kind": "workflow-finalize",
                "gc.root_bead_id": ROOT.id,
                "gc.expected_artifacts.v1": '["/a/pile.md"]',
                "gc.build.pile": "/a/pile.md",
            },
        )
        out = mol.describe_with_steps(ROOT, [ROOT, step])
        row = out["steps"][0]
        assert row["is_complete"] == mol.IS_COMPLETE_COMPLETE
        assert row["expected_artifacts"] == ["/a/pile.md"]
        assert row["artifacts"] == {"pile": "/a/pile.md"}

    def test_every_step_carries_the_evidence_object_with_five_links(self):
        step = _bead(
            "gsp-i3", "Finalize", {"gc.kind": "workflow-finalize", "gc.root_bead_id": ROOT.id}
        )
        out = mol.describe_with_steps(ROOT, [ROOT, step])
        evidence = out["steps"][0]["evidence"]
        assert {link["link"] for link in evidence["links"]} == set(mol.EVIDENCE_LINK_ORDER)
        assert "broken_at" in evidence
        assert "broken_at_reason" in evidence
