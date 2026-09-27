"""Overlap independent core reads instead of queueing them.

A page that needs three independent facts about a brief was paying for them
one after another. The cost was not the work -- it was the transport: a stdio
client holds a lock around the whole request/response exchange, because one
pipe cannot carry two conversations. So three 4-second reads cost 13 seconds
of wall clock for 4 seconds of latency.

The fix is more pipes, not fewer locks. `fan_out` borrows sibling connections
from a pool for the duration of one page render, runs the reads concurrently,
and returns results **in the order they were asked for** so callers can unpack
positionally.

Two deliberate properties:

**A failed read rides along rather than raising.** The caller gets the
exception in the slot where the result would have been and decides what to
render. One unreadable fact should degrade one panel, not blank the page --
the same reasoning as the degraded-rig row: a thing you could not read must
appear as a thing you could not read.

**One spec does not build a pool.** The overwhelmingly common case is a single
call, and it goes straight down the primary client with no thread and no
sibling.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Mapping, Sequence

#: Sibling connections are expensive (each is a process holding a store
#: handle), so the pool stays small.
#:
#: This said "Three is the widest fan-out any current page performs" and that
#: had gone stale: `_city_operations` fans out EIGHT surfaces (fleet_sessions,
#: city_health, gates_status, blast_radius_registry, queue_status,
#: costs_summary, worktrees_status, events_list), plus `context_rigs` when a
#: panel is deferred. So the widest fan-out is nine, not three, and `/city` was
#: running four-way concurrent while asking for eight.
#:
#: Four, not nine, and deliberately. `/city` keeps the same four-way concurrency
#: it already had -- this buys the fix below, not extra width. Raising it
#: further multiplies processes against a call that is slow because `gc` times
#: out (#159), which is four slow pages instead of one, exactly as #244 warned.
MAX_SIBLINGS = 4

#: The pool lives ON the client, not in a module-level registry keyed by
#: `id()`. CPython reuses ids once an object is collected, so an id-keyed
#: registry can hand a fresh client the siblings of a dead one -- connections
#: to a process that has already exited. Storing them as an attribute ties
#: their lifetime to the client's, which is what we actually meant.
_POOL_ATTR = "_mctl_fanout_siblings"

_lock = threading.Lock()


def _pool_for(client: Any, wanted: int) -> list[Any]:
    """Siblings for `client`, created once and reused for that client's life."""
    if not hasattr(client, "clone"):
        return []
    with _lock:
        try:
            pool = getattr(client, _POOL_ATTR)
        except AttributeError:
            pool = []
            try:
                setattr(client, _POOL_ATTR, pool)
            except (AttributeError, TypeError):
                # Slotted or frozen client -- run serialized rather than fail.
                return []
        while len(pool) < min(wanted, MAX_SIBLINGS):
            try:
                pool.append(client.clone())
            except Exception:  # pragma: no cover - a sibling is an optimisation
                break
        return list(pool)


def fan_out(
    client: Any, specs: Sequence[tuple[str, Mapping[str, Any] | None]]
) -> list[Any]:
    """Run `specs` concurrently; return results positionally.

    Each entry is `(tool_name, arguments)`. A spec whose call raises yields the
    exception object in its slot rather than propagating.
    """
    if not specs:
        return []
    if len(specs) == 1:
        name, arguments = specs[0]
        try:
            return [client.call(name, arguments)]
        except Exception as exc:  # noqa: BLE001 - handed back to the caller
            return [exc]

    # SIBLINGS ONLY, when there are any. The primary client is the one every
    # OTHER request on the dashboard shares, and it holds a lock around each
    # exchange -- so any spec placed on it blocks every concurrent page for that
    # spec's duration.
    #
    # This is #244's measured 36x: `/queue` costs ~1.8s idle and 65s during a
    # `/city` render. `_city_operations` lists `fleet_sessions` FIRST, it takes
    # 60.0s because `gc` times out (#159), and `index % len(workers)` put index 0
    # on the primary every time. So a concurrent `/queue` waited behind a 60s
    # call on a shared pipe -- 60s of the measured 65s, arrived at from the
    # assignment rule rather than from any property of `/queue`.
    #
    # Falling back to the primary when NO sibling could be made is the
    # documented behaviour and stays: serialized is worse than concurrent and
    # far better than not running.
    pool = _pool_for(client, len(specs))
    workers = pool or [client]
    results: list[Any] = [None] * len(specs)

    def _run(index: int) -> None:
        name, arguments = specs[index]
        worker = workers[index % len(workers)]
        try:
            results[index] = worker.call(name, arguments)
        except Exception as exc:  # noqa: BLE001 - handed back to the caller
            results[index] = exc

    with ThreadPoolExecutor(max_workers=len(specs)) as pool_exec:
        list(pool_exec.map(_run, range(len(specs))))
    return results
