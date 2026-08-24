"""#115 -- molecules_show's served output must satisfy its declared schema.

Mirrors `test_orders_status_schema.py` (#203): every MCP response is validated
against the tool's declared `output_schema` by the dispatcher, and a shape the
handler can genuinely produce but the schema forbids dies FATAL
`MCTL_MCP_OUTPUT_SCHEMA_VIOLATION` on exactly the path a happy-path fixture
never exercises. These tests run `build_molecule`/`build_molecules` directly
(no live store, no subprocess) across the three `is_complete` states this
issue adds, plus the pre-existing failure paths, and check the served
envelope against `mcp_server.TOOLS`'s declared schema for each tool.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import mcp_server  # noqa: E402
from mctl_core.beads import Bead  # noqa: E402
from mctl_core.molecules import build_molecule, build_molecules  # noqa: E402
from mctl_core.schemas import schema_errors  # noqa: E402


def _output_schema(tool_name: str) -> dict:
    tool = next(t for t in mcp_server.TOOLS if t.name == tool_name)
    return tool.output_schema


def _as_served(payload: dict) -> dict:
    payload.setdefault("diagnostics", [])
    payload["trace_id"] = "trace-fixture"
    return payload


def _envelope(report) -> dict:
    """The same shape `_handle_molecules_list`/`_handle_molecules_show` build,
    minus `ctx.warnings` (empty for every fixture context these tests use)."""
    return _as_served(
        {"diagnostics": [d.to_dict() for d in report.diagnostics], **report.to_dict()}
    )


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


ROOT = _bead("gsp-root1", "build-basic-briefed", {"gc.kind": "workflow"})


def _fixture(tmp_path: Path, beads: list[Bead]) -> Path:
    path = tmp_path / "beads.jsonl"
    path.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": b.id,
                    "title": b.title,
                    "status": b.status,
                    "issue_type": b.issue_type,
                    "labels": [],
                    "created_at": b.created_at,
                    "updated_at": b.updated_at,
                    "metadata": dict(b.raw.get("metadata") or {}),
                }
            )
            for b in beads
        )
        + "\n"
    )
    return path


def test_a_step_with_no_declaration_validates(tmp_path):
    step = _bead("gsp-s1", metadata={"gc.kind": "workflow-finalize", "gc.root_bead_id": ROOT.id})
    fixture = _fixture(tmp_path, [ROOT, step])
    report = build_molecule(tmp_path, ROOT.id, fixture_path=fixture)
    payload = _envelope(report)
    violations = schema_errors(payload, _output_schema("molecules_show"))
    assert violations == [], violations
    assert payload["molecules"][0]["steps"][0]["is_complete"] == "unknown"


def test_a_step_declared_complete_validates(tmp_path):
    step = _bead(
        "gsp-s2",
        metadata={
            "gc.kind": "workflow-finalize",
            "gc.root_bead_id": ROOT.id,
            "gc.expected_artifacts.v1": '["/a/x.md"]',
            "gc.build.x": "/a/x.md",
        },
    )
    fixture = _fixture(tmp_path, [ROOT, step])
    report = build_molecule(tmp_path, ROOT.id, fixture_path=fixture)
    payload = _envelope(report)
    violations = schema_errors(payload, _output_schema("molecules_show"))
    assert violations == [], violations
    assert payload["molecules"][0]["steps"][0]["is_complete"] == "complete"


def test_a_step_declared_incomplete_validates(tmp_path):
    step = _bead(
        "gsp-s3",
        metadata={
            "gc.kind": "workflow-finalize",
            "gc.root_bead_id": ROOT.id,
            "gc.expected_artifacts.v1": '["/a/x.md", "/a/y.md"]',
            "gc.build.x": "/a/x.md",
        },
    )
    fixture = _fixture(tmp_path, [ROOT, step])
    report = build_molecule(tmp_path, ROOT.id, fixture_path=fixture)
    payload = _envelope(report)
    violations = schema_errors(payload, _output_schema("molecules_show"))
    assert violations == [], violations
    assert payload["molecules"][0]["steps"][0]["is_complete"] == "incomplete"


def test_a_malformed_declaration_validates_and_reads_unknown(tmp_path):
    step = _bead(
        "gsp-s4",
        metadata={
            "gc.kind": "workflow-finalize",
            "gc.root_bead_id": ROOT.id,
            "gc.expected_artifacts.v1": "not json",
        },
    )
    fixture = _fixture(tmp_path, [ROOT, step])
    report = build_molecule(tmp_path, ROOT.id, fixture_path=fixture)
    payload = _envelope(report)
    violations = schema_errors(payload, _output_schema("molecules_show"))
    assert violations == [], violations
    assert payload["molecules"][0]["steps"][0]["is_complete"] == "unknown"


def test_the_no_such_id_diagnostic_path_still_validates(tmp_path):
    fixture = _fixture(tmp_path, [ROOT])
    report = build_molecule(tmp_path, "nope-123", fixture_path=fixture)
    payload = _envelope(report)
    violations = schema_errors(payload, _output_schema("molecules_show"))
    assert violations == [], violations


def test_molecules_list_with_steps_validates(tmp_path):
    step = _bead(
        "gsp-s5",
        metadata={
            "gc.kind": "workflow-finalize",
            "gc.root_bead_id": ROOT.id,
            "gc.expected_artifacts.v1": '["/a/x.md"]',
        },
    )
    fixture = _fixture(tmp_path, [ROOT, step])
    report = build_molecules(tmp_path, fixture_path=fixture, with_steps=True)
    payload = _envelope(report)
    violations = schema_errors(payload, _output_schema("molecules_list"))
    assert violations == [], violations
