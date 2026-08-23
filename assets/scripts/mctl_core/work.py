"""Work readiness, provenance, and dispatch controls for mctl."""
from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Mapping

from .beads import BD_LIST_ARGS, Bead, BeadCreate, BeadReadError, BeadRelate, read_beads, BeadUpdate
from .briefs import BriefError, DoctorReport, doctor_briefs
from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .effects import EffectPlan, JsonlWrite
from .events import append_jsonl
from .liveness import probe_control_plane
from .verdicts import brief_population, is_brief_bead, read_verdict
from .trace import append_applied, append_planned
from .provenance import (
    DispatchProvenance,
    ProvenanceError,
    read_dispatch_provenance,
    write_dispatch_provenance,
)


@dataclass(frozen=True)
class WorkItem:
    brief_id: str
    bead_id: str
    title: str
    readiness: str
    blockers: tuple[Diagnostic, ...]
    provenance: DispatchProvenance | None

    def to_dict(self) -> dict[str, object]:
        return {
            "bead_id": self.bead_id,
            "blockers": [blocker.to_dict() for blocker in self.blockers],
            "brief_id": self.brief_id,
            "provenance": self.provenance.to_dict() if self.provenance is not None else None,
            "readiness": self.readiness,
            "title": self.title,
        }


@dataclass(frozen=True)
class WorkDispatchPlan:
    trace_id: str
    target_brief_id: str
    bead_id: str
    formula_invocation: Mapping[str, object]
    provenance: Mapping[str, object]
    event_path: Path
    trace_path: Path

    @property
    def operation(self) -> str:
        return "work.dispatch"

    def to_dict(self) -> dict[str, object]:
        return {
            "bead_id": self.bead_id,
            "event_writes": [{"kind": "event_write", "path": str(self.event_path)}],
            "formula_invocation": dict(self.formula_invocation),
            "operation": self.operation,
            "provenance": dict(self.provenance),
            "target_brief_id": self.target_brief_id,
            "trace_id": self.trace_id,
            "trace_writes": [{"kind": "trace_write", "path": str(self.trace_path)}],
        }


#: The command never started -- `OSError` from spawn. Nothing ran, so nothing
#: landed, and a retry is safe.
DISPATCH_UNRUNNABLE_CODE = "MWRK_DISPATCH_COMMAND_FAILED"

#: The command RAN and we stopped waiting -- `subprocess.TimeoutExpired`. Whether
#: its work landed is unknowable from here, so the honest answer is `unknown`.
DISPATCH_TIMEOUT_CODE = "MWRK_DISPATCH_TIMEOUT_UNKNOWN"


@dataclass(frozen=True)
class DispatchFailureVerdict:
    """What a failed dispatch subprocess lets us claim about the world (#184).

    `applied` is deliberately three-valued. `False` means the dispatch provably
    did not happen; `None` means we cannot tell. Collapsing the second into the
    first is a claim about the world derived from an observation about our
    patience -- and callers act on it, so it is unsafe rather than merely
    uninformative.
    """

    code: str
    applied: bool | None
    may_have_dispatched: bool
    message: str
    suggested_next_command: str | None = None


def classify_dispatch_subprocess_error(error: BaseException) -> DispatchFailureVerdict:
    """Separate `did-not-run` from `ran-and-we-stopped-waiting`.

    These were caught in one handler and reported with one message, *"the
    dispatch command could not be run, so no dispatch was recorded."* For a
    timeout both clauses are wrong: it ran, and whether a dispatch was recorded
    is exactly what we do not know.

    Measured instance: trace `515ba38a` timed out while the city event log shows
    `execution.work_associated` 1 ms in and four beads created 35 s in. The
    dispatch was recorded; the tool reported it was not.
    """
    if isinstance(error, subprocess.TimeoutExpired):
        return DispatchFailureVerdict(
            code=DISPATCH_TIMEOUT_CODE,
            applied=None,
            may_have_dispatched=True,
            message=(
                "The dispatch command ran but did not finish before the timeout, so "
                "whether a dispatch was recorded is UNKNOWN. It may have completed."
            ),
            suggested_next_command=(
                "check whether the dispatch landed before you retry -- a retry after a "
                "timeout can dispatch a second time"
            ),
        )
    return DispatchFailureVerdict(
        code=DISPATCH_UNRUNNABLE_CODE,
        applied=False,
        may_have_dispatched=False,
        message="The dispatch command could not be run, so no dispatch was recorded.",
    )


