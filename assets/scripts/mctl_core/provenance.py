"""Dispatch provenance parsing and validation for mctl work commands."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Mapping

from .context import MctlContext
from .diagnostics import Diagnostic, Severity


@dataclass(frozen=True)
class DispatchProvenance:
    bead_id: str
    observed_at: str
    observer: str
    dispatch: Mapping[str, str]
    path: Path

    def to_dict(self) -> dict[str, object]:
        return {
            "bead_id": self.bead_id,
            "dispatch": dict(sorted(self.dispatch.items())),
            "observed_at": self.observed_at,
            "observer": self.observer,
            "path": str(self.path),
            "schema": "dispatch-provenance.v1",
        }


class ProvenanceError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def provenance_path(ctx: MctlContext, bead_id: str) -> Path:
    return ctx.rig_root / ".beads" / "mctl" / "provenance" / f"{bead_id}.toml"


def read_dispatch_provenance(
    ctx: MctlContext, bead_id: str, *, required: bool
) -> DispatchProvenance | None:
    path = provenance_path(ctx, bead_id)
    if not path.is_file():
        if required:
            raise ProvenanceError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MWRK_PROVENANCE_NOT_FOUND",
                    f"No dispatch provenance exists for {bead_id!r}.",
                    bead_id=bead_id,
                    data_location=str(path),
                )
            )
        return None
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ProvenanceError(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MWRK_PROVENANCE_INVALID",
                "Dispatch provenance could not be parsed as TOML.",
                bead_id=bead_id,
                data_location=str(path),
                detail=str(error),
            )
        ) from error
    return _validate(ctx, bead_id, path, raw)


def write_dispatch_provenance(
    ctx: MctlContext,
    *,
    bead_id: str,
    brief_id: str,
    observed_at: str,
    formula_invocation: Mapping[str, object],
) -> DispatchProvenance:
    path = provenance_path(ctx, bead_id)
    target = f"{ctx.rig_id}/gc.run-operator"
    dispatch = {
        "brief_id": brief_id,
        "created_at": observed_at,
        "formula": str(formula_invocation["formula"]),
        "preflight_result": "passed",
        "rig": ctx.rig_id,
        "routing_reason": f"mctl work dispatch from {brief_id}",
        "source": "mathcity.work",
        "target": target,
        "trace_id": ctx.trace_id,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        'schema = "dispatch-provenance.v1"',
        f'bead_id = "{_toml_escape(bead_id)}"',
        f'observed_at = "{_toml_escape(observed_at)}"',
        'observer = "mctl"',
        "",
        "[dispatch]",
    ]
    for key, value in sorted(dispatch.items()):
        lines.append(f'{key} = "{_toml_escape(value)}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return DispatchProvenance(bead_id, observed_at, "mctl", dispatch, path)


def _validate(
    ctx: MctlContext, bead_id: str, path: Path, raw: Mapping[str, object]
) -> DispatchProvenance:
    schema = _schema(ctx)
    errors: list[str] = []
    if raw.get("schema") != "dispatch-provenance.v1":
        errors.append("schema must be dispatch-provenance.v1")
    if raw.get("bead_id") != bead_id:
        errors.append("bead_id must match the requested work bead")
    observed_at = _string(raw, "observed_at")
    observer = _string(raw, "observer")
    if not observed_at:
        errors.append("observed_at must be a non-empty string")
    if not observer:
        errors.append("observer must be a non-empty string")
    dispatch_raw = raw.get("dispatch")
    if not isinstance(dispatch_raw, dict):
        dispatch_raw = {}
        errors.append("[dispatch] table is required")
    required = schema.get("required_dispatch_fields", ())
    for key in required if isinstance(required, list) else ():
        if isinstance(key, str) and not _string(dispatch_raw, key):
            errors.append(f"dispatch.{key} must be a non-empty string")
    source = _string(dispatch_raw, "source")
    sources = schema.get("sources", ())
    if source and isinstance(sources, list) and source not in sources:
        errors.append(f"dispatch.source {source!r} is not allowed")
    preflight = _string(dispatch_raw, "preflight_result")
    preflights = schema.get("preflight_results", ())
    if preflight and isinstance(preflights, list) and preflight not in preflights:
        errors.append(f"dispatch.preflight_result {preflight!r} is not allowed")
    if errors:
        raise ProvenanceError(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MWRK_PROVENANCE_INVALID",
                "Dispatch provenance failed schema validation.",
                bead_id=bead_id,
                data_location=str(path),
                detail="; ".join(errors),
            )
        )
    return DispatchProvenance(
        bead_id=bead_id,
        observed_at=observed_at or "",
        observer=observer or "",
        dispatch={key: value for key, value in dispatch_raw.items() if isinstance(key, str) and isinstance(value, str)},
        path=path,
    )


def _schema(ctx: MctlContext) -> Mapping[str, object]:
    path = ctx.source_checkout / "assets" / "bead-filter" / "dispatch-provenance-schema.toml"
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ProvenanceError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MWRK_PROVENANCE_SCHEMA_UNAVAILABLE",
                "Dispatch provenance schema could not be loaded.",
                data_location=str(path),
                detail=str(error),
            )
        ) from error
    schema = raw.get("schema")
    if not isinstance(schema, dict) or schema.get("id") != "dispatch-provenance.v1":
        raise ProvenanceError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MWRK_PROVENANCE_SCHEMA_UNAVAILABLE",
                "Dispatch provenance schema is missing or has the wrong id.",
                data_location=str(path),
            )
        )
    return schema


def _diagnostic(
    ctx: MctlContext,
    severity: Severity,
    code: str,
    message: str,
    *,
    bead_id: str | None = None,
    data_location: str | None = None,
    detail: str | None = None,
) -> Diagnostic:
    facts = {
        "city_path": str(ctx.city_root),
        "implementation_provenance": "mctl Slice 4 work dispatch controls",
        "rig_name": ctx.rig_id,
        "rig_path": str(ctx.rig_root),
    }
    if bead_id:
        facts["bead_id"] = bead_id
    if data_location:
        facts["data_location"] = data_location
    if detail:
        facts["detail"] = detail
    return Diagnostic(severity, code, message, facts=facts, trace_id=ctx.trace_id)


def _string(value: Mapping[str, object], key: str) -> str | None:
    candidate = value.get(key)
    return candidate if isinstance(candidate, str) and candidate else None


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
