#!/usr/bin/env python3
import argparse, json, re
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
TERMINAL_PREFIXES = ("adjudicated", "rescinded", "auto-dispatched", "moot", "superseded")


def is_terminal_status(status: str) -> bool:
    s = status.strip().lower()
    return any(s.startswith(prefix) for prefix in TERMINAL_PREFIXES)


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

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("--rig-root", required=True)
    inv.add_argument("--output", required=True)
    args = parser.parse_args()
    rows = inventory(Path(args.rig_root))
    out = Path(args.output)
    out.write_text("".join(json.dumps(row, sort_keys=True, separators=(",",":")) + "\n" for row in rows))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
