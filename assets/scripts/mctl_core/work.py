"""Work readiness, provenance, and dispatch controls for mctl."""
from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence

from .beads import BD_LIST_ARGS, Bead, BeadCreate, BeadReadError, BeadRelate, read_beads, BeadUpdate
from .briefs import BriefError, DoctorReport, doctor_briefs
from .context import MctlContext
from .deadlines import (
    ElapsedNotice,
    ElapsedPolicy,
    parse_optional_seconds,
    run_supervised,
    unbounded_policy,
)
from .diagnostics import Diagnostic, Severity
from .effects import EffectPlan, JsonlWrite
from .events import append_jsonl
from .liveness import probe_control_plane
from .molecules import is_molecule_root
from .verdicts import brief_population, is_brief_bead, read_verdict
from .trace import append_applied, append_planned
from .redundant_state import artifact_layout
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
    #: Sources the multi-source resolver walked PAST because they were already
    #: being worked (#228). Empty for a single-source brief, or when the first
    #: source was dispatchable. Named in the payload so the walk is not silent.
    skipped_sources: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "bead_id": self.bead_id,
            "blockers": [blocker.to_dict() for blocker in self.blockers],
            "brief_id": self.brief_id,
            "provenance": self.provenance.to_dict() if self.provenance is not None else None,
            "readiness": self.readiness,
            "skipped_sources": list(self.skipped_sources),
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

#: The command RAN and we stopped waiting -- `subprocess.TimeoutExpired`, and no
#: dispatch is observable afterwards. Whether its work landed is still unknown.
DISPATCH_TIMEOUT_CODE = "MWRK_DISPATCH_TIMEOUT_UNKNOWN"

#: The command RAN, we stopped waiting, and the dispatch IS observable afterwards.
#: mc-u9eun: the 2026-08-28 sling completed at 243.51s and minted molecule
#: mc-mgejq, and the 200s budget reported that as UNKNOWN. UNKNOWN is strictly
#: worse than a refusal -- it is what invites the retry that double-dispatches,
#: and mc-5wdje acquired two work streams that way. When the claim is visible we
#: do not have to guess: look, and say so.
DISPATCH_TIMEOUT_LANDED_CODE = "MWRK_DISPATCH_TIMEOUT_LANDED"


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


def resolve_dispatch_timeout(*, claim_observed: bool) -> DispatchFailureVerdict:
    """Turn a timeout into an ANSWER when the dispatch is observable (mc-u9eun).

    A timeout says only that we stopped waiting. It does not say the work did not
    happen -- on 2026-08-28 the command had already succeeded (exit 0, 243.51s,
    molecule mc-mgejq) when the 200s budget killed the wait.

    So: run the same claim observation the success path runs. If a claim IS
    visible the dispatch demonstrably landed, and reporting `unknown` there is a
    self-inflicted ambiguity that invites a double dispatch.

    When nothing is observable this stays `applied=None`, NEVER False. Absence of
    a claim is not proof nothing landed -- the claim may merely not be observable
    yet (#212/MWRK003) -- and False would tell the caller a retry is safe.
    """
    if claim_observed:
        return DispatchFailureVerdict(
            code=DISPATCH_TIMEOUT_LANDED_CODE,
            applied=True,
            may_have_dispatched=True,
            message=(
                "The dispatch command exceeded the timeout, but the dispatch IS "
                "observable, so it LANDED. The wait was abandoned; the work was not."
            ),
            suggested_next_command=(
                "do not retry -- the dispatch landed; follow it with "
                "`mctl work status <brief-id> --json`"
            ),
        )
    return DispatchFailureVerdict(
        code=DISPATCH_TIMEOUT_CODE,
        applied=None,
        may_have_dispatched=True,
        message=(
            "The dispatch command ran but did not finish before the timeout, and no "
            "dispatch is observable yet, so whether one was recorded is UNKNOWN."
        ),
        suggested_next_command=(
            "check whether the dispatch landed before you retry -- a retry after a "
            "timeout can dispatch a second time"
        ),
    )



def dispatch_timeout_is_failure(verdict: DispatchFailureVerdict) -> bool:
    """Whether a timeout verdict should be rendered as a failure at all (P6.3).

    `subdomains/dev/POLICY.md:554` -- a deadline is a fact about the CALLER, not
    the probed system, and an expiry "must never render as `failed`". A dispatch
    we can SEE landed is the least-failed outcome available: the wait was
    abandoned, the work was not. Rendering it FATAL attributes our impatience to
    a system that did its job, and tells the caller to clean up work running fine.

    An unresolved timeout stays a failure: nothing is known, and the operator
    does need to act before retrying.
    """
    return verdict.applied is not True


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


def _all_work_items(
    ctx: MctlContext,
) -> tuple[tuple[Bead, ...], tuple[Bead, ...], tuple[WorkItem, ...]]:
    """Every brief's work item, with the store and population it came from.

    Split out of `ready_work` so `ready_work_payload` can report the
    denominator WITHOUT reading the store a second time. `_beads` shells out to
    `bd`, and `test_bd_invocation_count` exists because a read that quietly
    doubled its subprocess count is a regression this repo has already paid
    for once.
    """
    beads = _beads(ctx)
    population = brief_population(beads)
    doctor = _doctor_report(ctx, None, beads)
    items = tuple(
        _work_item(ctx, bead.id, beads=beads, doctor=doctor) for bead in population
    )
    return beads, population, items


