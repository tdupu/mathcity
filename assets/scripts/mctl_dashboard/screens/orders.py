"""The Orders and Formulas screen (#117 / mc-0mhh).

Two of the three nouns asked for by name. The screen's opinionated choices:

**Health is the terminal outcome, never recency.** `orders_status` folds the
event log (`order.completed` / `order.failed`); an order that fired punctually
and never completed is `unknown`, not green. A tick or a blank would look fine
and would be a claim the city cannot support -- a blank cell reads as "fine" to
everyone who has ever seen a table.

**`unknown` means "no terminal event", not "fine".** The earlier version of
this screen claimed EVERY outcome was unknown; that was true only while the
reader ignored the event log (#156). Now `unknown` is per-order and specific:
the event log has no `completed`/`failed` for that registered order.

**An unreadable catalog is an unknown denominator, never zero orders** (§5.4):
`state == "unreachable"` renders a reason, and the failing count still shows if
the event log answered even when the catalog did not.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


def _e(text: Any) -> str:
    return (
        str("" if text is None else text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def unreachable_note(what: str, reason: str) -> str:
    """A read that could not run. Never a zero -- see §5.4."""
    return (
        f'<p class="review-note" data-region="{_e(what)}-unreachable">'
        f"<strong>{_e(what)} could not be read.</strong> {_e(reason)} "
        "This is not a count of zero; the surface did not answer.</p>"
    )


def _outcome_cell(outcome: Any) -> str:
    """Render one order's terminal outcome, marking a failure distinctly.

    Never a tick and never blank: `completed`, `failed`, `unknown` are all
    words, because a blank cell reads as "fine". `failed` carries a data-flag so
    the operator's eye lands on it, but nothing here paints an order green from
    having merely run.
    """
    text = str(outcome or "unknown")
    flag = "failed" if text == "failed" else ("completed" if text == "completed" else "unknown")
    return f'<td class="mono" data-outcome="{_e(flag)}">{_e(text)}</td>'


def _order_name_cell(row: Mapping[str, Any]) -> str:
    """The order's name, plus its scoped name when the two differ.

    A scoped order (`pack:brief-gate-keep`) and its bare name are different
    facts; showing only one hides which registration this row is."""
    name = str(row.get("name") or "")
    scoped = str(row.get("scoped_name") or "")
    if scoped and scoped != name:
        return (
            f'<td class="mono">{_e(name)}'
            f'<span style="color: var(--color-neutral-500); font-size: 10.5px; '
            f'margin-left: 6px;">{_e(scoped)}</span></td>'
        )
    return f'<td class="mono">{_e(name)}</td>'


def _outcome_summary(payload: Mapping[str, Any], *, total: Any) -> str:
    """The count line above the table: total, executed, recorded, failing."""
    ran = payload.get("ran_at_least_once", 0)
    recorded = payload.get("outcome_recorded", 0)
    failing = payload.get("failing", 0)
    total_text = "unknown" if total is None else str(total)
    failing_html = (
        f'<span data-region="orders-failing" data-failing="{_e(failing)}">'
        f"{_e(failing)} failing</span>"
    )
    return (
        f'<p class="review-note" data-region="orders-outcome-note">'
        f"<strong>{_e(total_text)} orders · {_e(ran)} have executed · "
        f"{_e(recorded)} outcomes recorded · {failing_html}.</strong> "
        "Outcome is the terminal event-log verdict "
        '(<span class="mono">order.completed</span> / '
        '<span class="mono">order.failed</span>). '
        '<span class="mono">unknown</span> means no terminal event is recorded '
        "for that order — health is the outcome, never recency, so a punctual "
        "order that has never completed is not green.</p>"
    )


def orders_table(payload: Mapping[str, Any]) -> str:
    if payload.get("state") == "unreachable":
        reason = (payload.get("diagnostics") or ["no reason recorded"])[0]
        note = unreachable_note("Orders", reason)
        # The catalog did not answer, so the denominator (how many orders exist)
        # is unknown -- NOT zero. But the event log is a local file and may have
        # answered even when `gc order list` did not, so any outcomes it did
        # yield are still worth showing, with the count line reading the total as
        # `unknown` rather than pretending there are none.
        if payload.get("outcome_recorded") or payload.get("known_outcomes"):
            return note + _outcome_summary(payload, total=None)
        return note

    rows: Sequence[Mapping[str, Any]] = payload.get("orders") or []
    if not rows:
        return '<p class="review-note">No orders are registered in this city.</p>'

    body = "\n".join(
        "<tr>"
        + _order_name_cell(r)
        + f"<td>{_e(r.get('type'))}</td>"
        f"<td>{_e(r.get('trigger'))}</td>"
        f"<td>{_e(r.get('interval') or '—')}</td>"
        f"<td>{_e(r.get('last_executed') or 'never')}</td>"
        + _outcome_cell(r.get("last_outcome"))
        + "</tr>"
        for r in rows
    )
    return (
        _outcome_summary(payload, total=payload.get("total", len(rows)))
        + '<div class="scroll-x"><table data-region="orders-table">'
        "<thead><tr><th>Order</th><th>Type</th><th>Trigger</th>"
        "<th>Interval</th><th>Last executed</th><th>Last outcome</th></tr></thead>"
        f"<tbody>{body}</tbody></table></div>"
    )


def formulas_list(payload: Mapping[str, Any]) -> str:
    if payload.get("state") == "unreachable":
        reason = (payload.get("diagnostics") or ["no reason recorded"])[0]
        return unreachable_note("Formulas", reason)

    rows: Sequence[Mapping[str, Any]] = payload.get("formulas") or []
    if not rows:
        return '<p class="review-note">No formulas are registered in this city.</p>'

    items = "\n".join(f'<li class="mono">{_e(f.get("name"))}</li>' for f in rows)
    return (
        f'<p class="review-note"><strong>{payload.get("total", len(rows))} formulas.</strong></p>'
        f'<ul data-region="formulas-list">{items}</ul>'
    )
