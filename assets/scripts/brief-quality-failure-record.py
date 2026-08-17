#!/usr/bin/env python3
"""Record brief quality failures from durable rejected-brief directories.

This script is intentionally dependency-free. It is used by a formula check so
the feedback record is derived from `.pile/.rejected/<slug>/` state even when a
worker skips a prompt-only event emission instruction.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_frontmatter(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    data: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and value:
            data[key] = value
    return data


def read_text(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def toml_string(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=True)


def toml_array(values: list[str]) -> str:
    return "[" + ", ".join(toml_string(value) for value in values) + "]"


def normalize_gate_id(raw: str) -> str:
    match = re.fullmatch(r"G(\d+)([A-Za-z]?)", raw.strip())
    if not match:
        return raw.strip()
    suffix = match.group(2).lower()
    return f"G{match.group(1)}{suffix}"


def clean_label(value: str) -> str:
    value = re.sub(r"[*_`|#]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip(" -:\t")


def slugify(value: str, fallback: str = "unknown") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80].strip("-") or fallback


def split_routing_path(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        parts = [part.strip().strip("\"'") for part in value[1:-1].split(",")]
        return [part for part in parts if part]
    return [value.strip("\"'")]


def rejection_file(rejected_dir: Path) -> Path | None:
    for name in ("rejection.md", "rejection-record.md", "rejection.json"):
        candidate = rejected_dir / name
        if candidate.exists():
            return candidate
    return None


def rejection_metadata(path: Path) -> dict[str, str]:
    if path.suffix != ".json":
        return parse_frontmatter(path)
    try:
        data = json.loads(path.read_text(errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if isinstance(value, (str, int, float, bool))}


def extract_failed_gate(rejection_text: str, rejection_meta: dict[str, str]) -> tuple[str, str, str]:
    if rejection_meta.get("failed_gate"):
        gate = normalize_gate_id(rejection_meta["failed_gate"])
        return gate, rejection_meta.get("failed_gate_name", gate), rejection_meta.get("failure_summary", "")

    reason = rejection_meta.get("reason", "")
    reason_match = re.search(
        r"\b(G\d+[A-Za-z]?)\s+(.+?):\s*(FAIL|BLOCKED)\b(?:\s*[-:]\s*(.*))?",
        reason,
        re.IGNORECASE,
    )
    if reason_match:
        gate = normalize_gate_id(reason_match.group(1))
        name = clean_label(reason_match.group(2)) or gate
        summary = clean_label(reason_match.group(4) or reason)
        return gate, name, summary

    lines = rejection_text.splitlines()
    for index, line in enumerate(lines):
        if not re.search(r"\b(FAIL|BLOCKED)\b", line, re.IGNORECASE):
            continue
        match = re.search(r"\bG\d+[A-Za-z]?\b", line)
        if not match:
            continue
        gate = normalize_gate_id(match.group(0))
        tail = line[match.end():]
        name = clean_label(re.split(r"\(|\s+-\s+|\s+\u2014\s+|FAIL|BLOCKED", tail, maxsplit=1)[0])
        if not name:
            name = gate
        summary = ""
        for candidate in lines[index + 1:index + 8]:
            stripped = clean_label(candidate)
            if not stripped or stripped.startswith("---"):
                continue
            if re.match(r"^G\d+[A-Za-z]?\b", stripped):
                continue
            summary = stripped
            break
        return gate, name, summary

    verdict = ""
    for line in lines:
        if "Verdict:" in line:
            verdict = clean_label(line)
            break
    return "G0", "Unknown", verdict


def is_repair_brief(brief_meta: dict[str, str]) -> bool:
    return brief_meta.get("producer_contract") == "brief-producer-repair.v1"


def is_producer_origin(brief_meta: dict[str, str]) -> bool:
    return not is_repair_brief(brief_meta)


def build_record(slug: str, rejected_dir: Path) -> dict[str, Any] | None:
    brief_path = rejected_dir / "brief.md"
    reject_path = rejection_file(rejected_dir)
    if not brief_path.exists() or reject_path is None:
        return None

    brief_meta = parse_frontmatter(brief_path)
    if is_repair_brief(brief_meta):
        return None

    rejection_meta = rejection_metadata(reject_path)
    rejection_text = read_text(reject_path)
    failed_gate, failed_gate_name, failure_summary = extract_failed_gate(rejection_text, rejection_meta)
    if not failure_summary:
        failure_summary = f"Gate rejection recorded for {slug}."
    fingerprint = rejection_meta.get("failure_fingerprint") or slugify(f"{failed_gate}-{failure_summary}")
    source_surface = brief_meta.get("track") or brief_meta.get("brief_kind") or "brief-pile"
    source_formula = brief_meta.get("source_formula") or source_surface
    source_step = brief_meta.get("source_step") or "file-brief"
    source_bead = (
        brief_meta.get("source_bead")
        or brief_meta.get("artifact")
        or brief_meta.get("brief_bead")
        or rejection_meta.get("artifact")
        or "unknown"
    )
    routing_path = split_routing_path(brief_meta.get("routing_path", source_formula))
    observed_at = rejection_meta.get("rejected_at") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "slug": slug,
        "brief_id": brief_meta.get("brief_slug", slug),
        "brief_path": str(brief_path),
        "brief_kind": brief_meta.get("brief_kind") or brief_meta.get("track") or "artifact",
        "gate_profile": rejection_meta.get("gate_profile") or brief_meta.get("gate_profile", "standard"),
        "source_bead": source_bead,
        "source_surface": source_surface,
        "source_formula": source_formula,
        "source_step": source_step,
        "routing_path": routing_path,
        "failed_gate": failed_gate,
        "failed_gate_name": failed_gate_name,
        "failure_summary": failure_summary,
        "failure_fingerprint": fingerprint,
        "observed_at": observed_at,
        "dedupe_key": f"{source_formula}:{failed_gate}:{fingerprint}:{source_bead}",
        "producer_origin": is_producer_origin(brief_meta),
    }


def write_toml(path: Path, fields: list[tuple[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for key, value in fields:
        if isinstance(value, list):
            lines.append(f"{key} = {toml_array([str(item) for item in value])}")
        else:
            lines.append(f"{key} = {toml_string(value)}")
    path.write_text("\n".join(lines) + "\n")


def write_quality_record(path: Path, record: dict[str, Any]) -> bool:
    if path.exists():
        return False
    write_toml(path, [
        ("schema", "brief_quality_failure.v1"),
        ("brief_id", record["brief_id"]),
        ("brief_kind", record["brief_kind"]),
        ("gate_profile", record["gate_profile"]),
        ("source_bead", record["source_bead"]),
        ("source_surface", record["source_surface"]),
        ("failed_gate", record["failed_gate"]),
        ("failure_summary", record["failure_summary"]),
        ("failure_fingerprint", record["failure_fingerprint"]),
        ("status", "untriaged"),
        ("brief_path", record["brief_path"]),
        ("source_formula", record["source_formula"]),
        ("source_step", record["source_step"]),
        ("routing_path", record["routing_path"]),
        ("failed_gate_name", record["failed_gate_name"]),
        ("observed_at", record["observed_at"]),
        ("dedupe_key", record["dedupe_key"]),
    ])
    return True


def write_producer_record(path: Path, record: dict[str, Any]) -> bool:
    if path.exists():
        return False
    write_toml(path, [
        ("schema", "brief-producer-failure.v1"),
        ("brief_id", record["brief_id"]),
        ("brief_path", record["brief_path"]),
        ("source_bead", record["source_bead"]),
        ("source_formula", record["source_formula"]),
        ("source_step", record["source_step"]),
        ("routing_path", record["routing_path"]),
        ("failed_gate", record["failed_gate"]),
        ("failed_gate_name", record["failed_gate_name"]),
        ("failure_summary", record["failure_summary"]),
        ("failure_fingerprint", record["failure_fingerprint"]),
        ("observed_at", record["observed_at"]),
        ("status", "untriaged"),
        ("dedupe_key", record["dedupe_key"]),
    ])
    return True


def record_rejected(brief_root: Path, only_slugs: set[str] | None = None, dry_run: bool = False) -> dict[str, Any]:
    rejected_root = brief_root / ".pile" / ".rejected"
    quality_root = brief_root / ".brief-quality-failure-pile"
    producer_root = brief_root / ".producer-failure-pile"
    created: list[str] = []
    skipped: list[str] = []
    if not rejected_root.exists():
        return {"created": created, "skipped": skipped, "rejected_root": str(rejected_root)}

    for rejected_dir in sorted(path for path in rejected_root.iterdir() if path.is_dir()):
        slug = rejected_dir.name
        if only_slugs is not None and slug not in only_slugs:
            continue
        record = build_record(slug, rejected_dir)
        if record is None:
            skipped.append(slug)
            continue
        quality_path = quality_root / f"{slug}.toml"
        producer_path = producer_root / f"{slug}.toml"
        if not quality_path.exists() and dry_run:
            created.append(str(quality_path))
        elif write_quality_record(quality_path, record):
            created.append(str(quality_path))
        if record["producer_origin"]:
            if not producer_path.exists() and dry_run:
                created.append(str(producer_path))
            elif write_producer_record(producer_path, record):
                created.append(str(producer_path))
    return {"created": created, "dry_run": dry_run, "skipped": skipped, "rejected_root": str(rejected_root)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief-root", default=".beads/briefs")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--slug", action="append", default=[], help="Limit recording to one rejected slug; may be repeated.")
    args = parser.parse_args()
    report = record_rejected(
        Path(args.brief_root).expanduser(),
        only_slugs=set(args.slug) if args.slug else None,
        dry_run=args.dry_run,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
