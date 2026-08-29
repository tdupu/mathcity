"""Read-only inspection of non-canonical brief cache artifacts."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tomllib
from typing import Iterable

from .context import MctlContext
from .fields import read_frontmatter


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
    # mc-crc4o: last, resolve by BEAD IDENTITY -- the `artifact:` frontmatter key
    # -- for files whose name says nothing about which bead they belong to.
    #
    # Q5 (RESOLVED 2026-08-19) settled the convention: "the briefs are supposed
    # to be decision beads so it should be however beads are looked-up", and
    # names this exact consequence -- scan_artifacts "would fail to find these
    # files even if it were pointed at the correct root."
    #
    # Measured on the live mathcity pile the day this landed: 99 files, four
    # addressable ONLY this way and by no filename at all (mc-g4k2 in
    # mc-cbks.md, mc-99jj in mc-j6uh.md, mc-k4t1s in mc-kjot0.md, mc-jvqq in
    # mc-tfp4.md). Without this they report `missing`, and MBRF021's documented
    # remedy would then CREATE duplicates of artifacts that already exist.
    #
    # Shared with `locate_artifact` rather than reimplemented: one resolution
    # rule, so the validate path and the locate tool cannot disagree about
    # whether an artifact exists -- which is the split this bead is closing.
    claimants = _frontmatter_claimants(layout.pile, brief_id, ".md")
    if len(claimants) == 1:
        return RedundantArtifact(
            kind="pile",
            path=claimants[0],
            state="present",
            detail="redundant cache file, resolved by `artifact:` frontmatter",
        )
    if len(claimants) > 1:
        return RedundantArtifact(
            kind="pile",
            path=layout.pile,
            state="ambiguous",
            detail=(
                f"{len(claimants)} cache files claim this brief id in `artifact:` "
                "frontmatter: " + ", ".join(path.name for path in claimants)
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


# --- locate (mc-8q0g4) -------------------------------------------------------
#
# The typed answer to "where does this bead's artifact live, and is it there?"
#
# Two properties carry the whole point, and both are structural rather than
# advisory. FIRST, the caller names a BEAD, never a path: the root comes from
# `artifact_layout()` above, so searching the wrong tree stops being a move that
# exists. SECOND, an answer that could not have been reached says so. When the
# root is absent, "this rig has piled nothing yet" and "I resolved the wrong
# root" are the same observation, so the verdict is `unknown` -- never `absent`.
#
# That distinction is not fussiness. On 2026-08-28 a `find` under the CITY root
# reported brief mc-tbucy as having no verdict artifact; both artifacts were in
# the RIG root the whole time, and the false absence was published to a peer as
# a correction. The trap is that the wrong root was POPULATED -- 11 decision
# tomls against the right root's 118 -- so the probe returned clean, plausible
# output about a different rig. It did not fail; it exited 0 with an empty list.
#
# Which is why NOT-FOUND and COULD-NOT-LOOK must be different return shapes. A
# typed tool that returned an empty list for both would reproduce that ambiguity
# one layer up, where it would be believed harder for having come from the typed
# surface. `corpus_size` is the other half: it is the "probe a case that must be
# present" control, executed here rather than remembered by the caller.

#: Verdicts. `inconsistent` is preserved rather than folded into `absent`: a
#: file whose recorded id disagrees with its name is a different problem from a
#: file that is not there, and flattening them would hide the one needing a human.
LOCATE_PRESENT = "present"
LOCATE_ABSENT = "absent"
LOCATE_AMBIGUOUS = "ambiguous"
LOCATE_UNKNOWN = "unknown"
LOCATE_INCONSISTENT = "inconsistent"


@dataclass(frozen=True)
class ArtifactFinding:
    """One artifact kind's answer, carrying the evidence for its own verdict."""

    kind: str
    verdict: str
    path: Path | None
    directory: Path
    directory_exists: bool
    corpus_size: int
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {
            "corpus_size": self.corpus_size,
            "detail": self.detail,
            "directory": str(self.directory),
            "directory_exists": self.directory_exists,
            "kind": self.kind,
            "path": str(self.path) if self.path is not None else None,
            "verdict": self.verdict,
        }


@dataclass(frozen=True)
class ArtifactLocation:
    bead_id: str
    resolved_root: Path
    root_exists: bool
    findings: tuple[ArtifactFinding, ...]

    def artifact(self, kind: str) -> ArtifactFinding:
        for finding in self.findings:
            if finding.kind == kind:
                return finding
        raise KeyError(f"no artifact kind {kind!r}; have {[f.kind for f in self.findings]}")

    def to_dict(self) -> dict[str, object]:
        return {
            "artifacts": [finding.to_dict() for finding in self.findings],
            "bead_id": self.bead_id,
            "resolved_root": str(self.resolved_root),
            "root_exists": self.root_exists,
        }


