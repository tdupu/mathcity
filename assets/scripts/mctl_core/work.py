"""Work readiness, provenance, and dispatch controls for mctl."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Mapping

from .beads import BD_LIST_ARGS, Bead, BeadReadError, read_beads
from .briefs import BriefError, doctor_briefs
from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .events import append_jsonl
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


class WorkError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def ready_work(ctx: MctlContext) -> tuple[WorkItem, ...]:
    return tuple(
        item
        for item in (_work_item(ctx, bead.id) for bead in _decision_beads(ctx))
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


def apply_dispatch_plan(ctx: MctlContext, plan: WorkDispatchPlan) -> dict[str, object]:
    if ctx.beads_fixture is None:
        raise WorkError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MWRK_LIVE_DISPATCH_NOT_ENABLED",
                "Live mctl work dispatch requires a dedicated runtime canary before it is enabled.",
                brief_id=plan.target_brief_id,
                bead_id=plan.bead_id,
                suggested_next_command=(
                    f"mctl work dispatch {plan.target_brief_id} --dry-run --json"
                ),
            )
        )
    provenance = write_dispatch_provenance(
        ctx,
        bead_id=plan.bead_id,
        brief_id=plan.target_brief_id,
        observed_at=str(plan.provenance["created_at"]),
        formula_invocation=plan.formula_invocation,
    )
    event_row = {
        "bead_id": plan.bead_id,
        "brief_id": plan.target_brief_id,
        "formula_invocation": plan.formula_invocation,
        "operation": plan.operation,
        "provenance_path": str(provenance.path),
        "trace_id": plan.trace_id,
    }
    trace_row = {
        "actual_effects": [
            {"kind": "provenance_write", "path": str(provenance.path)},
            {"kind": "event_write", "path": str(plan.event_path)},
        ],
        "bead_id": plan.bead_id,
        "brief_id": plan.target_brief_id,
        "formula_invocation": plan.formula_invocation,
        "operation": plan.operation,
        "trace_id": plan.trace_id,
    }
    append_jsonl(plan.event_path, event_row)
    append_jsonl(plan.trace_path, trace_row)
    return {
        "actual_effects": trace_row["actual_effects"],
        "applied": True,
        "effect_plan": plan.to_dict(),
        "provenance": provenance.to_dict(),
        "trace_id": plan.trace_id,
    }


def _work_item(
    ctx: MctlContext, brief_id: str, *, include_provenance_errors: bool = True
) -> WorkItem:
    beads = _beads(ctx)
    bead_by_id = {bead.id: bead for bead in beads}
    brief = bead_by_id.get(brief_id)
    if brief is None or not brief.is_brief:
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
    try:
        blockers.extend(_blocking_doctor_diagnostics(doctor_briefs(ctx, brief_id).diagnostics))
    except BriefError as error:
        raise WorkError(error.diagnostic) from error
    source_id = brief.source_dependencies[0] if brief.source_dependencies else ""
    if not source_id:
        blockers.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MWRK002",
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
                "MWRK003",
                "The source bead named by the brief dependency was not found.",
                brief_id=brief_id,
                bead_id=source_id,
                data_location=_canonical_bead_location(ctx),
            )
        )
    if not _approved_for_dispatch(brief):
        blockers.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MWRK001",
                "Brief has no approving verdict for work dispatch.",
                brief_id=brief_id,
                bead_id=source_id,
                data_location=_canonical_bead_location(ctx),
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


def _decision_beads(ctx: MctlContext) -> tuple[Bead, ...]:
    return tuple(bead for bead in _beads(ctx) if bead.is_brief)


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
    verdict = _verdict(bead)
    return bead.status.lower() in {"closed", "done"} and verdict in {"approve", "approved", "accept", "accepted"}


def _verdict(bead: Bead) -> str | None:
    for key in ("verdict", "decision", "recorded_verdict"):
        value = bead.raw.get(key)
        if isinstance(value, str) and value:
            return value.strip().lower()
    metadata = bead.raw.get("metadata")
    if isinstance(metadata, dict):
        for key in ("verdict", "decision", "recorded_verdict"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                return value.strip().lower()
    return None


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
