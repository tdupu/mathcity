"""The Orders and Formulas screen (#117).

Two of the three nouns asked for by name. The screen's one opinionated choice:
**the outcome column says `unknown` for every order, including the ones that
have run**, because `gc order history` records that an order executed and never
whether it succeeded (#156).

That column will look broken. A tick or a blank would look fine and would be a
claim the city cannot support -- and a blank cell reads as "fine" to everyone
who has ever seen a table.
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


def orders_table(payload: Mapping[str, Any]) -> str:
    if payload.get("state") == "unreachable":
        reason = (payload.get("diagnostics") or ["no reason recorded"])[0]
        return unreachable_note("Orders", reason)

    rows: Sequence[Mapping[str, Any]] = payload.get("orders") or []
    if not rows:
        return '<p class="review-note">No orders are registered in this city.</p>'

    body = "\n".join(
        "<tr>"
        f'<td class="mono">{_e(r.get("name"))}</td>'
        f"<td>{_e(r.get('type'))}</td>"
        f"<td>{_e(r.get('trigger'))}</td>"
        f"<td>{_e(r.get('interval') or '—')}</td>"
        f"<td>{_e(r.get('last_executed') or 'never')}</td>"
        f'<td class="mono">{_e(r.get("last_outcome"))}</td>'
        "</tr>"
        for r in rows
    )
    ran = payload.get("ran_at_least_once", 0)
    total = payload.get("total", len(rows))
    return (
        f'<p class="review-note" data-region="orders-outcome-note">'
        f"<strong>{total} orders · {ran} have executed · "
        f"{payload.get('outcome_recorded', 0)} outcomes recorded.</strong> "
        "The city logs that an order ran, never whether it succeeded, so every "
        "outcome below is <span class=\"mono\">unknown</span> — including for "
        "orders that have run. That is the true reading, not a rendering fault "
        "(see the outcome-recorder issue).</p>"
        '<div class="scroll-x"><table data-region="orders-table">'
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
