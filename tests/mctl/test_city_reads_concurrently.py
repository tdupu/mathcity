"""The city page waited for three independent reads in sequence.

Measured against the live city on `5c37a2e`:

    fleet_sessions   60.0s
    city_health      31.1s
    gates_status      0.0s
    serial total     91.1s

which is the ~90s load `#121` shipped with. The three reads share nothing --
different tools, no ordering, no data dependency -- and the handler ran them in
a `for` loop.

`fan_out` already exists for exactly this and `app.py` already uses it on the
brief page. This is not new machinery, it is a loop that should have been a
fan-out.

**This does not make the city fast.** `fleet_sessions` alone is 60s because `gc`
is timing out, and that is `#159`. What it removes is the part that was ours:
waiting for the second and third reads after the first has already paid the
price.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.app import Dashboard, Request


class _SlowClient:
    """Every call sleeps. Serial => 3 units, concurrent => ~1."""

    UNIT = 0.4

    def __init__(self, calls: list[str] | None = None):
        # Siblings SHARE the log. `fan_out` hands work to clones, so a
        # per-instance list would record only the share this object happened to
        # take -- and the test would then be asserting which worker ran what,
        # which is not the property under test.
        self.calls: list[str] = [] if calls is None else calls

    def call(self, name, arguments=None):
        self.calls.append(name)
        time.sleep(self.UNIT)

        class _R:
            payload = {"slots": [], "diagnostics": [], "data_plane": "healthy",
                       "per_rig": [], "gates": [], "gates_readable": True}

        return _R()

    def clone(self):
        return _SlowClient(self.calls)

    def list_tools(self):
        return []


def test_the_city_page_does_not_serialize_its_three_reads():
    """The property, stated as time rather than as implementation.

    Serial would be >= 3 units. Concurrent should land near 1. The threshold is
    deliberately loose -- this asserts "not serialized", not a latency budget.
    """
    client = _SlowClient()
    app = Dashboard(client, city_wide=True, rig=None)

    started = time.monotonic()
    app.handle(Request.get("/city"))
    elapsed = time.monotonic() - started

    serial = 3 * _SlowClient.UNIT
    assert elapsed < serial * 0.75, (
        f"{elapsed:.2f}s against a {serial:.2f}s serial floor -- the reads are "
        "still running in sequence"
    )


def test_all_three_surfaces_are_still_read():
    """The guard: going concurrent must not drop one."""
    client = _SlowClient()
    Dashboard(client, city_wide=True, rig=None).handle(Request.get("/city"))
    assert {"fleet_sessions", "city_health", "gates_status"} <= set(client.calls)
