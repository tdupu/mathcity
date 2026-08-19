"""Dry-run-first effect planning for mctl mutations."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
import tempfile
import tomllib
from pathlib import Path
from typing import Mapping

from .beads import (
    BeadCreate,
    BeadRaceLostError,
    BeadUpdate,
    BeadWriteError,
    apply_bead_create,
    apply_bead_update,
)
from .briefs import (
    decision_options,
    doctor_briefs,
    legacy_gate_diagnostics,
    show_brief,
    validate_brief_input,
)
from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .events import append_jsonl
from .redundant_state import ArtifactLayout, artifact_layout
from .trace import append_aborted, append_applied, append_planned, trace_path


VALID_VERDICTS = {
    "accept": "approve",
    "accepted": "approve",
    "approve": "approve",
    "approved": "approve",
    "reject": "reject",
    "rejected": "reject",
    "revise": "revise",
    "revision": "revise",
}


@dataclass(frozen=True)
class CacheUpdate:
    kind: str
    path: Path
    target_brief_id: str
    fields: Mapping[str, str]

    def to_dict(self) -> dict[str, object]:
        return {
            "fields": dict(sorted(self.fields.items())),
            "kind": self.kind,
            "path": str(self.path),
            "target_brief_id": self.target_brief_id,
        }


@dataclass(frozen=True)
class FileCreate:
    """A redundant cache file this operation brings into existence.

    Distinct from CacheUpdate: an update merges fields into a file that may
    already exist, while a create must refuse to touch one that does. The
    content is summarized rather than inlined so a dry-run plan stays readable
    for a brief body of any size.
    """

    kind: str
    path: Path
    content: str

    def to_dict(self) -> dict[str, object]:
        return {
            "content_bytes": len(self.content.encode("utf-8")),
            "content_sha256": hashlib.sha256(self.content.encode("utf-8")).hexdigest(),
            "kind": self.kind,
            "path": str(self.path),
        }


@dataclass(frozen=True)
class JsonlWrite:
    kind: str
    path: Path
    row: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "path": str(self.path), "row": dict(self.row)}


@dataclass(frozen=True)
class EffectPlan:
    trace_id: str
    operation: str
    target_brief_id: str
    preconditions: tuple[Diagnostic, ...]
    bead_updates: tuple[BeadUpdate, ...]
    cache_updates: tuple[CacheUpdate, ...]
    event_writes: tuple[JsonlWrite, ...]
    trace_writes: tuple[JsonlWrite, ...]
    # Creation-only. `preconditions` blocks the mutation outright, so advice
    # that should reach the operator without refusing the write lives here.
    bead_creates: tuple[BeadCreate, ...] = ()
    file_creates: tuple[FileCreate, ...] = ()
    advisories: tuple[Diagnostic, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "advisories": [diagnostic.to_dict() for diagnostic in self.advisories],
            "bead_creates": [create.to_dict() for create in self.bead_creates],
            "bead_updates": [update.to_dict() for update in self.bead_updates],
            "cache_updates": [update.to_dict() for update in self.cache_updates],
            "event_writes": [write.to_dict() for write in self.event_writes],
            "file_creates": [create.to_dict() for create in self.file_creates],
            "operation": self.operation,
            "preconditions": [diagnostic.to_dict() for diagnostic in self.preconditions],
            "target_brief_id": self.target_brief_id,
            "trace_id": self.trace_id,
            "trace_writes": [write.to_dict() for write in self.trace_writes],
        }


@dataclass(frozen=True)
class ApplyResult:
    trace_id: str
    effect_plan: EffectPlan
    actual_effects: tuple[Mapping[str, object], ...]
    diagnostics: tuple[Diagnostic, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "actual_effects": [dict(effect) for effect in self.actual_effects],
            "applied": True,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "effect_plan": self.effect_plan.to_dict(),
            "trace_id": self.trace_id,
        }


class MutationError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


@dataclass(frozen=True)
class BriefCreateInput:
    title: str
    body: str
    labels: tuple[str, ...]
    requested_by: str | None
    # Not in the plan's four-field sketch, but B2.1 makes a brief without a
    # source link malformed, and every downstream mctl command refuses to act
    # on a malformed brief. Optional, so creation without one still works and
    # warns instead of silently minting an unusable brief.
    sources: tuple[str, ...] = ()


# The plan cannot name the bead it is about to create, because bd mints the
# id. Derived paths are planned against this token and rewritten once bd has
# answered.
NEW_BRIEF_ID_PLACEHOLDER = "(pending-bead-id)"


def plan_create_brief(ctx: MctlContext, request: BriefCreateInput) -> EffectPlan:
    """Plan a bead-first brief creation.

    The canonical decision bead is the only thing that must exist for the
    brief to exist (B2.8); the pile markdown and the decision TOML are cache
    written afterwards. The presentable stack index is deliberately NOT
    written: B2.10 makes brief-shuffle the single `.pile -> stack` writer.
    """
    title, body, labels = validate_brief_input(
        ctx, request.title, request.body, request.labels
    )
    # Creation is a mutation, so the same legacy-migration gate that blocks
    # adjudication blocks it. Doctor's per-brief findings are deliberately not
    # consulted: an unrelated malformed brief must not make the rig unable to
    # accept new ones.
    preconditions = _blocking_preconditions(legacy_gate_diagnostics(ctx))
    advisories: list[Diagnostic] = []
    if not request.sources:
        advisories.append(
            _diagnostic(
                ctx,
                Severity.WARN,
                "MBRF034",
                "Created brief has no source dependency, so it is B2.1-incomplete.",
                brief_id=NEW_BRIEF_ID_PLACEHOLDER,
                policy_ref="B2.1",
                suggested_next_command="bd link <new-brief-id> <source-bead-id> --type related",
            )
        )
    metadata = {"created_by": "mctl", "mctl_trace_id": ctx.trace_id, "created_at": _now()}
    if request.requested_by:
        metadata["requested_by"] = request.requested_by
    bead_create = BeadCreate(
        placeholder_id=NEW_BRIEF_ID_PLACEHOLDER,
        title=title,
        body=body,
        issue_type="decision",
        labels=labels,
        metadata=metadata,
        sources=request.sources,
    )
    layout = artifact_layout(ctx)
    _require_brief_root(ctx, layout)
    pile_create = FileCreate(
        "pile_markdown", layout.pile / f"{NEW_BRIEF_ID_PLACEHOLDER}.md", body
    )
    cache_update = CacheUpdate(
        "decision_toml",
        layout.decisions / f"{NEW_BRIEF_ID_PLACEHOLDER}.toml",
        NEW_BRIEF_ID_PLACEHOLDER,
        {
            "brief_id": NEW_BRIEF_ID_PLACEHOLDER,
            "status": "open",
            "title": title,
        },
    )
    planned_effects = [bead_create.to_dict(), pile_create.to_dict(), cache_update.to_dict()]
    event_row = {
        "brief_id": NEW_BRIEF_ID_PLACEHOLDER,
        "operation": "briefs.create",
        "planned_effects": planned_effects,
        "trace_id": ctx.trace_id,
    }
    trace_row = {
        "brief_id": NEW_BRIEF_ID_PLACEHOLDER,
        "city_path": str(ctx.city_root),
        "operation": "briefs.create",
        "planned_effects": planned_effects,
        "rig_name": ctx.rig_id,
        "trace_id": ctx.trace_id,
    }
    today = date.today().isoformat()
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation="briefs.create",
        target_brief_id=NEW_BRIEF_ID_PLACEHOLDER,
        preconditions=preconditions,
        bead_updates=(),
        cache_updates=(cache_update,),
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
        bead_creates=(bead_create,),
        file_creates=(pile_create,),
        advisories=tuple(advisories),
    )


def _require_brief_root(ctx: MctlContext, layout: ArtifactLayout) -> None:
    """Refuse to create a brief under a root the resolver could not find.

    `assets/brief-pipeline/paths.toml` declares rig-relative artifact paths,
    but the live city keeps its brief tree at the city root, and the shuffler
    never reads paths.toml at all — it is handed `--brief-root` explicitly. So
    the declared contract and the live layout currently disagree, and which
    root is correct is an open policy question, not something creation may
    decide.

    Reading through a missing root is harmless: it reports `missing`. Writing
    through one is not — `mkdir -p` would silently build a parallel shadow
    brief tree that diverges from the real one, with nothing downstream to
    notice. So creation aborts and names the path it resolved.
    """
    if layout.root.is_dir():
        return
    raise MutationError(
        _diagnostic(
            ctx,
            Severity.FATAL,
            "MBRF035",
            (
                f"Resolved brief root {layout.root} does not exist; refusing to "
                "create a brief tree there."
            ),
            brief_id=NEW_BRIEF_ID_PLACEHOLDER,
            data_location=str(layout.root),
            policy_ref="B2.8",
            suggested_next_command=(
                "Check paths.brief_root in assets/brief-pipeline/paths.toml "
                "against the rig's actual brief tree."
            ),
        )
    )


def plan_adjudication(
    ctx: MctlContext,
    brief_id: str,
    *,
    verdict: str | None,
    reason: str | None,
    option: str | None = None,
) -> EffectPlan:
    normalized = _normalize_verdict(ctx, verdict, brief_id)
    reason = _require_reason(ctx, reason, brief_id)
    observed = show_brief(ctx, brief_id)
    diagnostics = list(_blocking_preconditions(doctor_briefs(ctx, brief_id).diagnostics))
    # Plan §4 MOPT001/MOPT002: a verdict on a multi-option brief has to say
    # which option it is approving, or it records a decision against nothing.
    # `show_brief` already carries the canonical body, so options resolve
    # from it rather than costing a second `bd list` subprocess.
    offered = decision_options(ctx, brief_id, observed.body)
    if offered:
        labels = {item.label.upper() for item in offered}
        if option is None and len(offered) > 1:
            diagnostics.append(
                _diagnostic(
                    ctx,
                    Severity.ERROR,
                    "MOPT001",
                    "This brief offers multiple options; adjudication must name one.",
                    brief_id=brief_id,
                    detail="options=" + ", ".join(sorted(labels)),
                )
            )
        elif option is not None and option.upper() not in labels:
            diagnostics.append(
                _diagnostic(
                    ctx,
                    Severity.ERROR,
                    "MOPT002",
                    f"Option {option!r} is not offered by this brief.",
                    brief_id=brief_id,
                    detail="options=" + ", ".join(sorted(labels)),
                )
            )
    diagnostics = tuple(diagnostics)
    now = _now()
    metadata = {
        "adjudicated_at": now,
        "mctl_trace_id": ctx.trace_id,
        "verdict": normalized,
        "verdict_reason": reason,
    }
    if option:
        metadata["verdict_option"] = option
    cache_fields = {
        "adjudicated_at": now,
        "status": "adjudicated",
        "verdict": normalized,
        "verdict_reason": reason,
    }
    return _plan(
        ctx,
        operation="briefs.adjudicate",
        brief_id=brief_id,
        preconditions=diagnostics,
        bead_update=BeadUpdate(
            brief_id,
            status="closed",
            metadata=metadata,
            if_status=observed.status,
        ),
        cache_fields=cache_fields,
    )


def plan_deferral(
    ctx: MctlContext,
    brief_id: str,
    *,
    reason: str | None,
    until: str | None,
    days: int | None = None,
) -> EffectPlan:
    reason = _require_reason(ctx, reason, brief_id)
    defer_until = _resolve_until(ctx, until, days, brief_id)
    observed = show_brief(ctx, brief_id)
    diagnostics = _blocking_preconditions(doctor_briefs(ctx, brief_id).diagnostics)
    metadata = {
        "defer_reason": reason,
        "deferred_at": _now(),
        "mctl_trace_id": ctx.trace_id,
    }
    cache_fields = {
        "defer_reason": reason,
        "defer_until": defer_until,
        "status": "deferred",
    }
    return _plan(
        ctx,
        operation="briefs.defer",
        brief_id=brief_id,
        preconditions=diagnostics,
        bead_update=BeadUpdate(
            brief_id,
            status="deferred",
            metadata=metadata,
            defer_until=defer_until,
            if_status=observed.status,
        ),
        cache_fields=cache_fields,
    )


def dry_run_payload(plan: EffectPlan) -> dict[str, object]:
    _raise_if_blocked(plan)
    return {
        "applied": False,
        "diagnostics": [diagnostic.to_dict() for diagnostic in plan.advisories],
        "effect_plan": plan.to_dict(),
        "trace_id": plan.trace_id,
    }


def apply_effect_plan(ctx: MctlContext, plan: EffectPlan) -> ApplyResult:
    _raise_if_blocked(plan)
    actual: list[Mapping[str, object]] = []
    diagnostics: list[Diagnostic] = []
    # Plan §4: the trace records the intent before anything is mutated, then
    # exactly one outcome row -- so a crash mid-mutation still leaves evidence.
    trace_file = trace_path(ctx.rig_root)
    for write in plan.trace_writes:
        append_planned(write.path, write.row)
        trace_file = write.path
    return _apply_effects(ctx, plan, actual, diagnostics, trace_file)


def _apply_effects(
    ctx: MctlContext,
    plan: EffectPlan,
    actual: list[Mapping[str, object]],
    diagnostics: list[Diagnostic],
    trace_file: Path,
) -> ApplyResult:
    minted: dict[str, str] = {}
    for create in plan.bead_creates:
        try:
            result = apply_bead_create(
                ctx.rig_root,
                create,
                fixture_path=ctx.beads_fixture,
            )
        except BeadWriteError as error:
            append_aborted(
                trace_file,
                plan.trace_id,
                [{"code": "MCTL_CANONICAL_BEAD_CREATE_FAILED", "detail": str(error)}],
            )
            raise MutationError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MCTL_CANONICAL_BEAD_CREATE_FAILED",
                    "Canonical decision bead creation failed; nothing was written.",
                    brief_id=create.placeholder_id,
                    detail=str(error),
                )
            ) from error
        minted[create.placeholder_id] = str(result["id"])
        actual.append({"kind": "bead_create", "target": result["id"], "result": result})
    for update in plan.bead_updates:
        try:
            result = apply_bead_update(
                ctx.rig_root,
                update,
                fixture_path=ctx.beads_fixture,
            )
        except BeadRaceLostError as error:
            append_aborted(trace_file, plan.trace_id, [{"code": "MCTL_BEAD_UPDATE_RACE_LOST", "detail": str(error)}])
            raise MutationError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MCTL_BEAD_UPDATE_RACE_LOST",
                    f"Another actor changed {update.id!r} before this mutation applied.",
                    brief_id=update.id,
                    detail=str(error),
                )
            ) from error
        except BeadWriteError as error:
            append_aborted(trace_file, plan.trace_id, [{"code": "MCTL_CANONICAL_BEAD_UPDATE_FAILED", "detail": str(error)}])
            raise MutationError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MCTL_CANONICAL_BEAD_UPDATE_FAILED",
                    f"Canonical bead update failed for {update.id!r}.",
                    brief_id=update.id,
                    detail=str(error),
                )
            ) from error
        actual.append({"kind": "bead_update", "target": update.id, "result": result})
    if plan.bead_creates:
        _apply_created_artifacts(ctx, plan, minted, actual, diagnostics)
    else:
        for update in plan.cache_updates:
            try:
                _apply_cache_update(update)
            except OSError as error:
                diagnostic = _diagnostic(
                    ctx,
                    Severity.ERROR,
                    "MCTL_REDUNDANT_CACHE_UPDATE_FAILED",
                    "Redundant brief cache update failed after canonical bead update.",
                    brief_id=plan.target_brief_id,
                    data_location=str(update.path),
                    detail=str(error),
                )
                diagnostics.append(diagnostic)
                continue
            actual.append({"kind": "cache_update", "path": str(update.path)})
    for write in plan.event_writes:
        append_jsonl(write.path, _resolve_row(write.row, minted))
        actual.append({"kind": write.kind, "path": str(write.path)})
    append_applied(trace_file, plan.trace_id, actual)
    actual.append({"kind": "trace_write", "path": str(trace_file)})
    return ApplyResult(
        plan.trace_id, plan, tuple(actual), plan.advisories + tuple(diagnostics)
    )


def _apply_created_artifacts(
    ctx: MctlContext,
    plan: EffectPlan,
    minted: Mapping[str, str],
    actual: list[Mapping[str, object]],
    diagnostics: list[Diagnostic],
) -> None:
    """Write a new brief's redundant artifacts, all-or-nothing.

    The canonical bead already exists and cannot be un-created, but a cache
    that is half-written is worse than one that is absent: `briefs doctor`
    would read the orphan half as a real invariant violation. So every file
    this operation brought into existence is removed if any of them fails,
    and the operator is told the redundancy still has to be rebuilt.
    """
    created: list[Path] = []
    try:
        for file_create in plan.file_creates:
            resolved = _resolve_file_create(file_create, minted)
            apply_file_create(resolved)
            created.append(resolved.path)
            actual.append({"kind": resolved.kind, "path": str(resolved.path)})
        for update in plan.cache_updates:
            resolved_update = _resolve_cache_update(update, minted)
            existed = resolved_update.path.exists()
            _apply_cache_update(resolved_update)
            if not existed:
                created.append(resolved_update.path)
            actual.append({"kind": "cache_update", "path": str(resolved_update.path)})
    except OSError as error:
        for path in created:
            path.unlink(missing_ok=True)
        actual[:] = [
            effect
            for effect in actual
            if str(effect.get("path", "")) not in {str(path) for path in created}
        ]
        diagnostics.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MCTL_REDUNDANT_CACHE_ROLLED_BACK",
                (
                    "Redundant brief cache writes failed and were rolled back; the "
                    "canonical decision bead was created and is intact."
                ),
                brief_id=next(iter(minted.values()), plan.target_brief_id),
                data_location=str(getattr(error, "filename", "") or ""),
                detail=str(error),
                policy_ref="B2.8",
                suggested_next_command="mctl briefs validate <brief-id> --json",
            )
        )


def _resolve_file_create(file_create: FileCreate, minted: Mapping[str, str]) -> FileCreate:
    return FileCreate(
        file_create.kind, _resolve_path(file_create.path, minted), file_create.content
    )


def _resolve_cache_update(update: CacheUpdate, minted: Mapping[str, str]) -> CacheUpdate:
    return CacheUpdate(
        update.kind,
        _resolve_path(update.path, minted),
        _resolve_text(update.target_brief_id, minted),
        {key: _resolve_text(str(value), minted) for key, value in update.fields.items()},
    )


def _resolve_path(path: Path, minted: Mapping[str, str]) -> Path:
    return Path(_resolve_text(str(path), minted))


def _resolve_row(row: Mapping[str, object], minted: Mapping[str, str]) -> Mapping[str, object]:
    if not minted:
        return row
    return json.loads(_resolve_text(json.dumps(dict(row), sort_keys=True), minted))


def _resolve_text(value: str, minted: Mapping[str, str]) -> str:
    for placeholder, bead_id in minted.items():
        value = value.replace(placeholder, bead_id)
    return value


def apply_file_create(file_create: FileCreate) -> None:
    """Write a brand-new cache file, refusing to overwrite an existing one."""
    if file_create.path.exists():
        raise FileExistsError(
            f"refusing to overwrite existing cache file {file_create.path}"
        )
    _atomic_write(file_create.path, file_create.content)


def _plan(
    ctx: MctlContext,
    *,
    operation: str,
    brief_id: str,
    preconditions: tuple[Diagnostic, ...],
    bead_update: BeadUpdate,
    cache_fields: Mapping[str, str],
) -> EffectPlan:
    cache_updates = _cache_updates(ctx, brief_id, cache_fields)
    event_row = {
        "brief_id": brief_id,
        "operation": operation,
        "planned_effects": [bead_update.to_dict(), *[item.to_dict() for item in cache_updates]],
        "trace_id": ctx.trace_id,
    }
    trace_row = {
        "brief_id": brief_id,
        "city_path": str(ctx.city_root),
        "operation": operation,
        "planned_effects": event_row["planned_effects"],
        "rig_name": ctx.rig_id,
        "trace_id": ctx.trace_id,
    }
    today = date.today().isoformat()
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation=operation,
        target_brief_id=brief_id,
        preconditions=preconditions,
        bead_updates=(bead_update,),
        cache_updates=cache_updates,
        event_writes=(JsonlWrite("event_write", ctx.rig_root / ".beads" / "mctl" / "events" / f"{today}.jsonl", event_row),),
        trace_writes=(JsonlWrite("trace_write", ctx.rig_root / ".beads" / "mctl" / "traces" / f"{today}.jsonl", trace_row),),
    )


def _cache_updates(
    ctx: MctlContext, brief_id: str, fields: Mapping[str, str]
) -> tuple[CacheUpdate, ...]:
    updates: list[CacheUpdate] = []
    decision_toml = ctx.rig_root / ".beads" / "briefs" / "decisions" / f"{brief_id}.toml"
    if decision_toml.exists():
        updates.append(CacheUpdate("decision_toml", decision_toml, brief_id, fields))
    stack_index = ctx.rig_root / ".beads" / "briefs" / "stack" / ".index.jsonl"
    if stack_index.exists():
        updates.append(CacheUpdate("stack_index", stack_index, brief_id, fields))
    return tuple(updates)


def _blocking_preconditions(diagnostics: tuple[Diagnostic, ...]) -> tuple[Diagnostic, ...]:
    return tuple(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.severity in {Severity.ERROR, Severity.FATAL}
    )


def _raise_if_blocked(plan: EffectPlan) -> None:
    if not plan.preconditions:
        return
    legacy = next(
        (
            diagnostic
            for diagnostic in plan.preconditions
            if diagnostic.code == "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED"
        ),
        None,
    )
    if legacy is not None:
        raise MutationError(legacy)
    first = plan.preconditions[0]
    raise MutationError(
        Diagnostic(
            severity=Severity.FATAL,
            code="MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS",
            message="Mutation blocked because brief doctor reported ERROR or FATAL diagnostics.",
            facts={
                "blocking_code": first.code,
                "brief_id": plan.target_brief_id,
                "operation": plan.operation,
            },
            trace_id=plan.trace_id,
        )
    )


def _normalize_verdict(ctx: MctlContext, verdict: str | None, brief_id: str) -> str:
    if not verdict:
        raise MutationError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MCTL_MUTATION_VERDICT_REQUIRED",
                "Adjudication requires --verdict.",
                brief_id=brief_id,
            )
        )
    normalized = VALID_VERDICTS.get(verdict.strip().lower())
    if normalized is None:
        raise MutationError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MCTL_MUTATION_INVALID_VERDICT",
                "Adjudication verdict must be approve, revise, or reject.",
                brief_id=brief_id,
            )
        )
    return normalized


def _require_reason(ctx: MctlContext, reason: str | None, brief_id: str) -> str:
    if reason is None or not reason.strip():
        raise MutationError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MCTL_MUTATION_REASON_REQUIRED",
                "Brief mutations require a non-empty --reason.",
                brief_id=brief_id,
            )
        )
    return reason.strip()


def _resolve_until(ctx: MctlContext, until: str | None, days: int | None, brief_id: str) -> str:
    if until:
        return until
    if days is not None and days > 0:
        return (date.today() + timedelta(days=days)).isoformat()
    raise MutationError(
        _diagnostic(
            ctx,
            Severity.FATAL,
            "MCTL_MUTATION_DEFER_UNTIL_REQUIRED",
            "Deferral requires --until YYYY-MM-DD or --days N.",
            brief_id=brief_id,
        )
    )


def _apply_cache_update(update: CacheUpdate) -> None:
    if update.kind == "decision_toml":
        _update_simple_toml(update.path, update.fields)
        return
    if update.kind == "stack_index":
        _update_stack_index(update.path, update.target_brief_id, update.fields)
        return
    raise OSError(f"unknown cache update kind: {update.kind}")


def _atomic_write(path: Path, text: str) -> None:
    """Write via a same-directory temp file and os.replace.

    A whole-file rewrite that is interrupted between truncate and write
    destroys the cache it was updating. os.replace is atomic within a
    filesystem, so readers see either the old file or the new one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


