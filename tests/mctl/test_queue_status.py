"""#113 — queue_status: the six queue populations, shaped from injected `bd` reads.

`queue_status` never shells out itself -- `read(what)` is injected, exactly
like `mctl_core.orders.orders_status`, so these tests never touch a live `bd`
store. The reader keys mirror real `bd` flags with real dependency-aware
semantics rather than a second, drifting definition of "ready" or "blocked":

    ready_explain -> `bd ready --explain --json --limit 0`   (ready + blocked, with blocked_by)
    unclaimed     -> `bd ready --unassigned --json --limit 0`
    deferred      -> `bd list --all --deferred --json --limit 0 --readonly`
    routed_ids    -> union of `bd list --has-metadata-key <key> ...` (tail-end-detector's set)

THE LOAD-BEARING ASSERTIONS:
  - `next_up_is_prediction` is always `True` (#113: dispatch order is measured
    arbitrary; see queue.py's module docstring).
  - `deferred` is exclusive of `blocked`/`tail`/`starved`/`ready_unclaimed` --
    a bead with a future `defer_until` is deliberately parked, not stuck.
  - Three-valued: a failed `ready_explain` read makes EVERY population `None`,
    never `[]`. A failed auxiliary read (`deferred`/`unclaimed`/`routed_ids`)
    nulls only the population(s) that depend on it -- the rest of the queue is
    still a real measurement and must not be thrown away with it.
  - An empty population from a read that SUCCEEDED is `[]`, not `None`.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.queue import queue_status  # noqa: E402

NOW = datetime(2026, 8, 24, 12, 0, 0, tzinfo=timezone.utc)
FRESH = "2026-08-24T10:00:00Z"          # 2h old
STALE = "2026-08-20T12:00:00Z"          # 4d old -- past the 3d tail/starved trigger


def _explain(ready=(), blocked=()):
    return {"ready": list(ready), "blocked": list(blocked), "summary": {}, "schema_version": 1}


def _bead(bead_id, *, title="untitled", created_at=FRESH, updated_at=FRESH, priority=2, blocked_by=None):
    row = {
        "id": bead_id,
        "title": title,
        "created_at": created_at,
        "updated_at": updated_at,
        "priority": priority,
    }
    if blocked_by is not None:
        row["blocked_by"] = blocked_by
        row["blocked_by_count"] = len(blocked_by)
    return row


def _reader(*, ready_explain=None, unclaimed=None, deferred=None, routed_ids=None, fail=()):
    values = {
        "ready_explain": ready_explain if ready_explain is not None else _explain(),
        "unclaimed": unclaimed if unclaimed is not None else [],
        "deferred": deferred if deferred is not None else [],
        "routed_ids": routed_ids if routed_ids is not None else set(),
    }

    def read(what: str):
        if what in fail:
            raise RuntimeError(f"bd {what} unavailable")
        return values[what]

    return read


# ---------------------------------------------------------------------------
# Happy path: each population shaped from the right read
# ---------------------------------------------------------------------------


def test_ready_unclaimed_is_shaped_from_the_unassigned_read():
    ready_bead = _bead("mc-ready", title="Ready work")
    out = queue_status(
        _reader(
            ready_explain=_explain(ready=[ready_bead]),
            unclaimed=[ready_bead],
        ),
        now=NOW,
    )
    assert out["state"] == "healthy"
    assert out["ready_unclaimed"] == [{"bead_id": "mc-ready", "title": "Ready work", "priority": 2}]


def test_blocked_carries_blocked_on_from_bd_explain():
    blocked_bead = _bead(
        "mc-blocked", title="Blocked work",
        blocked_by=[{"id": "mc-dep", "title": "The dependency", "status": "open"}],
    )
    out = queue_status(_reader(ready_explain=_explain(blocked=[blocked_bead])), now=NOW)
    assert out["blocked"] == [
        {"bead_id": "mc-blocked", "title": "Blocked work", "blocked_on": "mc-dep", "blocked_on_title": "The dependency"}
    ]


def test_deferred_carries_the_until_timestamp():
    deferred_bead = {"id": "mc-park", "title": "Parked", "defer_until": "2026-09-01T00:00:00Z"}
    out = queue_status(_reader(deferred=[deferred_bead]), now=NOW)
    assert out["deferred"] == [{"bead_id": "mc-park", "title": "Parked", "until": "2026-09-01T00:00:00Z"}]


def test_next_up_is_prediction_is_always_true_on_the_happy_path():
    out = queue_status(_reader(), now=NOW)
    assert out["next_up_is_prediction"] is True


# ---------------------------------------------------------------------------
# Deliberate != accidental: deferred is exclusive (#113 §5.8)
# ---------------------------------------------------------------------------


def test_a_deferred_bead_does_not_also_appear_as_blocked():
    same_id = "mc-both"
    blocked_bead = _bead(same_id, blocked_by=[{"id": "mc-dep", "title": "dep"}])
    deferred_bead = {"id": same_id, "title": "untitled", "defer_until": "2026-09-01T00:00:00Z"}
    out = queue_status(
        _reader(ready_explain=_explain(blocked=[blocked_bead]), deferred=[deferred_bead]),
        now=NOW,
    )
    assert out["blocked"] == []
    assert [row["bead_id"] for row in out["deferred"]] == [same_id]


def test_a_deferred_bead_does_not_also_appear_as_ready_unclaimed():
    same_id = "mc-both"
    ready_bead = _bead(same_id)
    deferred_bead = {"id": same_id, "title": "untitled", "defer_until": "2026-09-01T00:00:00Z"}
    out = queue_status(
        _reader(
            ready_explain=_explain(ready=[ready_bead]),
            unclaimed=[ready_bead],
            deferred=[deferred_bead],
        ),
        now=NOW,
    )
    assert out["ready_unclaimed"] == []


# ---------------------------------------------------------------------------
# tail / starved: idle-derived, distinct sources (ready side vs blocked side)
# ---------------------------------------------------------------------------


def test_tail_is_ready_unclaimed_idle_past_the_trigger_and_never_routed():
    stale_unrouted = _bead("mc-tail", created_at=STALE, updated_at=STALE)
    stale_routed = _bead("mc-routed", created_at=STALE, updated_at=STALE)
    fresh = _bead("mc-fresh", created_at=FRESH, updated_at=FRESH)
    out = queue_status(
        _reader(
            ready_explain=_explain(ready=[stale_unrouted, stale_routed, fresh]),
            unclaimed=[stale_unrouted, stale_routed, fresh],
            routed_ids={"mc-routed"},
        ),
        now=NOW,
    )
    assert [row["bead_id"] for row in out["tail"]] == ["mc-tail"]


def test_starved_is_blocked_idle_past_the_same_trigger():
    stale_blocked = _bead("mc-starved", created_at=STALE, updated_at=STALE, blocked_by=[{"id": "mc-dep"}])
    fresh_blocked = _bead("mc-fine", created_at=FRESH, updated_at=FRESH, blocked_by=[{"id": "mc-dep"}])
    out = queue_status(_reader(ready_explain=_explain(blocked=[stale_blocked, fresh_blocked])), now=NOW)
    assert [row["bead_id"] for row in out["starved"]] == ["mc-starved"]
    assert out["starved"][0]["idle_seconds"] >= 3 * 86400


# ---------------------------------------------------------------------------
# next_up: oldest-first, capped -- mirrors the dispatcher's own
# `--sort oldest --limit=20` (workquery.go:323/:239), computed in pure Python
# so it stays testable without shelling out to `bd`.
# ---------------------------------------------------------------------------


def test_next_up_sorts_ready_unclaimed_oldest_first():
    older = _bead("mc-older", created_at="2026-08-01T00:00:00Z")
    newer = _bead("mc-newer", created_at="2026-08-20T00:00:00Z")
    out = queue_status(
        _reader(ready_explain=_explain(ready=[newer, older]), unclaimed=[newer, older]),
        now=NOW,
    )
    assert [row["bead_id"] for row in out["next_up"]] == ["mc-older", "mc-newer"]


def test_next_up_is_capped():
    from mctl_core.queue import NEXT_UP_LIMIT

    beads = [_bead(f"mc-{i:03d}", created_at=f"2026-08-{(i % 27) + 1:02d}T00:00:00Z") for i in range(NEXT_UP_LIMIT + 5)]
    out = queue_status(_reader(ready_explain=_explain(ready=beads), unclaimed=beads), now=NOW)
    assert len(out["next_up"]) == NEXT_UP_LIMIT


# ---------------------------------------------------------------------------
# Three-valued: total failure vs partial failure vs a genuine empty queue
# ---------------------------------------------------------------------------


def test_a_failed_core_read_makes_every_population_null_not_empty():
    out = queue_status(_reader(fail=("ready_explain",)), now=NOW)
    assert out["state"] == "unreachable"
    for key in ("ready_unclaimed", "blocked", "tail", "starved", "deferred", "next_up"):
        assert out[key] is None, f"{key} must be None (we could not look), not []"
    assert out["next_up_is_prediction"] is True
    codes = {d["code"] for d in out["diagnostics"]}
    assert "MQUE_QUEUE_UNREACHABLE" in codes


def test_a_failed_deferred_read_nulls_only_deferred():
    ready_bead = _bead("mc-ready")
    out = queue_status(
        _reader(
            ready_explain=_explain(ready=[ready_bead]),
            unclaimed=[ready_bead],
            fail=("deferred",),
        ),
        now=NOW,
    )
    assert out["state"] == "degraded"
    assert out["deferred"] is None
    assert out["ready_unclaimed"] == [{"bead_id": "mc-ready", "title": "untitled", "priority": 2}]
    codes = {d["code"] for d in out["diagnostics"]}
    assert "MQUE_DEFERRED_UNREACHABLE" in codes


def test_a_failed_unclaimed_read_nulls_ready_unclaimed_tail_and_next_up_but_not_blocked():
    blocked_bead = _bead("mc-blocked", blocked_by=[{"id": "mc-dep"}])
    out = queue_status(
        _reader(ready_explain=_explain(blocked=[blocked_bead]), fail=("unclaimed",)),
        now=NOW,
    )
    assert out["state"] == "degraded"
    assert out["ready_unclaimed"] is None
    assert out["tail"] is None
    assert out["next_up"] is None
    assert out["blocked"] == [
        {"bead_id": "mc-blocked", "title": "untitled", "blocked_on": "mc-dep", "blocked_on_title": None}
    ]


def test_a_failed_routed_ids_read_nulls_only_tail():
    ready_bead = _bead("mc-ready", created_at=STALE, updated_at=STALE)
    out = queue_status(
        _reader(
            ready_explain=_explain(ready=[ready_bead]),
            unclaimed=[ready_bead],
            fail=("routed_ids",),
        ),
        now=NOW,
    )
    assert out["state"] == "degraded"
    assert out["tail"] is None
    assert out["ready_unclaimed"] == [{"bead_id": "mc-ready", "title": "untitled", "priority": 2}]


def test_a_genuinely_empty_queue_reports_empty_lists_not_null():
    out = queue_status(_reader(), now=NOW)
    assert out["state"] == "healthy"
    for key in ("ready_unclaimed", "blocked", "tail", "starved", "deferred", "next_up"):
        assert out[key] == [], f"{key} was read successfully and is empty -- a measurement, not None"
    assert out["diagnostics"] == []
