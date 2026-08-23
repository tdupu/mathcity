"""A brief this tool emits must be DISPATCHABLE, not merely created.

#85 records the damage: `decisions-to-briefs/SKILL.md` writes
`.pile/manifest.jsonl` and `decisions-track/` directly, behind mctl's back,
because no typed tool exists to do it properly. Shipping a tool that emits briefs
which cannot then be dispatched relocates that problem instead of fixing it -- the
skill keeps writing directly, because the sanctioned path still does not work.

So the bar is `work_status` on the created brief returning `readiness: "ready"`
with `blockers: []`. A test that creates a brief and asserts the call returned
cleanly does NOT satisfy it. That is exactly the gap that let #173 exist: a brief
made its own source bead, then bricked by its own approval.

`readiness == "ready"` requires all of:

    MWRK011  a source dependency exists
    MWRK012  the source bead resolves
             the source bead is NOT closed
    MWRK010  the brief carries an approving verdict
    MWRK001  the source has no active assignee
    MWRK002  no open child workflow on the source
             no prior dispatch provenance  (else readiness is "dispatched")

The fixture's source beads are all claimed by a brief, so the choice matters:
`source-open`'s brief is OPEN and would trip MWRK002, failing this test for a
reason unrelated to the tool. `source-revise` is open and unassigned with a CLOSED
brief, so it is the one clean source in the fixture.

which is lumby's pair requirement stated as code:

    ADJUDICATED BRIEF --(source dependency)--> OPEN SOURCE BEAD
      closed + approving verdict                  status NOT closed
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from test_mcp_server import call, server, work_fixture


def _tool_names(instance) -> set[str]:
    response = instance.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    return {t["name"] for t in response["result"]["tools"]}


def _create(city_root, rig_root, **overrides):
    arguments = {
        "decision": "Adopt the narrowed brief read",
        "source_bead_id": "source-revise",
        "dry_run": False,
        **overrides,
    }
    return call(server(city_root, rig_root), "decisions_to_briefs", arguments)


def test_the_tool_exists_and_is_reachable(tmp_path: Path):
    """CT13.2: capability present, surface absent is the whole defect in #85."""
    names = _tool_names(server(*work_fixture(tmp_path)))

    assert "decisions_to_briefs" in names, f"tool not exposed: {sorted(names)}"


def test_the_created_brief_is_blocked_only_on_the_missing_verdict(tmp_path: Path):
    """THE bar, moved to the right point in the lifecycle -- not weakened.

    This test used to assert `readiness == "ready"` straight out of creation.
    That bar is right in spirit and was wrong in placement: `ready` requires
    MWRK010, an approving verdict, so demanding it at creation MANDATED the
    forged approval that #194 is about. The test encoded the bug.

    The concern behind it survives intact. Its original docstring is still the
    reason this file exists: a tool that emits briefs which cannot then be
    dispatched RELOCATES #85 instead of fixing it -- the skill keeps writing
    `.pile/manifest.jsonl` directly, because the sanctioned path still does not
    work. So we still prove dispatchability. We prove it in two halves:

        here          everything about the brief is dispatch-ready EXCEPT the
                      verdict -- MWRK010 is the ONLY blocker
        next test     supplying that verdict through the ordinary gate makes it
                      ready

    Asserting `blockers == ["MWRK010"]` exactly is stronger than the old
    `blockers == []`: it proves the brief is well-formed AND names the single
    thing deliberately withheld. A brief blocked on MWRK010 *plus* anything else
    is still a defect, and this still catches it.
    """
    city_root, rig_root = work_fixture(tmp_path)

    created = _create(city_root, rig_root)["result"]["structuredContent"]
    brief_id = created["brief_id"]

    status = call(
        server(city_root, rig_root), "work_status", {"brief_id": brief_id}
    )["result"]["structuredContent"]["work"]

    codes = sorted(b.get("code") for b in status["blockers"])
    assert codes == ["MWRK010"], (
        "an UNDECIDED brief must be blocked on the missing verdict and nothing "
        f"else; anything more is a malformed brief. blockers={codes}"
    )


def test_it_becomes_dispatchable_once_a_human_adjudicates(tmp_path: Path):
    """The other half: the honest path to `ready` still works.

    #194 removes the tool's self-approval. If nothing else could supply that
    verdict the pipeline would be severed, so this proves the human gate --
    `briefs_adjudicate`, which exists for exactly this -- closes the gap.

    Together with the previous test this is a strictly stronger guarantee than
    the assertion it replaced: the old one proved a brief could reach `ready`,
    but could not tell whether a HUMAN or the TOOL put it there.
    """
    city_root, rig_root = work_fixture(tmp_path)

    created = _create(city_root, rig_root)["result"]["structuredContent"]
    brief_id = created["brief_id"]

    call(
        server(city_root, rig_root),
        "briefs_adjudicate",
        {
            "brief_id": brief_id,
            "verdict": "approve",
            "reason": "test: a human adjudicated this brief",
            "dry_run": False,
        },
    )

    status = call(
        server(city_root, rig_root), "work_status", {"brief_id": brief_id}
    )["result"]["structuredContent"]["work"]

    assert status["blockers"] == [], (
        "adjudicating did not clear the blockers: "
        f"{[b.get('code') for b in status['blockers']]}"
    )
    assert status["readiness"] == "ready", f"readiness={status['readiness']}"


