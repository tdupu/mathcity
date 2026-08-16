#!/usr/bin/env python3
"""Deterministically promote or reject a bounded batch of brief pile entries."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import socket
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OWNER = "brief-shuffle-fast-drain"
STATUS_PATTERN = re.compile(r"^(.+?):\s*(PASS|N/A|FAIL|BLOCKED|PENDING)\b", re.MULTILINE)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line == "---":
            return metadata
        if not line or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            metadata[key] = value
    return {}


def gate_statuses(text: str) -> dict[str, list[str]]:
    statuses: dict[str, list[str]] = {}
    for match in STATUS_PATTERN.finditer(text):
        statuses.setdefault(match.group(1), []).append(match.group(2))
    return statuses


def profile_error(profile: str, metadata: dict[str, str], text: str) -> str | None:
    if profile == "standard":
        if not any(metadata.get(key) for key in ("source_bead", "artifact", "brief_bead")):
            return "standard brief missing provenance metadata"
    elif profile == "decision":
        if metadata.get("brief_kind") != "decision":
            return "decision brief must set brief_kind: decision"
        if not metadata.get("feedback_sink"):
            return "decision brief missing feedback_sink metadata"
        if not (metadata.get("source_bead") or metadata.get("legacy_source")):
            return "decision brief missing source_bead or legacy_source metadata"
        if not re.search(r"^action_block:\s*$", text, re.MULTILINE):
            return "decision brief missing action_block"
        for action in ("on_approve", "on_reject", "on_defer"):
            if not re.search(rf"^\s*{action}:", text, re.MULTILINE):
                return f"decision brief action_block missing {action}"
    elif profile == "lost_bead_filter":
        required = ("source_bead", "fingerprint", "threshold_count", "distinct_bead_count", "replay_command", "false_positive_risk")
        if metadata.get("brief_kind") != "lost_bead_filter" or not metadata.get("feedback_sink"):
            return "lost_bead_filter brief missing required profile metadata"
        missing = next((key for key in required if not metadata.get(key)), None)
        if missing:
            return f"lost_bead_filter brief missing {missing} metadata"
    elif profile == "producer_repair":
        required = ("repair_source_formula", "repair_failed_gate", "repair_failure_fingerprint", "replay_command")
        if (metadata.get("brief_kind") != "producer_repair"
                or metadata.get("producer_contract") != "brief-producer-repair.v1"
                or not metadata.get("feedback_sink")):
            return "producer_repair brief missing required profile metadata"
        missing = next((key for key in required if not metadata.get(key)), None)
        if missing:
            return f"producer_repair brief missing {missing} metadata"
    elif profile == "no_brainer":
        g9 = [line for line in text.splitlines() if line.startswith("G9 No-brainer-filter:")]
        if len(g9) != 1 or "classified_at=" not in g9[0] or "classifier_state=" not in g9[0]:
            return "no_brainer brief missing classifier evidence"
    return None


def evaluate(path: Path, gate_config: dict[str, Any]) -> tuple[str, str, dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    metadata = parse_frontmatter(path)
    if not metadata:
        return "standard", "invalid or missing frontmatter", metadata
    profile = metadata.get("gate_profile", gate_config["registry"].get("default_profile", "standard"))
    profiles = gate_config.get("profiles", {})
    if profile not in profiles:
        return profile, f"unknown gate profile: {profile}", metadata
    error = profile_error(profile, metadata, text)
    if error:
        return profile, error, metadata
    statuses = gate_statuses(text)
    gates_by_id = {gate["id"]: gate for gate in gate_config.get("gates", [])}
    for gate_id in profiles[profile].get("gates", []):
        gate = gates_by_id.get(gate_id)
        if gate is None:
            return profile, f"gate profile {profile} references unknown gate {gate_id}", metadata
        evidence_key = gate["evidence_key"]
        evidence_statuses = statuses.get(evidence_key, [])
        if evidence_statuses and all(status in ("PASS", "N/A") for status in evidence_statuses):
            continue
        failed_status = next((status for status in evidence_statuses if status not in ("PASS", "N/A")), None)
        if failed_status:
            return profile, f"{evidence_key}: {failed_status}", metadata
        return profile, f"missing required gate {evidence_key}", metadata
    return profile, "", metadata


def selected_pile_items(pile: Path, max_items: int) -> list[Path]:
    if not pile.exists():
        return []
    return sorted(
        (path for path in pile.iterdir() if path.is_file() and path.suffix == ".md" and not path.name.startswith(".")),
        key=lambda path: path.name,
    )[:max_items]


def append_index(stack: Path, row: dict[str, Any]) -> None:
    stack.mkdir(parents=True, exist_ok=True)
    index = stack / ".index.jsonl"
    lock_path = stack / ".manifest.lock"
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        except OSError:
            pass
        try:
            existing = set()
            if index.exists():
                for line in index.read_text(encoding="utf-8").splitlines():
                    try:
                        existing.add(json.loads(line).get("slug"))
                    except json.JSONDecodeError:
                        continue
            if row["slug"] not in existing:
                with index.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
        finally:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def claim(source: Path, brief_root: Path, slug: str) -> tuple[Path, Path]:
    staging_dir = brief_root / ".staging" / f"fast-drain-{os.getpid()}-{slug}"
    staging_dir.mkdir(parents=True, exist_ok=False)
    staged = staging_dir / "brief.md"
    source.replace(staged)
    marker = {
        "owner": OWNER,
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "claimed_at": utc_now(),
        "source_path": f".pile/{source.name}",
    }
    (staging_dir / ".claimed_by").write_text(json.dumps(marker, sort_keys=True) + "\n", encoding="utf-8")
    return staging_dir, staged


def cleanup_own_staging(staging_dir: Path) -> None:
    marker = staging_dir / ".claimed_by"
    if not marker.exists():
        return
    try:
        if json.loads(marker.read_text(encoding="utf-8")).get("owner") != OWNER:
            return
    except json.JSONDecodeError:
        return
    marker.unlink()
    staging_dir.rmdir()


def process_item(source: Path, brief_root: Path, gate_config: dict[str, Any], apply: bool) -> tuple[str, str, str]:
    slug = source.stem
    profile, reason, metadata = evaluate(source, gate_config)
    action = "promote" if not reason else "reject"
    if not apply:
        return action, slug, reason
    staging_dir, staged = claim(source, brief_root, slug)
    if action == "promote":
        stack = brief_root / "stack"
        stack.mkdir(parents=True, exist_ok=True)
        staged.replace(stack / f"{slug}.md")
        append_index(stack, {
            "slug": slug,
            "path": f"stack/{slug}.md",
            "source": f".pile/{slug}.md",
            "gate_profile": profile,
            "unlock_count": 0,
            "created_at": utc_now(),
        })
    else:
        rejected_dir = brief_root / ".pile" / ".rejected" / slug
        rejected_dir.mkdir(parents=True, exist_ok=False)
        staged.replace(rejected_dir / "brief.md")
        rejection = {
            "slug": slug,
            "gate_profile": profile,
            "reason": reason,
            "source_path": f".pile/{slug}.md",
            "rejected_at": utc_now(),
        }
        (rejected_dir / "rejection.json").write_text(json.dumps(rejection, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    cleanup_own_staging(staging_dir)
    return action, slug, reason


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief-root", type=Path, default=Path(".beads/briefs"))
    parser.add_argument("--gate-config", type=Path, default=Path("assets/brief-pipeline/gates.toml"))
    parser.add_argument("--max-items", type=int, default=3)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-external", action="store_true", help="Reserved: this script has no external side effects.")
    args = parser.parse_args()
    if args.max_items < 1:
        parser.error("--max-items must be at least 1")
    with args.gate_config.open("rb") as handle:
        gate_config = tomllib.load(handle)
    brief_root = args.brief_root.expanduser()
    pile = brief_root / ".pile"
    items = selected_pile_items(pile, args.max_items)
    report: dict[str, Any] = {
        "apply": args.apply,
        "promoted": [], "rejected": [], "skipped": [],
        "planned_promoted": [], "planned_rejected": [],
        "reasons": {},
    }
    for source in items:
        action, slug, reason = process_item(source, brief_root, gate_config, args.apply)
        key = {"promote": "promoted", "reject": "rejected"}[action]
        if args.apply:
            report[key].append(slug)
        else:
            report[f"planned_{key}"].append(slug)
        if reason:
            report["reasons"][slug] = reason
    report["remaining_pile"] = len(selected_pile_items(pile, sys.maxsize))
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(
            "brief-shuffle-fast-drain: "
            f"promoted={len(report['promoted'])} rejected={len(report['rejected'])} "
            f"skipped={len(report['skipped'])} remaining_pile={report['remaining_pile']}"
        )
        if not args.apply:
            print("dry-run planned: " + ", ".join(report["planned_promoted"] + report["planned_rejected"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
