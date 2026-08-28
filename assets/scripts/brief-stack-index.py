#!/usr/bin/env python3
"""Maintain the brief stack index cache.

Dry-run is the default for every command because stack/.index.jsonl is the
human presentation queue. Use --apply for writes.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TERMINAL_INDEX_STATUSES = {"archived", "decided", "adjudicated"}

#: Frontmatter keys consulted for a new row's ``source``, in authority order.
#: ``source_bead`` is the explicit declaration; ``artifact`` is what the
#: decisions-to-briefs producer writes instead (`gh-38` carries
#: ``artifact: gh-issue-38`` and no ``source_bead``). Neither present means the
#: brief declares no subject, and the key is omitted rather than guessed --
#: whether "no bead subject" is even legitimate is an open policy question
#: (bead mc-csr), and answering it by inventing a value here would foreclose it.
#:
#: NOTE these name the brief's SUBJECT bead -- the work the brief is about --
#: NEVER the brief's own decision bead. That distinction is `brief_bead` below,
#: and conflating the two is the #234 defect: a reader that took `source` for a
#: bead link found a track name (`decisions-track`) or a file path instead.
SOURCE_FRONTMATTER_KEYS = ("source_bead", "artifact")

#: The frontmatter key that names the brief's OWN canonical decision bead
#: (`skills/check-briefs` step 3 reads `${brief_bead:-$artifact}`). #234: this
#: is the only key that answers "does this stack brief have a bead, and which
#: one?", and no index producer read it, so the index could not answer it.
BRIEF_BEAD_FRONTMATTER_KEY = "brief_bead"

#: Frontmatter keys consulted for ``created_at``. ``deposited_at`` is the
#: producer's own record of when the brief landed. A file mtime is NOT a
#: fallback: it records when the bytes were last touched, which is a different
#: claim, and the index has no way to say which of the two it holds.
CREATED_AT_FRONTMATTER_KEYS = ("deposited_at", "created_at")


@dataclass(frozen=True)
class IndexLine:
    raw: str
    entry: dict[str, Any] | None
    line_no: int


def load_index(index: Path) -> list[IndexLine]:
    if not index.exists():
        return []
    lines: list[IndexLine] = []
    for line_no, raw in enumerate(index.read_text(errors="replace").splitlines(), 1):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            lines.append(IndexLine(raw=raw, entry=None, line_no=line_no))
            continue
        if not isinstance(parsed, dict):
            lines.append(IndexLine(raw=raw, entry=None, line_no=line_no))
            continue
        lines.append(IndexLine(raw=raw, entry=parsed, line_no=line_no))
    return lines


def atomic_write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as handle:
            if lines:
                handle.write("\n".join(lines) + "\n")
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def entry_slug(entry: dict[str, Any]) -> str:
    slug = entry.get("slug")
    return slug if isinstance(slug, str) else ""


def entry_path(entry: dict[str, Any]) -> Path | None:
    path = entry.get("path")
    if not isinstance(path, str) or not path:
        return None
    return Path(path).expanduser()


def archive_candidates(brief_root: Path, entry: dict[str, Any]) -> list[Path]:
    slug = entry_slug(entry)
    path = entry_path(entry)
    basename = path.name if path is not None else ""
    candidates: list[Path] = []
    if basename:
        candidates.extend([
            brief_root / ".adjudicated-archive" / basename,
            brief_root / "archive" / basename,
        ])
    if slug:
        candidates.extend([
            brief_root / ".adjudicated-archive" / f"{slug}.md",
            brief_root / ".adjudicated-archive" / slug,
            brief_root / "archive" / f"{slug}.md",
            brief_root / "archive" / slug,
            brief_root / "archive" / slug / "brief.md",
        ])
        if basename:
            candidates.append(brief_root / "archive" / slug / basename)
    return candidates


def archive_hit(brief_root: Path, entry: dict[str, Any]) -> Path | None:
    for candidate in archive_candidates(brief_root, entry):
        if candidate.exists():
            return candidate
    return None


def should_reconcile_remove(brief_root: Path, entry: dict[str, Any]) -> tuple[bool, str, str]:
    status = entry.get("status")
    if isinstance(status, str) and status.strip().lower() in TERMINAL_INDEX_STATUSES:
        # POLICY B2.15: de-indexing without archiving is not draining, and the
        # rule binds EVERY removal path -- not just remove-archived-row.
        #
        # This branch used to return True here, on the row's own claim about
        # itself, before any archive lookup. Measured on a fixture with no
        # archive directory: the row was removed with
        # reason="terminal_index_status", archived_at="", and the brief was left
        # sitting in stack/ -- structurally the same lying write the sibling
        # subcommand had, under a different name.
        #
        # It was originally carved out of B2.15 as "a semantics change rather
        # than a bug fix". Reviewer trans pushed back that the justification was
        # asserted and not shown; the fixture showed it did not hold. A row
        # saying "adjudicated" is a claim, and a claim is not an archive.
        hit = archive_hit(brief_root, entry)
        if hit is not None:
            return True, "terminal_index_status_archive_present", str(hit)
        return False, "terminal_index_status_no_archive_match", ""
    path = entry_path(entry)
    if path is not None and path.exists():
        return False, "path_exists", ""
    hit = archive_hit(brief_root, entry)
    if hit is not None:
        return True, "path_absent_archive_present", str(hit)
    return False, "path_absent_no_archive_match", ""


def read_frontmatter(text: str) -> dict[str, str]:
    """The leading ``---`` block, as a line matcher rather than a YAML parse.

    Deliberately tolerant, mirroring `mctl_core.fields.read_frontmatter`: live
    briefs carry values a YAML loader rejects outright (an unquoted
    ``needs-revision(...:...;...)`` status, a bare ``[236]``), and a strict
    parse would drop the whole brief instead of losing one key. Re-implemented
    here rather than imported because this script ships as a standalone pack
    asset with no `mctl_core` on its path.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip()
        if not key or key.startswith("#"):
            continue
        fields.setdefault(key, _unquote(value.strip()))
    return fields


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def index_path_value(brief_root: Path, name: str) -> str:
    """The ONE path serialization this script emits: root-relative from `.beads`.

    The live index holds three incompatible forms across 88 rows -- 45
    ``.beads/briefs/stack/x.md``, 40 absolute, 3 bare ``stack/x.md``. Three
    producers already disagree; this one must not become the fourth, so it
    emits the 45-row plurality form and nothing else.

    Why the plurality form and not the absolute one, which is a close second at
    40: an absolute path bakes one machine's `$HOME` into a file that is
    supposed to be a regenerable cache of a rig-relative layout
    (`assets/brief-pipeline/paths.toml` declares every path rig-relative), and
    it is the shape gsp-5h17 already retired once. Relative also makes the
    reader's root explicit instead of implied.

    One rule, applied deterministically: serialize relative to the directory
    that CONTAINS `.beads`, i.e. the rig or city root. A `--brief-root` with no
    `.beads` component -- a fixture -- has no such root, and falls back to
    ``stack/<name>``, which is the same rule with the root being the brief root
    itself, not a second convention.
    """
    target = Path("stack") / name
    parts = brief_root.parts
    if ".beads" in parts:
        first = parts.index(".beads")
        return str(Path(*parts[first:]) / target)
    return str(target)


