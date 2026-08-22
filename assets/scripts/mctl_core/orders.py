"""Orders and formulas as typed reads (#117).

Two of the three nouns the project owner asked for by name: *"The dashboard I
want has Formulas, Orders, Molecules etc"*.

WHY EVERY OUTCOME IS `unknown`. `gc order history` records THAT an order ran
and never WHETHER it succeeded -- there is no outcome, result, status or exit
field on any order or any history entry (#156, measured across 127 orders and
50 history entries). So this module reports `last_outcome="unknown"` for every
order, including the 24 that have run.

That will look wrong on screen, and it is the true reading. Mapping "it
executed" to "it succeeded" would render a check that could not have failed as
a check that passed (P6.2) -- in the exact noun the owner asked for. When the
city starts recording outcomes, `last_outcome` is where they land and nothing
else here changes.

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

#: The outcome every order reports until the city records execution results (#156).
UNKNOWN_OUTCOME = "unknown"


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

    last: dict[str, str] = {}
    for entry in history:
        name = entry.get("order")
        when = entry.get("executed")
        if name and when and when > last.get(name, ""):
            last[name] = when

    rows = []
    for order in orders:
        name = order.get("name")
        executed = last.get(name)
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
                # Never derived from `ever_ran`. See module docstring.
                "last_outcome": UNKNOWN_OUTCOME,
            }
        )

    return {
        "state": history_state,
        "total": len(rows),
        "orders": rows,
        "ran_at_least_once": sum(1 for r in rows if r["ever_ran"]),
        "outcome_recorded": 0,
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
