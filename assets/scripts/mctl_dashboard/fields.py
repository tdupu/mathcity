"""Render whatever attributes a brief happens to have.

Taylor's ruling, 2026-08-19: *"All of these fields could be adapted to the
webpage. We just need a function that takes every subset of attributes and
returns a display for them."*

That is this module, and the design follows from three rules.

**Absent fields do not render.** No em-dash row, no "not exposed yet" apology.
A brief with no `verdict` has not been adjudicated -- that is a fact about the
brief, not a hole in the data, and drawing an empty row for it invents a gap
nobody measured. This replaces the earlier stack-table behaviour, where six
columns rendered a permanent em dash and a footnote explaining themselves.

**Unknown fields still render.** This is the point of the module rather than a
nicety. Brief frontmatter is an open vocabulary written by producers -- the
live corpus carries `status`, `artifact`, `form`, `track`, `unlock_count`,
`gates`, `shape`, `priority`, `verdict`, `deposited_by`, `server_touching`,
`review_gate` and more, in every combination. A renderer with a fixed schema
would need a release before any new field became visible; this one shows it
the moment a producer writes it.

**Known fields get known treatment.** A registry keyed by field name gives
figures tabular numerals, makes `track` a filter link, and lets a verdict read
as a verdict. Everything not in the registry falls through to a labelled row,
which is unglamorous and correct.

One further rule, from the provenance work: **a value's source is shown when
the core states it and never guessed.** A frontmatter value and a bead value
are not equally attested, and where the two disagree both are shown with the
disagreement marked, because the dashboard must not be the place a conflict
quietly disappears.
"""

from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import quote

from mctl_dashboard.render import esc as _e

#: Fields whose meaning is known well enough to style. Everything else still
#: renders -- see `_generic`.
NUMERIC_FIELDS = frozenset({"unlock_count", "priority_rank", "age_days", "score"})
LIST_FIELDS = frozenset({"gates", "labels", "policy_references", "relates"})
MONO_FIELDS = frozenset(
    {"artifact", "bead_id", "brief_id", "source_bead", "trace_id", "canonical_source"}
)

#: Rendered first, in this order, when present. Everything else follows in the
#: order the core supplied, which is the producer's own order.
PREFERRED_ORDER = (
    "status",
    "decision_state",
    "verdict",
    "verdict_note",
    "adjudicated_at",
    "adjudicated_by",
    "artifact",
    "source_bead",
    "track",
    "form",
    "unlock_count",
    "priority",
    "gates",
)

#: Never shown as an attribute row: either rendered elsewhere on the page, or
#: internal bookkeeping that tells the reader nothing.
SUPPRESSED = frozenset(
    {
        "title",
        "body",
        "sections",
        "body_diagnostics",
        # Structural payloads rendered elsewhere or unpacked by `unpack`.
        # Left in, they stringify as Python reprs -- agent exhaust in the
        # operator's page, which is the thing this dashboard is least allowed
        # to do.
        "fields",
        "policy_references",
        "redundant_artifacts",
        "readings",
    }
)


