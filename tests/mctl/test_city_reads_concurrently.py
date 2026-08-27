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
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.app import Dashboard, Request


class _InFlight:
    """A concurrency tracker SHARED across a client and its fan-out siblings.

    The property under test is *overlap* -- were two reads ever in flight at
    once. Measuring it directly is the whole point of mc-5p8v: the previous form
    asserted a wall-clock bound (`elapsed < serial * 0.75`), which renders a
    CPU-starved scheduler -- threads that could not be dispatched promptly -- as
    a serialized handler. That is the P6.3 anti-pattern inside a test assertion
    ("a deadline is not a verdict"): the prober's contention attributed to the
    probed. A shared in-flight counter cannot be fooled that way -- it rises
    above one only when calls genuinely run at the same time, however slowly.
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
    """Every call sleeps. A shared `_InFlight` records true overlap.

    `serialize` optionally holds a shared lock across the whole call, which is
    what a single-pipe client does -- only one read runs at a time. It exists so
    the overlap assertion has an observed failing case (P6.2): a serialized
    client drives the peak to exactly one.
    """

    UNIT = 0.4

    def __init__(
        self,
        calls: list[str] | None = None,
        *,
        inflight: "_InFlight | None" = None,
        serialize_lock: "threading.Lock | None" = None,
    ):
        # Siblings SHARE the log AND the tracker. `fan_out` hands work to clones,
        # so a per-instance counter would stay at one however much overlap there
        # was -- which is exactly why the old test could not measure overlap and
        # fell back to the wall clock.
        self.calls: list[str] = [] if calls is None else calls
        self.inflight = inflight or _InFlight()
        self.serialize_lock = serialize_lock

    def call(self, name, arguments=None):
        # Acquire the serialization lock BEFORE counting as in-flight: a thread
        # blocked on the lock is not running, so counting it would inflate the
        # peak and hide the very serialization this models.
        if self.serialize_lock is not None:
            self.serialize_lock.acquire()
        self.inflight.enter()
        try:
            self.calls.append(name)
            time.sleep(self.UNIT)

            class _R:
                payload = {"slots": [], "diagnostics": [], "data_plane": "healthy",
                           "per_rig": [], "gates": [], "gates_readable": True}

            return _R()
        finally:
            self.inflight.exit()
            if self.serialize_lock is not None:
                self.serialize_lock.release()

    def clone(self):
        return _SlowClient(
            self.calls, inflight=self.inflight, serialize_lock=self.serialize_lock
        )

    def list_tools(self):
        return []


def test_the_city_page_does_not_serialize_its_three_reads():
    """The property, stated as OVERLAP observed directly -- not a wall clock.

    A serialized handler drives the shared in-flight peak to one; a fan-out
    lets two or more reads run at once and the peak rises above one. This holds
    under CPU contention, where the old wall-clock threshold spuriously failed.
    """
    tracker = _InFlight()
    client = _SlowClient(inflight=tracker)
    app = Dashboard(client, city_wide=True, rig=None)

    app.handle(Request.get("/city"))

    assert tracker.peak >= 2, (
        f"peak of {tracker.peak} in flight -- the reads are still running in sequence"
    )


def test_a_serialized_handler_would_fail_the_overlap_check():
    """The observed failing case (P6.2): serialize every read and the peak is 1.

    This is the state the overlap assertion above exists to reject. Holding a
    single lock across each call is what a one-pipe client does, and it drives
    the shared in-flight counter to exactly one -- so `peak >= 2` is falsifiable,
    not a check that cannot fail.
    """
    tracker = _InFlight()
    client = _SlowClient(inflight=tracker, serialize_lock=threading.Lock())
    Dashboard(client, city_wide=True, rig=None).handle(Request.get("/city"))
    assert tracker.peak == 1


def test_all_three_surfaces_are_still_read():
    """The guard: going concurrent must not drop one."""
    client = _SlowClient()
    Dashboard(client, city_wide=True, rig=None).handle(Request.get("/city"))
    assert {"fleet_sessions", "city_health", "gates_status"} <= set(client.calls)