class WorkError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


#: The `dispatch-provenance.v1` classification a claim read implies. These are
#: the exact strings `skills/work/SKILL.md` writes into a path-B provenance
#: event, derived here so the event and the observation cannot disagree: they
#: were previously typed out by hand next to a `bd show | grep -i assignee`
#: that nobody could re-derive them from.
CLAIM_HEALTHY = "healthy"
CLAIM_IMMEDIATE_STRAND = "immediate_strand"
FINGERPRINT_CLAIMED = "verified_sling_claimed"
FINGERPRINT_UNCLAIMED = "empty_assignee_after_verified_sling"


@dataclass(frozen=True)
class ClaimState:
    """Who holds one bead, read from the canonical store rather than grepped.

    This replaces `bd show <id> | grep -i assignee`. The grep is not merely
    ugly: it reads a human-readable rendering, so it answers "some line
    mentioned the word assignee" and cannot tell an empty assignee from a
    missing bead from a field bd renamed. Every consumer of that line then
    re-derived the same four provenance strings by hand.

    `window_seconds` is the verification window the caller waited, and only
    ever names the observation: `assignee_state` reports `empty_after_60s`
    when a caller waited 60 seconds, and plain `empty` when it waited none.
    Nothing here sleeps or polls -- the wait belongs to the caller, and a
    reader that slept would make a cheap read expensive.
    """

    bead_id: str
    title: str
    status: str
    assignee: str | None
    window_seconds: int | None
    observed_at: str

    @property
    def verified_assignee(self) -> bool:
        return bool(self.assignee and self.assignee.strip())

    @property
    def assignee_state(self) -> str:
        if self.verified_assignee:
            return "non_empty"
        return "empty" if self.window_seconds is None else f"empty_after_{self.window_seconds}s"

    @property
    def classification_hint(self) -> str:
        return CLAIM_HEALTHY if self.verified_assignee else CLAIM_IMMEDIATE_STRAND

    @property
    def fingerprint(self) -> str:
        return FINGERPRINT_CLAIMED if self.verified_assignee else FINGERPRINT_UNCLAIMED

    def to_dict(self) -> dict[str, object]:
        return {
            "assignee": self.assignee,
            "assignee_state": self.assignee_state,
            "bead_id": self.bead_id,
            "classification_hint": self.classification_hint,
            "fingerprint": self.fingerprint,
            "observed_at": self.observed_at,
            "status": self.status,
            "title": self.title,
            "verified_assignee": self.verified_assignee,
            "window_seconds": self.window_seconds,
        }


def work_claim(ctx: MctlContext, bead_id: str, *, window_seconds: int | None = None) -> ClaimState:
    """Read one bead's claim state from the canonical store.

    Takes a bead id, not a brief id: the call site this exists for is path B,
    where a `gc sling` commissioned work that has no brief yet, so there is no
    brief to ask about.
    """
    bead = _require_bead(ctx, bead_id)
    return ClaimState(
        bead_id=bead.id,
        title=bead.title,
        status=bead.status,
        assignee=bead.assignee,
        window_seconds=window_seconds,
        observed_at=_now(),
    )


def _require_bead(ctx: MctlContext, bead_id: str) -> Bead:
    bead = {bead.id: bead for bead in _beads(ctx)}.get(bead_id)
    if bead is None:
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MWRK_BEAD_NOT_FOUND",
                f"No bead named {bead_id!r} exists in this rig's canonical store.",
                bead_id=bead_id,
                data_location=_canonical_bead_location(ctx),
                suggested_next_command="mctl context rigs --json",
            )
        )
    return bead


def ready_work(ctx: MctlContext) -> tuple[WorkItem, ...]:
    beads = _beads(ctx)
    doctor = _doctor_report(ctx, None, beads)
    return tuple(
        item
        for item in (
            _work_item(ctx, bead.id, beads=beads, doctor=doctor)
            for bead in brief_population(beads)
        )
        if item.readiness == "ready"
    )


def work_status(ctx: MctlContext, brief_id: str) -> WorkItem:
    return _work_item(ctx, brief_id)


def work_provenance(ctx: MctlContext, brief_id: str) -> DispatchProvenance:
    item = _work_item(ctx, brief_id, include_provenance_errors=False)
    try:
        return read_dispatch_provenance(ctx, item.bead_id, required=True)
    except ProvenanceError as error:
        raise WorkError(error.diagnostic) from error


