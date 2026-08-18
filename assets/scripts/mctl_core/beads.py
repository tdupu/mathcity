"""Read-only adapters for canonical MathCity decision beads."""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Iterable, Mapping


DEFAULT_BD_TIMEOUT_SECONDS = 30
BD_TIMEOUT_ENV = "MCTL_BD_TIMEOUT_SECONDS"
# bd reserves exit 13 for "an --if-status/--if-assignee guard no longer held".
BD_GUARD_MISMATCH_EXIT = 13
BD_LIST_ARGS = ("bd", "list", "--all", "--limit", "0", "--json", "--readonly")


def bd_timeout_seconds() -> int:
    """Seconds to allow a bd subprocess.

    A full read of the largest live rig already costs seconds, and a read
    is slowest exactly when the data plane is degraded -- the moment these
    commands are most useful. Keep the ceiling well clear of that, and let
    an operator raise it further per invocation.
    """
    raw = os.environ.get(BD_TIMEOUT_ENV)
    if raw is None:
        return DEFAULT_BD_TIMEOUT_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_BD_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_BD_TIMEOUT_SECONDS


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
        return self.issue_type == "decision"


class BeadReadError(RuntimeError):
    """The canonical bead source could not be read."""


class BeadWriteError(RuntimeError):
    """The canonical bead source could not be updated."""


class BeadRaceLostError(BeadWriteError):
    """Another actor changed the bead first, so the guarded write was skipped.

    bd exits 13 when an --if-status/--if-assignee guard no longer holds. It
    wrote nothing, and retrying the same guard cannot succeed.
    """


@dataclass(frozen=True)
class BeadUpdate:
    id: str
    status: str | None = None
    metadata: Mapping[str, str] | None = None
    defer_until: str | None = None
    # Optimistic-concurrency guard: the status observed when the plan was
    # built. bd writes nothing and exits 13 if it no longer holds.
    if_status: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "metadata": dict(sorted((self.metadata or {}).items())),
        }
        if self.status is not None:
            payload["status"] = self.status
        if self.defer_until is not None:
            payload["defer_until"] = self.defer_until
        payload["if_status"] = self.if_status
        return payload


def read_beads(
    rig_root: Path,
    *,
    fixture_path: Path | None = None,
    timeout: int | None = None,
) -> tuple[Bead, ...]:
    """Query the canonical bead store, or read an explicitly injected fixture."""
    if fixture_path is not None:
        return tuple(_bead_from_mapping(row) for row in _read_jsonl(fixture_path))
    return tuple(_bead_from_mapping(row) for row in _read_bd(rig_root, timeout or bd_timeout_seconds()))


def apply_bead_update(
    rig_root: Path,
    update: BeadUpdate,
    *,
    fixture_path: Path | None = None,
    timeout: int | None = None,
) -> dict[str, object]:
    """Apply one canonical bead update through the fixture seam or bd."""
    if fixture_path is not None:
        _apply_fixture_update(fixture_path, update)
        return {"id": update.id, "mode": "fixture"}
    return _apply_bd_update(rig_root, update, timeout or bd_timeout_seconds())


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
            list(BD_LIST_ARGS),
            cwd=rig_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BeadReadError(f"Could not query beads through bd: {error}") from error
    if result.returncode != 0:
        raise BeadReadError(result.stderr.strip() or f"{' '.join(BD_LIST_ARGS)} failed")
    try:
        parsed: Any = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise BeadReadError(f"{' '.join(BD_LIST_ARGS)} returned invalid JSON: {error}") from error
    if not isinstance(parsed, list) or not all(isinstance(row, dict) for row in parsed):
        raise BeadReadError(f"{' '.join(BD_LIST_ARGS)} did not return a JSON list of objects")
    return parsed


def _apply_bd_update(rig_root: Path, update: BeadUpdate, timeout: int) -> dict[str, object]:
    args = ["bd", "update", update.id]
    if update.status is not None:
        args.extend(("--status", update.status))
    if update.defer_until is not None:
        args.extend(("--defer", update.defer_until))
    for key, value in sorted((update.metadata or {}).items()):
        args.extend(("--set-metadata", f"{key}={value}"))
    if update.if_status is not None:
        args.extend(("--if-status", update.if_status))
    args.append("--json")
    try:
        result = subprocess.run(
            args,
            cwd=rig_root,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BeadWriteError(f"Could not update bead {update.id}: {error}") from error
    if result.returncode == BD_GUARD_MISMATCH_EXIT:
        raise BeadRaceLostError(
            f"another actor changed {update.id!r} before this write "
            f"(bd exit {BD_GUARD_MISMATCH_EXIT}; expected status "
            f"{update.if_status!r})"
        )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise BeadWriteError(detail or f"{' '.join(args)} failed")
    if not result.stdout.strip():
        return {"id": update.id, "mode": "bd", "stdout": ""}
    try:
        parsed: Any = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"id": update.id, "mode": "bd", "stdout": result.stdout.strip()}
    return {"id": update.id, "mode": "bd", "result": parsed}


def _apply_fixture_update(path: Path, update: BeadUpdate) -> None:
    rows = list(_read_jsonl(path))
    changed = False
    rewritten: list[dict[str, object]] = []
    for row in rows:
        mutable = dict(row)
        if mutable.get("id") == update.id:
            if update.status is not None:
                mutable["status"] = update.status
            if update.defer_until is not None:
                mutable["defer_until"] = update.defer_until
            metadata = mutable.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            metadata = dict(metadata)
            metadata.update(update.metadata or {})
            if metadata:
                mutable["metadata"] = metadata
            changed = True
        rewritten.append(mutable)
    if not changed:
        raise BeadWriteError(f"No bead named {update.id!r} exists in {path}")
    path.write_text(
        "".join(f"{json.dumps(row, sort_keys=True)}\n" for row in rewritten),
        encoding="utf-8",
    )


def _bead_from_mapping(raw: Mapping[str, object]) -> Bead:
    bead_id = _string(raw, "id")
    if not bead_id:
        raise BeadReadError("A bead has no string id")
    dependencies = raw.get("dependencies", ())
    source_dependencies = tuple(sorted(_dependency_ids(bead_id, dependencies)))
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


def _dependency_ids(bead_id: str, value: object) -> Iterable[str]:
    if not isinstance(value, list):
        return ()
    ids: list[str] = []
    for dependency in value:
        if isinstance(dependency, str):
            ids.append(dependency)
        elif isinstance(dependency, dict):
            issue_id = dependency.get("issue_id")
            depends_on = _first_string(
                dependency,
                ("depends_on_id", "depends_on_issue_id", "depends_on", "source_id"),
            )
            if issue_id == bead_id and depends_on:
                ids.append(depends_on)
                continue
            if issue_id is None and depends_on:
                ids.append(depends_on)
                continue
            if issue_id != bead_id and isinstance(issue_id, str) and issue_id and depends_on is None:
                ids.append(issue_id)
                continue
            fallback = _first_string(dependency, ("id",))
            if fallback:
                ids.append(fallback)
    return ids


def _first_string(value: Mapping[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _string(value: Mapping[str, object], key: str) -> str | None:
    candidate = value.get(key)
    return candidate if isinstance(candidate, str) and candidate else None


def _strings(value: object) -> Iterable[str]:
    if isinstance(value, list):
        return (item for item in value if isinstance(item, str) and item)
    return ()
