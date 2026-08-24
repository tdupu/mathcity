"""Queue status: the six populations a rig's work queue is made of (#113).

The dashboard has Orders, Formulas, Molecules -- and no answer to "what is
the queue doing". This module is that answer, shaped from `bd`'s OWN
dependency-aware reads rather than a second, drifting definition of "ready"
or "blocked":

    ready_unclaimed[]  -- `bd ready --unassigned`: ready, no claim.
    blocked[]          -- `bd ready --explain`'s blocked bucket, each with
                           `blocked_on` (the dependency it waits on) taken
                           straight from bd's own `blocked_by`.
    tail[]             -- ready_unclaimed, idle past the trigger, never
                           routed. Mirrors `assets/scripts/tail-end-detector.py`'s
                           core signal (ready + unrouted + idle >3d) without
                           its scaffolding/gated/dedup refinements, which are
                           batch-classification heuristics for the auto-resling
                           pipeline and out of scope for a live status read.
    starved[]          -- blocked, idle past the SAME trigger. No existing
                           detector computes this; it is derived here by
                           reusing tail-end-detector's own >3d idle threshold
                           against the blocked bucket instead of the ready
                           one -- "blocked and stuck" is the mirror of "ready
                           and never dispatched".
    deferred[]         -- `bd list --deferred`, each with `until`
                           (`defer_until`). DELIBERATE, not accidental (#113
                           §5.8): a deferred bead is excluded from
                           blocked/starved/tail/ready_unclaimed even if it
                           would otherwise land there, because those buckets
                           mean "waiting on something nobody chose" and
                           deferred means the opposite.
    next_up[]          -- ready_unclaimed, oldest-first, capped at
                           NEXT_UP_LIMIT. `next_up_is_prediction` is ALWAYS
                           `True`: measured 2026-08-20, `work.py:185
                           ready_work()` applies no ordering logic and the
                           dispatcher passes `--sort oldest --limit=20`
                           (`workquery.go:323`/`:239`), so priority is
                           DISCARDED at dispatch. Order is reproducible but
                           arbitrary, and every consumer of this field must
                           say so rather than imply a priority queue that
                           does not exist. Computed in pure Python (not via a
                           second `bd --sort oldest` call) so the "oldest
                           first" rule stays testable without shelling out.

WHY `bd ready --explain` AND NOT A HAND-ROLLED DEPENDENCY WALK. Measured live
2026-08-24: plain `bd list --json` returns `dependency_count` (an int) but not
the `dependencies` array, and carries no `assignee`/`metadata` field at all --
so a shaper built on `bd list` alone cannot resolve blockers or claims. `bd
ready --explain --json` returns BOTH buckets in one call, each blocked row
carrying real `blocked_by` edges bd already resolved; `bd ready --unassigned`
and `bd list --deferred` are bd's own filters for claim and defer state. Using
bd's own answers means this module can never define "ready" or "blocked"
differently than `bd ready` itself does.

THREE-VALUED, PER POPULATION. `ready_explain` is the one read every other
population is scoped against; if it fails the whole tool reports
`state="unreachable"` and every population is `None` -- never `[]`, because
"we could not look" and "there is nothing here" are different facts. Each of
the three auxiliary reads (`unclaimed`, `deferred`, `routed_ids`) can fail
independently without discarding the populations that do not depend on it:
losing the ability to check claims must not also throw away a real,
successfully-read `blocked` list.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .beads import bd_timeout_seconds
from .diagnostics import Diagnostic, Severity

MQUE_QUEUE_UNREACHABLE = "MQUE_QUEUE_UNREACHABLE"
MQUE_UNCLAIMED_UNREACHABLE = "MQUE_UNCLAIMED_UNREACHABLE"
MQUE_DEFERRED_UNREACHABLE = "MQUE_DEFERRED_UNREACHABLE"
MQUE_ROUTED_UNREACHABLE = "MQUE_ROUTED_UNREACHABLE"

#: tail-end-detector.py's own trigger (`DEFAULT_MIN_IDLE_DAYS = 3`), reused
#: rather than reinvented so "idle too long" means the same thing in both
#: places this city measures it.
MIN_IDLE_SECONDS = 3 * 86400

#: The dispatcher's own limit, measured 2026-08-20 at `workquery.go:239/323`
#: (`--sort oldest --limit=20`). `next_up` mirrors it exactly so the
#: prediction is the same size as what would actually be offered.
NEXT_UP_LIMIT = 20

#: Never-dispatched == carries none of these routing keys. Identical to
#: `tail-end-detector.py`'s `ROUTED_METADATA_KEYS`, scoped here to one rig via
#: plain `bd list --has-metadata-key` (that detector's cross-rig
#: `gc bd list --has-metadata-key` is a city-wide concern this rig-scoped tool
#: does not have).
ROUTED_METADATA_KEYS = ("gc.routed_to", "gc.run_target", "gc.execution_routed_to")


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _idle_seconds(row: Mapping[str, Any], now: datetime) -> float | None:
    stamps = (row.get("created_at"), row.get("updated_at"))
    parsed = [ts for ts in (_parse_ts(s) for s in stamps) if ts is not None]
    if not parsed:
        return None
    return (now - max(parsed)).total_seconds()


def _ready_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {"bead_id": row.get("id"), "title": row.get("title"), "priority": row.get("priority")}


def _blocked_row(row: Mapping[str, Any]) -> dict[str, Any]:
    blockers = row.get("blocked_by") or []
    first = blockers[0] if blockers else {}
    if not isinstance(first, Mapping):
        first = {}
    return {
        "bead_id": row.get("id"),
        "title": row.get("title"),
        "blocked_on": first.get("id"),
        "blocked_on_title": first.get("title"),
    }


def _deferred_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "bead_id": row.get("id"),
        "title": row.get("title"),
        "until": row.get("defer_until") or row.get("deferred_until"),
    }


def _unreachable(err: Exception) -> dict[str, Any]:
    """The core read failed. Every population is `None`, never `[]`."""
    return {
        "state": "unreachable",
        "ready_unclaimed": None,
        "blocked": None,
        "tail": None,
        "starved": None,
        "deferred": None,
        "next_up": None,
        "next_up_is_prediction": True,
        "diagnostics": [
            Diagnostic(
                Severity.WARN,
                MQUE_QUEUE_UNREACHABLE,
                f"bd ready --explain unavailable: {err}",
            ).to_dict()
        ],
    }


def queue_status(read: Callable[[str], Any], *, now: datetime | None = None) -> dict[str, Any]:
    """The QUEUE column: six populations, each a real measurement or `None`."""
    now = now or datetime.now(timezone.utc)

    try:
        explain = read("ready_explain") or {}
    except Exception as err:  # noqa: BLE001 -- any read failure is "we could not look"
        return _unreachable(err)

    ready_rows = list(explain.get("ready") or [])
    blocked_rows = list(explain.get("blocked") or [])
    diagnostics: list[dict] = []

    try:
        deferred_rows = list(read("deferred"))
    except Exception as err:  # noqa: BLE001
        deferred_rows = None
        diagnostics.append(
            Diagnostic(
                Severity.WARN,
                MQUE_DEFERRED_UNREACHABLE,
                f"bd list --deferred unavailable: {err}",
            ).to_dict()
        )

    if deferred_rows is None:
        deferred: list[dict[str, Any]] | None = None
        deferred_ids: set[str] = set()
    else:
        deferred = [_deferred_row(row) for row in deferred_rows]
        deferred_ids = {row.get("id") for row in deferred_rows if row.get("id")}

    # Deliberate != accidental (#113 §5.8): a bead deliberately parked with a
    # future `defer_until` must not also read as stuck.
    blocked_rows = [row for row in blocked_rows if row.get("id") not in deferred_ids]
    blocked = [_blocked_row(row) for row in blocked_rows]
    starved = [
        {**_blocked_row(row), "idle_seconds": _idle_seconds(row, now)}
        for row in blocked_rows
        if (_idle_seconds(row, now) or 0.0) >= MIN_IDLE_SECONDS
    ]

    try:
        unclaimed_rows = [row for row in read("unclaimed") if row.get("id") not in deferred_ids]
    except Exception as err:  # noqa: BLE001
        unclaimed_rows = None
        diagnostics.append(
            Diagnostic(
                Severity.WARN,
                MQUE_UNCLAIMED_UNREACHABLE,
                f"bd ready --unassigned unavailable: {err}",
            ).to_dict()
        )

    if unclaimed_rows is None:
        ready_unclaimed: list[dict[str, Any]] | None = None
        next_up: list[dict[str, Any]] | None = None
        tail: list[dict[str, Any]] | None = None
    else:
        ready_unclaimed = [_ready_row(row) for row in unclaimed_rows]
        next_up_rows = sorted(unclaimed_rows, key=lambda row: row.get("created_at") or "")[:NEXT_UP_LIMIT]
        next_up = [_ready_row(row) for row in next_up_rows]
        try:
            routed_ids = set(read("routed_ids"))
        except Exception as err:  # noqa: BLE001
            tail = None
            diagnostics.append(
                Diagnostic(
                    Severity.WARN,
                    MQUE_ROUTED_UNREACHABLE,
                    f"routed-metadata lookup unavailable: {err}",
                ).to_dict()
            )
        else:
            tail = [
                _ready_row(row)
                for row in unclaimed_rows
                if row.get("id") not in routed_ids and (_idle_seconds(row, now) or 0.0) >= MIN_IDLE_SECONDS
            ]

    return {
        "state": "healthy" if not diagnostics else "degraded",
        "ready_unclaimed": ready_unclaimed,
        "blocked": blocked,
        "tail": tail,
        "starved": starved,
        "deferred": deferred,
        "next_up": next_up,
        "next_up_is_prediction": True,
        "diagnostics": diagnostics,
    }


def city_reader(rig_root) -> Callable[[str], Any]:
    """A reader over the live rig's `bd` store, for the typed tool.

    Every branch raises rather than returning a default -- `queue_status`
    turns each exception into the named degradation for that population, and
    a reader that swallowed failures here would turn "we could not look" back
    into a silent empty list.
    """
    import json
    import subprocess

    def _bd(args: list[str]) -> Any:
        try:
            proc = subprocess.run(
                ["bd", *args],
                cwd=str(rig_root),
                capture_output=True,
                text=True,
                timeout=bd_timeout_seconds(),
            )
        except (OSError, subprocess.TimeoutExpired) as err:
            raise RuntimeError(f"bd {' '.join(args)} could not run: {err}") from err
        if proc.returncode != 0:
            raise RuntimeError(f"bd {' '.join(args)} exited {proc.returncode}: {proc.stderr.strip()}")
        try:
            return json.loads(proc.stdout or "null")
        except ValueError as err:
            raise RuntimeError(f"bd {' '.join(args)} returned invalid JSON: {err}") from err

    def read(what: str) -> Any:
        if what == "ready_explain":
            return _bd(["ready", "--explain", "--json", "--limit", "0"])
        if what == "unclaimed":
            data = _bd(["ready", "--unassigned", "--json", "--limit", "0"])
            return data if isinstance(data, list) else []
        if what == "deferred":
            data = _bd(["list", "--all", "--deferred", "--json", "--limit", "0", "--readonly"])
            return data if isinstance(data, list) else []
        if what == "routed_ids":
            ids: set[str] = set()
            for key in ROUTED_METADATA_KEYS:
                data = _bd(
                    ["list", "--all", "--has-metadata-key", key, "--json", "--limit", "0", "--readonly"]
                )
                for row in data if isinstance(data, list) else ():
                    bead_id = row.get("id")
                    if bead_id:
                        ids.add(bead_id)
            return ids
        raise KeyError(what)

    return read
