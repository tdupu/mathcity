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
#: handle), so the pool is small. Three is the widest fan-out any current page
#: performs.
MAX_SIBLINGS = 3

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

    # The primary client handles one spec; siblings take the rest. If no
    # sibling could be made, everything still runs -- just serialized, which is
    # exactly the behaviour we had before.
    pool = _pool_for(client, len(specs) - 1)
    workers = [client] + pool
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
