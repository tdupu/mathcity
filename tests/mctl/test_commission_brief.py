"""commission_brief: a source bead becomes a commission brief in the pile (#190).

WHY THIS IS A SEPARATE SURFACE FROM `briefs_create`. `briefs_create` makes *a*
brief from arbitrary title/body/sources. It does not know what a commission is:
no template, no tracker provenance, and none of the five constraints below.
Building commission semantics into it would overload a general primitive, and
the constraints would then apply conditionally inside one function -- which is
how they get skipped.

WHY IT IS SEPARATE FROM `#170`. That is the inverse half: `#170` is *have a
brief, need a bead*; this is *have a bead, need a brief*.

THE FIVE CONSTRAINTS ARE NOT STYLE. Each produced a real failure during the
by-hand proof on 2026-08-23 (`gh#1` -> `mc-7d0` -> `mc-60j` -> readiness
"ready"). They are pinned here so a second operator does not rediscover them:

  1. sources required and non-empty  -- omitting bricks the brief (MWRK011)
  2. bead and brief in the SAME STORE -- cross-store fails at creation
  3. tracker provenance in METADATA   -- bd rejects `kind/bug` (MBRF033)
  4. bd labels carry only what it IS  -- `commission`, nothing invented
  5. pile only, never a stack write   -- B2.10; the stack is brief-shuffle's

WHAT THESE TESTS DO NOT COVER. The MCP registration is deliberately absent:
adding a tool touches six declarations that three agents are queued to edit, and
the agreed order puts this last. These tests exercise the core only.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import commission  # noqa: E402
from mctl_core.context import resolve_context  # noqa: E402
from mctl_core.effects import plan_commission_brief  # noqa: E402

from test_mcp_server import empty_rig_fixture  # noqa: E402


class TestSourcesAreMandatory:
    """Constraint 1. The single most expensive omission on this path."""

    def test_empty_sources_is_refused(self):
        with pytest.raises(commission.CommissionRefused) as excinfo:
            commission.validate_commission(sources=(), bead_rig="mathcity", brief_rig="mathcity")
        assert excinfo.value.code == "MCMS_SOURCES_REQUIRED"

    def test_the_refusal_names_MWRK011_as_the_downstream_cost(self):
        """A refusal that does not say what it prevents gets argued with."""
        with pytest.raises(commission.CommissionRefused) as excinfo:
            commission.validate_commission(sources=(), bead_rig="mathcity", brief_rig="mathcity")
        assert "MWRK011" in str(excinfo.value)

    def test_a_source_is_enough(self):
        commission.validate_commission(
            sources=("mc-7d0",), bead_rig="mathcity", brief_rig="mathcity"
        )


class TestSameStore:
    """Constraint 2. A city-root bead against a rig brief fails at creation with
    'no issue found matching <id>' -- clean, nothing written, and invisible
    until you hit it. Caught here instead."""

    def test_a_cross_store_source_is_refused_BEFORE_the_write(self):
        with pytest.raises(commission.CommissionRefused) as excinfo:
            commission.validate_commission(
                sources=("gt-xbk10c",), bead_rig="hq", brief_rig="mathcity"
            )
        assert excinfo.value.code == "MCMS_CROSS_STORE_SOURCE"

    def test_the_refusal_names_BOTH_rigs_so_the_fix_is_obvious(self):
        with pytest.raises(commission.CommissionRefused) as excinfo:
            commission.validate_commission(
                sources=("gt-xbk10c",), bead_rig="hq", brief_rig="mathcity"
            )
        assert "hq" in str(excinfo.value) and "mathcity" in str(excinfo.value)


class TestTrackerProvenanceGoesToMetadata:
    """Constraint 3. GitHub labels are namespaced (`kind/bug`); bd rejects
    slashes as label tokens (MBRF033). Dropping the namespace is lossy --
    `kind/bug` and `status/bug` collapse. Metadata is lossless and queryable."""

    def test_gh_labels_are_carried_VERBATIM_in_metadata(self):
        md = commission.tracker_metadata(
            issue_url="https://github.com/tdupu/mathcity/issues/1",
            labels=("kind/bug", "priority/p1"),
        )
        assert md["gh.labels"] == "kind/bug,priority/p1"

    def test_the_slash_survives_because_metadata_has_no_token_rules(self):
        md = commission.tracker_metadata(
            issue_url="https://github.com/tdupu/mathcity/issues/1", labels=("kind/bug",)
        )
        assert "/" in md["gh.labels"], "namespace must not be stripped -- that is lossy"

    def test_issue_and_repo_are_separate_queryable_keys(self):
        md = commission.tracker_metadata(
            issue_url="https://github.com/tdupu/mathcity/issues/1", labels=()
        )
        assert md["gh.issue"] == "tdupu/mathcity#1"
        assert md["gh.repo"] == "tdupu/mathcity"

    def test_no_labels_means_the_key_is_ABSENT_not_empty_string(self):
        """Absent means 'the issue had none'. An empty string is a value that
        looks like a measurement and is not one."""
        md = commission.tracker_metadata(
            issue_url="https://github.com/tdupu/mathcity/issues/1", labels=()
        )
        assert "gh.labels" not in md


class TestRigIsDerivedFromTheTracker:
    """Taylor: 'if you are pulling an issue from a github issue tracker, then
    that tracker belongs to the repo of a rig. The obvious spot is that rig.'"""

    def test_the_repo_name_is_the_rig(self):
        assert commission.rig_for_issue("https://github.com/tdupu/mathcity/issues/1") == "mathcity"

    def test_an_unparseable_url_returns_None_rather_than_guessing(self):
        assert commission.rig_for_issue("not-a-url") is None