def slug_for(name: str) -> str:
    """A row's slug: the filename stem, verbatim.

    NOT the stem with ``-brief`` stripped. 46 of the 88 live rows keep the
    suffix in `slug` (`he-a9cfa-brief.md` -> `he-a9cfa-brief`), so stripping it
    would make new rows unjoinable with old ones. Where a `-brief` strip IS
    correct -- deriving a display title -- it is anchored, `re.sub(r'-brief$')`,
    never `.replace`, which would maul `257-decision-brief-gate-profile-brief`.
    """
    return re.sub(r"\.md$", "", name)


def declares_no_subject(text: str, frontmatter: dict[str, str]) -> bool:
    """Whether the brief EXPLICITLY declares it has no bead subject (B2.1a).

    B2.1a is explicit-only: *"Silence is never a declaration."* Two of its
    three markers are visible in the file itself and are the ones checked here
    -- a `[no-subject]` title tag and a whole-line ``Source: none`` body field.
    The third, the `no-subject` label, lives on the bead rather than the file
    and is out of this standalone script's reach; the bead-side surface reports
    it as `MBRF056`. A file carrying none of these is silent, and silence must
    not become a declaration, or the null would swallow the ordinary omission
    it exists to be distinguished from.
    """
    title = frontmatter.get("title", "")
    if "[no-subject]" in title.lower():
        return True
    for line in text.splitlines():
        if line.strip().lower() == "source: none":
            return True
    return False


