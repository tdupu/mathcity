"""The priority list: the operator's own ordering over the stack.

This is the one screen whose state deliberately does **not** live in the bead
store. No policy defines importance -- the design says so itself, calling the
score "a working hypothesis" -- so persisting one clerk's ordering server-side
would make an experiment look like a fact about briefs. It lives in the
browser, and the screen says so rather than leaving the operator to discover
it when they open the dashboard elsewhere.

Same reasoning for verdict drafts, and it also dissolves a standing objection.
The implementation plan recorded "no canonical store for either; adding one
would be new domain state invented at the presentation layer". A draft is not
domain state -- it is browser state on a single-operator loopback tool -- so
there is nothing to invent.

**Reordering has a no-JavaScript baseline.** Drag-and-drop is the enhancement;
move-up and move-down are ordinary links carrying the whole order in the query
string, so the list is reorderable with scripting off. `reorder` is the pure
function both paths share, which is also why the prototype's off-by-one is not
reproduced here: its splice removed before inserting, so a downward drag landed
one slot short of where the reader aimed.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence
from urllib.parse import urlencode

from mctl_dashboard.render import esc as _e


def reorder(order: Sequence[str], bead_id: str, direction: str) -> list[str]:
    """Move one id one place, returning a new order.

    Moving the first item up, or the last down, is a no-op rather than an
    error: the links are rendered on every row, and a reader who clicks the
    one at the boundary has not done anything wrong.

    An unknown id is also a no-op -- a stale link from a list that has since
    changed must not raise.
    """
    items = list(order)
    if bead_id not in items:
        return items
    index = items.index(bead_id)
    target = index - 1 if direction == "up" else index + 1
    if target < 0 or target >= len(items):
        return items
    items[index], items[target] = items[target], items[index]
    return items


def _move_link(order: Sequence[str], bead_id: str, direction: str, label: str) -> str:
    query = urlencode({"order": ",".join(reorder(order, bead_id, direction))})
    return (
        f'<a href="/priority?{query}" class="mono" '
        'style="font-size: 10.5px; color: var(--color-accent-700);">'
        f"{_e(label)}</a>"
    )


def screen(briefs: Sequence[Mapping[str, Any]]) -> str:
    """The priority list, in the operator's own order."""
    heading = (
        '<h1 style="font-family: var(--font-heading); font-size: 27px; '
        'font-weight: 600; margin: 0 0 2px;">My priority list</h1>'
    )

    if not briefs:
        return (
            '<section data-region="priority">'
            + heading
            + '<div class="mono" style="font-size: 11.5px; '
            'color: var(--color-neutral-600);">empty · add briefs from the stack</div>'
            '<div style="height: 2px; background: var(--color-neutral-900); '
            'margin: 9px 0 16px;"></div>'
            '<div style="border: 1px dashed var(--color-neutral-400); '
            "border-radius: var(--radius-md); padding: 26px 22px; max-width: 620px; "
            'text-align: center;">'
            '<h2 style="font-size: 19px; margin: 0 0 8px;">Nothing here yet</h2>'
            '<p style="max-width: 430px; margin: 0 auto 14px; font-size: 13px; '
            'color: var(--color-neutral-700); text-wrap: pretty;">'
            "Your priority list starts empty. Add briefs from the stack, then put "
            "them in the order you actually want to work — this is your ordering, "
            "not the pipeline's, and nothing here changes pipeline state.</p>"
            '<a class="btn btn-primary" href="/queue">Go to the stack &rarr;</a>'
            "</div></section>"
        )

    order = [str(brief.get("bead_id") or "") for brief in briefs]
    rows = []
    for position, brief in enumerate(briefs):
        bead = str(brief.get("bead_id") or "")
        rows.append(
            '<div class="mc-row" draggable="true" data-bead="' + _e(bead) + '" '
            'style="display: flex; align-items: baseline; gap: 11px; padding: 9px 12px; '
            "border: 1px solid var(--color-divider); border-radius: var(--radius-md); "
            'background: var(--color-neutral-100); margin-bottom: 7px;">'
            '<span class="mono" style="font-size: 11px; color: var(--color-neutral-500); '
            'cursor: grab;">&#10287;</span>'
            f'<span class="mono" style="font-size: 12px; color: var(--color-accent-700); '
            f'width: 20px;">{position + 1}</span>'
            f'<a href="/briefs/{_e(brief.get("brief_id") or bead)}" '
            'style="font-family: var(--font-heading); font-size: 15px; font-weight: 600; '
            f'flex: 1 1 auto; color: var(--color-text);">{_e(brief.get("title"))}</a>'
            + _move_link(order, bead, "up", "move up")
            + _move_link(order, bead, "down", "move down")
            + "</div>"
        )

    return (
        '<section data-region="priority">'
        + heading
        + f'<div class="mono" style="font-size: 11.5px; color: var(--color-neutral-600);">'
        f"{len(briefs)} briefs · your own ordering</div>"
        '<div style="height: 2px; background: var(--color-neutral-900); '
        'margin: 9px 0 16px;"></div>'
        '<p class="lede" style="max-width: 620px;">This is <strong>your own '
        "ordering</strong>, not a fact about the briefs — no policy defines "
        "importance, so nothing here changes pipeline state. It is kept in "
        "<strong>this browser</strong> and will not follow you to another machine.</p>"
        '<div style="max-width: 780px;">' + "".join(rows) + "</div>"
        "</section>"
    )
