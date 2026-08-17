"""Read-only adapters for canonical MathCity decision beads."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Any, Iterable, Mapping


BD_TIMEOUT_SECONDS = 5


@dataclass(frozen=True)
class Bead:
    id: str
    title: str
    status: str
    issue_type: str
    labels: tuple[str, ...]
    source_dependencies: tuple[str, ...]
    created_at: str | None
    updated_at: str | None
    raw: Mapping[str, object]

    @property
    def is_brief(self) -> bool:
        return self.issue_type == "decision" and bool(
            {"brief-open", "brief-closed"}.intersection(self.labels)
        )


class BeadReadError(RuntimeError):
    """The canonical bead source could not be read."""


def read_beads(
    rig_root: Path,
    *,
    fixture_path: Path | None = None,
    timeout: int = BD_TIMEOUT_SECONDS,
) -> tuple[Bead, ...]:
    """Query the canonical bead store, or read an explicitly injected fixture."""
    if fixture_path is not None:
        return tuple(_bead_from_mapping(row) for row in _read_jsonl(fixture_path))
    return tuple(_bead_from_mapping(row) for row in _read_bd(rig_root, timeout))


def _read_jsonl(path: Path) -> Iterable[Mapping[str, object]]:
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                value = json.loads(stripped)
                if not isinstance(value, dict):
                    raise BeadReadError(f"{path}:{line_number} is not a JSON object")
                yield value
    except (OSError, json.JSONDecodeError) as error:
        raise BeadReadError(f"Could not read bead export {path}: {error}") from error


def _read_bd(rig_root: Path, timeout: int) -> Iterable[Mapping[str, object]]:
    try:
        result = subprocess.run(
            ["bd", "list", "--json"],
            cwd=rig_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BeadReadError(f"Could not query beads through bd: {error}") from error
    if result.returncode != 0:
        raise BeadReadError(result.stderr.strip() or "bd list --json failed")
    try:
        parsed: Any = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise BeadReadError(f"bd list --json returned invalid JSON: {error}") from error
    if not isinstance(parsed, list) or not all(isinstance(row, dict) for row in parsed):
        raise BeadReadError("bd list --json did not return a JSON list of objects")
    return parsed


def _bead_from_mapping(raw: Mapping[str, object]) -> Bead:
    bead_id = _string(raw, "id")
    if not bead_id:
        raise BeadReadError("A bead has no string id")
    dependencies = raw.get("dependencies", ())
    source_dependencies = tuple(sorted(_dependency_ids(dependencies)))
    return Bead(
        id=bead_id,
        title=_string(raw, "title") or bead_id,
        status=_string(raw, "status") or "open",
        issue_type=_string(raw, "issue_type") or _string(raw, "type") or "",
        labels=tuple(sorted(_strings(raw.get("labels", ())))),
        source_dependencies=source_dependencies,
        created_at=_string(raw, "created_at"),
        updated_at=_string(raw, "updated_at"),
        raw=raw,
    )


def _dependency_ids(value: object) -> Iterable[str]:
    if not isinstance(value, list):
        return ()
    ids: list[str] = []
    for dependency in value:
        if isinstance(dependency, str):
            ids.append(dependency)
        elif isinstance(dependency, dict):
            for key in ("issue_id", "depends_on_id", "id", "source_id"):
                candidate = dependency.get(key)
                if isinstance(candidate, str) and candidate:
                    ids.append(candidate)
                    break
    return ids


def _string(value: Mapping[str, object], key: str) -> str | None:
    candidate = value.get(key)
    return candidate if isinstance(candidate, str) and candidate else None


def _strings(value: object) -> Iterable[str]:
    if isinstance(value, list):
        return (item for item in value if isinstance(item, str) and item)
    return ()
