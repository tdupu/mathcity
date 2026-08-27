"""Independent reads should overlap rather than queue behind one another.

The brief detail page makes three independent core calls -- `briefs_show`,
`briefs_options`, `briefs_doctor` -- each of which costs several seconds
against the live store. They were serialized, not because they depend on one
another but because a single stdio client holds a lock around the whole
request/response exchange. Overlapping them is the difference between a page
an operator can triage 182 briefs on and one they cannot.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))


class _InFlight:
    """A concurrency counter shared across a client and its fan-out siblings.

    `fan_out` hands each spec to a SEPARATE client (`clone()` returns a fresh
    object), so a per-instance counter stays at one however much overlap there
    is -- which is why the overlap test used to fall back to a wall-clock bound.
    Sharing one counter across the pool lets the test observe overlap directly.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._live = 0
        self.peak = 0

    def enter(self) -> None:
        with self._lock:
            self._live += 1
            self.peak = max(self.peak, self._live)

    def exit(self) -> None:
        with self._lock:
            self._live -= 1


class _SlowClient:
    """Stands in for the stdio client. A shared `_InFlight` records real overlap.

    `serialize_lock`, when shared across the pool, holds one lock across the
    whole call so only one read runs at a time -- the single-pipe behaviour that
    gives the overlap check its observed failing case (P6.2).
    """

    def __init__(
        self,
        delay: float = 0.05,
        *,
        inflight: "_InFlight | None" = None,
        serialize_lock: "threading.Lock | None" = None,
    ) -> None:
        self.delay = delay
        self.calls: list[str] = []
        self.inflight = inflight or _InFlight()
        self.serialize_lock = serialize_lock
        # Retained for `test_a_single_spec_does_not_pay_for_a_pool`, which reads
        # this instance's own peak on the single-spec path (no pool, no clone).
        self.max_concurrent = 0

    def call(self, name, arguments=None):
        # Serialize (if asked) BEFORE counting in-flight: a thread blocked on the
        # lock is not running, so counting it would inflate the peak.
        if self.serialize_lock is not None:
            self.serialize_lock.acquire()
        self.inflight.enter()
        self.max_concurrent = max(self.max_concurrent, self.inflight._live)
        try:
            time.sleep(self.delay)
            self.calls.append(name)
            return {"tool": name, "arguments": dict(arguments or {})}
        finally:
            self.inflight.exit()
            if self.serialize_lock is not None:
                self.serialize_lock.release()

    def clone(self):
        # type(self) so a subclass double stays itself in the pool; the tracker
        # and serialization lock are SHARED so the pool measures one truth.
        return type(self)(
            self.delay, inflight=self.inflight, serialize_lock=self.serialize_lock
        )


def test_fanout_returns_results_in_request_order():
    """Order of results must track the request list, not completion order."""
    from mctl_dashboard.fanout import fan_out

    client = _SlowClient()
    specs = [("briefs_show", {"n": 1}), ("briefs_options", {"n": 2}), ("briefs_doctor", {"n": 3})]
    results = fan_out(client, specs)

    assert [r["tool"] for r in results] == ["briefs_show", "briefs_options", "briefs_doctor"]
    assert [r["arguments"]["n"] for r in results] == [1, 2, 3]


def test_fanout_actually_overlaps():
    """Three reads must genuinely OVERLAP -- asserted as overlap, not wall clock.

    The previous form asserted `elapsed < 0.12s` for three 50ms calls. That is a
    wall-clock threshold, and under CPU contention the `ThreadPoolExecutor`
    threads cannot be scheduled promptly, so overlapping sleeps elapse
    near-serially and the bound fails though the fan-out is correct -- the P6.3
    anti-pattern ("a deadline is not a verdict"). This measures the thing itself:
    a concurrency counter shared across the sibling pool (each `clone()` shares
    it), which rises above one only when calls truly run at the same time.
    """
    from mctl_dashboard.fanout import fan_out

    tracker = _InFlight()
    client = _SlowClient(delay=0.05, inflight=tracker)
    results = fan_out(
        client, [("briefs_show", {}), ("briefs_options", {}), ("briefs_doctor", {})]
    )

    assert [r["tool"] for r in results] == ["briefs_show", "briefs_options", "briefs_doctor"]
    assert tracker.peak >= 2, f"calls did not overlap: peak in flight was {tracker.peak}"


def test_a_serialized_fanout_would_fail_the_overlap_check():
    """The observed failing case (P6.2): one shared lock => peak of exactly 1.

    A single-pipe client serializes every call; the shared in-flight counter
    then never exceeds one, which is the state `test_fanout_actually_overlaps`
    exists to reject. Without this, `peak >= 2` would be a check with no
    demonstrated way to fail.
    """
    from mctl_dashboard.fanout import fan_out

    tracker = _InFlight()
    client = _SlowClient(delay=0.05, inflight=tracker, serialize_lock=threading.Lock())
    fan_out(client, [("briefs_show", {}), ("briefs_options", {}), ("briefs_doctor", {})])

    assert tracker.peak == 1


def test_a_failing_call_does_not_lose_the_others():
    """One bad read must not blank the page -- the exception rides along."""
    from mctl_dashboard.fanout import fan_out

    class _Flaky(_SlowClient):
        def call(self, name, arguments=None):
            if name == "briefs_doctor":
                raise RuntimeError("boom")
            return super().call(name, arguments)

    results = fan_out(
        _Flaky(), [("briefs_show", {}), ("briefs_doctor", {}), ("briefs_options", {})]
    )
    assert results[0]["tool"] == "briefs_show"
    assert isinstance(results[1], RuntimeError)
    assert results[2]["tool"] == "briefs_options"


def test_a_single_spec_does_not_pay_for_a_pool():
    """One call should go straight down the primary client."""
    from mctl_dashboard.fanout import fan_out

    client = _SlowClient()
    results = fan_out(client, [("briefs_show", {})])
    assert results[0]["tool"] == "briefs_show"
    assert client.max_concurrent == 1
