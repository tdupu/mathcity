"""The brief stack: the dense sortable table the operator works from.

Thirteen columns, nine on by default, sortable by clicking a heading. Sorting
and column toggling are a link and a GET form respectively, so the table is
fully operable with JavaScript disabled; the j/k cursor is the only part that
needs script, and it duplicates clicking.

A note on honesty, because it shapes most of this module: `briefs_list`
supplies bead identity, title, status, decision state, labels, timestamps and
redundant-artifact state. It does **not** supply unlock_count, priority,
producing formula, option count, or a recommendation -- the design assumes all
five and the core exposes none of them (issue #66, and `CHANGELOG.md` §G).
Rather than inventing plausible values or quietly dropping the columns, an
unfed cell renders an em dash and the table footnote names what is missing and
where it is tracked. A column that silently showed zero would be read as "this
brief unblocks nothing", which is a claim nobody made.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from mctl_dashboard.render import esc as _e
from mctl_dashboard.state import ViewState
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
    "formula": "producing formula",
    "nopts": "decision options",
    "rec": "recommendation",
}

_DASH = "—"


# --------------------------------------------------------------------------
# derivation
# --------------------------------------------------------------------------


def age_days(brief: Mapping[str, Any], *, now: datetime | None = None) -> int | None:
    """Whole days since the brief bead was created, or None if unknown."""
    raw = str(brief.get("created_at") or "").strip()
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
    codes = brief.get("diagnostics") or ()
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

    unlock = brief.get("unlock_count")
    priority = brief.get("priority")
    days = age_days(brief)
    if unlock is None and priority is None:
        return None

    total = 0.0
    if unlock is not None:
        total += float(unlock) * settings["unlock"]
    if brief.get("convoy"):
        total += settings["convoy"] * 2.4
    if days is not None:
        total += days * settings["age"] * 0.35
    if priority is not None:
        total += PRIO_RANK.get(str(priority).lower(), 2) * settings["prio"]
    return round(total)


def sort_value(brief: Mapping[str, Any], key: str) -> Any:
    """A comparable for one column. Unknowns sort last in both directions."""
    if key == "score":
        value = score(brief)
        return (value is None, value if value is not None else 0)
    if key == "age":
        days = age_days(brief)
        return (days is None, days if days is not None else 0)
    if key == "sev":
        return (False, SEV_RANK.get(severity(brief), 1))
    if key == "prio":
        raw = brief.get("priority")
        return (raw is None, PRIO_RANK.get(str(raw).lower(), 0))
    if key == "unlock":
        raw = brief.get("unlock_count")
        return (raw is None, float(raw) if raw is not None else 0.0)
    if key == "slug":
        return (False, str(brief.get("title") or "").lower())
    if key == "rig":
        return (False, str(brief.get("rig_id") or "").lower())
    if key == "source":
        return (False, str(brief.get("canonical_source") or "").lower())
    if key == "artifact":
        return (False, _artifact_text(brief).lower())
    return (True, "")


def sorted_briefs(
    briefs: Sequence[Mapping[str, Any]], view: ViewState
) -> list[Mapping[str, Any]]:
    ordered = sorted(briefs, key=lambda brief: sort_value(brief, view.sort_key))
    if view.sort_dir < 0:
        known = [b for b in ordered if not sort_value(b, view.sort_key)[0]]
        unknown = [b for b in ordered if sort_value(b, view.sort_key)[0]]
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
    if brief.get("kind") == "error":
        return STOP["error"]["bg"]
    level = brief.get("sev") or severity(brief)
    if level == "error":
        return STOP["held"]["bg"]
    if level == "warn":
        return STOP["warn"]["bg"]
    if index == cursor:
        return "var(--color-accent-100)"
    return "var(--color-neutral-100)" if index % 2 else "transparent"


def row_edge(brief: Mapping[str, Any], *, index: int, cursor: int) -> str:
    if brief.get("kind") == "error":
        return STOP["error"]["edge"]
    level = brief.get("sev") or severity(brief)
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


def cell_text(brief: Mapping[str, Any], key: str) -> str:
    """The visible text for one cell, em dash where the core has no value."""
    if key == "slug":
        return str(brief.get("title") or brief.get("bead_id") or _DASH)
    if key == "rig":
        return str(brief.get("rig_id") or _DASH)
    if key == "artifact":
        return _artifact_text(brief) or _DASH
    if key == "source":
        return str(brief.get("canonical_source") or _DASH)
    if key == "age":
        days = age_days(brief)
        return f"{days}d" if days is not None else _DASH
    if key == "score":
        value = score(brief)
        return str(value) if value is not None else _DASH
    if key == "sev":
        if brief.get("kind") == "error":
            return "ERROR"
        level = brief.get("sev") or severity(brief)
        return "HELD" if level == "error" else str(level).upper()
    if key == "unlock":
        raw = brief.get("unlock_count")
        return str(raw) if raw is not None else _DASH
    if key == "prio":
        return str(brief.get("priority") or _DASH)
    if key == "kind":
        return str(brief.get("kind") or brief.get("decision_state") or _DASH)
    if key == "formula":
        return str(brief.get("producing_formula") or _DASH)
    if key == "nopts":
        options = brief.get("decision_options")
        return str(len(options)) if options else _DASH
    if key == "rec":
        return str(brief.get("recommendation") or _DASH)
    return _DASH


def _cell_style(key: str, numeric: bool) -> str:
    base = (
        "padding: 5px 8px; vertical-align: top; white-space: nowrap; "
        "overflow: hidden; text-overflow: ellipsis;"
    )
    if key == "slug":
        return base + (
            " font-family: var(--font-heading); font-size: 14.5px; font-weight: 600;"
            " white-space: normal; line-height: 1.25; color: var(--color-text);"
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
    if brief.get("kind") == "error":
        return STOP["error"]["fg"]
    level = brief.get("sev") or severity(brief)
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
            "border: 0; font-family: var(--font-heading); font-size: 12.5px; "
            f"font-weight: 600; letter-spacing: 0.02em; color: {colour}; "
            'white-space: nowrap; overflow: hidden;">'
            f'<a href="{_e(view.sort_link(key))}">{_e(label)}'
            f'<span class="mono" style="color: var(--color-accent-700);">'
            f"{_e(view.sort_marker(key))}</span></a></th>"
        )
    cells.append('<th style="width: 104px; border: 0;"></th>')
    return "".join(cells)


def _row(
    brief: Mapping[str, Any],
    view: ViewState,
    *,
    index: int,
    queued: Sequence[str],
) -> str:
    bead = str(brief.get("bead_id") or "")
    brief_id = str(brief.get("brief_id") or bead)
    href = view.url(view="brief", brief_id=brief_id)
    background = row_background(brief, index=index, cursor=view.cursor)
    edge = row_edge(brief, index=index, cursor=view.cursor)

    cells = []
    for key, _label, _width, numeric in view.visible_columns:
        style = _cell_style(key, numeric)
        if key == "sev":
            style += f" color: {_severity_colour(brief)};"
            if brief.get("kind") == "error":
                style += " font-weight: 600;"
        text = cell_text(brief, key)
        inner = (
            'style="display: -webkit-box; -webkit-line-clamp: 2; '
            '-webkit-box-orient: vertical; overflow: hidden;"'
            if key == "slug"
            else 'style="display: block; overflow: hidden; text-overflow: ellipsis;"'
        )
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

    return (
        f'<tr class="mc-row" data-row-index="{index}" data-href="{_e(href)}" '
        f'style="background: {background}; box-shadow: inset 3px 0 0 {edge};">'
        '<td style="padding: 5px 4px 5px 8px; vertical-align: top; white-space: nowrap;">'
        f'<span class="mono" style="font-size: 10px; color: var(--color-neutral-500);">'
        f"{index + 1}</span></td>"
        + "".join(cells)
        + '<td style="padding: 5px 8px 5px 4px; text-align: center; vertical-align: top;">'
        + queue_cell
        + "</td></tr>"
    )


def table(
    briefs: Sequence[Mapping[str, Any]],
    view: ViewState,
    *,
    queued: Sequence[str] = (),
) -> str:
    ordered = sorted_briefs(briefs, view)
    if not ordered:
        return (
            '<p class="lede" data-region="brief-stack-empty">'
            "No briefs on this stack. Produced briefs land in the "
            '<a href="/pile">pile</a> and are promoted by the gates.</p>'
        )
    rows = "".join(
        _row(brief, view, index=index, queued=queued)
        for index, brief in enumerate(ordered)
    )
    return (
        '<div class="scroll-x" style="border-bottom: 2px solid var(--color-neutral-900);">'
        f'<table class="ntdata" data-region="brief-stack" '
        f'style="min-width: {view.table_min_width}px; table-layout: fixed; '
        'border-collapse: collapse; font-size: 12.5px;">'
        f"<thead><tr>{_headers(view)}</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
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


def unfed_note() -> str:
    """Name the columns the core cannot fill yet, rather than showing zeros."""
    names = ", ".join(sorted(UNFED_COLUMNS.values()))
    return (
        '<p class="lede" data-region="unfed-columns" style="margin-top: 10px; '
        'font-style: italic;">'
        f"Six columns show — because the core does not expose them yet: {_e(names)}. "
        "They are tracked on "
        '<a href="https://github.com/tdupu/mathcity/issues/66">issue #66</a>. '
        "An empty cell here means no value was read, not a value of zero.</p>"
    )
