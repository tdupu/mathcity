"""The ticker's tier vocabulary and cause/response pairing (#116, handoff §3.7).

Two things this pins that are easy to get wrong:

1. An UNKNOWN event type is `Unknown`, not silently bucketed. Honesty invariant
   2 -- "None means there is none; Unknown means we did not look" -- applies to
   classification as much as to probes. If a new event type defaulted to
   `chatter` it would vanish from a default view without anyone deciding that,
   which is the same silent-disappearance the tiering exists to prevent.

2. A CAUSE WITH NO RESPONSE must be representable. That is the proof-of-life
   mechanism: an order that fired and produced nothing is a visible break in the
   chain, and it is more informative than either event alone.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core import ticker  # noqa: E402


def ev(t, ts="2026-08-20T10:00:00-04:00", **kw):
    return {"type": t, "ts": ts, **kw}


def test_every_tier_name_is_one_of_the_four():
    assert set(ticker.TIERS) == {"alarm", "milestone", "progress", "chatter"}


def test_an_unknown_event_type_is_Unknown_not_chatter():
    # The failure this prevents: a new event type silently defaulting into a
    # tier that is off by default, disappearing without anyone deciding.
    assert ticker.tier_of("some.brand.new.type") is ticker.UNKNOWN_TIER
    assert ticker.tier_of("some.brand.new.type") != "chatter"


def test_bead_updated_is_chatter_because_it_is_the_actual_volume():
    # Measured 2026-08-13..20: bead.updated is 4,169/day, 52.8% of all events --
    # five times all order.* combined. The issue's premise named order firings.
    assert ticker.tier_of("bead.updated") == "chatter"


def test_a_failed_order_is_an_alarm_and_a_fired_one_is_not():
    assert ticker.tier_of("order.failed") == "alarm"
    assert ticker.tier_of("order.fired") == "progress"


def test_chatter_is_excluded_by_default_and_included_on_request():
    rows = [ev("bead.updated"), ev("order.failed")]
    assert [e["type"] for e in ticker.select(rows)] == ["order.failed"]
    assert len(ticker.select(rows, include_chatter=True)) == 2


def test_unknown_tier_events_are_never_hidden_by_the_default_filter():
    # Unknown must surface, because hiding it is how a new event type goes
    # unnoticed. It is the opposite of chatter.
    rows = [ev("totally.new.event")]
    assert len(ticker.select(rows)) == 1


def test_a_cause_pairs_with_its_response():
    rows = [
        ev("order.fired", ts="2026-08-20T10:00:00-04:00", subject="brief-shuffle:rig:hecke"),
        ev("order.completed", ts="2026-08-20T10:00:05-04:00", subject="brief-shuffle:rig:hecke"),
    ]
    paired = ticker.pair_causes(rows)
    assert len(paired) == 1
    assert paired[0]["cause"]["type"] == "order.fired"
    assert [r["type"] for r in paired[0]["response"]] == ["order.completed"]


def test_a_cause_with_no_response_is_representable_and_flagged():
    rows = [ev("order.fired", subject="brief-shuffle:rig:hecke")]
    paired = ticker.pair_causes(rows)
    assert len(paired) == 1
    assert paired[0]["response"] == []
    # Not None: "there is none" is a fact we established, not a lookup we skipped.
    assert paired[0]["unanswered"] is True


def test_pairing_does_not_invent_a_response_from_another_subject():
    rows = [
        ev("order.fired", ts="2026-08-20T10:00:00-04:00", subject="a"),
        ev("order.completed", ts="2026-08-20T10:00:05-04:00", subject="b"),
    ]
    paired = ticker.pair_causes(rows)
    by_subject = {p["cause"]["subject"]: p for p in paired}
    assert by_subject["a"]["unanswered"] is True


def test_a_response_earlier_than_its_cause_is_not_paired():
    # Guards against pairing on subject alone and calling any match a response.
    rows = [
        ev("order.completed", ts="2026-08-20T09:00:00-04:00", subject="a"),
        ev("order.fired", ts="2026-08-20T10:00:00-04:00", subject="a"),
    ]
    paired = ticker.pair_causes(rows)
    assert paired[0]["unanswered"] is True


def test_page_size_and_truncation_are_stated():
    rows = [ev("order.failed") for _ in range(5)]
    page = ticker.page(rows, limit=2)
    assert page["page_size"] == 2
    assert page["truncated"] is True
    assert page["returned"] == 2
    assert page["available"] == 5


def test_an_untruncated_page_says_so_rather_than_omitting_the_field():
    page = ticker.page([ev("order.failed")], limit=10)
    assert page["truncated"] is False
    assert page["available"] == 1
