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


class _SlowClient:
    """Stands in for the stdio client: one lock, one call at a time."""

    def __init__(self, delay: float = 0.05) -> None:
        self.delay = delay
        self.lock = threading.Lock()
        self.calls: list[str] = []
        self.max_concurrent = 0
        self._live = 0
        self._guard = threading.Lock()

    def call(self, name, arguments=None):
        with self._guard:
            self._live += 1
            self.max_concurrent = max(self.max_concurrent, self._live)
        try:
            with self.lock:
                time.sleep(self.delay)
            self.calls.append(name)
            return {"tool": name, "arguments": dict(arguments or {})}
        finally:
            with self._guard:
                self._live -= 1

    def clone(self):
        # type(self) so a subclass double stays itself in the pool.
        return type(self)(self.delay)


def test_fanout_returns_results_in_request_order():
    """Order of results must track the request list, not completion order."""
    from mctl_dashboard.fanout import fan_out

    client = _SlowClient()
    specs = [("briefs_show", {"n": 1}), ("briefs_options", {"n": 2}), ("briefs_doctor", {"n": 3})]
    results = fan_out(client, specs)

    assert [r["tool"] for r in results] == ["briefs_show", "briefs_options", "briefs_doctor"]
    assert [r["arguments"]["n"] for r in results] == [1, 2, 3]


def test_fanout_actually_overlaps():
    """Three 50ms calls should finish in well under the 150ms serial cost."""
    from mctl_dashboard.fanout import fan_out

    client = _SlowClient(delay=0.05)
    started = time.perf_counter()
    fan_out(client, [("briefs_show", {}), ("briefs_options", {}), ("briefs_doctor", {})])
    elapsed = time.perf_counter() - started

    assert elapsed < 0.12, f"calls did not overlap: {elapsed:.3f}s"


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
