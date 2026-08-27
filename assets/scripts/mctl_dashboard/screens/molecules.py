"""The Molecules screen (#109, #115, #153).

`molecules_list` and `molecules_show` were registered MCP tools reachable
from no page: `grep -rn molecules assets/scripts/mctl_dashboard/` found only
the client allowlist. This module is where they land.

The detail page is where #115's evidence core actually becomes visible: per
step, `expected_artifacts` (declared, #142) against `artifacts` (actual,
`gc.build.*`), the derived THREE-VALUED `is_complete`, and the five evidence
links with their honest tri-state. Two rendering rules carry the honesty
invariants to the pixel:

* **`is_complete: unknown` is not styled as a failure.** It means "no
  declaration, so nothing was measured" -- painting it red would claim a
  finding the city cannot support (P6.2's mirror).
* **`not_recorded` evidence links read "no recorder", never a cross or the
  word "broken".** An unrecorded link is not a failed one; a page that shows
  three red marks on `claimed`/`agent_active`/`commit` for every single
  molecule would train an operator to stop reading them, which is worse than
  not showing them at all.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from mctl_dashboard.render import esc as _e
from mctl_dashboard.render import molecule_href
from mctl_dashboard.render import stoplight


def _panel(title: str, body: str, *, region: str) -> str:
    return f'<section class="panel" data-region="{region}"><h2>{_e(title)}</h2>{body}</section>'


def molecules_list(payload: Mapping[str, Any], *, rig: str | None = None) -> str:
    """The roster: one row per RUN, not per work item (#109)."""
    rows: Sequence[Mapping[str, Any]] = payload.get("molecules") or []
    if not rows:
        return _panel(
            "Molecules",
            '<p class="lede">No molecules in this rig -- a measurement, not a failure to '
            "look (an unreadable store reports a diagnostic instead, never a bare empty "
            "list).</p>",
            region="molecules-empty",
        )
    body_rows = "".join(
        '<tr class="mc-row">'
        f'<td><a href="{molecule_href(m.get("id"), rig)}">'
        f'<span class="mono">{_e(m.get("id"))}</span></a></td>'
        f'<td>{_e(m.get("formula") or m.get("title"))}</td>'  # single-shape-ok: molecules_list row, not a brief
        f'<td><span class="mono">{_e(m.get("worker") or "-")}</span></td>'
        f'<td><span class="mono">{_e(m.get("rig") or "-")}</span></td>'
        f'<td><span class="mono">{_e(m.get("status"))}</span></td>'  # single-shape-ok: molecule root status, not a brief
        "</tr>"
        for m in rows
    )
    return _panel(
        "Molecules",
        f'<p class="lede"><strong>{len(rows)}</strong> molecule'
        f'{"" if len(rows) == 1 else "s"} -- one row per workflow RUN. No overall '
        '<span class="mono">state</span> column: advancing/stalled/stranded need the full '
        "evidence chain, which is not buildable today (#115) -- open a molecule for its "
        "per-step evidence instead.</p>"
        '<div class="scroll-x"><table class="ntdata" data-region="molecules-table">'
        "<thead><tr><th>Molecule</th><th>Formula</th><th>Worker</th><th>Rig</th>"
        "<th>Root status</th></tr></thead>"
        f"<tbody>{body_rows}</tbody></table></div>",
        region="molecules-list",
    )


#: Never styled as a failure -- see the module docstring.
_IS_COMPLETE_LABEL = {
    "complete": "complete",
    "incomplete": "incomplete",
    "unknown": "unknown (no declaration -- not measured)",
}


#: The stoplight tone each three-valued `is_complete` gets. `unknown` maps to
#: the neutral `ok` -- painting "no declaration, so nothing was measured" red
#: or green would claim a finding the city cannot support (P6.2's mirror).
_IS_COMPLETE_TONE = {"complete": "go", "incomplete": "warn", "unknown": "ok"}


def _is_complete_cell(step: Mapping[str, Any]) -> str:
    value = str(step.get("is_complete") or "unknown")
    label = _IS_COMPLETE_LABEL.get(value, value)
    return stoplight(label, _IS_COMPLETE_TONE.get(value, "ok"))


def _artifact_lists(step: Mapping[str, Any]) -> str:
    declared = step.get("expected_artifacts")
    if declared is None:
        return '<p class="lede">No <span class="mono">gc.expected_artifacts.v1</span> declared for this step.</p>'
    present = step.get("artifacts_present") or []
    missing = step.get("artifacts_missing") or []
    items = "".join(
        f'<li><span class="mono">{_e(path)}</span> -- '
        + ("present" if path in present else "missing")
        + "</li>"
        for path in declared
    )
    return f'<p class="lede">{len(declared)} declared.</p><ul class="reason-list">{items}</ul>'


#: `not_recorded` reads "no recorder" -- never a cross, never the word
#: "broken". See the module docstring.
_LINK_STATUS_LABEL = {
    "recorded": "recorded",
    "not_yet": "not yet recorded",
    "not_recorded": "no recorder",
}


def _evidence_block(step: Mapping[str, Any]) -> str:
    evidence: Mapping[str, Any] = step.get("evidence") or {}
    links: Sequence[Mapping[str, Any]] = evidence.get("links") or []
    items = "".join(
        f'<li><span class="mono">{_e(link.get("link"))}</span> -- '
        f'<strong>{_e(_LINK_STATUS_LABEL.get(str(link.get("status")), link.get("status")))}</strong>'  # single-shape-ok: evidence-link tri-state object, not a brief
        f' <span class="muted">{_e(link.get("reason"))}</span></li>'
        for link in links
    )
    broken_at = evidence.get("broken_at")
    broken_line = (
        f'<p class="review-note" data-region="broken-at">'
        f'<strong>Break: <span class="mono">{_e(broken_at)}</span>.</strong> '
        f"{_e(evidence.get('broken_at_reason'))}</p>"
        if broken_at
        else f'<p class="lede" data-region="broken-at">'
        f"No checkable break. {_e(evidence.get('broken_at_reason'))}</p>"
    )
    return f'<ul class="reason-list">{items}</ul>{broken_line}'


def cancel_control(molecule: Mapping[str, Any], rig: str | None) -> str:
    """The typed-cancel action, shown only when the tool reports it permitted.

    "Permitted" here is the coarse answer `molecules_show` carries -- the root is
    not already closed, so there is a run to stop (the `BriefOption.enabled`
    pattern applied to a molecule). The finer answer -- a step a worker is
    actively running, which needs force -- is the cancel tool's own dry-run
    refusal, surfaced when the operator previews. An already-finished molecule
    shows no control at all rather than a button that could only ever refuse.
    """
    molecule_id = _e(molecule.get("id"))
    if not molecule.get("is_cancellable"):
        return _panel(
            "Cancel",
            '<p class="lede">This molecule\'s root is '
            f'<span class="mono">{_e(molecule.get("status"))}</span> — it has finished or '  # single-shape-ok: molecule root row, not a brief
            "already been cancelled, so there is nothing running to stop.</p>",
            region="molecule-cancel-unavailable",
        )
    rig_field = (
        f'<input type="hidden" name="rig" value="{_e(rig)}">' if rig else ""
    )
    body = (
        '<p class="lede">Deliberately stop this run. Preview first — nothing is written '
        "until you confirm. The cancel closes the open steps and the root with a cancel "
        "reason and releases any claim; the record survives. A step a worker is actively "
        "running is refused unless you force it.</p>"
        '<form class="operation" method="post" action="/preview">'
        '<input type="hidden" name="operation" value="molecule_cancel">'
        f'<input type="hidden" name="root_bead_id" value="{molecule_id}">'
        + rig_field
        + '<label>Reason<input type="text" name="reason" '
        'placeholder="why this molecule is being cancelled"></label>'
        '<label><input type="checkbox" name="force" value="1"> '
        "Force — cancel even if a step is mid-execution (releases the worker’s claim)"
        "</label>"
        '<div><button type="submit" class="secondary">Preview cancel</button></div>'
        "</form>"
    )
    return _panel("Cancel this molecule", body, region="molecule-cancel")


def molecule_detail(payload: Mapping[str, Any], *, rig: str | None = None) -> str:
    """One molecule: identity, then per-step `expected_artifacts` vs
    `artifacts`, the three-valued `is_complete`, and the evidence links."""
    rows: Sequence[Mapping[str, Any]] = payload.get("molecules") or []
    if not rows:
        return _panel(
            "Molecule not found",
            '<p class="lede">No such molecule, or the store could not be read -- see the '
            "diagnostics above.</p>",
            region="molecule-not-found",
        )
    molecule = rows[0]
    identity = (
        '<dl class="kv">'
        f'<dt>Formula</dt><dd>{_e(molecule.get("formula") or "-")}</dd>'
        f'<dt>Worker</dt><dd class="mono">{_e(molecule.get("worker") or "-")}</dd>'
        f'<dt>Rig</dt><dd class="mono">{_e(molecule.get("rig") or "-")}</dd>'
        f'<dt>Root status</dt><dd class="mono">{_e(molecule.get("status"))}</dd>'  # single-shape-ok: molecule root row, not a brief
        "</dl>"
    )
    steps: Sequence[Mapping[str, Any]] = molecule.get("steps") or []
    if not steps:
        steps_body = '<p class="lede">This molecule has no steps.</p>'
    else:
        steps_body = "".join(
            '<section class="panel" data-region="molecule-step">'
            f'<h3><span class="mono">{_e(step.get("id"))}</span> {_e(step.get("title"))}</h3>'  # single-shape-ok: molecule-step row, not a brief
            f'<p class="lede">Kind <span class="mono">{_e(step.get("kind") or "-")}</span> '  # single-shape-ok: molecule-step row, not a brief
            f'&middot; bead status <span class="mono">{_e(step.get("status"))}</span> '  # single-shape-ok: molecule-step row, not a brief
            f"&middot; is_complete {_is_complete_cell(step)}</p>"
            "<h4>Declared vs actual artifacts</h4>"
            + _artifact_lists(step)
            + "<h4>Evidence links</h4>"
            + _evidence_block(step)
            + "</section>"
            for step in steps
        )
    return (
        _panel(
            f"Molecule {molecule.get('id')}",
            identity + f'<h3>Steps ({len(steps)})</h3>' + steps_body,
            region="molecule-detail",
        )
        + cancel_control(molecule, rig)
    )