# brief-shuffle-fast-drain.py::append_index locks `<stack>/.manifest.lock`.
# flock only serializes writers that take the SAME lock file, so mctl must use
# that exact path -- a lock of our own would serialize mctl against mctl and
# leave the shuffler race wide open while looking like it was handled.
STACK_INDEX_LOCK_NAME = ".manifest.lock"


def _stack_index_lock_path(path: Path) -> Path:
    return path.parent / STACK_INDEX_LOCK_NAME


@contextmanager
def _stack_index_lock(path: Path):
    """Serialize stack-index writers.

    formulas/brief-prep.toml and the fast-drain plan both name the shuffler as
    the single writer that promotes stack entries and appends .index.jsonl.
    mctl now writes it too, so the boundary needs an explicit lock rather than
    two documents that quietly contradict the code.
    """
    lock_path = _stack_index_lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return f'"{_toml_escape(str(value))}"'


def _update_simple_toml(path: Path, fields: Mapping[str, object]) -> None:
    """Rewrite a decision TOML through a real parser.

    The previous writer split each line on the first `=`, so any line inside a
    multi-line string that looked like `key = ...` was rewritten instead of the
    real key -- silently losing the verdict and mutating unrelated prose.
    """
    existing: dict[str, object] = {}
    if path.exists():
        existing = dict(tomllib.loads(path.read_text(encoding="utf-8")))
    existing.update(fields)
    lines = [f"{key} = {_toml_value(value)}" for key, value in existing.items()]
    _atomic_write(path, "\n".join(lines) + "\n")


