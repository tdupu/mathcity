"""Authoring decision options + a recommendation at creation (#208, Plan G Part 1).

The adjudication side was already built for options -- `decision_options()` reads
them and MOPT001/MOPT002 refuse a verdict that does not name WHICH one -- but no
tool WROTE what that reader reads, so 1 of 280 decision beads carried labeled
options. `decisions_to_briefs` and `briefs_create` now accept
`decision_options: [{id, label, description}]` and an advisory `recommendation`
(an option id), rendered as the exact §4 markdown the reader parses.

TWO invariants this file pins:

* the writer round-trips through the EXISTING reader -- a brief created with
  options makes MOPT001 fire when adjudicated without naming one;
* the recommendation is ADVISORY, never a verdict (#194): a brief created WITH a
  recommendation is still deposited UNDECIDED, blocked on exactly MWRK010.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_mcp_server import call, server, work_fixture

OPTIONS = [
    {"id": "A", "label": "Do it now", "description": "Cheapest path"},
    {"id": "B", "label": "Defer it", "description": "Costs a cycle"},
    {"id": "C", "label": "Drop it", "description": "Status quo produced this brief"},
]

UNKNOWN_CODE = "MBRF_RECOMMENDATION_UNKNOWN_OPTION"

GATE_BODY = (
    "# Brief\n\n"
    "## §1 — What is being decided\n\nWhether to do the thing.\n\n"
    "## Gate Evidence\n\nChecked before writing.\n"
)


def _d2b(city, rig, **overrides):
    arguments = {
        "decision": "Whether to do the thing",
        "source_bead_id": "source-revise",
        "dry_run": False,
        **overrides,
    }
    return call(server(city, rig), "decisions_to_briefs", arguments)["result"][
        "structuredContent"
    ]


def _create(city, rig, **overrides):
    arguments = {
        "title": "Whether to do the thing",
        "body": GATE_BODY,
        "sources": ["source-revise"],
        "dry_run": False,
        **overrides,
    }
    return call(server(city, rig), "briefs_create", arguments)["result"][
        "structuredContent"
    ]


def _minted_brief_id(structured):
    for entry in structured.get("actual_effects") or ():
        if isinstance(entry, dict) and entry.get("kind") == "bead_create":
            target = entry.get("target")
            if isinstance(target, str):
                return target
    return None


def _show(city, rig, brief_id):
    return call(server(city, rig), "briefs_show", {"brief_id": brief_id})["result"][
        "structuredContent"
    ]["brief"]


# --- decisions_to_briefs ----------------------------------------------------


def test_decisions_to_briefs_writes_readable_options(tmp_path: Path):
    city, rig = work_fixture(tmp_path)
    created = _d2b(city, rig, decision_options=OPTIONS, recommendation="A")
    brief_id = created["brief_id"]
    assert brief_id, f"nothing created: {created.get('diagnostics')}"

    body = _show(city, rig, brief_id)["body"]
    assert "**(A) Do it now**" in body
    assert "**(B) Defer it**" in body
    assert "**(C) Drop it**" in body
    # The recommendation is the corpus's own `*(recommended)*` marker, on A.
    a_line = next(line for line in body.splitlines() if "**(A) Do it now**" in line)
    assert "*(recommended)*" in a_line, f"recommendation marker not on A: {a_line!r}"
    assert body.count("*(recommended)*") == 1, "only the recommended option is marked"


def test_the_authored_options_are_seen_by_the_adjudication_reader(tmp_path: Path):
    """End-to-end: the writer feeds the EXISTING MOPT reader, not a new one.

    A verdict on a multi-option brief that does not name an option is MOPT001.
    If the writer's markdown did not parse back into options, this would pass
    with no diagnostic -- so this is the round-trip proof.
    """
    city, rig = work_fixture(tmp_path)
    brief_id = _d2b(city, rig, decision_options=OPTIONS, recommendation="A")["brief_id"]

    adjudicated = call(
        server(city, rig),
        "briefs_adjudicate",
        {"brief_id": brief_id, "verdict": "approve", "reason": "r", "dry_run": False},
    )["result"]["structuredContent"]
    blocking = {
        (d.get("facts") or {}).get("blocking_code") for d in adjudicated.get("diagnostics", [])
    }
    assert "MOPT001" in blocking, (
        f"the authored options were not read back by the MOPT reader: {adjudicated.get('diagnostics')}"
    )


def test_a_recommendation_is_advisory_not_a_verdict(tmp_path: Path):
    """THE #208 contract test (the #194 invariant).

    Creating WITH a recommendation must still deposit the brief UNDECIDED. The
    recommendation is advice for the adjudicator, never an auto-verdict.
    """
    city, rig = work_fixture(tmp_path)
    brief_id = _d2b(city, rig, decision_options=OPTIONS, recommendation="B")["brief_id"]

    brief = _show(city, rig, brief_id)
    assert brief.get("verdict") is None, f"a recommendation became a verdict: {brief.get('verdict')!r}"

    status = call(server(city, rig), "work_status", {"brief_id": brief_id})["result"][
        "structuredContent"
    ]["work"]
    codes = sorted(b.get("code") for b in status["blockers"])
    assert codes == ["MWRK010"], (
        "a brief created with a recommendation must be blocked on the missing "
        f"verdict and nothing else: {codes}"
    )


def test_an_unknown_recommendation_is_refused_before_the_write(tmp_path: Path):
    city, rig = work_fixture(tmp_path)
    refused = _d2b(city, rig, decision_options=OPTIONS, recommendation="Z")

    codes = [d.get("code") for d in refused.get("diagnostics", [])]
    assert UNKNOWN_CODE in codes, f"an unknown recommendation was accepted: {codes}"
    assert not refused.get("applied"), "wrote a brief despite an unknown recommendation"
    assert not refused.get("brief_id"), "minted a brief despite an unknown recommendation"


def test_options_are_optional(tmp_path: Path):
    """The old call shape still works: no options, no §4 section, no refusal."""
    city, rig = work_fixture(tmp_path)
    brief_id = _d2b(city, rig)["brief_id"]
    body = _show(city, rig, brief_id)["body"]
    assert "*(recommended)*" not in body


# --- briefs_create ----------------------------------------------------------


def test_briefs_create_writes_readable_options(tmp_path: Path):
    city, rig = work_fixture(tmp_path)
    created = _create(city, rig, decision_options=OPTIONS, recommendation="C")
    brief_id = _minted_brief_id(created)
    assert brief_id, f"nothing created: {created.get('diagnostics')}"

    body = _show(city, rig, brief_id)["body"]
    assert "**(A) Do it now**" in body
    c_line = next(line for line in body.splitlines() if "**(C) Drop it**" in line)
    assert "*(recommended)*" in c_line
    # Gate Evidence -- the one structurally-required section -- must survive the
    # appended options block, or MBRF036 would have refused the create.
    assert "Gate Evidence" in body


def test_briefs_create_refuses_an_unknown_recommendation(tmp_path: Path):
    city, rig = work_fixture(tmp_path)
    refused = _create(city, rig, decision_options=OPTIONS, recommendation="Q")
    codes = [d.get("code") for d in refused.get("diagnostics", [])]
    assert UNKNOWN_CODE in codes, codes
    assert not refused.get("applied")