def ready_work(ctx: MctlContext) -> tuple[WorkItem, ...]:
    _, _, items = _all_work_items(ctx)
    return tuple(item for item in items if item.readiness == "ready")


#: What `work_scope` looks like when nothing was read at all. Declared here,
#: beside the block itself, so the cross-rig merge can seed a city where every
#: rig failed with `matched: 0 of 0` instead of dropping the key and returning
#: an array with no denominator -- which is the exact shape this block exists
#: to remove. Zeros, never a missing key: absence would read as "the question
#: was not asked", and here it always was.
EMPTY_WORK_SCOPE: Mapping[str, object] = {
    "matched": 0,
    "distinct_bead_ids": 0,
    "briefs_examined": 0,
    "total_in_store": 0,
    "readiness_excluded": [],
}


def ready_work_payload(ctx: MctlContext) -> dict[str, object]:
    """Ready work, and the scope the enumeration applied (M3, mc-uvl).

    `ready_work` returns a bare tuple, and every one of its three callers
    turned it straight into a bare `work` array. A bare array of dispatchable
    rows is indistinguishable from a census of dispatchable work, and it was
    read as one: "33 ready in mathcity" on 2026-08-28, with nothing in the
    payload saying that 33 was drawn from a brief population, that the rest
    were dropped as `blocked`, or that two of the 33 rows named the same bead.

    This is #245's `beads_list` shape, field for field -- `matched` beside
    `total_in_store`, and an `_excluded` list naming what was dropped rather
    than letting it vanish. `total_in_store` counts the WHOLE store, never the
    brief population and never the matched set: a denominator that shrank with
    the filter would report 33-of-33 for a read that dropped 200 rows, which is
    the bug with extra steps. `briefs_examined` sits between the two because
    `work_ready`'s population is briefs, not beads, and a caller comparing 33
    against the store size without it would draw the wrong conclusion in the
    other direction.

    `distinct_bead_ids` is here because rows are not beads. `mc-7h1` occupied
    two of mathcity's 33 rows (briefs `mc-02zyz` and `mc-u0ix`) and `gt-byxtj`
    two of hq's four, so the row count overstates dispatchable work AND names
    a double-dispatch. Reporting only the row count would leave that
    unmeasurable from the payload.

    THE KEY IS `work_scope`, NOT `scope`, AND THAT IS DELIBERATE. The cross-rig
    merge already occupies the top-level `scope` key with the STRING
    `"all-rigs"` (`city.ALL_RIGS_SCOPE`), so a `work_ready` that declared
    `scope` as an object would fail its own output schema the moment anyone
    passed `--all-rigs` -- which is precisely the call whose total got quoted.
    The convention is the field set; only the key had to move.
    """
    beads, population, all_items = _all_work_items(ctx)
    items = tuple(item for item in all_items if item.readiness == "ready")
    # Derived from what the population actually produced, not from a fixed
    # vocabulary, so a readiness state nobody anticipated shows up as excluded
    # instead of disappearing.
    returned = {item.readiness for item in items}
    excluded = sorted({item.readiness for item in all_items} - returned)
    return {
        "work": [item.to_dict() for item in items],
        "work_scope": {
            "matched": len(items),
            "distinct_bead_ids": len({item.bead_id for item in items}),
            "briefs_examined": len(population),
            "total_in_store": len(beads),
            "readiness_excluded": excluded,
        },
    }


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

#: The worst MEASURED cost of a live `gc sling`. Raise this ONLY when a LARGER
#: cost is measured, never to make a failing call pass (same discipline as
#: `orders.MEASURED_CATALOG_WORST_SECONDS`).
#:
#:   162.7s  S48, 2026-08-22/23, exit 0 -- slow, not hung (SURFACE-STATUS.md §4/row 7)
#:   243.51s mc-u9eun, 2026-08-28 21:51:18-21:55:21Z, exit 0, molecule mc-mgejq minted
#:
#: `gc` does ~8-10s of cwd-scoped whole-city enumeration before it even knows its
#: subcommand, and dry-run resolution alone measured 56s (#181); the routing half
#: pushes the total past two minutes. The 2026-08-28 run additionally rode out
#: four Dolt connection resets (bad idle connection EOF, reset by peer, broken
#: pipe, unexpected EOF) and still exited 0 -- SLOW, NOT HUNG, the framing S48
#: recorded in gt-ybi8j2.
MEASURED_SLING_WORST_SECONDS = 243.51

#: What `apply_dispatch_plan` calls the thing it is waiting on, in every notice.
DISPATCH_LABEL = "the `gc sling` dispatch"

