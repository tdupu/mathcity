"""One brief, in full: the screen an adjudication is actually made from.

The adopted design draws seven numbered sections (§1 what is being decided
through §7 plan membership). Live briefs do not look like that, and this module
is built for the ones that exist rather than the ones the design drew. Measured
across 25 pending hecke briefs on 2026-08-19:

* **9 of 25 carried no headings at all** and parse to zero sections (MBRF041).
  Their body is one run of prose.
* Of the 16 that did parse, **42 sections were unmapped against 31 mapped**.
* **None had all seven.** The most any brief mapped was four; eight mapped one.
* 14 of 16 did put §1 first, so Decision-at-Top holds where sections exist.

Three consequences, each of which is a rendering rule here:

1. **Document order is preserved and unmapped sections are rendered.** They are
   the majority of the content -- an "Encoding" or "Expected output" section
   carries the mathematics. Reordering into §1-§7 would rearrange the author's
   argument; dropping the unmapped ones would discard most of it.
2. **An absent section is not drawn as an empty slot.** Rendering the five
   sections a brief lacks as empty headings would assert the author omitted
   required sections, when in fact the parser found no heading that mapped.
3. **A brief that did not parse shows its body and the reason.** `MBRF041` on
   a third of the queue is a fact about how briefs are written, not a defect in
   any one of them.

The section mapping itself comes from `mctl_core` -- `briefs_show` returns
`sections` already typed, each with its `section_index` and `section_key`. This
module never parses markdown. A second parser here would drift from what the
core reports, which is the failure `client.py` exists to prevent.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from mctl_dashboard import fields, knowl
from mctl_dashboard.render import esc as _e
from mctl_dashboard.state import ViewState
from mctl_dashboard.theme import STOP

#: §-number to the design's heading. From `mctl_core.briefs.PRESENT_IT_SECTIONS`.
SECTION_LABELS: dict[int, str] = {
    1: "What is being decided",
    2: "Recommended answer",
    3: "Assumptions surfaced",
    4: "Alternatives named",
    5: "Risks",
    6: "Supporting evidence",
    7: "Plan membership, blocking, required gates",
}


def _section_heading(section: Mapping[str, Any]) -> tuple[str, str]:
    """(label, marker) for one section.

    A mapped section shows its § marker *and* the author's own heading, because
    the two differ: `section_index` 2 on a live brief was headed "Rationale",
    not "Recommended answer". Showing only the canonical label would misquote
    the document; showing only the author's heading would lose the mapping.
    """
    index = section.get("section_index")
    heading = str(section.get("heading") or "").strip()
    if index in SECTION_LABELS:
        return heading or SECTION_LABELS[int(index)], f"§{int(index)}"
    return heading or "Untitled section", ""


def _body_paragraphs(text: str, *, key: str, knowls: Mapping[str, Any]) -> str:
    """Render a section body as paragraphs, with knowls, without a parser.

    Splitting on blank lines is presentation, not parsing: it decides where
    paragraph breaks go and reads no structure out of the text. The section
    boundaries and their meaning came from the core.
    """
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    if not chunks:
        return ""
    return "".join(
        '<p style="margin: 0 0 8px; text-wrap: pretty; color: var(--color-neutral-900);">'
        + knowl.tokenize(chunk, key=f"{key}-{position}", **knowls)
        + "</p>"
        for position, chunk in enumerate(chunks)
    )


def _decision_at_top_notice(sections: Sequence[Mapping[str, Any]]) -> str:
    """Flag a brief whose decision is not its first content.

    Decision-at-Top is an invariant of the brief form, not a style preference:
    a brief that opens with its origin story makes the reader reconstruct the
    question before they can answer it.
    """
    if not sections:
        return ""
    indices = [section.get("section_index") for section in sections]
    if 1 not in [index for index in indices if index]:
        return ""
    if indices[0] == 1:
        return ""
    return (
        '<p class="review-note" data-region="decision-at-top">'
        "<strong>Decision-at-Top not satisfied.</strong> This brief states what "
        "is being decided, but not first — the reader has to reconstruct the "
        "question before they can answer it. Rendered in the author's order.</p>"
    )


def _parse_notice(diagnostics: Sequence[Mapping[str, Any]]) -> str:
    """Say why a body produced the sections it did, in the body's own words."""
    if not diagnostics:
        return ""
    items = "".join(
        '<li class="diagnostic" data-code="{code}" data-under-review="false">'
        '<code class="diagnostic-code">{code}</code> '
        '<span class="diagnostic-message">{message}</span></li>'.format(
            code=_e(item.get("code")), message=_e(item.get("message"))
        )
        for item in diagnostics
    )
    return (
        '<section class="panel" data-region="body-parse">'
        "<h2 style=\"font-size: 14px; margin: 0 0 6px;\">How this body parsed</h2>"
        '<p class="lede">The section structure below is what the core could read '
        "out of this brief. These notes say why it read what it did — they are "
        "about the brief's shape, not its correctness.</p>"
        f'<ul class="diagnostics">{items}</ul>'
        "</section>"
    )


