"""Overview `pending` and `/queue` in-scope must count the same bucket (`#198`).

Measured live at `b527d2a`: `/` reported `pending 174` and `/queue` reported
`173 briefs in scope`, two page loads apart, both describing "open, no verdict
recorded -- the queue that needs a human". A one-brief gap.

Re-measured here on current main by tracing the two paths, not the stale live
numbers:

- `/queue` in-scope = `app._scoped(rows, "stack")` = `decision_state == "pending"`
  AND **not deferred** (`_scoped` drops deferred briefs -- the whole point of
  deferring one is that it is not waiting on you).
- `/` overview pending = `CityView.state_counts()["pending"]`, a raw census by
  `decision_state` that counts a **deferred-but-pending** brief under `pending`
  (its `decision_state` is still `"pending"`; deferral lives in `status`).

So a brief with `status="deferred"`, `decision_state="pending"` is in the
overview's pending total and NOT in the queue's -- the exact off-by-one. The
overview is the wrong path: its own caveat says pending is "the queue that needs
a human", and a deferred brief has been excused from exactly that. The fix
counts it where it belongs -- under `deferred` -- so the two paths agree and the
city total still balances.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard import app  # noqa: E402
from mctl_dashboard.aggregate import CityView  # noqa: E402


def _rows():
    return [
        {"brief_id": "a", "bead_id": "he-a", "decision_state": "pending"},
        {"brief_id": "b", "bead_id": "he-b", "decision_state": "pending"},
        # deferred: status carries it, decision_state stays "pending".
        {"brief_id": "c", "bead_id": "he-c", "decision_state": "pending", "status": "deferred"},
        {"brief_id": "d", "bead_id": "he-d", "decision_state": "adjudicated"},
    ]


def _city_view(rows):
    return CityView.from_payload({"city_root": "/c", "briefs": rows})


def test_overview_pending_equals_queue_in_scope():
    """The pin: the two counting paths report the same pending bucket."""
    rows = _rows()
    overview_pending = _city_view(rows).state_counts().get("pending", 0)
    queue_in_scope = len(app._scoped(rows, "stack"))
    assert overview_pending == queue_in_scope, (
        f"overview says {overview_pending} pending, queue says {queue_in_scope} in scope"
    )


def test_a_deferred_brief_is_counted_under_deferred_not_pending():
    counts = _city_view(_rows()).state_counts()
    assert counts.get("pending", 0) == 2, "the deferred brief must not inflate pending"
    assert counts.get("deferred", 0) == 1, "the deferred brief must be counted, under deferred"


def test_the_city_total_still_conserves_every_brief():
    """Reclassifying deferred must not drop or double-count a row: the census
    total still equals the number of briefs."""
    rows = _rows()
    counts = _city_view(rows).state_counts()
    assert sum(counts.values()) == len(rows)
