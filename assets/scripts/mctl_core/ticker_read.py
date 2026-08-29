"""The city ticker READER: recent events, tiered, with cause/response pairing (#116).

NAMED `ticker_read`, NOT `events`. `mctl_core/events.py` already exists and is
the trace/event WRITE helper (`append_jsonl`), imported by `trace.py`; taking
that name would have shadowed it and broken every import in the package. This
module sits beside `ticker.py`, whose vocabulary it serves, and the pairing is
read-side only.

`mctl_core/ticker.py` has held the derived vocabulary -- tiers, the
default-hidden chatter band, and the cause/response pairing -- since it was
written, and it is tested. What it never had was a way IN: no reader, and no
MCP tool. The dashboard's Events panel therefore rendered
`city_screen.unwired()`, saying in as many words *"Built, and not reachable
from any page ... the MCP tool surface is the only way this dashboard can
reach data. So there is nothing for this screen to call."*

This module is the way in. It reads the event log directly, exactly as
`orders.py` and `costs.py` do, rather than shelling to `gc` -- the log is a
local file and `gc order list` measures ~89 s in-city (#156).

## THE TAIL, AND WHY THE DENOMINATOR IS NAMED

The live log measured **218 MB** on 2026-08-29. Parsing all of it per request
is not servable, so this reads a bounded TAIL.

That makes every count here a count *within the scanned window*, not within
the log. Reporting `available` from `ticker.page` without saying so would be a
denominator lie of exactly the kind #124 names -- "every figure is a FLOOR" --
and the kind #129 found when a rig table hid a partial rig's counts while
claiming the total was the sum of its rows.

So the payload always carries `scan`: how many bytes the log holds, how many
were read, and `truncated`. When the scan is truncated a WARN says the counts
describe the window. A caller can then treat them as a floor, which they are.

## WHY A TICKER IS ALLOWED TO BE A TAIL AT ALL

A ticker answers "what is happening now". Recency is its whole contract, so a
bounded recent window is the honest shape rather than a compromise -- unlike a
conservation count, where a truncated scan would be a wrong answer to the
question asked. The window is generous by default and configurable, and the
truncation is stated rather than inferred.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .diagnostics import Diagnostic, Severity
from . import ticker

#: Bytes of the event log tail to parse. ~8 MB covered roughly 12 hours of a
#: busy city when measured (159-456 events/hour, 2026-08-29), which is a
#: generous window for a "what is happening now" view while staying far below
#: the cost of the whole 218 MB file.
DEFAULT_TAIL_BYTES = 8_000_000

#: Rows returned when the caller names no limit.
DEFAULT_LIMIT = 100

MEVT_EVENTS_UNREACHABLE = "MEVT_EVENTS_UNREACHABLE"
MEVT_SCAN_TRUNCATED = "MEVT_SCAN_TRUNCATED"


def city_reader(city_root: Any, *, tail_bytes: int = DEFAULT_TAIL_BYTES) -> Callable[[str], Any]:
    """A reader over the live city's event log.

    Raises rather than returning a default on every failure path: a caller that
    cannot read the log must say `unreachable`, never "no events". An empty
    city and an unreadable one are different answers and this refuses to
    conflate them.
    """

    def read(what: str) -> Any:
        if what != "events":
            raise KeyError(what)
        log = Path(city_root) / ".gc" / "events.jsonl"
        if not log.is_file():
            raise FileNotFoundError(f"no event log at {log}")
        size = log.stat().st_size
        truncated = size > tail_bytes
        with log.open("rb") as handle:
            if truncated:
                handle.seek(size - tail_bytes)
                # The seek lands mid-line. Discard that fragment rather than
                # feeding a half-object to the parser, where it would be
                # counted as one malformed line and quietly dropped -- correct
                # either way, but this makes the intent explicit.
                handle.readline()
            raw = handle.read()
        rows: list[dict[str, Any]] = []
        malformed = 0
        for line in raw.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                malformed += 1  # one bad line is not a dead log
        return {
            "rows": rows,
            "log_bytes": size,
            "scanned_bytes": min(size, tail_bytes),
            "truncated": truncated,
            "malformed_lines": malformed,
        }

    return read


def _unreachable(err: Exception) -> dict[str, Any]:
    """The log could not be read. Every population is `None`, never `[]`."""
    return {
        "state": "unreachable",
        "events": None,
        "unanswered_causes": None,
        "page_size": None,
        "returned": None,
        "available_in_scan": None,
        "truncated": None,
        "scan": None,
        "diagnostics": [
            Diagnostic(
                Severity.WARN,
                MEVT_EVENTS_UNREACHABLE,
                f"city event log unavailable: {err}",
            ).to_dict()
        ],
    }


def events_list(
    read: Callable[[str], Any],
    *,
    limit: int = DEFAULT_LIMIT,
    include_chatter: bool = False,
    tiers: Any = None,
) -> dict[str, Any]:
    """Recent events, newest first, tiered, with unanswered causes named.

    `include_chatter` is off by default, matching `ticker.DEFAULT_HIDDEN`.
    UNKNOWN-tier events always survive the filter -- `ticker.select` enforces
    that, and it is why a newly-introduced event type cannot silently vanish
    from the default view.

    `unanswered_causes` is computed over the WHOLE scanned window rather than
    the returned page: a cause is unanswered relative to everything that
    followed it, and pairing only within one page would invent breaks at every
    page boundary.
    """
    try:
        payload = read("events")
    except Exception as err:  # noqa: BLE001 -- any read failure is "we could not look"
        return _unreachable(err)

    rows = list(payload.get("rows") or ())
    diagnostics: list[dict[str, Any]] = []

    selected = ticker.select(rows, include_chatter=include_chatter, tiers=tiers)
    # Newest first: a ticker is read from the top. `ts` sorts lexically because
    # the log writes RFC3339; a row missing `ts` sorts last rather than raising,
    # because an undateable event is still an event the operator should see.
    selected.sort(key=lambda row: str(row.get("ts") or ""), reverse=True)
    page = ticker.page(selected, limit=limit)

    unanswered = [pair for pair in ticker.pair_causes(rows) if pair.get("unanswered")]

    if payload.get("truncated"):
        diagnostics.append(
            Diagnostic(
                Severity.WARN,
                MEVT_SCAN_TRUNCATED,
                (
                    f"Read the last {payload.get('scanned_bytes')} of "
                    f"{payload.get('log_bytes')} bytes. Counts describe that window, "
                    "not the whole log -- treat them as a floor."
                ),
            ).to_dict()
        )

    return {
        "state": "healthy" if not diagnostics else "degraded",
        "events": page["events"],
        "page_size": page["page_size"],
        "returned": page["returned"],
        # Deliberately NOT called `available`: it is the count within the
        # scanned window. Naming it `available` would invite a reader to treat
        # a tail as the population (#124).
        "available_in_scan": page["available"],
        "truncated": page["truncated"],
        "unanswered_causes": unanswered,
        "tiers": list(ticker.TIERS),
        "chatter_included": bool(include_chatter),
        "scan": {
            "log_bytes": payload.get("log_bytes"),
            "scanned_bytes": payload.get("scanned_bytes"),
            "truncated": bool(payload.get("truncated")),
            "malformed_lines": payload.get("malformed_lines", 0),
        },
        "diagnostics": diagnostics,
    }
