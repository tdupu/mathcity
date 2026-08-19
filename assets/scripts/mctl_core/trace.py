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
    record["outcome"] = (
        PHASE_ABORTED
        if PHASE_ABORTED in record["phases"]
        else PHASE_APPLIED
        if PHASE_APPLIED in record["phases"]
        else PHASE_PLANNED
    )
    return record
