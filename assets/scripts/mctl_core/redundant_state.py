"""Read-only inspection of non-canonical brief cache artifacts."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tomllib
from typing import Iterable

from .context import MctlContext


@dataclass(frozen=True)
class RedundantArtifact:
    kind: str
    path: Path
    state: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {
            "detail": self.detail,
            "kind": self.kind,
            "path": str(self.path),
            "state": self.state,
        }


@dataclass(frozen=True)
class ArtifactLayout:
    pile: Path
    stack: Path
    stack_index: Path
    decisions: Path
    legacy_manifest: Path


def artifact_layout(ctx: MctlContext) -> ArtifactLayout:
    paths = _read_paths(ctx.paths_toml)
    root_value = paths.get("brief_root") or paths.get("root") or ".beads/briefs"
    root = _rig_relative(ctx.rig_root, root_value)
    pile = _rig_relative(ctx.rig_root, paths.get("pile", str(root.relative_to(ctx.rig_root) / ".pile")))
    stack = _rig_relative(ctx.rig_root, paths.get("stack", str(root.relative_to(ctx.rig_root) / "stack")))
    manifest = _rig_relative(
        ctx.rig_root,
        paths.get("manifest", str(stack.relative_to(ctx.rig_root) / ".index.jsonl")),
    )
    decisions = _rig_relative(
        ctx.rig_root, paths.get("decisions", str(root.relative_to(ctx.rig_root) / "decisions"))
    )
    return ArtifactLayout(
        pile=pile,
        stack=stack,
        stack_index=manifest,
        decisions=decisions,
        legacy_manifest=ctx.rig_root / ".beads" / "decisions-track" / "manifest.jsonl",
    )


def scan_artifacts(layout: ArtifactLayout, brief_id: str, decision_state: str) -> tuple[RedundantArtifact, ...]:
    stack_rows = tuple(_read_jsonl(layout.stack_index))
    stack_row = next((row for row in stack_rows if _row_id(row) == brief_id), None)
    pile_path = layout.pile / f"{brief_id}.md"
    cache_path = layout.decisions / f"{brief_id}.toml"
    legacy_rows = tuple(_read_jsonl(layout.legacy_manifest))
    legacy_row = next((row for row in legacy_rows if _row_id(row) == brief_id), None)
    return (
        _file_artifact("pile", pile_path),
        _stack_artifact(layout, stack_row, decision_state),
        _toml_artifact(cache_path, brief_id),
        _legacy_artifact(layout.legacy_manifest, legacy_row),
    )


def orphan_decision_cache_ids(layout: ArtifactLayout) -> tuple[str, ...]:
    if not layout.decisions.is_dir():
        return ()
    ids: list[str] = []
    for path in sorted(layout.decisions.glob("*.toml")):
        brief_id = _toml_brief_id(path)
        if brief_id:
            ids.append(brief_id)
    return tuple(ids)


def orphan_markdown_cache_ids(layout: ArtifactLayout) -> tuple[tuple[str, Path], ...]:
    """Return pile/stack Markdown cache files independent of canonical beads."""
    files: list[tuple[str, Path]] = []
    for kind, directory in (("pile", layout.pile), ("stack", layout.stack)):
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            files.append((path.stem, path))
    return tuple(files)


def legacy_nonterminal_rows(layout: ArtifactLayout) -> tuple[dict[str, object], ...]:
    terminal = {"closed", "done", "terminal", "adjudicated", "rejected", "moot"}
    return tuple(
        row
        for row in _read_jsonl(layout.legacy_manifest)
        if str(row.get("status", "")).lower() not in terminal
    )


def _read_paths(path: Path) -> dict[str, str]:
    try:
        with path.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    paths = raw.get("paths")
    if not isinstance(paths, dict):
        return {}
    return {key: value for key, value in paths.items() if isinstance(key, str) and isinstance(value, str)}


def _rig_relative(rig_root: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else rig_root / candidate


def _file_artifact(kind: str, path: Path) -> RedundantArtifact:
    return RedundantArtifact(
        kind=kind,
        path=path,
        state="present" if path.is_file() else "missing",
        detail="redundant cache file" if path.is_file() else "redundant cache file is absent",
    )


def _stack_artifact(
    layout: ArtifactLayout, row: dict[str, object] | None, decision_state: str
) -> RedundantArtifact:
    if row is None:
        return RedundantArtifact(
            "stack_index", layout.stack_index, "missing", "no stack index row"
        )
    raw_path = row.get("path")
    stack_path = Path(raw_path) if isinstance(raw_path, str) else layout.stack / "<missing-path>"
    if not stack_path.is_absolute():
        stack_path = layout.stack / stack_path
    if not stack_path.is_file():
        return RedundantArtifact("stack_index", stack_path, "stale", "index row points at a missing file")
    if decision_state in {"adjudicated", "deferred"}:
        return RedundantArtifact(
            "stack_index", stack_path, "inconsistent", "presentable stack disagrees with bead state"
        )
    return RedundantArtifact("stack_index", stack_path, "present", "redundant stack cache")


def _toml_artifact(path: Path, brief_id: str) -> RedundantArtifact:
    if not path.is_file():
        return RedundantArtifact("decision_toml", path, "missing", "redundant decision cache is absent")
    cached_id = _toml_brief_id(path)
    if cached_id != brief_id:
        return RedundantArtifact("decision_toml", path, "inconsistent", "cache brief id disagrees with filename")
    return RedundantArtifact("decision_toml", path, "present", "redundant decision cache")


def _legacy_artifact(path: Path, row: dict[str, object] | None) -> RedundantArtifact:
    if row is None:
        return RedundantArtifact("legacy_decisions_track", path, "missing", "no legacy migration row")
    return RedundantArtifact(
        "legacy_decisions_track", path, "stale", "legacy migration input requires #38 proof"
    )


def _read_jsonl(path: Path) -> Iterable[dict[str, object]]:
    if not path.is_file():
        return ()
    rows: list[dict[str, object]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    rows.append(parsed)
    except (OSError, json.JSONDecodeError):
        return ()
    return rows


def _row_id(row: dict[str, object]) -> str | None:
    for key in ("brief_id", "bead_id", "slug", "id"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _toml_brief_id(path: Path) -> str | None:
    try:
        with path.open("rb") as handle:
            parsed = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return None
    for key in ("brief_id", "bead_id", "id"):
        value = parsed.get(key)
        if isinstance(value, str) and value:
            return value
    return None
