"""Canonical, read-only brief inspection core for mctl."""
from __future__ import annotations

from dataclasses import dataclass
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Iterable

from .beads import BD_LIST_ARGS, Bead, BeadReadError, read_beads
from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .policy_refs import BRIEF_POLICY_REFERENCES, PolicyReference
from .redundant_state import (
    ArtifactLayout,
    LegacyManifestState,
    RedundantArtifact,
    artifact_layout,
    legacy_manifest_state,
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


@dataclass(frozen=True)
class ValidationReport:
    """Proof that canonical and redundant brief state still agree.

    `briefs doctor` reports drift across the whole rig; validate is the
    stricter per-brief gate creation and mutation workflows lean on, so it
    composes doctor and adds the invariants doctor deliberately leaves out.
    Read-only: it never repairs what it reports.
    """

    scope: str
    records: tuple[BriefRecord, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def severity_counts(self) -> dict[str, int]:
        return {
            severity.value: sum(item.severity is severity for item in self.diagnostics)
            for severity in Severity
        }

    @property
    def valid(self) -> bool:
        return not any(
            diagnostic.severity in {Severity.ERROR, Severity.FATAL}
            for diagnostic in self.diagnostics
        )

    def to_dict(self) -> dict[str, object]:
        brief_ids = [record.brief_id for record in self.records]
        for diagnostic in self.diagnostics:
            brief_id = diagnostic.facts.get("brief_id")
            if brief_id and brief_id not in brief_ids:
                brief_ids.append(brief_id)
        return {
            "briefs": [record.to_dict() for record in self.records],
            "brief_diagnostics": [
                {
                    "brief_id": brief_id,
                    "diagnostics": [
                        diagnostic.to_dict()
                        for diagnostic in self.diagnostics
                        if diagnostic.facts.get("brief_id") == brief_id
                    ],
                }
                for brief_id in brief_ids
            ],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "scope": self.scope,
            "severity_counts": self.severity_counts,
            "valid": self.valid,
        }


class BriefError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def list_briefs(ctx: MctlContext, filters: BriefFilters) -> tuple[BriefRecord, ...]:
    records = _records(ctx)
    return tuple(record for record in records if _matches(record, filters))


def show_brief(ctx: MctlContext, brief_id: str) -> BriefRecord:
    return _find_record(ctx, _records(ctx), brief_id)


def brief_command_diagnostics(ctx: MctlContext, records: Iterable[BriefRecord]) -> tuple[Diagnostic, ...]:
    layout = artifact_layout(ctx)
    legacy_state = legacy_manifest_state(layout)
    brief_ids = {record.brief_id for record in records}
    return _legacy_gate_diagnostics(ctx, layout, legacy_state, brief_ids)


def legacy_gate_diagnostics(ctx: MctlContext) -> tuple[Diagnostic, ...]:
    """The #38 legacy-migration gate, independent of any single brief.

    Creation has no existing brief to scope the gate to, but it is still a
    mutation and must fail closed on unmigrated decisions-track rows.
    """
    layout = artifact_layout(ctx)
    return _legacy_gate_diagnostics(ctx, layout, legacy_manifest_state(layout), None)


# A brief label is a bd label: one lowercase token, no spaces.
_LABEL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

# B2.4 keeps exactly one pile and expresses urgency through ordering, and
# B2.10 forbids an active side presentation lane. A label that names its own
# lane is a request for the thing both rules exclude.
_BYPASS_LABEL_TOKENS = ("urgent", "bypass", "side-pile", "sidepile", "hotfix", "jump-queue")


def validate_brief_input(
    ctx: MctlContext, title: str | None, body: str | None, labels: Iterable[str]
) -> tuple[str, str, tuple[str, ...]]:
    """Check a proposed brief against brief-system policy before any write.

    Each check maps to a policy section reference rather than restating the
    prose; the reference is what the operator follows to see why.
    """
    clean_title = (title or "").strip()
    if not clean_title:
        raise BriefError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MBRF030",
                "A brief needs a non-empty title stating what is being decided.",
                policy_ref="B1.1",
            )
        )
    clean_body = (body or "").strip()
    if not clean_body:
        raise BriefError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MBRF031",
                "A brief needs a non-empty body carrying its decision evidence.",
                policy_ref="B1.5",
            )
        )
    clean_labels: list[str] = []
    for label in labels:
        candidate = label.strip()
        if not _LABEL_PATTERN.match(candidate):
            raise BriefError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MBRF033",
                    f"Brief label {label!r} is not a usable bd label token.",
                )
            )
        if any(token in candidate for token in _BYPASS_LABEL_TOKENS):
            raise BriefError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MBRF032",
                    f"Brief label {candidate!r} requests a side or bypass pile.",
                    policy_ref="B2.4",
                )
            )
        clean_labels.append(candidate)
    return clean_title, clean_body, tuple(dict.fromkeys(clean_labels))


