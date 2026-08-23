"""`#159`: a `gc` timeout was charged to Dolt.

`city_health` reported `data_plane: "unreachable"` while Dolt answered in 113ms
with 18 databases. What was broken was `gc`, hanging on "Starting bead store"
(`#138`). Every one of 17 rigs corroborated the wrong conclusion, so a reader
who trusted the verdict went looking in the wrong place with maximum confidence.

The root cause is one line:

    if dolt_probe.outcome != PROBE_SUCCEEDED:
        data_plane = DATA_PLANE_UNREACHABLE

**Every way of not succeeding became a statement about the subject.** And the
collapse runs one level deeper than the issue describes: `PROBE_REFUSED` was
carrying two incompatible facts.

    gc answered, server.reachable=false   -> a MEASUREMENT: Dolt is down
    gc timed out / errored                -> NO measurement was taken

Only the first is a fact about the data plane. The second is a fact about the
probe, and reporting it as `unreachable` is the inverse of the failure `#114`
built this module to prevent.

So a probe *succeeds* when `gc` answers — that is what a probe is for — and
what it answers decides the data plane. A probe that never answered leaves the
data plane **unknown**, which is a third thing and must not be spelled as
either of the other two.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_core import health


def _probe(outcome: str, detail: str = ""):
    return health.ProbeResult(
        name="dolt_health",
        outcome=outcome,
        timeout_seconds=30.0,
        latency_ms=None,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# the distinction
# ---------------------------------------------------------------------------


def test_a_timed_out_probe_leaves_the_data_plane_unknown():
    """The #159 case. We never asked; we must not answer."""
    assert health.data_plane_for(
        _probe(health.PROBE_TIMED_OUT, "gc did not answer within 30.0s"), {}
    ) == health.DATA_PLANE_UNKNOWN


def test_a_probe_that_answered_dolt_is_down_reports_unreachable():
    """The measurement that `unreachable` is FOR. It must survive the fix."""
    assert health.data_plane_for(
        _probe(health.PROBE_REFUSED, "gc dolt health reports server.reachable=false"), {}
    ) == health.DATA_PLANE_UNREACHABLE


def test_a_gc_error_is_unknown_not_unreachable():
    """`PROBE_REFUSED` carried both facts. A gc that failed for its own reasons
    measured nothing about Dolt."""
    assert health.data_plane_for(
        _probe(health.PROBE_REFUSED, "gc dolt health exited 1"), {}
    ) == health.DATA_PLANE_UNKNOWN


def test_a_successful_probe_still_reports_healthy():
    assert health.data_plane_for(_probe(health.PROBE_SUCCEEDED, "answered"), {}) == health.DATA_PLANE_HEALTHY


def test_quarantine_still_wins_over_healthy():
    assert health.data_plane_for(
        _probe(health.PROBE_SUCCEEDED, "answered"), {"hq": "quarantined"}
    ) == health.DATA_PLANE_QUARANTINED


# ---------------------------------------------------------------------------
# and the per-rig rows must not corroborate a conclusion nobody measured
# ---------------------------------------------------------------------------


def test_per_rig_state_for_a_failed_probe_is_unknown():
    """17 rigs all saying "unreachable" is what made the wrong answer
    persuasive. They were all repeating one probe's silence."""
    assert health.per_rig_state_for(_probe(health.PROBE_TIMED_OUT, "no answer")) == "unknown"


def test_per_rig_state_when_dolt_really_is_down_is_unreachable():
    assert health.per_rig_state_for(
        _probe(health.PROBE_REFUSED, "gc dolt health reports server.reachable=false")
    ) == "unreachable"
