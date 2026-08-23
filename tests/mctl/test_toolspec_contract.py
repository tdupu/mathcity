"""#194 follow-up: the SERVED SPEC must not advertise the deleted contract.

`99a1c24` fixed the BEHAVIOUR -- `decisions_to_briefs` stopped stamping
`verdict="approve"` and now deposits the brief UNDECIDED. It did not touch the
ToolSpec, and a docstring-only follow-up did not either. So the tool stopped
adjudicating while its own title, description and parameter docs kept telling
callers it files "an already-made decision" as "a dispatchable brief".

That is worse than stale prose. **A caller -- human or agent -- decides whether and
how to invoke a tool from its SPEC, not from its handler.** Leaving the spec intact
instructs every caller toward exactly the behaviour that was deliberately removed,
and it is the same ambiguity that caused the original bug:

    decisions ALREADY MADE -> briefs   ==> a verdict is required
    decisions TO BE MADE   -> briefs   ==> no verdict exists yet

Asserted against the served `tools/list` payload rather than the source text,
because `tools/list` is what a caller actually receives. A test reading the source
would pass on a spec that never reaches anyone.

Kept in its own file rather than appended to `test_decisions_to_briefs_tool.py`:
that file tests the HANDLER's behaviour, this one tests the CONTRACT the surface
advertises. They fail for different reasons and a reader should not have to
disentangle them.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_mcp_server import server, work_fixture


def _served_spec(instance, name: str) -> dict:
    """The spec as a CALLER receives it, not as the source declares it."""
    response = instance.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    for tool in response["result"]["tools"]:
        if tool["name"] == name:
            return tool
    served = [t["name"] for t in response["result"]["tools"]]
    raise AssertionError(f"{name} is not served at all: {served}")


def test_the_served_spec_does_not_advertise_the_deleted_contract(tmp_path: Path):
    """It must not tell callers to supply a decision already made."""
    spec = _served_spec(server(*work_fixture(tmp_path)), "decisions_to_briefs")

    prose = " ".join([spec.get("title", ""), spec.get("description", "")]).lower()

    assert "already-made" not in prose and "already made" not in prose, (
        "the served spec still advertises the DELETED contract -- it tells callers "
        f"this files a decision already made. title+description: {prose!r}"
    )

    decision_doc = str(
        spec["inputSchema"]["properties"]["decision"].get("description", "")
    ).lower()
    assert "as made" not in decision_doc, (
        "the `decision` parameter still reads 'The decision, as made', which "
        "instructs the caller to supply an ANSWER. It carries the QUESTION. "
        f"got: {decision_doc!r}"
    )


def test_the_served_spec_states_the_undecided_contract(tmp_path: Path):
    """Absence of the lie is not enough -- it must state what the tool now does.

    Removing the false claim without asserting the true one leaves a caller unable
    to distinguish a correct undecided deposit from a failure to adjudicate. That
    is the same distinction the handler tests turn on.
    """
    spec = _served_spec(server(*work_fixture(tmp_path)), "decisions_to_briefs")
    prose = " ".join([spec.get("title", ""), spec.get("description", "")]).lower()

    assert "undecided" in prose, (
        "the spec never says the brief is deposited UNDECIDED, which is the whole "
        f"of the new contract. got: {prose!r}"
    )
    assert "not adjudicate" in prose, (
        f"the spec never says the tool does NOT adjudicate. got: {prose!r}"
    )


def test_decision_remains_required_and_that_is_correct(tmp_path: Path):
    """`decision` is REQUIRED, and it should stay that way. Guard against overcorrection.

    It was reported as "the killer -- a structurally required field forcing the
    caller to supply a verdict." That reading is wrong, and acting on it would
    break the tool: `decision` carries the QUESTION TEXT, not an answer. The handler
    uses it as the brief body and as the default title. A brief with no question is
    not a brief.

    So the fix is the DESCRIPTION, not the requirement. This test exists so a later
    reader acting on that report does not remove it.
    """
    spec = _served_spec(server(*work_fixture(tmp_path)), "decisions_to_briefs")
    required = spec["inputSchema"].get("required", [])

    assert "decision" in required, (
        "`decision` was removed from required. It carries the question text, not a "
        "verdict -- a brief with no question is not a brief. If the intent was to "
        "stop the tool recording answers, that was fixed in the handler (99a1c24) "
        "and in the parameter description, not here."
    )
    assert "source_bead_id" in required, "a brief needs a source dependency (B2.1)"
