"""The city-operations screens: what the city is doing, not what it decided.

The briefs surface answers "what needs a verdict". This one answers Taylor's
question -- *"the dashboard I want has Formulas, Orders, Molecules"* -- which is
about the city's own machinery. Five slices were merged for it and none of them
rendered anywhere (`#153`); this module is where they land.

Two of those five are reachable today. `fleet_sessions` and `city_health` have
MCP tools, which is the only way `mctl_dashboard` can reach data at all. The
rest have core modules and no tool, so `unwired()` renders them as a named gap
rather than as an empty panel -- an empty panel is indistinguishable from a
working surface with nothing in it, which is the whole defect this dashboard
keeps finding elsewhere.

**P6.2 governs every cell here.** A probe that did not answer renders as
*unknown*, never as zero. That is not a hypothetical: `gc` is currently timing
out at 30s, so `fleet_sessions` returns an empty slot list and `city_health`
reports `data_plane: unreachable`. Rendered naively that reads as "0 agents"
and a dead city -- and an operator would go looking for a fleet that never
stopped running.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from mctl_dashboard.render import esc as _e
from mctl_dashboard.render import stoplight

#: How a city-health state word maps onto the shared stoplight scale.
#:
#: `unknown` is deliberately absent -- it must resolve to the neutral `ok`
#: tone, never a colour, because a probe that could not answer is neither a
#: pass nor a failure (P6.2). `_state_tone` returns `ok` for anything not
#: listed here, so an unmapped or unknown state is dressed neutrally by
#: construction rather than by a caller remembering to.
_HEALTH_TONE: dict[str, str] = {
    "healthy": "go",
    "reachable": "go",
    "ok": "go",
    "degraded": "warn",
    "partial": "warn",
    "unhealthy": "error",
    "unreachable": "error",
    "down": "error",
}


def _state_tone(state: str) -> str:
    """The stoplight tone for a health/rig state, defaulting to neutral.

    Neutral is the honest default: a state this map does not recognise -- and
    `unknown` in particular -- is painted `ok`, so it reads as "not classified"
    rather than borrowing the green of a pass or the red of a failure.
    """
    return _HEALTH_TONE.get(str(state).lower(), "ok")


#: A diagnostic whose presence means the answer below it is not a measurement.
PROBE_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "MCTL_FLEET_STATUS_PROBE_FAILED",
        "MCTL_CITY_RIG_PARTIAL",
        "MCTL_HEALTH_PROBE_FAILED",
    }
)


def _codes(payload: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(d.get("code"))
        for d in (payload.get("diagnostics") or [])
        if isinstance(d, Mapping) and d.get("code")
    )


def probe_failed(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """The probe-failure codes present, if any.

    Their presence is what separates "we asked and the answer was none" from
    "we could not ask" -- the two states an empty list cannot tell apart on
    its own.
    """
    return tuple(c for c in _codes(payload) if c in PROBE_FAILURE_CODES)


def _panel(title: str, body: str, *, region: str) -> str:
    return (
        f'<section class="panel" data-region="{region}">'
        f"<h2>{_e(title)}</h2>{body}</section>"
    )


def fleet(payload: Mapping[str, Any]) -> str:
    """Agent slots, or an honest statement that the fleet size is unknown."""
    slots: Sequence[Mapping[str, Any]] = payload.get("slots") or []
    failures = probe_failed(payload)
    if failures:
        return _panel(
            "Agents",
            '<p class="lede"><strong>Fleet size is unknown.</strong> The probe did '
            "not answer, so this is not a count of zero — it is the absence of a "
            "count. The fleet may be entirely healthy behind a probe that timed "
            "out.</p>"
            f'<p class="mono">{_e(" · ".join(failures))}</p>',
            region="city-fleet",
        )
    occupied = sum(1 for s in slots if str(s.get("state")) == "occupied")
    # The prototype's capacity strip: one cell per configured slot, filled when
    # the slot is occupied. Drawn only in this branch -- the probe answered, so
    # the strip is a measurement. An unknown fleet (handled above) gets no strip
    # at all rather than a row of empty cells that would read as "all free".
    cells = "".join(
        '<i class="mc-cap '
        + ("mc-cap-occupied" if str(s.get("state")) == "occupied" else "mc-cap-free")
        + '"></i>'
        for s in slots
    )
    strip = f'<div class="mc-cap-strip" data-region="city-capacity">{cells}</div>' if cells else ""
    return _panel(
        "Agents",
        strip
        + f'<p class="lede"><strong>{len(slots)}</strong> configured slot'
        f'{"" if len(slots) == 1 else "s"}, <strong>{occupied}</strong> occupied. '
        "This is a measurement: the probe answered.</p>",
        region="city-fleet",
    )


def health(payload: Mapping[str, Any]) -> str:
    """Data-plane state, with `unreachable` kept distinct from `unhealthy`."""
    state = str(payload.get("data_plane") or "unknown")
    per_rig: Sequence[Mapping[str, Any]] = payload.get("per_rig") or []
    if state == "unknown":
        # #159's fix reaching the page. This is the state that means "we could
        # not ask" -- and until the core distinguished it, this panel carried
        # prose apologising for `unreachable` meaning the same thing.
        body = (
            '<p class="lede"><strong>The data plane\'s state was not '
            "established.</strong> The probe did not answer, so this is a fact "
            "about the probe and <em>not</em> evidence about the database. "
            "Nothing here should be read as anything being down — it may be "
            "entirely healthy behind a probe that timed out.</p>"
        )
        # THE SEAM. #159 made this panel say `unknown` when the CITY-level
        # probe does not answer. #176 then made every rig probed DIRECTLY, so
        # the rows below are real measurements. Both landed correctly and the
        # page was left asserting "we established nothing" directly above
        # seventeen establishments, with nothing in between.
        #
        # Conditional on purpose: it fires only when something actually WAS
        # established under the claim that nothing was. When every rig is also
        # unreachable there is no tension, and a sentence that always appears
        # is prose the reader learns to skip -- which is the defect #159's
        # commit removed from this same function.
        if any(str(r.get("state") or "") != "unreachable" for r in per_rig):
            body += (
                '<p class="note">Both of these are true at once. <strong>The '
                "city-level probe did not answer; each rig was asked directly "
                "and did.</strong> A rig row below is that rig&rsquo;s own "
                "answer, not an inference from the line above — so an "
                "established rig under an unestablished data plane is a "
                "narrower failure than an outage, not a contradiction.</p>"
            )
    elif state == "unreachable":
        # And this one now means what it says. Before #159 every probe failure
        # landed here, so this panel had to hedge -- "unreachable is not
        # unhealthy" was true then and would be FALSE now. Prose written to
        # compensate for a bug becomes a lie the moment the bug is fixed.
        body = (
            f'<p>{stoplight("unreachable", "error")}</p>'
            '<p class="lede"><strong>The data plane is unreachable.</strong> '
            "This is a measurement, not a missing one: the probe answered and "
            "reported the server down. Distinct from "
            '<em>unknown</em>, which is what a probe that never answered '
            "produces.</p>"
        )
    else:
        # A measured state: paint it with the stoplight its word maps to.
        # `_state_tone` returns the neutral `ok` for anything it does not
        # recognise, so an unfamiliar state is never dressed as a pass.
        body = (
            f'<p>{stoplight(state, _state_tone(state))}</p>'
            f'<p class="lede">Data plane: <strong>{_e(state)}</strong>, '
            f"across {len(per_rig)} rig{'' if len(per_rig) == 1 else 's'}.</p>"
        )
    if per_rig:
        body += (
            '<ul class="reason-list">'
            + "".join(
                f'<li><span class="mono">{_e(str(r.get("rig_id")))}</span> — '  # single-shape-ok: city_health per-rig envelope, not a brief row
                f'{stoplight(str(r.get("state")), _state_tone(str(r.get("state"))))}'
                + (f' <span class="muted">({_e(str(r.get("reason")))})</span>' if r.get("reason") else "")
                + "</li>"
                for r in per_rig[:20]
            )
            + "</ul>"
        )
    return _panel("City health", body, region="city-health")


def gates(payload: Mapping[str, Any]) -> str:
    """Gate definitions, keeping "none defined" apart from "could not look".

    `mctl_core/gates.py` protects that distinction with `gates_readable`, and
    the whole point of carrying it through the tool was to be able to carry it
    to the pixel. A screen that renders "0 gates" for both destroys it at the
    last step, which would make the care taken underneath worthless.
    """
    rows: Sequence[Mapping[str, Any]] = payload.get("gates") or []  # single-shape-ok: gates_status envelope, not a brief row
    readable = payload.get("gates_readable")
    if readable is False:
        return _panel(
            "Gates",
            '<p class="lede"><strong>The gate set is unknown.</strong> The gate '
            "directory could not be read, so this is not a city with no gates — it "
            "is a city whose gates we could not look at.</p>",
            region="city-gates",
        )
    if not rows:
        return _panel(
            "Gates",
            '<p class="lede">This city defines <strong>no gates</strong>. The '
            "directory was read successfully and is empty — a measurement, not a "
            "failure to look.</p>",
            region="city-gates",
        )
    body = (
        f'<p class="lede"><strong>{len(rows)}</strong> gate'
        f'{"" if len(rows) == 1 else "s"} defined. '
        "Pass/fail statistics are deliberately absent rather than zero: no "
        "evaluation store exists yet, so the numbers are unknown and say so.</p>"
        '<ul class="reason-list">'
        + "".join(
            f'<li><span class="mono">{_e(str(r.get("gate_id")))}</span>'  # single-shape-ok: gates_status row, not a brief
            + (f' — {_e(str(r.get("checks")))} check(s)' if r.get("checks") is not None else "")
            + "</li>"
            for r in rows
        )
        + "</ul>"
    )
    return _panel("Gates", body, region="city-gates")


def _tier_label(row: Mapping[str, Any]) -> str:
    """What this operation's row should say, from the payload alone.

    Three genuinely different states, and the old code collapsed the last two:

      floor set        -> the tier
      gate set         -> `gated`, and the gate OWNS it: no tier is consulted
      neither          -> `unclassified`, which is what `classify()` calls it.
                          It must NOT read `gated`: the classifier resolves a
                          floorless entry to `medium`, and displaying the
                          strictest tier for the one the classifier treats as
                          middling is the wrong direction to be wrong in.
    """
    floor = row.get("floor")  # single-shape-ok: registry row, not a brief
    if floor:
        return str(floor)
    if row.get("gate"):
        return "gated"
    return "unclassified"


def blast_radius(payload: Mapping[str, Any]) -> str:
    """Which operations this city treats as dangerous, and what awaits an emitter.

    `registry_present` is kept separate from emptiness for the reason the core
    cannot: `load_registry` collapses an absent file into an empty registry so
    that every lookup misses and fails safe, which is right for a gate and
    wrong for a page. Rendered, both would read `0` -- and "nothing here is
    dangerous" is the most reassuring possible way to say "we could not look".
    """
    present = payload.get("registry_present")
    rows: Sequence[Mapping[str, Any]] = payload.get("operations") or []
    awaiting: Sequence[str] = payload.get("awaiting_emitter") or []

    if present is False:
        return _panel(
            "Blast radius",
            '<p class="lede"><strong>The classification registry was not found.</strong> '
            "This is not a city with no dangerous operations — it is a registry we "
            "could not read. Every lookup against it misses and resolves to "
            "<span class=\"mono\">UNCLASSIFIED</span>, which is safe, and is not "
            "the same as safe-because-nothing-is-dangerous.</p>",
            region="city-blast-radius",
        )

    if not rows:
        body = (
            '<p class="lede">The registry was read and <strong>classifies no '
            "operations</strong>. A measurement, not a failure to look.</p>"
        )
    else:
        body = (
            f'<p class="lede"><strong>{len(rows)}</strong> operation'
            f'{"" if len(rows) == 1 else "s"} classified. <span class="mono">floor</span> '
            "is a floor: a plan's contents may raise it and may never lower it.</p>"
            '<ul class="reason-list">'
            + "".join(
                f'<li><span class="mono">{_e(str(r.get("operation")))}</span> — '  # single-shape-ok: registry row, not a brief
                # Render what the payload SAYS. The old `or "gated"` invented
                # the most restrictive tier for any missing floor -- including
                # entries the classifier calls `medium`, which is the opposite
                # end of the ladder and the more reassuring one.
                f'<strong>{_e(_tier_label(r))}</strong>'
                + (f' · {_e(str(r.get("reason")))}' if r.get("reason") else "")
                + "</li>"
                for r in rows
            )
            + "</ul>"
        )

    # What happens to an operation that is NOT on this list -- stick-dog's
    # review of #110. The count leads the panel, and a reader who sees "7
    # classified" naturally infers that coverage is seven and everything else
    # is unconstrained. The opposite is true: `classify()` returns
    # `gate: UNCLASSIFIED` for an unlisted operation with the reason "refused
    # rather than permitted", so ABSENCE IS THE SAFE STATE.
    #
    # Kept separate from the floor sentence deliberately. That one is about
    # escalation (contents may raise a floor, never lower it); this is about
    # omission. They are different mechanisms and collapsing them would let a
    # reader think the registry is the only thing standing between the city and
    # an unclassified operation.
    body += (
        '<p class="review-note" data-region="blast-radius-omission">'
        "<strong>An operation absent from this registry is refused, not "
        "permitted.</strong> It resolves to "
        '<span class="mono">UNCLASSIFIED</span> and is declined rather than run '
        "at some default tier — so this list is not the extent of what is "
        "protected, it is the extent of what has been given a tier.</p>"
    )

    if awaiting:
        body += (
            f'<p class="review-note"><strong>{len(awaiting)} '
            f'{"entry awaits" if len(awaiting) == 1 else "entries await"} an emitter.</strong> '
            "Classified, with nothing emitting them yet — a fact about coverage, "
            "not a defect and not something to clean up: "
            + " · ".join(f'<span class="mono">{_e(op)}</span>' for op in awaiting)
            + "</p>"
        )
    return _panel("Blast radius", body, region="city-blast-radius")


#: `queue_status` (#113): a diagnostic here means one of the six populations
#: (or all of them) could not be read. Distinct from `PROBE_FAILURE_CODES`
#: above -- those are `gc`-probe failures; these are `bd`-read failures with a
#: narrower, per-population blast radius (see `mctl_core/queue.py`).
QUEUE_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "MQUE_QUEUE_UNREACHABLE",
        "MQUE_UNCLAIMED_UNREACHABLE",
        "MQUE_DEFERRED_UNREACHABLE",
        "MQUE_ROUTED_UNREACHABLE",
    }
)

_QUEUE_SECTIONS: tuple[tuple[str, str], ...] = (
    ("ready_unclaimed", "Ready, unclaimed"),
    ("blocked", "Blocked"),
    ("tail", "Tail (ready, never dispatched, idle)"),
    ("starved", "Starved (blocked and idle)"),
    ("deferred", "Deferred (deliberately parked)"),
    ("next_up", "Next up (predicted — dispatch order is arbitrary)"),
)


def _queue_section(payload: Mapping[str, Any], key: str, label: str) -> str:
    rows: Sequence[Mapping[str, Any]] | None = payload.get(key)
    if rows is None:
        # This ONE population's read failed -- distinct from the whole panel
        # being unreachable (handled before this is ever called). Still not a
        # zero: a null population is unknown, not empty.
        codes = tuple(c for c in _codes(payload) if c in QUEUE_FAILURE_CODES)
        return (
            f"<h3>{_e(label)}</h3>"
            f'<p class="lede"><strong>{_e(label)} is unknown.</strong> This read '
            "failed independently of the rest of this panel.</p>"
            + (f'<p class="mono">{_e(" · ".join(codes))}</p>' if codes else "")
        )
    if not rows:
        return f'<h3>{_e(label)}</h3><p class="lede">{_e(label)}: <strong>0</strong>.</p>'
    items = []
    for row in rows[:20]:
        line = (
            f'<span class="mono">{_e(str(row.get("bead_id")))}</span> — '  # single-shape-ok: queue_status row, not a brief
            f'{_e(str(row.get("title")))}'  # single-shape-ok: queue_status row, not a brief
        )
        if row.get("blocked_on"):
            line += f' <span class="muted">(blocked on <span class="mono">{_e(str(row.get("blocked_on")))}</span>)</span>'
        if row.get("until"):
            line += f' <span class="muted">(until {_e(str(row.get("until")))})</span>'
        items.append(f"<li>{line}</li>")
    return (
        f"<h3>{_e(label)}</h3>"
        f'<p class="lede"><strong>{len(rows)}</strong> item{"" if len(rows) == 1 else "s"}.</p>'
        f'<ul class="reason-list">{"".join(items)}</ul>'
    )


def queue(payload: Mapping[str, Any]) -> str:
    """The QUEUE column: six populations, `next_up` explicitly labeled a prediction.

    `state == "unreachable"` means the core `bd ready --explain` read itself
    failed -- every population is unknown, never zero, and this panel says so
    once rather than six times. A population that is individually `None`
    (one of the three auxiliary reads failed, the core read did not) is
    handled per-section by `_queue_section` instead, so a real `blocked` list
    is not thrown away because `deferred` could not be read.
    """
    state = str(payload.get("state") or "unknown")
    if state == "unreachable":
        codes = _codes(payload)
        return _panel(
            "Queue",
            '<p class="lede"><strong>The queue is unknown.</strong> The bead '
            "store could not be read, so this is not a city with an empty "
            "queue — it is a queue we could not look at.</p>"
            + (f'<p class="mono">{_e(" · ".join(codes))}</p>' if codes else ""),
            region="city-queue",
        )
    body = "".join(_queue_section(payload, key, label) for key, label in _QUEUE_SECTIONS)
    return _panel("Queue", body, region="city-queue")


#: `costs_summary` (#118): a single local-file read backs the whole tool, so
#: a diagnostic here means the read itself failed -- distinct from
#: `MCOS_RIG_UNRESOLVED`, which is informational and fires on a SUCCESSFUL
#: read that still could not attribute every token to a rig side.
COSTS_FAILURE_CODES: frozenset[str] = frozenset({"MCOS_USAGE_UNREACHABLE"})


def _fmt_ratio(value: Any) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:.2f}"
    return "n/a (no math-side spend yet)"


def costs(payload: Mapping[str, Any]) -> str:
    """Token totals + worker-hours + the meta-work ratio, with its
    numerator/denominator, and `unpriced_count` stated explicitly (#118).

    `state == "unreachable"` means the local usage log itself could not be
    read -- every total is unknown, never zero. A successful read that still
    could not attribute every token to a rig side reports that gap as
    `unclassified_tokens`, a measurement, not a failure.
    """
    state = str(payload.get("state") or "unknown")
    if state == "unreachable":
        codes = tuple(c for c in _codes(payload) if c in COSTS_FAILURE_CODES)
        return _panel(
            "Costs",
            '<p class="lede"><strong>Token spend is unknown.</strong> The usage '
            "log could not be read, so this is not a city that spent nothing — "
            "it is spend we could not look at.</p>"
            + (f'<p class="mono">{_e(" · ".join(codes))}</p>' if codes else ""),
            region="city-costs",
        )

    total_tokens = payload.get("total_tokens") or 0
    worker_hours = payload.get("worker_hours") or 0.0
    unpriced_count = payload.get("unpriced_count") or 0
    unclassified_tokens = payload.get("unclassified_tokens") or 0
    ratio: Mapping[str, Any] = payload.get("meta_work_ratio") or {}
    numerator = ratio.get("numerator")
    denominator = ratio.get("denominator")

    body = (
        f'<p class="lede"><strong>{total_tokens:,}</strong> token'
        f'{"" if total_tokens == 1 else "s"} this window, '
        f'<strong>{worker_hours:.1f}</strong> worker-hour'
        f'{"" if worker_hours == 1 else "s"} beside it.</p>'
        f'<p class="lede">Meta-work ratio: <strong>{_e(_fmt_ratio(ratio.get("ratio")))}</strong> '
        f'(<span class="mono">{_e(str(numerator) if numerator is not None else "unknown")}</span> meta '
        f'/ <span class="mono">{_e(str(denominator) if denominator is not None else "unknown")}</span> math)'
        "  — city/meta effort over mathematics effort, by rig.</p>"
        f'<p class="lede"><strong>{unpriced_count}</strong> run'
        f'{"" if unpriced_count == 1 else "s"} unpriced — excluded from any dollar '
        "estimate, never valued at zero.</p>"
    )
    if unclassified_tokens:
        body += (
            f'<p class="note"><strong>{unclassified_tokens:,}</strong> token'
            f'{"" if unclassified_tokens == 1 else "s"} could not be attributed to '
            "either side of the ratio (the rig matched neither list, or its worker "
            "could not be resolved to a rig) and are reported separately, never "
            "folded into meta or math.</p>"
        )

    windows: Sequence[Mapping[str, Any]] = payload.get("windows") or []
    if windows:
        rows = "".join(
            f'<li><span class="mono">{_e(str(w.get("window")))}</span> — '  # single-shape-ok: costs_summary window row
            f'{int(w.get("total_tokens") or 0):,} tokens, ratio {_e(_fmt_ratio(w.get("meta_work_ratio")))}</li>'
            for w in windows[-30:]
        )
        body += f'<h3>By window (trend)</h3><ul class="reason-list">{rows}</ul>'

    return _panel("Costs", body, region="city-costs")


#: `worktrees_status` (#120): the rig roster (or every registered rig's own
#: `git worktree list`) failed -- distinct from `MWKT_ORPHAN_UNDERIVABLE` /
#: `MWKT_CREATED_BY_UNRECORDED` / `MWKT_SIZE_UNKNOWN`, which are informational
#: and fire on a SUCCESSFUL read that still carries honest gaps.
WORKTREES_FAILURE_CODES: frozenset[str] = frozenset({"MWKT_WORKTREES_UNREACHABLE"})

#: The typed sentinel `mctl_core.worktrees.UNRECORDED` uses for "nothing
#: records this field today" -- distinct from a real (possibly empty) value
#: and distinct from a read failure. Duplicated here rather than imported so
#: this render module has no import-time dependency on `mctl_core` (matching
#: every other renderer in this file).
_UNRECORDED = "unrecorded"


def _owner_cell(value: Any) -> str:
    """The unrecorded sentinel renders as an em dash -- visually distinct
    from a real recorded value, which may itself legitimately be empty."""
    if value == _UNRECORDED:
        return "—"
    text = str(value) if value not in (None, "") else "(empty)"
    return _e(text)


def _fmt_tri(value: Any) -> str:
    """A three-valued flag (`True`/`False`/`None`), rendered as `yes`/`no`/
    `unknown` -- `None` is a real "we do not know", never treated as `False`."""
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def _fmt_age(seconds: Any) -> str:
    if not isinstance(seconds, (int, float)) or isinstance(seconds, bool):
        return "unknown"
    return f"{seconds / 86400.0:.1f}d"


def _fmt_size(size_bytes: Any) -> str:
    if not isinstance(size_bytes, (int, float)) or isinstance(size_bytes, bool):
        return "unknown"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def worktrees(payload: Mapping[str, Any]) -> str:
    """Worktree inventory keyed by path, or an honest statement that it is
    unknown (#120).

    `state == "unreachable"` means the rig roster itself -- or every
    registered rig's own `git worktree list` -- could not be read: every
    count is unknown, never zero. `created_by`/`step`/`molecule` render as an
    em dash when the row carries the `unrecorded` sentinel, kept visually
    distinct from a real (possibly empty) value. `is_orphan` and
    `is_registered` render as two separate columns -- never folded into one,
    per the brief: different problems, different remedies.
    """
    state = str(payload.get("state") or "unknown")
    if state == "unreachable":
        codes = tuple(c for c in _codes(payload) if c in WORKTREES_FAILURE_CODES)
        return _panel(
            "Worktrees",
            '<p class="lede"><strong>The worktree inventory is unknown.</strong> The rig '
            "roster — or every registered rig's own read — could not be answered, so "
            "this is not a city with no worktrees, it is worktrees we could not look "
            "at.</p>"
            + (f'<p class="mono">{_e(" · ".join(codes))}</p>' if codes else ""),
            region="city-worktrees",
        )

    rows: Sequence[Mapping[str, Any]] = payload.get("worktrees") or []
    total = payload.get("total") or 0
    harvestable_count = payload.get("harvestable_count")

    body = (
        f'<p class="lede"><strong>{total}</strong> worktree{"" if total == 1 else "s"} '
        "across every registered rig, keyed by path.</p>"
    )
    if harvestable_count is not None:
        body += (
            f'<p class="lede"><strong>{harvestable_count}</strong> harvestable '
            "(git itself reports the directory gone).</p>"
        )

    if not rows:
        return _panel("Worktrees", body, region="city-worktrees")

    header = (
        "<thead><tr><th>Path</th><th>Rig</th><th>Branch</th><th>Molecule</th>"
        "<th>Created by</th><th>Step</th><th>Merged</th><th>Age</th><th>Size</th>"
        "<th>Orphan</th><th>Registered</th><th>Harvestable</th><th>Commits</th></tr></thead>"
    )
    body_rows = []
    for row in rows:
        path = str(row.get("path") or "")
        url = row.get("url")
        path_cell = f'<a href="{_e(str(url))}">{_e(path)}</a>' if url else _e(path)
        branch = row.get("branch")
        body_rows.append(
            '<tr class="mc-row">'
            f'<td class="mono">{path_cell}</td>'  # single-shape-ok: worktrees_status row, not a brief
            f'<td>{_e(str(row.get("rig") or "unknown"))}</td>'
            f'<td class="mono">{_e(str(branch)) if branch else "(detached)"}</td>'
            f"<td>{_owner_cell(row.get('molecule'))}</td>"
            f"<td>{_owner_cell(row.get('created_by'))}</td>"
            f"<td>{_owner_cell(row.get('step'))}</td>"
            f"<td>{_fmt_tri(row.get('merged'))}</td>"
            f"<td>{_fmt_age(row.get('age_seconds'))}</td>"
            f"<td>{_fmt_size(row.get('size_bytes'))}</td>"
            f"<td>{_fmt_tri(row.get('is_orphan'))}</td>"
            f"<td>{_fmt_tri(row.get('is_registered'))}</td>"
            f"<td>{_fmt_tri(row.get('harvestable'))}</td>"
            f'<td>{row.get("commits") if row.get("commits") is not None else "unknown"}</td>'
            "</tr>"
        )
    body += f'<div class="scroll-x"><table class="ntdata">{header}<tbody>{"".join(body_rows)}</tbody></table></div>'

    codes = _codes(payload)
    if codes:
        body += f'<p class="mono">{_e(" · ".join(codes))}</p>'

    return _panel("Worktrees", body, region="city-worktrees")


def unwired(tool: str, *, module: str, issue: int) -> str:
    """A surface whose backend exists and which no page can call.

    Deliberately not an empty panel and not a spinner. Both of those say
    "nothing here", which is false -- the work is done and unreachable, and
    saying so is the difference between a gap someone closes and a gap
    everyone walks past.
    """
    return _panel(
        tool.replace("_", " ").title(),
        '<p class="lede"><strong>Built, and not reachable from any page.</strong> '
        f'The logic exists in <span class="mono">{_e(module)}</span> and is tested, '
        f'but <span class="mono">{_e(tool)}</span> is not exposed as an MCP tool — '
        "and the MCP tool surface is the only way this dashboard can reach data. "
        "So there is nothing for this screen to call.</p>"
        f'<p class="lede">This is the gap described in issue #{issue}, and it is '
        "not a loading state, not an empty result, and not a statement that the "
        "city has none of these.</p>",
        region=f"city-unwired-{tool}",
    )


#: The surfaces in the `/city` fan-out that are RIG-SCOPED. Every other tool on
#: that page carries `CITY_SCOPE` in `mctl_core/mcp_server.py` and answers with
#: no rig named; these two do not, so on a city-wide dashboard with no rig
#: chosen they can only return `MCTL_CONTEXT_RIG_REQUIRED`.
RIG_SCOPED: frozenset[str] = frozenset({"queue_status", "costs_summary"})


def needs_rig(tool: str, rig_ids: Sequence[str], selected: str | None = None) -> str:
    """A rig-scoped surface on a page that has not been given a rig.

    Not a failure panel and not an empty one. The call did not fail -- it was
    never worth making: this tool has no `CITY_SCOPE`, so with no rig named the
    only reachable answer is `MCTL_CONTEXT_RIG_REQUIRED`, which is a statement
    about the request and not about the city. Rendering that in the slot where
    a measurement belongs is P6.2's mirror: a probe that could not have passed,
    dressed as one that ran and found something wrong.

    `_molecules` already answers this with a picker rather than a guaranteed
    failure; this is the same answer for the two rig-scoped surfaces that share
    the city fan-out with five city-scoped ones. The five still render -- the
    picker replaces two panels, never the page.
    """
    from mctl_dashboard.render import rig_filter_field

    return _panel(
        tool.replace("_", " ").title(),
        '<p class="lede"><strong>This surface is read per rig.</strong> '
        f'<span class="mono">{_e(tool)}</span> is rig-scoped, and no rig is '
        "selected — so there is no city-wide answer to show here. This is not a "
        "failure, not an empty result, and not a statement that the city has "
        "none of these.</p>"
        '<form class="operation" method="get" action="/city">'
        + rig_filter_field(rig_ids, selected)
        + '<div><button type="submit" class="secondary">'
        f"Show {_e(tool.replace('_', ' '))}</button></div></form>",
        region=f"city-needs-rig-{tool}",
    )
