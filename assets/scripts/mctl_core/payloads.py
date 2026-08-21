"""The dict shapes both consumers of `mctl` read.

The dashboard and the MCP server are **siblings over `mctl`**, not a chain --
the dashboard must not reach `mctl` by speaking JSON-RPC to the MCP server
(Taylor, 2026-08-20: *"The dashboard is powered by mctl and the MCP is powered
by mctl. That is what they have in common."*).

Decoupling them needs somewhere for the payload shaping to live. The core
functions -- `list_briefs_report`, `show_brief`, `brief_options_report`,
`doctor_briefs`, `validate_brief`, `ready_work` -- were always importable; what
was not was the layer that turns a typed `BriefListing` into the dict a
renderer reads. That lived module-private inside `mcp_server`, so the only way
to obtain a payload was to be an MCP client.

It lives here now, so both consumers call one definition. The alternative --
letting the dashboard shape its own dicts from core types -- is a second
implementation of the same contract, which is precisely the trap that produced
the `unlock_count` misreads and the adjudication write reach-around. **One
shaping layer, two consumers.**

What deliberately does *not* move: the `_handle_*` adapters. They carry
MCP-specific concerns -- the `RigProgress` partial slot, tool-argument
validation, the JSON-RPC error envelope -- and moving them would make the
dashboard inherit an argument protocol it has no reason to speak.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .briefs import BriefError, BriefFilters, BriefListing, brief_command_diagnostics
from .city import DEGRADED_SOURCES
from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .trace import fold, read_rows, trace_not_found_diagnostic

__all__ = [
    "brief_filters",
    "briefs_list_payload",
    "diagnostics_payload",
    "replay_blocked",
    "require_trace",
]


def brief_filters(arguments: Mapping[str, Any]) -> BriefFilters:
    return BriefFilters(arguments.get("status"), arguments.get("label"))


def diagnostics_payload(
    ctx: MctlContext, diagnostics: Sequence[Diagnostic]
) -> list[dict[str, object]]:
    """Context warnings first, then the call's own.

    Order is part of the contract: a reader that stops at the first ERROR must
    see a degraded-context warning before a finding derived from it.
    """
    return [warning.to_dict() for warning in ctx.warnings] + [
        diagnostic.to_dict() for diagnostic in diagnostics
    ]


def briefs_list_payload(ctx: MctlContext, listing: BriefListing) -> dict[str, object]:
    """The roster, with an incomplete read declared rather than implied.

    `degraded_sources` is only present when the listing is incomplete, so its
    absence means "everything answered" rather than "nobody checked".
    """
    payload: dict[str, object] = {
        "briefs": [record.to_dict() for record in listing.records],
        "diagnostics": diagnostics_payload(
            ctx,
            brief_command_diagnostics(ctx, listing.records)
            + tuple(
                diagnostic
                for outcome in listing.degraded_sources
                for diagnostic in outcome.diagnostics
            ),
        ),
    }
    if not listing.complete:
        payload[DEGRADED_SOURCES] = listing.degraded_payload()
    return payload


def replay_blocked(ctx: MctlContext, source_trace_id: str, message: str) -> Diagnostic:
    return Diagnostic(
        severity=Severity.WARN,
        code="MCTL_TRACE_REPLAY_BLOCKED",
        message=message,
        hint="Preview only. Re-run the originating mutation if the effect is still wanted.",
        facts={
            "city_path": str(ctx.city_root),
            "implementation_provenance": "mctl MCP trace_replay_preview",
            "rig_name": ctx.rig_id,
            "rig_path": str(ctx.rig_root),
            "source_trace_id": source_trace_id,
        },
        trace_id=ctx.trace_id,
    )


def require_trace(ctx: MctlContext, trace_id: str) -> dict[str, object]:
    record = fold(read_rows(ctx.rig_root), trace_id)
    if record is None:
        raise BriefError(trace_not_found_diagnostic(ctx, trace_id))
    return record