def _update_stack_index(path: Path, target_brief_id: str, fields: Mapping[str, str]) -> None:
    """Splice the matching row; leave every other line byte-identical.

    The stack index has two producers with different json.dumps settings, so
    re-serializing untouched rows makes the file's convention "whoever wrote
    last wins" -- one adjudication would rewrite every unrelated line. Only the
    row we actually change is re-emitted, in the file's compact convention and
    without escaping non-ASCII.

    Read and write happen inside the lock: the shuffler drains this same file,
    so a read-modify-write outside it is a lost update either way.
    """
    with _stack_index_lock(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        spliced: list[str] = []
        changed = False
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                spliced.append(line)
                continue
            if isinstance(row, dict) and _row_targets_brief(row, target_brief_id):
                row.update(fields)
                spliced.append(
                    json.dumps(
                        row,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    )
                )
                changed = True
            else:
                # Untouched: preserve the original bytes exactly.
                spliced.append(line)
        if changed:
            _atomic_write(path, "\n".join(spliced) + "\n")


def _row_targets_brief(row: Mapping[str, object], target_brief_id: str) -> bool:
    for key in ("brief_id", "bead_id", "slug", "id"):
        value = row.get(key)
        if value == target_brief_id:
            return True
    path = row.get("path")
    if isinstance(path, str):
        stem = Path(path).stem
        return stem == target_brief_id or stem.removesuffix("-brief") == target_brief_id
    return False


def _diagnostic(
    ctx: MctlContext,
    severity: Severity,
    code: str,
    message: str,
    *,
    brief_id: str,
    data_location: str | None = None,
    detail: str | None = None,
    policy_ref: str | None = None,
    suggested_next_command: str | None = None,
) -> Diagnostic:
    facts = {
        "brief_id": brief_id,
        "city_path": str(ctx.city_root),
        "implementation_provenance": "mctl Slice 3 safe brief mutations",
        "operation_context": "brief mutation",
        "rig_name": ctx.rig_id,
        "rig_path": str(ctx.rig_root),
    }
    if data_location:
        facts["data_location"] = data_location
    if detail:
        facts["detail"] = detail
    if policy_ref:
        facts["policy_reference"] = policy_ref
    if suggested_next_command:
        facts["suggested_next_command"] = suggested_next_command
    return Diagnostic(severity, code, message, facts=facts, trace_id=ctx.trace_id)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _toml_escape(value: str) -> str:
    # Control characters are illegal raw inside a TOML basic string, so a
    # reason carrying newlines must be escaped rather than emitted literally.
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