#: How long a dispatch may run before we START SAYING SO. This is a warn
#: threshold, NOT a bound: nothing is killed when it is crossed.
#:
#: mc-vtru8, Taylor: *"We shouldn't have a dispatch timeout. So yes, if we raise
#: the dispatch timeout to infinity and replace it with a warning."* The 300s
#: that used to KILL this call now only reports it. That is the whole change --
#: the same number, moved from a verdict to an observation. Raising it three
#: times on measurement (120 -> 200 -> 300) never worked, because each raise was
#: a better guess at a bound that should not have existed; every kill was a true
#: statement about our patience and a false one about the sling.
DISPATCH_WARN_AFTER_SECONDS = 300.0

#: Where the warn threshold sits UNDER an operator-set deadline. P6.3(a) requires
#: a warn strictly below any deadline; this is the fraction `bounded_policy`
#: derives it at, so an operator who sets a bound cannot accidentally set one
#: with no early signal beneath it.
DISPATCH_BUDGET_WARN_FRACTION = 0.75

#: Part 3 of the verdict -- *"There should also be a surface for adjusting the
#: timeout size."* Unset means UNBOUNDED, which is the default and the point.
#: `--deadline-seconds` on `mctl work dispatch` overrides this per call.
DISPATCH_DEADLINE_ENV = "MCTL_DISPATCH_DEADLINE_SECONDS"

#: Companion surface for the warn threshold, for an operator who wants to hear
#: about a slow dispatch earlier (or later) than 300s.
DISPATCH_WARN_AFTER_ENV = "MCTL_DISPATCH_WARN_AFTER_SECONDS"

#: Emitted WHILE a dispatch is still running and has passed its warn threshold.
#: This is the signal that replaces the deadline: a visible non-failure statement
#: of elapsed time, made at a moment when nobody yet knows the outcome.
DISPATCH_STILL_RUNNING_CODE = "MWRK_DISPATCH_STILL_RUNNING"

#: Emitted on a dispatch that FINISHED but ran past the warn threshold.
DISPATCH_SLOW_CODE = "MWRK_DISPATCH_SLOW"

#: Emitted when the operator's own bound configuration needs reporting back --
#: unreadable, or set below the worst cost this dispatch has been MEASURED to
#: take. Never silently corrected: it is the operator's bound.
DISPATCH_OPERATOR_BOUND_CODE = "MWRK_DISPATCH_OPERATOR_BOUND"


def operator_bound_below_measurement_warning(deadline_seconds: float | None) -> str | None:
    """Detail when an operator's bound is smaller than the cost it wraps, else None.

    This carries forward the subject of `test_dispatch_budget.py`: *a bound below
    the measurement is a path that cannot succeed.* That test was written against
    a hardcoded budget that shipped at 120s while a live sling measured 162.7s,
    and the same relationship now applies to whatever an operator can set.

    Returns None when there is no bound -- the default. A bound that does not
    exist cannot sit below a measurement, which is the structural reason the
    unbounded default retires this failure class rather than re-tuning it.
    """
    if deadline_seconds is None:
        return None
    if deadline_seconds >= MEASURED_SLING_WORST_SECONDS:
        return None
    return (
        f"the operator-set dispatch deadline of {deadline_seconds:.1f}s is below "
        f"the worst MEASURED cost of the sling it wraps "
        f"({MEASURED_SLING_WORST_SECONDS}s, mc-u9eun 2026-08-28, exit 0). A bound "
        "below the measurement is a path that cannot succeed: it kills a dispatch "
        "that would have landed and reports the outcome UNKNOWN, which is #181 and "
        "mc-u9eun. The default is NO deadline; unset "
        f"{DISPATCH_DEADLINE_ENV} to restore it."
    )


def resolve_dispatch_elapsed_policy(
    env: Mapping[str, str] | None = None,
) -> tuple[ElapsedPolicy, tuple[str, ...]]:
    """Read the operator surface into a policy, plus anything worth reporting back.

    Default: warn at `DISPATCH_WARN_AFTER_SECONDS`, deadline None. An unusable
    value is reported and IGNORED rather than coerced -- a typo must not become a
    kill bound nobody chose.
    """
    source = os.environ if env is None else env
    notes: list[str] = []

    deadline, complaint = parse_optional_seconds(source.get(DISPATCH_DEADLINE_ENV))
    if complaint:
        notes.append(f"{DISPATCH_DEADLINE_ENV}: {complaint}")
    warn_after, warn_complaint = parse_optional_seconds(source.get(DISPATCH_WARN_AFTER_ENV))
    if warn_complaint:
        notes.append(f"{DISPATCH_WARN_AFTER_ENV}: {warn_complaint}")
    if warn_after is None:
        warn_after = DISPATCH_WARN_AFTER_SECONDS

    below = operator_bound_below_measurement_warning(deadline)
    if below:
        notes.append(below)

    if deadline is None:
        return unbounded_policy(DISPATCH_LABEL, warn_after_seconds=warn_after), tuple(notes)
    if warn_after >= deadline:
        # P6.3(a) leaves no discretion here: the warn must sit strictly below the
        # deadline. Derive one rather than refusing the operator's bound.
        warn_after = deadline * DISPATCH_BUDGET_WARN_FRACTION
    return (
        ElapsedPolicy(
            label=DISPATCH_LABEL, warn_after_seconds=warn_after, deadline_seconds=deadline
        ),
        tuple(notes),
    )