@dataclass(frozen=True)
class WorkRoutePlan:
    """A planned write of `gc.routed_to` onto one step bead (#182)."""

    trace_id: str
    bead_id: str
    route: str
    previous_route: str
    bead_update: BeadUpdate

    def to_dict(self) -> dict[str, object]:
        return {
            "bead_id": self.bead_id,
            "bead_update": self.bead_update.to_dict(),
            "previous_route": self.previous_route,
            "route": self.route,
            "trace_id": self.trace_id,
        }


def plan_route_to(
    ctx: MctlContext, step: Bead, route: str, *, reroute: bool = False
) -> WorkRoutePlan:
    """Plan the write that makes a step visible to a pool.

    TAYLOR NAMED THIS VERB, and the name is the correction. It is not `assign`:
    what a step carries is `gc.routed_to`, a POOL, stamped at cook time by
    `ApplyGraphRouteBinding`. `assign` would have written an assignee -- a
    session bead -- which is a different target and duplicates a write cook
    already performs.

    WHY IT IS NOT REDUNDANT, measured across hecke's 746 step beads: 598 carry
    `gc.routed_to` and 148 carry NONE. An unrouted step is invisible to every
    pool query -- `bd ready --metadata-field gc.routed_to=<pool> --unassigned`
    cannot return it -- so no worker can claim it and it never becomes work.

    WHAT THIS DOES NOT DO. It does not assign, claim, or spawn. A routed step
    with no live session still waits. Routing is necessary and not sufficient,
    and this docstring says so because the next reader will otherwise assume
    the verb makes work execute.

    A REROUTE IS REFUSED BY DEFAULT. 598 steps already carry a route; silently
    overwriting one moves work away from a pool that may be mid-claim. The
    caller opts in, and the plan records what it displaced.
    """
    if not route.strip():
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MWRK015",
                "A route target is required; an empty route matches no pool query.",
                bead_id=step.id,
                suggested_next_command="mctl work route-to <bead-id> <pool>",
            )
        )
    if not step.is_open:
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MWRK016",
                "A step that is not open cannot be routed; routing it would "
                "resurrect finished work into a pool query.",
                bead_id=step.id,
                detail=f"status={step.status}",
            )
        )
    metadata = step.raw.get("metadata") if isinstance(step.raw, dict) else None
    previous = ""
    if isinstance(metadata, dict):
        existing = metadata.get("gc.routed_to")
        previous = existing if isinstance(existing, str) else ""
    if previous and not reroute:
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MWRK014",
                "This step is already routed; rerouting must be explicit.",
                bead_id=step.id,
                detail=f"current route={previous}",
                suggested_next_command=(
                    f"mctl work route-to {step.id} {route} --reroute"
                ),
            )
        )
    return WorkRoutePlan(
        trace_id=ctx.trace_id,
        bead_id=step.id,
        route=route,
        previous_route=previous,
        bead_update=BeadUpdate(
            id=step.id,
            metadata={"gc.routed_to": route},
            # Optimistic concurrency: bd exits 13 and writes nothing if the
            # status moved between plan and apply.
            if_status=step.status,
        ),
    )


def plan_dispatch(ctx: MctlContext, brief_id: str) -> WorkDispatchPlan:
    item = _work_item(ctx, brief_id)
    _raise_if_blocked(ctx, item)
    formula_invocation = _formula_invocation(ctx, item)
    now = _now()
    provenance = {
        "bead_id": item.bead_id,
        "brief_id": item.brief_id,
        "created_at": now,
        "formula": formula_invocation["formula"],
        "preflight_result": "passed",
        "rig": ctx.rig_id,
        "source": "mathcity.work",
        "target": f"{ctx.rig_id}/gc.run-operator",
        "trace_id": ctx.trace_id,
    }
    today = datetime.now(timezone.utc).date().isoformat()
    return WorkDispatchPlan(
        trace_id=ctx.trace_id,
        target_brief_id=item.brief_id,
        bead_id=item.bead_id,
        formula_invocation=formula_invocation,
        provenance=provenance,
        event_path=ctx.rig_root / ".beads" / "mctl" / "events" / f"{today}.jsonl",
        trace_path=ctx.rig_root / ".beads" / "mctl" / "traces" / f"{today}.jsonl",
    )


def dispatch_dry_run_payload(plan: WorkDispatchPlan) -> dict[str, object]:
    return {
        "applied": False,
        "effect_plan": plan.to_dict(),
        "trace_id": plan.trace_id,
    }


