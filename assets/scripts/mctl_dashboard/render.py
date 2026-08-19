"""Server-rendered HTML for the operator dashboard.

Server-rendered, standard library only, no build step and no client-side
framework. The repository declares no Python dependencies and Slice 6 declined
the installed `mcp` SDK for exactly that reason -- an undeclared dependency
makes CI depend on one developer's machine. The same standard applies here, so
this is `str.join` and a stylesheet.

Every screen, every sort, every filter and every verdict works with JavaScript
disabled: navigation and data state live in the query string (see `state.py`),
sortable headings are links, column toggles are a GET form, disclosure is
`<details>`, and mutations are ordinary form posts through `/preview` and
`/apply`. JavaScript is layered on top for four affordances that cannot be
expressed as a link or a form -- the j/k row cursor, drag-to-reorder on the
priority list, live score-weight sliders, and locally saved verdict drafts --
and each degrades to a working no-JS path. All of it lives in `assets.py`, in
one file, so it can be read at once.

Two rendering rules are not cosmetic:

* **The diagnostic code is never replaced by a friendly message.** Severity
  gets color and a badge; the code gets its own element and always renders.
  An operator has to be able to read `MBRF005` off the screen and grep for it.
* **Under-review codes are visually separated but never hidden.** See
  `review.py` for which codes and why.
"""
from __future__ import annotations

from html import escape
import json
from urllib.parse import quote
from typing import Any, Iterable, Mapping, Sequence

from .review import MALFORMED_CAVEAT, is_under_review, note_for, partition


#: The meta-diagnostic Slice 6 attaches when artifact readings are unusable.
#: It belongs with the trust banner, not in the findings list: it is the
#: statement that the findings below cannot be trusted, not one of them.
TRUST_DIAGNOSTIC_CODES = frozenset({"MCTL_MCP_ARTIFACT_STATE_UNTRUSTED"})

SEVERITY_ORDER = ("FATAL", "ERROR", "WARN", "INFO")

#: The stylesheet now lives in `theme.py`, which is the single source for
#: every colour, font and radius. Re-exported here because `page()` inlines it.
from mctl_dashboard.theme import STYLESHEET  # noqa: E402  (kept near its use)


#: (href, label, counts-key). The order is the pipeline's own order -- produced
#: briefs land in the pile, gates promote them to the stack, verdicts close
#: them. Listing these alphabetically would hide the one thing the sidebar is
#: for, which is saying where in the pipeline a brief currently is.
NAV = (
    ("/queue", "Stack — ready for you", "stack"),
    ("/pile", "Pile — awaiting gates", "pile"),
    ("/queue?scope=errors", "Error briefs", "errors"),
    ("/adjudicated", "Adjudicated — closed", "adjudicated"),
    ("/queue?scope=nobrainer", "No-brainers — DRY RUN", "nobrainer"),
)

#: The older tab bar, kept so the pre-redesign routes still navigate while the
#: remaining slices land. Removed when every screen has moved.
LEGACY_NAV = (
    ("/", "Overview"),
    ("/briefs", "Briefs"),
    ("/diagnostics", "Diagnostics"),
    ("/work", "Work"),
    ("/validate", "Validate"),
)


def esc(value: object) -> str:
    """Escape for both text and attribute positions. Every value goes through it."""
    return escape("" if value is None else str(value), quote=True)


#: Short alias used throughout this module; `esc` is the name other modules use.
_e = esc


CURRENT_TAB = ' aria-current="page"'


def _chip(href: str, label: str, count: object, *, accent: bool = False) -> str:
    """One header count, linked to the screen it counts.

    `count is None` means no source read this number, and the chip renders
    without one. Showing a zero instead would assert emptiness that nothing
    measured -- the pile and the no-brainer lane are not readable through the
    typed surface yet (issue #66).
    """
    colour = "var(--color-accent-800)" if accent else "var(--color-neutral-700)"
    value = (
        f' <b class="mono" style="font-weight: 600; color: var(--color-text);">{_e(count)}</b>'
        if count is not None
        else ' <span class="mono" style="color: var(--color-neutral-500);" '
        'title="not readable through the typed surface yet">&mdash;</span>'
    )
    return (
        f'<a href="{_e(href)}" style="font-size: 12px; color: {colour}; '
        'border-bottom: 1px dotted var(--color-accent-600);">'
        f"{_e(label)}{value}</a>"
    )