#: The operator surface's two keys, indexed by the argument name each is set
#: from. `work_dispatch_bound` writes THESE keys -- the same two the env surface
#: documents and the CLI flags layer onto -- so an agent, an operator's shell,
#: and a per-call flag all end up in one store, read back by one function.
#:
#: Taylor, asked whether the surface built for mc-vtru8 part 3 had to be
#: reachable from an agent and not only from a shell: *"Yes MCP reachable."*
#: A tool that parsed its own seconds into its own policy would have made the
#: MCP answer to "what is the bound" independent of the CLI answer, and two
#: surfaces that can disagree about a kill bound are worse than one surface that
#: is merely inconvenient.
DISPATCH_BOUND_ENV_KEYS: Mapping[str, str] = {
    "deadline_seconds": DISPATCH_DEADLINE_ENV,
    "warn_after_seconds": DISPATCH_WARN_AFTER_ENV,
}


def dispatch_bound_state(
    policy: ElapsedPolicy, notes: Sequence[str] = ()
) -> dict[str, object]:
    """One resolved policy, rendered for a payload.

    `deadline_seconds` is null for the default, and null is the ANSWER here --
    *there is no bound* -- not a missing value. `bounded` states the same fact
    as a boolean so a client never has to infer it from a null.
    """
    return {
        "bounded": policy.bounded,
        "deadline_seconds": policy.deadline_seconds,
        "label": policy.label,
        "notes": list(notes),
        "warn_after_seconds": policy.warn_after_seconds,
    }


@dataclass(frozen=True)
class DispatchBoundPlan:
    """What adjusting the dispatch bound intends to do, before it does it.

    `in_force` is what a dispatch resolves to right now; `resolved` is what it
    would resolve to once `requested` is installed. Both come from
    `resolve_dispatch_elapsed_policy`, so a preview cannot describe a policy the
    apply would not produce.
    """

    trace_id: str
    #: Env key -> the caller's raw string, unparsed. Raw on purpose: the parsing
    #: and the complaining both belong to the resolver, and a value this class
    #: had already normalised could not be reported back as the operator typed it.
    requested: Mapping[str, str]
    in_force: ElapsedPolicy
    resolved: ElapsedPolicy
    notes: tuple[str, ...]

    @property
    def operation(self) -> str:
        return "work.dispatch_bound"

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "provenance": {
                "env_writes": dict(sorted(self.requested.items())),
                "in_force": dispatch_bound_state(self.in_force),
                "resolved": dispatch_bound_state(self.resolved, self.notes),
            },
            "trace_id": self.trace_id,
        }


def plan_dispatch_bound(
    trace_id: str,
    *,
    deadline_seconds: str | None = None,
    warn_after_seconds: str | None = None,
    env: Mapping[str, str] | None = None,
) -> DispatchBoundPlan:
    """Read the bound in force, and what the caller's request would make it.

    An omitted field writes nothing: absent means *leave it alone*, never *reset
    it to the default*, so an agent adjusting the warn threshold cannot silently
    drop a deadline an operator set in the environment.

    Nothing here interprets a number. The caller's raw strings are layered onto
    the environment and the whole mapping goes to
    `resolve_dispatch_elapsed_policy` -- exactly what `cli.py` does with
    `--deadline-seconds`, and exactly what `apply_dispatch_plan` reads.
    """
    source = dict(os.environ if env is None else env)
    in_force, _ = resolve_dispatch_elapsed_policy(source)

    asked = {"deadline_seconds": deadline_seconds, "warn_after_seconds": warn_after_seconds}
    requested = {
        DISPATCH_BOUND_ENV_KEYS[name]: str(value)
        for name, value in asked.items()
        if value is not None
    }
    resolved, notes = resolve_dispatch_elapsed_policy({**source, **requested})
    return DispatchBoundPlan(
        trace_id=trace_id,
        requested=requested,
        in_force=in_force,
        resolved=resolved,
        notes=tuple(notes),
    )


def apply_dispatch_bound(
    plan: DispatchBoundPlan, env: MutableMapping[str, str] | None = None
) -> dict[str, str]:
    """Install the plan's env writes where the resolver reads them.

    The store is the process environment, which is the same store an operator's
    `export` writes to and the only one `resolve_dispatch_elapsed_policy` reads.
    A separate MCP-only store would have been a second source of truth; there is
    deliberately none.

    Scope, stated plainly because a client cannot see it: this lasts for the life
    of the server process and does not survive its restart. It is a session
    control, not a configuration file.
    """
    target = os.environ if env is None else env
    for key, value in plan.requested.items():
        target[key] = value
    return dict(plan.requested)


