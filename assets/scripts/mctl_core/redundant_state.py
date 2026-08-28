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
    # The brief root every other artifact path is derived from. Exposed, not
    # recomputed: artifact_layout() is the single resolver, and a caller that
    # re-derived the root would be the second resolution rule this module
    # exists to prevent.
    root: Path
    pile: Path
    stack: Path
    stack_index: Path
    decisions: Path
    legacy_manifest: Path


@dataclass(frozen=True)
class JsonlReadResult:
    rows: tuple[dict[str, object], ...]
    parse_error: str | None = None


@dataclass(frozen=True)
class LegacyManifestState:
    path: Path
    rows: tuple[dict[str, object], ...]
    parse_error: str | None = None

    @property
    def nonterminal_rows(self) -> tuple[dict[str, object], ...]:
        """Rows whose status is not a settled outcome.

        PREFIX-matched, deliberately, and it must stay that way. A settled
        status carries its disposition inline -- `adjudicated:defer-c(7d)`,
        `adjudicated:approve-b(push=false)`, `adjudicated:close(...)` -- so an
        exact-equality test reads every one of them as unsettled.

        This was exact-equality until 2026-08-20 and the mismatch was not
        cosmetic. `brief-decisions-track-inventory.py::is_terminal_status`
        prefix-matches the same concept, so the migrator PRESERVED 43 rows as
        terminal while this gate BLOCKED the same 43 as non-terminal --
        structurally unreachable by any migration run, because the tool
        excluded them before the plan was built. One brief-system concept,
        two predicates, and on compound statuses they could never agree.

        `rescinded`, `auto-dispatched` and `superseded` were absent here and
        present there; they are settled outcomes and belong in both.

        Keep this list and TERMINAL_PREFIXES in the migrator identical. If they
        drift again the symptom is silent: rows that no migration can reach and
        a gate that will not clear.
        """
        return tuple(
            row for row in self.rows if not _is_terminal_status(str(row.get("status", "")))
        )


#: Settled-outcome prefixes. MUST match TERMINAL_PREFIXES in
#: assets/scripts/brief-decisions-track-inventory.py -- see nonterminal_rows.
TERMINAL_STATUS_PREFIXES = (
    "adjudicated",
    "rescinded",
    "auto-dispatched",
    "moot",
    "superseded",
    "closed",
    "done",
    "terminal",
    "rejected",
)


def _is_terminal_status(status: str) -> bool:
    s = status.strip().lower()
    return any(s.startswith(prefix) for prefix in TERMINAL_STATUS_PREFIXES)


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
        root=root,
        pile=pile,
        stack=stack,
        stack_index=manifest,
        decisions=decisions,
        legacy_manifest=ctx.rig_root / ".beads" / "decisions-track" / "manifest.jsonl",
    )


def scan_artifacts(
    layout: ArtifactLayout,
    brief_id: str,
    decision_state: str,
    legacy_state: LegacyManifestState | None = None,
) -> tuple[RedundantArtifact, ...]:
    stack_rows = tuple(_read_jsonl(layout.stack_index))
    stack_row = next((row for row in stack_rows if _row_id(row) == brief_id), None)
    pile_artifact = _pile_artifact(layout, brief_id)
    cache_path = layout.decisions / f"{brief_id}.toml"
    legacy = legacy_manifest_state(layout) if legacy_state is None else legacy_state
    legacy_row = next((row for row in legacy.rows if _row_id(row) == brief_id), None)
    return (
        pile_artifact,
        _stack_artifact(layout, stack_row, decision_state),
        _toml_artifact(cache_path, brief_id),
        _legacy_artifact(layout.legacy_manifest, legacy_row, legacy.parse_error),
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
    return legacy_manifest_state(layout).nonterminal_rows


def legacy_manifest_state(layout: ArtifactLayout) -> LegacyManifestState:
    result = _read_jsonl_strict(layout.legacy_manifest)
    return LegacyManifestState(layout.legacy_manifest, result.rows, result.parse_error)


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


def _pile_artifact(layout: ArtifactLayout, brief_id: str) -> RedundantArtifact:
    """Resolve the pile cache file for `brief_id` (#128).

    The exact-name form `<brief_id>.md` was the only one consulted, but the
    deposited convention is frequently `<brief_id>-<slug>.md`, so a file that
    exists reported `missing`.

    On the numbers, precisely, because two different populations are easy to
    conflate here: of the 12 `.md` files in the live rig piles when #128 was
    filed, 5 carried an exact `<brief_id>.md` name and 7 carried a slug. That
    is a count of FILENAME SHAPES. It is NOT a claim that 5 of 12 listed
    briefs resolved their cache file -- #128's own measurement found the listed
    brief ids and the pile filenames to be largely disjoint populations, so the
    resolution rate against the listing is lower and this fix does not change
    it. That half is the issue's live symptom and is untouched here.

    Exact wins outright when present, so an unambiguous deposit is never
    reinterpreted. Otherwise the slug candidates are considered, and the `-`
    separator is required: without it `mc-ab` would claim `mc-abc-x.md`, and a
    prefix collision is precisely the kind of wrong-but-plausible answer this
    check exists to avoid.

    Two or more candidates report `ambiguous` rather than resolving by sort
    order. Silently taking the first would replace a false `missing` with a
    false `present` -- worse, because it names a specific file as the brief's
    cache when the tool cannot tell which one is.
    """
    exact = layout.pile / f"{brief_id}.md"
    if exact.is_file():
        return _file_artifact("pile", exact)
    if not layout.pile.is_dir():
        return _file_artifact("pile", exact)
    candidates = sorted(
        path
        for path in layout.pile.glob(f"{brief_id}-*.md")
        if path.is_file()
    )
    if len(candidates) == 1:
        return _file_artifact("pile", candidates[0])
    if len(candidates) > 1:
        return RedundantArtifact(
            kind="pile",
            path=layout.pile,
            state="ambiguous",
            detail=(
                f"{len(candidates)} candidate cache files match this brief id: "
                + ", ".join(path.name for path in candidates)
            ),
        )
    return _file_artifact("pile", exact)


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


def _legacy_artifact(
    path: Path, row: dict[str, object] | None, parse_error: str | None
) -> RedundantArtifact:
    if parse_error is not None:
        return RedundantArtifact(
            "legacy_decisions_track", path, "inconsistent", "legacy migration manifest could not be parsed"
        )
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


def _read_jsonl_strict(path: Path) -> JsonlReadResult:
    if not path.is_file():
        return JsonlReadResult(())
    rows: list[dict[str, object]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    parsed = json.loads(stripped)
                except json.JSONDecodeError as error:
                    return JsonlReadResult((), f"{path}:{line_number}: {error.msg}")
                if not isinstance(parsed, dict):
                    return JsonlReadResult((), f"{path}:{line_number}: row is not a JSON object")
                rows.append(parsed)
    except OSError as error:
        return JsonlReadResult((), f"{path}: {error}")
    return JsonlReadResult(tuple(rows))


def _row_id(row: dict[str, object]) -> str | None:
    # `brief_bead` leads: it is the row's typed statement of the brief's own
    # decision bead (#234), so a bead-backed brief whose `slug` is only the
    # filename stem still joins to its row by bead id. The `isinstance str`
    # guard makes a `brief_bead: null` -- a declared no-subject brief (B2.1a) --
    # fall through rather than resolve to a bogus id.
    for key in ("brief_bead", "brief_id", "bead_id", "slug", "id"):
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
