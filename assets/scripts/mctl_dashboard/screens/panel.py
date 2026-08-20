"""The adjudication panel: where a verdict is actually recorded.

This is a **form**, not a widget. Verdict and disposition are radio inputs, the
reason is a required textarea, and submitting posts to the existing `/preview`
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

from mctl_dashboard.render import esc as _e
from mctl_dashboard.review import UNDER_REVIEW_CODES
from mctl_dashboard.state import ViewState
from mctl_dashboard.theme import LOCKED_BODY, LOCKED_RULE, STOP

#: The verdicts the panel offers. Deliberately a list rather than a closed
#: enum: 12 of 86 closed briefs carry a compound verdict, and at least one
#: records two different verdicts in a single submission
#: (`PASSED-TO-MAYOR-...-PLUS-DEPENDENCY-GRAPH-REJECTED`). Nothing here may
#: assume four is the final number.
VERDICTS: tuple[tuple[str, str], ...] = (
    ("approve", "approve"),
    ("revise", "revise"),
    ("reject", "reject"),
    ("defer", "defer"),
)

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
    name: str, label: str, *, state: str, disabled: bool
) -> str:
    struck = state == "held" and disabled
    style = (
        "font-family: var(--font-mono); font-size: 11px; padding: 3px 9px; "
        "border-radius: var(--radius-md); display: inline-flex; align-items: center; "
        "gap: 6px; border: 1px solid "
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
    return (
        f'<label style="{style}">'
        f'<input type="radio" name="verdict" value="{_e(name)}"{attrs} '
        'style="accent-color: var(--color-accent-600); margin: 0;">'
        f"{_e(label)}</label>"
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


def _disposition_control(brief: Mapping[str, Any]) -> str:
    """Which option the verdict adopts, offered as the brief's own options.

    A bare "option letter" text box asks the operator to remember what the
    letters were and to retype one correctly; the brief already states them,
    so the panel can offer them. Where a brief names no options the box is
    honest about that instead of demanding a letter that does not exist.

    The last choice is always to propose something else. A decision-maker who
    can only pick from the options as filed cannot say "none of these, do
    that" -- and that is a real verdict, not an absence of one.
    """
    options = list(brief.get("decision_options") or ())
    rows: list[str] = []

    def _chip(value: str, label: str, *, checked: bool = False) -> str:
        return (
            '<label style="display: flex; gap: 7px; align-items: baseline; '
            "font-family: var(--font-mono); font-size: 11px; padding: 4px 9px; "
            "border: 1px solid var(--color-divider); border-radius: var(--radius-md); "
            'cursor: pointer;">'
            f'<input type="radio" name="option" value="{_e(value)}"'
            f'{" checked" if checked else ""} '
            'style="accent-color: var(--color-accent-600); margin: 0; flex: none;">'
            f'<span style="min-width: 0;">{label}</span></label>'
        )

    rows.append(_chip("", "Accept the recommendation as filed", checked=True))
    for entry in options:
        if not isinstance(entry, Mapping):
            continue
        label = str(entry.get("label") or "").strip()
        title = str(entry.get("title") or entry.get("summary") or "").strip()
        if not label:
            continue
        text = f"{_e(label)} &middot; {_e(title)}" if title else _e(label)
        rows.append(_chip(label, text))

    rows.append(
        _chip(
            "other",
            "Other &mdash; propose your own",
        )
    )

    label_text = (
        "Disposition"
        if options
        else "Disposition &mdash; this brief names no options"
    )
    return (
        '<div style="font-size: 11.5px; letter-spacing: 0.04em; text-transform: uppercase; '
        f'color: var(--color-neutral-600); margin-bottom: 5px;">{label_text}</div>'
        '<div style="display: flex; flex-direction: column; gap: 5px; margin-bottom: 10px;">'
        + "".join(rows)
        + "</div>"
        '<textarea name="option_other" rows="2" '
        'placeholder="If you chose Other: describe the disposition you want. Recorded as a '
        'proposed option on the brief bead." '
        'style="width: 100%; font-family: var(--font-body); font-size: 12.5px; '
        "padding: 5px 8px; margin-bottom: 12px; border: 1px solid var(--color-divider); "
        'border-radius: var(--radius-sm); resize: vertical; box-sizing: border-box;">'
        "</textarea>"
    )


def _no_brainer_control() -> str:
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
        '<input type="checkbox" name="no_brainer" value="1" '
        'style="accent-color: var(--color-accent-600); margin: 0;">'
        "<strong>No-brainer</strong> &mdash; this should not have needed me"
        "</label>"
        '<textarea name="no_brainer_reason" rows="2" '
        'placeholder="Why was this a no-brainer? Recorded as a classifier signal, '
        'not part of the verdict." '
        'style="width: 100%; margin-top: 7px; font-family: var(--font-body); '
        "font-size: 12.5px; padding: 5px 8px; border: 1px solid var(--color-divider); "
        'border-radius: var(--radius-sm); resize: vertical; box-sizing: border-box;">'
        "</textarea>"
        "</div>"
    )


def entry(
    brief: Mapping[str, Any],
    options: Sequence[Mapping[str, Any]],
    view: ViewState,
    *,
    rig: str | None = None,
) -> str:
    """The adjudication form."""
    state, reason = panel_state(options)
    brief_id = str(brief.get("brief_id") or brief.get("bead_id") or "")

    controls = "".join(
        _verdict_control(
            name,
            label,
            state=state,
            disabled=state != "open" and name not in RETURN_VERDICTS,
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
        + '<form method="post" action="/preview">'
        f'<input type="hidden" name="operation" value="adjudicate">'
        f'<input type="hidden" name="brief_id" value="{_e(brief_id)}">'
        f"{rig_field}"
        '<div style="font-size: 11.5px; letter-spacing: 0.04em; text-transform: uppercase; '
        'color: var(--color-neutral-600); margin-bottom: 5px;">Verdict</div>'
        f'<div style="display: flex; gap: 7px; margin-bottom: 12px; flex-wrap: wrap;">'
        f"{controls}</div>"
        + _disposition_control(brief)
        +         '<div style="font-size: 11.5px; letter-spacing: 0.04em; text-transform: uppercase; '
        'color: var(--color-neutral-600); margin-bottom: 5px;">Reason</div>'
        '<textarea name="reason" required minlength="3" rows="3" '
        'placeholder="Why this verdict — recorded on the brief bead." '
        
        'style="width: 100%; font-family: var(--font-body); font-size: 13px; '
        "padding: 6px 8px; border: 1px solid var(--color-divider); "
        'border-radius: var(--radius-sm); resize: vertical; box-sizing: border-box;">'
        "</textarea>"
        + _no_brainer_control()
        + '<div style="display: flex; gap: 9px; align-items: center; margin-top: 13px;">'
        '<button class="btn btn-primary" type="submit">'
        "Review verdict &rarr;</button>"
        '<span class="mono" style="font-size: 10.5px; color: var(--color-neutral-600);">'
        + (
            "approve is unavailable here — you can still revise or reject"
            if locked
            else "shows the DRY RUN effect plan first — nothing is written yet"
        )
        + "</span></div>"
        "</form></div></section>"
    )