def dispatch_bound_payload(
    ctx: MctlContext, plan: DispatchBoundPlan, *, applied: bool
) -> dict[str, object]:
    """The bound before, the bound after, and anything the operator should hear.

    `applied` is what tells `after` apart from a preview: on a dry run nothing
    was written, so `after` is what a dispatch WOULD resolve to. The notes ride
    as `MWRK_DISPATCH_OPERATOR_BOUND` WARNs -- the same code `apply_dispatch_plan`
    reports them under, because they are the same notes from the same resolver.
    """
    return {
        "applied": applied,
        "dispatch_bound": {
            "after": dispatch_bound_state(plan.resolved, plan.notes),
            "before": dispatch_bound_state(plan.in_force),
            "env_writes": dict(sorted(plan.requested.items())),
        },
        "diagnostics": [
            _diagnostic(
                ctx,
                Severity.WARN,
                DISPATCH_OPERATOR_BOUND_CODE,
                "The operator's dispatch-deadline configuration needs reporting back.",
                detail=note,
            ).to_dict()
            for note in plan.notes
        ],
        "effect_plan": plan.to_dict(),
        "trace_id": plan.trace_id,
    }


def dispatch_elapsed_warning(
    elapsed_seconds: float, *, policy: ElapsedPolicy | None = None
) -> str | None:
    """Detail for a dispatch that FINISHED but ran long, else None.

    Returns None for a comfortable dispatch: the check must be capable of not
    firing, or it reports nothing (P6.2 -- a check that could not have failed
    must not render as a check that passed).
    """
    active = policy if policy is not None else resolve_dispatch_elapsed_policy()[0]
    if not active.exceeds_warn(elapsed_seconds):
        return None
    return active.notice(elapsed_seconds, still_running=False).message()


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


def announce_dispatch_notice(notice: ElapsedNotice) -> None:
    """Put a still-running notice where a human can see it AS IT HAPPENS.

    P6.2: the warning replaces a check, so a warn path that never emits is
    indistinguishable from a dispatch that was never slow. The returned payload
    carries the same notices, but a payload is rendered after the call returns --
    which, for the case this exists for, may be many minutes later. stderr is the
    only channel that is visible while the dispatch is still running, and `--json`
    callers read stdout, so this cannot corrupt a machine consumer.
    """
    print(f"[mctl] {notice.message()}", file=sys.stderr, flush=True)


