"""The adjudication panel: where a verdict is actually recorded.

This is a **form**, not a widget. Verdict and disposition are radio inputs, the
reason is an OPTIONAL textarea (briefs_adjudicate types `reason` as
`["string", "null"]` and the handler defaults it to `""`, so a bare verdict is a
legal call -- the form must not force what the schema does not; mc-qlmh), and
submitting posts to the existing `/preview`
route -- which already renders the DRY RUN effect plan, mints a single-use
token and holds the three-fingerprint staleness guard. Reusing that path rather
than building a parallel one is why the panel works with scripting disabled,
and why `MUTATION_ROUTES` stays exactly `("/preview", "/apply")`.

## Three states, not two

The design draws two: adjudicable, and HELD. Live data needs a third, and
conflating them would be the most consequential rendering mistake in this
dashboard.

**HELD** means *a gate failed, and approving would ratify a violation.* Red
panel, verdicts struck through and inert, reject the only way out. The operator
is being stopped from endorsing something known-bad.

**Refused-under-review** means *the core will not accept a verdict yet, but
nothing is known-bad.* `MBRF004` -- which gates roughly two thirds of the live
pending queue -- means the brief bead has no dependency edge to the thing it is
deciding about. The brief may be entirely sound; it is simply not attached to
its subject, so an approval would land on a bead pointing at nothing. That is
structural incompleteness, not a violation.

The rendering difference carries the whole distinction: **disabled, not struck
through.** Struck-through text says "this would be wrong". A disabled control
says "you may not, yet". On a queue where two thirds of briefs are in this
state, using the first would tell the operator most of their work is bad.

A further reason for restraint: a large share of that population turns out not
to be briefs at all. `POLICY` B2.1 already excludes decision beads created for
other purposes -- push authorisations, kill-switch receipts -- and 41 of 139
closed decision beads are `authorize-git-operation` receipts. `MBRF004` on a
push receipt is the checker asking a question that does not apply. The
discriminator is being implemented; this population is expected to shrink.

Treatment is chosen from the `disabled_reason`'s own code and severity rather
than by mapping every refusal onto HELD.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from mctl_dashboard.reading import attr
from mctl_dashboard.render import esc as _e
from mctl_dashboard.review import UNDER_REVIEW_CODES
from mctl_dashboard.state import ViewState
from mctl_dashboard.theme import LOCKED_BODY, LOCKED_RULE, STOP

#: The verdicts the panel offers. Deliberately a list rather than a closed
#: enum: 12 of 86 closed briefs carry a compound verdict, and at least one
#: records two different verdicts in a single submission
#: (`PASSED-TO-MAYOR-...-PLUS-DEPENDENCY-GRAPH-REJECTED`). Nothing here may
#: assume four is the final number.
#:
#: `defer` is a fourth verdict again (ADR 0002 D3, 2026-08-24): the Brief
#: Manager design draws it as a verdict radio, and #136's earlier removal is
#: overridden. The panel owns it -- the dashboard translates `verdict=defer`
#: to the existing `briefs_defer` tool (`app._preview`) rather than a second
#: control, so there is one place a disposition is chosen, not two disagreeing.
VERDICTS: tuple[tuple[str, str], ...] = (
    ("approve", "approve"),
    ("revise", "revise"),
    ("reject", "reject"),
    ("defer", "defer"),
)

#: One-line meaning hint per verdict (ADR 0002 D3). Kept beside `VERDICTS`
#: rather than folded into it so the `(name, label)` tuple shape stays a plain
#: two-item pair -- extensible by concatenation, and unpackable everywhere it
#: already is. A verdict with no hint here simply renders without one.
VERDICT_HINTS: dict[str, str] = {
    "approve": "adopt + dispatch per disposition",
    "revise": "sent back for extra work; returns via revise-return",
    "reject": "closed; nothing dispatches",
    "defer": "parked with a window; who and why recorded",
}

#: The one verdict that stays available under a HELD lock. Rejecting a brief
#: that reached the stack through a failed gate is the only response that does
#: not ratify the violation.
HELD_ESCAPE = "reject"

#: Verdicts that send a brief BACK. These are never gated, in any state.
#:
#: Refusal restricts what you may *ratify*, never what you may *return*. An
#: empty or malformed brief is precisely the thing you send back for revision,
#: and its emptiness is the reason for that verdict rather than an obstacle to
#: recording it. Gating these was a design error: it made the one action the
#: adjudicator actually needed on the empty briefs -- "revise, go add fields" --
#: the one action the panel would not accept.
RETURN_VERDICTS = frozenset({"revise", "reject"})


def _adjudicate_option(options: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for entry in options or ():
        if str(entry.get("id")) == "adjudicate":
            return entry
    return None


def panel_state(options: Sequence[Mapping[str, Any]]) -> tuple[str, Mapping[str, Any]]:
    """(state, disabled_reason) for this brief.

    `open` -- a verdict can be recorded.
    `refused` -- the core declines for a reason that is under review; nothing
        is known-bad.
    `held` -- a real gate failure; approving would ratify it.
    """
    entry = _adjudicate_option(options)
    if entry is None or entry.get("enabled"):
        return "open", {}
    reason = entry.get("disabled_reason") or {}
    code = str(reason.get("code") or "")
    if code in UNDER_REVIEW_CODES:
        return "refused", reason
    return "held", reason


def _verdict_control(
    name: str, label: str, *, state: str, disabled: bool, checked: bool = False
) -> str:
    struck = state == "held" and disabled
    style = (
        "font-family: var(--font-mono); font-size: 11px; padding: 4px 9px; "
        "border-radius: var(--radius-md); display: flex; align-items: baseline; "
        "gap: 7px; border: 1px solid "
    )
    if struck:
        # "This would be wrong." Reserved for a real violation.
        style += (
            "var(--color-neutral-300); color: var(--color-neutral-400); "
            "text-decoration: line-through; cursor: not-allowed;"
        )
    elif disabled:
        # "You may not, yet." Nothing is condemned.
        style += "var(--color-neutral-300); color: var(--color-neutral-500); cursor: not-allowed;"
    else:
        style += "var(--color-divider); color: var(--color-neutral-800); cursor: pointer;"
    attrs = ' disabled aria-disabled="true"' if disabled else ""
    if checked and not disabled:
        attrs += " checked"
    # The one-line meaning hint (ADR 0002 D3). It carries the same
    # line-through under HELD as the label, so a struck verdict reads as
    # struck whole rather than a crossed word beside a live gloss.
    hint = VERDICT_HINTS.get(name, "")
    hint_html = (
        f'<span data-region="verdict-hint" style="font-family: var(--font-body); '
        f"font-size: 11px; color: var(--color-neutral-600); flex: 1 1 auto; "
        f'min-width: 0;">{_e(hint)}</span>'
        if hint
        else ""
    )
    return (
        f'<label data-verdict="{_e(name)}" style="{style}">'
        f'<input type="radio" name="verdict" value="{_e(name)}"{attrs} '
        'style="accent-color: var(--color-accent-600); margin: 0; flex: none;">'
        f'<span style="flex: none; font-weight: 600;">{_e(label)}</span>'
        f"{hint_html}</label>"
    )


def _refusal_notice(state: str, reason: Mapping[str, Any]) -> str:
    code = str(reason.get("code") or "")
    message = str(reason.get("message") or "")
    policy = str(reason.get("policy_reference") or reason.get("policy_ref") or "")

    if state == "held":
        return (
            f'<div style="border: 1px solid {STOP["error"]["edge"]}; '
            f'border-left: 5px solid {STOP["error"]["edge"]}; background: {STOP["error"]["bg"]}; '
            'padding: 11px 13px; margin-bottom: 12px; border-radius: var(--radius-sm);">'
            f'<div class="mono" style="font-size: 11px; color: {STOP["error"]["fg"]}; '
            'letter-spacing: 0.04em; margin-bottom: 4px;">ADJUDICATION HELD &middot; '
            f'<code class="diagnostic-code">{_e(code)}</code></div>'
            f'<div style="font-size: 13px;">{_e(message)}</div>'
            '<div style="font-size: 12.5px; margin-top: 7px; color: var(--color-neutral-800);">'
            "A gate failed before this reached the stack. Approving would ratify "
            "the violation, so approve is unavailable. Sending it back is not: "
            "revise it once you know the repair, or reject it.</div>"
            "</div>"
        )

    # Refused, but nothing is condemned.
    return (
        '<div style="border: 1px solid var(--color-divider); '
        "border-left: 3px solid var(--color-accent-600); "
        "background: var(--color-neutral-100); padding: 11px 13px; "
        'margin-bottom: 12px; border-radius: var(--radius-sm);">'
        '<div class="mono" style="font-size: 11px; color: var(--color-neutral-700); '
        'letter-spacing: 0.04em; margin-bottom: 4px;">APPROVE UNAVAILABLE &middot; '
        f'<code class="diagnostic-code">{_e(code)}</code>'
        f'{f" &middot; {_e(policy)}" if policy else ""}</div>'
        f'<div style="font-size: 13px;">{_e(message)}</div>'
        '<div style="font-size: 12.5px; margin-top: 7px; color: var(--color-neutral-800);">'
        "This brief is <strong>not linked to what it decides</strong>, so an approval "
        "would land on a bead that points at nothing. Nothing here says the brief is "
        "wrong — what is missing is the edge, not the reasoning. "
        "<strong>Revise and reject remain available</strong>: a brief you cannot "
        "ratify is still a brief you can send back."
        "</div>"
        '<div style="font-size: 12px; margin-top: 7px; color: var(--color-neutral-600); '
        'font-style: italic;">'
        "This check is under review. It used to fire on most of the queue; "
        "implementing B2.1's discriminator removed 49 beads that were never briefs "
        "— push authorisations and kill-switch receipts, which decide about no other "
        "bead and so cannot have a source dependency — taking the blocked population "
        "from 120 to 71. Of that residue only about 30 are real open briefs."
        "</div>"
        "</div>"
    )


def _option_title(entry: Mapping[str, Any]) -> str:
    return str(entry.get("title") or entry.get("summary") or "").strip()  # single-shape-ok: decision option


def _option_meta(entry: Mapping[str, Any]) -> str:
    """The small marks an option card carries -- and only the ones it carries.

    ADR 0002 D5 drops the design's per-option `blast` / `reversible` / `gates`
    chips: they were fixture fiction, no such fields exist on the parsed option
    type. What a `ParsedDecisionOption` (core `BriefDecisionOption`) actually
    holds is `recommended`, `confidence` and `source`, so those are what render
    here -- each only when present, so an option with no confidence shows no
    empty confidence chip. Enabled/locked is a separate axis and reads from the
    action option's `BriefOption.enabled`, not from these.
    """
    def _mark(text: str, *, strong: bool = False) -> str:
        weight = "font-weight: 600; " if strong else ""
        colour = "var(--color-accent-800)" if strong else "var(--color-neutral-600)"
        return (
            f'<span style="font-family: var(--font-mono); font-size: 9.5px; {weight}'
            f"letter-spacing: 0.03em; padding: 0 5px; border: 1px solid var(--color-divider); "
            f'border-radius: var(--radius-md); color: {colour}; white-space: nowrap;">{text}</span>'
        )

    marks: list[str] = []
    if entry.get("recommended"):
        marks.append(_mark("recommended", strong=True))
    confidence = str(entry.get("confidence") or "").strip()
    if confidence:
        marks.append(_mark(f"conf {_e(confidence)}"))
    source = str(entry.get("source") or "").strip()
    if source:
        marks.append(_mark(f"src {_e(source)}"))
    if not marks:
        return ""
    return (
        '<span data-region="option-meta" style="display: inline-flex; gap: 4px; '
        'flex-wrap: wrap; margin-left: 6px;">' + "".join(marks) + "</span>"
    )


def _adopt_reason(brief: Mapping[str, Any], letter: str) -> str:
    """The reason text a one-click adopt pre-quotes for option `letter`.

    Quoting the option the operator adopted, rather than leaving the box blank,
    is the point of click-to-adopt: the recorded reason then says which of the
    brief's own alternatives the verdict took, in the brief's own words. The
    human still confirms it through the preview before anything is written.
    """
    for entry in attr(brief, "decision_options") or ():
        if isinstance(entry, Mapping) and str(entry.get("label") or "").strip() == letter:
            title = _option_title(entry)
            return (
                f"Adopting option {letter}: {title}." if title
                else f"Adopting option {letter} as filed."
            )
    return f"Adopting option {letter}."


def _adopt_href(brief: Mapping[str, Any], letter: str, *, rig: str | None) -> str:
    """One click to adopt an option: reload the panel with it pre-filled.

    A link rather than script, so click-to-adopt works with JavaScript off --
    it lands the same `?prefill=adopt:{letter}` the server already forwards to
    this panel, which then checks approve, selects the option and quotes it in
    the reason. Preview-first is untouched: adopting fills the form, it does not
    record anything.
    """
    brief_id = str(attr(brief, "brief_id") or attr(brief, "bead_id") or "")
    query = f"?prefill=adopt:{_e(letter)}" + (f"&rig={_e(rig)}" if rig else "")
    return f"/briefs/{_e(brief_id)}{query}#mc-adjudicate"


def _defer_window(*, disabled: bool = False) -> str:
    """The defer window (days), used only when the verdict is `defer`.

    Defer is a verdict here (ADR 0002 D3), but the `briefs_defer` tool it
    routes to needs a window the other verdicts do not. Rather than a second
    form, the panel carries one small field the dashboard reads only when
    `verdict=defer` is submitted (`app._preview` translates it, `_arguments_for`
    reads `days`). Left blank it defers for the tool's own default. It stays
    out of the way for the common approve/revise/reject path -- a labelled,
    optional day count, not a step.
    """
    dis = " disabled" if disabled else ""
    return (
        '<div data-region="defer-window" style="display: flex; align-items: baseline; '
        'gap: 7px; margin: -4px 0 12px; padding-left: 2px;">'
        '<label style="font-family: var(--font-mono); font-size: 10.5px; '
        'color: var(--color-neutral-600);">defer window (days)</label>'
        f'<input type="text" name="days" inputmode="numeric" placeholder="7"{dis} '
        'style="width: 58px; font-family: var(--font-mono); font-size: 11.5px; '
        "padding: 3px 6px; border: 1px solid var(--color-divider); "
        'border-radius: var(--radius-sm); box-sizing: border-box;">'
        '<span style="font-family: var(--font-body); font-size: 10.5px; '
        'color: var(--color-neutral-500);">only applies when the verdict is '
        "<strong>defer</strong>; blank defers for the default window</span>"
        "</div>"
    )


def _disposition_control(
    brief: Mapping[str, Any], *, rig: str | None = None, selected: str | None = None
) -> str:
    """Which option the verdict adopts, offered as the brief's own options.

    A bare "option letter" text box asks the operator to remember what the
    letters were and to retype one correctly; the brief already states them,
    so the panel can offer them. Where a brief names no options the box is
    honest about that instead of demanding a letter that does not exist.

    Each named option also carries an **adopt** link -- one click that fills
    the whole form for that option (approve, the option selected, the reason
    quoting it) so the common case is a click, not three separate inputs. The
    radios remain for picking without committing the verdict.

    The last choice is always to propose something else. A decision-maker who
    can only pick from the options as filed cannot say "none of these, do
    that" -- and that is a real verdict, not an absence of one.
    """
    options = list(attr(brief, "decision_options") or ())
    # A brief whose body carries its options section more than once parses each
    # letter repeatedly, so the picker would offer '', A, B, C, A, B, C, other
    # (mc-13e0, mc-kij9). Collapse to one move per distinct label, and remember
    # which labels repeated so the cause can be stated -- the duplication is in the
    # brief bead's body (a doubled §4), not invented here.
    _seen: set[str] = set()
    _unique: list[Mapping[str, Any]] = []
    duplicated_labels: list[str] = []
    for entry in options:
        if not isinstance(entry, Mapping):
            continue
        label = str(entry.get("label") or "").strip()
        if not label:
            continue
        key = label.upper()
        if key in _seen:
            if label not in duplicated_labels:
                duplicated_labels.append(label)
            continue
        _seen.add(key)
        _unique.append(entry)
    options = _unique
    rows: list[str] = []

    def _chip(value: str, label: str, *, checked: bool = False, adopt: str = "") -> str:
        return (
            '<label style="display: flex; gap: 7px; align-items: baseline; '
            "font-family: var(--font-mono); font-size: 11px; padding: 4px 9px; "
            "border: 1px solid var(--color-divider); border-radius: var(--radius-md); "
            'cursor: pointer;">'
            f'<input type="radio" name="option" value="{_e(value)}"'
            f'{" checked" if checked else ""} '
            'style="accent-color: var(--color-accent-600); margin: 0; flex: none;">'
            f'<span style="min-width: 0; flex: 1 1 auto;">{label}</span>'
            f"{adopt}</label>"
        )

    rows.append(
        _chip("", "Accept the recommendation as filed", checked=selected is None)
    )
    for entry in options:
        if not isinstance(entry, Mapping):
            continue
        label = str(entry.get("label") or "").strip()
        title = _option_title(entry)
        if not label:
            continue
        text = f"{_e(label)} &middot; {_e(title)}" if title else _e(label)
        text += _option_meta(entry)
        adopt = (
            f'<a class="mc-adopt" data-region="adopt-option" '
            f'data-option="{_e(label)}" href="{_adopt_href(brief, label, rig=rig)}" '
            'style="flex: none; font-family: var(--font-mono); font-size: 10.5px; '
            "padding: 1px 7px; border: 1px solid var(--color-accent-600); "
            "border-radius: var(--radius-md); color: var(--color-accent-800); "
            'white-space: nowrap;">adopt &rarr;</a>'
        )
        rows.append(_chip(label, text, checked=label == selected, adopt=adopt))

    rows.append(
        _chip(
            "other",
            "Other &mdash; propose your own",
            checked=selected == "other",
        )
    )

    label_text = (
        "Disposition"
        if options
        else "Disposition &mdash; this brief names no options"
    )
    cause_note = (
        '<p data-region="options-deduped" style="font-size: 11px; '
        'color: var(--color-warn, #8f6a1f); margin: -3px 0 9px;">'
        f"This brief&rsquo;s body repeats its options section, so "
        f"{_e(', '.join(duplicated_labels))} appeared more than once; each move is "
        "shown here once. The duplication is in the brief bead&rsquo;s body (a "
        "doubled &sect;4) and should be repaired there.</p>"
        if duplicated_labels
        else ""
    )
    return (
        '<div style="font-size: 11.5px; letter-spacing: 0.04em; text-transform: uppercase; '
        f'color: var(--color-neutral-600); margin-bottom: 5px;">{label_text}</div>'
        '<div style="display: flex; flex-direction: column; gap: 5px; margin-bottom: 10px;">'
        + "".join(rows)
        + "</div>"
        + cause_note
        + '<textarea name="option_other" rows="2" '
        'placeholder="If you chose Other: describe the disposition you want. Recorded as a '
        'proposed option on the brief bead." '
        'style="width: 100%; font-family: var(--font-body); font-size: 12.5px; '
        "padding: 5px 8px; margin-bottom: 12px; border: 1px solid var(--color-divider); "
        'border-radius: var(--radius-sm); resize: vertical; box-sizing: border-box;">'
        "</textarea>"
    )


def _no_brainer_control(*, checked: bool = False, reason: str = "") -> str:
    """The no-brainer flag: "this reached me and should not have".

    Deliberately NOT a verdict. Ticking it does not change what is recorded as
    the disposition; it records that surfacing this brief was a pipeline
    regression, which is a signal about the *classifier* rather than about the
    brief. Taylor's standing rule is that a no-brainer reaching the adjudicator
    at all is the defect -- so the flag has to be capturable at the moment of
    adjudication, when the judgement is fresh, or it never gets captured.
    """
    return (
        '<div style="margin-top: 12px; padding: 9px 11px; '
        "border: 1px dashed var(--color-neutral-300); "
        'border-radius: var(--radius-sm); background: var(--color-neutral-050);">'
        '<label style="display: flex; align-items: center; gap: 7px; '
        'font-size: 12.5px; cursor: pointer;">'
        '<input type="checkbox" name="no_brainer" value="1"'
        + (" checked" if checked else "")
        + ' style="accent-color: var(--color-accent-600); margin: 0;">'
        "<strong>No-brainer</strong> &mdash; this should not have needed me"
        "</label>"
        '<textarea name="no_brainer_reason" rows="2" '
        'placeholder="Why was this a no-brainer? Recorded as a classifier signal, '
        'not part of the verdict." '
        'style="width: 100%; margin-top: 7px; font-family: var(--font-body); '
        "font-size: 12.5px; padding: 5px 8px; border: 1px solid var(--color-divider); "
        'border-radius: var(--radius-sm); resize: vertical; box-sizing: border-box;">'
        + _e(reason)
        + "</textarea>"
        "</div>"
    )


#: The standing verdict for a brief that carries nothing to judge. Taylor's
#: instruction, 2026-08-19: mark the empty ones revise, flag them no-brainer,
#: "and send them back saying they need to give more fields".
INCOMPLETE_REASON = (
    "Returned as incomplete: this brief carries no body, so there is nothing "
    "stated for a verdict to be about. Re-file it with the required fields -- "
    "what is being decided, the options, and what each one commits us to."
)
INCOMPLETE_NO_BRAINER = (
    "An empty brief should not have reached adjudication; the classifier "
    "should have caught it."
)


def prefill_offer(brief: Mapping[str, Any], *, rig: str | None = None) -> str:
    """One click to load the standing verdict for an empty brief.

    There are ~90 of these. Adjudicating them one at a time by retyping the
    same sentence is the kind of work that does not get done, and doing them
    in a batch means recording ~90 verdicts nobody read. This is the middle:
    the form arrives filled in, and every one still gets a human confirming it.
    """
    has_body = bool(str(brief.get("body") or "").strip()) or bool(brief.get("sections"))
    if has_body:
        return ""
    brief_id = str(attr(brief, "brief_id") or attr(brief, "bead_id") or "")
    query = f"?prefill=incomplete" + (f"&rig={_e(rig)}" if rig else "")
    return (
        '<div data-region="prefill-offer" style="margin-bottom: 11px; padding: 8px 11px; '
        "border: 1px solid var(--color-divider); "
        "border-left: 3px solid var(--color-accent-600); "
        'border-radius: var(--radius-sm); background: var(--color-neutral-100);">'
        '<div style="font-size: 12.5px;">This brief states nothing to judge. '
        f'<a href="/briefs/{_e(brief_id)}{query}#mc-adjudicate">'
        "Fill in the standing return &rarr;</a></div>"
        '<div class="mono" style="font-size: 10.5px; color: var(--color-neutral-600); '
        'margin-top: 4px;">revise &middot; no-brainer &middot; asks for the required '
        "fields. Nothing is recorded until you confirm it.</div>"
        "</div>"
    )


def _save_draft_control(brief_id: str) -> str:
    """Save the in-progress verdict to THIS browser only (ADR 0002 D6).

    Same contract as the design's priority list: personal, machine-local, no
    authority, and explicitly labelled as not following the user. It is inline
    localStorage (wired in `assets.SCRIPT`, keyed by brief id) -- so with
    JavaScript off the button simply does nothing and every other control still
    works. It is not a mutation: nothing browser-local can record a verdict, so
    it never touches `/preview` or `/apply`.
    """
    return (
        '<div data-region="save-draft" data-brief-id="' + _e(brief_id) + '" '
        'style="margin-top: 12px; display: flex; align-items: center; gap: 9px; '
        'flex-wrap: wrap;">'
        '<button type="button" class="btn btn-ghost" data-role="save-draft" '
        'style="font-size: 11px; padding: 4px 10px;">Save draft</button>'
        '<button type="button" class="btn btn-ghost" data-role="clear-draft" '
        'style="font-size: 11px; padding: 4px 10px;">Clear draft</button>'
        '<span data-role="draft-status" class="mono" '
        'style="font-size: 10px; color: var(--color-neutral-600);"></span>'
        '<span class="mono" style="font-size: 10px; color: var(--color-neutral-500); '
        'font-style: italic;">saved on this browser only — does not follow you</span>'
        "</div>"
    )


def _dry_run_block() -> str:
    """A passive, render-only note of the dry-run effect plan (ADR 0002 D3).

    It sits UNDER the panel and is not a step or a gate: submitting runs one
    dry run through the existing preview path and renders the effect plan, and
    this block says so where the operator will read it. It renders nothing from
    the city -- the live plan is computed by `/preview`; this is the standing
    explanation of what the one Submit produces, not a second control.
    """
    return (
        '<div data-region="dry-run-plan" style="margin-top: 14px; padding: 10px 12px; '
        "border: 1px solid var(--color-divider); border-left: 3px solid "
        "var(--color-neutral-400); border-radius: var(--radius-sm); "
        'background: var(--color-neutral-050);">'
        '<div class="mono" style="font-size: 10px; letter-spacing: 0.05em; '
        'text-transform: uppercase; color: var(--color-neutral-600); margin-bottom: 4px;">'
        "Dry run</div>"
        '<div style="font-size: 12px; color: var(--color-neutral-800);">'
        "Submitting runs a <strong>dry run</strong> and shows the effect plan — the "
        "bead fields it would write and the follow-up it would dispatch. It is "
        "shown to be read, not stepped through: nothing here is an extra gate."
        "</div></div>"
    )


def entry(
    brief: Mapping[str, Any],
    options: Sequence[Mapping[str, Any]],
    view: ViewState,
    *,
    rig: str | None = None,
    prefill: str | None = None,
) -> str:
    """The adjudication form."""
    state, reason = panel_state(options)
    brief_id = str(attr(brief, "brief_id") or attr(brief, "bead_id") or "")

    filled = prefill == "incomplete"
    # `?prefill=adopt:{letter}` is one-click adoption of a named option: it
    # arrives from the option's adopt link and pre-fills approve + that option
    # + a reason quoting it. Parsed here, not in the router, so the panel owns
    # the whole pre-fill and the app just forwards the raw prefill value.
    adopt_letter = (
        prefill.split(":", 1)[1].strip()
        if prefill and prefill.startswith("adopt:")
        else None
    )
    adopting = bool(adopt_letter)
    controls = "".join(
        _verdict_control(
            name,
            label,
            state=state,
            disabled=state != "open" and name not in RETURN_VERDICTS,
            checked=(filled and name == "revise") or (adopting and name == "approve"),
        )
        for name, label in VERDICTS
    )

    locked = state != "open"
    # `locked` still drives the refusal notice and the styling, but no longer
    # disables the form itself -- a return verdict is always recordable.
    bar_bg = STOP["error"]["edge"] if state == "held" else "var(--color-neutral-900)"
    bar_fg = STOP["error"]["bg"] if state == "held" else "var(--color-accent-200)"
    body_bg = LOCKED_BODY if state == "held" else "var(--color-neutral-100)"
    border = STOP["error"]["edge"] if state == "held" else "var(--color-neutral-900)"
    title = "Repair this violation" if state == "held" else "Adjudicate"

    rig_field = f'<input type="hidden" name="rig" value="{_e(rig)}">' if rig else ""

    return (
        f'<section id="mc-adjudicate" data-region="adjudicate" data-panel-state="{_e(state)}" '
        f'style="border: 1px solid {border}; border-radius: var(--radius-md); '
        'max-width: 640px; overflow: hidden; margin-top: 18px;">'
        f'<div style="background: {bar_bg}; color: {bar_fg}; padding: 7px 12px; '
        "font-family: var(--font-heading); font-size: 14px; font-weight: 600; "
        f'letter-spacing: 0.05em; text-transform: uppercase;">{_e(title)}</div>'
        f'<div style="padding: 13px 14px; background: {body_bg};">'
        + (_refusal_notice(state, reason) if locked else "")
        + ("" if filled else prefill_offer(brief, rig=rig))
        + '<form method="post" action="/preview">'
        f'<input type="hidden" name="operation" value="adjudicate">'
        f'<input type="hidden" name="brief_id" value="{_e(brief_id)}">'
        f"{rig_field}"
        '<div style="font-size: 11.5px; letter-spacing: 0.04em; text-transform: uppercase; '
        'color: var(--color-neutral-600); margin-bottom: 5px;">Verdict</div>'
        f'<div data-region="verdict-set" style="display: flex; flex-direction: column; '
        f'gap: 5px; margin-bottom: 12px;">{controls}</div>'
        + _defer_window(disabled=locked)
        + _disposition_control(brief, rig=rig, selected=adopt_letter)
        +         '<div style="font-size: 11.5px; letter-spacing: 0.04em; text-transform: uppercase; '
        'color: var(--color-neutral-600); margin-bottom: 5px;">Reason</div>'
        '<textarea name="reason" rows="3" '
        'placeholder="Why this verdict — recorded on the brief bead." '

        'style="width: 100%; font-family: var(--font-body); font-size: 13px; '
        "padding: 6px 8px; border: 1px solid var(--color-divider); "
        'border-radius: var(--radius-sm); resize: vertical; box-sizing: border-box;">'
        + (
            _e(INCOMPLETE_REASON) if filled
            else _e(_adopt_reason(brief, adopt_letter)) if adopting
            else ""
        )
        + "</textarea>"
        + _no_brainer_control(
            checked=filled, reason=INCOMPLETE_NO_BRAINER if filled else ""
        )
        + _save_draft_control(brief_id)
        + '<div style="display: flex; gap: 9px; align-items: center; margin-top: 13px;">'
        '<button class="btn btn-primary" type="submit">'
        "Submit verdict &rarr;</button>"
        '<span class="mono" style="font-size: 10.5px; color: var(--color-neutral-600);">'
        + (
            "approve is unavailable here — you can still revise or reject"
            if locked
            else "one click — submitting records this verdict; the dry-run effect "
            "plan below shows what it does"
        )
        + "</span></div>"
        "</form>"
        + _dry_run_block()
        + "</div></section>"
    )