def validate_brief(ctx: MctlContext, brief_id: str | None) -> ValidationReport:
    """Validate one brief, or every brief when `brief_id` is None.

    The bead store is read exactly once and the snapshot threaded through
    every per-brief check, so `--all` costs the same number of bd calls as a
    single brief.
    """
    beads = _beads(ctx)
    layout = artifact_layout(ctx)
    report = _doctor_briefs(ctx, brief_id, beads)
    bead_by_id = {bead.id: bead for bead in beads}
    diagnostics = list(report.diagnostics)
    for record in report.records:
        diagnostics.extend(
            _strict_invariants(ctx, layout, record, bead_by_id[record.bead_id])
        )
    return ValidationReport(
        scope=brief_id if brief_id is not None else "--all",
        records=report.records,
        diagnostics=tuple(diagnostics),
    )


def _strict_invariants(
    ctx: MctlContext, layout: ArtifactLayout, record: BriefRecord, bead: Bead
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    cache_path = layout.decisions / f"{record.brief_id}.toml"
    cached = _read_toml(cache_path)
    cached_status = cached.get("status")
    if isinstance(cached_status, str) and cached_status:
        if cached_status not in {record.status, record.decision_state}:
            diagnostics.append(
                _diagnostic(
                    ctx,
                    Severity.ERROR,
                    "MBRF020",
                    "Redundant decision cache disagrees with the canonical bead.",
                    brief_id=record.brief_id,
                    data_location=str(cache_path),
                    policy_ref="B2.8",
                    detail=(
                        f"cache status={cached_status!r}; canonical status="
                        f"{record.status!r}, decision_state={record.decision_state!r}"
                    ),
                )
            )
    cached_verdict = cached.get("verdict")
    if isinstance(cached_verdict, str) and cached_verdict:
        canonical_verdict = _verdict(bead)
        if (canonical_verdict or "").strip().lower() != cached_verdict.strip().lower():
            diagnostics.append(
                _diagnostic(
                    ctx,
                    Severity.ERROR,
                    "MBRF020",
                    "Redundant decision cache records a verdict the bead does not.",
                    brief_id=record.brief_id,
                    data_location=str(cache_path),
                    policy_ref="B2.8",
                    detail=(
                        f"cache verdict={cached_verdict!r}; canonical verdict="
                        f"{canonical_verdict!r}"
                    ),
                )
            )
    if not any(artifact.state == "present" for artifact in record.redundant_artifacts):
        diagnostics.append(
            _diagnostic(
                ctx,
                Severity.WARN,
                "MBRF021",
                "Canonical brief bead has no redundant cache artifact.",
                brief_id=record.brief_id,
                data_location=str(layout.pile / f"{record.brief_id}.md"),
                policy_ref="B2.8",
            )
        )
    return tuple(diagnostics)


def _read_toml(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        return dict(tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def brief_options(ctx: MctlContext, brief_id: str) -> tuple[BriefOption, ...]:
    options, _ = brief_options_report(ctx, brief_id)
    return options


def brief_options_report(ctx: MctlContext, brief_id: str) -> tuple[tuple[BriefOption, ...], tuple[Diagnostic, ...]]:
    beads = _beads(ctx)
    records = _records(ctx, beads)
    record = _find_record(ctx, records, brief_id)
    bead_by_id = {bead.id: bead for bead in beads}
    bead = bead_by_id[record.bead_id]
    doctor = _doctor_briefs(ctx, brief_id, beads)
    blocker = _blocking_diagnostic(doctor.diagnostics)
    pending_blocker = blocker
    if pending_blocker is None and record.decision_state != "pending":
        pending_blocker = _diagnostic(
            ctx,
            Severity.ERROR,
            "MBRF011",
            f"Brief {brief_id!r} is not pending adjudication.",
            brief_id=brief_id,
            data_location=_canonical_bead_location(ctx),
            policy_ref="B2.2",
        )
    dispatch_blocker = blocker
    if dispatch_blocker is None and not _approved_for_dispatch(bead):
        dispatch_blocker = _diagnostic(
            ctx,
            Severity.ERROR,
            "MBRF011",
            f"Brief {brief_id!r} has no approving verdict for dispatch.",
            brief_id=brief_id,
            data_location=_canonical_bead_location(ctx),
            policy_ref="B2.2",
        )
    return (
        (
            BriefOption("validate", "Validate", "Inspect canonical state and cache drift.", True, None),
            BriefOption(
                "adjudicate",
                "Adjudicate",
                "Record a human verdict on the canonical brief bead.",
                pending_blocker is None,
                pending_blocker,
            ),
            BriefOption(
                "defer",
                "Defer",
                "Set a timed defer window on the canonical brief bead.",
                pending_blocker is None,
                pending_blocker,
            ),
            BriefOption(
                "dispatch-work",
                "Dispatch work",
                "Dispatch work unlocked by the canonical brief bead.",
                dispatch_blocker is None,
                dispatch_blocker,
            ),
        ),
        doctor.diagnostics,
    )



@dataclass(frozen=True)
class BriefDecisionOption:
    """One decision option offered by a brief, per plan §2.

    Distinct from the action options `brief_options` returns (adjudicate /
    defer / validate). The plan gives both types the name BriefOption; this is
    the §2 one, parsed out of the brief markdown.
    """

    label: str
    heading: str
    start_line: int
    end_line: int
    raw_text: str
    confidence: str


# Real briefs enumerate options as list items under an Options section:
#     ## §4 — Options
#     - **(A) Do it now.** *(recommended)* ...
# Confirmed on 4 of 5 briefs on the live pile. Scoping to the section keeps
# ordinary bolded prose elsewhere from fabricating options.
_OPTIONS_SECTION = re.compile(
    r"^##\s+(?:§\d+\s*[—-]\s*)?Options\s*$(?P<body>.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
_OPTION_ITEM = re.compile(
    r"^\s*[-*]\s+\*\*\((?P<label>[A-Za-z0-9]+)\)\s*(?P<heading>[^*]+?)\*\*",
    re.MULTILINE,
)


def parse_decision_options(markdown: str) -> tuple[BriefDecisionOption, ...]:
    """Extract the decision options a brief offers, if any."""
    section = _OPTIONS_SECTION.search(markdown)
    if section is None:
        return ()
    body = section.group("body")
    body_offset = section.start("body")
    line_of = lambda index: markdown.count("\n", 0, index) + 1

    matches = list(_OPTION_ITEM.finditer(body))
    options: list[BriefDecisionOption] = []
    for position, match in enumerate(matches):
        start = body_offset + match.start()
        end_in_body = (
            matches[position + 1].start() if position + 1 < len(matches) else len(body)
        )
        raw = body[match.start():end_in_body].strip()
        options.append(
            BriefDecisionOption(
                label=match.group("label"),
                heading=match.group("heading").strip(),
                start_line=line_of(start),
                end_line=line_of(body_offset + end_in_body),
                raw_text=raw,
                confidence="explicit",
            )
        )
    return tuple(options)


def decision_options(ctx: MctlContext, brief_id: str) -> tuple[BriefDecisionOption, ...]:
    """Decision options for a brief, read from its markdown cache.

    The bead is canonical, so a missing or unreadable cache yields no options
    rather than blocking a verdict.
    """
    layout = artifact_layout(ctx)
    for directory in (layout.pile, layout.stack):
        path = directory / f"{brief_id}.md"
        if path.is_file():
            try:
                return parse_decision_options(path.read_text(encoding="utf-8"))
            except OSError:
                return ()
    return ()

def doctor_briefs(
    ctx: MctlContext, brief_id: str | None, beads: tuple[Bead, ...] | None = None
) -> DoctorReport:
    """Report canonical/cache drift.

    Callers that already hold a bead snapshot pass it in; each bead read is a
    full `bd list` subprocess, so re-reading per brief makes callers that loop
    over briefs scale with the size of the rig.
    """
    return _doctor_briefs(ctx, brief_id, beads)


def _doctor_briefs(ctx: MctlContext, brief_id: str | None, beads: tuple[Bead, ...] | None = None) -> DoctorReport:
    beads = _beads(ctx) if beads is None else beads
    layout = artifact_layout(ctx)
    legacy_state = legacy_manifest_state(layout)
    records = _records(ctx, beads, layout, legacy_state)
    if brief_id is not None:
        records = tuple(record for record in records if record.brief_id == brief_id)
        if not records:
            raise BriefError(
                _diagnostic(ctx, Severity.FATAL, "MBRF010", f"No canonical brief bead named {brief_id!r} was found.", brief_id=brief_id)
            )
    bead_by_id = {bead.id: bead for bead in beads}
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
    diagnostics.extend(
        _legacy_gate_diagnostics(
            ctx,
            layout,
            legacy_state,
            {brief_id} if brief_id is not None else None,
        )
    )
    return DoctorReport(records, tuple(diagnostics))


def _records(
    ctx: MctlContext,
    beads: tuple[Bead, ...] | None = None,
    layout: ArtifactLayout | None = None,
    legacy_state: LegacyManifestState | None = None,
) -> tuple[BriefRecord, ...]:
    layout = artifact_layout(ctx) if layout is None else layout
    legacy_state = legacy_manifest_state(layout) if legacy_state is None else legacy_state
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
            redundant_artifacts=scan_artifacts(layout, bead.id, _decision_state(bead), legacy_state),
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
    return f"{' '.join(BD_LIST_ARGS)} (rig database {ctx.rig_db})"


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
    return _verdict(bead) is not None


def _verdict(bead: Bead) -> str | None:
    for key in ("verdict", "decision", "recorded_verdict"):
        value = bead.raw.get(key)
        if isinstance(value, str) and value:
            return value
    metadata = bead.raw.get("metadata")
    if isinstance(metadata, dict):
        for key in ("verdict", "decision", "recorded_verdict"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _approved_for_dispatch(bead: Bead) -> bool:
    verdict = _verdict(bead)
    if verdict is None:
        return False
    return bead.status.lower() in {"closed", "done"} and verdict.strip().lower() in {
        "accept",
        "accepted",
        "approve",
        "approved",
    }


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


def _find_record(ctx: MctlContext, records: Iterable[BriefRecord], brief_id: str) -> BriefRecord:
    for record in records:
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


def _blocking_diagnostic(diagnostics: Iterable[Diagnostic]) -> Diagnostic | None:
    return next(
        (diagnostic for diagnostic in diagnostics if diagnostic.severity in {Severity.ERROR, Severity.FATAL}),
        None,
    )


def _legacy_gate_diagnostics(
    ctx: MctlContext,
    layout: ArtifactLayout,
    legacy_state: LegacyManifestState,
    brief_ids: set[str] | None,
) -> tuple[Diagnostic, ...]:
    if legacy_state.parse_error is not None:
        return (
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MBRF013",
                "Legacy decisions-track manifest could not be parsed.",
                data_location=str(layout.legacy_manifest),
                policy_ref="B2.10",
            ),
            _legacy_migration_blocker(ctx, layout),
        )
    legacy_rows = legacy_state.nonterminal_rows
    if brief_ids is not None:
        legacy_rows = tuple(row for row in legacy_rows if _row_slug(row) in brief_ids)
    if not legacy_rows:
        return ()
    diagnostics: list[Diagnostic] = []
    for row in legacy_rows:
        slug = _row_slug(row)
        diagnostics.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MBRF008",
                "Legacy decisions-track row is non-terminal and not migration-visible.",
                brief_id=slug,
                data_location=str(layout.legacy_manifest),
                policy_ref="B2.10",
            )
        )
    diagnostics.append(_legacy_migration_blocker(ctx, layout))
    return tuple(diagnostics)


def _legacy_migration_blocker(ctx: MctlContext, layout: ArtifactLayout) -> Diagnostic:
    return _diagnostic(
        ctx,
        Severity.FATAL,
        "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED",
        "Legacy decisions-track state requires the authorized #38 migration proof/canary.",
        data_location=str(layout.legacy_manifest),
        policy_ref="B2.10",
        suggested_next_command="bash tests/decisions-track-migration/smoke_test.sh",
    )


def _diagnostic(
    ctx: MctlContext,
    severity: Severity,
    code: str,
    message: str,
    *,
    brief_id: str | None = None,
    data_location: str | None = None,
    detail: str | None = None,
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
    if detail:
        facts["detail"] = detail
    if policy_ref:
        facts["policy_reference"] = policy_ref
    if suggested_next_command:
        facts["suggested_next_command"] = suggested_next_command
    return Diagnostic(severity, code, message, facts=facts, trace_id=ctx.trace_id)
