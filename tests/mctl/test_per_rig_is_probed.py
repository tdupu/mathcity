"""`#176`: `city_health` asserted rig health it never measured.

During a total outage — every read FATAL, the city's port file missing, every `bd`
resolving to port 0 — `city_health` reported `data_plane: healthy` and **17/17
rigs healthy**. No rig was read. Every row was one `gc dolt health` answer
relabelled seventeen times, and seventeen agreeing rows is what made the wrong
answer persuasive.

The ruling (lumby, 2026-08-23) was **probe each rig**, and rejected the cheaper
option in terms worth keeping:

    "'Stop claiming' is the wrong half. A version that says nothing is not better
     than one that lies — it is the same failure with a quieter voice."

So each rig is now actually read, and the result is three-valued per rig:

    healthy | degraded | unreachable

A rig that could not be reached is a **named row with a reason**, and it is
**excluded from the total explicitly** rather than silently dropped or silently
counted. `unknown` is never rendered as zero.

Note what probing changes about the vocabulary: once a rig has actually been
asked, `unreachable` becomes a *measurement about that rig* rather than an
inherited guess. That is why per-rig `unreachable` is right here while the
city-level `data_plane` still needs `unknown` (`#159`) — one was asked, the other
was not.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_core import health


class _Rig:
    def __init__(self, name, root, db=None):
        self.name = name
        self.root = Path(root)
        self.db = db or name


# ---------------------------------------------------------------------------
# each rig is asked
# ---------------------------------------------------------------------------


def test_every_rig_is_probed_individually(tmp_path):
    """The defect in one line: 17 rows from one probe. Now 17 rows from 17."""
    asked: list[str] = []

    def _probe(rig, timeout=None):
        asked.append(rig.name)
        return health.RigProbe(state="healthy", reason="")

    rigs = [_Rig(n, tmp_path) for n in ("hecke", "hq", "gascity")]
    rows = health.probe_rigs(rigs, probe=_probe)

    assert asked == ["hecke", "hq", "gascity"]
    assert [r.rig_id for r in rows] == ["hecke", "hq", "gascity"]


def test_an_unreachable_rig_is_a_named_row_with_a_reason(tmp_path):
    def _probe(rig, timeout=None):
        if rig.name == "hq":
            return health.RigProbe(state="unreachable", reason="bd: port 0")
        return health.RigProbe(state="healthy", reason="")

    rows = health.probe_rigs([_Rig("hecke", tmp_path), _Rig("hq", tmp_path)], probe=_probe)
    bad = [r for r in rows if r.state == "unreachable"]

    assert [r.rig_id for r in bad] == ["hq"]
    assert bad[0].reason == "bd: port 0", "an unreachable rig must say WHY"


def test_an_unreachable_rig_is_excluded_from_the_total_explicitly(tmp_path):
    """Not silently dropped and not silently counted. The ruling's words."""
    def _probe(rig, timeout=None):
        return health.RigProbe(
            state="unreachable" if rig.name == "hq" else "healthy", reason="x"
        )

    rows = health.probe_rigs([_Rig("hecke", tmp_path), _Rig("hq", tmp_path)], probe=_probe)
    tally = health.rig_tally(rows)

    assert tally["counted"] == 1
    assert tally["healthy"] == 1
    assert tally["not_counted"] == 1
    assert tally["total"] == 2, "the denominator must still name every rig"


def test_the_three_states_are_exactly_the_ruling(tmp_path):
    states = {"healthy", "degraded", "unreachable"}
    for s in states:
        rows = health.probe_rigs([_Rig("r", tmp_path)], probe=lambda rig, timeout=None, s=s: health.RigProbe(state=s, reason=""))
        assert rows[0].state == s


def test_unknown_is_never_reported_as_zero(tmp_path):
    """A rig nobody could ask contributes to `not_counted`, never to a healthy
    count of zero. `unknown is never zero` -- the ruling."""
    def _probe(rig, timeout=None):
        return health.RigProbe(state="unreachable", reason="did not answer")

    rows = health.probe_rigs([_Rig("a", tmp_path), _Rig("b", tmp_path)], probe=_probe)
    tally = health.rig_tally(rows)

    assert tally["counted"] == 0
    assert tally["not_counted"] == 2
    assert tally["healthy"] == 0
    # and the caller can tell "0 healthy of 0 asked" from "0 healthy of 2 asked"
    assert tally["total"] == 2


# ---------------------------------------------------------------------------
# a failing probe is a rig result, not a crash
# ---------------------------------------------------------------------------


def test_a_probe_that_raises_becomes_an_unreachable_row(tmp_path):
    """One sulking rig must not take the whole report down -- the same rule the
    /city page follows for its three surfaces."""
    def _probe(rig, timeout=None):
        if rig.name == "bad":
            raise RuntimeError("boom")
        return health.RigProbe(state="healthy", reason="")

    rows = health.probe_rigs([_Rig("good", tmp_path), _Rig("bad", tmp_path)], probe=_probe)

    assert [r.state for r in rows] == ["healthy", "unreachable"]
    assert "boom" in rows[1].reason


# ---------------------------------------------------------------------------
# 17 independent reads must not be paid in sequence
# ---------------------------------------------------------------------------


def test_rigs_are_probed_concurrently(tmp_path):
    """Measured on the live city: 17 sequential probes cost 43.7s.

    They share nothing -- different stores, no ordering, no data dependency --
    and `city_health` is already a slow tool on a page an operator waits for.
    Asserted as time rather than as implementation: this pins "not serialized",
    not a particular pool.
    """
    import time

    UNIT = 0.3

    def _slow(rig, timeout=None):
        time.sleep(UNIT)
        return health.RigProbe(state="healthy", reason="")

    rigs = [_Rig(f"r{i}", tmp_path) for i in range(6)]
    started = time.monotonic()
    rows = health.probe_rigs(rigs, probe=_slow)
    elapsed = time.monotonic() - started

    assert len(rows) == 6
    serial = 6 * UNIT
    assert elapsed < serial * 0.6, f"{elapsed:.2f}s against a {serial:.2f}s serial floor"


def test_concurrent_probing_preserves_rig_order(tmp_path):
    """Order is load-bearing: the caller zips these rows against `scope.rigs`.

    Completion order would attach one rig's state to another's name -- a silent
    mismatch, not a crash, on a report whose whole job is to be read correctly.
    """
    import time

    def _uneven(rig, timeout=None):
        time.sleep(0.05 if rig.name == "last" else 0.2)
        return health.RigProbe(state="healthy", reason=rig.name)

    rigs = [_Rig(n, tmp_path) for n in ("first", "middle", "last")]
    rows = health.probe_rigs(rigs, probe=_uneven)

    assert [r.rig_id for r in rows] == ["first", "middle", "last"]
    assert [r.reason for r in rows] == ["first", "middle", "last"]