def apply_dispatch_plan(
    ctx: MctlContext, plan: WorkDispatchPlan, *, env: Mapping[str, str] | None = None
) -> dict[str, object]:
    """Sling the plan, watching elapsed time rather than bounding it (mc-vtru8).

    `env` is the operator surface, defaulting to the process environment; the CLI
    layers `--deadline-seconds` / `--warn-after-seconds` on top of it so a per-call
    bound and a per-process one resolve through exactly one code path.
    """
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
    # mc-vtru8: no client-side deadline unless an operator set one. `run_supervised`
    # reports elapsed WHILE the sling runs and kills nothing by default, so the
    # only claim this function makes about time is how much of it has passed.
    active_policy, policy_notes = resolve_dispatch_elapsed_policy(env)
    run = None
    error: BaseException | None = None
    try:
        run = run_supervised(
            command,
            policy=active_policy,
            cwd=ctx.rig_root,
            on_notice=announce_dispatch_notice,
        )
    except OSError as spawn_error:
        error = spawn_error
    else:
        # An operator-set bound expiring is the ONLY way to reach the timeout
        # branch now, and it lands in it unchanged -- same classifier, same
        # three-valued verdict, same `applied=None`.
        error = run.timeout_error if run.deadline_exceeded else None

    elapsed_notices = tuple(run.notices) if run is not None else ()
    elapsed_seconds = run.elapsed_seconds if run is not None else 0.0

    def elapsed_diagnostics() -> list[dict[str, object]]:
        """Carry the live elapsed reports and the operator's own config into the payload.

        The still-running notices were already announced on stderr as they fired;
        repeating the LAST one here is what a `--json` consumer sees, and it is the
        non-failure elapsed signal P6.3(a) requires a deadline path to emit.
        """
        rows: list[dict[str, object]] = []
        for note in policy_notes:
            rows.append(
                _diagnostic(
                    ctx,
                    Severity.WARN,
                    DISPATCH_OPERATOR_BOUND_CODE,
                    "The operator's dispatch-deadline configuration needs reporting back.",
                    brief_id=plan.target_brief_id,
                    bead_id=plan.bead_id,
                    detail=note,
                ).to_dict()
            )
        if elapsed_notices:
            rows.append(
                _diagnostic(
                    ctx,
                    Severity.WARN,
                    DISPATCH_STILL_RUNNING_CODE,
                    "The dispatch passed its warn threshold while it was still running.",
                    brief_id=plan.target_brief_id,
                    bead_id=plan.bead_id,
                    detail=(
                        f"{len(elapsed_notices)} elapsed report(s) were emitted while "
                        f"the sling was running; the last read: "
                        f"{elapsed_notices[-1].message()}"
                    ),
                ).to_dict()
            )
        return rows

    if error is not None:
        # #184: these are opposite worlds and shared one message. A timeout means
        # the command RAN; `applied: false` after one is a claim about the world
        # derived from how long we waited, and a caller who believes it retries.
        verdict = classify_dispatch_subprocess_error(error)
        # mc-u9eun: a timeout is not the end of what we can know. The command may
        # have already succeeded (2026-08-28: exit 0 at 243.51s under a 200s
        # budget, molecule mc-mgejq minted, reported UNKNOWN). Look before
        # shrugging -- an avoidable UNKNOWN is what invites the double dispatch.
        if verdict.may_have_dispatched and verdict.applied is None:
            try:
                observed = _claim_observed(_beads(ctx), plan.bead_id)
            except WorkError:
                observed = False
            verdict = resolve_dispatch_timeout(claim_observed=observed)
        if not dispatch_timeout_is_failure(verdict):
            # P6.3: the deadline expired, but the dispatch is OBSERVABLE. Record
            # it as the success it is, with a WARN naming the overrun -- never a
            # FATAL, which would report our own impatience as this system's
            # failure and invite an operator to clean up healthy work. Provenance
            # is written here too, so the landed dispatch cannot be re-dispatched.
            provenance = write_dispatch_provenance(
                ctx,
                bead_id=plan.bead_id,
                brief_id=plan.target_brief_id,
                observed_at=str(plan.provenance["created_at"]),
                formula_invocation=plan.formula_invocation,
            )
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
            return {
                "applied": True,
                "claim": "observed",
                "effect_plan": plan.to_dict(),
                "provenance": provenance.to_dict(),
                "trace_id": plan.trace_id,
                "diagnostics": [
                    _diagnostic(
                        ctx,
                        Severity.WARN,
                        verdict.code,
                        verdict.message,
                        brief_id=plan.target_brief_id,
                        bead_id=plan.bead_id,
                        detail=(
                            f"ran {elapsed_seconds:.1f}s and exceeded the "
                            f"operator-set {active_policy.deadline_seconds}s deadline; "
                            "the dispatch is observable, so it landed"
                        ),
                        suggested_next_command=verdict.suggested_next_command,
                    ).to_dict()
                ]
                + elapsed_diagnostics(),
            }
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                verdict.code,
                verdict.message,
                brief_id=plan.target_brief_id,
                bead_id=plan.bead_id,
                # P6.3(b): even the unresolved case names ELAPSED. The bound that
                # expired is the operator's own, and saying so keeps the fact
                # attributed to the caller who chose it.
                detail=(
                    f"ran {elapsed_seconds:.1f}s against an operator-set "
                    f"{active_policy.deadline_seconds}s deadline: {error}"
                    if run is not None
                    else str(error)
                ),
                suggested_next_command=verdict.suggested_next_command,
            )
        ) from error

    # Every path where the command did not report an outcome returned or raised
    # above, so `run.completed` is the real `CompletedProcess` here -- never a
    # synthesised one, which is the substitution P6.3 exists to prevent.
    result = run.completed
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

    # #212 MWRK003: a sling that exits 0 DISPATCHED. Whether the claim has been
    # OBSERVED yet is a separate question, and it is not fatal. The claim does
    # NOT land as a source-bead `assignee` -- work-briefed associates it on the
    # molecule it mints and on the source's `execution.work_associated` event.
    # Reading `assignee` and calling the claimless source a FATAL failure (the
    # old behaviour) reported every successful live dispatch as failed, and --
    # because it raised BEFORE provenance was written -- made the retry re-sling
    # and mint a duplicate input convoy (#213). So: write provenance on exit 0
    # (mirrors #184's UNKNOWN-not-failure contract), and report the claim as
    # `observed` or `pending` rather than raising.
    try:
        beads_after = _beads(ctx)
    except WorkError:
        beads_after = ()
    claim_observed = _claim_observed(beads_after, plan.bead_id)

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
    payload: dict[str, object] = {
        "actual_effects": actual_effects,
        "applied": True,
        "claim": "observed" if claim_observed else "pending",
        "effect_plan": plan.to_dict(),
        "provenance": provenance.to_dict(),
        "trace_id": plan.trace_id,
    }
    diagnostics: list[dict[str, object]] = elapsed_diagnostics()
    drift = dispatch_elapsed_warning(elapsed_seconds, policy=active_policy)
    if drift is not None:
        # mc-u9eun: the cost has outgrown three successive budgets (120 -> 200 ->
        # 243.51) and each was discovered in production, because nothing reported
        # the ACTUAL cost while it still fit. This is that report -- now against a
        # warn threshold that kills nothing, so growing past it costs a line of
        # output instead of a dispatch.
        diagnostics.append(
            _diagnostic(
                ctx,
                Severity.WARN,
                DISPATCH_SLOW_CODE,
                "The dispatch succeeded and ran past its warn threshold.",
                brief_id=plan.target_brief_id,
                bead_id=plan.bead_id,
                detail=drift,
            ).to_dict()
        )
    if not claim_observed:
        diagnostics.append(
            _diagnostic(
                ctx,
                Severity.WARN,
                "MWRK003",
                "The dispatch succeeded but the claim has not been observed yet.",
                brief_id=plan.target_brief_id,
                bead_id=plan.bead_id,
                data_location=_canonical_bead_location(ctx),
                detail=(
                    "no molecule, convoy, or execution.work_associated on the source yet; "
                    "the operator pool may not have picked it up -- recheck rather than retry"
                ),
                suggested_next_command=f"mctl work status {plan.target_brief_id} --json",
            ).to_dict()
        )
    if diagnostics:
        payload["diagnostics"] = diagnostics
    return payload