class TestBdLabels:
    """Constraint 4. bd labels say what the brief IS. Nothing invented --
    `kind/commission` was invented once and MBRF033 correctly refused it."""

    def test_the_only_bd_label_is_the_briefs_own_kind(self):
        assert commission.brief_labels() == ("commission",)

    def test_no_label_contains_a_slash(self):
        assert all("/" not in label for label in commission.brief_labels())


class TestPileOnly:
    """Constraint 5, B2.10: 'Every adjudicable brief source must enter the
    shared .pile -> brief-shuffle -> stack -> present-briefs lifecycle before it
    reaches the human adjudicator.' A stack write here would place a brief in
    the stack having never faced promote/reject."""

    def test_the_module_never_references_the_stack(self):
        source = (SCRIPTS_ROOT / "mctl_core" / "commission.py").read_text(encoding="utf-8")
        offenders = [
            line
            for line in source.splitlines()
            if "layout.stack" in line or "stack_index" in line
        ]
        assert not offenders, f"B2.10: commission_brief must not write the stack: {offenders}"


def test_plan_commission_brief_carries_commission_semantics_into_the_effect_plan(tmp_path):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    ctx = resolve_context(
        city_root,
        city=city_root,
        rig="mathcity",
        require_runtime_city=True,
        env={"MCTL_BEADS_FIXTURE": str(rig_root / ".beads" / "issues.jsonl")},
    )

    plan = plan_commission_brief(
        ctx,
        bead_id="mc-source",
        title="Commission the source bead",
        body=(
            "## What is being decided\n\nProceed.\n\n"
            "## Gate Evidence\n\nG5: n/a -- no server surface touched.\n"
        ),
        issue_url="https://github.com/tdupu/mathcity/issues/190",
        issue_labels=("kind/feature", "priority/p1"),
        bead_rig="mathcity",
    )

    create = plan.bead_creates[0]
    assert create.labels == ("commission",)
    assert create.sources == ("mc-source",)
    assert create.metadata["gh.issue"] == "tdupu/mathcity#190"
    assert create.metadata["gh.labels"] == "kind/feature,priority/p1"


class TestMetadataReachesTheBead:
    """The gap left open at e0bf1ad, closed now that #168 came off the path.

    `commission.tracker_metadata` computed the gh.* keys correctly and
    `BriefCreateInput` had nowhere to put them, so the provenance died between
    the two. Metadata is the whole reason we chose it over labels -- unreachable
    metadata is worse than the labels we rejected, because it looks carried.
    """

    def test_BriefCreateInput_accepts_metadata(self):
        import dataclasses

        from mctl_core.effects import BriefCreateInput

        names = {f.name for f in dataclasses.fields(BriefCreateInput)}
        assert "metadata" in names, "gh.* provenance has nowhere to go without this"

    def test_it_defaults_to_empty_so_existing_callers_are_unaffected(self):
        import dataclasses

        from mctl_core.effects import BriefCreateInput

        field = next(f for f in dataclasses.fields(BriefCreateInput) if f.name == "metadata")
        assert field.default == () or field.default_factory is not dataclasses.MISSING

    def test_supplied_metadata_is_written_onto_the_bead(self):
        source = (SCRIPTS_ROOT / "mctl_core" / "effects.py").read_text(encoding="utf-8")
        assert "request.metadata" in source, "the field must be READ, not merely accepted"

    def test_caller_metadata_cannot_overwrite_mctl_provenance(self):
        """created_by/trace_id/created_at are mctl's own attestation. A caller
        that could overwrite them could forge provenance."""
        source = (SCRIPTS_ROOT / "mctl_core" / "effects.py").read_text(encoding="utf-8")
        # Assert the CALLER-METADATA loop specifically, not merely that the word
        # "setdefault" appears nearby. The first version of this test checked a
        # 700-char window and passed when the guard was removed, because an
        # unrelated setdefault elsewhere in the file sat inside that window --
        # a check satisfied by code it was not testing.
        loop = source.split("for key, value in (request.metadata or {}).items():", 1)
        assert len(loop) == 2, "the caller-metadata loop is missing entirely"
        body = loop[1][:400]
        assert "metadata.setdefault(" in body, (
            "caller metadata must fill gaps, never clobber mctl's own attestation "
            "(created_by / mctl_trace_id / created_at) -- otherwise provenance is forgeable"
        )
        assert "metadata[str(key)] =" not in body, "direct assignment would clobber"