def new_row(brief_root: Path, path: Path) -> dict[str, Any]:
    """A row for a stack file that has none, carrying only grounded fields.

    Absent means absent. `gate_profile`, `source` and `created_at` appear only
    when the brief itself declares them; `unlock_count` never appears at all,
    because it is a graph measurement this script cannot take and manifest.py
    is explicit that it is "read, never derived". Consumers already tolerate
    its absence -- `brief-drain-manifest.sh` reads `(.unlock_count // 0)`.
    A row that omits a field says "the brief did not declare it"; a row that
    invents 0 says "the brief declared zero", and those are different claims.

    #234: `brief_bead` is three-valued, and the three states are the whole
    point -- a two-valued present/absent field would repeat the misread it
    fixes. A declared id is emitted verbatim; an EXPLICIT B2.1a no-subject
    declaration is emitted as `null`; a brief that says neither omits the key.
    So `"brief_bead": "mc-x"`, `"brief_bead": null` and no `brief_bead` are
    "has this bead", "declares it has none" and "did not say" -- three claims,
    told apart at the row rather than collapsed into nothing.
    """
    text = path.read_text(errors="replace")
    frontmatter = read_frontmatter(text)
    row: dict[str, Any] = {
        "path": index_path_value(brief_root, path.name),
        "slug": slug_for(path.name),
    }
    for key, sources in (
        ("gate_profile", ("gate_profile",)),
        ("source", SOURCE_FRONTMATTER_KEYS),
        ("created_at", CREATED_AT_FRONTMATTER_KEYS),
    ):
        for candidate in sources:
            value = frontmatter.get(candidate, "").strip()
            if value:
                row[key] = value
                break
    brief_bead = frontmatter.get(BRIEF_BEAD_FRONTMATTER_KEY, "").strip()
    if brief_bead:
        row["brief_bead"] = brief_bead
    elif declares_no_subject(text, frontmatter):
        row["brief_bead"] = None
    return row


def serialize_row(row: dict[str, Any]) -> str:
    """Compact and key-sorted, matching 86 of the 88 live rows.

    Appended, never spliced into an existing line. Brief 22's finding was that
    a whole-file re-serialization is what mangled 38 rows in the first place;
    the rule that follows from it is rewrite only the line you change, and this
    command changes none of them.
    """
    return json.dumps(row, sort_keys=True, separators=(",", ":"))


def build_report(
    apply: bool,
    command: str,
    removed: list[dict[str, Any]],
    kept: int,
    malformed: int,
    refused: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "apply": apply,
        "command": command,
        "removed_count": len(removed),
        "kept_count": kept,
        "malformed_kept_count": malformed,
        "removed": removed,
        "refused": refused or [],
    }


def rewrite_index(index: Path, lines: list[IndexLine], remove_lines: set[int]) -> None:
    kept = [line.raw for line in lines if line.line_no not in remove_lines]
    atomic_write_lines(index, kept)


def command_reconcile_archive(args: argparse.Namespace) -> int:
    brief_root = Path(args.brief_root).expanduser()
    index = brief_root / "stack" / ".index.jsonl"
    lines = load_index(index)
    remove_lines: set[int] = set()
    removed: list[dict[str, Any]] = []
    malformed = 0
    for line in lines:
        if line.entry is None:
            malformed += 1
            continue
        should_remove, reason, archived_at = should_reconcile_remove(brief_root, line.entry)
        if not should_remove:
            continue
        remove_lines.add(line.line_no)
        removed.append({
            "line": line.line_no,
            "slug": entry_slug(line.entry),
            "path": str(entry_path(line.entry) or ""),
            "reason": reason,
            "archived_at": archived_at,
        })
    report = build_report(args.apply, "reconcile-archive", removed, len(lines) - len(remove_lines), malformed)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.apply and remove_lines:
        rewrite_index(index, lines, remove_lines)
    return 0