def masthead(counts: Mapping[str, Any], context: Mapping[str, Any]) -> str:
    """Brand, resolved runtime context, and the clickable counts.

    The context line shows the *resolved* city, rig and store rather than what
    was asked for: a source-checkout invocation hard-errors upstream instead of
    resolving a plausible-but-wrong rig, and this line is where an operator
    notices which city they are actually reading.

    Each count is a link to the screen it counts, and both read the same
    mapping, so a chip cannot come to disagree with its destination.
    """
    city = context.get("city_root") or context.get("city_active") or "—"
    rig = context.get("rig_id") or "all rigs"
    store = context.get("rig_db") or ".beads"
    chips = "".join(
        (
            _chip("/pile", "pile", counts.get("pile")),
            _chip("/queue", "stack", counts.get("stack")),
            _chip("/deferred", "deferred", counts.get("deferred")),
            _chip("/queue?scope=errors", "error briefs", counts.get("errors"), accent=True),
        )
    ) + (
        '<a href="#mc-keys" style="font-size: 12px; color: var(--color-neutral-700); '
        'border-bottom: 1px dotted var(--color-accent-600);">keys</a>'
    )
    return (
        '<header data-region="masthead" style="display: flex; align-items: baseline; '
        "gap: 18px; padding: 12px 20px 10px; "
        "border-bottom: 2px solid var(--color-neutral-900); "
        'background: var(--color-neutral-100); flex-wrap: wrap;">'
        '<div style="font-family: var(--font-heading); font-size: 25px; font-weight: 600; '
        'letter-spacing: 0.01em;">MathCity '
        '<span style="color: var(--color-accent-700);">/</span> Briefs</div>'
        '<div class="mono" style="font-size: 11.5px; color: var(--color-neutral-700);">'
        f'<span style="color: var(--color-neutral-600);">city</span> {_e(city)} '
        '<span style="color: var(--color-neutral-400);">&middot;</span> '
        f'<span style="color: var(--color-neutral-600);">rig</span> {_e(rig)} '
        '<span style="color: var(--color-neutral-400);">&middot;</span> '
        f'<span style="color: var(--color-neutral-600);">store</span> {_e(store)}'
        "</div>"
        '<div style="margin-left: auto; display: flex; align-items: center; gap: 14px;">'
        f"{chips}</div>"
        "</header>"
    )


def sidebar(current: str, counts: Mapping[str, Any]) -> str:
    """Where the pipeline says each brief is, and the operator's own ordering."""
    rows = "".join(
        f'<a class="mc-navlink" href="{_e(href)}"'
        f"{CURRENT_TAB if href == current else ''}>"
        f"<span>{_e(label)}</span>"
        f'<span class="mono" style="font-size: 10.5px; color: var(--color-neutral-600);">'
        f"{_e(counts.get(key)) if counts.get(key) is not None else '&mdash;'}</span></a>"
        for href, label, key in NAV
    )
    return (
        '<nav class="mc-sidebar" data-region="sidebar">'
        '<span class="mc-section-head">Pipeline</span>'
        '<p style="padding: 7px 12px 4px; font-size: 11px; color: var(--color-neutral-600); '
        'font-style: italic; line-height: 1.35; margin: 0;">'
        "Where the pipeline says each brief is. Produced briefs land in the pile; "
        "gates promote them to the stack.</p>"
        f"{rows}"
        f'<a class="mc-section-head" href="/priority" style="margin-top: 14px;">'
        "Priority list</a>"
        '<p style="padding: 7px 12px 4px; font-size: 11px; color: var(--color-neutral-600); '
        'font-style: italic; line-height: 1.35; margin: 0;">'
        "Your ordering over the same stack — nothing here changes pipeline state.</p>"
        "</nav>"
    )


def footer(trace_id: str = "") -> str:
    trace = (
        f'<span style="margin-left: auto;">trace {_e(trace_id)}</span>' if trace_id else ""
    )
    return (
        '<footer data-region="footer" style="border-top: 1px solid var(--color-divider); '
        "background: var(--color-neutral-200); padding: 7px 20px; display: flex; "
        "gap: 16px; flex-wrap: wrap; font-family: var(--font-mono); font-size: 10.5px; "
        'color: var(--color-neutral-600);">'
        "<span>mctl briefs — read paths never mutate; verdicts fail closed on ERROR</span>"
        '<span><span class="mc-dry-run">DRY RUN</span> = preview or classifier output '
        "only, no bead writes</span>"
        f"{trace}"
        "</footer>"
    )


def page(
    title: str,
    current: str,
    sections: Sequence[str],
    *,
    context_bar: str = "",
    counts: Mapping[str, Any] | None = None,
    context: Mapping[str, Any] | None = None,
    trace_id: str = "",
) -> str:
    """The document shell.

    `counts` and `context` are optional so the pre-redesign routes keep
    rendering while the remaining slices land; both default to empty, which
    renders a masthead with zeroed chips rather than failing.
    """
    from .assets import SCRIPT

    counts = counts or {}
    context = context or {}
    return "\n".join(
        [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{_e(title)} - mctl dashboard</title>",
            f"<style>{STYLESHEET}</style>",
            "</head>",
            "<body>",
            masthead(counts, context),
            '<div class="mc-shell">',
            sidebar(current, counts),
            '<main class="mc-main">',
            context_bar,
            *sections,
            "</main>",
            "</div>",
            footer(trace_id),
            f"<script>{SCRIPT}</script>",
            "</body>",
            "</html>",
        ]
    )


# --- context ----------------------------------------------------------------


