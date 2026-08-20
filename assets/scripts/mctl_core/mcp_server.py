"""A typed MCP server over the CLI-proven mctl core (plan Slice 6).

The CLI and this server are two adapters over ONE core. Every handler below
calls the same `context.py` / `briefs.py` / `work.py` / `effects.py` /
`trace.py` functions `mctl` calls, with the same effect-plan and phased-trace
semantics. It never shells out to `bin/mctl`: a subprocess adapter would fork
the semantics and put an argv contract where a function call belongs.

Three properties are load-bearing and are what the tests pin:

1. **Typed in, typed out.** Arguments are validated against each tool's
   declared input schema *before* any core function runs, and a violation is
   a JSON-RPC `-32602` carrying structured failures -- never a traceback and
   never a prose string. The whole argument for MCP over prose skills is that
   failures stop being advisory.
2. **No passthrough.** There is no `shell`, `gc`, `bd`, `mctl`, `exec`, or
   `run_command` tool, and no tool accepts a raw command or argv.
3. **Honest artifact state.** Q5 (`subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md`)
   is open: the redundant-artifact model resolves rig-root-relative while the
   live stack is city-root-level, and looks up `<root>/.pile/<bead_id>.md`
   while real pile files carry the bead id in `artifact:` frontmatter. Against
   the live city that makes 66 of 70 briefs report a false `MBRF021`. Q5 is
   NOT fixed here -- the per-rig/city-wide question belongs to the repo owner
   -- but this layer refuses to present the resulting state as established.
   See `assess_artifact_trust`.

Rollout gate (plan §8): MCP tools stay disabled from external clients until
the surface is proven. `client_class` defaults to `external`, and an external
client sees an empty tool list until an operator explicitly arms external
access; even armed, mutating tools stay internal-only. Internal clients --
the Slice 6 harness and mctl's own tests -- get the full surface. The harness
exercises this gate rather than bypassing it: it asks for the internal
surface AND separately proves the external surface is closed.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Mapping, Sequence

from .briefs import (
    BriefError,
    BriefFilters,
    brief_command_diagnostics,
    brief_options_report,
    doctor_briefs,
    list_briefs,
    show_brief,
    validate_brief,
    validation_scope,
)
from .city import for_each_rig, merge_outcomes
from .context import CityScope, ContextError, MctlContext, resolve_city, resolve_context
from .diagnostics import Diagnostic, Severity
from .effects import (
    BriefCreateInput,
    MutationError,
    apply_effect_plan,
    dry_run_payload,
    plan_adjudication,
    plan_create_brief,
    plan_deferral,
)
from .liveness import city_not_active_diagnostic
from .provenance import ProvenanceError
from .redundant_state import artifact_layout
from .schemas import (
    BRIEF_DIAGNOSTICS_SCHEMA,
    BRIEF_DETAIL_SCHEMA,
    BRIEF_OPTION_SCHEMA,
    BRIEF_RECORD_SCHEMA,
    DRY_RUN_PROPERTY,
    EFFECT_PLAN_SCHEMA,
    SEVERITY_COUNTS_SCHEMA,
    STRING_ARRAY,
    TRACE_RECORD_SCHEMA,
    WORK_ITEM_SCHEMA,
    Schema,
    nullable_string,
    request_schema,
    response_schema,
    schema_errors,
)
from .trace import fold, new_trace_id, read_rows, trace_not_found_diagnostic
from .work import (
    WorkError,
    apply_dispatch_plan,
    dispatch_dry_run_payload,
    plan_dispatch,
    ready_work,
    work_provenance,
    work_status,
)


PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "mctl"
SERVER_VERSION = "0.6.0"

INSTRUCTIONS = (
    "Typed MathCity domain tools over the mctl core. The bead store is "
    "canonical; filesystem briefs are redundant cache. There is no generic "
    "command-execution tool -- no shell, gc, bd, mctl, or run_command "
    "passthrough -- by design. Mutating tools default to dry_run=true and "
    "return an EffectPlan; pass dry_run=false to apply. Responses that report "
    "redundant-artifact state carry an `artifact_trust` verdict: while "
    "OPEN-DESIGN-QUESTIONS Q5 is unresolved that state may be unverifiable, "
    "and unactionable diagnostics are moved to `untrusted_diagnostics`."
)

# Names a generic-passthrough tool would plausibly take. Asserted absent by
# tests and by the harness, so the constraint is checked rather than trusted.
FORBIDDEN_TOOL_NAMES = frozenset(
    {"shell", "gc", "bd", "mctl", "run_command", "exec", "run_shell"}
)

CLIENT_CLASS_ENV = "MCTL_MCP_CLIENT_CLASS"
EXTERNAL_TOOLS_ENV = "MCTL_MCP_ENABLE_EXTERNAL_TOOLS"
CLIENT_CLASSES = ("internal", "external")

METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


# --- Q5: is redundant-artifact state trustworthy at all? --------------------

#: Q5 names `MBRF021` explicitly: 66 of 70 live briefs report "no redundant
#: cache artifact" when the artifacts exist under different names in a
#: different tree. Its documented remedy is to repair the filesystem, so
#: acting on it today would CREATE 66 duplicate artifacts. Nothing may act on
#: it until Q5 resolves, so this layer moves it out of the actionable array
#: rather than quietly dropping it or shipping it as established fact.
UNTRUSTED_ARTIFACT_CODES = ("MBRF021",)

Q5_REFERENCE = "subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md#q5"


@dataclass(frozen=True)
class ArtifactTrust:
    """Whether the redundant-artifact readings in a response can be acted on."""

    trusted: bool
    reason: str
    resolved_brief_root: str
    resolved_pile: str
    open_question: str | None = None
    reference: str | None = None
    withheld_codes: tuple[str, ...] = ()

    def with_withheld(self, codes: Sequence[str]) -> "ArtifactTrust":
        return ArtifactTrust(
            trusted=self.trusted,
            reason=self.reason,
            resolved_brief_root=self.resolved_brief_root,
            resolved_pile=self.resolved_pile,
            open_question=self.open_question,
            reference=self.reference,
            withheld_codes=tuple(codes),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "open_question": self.open_question,
            "reason": self.reason,
            "reference": self.reference,
            "resolved_brief_root": self.resolved_brief_root,
            "resolved_pile": self.resolved_pile,
            "trusted": self.trusted,
            "withheld_codes": list(self.withheld_codes),
        }


def _frontmatter_artifact_id(path: Path) -> str | None:
    """Read the `artifact:` frontmatter key the live pile convention uses."""
    try:
        with path.open(encoding="utf-8") as handle:
            first = handle.readline().strip()
            if first != "---":
                return None
            for _ in range(64):
                line = handle.readline()
                if not line or line.strip() == "---":
                    return None
                key, separator, value = line.partition(":")
                if separator and key.strip() == "artifact":
                    return value.strip().strip("\"'") or None
    except OSError:
        return None
    return None


def _frontmatter_lookup_mismatch(pile: Path) -> tuple[str, str] | None:
    if not pile.is_dir():
        return None
    for path in sorted(pile.glob("*.md")):
        artifact_id = _frontmatter_artifact_id(path)
        if artifact_id and artifact_id != path.stem:
            return path.name, artifact_id
    return None


def assess_artifact_trust(ctx: MctlContext) -> ArtifactTrust:
    """Decide whether this rig's artifact readings mean anything.

    This deliberately does NOT resolve Q5 and does not add a second path
    resolver: it calls the one `artifact_layout()` the rest of mctl calls and
    then reports whether what came back can be believed. Two independent
    failures make it unbelievable, and Q5 documents both:

    * the resolved brief root does not exist, so every artifact reads
      `missing` for a structural reason rather than an observed one;
    * pile files carry their bead id in `artifact:` frontmatter instead of in
      the filename, so the `<bead_id>.md` lookup cannot find a file that is
      sitting right there.
    """
    layout = artifact_layout(ctx)
    root = str(layout.root)
    pile = str(layout.pile)
    if not layout.root.is_dir():
        return ArtifactTrust(
            trusted=False,
            reason=(
                f"the resolved brief root {root} does not exist, so every artifact "
                "reads `missing` for a structural reason rather than an observed one"
            ),
            resolved_brief_root=root,
            resolved_pile=pile,
            open_question="Q5",
            reference=Q5_REFERENCE,
        )
    if not layout.pile.is_dir():
        return ArtifactTrust(
            trusted=False,
            reason=f"the resolved pile directory {pile} does not exist",
            resolved_brief_root=root,
            resolved_pile=pile,
            open_question="Q5",
            reference=Q5_REFERENCE,
        )
    mismatch = _frontmatter_lookup_mismatch(layout.pile)
    if mismatch is not None:
        name, artifact_id = mismatch
        return ArtifactTrust(
            trusted=False,
            reason=(
                f"pile file {name} carries its bead id ({artifact_id}) in an "
                "`artifact:` frontmatter key rather than in its filename, so the "
                "<bead_id>.md lookup cannot find artifacts that exist"
            ),
            resolved_brief_root=root,
            resolved_pile=pile,
            open_question="Q5",
            reference=Q5_REFERENCE,
        )
    return ArtifactTrust(
        trusted=True,
        reason=(
            "the resolved brief root exists and its pile uses the <bead_id>.md "
            "filename convention the lookup assumes"
        ),
        resolved_brief_root=root,
        resolved_pile=pile,
    )


def _untrusted_state_diagnostic(ctx: MctlContext, trust: ArtifactTrust) -> Diagnostic:
    return Diagnostic(
        severity=Severity.WARN,
        code="MCTL_MCP_ARTIFACT_STATE_UNTRUSTED",
        message=(
            "Redundant-artifact state in this response is not trustworthy: "
            f"{trust.reason}. Open design question Q5 must resolve before any "
            "artifact-state finding here is acted on."
        ),
        hint=(
            f"Read Q5 in {Q5_REFERENCE}. Do not repair the filesystem from "
            f"withheld codes {list(trust.withheld_codes) or list(UNTRUSTED_ARTIFACT_CODES)}."
        ),
        facts={
            "city_path": str(ctx.city_root),
            "data_location": trust.resolved_brief_root,
            "implementation_provenance": "mctl MCP artifact-trust gate",
            "policy_reference": "B2.8",
            "rig_name": ctx.rig_id,
            "rig_path": str(ctx.rig_root),
        },
        trace_id=ctx.trace_id,
    )


def _mark_artifacts(record: object, trusted: bool) -> None:
    """Annotate every artifact with the core's raw reading, in place."""
    if not isinstance(record, dict):
        return
    for artifact in record.get("redundant_artifacts", []) or []:
        if not isinstance(artifact, dict):
            continue
        reported = artifact.get("state")
        artifact["state_reported_by_core"] = reported
        if not trusted and reported == "missing":
            # `missing` is a claim about the world; this reading cannot support
            # it, so the response says so instead of asserting it.
            artifact["state"] = "unverified"