def command_remove_archived_row(args: argparse.Namespace) -> int:
    brief_root = Path(args.brief_root).expanduser()
    index = brief_root / "stack" / ".index.jsonl"
    lines = load_index(index)
    remove_lines: set[int] = set()
    removed: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    malformed = 0
    for line in lines:
        if line.entry is None:
            malformed += 1
            continue
        if entry_slug(line.entry) != args.slug:
            continue
        hit = archive_hit(brief_root, line.entry)
        if hit is None:
            # The guard this subcommand's NAME already promised. It previously
            # computed `hit` only to fill `archived_at`, removed the row
            # unconditionally, and still reported
            # reason="explicit_slug_archived_row" -- asserting an archive
            # nothing had looked for.
            #
            # This runs as the LAST step of adjudication
            # (formulas/brief-record-decision.toml:206-213, "after the archive
            # move succeeds"). That ordering is prose in an agent-executed step,
            # not an enforced sequence, so a skipped or failed archive move used
            # to de-index anyway and leave the brief in stack/ as a stray --
            # the verdict lands and the representations disagree.
            refused.append({
                "line": line.line_no,
                "slug": args.slug,
                "path": str(entry_path(line.entry) or ""),
                "reason": "no archive copy found; refusing to de-index an unarchived brief",
            })
            continue
        remove_lines.add(line.line_no)
        removed.append({
            "line": line.line_no,
            "slug": args.slug,
            "path": str(entry_path(line.entry) or ""),
            "reason": "explicit_slug_archived_row",
            "archived_at": str(hit),
        })
    report = build_report(
        args.apply, "remove-archived-row", removed,
        len(lines) - len(remove_lines), malformed, refused,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.apply and remove_lines:
        rewrite_index(index, lines, remove_lines)
    # Non-zero so the formula step FAILS LOUDLY rather than reporting a
    # de-index it did not perform. Deliberately no --force: an escape hatch
    # would reopen the hole under a friendlier name.
    return 1 if refused else 0


def command_add_missing_rows(args: argparse.Namespace) -> int:
    """Give `stack/*.md` files with no index row one.

    The index had no rebuild path: both existing subcommands only REMOVE, so a
    file that never got a row could never acquire one, and 89 files sat against
    88 rows with the difference invisible to every tool.

    Append-only and idempotent: existing lines are never re-read into Python
    and re-emitted, so a malformed row stays exactly as malformed as it was
    rather than being silently normalised or dropped.
    """
    brief_root = Path(args.brief_root).expanduser()
    stack = brief_root / "stack"
    index = stack / ".index.jsonl"
    lines = load_index(index)

    indexed: set[str] = set()
    malformed = 0
    for line in lines:
        if line.entry is None:
            malformed += 1
            continue
        path = entry_path(line.entry)
        if path is not None:
            # Matched on basename, because the three serializations disagree
            # about everything else. Two rows for one file would otherwise be
            # the FIRST thing a repair tool produced.
            indexed.add(path.name)

    missing = sorted(p for p in stack.glob("*.md") if p.name not in indexed)
    added = [new_row(brief_root, path) for path in missing]

    report = {
        "apply": args.apply,
        "command": "add-missing-rows",
        "added": added,
        "added_count": len(added),
        "existing_row_count": len(lines),
        "malformed_kept_count": malformed,
        "stack_file_count": len(list(stack.glob("*.md"))),
    }
    print(json.dumps(report, indent=2, sort_keys=True))

    if args.apply and added:
        atomic_write_lines(
            index,
            [line.raw for line in lines] + [serialize_row(row) for row in added],
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    reconcile = sub.add_parser("reconcile-archive")
    reconcile.add_argument("--brief-root", required=True)
    reconcile.add_argument("--apply", action="store_true")
    reconcile.set_defaults(func=command_reconcile_archive)

    remove = sub.add_parser("remove-archived-row")
    remove.add_argument("--brief-root", required=True)
    remove.add_argument("--slug", required=True)
    remove.add_argument("--apply", action="store_true")
    remove.set_defaults(func=command_remove_archived_row)

    add_missing = sub.add_parser("add-missing-rows")
    add_missing.add_argument("--brief-root", required=True)
    add_missing.add_argument("--apply", action="store_true")
    add_missing.set_defaults(func=command_add_missing_rows)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
