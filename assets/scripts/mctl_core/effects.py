"""Dry-run-first effect planning for mctl mutations."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import fcntl
import json
import os
import tempfile
import tomllib
from pathlib import Path
from typing import Mapping

from .beads import BeadRaceLostError, BeadUpdate, BeadWriteError, apply_bead_update
from .briefs import decision_options, doctor_briefs, show_brief
from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .events import append_jsonl
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

    def to_dict(self) -> dict[str, object]:
        return {
            "bead_updates": [update.to_dict() for update in self.bead_updates],
            "cache_updates": [update.to_dict() for update in self.cache_updates],
            "event_writes": [write.to_dict() for write in self.event_writes],
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
    offered = decision_options(ctx, brief_id)
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
        "diagnostics": [],
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
        append_jsonl(write.path, write.row)
        actual.append({"kind": write.kind, "path": str(write.path)})
    append_applied(trace_file, plan.trace_id, actual)
    actual.append({"kind": "trace_write", "path": str(trace_file)})
    return ApplyResult(plan.trace_id, plan, tuple(actual), tuple(diagnostics))


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