def _resolve_by_id(directory: Path, bead_id: str, suffix: str) -> tuple[str, Path | None, str]:
    """Exact name wins; otherwise a single `<id>-<slug>` candidate; never a guess.

    The `-` separator is required: without it `mc-ab` would claim `mc-abc-x.md`,
    and a prefix collision is exactly the wrong-but-plausible answer this module
    exists to avoid. Two or more candidates report `ambiguous` rather than
    resolving by sort order -- silently taking the first would replace a false
    absence with a false presence, which is worse, because it names a specific
    file as the artifact when the tool cannot tell which one is.
    """
    exact = directory / f"{bead_id}{suffix}"
    if exact.is_file():
        return LOCATE_PRESENT, exact, "resolved by exact name"
    if not directory.is_dir():
        return LOCATE_ABSENT, None, "directory does not exist"
    candidates = sorted(p for p in directory.glob(f"{bead_id}-*{suffix}") if p.is_file())
    if len(candidates) == 1:
        return LOCATE_PRESENT, candidates[0], "resolved by slug"
    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        return LOCATE_AMBIGUOUS, None, f"{len(candidates)} candidates match this id: {names}"
    claimed = _frontmatter_claimants(directory, bead_id, suffix)
    if len(claimed) == 1:
        return LOCATE_PRESENT, claimed[0], "resolved by `artifact:` frontmatter, not by filename"
    if len(claimed) > 1:
        names = ", ".join(p.name for p in claimed)
        return (
            LOCATE_AMBIGUOUS,
            None,
            f"{len(claimed)} files claim this id in `artifact:` frontmatter: {names}",
        )
    return LOCATE_ABSENT, None, "no file matches this id by name or by `artifact:` frontmatter"


def _frontmatter_claimants(directory: Path, bead_id: str, suffix: str) -> list[Path]:
    """Files whose `artifact:` frontmatter names `bead_id`, whatever they are called.

    Bead identity is canonical, so the id in the frontmatter IS the address --
    Taylor, resolving OPEN-DESIGN-QUESTIONS Q5: *"the briefs are supposed to be
    decision beads so it should be however beads are looked-up."* A lookup that
    consults only filenames is reading the wrong key, which Q5 states outright:
    `scan_artifacts` "would fail to find these files even if it were pointed at
    the correct root."

    Measured on the live mathcity pile when this was added: 99 files, 4
    addressable ONLY this way (mc-g4k2 in mc-cbks.md, mc-99jj in mc-j6uh.md,
    mc-k4t1s in mc-kjot0.md, mc-jvqq in mc-tfp4.md), none of them findable by
    filename. Without this, `locate_artifact` reports `absent` for artifacts
    that are right there -- this bead's own defect, inside the fix for it.

    Deliberately a FALLBACK, reached only after exact and slug both miss: it
    opens every file in the directory, and an unambiguous deposit should never
    pay that cost or be reinterpreted by it.

    Parsing goes through `read_frontmatter`, the same parser materialize_plan
    and mctl use, rather than a second hand-rolled fence scan. `mcp_server`'s
    own `_frontmatter_artifact_id` records why: its hand-rolled predecessor
    diverged twice, dropping keys with leading whitespace and capping its scan
    at 64 lines so a later `artifact:` key read as absent.
    """
    if suffix != ".md" or not directory.is_dir():
        return []
    claimants: list[Path] = []
    for path in sorted(directory.glob(f"*{suffix}")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # Unreadable is not "does not claim this id"; skipping it keeps the
            # caller's verdict honest, since a file we could not read cannot be
            # evidence either way.
            continue
        if read_frontmatter(text).get("artifact", "").strip("\"'") == bead_id:
            claimants.append(path)
    return claimants


def locate_artifact(layout: ArtifactLayout, bead_id: str) -> ArtifactLocation:
    """Where `bead_id`'s redundant artifacts are, and whether the answer is knowable.

    `layout` must come from `artifact_layout()`. Nothing here re-derives a path.
    """
    root_exists = layout.root.is_dir()
    kinds = (
        ("pile", layout.pile, ".md"),
        ("stack", layout.stack, ".md"),
        ("decisions", layout.decisions, ".toml"),
    )
    findings: list[ArtifactFinding] = []
    for kind, directory, suffix in kinds:
        directory_exists = directory.is_dir()
        corpus = (
            len([p for p in directory.glob(f"*{suffix}") if p.is_file()])
            if directory_exists
            else 0
        )
        if not root_exists:
            # The one case where absence is unknowable. Reporting `absent` here
            # is the mc-8q0g4 defect itself.
            findings.append(
                ArtifactFinding(
                    kind=kind,
                    verdict=LOCATE_UNKNOWN,
                    path=None,
                    directory=directory,
                    directory_exists=directory_exists,
                    corpus_size=corpus,
                    detail=(
                        f"brief root {layout.root} does not exist, so an absence here "
                        "cannot be distinguished from a root resolved to the wrong tree"
                    ),
                )
            )
            continue
        verdict, path, detail = _resolve_by_id(directory, bead_id, suffix)
        if verdict == LOCATE_ABSENT and corpus == 0:
            detail = f"{detail}; the {kind} corpus is EMPTY, which is also how a wrong root reads"
        findings.append(
            ArtifactFinding(
                kind=kind,
                verdict=verdict,
                path=path,
                directory=directory,
                directory_exists=directory_exists,
                corpus_size=corpus,
                detail=detail,
            )
        )
    return ArtifactLocation(
        bead_id=bead_id,
        resolved_root=layout.root,
        root_exists=root_exists,
        findings=tuple(findings),
    )