LIVE_DISPATCH_ENV = "MCTL_ENABLE_LIVE_DISPATCH"
DISPATCH_TIMEOUT_SECONDS = 120


def live_dispatch_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Whether the operator has explicitly armed live dispatch.

    This is deliberately independent of MCTL_BEADS_FIXTURE. Gating a
    production side effect on "are we in a test" meant the production branch
    was unreachable and a fixture could arm dispatch by accident.
    """
    source = os.environ if env is None else env
    return str(source.get(LIVE_DISPATCH_ENV, "")).strip() in {"1", "true", "yes"}


def dispatch_disarmed_payload(ctx: MctlContext, plan: WorkDispatchPlan) -> dict[str, object]:
    """The dry-run payload plus the reason it is one.

    A disarmed dispatch used to return `dispatch_dry_run_payload` unchanged:
    `applied: false`, a complete plan reading `preflight_result: passed`, a trace
    id, and no diagnostics. That is substantively identical to a dry run the
    caller did not ask for, so every dispatch in a run would be recorded as
    dispatched and never happen. The only signal was one boolean.

    The refusal is correct and unchanged -- writing provenance would flip
    readiness to `dispatched` and block every future attempt. Only the silence
    was wrong. Both neighbouring refusals below already name themselves
    (`MCTL_CONTROL_PLANE_NOT_ACTIVE`, `MWRK_DISPATCH_COMMAND_FAILED`); this was
    the one branch that refused without saying so.

    Emitted into the payload rather than raised: the CLI's disarmed path is
    covered by kill-switch tests that pin `returncode == 0` while asserting no
    `gc sling` occurred, and the security property those defend is the absence of
    the side effect, not the exit status. Raising here would rewrite those
    assertions in the same change that fixes the silence.

    This does NOT arm dispatch. Arming is a separate decision.
    """
    payload = dispatch_dry_run_payload(plan)
    payload["diagnostics"] = [
        _diagnostic(
            ctx,
            Severity.ERROR,
            "MCTL_LIVE_DISPATCH_DISARMED",
            "Live dispatch is not armed, so this plan was not slung and nothing ran.",
            brief_id=plan.target_brief_id,
            bead_id=plan.bead_id,
            suggested_next_command=(
                f"set {LIVE_DISPATCH_ENV}=1 in the environment of the process "
                "running mctl, then dispatch again"
            ),
        ).to_dict()
    ]
    return payload


def apply_dispatch_plan(ctx: MctlContext, plan: WorkDispatchPlan) -> dict[str, object]:
    if not live_dispatch_enabled():
        # Not armed: no side effect, and say so. Writing provenance here would
        # flip readiness to `dispatched` and block every future attempt,
        # recording a handoff that never happened.
        return dispatch_disarmed_payload(ctx, plan)

    # The data-plane probe cannot see this: `gc stop` leaves Dolt listening, so
    # reads keep working while there is no supervisor to route a sling to.
    # `is not True` on purpose, NOT `is False`. The probe returns None when it
    # cannot tell -- gc missing, gc slow, unparseable answer. Arming a real
    # `gc sling` is irreversible, so an unknown control plane must refuse.
    # Testing `is False` here made every slow gc silently open the gate.
    if probe_control_plane(city_root=ctx.city_root) is not True:
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MCTL_CONTROL_PLANE_NOT_ACTIVE",
                "This city's controller is not confirmed running, so dispatched "
                "work would have nothing to route to.",
                brief_id=plan.target_brief_id,
                bead_id=plan.bead_id,
                suggested_next_command="gc start",
            )
        )

    command = [str(part) for part in plan.formula_invocation["command"]]
    try:
        result = subprocess.run(
            command,
            cwd=ctx.rig_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=DISPATCH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        # #184: these are opposite worlds and shared one message. A timeout means
        # the command RAN; `applied: false` after one is a claim about the world
        # derived from how long we waited, and a caller who believes it retries.
        verdict = classify_dispatch_subprocess_error(error)
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                verdict.code,
                verdict.message,
                brief_id=plan.target_brief_id,
                bead_id=plan.bead_id,
                detail=str(error),
                suggested_next_command=verdict.suggested_next_command,
            )
        ) from error
    if result.returncode != 0:
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MWRK_DISPATCH_COMMAND_FAILED",
                "The dispatch command failed, so no dispatch was recorded.",
                brief_id=plan.target_brief_id,
                bead_id=plan.bead_id,
                detail=(result.stderr or result.stdout).strip(),
            )
        )

    # Plan §4 MWRK003: a sling can exit 0 without actually claiming the bead.
    # Recording provenance then would assert a handoff that silently did not
    # take, and would block every retry via MWRK_ALREADY_DISPATCHED.
    try:
        dispatched = {bead.id: bead for bead in _beads(ctx)}.get(plan.bead_id)
    except WorkError:
        dispatched = None
    if dispatched is None or not dispatched.has_active_assignee:
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MWRK003",
                "The dispatch command succeeded but the bead was never claimed.",
                brief_id=plan.target_brief_id,
                bead_id=plan.bead_id,
                data_location=_canonical_bead_location(ctx),
                detail="no active assignee after dispatch; nothing was recorded",
            )
        )

    # Only now, with a verified handoff behind us, is provenance truthful.
    provenance = write_dispatch_provenance(
        ctx,
        bead_id=plan.bead_id,
        brief_id=plan.target_brief_id,
        observed_at=str(plan.provenance["created_at"]),
        formula_invocation=plan.formula_invocation,
    )
    actual_effects = [
        {"kind": "dispatch_command", "command": command, "exit_code": result.returncode},
        {"kind": "provenance_write", "path": str(provenance.path)},
        {"kind": "event_write", "path": str(plan.event_path)},
    ]
    append_jsonl(
        plan.event_path,
        {
            "bead_id": plan.bead_id,
            "brief_id": plan.target_brief_id,
            "formula_invocation": plan.formula_invocation,
            "operation": plan.operation,
            "provenance_path": str(provenance.path),
            "trace_id": plan.trace_id,
        },
    )
    append_applied(plan.trace_path, plan.trace_id, actual_effects)
    return {
        "actual_effects": actual_effects,
        "applied": True,
        "effect_plan": plan.to_dict(),
        "provenance": provenance.to_dict(),
        "trace_id": plan.trace_id,
    }


DISPATCH_EVENT_SCHEMA = "dispatch-provenance.v1"
DISPATCH_EVENT_CATEGORY = "dispatch.provenance"
NEW_EVENT_ID_PLACEHOLDER = "(pending-event-bead-id)"


def plan_dispatch_event(
    ctx: MctlContext,
    bead_id: str,
    *,
    dispatch_command: str,
    formula: str,
    window_seconds: int | None = None,
) -> EffectPlan:
    """Plan the path-B dispatch provenance event: create it, and link it.

    One operation, not two. The skill spelled this as a bare `bd create`
    piped into a bare `bd dep relate`, and the pair is only meaningful
    together -- the lost-bead filter keys on an event bead that is *attached*
    to the source bead, so an event created and left unlinked is invisible in
    exactly the way an unwritten one is.

    The source bead's existence is a **precondition**, so a bead id this rig's
    store cannot resolve stops the mutation before anything is created. That
    is what keeps the cross-store hazard out: `bd dep add` writes a dangling
    row for an unresolvable id and exits 0, and the cheapest place to refuse
    that edge is before there is an orphan event bead to explain.
    """
    preconditions: tuple[Diagnostic, ...] = ()
    claim: ClaimState | None = None
    try:
        claim = work_claim(ctx, bead_id, window_seconds=window_seconds)
    except WorkError as error:
        preconditions = (error.diagnostic,)

    payload = _dispatch_event_payload(ctx, bead_id, claim, dispatch_command, formula)
    create = BeadCreate(
        placeholder_id=NEW_EVENT_ID_PLACEHOLDER,
        title=f"dispatch provenance for {bead_id}",
        body=json.dumps(payload, indent=2, sort_keys=True),
        issue_type="event",
        event_category=DISPATCH_EVENT_CATEGORY,
        event_target=bead_id,
        event_payload=json.dumps(payload, sort_keys=True),
    )
    relate = BeadRelate(source_id=NEW_EVENT_ID_PLACEHOLDER, target_id=bead_id)
    today = datetime.now(timezone.utc).date().isoformat()
    row = {
        "bead_id": bead_id,
        "operation": "work.dispatch_event",
        "planned_effects": [create.to_dict(), relate.to_dict()],
        "provenance": payload,
        "trace_id": ctx.trace_id,
    }
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation="work.dispatch_event",
        target_brief_id=bead_id,
        preconditions=preconditions,
        bead_updates=(),
        cache_updates=(),
        bead_creates=(create,),
        bead_relates=(relate,),
        event_writes=(
            JsonlWrite(
                "event_write",
                ctx.rig_root / ".beads" / "mctl" / "events" / f"{today}.jsonl",
                row,
            ),
        ),
        trace_writes=(
            JsonlWrite(
                "trace_write",
                ctx.rig_root / ".beads" / "mctl" / "traces" / f"{today}.jsonl",
                {**row, "city_path": str(ctx.city_root), "rig_name": ctx.rig_id},
            ),
        ),
    )


def _dispatch_event_payload(
    ctx: MctlContext,
    bead_id: str,
    claim: ClaimState | None,
    dispatch_command: str,
    formula: str,
) -> dict[str, object]:
    """The `dispatch-provenance.v1` body, derived from the claim read.

    `verified_assignee`, `assignee_state`, `classification_hint` and
    `fingerprint` are read off `ClaimState` rather than chosen by the caller:
    an event that says `healthy` while the store says nobody holds the bead is
    precisely the false handoff record this replaces.
    """
    payload: dict[str, object] = {
        "schema": DISPATCH_EVENT_SCHEMA,
        "source_bead": bead_id,
        "dispatch_command": dispatch_command,
        "formula": formula,
        "rig": ctx.rig_id,
        "observer": "mctl",
        "trace_id": ctx.trace_id,
    }
    if claim is None:
        # The precondition already refuses this plan; the payload still says
        # what it does not know rather than inventing a classification.
        payload.update(
            {
                "verified_assignee": False,
                "assignee_state": "unknown",
                "classification_hint": "unknown",
                "fingerprint": "source_bead_not_found",
                "observed_at": _now(),
            }
        )
        return payload
    payload.update(
        {
            "assignee_state": claim.assignee_state,
            "classification_hint": claim.classification_hint,
            "fingerprint": claim.fingerprint,
            "observed_at": claim.observed_at,
            "verified_assignee": claim.verified_assignee,
        }
    )
    return payload


def _closed_source_blockers(
    ctx: MctlContext | None, *, brief_id: str, source: Bead | None
) -> list[Diagnostic]:
    """Blocker for a source bead that is no longer open (#157).

    `_work_item` checked that the source EXISTS, that it has no active
    assignee, and that no open child workflow claims it -- and never consulted
    its status. A closed bead cleared every one of those, so `blockers: []` did
    not mean "no blockers", it meant "never asked". Measured across all 17
    rigs, the only two items `work_ready` called dispatchable were closed
    throwaway test beads (QUIMBY, trace f9d4eb5b).

    `gc` refused the same bead one layer down -- "formulas v2 target
    gsp-odm8cx is closed" -- so the write was already safe and only the read
    lied. This closes the gap at the read.

    A MISSING source is deliberately not reported here: `source is None`
    already raises MWRK012 at the call site, and a second diagnostic for one
    fact would double-count the same brief.

    Uses `Bead.is_open`, which already carries the working-state vocabulary
    (`open · hooked · in_progress · blocked · review · testing`) and is
    case-insensitive. The check was absent, not wrong -- so this must not
    introduce a second, drifting definition of "closed".
    """
    if source is None or source.is_open:
        return []
    return [
        _diagnostic(
            ctx,
            Severity.ERROR,
            "MWRK013",
            "The source bead named by the brief dependency is closed.",
            brief_id=brief_id,
            bead_id=source.id,
            data_location=_canonical_bead_location(ctx) if ctx is not None else "",
            detail=f"status={source.status}",
        )
    ]


def _work_item(
    ctx: MctlContext,
    brief_id: str,
    *,
    include_provenance_errors: bool = True,
    beads: tuple[Bead, ...] | None = None,
    doctor: DoctorReport | None = None,
) -> WorkItem:
    beads = _beads(ctx) if beads is None else beads
    bead_by_id = {bead.id: bead for bead in beads}
    brief = bead_by_id.get(brief_id)
    # B2.1's brief population, not merely `type=decision`: a push-authorization
    # receipt or a kill-switch record is a standalone decision bead, so
    # dispatching work "from" one is a category error and says so plainly here
    # rather than surfacing as a missing-brief error from the doctor.
    if brief is None or not is_brief_bead(brief):
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MWRK_BRIEF_NOT_FOUND",
                f"No canonical decision brief named {brief_id!r} was found.",
                brief_id=brief_id,
                suggested_next_command="mctl briefs list --json",
            )
        )
    blockers: list[Diagnostic] = []
    if doctor is None:
        doctor = _doctor_report(ctx, brief_id, beads)
        brief_diagnostics = doctor.diagnostics
    else:
        brief_diagnostics = tuple(
            diagnostic
            for diagnostic in doctor.diagnostics
            if diagnostic.facts.get("brief_id") == brief_id
        )
    blockers.extend(_blocking_doctor_diagnostics(brief_diagnostics))
    source_id = brief.source_dependencies[0] if brief.source_dependencies else ""
    if not source_id:
        blockers.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MWRK011",
                "Approved work dispatch requires a source bead dependency.",
                brief_id=brief_id,
                data_location=_canonical_bead_location(ctx),
            )
        )
        source_id = brief_id
    source = bead_by_id.get(source_id)
    if source is None:
        blockers.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MWRK012",
                "The source bead named by the brief dependency was not found.",
                brief_id=brief_id,
                bead_id=source_id,
                data_location=_canonical_bead_location(ctx),
            )
        )
    blockers.extend(_closed_source_blockers(ctx, brief_id=brief_id, source=source))
    if not _approved_for_dispatch(brief):
        blockers.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MWRK010",
                "Brief has no approving verdict for work dispatch.",
                brief_id=brief_id,
                bead_id=source_id,
                data_location=_canonical_bead_location(ctx),
            )
        )
    # Plan §4 dispatch-safety invariants. These are the double-dispatch and
    # lost-claim protections, distinct from the readiness checks above.
    if source is not None and source.has_active_assignee:
        blockers.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MWRK001",
                "The source bead already has an active assignee.",
                brief_id=brief_id,
                bead_id=source_id,
                data_location=_canonical_bead_location(ctx),
                detail=f"assignee={source.assignee}",
            )
        )
    existing_workflow = _open_child_workflow(beads, source_id)
    if existing_workflow is not None:
        blockers.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MWRK002",
                "An open child workflow already exists for the same source bead.",
                brief_id=brief_id,
                bead_id=source_id,
                data_location=_canonical_bead_location(ctx),
                detail=f"workflow={existing_workflow.id} status={existing_workflow.status}",
            )
        )
    provenance: DispatchProvenance | None = None
    try:
        provenance = read_dispatch_provenance(ctx, source_id, required=False)
    except ProvenanceError as error:
        if include_provenance_errors:
            blockers.append(error.diagnostic)
        else:
            raise WorkError(error.diagnostic) from error
    if provenance is not None and not blockers:
        readiness = "dispatched"
    elif blockers:
        readiness = "blocked"
    else:
        readiness = "ready"
    return WorkItem(
        brief_id=brief_id,
        bead_id=source_id,
        title=source.title if source is not None else brief.title,
        readiness=readiness,
        blockers=tuple(blockers),
        provenance=provenance,
    )


def _open_child_workflow(beads: tuple[Bead, ...], source_id: str) -> Bead | None:
    """An open workflow bead already rooted at this source bead, if any.

    Gas City workflow beads carry their root in metadata as gc.root_bead_id;
    a live one means the source is already being worked.
    """
    for bead in beads:
        if bead.id == source_id:
            continue
        if bead.workflow_root_id == source_id and bead.is_open:
            return bead
    return None


def _doctor_report(
    ctx: MctlContext, brief_id: str | None, beads: tuple[Bead, ...] | None
) -> DoctorReport:
    try:
        return doctor_briefs(ctx, brief_id, beads)
    except BriefError as error:
        raise WorkError(error.diagnostic) from error


def _decision_beads(ctx: MctlContext) -> tuple[Bead, ...]:
    return brief_population(_beads(ctx))


def _beads(ctx: MctlContext) -> tuple[Bead, ...]:
    try:
        return read_beads(ctx.rig_root, fixture_path=ctx.beads_fixture)
    except BeadReadError as error:
        raise WorkError(
            _diagnostic(ctx, Severity.FATAL, "MWRK_BEAD_READ_FAILED", str(error))
        ) from error


def _blocking_doctor_diagnostics(diagnostics: tuple[Diagnostic, ...]) -> tuple[Diagnostic, ...]:
    return tuple(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.severity in {Severity.ERROR, Severity.FATAL}
    )


def _raise_if_blocked(ctx: MctlContext, item: WorkItem) -> None:
    if item.readiness == "dispatched":
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MWRK_ALREADY_DISPATCHED",
                "Work already has dispatch provenance.",
                brief_id=item.brief_id,
                bead_id=item.bead_id,
            )
        )
    if not item.blockers:
        return
    legacy = next(
        (
            diagnostic
            for diagnostic in item.blockers
            if diagnostic.code == "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED"
        ),
        None,
    )
    if legacy is not None:
        raise WorkError(legacy)
    first = item.blockers[0]
    raise WorkError(
        _diagnostic(
            ctx,
            Severity.FATAL,
            "MWRK_DISPATCH_BLOCKED",
            "Work dispatch is blocked by readiness diagnostics.",
            brief_id=item.brief_id,
            bead_id=item.bead_id,
            detail=first.code,
        )
    )


def _formula_invocation(ctx: MctlContext, item: WorkItem) -> dict[str, object]:
    brief_slug = item.brief_id
    artifact_root = str(ctx.rig_root / ".beads" / "briefs")
    command = [
        "gc",
        "sling",
        f"{ctx.rig_id}/gc.run-operator",
        item.bead_id,
        "--on",
        "work-briefed",
        "--var",
        f"source_bead={item.bead_id}",
        "--var",
        f"brief_slug={brief_slug}",
        "--var",
        f"artifact_root={artifact_root}",
        "--var",
        "routing_path=mctl.work.dispatch,work-briefed",
    ]
    return {
        "command": command,
        "formula": "work-briefed",
        "order": "brief-decision-dispatch",
        "target": f"{ctx.rig_id}/gc.run-operator",
        "work_bead": item.bead_id,
    }


def _approved_for_dispatch(bead: Bead) -> bool:
    """#160: this used to read three fixed metadata keys directly and compare
    the value against an exact set of four bare words. Real verdicts are not
    bare words -- `briefs_list` (which reads through `verdicts.read_verdict`)
    reports live verdicts like `APPROVE-OPTION-A` and
    `APPROVE-BRIEF-AS-RECOMMENDED-3A-5C-1NORELITIGATE-...` -- so the exact-set
    check rejected every real approval it was ever handed and only a bare,
    literal "approve" ever passed.

    Delegating to `read_verdict` fixes the reader half: `briefs_list` and
    `work_status` now agree about what a bead's recorded verdict text *is*.
    The prefix check (rather than an exact match) fixes the classification
    half for the population this was measured against -- verdict text that
    names its polarity up front.

    NOT fixed here, named rather than silently missed: a verdict recorded as
    a bare option letter with a human-readable parenthetical, e.g.
    `"A (implicit approval)"` (measured live: `he-hbyr`, a legacy-backfilled
    close_reason) carries no "approve"/"accept" prefix at all and is not
    recognised by this check. Classifying an arbitrary option letter as an
    approval is a genuine judgement call -- it would require knowing what
    "A" meant on the specific brief that offered it -- and is out of this
    fix's scope on purpose rather than guessed at.
    """
    if bead.status.lower() not in {"closed", "done"}:
        return False
    verdict = read_verdict(bead)
    if verdict is None:
        return False
    normalized = "".join(ch for ch in verdict.text.lower() if ch.isalnum())
    return normalized.startswith("approve") or normalized.startswith("accept")


def _canonical_bead_location(ctx: MctlContext) -> str:
    return f"{' '.join(BD_LIST_ARGS)} (rig database {ctx.rig_db})"


def _diagnostic(
    ctx: MctlContext,
    severity: Severity,
    code: str,
    message: str,
    *,
    brief_id: str | None = None,
    bead_id: str | None = None,
    data_location: str | None = None,
    detail: str | None = None,
    suggested_next_command: str | None = None,
) -> Diagnostic:
    facts = {
        "city_path": str(ctx.city_root),
        "implementation_provenance": "mctl Slice 4 work dispatch controls",
        "rig_name": ctx.rig_id,
        "rig_path": str(ctx.rig_root),
    }
    if brief_id:
        facts["brief_id"] = brief_id
    if bead_id:
        facts["bead_id"] = bead_id
    if data_location:
        facts["data_location"] = data_location
    if detail:
        facts["detail"] = detail
    if suggested_next_command:
        facts["suggested_next_command"] = suggested_next_command
    return Diagnostic(severity, code, message, facts=facts, trace_id=ctx.trace_id)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
