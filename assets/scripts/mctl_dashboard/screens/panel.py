"""The adjudication panel: where a verdict is actually recorded.

This is a **form**, not a widget. Verdict and disposition are radio inputs, the
reason is an OPTIONAL textarea (briefs_relay_adjudication types `reason` as
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
nothing is known-bad.* `MBRF004` means the brief bead has no dependency edge to
the thing it is deciding about. The brief may be entirely sound; it is simply
not attached to its subject, so an approval would land on a bead pointing at
nothing. That is structural incompleteness, not a violation.

This paragraph used to open *"`MBRF004` -- which gates roughly two thirds of
the live pending queue"*. **It gates none of it.** `MBRF004` is
`severity = "WARN"` (`assets/mctl/diagnostics.toml`, emitted at
`briefs.py:1652`), and `briefs.py::_blocking_diagnostic` selects only
ERROR/FATAL, so a WARN can never block a verdict. The claim was accurate until
issue #137 downgraded the code from ERROR on 2026-08-22; this file's copy never
followed. The severity source is cited rather than a fresh population count on
purpose -- a count is what went stale here, twice.

What survives the correction is the *rendering* rule below, which never
depended on MBRF004 blocking anything: a brief raising it is refused-under-
review, not HELD.

The rendering difference carries the whole distinction: **disabled, not struck
through.** Struck-through text says "this would be wrong". A disabled control
says "you may not, yet". `MBRF004` is raised across a large share of the
pending queue, so using the first would tell the operator most of their work is
bad. (Deliberately not a number: the "two thirds" this sentence used to carry
is the same stale figure corrected above.)

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


def _dedup_options(brief: Mapping[str, Any]) -> tuple[list[Mapping[str, Any]], list[str]]:
    """The brief's named options, one per distinct label, plus the repeats.

    A brief whose body carries its options section more than once parses each
    letter repeatedly, so the moves would offer A, B, C, A, B, C (mc-13e0,
    mc-kij9). Collapse to one move per distinct label and remember which labels
    repeated so the cause can be stated -- the duplication is in the brief
    bead's body (a doubled §4), not invented here.
    """
    seen: set[str] = set()
    unique: list[Mapping[str, Any]] = []
    duplicated: list[str] = []
    for entry in attr(brief, "decision_options") or ():
        if not isinstance(entry, Mapping):
            continue
        label = str(entry.get("label") or "").strip()
        if not label:
            continue
        key = label.upper()
        if key in seen:
            if label not in duplicated:
                duplicated.append(label)
            continue
        seen.add(key)
        unique.append(entry)
    return unique, duplicated


def _refusal_tag(reason: Mapping[str, Any]) -> str:
    """The disabled_reason a refused move carries beside itself.

    A refused move is disabled where it sits, with the code and message that
    refused it right there -- not hidden behind a banner, and not struck
    through (struck is reserved for a real gate violation). The operator reads
    why *this* move is unavailable without leaving the move.
    """
    code = str(reason.get("code") or "").strip()
    message = str(reason.get("message") or "").strip()
    if not code and not message:
        return ""
    body = f'<code class="diagnostic-code">{_e(code)}</code>' if code else ""
    if message:
        body += f' {_e(message)}' if body else _e(message)
    return (
        '<span data-region="move-refusal" class="mono" style="font-size: 10px; '
        'color: var(--color-neutral-600); padding-left: 2px;">' + body + "</span>"
    )


def _move_button(
    value: str,
    label_html: str,
    *,
    disabled: bool,
    struck: bool,
    verdict: str = "",
    option: str = "",
    reason_policy: str = "none",
) -> str:
    """One legal move, rendered as a submit button.

    The button *is* the control: pressing it posts the whole form (its `move`
    value carries both the verdict and the option together) to `/preview`, so
    an illegal verdict×option pair is unexpressible and one press is one
    dry-run -- no radio, no separate Submit, and it works with scripting off.

    `reason_policy` wires Taylor's textbox table (mc-q3m5q). The panel carries a
    single `required` reason box; a move that needs no reason (approve, reject,
    defer) carries `formnovalidate` so that required box does not block it, and
    declares `data-reason="none"`. The one move that requires it (revise) omits
    `formnovalidate` and declares `data-reason="required"`, so pressing it
    enforces the box JS-off. The opt-in path is enforced server-side regardless.
    """
    style = (
        "font-family: var(--font-mono); font-size: 11px; padding: 5px 10px; "
        "border-radius: var(--radius-md); display: flex; align-items: baseline; "
        "gap: 7px; text-align: left; width: 100%; box-sizing: border-box; "
        "border: 1px solid "
    )
    if struck:
        # "This would be wrong." Reserved for a real violation.
        style += (
            "var(--color-neutral-300); color: var(--color-neutral-400); "
            "text-decoration: line-through; cursor: not-allowed; "
            "background: var(--color-neutral-050);"
        )
    elif disabled:
        # "You may not, yet." Nothing is condemned.
        style += (
            "var(--color-neutral-300); color: var(--color-neutral-500); "
            "cursor: not-allowed; background: var(--color-neutral-050);"
        )
    else:
        style += (
            "var(--color-divider); color: var(--color-neutral-800); "
            "cursor: pointer; background: var(--color-surface, #ffffff);"
        )
    attrs = ' disabled aria-disabled="true"' if disabled else ""
    # A move that needs no reason skips the required-box validation; revise does
    # not, so pressing it enforces the box with scripting off.
    if reason_policy != "required":
        attrs += " formnovalidate"
    attrs += f' data-reason="{_e(reason_policy)}"'
    opt_attr = f' data-option="{_e(option)}"' if option else ""
    hint = VERDICT_HINTS.get(verdict, "")
    hint_html = (
        f'<span data-region="verdict-hint" style="font-family: var(--font-body); '
        f"font-size: 11px; color: var(--color-neutral-600); flex: 1 1 auto; "
        f'min-width: 0;">{_e(hint)}</span>'
        if hint
        else ""
    )
    return (
        f'<button type="submit" name="move" value="{_e(value)}" '
        f'data-move="{_e(value)}"{opt_attr}{attrs} style="{style}">'
        f"{label_html}{hint_html}</button>"
    )


def _defer_window() -> str:
    """The defer DURATION -- a number and a unit -- shown with the defer move.

    Taylor's spec (mc-q3m5q): defer takes a duration (days / weeks / months), not
    prose. So the defer move carries a small number field and a unit picker, NOT
    a textarea. The dashboard reads them only when the defer move is pressed
    (`app._preview` translates it, `_arguments_for` converts the unit to `days`).
    Left blank it defers for the tool's own default. It rides in the defer move's
    own group, not at form level for every verdict.
    """
    units = "".join(
        f'<option value="{unit}"'
        + (" selected" if unit == "days" else "")
        + f">{unit}</option>"
        for unit in ("days", "weeks", "months")
    )
    return (
        '<div data-region="defer-window" style="display: flex; align-items: baseline; '
        'gap: 7px; margin: 2px 0 0; padding-left: 26px;">'
        '<label style="font-family: var(--font-mono); font-size: 10.5px; '
        'color: var(--color-neutral-600);">defer for</label>'
        '<input type="text" name="days" inputmode="numeric" placeholder="7" '
        'style="width: 52px; font-family: var(--font-mono); font-size: 11.5px; '
        "padding: 3px 6px; border: 1px solid var(--color-divider); "
        'border-radius: var(--radius-sm); box-sizing: border-box;">'
        '<select name="days_unit" style="font-family: var(--font-mono); '
        "font-size: 11.5px; padding: 3px 6px; border: 1px solid var(--color-divider); "
        f'border-radius: var(--radius-sm); box-sizing: border-box;">{units}</select>'
        '<span style="font-family: var(--font-body); font-size: 10.5px; '
        'color: var(--color-neutral-500);">blank defers for the default window</span>'
        "</div>"
    )


def _move_group(value: str, button: str, *, extra: str = "", refusal: str = "") -> str:
    return (
        f'<div data-move-group="{_e(value)}" '
        'style="display: flex; flex-direction: column; gap: 3px;">'
        f"{button}{refusal}{extra}</div>"
    )


def _moves(
    brief: Mapping[str, Any],
    *,
    state: str,
    reason: Mapping[str, Any],
) -> str:
    """The one control: the legal moves for this brief, as submit buttons.

    Its members ARE the legal verdict×option pairs -- Approve A, Approve B,
    Approve (other…), Revise, Reject, Defer -- so the two illegal states the
    old verdict×disposition product allowed (approve + a blank option on a
    multi-option brief -> MOPT001; reject + a named option) cannot be posted.

    Ratifying moves (each Approve, and Defer) are gated when the brief is not
    open: struck through under a real gate failure (HELD), disabled-not-struck
    under a refusal that is only under review. Returning moves (revise, reject)
    are NEVER gated -- refusal restricts what you may ratify, not what you may
    send back.
    """
    options, duplicated = _dedup_options(brief)
    ratify_disabled = state != "open"
    struck = state == "held"
    refusal = _refusal_tag(reason) if ratify_disabled else ""

    rows: list[str] = []
    if options:
        for entry in options:
            label = str(entry.get("label") or "").strip()
            if not label:
                continue
            title = _option_title(entry)
            head = f"Approve {_e(label)}"
            if title:
                head += f" &middot; {_e(title)}"
            label_html = (
                f'<span style="flex: none; font-weight: 600;">{head}</span>'
                f"{_option_meta(entry)}"
            )
            button = _move_button(
                f"approve:{label}",
                label_html,
                disabled=ratify_disabled,
                struck=struck,
                verdict="approve",
                option=label,
            )
            rows.append(_move_group(f"approve:{label}", button, refusal=refusal))
        # "none of these, do that" -- an approve that proposes its own option.
        # It is a REVISE in the backend and the proposal is the reason, so it
        # requires the one reason box (mc-q3m5q) rather than a second textarea.
        other_button = _move_button(
            "approve:other",
            '<span style="flex: none; font-weight: 600;">Approve (other&hellip;)</span>'
            '<span style="font-family: var(--font-body); font-size: 11px; '
            'color: var(--color-neutral-600); flex: 1 1 auto; min-width: 0;">'
            "propose your own disposition in the reason</span>",
            disabled=ratify_disabled,
            struck=struck,
            verdict="approve",
            reason_policy="required",
        )
        rows.append(
            _move_group(
                "approve:other",
                other_button,
                refusal=refusal,
            )
        )
    else:
        # A brief that names no options: Approve carries no option at all, so
        # there is nothing for MOPT001 to be about.
        approve_button = _move_button(
            "approve",
            '<span style="flex: none; font-weight: 600;">Approve</span>',
            disabled=ratify_disabled,
            struck=struck,
            verdict="approve",
        )
        rows.append(_move_group("approve", approve_button, refusal=refusal))

    # Returning moves -- never gated, in any state. Revise requires the reason
    # box (it is the "go add these fields" instruction); reject does not, unless
    # the operator opts in, which is enforced server-side.
    for name in ("revise", "reject"):
        button = _move_button(
            name,
            f'<span style="flex: none; font-weight: 600;">{name.capitalize()}</span>',
            disabled=False,
            struck=False,
            verdict=name,
            reason_policy="required" if name == "revise" else "none",
        )
        rows.append(_move_group(name, button))

    # Defer -- a ratifying-side move (it parks rather than returns), so gated.
    defer_button = _move_button(
        "defer",
        '<span style="flex: none; font-weight: 600;">Defer</span>',
        disabled=ratify_disabled,
        struck=struck,
        verdict="defer",
    )
    rows.append(
        _move_group(
            "defer",
            defer_button,
            extra="" if ratify_disabled else _defer_window(),
            refusal=refusal,
        )
    )

    cause_note = (
        '<p data-region="options-deduped" style="font-size: 11px; '
        'color: var(--color-warn, #8f6a1f); margin: 6px 0 0;">'
        f"This brief&rsquo;s body repeats its options section, so "
        f"{_e(', '.join(duplicated))} appeared more than once; each move is "
        "shown here once. The duplication is in the brief bead&rsquo;s body (a "
        "doubled &sect;4) and should be repaired there.</p>"
        if duplicated
        else ""
    )
    label_text = (
        "The moves this brief permits"
        if options
        else "The moves this brief permits &mdash; it names no options"
    )
    return (
        '<div style="font-size: 11.5px; letter-spacing: 0.04em; text-transform: uppercase; '
        f'color: var(--color-neutral-600); margin-bottom: 5px;">{label_text}</div>'
        '<div data-region="moves" style="display: flex; flex-direction: column; '
        'gap: 6px; margin-bottom: 12px;">'
        + "".join(rows)
        + "</div>"
        + cause_note
    )


def _no_brainer_control(*, checked: bool = False) -> str:
    """The no-brainer opt-in: "this reached me and should not have".

    Deliberately NOT a verdict. Ticking it does not change what is recorded as
    the disposition; it records that surfacing this brief was a pipeline
    regression, which is a signal about the *classifier* rather than about the
    brief. Taylor's standing rule is that a no-brainer reaching the adjudicator
    at all is the defect -- so the flag has to be capturable at the moment of
    adjudication, when the judgement is fresh, or it never gets captured.

    mc-q3m5q: at most one textbox, ever. So the no-brainer no longer carries its
    own textarea -- ticking it makes the single reason box REQUIRED (declared by
    `data-requires-reason`, enforced server-side), and that reason is recorded as
    the classifier signal too. A plain checkbox needs no disclosure.
    """
    return (
        '<label data-region="no-brainer" '
        'style="display: flex; align-items: center; gap: 7px; margin-top: 12px; '
        "padding: 9px 11px; border: 1px dashed var(--color-neutral-300); "
        "border-radius: var(--radius-sm); background: var(--color-neutral-050); "
        'font-size: 12px; cursor: pointer;">'
        '<input type="checkbox" name="no_brainer" value="1" data-requires-reason'
        + (" checked" if checked else "")
        + ' style="accent-color: var(--color-accent-600); margin: 0;">'
        "<span><strong>No-brainer</strong> &mdash; this brief should not have "
        "reached me (records a classifier signal; the reason above is required "
        "when ticked)</span>"
        "</label>"
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
    """The adjudication form.

    ONE control -- the legal moves -- posts through the existing `/preview`
    route. Each move is a submit button, so pressing it runs that move's own
    dry-run (verdict AND option posted together) with no JavaScript and no
    separate Submit step. The reason, the no-brainer flag and the browser-local
    draft ride the same form.
    """
    state, reason = panel_state(options)
    brief_id = str(attr(brief, "brief_id") or attr(brief, "bead_id") or "")

    # The only pre-fill the panel still honours is the empty-brief standing
    # return (`?prefill=incomplete`): it fills the reason and ticks no-brainer,
    # and the operator presses Revise. Adopting a named option is no longer a
    # pre-fill -- pressing that option's Approve move IS the adoption, and it
    # goes straight to the move's dry-run.
    filled = prefill == "incomplete"

    locked = state != "open"
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
        + _moves(brief, state=state, reason=reason)
        + '<div style="font-size: 11.5px; letter-spacing: 0.04em; text-transform: uppercase; '
        'color: var(--color-neutral-600); margin-bottom: 5px;">Reason</div>'
        # mc-q3m5q: one textbox, ever. It is `required`; the moves that need no
        # reason carry `formnovalidate` and skip it, so it only bites revise (and
        # an opt-in, enforced server-side). No "optional" -- when it is asked
        # for, it is asked for.
        '<textarea name="reason" rows="3" required data-region="reason" '
        'placeholder="Why this move — recorded on the brief bead. Required for '
        'revise, and whenever you flag a no-brainer below." '
        'style="width: 100%; font-family: var(--font-body); font-size: 13px; '
        "padding: 6px 8px; border: 1px solid var(--color-divider); "
        'border-radius: var(--radius-sm); resize: vertical; box-sizing: border-box;">'
        + (_e(INCOMPLETE_REASON) if filled else "")
        + "</textarea>"
        + _no_brainer_control(checked=filled)
        + _save_draft_control(brief_id)
        + '<div style="margin-top: 13px;">'
        '<span class="mono" style="font-size: 10.5px; color: var(--color-neutral-600);">'
        + (
            "approve and defer are unavailable here — you can still revise or reject"
            if locked
            else "pressing a move IS the verdict — one press records the verdict "
            "and its option together; the dry run below and its confirm are the "
            "only step left, not a second decision"
        )
        + "</span></div>"
        "</form>"
        + _dry_run_block()
        + "</div></section>"
    )
