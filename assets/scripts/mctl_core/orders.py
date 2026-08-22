"""Orders and formulas as typed reads (#117).

Two of the three nouns the project owner asked for by name: *"The dashboard I
want has Formulas, Orders, Molecules etc"*.

WHERE OUTCOMES COME FROM. `<city-root>/.gc/events.jsonl` -- `order.fired`,
`order.completed`, `order.failed`, 6,593 events across 74 subjects. NOT from
`gc order history`, which logs that an order ran and never how it ended, and
not from `gc order check`, whose `last_run_outcome` is declared and never
populated (#156).

An earlier version of this module reported `unknown` for all 127 orders, on a
measurement that probed those two surfaces and read their silence as the city's
(#156, corrected). `unknown` now means only what it says: the event log has
never seen this order. 43 of 127 today.

HEALTH IS THE OUTCOME, NEVER THE RECENCY. `mol-dog-compactor` has fired 61 times
and completed zero; `orphan-sweep` 161 and one. They fire punctually, so a
signal keyed on "did it run lately" paints them green -- a fresh canary in front
of broken machinery. `healthy` is `outcome == "completed"` and nothing else.

THE OUTCOME AND ITS TIMESTAMP ARE ONE FACT. `fold_outcomes` returns both from
the same event. History and the event log disagree for every order present in
both (24 of 24, history hours behind) and do not share a timestamp format, so
pairing an outcome from one with a time from the other renders a reading
neither source supports.

WHY A READER IS INJECTED. `gc order list` takes ~33s and `gc order history`
~57s. A view that shells out per render reproduces the sluggishness complaint
this dashboard exists to fix, and a test suite that shells out is unusable.
The caller supplies the read; this module does the shaping.

THREE-VALUED, NOT BOOLEAN. A read that fails reports `state="unreachable"` with
`total=None`. It never reports zero orders -- "we could not look" and "there
are none" are different facts and a zero would collapse them.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

#: Reserved for orders the event log has never seen -- NOT a blanket default.
#: The earlier version of this module reported `unknown` for every order, on a
#: measurement that missed `<city-root>/.gc/events.jsonl` entirely (#156).
UNKNOWN_OUTCOME = "unknown"

#: The event types that settle an order's fate. `order.fired` says it started;
#: only these two say how it ended.
TERMINAL_EVENTS = {"order.completed": "completed", "order.failed": "failed"}


def fold_outcomes(events):
    """Latest terminal outcome per order subject, WITH the timestamp that settled it.

    Returns `{subject: (ts, outcome)}`. The pair is the unit: a caller that
    takes the outcome from here and the time from elsewhere renders a reading
    neither source supports.

    Freshness is not health. `mol-dog-compactor` fires punctually and has never
    once completed -- any signal keyed on "did it run lately" renders it green,
    which is the defect this fold exists to prevent (§5.7).
    """
    latest: dict[str, tuple[str, str]] = {}
    for event in events or ():
        outcome = TERMINAL_EVENTS.get(event.get("type"))
        if not outcome:
            continue
        subject, when = event.get("subject"), event.get("ts") or ""
        if not subject:
            continue
        if when > latest.get(subject, ("", ""))[0]:  # `>` so file order never decides
            latest[subject] = (when, outcome)
    return latest


def _unreachable(what: str, err: Exception) -> dict[str, Any]:
    """A read that could not run. `total` is None, never 0."""
    return {
        "state": "unreachable",
        "total": None,
        "diagnostics": [f"gc {what} unavailable: {err}"],
    }


def orders_status(read: Callable[[str], Any]) -> dict[str, Any]:
    """Every registered order, with its last execution and an unknown outcome."""
    try:
        orders = read("orders")
    except Exception as err:  # noqa: BLE001 -- any read failure is "we could not look"
        out = _unreachable("order list", err)
        out["orders"] = []
        return out

    try:
        history = read("history")
        history_state = "healthy"
        diagnostics: list[str] = []
    except Exception as err:  # noqa: BLE001
        history, history_state = [], "degraded"
        diagnostics = [f"gc order history unavailable: {err}"]

    try:
        outcomes = fold_outcomes(read("events"))
    except Exception as err:  # noqa: BLE001
        outcomes = {}
        diagnostics.append(f"event log unavailable: {err}")

    last: dict[str, str] = {}
    for entry in history:
        name = entry.get("order")
        when = entry.get("executed")
        if name and when and when > last.get(name, ""):
            last[name] = when

    rows = []
    for order in orders:
        name = order.get("name")
        settled_at, outcome = outcomes.get(name, (None, UNKNOWN_OUTCOME))
        # The outcome and its timestamp are ONE fact and travel together. The
        # two sources disagree for every order present in both -- `gc order
        # history` runs hours behind the event log, and they do not even share a
        # timestamp format (`...Z` vs `...-04:00`), so they are not comparable
        # as strings. History is a fallback only where the log is silent.
        executed = settled_at or last.get(name)
        rows.append(
            {
                "name": name,
                "scoped_name": order.get("scoped_name"),
                "description": order.get("description"),
                "type": order.get("type"),
                "trigger": order.get("trigger"),
                "interval": order.get("interval"),
                "enabled": order.get("enabled"),
                "source": order.get("source"),
                "last_executed": executed,
                "ever_ran": executed is not None,
                # From the event log, never from `ever_ran`: an order that ran
                # is not an order that worked.
                "last_outcome": outcome,
                # Health is the OUTCOME, not the recency. A punctual order that
                # has never completed is not healthy.
                "healthy": outcome == "completed",
            }
        )

    return {
        "state": history_state,
        "total": len(rows),
        "orders": rows,
        "ran_at_least_once": sum(1 for r in rows if r["ever_ran"]),
        "outcome_recorded": sum(1 for r in rows if r["last_outcome"] != UNKNOWN_OUTCOME),
        "failing": sum(1 for r in rows if r["last_outcome"] == "failed"),
        "diagnostics": diagnostics,
    }


def formulas_catalog(read: Callable[[str], Any]) -> dict[str, Any]:
    """Every formula the city knows about."""
    try:
        formulas = read("formulas")
    except Exception as err:  # noqa: BLE001
        out = _unreachable("formula list", err)
        out["formulas"] = []
        return out

    rows = [{"name": f} if isinstance(f, str) else dict(f) for f in formulas]
    return {
        "state": "healthy",
        "total": len(rows),
        "formulas": rows,
        "diagnostics": [],
    }
