#!/usr/bin/env python3
"""Maintain the brief stack index cache.

Dry-run is the default for every command because stack/.index.jsonl is the
human presentation queue. Use --apply for writes.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TERMINAL_INDEX_STATUSES = {"archived", "decided", "adjudicated"}


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
        return True, "terminal_index_status", ""
    path = entry_path(entry)
    if path is not None and path.exists():
        return False, "path_exists", ""
    hit = archive_hit(brief_root, entry)
    if hit is not None:
        return True, "path_absent_archive_present", str(hit)
    return False, "path_absent_no_archive_match", ""


def build_report(apply: bool, command: str, removed: list[dict[str, Any]], kept: int, malformed: int) -> dict[str, Any]:
    return {
        "apply": apply,
        "command": command,
        "removed_count": len(removed),
        "kept_count": kept,
        "malformed_kept_count": malformed,
        "removed": removed,
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
    malformed = 0
    for line in lines:
        if line.entry is None:
            malformed += 1
            continue
        if entry_slug(line.entry) != args.slug:
            continue
        hit = archive_hit(brief_root, line.entry)
        remove_lines.add(line.line_no)
        removed.append({
            "line": line.line_no,
            "slug": args.slug,
            "path": str(entry_path(line.entry) or ""),
            "reason": "explicit_slug_archived_row",
            "archived_at": str(hit or ""),
        })
    report = build_report(args.apply, "remove-archived-row", removed, len(lines) - len(remove_lines), malformed)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.apply and remove_lines:
        rewrite_index(index, lines, remove_lines)
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

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
