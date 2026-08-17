"""Runtime city and rig context resolution for mctl."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
from typing import Mapping

from .diagnostics import Diagnostic, Severity
from .trace import new_trace_id


SOURCE_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CITY_FILE_NAME = "city.toml"


@dataclass(frozen=True)
class MctlContext:
    city_root: Path
    rig_id: str
    rig_root: Path
    rig_db: str
    source_checkout: Path
    paths_toml: Path
    gates_toml: Path
    invocation_cwd: Path
    trace_id: str
    warnings: tuple[Diagnostic, ...]
    discovery_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "city_root": str(self.city_root),
            "discovery_path": self.discovery_path,
            "gates_toml": str(self.gates_toml),
            "invocation_cwd": str(self.invocation_cwd),
            "paths_toml": str(self.paths_toml),
            "rig_db": self.rig_db,
            "rig_id": self.rig_id,
            "rig_root": str(self.rig_root),
            "source_checkout": str(self.source_checkout),
            "trace_id": self.trace_id,
            "warnings": [warning.to_dict() for warning in self.warnings],
        }


class ContextError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.code = diagnostic.code
        self.diagnostic = diagnostic


def resolve_context(
    cwd: Path,
    *,
    city: Path | None,
    rig: str | None,
    require_runtime_city: bool,
    require_explicit_runtime: bool = False,
    env: Mapping[str, str],
) -> MctlContext:
    """Resolve one MathCity rig without invoking or mutating city services."""
    del env  # No established environment convention is currently supported.
    trace_id = new_trace_id()
    invocation_cwd = cwd.expanduser().resolve()
    if (
        require_runtime_city
        and _is_within(invocation_cwd, SOURCE_REPOSITORY_ROOT)
        and (city is None or (require_explicit_runtime and rig is None))
    ):
        raise _error(
            trace_id,
            "MCTL_CONTEXT_SOURCE_CHECKOUT",
            "Runtime context cannot be inferred from the MathCity source checkout.",
            "Pass --city <city-root> --rig mathcity to select a registered runtime rig.",
            cwd=str(invocation_cwd),
        )
    city_root, discovery_path = _discover_city(invocation_cwd, city, trace_id)

    if city_root is None:
        raise _error(
            trace_id,
            "MCTL_CONTEXT_CITY_NOT_FOUND",
            "Could not find city.toml from the current directory.",
            "Pass --city <city-root> and --rig <rig-id>.",
            cwd=str(invocation_cwd),
        )

    city_file = city_root / CITY_FILE_NAME
    config = _load_city_config(city_file, trace_id)
    rig_entries = config.get("rigs")
    if not isinstance(rig_entries, list):
        raise _error(
            trace_id,
            "MCTL_CONTEXT_RIGS_MISSING",
            "city.toml does not contain a registered rig list.",
            "Register a rig in city.toml, then rerun mctl context.",
            city_root=str(city_root),
        )

    selected_rig, warnings = _select_rig(rig_entries, rig, trace_id, city_root)
    rig_id = selected_rig["name"]
    rig_root = _resolve_rig_root(selected_rig, city_root)
    rig_db = selected_rig.get("db", rig_id)
    if not isinstance(rig_db, str) or not rig_db:
        raise _error(
            trace_id,
            "MCTL_CONTEXT_INVALID_RIG_DB",
            "The selected rig has an invalid database name.",
            "Set a non-empty db value in the rig configuration.",
            city_root=str(city_root),
            rig_id=rig_id,
        )

    source_checkout = _resolve_source_checkout(selected_rig, config, city_root, trace_id)
    paths_toml = source_checkout / "assets" / "brief-pipeline" / "paths.toml"
    gates_toml = source_checkout / "assets" / "brief-pipeline" / "gates.toml"
    _require_file(paths_toml, "MCTL_CONTEXT_MISSING_PATHS_TOML", trace_id, rig_id)
    _require_file(gates_toml, "MCTL_CONTEXT_MISSING_GATES_TOML", trace_id, rig_id)

    return MctlContext(
        city_root=city_root,
        rig_id=rig_id,
        rig_root=rig_root,
        rig_db=rig_db,
        source_checkout=source_checkout,
        paths_toml=paths_toml,
        gates_toml=gates_toml,
        invocation_cwd=invocation_cwd,
        trace_id=trace_id,
        warnings=tuple(warnings),
        discovery_path=discovery_path,
    )


def _discover_city(cwd: Path, city: Path | None, trace_id: str) -> tuple[Path | None, str]:
    if city is not None:
        candidate = city.expanduser().resolve()
        city_root = candidate.parent if candidate.name == CITY_FILE_NAME else candidate
        if not (city_root / CITY_FILE_NAME).is_file():
            raise _error(
                trace_id,
                "MCTL_CONTEXT_CITY_NOT_FOUND",
                "The requested city root does not contain city.toml.",
                "Pass --city <city-root> for a registered Gas City root.",
                city_root=str(city_root),
            )
        return city_root, "explicit --city"

    for directory in (cwd, *cwd.parents):
        if (directory / CITY_FILE_NAME).is_file():
            return directory, "cwd ancestry"
    return None, "unresolved"


def _load_city_config(city_file: Path, trace_id: str) -> dict[str, object]:
    try:
        with city_file.open("rb") as handle:
            parsed = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise _error(
            trace_id,
            "MCTL_CONTEXT_INVALID_CITY_TOML",
            "Could not parse city.toml.",
            "Fix the city configuration before running mctl context.",
            city_file=str(city_file),
            error=str(error),
        ) from error
    if not isinstance(parsed, dict):
        raise _error(
            trace_id,
            "MCTL_CONTEXT_INVALID_CITY_TOML",
            "city.toml must contain a TOML table.",
            city_file=str(city_file),
        )
    return parsed


def _select_rig(
    rig_entries: list[object], rig: str | None, trace_id: str, city_root: Path
) -> tuple[dict[str, object], list[Diagnostic]]:
    valid_rigs = [entry for entry in rig_entries if isinstance(entry, dict) and isinstance(entry.get("name"), str)]
    if rig is not None:
        for entry in valid_rigs:
            if entry["name"] == rig:
                return entry, []
        raise _error(
            trace_id,
            "MCTL_CONTEXT_UNKNOWN_RIG",
            f"Rig {rig!r} is not registered in city.toml.",
            "Pass a rig shown in the city configuration.",
            city_root=str(city_root),
            requested_rig=rig,
        )
    if len(valid_rigs) == 1:
        selected = valid_rigs[0]
        return selected, [
            Diagnostic(
                severity=Severity.WARN,
                code="MCTL_CONTEXT_IMPLICIT_RIG",
                message=f"Selected the only registered rig: {selected['name']}.",
                hint="Pass --rig explicitly when the city gains additional rigs.",
                facts={"rig_id": selected["name"]},
                trace_id=trace_id,
            )
        ]
    raise _error(
        trace_id,
        "MCTL_CONTEXT_RIG_REQUIRED",
        "The city has multiple registered rigs and none was selected.",
        "Pass --rig <rig-id>.",
        city_root=str(city_root),
    )


def _resolve_source_checkout(
    rig: dict[str, object], config: dict[str, object], city_root: Path, trace_id: str
) -> Path:
    source = rig.get("source_checkout")
    if not isinstance(source, str):
        source = _import_source(rig.get("imports"))
    if not isinstance(source, str):
        defaults = config.get("defaults")
        if isinstance(defaults, dict):
            default_rig = defaults.get("rig")
            if isinstance(default_rig, dict):
                source = _import_source(default_rig.get("imports"))
    if not isinstance(source, str) or not source:
        raise _error(
            trace_id,
            "MCTL_CONTEXT_SOURCE_CHECKOUT_MISSING",
            "The selected rig has no MathCity source checkout configured.",
            "Configure rigs.imports.mathcity.source or pass a city with that import.",
            city_root=str(city_root),
            rig_id=str(rig["name"]),
        )
    source_path = Path(source).expanduser()
    if not source_path.is_absolute():
        source_path = city_root / source_path
    return source_path.resolve()


def _import_source(imports: object) -> str | None:
    if not isinstance(imports, dict):
        return None
    mathcity = imports.get("mathcity")
    if isinstance(mathcity, dict):
        source = mathcity.get("source")
        if isinstance(source, str):
            return source
    return None


def _resolve_rig_root(rig: dict[str, object], city_root: Path) -> Path:
    configured = rig.get("path")
    if isinstance(configured, str) and configured:
        candidate = Path(configured).expanduser()
        return (candidate if candidate.is_absolute() else city_root / candidate).resolve()
    return (city_root / str(rig["name"])).resolve()


def _require_file(path: Path, code: str, trace_id: str, rig_id: str) -> None:
    if not path.is_file():
        raise _error(
            trace_id,
            code,
            f"Required pipeline file is missing: {path.name}.",
            "Restore the file in the selected MathCity source checkout.",
            rig_id=rig_id,
            path=str(path),
        )


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _error(trace_id: str, code: str, message: str, hint: str | None = None, **facts: str) -> ContextError:
    return ContextError(
        Diagnostic(
            severity=Severity.FATAL,
            code=code,
            message=message,
            hint=hint,
            facts=facts,
            trace_id=trace_id,
        )
    )
