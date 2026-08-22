"""Pile, Deferred, Adjudicated, Malformed -- the lanes either side of the stack.

These four screens are where the design and the core disagree most, so the
governing rule here is that **an absence is labelled with which kind it is**.
There are three, and collapsing them is how a dashboard starts lying:

* **No source.** The pile is not readable through the typed surface at all.
  Rendering an empty table would say "the pile is empty", which is a
  measurement nobody took.
* **A real zero.** No brief on the hecke rig is deferred. That is a fact about
  the queue and should read as one -- not as a gap.
* **Readable rows, unreadable field.** 31 briefs are adjudicated and the
  payload carries no verdict. `briefs.py::_verdict` computes one internally to
  decide `decision_state`, but `to_dict` never emits it, so this screen can say
  *which* briefs were decided and not *what was decided* -- on a screen whose
  entire purpose is the second.

A fourth lane exists because the data has one and the design does not.
`malformed` is 19 of 114 live briefs, and neither the adopted design nor the
sidebar had anywhere to put them, which made a sixth of the queue invisible.
They are surfaced here, and never as a bare count: "malformed" means *closed
with no verdict field*, not damaged, and the caveat travels with the number
(honesty property 2).
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from mctl_dashboard.reading import attr
from mctl_dashboard.render import esc as _e

ISSUE_66 = "https://github.com/tdupu/mathcity/issues/66"


def _heading(title: str, subtitle: str) -> str:
    return (
        f'<h1 style="font-family: var(--font-heading); font-size: 27px; '
        f'font-weight: 600; margin: 0 0 2px;">{_e(title)}</h1>'
        f'<div class="mono" style="font-size: 11.5px; color: var(--color-neutral-600);">'
        f"{_e(subtitle)}</div>"
        '<div style="height: 2px; background: var(--color-neutral-900); '
        'margin: 9px 0 14px;"></div>'
    )


def _gap(body: str) -> str:
    return f'<p class="review-note" style="margin: 0 0 14px;">{body}</p>'


def _rows(
    briefs: Sequence[Mapping[str, Any]],
    *,
    extra: str = "",
    cell: Any = None,
) -> str:
    """`extra` is one fixed trailing cell; `cell` derives one per brief."""
    body = "".join(
        "<tr>"
        f'<td><a href="/briefs/{_e(attr(brief, "brief_id") or attr(brief, "bead_id"))}">'
        f'<span class="mono">{_e(attr(brief, "bead_id"))}</span></a></td>'
        f'<td style="white-space: normal;">{_e(attr(brief, "title"))}</td>'
        f'<td><span class="mono">{_e(brief.get("updated_at") or "—")}</span></td>'
        + (cell(brief) if cell else extra)
        + "</tr>"
        for brief in briefs
    )
    return (
        '<div class="scroll-x" style="border-bottom: 2px solid var(--color-neutral-900);">'
        '<table class="ntdata"><thead><tr>'
        "<th>Bead</th><th>Title</th><th>Updated</th>"
        + ("<th>Verdict</th>" if (extra or cell) else "")
        + "</tr></thead><tbody>"
        + body
        + "</tbody></table></div>"
    )


def verdict_cell(brief: Mapping[str, Any]) -> str:
    """The recorded verdict, with where it was read from and how sure that is.

    Provenance is not decoration here. `source` ranges over typed_field,
    decisions_track, close_reason, notes and brief_frontmatter, and a verdict
    lifted out of a close_reason at low confidence is a different artifact
    from a typed field -- shown identically, the weak ones would be read as
    strong.
    """
    verdict = attr(brief, "verdict")
    if not isinstance(verdict, Mapping) or not verdict.get("text"):
        return '<td><span class="mono">&mdash;</span></td>'
    text = str(verdict["text"])
    source = str(verdict.get("source") or "")
    confidence = str(verdict.get("confidence") or "")
    marks = " · ".join(part for part in (source, confidence) if part)
    return (
        '<td><span class="mono">' + _e(text) + "</span>"
        + (
            '<br><span class="mono" style="font-size: 10px; '
            'color: var(--color-neutral-600);">' + _e(marks) + "</span>"
            if marks
            else ""
        )
        + "</td>"
    )


def pile() -> str:
    """Produced-but-unpromoted briefs. No source exists yet."""
    return (
        '<section data-region="pile">'
        + _heading("Pile", "produced but not yet promoted")
        + _gap(
            "<strong>The pile is not readable through the typed surface.</strong> "
            "Nothing below is a count of zero — no tool reports pile membership or "
            "gate state, so this screen cannot say what is waiting or what holds it. "
            f'Tracked as <a href="{ISSUE_66}">issue #66</a> (gate results per pile '
            "item) and in the design's own backend list as §G9."
        )
        + '<p class="lede">Gate evaluation lives in <span class="mono">'
        "brief-check.sh</span> and the shuffler — shell, outside the typed surface. "
        "Exposing it is the largest single item on the backend side, and it belongs "
        "to the fast-drain work rather than a second evaluator here.</p>"
        "</section>"
    )


def _count(briefs: Sequence[Mapping[str, Any]]) -> str:
    """"1 brief", not "1 briefs" -- these lanes now legitimately hold one."""
    n = len(briefs)
    return f"{n} brief" if n == 1 else f"{n} briefs"


def deferred(briefs: Sequence[Mapping[str, Any]]) -> str:
    """Briefs held out of the stack until their window expires."""
    if not briefs:
        return (
            '<section data-region="deferred">'
            + _heading("Deferred", "held out of the stack until their window expires")
            + '<p class="lede"><strong>No briefs are deferred.</strong> Read from '
            "both places deferral is recorded: <span class=\"mono\">status</span>, "
            "which <span class=\"mono\">plan_deferral</span> writes, and "
            "<span class=\"mono\">decision_state</span>, which is computed "
            "separately and does not currently take that value. This screen used to "
            "consult only the second and reported a confident zero while a brief sat "
            "deferred in the queue.</p>"
            "</section>"
        )
    return (
        '<section data-region="deferred">'
        + _heading("Deferred", _count(briefs))
        + _gap(
            "<strong>The defer window is not shown, because it is not readable.</strong> "
            "<span class=\"mono\">effects.py</span> writes "
            "<span class=\"mono\">defer_until</span>, "
            "<span class=\"mono\">defer_reason</span> and "
            "<span class=\"mono\">deferred_at</span> when a deferral is applied, but the "
            "read path returns only a boolean and discards the date, so this screen "
            "can say a brief is deferred and not until when, by whom, or why. "
            f'Tracked as <a href="{ISSUE_66}">issue #66</a>.'
        )
        + _rows(briefs)
        + "</section>"
    )


def adjudicated(briefs: Sequence[Mapping[str, Any]]) -> str:
    """Closed decision beads. Immutable -- no reopen affordance (B3.8).

    The heading promises "newest first", so the rows must actually be sorted
    by `updated_at` -- the same field the Updated column shows. A brief
    missing the field sorts last rather than raising or being dropped: a
    row with an unreadable date is still a row the operator needs to see,
    just not one that can be placed relative to the ones that have a date.
    """
    if not briefs:
        return (
            '<section data-region="adjudicated">'
            + _heading("Adjudicated", "closed decision beads")
            + '<p class="lede">Nothing has been adjudicated in this rig yet.</p>'
            "</section>"
        )
    briefs = sorted(briefs, key=lambda brief: brief.get("updated_at") or "", reverse=True)
    return (
        '<section data-region="adjudicated">'
        + _heading("Adjudicated", f"{len(briefs)} closed · newest first · immutable")
        + _gap(
            "<strong>The verdict is shown with where it was read from.</strong> "
            "The read path emits a verdict object — text, source and confidence — "
            "so this screen names what was decided, not merely that something was. "
            "Source ranges over <span class=\"mono\">typed_field</span>, "
            "<span class=\"mono\">decisions_track</span>, "
            "<span class=\"mono\">close_reason</span>, "
            "<span class=\"mono\">notes</span> and "
            "<span class=\"mono\">brief_frontmatter</span>: a verdict recovered from "
            "a close reason is a weaker artifact than a typed field, and is marked "
            "as such rather than shown as equivalent. The option taken and the "
            "follow-up bead are still not exposed. "
            f'Tracked as <a href="{ISSUE_66}">issue #66</a>.'
        )
        + _rows(briefs, cell=verdict_cell)
        + '<p class="lede" style="margin-top: 10px; font-style: italic;">'
        "Decision beads are never reopened (B3.8) — a change of mind is a new bead. "
        "That is why there is no control here to undo one.</p>"
        "</section>"
    )


def junk(briefs: Sequence[Mapping[str, Any]]) -> str:
    """Briefs no verdict can land on, with the reason stated per row.

    Taylor asked for these to be *separated out*, not hidden -- "it is a good
    signal for debugging". The first version filtered them away entirely,
    which is the failure this dashboard exists to not commit: the page looked
    healthy because the unhealthy rows were gone.

    One lane rather than four, because the population's value is being seen at
    once. The reason column carries the distinction that four lanes would have
    carried structurally, and it is derived from what the write path refuses
    rather than from a taxonomy maintained by hand.
    """
    from ..app import junk_reason

    if not briefs:
        return (
            '<section data-region="junk">'
            + _heading("Junk", 0)
            + _gap(
                "No brief in scope is unusable. Every open brief here can take "
                "a verdict of some kind."
            )
            + "</section>"
        )
    return (
        '<section data-region="junk">'
        + _heading("Junk", _count(briefs))
        + _gap(
            "Briefs <strong>no verdict can land on</strong>. They are here rather "
            "than hidden, because the size and shape of this population is a "
            "signal worth reading — a brief nobody can see is a brief nobody "
            "debugs. Nothing here is deleted, and nothing here is a judgement "
            "about the brief's content. "
            "<strong>A brief whose <span class=\"mono\">approve</span> is gated "
            "but which can still be sent back is NOT here</strong> — it stays in "
            "the stack with that one control switched off. "
            "<strong>This lane spans every decision state</strong> — open, "
            "adjudicated and malformed alike — so it is larger than the junk "
            "count on the stack, which counts only the open ones that would "
            "otherwise be queued for a verdict."
        )
        + '<ul class="reason-list" data-region="junk-reasons">'
        + "".join(
            f'<li><span class="mono">{_e(str(attr(b, "brief_id") or "?"))}</span> — '
            f"{_e(junk_reason(b) or '')}</li>"
            for b in briefs
        )
        + "</ul>"
        + _rows(
            briefs,
            cell=lambda b: f'<td style="white-space: normal;">{_e(junk_reason(b) or "")}</td>',
        )
        + "</section>"
    )


def malformed(briefs: Sequence[Mapping[str, Any]]) -> str:
    """Closed briefs carrying no verdict field.

    A lane the design does not have. Nineteen of 114 live briefs are in this
    state, and with nowhere to put them they were invisible.
    """
    if not briefs:
        return ""
    return (
        '<section data-region="malformed">'
        + _heading("Malformed", _count(briefs))
        + _gap(
            "<strong>Read this count carefully.</strong> "
            "&ldquo;Malformed&rdquo; here means <em>closed with no verdict "
            "field</em> — it does <strong>not</strong> mean the brief is damaged, "
            "and it is not a queue of things to repair. The verdicts for many of "
            "these are recorded in <span class=\"mono\">close_reason</span> or "
            "<span class=\"mono\">notes</span>, which the reader now does consult "
            "for adjudicated briefs but not for these, "
            "and a substantial share of the beads counted here were never briefs at "
            "all. The classification is under review."
        )
        + _rows(briefs)
        + "</section>"
    )
