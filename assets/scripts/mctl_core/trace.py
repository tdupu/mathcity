"""Trace identifiers and the phased trace log for mctl mutations.

Plan §4 requires a trace row appended *before* mutation, actual effects
appended after, and blocking diagnostics appended if the operation aborts.
A single row built at plan time and written afterwards cannot satisfy that:
it records intentions as if they were outcomes, and writes nothing at all
when the mutation raises.

The trace store is append-only JSONL, so one operation writes two rows keyed
by trace_id — `planned`, then exactly one of `applied` / `aborted`. Both
mutation paths (brief effects and work dispatch) go through this module so
they cannot drift apart again.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Mapping, Sequence
from uuid import uuid4

from .diagnostics import Diagnostic, Severity
from .events import append_jsonl

if TYPE_CHECKING:  # pragma: no cover - import cycle guard, context imports this module
    from .context import MctlContext

PHASE_PLANNED = "planned"
PHASE_APPLIED = "applied"
PHASE_ABORTED = "aborted"
# A refusal is caught at a presentation boundary (cli.py / mcp_server.py) after
# a MutationError aborts *before* any EffectPlan -- so it has no `planned` row
# and cannot use the applied/aborted pair. `refused` is its own terminal phase:
# the durable record (bead mc-rmqt) that makes the trace id shown to the
# operator resolve, and the input the mc-3q4v refusal->defect->repair router
# reads.
PHASE_REFUSED = "refused"


def new_trace_id() -> str:
    return str(uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def trace_path(rig_root: Path, when: str | None = None) -> Path:
    day = (when or _now())[:10]
    return rig_root / ".beads" / "mctl" / "traces" / f"{day}.jsonl"


def append_planned(path: Path, row: Mapping[str, object]) -> None:
    """Record the intended operation before anything is mutated."""
    append_jsonl(path, {**dict(row), "phase": PHASE_PLANNED, "recorded_at": _now()})


def append_applied(
    path: Path, trace_id: str, actual_effects: Sequence[Mapping[str, object]]
) -> None:
    append_jsonl(
        path,
        {
            "trace_id": trace_id,
            "phase": PHASE_APPLIED,
            "actual_effects": [dict(effect) for effect in actual_effects],
            "recorded_at": _now(),
        },
    )


def append_aborted(
    path: Path, trace_id: str, blocking_diagnostics: Sequence[Mapping[str, object]]
) -> None:
    append_jsonl(
        path,
        {
            "trace_id": trace_id,
            "phase": PHASE_ABORTED,
            "blocking_diagnostics": [dict(item) for item in blocking_diagnostics],
            "recorded_at": _now(),
        },
    )


def refusal_row(
    diagnostic: Diagnostic, *, surface: str, operation: str | None = None
) -> dict[str, object]:
    """The durable record of one refusal, built from the diagnostic the
    operator saw.

    `code` and `surface` are lifted to the top level so the router can dedupe
    on `(code, surface)` without re-parsing the nested diagnostic; the full
    diagnostic is kept whole so no context is lost for later classification.
    """
    row: dict[str, object] = {
        "code": diagnostic.code,
        "severity": diagnostic.severity.value,
        "message": diagnostic.message,
        "surface": surface,
        "diagnostic": diagnostic.to_dict(),
    }
    if operation is not None:
        row["operation"] = operation
    return row


def append_refused(path: Path, trace_id: str, refusal: Mapping[str, object]) -> None:
    """Record a refusal that aborted before any EffectPlan existed.

    `trace_id` and `phase` are written last so a `refusal` payload can never
    overwrite the two fields the store is keyed and folded on.
    """
    append_jsonl(
        path,
        {**dict(refusal), "trace_id": trace_id, "phase": PHASE_REFUSED, "recorded_at": _now()},
    )


def record_refusal(
    ctx: "MctlContext",
    diagnostic: Diagnostic,
    *,
    surface: str,
    operation: str | None = None,
) -> str:
    """Append the refusal ledger row and return the trace id it was keyed on.

    The id keyed on is the id the operator was shown -- `render_diagnostic`
    prints `diagnostic.trace_id` -- falling back to the context id so a
    diagnostic that forgot to carry one still resolves. Any write failure
    propagates (OSError); the caller surfaces it loudly rather than swallowing
    it (P6.1).
    """
    trace_id = diagnostic.trace_id or ctx.trace_id
    append_refused(trace_path(ctx.rig_root), trace_id, refusal_row(
        diagnostic, surface=surface, operation=operation
    ))
    return trace_id


def refusal_ledger_unwritable_diagnostic(
    ctx: "MctlContext", error: Exception
) -> Diagnostic:
    """A refusal happened but could not be written down -- a distinct failure
    from the refusal itself, and never allowed to mask it.

    Emitted at the point of the failed ledger write so the loss of the durable
    record announces itself (P6.1) instead of surfacing only when someone later
    finds the trace id resolves to nothing.
    """
    return Diagnostic(
        severity=Severity.FATAL,
        code="MCTL_REFUSAL_LEDGER_UNWRITABLE",
        message=f"Refusal could not be recorded to the trace ledger: {error}.",
        hint="The refusal below still holds; its durable record was lost. "
        "Check permissions on .beads/mctl/traces/.",
        facts={
            "city_path": str(ctx.city_root),
            "data_location": str(trace_path(ctx.rig_root)),
            "implementation_provenance": "mctl refusal ledger (mc-rmqt)",
            "rig_name": ctx.rig_id,
            "rig_path": str(ctx.rig_root),
        },
        trace_id=ctx.trace_id,
    )


def read_rows(rig_root: Path) -> list[dict[str, object]]:
    import json

    traces = rig_root / ".beads" / "mctl" / "traces"
    rows: list[dict[str, object]] = []
    if not traces.is_dir():
        return rows
    for path in sorted(traces.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows


def trace_not_found_diagnostic(ctx: "MctlContext", trace_id: str) -> Diagnostic:
    """Shared by `mctl trace show` and the MCP trace tools."""
    return Diagnostic(
        severity=Severity.FATAL,
        code="MCTL_TRACE_NOT_FOUND",
        message=f"No trace rows recorded for {trace_id!r}.",
        hint="List recent traces under .beads/mctl/traces/.",
        facts={
            "city_path": str(ctx.city_root),
            "implementation_provenance": "mctl trace show",
            "rig_name": ctx.rig_id,
            "rig_path": str(ctx.rig_root),
        },
        trace_id=ctx.trace_id,
    )


def fold(rows: Iterable[Mapping[str, object]], trace_id: str) -> dict[str, object] | None:
    """Fold every phase row for one trace_id into a single TraceRecord."""
    matching = [row for row in rows if row.get("trace_id") == trace_id]
    if not matching:
        return None
    record: dict[str, object] = {
        "trace_id": trace_id,
        "actual_effects": [],
        "blocking_diagnostics": [],
        "phases": [],
    }
    for row in matching:
        phase = str(row.get("phase", ""))
        record["phases"].append(phase)
        if phase == PHASE_PLANNED:
            for key, value in row.items():
                if key not in {"phase", "recorded_at"}:
                    record.setdefault(key, value)
                    record[key] = value if key != "trace_id" else trace_id
        elif phase == PHASE_APPLIED:
            record["actual_effects"] = list(row.get("actual_effects", []))
            record["applied_at"] = row.get("recorded_at")
        elif phase == PHASE_ABORTED:
            record["blocking_diagnostics"] = list(row.get("blocking_diagnostics", []))
            record["aborted_at"] = row.get("recorded_at")
        elif phase == PHASE_REFUSED:
            record["refusal"] = {
                key: value
                for key, value in row.items()
                if key not in {"phase", "recorded_at", "trace_id"}
            }
            record["refused_at"] = row.get("recorded_at")
    record["outcome"] = (
        PHASE_REFUSED
        if PHASE_REFUSED in record["phases"]
        else PHASE_ABORTED
        if PHASE_ABORTED in record["phases"]
        else PHASE_APPLIED
        if PHASE_APPLIED in record["phases"]
        else PHASE_PLANNED
    )
    return record