def context_panel(context: Mapping[str, Any], *, compact: bool = False) -> str:
    """Context is the first visible state on every page (plan Slice 8 step 3).

    Runtime and checkout are labelled, not merely listed: mctl fails closed
    when a mutation is attempted from a source checkout with no explicit city
    and rig, and an operator who cannot see which one they are looking at
    cannot tell a real queue from an empty one.
    """
    active = context.get("city_active")
    liveness = {True: "live", False: "not reachable", None: "unprobed"}.get(active, "unknown")
    rows = [
        ("City runtime", f'{_e(context.get("city_root"))} <span class="badge">{_e(liveness)}</span>'),
        ("Rig", f'{_e(context.get("rig_id"))} <span class="mono">{_e(context.get("rig_root"))}</span>'),
        ("Canonical store", f'<span class="mono">{_e(context.get("rig_db"))}</span> (bead store)'),
        ("Source checkout", f'<span class="mono">{_e(context.get("source_checkout"))}</span>'),
    ]
    if not compact:
        rows += [
            ("Discovery", f'<span class="mono">{_e(context.get("discovery_path"))}</span>'),
            ("Endpoint", f'<span class="mono">{_e(context.get("city_endpoint") or "-")}</span>'),
        ]
    facts = "".join(f"<dt>{_e(label)}</dt><dd>{value}</dd>" for label, value in rows)
    return (
        '<section class="panel" data-region="context">'
        "<h2>Context</h2>"
        '<p class="lede">Resolved through the <span class="mono">context_resolve</span> MCP tool. '
        "The bead store is canonical; brief files are redundant cache.</p>"
        f'<dl class="facts">{facts}</dl>'
        "</section>"
    )


# --- diagnostics -------------------------------------------------------------


def _diagnostic_item(diagnostic: Mapping[str, Any]) -> str:
    severity = str(diagnostic.get("severity") or "INFO")
    code = str(diagnostic.get("code") or "UNKNOWN")
    note = note_for(code)
    meta_bits = []
    for label, key in (
        ("policy", "policy_ref"),
        ("bead", "bead_id"),
        ("read from", "data_location"),
        ("trace", "trace_id"),
    ):
        value = diagnostic.get(key)
        if value:
            meta_bits.append(f"{_e(label)}: <span class=\"mono\">{_e(value)}</span>")
    # `MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS` names the code that actually
    # blocked it only in `facts`. Leaving it there would tell an operator
    # "blocked by ERROR diagnostics" without saying which -- the exact
    # friendly-message-instead-of-a-code failure this dashboard must not make.
    # Rendered as plain mono, not as a `diagnostic-code` element, so it stays
    # readable without being counted as a second finding.
    blocking = (diagnostic.get("facts") or {}).get("blocking_code")
    if blocking:
        meta_bits.append(f'blocked by: <span class="mono">{_e(blocking)}</span>')
    hint = diagnostic.get("hint")
    if hint:
        meta_bits.append(f"hint: {_e(hint)}")
    review_html = ""
    if note is not None:
        review_html = (
            '<p class="review-note"><strong>' + _e(note.headline) + "</strong> "
            + _e(note.detail)
            + ' <br>Reference: <span class="mono">'
            + _e(note.reference)
            + "</span>. Not counted as actionable; decide it as a human, do not batch-fix it.</p>"
        )
    return (
        f'<li class="diagnostic severity-row-{_e(severity)}" data-severity="{_e(severity)}" '
        f'data-code="{_e(code)}" data-under-review="{"true" if note else "false"}">'
        '<span class="head">'
        f'<span class="severity severity-{_e(severity)}">{_e(severity)}</span>'
        f'<code class="diagnostic-code">{_e(code)}</code>'
        "</span>"
        f'<p class="diagnostic-message">{_e(diagnostic.get("message"))}</p>'
        + (f'<p class="diagnostic-meta">{" &middot; ".join(meta_bits)}</p>' if meta_bits else "")
        + review_html
        + "</li>"
    )


def diagnostic_list(diagnostics: Iterable[Mapping[str, Any]], *, empty: str) -> str:
    items = [_diagnostic_item(diagnostic) for diagnostic in _by_severity(diagnostics)]
    if not items:
        return f'<p class="lede">{_e(empty)}</p>'
    return '<ul class="diagnostics">' + "".join(items) + "</ul>"