def _claim_observed(beads: tuple[Bead, ...], source_id: str) -> bool:
    """Whether a claim on this dispatch is observable yet (#212).

    True as soon as ANY real claim signal is present -- an assignee, the
    source's `execution.work_associated` event, or an open child molecule /
    convoy. None of these having landed is `pending`, not a failure: the claim
    can land minutes after an exit-0 sling (~210s measured, #212).
    """
    source = {bead.id: bead for bead in beads}.get(source_id)
    if source is not None and (source.has_active_assignee or _source_work_associated(source)):
        return True
    return _open_child_workflow(beads, source_id) is not None


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
    ctx: MctlContext | None,
    *,
    brief_id: str,
    source: Bead | None,
    synthetic_self_source: bool,
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

    `synthetic_self_source` is required rather than defaulted, and it narrows
    #173's exemption to the case #173 was actually about (M3, 2026-08-28).
    #173 keyed on `source.id == brief_id`, which is true of TWO different
    briefs: the sourceless one the fallback made its own source (meaningless
    question, exempt), and one that EXPLICITLY names its own id among its
    source dependencies. The second has a real `source_id`, so MWRK011 never
    fires, nothing contradicts MWRK013, and suppressing it hands back exactly
    the closed-bead-reports-ready defect #157 closed. Measured across the
    mathcity, hq and hecke stores on 2026-08-28: 46,550 beads, ZERO of them
    self-naming -- so this is a latent hole rather than a live one, and it is
    reported as latent. No default, because the safe answer differs per call
    site and a caller that forgot to say which one it is would silently get the
    permissive one.
    """
    if source is None or source.is_open:
        return []
    if source.id == brief_id and synthetic_self_source:
        # #173, and the regression is mine: I added this check in #157 without
        # considering that a SOURCELESS brief is made its own source bead
        # (the `source_id = brief_id` fallback in `_work_item`). `briefs_relay_adjudication`
        # then closes it -- closing the brief is what adjudication IS -- so the
        # brief became its own closed source and could never be dispatched.
        # CT4.5 mandates adjudicating before dispatch, so the prescribed
        # workflow walked straight into it.
        #
        # When the brief IS its own source, "is the source closed?" reduces to
        # "is the brief closed?", which adjudication guarantees. The question is
        # not merely inconvenient here; it is MEANINGLESS, and answering it
        # produces MWRK013 sitting beside MWRK011 -- "the source is closed" next
        # to "there is no source" -- two blockers describing incompatible
        # worlds.
        #
        # The fallback is NOT the defect and I checked before assuming it was:
        # `source_id` feeds `WorkItem.bead_id` (work.py:708) and nine other
        # readers, so removing it would empty that field in every payload for a
        # sourceless brief. MWRK011 already reports the real problem.
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
    skipped_sources: tuple[str, ...] = ()
    #: Whether the brief became its own source through the MWRK011 fallback
    #: below, as opposed to naming itself in `source_dependencies`. Recorded
    #: here, where the two are still distinguishable, because by the time
    #: `_closed_source_blockers` sees the bead they look identical.
    synthetic_self_source = False
    if brief.source_dependencies:
        # #228: WALK the sources, skipping any already being worked, instead of
        # blindly taking source[0] forever. Otherwise a multi-source brief
        # re-slings its first source on every call and never reaches the rest.
        source_id, skipped_sources = _select_dispatch_source(
            ctx, beads, bead_by_id, brief.source_dependencies
        )
    else:
        source_id = ""
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
        synthetic_self_source = True
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
    blockers.extend(
        _closed_source_blockers(
            ctx,
            brief_id=brief_id,
            source=source,
            synthetic_self_source=synthetic_self_source,
        )
    )
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
        skipped_sources=skipped_sources,
    )


def _bead_metadata(bead: Bead) -> Mapping[str, object]:
    metadata = bead.raw.get("metadata") if isinstance(bead.raw, Mapping) else None
    return metadata if isinstance(metadata, Mapping) else {}


def _metadata_str(metadata: Mapping[str, object], key: str) -> str | None:
    value = metadata.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _is_truthy_flag(value: object) -> bool:
    """Whether a metadata flag reads as set. `gc` writes booleans and strings."""
    if isinstance(value, bool):
        return value
    return isinstance(value, str) and value.strip().lower() in {"true", "1", "yes"}


def _open_child_workflow(beads: tuple[Bead, ...], source_id: str) -> Bead | None:
    """An open child molecule / synthetic input convoy already working this source.

    #228: the earlier version keyed SOLELY on `gc.root_bead_id == source_id`,
    which is the wrong edge and made this check blind to every real molecule.
    A real molecule ROOT carries NO `gc.root_bead_id` -- its STEPS do, and they
    point at the RUN root, never at the source bead (see `mctl_core.molecules`).
    The root records the source it works as the sling var `gc.var.source_bead`.
    So a source already being worked read as dispatchable, and the resolver
    re-slung it: the measured double-dispatch of mc-2xuc (tdupu/mathcity#228).

    Any of the following, open, means the source is already in flight:

    * a molecule ROOT whose `gc.var.source_bead` is this source (the real edge);
    * a bead pointing at this source via `gc.root_bead_id` (the legacy edge,
      kept so a step that genuinely roots at the source still counts, and so
      pre-existing fixtures built on that shape keep their meaning);
    * a synthetic input convoy (`gc.synthetic`) that DEPENDS ON this source --
      the convoy a prior partial dispatch left behind (#213). Detecting it is
      the pre-sling half of #192's adopt-don't-duplicate contract at this call
      site: an existing open convoy refuses a re-sling instead of minting a
      second one.
    """
    for bead in beads:
        if bead.id == source_id or not bead.is_open:
            continue
        metadata = _bead_metadata(bead)
        if is_molecule_root(bead) and _metadata_str(metadata, "gc.var.source_bead") == source_id:
            return bead
        if bead.workflow_root_id == source_id:
            return bead
        if _is_truthy_flag(metadata.get("gc.synthetic")) and source_id in bead.source_dependencies:
            return bead
    return None


def _source_work_associated(source: Bead) -> bool:
    """Whether the source carries an `execution.work_associated` claim event.

    This is the claim signal the work-briefed path actually writes (#212/#228):
    the association lands here (and on the minted molecule), NEVER as a source
    `assignee`. Reading it lets the claim observer recognise a real handoff.
    """
    value = _bead_metadata(source).get("execution.work_associated")
    if isinstance(value, str):
        return bool(value.strip())
    return value not in (None, False, "", [], {})


def _has_dispatch_provenance(ctx: MctlContext, source_id: str) -> bool:
    """Whether this source already carries a dispatch-provenance record.

    Swallows a malformed-provenance error as "already dispatched" for WALK
    purposes: the walk must not silently re-sling a source whose provenance
    merely failed to parse. The selected source's own path re-surfaces that
    error as a real blocker.
    """
    try:
        return read_dispatch_provenance(ctx, source_id, required=False) is not None
    except ProvenanceError:
        return True


def _source_dispatchable(
    ctx: MctlContext, beads: tuple[Bead, ...], source: Bead | None, source_id: str
) -> bool:
    """Whether this source can be slung right now -- not already in flight.

    A source is NOT dispatchable when it is missing, closed, already claimed,
    already has an open child molecule/convoy, or already carries dispatch
    provenance. The resolver walks PAST such sources to the next candidate.
    """
    if source is None or not source.is_open:
        return False
    if source.has_active_assignee:
        return False
    if _open_child_workflow(beads, source_id) is not None:
        return False
    if _has_dispatch_provenance(ctx, source_id):
        return False
    return True


def _select_dispatch_source(
    ctx: MctlContext,
    beads: tuple[Bead, ...],
    bead_by_id: Mapping[str, Bead],
    sources: tuple[str, ...],
) -> tuple[str, tuple[str, ...]]:
    """Walk a brief's sources, skipping any already being worked (#228).

    Returns the first dispatchable source and the sources skipped to reach it.
    When EVERY source is already in flight the brief has nothing new to
    dispatch: it falls back to the first source so its own blocker (MWRK002 /
    MWRK001 / already-dispatched) is reported and re-dispatch is refused --
    P1.21 honoured. The skipped list is surfaced so the skip is named, not
    silent.
    """
    skipped: list[str] = []
    for source_id in sources:
        if _source_dispatchable(ctx, beads, bead_by_id.get(source_id), source_id):
            return source_id, tuple(skipped)
        skipped.append(source_id)
    return sources[0], tuple(sources[1:])


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
    """The `gc sling work-briefed` command Path A records as provenance.

    `brief_root` is read out of `artifact_layout()` rather than composed here.
    That is the whole point: `artifact_layout()` is the single resolver every
    adjudication surface reads through, so taking the deposit root from it
    makes the writer and the reader agree BY CONSTRUCTION rather than by two
    string literals that happen to match today. Composing
    `rig_root / ".beads" / "briefs"` a second time would be the second
    resolution rule `redundant_state` exists to prevent -- and it is precisely
    how mc-4ovmy stranded eighteen briefs.

    `artifact_root` keeps its own value and is deliberately NOT unified with
    it. It is the build/stage root, it wants per-bead scoping (gsp-1bmxuz),
    and the shared rig-level value below is a separate known defect with its
    own bead; folding the two back together is what created this one.
    """
    brief_slug = item.brief_id
    artifact_root = str(ctx.rig_root / ".beads" / "briefs")
    brief_root = str(artifact_layout(ctx).root)
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
        f"brief_root={brief_root}",
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
