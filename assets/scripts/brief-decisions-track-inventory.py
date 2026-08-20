#!/usr/bin/env python3
import argparse, json, os, re, shutil, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)

def parse_frontmatter(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(errors="replace")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data

def slug_from_file(path: Path) -> tuple[int | None, str]:
    stem = path.name.removesuffix("-brief.md")
    match = re.match(r"^0*(\d+)-(.+)$", stem)
    if not match:
        return None, stem
    return int(match.group(1)), match.group(2)

# A status is confidently TERMINAL (nothing further owed to the human) only if it
# begins with one of these prefixes. Prefix-matched so free-text variants like
# "adjudicated:approve-b(...)" are correctly terminal. Everything else — including
# unrecognised free-text and near-misses like "ready-for-adjudication" — is treated
# as non-terminal and MIGRATED (visible), never preserved-invisible (#38, fix A).
MIGRATABLE_ACTIONS = {"copy_to_pile", "copy_to_pile_deferred", "copy_to_pile_review"}

# ONE definition of settled, shared with the gate that reads the same manifest.
# Two independently-correct copies is how 43 rows became unreachable: this file
# PRESERVED them as terminal while mctl_core/redundant_state.py BLOCKED them as
# non-terminal, so no migration run could ever reach them. Import, never restate.
_MCTL_CORE = Path(__file__).resolve().parent / "mctl_core"
if str(_MCTL_CORE.parent) not in sys.path:
    sys.path.insert(0, str(_MCTL_CORE.parent))
from mctl_core.redundant_state import (  # noqa: E402
    TERMINAL_STATUS_PREFIXES as TERMINAL_PREFIXES,
    _is_terminal_status as is_terminal_status,
)


def action_for(status: str, defer_until: str | None, has_file: bool) -> str:
    if not has_file:
        return "preserve_missing_file"
    # Fail-closed (#38): preserve ONLY confidently-terminal statuses. Any status that
    # is not confidently terminal migrates to the unified pile as visible legacy
    # decision material (the row carries manifest_status for review) rather than being
    # preserved where B2.10 makes it unreachable. A stray duplicate is visible and
    # adjudicable; a stray disappearance is not detectable from the queue.
    if is_terminal_status(status):
        return "preserve_terminal"
    if status.strip() == "ready" and defer_until:
        return "copy_to_pile_deferred"
    if status.strip() == "ready":
        return "copy_to_pile"
    # Non-terminal, non-`ready` (free-text, mid-decision) — migrate for review.
    return "copy_to_pile_review"

def malformed_manifest_row(line_no: int, reason: str) -> dict:
    return {
        "kind":"malformed_manifest_row",
        "legacy_n":None,
        "legacy_slug":None,
        "legacy_file":None,
        "manifest_status":None,
        "file_status":None,
        "defer_until":None,
        "unlock_count":0,
        "mapped_unified_path":None,
        "migration_action":"preserve_malformed_manifest",
        "reason":f"line {line_no}: {reason}",
    }

def inventory(rig_root: Path) -> list[dict]:
    ddir = rig_root / ".beads/decisions-track"
    manifest = ddir / "manifest.jsonl"
    rows = []
    seen_files = set()
    if manifest.exists():
        for line_no, line in enumerate(manifest.read_text(errors="replace").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                rows.append(malformed_manifest_row(line_no, str(exc)))
                continue
            if not isinstance(row, dict):
                rows.append(malformed_manifest_row(line_no, "manifest row must be a JSON object"))
                continue
            n = row.get("n")
            slug = row.get("slug")
            if isinstance(n, bool) or not isinstance(n, int):
                rows.append(malformed_manifest_row(line_no, "manifest row n must be an integer"))
                continue
            if slug is not None and not isinstance(slug, str):
                rows.append(malformed_manifest_row(line_no, "manifest row slug must be a string"))
                continue
            if slug:
                candidates = [
                    ddir / f"{n:02d}-{slug}-brief.md",
                    ddir / f"{n}-{slug}-brief.md",
                ]
            else:
                candidates = sorted(ddir.glob(f"{n:02d}-*-brief.md")) + sorted(ddir.glob(f"{n}-*-brief.md"))
            legacy_file = next((candidate for candidate in candidates if candidate.exists()), ddir / f"{n}-{slug}-brief.md")
            if legacy_file.exists():
                seen_files.add(legacy_file.resolve())
            fm = parse_frontmatter(legacy_file)
            defer_until = row.get("defer_until") or fm.get("defer_until")
            action = action_for(str(row.get("status","")), defer_until, legacy_file.exists())
            rows.append({
                "kind":"manifest_row",
                "legacy_n":n,
                "legacy_slug":slug,
                "legacy_file":str(legacy_file),
                "manifest_status":row.get("status"),
                "file_status":fm.get("status"),
                "defer_until":defer_until,
                "unlock_count":row.get("unlock_count",0),
                "mapped_unified_path":None,
                "migration_action":action,
                "reason":"manifest_status_and_file_presence",
            })
    for path in sorted(ddir.glob("*-brief.md")):
        if path.resolve() in seen_files:
            continue
        n, slug = slug_from_file(path)
        fm = parse_frontmatter(path)
        rows.append({
            "kind":"file_without_manifest",
            "legacy_n":n,
            "legacy_slug":slug,
            "legacy_file":str(path),
            "manifest_status":None,
            "file_status":fm.get("status"),
            "defer_until":fm.get("defer_until"),
            "unlock_count":0,
            "mapped_unified_path":None,
            "migration_action":"preserve_file_without_manifest",
            "reason":"no_manifest_row",
        })
    return rows


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def read_index_rows(index: Path) -> list[dict]:
    rows = []
    if not index.exists():
        return rows
    for line in index.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def normalize_slug(value: str | None) -> str:
    if not value:
        return ""
    stem = Path(value).stem
    stem = stem.removesuffix("-brief")
    stem = re.sub(r"^\d+-", "", stem)
    return stem


def entry_file_exists(rig_root: Path, entry: dict) -> bool:
    path = entry.get("path")
    if not isinstance(path, str) or not path:
        return False
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = rig_root / p
    return p.exists()


def find_existing_stack_entry(rig_root: Path, indexed: list[dict], row: dict, legacy_source: str, stack_path: Path) -> dict | None:
    legacy_slug = normalize_slug(row.get("legacy_slug"))
    target_stem = normalize_slug(stack_path.name)
    for entry in indexed:
        if entry.get("legacy_source") == legacy_source:
            return entry
    for entry in indexed:
        if not entry_file_exists(rig_root, entry):
            continue
        path = entry.get("path")
        path_name = Path(path).name if isinstance(path, str) else ""
        candidates = {
            normalize_slug(entry.get("slug") if isinstance(entry.get("slug"), str) else ""),
            normalize_slug(path_name),
            normalize_slug(entry.get("source") if isinstance(entry.get("source"), str) else ""),
        }
        if legacy_slug in candidates or target_stem in candidates:
            return entry
    return None


def existing_index_lines(index: Path) -> list[str]:
    if not index.exists():
        return []
    return index.read_text(errors="replace").splitlines()


def legacy_source_for(path: Path) -> str:
    return f"decisions-track/{path.name}"


def stack_entry_for(row: dict, stack_path: Path, legacy_source: str) -> dict:
    entry = {
        "slug": row.get("legacy_slug") or stack_path.stem.removesuffix("-brief"),
        "path": str(stack_path),
        "source": "decisions-track",
        "unlock_count": row.get("unlock_count", 0),
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "brief_kind": "decision",
        "gate_profile": "decision",
        "legacy_source": legacy_source,
        "legacy_n": row.get("legacy_n"),
        "manifest_status": row.get("manifest_status"),
        "migration_action": row.get("migration_action"),
    }
    if row.get("defer_until"):
        entry["defer_until"] = row["defer_until"]
    return entry


def migration_plan(rig_root: Path, marker: Path) -> tuple[list[dict], list[dict]]:
    rows = inventory(rig_root)
    stack = rig_root / ".beads/briefs/stack"
    index = stack / ".index.jsonl"
    indexed = read_index_rows(index)
    plan = []
    for row in rows:
        if row.get("migration_action") not in MIGRATABLE_ACTIONS:
            continue
        legacy_file = Path(str(row.get("legacy_file") or ""))
        if not legacy_file.exists():
            continue
        legacy_source = legacy_source_for(legacy_file)
        stack_path = stack / legacy_file.name
        existing_entry = find_existing_stack_entry(rig_root, indexed, row, legacy_source, stack_path)
        if existing_entry is None:
            action = "migrate"
        elif existing_entry.get("legacy_source") == legacy_source:
            action = "already_indexed"
        else:
            action = "annotate_existing"
        plan.append({
            "action": action,
            "legacy_file": str(legacy_file),
            "legacy_source": legacy_source,
            "stack_path": str(stack_path),
            "index_entry": stack_entry_for(row, stack_path, legacy_source),
            "existing_entry": existing_entry,
            "inventory_row": row,
        })
    return rows, plan


def write_migration_marker(marker: Path, rows: list[dict]) -> None:
    text = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    atomic_write(marker, text)


def apply_migration(rig_root: Path, marker: Path, rows: list[dict], plan: list[dict]) -> None:
    brief_root = rig_root / ".beads/briefs"
    stack = brief_root / "stack"
    migrations = brief_root / "migrations"
    index = stack / ".index.jsonl"
    lock = migrations / ".decisions-track-migration.lock"
    manifest_lock = brief_root / ".manifest.lock"
    stack.mkdir(parents=True, exist_ok=True)
    migrations.mkdir(parents=True, exist_ok=True)
    marker.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o644)
    manifest_lock_fd = os.open(manifest_lock, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            import fcntl
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            fcntl.flock(manifest_lock_fd, fcntl.LOCK_EX)
        except ImportError:
            pass
        existing_lines = existing_index_lines(index)
        parsed_lines: list[dict | None] = []
        for line in existing_lines:
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                parsed_lines.append(None)
                continue
            parsed_lines.append(parsed if isinstance(parsed, dict) else None)
        append_lines = []
        for item in plan:
            if item["action"] != "migrate":
                continue
            legacy_file = Path(item["legacy_file"])
            stack_path = Path(item["stack_path"])
            shutil.copy2(legacy_file, stack_path)
            append_lines.append(json.dumps(item["index_entry"], sort_keys=True, separators=(",", ":")))
        for item in plan:
            if item["action"] != "annotate_existing":
                continue
            existing = item.get("existing_entry")
            if not isinstance(existing, dict):
                continue
            for i, parsed in enumerate(parsed_lines):
                if parsed != existing:
                    continue
                updated = dict(parsed)
                updated["legacy_source"] = item["legacy_source"]
                updated["legacy_n"] = item["inventory_row"].get("legacy_n")
                updated["manifest_status"] = item["inventory_row"].get("manifest_status")
                updated["migration_action"] = item["inventory_row"].get("migration_action")
                updated.setdefault("brief_kind", "decision")
                updated.setdefault("gate_profile", "decision")
                parsed_lines[i] = updated
                break
        rewritten_existing = [
            json.dumps(parsed, sort_keys=True, separators=(",", ":")) if parsed is not None else existing_lines[i]
            for i, parsed in enumerate(parsed_lines)
        ]
        new_lines = rewritten_existing + append_lines
        atomic_write(index, ("\n".join(new_lines) + "\n") if new_lines else "")
        write_migration_marker(marker, rows)
    finally:
        try:
            import fcntl
            fcntl.flock(manifest_lock_fd, fcntl.LOCK_UN)
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        except ImportError:
            pass
        os.close(manifest_lock_fd)
        os.close(lock_fd)

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("--rig-root", required=True)
    inv.add_argument("--output", required=True)
    mig = sub.add_parser("migrate")
    mig.add_argument("--rig-root", required=True)
    mig.add_argument("--marker", required=True)
    mig.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.command == "inventory":
        rows = inventory(Path(args.rig_root))
        out = Path(args.output)
        if not out.parent.exists():
            raise SystemExit(f"output parent does not exist: {out.parent}")
        out.write_text("".join(json.dumps(row, sort_keys=True, separators=(",",":")) + "\n" for row in rows))
        return 0
    if args.command == "migrate":
        rig_root = Path(args.rig_root)
        marker = Path(args.marker)
        rows, plan = migration_plan(rig_root, marker)
        migratable = [item for item in plan if item["action"] == "migrate"]
        annotatable = [item for item in plan if item["action"] == "annotate_existing"]
        report = {
            "apply": args.apply,
            "marker": str(marker),
            "inventory_rows": len(rows),
            "planned_rows": len(plan),
            "migratable_rows": len(plan),
            "copy_rows": len(migratable),
            "annotate_existing_rows": len(annotatable),
            "already_indexed_rows": sum(1 for item in plan if item["action"] == "already_indexed"),
            "items": [
                {
                    "action": item["action"],
                    "legacy_source": item["legacy_source"],
                    "stack_path": item["stack_path"],
                    "migration_action": item["inventory_row"].get("migration_action"),
                    "manifest_status": item["inventory_row"].get("manifest_status"),
                }
                for item in plan
            ],
        }
        print(json.dumps(report, indent=2, sort_keys=True))
        if args.apply:
            if marker.exists():
                raise SystemExit(f"migration marker already exists: {marker}")
            apply_migration(rig_root, marker, rows, plan)
        return 0
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