def _partition(diagnostics: Sequence[Mapping[str, object]]) -> tuple[list, list]:
    kept, withheld = [], []
    for diagnostic in diagnostics:
        target = withheld if diagnostic.get("code") in UNTRUSTED_ARTIFACT_CODES else kept
        target.append(diagnostic)
    return kept, withheld


def apply_artifact_trust(
    ctx: MctlContext, payload: dict[str, object], trust: ArtifactTrust
) -> dict[str, object]:
    """Make the Q5 verdict part of the payload, not a footnote beside it."""
    withheld: list[Mapping[str, object]] = []
    _mark_artifacts(payload.get("brief"), trust.trusted)
    for record in payload.get("briefs", []) or []:
        _mark_artifacts(record, trust.trusted)

    if not trust.trusted:
        kept, moved = _partition(payload.get("diagnostics", []) or [])
        payload["diagnostics"] = kept
        withheld.extend(moved)
        for entry in payload.get("brief_diagnostics", []) or []:
            if isinstance(entry, dict):
                kept, moved = _partition(entry.get("diagnostics", []) or [])
                entry["diagnostics"] = kept
                withheld.extend(moved)

    trust = trust.with_withheld(sorted({str(item.get("code")) for item in withheld}))
    payload["untrusted_diagnostics"] = list(withheld)
    payload["artifact_trust"] = trust.to_dict()
    if not trust.trusted:
        payload["diagnostics"] = [
            *(payload.get("diagnostics", []) or []),
            _untrusted_state_diagnostic(ctx, trust).to_dict(),
        ]
    return payload