def unpack(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Split a `briefs_show` payload into attributes, sources and conflicts.

    The core reports field provenance as
    `fields: {name: {value, source, conflict, readings}}`. That is precisely
    what this module was built to render -- but only once it is taken apart.
    Passed through whole it renders as a dict repr.

    A field the core has provenance for wins over a bare top-level key of the
    same name, because the provenanced one knows where it came from.
    """
    attrs = {k: v for k, v in payload.items() if k not in SUPPRESSED}
    sources: dict[str, str] = {}
    conflicts: dict[str, dict[str, Any]] = {}

    for name, entry in (payload.get("fields") or {}).items():
        if not isinstance(entry, Mapping):
            continue
        attrs[name] = entry.get("value")
        origin = entry.get("source")
        if origin:
            sources[name] = str(origin)
        if entry.get("conflict"):
            readings = entry.get("readings") or []
            conflicts[name] = {
                str(r.get("source") or "?"): r.get("value")
                for r in readings
                if isinstance(r, Mapping)
            }
    return {"attrs": attrs, "sources": sources, "conflicts": conflicts}


def _label(key: str) -> str:
    return key.replace("_", " ")


def _track_link(value: str) -> str:
    """`track` is the most useful filter at city scale, so it is a link.

    With ~430 briefs in about six tracks, grouping beats sorting: nobody finds
    anything by ordering 430 rows, but "show me pack-hygiene" is 24 rows.
    """
    return (
        f'<a href="/queue?track={quote(str(value), safe="")}">{_e(value)}</a>'
    )


def _verdict_value(value: str) -> str:
    text = str(value).strip().strip('"')
    colour = (
        "#8f2c22"
        if text.upper().startswith("REJECT")
        else "var(--color-neutral-900)"
        if text.upper().startswith(("APPROVE", "REPAIR"))
        else "var(--color-accent-800)"
    )
    return (
        f'<span class="mono" style="color: {colour}; letter-spacing: 0.04em;">'
        f"{_e(text)}</span>"
    )


def _list_value(value: Any) -> str:
    items = value if isinstance(value, (list, tuple)) else str(value).split(",")
    cleaned = [str(i).strip() for i in items if str(i).strip()]
    if not cleaned:
        return ""
    return " · ".join(f'<span class="mono">{_e(i)}</span>' for i in cleaned)


def _generic(value: Any) -> str:
    """The fallback: show it, escaped, without pretending to understand it."""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return _list_value(value)
    if isinstance(value, Mapping):
        return " · ".join(f"{_e(k)}: {_e(v)}" for k, v in value.items())
    return _e(value)


def render_value(key: str, value: Any) -> str:
    """One value, styled by what the field is known to mean."""
    if key in NUMERIC_FIELDS:
        return (
            f'<span class="mono" style="font-feature-settings: \'tnum\'; '
            f'text-align: right;">{_e(value)}</span>'
        )
    if key == "track":
        return _track_link(str(value))
    if key.startswith("verdict"):
        return _verdict_value(value)
    if key in LIST_FIELDS:
        return _list_value(value)
    if key in MONO_FIELDS:
        return f'<span class="mono">{_e(value)}</span>'
    return _generic(value)


def _is_present(value: Any) -> bool:
    """Absent means absent. Zero and False are values, not absences."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() not in ("", "-", "—")
    if isinstance(value, (list, tuple, dict)):
        return len(value) > 0
    return True


def _ordered(keys: list[str]) -> list[str]:
    known = [k for k in PREFERRED_ORDER if k in keys]
    rest = [k for k in keys if k not in PREFERRED_ORDER]
    return known + rest


def attributes(
    attrs: Mapping[str, Any],
    *,
    sources: Mapping[str, str] | None = None,
    conflicts: Mapping[str, Mapping[str, Any]] | None = None,
    region: str = "attributes",
) -> str:
    """Render every attribute that is present, and nothing that is not.

    `sources` maps a field to where its value came from (`"bead"`,
    `"frontmatter"`, ...). Shown when supplied, omitted entirely when not --
    a guessed provenance is worse than none.

    `conflicts` maps a field to the competing values when the core found the
    bead and the file disagreeing. Both are shown and the disagreement is
    named; the dashboard does not pick a winner.
    """
    sources = sources or {}
    conflicts = conflicts or {}

    present = [
        k
        for k, v in attrs.items()
        if k not in SUPPRESSED and _is_present(v)
    ]
    if not present:
        return ""

    rows = []
    for key in _ordered(present):
        value = render_value(key, attrs[key])

        origin = sources.get(key)
        origin_html = (
            f'<span class="mono" style="font-size: 10px; color: var(--color-neutral-500); '
            f'margin-left: 8px;" title="where this value came from">{_e(origin)}</span>'
            if origin
            else ""
        )

        clash = conflicts.get(key)
        clash_html = ""
        if clash:
            pairs = " · ".join(
                f'{_e(src)} says <span class="mono">{_e(val)}</span>'
                for src, val in clash.items()
            )
            clash_html = (
                '<div class="review-note" style="margin: 4px 0 0; font-size: 11.5px;">'
                f"<strong>Sources disagree.</strong> {pairs}. "
                "Both are kept; nothing here chooses between them.</div>"
            )

        rows.append(
            '<div style="display: flex; gap: 10px; padding: 3px 0; '
            'border-bottom: 1px solid var(--color-divider); font-size: 12.5px;">'
            f'<span style="width: 150px; flex: none; color: var(--color-neutral-600);">'
            f"{_e(_label(key))}</span>"
            f'<span style="min-width: 0;">{value}{origin_html}{clash_html}</span>'
            "</div>"
        )

    return f'<div data-region="{_e(region)}">' + "".join(rows) + "</div>"