def properties(brief: Mapping[str, Any]) -> str:
    """The right-hand properties box: every attribute the brief actually has.

    Formerly a fixed list of eight rows, several of which were always empty.
    It now renders whatever the payload carries, so a field a producer adds
    tomorrow appears without a dashboard change -- and a field this brief does
    not have simply is not drawn, rather than showing an em dash that reads as
    missing data.

    `field_sources` and `field_conflicts` are passed through when the core
    supplies them, so a frontmatter-sourced value is distinguishable from a
    bead-sourced one and a disagreement between the two is shown rather than
    silently resolved.
    """
    body = fields.attributes(**fields.unpack(brief), region="properties")
    if not body:
        return ""
    return (
        '<aside class="properties-body" '
        'style="width: 254px; flex: none; border: 1px solid var(--color-divider); '
        'border-radius: var(--radius-md); overflow: hidden;">'
        '<h2 class="mc-section-head" style="font-size: 12px;">Properties</h2>'
        '<div style="padding: 6px 10px; background: var(--color-neutral-100);">'
        + body
        + "</div></aside>"
    )


def status_banner(
    brief: Mapping[str, Any], options: Sequence[Mapping[str, Any]] | None
) -> str:
    """Whether this brief can be acted on, stated before it is read.

    The adjudication panel sits below the body, the properties and the
    diagnostics -- on a real brief about 59% down the page. A reader who opens
    a refused brief scrolls all of that to arrive at four disabled controls and
    only then learns there was nothing to do. Decision-at-Top is the rule the
    briefs themselves must follow; the page about a brief owes the reader the
    same courtesy.

    So: state it at the top, name the code, and offer a jump to the panel
    rather than making the reader hunt for it.
    """
    from mctl_dashboard.screens import panel as panel_screen

    state_name, reason = panel_screen.panel_state(options or [])
    has_body = bool(str(brief.get("body") or "").strip()) or bool(brief.get("sections"))

    if state_name == "open":
        text = (
            '<strong>Ready to adjudicate.</strong> '
            '<a href="#mc-adjudicate">Go to the verdict panel &darr;</a>'
        )
        tone = "border-left: 3px solid var(--color-accent-600);"
    else:
        code = str(reason.get("code") or "")
        message = str(reason.get("message") or "")
        held = state_name == "held"
        lead = (
            "<strong>Approving is held.</strong>"
            if held
            else "<strong>Approving is unavailable.</strong>"
        )
        # An empty brief used to be described as a dead end -- "nothing you can
        # record". That was wrong twice over: it is not true (it can be sent
        # back) and the emptiness is itself the reason to send it back. Say
        # what the reader can do, because on these briefs there is something.
        empty = (
            " It carries no body either, which is <strong>itself grounds to "
            "return it</strong>."
            if not has_body
            else ""
        )
        text = (
            f"{lead} "
            f'<code class="diagnostic-code">{_e(code)}</code> — {_e(message)}'
            f"{empty} "
            "You can still send it back &mdash; "
            '<a href="#mc-adjudicate">revise or reject in the panel &darr;</a>'
        )
        tone = (
            f"border-left: 3px solid {STOP['error']['edge']};"
            if held
            else "border-left: 3px solid var(--color-neutral-400);"
        )

    return (
        f'<div data-region="brief-status" style="{tone} '
        "background: var(--color-neutral-100); padding: 9px 12px; margin: 10px 0 0; "
        'border-radius: var(--radius-sm); font-size: 12.5px;">'
        f"{text}</div>"
    )