def test_it_refuses_a_closed_source_bead(tmp_path: Path):
    """#173's shape: a brief that bricks the moment it is approved.

    A closed source cannot be worked, so a brief pointing at one is born
    undispatchable. Refusing at creation is the whole point of the pair rule.
    """
    city_root, rig_root = work_fixture(tmp_path)

    response = _create(city_root, rig_root, source_bead_id="mc-approved")
    structured = response["result"]["structuredContent"]

    codes = [d.get("code") for d in structured.get("diagnostics", [])]
    assert any(c and c.startswith("MDTB") for c in codes), (
        f"a closed source bead was accepted without complaint: {codes}"
    )
    assert not structured.get("applied"), "applied a brief onto a closed source"


def test_dry_run_is_the_default_and_writes_nothing(tmp_path: Path):
    """Mutating tools default to dry_run per the MCP conventions."""
    city_root, rig_root = work_fixture(tmp_path)

    structured = call(
        server(city_root, rig_root),
        "decisions_to_briefs",
        {"decision": "d", "source_bead_id": "source-revise"},
    )["result"]["structuredContent"]

    assert structured["applied"] is False, "omitting dry_run applied a write"
    assert structured.get("effect_plan"), "a dry run must still return its plan"


def test_present_briefs_completes_through_the_mcp(tmp_path: Path):
    """CT13.1: the operation must COMPLETE through the MCP, not merely exist."""
    city_root, rig_root = work_fixture(tmp_path)

    names = _tool_names(server(city_root, rig_root))
    assert "briefs_present" in names, f"present-briefs not exposed: {sorted(names)}"

    structured = call(
        server(city_root, rig_root), "briefs_present", {}
    )["result"]["structuredContent"]

    assert "briefs" in structured, "present returned no briefs collection"


# --- #169 regression -------------------------------------------------------
#
# The body this tool emits must satisfy the structural rule in
# assets/brief-pipeline/required-sections.toml. Nothing asserted that, so when
# #169 landed the tool silently began emitting briefs that briefs_create refused
# with MBRF036 -- and the response came back with neither `applied` nor
# `brief_id`, only diagnostics.
#
# The rule lives in a data file precisely so two checkers cannot drift. This test
# reads THAT file rather than restating the regex, so if the required sections
# change, this fails instead of quietly passing against a stale copy.


def test_the_emitted_body_satisfies_every_required_section(tmp_path: Path):
    import re
    import tomllib

    spec = (
        Path(__file__).resolve().parents[2]
        / "assets" / "brief-pipeline" / "required-sections.toml"
    )
    required = tomllib.loads(spec.read_text(encoding="utf-8"))["section"]
    assert required, "the required-sections spec is empty; this test would be vacuous"

    from mctl_core.decisions import brief_body

    body = brief_body(
        "Adopt the narrowed brief read",
        source_bead_id="source-revise",
        checks_passed=("source resolves", "source is open"),
    )

    for section in required:
        # the spec's regex is POSIX bracket syntax for brief-check.sh; translate
        # the one class it uses so Python's `re` sees the same rule.
        pattern = section["match"].replace("[[:space:]]", r"\s")
        assert re.search(pattern, body, re.MULTILINE), (
            f"emitted body is missing the required section {section['name']!r}, "
            f"which briefs_create refuses with MBRF036"
        )


# --- #194: the tool transports a QUESTION, not a decision ------------------
#
# Taylor's ruling, 2026-08-23 -- neither of the two readings that were put to
# him. The NAME is the bug:
#
#   "decisions to briefs"
#     read as   decisions ALREADY MADE -> briefs   ==> a verdict is required
#                                                   ==> hardcode verdict="approve"
#     he means  decisions TO BE MADE   -> briefs   ==> no verdict EXISTS yet
#                                                   ==> deposit UNDECIDED
#
# His pipeline: a decision he needs to make becomes a hygienic brief deposited
# UNDECIDED on the PILE; the no-brainer cycle either answers it automatically or
# promotes it to the STACK, where he adjudicates systematically. The pile is
# load-bearing -- it is where a question gets a chance to be resolved before it
# costs him attention.
#
# So the tool must not approve at all. A tool that stamps its own verdict forges
# the single thing it exists to collect.
#
# This is deliberately NOT asserted via work_status/readiness. `readiness ==
# "ready"` requires MWRK010, an approving verdict -- so a readiness assertion
# cannot distinguish "correctly undecided" from "broken". It has to be read off
# the brief's own state.


def test_it_deposits_undecided_and_does_not_adjudicate_at_creation(tmp_path: Path):
    """#194. The tool must NOT record a verdict nobody gave."""
    city_root, rig_root = work_fixture(tmp_path)

    created = _create(city_root, rig_root)["result"]["structuredContent"]
    brief_id = created["brief_id"]
    assert brief_id, f"nothing was created: {created.get('diagnostics')}"

    brief = call(
        server(city_root, rig_root), "briefs_show", {"brief_id": brief_id}
    )["result"]["structuredContent"]["brief"]

    verdict = brief.get("verdict")
    assert not verdict, (
        "decisions_to_briefs stamped a verdict nobody gave -- #194. "
        f"verdict={verdict!r}. The tool transports a question; it does not "
        "answer it."
    )
    assert brief.get("decision_state") != "adjudicated", (
        "the brief was marked adjudicated at creation; no human has seen it"
    )
    assert brief.get("status") != "closed", (
        "the brief was CLOSED at creation -- it never reaches the pile as an "
        "open question, so the no-brainer cycle can never triage it"
    )
