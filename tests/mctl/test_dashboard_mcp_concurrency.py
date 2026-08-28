"""One slow page must not freeze the whole dashboard.

Measured on the live city 2026-08-28 (mc-znfnm), same process, same route,
only concurrency differing:

    /queue alone           1.6s, 1.8s
    /queue during /city   64.9s        <- 36x

`_JsonRpcClient` holds a single `threading.RLock` around every JSON-RPC
exchange (`client.py:157`, taken in `_request`). Every MCP call from every
`ThreadingHTTPServer` worker passes through that one lock, so the dashboard
serves exactly one MCP-backed request at a time, process-wide. A single slow
page is a full outage for every concurrent viewer.

**The lock is correct and must not be removed.** Its comment argues the case
properly: two half-written JSON-RPC frames on one stdin is a corrupt session,
not a slow one. The bug is the *shared pipe*, not the mutual exclusion. The
fix is to give each concurrent caller its own pipe -- a small pool of child
clients, or thread-local clients -- so each pipe still has exactly one writer
and there is nothing left to serialize.

`test_concurrent_calls_overlap` is marked `xfail(strict=True)` on purpose:
it documents the defect without breaking the suite, and the strictness makes
it self-cleaning. Whoever lands the pool/thread-local fix will see it fail as
XPASS, which forces them to delete the marker rather than leave a stale
"known bug" note behind.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_dashboard.client import _JsonRpcClient  # noqa: E402

#: Long enough that serialization is unmistakable, short enough to keep the
#: suite fast. Two overlapping calls take ~DELAY; two serialized calls ~2x.
DELAY = 0.30


class _SlowClient(_JsonRpcClient):
    """A client whose every exchange takes DELAY, recording true concurrency."""

    def __init__(self) -> None:
        super().__init__()
        self.in_flight = 0
        self.max_in_flight = 0
        self._counter_lock = threading.Lock()

    def _exchange(self, message):  # type: ignore[no-untyped-def]
        with self._counter_lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            time.sleep(DELAY)
            return {"jsonrpc": "2.0", "id": message.get("id"), "result": {}}
        finally:
            with self._counter_lock:
                self.in_flight -= 1


def _fire(client: _SlowClient, n: int) -> float:
    """Run n concurrent _request calls; return wall-clock seconds."""
    threads = [
        threading.Thread(target=lambda: client._request("tools/call", {}))
        for _ in range(n)
    ]
    start = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return time.monotonic() - start


# -- control ---------------------------------------------------------------
# Without these, a passing concurrency test could be passing on a client that
# never ran anything at all.


def test_single_call_costs_about_one_delay() -> None:
    client = _SlowClient()
    elapsed = _fire(client, 1)
    assert DELAY <= elapsed < DELAY * 2
    assert client.max_in_flight == 1


def test_exchange_actually_ran() -> None:
    client = _SlowClient()
    _fire(client, 2)
    assert client.max_in_flight >= 1, "the stub never executed; the test is void"


# -- the defect ------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "mc-znfnm: every MCP call serializes on one process-wide RLock over a "
        "single pipe, so concurrent dashboard requests queue instead of "
        "overlapping. Fix by giving each caller its own pipe (client pool or "
        "thread-local clients), NOT by removing the lock. When this XPASSes, "
        "delete this marker."
    ),
)
def test_concurrent_calls_overlap() -> None:
    """Four concurrent calls should cost ~1 delay, not ~4."""
    client = _SlowClient()
    elapsed = _fire(client, 4)
    assert client.max_in_flight > 1, (
        f"calls never overlapped: max_in_flight={client.max_in_flight}"
    )
    assert elapsed < DELAY * 2, f"serialized: {elapsed:.2f}s for 4 concurrent calls"


def test_serialization_is_measurable_today() -> None:
    """Pins the CURRENT behaviour so the regression is visible, not folklore.

    This passes today and must be deleted in the same commit that removes the
    xfail above -- the two assert opposite things by design.
    """
    client = _SlowClient()
    elapsed = _fire(client, 4)
    assert client.max_in_flight == 1, "expected full serialization on one pipe"
    assert elapsed >= DELAY * 3, f"expected ~4 serialized delays, got {elapsed:.2f}s"