# --- tool specifications ----------------------------------------------------


#: A tool resolves either one rig (`rig`) or the city registry alone (`city`).
#: City-scoped tools answer questions that must stay answerable when a rig is
#: unselectable or its data plane is down -- "which rigs exist" above all,
#: since a city-wide reader cannot report a rig as degraded without first
#: knowing the rig is there.
RIG_SCOPE = "rig"
CITY_SCOPE = "city"

#: `all_rigs` is the plan's own name for the explicit cross-rig opt-in (Slice 2
#: Global Constraints, and the `briefs_list` input schema). The tools that
#: accept it name the arrays their per-rig payloads contribute; `city.py` does
#: the fan-out and the merge, so no consumer assembles a city-wide answer for
#: itself. Cross-rig *mutation* stays forbidden -- an assertion below refuses
#: to register a mutating tool here.
CROSS_RIG_ARRAYS: dict[str, tuple[str, ...]] = {
    "briefs_list": ("briefs",),
    "briefs_validate": ("briefs", "brief_diagnostics"),
    "work_ready": ("work",),
}

ALL_RIGS_PROPERTY: Schema = {
    "type": "boolean",
    "default": False,
    "description": (
        "Read every registered rig instead of one. Rows carry `rig_id`, and `rigs` reports "
        "each rig's outcome -- a rig that cannot be read is a degraded entry, not a failure "
        "of the call."
    ),
}


@dataclass(frozen=True)
class ToolSpec:
    name: str
    title: str
    description: str
    input_schema: Schema
    output_schema: Schema
    handler: Callable[[Any, Mapping[str, Any]], dict[str, object]]
    mutating: bool = False
    scope: str = RIG_SCOPE

    @property
    def cross_rig(self) -> bool:
        return self.name in CROSS_RIG_ARRAYS
    # Plan §8: "Keep MCP tools disabled from external clients until CLI
    # behavior for the same core function is proven." Read paths are proven by
    # Slices 1-5; mutation stays internal until the MCP surface itself has a
    # track record.
    external_ready: bool = True
    artifact_state: bool = False

    def to_wire(self) -> dict[str, object]:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
            "outputSchema": self.output_schema,
            "_meta": {
                "mctl": {
                    "artifact_state": self.artifact_state,
                    "external_ready": self.external_ready,
                    "mutating": self.mutating,
                    "scope": self.scope,
                }
            },
        }


def _filters(arguments: Mapping[str, Any]) -> BriefFilters:
    return BriefFilters(arguments.get("status"), arguments.get("label"))


