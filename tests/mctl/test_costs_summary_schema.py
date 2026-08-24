"""#118/#203 — costs_summary must satisfy its DECLARED schema on every path.

Modeled on test_orders_status_schema.py / test_queue_status_schema.py: these
tests reproduce the server's own post-handler step (setdefault diagnostics,
inject trace_id) and then run the exact `schema_errors` check the dispatcher
runs, against `costs_summary`'s declared `output_schema` -- on the happy path
AND the failed-read (unreachable) path, since the unreachable path returns an
entirely different shape (every total `None`) that a schema built only
against the happy path would not catch.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import mcp_server  # noqa: E402
from mctl_core.costs import costs_summary  # noqa: E402
from mctl_core.schemas import schema_errors  # noqa: E402


def _output_schema() -> dict:
    tool = next(t for t in mcp_server.TOOLS if t.name == "costs_summary")
    return tool.output_schema


def _as_served(payload: dict) -> dict:
    payload.setdefault("diagnostics", [])
    payload["trace_id"] = "trace-fixture"
    return payload


def _reader(facts=()):
    def read(what: str):
        if what == "usage_facts":
            return list(facts)
        raise KeyError(what)

    return read


def _failing_reader():
    def read(what: str):
        raise RuntimeError("usage.jsonl unavailable")

    return read


MODEL_FACT = {
    "kind": "model",
    "worker": "hecke--mayor",
    "input_tokens": 100,
    "output_tokens": 50,
    "cache_read_tokens": 0,
    "cache_creation_tokens": 0,
    "unpriced": False,
    "cost_usd_estimate": 1.23,
    "at": 1755691200000,
}

UNPRICED_FACT = {
    "kind": "model",
    "worker": "gascity--mayor",
    "input_tokens": 10,
    "output_tokens": 5,
    "cache_read_tokens": 0,
    "cache_creation_tokens": 0,
    "unpriced": True,
    "cost_usd_estimate": 0.0,
    "at": 1755691200000,
}

COMPUTE_FACT = {"kind": "compute", "worker": "hecke--mayor", "wall_seconds": 1800.0, "at": 1755691200000}


def test_happy_path_response_satisfies_declared_schema():
    payload = _as_served(costs_summary(_reader([MODEL_FACT, UNPRICED_FACT, COMPUTE_FACT])))
    violations = schema_errors(payload, _output_schema())
    assert violations == [], f"costs_summary happy-path response violates its declared schema: {violations}"


def test_empty_log_response_satisfies_declared_schema():
    payload = _as_served(costs_summary(_reader([])))
    violations = schema_errors(payload, _output_schema())
    assert violations == [], f"costs_summary empty-log response violates its declared schema: {violations}"


def test_unreachable_response_satisfies_declared_schema():
    payload = _as_served(costs_summary(_failing_reader()))
    violations = schema_errors(payload, _output_schema())
    assert violations == [], f"costs_summary unreachable response violates its declared schema: {violations}"
    assert payload["diagnostics"], "the unreachable path must emit a diagnostic"
    assert all(
        isinstance(d, dict) and {"code", "message", "severity"} <= set(d)
        for d in payload["diagnostics"]
    )
