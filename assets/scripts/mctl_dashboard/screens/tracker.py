"""The tracker screen (#186) -- every GitHub issue with its bead and brief.

Taylor, verbatim: *"I would love to have links to issues on the github issue
tracker ... It should also list the associated beads and briefs if available.
That would be an amazing feature."*

**This screen is mostly a picture of absence, and that is the point.** Measured
2026-08-28: 7 of 1142 beads carry an `external_ref`, so **102 of 107 open
issues have no bead**. #180's pipeline is minting those, and a tracker that
rendered the gap as a blank cell would be useless for the one job it exists to
do. So `no bead` is a *stated* value here, never an empty cell.

Three states, never two, matching `mctl_core.tracker`:

    paired     a bead claims this issue
    unpaired   the store WAS read and holds no bead   -> actionable, #180
    unknown    the store could not be read            -> NOT actionable

The last distinction is the one that earns its keep. A blank cell would collapse
`unpaired` and `unknown` into "fine", and dispatching #180 work off a store that
never answered would mint duplicates on top of the beads it could not see.

Two conditions are surfaced because live data had them, not because they were
imagined: an issue whose beads are all CLOSED while the issue is still open
(one such row today, #55), and an issue claimed by more than one bead -- the
mc-vwkn7 duplicate signature.

Pure render functions over `TrackerRow`; no I/O, no MCP calls. The reading is
`mctl_core.tracker.build_rows`.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from mctl_dashboard.reading import attr
from mctl_dashboard.render import esc as _e

#: The three pairing states, duplicated from `mctl_core.tracker` rather than
#: imported. `screens/city.py:513` states the convention: a render module must
#: have no import-time dependency on `mctl_core`. Three short strings are a
#: cheaper coupling than inverting that, and the tests assert both modules
#: agree, so the duplication cannot drift silently.
PAIRED = "paired"
UNPAIRED = "unpaired"
UNKNOWN = "unknown"


def unreadable_note(what: str, reason: str) -> str:
    """A read that could not run. Never a zero -- the §5.4 rule."""
    return (
        f'<p class="review-note" data-region="{_e(what)}-unreachable">'
        f"<strong>{_e(what)} could not be read.</strong> {_e(reason)} "
        "This is not a count of zero; the surface did not answer.</p>"
    )


def issue_cell(row: Any) -> str:
    """Number and title, linked to the tracker -- the thing asked for by name."""
    label = f"#{row.number}"
    link = (
        f'<a class="mono" href="{_e(row.url)}" rel="noopener">{_e(label)}</a>'
        if row.url
        else f'<span class="mono">{_e(label)}</span>'
    )
    return f'<td>{link} {_e(row.title)}</td>'


def bead_cell(row: Any) -> str:
    """The bead, or a STATED absence -- never a blank.

    `no bead` and `unknown` are different words on purpose. A reader scanning
    this column must be able to tell "nobody has minted one" from "we could not
    look", because only the first is work.
    """
    if row.pairing == UNKNOWN:
        return (
            '<td class="mono" data-pairing="unknown" '
            f'title="{_e(row.unknown_reason or "the bead store did not answer")}">'
            "unknown</td>"
        )
    if not row.beads:
        return '<td class="mono" data-pairing="unpaired">no bead</td>'
    ids = " ".join(f'<span class="mono">{_e(b)}</span>' for b in row.bead_ids)
    flags = []
    if row.is_duplicated:
        flags.append('<span data-flag="duplicated">2+ beads</span>')
    if row.is_orphaned_by_bead:
        flags.append('<span data-flag="bead-closed">bead closed</span>')
    suffix = (" " + " ".join(flags)) if flags else ""
    return f'<td data-pairing="paired">{ids}{suffix}</td>'


def brief_cell(row: Any) -> str:
    """Briefs on the paired bead, or a stated absence.

    An unpaired issue has no bead, so it cannot have a brief *through this
    path*. That renders as a dash with a title explaining why, rather than as
    "no brief" -- which would assert something this screen did not check.
    """
    if row.pairing == UNKNOWN:
        return '<td class="mono" data-brief="unknown">unknown</td>'
    if not row.beads:
        return (
            '<td class="mono" data-brief="not-applicable" '
            'title="no bead, so no brief is reachable from here — not a '
            'statement that none exists">&mdash;</td>'
        )
    if not row.briefs:
        return '<td class="mono" data-brief="none">no brief</td>'
    # `attr` rather than `.get`: a brief row may carry its id at the top level
    # or nested under `fields`, and reading only one shape is the defect
    # `tests/mctl/test_no_single_shape_reads.py` exists to catch. It caught this.
    ids = " ".join(
        f'<span class="mono">{_e(attr(b, "brief_id") or attr(b, "id") or "?")}</span>'
        for b in row.briefs
    )
    return f'<td data-brief="present">{ids}</td>'


def readiness_cell(row: Any) -> str:
    """What this row is asking someone to do, in one word."""
    if row.pairing == UNKNOWN:
        return '<td class="mono" data-readiness="unknown">unknown</td>'
    if row.is_orphaned_by_bead:
        return '<td class="mono" data-readiness="review">review closed bead</td>'
    if row.needs_bead:
        return '<td class="mono" data-readiness="needs-bead">needs a bead</td>'
    if row.beads and not row.briefs:
        return '<td class="mono" data-readiness="needs-brief">needs a brief</td>'
    if row.briefs:
        return '<td class="mono" data-readiness="briefed">briefed</td>'
    return '<td class="mono" data-readiness="none">&mdash;</td>'


def actions_cell(row: Any, *, repo: str) -> str:
    """The row's available moves, and only the ones that make sense for it.

    Taylor asked for `make_hygienic`, `to_brief` and `split_to_smaller_issues`.
    The first two are wired to tools that already exist -- `make_hygienic` is
    `standardize_github_issue` (its own description opens "Make an existing
    GitHub issue hygienic in place"), and the first half of `to_brief` is
    `create_issue_bead`, which is also exactly what closes the unpaired gap
    this screen exists to show.

    **Actions are offered only where they apply.** A row whose pairing is
    `unknown` gets NONE: the store did not answer, so minting a bead could
    duplicate one it could not see. An already-paired row is not offered
    "mint a bead" either -- `create_issue_bead` is idempotent and would no-op,
    but offering a button whose only outcome is "nothing happened" trains an
    operator to distrust the page.

    Every action posts to `/preview`, so it lands in the dry-run-then-confirm
    flow every other mutation uses. Nothing here writes on a click.
    """
    if row.pairing == UNKNOWN:
        return (
            '<td class="mono" data-actions="none" '
            'title="the bead store did not answer, so no action here would be '
            'safe — an action offered on unknown state can duplicate work">'
            "&mdash;</td>"
        )
    buttons = [_action_form("make_hygienic", "make hygienic", row, repo)]
    if row.needs_bead:
        buttons.append(_action_form("mint_bead", "mint a bead", row, repo))
    return f'<td data-actions="available">{"".join(buttons)}</td>'


def _action_form(operation: str, label: str, row: Any, repo: str) -> str:
    """One action as a real form post -- works with scripting off."""
    return (
        '<form class="operation-inline" method="post" action="/preview" '
        f'style="display: inline-block; margin-right: 6px;">'
        f'<input type="hidden" name="operation" value="{_e(operation)}">'
        f'<input type="hidden" name="repo" value="{_e(repo)}">'
        f'<input type="hidden" name="issue_number" value="{_e(row.number)}">'
        f'<button type="submit" class="btn btn-ghost" '
        f'style="font-size: 11px; padding: 3px 8px;">{_e(label)}</button>'
        "</form>"
    )


def summary_line(summary: Mapping[str, Any]) -> str:
    """The header counts.

    `needs_bead` is None whenever any row is unknown, and this renders that as
    the word "unknown" rather than omitting it or printing 0. A partial
    denominator shown as a total is how a number nobody can act on gets made.
    """
    needs = summary.get("needs_bead")
    needs_text = "unknown" if needs is None else str(needs)
    parts = [
        f'{summary.get("issues", 0)} issues',
        f'{summary.get("paired", 0)} with a bead',
        f'{summary.get("unpaired", 0)} without',
        f"{needs_text} needing one",
    ]
    if summary.get("duplicated"):
        parts.append(f'{summary["duplicated"]} claimed by 2+ beads')
    if summary.get("unknown"):
        parts.append(f'{summary["unknown"]} unreadable')
    # Escape each part, THEN join with the raw separator entity. Escaping the
    # joined string would turn the separator into a literal "&middot;", and
    # un-escaping it afterwards would also un-escape any "&amp;" a title
    # legitimately contained -- reintroducing the injection the escape exists
    # to prevent.
    return (
        '<p class="review-note" data-region="tracker-summary">'
        + " &middot; ".join(_e(part) for part in parts)
        + "</p>"
    )


def table(rows: Sequence[Any], *, repo: str = "") -> str:
    """One row per issue. Empty input renders a stated emptiness, not a blank."""
    if not rows:
        return (
            '<p class="review-note" data-region="tracker-empty">'
            "No issues to show. This is a read that returned nothing, not a "
            "read that failed &mdash; a failed read renders its reason.</p>"
        )
    body = "".join(
        "<tr>"
        + issue_cell(r)
        + bead_cell(r)
        + brief_cell(r)
        + readiness_cell(r)
        + actions_cell(r, repo=repo)
        + "</tr>"
        for r in rows
    )
    return (
        '<table class="grid" data-region="tracker-table">'
        "<thead><tr><th>Issue</th><th>Bead</th><th>Brief</th><th>Readiness</th>"
        "<th>Actions</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def render(
    rows: Sequence[Any],
    summary: Mapping[str, Any],
    *,
    issues_unreadable: str | None = None,
    repo: str = "",
) -> str:
    """The whole screen.

    `issues_unreadable` is GitHub not answering, which is different from the
    bead store not answering (that is per-row `unknown`). Both are stated;
    neither is ever a blank table.
    """
    if issues_unreadable is not None:
        return unreadable_note("The issue tracker", issues_unreadable)
    return summary_line(summary) + table(rows, repo=repo)