def _handle_context_resolve(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    payload = dict(ctx.to_dict())
    payload["diagnostics"] = [warning.to_dict() for warning in ctx.warnings]
    return payload


def _handle_context_rigs(scope: CityScope, arguments: Mapping[str, Any]) -> dict[str, object]:
    """The city registry, with no rig selected and nothing probed.

    A city-wide client asks this first. It reads configuration only, so it
    still answers when Dolt is down -- which is exactly when the client most
    needs the roster, because a rig it cannot name is a rig it cannot report
    as degraded.
    """
    return {
        "city_root": str(scope.city_root),
        "diagnostics": [],
        "discovery_path": scope.discovery_path,
        "rigs": [rig.to_dict() for rig in scope.rigs],
    }


def _handle_briefs_list(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    records = list_briefs(ctx, _filters(arguments))
    return {
        "briefs": [record.to_dict() for record in records],
        "diagnostics": _diagnostics(ctx, brief_command_diagnostics(ctx, records)),
    }


def _handle_briefs_show(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    record = show_brief(ctx, arguments["brief_id"])
    return {
        "brief": record.to_dict(),
        "diagnostics": _diagnostics(ctx, brief_command_diagnostics(ctx, (record,))),
    }


def _handle_briefs_options(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    options, diagnostics = brief_options_report(ctx, arguments["brief_id"])
    return {
        "brief_id": arguments["brief_id"],
        "diagnostics": _diagnostics(ctx, diagnostics),
        "options": [option.to_dict() for option in options],
    }


def _handle_briefs_doctor(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    report = doctor_briefs(ctx, arguments.get("brief_id"))
    payload = report.to_dict()
    payload["diagnostics"] = _diagnostics(ctx, report.diagnostics)
    return payload


def _handle_briefs_validate(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    scope = validation_scope(ctx, arguments.get("brief_id"), bool(arguments.get("all")))
    report = validate_brief(ctx, scope)
    payload = report.to_dict()
    payload["diagnostics"] = _diagnostics(ctx, report.diagnostics)
    return payload


def _handle_briefs_adjudicate(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    plan = plan_adjudication(
        ctx,
        arguments["brief_id"],
        verdict=arguments.get("verdict"),
        reason=arguments.get("reason"),
        option=arguments.get("option"),
    )
    return _effect_payload(ctx, plan, _dry_run(arguments))


def _handle_briefs_defer(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    plan = plan_deferral(
        ctx,
        arguments["brief_id"],
        reason=arguments.get("reason"),
        until=arguments.get("until"),
        days=arguments.get("days"),
    )
    return _effect_payload(ctx, plan, _dry_run(arguments))


def _handle_briefs_create(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    plan = plan_create_brief(
        ctx,
        BriefCreateInput(
            title=arguments.get("title") or "",
            body=arguments.get("body") or "",
            labels=tuple(arguments.get("labels") or ()),
            requested_by=arguments.get("requested_by"),
            sources=tuple(arguments.get("sources") or ()),
        ),
    )
    return _effect_payload(ctx, plan, _dry_run(arguments))


def _handle_work_ready(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    return {"diagnostics": _diagnostics(ctx, ()), "work": [item.to_dict() for item in ready_work(ctx)]}


def _handle_work_status(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    return {
        "diagnostics": _diagnostics(ctx, ()),
        "work": work_status(ctx, arguments["brief_id"]).to_dict(),
    }


def _handle_work_provenance(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    return {
        "diagnostics": _diagnostics(ctx, ()),
        "provenance": work_provenance(ctx, arguments["brief_id"]).to_dict(),
    }


def _handle_work_dispatch(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    plan = plan_dispatch(ctx, arguments["brief_id"])
    payload = (
        dispatch_dry_run_payload(plan) if _dry_run(arguments) else apply_dispatch_plan(ctx, plan)
    )
    payload.setdefault("diagnostics", [])
    payload["diagnostics"] = _diagnostics(ctx, ()) + list(payload["diagnostics"])
    return payload


def _handle_trace_show(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    return {"diagnostics": _diagnostics(ctx, ()), "trace": _require_trace(ctx, arguments["trace_id"])}


def _handle_trace_replay_preview(
    ctx: MctlContext, arguments: Mapping[str, Any]
) -> dict[str, object]:
    """Show what a replay WOULD do. It reapplies nothing, ever.

    The recorded `planned` row already holds the intended effects, so the
    preview is a read of history rather than a re-plan. Re-planning here would
    be a second mutation path with none of the effect-plan guards.
    """
    source_trace_id = arguments["trace_id"]
    record = _require_trace(ctx, source_trace_id)
    blockers: list[dict[str, object]] = []
    outcome = record.get("outcome")
    if outcome == "applied":
        blockers.append(
            _replay_blocked(
                ctx,
                source_trace_id,
                "This trace was already applied; replaying it would duplicate its effects.",
            ).to_dict()
        )
    elif outcome == "aborted":
        blockers.append(
            _replay_blocked(
                ctx,
                source_trace_id,
                "This trace aborted; replay it only after its blocking diagnostics are cleared.",
            ).to_dict()
        )
    return {
        "applied": False,
        "blocking_diagnostics": list(record.get("blocking_diagnostics", []) or []),
        "diagnostics": _diagnostics(ctx, ()),
        "operation": record.get("operation"),
        "outcome": outcome,
        "planned_effects": list(record.get("planned_effects", []) or []),
        "replay_blockers": blockers,
        "source_trace_id": source_trace_id,
    }


def _replay_blocked(ctx: MctlContext, source_trace_id: str, message: str) -> Diagnostic:
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


def _require_trace(ctx: MctlContext, trace_id: str) -> dict[str, object]:
    record = fold(read_rows(ctx.rig_root), trace_id)
    if record is None:
        raise BriefError(trace_not_found_diagnostic(ctx, trace_id))
    return record


def _dry_run(arguments: Mapping[str, Any]) -> bool:
    """Absent means dry run. Mutation is opt-in, never opt-out."""
    return bool(arguments.get("dry_run", True))


def _effect_payload(ctx: MctlContext, plan, dry_run: bool) -> dict[str, object]:
    payload = dry_run_payload(plan) if dry_run else apply_effect_plan(ctx, plan).to_dict()
    payload["diagnostics"] = _diagnostics(ctx, ()) + list(payload.get("diagnostics", []))
    return payload


def _diagnostics(ctx: MctlContext, diagnostics: Sequence[Diagnostic]) -> list[dict[str, object]]:
    return [warning.to_dict() for warning in ctx.warnings] + [
        diagnostic.to_dict() for diagnostic in diagnostics
    ]


_BRIEF_ID = {"type": "string", "description": "Canonical brief bead id."}

_EFFECT_RESPONSE = {
    "applied": {"type": "boolean", "description": "False for a dry run."},
    "actual_effects": {"type": "array", "description": "Effects that really landed."},
    "effect_plan": EFFECT_PLAN_SCHEMA,
}

TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="context_resolve",
        title="Resolve runtime context",
        description="Resolve one registered Gas City rig, exactly as `mctl context --json` does.",
        input_schema=request_schema(),
        output_schema=response_schema(
            {
                "city_active": {"type": ["boolean", "null"]},
                "city_endpoint": nullable_string("Probed Dolt endpoint."),
                "city_root": {"type": "string"},
                "discovery_path": {"type": "string"},
                "gates_toml": {"type": "string"},
                "invocation_cwd": {"type": "string"},
                "paths_toml": {"type": "string"},
                "registered_rigs": dict(
                    STRING_ARRAY, description="Every rig this city registers, in registry order."
                ),
                "rig_db": {"type": "string"},
                "rig_id": {"type": "string"},
                "rig_root": {"type": "string"},
                "source_checkout": {"type": "string"},
                "warnings": {"type": "array"},
            },
            [
                "city_active",
                "city_root",
                "discovery_path",
                "registered_rigs",
                "rig_db",
                "rig_id",
                "rig_root",
                "source_checkout",
                "warnings",
            ],
        ),
        handler=_handle_context_resolve,
    ),
    ToolSpec(
        name="context_rigs",
        title="List registered rigs",
        description=(
            "Enumerate every rig this city registers, selecting none. Configuration only: "
            "it answers while a rig's data plane is down, which is when a city-wide reader "
            "needs the roster most."
        ),
        input_schema=request_schema(),
        output_schema=response_schema(
            {
                "city_root": {"type": "string"},
                "discovery_path": {"type": "string"},
                "rigs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rig_db": {"type": "string"},
                            "rig_id": {"type": "string"},
                            "rig_root": {"type": "string"},
                        },
                        "required": ["rig_db", "rig_id", "rig_root"],
                        "additionalProperties": True,
                    },
                },
            },
            ["city_root", "discovery_path", "rigs"],
        ),
        handler=_handle_context_rigs,
        scope=CITY_SCOPE,
    ),
    ToolSpec(
        name="briefs_list",
        title="List briefs",
        description=(
            "List briefs from both stores: canonical decision brief beads, plus "
            "decisions-track manifest rows that no bead and no stack file represents. "
            "Every record names its `source` (`bead` or `manifest`); a manifest row is "
            "attested by nothing else, carries no body, and is `adjudicated` only when "
            "the row itself holds a verdict -- otherwise `unreadable`, which is not the "
            "pending queue. Optionally filtered by status or label."
        ),
        input_schema=request_schema(
            {
                "status": nullable_string("Filter by raw bead or decision status."),
                "label": nullable_string("Filter by brief label."),
                "all_rigs": ALL_RIGS_PROPERTY,
            }
        ),
        output_schema=response_schema(
            {"briefs": {"type": "array", "items": BRIEF_RECORD_SCHEMA}},
            ["briefs"],
            artifact_state=True,
        ),
        handler=_handle_briefs_list,
        artifact_state=True,
    ),
    ToolSpec(
        name="briefs_show",
        title="Show one brief",
        description=(
            "Show one brief's canonical bead state, its body, that body's parsed sections, "
            "redundant artifacts, and policy refs. `body` is the verbatim canonical text and "
            "stays authoritative: `sections` is a convenience over it, never a replacement."
        ),
        input_schema=request_schema({"brief_id": _BRIEF_ID}, ["brief_id"]),
        output_schema=response_schema({"brief": BRIEF_DETAIL_SCHEMA}, ["brief"], artifact_state=True),
        handler=_handle_briefs_show,
        artifact_state=True,
    ),
    ToolSpec(
        name="briefs_options",
        title="Show available brief actions",
        description="Report which actions this brief's bead state permits, and why the rest do not.",
        input_schema=request_schema({"brief_id": _BRIEF_ID}, ["brief_id"]),
        output_schema=response_schema(
            {
                "brief_id": {"type": "string"},
                "options": {"type": "array", "items": BRIEF_OPTION_SCHEMA},
            },
            ["brief_id", "options"],
        ),
        handler=_handle_briefs_options,
    ),
    ToolSpec(
        name="briefs_doctor",
        title="Report brief invariant violations",
        description="Report canonical/cache invariant violations across the rig without repairing them.",
        input_schema=request_schema(
            {"brief_id": nullable_string("Inspect one brief instead of the whole rig.")}
        ),
        output_schema=response_schema(
            {
                "brief_diagnostics": BRIEF_DIAGNOSTICS_SCHEMA,
                "briefs": {"type": "array", "items": BRIEF_RECORD_SCHEMA},
                "severity_counts": SEVERITY_COUNTS_SCHEMA,
            },
            ["brief_diagnostics", "briefs", "severity_counts"],
            artifact_state=True,
        ),
        handler=_handle_briefs_doctor,
        artifact_state=True,
    ),
    ToolSpec(
        name="briefs_validate",
        title="Validate brief consistency",
        description="Prove canonical bead state and redundant cache agree, for one brief or all of them.",
        input_schema=request_schema(
            {
                "brief_id": nullable_string("Validate exactly this brief."),
                "all": {"type": "boolean", "description": "Validate every canonical brief."},
                "all_rigs": ALL_RIGS_PROPERTY,
            }
        ),
        output_schema=response_schema(
            {
                "brief_diagnostics": BRIEF_DIAGNOSTICS_SCHEMA,
                "briefs": {"type": "array", "items": BRIEF_RECORD_SCHEMA},
                "scope": {"type": "string"},
                "severity_counts": SEVERITY_COUNTS_SCHEMA,
                "valid": {"type": "boolean"},
            },
            ["brief_diagnostics", "briefs", "scope", "severity_counts", "valid"],
            artifact_state=True,
        ),
        handler=_handle_briefs_validate,
        artifact_state=True,
    ),
    ToolSpec(
        name="briefs_adjudicate",
        title="Record a brief verdict",
        description="Record a verdict through the shared effect plan. Dry run by default.",
        input_schema=request_schema(
            {
                "brief_id": _BRIEF_ID,
                "verdict": nullable_string("approve, reject, or revise."),
                "reason": nullable_string("Why this verdict, recorded on the bead."),
                "option": nullable_string("Which offered option the verdict selects."),
                "dry_run": DRY_RUN_PROPERTY,
            },
            ["brief_id"],
        ),
        output_schema=response_schema(
            _EFFECT_RESPONSE, ["applied", "effect_plan"], artifact_state=True
        ),
        handler=_handle_briefs_adjudicate,
        mutating=True,
        external_ready=False,
        artifact_state=True,
    ),
    ToolSpec(
        name="briefs_defer",
        title="Defer a brief",
        description="Defer a brief through the shared effect plan. Dry run by default.",
        input_schema=request_schema(
            {
                "brief_id": _BRIEF_ID,
                "reason": nullable_string("Why the brief is being deferred."),
                "until": nullable_string("ISO date the defer window ends."),
                "days": {"type": ["integer", "null"], "description": "Defer window length in days."},
                "dry_run": DRY_RUN_PROPERTY,
            },
            ["brief_id"],
        ),
        output_schema=response_schema(
            _EFFECT_RESPONSE, ["applied", "effect_plan"], artifact_state=True
        ),
        handler=_handle_briefs_defer,
        mutating=True,
        external_ready=False,
        artifact_state=True,
    ),
    ToolSpec(
        name="briefs_create",
        title="Create a brief bead",
        description="Create a bead-first decision brief through the shared effect plan. Dry run by default.",
        input_schema=request_schema(
            {
                "title": {"type": "string", "description": "What is being decided."},
                "body": {"type": "string", "description": "Brief body markdown."},
                "labels": dict(STRING_ARRAY, description="Brief labels."),
                "sources": dict(STRING_ARRAY, description="Source bead ids this brief decides on."),
                "requested_by": nullable_string("Who asked for the brief."),
                "dry_run": DRY_RUN_PROPERTY,
            },
            ["title", "body"],
        ),
        output_schema=response_schema(
            _EFFECT_RESPONSE, ["applied", "effect_plan"], artifact_state=True
        ),
        handler=_handle_briefs_create,
        mutating=True,
        external_ready=False,
        artifact_state=True,
    ),
    ToolSpec(
        name="work_ready",
        title="List ready work",
        description="List brief-backed work whose canonical state permits dispatch.",
        input_schema=request_schema({"all_rigs": ALL_RIGS_PROPERTY}),
        output_schema=response_schema(
            {"work": {"type": "array", "items": WORK_ITEM_SCHEMA}}, ["work"]
        ),
        handler=_handle_work_ready,
    ),
    ToolSpec(
        name="work_status",
        title="Show work readiness",
        description="Show one brief's work readiness and every blocker holding it.",
        input_schema=request_schema({"brief_id": _BRIEF_ID}, ["brief_id"]),
        output_schema=response_schema({"work": WORK_ITEM_SCHEMA}, ["work"]),
        handler=_handle_work_status,
    ),
    ToolSpec(
        name="work_provenance",
        title="Show dispatch provenance",
        description="Show the validated dispatch provenance recorded for a brief's work bead.",
        input_schema=request_schema({"brief_id": _BRIEF_ID}, ["brief_id"]),
        output_schema=response_schema({"provenance": {"type": "object"}}, ["provenance"]),
        handler=_handle_work_provenance,
    ),
    ToolSpec(
        name="work_dispatch",
        title="Dispatch brief-backed work",
        description="Dispatch brief-backed work through the shared effect plan. Dry run by default.",
        input_schema=request_schema(
            {"brief_id": _BRIEF_ID, "dry_run": DRY_RUN_PROPERTY}, ["brief_id"]
        ),
        output_schema=response_schema(_EFFECT_RESPONSE, ["applied", "effect_plan"]),
        handler=_handle_work_dispatch,
        mutating=True,
        external_ready=False,
    ),
    ToolSpec(
        name="trace_show",
        title="Show a trace",
        description="Fold every recorded phase row for one trace id into a single record.",
        input_schema=request_schema(
            {"trace_id": {"type": "string", "description": "Trace id to fold."}}, ["trace_id"]
        ),
        output_schema=response_schema({"trace": TRACE_RECORD_SCHEMA}, ["trace"]),
        handler=_handle_trace_show,
    ),
    ToolSpec(
        name="trace_replay_preview",
        title="Preview a trace replay",
        description="Show the effects a recorded trace planned, without reapplying any of them.",
        input_schema=request_schema(
            {"trace_id": {"type": "string", "description": "Trace id to preview."}}, ["trace_id"]
        ),
        output_schema=response_schema(
            {
                "applied": {"type": "boolean", "const": False},
                "blocking_diagnostics": {"type": "array"},
                "operation": nullable_string("Operation the trace recorded."),
                "outcome": nullable_string("planned, applied, or aborted."),
                "planned_effects": {"type": "array"},
                "replay_blockers": {"type": "array", "items": {"type": "object"}},
                "source_trace_id": {"type": "string"},
            },
            ["applied", "planned_effects", "replay_blockers", "source_trace_id"],
        ),
        handler=_handle_trace_replay_preview,
    ),
)

TOOLS_BY_NAME: dict[str, ToolSpec] = {tool.name: tool for tool in TOOLS}

_CROSS_RIG_MUTATORS = sorted(
    name for name in CROSS_RIG_ARRAYS if TOOLS_BY_NAME.get(name) and TOOLS_BY_NAME[name].mutating
)
if _CROSS_RIG_MUTATORS:
    # Plan Global Constraints: "Cross-rig mutations are forbidden until a
    # command-specific batch mode is designed and reviewed." An `all_rigs`
    # mutation would fan a write across every store in one unreviewed call.
    raise RuntimeError(f"cross-rig mutation is forbidden: {_CROSS_RIG_MUTATORS}")

if set(CROSS_RIG_ARRAYS) - set(TOOLS_BY_NAME):
    raise RuntimeError(
        f"CROSS_RIG_ARRAYS names unregistered tools: {sorted(set(CROSS_RIG_ARRAYS) - set(TOOLS_BY_NAME))}"
    )

if FORBIDDEN_TOOL_NAMES & set(TOOLS_BY_NAME):
    # Not an `assert`: `python -O` strips those, and this is the one invariant
    # that must hold at import time on every interpreter.
    raise RuntimeError(
        "a generic command-execution tool was registered: "
        f"{sorted(FORBIDDEN_TOOL_NAMES & set(TOOLS_BY_NAME))}"
    )


# --- server -----------------------------------------------------------------


def _server_diagnostic(code: str, message: str, hint: str, **facts: str) -> Diagnostic:
    return Diagnostic(
        severity=Severity.FATAL,
        code=code,
        message=message,
        hint=hint,
        facts={"implementation_provenance": "mctl MCP server", **facts},
    )


@dataclass
class MctlMcpServer:
    """A JSON-RPC 2.0 MCP server. One tool call, one resolved context, one trace."""

    default_city: Path | None = None
    default_rig: str | None = None
    client_class: str = "external"
    env: Mapping[str, str] = field(default_factory=dict)
    cwd: Path | None = None

    def __post_init__(self) -> None:
        declared = self.env.get(CLIENT_CLASS_ENV) or self.client_class
        # Anything unrecognised falls back to the closed surface rather than
        # the open one; a typo must not arm a client class.
        self.client_class = declared if declared in CLIENT_CLASSES else "external"

    # -- rollout gate --

    @property
    def external_tools_armed(self) -> bool:
        return str(self.env.get(EXTERNAL_TOOLS_ENV, "")).strip() in {"1", "true", "yes"}

    def visible_tools(self) -> tuple[ToolSpec, ...]:
        if self.client_class == "internal":
            return TOOLS
        if not self.external_tools_armed:
            return ()
        return tuple(tool for tool in TOOLS if tool.external_ready)

    def _gate(self, name: str) -> Diagnostic | None:
        if name in {tool.name for tool in self.visible_tools()}:
            return None
        if name not in TOOLS_BY_NAME:
            return _server_diagnostic(
                "MCTL_MCP_UNKNOWN_TOOL",
                f"No MCP tool named {name!r} is registered.",
                "Call tools/list for the available typed tools.",
                requested_tool=name,
            )
        tool = TOOLS_BY_NAME[name]
        reason = (
            "mutating tools stay internal-only until the MCP surface is proven"
            if tool.mutating
            else f"external tools are disabled; set {EXTERNAL_TOOLS_ENV}=1 to arm them"
        )
        return _server_diagnostic(
            "MCTL_MCP_TOOL_DISABLED",
            f"Tool {name!r} is disabled for {self.client_class} clients: {reason}.",
            "Run the server with --client-class internal, or arm external tools deliberately.",
            client_class=self.client_class,
            requested_tool=name,
        )

    # -- transport --

    def handle(self, message: Mapping[str, Any]) -> dict[str, object] | None:
        method = message.get("method")
        message_id = message.get("id")
        if message_id is None:
            return None  # a notification: acknowledged by doing nothing
        params = message.get("params") or {}
        if method == "initialize":
            return self._ok(message_id, self._initialize())
        if method == "ping":
            return self._ok(message_id, {})
        if method == "tools/list":
            return self._ok(message_id, {"tools": [tool.to_wire() for tool in self.visible_tools()]})
        if method == "tools/call":
            return self._call(message_id, params)
        return self._error(
            message_id,
            METHOD_NOT_FOUND,
            f"Method {method!r} is not supported.",
            {"method": method, "supported": ["initialize", "ping", "tools/list", "tools/call"]},
        )

    def _initialize(self) -> dict[str, object]:
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
            "instructions": INSTRUCTIONS,
        }

    def _call(self, message_id: object, params: Mapping[str, Any]) -> dict[str, object]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        gate = self._gate(str(name))
        if gate is not None:
            return self._error(
                message_id,
                METHOD_NOT_FOUND,
                gate.message,
                {
                    "client_class": self.client_class,
                    "diagnostic": gate.to_dict(),
                    "tool": name,
                },
            )
        tool = TOOLS_BY_NAME[str(name)]
        failures = schema_errors(arguments, tool.input_schema)
        if failures:
            diagnostic = _server_diagnostic(
                "MCTL_MCP_INVALID_ARGUMENTS",
                f"Arguments for {name!r} do not satisfy its declared input schema.",
                "Read the tool's inputSchema from tools/list and correct the named fields.",
                requested_tool=str(name),
            )
            return self._error(
                message_id,
                INVALID_PARAMS,
                diagnostic.message,
                {"diagnostic": diagnostic.to_dict(), "schema_errors": failures, "tool": name},
            )
        return self._ok(message_id, self._run(tool, arguments))

    def _run(self, tool: ToolSpec, arguments: Mapping[str, Any]) -> dict[str, object]:
        if tool.scope == CITY_SCOPE:
            return self._run_city_scoped(tool, arguments)
        if tool.cross_rig and bool(arguments.get("all_rigs")):
            return self._run_all_rigs(tool, arguments)
        try:
            ctx = self._context(arguments)
        except ContextError as error:
            return _tool_error([error.diagnostic.to_dict()], None)
        if ctx.city_active is False and not tool.name.startswith("trace_"):
            return _tool_error([city_not_active_diagnostic(ctx).to_dict()], ctx.trace_id)
        try:
            payload = tool.handler(ctx, arguments)
        except (BriefError, MutationError, WorkError, ProvenanceError) as error:
            return _tool_error([error.diagnostic.to_dict()], ctx.trace_id)
        except Exception as error:  # noqa: BLE001 - a crash must not reach the wire raw
            diagnostic = _server_diagnostic(
                "MCTL_MCP_INTERNAL_ERROR",
                f"{tool.name} failed unexpectedly: {type(error).__name__}.",
                "Re-run the equivalent mctl CLI command to reproduce with a full traceback.",
                requested_tool=tool.name,
            )
            return _tool_error([diagnostic.to_dict()], ctx.trace_id)

        payload.setdefault("diagnostics", [])
        payload["trace_id"] = ctx.trace_id
        if tool.artifact_state:
            payload = apply_artifact_trust(ctx, payload, assess_artifact_trust(ctx))
        violations = schema_errors(payload, tool.output_schema)
        if violations:
            # Shipping a payload that violates the schema it advertises is
            # worse than failing: the client trusts the schema, not the code.
            diagnostic = _server_diagnostic(
                "MCTL_MCP_OUTPUT_SCHEMA_VIOLATION",
                f"{tool.name} produced a response that violates its declared output schema.",
                "This is an mctl bug; the declared schema and the handler have drifted.",
                requested_tool=tool.name,
            )
            return _tool_error(
                [diagnostic.to_dict()], ctx.trace_id, extra={"schema_errors": violations}
            )
        return _tool_result(payload)

    def _run_all_rigs(self, tool: ToolSpec, arguments: Mapping[str, Any]) -> dict[str, object]:
        """The explicit cross-rig opt-in, run through the one core fan-out.

        The handler is unchanged and runs once per rig against that rig's own
        resolved context, including its own artifact-trust pass -- so a
        city-wide answer is exactly the per-rig answers, assembled. Nothing
        here re-derives a fact the single-rig path derives differently.
        """
        city = arguments.get("city") or self.default_city
        per_rig = {key: value for key, value in arguments.items() if key not in {"rig", "all_rigs"}}

        def run(ctx: MctlContext) -> dict[str, object]:
            payload = tool.handler(ctx, per_rig)
            payload.setdefault("diagnostics", [])
            if tool.artifact_state:
                payload = apply_artifact_trust(ctx, payload, assess_artifact_trust(ctx))
            return payload

        try:
            scope, outcomes = for_each_rig(
                self.cwd or Path.cwd(),
                city=Path(city) if city else None,
                env=self.env,
                run=run,
            )
        except ContextError as error:
            return _tool_error([error.diagnostic.to_dict()], None)
        payload = merge_outcomes(
            scope,
            outcomes,
            arrays=CROSS_RIG_ARRAYS[tool.name],
            trace_id=new_trace_id(),
            artifact_state=tool.artifact_state,
            validity=tool.name == "briefs_validate",
        )
        violations = schema_errors(payload, tool.output_schema)
        if violations:
            diagnostic = _server_diagnostic(
                "MCTL_MCP_OUTPUT_SCHEMA_VIOLATION",
                f"{tool.name} produced a response that violates its declared output schema.",
                "This is an mctl bug; the declared schema and the handler have drifted.",
                requested_tool=tool.name,
            )
            return _tool_error(
                [diagnostic.to_dict()],
                str(payload.get("trace_id") or ""),
                extra={"schema_errors": violations},
            )
        return _tool_result(payload)

    def _run_city_scoped(self, tool: ToolSpec, arguments: Mapping[str, Any]) -> dict[str, object]:
        """Run a tool that resolves the city registry and no rig.

        Deliberately NOT gated on `city_active`. These tools read `city.toml`
        and touch no bead store, so refusing them when Dolt is down would
        deny a city-wide client the one fact it needs to say *which* rigs it
        could not read.
        """
        city = arguments.get("city") or self.default_city
        try:
            scope = resolve_city(
                self.cwd or Path.cwd(),
                city=Path(city) if city else None,
                require_runtime_city=True,
                env=self.env,
            )
        except ContextError as error:
            return _tool_error([error.diagnostic.to_dict()], None)
        try:
            payload = tool.handler(scope, arguments)
        except Exception as error:  # noqa: BLE001 - a crash must not reach the wire raw
            diagnostic = _server_diagnostic(
                "MCTL_MCP_INTERNAL_ERROR",
                f"{tool.name} failed unexpectedly: {type(error).__name__}.",
                "Re-run the equivalent mctl CLI command to reproduce with a full traceback.",
                requested_tool=tool.name,
            )
            return _tool_error([diagnostic.to_dict()], scope.trace_id)
        payload.setdefault("diagnostics", [])
        payload["trace_id"] = scope.trace_id
        violations = schema_errors(payload, tool.output_schema)
        if violations:
            diagnostic = _server_diagnostic(
                "MCTL_MCP_OUTPUT_SCHEMA_VIOLATION",
                f"{tool.name} produced a response that violates its declared output schema.",
                "This is an mctl bug; the declared schema and the handler have drifted.",
                requested_tool=tool.name,
            )
            return _tool_error(
                [diagnostic.to_dict()], scope.trace_id, extra={"schema_errors": violations}
            )
        return _tool_result(payload)

    def _context(self, arguments: Mapping[str, Any]) -> MctlContext:
        city = arguments.get("city") or self.default_city
        rig = arguments.get("rig") or self.default_rig
        return resolve_context(
            self.cwd or Path.cwd(),
            city=Path(city) if city else None,
            rig=rig,
            require_runtime_city=True,
            require_explicit_runtime=True,
            env=self.env,
        )

    def _ok(self, message_id: object, result: Mapping[str, object]) -> dict[str, object]:
        return {"jsonrpc": "2.0", "id": message_id, "result": dict(result)}

    def _error(
        self, message_id: object, code: int, message: str, data: Mapping[str, object]
    ) -> dict[str, object]:
        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {"code": code, "message": message, "data": dict(data)},
        }

    # -- stdio loop --

    def serve(self, stdin=None, stdout=None) -> int:
        source = stdin if stdin is not None else sys.stdin
        sink = stdout if stdout is not None else sys.stdout
        for line in source:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except ValueError:
                sink.write(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {"code": -32700, "message": "Parse error", "data": {}},
                        }
                    )
                    + "\n"
                )
                sink.flush()
                continue
            response = self.handle(message) if isinstance(message, Mapping) else None
            if response is not None:
                sink.write(json.dumps(response) + "\n")
                sink.flush()
        return 0


def _tool_result(payload: Mapping[str, object]) -> dict[str, object]:
    body = dict(payload)
    return {
        "content": [{"type": "text", "text": json.dumps(body, indent=2, sort_keys=True)}],
        "structuredContent": body,
        "isError": False,
    }


def _tool_error(
    diagnostics: Sequence[Mapping[str, object]],
    trace_id: str | None,
    extra: Mapping[str, object] | None = None,
) -> dict[str, object]:
    body: dict[str, object] = {
        "diagnostics": [dict(diagnostic) for diagnostic in diagnostics],
        "trace_id": trace_id or "",
        **dict(extra or {}),
    }
    return {
        "content": [{"type": "text", "text": json.dumps(body, indent=2, sort_keys=True)}],
        "structuredContent": body,
        "isError": True,
    }


def serve_from_args(args: argparse.Namespace) -> int:
    """Entry point for `mctl mcp serve`, wired from mctl_core.cli."""
    server = MctlMcpServer(
        default_city=Path(args.city) if args.city else None,
        default_rig=args.rig,
        client_class=args.client_class or "external",
        env=os.environ,
    )
    return server.serve()
