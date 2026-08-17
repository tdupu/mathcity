"""Canonical, read-only brief inspection core for mctl."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

from .beads import Bead, BeadReadError, read_beads
from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .policy_refs import BRIEF_POLICY_REFERENCES, PolicyReference
from .redundant_state import (
    RedundantArtifact,
    artifact_layout,
    legacy_nonterminal_rows,
    orphan_decision_cache_ids,
    orphan_markdown_cache_ids,
    scan_artifacts,
)


@dataclass(frozen=True)
class BriefFilters:
    status: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class BriefRecord:
    brief_id: str
    bead_id: str
    title: str
    status: str
    decision_state: str
    labels: tuple[str, ...]
    created_at: str | None
    updated_at: str | None
    redundant_artifacts: tuple[RedundantArtifact, ...]
    policy_references: tuple[PolicyReference, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "bead_id": self.bead_id,
            "brief_id": self.brief_id,
            "canonical_source": "bead_store",
            "created_at": self.created_at,
            "decision_state": self.decision_state,
            "labels": list(self.labels),
            "policy_references": [reference.to_dict() for reference in self.policy_references],
            "redundant_artifacts": [artifact.to_dict() for artifact in self.redundant_artifacts],
            "status": self.status,
            "title": self.title,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class BriefOption:
    id: str
    label: str
    description: str
    enabled: bool
    disabled_reason: Diagnostic | None

    def to_dict(self) -> dict[str, object]:
        return {
            "description": self.description,
            "disabled_reason": (
                self.disabled_reason.to_dict() if self.disabled_reason is not None else None
            ),
            "enabled": self.enabled,
            "id": self.id,
            "label": self.label,
        }


@dataclass(frozen=True)
class DoctorReport:
    records: tuple[BriefRecord, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def severity_counts(self) -> dict[str, int]:
        return {severity.value: sum(item.severity is severity for item in self.diagnostics) for severity in Severity}

    def to_dict(self) -> dict[str, object]:
        per_brief = []
        brief_ids = [record.brief_id for record in self.records]
        for diagnostic in self.diagnostics:
            brief_id = diagnostic.facts.get("brief_id")
            if brief_id and brief_id not in brief_ids:
                brief_ids.append(brief_id)
        for brief_id in brief_ids:
            per_brief.append(
                {
                    "brief_id": brief_id,
                    "diagnostics": [
                        diagnostic.to_dict()
                        for diagnostic in self.diagnostics
                        if diagnostic.facts.get("brief_id") == brief_id
                    ],
                }
            )
        return {
            "briefs": [record.to_dict() for record in self.records],
            "brief_diagnostics": per_brief,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "severity_counts": self.severity_counts,
            "trace_id": self.diagnostics[0].trace_id if self.diagnostics else None,
        }


class BriefError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def list_briefs(ctx: MctlContext, filters: BriefFilters) -> tuple[BriefRecord, ...]:
    records = _records(ctx)
    return tuple(record for record in records if _matches(record, filters))


def show_brief(ctx: MctlContext, brief_id: str) -> BriefRecord:
    for record in _records(ctx):
        if record.brief_id == brief_id:
            return record
    raise BriefError(
        _diagnostic(
            ctx,
            Severity.FATAL,
            "MBRF010",
            f"No canonical brief bead named {brief_id!r} was found.",
            brief_id=brief_id,
            suggested_next_command="mctl briefs list --json",
        )
    )


def brief_options(ctx: MctlContext, brief_id: str) -> tuple[BriefOption, ...]:
    record = show_brief(ctx, brief_id)
    doctor = doctor_briefs(ctx, brief_id)
    blocker = next(
        (diagnostic for diagnostic in doctor.diagnostics if diagnostic.severity in {Severity.ERROR, Severity.FATAL}),
        None,
    )
    mutation_enabled = blocker is None and record.decision_state == "pending"
    if blocker is None and record.decision_state != "pending":
        blocker = _diagnostic(
            ctx,
            Severity.ERROR,
            "MBRF011",
            f"Brief {brief_id!r} is not pending adjudication.",
            brief_id=brief_id,
            data_location=_canonical_bead_location(ctx),
            policy_ref="B2.2",
        )
    return (
        BriefOption("validate", "Validate", "Inspect canonical state and cache drift.", True, None),
        BriefOption("adjudicate", "Adjudicate", "Record a human verdict on the canonical brief bead.", mutation_enabled, blocker),
        BriefOption("defer", "Defer", "Set a timed defer window on the canonical brief bead.", mutation_enabled, blocker),
        BriefOption("dispatch-work", "Dispatch work", "Dispatch work unlocked by the canonical brief bead.", mutation_enabled, blocker),
    )


def doctor_briefs(ctx: MctlContext, brief_id: str | None) -> DoctorReport:
    beads = _beads(ctx)
    records = _records(ctx, beads)
    if brief_id is not None:
        records = tuple(record for record in records if record.brief_id == brief_id)
        if not records:
            raise BriefError(
                _diagnostic(ctx, Severity.FATAL, "MBRF010", f"No canonical brief bead named {brief_id!r} was found.", brief_id=brief_id)
            )
    bead_by_id = {bead.id: bead for bead in beads}
    layout = artifact_layout(ctx)
    diagnostics: list[Diagnostic] = []
    for record in records:
        bead = bead_by_id[record.bead_id]
        if not bead.source_dependencies:
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF004", "Brief bead has no source dependency.", brief_id=record.brief_id, data_location=_canonical_bead_location(ctx), policy_ref="B2.1"))
        if bead.status.lower() in {"closed", "done"} and not _has_verdict(bead):
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF005", "Closed brief bead has no recorded verdict.", brief_id=record.brief_id, data_location=_canonical_bead_location(ctx), policy_ref="B2.2"))
        for artifact in record.redundant_artifacts:
            if artifact.kind == "stack_index" and artifact.state == "stale":
                diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF001", "Stack index row points at a missing file.", brief_id=record.brief_id, data_location=str(artifact.path), policy_ref="B2.8"))
            if artifact.kind == "stack_index" and artifact.state == "inconsistent":
                code = "MBRF006" if record.decision_state == "adjudicated" else "MBRF007"
                message = "Closed/adjudicated brief appears in presentable stack." if code == "MBRF006" else "Deferred brief appears before defer expiry."
                diagnostics.append(_diagnostic(ctx, Severity.ERROR, code, message, brief_id=record.brief_id, data_location=str(artifact.path), policy_ref="B2.3" if code == "MBRF006" else "B2.7"))
    for cached_id in orphan_decision_cache_ids(layout):
        if brief_id is not None and cached_id != brief_id:
            continue
        bead = bead_by_id.get(cached_id)
        if bead is None:
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF002", "Brief cache file exists with no matching decision bead.", brief_id=cached_id, data_location=str(layout.decisions / f"{cached_id}.toml"), policy_ref="B2.1"))
        elif bead.issue_type != "decision":
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF003", "Brief cache maps to a bead that is not type=decision.", brief_id=cached_id, data_location=str(layout.decisions / f"{cached_id}.toml"), policy_ref="B2.1"))
    for cached_id, path in orphan_markdown_cache_ids(layout):
        if brief_id is not None and cached_id != brief_id:
            continue
        if cached_id not in bead_by_id:
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF002", "Brief cache file exists with no matching decision bead.", brief_id=cached_id, data_location=str(path), policy_ref="B2.1"))
        elif bead_by_id[cached_id].issue_type != "decision":
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF003", "Brief cache maps to a bead that is not type=decision.", brief_id=cached_id, data_location=str(path), policy_ref="B2.1"))
    legacy_rows = legacy_nonterminal_rows(layout)
    if brief_id is not None:
        legacy_rows = tuple(row for row in legacy_rows if _row_slug(row) == brief_id)
    if legacy_rows:
        for row in legacy_rows:
            slug = _row_slug(row)
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF008", "Legacy decisions-track row is non-terminal and not migration-visible.", brief_id=slug, data_location=str(layout.legacy_manifest), policy_ref="B2.10"))
        diagnostics.append(_diagnostic(ctx, Severity.FATAL, "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED", "Legacy decisions-track state requires the authorized #38 migration proof/canary.", data_location=str(layout.legacy_manifest), policy_ref="B2.10", suggested_next_command="bash tests/decisions-track-migration/smoke_test.sh"))
    return DoctorReport(records, tuple(diagnostics))


def _records(ctx: MctlContext, beads: tuple[Bead, ...] | None = None) -> tuple[BriefRecord, ...]:
    layout = artifact_layout(ctx)
    beads = _beads(ctx) if beads is None else beads
    return tuple(
        BriefRecord(
            brief_id=bead.id,
            bead_id=bead.id,
            title=bead.title,
            status=bead.status,
            decision_state=_decision_state(bead),
            labels=bead.labels,
            created_at=bead.created_at,
            updated_at=bead.updated_at,
            redundant_artifacts=scan_artifacts(layout, bead.id, _decision_state(bead)),
            policy_references=BRIEF_POLICY_REFERENCES,
        )
        for bead in beads
        if bead.is_brief
    )


def _beads(ctx: MctlContext) -> tuple[Bead, ...]:
    try:
        return read_beads(ctx.rig_root, fixture_path=ctx.beads_fixture)
    except BeadReadError as error:
        raise BriefError(_diagnostic(ctx, Severity.FATAL, "MBRF012", str(error))) from error


def _canonical_bead_location(ctx: MctlContext) -> str:
    return f"bd list --json (rig database {ctx.rig_db})"


def _matches(record: BriefRecord, filters: BriefFilters) -> bool:
    if filters.status and filters.status not in {record.status, record.decision_state}:
        return False
    return not filters.label or filters.label in record.labels


def _decision_state(bead: Bead) -> str:
    status = bead.status.lower()
    if status in {"closed", "done"}:
        return "adjudicated" if _has_verdict(bead) else "malformed"
    if status == "deferred" or _defer_until(bead):
        return "deferred"
    return "pending"


def _has_verdict(bead: Bead) -> bool:
    for key in ("verdict", "decision", "recorded_verdict"):
        value = bead.raw.get(key)
        if isinstance(value, str) and value:
            return True
    metadata = bead.raw.get("metadata")
    return isinstance(metadata, dict) and any(
        isinstance(metadata.get(key), str) and metadata[key] for key in ("verdict", "decision", "recorded_verdict")
    )


def _defer_until(bead: Bead) -> bool:
    for key in ("deferred_until", "defer_until"):
        value = bead.raw.get(key)
        if isinstance(value, str) and value >= date.today().isoformat():
            return True
    return False


def _row_slug(row: dict[str, object]) -> str | None:
    for key in ("slug", "brief_id", "id"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _diagnostic(
    ctx: MctlContext,
    severity: Severity,
    code: str,
    message: str,
    *,
    brief_id: str | None = None,
    data_location: str | None = None,
    policy_ref: str | None = None,
    suggested_next_command: str | None = None,
) -> Diagnostic:
    facts = {
        "city_path": str(ctx.city_root),
        "implementation_provenance": "mctl Slice 2 read-only brief inspection",
        "rig_name": ctx.rig_id,
        "rig_path": str(ctx.rig_root),
    }
    if brief_id:
        facts["brief_id"] = brief_id
        facts["bead_id"] = brief_id
    if data_location:
        facts["data_location"] = data_location
    if policy_ref:
        facts["policy_reference"] = policy_ref
    if suggested_next_command:
        facts["suggested_next_command"] = suggested_next_command
    return Diagnostic(severity, code, message, facts=facts, trace_id=ctx.trace_id)
