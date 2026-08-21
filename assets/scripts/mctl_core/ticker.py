"""The ticker's derived vocabulary: tiers, and cause/response pairing.

Handoff §3.7. This is deliberately **its own view**, not an alias for bells,
event beads, or the raw log. Many bells are internal plumbing nobody wants to
watch, and the most watchable things emit no bell at all.

WHY `bead.updated` IS CHATTER, AND WHY THE ISSUE'S PREMISE NEEDED CORRECTING.
`#116` justified a chatter tier with "order firings alone are ~2,400/day".
Measured over `<city>/.gc/events.jsonl`, 2026-08-13..2026-08-20, 8 distinct
days, 63,107 events:

    bead.updated   33,351   4,169/day   52.8%
    order.fired     3,130     391/day    5.0%
    all order.*     7,944     772/day   12.6%

`order.fired` is ~391/day, not 2,400, and `bead.updated` outweighs all order
events by roughly 5:1. A chatter tier scoped to order firings would suppress
5% of the stream and leave half of it in place. The ratio is the durable part;
the six rotated archives were not examined, so a busier window could plausibly
reach the cited figure.

UNKNOWN IS NOT A TIER, AND IS NEVER HIDDEN. Honesty invariant 2 -- "`None`
means there is none; `Unknown` means we did not look" -- applies to
classification, not only to probes. An event type this module has never been
told about is `Unknown`, and `Unknown` survives the default filter. Defaulting
it to `chatter` would make every newly-introduced event type vanish from the
default view without anyone deciding that, which is precisely the silent
disappearance the tiering exists to prevent.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

#: The four tiers the page renders. `Unknown` is deliberately not among them.
TIERS: tuple[str, ...] = ("alarm", "milestone", "progress", "chatter")

#: Distinct from every tier and from None: we have not classified this type.
UNKNOWN_TIER = "unknown"

#: Off by default -- the only tier that is.
DEFAULT_HIDDEN: frozenset[str] = frozenset({"chatter"})

#: Event type -> tier. Absent means Unknown, never a default bucket.
TIER_BY_TYPE: dict[str, str] = {
    # alarm: something is wrong and a human would want to know now.
    "order.failed": "alarm",
    "execution.claim_window_expired": "alarm",
    # milestone: real work finished.
    "bead.closed": "milestone",
    "execution.step_completed": "milestone",
    # progress: the machine is turning over.
    "order.fired": "progress",
    "order.completed": "progress",
    "bead.created": "progress",
    "execution.step_defined": "progress",
    "session.woke": "progress",
    "session.stopped": "progress",
    # chatter: high-volume bookkeeping. See the module docstring for the counts.
    "bead.updated": "chatter",
    "bead.deleted": "chatter",
    "events.rotated": "chatter",
}

#: A cause is an event that should produce a response. The pairing is the
#: proof-of-life mechanism: a cause with no response is a visible break in the
#: chain, and more informative than either event alone.
CAUSE_TYPES: frozenset[str] = frozenset({"order.fired"})
RESPONSE_TYPES: dict[str, frozenset[str]] = {
    "order.fired": frozenset({"order.completed", "order.failed"}),
}


def tier_of(event_type: str) -> str:
    """Tier for an event type, or UNKNOWN_TIER if we have never classified it."""
    return TIER_BY_TYPE.get(event_type, UNKNOWN_TIER)


def select(
    rows: Iterable[Mapping[str, Any]],
    *,
    include_chatter: bool = False,
    tiers: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Filter to the tiers a caller wants. Unknown always survives.

    `include_chatter` is the documented default-off switch. `tiers` is an
    explicit allowlist for callers that want one band; when given, it is
    honoured exactly, including the ability to ask for chatter alone.
    """
    wanted = set(tiers) if tiers is not None else set(TIERS)
    if tiers is None and not include_chatter:
        wanted -= DEFAULT_HIDDEN
    out: list[dict[str, Any]] = []
    for row in rows:
        tier = tier_of(str(row.get("type", "")))
        # Unknown bypasses the filter on purpose: hiding an unclassified type
        # is how a new event goes unnoticed for a week.
        if tier is UNKNOWN_TIER or tier == UNKNOWN_TIER or tier in wanted:
            out.append({**row, "tier": tier})
    return out


def pair_causes(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Pair each cause with the responses that followed it on the same subject.

    A response must share the cause's `subject` AND occur at or after it. Both
    conditions matter: matching on subject alone would let an earlier
    completion answer a later firing, which reports a chain as healthy when
    the firing in fact produced nothing.

    `unanswered` is an explicit boolean rather than an absent key, because
    "this cause produced nothing" is a fact we established, not a lookup we
    skipped.
    """
    ordered = sorted(rows, key=lambda r: str(r.get("ts", "")))
    pairs: list[dict[str, Any]] = []
    for index, row in enumerate(ordered):
        cause_type = str(row.get("type", ""))
        if cause_type not in CAUSE_TYPES:
            continue
        wanted = RESPONSE_TYPES.get(cause_type, frozenset())
        subject = row.get("subject")
        responses = [
            later
            for later in ordered[index + 1:]
            if str(later.get("type", "")) in wanted and later.get("subject") == subject
        ]
        pairs.append({
            "cause": dict(row),
            "response": [dict(r) for r in responses],
            "unanswered": not responses,
        })
    return pairs


def page(rows: Iterable[Mapping[str, Any]], *, limit: int) -> dict[str, Any]:
    """One page, stating its size and whether it truncated.

    Honesty invariants 9 and 10: every list states its page size and says when
    it truncated, and `available` is the denominator the count came from -- so
    a caller can never read a short page as a small population.
    """
    materialized = list(rows)
    returned = materialized[:limit]
    return {
        "events": returned,
        "page_size": limit,
        "returned": len(returned),
        "available": len(materialized),
        "truncated": len(materialized) > limit,
    }
