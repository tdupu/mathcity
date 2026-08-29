"""mc-p0wps: typed bead-write verbs -- close, hold, release.

The mctl MCP surface could dispatch work IN but had no verb to close, hold, or
release a bead: `bead_comment` is append-only, and the two create paths mint new
beads. This module fills that P7.3 gap behind the interface rather than routing
around it with a shell-out.

Kept in its own module (not folded into `effects.py`), the same reason
`bead_comments.py` and `defect_beads.py` are: each is a distinct write seam that
reuses the shared effect-plan machinery and adds only its own refusals.

`plan_bead_close` mirrors `plan_molecule_cancel` (effects.py) but closes ONE
bead -- cascade-close is `molecule_cancel`'s explicit job. Two conditional
refusals, both visible in dry-run because they are blocking `preconditions`
(`_raise_if_blocked` stops the dry run and the apply alike):

- a molecule ROOT with open steps (`MBCL_ROOT_HAS_OPEN_STEPS`, FATAL). `force`
  does NOT bypass it -- it is the false-success guard mc-i9bwz Sec 5.1 exists to
  create; deliberate cascade-close is `molecule_cancel` (adjudicated 2026-08-28).
- a bead blocked by open dependencies (`MBCL_BLOCKED_BY_OPEN_DEPS`, ERROR).
  `force` downgrades ONLY this one, and the apply passes `bd update --force`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .beads import BeadLabelChange, BeadUpdate, read_beads
from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .effects import EffectPlan, JsonlWrite, MutationError, _diagnostic, _now
from .molecules import (
    MOLECULE_BEAD_TYPE,
    is_closed_status,
    is_molecule_root,
    open_steps_of,
)


@dataclass(frozen=True)
class BeadCloseInput:
    bead_id: str
    reason: str | None = None
    force: bool = False


def plan_bead_close(ctx: MctlContext, request: BeadCloseInput) -> EffectPlan:
    """Plan closing ONE bead, with the root-open-steps and blocked-by-deps guards.

    Every branch is a read (the bead scan) or pure computation -- no `bd`,
    nothing that could make a dry run mutate (#188). Refusals are blocking
    `preconditions`, so a dry run previews them and refuses to "succeed".
    """
    bead_id = request.bead_id.strip()
    beads = read_beads(
        ctx.rig_root, fixture_path=ctx.beads_fixture, issue_type=MOLECULE_BEAD_TYPE
    )
    bead = next((b for b in beads if b.id == bead_id), None)

    if bead is None:
        return _bead_close_plan(
            ctx,
            bead_id,
            (
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MBCL_NO_SUCH_BEAD",
                    f"No bead {bead_id!r} in this rig -- nothing was read and nothing "
                    "will be written.",
                    brief_id=bead_id,
                    bead_id=bead_id,
                ),
            ),
            (),
        )

    # The false-success guard (mc-i9bwz Sec 5.1). A molecule root with open steps
    # is NEVER closed here -- that is a cascade, which is `molecule_cancel`'s job.
    # force does NOT reach this refusal: it is deps-only (adjudicated 2026-08-28).
    if is_molecule_root(bead):
        open_steps = open_steps_of(bead_id, beads)
        if open_steps:
            named = ", ".join(step.id for step in open_steps)
            return _bead_close_plan(
                ctx,
                bead_id,
                (
                    _diagnostic(
                        ctx,
                        Severity.FATAL,
                        "MBCL_ROOT_HAS_OPEN_STEPS",
                        f"{bead_id!r} is a molecule ROOT with {len(open_steps)} open "
                        f"step(s): {named}. Refusing to close it -- closing a root with "
                        "open steps would report a false success. Use molecule_cancel to "
                        "cancel the whole molecule.",
                        brief_id=bead_id,
                        bead_id=bead_id,
                        suggested_next_command="molecule_cancel dry_run=false",
                    ),
                ),
                (),
            )

    preconditions: list[Diagnostic] = []
    open_deps = _open_dependencies(bead.source_dependencies, beads)
    if open_deps and not request.force:
        named = ", ".join(open_deps)
        preconditions.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MBCL_BLOCKED_BY_OPEN_DEPS",
                f"{bead_id!r} is blocked by {len(open_deps)} open dependenc(ies): "
                f"{named}. Refusing to close a blocked bead; pass force=true to close "
                "anyway (bd's own --force gate).",
                brief_id=bead_id,
                bead_id=bead_id,
                suggested_next_command="bead_close force=true dry_run=false",
            )
        )

    metadata: dict[str, str] = {
        "mctl_closed_at": _now(),
        "mctl_trace_id": ctx.trace_id,
    }
    reason_text = (request.reason or "").strip()
    if reason_text:
        metadata["mctl_close_reason"] = reason_text

    update = BeadUpdate(
        bead_id,
        status="closed",
        metadata=metadata,
        if_status=bead.status,
        force=request.force,
    )
    return _bead_close_plan(ctx, bead_id, tuple(preconditions), (update,))


@dataclass(frozen=True)
class BeadHoldInput:
    bead_id: str
    label: str = "hold"


@dataclass(frozen=True)
class BeadReleaseInput:
    bead_id: str
    label: str = "hold"


def plan_bead_hold(ctx: MctlContext, request: BeadHoldInput) -> EffectPlan:
    """Plan setting a `hold:*` label on an existing bead (mc-qcnaz option A).

    A hold is a LABEL, not a status change: `apply_bead_label` add is
    idempotent, so a second hold is a no-op and there is no `if_status` race to
    guard. Two FATAL refusals, raised before the plan is built so a dry run
    previews them: a slashed label (MBRF033 -- colon-form or bare only) and a
    bead that does not exist.
    """
    return _plan_label_change(
        ctx,
        bead_id=request.bead_id,
        label=request.label,
        action="add",
        operation="bead.hold",
        slash_code="MBHD_LABEL_HAS_SLASH",
        missing_code="MBHD_NO_SUCH_BEAD",
    )


def plan_bead_release(ctx: MctlContext, request: BeadReleaseInput) -> EffectPlan:
    """Plan clearing a `hold:*` label from an existing bead (mc-qcnaz option A).

    The inverse of `plan_bead_hold`: `apply_bead_label` remove is idempotent, so
    releasing a bead that never held is a no-op. One FATAL refusal beyond the
    slash check -- a bead that does not exist.
    """
    return _plan_label_change(
        ctx,
        bead_id=request.bead_id,
        label=request.label,
        action="remove",
        operation="bead.release",
        slash_code="MBRL_LABEL_HAS_SLASH",
        missing_code="MBRL_NO_SUCH_BEAD",
    )


def _plan_label_change(
    ctx: MctlContext,
    *,
    bead_id: str,
    label: str,
    action: str,
    operation: str,
    slash_code: str,
    missing_code: str,
) -> EffectPlan:
    bead_id = bead_id.strip()
    label = label.strip()
    facts = {
        "city_path": str(ctx.city_root),
        "rig_name": ctx.rig_id,
        "bead_id": bead_id,
        "label": label,
    }
    if "/" in label:
        raise MutationError(
            Diagnostic(
                Severity.FATAL,
                slash_code,
                f"A label may not contain '/': {label!r} (MBRF033 -- colon-form or "
                "bare only).",
                hint="Use a bare label like `hold` or a colon form like `hold:soak`.",
                facts=facts,
                trace_id=ctx.trace_id,
            )
        )
    if not _bead_exists(ctx, bead_id):
        raise MutationError(
            Diagnostic(
                Severity.FATAL,
                missing_code,
                f"No bead {bead_id!r} exists to {action} a label on.",
                hint="A hold must attach to an existing bead; check the id.",
                facts=facts,
                trace_id=ctx.trace_id,
            )
        )
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation=operation,
        target_brief_id=bead_id,
        preconditions=(),
        bead_updates=(),
        cache_updates=(),
        event_writes=(),
        trace_writes=(),
        bead_label_changes=(BeadLabelChange(bead_id=bead_id, label=label, action=action),),
    )


def _bead_exists(ctx: MctlContext, bead_id: str) -> bool:
    """True if a bead of ANY type carries this id (mirror bead_comments).

    `issue_type=None` reads every kind: a hold can be placed on a task, a
    decision brief, or a mirror bead, so the existence check must not narrow.
    """
    for bead in read_beads(ctx.rig_root, fixture_path=ctx.beads_fixture):
        if bead.id == bead_id:
            return True
    return False


def _open_dependencies(dep_ids, beads) -> tuple[str, ...]:
    """The dependency ids that resolve to a still-open bead in this rig.

    Reimplemented as a plan-time read (bd's own blocked refusal fires only at
    apply time, so it would never show in a dry run). A dependency this rig
    cannot resolve is NOT counted as blocking: "we could not see it" is not "it
    is open", and inventing a block would be a plausible-refusal failure.
    """
    by_id = {b.id: b for b in beads}
    open_deps: list[str] = []
    for dep_id in dep_ids:
        dep = by_id.get(dep_id)
        if dep is not None and not is_closed_status(dep.status):
            open_deps.append(dep_id)
    return tuple(open_deps)


def _bead_close_plan(
    ctx: MctlContext,
    bead_id: str,
    preconditions: tuple[Diagnostic, ...],
    updates: tuple[BeadUpdate, ...],
) -> EffectPlan:
    planned_effects = [update.to_dict() for update in updates]
    event_row = {
        "brief_id": bead_id,
        "operation": "bead.close",
        "planned_effects": planned_effects,
        "trace_id": ctx.trace_id,
    }
    trace_row = {
        "brief_id": bead_id,
        "city_path": str(ctx.city_root),
        "operation": "bead.close",
        "planned_effects": planned_effects,
        "rig_name": ctx.rig_id,
        "trace_id": ctx.trace_id,
    }
    today = date.today().isoformat()
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation="bead.close",
        target_brief_id=bead_id,
        preconditions=preconditions,
        bead_updates=updates,
        cache_updates=(),
        event_writes=(
            JsonlWrite(
                "event_write",
                ctx.rig_root / ".beads" / "mctl" / "events" / f"{today}.jsonl",
                event_row,
            ),
        ),
        trace_writes=(
            JsonlWrite(
                "trace_write",
                ctx.rig_root / ".beads" / "mctl" / "traces" / f"{today}.jsonl",
                trace_row,
            ),
        ),
    )
