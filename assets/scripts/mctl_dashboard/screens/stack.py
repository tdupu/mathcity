"""The brief stack: the dense sortable table the operator works from.

Thirteen columns, nine on by default, sortable by clicking a heading. Sorting
and column toggling are a link and a GET form respectively, so the table is
fully operable with JavaScript disabled; the j/k cursor is the only part that
needs script, and it duplicates clicking.

A note on honesty, because it shapes most of this module: `briefs_list`
supplies bead identity, title, status, decision state, labels, timestamps and
redundant-artifact state. It does **not** supply unlock_count, priority, brief
type, option count, or a recommendation -- the design assumes all five and the
core exposes none of them yet (issue #66). All five are agreed to be worth
building; `Producer` was the sixth and is dropped, because nothing records
which formula filed a brief.
Rather than inventing plausible values or quietly dropping the columns, an
unfed cell renders an em dash and the table footnote names what is missing and
where it is tracked. A column that silently showed zero would be read as "this
brief unblocks nothing", which is a claim nobody made.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from mctl_dashboard.reading import attr
from mctl_dashboard.render import esc as _e
from mctl_dashboard.state import COLUMN_LABEL, ViewState
from mctl_dashboard.theme import STOP

#: Score weights. Deliberately adjustable and deliberately not canonical: no
#: policy defines importance, so this ordering is a working hypothesis the
#: operator experiments with, not a fact about briefs.
DEFAULT_WEIGHTS: dict[str, int] = {"unlock": 8, "convoy": 5, "age": 3, "prio": 4}

PRIO_RANK: dict[str, int] = {"high": 3, "normal": 2, "low": 1}
SEV_RANK: dict[str, int] = {"error": 3, "warn": 2, "ok": 1}

#: Columns the core cannot feed today. Rendered as an em dash, and named in
#: the footnote so the gap is visible rather than mistaken for a zero.
UNFED_COLUMNS: dict[str, str] = {
    "unlock": "unlock_count",
    "prio": "priority",
    "kind": "brief type",
    "nopts": "decision options",
    "rec": "recommendation",
}

_DASH = "—"

#: Never hidden, however empty. The title is the row's identity, and Health is
#: the column an operator scans for trouble -- an all-OK Health column is a
#: real answer ("nothing is wrong here"), not an absence.
KEEP_ALWAYS: frozenset[str] = frozenset({"slug", "rig", "sev"})


# --------------------------------------------------------------------------
# derivation
# --------------------------------------------------------------------------


def age_days(brief: Mapping[str, Any], *, now: datetime | None = None) -> int | None:
    """Whole days since the brief bead was created, or None if unknown."""
    raw = str(attr(brief, "created_at") or "").strip()
    if not raw:
        return None
    text = raw.replace("Z", "+00:00")
    try:
        created = datetime.fromisoformat(text)
    except ValueError:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    reference = now or datetime.now(timezone.utc)
    return max(0, (reference - created).days)


def severity(brief: Mapping[str, Any]) -> str:
    """Health for the row, from the brief's own diagnostics.

    `ok` is the honest default: a brief with no diagnostics attached is clean
    as far as anything has looked, and saying so is different from claiming it
    was checked.
    """
    codes = attr(brief, "diagnostics") or ()
    worst = "ok"
    for item in codes:
        level = str((item or {}).get("severity") or "").upper()
        if level in {"ERROR", "FATAL"}:
            return "error"
        if level == "WARN":
            worst = "warn"
    return worst


def score(brief: Mapping[str, Any], weights: Mapping[str, int] | None = None) -> int | None:
    """The weighted ordering score, or None when its inputs are missing.

    Returns None rather than 0 when `unlock_count` and priority are absent,
    which they are today: a zero would sort as "least important" and be read
    as a measurement, when in fact nothing was measured.
    """
    settings = dict(DEFAULT_WEIGHTS)
    if weights:
        settings.update(weights)

    unlock = attr(brief, "unlock_count")
    priority = attr(brief, "priority")
    days = age_days(brief)
    if unlock is None and priority is None:
        return None

    total = 0.0
    if unlock is not None:
        total += float(unlock) * settings["unlock"]
    if attr(brief, "convoy"):
        total += settings["convoy"] * 2.4
    if days is not None:
        total += days * settings["age"] * 0.35
    if priority is not None:
        total += PRIO_RANK.get(str(priority).lower(), 2) * settings["prio"]
    return round(total)


def sort_value(
    brief: Mapping[str, Any], key: str, weights: Mapping[str, int] | None = None
) -> Any:
    """A comparable for one column. Unknowns sort last in both directions."""
    if key == "score":
        value = score(brief, weights)
        return (value is None, value if value is not None else 0)
    if key == "age":
        days = age_days(brief)
        return (days is None, days if days is not None else 0)
    if key == "sev":
        return (False, SEV_RANK.get(severity(brief), 1))
    if key == "prio":
        raw = attr(brief, "priority")
        return (raw is None, PRIO_RANK.get(str(raw).lower(), 0))
    if key == "unlock":
        raw = attr(brief, "unlock_count")
        return (raw is None, float(raw) if raw is not None else 0.0)
    if key == "slug":
        return (False, str(attr(brief, "title") or "").lower())
    if key == "rig":
        return (False, str(attr(brief, "rig_id") or "").lower())
    if key == "source":
        return (False, str(attr(brief, "canonical_source") or "").lower())
    if key == "artifact":
        return (False, _artifact_text(brief).lower())
    return (True, "")


def sorted_briefs(
    briefs: Sequence[Mapping[str, Any]], view: ViewState
) -> list[Mapping[str, Any]]:
    weights = view.weights
    ordered = sorted(briefs, key=lambda brief: sort_value(brief, view.sort_key, weights))
    if view.sort_dir < 0:
        known = [b for b in ordered if not sort_value(b, view.sort_key, weights)[0]]
        unknown = [b for b in ordered if sort_value(b, view.sort_key, weights)[0]]
        return list(reversed(known)) + unknown
    return ordered


# --------------------------------------------------------------------------
# colour
# --------------------------------------------------------------------------


def row_background(brief: Mapping[str, Any], *, index: int, cursor: int) -> str:
    """Stoplight precedence, health above cursor.

    Health outranks the cursor deliberately. If the cursor recoloured an error
    row, running j/k down the table would make a violation look like an
    ordinary selected row for exactly as long as the cursor rested on it --
    which is the moment the operator is most likely to act on it.
    """
    if attr(brief, "kind") == "error":
        return STOP["error"]["bg"]
    level = attr(brief, "sev") or severity(brief)
    if level == "error":
        return STOP["held"]["bg"]
    if level == "warn":
        return STOP["warn"]["bg"]
    if index == cursor:
        return "var(--color-accent-100)"
    return "var(--color-neutral-100)" if index % 2 else "transparent"


def row_edge(brief: Mapping[str, Any], *, index: int, cursor: int) -> str:
    if attr(brief, "kind") == "error":
        return STOP["error"]["edge"]
    level = attr(brief, "sev") or severity(brief)
    if level == "error":
        return STOP["held"]["edge"]
    if level == "warn":
        return STOP["warn"]["edge"]
    if index == cursor:
        return "var(--color-accent-600)"
    return "transparent"


# --------------------------------------------------------------------------
# cells
# --------------------------------------------------------------------------


def _artifact_text(brief: Mapping[str, Any]) -> str:
    states = sorted(
        {str(item.get("state")) for item in brief.get("redundant_artifacts") or ()}
    )
    return ", ".join(states)


def cell_text(
    brief: Mapping[str, Any], key: str, weights: Mapping[str, int] | None = None
) -> str:
    """The visible text for one cell, em dash where the core has no value."""
    if key == "slug":
        return str(attr(brief, "title") or attr(brief, "bead_id") or _DASH)
    if key == "rig":
        return str(attr(brief, "rig_id") or _DASH)
    if key == "artifact":
        return _artifact_text(brief) or _DASH
    if key == "source":
        return str(attr(brief, "canonical_source") or _DASH)
    if key == "age":
        days = age_days(brief)
        return f"{days}d" if days is not None else _DASH
    if key == "score":
        value = score(brief, weights)
        return str(value) if value is not None else _DASH
    if key == "sev":
        if attr(brief, "kind") == "error":
            return "ERROR"
        level = attr(brief, "sev") or severity(brief)
        return "HELD" if level == "error" else str(level).upper()
    if key == "unlock":
        raw = attr(brief, "unlock_count")
        return str(raw) if raw is not None else _DASH
    if key == "prio":
        return str(attr(brief, "priority") if attr(brief, "priority") is not None else _DASH)
    if key == "kind":
        return str(attr(brief, "kind") or attr(brief, "decision_state") or _DASH)
    if key == "nopts":
        options = attr(brief, "decision_options")
        return str(len(options)) if options else _DASH
    if key == "rec":
        return str(attr(brief, "recommendation") or _DASH)
    return _DASH


def _cell_style(key: str, numeric: bool) -> str:
    base = (
        "padding: 5px 8px; vertical-align: top; white-space: nowrap; "
        "overflow: hidden; text-overflow: ellipsis;"
    )
    if key == "slug":
        return base + (
            " font-family: var(--font-heading); font-size: 14.5px; font-weight: 600;"
            " line-height: 1.3; color: var(--color-text);"
        )
    if numeric:
        colour = "var(--color-accent-800)" if key == "score" else "var(--color-neutral-800)"
        return base + (
            " font-family: var(--font-mono); font-size: 11.5px; text-align: right;"
            f" font-feature-settings: 'tnum'; color: {colour};"
        )
    if key == "sev":
        return base + (
            " font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.04em;"
        )
    return base + " font-family: var(--font-mono); font-size: 11.5px; color: var(--color-neutral-700);"


def _severity_colour(brief: Mapping[str, Any]) -> str:
    if attr(brief, "kind") == "error":
        return STOP["error"]["fg"]
    level = attr(brief, "sev") or severity(brief)
    if level == "error":
        return STOP["held"]["fg"]
    if level == "warn":
        return STOP["warn"]["fg"]
    return STOP["ok"]["fg"]


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def _headers(view: ViewState) -> str:
    cells = [f'<th style="width: 46px; padding: 6px 4px 6px 8px; border: 0;"></th>']
    for key, label, width, numeric in view.visible_columns:
        # The title column declares no width -- it absorbs whatever the others
        # leave, which is what `table_min_width` computes the floor for.
        sizing = "" if key == "slug" else f"width: {width}px; "
        align = "right" if numeric else "left"
        colour = (
            "var(--color-accent-800)" if key == view.sort_key else "var(--color-neutral-800)"
        )
        # 12px horizontal padding, not the prototype's 5px: with nowrap and
        # overflow hidden on a fixed-width th, 5px clips the sort arrow.
        cells.append(
            f'<th class="mc-th" style="{sizing}text-align: {align}; padding: 6px 12px; '
            "border: 0; font-family: var(--font-mono); font-size: 10.5px; "
            "text-transform: uppercase; "
            f"font-weight: 600; letter-spacing: 0.06em; color: {colour}; "
            'white-space: nowrap; overflow: hidden;">'
            f'<a href="{_e(view.sort_link(key))}">{_e(label)}'
            f'<span class="mono" style="color: var(--color-accent-700);">'
            f"{_e(view.sort_marker(key))}</span></a></th>"
        )
    cells.append('<th style="width: 184px; border: 0;"></th>')
    return "".join(cells)


def _quick_action(brief: Mapping[str, Any], brief_id: str, rig: str | None) -> str:
    """The triage-first row action, when this row's data qualifies for one.

    The design's stack lets a clerk clear the obvious rows without opening
    them: a no-brainer `resolve →`, an untitled brief `send back →`. Both are
    LINKS into the brief's own adjudication panel, not a one-click write --
    firing one lands the operator in the preview-first panel with the honest
    verdict already in view, so nothing is recorded until they confirm.

    Gated on data that is actually present. `kind` is unfed today (issue #66),
    so the `resolve →` action stays dark until the core reports brief type --
    the same self-feeding rule the columns follow. A missing title, by
    contrast, is readable now, so `send back →` lights up on the empties.
    """
    query_rig = f"&rig={_e(rig)}" if rig else ""
    title = str(attr(brief, "title") or "").strip()
    kind = str(attr(brief, "kind") or "")
    if not title:
        href = f"/briefs/{_e(brief_id)}?prefill=incomplete{query_rig}#mc-adjudicate"
        tip = ("No title — the honest verdict is to send it back for the "
               "required fields. Opens the panel; nothing is written yet.")
        label = "send back &rarr;"
    elif kind == "nobrainer":
        href = f"/briefs/{_e(brief_id)}?{query_rig[1:]}#mc-adjudicate" if query_rig else f"/briefs/{_e(brief_id)}#mc-adjudicate"
        tip = ("Flagged a no-brainer — clear it in the panel. Preview-first; "
               "nothing is written until you confirm.")
        label = "resolve &rarr;"
    else:
        return ""
    return (
        f'<a class="mc-quick" data-region="quick-action" href="{href}" '
        f'title="{_e(tip)}">{label}</a>'
    )


def _row(
    brief: Mapping[str, Any],
    view: ViewState,
    *,
    index: int,
    queued: Sequence[str],
) -> str:
    bead = str(attr(brief, "bead_id") or "")
    brief_id = str(attr(brief, "brief_id") or bead)
    rig_val = str(attr(brief, "rig_id") or "") or view.rig
    # The rig travels with the link. A brief lives in exactly one rig's store,
    # so a city-wide detail page cannot resolve it without being told which --
    # without this every click city-wide returns 400 rig-required.
    href = view.url(view="brief", brief_id=brief_id, rig=rig_val)
    background = row_background(brief, index=index, cursor=view.cursor)
    edge = row_edge(brief, index=index, cursor=view.cursor)

    cells = []
    for key, _label, _width, numeric in view.visible_columns:
        style = _cell_style(key, numeric)
        if key == "sev":
            style += f" color: {_severity_colour(brief)};"
            if attr(brief, "kind") == "error":
                style += " font-weight: 600;"
        text = cell_text(brief, key, view.weights)
        # One line per row, ellipsised. The design's density is the point:
        # a stack you scan is a stack you can rank, and a wrapped title turns
        # thirteen visible rows into seven.
        inner = 'style="display: block; overflow: hidden; text-overflow: ellipsis;"' 
        cells.append(
            f'<td style="{style}"><a href="{_e(href)}" style="color: inherit;" '
            f"{inner}>{_e(text)}</a></td>"
        )

    position = list(queued).index(bead) + 1 if bead in queued else None
    if position is None:
        queue_cell = (
            f'<a class="btn btn-ghost" style="font-size: 10.5px; padding: 3px 7px;" '
            f'href="{_e(view.url(view="priority"))}">add to queue</a>'
        )
    else:
        queue_cell = (
            '<span class="mono" style="font-size: 10.5px; padding: 3px 7px; '
            "border: 1px solid var(--color-accent-600); border-radius: var(--radius-md); "
            "background: var(--color-accent-200); color: var(--color-accent-900);\">"
            f"✓ queued {position}</span>"
        )

    action = _quick_action(brief, brief_id, rig_val)
    trailing = (
        '<span style="display: inline-flex; gap: 6px; align-items: center; '
        'justify-content: flex-end; flex-wrap: nowrap;">'
        + queue_cell
        + action
        + "</span>"
    )

    return (
        f'<tr class="mc-row" data-row-index="{index}" data-href="{_e(href)}" '
        f'style="background: {background}; box-shadow: inset 3px 0 0 {edge};">'
        '<td style="padding: 5px 4px 5px 8px; vertical-align: top; white-space: nowrap;">'
        f'<input type="checkbox" name="pick" value="{_e(bead)}" '
        'style="accent-color: var(--color-accent-600); margin: 0; vertical-align: middle;">'
        f'<span class="mono" style="font-size: 10px; color: var(--color-neutral-500); '
        f'margin-left: 4px;">{index + 1}</span></td>'
        + "".join(cells)
        + '<td style="padding: 5px 8px 5px 4px; text-align: right; vertical-align: top;">'
        + trailing
        + "</td></tr>"
    )


def _fed_columns(
    briefs: Sequence[Mapping[str, Any]], view: ViewState
) -> tuple[ViewState, tuple[str, ...]]:
    """Drop columns no brief in this result can feed.

    A column whose every cell is an em dash is not information -- it is a
    claim that something was measured and came back empty, which is a
    different and false statement. The stack table was drawing five of them,
    so the operator's first impression of the queue was a wall of dashes.

    Two properties make this safe to do automatically. It is computed from the
    rows in hand, so the column **reappears on its own** the moment the core
    starts feeding it -- no release, no flag. And it never overrides an
    explicit choice: a column you ticked yourself is a column you get, dashes
    and all, because you asked a question and empty is the answer.

    Returns the view to render with, and the keys that were dropped so the
    caller can name them.
    """
    if view.columns_chosen:
        return view, ()

    droppable = tuple(
        key
        for key in view.columns
        if key not in KEEP_ALWAYS
        and all(cell_text(brief, key, view.weights) == _DASH for brief in briefs)
    )
    if not droppable:
        return view, ()
    kept = tuple(key for key in view.columns if key not in droppable)
    return replace(view, columns=kept), droppable


def _hidden_note(dropped: Sequence[str]) -> str:
    """Name what was hidden. A column that vanishes silently reads as absent."""
    if not dropped:
        return ""
    names = ", ".join(
        f"{COLUMN_LABEL.get(key, key)} ({UNFED_COLUMNS[key]})"
        if key in UNFED_COLUMNS
        else COLUMN_LABEL.get(key, key)
        for key in dropped
    )
    return (
        '<p class="lede" data-region="stack-hidden-columns" '
        'style="margin-top: 8px; font-style: italic;">'
        f"{len(dropped)} column{'s' if len(dropped) != 1 else ''} hidden because no "
        f"brief here carries a value for {'them' if len(dropped) != 1 else 'it'}: "
        f"{_e(names)}. They return on their own once the core feeds them, and "
        "the column picker shows them either way."
        "</p>"
    )


def junk_count_note(held: Sequence[Mapping[str, Any]], total: int) -> str:
    """`N briefs · M junk`, on the stack, before the lane is opened.

    Taylor asked for the *size of the problem* to be visible without a click:
    "it is a good signal for debugging". A count he has to go looking for is
    a count he will not see.
    """
    junk = len(held)
    return (
        '<p class="review-note" data-region="junk-count" style="margin-top: 10px;">'
        f"<strong>{total} brief{'' if total == 1 else 's'} in scope · "
        f"{junk} junk.</strong> "
        + (
            'No brief here is unusable — every one can take a verdict.'
            if not junk
            else f'{junk} of them can take no verdict at all and '
            f'{"is" if junk == 1 else "are"} separated into the '
            '<a href="/junk">Junk</a> lane, with the reason for each. '
            "They are separated rather than hidden: a brief nobody can see is "
            "a brief nobody debugs. "
            "<em>The Junk lane lists more than this number</em> — it shows every "
            "brief no verdict can land on, in any state, while this count is "
            "only the ones that would otherwise be sitting in this queue."
        )
        + "</p>"
    )


def held_back_note(held: Sequence[Mapping[str, Any]]) -> str:
    """Name the briefs the stack is not showing, and why.

    Excluded is not dropped. A queue that quietly shrinks is indistinguishable
    from a city that quietly emptied, which is the defect this dashboard exists
    to not commit. So the count is stated, the reason is stated, and the rows
    remain reachable in the lane that owns them.
    """
    if not held:
        return ""
    reasons: dict[str, int] = {}
    for brief in held:
        why = str(attr(brief, "bead_id") and "not open" or "no canonical brief bead")
        reasons[why] = reasons.get(why, 0) + 1
    named = " · ".join(f"{count} {_e(why)}" for why, count in sorted(reasons.items()))
    total = len(held)
    return (
        '<p class="review-note" data-region="held-back" style="margin-top: 10px;">'
        f"<strong>{total} open brief{'' if total == 1 else 's'} "
        f"{'is' if total == 1 else 'are'} not shown here.</strong> "
        f"{named}. A brief with no canonical bead is refused by the write path "
        "(<span class=\"mono\">MBRF010</span>), so a verdict on it cannot land — "
        "it is held out of the stack rather than offered and then refused. "
        "Nothing is deleted; these remain in the lanes that own them.</p>"
    )


def empty_notice(elsewhere: Mapping[str, Any] | None = None) -> str:
    """Say why the stack is empty, not merely that it is.

    A rig-scoped dashboard on a rig with no briefs is *correct* on an empty
    set, and looks exactly like a broken one: empty table, empty priority
    list, blank counts. Nothing distinguishes "there is nothing here" from
    "I could not look", and those two have opposite next moves.

    So when briefs exist outside the current scope, name the scope, the
    count, and how to widen it. The operator should never have to know that
    a `--rig` flag was the difference.
    """
    base = (
        "No briefs on this stack. Produced briefs land in the "
        '<a href="/pile">pile</a> and are promoted by the gates.'
    )
    if not elsewhere or not elsewhere.get("total"):
        return f'<p class="lede" data-region="brief-stack-empty">{base}</p>'
    rig = _e(str(elsewhere.get("rig") or "this rig"))
    total = int(elsewhere["total"])
    rigs = int(elsewhere.get("rigs") or 0)
    where = f"{total} brief{'' if total == 1 else 's'} exist in "
    where += f"{rigs} registered rigs" if rigs else "other rigs"
    return (
        '<p class="review-note" data-region="brief-stack-empty">'
        f"<strong>Rig <code>{rig}</code> has no briefs at all.</strong> "
        f"{where} — this page is empty because of its scope, not because the "
        "city is. Restart the dashboard without <code>--rig</code> to work "
        "across all rigs.</p>"
        f'<p class="lede">{base}</p>'
    )


def table(
    briefs: Sequence[Mapping[str, Any]],
    view: ViewState,
    *,
    queued: Sequence[str] = (),
    elsewhere: Mapping[str, Any] | None = None,
) -> str:
    ordered = sorted_briefs(briefs, view)
    if not ordered:
        return empty_notice(elsewhere)
    view, dropped = _fed_columns(ordered, view)
    rows = "".join(
        _row(brief, view, index=index, queued=queued)
        for index, brief in enumerate(ordered)
    )
    return (
        # A GET form so ticking rows and adding them together needs no script:
        # the checkboxes carry bead ids and the button submits them to the
        # priority list, which reads its order straight from the query string.
        '<form method="get" action="/priority">'
        '<div class="scroll-x" style="border-bottom: 2px solid var(--color-neutral-900);">'
        f'<table class="ntdata" data-region="brief-stack" '
        f'style="min-width: {view.table_min_width}px; table-layout: fixed; '
        'border-collapse: collapse; font-size: 12.5px;">'
        f"<thead><tr>{_headers(view)}</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
        '<div style="margin-top: 9px; display: flex; gap: 9px; align-items: center;">'
        '<button class="btn btn-secondary" type="submit" '
        'style="font-size: 11.5px; padding: 4px 10px;">Add ticked to priority list</button>'
        '<span class="lede" style="font-size: 11px;">Ticking changes nothing until you '
        "add them; the priority list is your ordering, not pipeline state.</span></div>"
        "</form>"
        + _hidden_note(dropped)
    )


def column_picker(view: ViewState) -> str:
    """A GET form, so toggling columns survives JavaScript being off."""
    boxes = []
    for key, label, _width, _numeric in (
        (key, l, w, n) for key, l, w, n in _all_columns()
    ):
        checked = " checked" if key in view.columns else ""
        boxes.append(
            '<label style="font-size: 12px; display: inline-flex; align-items: center; '
            'gap: 5px; cursor: pointer;">'
            f'<input type="checkbox" name="columns" value="{_e(key)}"{checked} '
            'style="accent-color: var(--color-accent-600); margin: 0;">'
            f"{_e(label)}</label>"
        )
    hidden = (
        f'<input type="hidden" name="sort_key" value="{_e(view.sort_key)}">'
        f'<input type="hidden" name="sort_dir" value="{_e(view.sort_dir)}">'
        f'<input type="hidden" name="scope" value="{_e(view.scope)}">'
    )
    return (
        '<form method="get" action="/queue" data-region="column-picker" '
        'style="border: 1px solid var(--color-divider); border-top: 0; '
        "background: var(--color-neutral-100); padding: 10px 12px; display: flex; "
        'flex-wrap: wrap; gap: 6px 16px; align-items: center;">'
        '<span style="font-size: 11.5px; color: var(--color-neutral-700); '
        'font-style: italic; margin-right: 4px;">Show columns —</span>'
        + "".join(boxes)
        + hidden
        + '<button class="btn btn-secondary" type="submit" '
        'style="font-size: 11.5px; padding: 3px 10px;">Apply</button>'
        "</form>"
    )


def _all_columns() -> Iterable[tuple[str, str, int, bool]]:
    from mctl_dashboard.state import COLUMNS

    for key, label, width, numeric, _default in COLUMNS:
        yield key, label, width, numeric


def key_legend() -> str:
    """Every row colour, explained. A colour with no entry is one to guess at."""
    entries = (
        (STOP["error"], "ERROR", "invariant violation, decide the repair"),
        (STOP["held"], "HELD", "blocked by an error brief"),
        (STOP["warn"], "WARN", "degraded, still adjudicable"),
        (STOP["ok"], "OK", "clean, ready to decide"),
    )
    items = []
    for stop, label, gloss in entries:
        swatch = (
            f'<span style="width: 22px; height: 13px; background: {stop["bg"]}; '
            "border: 1px solid var(--color-divider); "
            f'border-left: 3px solid {stop["edge"]}; flex: none;"></span>'
        )
        items.append(
            '<span style="display: inline-flex; align-items: center; gap: 7px; '
            'font-size: 11.5px; color: var(--color-neutral-800);">'
            + swatch
            + f'<b class="mono" style="font-size: 10px; font-weight: 600; '
            f'color: {stop["fg"]};">{label}</b> — {gloss}</span>'
        )
    items.append(
        '<span style="display: inline-flex; align-items: center; gap: 7px; '
        'font-size: 11.5px; color: var(--color-neutral-800);">'
        '<span style="width: 22px; height: 13px; background: var(--color-accent-100); '
        "border: 1px solid var(--color-divider); "
        'border-left: 3px solid var(--color-accent-600); flex: none;"></span>'
        "cursor — j / k moves, enter opens</span>"
    )
    return (
        '<div data-region="stack-key" style="margin-top: 12px; '
        "border-top: 1px solid var(--color-divider); padding-top: 9px; display: flex; "
        'flex-wrap: wrap; gap: 7px 20px; align-items: center;">'
        '<span class="mono" style="font-size: 10px; letter-spacing: 0.05em; '
        'text-transform: uppercase; color: var(--color-neutral-600);">Key</span>'
        + "".join(items)
        + "</div>"
    )


_COUNT_WORD = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five"}


def unfed_columns(
    briefs: Sequence[Mapping[str, Any]], weights: Mapping[str, int] | None = None
) -> list[str]:
    """Which assumed-but-unfed columns *this* data actually cannot fill.

    Derived from the rendered rows rather than declared, because a fixed list
    goes stale the moment the core starts supplying one of them. It did: the
    note claimed six columns while the dict named five, and by then `priority`
    had a source, so a live city-wide queue carried a footnote naming a column
    the table was visibly filling.

    That is the same defect the footnote exists to prevent, one level up. An
    empty cell is honest about having no value; a footnote that misreports
    which cells those are teaches the reader to distrust cells that are right.

    All-or-nothing per column: the claim is "the core cannot fill this", and a
    single filled cell disproves it.
    """
    missing: list[str] = []
    for key, name in sorted(UNFED_COLUMNS.items(), key=lambda kv: kv[1]):
        if briefs and all(cell_text(brief, key, weights) == _DASH for brief in briefs):
            missing.append(name)
    return missing


def unfed_note(
    briefs: Sequence[Mapping[str, Any]], weights: Mapping[str, int] | None = None
) -> str:
    """Name the columns the core cannot fill yet, rather than showing zeros."""
    names = unfed_columns(briefs, weights)
    if not names:
        return ""
    count = _COUNT_WORD.get(len(names), str(len(names)))
    plural = "" if len(names) == 1 else "s"
    return (
        '<p class="lede" data-region="unfed-columns" style="margin-top: 10px; '
        'font-style: italic;">'
        f"{count} column{plural} show — because the core does not expose "
        f"{'it' if len(names) == 1 else 'them'} yet: {_e(', '.join(names))}. "
        f"{'It is' if len(names) == 1 else 'They are'} tracked on "
        '<a href="https://github.com/tdupu/mathcity/issues/66">issue #66</a>. '
        "An empty cell here means no value was read, not a value of zero.</p>"
    )


def empty_sort_note(
    briefs: Sequence[Mapping[str, Any]], view: ViewState
) -> str:
    """Say so when the active sort column has no values at all.

    A sort over an empty column produces a stable, arbitrary order that is
    indistinguishable from a working one -- the rows are lined up, the arrow is
    drawn, and nothing indicates the ordering means nothing. That is the same
    failure as showing a zero for an unread value, one level up: the operator
    reads an ordering as a ranking.

    Louder than the column footnote, because this one changes what the whole
    screen appears to be telling you.
    """
    if not briefs:
        return ""
    label = COLUMN_LABEL.get(view.sort_key, view.sort_key)
    if any(not sort_value(brief, view.sort_key)[0] for brief in briefs):
        return ""
    return (
        '<p class="review-note" data-region="empty-sort" style="margin-top: 10px;">'
        f"<strong>Sorted by {_e(label)}, which has no values.</strong> "
        "Every brief here is missing that field, so the order below is stable "
        "but arbitrary — it is not a ranking. Sort by a column with data, or see "
        '<a href="https://github.com/tdupu/mathcity/issues/66">issue #66</a> for '
        "when this one gets a source.</p>"
    )
