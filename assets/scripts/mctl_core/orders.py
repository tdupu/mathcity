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

THE CATALOG IS LOCAL FILES. `read_order_catalog` reads order TOML off disk, so
the catalog half costs a directory walk instead of the 89s subprocess that made
it unservable in the first place. Which root it read is a decision the caller
gets to see: roots that disagree, and roots that were never materialized, are
typed diagnostics -- never a quietly partial catalog wearing a total.
"""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Callable, Mapping

from .diagnostics import Diagnostic, Severity

#: Structured diagnostic codes for the orders/formulas reads. Registered in
#: assets/mctl/diagnostics.toml; every consumer (the MCP tool AND the dashboard)
#: receives typed diagnostic OBJECTS, never strings -- a string diagnostic dies
#: FATAL MCTL_MCP_OUTPUT_SCHEMA_VIOLATION against the declared object schema
#: (#203).
MORD_CATALOG_UNREACHABLE = "MORD_CATALOG_UNREACHABLE"
MORD_CATALOG_NOT_READ = "MORD_CATALOG_NOT_READ"
MORD_HISTORY_UNAVAILABLE = "MORD_HISTORY_UNAVAILABLE"
MORD_EVENT_LOG_UNAVAILABLE = "MORD_EVENT_LOG_UNAVAILABLE"

#: Bounded-reader codes. Root selection and per-file failures are REPORTED, on
#: the standing rule that a partial catalog must never render as a complete one.
MORD_CATALOG_ROOT_MISMATCH = "MORD_CATALOG_ROOT_MISMATCH"
MORD_CATALOG_ROOT_UNAVAILABLE = "MORD_CATALOG_ROOT_UNAVAILABLE"
MORD_CATALOG_FILE_UNREADABLE = "MORD_CATALOG_FILE_UNREADABLE"

#: Reserved for orders the event log has never seen -- NOT a blanket default.
#: The earlier version of this module reported `unknown` for every order, on a
#: measurement that missed `<city-root>/.gc/events.jsonl` entirely (#156).
UNKNOWN_OUTCOME = "unknown"

#: The worst measured cost of the catalog reads, across one night in one city:
#:
#:     gc order list --json      28.34s · 43.10s · 42.84s · 46.72s · 89s
#:     gc order history --json   55.46s
#:
#: The dashboard makes BOTH calls, so its cost is the sum. A bound below this is a
#: path that cannot succeed -- which is what shipped at 15s and what stick-dog
#: measured and refused. Raise it when a larger cost is MEASURED, never to make a
#: failing call pass.
MEASURED_CATALOG_WORST_SECONDS = 89 + 56

#: The dashboard renders a page and can wait; it pays list + history and always
#: needs the real catalog. This bound must accommodate the measured worst case --
#: `test_the_dashboard_bound_can_actually_succeed` fails if it does not.
DASHBOARD_CATALOG_TIMEOUT_SECONDS = 180

#: The MCP request path takes NO catalog bound, because it makes no catalog call.
#: See EVENT_LOG_ONLY. The two callers do not share a budget because they do not
#: share a cost -- one constant cannot serve both.

#: Serve only the event log -- a local file, milliseconds, 6,800+ order events.
#: The outcomes half works today; the catalog is what cannot be served. In this
#: mode no subprocess is spawned at all and the catalog reports `unreachable`.
EVENT_LOG_ONLY = "event_log_only"

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
        "diagnostics": [
            Diagnostic(
                Severity.WARN,
                MORD_CATALOG_UNREACHABLE,
                f"gc {what} unavailable: {err}",
            ).to_dict()
        ],
    }


def _event_log_only(read: Callable[[str], Any]) -> dict[str, Any]:
    """Outcomes without the catalog: no subprocess, no wait.

    The catalog is reported `unreachable` rather than empty -- we did not look,
    which is not the same as finding nothing.
    """
    diagnostics: list[dict] = [
        Diagnostic(
            Severity.INFO,
            MORD_CATALOG_NOT_READ,
            "catalog not read: gc order list is not servable inside a request budget "
            "(measured 89s in-city); serving event-log outcomes only",
        ).to_dict()
    ]
    try:
        outcomes = fold_outcomes(read("events"))
        outcomes_state = "healthy"
    except Exception as err:  # noqa: BLE001
        outcomes, outcomes_state = {}, "unreachable"
        diagnostics.append(
            Diagnostic(
                Severity.WARN,
                MORD_EVENT_LOG_UNAVAILABLE,
                f"event log unavailable: {err}",
            ).to_dict()
        )
    return {
        "state": "unreachable",
        "outcomes_state": outcomes_state,
        "total": None,
        "orders": [],
        "known_outcomes": {name: outcome for name, (_, outcome) in outcomes.items()},
        "failing": sum(1 for _, o in outcomes.values() if o == "failed"),
        "outcome_recorded": len(outcomes),
        "diagnostics": diagnostics,
    }


def orders_status(read: Callable[[str], Any], mode: str | None = None) -> dict[str, Any]:
    """Every registered order, with its last execution and an unknown outcome."""
    if mode == EVENT_LOG_ONLY:
        return _event_log_only(read)

    try:
        orders = read("orders")
    except Exception as err:  # noqa: BLE001 -- any read failure is "we could not look"
        out = _unreachable("order list", err)
        out["orders"] = []
        # The declared schema requires `failing` and `outcome_recorded` on every
        # orders_status response; with no orders read, both are 0 -- not absent.
        # (`_unreachable` is shared with formulas_catalog, so these orders-only
        # keys live here, not in it.)
        out["failing"] = 0
        out["outcome_recorded"] = 0
        return out

    try:
        history = read("history")
        history_state = "healthy"
        diagnostics: list[dict] = []
    except Exception as err:  # noqa: BLE001
        history, history_state = [], "degraded"
        diagnostics = [
            Diagnostic(
                Severity.WARN,
                MORD_HISTORY_UNAVAILABLE,
                f"gc order history unavailable: {err}",
            ).to_dict()
        ]

    try:
        outcomes = fold_outcomes(read("events"))
    except Exception as err:  # noqa: BLE001
        outcomes = {}
        diagnostics.append(
            Diagnostic(
                Severity.WARN,
                MORD_EVENT_LOG_UNAVAILABLE,
                f"event log unavailable: {err}",
            ).to_dict()
        )

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


#: Where order definitions live in a pack checkout: the root set and each
#: sub-pack's set. A reader that scans only the first silently drops every
#: subdomain order and still reports a total, which reads as a full catalog.
ORDER_GLOBS = ("orders/*.toml", "subdomains/*/orders/*.toml")


def _order_row(path: Path, root: Path, rig_name: str | None) -> dict[str, Any]:
    """Shape one `[order]` table the way `gc order list --json` shapes it.

    Field derivation follows gc so the two readers cannot disagree about the
    same file: `orderToJSON` (cmd/gc/cmd_order.go:562) for `type`/`enabled`,
    `orderDecode.normalized` for the `gate` spelling of `trigger`, and
    `Order.ScopedName` (internal/orders/order.go:141) for the scoped name.
    """
    with path.open("rb") as handle:
        order = (tomllib.load(handle) or {}).get("order") or {}

    name = path.stem
    scope = str(order.get("scope") or "")
    # `ScopedName()`: the bare name unless the order is rig-scoped.
    scoped_name = f"{name}:rig:{rig_name}" if scope == "rig" and rig_name else name

    enabled = order.get("enabled")
    try:
        source = str(path.relative_to(root))
    except ValueError:  # outside the scanned root; an absolute path is the honest answer
        source = str(path)

    return {
        "name": name,
        "scoped_name": scoped_name,
        "description": str(order.get("description") or ""),
        # `IsExec()`: an order that execs is exec-typed, everything else is a formula.
        "type": "exec" if order.get("exec") else "formula",
        # `normalized()` reads `gate` when `trigger` is absent.
        "trigger": str(order.get("trigger") or order.get("gate") or ""),
        "interval": str(order.get("interval") or ""),
        # `IsEnabled()`: absent means enabled.
        "enabled": True if enabled is None else bool(enabled),
        "source": source,
        "scope": scope,
        "formula": str(order.get("formula") or ""),
        "exec": str(order.get("exec") or ""),
        "on": str(order.get("on") or ""),
        "target": str(order.get("pool") or ""),
        "timeout": str(order.get("timeout") or ""),
    }


def read_order_catalog(
    *,
    city_root: Any = None,
    rig_root: Any = None,
    source_checkout: Any = None,
    pack_root: Any = None,
    rig_name: str | None = None,
) -> dict[str, Any]:
    """Every registered order, read from local TOML -- no subprocess, ever.

    `gc order list --json` is the only catalog `orders_status` has ever had, and
    it costs a measured 28-89s. That is why the request path serves
    `EVENT_LOG_ONLY` and reports the catalog `unreachable`: not because the
    catalog is unknowable, but because the one reader for it could not be
    afforded. The definitions are files; this reads the files.

    ROOT SELECTION IS EXPLICIT. `source_checkout` (or `pack_root`) wins when it
    resolves, and `rig_root` is the fallback -- never a guess, and never silent.
    A declared root that is not materialized, and a `rig_root` that disagrees
    with the chosen source root, each raise a typed diagnostic, because the
    failure this guards against is a confidently incomplete catalog.

    Three-valued like the rest of this module: with no root to read, `state` is
    `unreachable` and `total` is None. It never returns zero orders to mean
    "we could not look".
    """
    facts = {k: str(v) for k, v in (("city_path", city_root), ("rig_name", rig_name)) if v}
    diagnostics: list[dict] = []

    def _note(severity: Severity, code: str, message: str, **extra: str) -> None:
        diagnostics.append(Diagnostic(severity, code, message, facts={**facts, **extra}).to_dict())

    # Preference order. `pack_root` is the source root under its other name, so
    # it sits with `source_checkout` and ahead of the rig fallback.
    declared = (
        ("source_checkout", source_checkout),
        ("pack_root", pack_root),
        ("rig_root", rig_root),
    )
    root: Path | None = None
    chosen_as = ""
    incomplete = False
    for label, value in declared:
        if value is None:
            continue
        candidate = Path(value)
        if not candidate.is_dir():
            # An unmaterialized import root. Reported, not skipped in silence.
            incomplete = True
            _note(
                Severity.WARN,
                MORD_CATALOG_ROOT_UNAVAILABLE,
                f"{label} {candidate} is not a materialized directory; it was not scanned",
                data_location=str(candidate),
            )
            continue
        if root is None:
            root, chosen_as = candidate, label

    if root is None:
        return {
            "state": "unreachable",
            "total": None,
            "orders": [],
            "scan_root": None,
            "diagnostics": diagnostics
            or [
                Diagnostic(
                    Severity.WARN,
                    MORD_CATALOG_ROOT_UNAVAILABLE,
                    "no order catalog root was supplied; nothing was scanned",
                    facts=facts,
                ).to_dict()
            ],
        }

    # A source root was chosen while a different rig root was also declared.
    # Both are real roots; say which one the rows came from.
    if chosen_as != "rig_root" and rig_root is not None:
        rig_path = Path(rig_root)
        if rig_path.is_dir() and rig_path.resolve() != root.resolve():
            _note(
                Severity.INFO,
                MORD_CATALOG_ROOT_MISMATCH,
                f"{chosen_as} {root} and rig_root {rig_path} disagree; "
                f"the catalog was read from {chosen_as} only",
                data_location=str(root),
            )

    rows: list[dict[str, Any]] = []
    seen: set[Path] = set()
    for pattern in ORDER_GLOBS:
        for path in sorted(root.glob(pattern)):
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            try:
                rows.append(_order_row(path, root, rig_name))
            except (OSError, tomllib.TOMLDecodeError, AttributeError) as err:
                # One malformed file is not a dead catalog -- the same stance
                # the event log reader takes toward one malformed line.
                incomplete = True
                _note(
                    Severity.WARN,
                    MORD_CATALOG_FILE_UNREADABLE,
                    f"order definition {path.name} could not be read: {err}",
                    data_location=str(path),
                )

    rows.sort(key=lambda row: (row["name"], row["source"]))
    return {
        # `degraded` when something declared could not be read: the rows are
        # real, the catalog is not provably complete, and those differ.
        "state": "degraded" if incomplete else "healthy",
        "total": len(rows),
        "orders": rows,
        "scan_root": str(root),
        "diagnostics": diagnostics,
    }


def city_reader(city_root):
    """A reader over the live city, for the typed tool (#156).

    The event log is a local file and answers in milliseconds. The catalog is
    `gc order list`, which takes ~33 s -- roughly a third of it `gc` process
    startup, measured. That asymmetry is why the two are separate reads: an
    outcome question does not have to pay the catalog's cost.

    Every branch raises rather than returning a default. A caller that cannot
    read a surface must say so, and `orders_status` turns the exception into a
    named `unreachable` state -- never into zero orders.
    """
    import json
    import subprocess
    from pathlib import Path as _Path

    def read(what: str):
        if what == "events":
            log = _Path(city_root) / ".gc" / "events.jsonl"
            if not log.is_file():
                raise FileNotFoundError(f"no event log at {log}")
            out = []
            with log.open(errors="replace") as handle:
                for line in handle:
                    if '"order.' not in line:
                        continue
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue  # one malformed line is not a dead log
            return out
        if what == "orders":
            proc = subprocess.run(
                ["gc", "order", "list", "--json"],
                capture_output=True, text=True, cwd=str(city_root), timeout=DASHBOARD_CATALOG_TIMEOUT_SECONDS,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"gc order list exited {proc.returncode}")
            return json.loads(proc.stdout).get("orders") or []
        if what == "history":
            proc = subprocess.run(
                ["gc", "order", "history", "--json"],
                capture_output=True, text=True, cwd=str(city_root), timeout=DASHBOARD_CATALOG_TIMEOUT_SECONDS,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"gc order history exited {proc.returncode}")
            return json.loads(proc.stdout).get("entries") or []
        if what == "formulas":
            proc = subprocess.run(
                ["gc", "formula", "list"],
                capture_output=True, text=True, cwd=str(city_root), timeout=DASHBOARD_CATALOG_TIMEOUT_SECONDS,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"gc formula list exited {proc.returncode}")
            return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
        raise KeyError(what)

    return read
