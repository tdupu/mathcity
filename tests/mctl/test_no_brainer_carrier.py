"""briefs_relay_adjudication carries the no-brainer signal as typed metadata (#208 Part 2).

The classifier signal "this reached me and should not have" had no typed write
path: the dashboard folded it into the verdict reason behind a marker string,
and the MCP tool had no parameter at all, so a typed adjudication lost it. #76
Field 7 defines it as `no_brainer` (bool) + `no_brainer_reason` on the bead.

This file pins the write path end to end: the tool exposes the params, the plan
writes the two metadata keys onto the bead, and an unticked flag writes neither
(absent means absent). The dashboard form now maps its checkbox to the params
rather than the marker-string stopgap it replaces.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_mcp_server import call, server, work_fixture

from mctl_core import effects


def _brief(city, rig):
    return call(
        server(city, rig),
        "decisions_to_briefs",
        {"decision": "d", "source_bead_id": "source-revise", "dry_run": False},
    )["result"]["structuredContent"]["brief_id"]


def _bead_metadata(effect_plan, brief_id):
    for entry in effect_plan.get("bead_updates") or ():
        if entry.get("id") == brief_id:
            return entry.get("metadata") or {}
    return {}


class TestTheParametersExist:
    def test_plan_adjudication_accepts_the_no_brainer_pair(self):
        params = inspect.signature(effects.plan_adjudication).parameters
        assert "no_brainer" in params
        assert "no_brainer_reason" in params

    def test_they_are_optional(self):
        params = inspect.signature(effects.plan_adjudication).parameters
        assert params["no_brainer"].default in (False, None)
        assert params["no_brainer_reason"].default is None

    def test_the_tool_exposes_them_and_does_not_require_them(self):
        from mctl_core.mcp_server import TOOLS_BY_NAME

        schema = TOOLS_BY_NAME["briefs_relay_adjudication"].input_schema
        assert "no_brainer" in schema["properties"]
        assert "no_brainer_reason" in schema["properties"]
        assert "no_brainer" not in schema.get("required", [])
        assert "no_brainer_reason" not in schema.get("required", [])


class TestTheSignalReachesTheBead:
    def test_a_ticked_no_brainer_writes_both_keys(self, tmp_path: Path):
        city, rig = work_fixture(tmp_path)
        brief_id = _brief(city, rig)

        plan = call(
            server(city, rig),
            "briefs_relay_adjudication",
            {
                "brief_id": brief_id,
                "verdict": "revise",
                "reason": "needs fields",
                "no_brainer": True,
                "no_brainer_reason": "classifier should have caught it",
                "dry_run": True,
            },
        )["result"]["structuredContent"]["effect_plan"]

        metadata = _bead_metadata(plan, brief_id)
        assert metadata.get("no_brainer") == "true", metadata
        assert metadata.get("no_brainer_reason") == "classifier should have caught it", metadata

    def test_an_unticked_no_brainer_writes_neither_key(self, tmp_path: Path):
        """Absent means absent -- not a false written on every ordinary verdict."""
        city, rig = work_fixture(tmp_path)
        brief_id = _brief(city, rig)

        plan = call(
            server(city, rig),
            "briefs_relay_adjudication",
            {"brief_id": brief_id, "verdict": "approve", "reason": "r", "dry_run": True},
        )["result"]["structuredContent"]["effect_plan"]

        metadata = _bead_metadata(plan, brief_id)
        assert "no_brainer" not in metadata, metadata
        assert "no_brainer_reason" not in metadata, metadata

    def test_the_reason_is_not_polluted_by_the_marker_string(self, tmp_path: Path):
        """The typed keys REPLACE the reason-string stopgap: the verdict reason
        stays the operator's reason, verbatim, with no folded-in marker."""
        city, rig = work_fixture(tmp_path)
        brief_id = _brief(city, rig)

        plan = call(
            server(city, rig),
            "briefs_relay_adjudication",
            {
                "brief_id": brief_id,
                "verdict": "revise",
                "reason": "needs fields",
                "no_brainer": True,
                "dry_run": True,
            },
        )["result"]["structuredContent"]["effect_plan"]

        metadata = _bead_metadata(plan, brief_id)
        assert metadata.get("verdict_reason") == "needs fields", metadata
        assert "no-brainer" not in str(metadata.get("verdict_reason") or "")
