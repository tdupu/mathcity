"""#118 — costs_summary must be reachable as a typed tool.

Modeled on test_queue_tool.py. The load-bearing assertion is that the
meta-work ratio's numerator/denominator are part of the DECLARED contract --
a tool that computes them but omits them from the schema would satisfy a
naive "is it registered" check while still hiding the headline measure.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))


def _spec(name: str):
    from mctl_core.mcp_server import TOOLS

    return next((t for t in TOOLS if t.name == name), None)


def test_costs_summary_is_a_registered_tool():
    assert _spec("costs_summary") is not None, "no typed tool exposes the costs projection"


def test_the_tool_declares_the_ratio_numerator_and_denominator_in_its_output_schema():
    spec = _spec("costs_summary")
    schema = repr(spec.output_schema)
    for field in ("numerator", "denominator", "ratio"):
        assert field in schema, f"meta_work_ratio.{field} is not in the declared output"


def test_the_tool_declares_unpriced_count_and_unclassified_tokens():
    spec = _spec("costs_summary")
    schema = repr(spec.output_schema)
    assert "unpriced_count" in schema
    assert "unclassified_tokens" in schema


def test_the_tool_declares_a_windows_series_for_the_trend():
    spec = _spec("costs_summary")
    schema = repr(spec.output_schema)
    assert "windows" in schema


def test_the_tool_reports_the_ratio_for_classified_workers():
    from mctl_core.costs import costs_summary

    def read(what: str):
        if what == "usage_facts":
            return [
                {
                    "kind": "model",
                    "worker": "gascity--mayor",
                    "input_tokens": 200,
                    "output_tokens": 0,
                    "cache_read_tokens": 0,
                    "cache_creation_tokens": 0,
                    "unpriced": False,
                    "at": 1755691200000,
                },
                {
                    "kind": "model",
                    "worker": "hecke--worker",
                    "input_tokens": 100,
                    "output_tokens": 0,
                    "cache_read_tokens": 0,
                    "cache_creation_tokens": 0,
                    "unpriced": False,
                    "at": 1755691200000,
                },
            ]
        raise KeyError(what)

    out = costs_summary(read)
    assert out["meta_work_ratio"]["ratio"] == 2.0


def test_the_dashboard_allowlist_names_costs_summary():
    """`ALLOWED_TOOLS` is spelled out, never derived -- so it must be updated."""
    from mctl_dashboard.client import ALLOWED_TOOLS

    assert "costs_summary" in ALLOWED_TOOLS
