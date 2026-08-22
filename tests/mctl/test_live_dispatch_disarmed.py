"""A disarmed dispatch must say so, not impersonate a dry run.

`work_dispatch(dry_run=false)` against an MCP server without
`MCTL_ENABLE_LIVE_DISPATCH` returned `applied: false`, a complete effect plan with
`preflight_result: passed`, a trace id, and **an empty diagnostics list** -- a
response substantively identical to a dry run the caller did not ask for. Nothing
was slung and nothing was said, so every dispatch in a dogfood run would be
recorded as dispatched and never run.

The refusal itself is correct and stays: writing provenance would flip readiness to
`dispatched` and block every future attempt. What was wrong is the silence.

Both neighbouring refusals in `apply_dispatch_plan` already name themselves --
`MCTL_CONTROL_PLANE_NOT_ACTIVE` and `MWRK_DISPATCH_COMMAND_FAILED`, each with a
`suggested_next_command`. The disarmed branch was the only one that refused
silently.

This does NOT arm dispatch. Arming is a separate, security-relevant decision that
the issue explicitly says must not land alone.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import work as work_mod


def test_a_disarmed_dispatch_is_not_silent():
    """The whole bug: the payload carried no way to tell a refusal from a dry run."""
    payload = work_mod.dispatch_disarmed_payload(_ctx(), _plan())

    codes = [d.get("code") for d in payload.get("diagnostics", [])]
    assert "MCTL_LIVE_DISPATCH_DISARMED" in codes, (
        f"a refused dispatch reported no diagnostic at all: {codes}"
    )


def test_the_diagnostic_is_blocking_severity():
    """INFO would be read past by exactly the automation this exists to stop."""
    payload = work_mod.dispatch_disarmed_payload(_ctx(), _plan())

    diag = _disarmed(payload)
    assert diag["severity"] in {"ERROR", "FATAL"}, (
        f"severity {diag['severity']} does not stop a caller treating this as success"
    )


def test_the_diagnostic_names_the_way_out():
    """A refusal a caller cannot act on is only marginally better than silence."""
    diag = _disarmed(work_mod.dispatch_disarmed_payload(_ctx(), _plan()))

    facts = diag.get("facts") or {}
    nxt = diag.get("suggested_next_command") or facts.get("suggested_next_command") or ""
    assert "MCTL_ENABLE_LIVE_DISPATCH" in nxt, (
        f"the diagnostic does not name the variable that would arm it: {nxt!r}"
    )


def test_it_still_refuses_and_still_reports_not_applied():
    """The kill switch is the point. Making it loud must not make it permissive."""
    payload = work_mod.dispatch_disarmed_payload(_ctx(), _plan())

    assert payload["applied"] is False, "a disarmed dispatch must never report applied"
    assert payload["effect_plan"], "the plan is still useful to a caller inspecting it"


# --- helpers ---------------------------------------------------------------


class _Ctx:
    """The fields `_diagnostic` reads. Nothing else is touched."""

    city_root = Path("/city")
    rig_root = Path("/city/rig")
    rig_id = "rig"
    trace_id = "test-trace"


def _ctx():
    return _Ctx()


class _Plan:
    """The minimum surface `dispatch_dry_run_payload` reads."""

    trace_id = "test-trace"
    target_brief_id = "mc-test"
    bead_id = "mc-test"

    def to_dict(self):
        return {"operation": "work.dispatch", "preflight_result": "passed"}


def _plan():
    return _Plan()


def _disarmed(payload):
    for d in payload.get("diagnostics", []):
        if d.get("code") == "MCTL_LIVE_DISPATCH_DISARMED":
            return d
    raise AssertionError("no MCTL_LIVE_DISPATCH_DISARMED diagnostic in payload")


# --- the reported surface -------------------------------------------------
#
# The unit tests above cover the payload builder. The defect was reported
# against the MCP tool, so this exercises that path end to end: an MCP server
# with no MCTL_ENABLE_LIVE_DISPATCH, called with dry_run false.


def test_the_mcp_surface_reports_the_refusal(tmp_path: Path):
    """The exact call from the issue: work_dispatch, dry_run false, disarmed."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_mcp_server import call, server, work_fixture

    city_root, rig_root = work_fixture(tmp_path)

    structured = call(
        server(city_root, rig_root),
        "work_dispatch",
        {"brief_id": "mc-approved", "dry_run": False},
    )["result"]["structuredContent"]

    codes = [d.get("code") for d in structured.get("diagnostics", [])]
    assert "MCTL_LIVE_DISPATCH_DISARMED" in codes, (
        "the MCP response still cannot be told apart from a dry run: "
        f"applied={structured.get('applied')} diagnostics={codes}"
    )
    assert structured["applied"] is False, "a disarmed dispatch must not report applied"