def _by_severity(diagnostics: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    ordered = list(diagnostics)
    return sorted(
        ordered,
        key=lambda diagnostic: (
            SEVERITY_ORDER.index(str(diagnostic.get("severity")))
            if str(diagnostic.get("severity")) in SEVERITY_ORDER
            else len(SEVERITY_ORDER),
            str(diagnostic.get("code")),
        ),
    )


def split_diagnostics(
    diagnostics: Sequence[Mapping[str, Any]], untrusted: Sequence[Mapping[str, Any]]
) -> tuple[list, list, list]:
    """Return (trust meta-diagnostics, actionable, under review).

    The server has already withheld `MBRF021` into `untrusted`; this adds the
    codes under review for reasons the server does not model, so one rule
    governs every page.
    """
    trust = [item for item in diagnostics if str(item.get("code")) in TRUST_DIAGNOSTIC_CODES]
    remaining = [item for item in diagnostics if str(item.get("code")) not in TRUST_DIAGNOSTIC_CODES]
    actionable, reviewed = partition(list(remaining))
    return trust, actionable, reviewed + list(untrusted)


def diagnostics_sections(
    diagnostics: Sequence[Mapping[str, Any]],
    untrusted: Sequence[Mapping[str, Any]],
    trust: Mapping[str, Any] | None,
    *,
    heading: str = "Diagnostics",
) -> str:
    trust_diagnostics, actionable, reviewed = split_diagnostics(diagnostics, untrusted)
    return "".join(
        [
            artifact_trust_panel(trust, trust_diagnostics),
            (
                '<section class="panel" data-region="actionable-diagnostics" '
                f'data-actionable-count="{len(actionable)}">'
                f"<h2>{_e(heading)} - actionable ({len(actionable)})</h2>"
                + diagnostic_list(actionable, empty="No actionable diagnostics.")
                + "</section>"
            ),
            (
                '<section class="panel untrusted" data-region="untrusted-diagnostics" '
                f'data-under-review-count="{len(reviewed)}">'
                f"<h2>Under review - not actionable ({len(reviewed)})</h2>"
                '<p class="lede">These codes are known instrumentation problems. They are shown '
                "in full, with their codes, and deliberately excluded from the actionable count: "
                "acting on them would repair beads that are fine. Each names the document that "
                "owns the open question.</p>"
                + diagnostic_list(reviewed, empty="Nothing withheld for this view.")
                + "</section>"
            ),
        ]
    )


def artifact_trust_panel(
    trust: Mapping[str, Any] | None,
    trust_diagnostics: Sequence[Mapping[str, Any]] = (),
    *,
    rig: str | None = None,
) -> str:
    """State artifact trust wherever artifact state is shown -- both ways.

    Rendering only the untrusted case would leave an operator unable to tell
    "trusted" from "this page forgot to say".

    `rig` names which rig the verdict is about. In a city-wide view that is
    not decoration: the brief root and pile resolve per rig, so trust really
    does differ per rig, and one banner covering sixteen of them would be a
    claim about fifteen rigs nobody checked.
    """
    if trust is None:
        return ""
    trusted = bool(trust.get("trusted"))
    withheld = ", ".join(str(code) for code in trust.get("withheld_codes") or ()) or "none"
    extra = (
        "".join(_diagnostic_item(diagnostic) for diagnostic in trust_diagnostics)
        if trust_diagnostics
        else ""
    )
    reference = trust.get("reference") or ""
    question = trust.get("open_question") or ""
    headline = (
        "Redundant-artifact state is trustworthy for this rig."
        if trusted
        else "Redundant-artifact state cannot be trusted, and is not being presented as fact."
    )
    body = [
        f'<section class="panel" data-region="artifact-trust" data-artifact-trust="{"true" if trusted else "false"}"'
        + (f' data-rig="{_e(rig)}"' if rig else "")
        + ">",
        f'<h2>Artifact state{f" - rig {_e(rig)}" if rig else ""}</h2>',
        f'<div class="trust-banner{" trust-ok" if trusted else ""}">',
        f"<p><strong>{_e(headline)}</strong></p>",
        f'<p class="diagnostic-meta">{_e(trust.get("reason"))}</p>',
    ]
    if not trusted:
        body.append(
            '<p class="diagnostic-meta">Open question: '
            f'<span class="mono">{_e(question)}</span> - see <span class="mono">{_e(reference)}</span>. '
            "Artifacts the core read as <span class=\"mono\">missing</span> are shown as "
            "<span class=\"mono\">unverified</span>; the raw reading is kept beside them. "
            f"Withheld codes: <span class=\"mono\">{_e(withheld)}</span>.</p>"
        )
    body += [
        f'<p class="diagnostic-meta">Resolved brief root: <span class="mono">{_e(trust.get("resolved_brief_root"))}</span></p>',
        f'<p class="diagnostic-meta">Resolved pile: <span class="mono">{_e(trust.get("resolved_pile"))}</span></p>',
        "</div>",
        ('<ul class="diagnostics">' + extra + "</ul>") if extra else "",
        "</section>",
    ]
    return "".join(body)


# --- briefs ------------------------------------------------------------------


def _state_badge(state: str) -> str:
    return f'<span class="badge state-{_e(state)}">{_e(state)}</span>'


def brief_href(brief_id: object, rig: str | None = None) -> str:
    """The one place a brief link is built.

    In a city-wide list the rig is not decoration: a brief id with no rig is
    an address with no store behind it, and the detail view would have to
    guess which of sixteen bead stores to open.
    """
    href = f"/briefs/{_e(brief_id)}"
    return f"{href}?rig={quote(str(rig), safe='')}" if rig else href


def brief_rows(briefs: Sequence[Mapping[str, Any]], *, show_rig: bool = False) -> str:
    rows = []
    for brief in briefs:
        artifacts = ", ".join(
            sorted({str(item.get("state")) for item in brief.get("redundant_artifacts") or ()})
        )
        rig = str(brief.get("rig_id") or "") or None
        rig_cell = f'<td><span class="mono">{_e(rig or "-")}</span></td>' if show_rig else ""
        rows.append(
            "<tr>"
            + rig_cell
            + f'<td><a href="{brief_href(brief.get("brief_id"), rig)}">'
            f'<span class="mono">{_e(brief.get("bead_id"))}</span></a></td>'
            f'<td>{_e(brief.get("title"))}</td>'
            f'<td>{_state_badge(str(brief.get("decision_state")))}</td>'
            f'<td><span class="mono">{_e(brief.get("status"))}</span></td>'
            f'<td><span class="mono">{_e(", ".join(brief.get("labels") or ()) or "-")}</span></td>'
            f'<td><span class="mono">{_e(artifacts or "-")}</span></td>'
            f'<td><span class="mono">{_e(brief.get("updated_at") or "-")}</span></td>'
            "</tr>"
        )
    if not rows:
        return '<p class="lede">No briefs match this filter.</p>'
    return (
        '<div class="scroll-x"><table><thead><tr>'
        + ("<th>Rig</th>" if show_rig else "")
        + "<th>Bead</th><th>Title</th><th>Decision state</th><th>Bead status</th>"
        "<th>Labels</th><th>Artifacts</th><th>Updated</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def state_counts(briefs: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for brief in briefs:
        state = str(brief.get("decision_state"))
        counts[state] = counts.get(state, 0) + 1
    return counts


def queue_panel(briefs: Sequence[Mapping[str, Any]]) -> str:
    counts = state_counts(briefs)
    cells = "".join(
        f"<tr><td>{_state_badge(state)}</td><td class=\"mono\">{counts[state]}</td>"
        f"<td>{_e(_state_gloss(state))}</td></tr>"
        for state in sorted(counts)
    )
    caveat = ""
    if counts.get("malformed"):
        caveat = f'<p class="review-note"><strong>Read the malformed count carefully.</strong> {_e(MALFORMED_CAVEAT)}</p>'
    return (
        '<section class="panel" data-region="queue">'
        f"<h2>Decision queue ({len(briefs)} briefs)</h2>"
        '<p class="lede">Canonical source: <span class="mono">bead_store</span>. '
        'Read through <span class="mono">briefs_list</span>.</p>'
        '<div class="scroll-x"><table><thead><tr><th>State</th><th>Count</th><th>Meaning</th></tr></thead>'
        f"<tbody>{cells}</tbody></table></div>"
        f"{caveat}"
        '<p class="lede"><a href="/briefs?status=open">Open the pending queue</a></p>'
        "</section>"
    )


def _state_gloss(state: str) -> str:
    return {
        "pending": "Open, no verdict recorded. This is the queue that needs a human.",
        "adjudicated": "Closed with a recorded verdict field.",
        "deferred": "Deferred with a defer window on the bead.",
        "malformed": "Closed with no verdict field. See the caveat below.",
    }.get(state, "Reported by the canonical bead store.")


def brief_detail_panel(brief: Mapping[str, Any]) -> str:
    policy = "".join(
        f'<li><span class="mono">{_e(reference.get("reference"))}</span> - {_e(reference.get("description"))}</li>'
        for reference in brief.get("policy_references") or ()
    )
    artifacts = "".join(
        "<tr>"
        f'<td><span class="mono">{_e(item.get("kind"))}</span></td>'
        f'<td><span class="badge">{_e(item.get("state"))}</span></td>'
        f'<td><span class="mono">{_e(item.get("state_reported_by_core"))}</span></td>'
        f'<td><span class="mono">{_e(item.get("path"))}</span></td>'
        "</tr>"
        for item in brief.get("redundant_artifacts") or ()
    )
    facts = "".join(
        f"<dt>{_e(label)}</dt><dd>{value}</dd>"
        for label, value in (
            ("Bead id", f'<span class="mono">{_e(brief.get("bead_id"))}</span>'),
            ("Brief id", f'<span class="mono">{_e(brief.get("brief_id"))}</span>'),
            ("Canonical source", f'<span class="mono">{_e(brief.get("canonical_source"))}</span>'),
            ("Decision state", _state_badge(str(brief.get("decision_state")))),
            ("Bead status", f'<span class="mono">{_e(brief.get("status"))}</span>'),
            ("Labels", f'<span class="mono">{_e(", ".join(brief.get("labels") or ()) or "-")}</span>'),
            ("Created", f'<span class="mono">{_e(brief.get("created_at") or "-")}</span>'),
            ("Updated", f'<span class="mono">{_e(brief.get("updated_at") or "-")}</span>'),
        )
    )
    return (
        '<section class="panel" data-region="brief">'
        f'<h2>{_e(brief.get("title"))}</h2>'
        f'<dl class="facts">{facts}</dl>'
        + (f"<h2>Policy references</h2><ul>{policy}</ul>" if policy else "")
        + (
            '<h2>Redundant cache artifacts</h2><div class="scroll-x"><table><thead><tr>'
            "<th>Kind</th><th>State</th><th>Raw core reading</th><th>Path</th>"
            f"</tr></thead><tbody>{artifacts}</tbody></table></div>"
            if artifacts
            else ""
        )
        + "</section>"
    )


def options_panel(options: Sequence[Mapping[str, Any]]) -> str:
    rows = []
    for option in options:
        reason = option.get("disabled_reason") or {}
        if option.get("enabled"):
            status = '<span class="badge">available</span>'
        else:
            status = (
                '<span class="badge">blocked</span> '
                f'<code class="diagnostic-code">{_e(reason.get("code"))}</code>'
                f'<div class="disabled-reason">{_e(reason.get("message"))}</div>'
            )
        rows.append(
            "<tr>"
            f'<td><strong>{_e(option.get("label"))}</strong></td>'
            f'<td>{_e(option.get("description"))}</td>'
            f"<td>{status}</td>"
            "</tr>"
        )
    return (
        '<section class="panel" data-region="options">'
        "<h2>Available actions</h2>"
        '<p class="lede">Reported by <span class="mono">briefs_options</span>: what this bead\'s '
        "current state permits, and the diagnostic code behind every refusal.</p>"
        '<div class="scroll-x"><table><thead><tr><th>Action</th><th>What it does</th><th>State</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        "</section>"
    )


# --- mutations ---------------------------------------------------------------


def operation_forms(
    brief_id: str, options: Sequence[Mapping[str, Any]], *, rig: str | None = None
) -> str:
    """The mutation forms, each pinned to the rig whose store owns this brief.

    The rig travels as a hidden field rather than being inferred at submit
    time. A city-wide dashboard that let the target store be re-derived from
    ambient state could adjudicate the wrong bead after the operator changed
    the rig filter in another tab; carrying it makes the target explicit, and
    the apply path refuses when the two disagree.
    """
    enabled = {str(option.get("id")): bool(option.get("enabled")) for option in options}
    rig_field = f'<input type="hidden" name="rig" value="{_e(rig)}">' if rig else ""

    def _blocked(name: str) -> str:
        if enabled.get(name, False):
            return ""
        return (
            '<p class="disabled-reason">This bead\'s current state does not permit it; '
            "a preview will show the blocking diagnostic code.</p>"
        )

    return (
        '<section class="panel" data-region="mutations">'
        "<h2>Record a decision</h2>"
        '<p class="lede">Every mutation is preview-first. Submitting here runs a '
        "<strong>dry run</strong> through the MCP tool and writes nothing; the confirm control "
        "appears only on the preview, and only while that preview is still true.</p>"
        '<form class="operation" method="post" action="/preview">'
        f'<input type="hidden" name="brief_id" value="{_e(brief_id)}">{rig_field}'
        '<input type="hidden" name="operation" value="adjudicate">'
        "<label>Verdict"
        '<select name="verdict">'
        '<option value="approve">approve</option>'
        '<option value="reject">reject</option>'
        '<option value="revise">revise</option>'
        "</select></label>"
        '<label>Option (required when the brief offers more than one)'
        '<input type="text" name="option" placeholder="A"></label>'
        '<label>Reason (recorded on the bead)<textarea name="reason" rows="3"></textarea></label>'
        "<div><button type=\"submit\">Preview adjudication</button></div>"
        f"{_blocked('adjudicate')}"
        "</form>"
        '<form class="operation" method="post" action="/preview">'
        f'<input type="hidden" name="brief_id" value="{_e(brief_id)}">{rig_field}'
        '<input type="hidden" name="operation" value="defer">'
        '<label>Defer for (days)<input type="text" name="days" value="7"></label>'
        '<label>Reason<textarea name="reason" rows="2"></textarea></label>'
        '<div><button type="submit" class="secondary">Preview deferral</button></div>'
        f"{_blocked('defer')}"
        "</form>"
        '<form class="operation" method="post" action="/preview">'
        f'<input type="hidden" name="brief_id" value="{_e(brief_id)}">{rig_field}'
        '<input type="hidden" name="operation" value="dispatch">'
        '<div><button type="submit" class="secondary">Preview work dispatch</button></div>'
        f"{_blocked('dispatch-work')}"
        "</form>"
        "</section>"
    )


def effect_plan_panel(plan: Mapping[str, Any], *, title: str) -> str:
    rows = []
    for update in plan.get("bead_updates") or ():
        rows.append(
            ("canonical bead update", f'{update.get("id")} -> status={update.get("status")} '
             f'(only if it is still {update.get("if_status")!r})')
        )
    for create in plan.get("bead_creates") or ():
        rows.append(("canonical bead create", str(create.get("title"))))
    for update in plan.get("cache_updates") or ():
        rows.append((f'redundant cache: {update.get("kind")}', str(update.get("path"))))
    for create in plan.get("file_creates") or ():
        rows.append((f'redundant file: {create.get("kind")}', str(create.get("path"))))
    for write in plan.get("event_writes") or ():
        rows.append(("event log", str(write.get("path"))))
    for write in plan.get("trace_writes") or ():
        rows.append(("trace log", str(write.get("path"))))
    body = "".join(
        f'<tr><td>{_e(label)}</td><td><span class="mono">{_e(value)}</span></td></tr>'
        for label, value in rows
    )
    encoded = _e(json.dumps(plan, sort_keys=True))
    return (
        f'<section class="panel" data-region="effect-plan" data-plan-json="{encoded}" '
        f'data-operation="{_e(plan.get("operation"))}" data-trace-id="{_e(plan.get("trace_id"))}">'
        f"<h2>{_e(title)}</h2>"
        f'<p class="lede">Operation <span class="mono">{_e(plan.get("operation"))}</span> on '
        f'<span class="mono">{_e(plan.get("target_brief_id"))}</span>. Canonical bead state is '
        "written before any redundant artifact.</p>"
        '<div class="scroll-x"><table><thead><tr><th>Effect</th><th>Target</th></tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
        f"<pre class=\"plan\">{_e(json.dumps(plan, indent=2, sort_keys=True))}</pre>"
        "</section>"
    )


def confirm_panel(
    token: str, operation: str, brief_id: str | None, *, rig: str | None = None
) -> str:
    return (
        '<section class="panel" data-region="confirm">'
        '<div class="confirm">'
        "<h2>Confirm</h2>"
        "<p>Applying re-resolves the context, re-reads the brief, and re-plans before writing. "
        "If any of the three has moved since this preview was taken, nothing is applied and a "
        "fresh preview replaces this one.</p>"
        '<form method="post" action="/apply">'
        f'<input type="hidden" name="token" value="{_e(token)}">'
        + (f'<input type="hidden" name="rig" value="{_e(rig)}">' if rig else "")
        + f'<button type="submit">Apply this {_e(operation)}</button>'
        "</form>"
        + (
            f'<p class="lede"><a href="{brief_href(brief_id, rig)}">Back to the brief without applying</a></p>'
            if brief_id
            else ""
        )
        + "</div></section>"
    )


def applied_panel(payload: Mapping[str, Any], operation: str) -> str:
    effects = "".join(
        f'<li><span class="mono">{_e(effect.get("kind"))}</span> '
        f'<span class="mono">{_e(effect.get("path") or effect.get("id") or "")}</span></li>'
        for effect in payload.get("actual_effects") or ()
    )
    return (
        '<section class="panel" data-region="applied" '
        f'data-trace-id="{_e(payload.get("trace_id"))}">'
        f"<h2>Applied - {_e(operation)}</h2>"
        f'<p>Trace id <span class="mono">{_e(payload.get("trace_id"))}</span>. '
        "The preview was still current at confirm time, so exactly the previewed plan was applied.</p>"
        + (f"<h2>Effects that landed</h2><ul>{effects}</ul>" if effects else "")
        + "</section>"
    )


def notice_panel(
    title: str, message: str, diagnostics: Sequence[Mapping[str, Any]] = (), *, region: str = "notice"
) -> str:
    return (
        f'<section class="panel" data-region="{_e(region)}">'
        f"<h2>{_e(title)}</h2>"
        f'<p class="lede">{_e(message)}</p>'
        + diagnostic_list(diagnostics, empty="No further detail was reported.")
        + "</section>"
    )


# --- city-wide views ---------------------------------------------------------


def city_context_panel(payload: Mapping[str, Any], *, degraded: Sequence[str] = ()) -> str:
    """Context for a city-wide page: the city, and every rig it registers.

    The rig-scoped page names one rig; this names all of them, for the same
    reason -- an operator who cannot see which stores a total covers cannot
    tell a complete queue from a partial one.
    """
    rigs = list(payload.get("rigs") or ())
    unreadable = set(degraded)
    listed = ", ".join(
        f'{_e(entry.get("rig_id"))}{" (degraded)" if entry.get("rig_id") in unreadable else ""}'
        for entry in rigs
    )
    rows = [
        ("City runtime", f'{_e(payload.get("city_root"))} <span class="badge">city-wide</span>'),
        ("Scope", f"every registered rig ({len(rigs)})"),
        ("Registered rigs", f'<span class="mono">{listed or "-"}</span>'),
        ("Discovery", f'<span class="mono">{_e(payload.get("discovery_path"))}</span>'),
    ]
    facts = "".join(f"<dt>{_e(label)}</dt><dd>{value}</dd>" for label, value in rows)
    return (
        '<section class="panel" data-region="context" data-scope="city">'
        "<h2>Context</h2>"
        '<p class="lede">Resolved through the <span class="mono">context_rigs</span> MCP tool. '
        "Storage is per rig and the bead store is canonical; this page reports across rigs "
        'through <span class="mono">all_rigs</span>, and every brief stays addressed by the rig '
        "that owns it.</p>"
        f'<dl class="facts">{facts}</dl>'
        "</section>"
    )


def degraded_rigs_panel(degraded: Sequence[Any], total: int) -> str:
    """Name every rig that could not be read, and say the totals are partial.

    Silence here would be the worst available behavior: a city-wide page that
    drops a rig without saying so looks complete, and an operator would read
    a missing queue as an empty one.
    """
    if not degraded:
        return (
            '<section class="panel" data-region="degraded-rigs" data-degraded-count="0">'
            "<h2>Rig health</h2>"
            f'<p class="lede">All {total} registered rigs answered, so the totals on this page '
            "cover the whole city.</p></section>"
        )
    rows = "".join(
        "<tr>"
        f'<td><span class="mono">{_e(rig.rig_id)}</span></td>'
        f"<td>{_e(rig.reason)}</td>"
        f'<td><a href="/briefs?rig={quote(rig.rig_id, safe="")}">read this rig alone</a></td>'
        "</tr>"
        for rig in degraded
    )
    diagnostics = [item for rig in degraded for item in rig.diagnostics]
    return (
        '<section class="panel untrusted" data-region="degraded-rigs" '
        f'data-degraded-count="{len(degraded)}">'
        f"<h2>Degraded rigs ({len(degraded)} of {total})</h2>"
        '<p class="lede"><strong>The totals on this page are incomplete.</strong> These rigs '
        "could not be read, so their briefs are counted nowhere. Every other rig still "
        "reports normally.</p>"
        '<div class="scroll-x"><table><thead><tr><th>Rig</th><th>Why</th><th></th></tr></thead>'
        f"<tbody>{rows}</tbody></table></div>"
        + diagnostic_list(diagnostics, empty="No further detail was reported.")
        + "</section>"
    )


def city_queue_panel(view: Any) -> str:
    """City-wide totals with the per-rig breakdown beside them.

    The aggregate answers "how much is there"; the breakdown answers "where
    is it". Neither is sufficient alone, and the city row is only ever the sum
    of the rig rows printed above it.
    """
    states = sorted(view.state_counts())
    totals = view.state_counts()
    header = "".join(f"<th>{_state_badge(state)}</th>" for state in states)
    rows = []
    for rig in view.rigs:
        if not rig.ok:
            rows.append(
                f'<tr data-rig="{_e(rig.rig_id)}" data-degraded="true">'
                f'<td><span class="mono">{_e(rig.rig_id)}</span></td>'
                f'<td colspan="{len(states) + 1}">{_e(rig.rig_id)}: could not be read '
                f"({_e(rig.reason)})</td></tr>"
            )
            continue
        counts = view.state_counts(rig.rig_id)
        cells = "".join(f'<td class="mono">{counts.get(state, 0)}</td>' for state in states)
        rows.append(
            f'<tr data-rig="{_e(rig.rig_id)}" data-degraded="false">'
            f'<td><a href="/briefs?rig={quote(rig.rig_id, safe="")}">'
            f'<span class="mono">{_e(rig.rig_id)}</span></a></td>'
            + cells
            + f'<td class="mono">{sum(counts.values())}</td></tr>'
        )
    total_cells = "".join(
        f'<td class="mono" data-total-state="{_e(state)}">{totals.get(state, 0)}</td>'
        for state in states
    )
    caveat = ""
    if totals.get("malformed"):
        caveat = (
            '<p class="review-note"><strong>Read the malformed count carefully.</strong> '
            f"{_e(MALFORMED_CAVEAT)}</p>"
        )
    return (
        '<section class="panel" data-region="queue" data-scope="city" '
        f'data-brief-total="{len(view.rows)}" data-rig-count="{len(view.rigs)}">'
        f"<h2>Decision queue - whole city ({len(view.rows)} briefs across "
        f"{len(view.healthy)} readable rigs)</h2>"
        '<p class="lede">Canonical source: each rig\'s own <span class="mono">bead_store</span>. '
        'Read through <span class="mono">briefs_list</span> with '
        '<span class="mono">all_rigs</span>; storage stays per rig, only the reporting is '
        "city-wide. The city total is the sum of the rig rows above it.</p>"
        '<div class="scroll-x"><table><thead><tr><th>Rig</th>'
        f"{header}<th>Total</th></tr></thead><tbody>"
        + "".join(rows)
        + f'<tr data-region="city-total"><td><strong>City</strong></td>{total_cells}'
        f'<td class="mono" data-total-state="all">{len(view.rows)}</td></tr>'
        "</tbody></table></div>"
        + "".join(
            f'<p class="lede"><span class="badge state-{_e(state)}">{_e(state)}</span> '
            f"{_e(_state_gloss(state))}</p>"
            for state in states
        )
        + caveat
        + '<p class="lede"><a href="/briefs?status=open">Open the pending queue, city-wide</a></p>'
        "</section>"
    )


def rig_filter_field(rig_ids: Sequence[str], selected: str | None) -> str:
    options = "".join(
        f'<option value="{_e(rig)}"{" selected" if rig == selected else ""}>{_e(rig)}</option>'
        for rig in rig_ids
    )
    return (
        '<label>Rig<select name="rig" data-region="rig-filter">'
        f'<option value=""{" selected" if not selected else ""}>every rig</option>'
        f"{options}</select></label>"
    )


def rig_trust_panels(view: Any) -> str:
    """One artifact-trust verdict per rig, never one for the city.

    `artifact_trust` is a statement about a resolved brief root and pile, and
    those are per rig. Collapsing the verdicts into one would either understate
    a healthy rig or -- far worse -- state "trusted" over rigs that are not.

    Each rig's trust meta-diagnostic travels into its own banner. They are
    stripped out of the findings list by `split_diagnostics` -- they are the
    statement that the findings cannot be trusted, not findings themselves --
    so if they did not land here they would be dropped entirely.
    """
    by_rig: dict[str, list[Mapping[str, Any]]] = {}
    for item in view.diagnostics:
        if str(item.get("code")) in TRUST_DIAGNOSTIC_CODES:
            rig_id = str((item.get("facts") or {}).get("rig_name") or "")
            by_rig.setdefault(rig_id, []).append(item)
    panels = [
        artifact_trust_panel(rig.artifact_trust, by_rig.get(rig.rig_id, ()), rig=rig.rig_id)
        for rig in view.rigs
        if rig.artifact_trust is not None
    ]
    if not panels:
        return ""
    return (
        '<section class="panel" data-region="rig-artifact-trust" '
        f'data-rig-trust-count="{len(panels)}">'
        "<h2>Artifact state, per rig</h2>"
        '<p class="lede">Trust is a verdict about one rig\'s resolved brief root and pile, so '
        "it is reported per rig rather than collapsed into a single city-wide claim.</p>"
        "</section>" + "".join(panels)
    )


def city_diagnostics_sections(view: Any, *, heading: str) -> str:
    """The aggregate diagnostics split, with the withheld codes still withheld.

    The concatenation is across rigs; the partition is the same one every
    other view applies. An `MBRF021` from any rig lands under review, and the
    actionable count on a city-wide page counts exactly what the rig-scoped
    pages would have counted, summed.
    """
    return diagnostics_sections(
        list(view.diagnostics), list(view.untrusted_diagnostics), None, heading=heading
    )
