"""#118 — costs_summary: token bucketing + the meta-work ratio, shaped from
injected `.gc/usage.jsonl` reads.

`costs_summary` never shells out itself -- `read(what)` is injected, exactly
like `mctl_core.orders.orders_status` and `mctl_core.queue.queue_status`, so
these tests never touch a live city.

THE LOAD-BEARING ASSERTIONS:
  - Unit is TOKENS (input+output+cache_read+cache_creation), never bead count.
  - `unpriced_count` is an explicit COUNT of facts whose price is unknown --
    never valued at zero, never dropped.
  - The meta-work ratio classifies by RIG PREFIX derived from the `worker`
    field (`<rig>--<agent>` is the sanitized `<rig>/<agent>` session name):
    gascity/gascity-packs/mathcity -> meta; hecke/differential_valuations/
    magma_*/lmfdb/jacobi/homog -> math; anything else (or an unresolvable
    worker) -> its own `unclassified` bucket, never folded into either side.
  - The ratio carries its numerator and denominator alongside the computed
    value, on every path.
  - Three-valued: a failed usage-log read reports `state="unreachable"` with
    every total `None` (never 0 tokens) and `windows` `None` (never `[]`).
  - A genuinely empty (successfully read, no facts) log reports `0`s and `[]`,
    not `None` -- a real measurement, not an absence of one.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.costs import costs_summary  # noqa: E402

DAY1 = int(datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
DAY2 = int(datetime(2026, 8, 21, 9, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)


def _model_fact(worker, *, input_tokens=100, output_tokens=50, cache_read=0, cache_creation=0,
                 unpriced=False, at=DAY1):
    return {
        "kind": "model",
        "worker": worker,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read,
        "cache_creation_tokens": cache_creation,
        "unpriced": unpriced,
        "cost_usd_estimate": 0.0 if unpriced else 1.23,
        "at": at,
    }


def _compute_fact(worker, *, wall_seconds=3600.0, at=DAY1):
    return {"kind": "compute", "worker": worker, "wall_seconds": wall_seconds, "at": at}


def _reader(facts):
    def read(what: str):
        if what == "usage_facts":
            return list(facts)
        raise KeyError(what)

    return read


def _failing_reader(err_message="usage.jsonl unavailable"):
    def read(what: str):
        raise RuntimeError(err_message)

    return read


# ---------------------------------------------------------------------------
# Happy path: token bucketing, worker-hours, unpriced_count
# ---------------------------------------------------------------------------


def test_total_tokens_sums_all_four_token_fields_not_bead_count():
    facts = [_model_fact("hecke--mayor", input_tokens=100, output_tokens=50, cache_read=10, cache_creation=5)]
    out = costs_summary(_reader(facts))
    assert out["state"] == "healthy"
    assert out["total_tokens"] == 165


def test_worker_hours_is_wall_seconds_summed_and_converted():
    facts = [_compute_fact("hecke--mayor", wall_seconds=7200.0)]
    out = costs_summary(_reader(facts))
    assert out["worker_hours"] == 2.0


def test_unpriced_count_is_an_explicit_count_never_zeroed_out():
    facts = [
        _model_fact("hecke--mayor", unpriced=True),
        _model_fact("hecke--mayor", unpriced=True),
        _model_fact("hecke--mayor", unpriced=False),
    ]
    out = costs_summary(_reader(facts))
    assert out["unpriced_count"] == 2


def test_a_genuinely_empty_log_reports_zeros_and_empty_windows_not_none():
    out = costs_summary(_reader([]))
    assert out["state"] == "healthy"
    assert out["total_tokens"] == 0
    assert out["worker_hours"] == 0.0
    assert out["unpriced_count"] == 0
    assert out["windows"] == []
    assert out["diagnostics"] == []


# ---------------------------------------------------------------------------
# The meta-work ratio: rig-prefix classification, numerator/denominator carried
# ---------------------------------------------------------------------------


def test_gascity_and_mathcity_workers_count_as_meta_side():
    facts = [
        _model_fact("gascity--mayor", input_tokens=100, output_tokens=0),
        _model_fact("gascity-packs--worker", input_tokens=50, output_tokens=0),
        _model_fact("mathcity--mayor", input_tokens=25, output_tokens=0),
    ]
    out = costs_summary(_reader(facts))
    assert out["meta_work_ratio"]["numerator"] == 175


def test_math_rig_workers_count_as_math_side():
    facts = [
        _model_fact("hecke--worker", input_tokens=100, output_tokens=0),
        _model_fact("differential_valuations--worker", input_tokens=50, output_tokens=0),
        _model_fact("magma_general--worker", input_tokens=10, output_tokens=0),
        _model_fact("lmfdb--worker", input_tokens=5, output_tokens=0),
        _model_fact("jacobi--worker", input_tokens=5, output_tokens=0),
        _model_fact("homog--worker", input_tokens=5, output_tokens=0),
    ]
    out = costs_summary(_reader(facts))
    assert out["meta_work_ratio"]["denominator"] == 175


def test_ratio_is_numerator_over_denominator():
    facts = [
        _model_fact("gascity--mayor", input_tokens=200, output_tokens=0),
        _model_fact("hecke--worker", input_tokens=100, output_tokens=0),
    ]
    out = costs_summary(_reader(facts))
    ratio = out["meta_work_ratio"]
    assert ratio["numerator"] == 200
    assert ratio["denominator"] == 100
    assert ratio["ratio"] == 2.0


def test_a_rig_matching_neither_list_is_unclassified_not_folded_into_either_side():
    facts = [_model_fact("some_other_rig--worker", input_tokens=100, output_tokens=0)]
    out = costs_summary(_reader(facts))
    assert out["meta_work_ratio"]["numerator"] == 0
    assert out["meta_work_ratio"]["denominator"] == 0
    assert out["unclassified_tokens"] == 100


def test_an_unresolvable_worker_name_is_unclassified_not_fabricated():
    """A worker with no `rig/agent` structure (no `--`) cannot be attributed
    to a side -- it must land in `unclassified`, never guessed into meta or
    math (that would fabricate the ratio, #118 honesty specifics)."""
    facts = [_model_fact("solo-chat-session", input_tokens=100, output_tokens=0)]
    out = costs_summary(_reader(facts))
    assert out["unclassified_tokens"] == 100
    assert out["meta_work_ratio"]["numerator"] == 0
    assert out["meta_work_ratio"]["denominator"] == 0


def test_ratio_is_none_when_denominator_is_zero_never_a_division_by_zero():
    facts = [_model_fact("gascity--mayor", input_tokens=100, output_tokens=0)]
    out = costs_summary(_reader(facts))
    assert out["meta_work_ratio"]["denominator"] == 0
    assert out["meta_work_ratio"]["ratio"] is None


# ---------------------------------------------------------------------------
# Windows: the trend is the alarming view, not the snapshot -- a series, not
# just one number.
# ---------------------------------------------------------------------------


def test_facts_are_bucketed_into_per_day_windows():
    facts = [
        _model_fact("gascity--mayor", input_tokens=100, output_tokens=0, at=DAY1),
        _model_fact("hecke--worker", input_tokens=50, output_tokens=0, at=DAY2),
    ]
    out = costs_summary(_reader(facts))
    windows = out["windows"]
    assert [w["window"] for w in windows] == ["2026-08-20", "2026-08-21"]
    assert windows[0]["meta_tokens"] == 100
    assert windows[1]["math_tokens"] == 50


def test_each_window_carries_its_own_ratio_so_a_trend_is_renderable():
    facts = [
        _model_fact("gascity--mayor", input_tokens=100, output_tokens=0, at=DAY1),
        _model_fact("hecke--worker", input_tokens=100, output_tokens=0, at=DAY1),
        _model_fact("gascity--mayor", input_tokens=300, output_tokens=0, at=DAY2),
        _model_fact("hecke--worker", input_tokens=100, output_tokens=0, at=DAY2),
    ]
    out = costs_summary(_reader(facts))
    windows = {w["window"]: w for w in out["windows"]}
    assert windows["2026-08-20"]["meta_work_ratio"] == 1.0
    assert windows["2026-08-21"]["meta_work_ratio"] == 3.0


def test_a_fact_with_no_timestamp_lands_in_an_unknown_window_not_dropped():
    facts = [_model_fact("gascity--mayor", input_tokens=100, output_tokens=0, at=None)]
    out = costs_summary(_reader(facts))
    assert out["total_tokens"] == 100, "the fact must still be counted in the totals"
    assert [w["window"] for w in out["windows"]] == ["unknown"]


# ---------------------------------------------------------------------------
# Three-valued: a failed read is unreachable, never zero
# ---------------------------------------------------------------------------


def test_a_failed_read_reports_unreachable_with_every_total_null_not_zero():
    out = costs_summary(_failing_reader())
    assert out["state"] == "unreachable"
    assert out["total_tokens"] is None
    assert out["worker_hours"] is None
    assert out["unpriced_count"] is None
    assert out["unclassified_tokens"] is None
    assert out["windows"] is None
    ratio = out["meta_work_ratio"]
    assert ratio["numerator"] is None
    assert ratio["denominator"] is None
    assert ratio["ratio"] is None
    codes = {d["code"] for d in out["diagnostics"]}
    assert "MCOS_USAGE_UNREACHABLE" in codes


def test_the_unreachable_diagnostic_is_a_typed_object_not_a_string():
    out = costs_summary(_failing_reader())
    for diagnostic in out["diagnostics"]:
        assert isinstance(diagnostic, dict)
        assert {"code", "message", "severity"} <= set(diagnostic)


# ---------------------------------------------------------------------------
# Honesty: unresolved-rig attribution is surfaced, not silently absorbed
# ---------------------------------------------------------------------------


def test_unclassified_tokens_present_emits_an_informational_diagnostic():
    facts = [_model_fact("some_other_rig--worker", input_tokens=100, output_tokens=0)]
    out = costs_summary(_reader(facts))
    codes = {d["code"] for d in out["diagnostics"]}
    assert "MCOS_RIG_UNRESOLVED" in codes
    assert out["state"] == "healthy", "unclassified data is not itself a read failure"
