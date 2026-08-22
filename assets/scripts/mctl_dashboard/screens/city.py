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
    if state == "unreachable":
        body = (
            '<p class="lede"><strong>The data plane could not be reached.</strong> '
            "That is a statement about the probe, <em>not</em> about the city: "
            "<em>unreachable</em> is not <em>unhealthy</em>. Nothing here should be "
            "read as evidence that anything is down.</p>"
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
