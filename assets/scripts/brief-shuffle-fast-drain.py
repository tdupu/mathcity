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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


OWNER = "brief-shuffle-fast-drain"
STATUS_PATTERN = re.compile(r"^(.+?):\s*(PASS|N/A|FAIL|BLOCKED|PENDING)\b", re.MULTILINE)
GATE_EVIDENCE_HEADING = re.compile(r"^(?:#{1,6}\s+)?Gate Evidence\s*$", re.MULTILINE)
MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)
CLASSIFIER_STATES = {
    "known_no_brainer",
    "known_non_no_brainer",
    "candidate",
    "capability_blocker",
    "safety_blocked",
}
CLASSIFIER_TIMESTAMP = re.compile(r"classified_at=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


@dataclass(frozen=True)
class Outcome:
    action: str
    slug: str
    reason: str = ""


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


def gate_evidence_section(text: str) -> str | None:
    """Return only the canonical Gate Evidence section, or None if absent."""
    match = GATE_EVIDENCE_HEADING.search(text)
    if match is None:
        return None
    section = text[match.end():]
    next_heading = MARKDOWN_HEADING.search(section)
    return section if next_heading is None else section[:next_heading.start()]


def gate_statuses(text: str) -> dict[str, list[str]]:
    statuses: dict[str, list[str]] = {}
    for match in STATUS_PATTERN.finditer(text):
        statuses.setdefault(match.group(1), []).append(match.group(2))
    return statuses


def classifier_error(text: str) -> str | None:
    lines = [line for line in text.splitlines() if "G9 No-brainer-filter:" in line]
    if len(lines) != 1:
        return "G9 evidence must contain exactly one G9 No-brainer-filter line"
    line = lines[0]
    if not re.search(r"G9 No-brainer-filter:\s*PASS\b", line):
        return "G9 No-brainer-filter evidence must be PASS"
    if not CLASSIFIER_TIMESTAMP.search(line):
        return "G9 evidence must set classified_at=<ISO-8601-utc>"
    states = re.findall(r"classifier_state=([^\s;]+)", line)
    if len(states) != 1 or states[0] not in CLASSIFIER_STATES:
        return "G9 evidence must contain exactly one valid classifier_state"
    state = states[0]
    if state == "known_no_brainer":
        category = re.search(r"category=([A-Za-z0-9._-]+)", line)
        if not category or category.group(1) == "none":
            return "known_no_brainer G9 evidence must set a registry category"
        categories_path = Path(__file__).resolve().parents[1] / "brief-pipeline/no-brainer-categories.toml"
        with categories_path.open("rb") as handle:
            registry = tomllib.load(handle)
        categories = {item.get("id") for item in registry.get("category", [])}
        if category.group(1) not in categories:
            return f"known_no_brainer category is not in registry: {category.group(1)}"
        if "stop_gates_clear=true" not in line:
            return "known_no_brainer G9 evidence requires stop_gates_clear=true"
        confidence = re.search(r"confidence=([0-9]+(?:\.[0-9]+)?)", line)
        if not confidence or float(confidence.group(1)) < 0.85:
            return "known_no_brainer confidence must be >= 0.85"
    elif state == "known_non_no_brainer" and not re.search(r"reason=[^;]+", line):
        return "known_non_no_brainer G9 evidence must set reason"
    elif state == "candidate" and not re.search(r"proposed_registry_extension=[^;]+", line):
        return "candidate G9 evidence must set proposed_registry_extension"
    elif state == "capability_blocker" and not re.search(r"reason=[^;]+", line):
        return "capability_blocker G9 evidence must set blocker reason"
    elif state == "safety_blocked" and not re.search(r"stop_gate=(G5|G5b|L4)", line):
        return "safety_blocked G9 evidence must name stop_gate=G5, G5b, or L4"
    return None


def profile_error(profile: str, metadata: dict[str, str], text: str) -> str | None:
    if profile == "standard":
        if not any(metadata.get(key) for key in ("source_bead", "artifact", "brief_bead")):
            return "standard brief missing provenance metadata"
    elif profile == "decision":
        if metadata.get("brief_kind") != "decision":
            return "decision brief must set brief_kind: decision"
        if metadata.get("feedback_sink") != "brief_quality_failure":
            return "decision brief feedback_sink must equal brief_quality_failure"
        if not (metadata.get("source_bead") or metadata.get("legacy_source")):
            return "decision brief missing source_bead or legacy_source metadata"
        if not re.search(r"^action_block:\s*$", text, re.MULTILINE):
            return "decision brief missing action_block"
        for action in ("on_approve", "on_reject", "on_defer"):
            if not re.search(rf"^\s*{action}:", text, re.MULTILINE):
                return f"decision brief action_block missing {action}"
    elif profile == "lost_bead_filter":
        required = ("source_bead", "fingerprint", "threshold_count", "distinct_bead_count", "replay_command", "false_positive_risk")
        if metadata.get("brief_kind") != "lost_bead_filter":
            return "lost_bead_filter brief must set brief_kind: lost_bead_filter"
        if metadata.get("feedback_sink") != "brief_quality_failure":
            return "lost_bead_filter brief feedback_sink must equal brief_quality_failure"
        missing = next((key for key in required if not metadata.get(key)), None)
        if missing:
            return f"lost_bead_filter brief missing {missing} metadata"
    elif profile == "producer_repair":
        required = ("repair_source_formula", "repair_failed_gate", "repair_failure_fingerprint", "replay_command")
        if metadata.get("brief_kind") != "producer_repair":
            return "producer_repair brief must set brief_kind: producer_repair"
        if metadata.get("producer_contract") != "brief-producer-repair.v1":
            return "producer_repair brief producer_contract must equal brief-producer-repair.v1"
        if metadata.get("feedback_sink") != "brief_quality_failure":
            return "producer_repair brief feedback_sink must equal brief_quality_failure"
        missing = next((key for key in required if not metadata.get(key)), None)
        if missing:
            return f"producer_repair brief missing {missing} metadata"
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
    evidence = gate_evidence_section(text)
    if evidence is None:
        return profile, "missing Gate Evidence section", metadata
    if "G9" in profiles[profile].get("gates", []):
        error = classifier_error(evidence)
        if error:
            return profile, error, metadata
    statuses = gate_statuses(evidence)
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
    marker = {
        "owner": OWNER,
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "claimed_at": utc_now(),
        "source_path": f".pile/{source.name}",
    }
    marker_path = staging_dir / ".claimed_by"
    try:
        marker_path.write_text(json.dumps(marker, sort_keys=True) + "\n", encoding="utf-8")
        source.replace(staged)
    except OSError:
        marker_path.unlink(missing_ok=True)
        staging_dir.rmdir()
        raise
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


def owned_staging_source(staging_dir: Path, brief_root: Path) -> Path | None:
    """Return a validated original pile path for a fast-drain staging claim."""
    if not staging_dir.name.startswith("fast-drain-"):
        return None
    marker = staging_dir / ".claimed_by"
    try:
        claim_data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if claim_data.get("owner") != OWNER:
        return None
    source_path = claim_data.get("source_path")
    if not isinstance(source_path, str):
        return None
    relative = Path(source_path)
    if relative.parts[:1] != (".pile",) or len(relative.parts) != 2 or relative.suffix != ".md":
        return None
    return brief_root / relative


def recovery_rejection_dir(brief_root: Path, slug: str) -> Path:
    rejected_root = brief_root / ".pile" / ".rejected"
    candidate = rejected_root / f"{slug}-recovery"
    suffix = 2
    while candidate.exists():
        candidate = rejected_root / f"{slug}-recovery-{suffix}"
        suffix += 1
    return candidate


def recover_owned_staging(brief_root: Path) -> list[str]:
    """Requeue interrupted fast-drain claims without disturbing foreign staging."""
    staging_root = brief_root / ".staging"
    if not staging_root.exists():
        return []
    recovered: list[str] = []
    for staging_dir in sorted(path for path in staging_root.iterdir() if path.is_dir()):
        source = owned_staging_source(staging_dir, brief_root)
        staged = staging_dir / "brief.md"
        if source is None or not staged.is_file():
            continue
        try:
            if source.exists():
                rejected_dir = recovery_rejection_dir(brief_root, source.stem)
                rejected_dir.mkdir(parents=True)
                rejection = {
                    "slug": source.stem,
                    "gate_profile": parse_frontmatter(staged).get("gate_profile", "standard"),
                    "reason": "owned staging recovery found an existing pile entry",
                    "rejection_kind": "operational_recovery_collision",
                    "feedback_required": False,
                    "source_path": f".pile/{source.name}",
                    "rejected_at": utc_now(),
                }
                (rejected_dir / "rejection.json").write_text(
                    json.dumps(rejection, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8",
                )
                staged.replace(rejected_dir / "brief.md")
            else:
                source.parent.mkdir(parents=True, exist_ok=True)
                staged.replace(source)
            cleanup_own_staging(staging_dir)
        except OSError:
            continue
        recovered.append(source.stem)
    return recovered


def reject_staged(staging_dir: Path, staged: Path, brief_root: Path, slug: str, profile: str, reason: str) -> None:
    rejected_dir = brief_root / ".pile" / ".rejected" / slug
    rejected_dir.mkdir(parents=True, exist_ok=False)
    rejected_brief = rejected_dir / "brief.md"
    rejection_path = rejected_dir / "rejection.json"
    rejection = {
        "slug": slug,
        "gate_profile": profile,
        "reason": reason,
        "source_path": f".pile/{slug}.md",
        "rejected_at": utc_now(),
    }
    try:
        rejection_path.write_text(json.dumps(rejection, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        staged.replace(rejected_brief)
    except OSError:
        if rejected_brief.exists():
            rejected_brief.replace(staged)
        rejection_path.unlink(missing_ok=True)
        rejected_dir.rmdir()
        raise
    cleanup_own_staging(staging_dir)


def process_item(source: Path, brief_root: Path, gate_config: dict[str, Any], apply: bool) -> Outcome:
    slug = source.stem
    profile, reason, _metadata = evaluate(source, gate_config)
    action = "promote" if not reason else "reject"
    if action == "promote" and (brief_root / "stack" / f"{slug}.md").exists():
        action = "reject"
        reason = "duplicate stack slug"
    if not apply:
        return Outcome(action, slug, reason)
    try:
        staging_dir, staged = claim(source, brief_root, slug)
    except FileNotFoundError:
        return Outcome("skipped", slug, "source disappeared before claim")
    except OSError as error:
        return Outcome("skipped", slug, f"unable to claim source: {error}")
    try:
        if action == "promote":
            stack = brief_root / "stack"
            destination = stack / f"{slug}.md"
            if destination.exists():
                action = "reject"
                reason = "duplicate stack slug"
            else:
                stack.mkdir(parents=True, exist_ok=True)
                staged.replace(destination)
                try:
                    append_index(stack, {
                        "slug": slug,
                        "path": f"stack/{slug}.md",
                        "source": f".pile/{slug}.md",
                        "gate_profile": profile,
                        "unlock_count": 0,
                        "created_at": utc_now(),
                    })
                except OSError:
                    destination.replace(staged)
                    raise
                cleanup_own_staging(staging_dir)
                return Outcome("promote", slug)
        reject_staged(staging_dir, staged, brief_root, slug, profile, reason)
        return Outcome("reject", slug, reason)
    except OSError as error:
        return Outcome("skipped", slug, f"disposition failed; staged for recovery: {error}")


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
    report: dict[str, Any] = {
        "apply": args.apply,
        "promoted": [], "rejected": [], "skipped": [], "recovered": [],
        "planned_promoted": [], "planned_rejected": [],
        "reasons": {},
    }
    if args.apply:
        report["recovered"] = recover_owned_staging(brief_root)
    items = selected_pile_items(pile, args.max_items)
    for source in items:
        outcome = process_item(source, brief_root, gate_config, args.apply)
        if outcome.action == "skipped":
            report["skipped"].append(outcome.slug)
        elif args.apply:
            report[{"promote": "promoted", "reject": "rejected"}[outcome.action]].append(outcome.slug)
        else:
            key = {"promote": "promoted", "reject": "rejected"}[outcome.action]
            report[f"planned_{key}"].append(outcome.slug)
        if outcome.reason:
            report["reasons"][outcome.slug] = outcome.reason
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
