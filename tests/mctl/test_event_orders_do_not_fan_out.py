"""A rig-scoped EVENT order fires in EVERY registered rig, not just the one
where the event happened.

THE DEFECT (measured on kolchin, 2026-09-10). `brief-shuffle-on-submit` was
`scope = "rig"` + `trigger = "event"` + `on = "brief.submitted"`, registered
for three rigs. `.gc/events.jsonl` on kolchin:

    74   brief-shuffle-on-submit:rig:mathcity
    74   brief-shuffle-on-submit:rig:gascity

Exactly 74 and 74. Neither rig has a `.beads/briefs/` tree, so neither can
have ORIGINATED a single `brief.submitted` event -- yet the order fired 74
times in each, in lockstep. One submission in the testrig poured
`brief-shuffle` into all three.

Two roots stranded that way, one second apart:

    ga-333    2026-09-09 02:22:56   open
    ma-v7h    2026-09-09 02:22:57   open

14 accumulated in `ma` since 2026-08-24; 13 still open two weeks later.

WHY IT WAS SILENT. `brief-shuffle` handles an empty pile correctly -- it
records `claim_result=empty` and exits (formula step 3, the gsp-3al3
EMPTY-PILE ROUTE). A pour into a pile-less rig SHOULD have been a harmless
no-op. It was not, because `mathcity.brief-operator` sits at max=0: nothing
ever claimed the work, so the clean-exit path was never reached. The workflow
just stayed open. No error, no failed order, no diagnostic at any layer.

THE INVARIANT. Every other event-triggered order in the catalog is
`scope = "city"` -- they fire once per event and resolve the target from the
event itself. `brief-shuffle-on-submit` was the only `scope="rig"` one, and
the only one that fanned out. A rig-scoped event order has no way to ask
"did this event happen HERE", so the combination is banned outright.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

ORDERS = sorted((Path(__file__).resolve().parents[2] / "orders").glob("*.toml"))


def _order(path):
    with path.open("rb") as fh:
        return (tomllib.load(fh) or {}).get("order", {}) or {}


def test_orders_dir_was_actually_found():
    """P6.2: a check that could not fail must not render as passed."""
    assert ORDERS, "no orders/*.toml found -- the sweep below would vacuously pass"


@pytest.mark.parametrize("path", ORDERS, ids=lambda p: p.name)
def test_no_event_order_is_rig_scoped(path):
    o = _order(path)
    if str(o.get("trigger", "")).strip() != "event":
        pytest.skip("not event-triggered")
    scope = str(o.get("scope", "city")).strip() or "city"
    assert scope != "rig", (
        f"{path.name} is trigger=event + scope=rig (on={o.get('on')!r}).\n"
        "A rig-scoped event order fires in EVERY registered rig, not only the "
        "rig where the event originated -- one event becomes N pours, N-1 of "
        "them into rigs that never produced it. Use scope=\"city\" (as every "
        "other event order in this catalog does) and resolve the target rig "
        "from the event subject."
    )
