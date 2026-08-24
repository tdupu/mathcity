"""#113/#203 — queue_status must satisfy its DECLARED schema on every path.

Modeled on test_orders_status_schema.py: `orders_status` shipped once with a
`diagnostics: list[str]` bug that only a schema-validating test against the
real served envelope would catch (a plain "does it return a dict" test does
not). These tests reproduce the server's own post-handler step (setdefault
diagnostics, inject trace_id) and then run the exact `schema_errors` check the
dispatcher runs, against `queue_status`'s declared `output_schema` -- on the
happy path, the total-unreachable path, AND each of the three partial-failure
paths (since each nulls a different subset of populations and each is a
distinct shape the schema must accept).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import mcp_server  # noqa: E402
from mctl_core.queue import queue_status  # noqa: E402
from mctl_core.schemas import schema_errors  # noqa: E402


def _output_schema() -> dict:
    tool = next(t for t in mcp_server.TOOLS if t.name == "queue_status")
    return tool.output_schema


def _as_served(payload: dict) -> dict:
    payload.setdefault("diagnostics", [])
    payload["trace_id"] = "trace-fixture"
    return payload


def _reader(**overrides):
    values = {
        "ready_explain": {"ready": [], "blocked": []},
        "unclaimed": [],
        "deferred": [],
        "routed_ids": set(),
    }
    fail = overrides.pop("fail", ())
    values.update(overrides)

    def read(what: str):
        if what in fail:
            raise RuntimeError(f"bd {what} unavailable")
        return values[what]

    return read


READY_BEAD = {"id": "mc-1", "title": "Ready", "created_at": "2026-08-20T00:00:00Z", "updated_at": "2026-08-20T00:00:00Z", "priority": 1}
BLOCKED_BEAD = {
    "id": "mc-2", "title": "Blocked", "created_at": "2026-08-20T00:00:00Z", "updated_at": "2026-08-20T00:00:00Z",
    "blocked_by": [{"id": "mc-9", "title": "Dep"}],
}
DEFERRED_BEAD = {"id": "mc-3", "title": "Parked", "defer_until": "2026-09-01T00:00:00Z"}


def test_happy_path_response_satisfies_declared_schema():
    payload = _as_served(
        queue_status(
            _reader(
                ready_explain={"ready": [READY_BEAD], "blocked": [BLOCKED_BEAD]},
                unclaimed=[READY_BEAD],
                deferred=[DEFERRED_BEAD],
                routed_ids={"mc-5"},
            )
        )
    )
    violations = schema_errors(payload, _output_schema())
    assert violations == [], f"queue_status happy-path response violates its declared schema: {violations}"
    assert payload["next_up_is_prediction"] is True


def test_unreachable_core_read_response_satisfies_declared_schema():
    payload = _as_served(queue_status(_reader(fail=("ready_explain",))))
    violations = schema_errors(payload, _output_schema())
    assert violations == [], f"queue_status unreachable response violates its declared schema: {violations}"
    assert payload["diagnostics"], "the unreachable path must emit a diagnostic"
    assert all(
        isinstance(d, dict) and {"code", "message", "severity"} <= set(d)
        for d in payload["diagnostics"]
    )


def test_failed_deferred_read_response_satisfies_declared_schema():
    payload = _as_served(
        queue_status(_reader(ready_explain={"ready": [READY_BEAD], "blocked": []}, fail=("deferred",)))
    )
    violations = schema_errors(payload, _output_schema())
    assert violations == [], f"queue_status degraded (deferred) response violates its declared schema: {violations}"


def test_failed_unclaimed_read_response_satisfies_declared_schema():
    payload = _as_served(
        queue_status(_reader(ready_explain={"ready": [], "blocked": [BLOCKED_BEAD]}, fail=("unclaimed",)))
    )
    violations = schema_errors(payload, _output_schema())
    assert violations == [], f"queue_status degraded (unclaimed) response violates its declared schema: {violations}"


def test_failed_routed_ids_read_response_satisfies_declared_schema():
    payload = _as_served(
        queue_status(
            _reader(
                ready_explain={"ready": [READY_BEAD], "blocked": []},
                unclaimed=[READY_BEAD],
                fail=("routed_ids",),
            )
        )
    )
    violations = schema_errors(payload, _output_schema())
    assert violations == [], f"queue_status degraded (routed_ids) response violates its declared schema: {violations}"
