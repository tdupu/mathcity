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


def _rows(briefs: Sequence[Mapping[str, Any]], *, extra: str = "") -> str:
    body = "".join(
        "<tr>"
        f'<td><a href="/briefs/{_e(brief.get("brief_id") or brief.get("bead_id"))}">'
        f'<span class="mono">{_e(brief.get("bead_id"))}</span></a></td>'
        f'<td style="white-space: normal;">{_e(brief.get("title"))}</td>'
        f'<td><span class="mono">{_e(brief.get("updated_at") or "—")}</span></td>'
        + extra
        + "</tr>"
        for brief in briefs
    )
    return (
        '<div class="scroll-x" style="border-bottom: 2px solid var(--color-neutral-900);">'
        '<table class="ntdata"><thead><tr>'
        "<th>Bead</th><th>Title</th><th>Updated</th>"
        + ("<th>Verdict</th>" if extra else "")
        + "</tr></thead><tbody>"
        + body
        + "</tbody></table></div>"
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


def deferred(briefs: Sequence[Mapping[str, Any]]) -> str:
    """Briefs held out of the stack until their window expires."""
    if not briefs:
        return (
            '<section data-region="deferred">'
            + _heading("Deferred", "held out of the stack until their window expires")
            + '<p class="lede"><strong>No briefs are deferred.</strong> This is a '
            "real zero read from the bead store, not a gap: the deferred state is "
            "reported by <span class=\"mono\">decision_state</span> and no brief "
            "currently carries it.</p>"
            "</section>"
        )
    return (
        '<section data-region="deferred">'
        + _heading("Deferred", f"{len(briefs)} briefs")
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
    """Closed decision beads. Immutable -- no reopen affordance (B3.8)."""
    if not briefs:
        return (
            '<section data-region="adjudicated">'
            + _heading("Adjudicated", "closed decision beads")
            + '<p class="lede">Nothing has been adjudicated in this rig yet.</p>'
            "</section>"
        )
    return (
        '<section data-region="adjudicated">'
        + _heading("Adjudicated", f"{len(briefs)} closed · newest first · immutable")
        + _gap(
            "<strong>The verdict itself is not readable, only that one was "
            "recorded.</strong> "
            "<span class=\"mono\">briefs.py::_verdict</span> reads a verdict from the "
            "bead to decide that these are adjudicated rather than malformed, but "
            "<span class=\"mono\">to_dict</span> never emits it — so this screen can "
            "say which briefs were decided and not what was decided, which is the "
            "column it exists for. The option taken, the recorded reason and the "
            "follow-up bead are absent for the same reason. "
            f'Tracked as <a href="{ISSUE_66}">issue #66</a>, and second on the '
            "design's own backend list."
        )
        + _rows(
            briefs,
            extra='<td><span class="mono" style="color: var(--color-neutral-500);" '
            'title="recorded on the bead but not exposed by the read path">'
            "&mdash;</span></td>",
        )
        + '<p class="lede" style="margin-top: 10px; font-style: italic;">'
        "Decision beads are never reopened (B3.8) — a change of mind is a new bead. "
        "That is why there is no control here to undo one.</p>"
        "</section>"
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
        + _heading("Malformed", f"{len(briefs)} briefs")
        + _gap(
            "<strong>Read this count carefully.</strong> "
            "&ldquo;Malformed&rdquo; here means <em>closed with no verdict "
            "field</em> — it does <strong>not</strong> mean the brief is damaged, "
            "and it is not a queue of things to repair. The verdicts for many of "
            "these are recorded in <span class=\"mono\">close_reason</span> or "
            "<span class=\"mono\">notes</span>, which the reader does not consult, "
            "and a substantial share of the beads counted here were never briefs at "
            "all. The classification is under review."
        )
        + _rows(briefs)
        + "</section>"
    )