def queue_nav(
    brief: Mapping[str, Any],
    neighbours: Mapping[str, Any] | None,
    *,
    rig: str | None = None,
) -> str:
    """Where this brief sits in the queue, and how to leave it.

    Adjudicating is a sequence, not a lookup: the operator works a queue of
    ~180 and the cost that matters is the cost of getting to the next one. A
    page that can only be left by the back button turns a queue into 180
    separate errands.

    `neighbours` carries `index`, `total`, `prev_id` and `next_id`. When the
    core could not tell us the queue -- a degraded rig, a brief that is not on
    this stack -- the position is simply omitted rather than guessed, and the
    queue link stays, because that is still true.
    """
    suffix = f"?rig={_e(rig)}" if rig else ""
    left = f'<a href="/queue{suffix}">&larr; queue</a>'
    bead = str(brief.get("bead_id") or "")

    if not neighbours:
        return (
            '<div class="mono" data-region="queue-nav" style="display: flex; gap: 10px; '
            'align-items: baseline; font-size: 11.5px; color: var(--color-neutral-600);">'
            f"{left}<span>{_e(bead)}</span></div>"
        )

    index = neighbours.get("index")
    total = neighbours.get("total")
    position = (
        f"brief {int(index) + 1} of {int(total)}"
        if isinstance(index, int) and isinstance(total, int)
        else ""
    )
    prev_id = neighbours.get("prev_id")
    next_id = neighbours.get("next_id")
    prev_link = (
        f'<a href="/briefs/{_e(prev_id)}{suffix}">&larr; prev</a>'
        if prev_id
        else '<span style="color: var(--color-neutral-400);">&larr; prev</span>'
    )
    next_link = (
        f'<a href="/briefs/{_e(next_id)}{suffix}">next &rarr;</a>'
        if next_id
        else '<span style="color: var(--color-neutral-400);">next &rarr;</span>'
    )
    return (
        '<div class="mono" data-region="queue-nav" style="display: flex; gap: 10px; '
        'align-items: baseline; font-size: 11.5px; color: var(--color-neutral-600); '
        'font-feature-settings: \'tnum\';">'
        f"{left}"
        f'<span style="color: var(--color-neutral-400);">&middot;</span>'
        f"<span>{_e(bead)}</span>"
        f'<span style="margin-left: auto; display: flex; gap: 12px; align-items: baseline;">'
        f'<span>{_e(position)}</span>{prev_link}{next_link}</span>'
        "</div>"
    )


def detail(
    brief: Mapping[str, Any],
    view: ViewState,
    *,
    knowls: Mapping[str, Any] | None = None,
    options: Sequence[Mapping[str, Any]] | None = None,
    neighbours: Mapping[str, Any] | None = None,
    rig: str | None = None,
) -> str:
    """The brief detail screen."""
    knowls = dict(knowls or {})
    sections = list(brief.get("sections") or ())
    diagnostics = list(brief.get("body_diagnostics") or ())
    bead = str(brief.get("bead_id") or "")

    blocks: list[str] = []
    for position, section in enumerate(sections):
        heading, marker = _section_heading(section)
        marker_html = (
            f'<span class="mono" style="font-size: 11px; color: var(--color-accent-700); '
            f'margin-right: 7px;">{_e(marker)}</span>'
            if marker
            else ""
        )
        unmapped = not marker
        note = (
            '<span class="mono" style="font-size: 10px; color: var(--color-neutral-500); '
            'margin-left: 8px;">the author\'s own section</span>'
            if unmapped
            else ""
        )
        blocks.append(
            f'<section data-region="brief-section" data-section-index="{_e(section.get("section_index") or "")}" '
            'style="margin-bottom: 17px;">'
            '<h2 style="font-family: var(--font-heading); font-size: 17px; '
            'font-weight: 600; margin: 0 0 5px; letter-spacing: 0.01em;">'
            f"{marker_html}{_e(heading)}{note}</h2>"
            + _body_paragraphs(
                str(section.get("body") or ""), key=f"{bead}-{position}", knowls=knowls
            )
            + "</section>"
        )

    if not sections:
        body_text = str(brief.get("body") or "")
        if body_text.strip():
            blocks.append(
                '<section data-region="brief-body-unparsed" style="margin-bottom: 17px;">'
                '<h2 style="font-family: var(--font-heading); font-size: 17px; '
                'font-weight: 600; margin: 0 0 5px;">Brief body</h2>'
                + _body_paragraphs(body_text, key=f"{bead}-body", knowls=knowls)
                + "</section>"
            )
        else:
            blocks.append(
                '<p class="lede" data-region="brief-body-empty">This brief bead '
                "carries no description, so there is no body to read. The verdict "
                "would be recorded against a brief with no stated content.</p>"
            )

    content = (
        '<div style="flex: 1 1 auto; min-width: 0; max-width: 640px;">'
        + queue_nav(brief, neighbours, rig=rig)
        + f'<h1 style="font-family: var(--font-heading); font-size: 30px; '
        f'font-weight: 600; margin: 6px 0 2px; line-height: 1.15;">'
        f'{_e(brief.get("title"))}</h1>'
        f'<div class="mono" style="font-size: 11.5px; color: var(--color-neutral-600);">'
        f'{_e(bead)}</div>'
        + status_banner(brief, options)
        + '<div style="height: 2px; background: var(--color-neutral-900); '
        'margin: 14px 0 18px;"></div>'
        + _decision_at_top_notice(sections)
        + _parse_notice(diagnostics)
        + "".join(blocks)
        + "</div>"
    )
    return (
        '<div style="display: flex; gap: 22px; align-items: flex-start;">'
        + content
        + properties(brief)
        + "</div>"
    )
