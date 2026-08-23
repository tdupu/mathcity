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

from .beads import bd_timeout_within
from .briefs import (
    BriefError,
    BriefFilters,
    BriefListing,
    brief_command_diagnostics,
    brief_options_report,
    doctor_briefs,
    empty_scope_diagnostic,
    list_briefs_report,
    show_brief,
    validate_brief,
    validation_scope,
)
from .city import (
    ALL_RIGS_DEADLINE_SECONDS,
    DEGRADED_SOURCES,
    RigProgress,
    for_each_rig,
    merge_outcomes,
)
from .context import CityScope, ContextError, MctlContext, resolve_city, resolve_context
from .diagnostics import Diagnostic, Severity
from .payloads import (
    brief_filters as _filters,
    briefs_list_payload as _briefs_list_payload,
    diagnostics_payload as _diagnostics,
    replay_blocked as _replay_blocked,
    require_trace as _require_trace,
)
from .commission import CommissionRefused
from .effects import (
    BriefCreateInput,
    IssueBeadCreateInput,
    MutationError,
    apply_effect_plan,
    dry_run_payload,
    plan_adjudication,
    plan_commission_brief,
    plan_create_brief,
    plan_create_issue_bead,
    plan_deferral,
)
from .fields import read_frontmatter
from .fleet import build_fleet_sessions
from .blast_radius import registry_report
from .gates import gates_status
from .molecules import build_molecule, build_molecules
from .health import build_city_health
from .liveness import city_not_active_diagnostic
from .provenance import ProvenanceError
from .redundant_state import artifact_layout
from .schemas import (
    BRIEF_DIAGNOSTICS_SCHEMA,
    BRIEF_DETAIL_SCHEMA,
    BRIEF_OPTION_SCHEMA,
    BRIEF_RECORD_SCHEMA,
    CLAIM_STATE_SCHEMA,
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
from .mayor import boot_state as mayor_boot_state
from .mayor import city_state as mayor_city_state
from .mayor import conservation_report as mayor_conservation_report
from .trace import fold, new_trace_id, read_rows, trace_not_found_diagnostic
from .beads import read_beads
from .decisions import brief_body, dispatchability_refusals
from .work import (
    WorkError,
    _open_child_workflow,
    apply_dispatch_plan,
    dispatch_dry_run_payload,
    plan_dispatch,
    plan_dispatch_event,
    ready_work,
    work_claim,
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
    """Read the `artifact:` frontmatter key the live pile convention uses.

    Delegates to `fields.read_frontmatter()` -- the same parser
    `materialize_plan`/`mctl` use everywhere else -- rather than a second,
    hand-rolled fence scan. The hand-rolled version diverged in two proven
    ways: it silently dropped a key on any line with leading whitespace
    (the canonical parser's key regex is column-anchored, so the hand-rolled
    version was the more permissive one there), and it capped its scan at 64
    lines, so an `artifact:` key past that point read as absent while the
    canonical parser -- which locates the closing fence rather than counting
    lines -- found it correctly. Neither case occurs in the live corpus
    today; this removes the possibility going forward.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return read_frontmatter(text).get("artifact", "").strip("\"'") or None


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
    then reports whether what came back can be believed.

    Trust answers exactly one question -- *can these readings be believed?*
    It is NOT a claim that the brief tree is fully provisioned. Separating
    those two is the whole content of #149.

    An **absent** pile cannot lie. Every artifact under it reads `missing`,
    and they really are missing, so the reading is accurate and may be acted
    on. The pile is created lazily: every brief-producing formula runs
    `mkdir -p "{{artifact_root}}/.pile"` at the moment it writes its first
    brief (`formulas/create-issue-briefed.formula.toml:194` and six siblings),
    and nothing provisions it before then. "No pile directory" is therefore
    the ordinary empty state of a rig that has not yet piled a brief, not a
    defect -- so it no longer untrusts the rig. Measured when #149 was filed:
    6 of 17 rigs were untrusted on this branch alone, and 4 of those 6 held
    zero brief beads.

    A **malformed** pile does lie: its files carry their bead id in an
    `artifact:` frontmatter key rather than in the filename, so the
    `<bead_id>.md` lookup reports `missing` for artifacts sitting right
    there. That is the one condition Q5 documents which makes a reading
    unbelievable, and it remains the one condition that untrusts a rig whose
    root exists.

    A missing *root* stays untrusted and is left to Q5 / issue #2. Unlike the
    pile it also gates the mutation path -- `_require_brief_root` refuses
    with MBRF035 rather than let `mkdir -p` build a shadow tree -- so
    narrowing it is a separate decision with a separate blast radius.

    On MBRF021: it is withheld only while a rig is untrusted. Dropping the
    pile branch lets it surface on rigs whose pile is genuinely
    unmaterialised, where it is TRUE ("this bead has no cache artifact"). It
    stays withheld on the malformed rigs -- which is precisely where Q5
    measured it firing falsely on 66 of 70 briefs.
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
    # No `pile.is_dir()` gate here on purpose (#149). `_frontmatter_lookup_mismatch`
    # already returns None for an absent pile, so an unmaterialised pile falls
    # through to the trusted return below -- absence is the empty state, not a
    # data problem.
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
            "the resolved brief root exists and its pile is addressable: it "
            "either uses the <bead_id>.md filename convention the lookup "
            "assumes, or has not been created yet, which is the empty state "
            "of a rig that has not piled a brief"
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
    handler: Callable[..., dict[str, object]]
    mutating: bool = False
    scope: str = RIG_SCOPE
    #: Whether `handler` takes a third argument, the cross-rig read's
    #: `RigProgress` slot. Declared rather than sniffed from the signature:
    #: a tool that quietly stopped accepting it would silently lose its
    #: partial answers, and that is the failure this whole path is about.
    #: Ignored on the single-rig path, where there is no deadline to miss.
    accepts_progress: bool = False

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


def _handle_orders_status(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    """Every registered order with the outcome of its last run (#156).

    The outcome comes from `<city-root>/.gc/events.jsonl`, not from
    `gc order history` (which logs that an order ran, never how it ended) and
    not from `gc order check` (whose `last_run_outcome` is declared and never
    populated). Without this tool the projection existed in `mctl_core` and no
    MCP caller could reach it.
    """
    from .orders import EVENT_LOG_ONLY, city_reader, orders_status

    # #156 follow-up: the catalog (`gc order list`) measured 89 s in-city and the
    # tool timed out at 120 s when first exercised live. The outcomes half is a
    # local file. Serve what is servable; report the catalog `unreachable`.
    return orders_status(city_reader(ctx.city_root), mode=EVENT_LOG_ONLY)


def _handle_formulas_catalog(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    """Every formula the city knows about (#117 / #156)."""
    from .orders import city_reader, formulas_catalog

    return formulas_catalog(city_reader(ctx.city_root))


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


def _handle_fleet_sessions(scope: CityScope, arguments: Mapping[str, Any]) -> dict[str, object]:
    """Dashboard handoff #112: every configured slot, occupied or empty."""
    report = build_fleet_sessions(scope)
    return {"diagnostics": [diag.to_dict() for diag in report.diagnostics], **report.to_dict()}


def _handle_blast_radius_registry(scope: CityScope, arguments: Mapping[str, Any]) -> dict[str, object]:
    """#110's classification, made reachable.

    `mctl_core/blast_radius.py` shipped with #110 and closed with no tool, no
    consumer, and -- despite the issue's title -- no presence on `EffectPlan`.
    #153's deeper shape: not "the front end was never staffed" but "there is no
    route from the core to a front end at all".

    Reports `registry_present` rather than only the entry list. `load_registry`
    collapses an absent file into an empty registry on purpose (safe for a
    gate: every lookup misses and resolves to UNCLASSIFIED), and that collapse
    is wrong for a report -- rendered, "no operations are classified" and "the
    registry is missing" are both `0`.
    """
    return {"diagnostics": [], **registry_report()}


def _handle_gates_status(scope: CityScope, arguments: Mapping[str, Any]) -> dict[str, object]:
    """Dashboard handoff #119, made reachable.

    `mctl_core/gates.py` has been correct and unreachable since #119 closed:
    the dashboard can only call MCP tools, and there was no `gates_status`
    tool, so no page could ever show a gate. That is #153's deeper shape.

    `gates_readable` is carried through deliberately. An empty `gates` list
    means two different things -- "this city defines no gates" and "the gate
    directory could not be read" -- and flattening them here would make the
    distinction unrecoverable for every screen above.
    """
    # `<city>/mathcity/gates` -- measured, not assumed: that is where the gate
    # TOMLs actually live. `<city>/gates` does not exist, and the pack copies
    # under `gascity-packs/` are sources rather than the registered rig's set.
    #
    # `gates.py` deliberately takes this path explicitly rather than deriving
    # it, "so this function cannot silently compose a path against a working
    # directory that is not what the caller meant". Choosing it is therefore
    # the caller's job, and getting it wrong reports a city with no gates
    # instead of failing -- so a wrong path here is worse than no tool. If the
    # directory is absent, `gates_readable=False` says we could not look; it
    # never claims the city defines none.
    report = gates_status(gates_dir=scope.city_root / "mathcity" / "gates")
    return {"diagnostics": [diag.to_dict() for diag in report.diagnostics], **report.to_dict()}
def _handle_molecules_list(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    """Dashboard handoff #111: every molecule in this rig -- one row per RUN.

    An unreadable store returns no molecules AND a diagnostic. It never returns
    a bare empty list, because an empty census reads as "the city has nothing
    running" rather than "we could not look".
    """
    report = build_molecules(
        ctx.rig_root,
        fixture_path=ctx.beads_fixture,
        with_steps=bool(arguments.get("with_steps")),
    )
    return {"diagnostics": _diagnostics(ctx, report.diagnostics), **report.to_dict()}


def _handle_molecules_show(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    """Dashboard handoff #111: one molecule with its steps."""
    report = build_molecule(
        ctx.rig_root, str(arguments.get("molecule_id") or ""), fixture_path=ctx.beads_fixture
    )
    return {"diagnostics": _diagnostics(ctx, report.diagnostics), **report.to_dict()}


def _handle_city_health(scope: CityScope, arguments: Mapping[str, Any]) -> dict[str, object]:
    """Dashboard handoff #114: three-valued data-plane health and resource pressure."""
    report = build_city_health(scope)
    return {"diagnostics": [diag.to_dict() for diag in report.diagnostics], **report.to_dict()}


def _handle_briefs_list(
    ctx: MctlContext, arguments: Mapping[str, Any], progress: RigProgress | None = None
) -> dict[str, object]:
    """The roster, from both lanes, with either lane's failure named.

    `progress` is the cross-rig read's partial slot. The document lane is
    published into it before the bead read starts, so a rig whose bead store
    outlives the fan-out deadline still reports its manifest rows and stack
    files -- documents on disk that never touched the store that was slow.
    """
    listing = list_briefs_report(
        ctx,
        _filters(arguments),
        bodies=bool(arguments.get("bodies")),
        bead_timeout=None if progress is None else bd_timeout_within(progress.remaining_seconds()),
        on_documents=(
            None
            if progress is None
            else lambda partial: progress.publish(_briefs_list_payload(ctx, partial))
        ),
    )
    payload = _briefs_list_payload(ctx, listing)
    if progress is None and not listing.records:
        payload["diagnostics"] = list(payload["diagnostics"]) + [
            empty_scope_diagnostic(ctx).to_dict()
        ]
    return payload


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
    brief_id = arguments.get("brief_id")
    report = doctor_briefs(ctx, brief_id)
    payload = report.to_dict()
    diagnostics = _diagnostics(ctx, report.diagnostics)
    if brief_id is None and not report.records:
        diagnostics = list(diagnostics) + [empty_scope_diagnostic(ctx).to_dict()]
    payload["diagnostics"] = diagnostics
    return payload


def _handle_briefs_validate(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    scope = validation_scope(ctx, arguments.get("brief_id"), bool(arguments.get("all")))
    report = validate_brief(ctx, scope)
    payload = report.to_dict()
    payload["diagnostics"] = _diagnostics(ctx, report.diagnostics)
    return payload


def _handle_commission_brief(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    """#190: a source bead becomes a commission brief in the pile.

    A COMMISSION AUTHORIZES PLANNING, NOT WORK -- the plan it commissions returns
    as its own brief for separate approval, which keeps the CT4.5 commission
    exemption one hop deep.

    `CommissionRefused` is caught HERE and converted, deliberately. It is an
    exception in the core, which is right for a library: a caller who ignores it
    gets a traceback rather than a silent half-commission. At a tool boundary an
    exception escapes the response envelope, so the caller receives a crash
    instead of a code it can branch on. The refusal carries its own code
    (MCMS_SOURCES_REQUIRED / MCMS_CROSS_STORE_SOURCE) and that code is surfaced
    rather than replaced with a generic one.
    """
    try:
        plan = plan_commission_brief(
            ctx,
            bead_id=str(arguments.get("bead_id") or ""),
            title=str(arguments.get("title") or ""),
            body=str(arguments.get("body") or ""),
            issue_url=arguments.get("issue_url"),
            issue_labels=tuple(arguments.get("issue_labels") or ()),
            bead_rig=arguments.get("bead_rig"),
        )
    except CommissionRefused as refused:
        return {
            "diagnostics": [
                _diagnostic(ctx, Severity.FATAL, refused.code, str(refused)).to_dict()
            ],
            "applied": False,
        }
    return _effect_payload(ctx, plan, _dry_run(arguments))


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


def _diagnostic(
    ctx: MctlContext,
    severity: Severity,
    code: str,
    message: str,
    *,
    suggested_next_command: str | None = None,
) -> Diagnostic:
    facts: dict[str, object] = {
        "city_path": str(ctx.city_root),
        "implementation_provenance": "mctl decisions-to-briefs",
        "rig_name": ctx.rig_id,
        "rig_path": str(ctx.rig_root),
    }
    if suggested_next_command:
        facts["suggested_next_command"] = suggested_next_command
    return Diagnostic(severity, code, message, facts=facts, trace_id=ctx.trace_id)


def _brief_population_beads(ctx: MctlContext) -> tuple:
    """Every bead, not just decisions.

    The source bead is typically a task, so the narrowed decision-only read used
    by the brief surfaces would not find it.
    """
    return read_beads(ctx.rig_root, fixture_path=ctx.beads_fixture)


def _open_child_workflow_id(ctx: MctlContext, beads: tuple, bead_id: str) -> str | None:
    """Delegates to work.py so the two notions of "already being worked" agree."""
    existing = _open_child_workflow(beads, bead_id)
    return None if existing is None else existing.id


def _minted_brief_id(applied: Mapping[str, Any]) -> str | None:
    for entry in applied.get("actual_effects") or applied.get("actual") or ():
        if isinstance(entry, Mapping) and entry.get("kind") == "bead_create":
            target = entry.get("target")
            if isinstance(target, str):
                return target
    return None


def _handle_decisions_to_briefs(
    ctx: MctlContext, arguments: Mapping[str, Any]
) -> dict[str, object]:
    """One already-made decision -> one brief that can actually be dispatched.

    #85: the `decisions-to-briefs` skill writes the pile manifest and the
    `decisions-track/` behind mctl's back because no typed tool does it properly.
    A tool emitting briefs that cannot then be dispatched would relocate that, not
    fix it -- so the bar is `work_status` returning readiness "ready".

    Composes two ALREADY-GATED operations in sequence rather than conflating
    them: create (through `plan_create_brief`) then adjudicate (through
    `plan_adjudication`), each keeping its own preconditions. #173 is what
    conflation looks like -- a brief that made its own source bead and bricked by
    its own approval. Here the source must already exist and be open, and the
    caller names it; this tool never mints a source.

    The two steps cannot be one plan: `apply_effect_plan` substitutes minted ids
    into `bead_relates` but NOT into `bead_updates`, so a close planned alongside
    the create would target the placeholder.
    """
    source_bead_id = str(arguments.get("source_bead_id") or "")
    decision = str(arguments.get("decision") or "")
    beads = _brief_population_beads(ctx)

    refusals = dispatchability_refusals(
        lambda severity, code, message, suggested_next_command=None: _diagnostic(
            ctx, severity, code, message, suggested_next_command=suggested_next_command
        ),
        source_bead_id=source_bead_id,
        beads=beads,
        open_child_workflow_of=lambda bead_id: _open_child_workflow_id(ctx, beads, bead_id),
    )
    if refusals:
        # Refused BEFORE any write, so the caller learns at creation rather than
        # at dispatch. `applied` is false and the reasons are named.
        # `effect_plan` is omitted rather than null: the declared schema types
        # it as a plan, and a null there fails validation with
        # MCTL_MCP_OUTPUT_SCHEMA_VIOLATION -- which would replace the real
        # reasons with a schema complaint, hiding exactly what the caller needs.
        return {
            "applied": False,
            "brief_id": None,
            "diagnostics": _diagnostics(ctx, refusals),
            "trace_id": ctx.trace_id,
        }

    title = str(arguments.get("title") or decision).strip()[:120] or decision
    # #169: a body with no `Gate Evidence` section is refused with MBRF036. The
    # evidence is the checks above that did NOT fire -- each maps to a work.py
    # dispatch blocker -- so the section carries something a gate can use rather
    # than a heading over filler.
    body = brief_body(
        decision,
        source_bead_id=source_bead_id,
        checks_passed=(
            f"source `{source_bead_id}` resolves in this rig (MDTB002 did not fire)",
            "source is not closed, so the brief is dispatchable (MDTB003 did not fire)",
            "source has no active assignee (MDTB004 did not fire)",
            "source has no open child workflow (MDTB005 did not fire)",
        ),
    )
    plan = plan_create_brief(
        ctx,
        BriefCreateInput(
            title=title,
            body=body,
            labels=tuple(arguments.get("labels") or ()),
            requested_by=arguments.get("requested_by"),
            sources=(source_bead_id,),
        ),
    )
    if _dry_run(arguments):
        return _effect_payload(ctx, plan, True)

    created = apply_effect_plan(ctx, plan).to_dict()
    brief_id = _minted_brief_id(created)
    diagnostics = list(created.get("diagnostics") or [])
    if brief_id:
        # The decision is already made; recording it is what makes the brief
        # dispatchable (MWRK010). This goes through the ordinary adjudication
        # gate rather than writing a verdict directly.
        verdict_plan = plan_adjudication(
            ctx,
            brief_id,
            verdict="approve",
            reason=f"decisions-to-briefs: {decision}"[:400],
        )
        applied_verdict = apply_effect_plan(ctx, verdict_plan).to_dict()
        diagnostics.extend(applied_verdict.get("diagnostics") or [])
    return {
        "applied": True,
        "brief_id": brief_id,
        "diagnostics": diagnostics,
        "effect_plan": created.get("effect_plan") or plan.to_dict(),
        "trace_id": ctx.trace_id,
    }


def _handle_briefs_present(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    """CT13.1: presenting briefs must COMPLETE through the MCP, not merely exist.

    Today it is reachable only as a skill. This is the read half of the same
    lifecycle as `decisions_to_briefs`, which is why both land together -- split
    them and one ships without the other.
    """
    listing = list_briefs_report(ctx, _filters(arguments), bodies=bool(arguments.get("bodies")))
    payload = _briefs_list_payload(ctx, listing)
    payload["trace_id"] = ctx.trace_id
    return payload


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


def _handle_create_issue_bead(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    plan = plan_create_issue_bead(
        ctx,
        IssueBeadCreateInput(
            repo=arguments.get("repo") or "",
            issue_number=int(arguments["issue_number"]),
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


def _handle_work_claim(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    claim = work_claim(
        ctx, arguments["bead_id"], window_seconds=arguments.get("window_seconds")
    )
    return {"claim": claim.to_dict(), "diagnostics": _diagnostics(ctx, ())}


def _handle_work_dispatch_event(
    ctx: MctlContext, arguments: Mapping[str, Any]
) -> dict[str, object]:
    plan = plan_dispatch_event(
        ctx,
        arguments["bead_id"],
        dispatch_command=arguments["dispatch_command"],
        formula=arguments.get("formula") or "work-briefed",
        window_seconds=arguments.get("window_seconds"),
    )
    return _effect_payload(ctx, plan, _dry_run(arguments))


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


def _dry_run(arguments: Mapping[str, Any]) -> bool:
    """Absent means dry run. Mutation is opt-in, never opt-out."""
    return bool(arguments.get("dry_run", True))


def _effect_payload(ctx: MctlContext, plan, dry_run: bool) -> dict[str, object]:
    payload = dry_run_payload(plan) if dry_run else apply_effect_plan(ctx, plan).to_dict()
    payload["diagnostics"] = _diagnostics(ctx, ()) + list(payload.get("diagnostics", []))
    return payload


_BRIEF_ID = {"type": "string", "description": "Canonical brief bead id."}

_EFFECT_RESPONSE = {
    "applied": {"type": "boolean", "description": "False for a dry run."},
    "actual_effects": {"type": "array", "description": "Effects that really landed."},
    "effect_plan": EFFECT_PLAN_SCHEMA,
}

def _handle_mayor_city_state(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    """Four-valued city state. `unknown` is a real answer, not a soft `down`.

    The probes are reported individually so a client can see WHICH instrument
    said what. Collapsing them is how three commands gave three different
    answers about the same city in QUIMBY 44.
    """
    state = mayor_city_state(ctx.city_root)
    payload = state.to_dict()
    payload["diagnostics"] = _diagnostics(ctx, state.diagnostics)
    return payload


def _handle_mayor_boot(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    """Mayor boot state: the handoff, factored into queries.

    `prose_residue` names what NO query can answer -- charge, rationale,
    retractions, standing policy. It ships in the payload rather than in a
    docstring so a consumer cannot mistake a partial handoff for a whole one.
    """
    state = mayor_boot_state(ctx)
    payload = state.to_dict()
    payload["diagnostics"] = _diagnostics(ctx, state.diagnostics)
    return payload


def _handle_mayor_conservation(ctx: MctlContext, arguments: Mapping[str, Any]) -> dict[str, object]:
    """Referential-integrity conservation check for one rig's store.

    Enumerates POINTERS, not beads. The lost-bead reclaim chain enumerates
    beads that exist, so a deleted root is outside its domain by construction
    -- arming more of that chain cannot reach it (issue #123).
    """
    report = mayor_conservation_report(ctx)
    payload = report.to_dict()
    payload["diagnostics"] = _diagnostics(ctx, report.diagnostics)
    return payload


_PROBE_SCHEMA: Schema = {
    "type": "object",
    "description": "One instrument's answer, carrying whether it actually looked.",
    "properties": {
        "name": {"type": "string"},
        "ok": {
            "type": ["boolean", "null"],
            "description": "null means the probe did NOT complete. That is not 'false'.",
        },
        "detail": {"type": "string"},
        "value": {"type": ["integer", "null"]},
    },
    "required": ["detail", "name", "ok", "value"],
    "additionalProperties": False,
}


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="orders_status",
        title="Order status with outcomes",
        description=(
            "Every registered order with the outcome of its last run. The outcome is "
            "folded from the city event log; `healthy` is the outcome and never the "
            "recency, because an order can fire punctually and fail every time."
        ),
        input_schema=request_schema(),
        output_schema=response_schema(
            {
                "state": {"type": "string"},
                "total": {"type": ["integer", "null"]},
                "failing": {"type": "integer"},
                "outcome_recorded": {"type": "integer"},
                "ran_at_least_once": {"type": "integer"},
                "orders": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": ["string", "null"]},
                            "trigger": {"type": ["string", "null"]},
                            "enabled": {"type": ["boolean", "null"]},
                            "last_executed": {"type": ["string", "null"]},
                            "last_outcome": {"type": "string"},
                            "healthy": {"type": "boolean"},
                        },
                    },
                },
            },
            ["state", "total", "orders", "failing", "outcome_recorded"],
        ),
        handler=_handle_orders_status,
    ),
    ToolSpec(
        name="formulas_catalog",
        title="Formula catalog",
        description="Every formula the city knows about.",
        input_schema=request_schema(),
        output_schema=response_schema(
            {
                "state": {"type": "string"},
                "total": {"type": ["integer", "null"]},
                "formulas": {"type": "array", "items": {"type": "object"}},
            },
            ["state", "total", "formulas"],
        ),
        handler=_handle_formulas_catalog,
    ),
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
        name="fleet_sessions",
        title="List fleet slots, occupied and empty",
        description=(
            "Every configured agent slot for this city, joined against the live session "
            "list: occupied slots carry the session's state, template, and idle time; "
            "empty slots are rows too, so absence renders the same as presence rather than "
            "shrinking the roster. `limit_state` is always 'unknown' -- no quota/usage-window "
            "recording exists yet; see the MCTL_FLEET_LIMIT_STATE_UNRECORDED diagnostic."
        ),
        input_schema=request_schema(),
        output_schema=response_schema(
            {
                "slots": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "qualified_name": {"type": "string"},
                            "template": nullable_string("Agent template name."),
                            "occupied": {"type": "boolean"},
                            "state": nullable_string("Session state, null when the slot is empty."),
                            "holds": nullable_string("Session id this slot currently carries."),
                            "model": nullable_string("Model/provider, when recorded."),
                            "account": nullable_string("Not recorded today; always null."),
                            "limit_state": {
                                "type": "string",
                                "description": "Always 'unknown' -- see tool description.",
                            },
                            "idle_for_seconds": {"type": ["number", "null"]},
                            "idle_reason": nullable_string(
                                "Why idle_for_seconds is null, when it is."
                            ),
                        },
                        "required": [
                            "qualified_name",
                            "template",
                            "occupied",
                            "state",
                            "holds",
                            "model",
                            "account",
                            "limit_state",
                            "idle_for_seconds",
                            "idle_reason",
                        ],
                        "additionalProperties": False,
                    },
                },
            },
            ["slots"],
        ),
        handler=_handle_fleet_sessions,
        scope=CITY_SCOPE,
    ),
    ToolSpec(
        name="blast_radius_registry",
        title="Which operations are classified for blast radius, and which await an emitter",
        description=(
            "The operation -> control-safety registry behind #110. `registry_present` is "
            "the load-bearing field: an empty `operations` list with `registry_present: "
            "true` means this city classifies no operations, and the same empty list with "
            "`registry_present: false` means the registry file was not found. "
            "`load_registry` collapses those two on purpose -- safe for a gate, since every "
            "lookup then misses and resolves to UNCLASSIFIED -- and this surface un-collapses "
            "them, because a reader seeing only `0` would conclude the city has nothing "
            "dangerous rather than that we failed to look. "
            "`awaiting_emitter` lists entries marked aspirational: classified, with nothing "
            "emitting them yet. That is a fact about coverage, not a warning -- reporting "
            "them as orphans would be a warning about the wrong thing."
        ),
        input_schema=request_schema(),
        output_schema=response_schema(
            {
                "registry_present": {"type": "boolean"},
                "registry_path": {"type": "string"},
                "operations": {"type": "array", "items": {"type": "object"}},
                "awaiting_emitter": {"type": "array", "items": {"type": "string"}},
            },
            ["registry_present", "operations", "awaiting_emitter"],
        ),
        handler=_handle_blast_radius_registry,
        scope=CITY_SCOPE,
    ),
    ToolSpec(
        name="gates_status",
        title="The city's gate definitions, and whether they could be read",
        description=(
            "Gate definitions read from `<city>/mathcity/gates/*.toml`. "
            "`gates_readable` is the load-bearing field: an empty `gates` list with "
            "`gates_readable: true` means this city defines no gates, and the same "
            "empty list with `gates_readable: false` means the directory could not be "
            "read. Those are different facts and this tool never collapses them -- a "
            "reader that sees only the empty list cannot tell a city with no gates "
            "from a city whose gates are unreadable. "
            "Statistics are deliberately absent rather than zero: no evaluation store "
            "exists, so pass/fail counts are Unknown and say so (#119)."
        ),
        input_schema=request_schema(),
        output_schema=response_schema(
            {
                "gates": {"type": "array", "items": {"type": "object"}},
                "gates_readable": {"type": "boolean"},
            },
            ["gates", "gates_readable"],
        ),
        handler=_handle_gates_status,
        scope=CITY_SCOPE,
    ),
    ToolSpec(
        name="city_health",
        title="City-wide data-plane health and resource pressure",
        description=(
            "Four-valued data-plane health (`healthy` / `reachable_quarantined` / `unknown` / "
            "`unreachable`) read from `gc dolt health`, never collapsed to a boolean -- a "
            "reachable-but-quarantined database is a real, distinct state, not a degraded "
            "'healthy'. Resource pressure covers file descriptors against the OS-level "
            "`kern.maxfilesperproc` ceiling (not `ulimit -n`, which is not the binding "
            "constraint) and per-rig Dolt directory size. `fds_trend` is always 'unknown': no "
            "time-series sample store exists yet."
        ),
        input_schema=request_schema(),
        output_schema=response_schema(
            {
                "data_plane": {
                    "type": "string",
                    "enum": ["healthy", "reachable_quarantined", "unreachable", "unknown"],
                },
                "probe_results": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "outcome": {
                                "type": "string",
                                "enum": ["succeeded", "timed_out", "refused"],
                            },
                            "timeout_seconds": {"type": ["number", "null"]},
                            "latency_ms": {"type": ["number", "null"]},
                            "detail": {"type": "string"},
                        },
                        "required": ["name", "outcome", "timeout_seconds", "latency_ms", "detail"],
                        "additionalProperties": False,
                    },
                },
                "resources": {
                    "type": "object",
                    "properties": {
                        "fds_used": {"type": ["integer", "null"]},
                        "fds_limit": {"type": ["integer", "null"]},
                        "fds_trend": {"type": "string"},
                        "disk_per_rig": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "rig_id": {"type": "string"},
                                    "bytes_used": {"type": ["integer", "null"]},
                                    "reason": nullable_string("Why bytes_used is null, when it is."),
                                },
                                "required": ["rig_id", "bytes_used", "reason"],
                                "additionalProperties": False,
                            },
                        },
                        "flood_conditions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "resource": {"type": "string"},
                                    "detail": {"type": "string"},
                                    "growth": {"type": "string"},
                                    "since": nullable_string("When this condition started, if known."),
                                },
                                "required": ["resource", "detail", "growth", "since"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["fds_used", "fds_limit", "fds_trend", "disk_per_rig", "flood_conditions"],
                    "additionalProperties": False,
                },
                "per_rig": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rig_id": {"type": "string"},
                            "state": {"type": "string", "enum": ["healthy", "degraded", "unreachable", "unknown"]},  # `unknown` (#159): the probe established nothing about this rig
                            "reason": {"type": "string"},
                        },
                        "required": ["rig_id", "state", "reason"],
                        "additionalProperties": False,
                    },
                },
            },
            ["data_plane", "probe_results", "resources", "per_rig"],
        ),
        handler=_handle_city_health,
        scope=CITY_SCOPE,
    ),
    ToolSpec(
        name="molecules_list",
        title="List molecules",
        description=(
            "Every molecule in this rig -- one row per RUN, not per work item. A molecule "
            "is a workflow root bead (`gc.kind == \"workflow\"`, an EXACT match: every step "
            "kind also startswith `workflow`). Its steps are the beads that point AT it via "
            "`gc.root_bead_id`; the root does NOT carry that key, and the dashboard handoff "
            "says otherwise -- building the edge from that sentence reverses it. "
            "Re-dispatching one source bead mints a NEW root, so four attempts are four "
            "molecules, which is what makes repeated attempts visible. "
            "NO `state` FIELD: advancing/stalled/stranded need the evidence chain (#115), "
            "which records nothing today, and a row showing a state it cannot derive would "
            "be worse than one that omits it. An unreadable store yields a diagnostic and "
            "no rows -- never a bare empty list."
        ),
        input_schema=request_schema(
            {
                "with_steps": {
                    "type": "boolean",
                    "default": False,
                    "description": "Attach each molecule's steps. Off by default: a roster read is not a content read.",
                }
            }
        ),
        output_schema=response_schema(
            {"molecules": {"type": "array", "items": {"type": "object"}}}, ["molecules"]
        ),
        handler=_handle_molecules_list,
    ),
    ToolSpec(
        name="molecules_show",
        title="Show one molecule",
        description=(
            "One molecule with its steps, by root bead id. A missing id and an id that "
            "exists but is not a molecule root are DIFFERENT diagnostics: 'no such molecule' "
            "is an answer, 'that is a step, not a run' is a different answer, and neither is "
            "an empty result."
        ),
        input_schema=request_schema(
            {"molecule_id": {"type": "string", "description": "The molecule's ROOT bead id."}},
            ["molecule_id"],
        ),
        output_schema=response_schema(
            {"molecules": {"type": "array", "items": {"type": "object"}}}, ["molecules"]
        ),
        handler=_handle_molecules_show,
    ),
    ToolSpec(
        name="briefs_list",
        title="List briefs",
        description=(
            "List briefs from all three stores: canonical decision brief beads, markdown "
            "briefs in `.beads/briefs/stack/`, and decisions-track manifest rows that "
            "neither represents. Every record names its `source` (`bead`, `stack_file` or "
            "`manifest`); only a bead is an attested decision record. A stack file and a "
            "manifest row describing one brief produce ONE record and the row is named in "
            "`also_recorded_in` -- no document is suppressed without an emitted record "
            "that names it. `unreadable` means no body file exists, and nothing else; a "
            "brief with a body and no verdict is an ordinary `pending` one. `fields` "
            "carries EVERY key the record's stores declare -- an open set, not a fixed "
            "list, so a producer adding a frontmatter key needs no core change -- each "
            "naming the store it was read from, with `conflict` set where two stores "
            "disagree. Bodies are off by default -- pass `bodies=true`, "
            "or read one brief through `briefs_show`, which always carries it; a record "
            "whose body was left out says so in `body_elided` and is never truncated. "
            "Optionally filtered by status or label."
        ),
        input_schema=request_schema(
            {
                "status": nullable_string("Filter by raw bead or decision status."),
                "label": nullable_string("Filter by brief label."),
                "bodies": {
                    "type": "boolean",
                    "default": False,
                    "description": (
                        "Attach each document brief's body and parsed sections. Off by "
                        "default: with every body attached this read measures 5.17 MB "
                        "city-wide, which makes a roster read a content read."
                    ),
                },
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
        accepts_progress=True,
    ),
    ToolSpec(
        name="briefs_show",
        title="Show one brief",
        description=(
            "Show one brief's canonical bead state, its body, that body's parsed sections, "
            "redundant artifacts, and policy refs. `body` is the verbatim canonical text and "
            "stays authoritative: `sections` is a convenience over it, never a replacement. "
            "Document briefs -- `source` `stack_file` or `manifest` -- are served here too, "
            "which is what makes the roster's body elision safe: they reach no other detail "
            "surface, because `options`, `doctor` and `validate` all act on a bead."
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
        name="commission_brief",
        title="Commission a brief from a source bead",
        description=(
            "Turn an existing source bead into a COMMISSION brief in the pile. A commission "
            "authorizes PLANNING ONLY -- the dispatch plan it produces returns as its own "
            "brief for separate approval, which is what keeps the CT4.5 commission exemption "
            "one hop deep. "
            "`bead_id` is required and must live in the SAME rig store as the brief: a "
            "cross-store source fails at creation with 'no issue found matching', so it is "
            "refused here first (MCMS_CROSS_STORE_SOURCE). A missing source is refused as "
            "MCMS_SOURCES_REQUIRED, because a brief without one warns at creation and is "
            "FATAL at dispatch (MWRK011) -- permanently uncommissionable. "
            "Tracker provenance rides in METADATA (`gh.issue`, `gh.repo`, `gh.labels`), never "
            "in bd labels: GitHub labels are namespaced and bd rejects slashes (MBRF033). An "
            "issue with no labels OMITS `gh.labels` rather than writing an empty string. "
            "The brief lands in the PILE and enters the shared lifecycle (B2.10); it never "
            "writes a stack row, because the stack is brief-shuffle's to write."
        ),
        input_schema=request_schema(
            {
                "bead_id": {"type": "string", "description": "Source bead this brief decides on."},
                "title": nullable_string("What is being decided."),
                "body": nullable_string("Brief body markdown."),
                "issue_url": nullable_string("Originating GitHub issue, if any."),
                "issue_labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The issue's labels, carried verbatim into gh.labels metadata.",
                },
                "bead_rig": nullable_string(
                    "Rig whose store holds the source bead. Omit when it is this rig; "
                    "supplying a different one is refused rather than attempted."
                ),
                "dry_run": DRY_RUN_PROPERTY,
            },
            ["bead_id"],
        ),
        output_schema=response_schema({"applied": {"type": "boolean"}}, ["applied"]),
        handler=_handle_commission_brief,
        mutating=True,
        # Every mutating tool in this surface is external_ready=False, and the
        # snapshot test enforces it. A tool that mints a bead must not be
        # reachable by an external client; the default (True) would have made
        # it so, and the test caught that rather than my reading it.
        external_ready=False,
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
        name="decisions_to_briefs",
        title="File an already-made decision as a dispatchable brief",
        description=(
            "Turn one already-made decision into a brief that work_dispatch can "
            "actually act on. Refuses before writing if the named source bead "
            "would make the brief undispatchable. Dry run by default."
        ),
        input_schema=request_schema(
            {
                "decision": {"type": "string", "description": "The decision, as made."},
                "source_bead_id": {
                    "type": "string",
                    "description": "The OPEN bead this decision is about. Never minted here.",
                },
                "title": nullable_string("Brief title; defaults to the decision text."),
                "labels": dict(STRING_ARRAY, description="Brief labels."),
                "requested_by": nullable_string("Who asked for the brief."),
                "dry_run": DRY_RUN_PROPERTY,
            },
            ["decision", "source_bead_id"],
        ),
        output_schema=response_schema(
            _EFFECT_RESPONSE, ["applied"], artifact_state=True
        ),
        handler=_handle_decisions_to_briefs,
        mutating=True,
        external_ready=False,
        artifact_state=True,
    ),
    ToolSpec(
        name="briefs_present",
        title="Present briefs for adjudication",
        description=(
            "The read half of the brief lifecycle: what is waiting for a human "
            "verdict. CT13.1 requires this to complete through the MCP."
        ),
        input_schema=request_schema(
            {
                "status": nullable_string("Filter by bead or decision status."),
                "label": nullable_string("Filter by label."),
                "bodies": {"type": "boolean", "description": "Include brief bodies."},
            },
            [],
        ),
        output_schema=response_schema(
            {"briefs": {"type": "array"}}, ["briefs"], artifact_state=True
        ),
        handler=_handle_briefs_present,
        mutating=False,
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
        name="create_issue_bead",
        title="Mint an open bead mirroring a GitHub issue",
        description=(
            "Mint an OPEN bead from an open GitHub issue, so a brief can carry it as a "
            "legal source dependency (#170, MWRK011). Idempotent: a second call for the "
            "same issue returns the existing mirror bead rather than minting another. "
            "Dry run by default."
        ),
        input_schema=request_schema(
            {
                "repo": {"type": "string", "description": "owner/name, e.g. tdupu/mathcity."},
                "issue_number": {"type": "integer", "description": "The GitHub issue number."},
                "dry_run": DRY_RUN_PROPERTY,
            },
            ["repo", "issue_number"],
        ),
        output_schema=response_schema(
            _EFFECT_RESPONSE, ["applied", "effect_plan"], artifact_state=True
        ),
        handler=_handle_create_issue_bead,
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
        name="work_claim",
        title="Show who holds a bead",
        description=(
            "Report one bead's claim state -- assignee, status, and the four "
            "`dispatch-provenance.v1` classification fields derived from it "
            "(`verified_assignee`, `assignee_state`, `classification_hint`, "
            "`fingerprint`). Takes a BEAD id, not a brief id: the caller this "
            "exists for commissioned work that has no brief yet. It replaces "
            "`bd show <id> | grep -i assignee`, which answered 'some rendered "
            "line mentioned assignee' and could not tell an unclaimed bead "
            "from a missing one. `window_seconds` names how long the caller "
            "already waited and only labels the observation -- nothing here "
            "sleeps or polls."
        ),
        input_schema=request_schema(
            {
                "bead_id": {"type": "string", "description": "Canonical bead id to read."},
                "window_seconds": {
                    "type": ["integer", "null"],
                    "description": (
                        "Seconds the caller waited before reading. Reported as "
                        "`empty_after_<n>s`; omit when no wait was involved."
                    ),
                },
            },
            ["bead_id"],
        ),
        output_schema=response_schema({"claim": CLAIM_STATE_SCHEMA}, ["claim"]),
        handler=_handle_work_claim,
    ),
    ToolSpec(
        name="work_dispatch_event",
        title="Record a dispatch provenance event",
        description=(
            "Create the `dispatch-provenance.v1` event bead for a commission "
            "sling and attach it to its source bead, as ONE operation -- an "
            "event that is created but not attached is invisible to the "
            "lost-bead filter in exactly the way an unwritten one is. The "
            "classification fields come from a canonical claim read, not from "
            "the caller. The edge is written with `bd dep relate` and then "
            "PROVEN from the store: `bd dep add` exits 0 on an edge whose "
            "target it cannot resolve, leaving a row `bd show` counts and "
            "hides, and `bd dep relate` resolves ids fuzzily, so a clean exit "
            "does not say which beads were linked. An unresolvable source "
            "bead is refused as a precondition, before anything is created. "
            "Dry run by default."
        ),
        input_schema=request_schema(
            {
                "bead_id": {
                    "type": "string",
                    "description": "Source bead the sling commissioned work on.",
                },
                "dispatch_command": {
                    "type": "string",
                    "description": "The sling command this event records, verbatim.",
                },
                "formula": nullable_string("Formula the sling named; defaults to work-briefed."),
                "window_seconds": {
                    "type": ["integer", "null"],
                    "description": "Seconds waited before reading the claim.",
                },
                "dry_run": DRY_RUN_PROPERTY,
            },
            ["bead_id", "dispatch_command"],
        ),
        output_schema=response_schema(_EFFECT_RESPONSE, ["applied", "effect_plan"]),
        handler=_handle_work_dispatch_event,
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
    ToolSpec(
        name="mayor_city_state",
        title="Mayor: city state",
        description=(
            "Four-valued city state (up/idle/down/unknown) assembled from probes that each "
            "report whether they completed. 'unknown' means a load-bearing probe did not "
            "answer and MUST NOT be read as 'down'."
        ),
        input_schema=request_schema({}, []),
        output_schema=response_schema(
            {
                "state": {
                    "type": "string",
                    "enum": ["up", "idle", "down", "unknown"],
                    "description": "unknown outranks the rest; a partial answer is not a whole one.",
                },
                "pane_count": {"type": ["integer", "null"]},
                "probes": {"type": "array", "items": _PROBE_SCHEMA},
                "active_rigs": STRING_ARRAY,
                "suspended_rigs": dict(
                    STRING_ARRAY,
                    description="The reconciler skips these rigs' agents; their ready work never dispatches.",
                ),
            },
            ["active_rigs", "pane_count", "probes", "state", "suspended_rigs"],
        ),
        handler=_handle_mayor_city_state,
    ),
    ToolSpec(
        name="mayor_boot",
        title="Mayor: boot state",
        description=(
            "Everything a Mayor reboot can learn by query -- city state, conservation, open "
            "and blocked counts, the handoff chain -- plus `prose_residue`, the facts no "
            "query can answer. Negative counts mean UNMEASURED, never zero."
        ),
        input_schema=request_schema({}, []),
        output_schema=response_schema(
            {
                "city": {"type": "object"},
                "conservation": {"type": "object"},
                "open_beads": {"type": "integer", "description": "-1 when the store was unreadable."},
                "blocked_beads": {"type": "integer", "description": "-1 when the store was unreadable."},
                "recent_handoffs": {"type": "array", "items": {"type": "object"}},
                "escalations_queryable": {"type": "boolean"},
                "prose_residue": dict(STRING_ARRAY, description="Facts no query answers. Shrinks as gaps close."),
            },
            [
                "blocked_beads",
                "city",
                "conservation",
                "escalations_queryable",
                "open_beads",
                "prose_residue",
                "recent_handoffs",
            ],
        ),
        handler=_handle_mayor_boot,
    ),
    ToolSpec(
        name="mayor_conservation",
        title="Mayor: conservation check",
        description=(
            "Referential-integrity check for unaccounted exits: live beads whose "
            "gc.root_bead_id resolves to no bead. Enumerates pointers, not beads, so it "
            "detects the deleted-root class the idleness-based lost-bead filter cannot. "
            "DO NOT prune the pointers it reports -- they are the only surviving evidence "
            "those workflows existed."
        ),
        input_schema=request_schema({}, []),
        output_schema=response_schema(
            {
                "clean": {
                    "type": ["boolean", "null"],
                    "description": "null when the store was unreadable. Unreadable is UNKNOWN, not clean.",
                },
                "readable": {"type": "boolean"},
                "molecules": {"type": "integer"},
                "rig": {
                    "type": "string",
                    "description": (
                        "#150 G1: this report is always ONE rig's store, never the "
                        "city -- empty string only when built without an "
                        "MctlContext to read a rig from."
                    ),
                },
                "roots_resolving": {"type": "integer"},
                "roots_dangling": {"type": "integer"},
                "orphaned_members": {"type": "integer"},
                "dangling_root_ids": STRING_ARRAY,
                "window_earliest": nullable_string("Earliest created_at among orphaned members."),
                "window_latest": nullable_string("Latest created_at among orphaned members."),
                "store_refs": {
                    "type": "object",
                    "description": "gc.root_store_ref counts for orphaned members; shows whether they are cross-store or simply gone.",
                },
            },
            [
                "clean",
                "readable",
                "dangling_root_ids",
                "molecules",
                "orphaned_members",
                "rig",
                "roots_dangling",
                "roots_resolving",
            ],
        ),
        handler=_handle_mayor_conservation,
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
    #: Wall-clock budget for one cross-rig fan-out. Overridable so a test can
    #: reach the deadline path in under a second instead of twenty-five.
    all_rigs_deadline: float = ALL_RIGS_DEADLINE_SECONDS

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

        def finish(ctx: MctlContext, payload: dict[str, object]) -> dict[str, object]:
            payload.setdefault("diagnostics", [])
            if tool.artifact_state:
                payload = apply_artifact_trust(ctx, payload, assess_artifact_trust(ctx))
            return payload

        def run(ctx: MctlContext, progress: RigProgress) -> dict[str, object]:
            if not tool.accepts_progress:
                return finish(ctx, tool.handler(ctx, per_rig))
            # The handler publishes its own partial answers, and they go
            # through the same `finish` as the whole one -- a partial payload
            # that skipped the artifact-trust pass would be the one payload on
            # this surface carrying artifact state with no verdict beside it.
            relay = progress.relaying(lambda partial: finish(ctx, partial))
            return finish(ctx, tool.handler(ctx, per_rig, relay))

        try:
            scope, outcomes = for_each_rig(
                self.cwd or Path.cwd(),
                city=Path(city) if city else None,
                env=self.env,
                run=run,
                deadline=self.all_rigs_deadline,
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
