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
    return _panel(
        "Agents",
        f'<p class="lede"><strong>{len(slots)}</strong> configured slot'
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
            '<p class="lede"><strong>The data plane is unreachable.</strong> '
            "This is a measurement, not a missing one: the probe answered and "
            "reported the server down. Distinct from "
            '<em>unknown</em>, which is what a probe that never answered '
            "produces.</p>"
        )
    else:
        body = (
            f'<p class="lede">Data plane: <strong>{_e(state)}</strong>, '
            f"across {len(per_rig)} rig{'' if len(per_rig) == 1 else 's'}.</p>"
        )
    if per_rig:
        body += (
            '<ul class="reason-list">'
            + "".join(
                f'<li><span class="mono">{_e(str(r.get("rig_id")))}</span> — '  # single-shape-ok: city_health per-rig envelope, not a brief row
                f'{_e(str(r.get("state")))}'
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
