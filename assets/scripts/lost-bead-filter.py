#!/usr/bin/env python3
"""Validate and roll up BEADS lost-bead classification records."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOST_SCHEMA = ROOT / "assets" / "bead-filter" / "lost-bead-schema.toml"
PROV_SCHEMA = ROOT / "assets" / "bead-filter" / "dispatch-provenance-schema.toml"


def fail(message: str) -> None:
    print(f"lost-bead-filter: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_toml(path: Path) -> dict:
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError:
        fail(f"missing file: {path}")
    except tomllib.TOMLDecodeError as exc:
        fail(f"{path}: invalid TOML: {exc}")


def load_schema(path: Path) -> dict:
    data = load_toml(path)
    schema = data.get("schema")
    if not isinstance(schema, dict):
        fail(f"{path}: missing [schema]")
    return schema


def iter_toml(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        fail(f"missing input path: {root}")
    return sorted(root.glob("*.toml"))


def require_string(path: Path, data: dict, dotted: str) -> str:
    current = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            fail(f"{path}: missing {dotted}")
        current = current[part]
    if not isinstance(current, str) or not current:
        fail(f"{path}: {dotted} must be a non-empty string")
    return current


def require_bool(path: Path, data: dict, dotted: str) -> bool:
    current = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            fail(f"{path}: missing {dotted}")
        current = current[part]
    if not isinstance(current, bool):
        fail(f"{path}: {dotted} must be a boolean")
    return current


def require_evidence(path: Path, data: dict) -> None:
    evidence = data.get("finding", {}).get("evidence")
    if not isinstance(evidence, list) or not evidence or not all(isinstance(item, str) and item for item in evidence):
        fail(f"{path}: finding.evidence must be a non-empty string list")


def validate_lost_record(path: Path, data: dict, schema: dict) -> dict:
    if data.get("schema") != "lost-bead-classification.v1":
        fail(f"{path}: missing schema lost-bead-classification.v1")
    require_string(path, data, "bead_id")
    require_string(path, data, "observed_at")
    require_string(path, data, "observer")
    lost_class = require_string(path, data, "finding.lost_class")
    recommendation = require_string(path, data, "disposition.recommendation")
    require_string(path, data, "disposition.rationale")
    require_bool(path, data, "disposition.reversible")
    root_class = require_string(path, data, "root_cause.class")
    source = require_string(path, data, "root_cause.suspected_source")
    require_bool(path, data, "root_cause.repair_candidate")
    require_string(path, data, "root_cause.fingerprint")
    require_evidence(path, data)

    if lost_class not in schema["lost_classes"]:
        fail(f"{path}: invalid finding.lost_class {lost_class}")
    if recommendation not in schema["dispositions"]:
        fail(f"{path}: invalid disposition.recommendation {recommendation}")
    if root_class not in schema["root_causes"]:
        fail(f"{path}: invalid root_cause.class {root_class}")
    if source not in schema["dispatch_sources"]:
        fail(f"{path}: invalid root_cause.suspected_source {source}")
    return data


def validate_provenance_record(path: Path, data: dict, schema: dict) -> dict:
    if data.get("schema") != "dispatch-provenance.v1":
        fail(f"{path}: missing schema dispatch-provenance.v1")
    require_string(path, data, "bead_id")
    require_string(path, data, "observed_at")
    require_string(path, data, "observer")
    dispatch = data.get("dispatch")
    if not isinstance(dispatch, dict):
        fail(f"{path}: missing [dispatch]")
    for key in schema["required_dispatch_fields"]:
        require_string(path, data, f"dispatch.{key}")
    if dispatch["source"] not in schema["sources"]:
        fail(f"{path}: invalid dispatch.source {dispatch['source']}")
    if dispatch["preflight_result"] not in schema["preflight_results"]:
        fail(f"{path}: invalid dispatch.preflight_result {dispatch['preflight_result']}")
    return data


def load_records(root: Path) -> tuple[list[dict], dict[str, dict]]:
    lost_schema = load_schema(LOST_SCHEMA)
    prov_schema = load_schema(PROV_SCHEMA)
    classifications: list[dict] = []
    provenance: dict[str, dict] = {}
    for path in iter_toml(root):
        data = load_toml(path)
        schema_id = data.get("schema")
        if schema_id == "lost-bead-classification.v1":
            classifications.append(validate_lost_record(path, data, lost_schema))
        elif schema_id == "dispatch-provenance.v1":
            record = validate_provenance_record(path, data, prov_schema)
            provenance[record["bead_id"]] = record
        else:
            fail(f"{path}: unknown schema {schema_id!r}")
    return classifications, provenance


def command_validate(args: argparse.Namespace) -> None:
    classifications, provenance = load_records(Path(args.path))
    print(f"lost-bead-filter: PASS classifications={len(classifications)} provenance={len(provenance)}")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def command_rollup_downstream(args: argparse.Namespace) -> None:
    classifications, _ = load_records(Path(args.input))
    groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for record in classifications:
        key = (
            record["finding"]["lost_class"],
            record["disposition"]["recommendation"],
            record["root_cause"]["class"],
            record["root_cause"]["fingerprint"],
        )
        groups[key].append(record)
    rows = []
    for (lost_class, disposition, root_class, fingerprint), items in sorted(groups.items()):
        bead_ids = sorted({item["bead_id"] for item in items})
        if len(bead_ids) < args.threshold:
            continue
        rows.append(
            {
                "schema": "lost-bead-filter-candidate.v1",
                "kind": "downstream_filter_rule",
                "lost_class": lost_class,
                "recommended_disposition": disposition,
                "root_cause": root_class,
                "fingerprint": fingerprint,
                "count": len(bead_ids),
                "bead_ids": bead_ids,
                "decision": "promote repeated lost-bead hand label into downstream filter rule",
            }
        )
    write_jsonl(Path(args.output), rows)


def repair_target(source: str, root_class: str, fingerprint: str) -> tuple[str, str]:
    if source == "unknown":
        return "UNKNOWN_PROVENANCE", "dispatch provenance recording"
    if source == "mathcity.work" and root_class == "no_worker_claimed":
        return "DISPATCH_PRECHECK_MISSING", "mathcity.work verify-assignee gate"
    if root_class == "dead_or_deprecated_target":
        return "TARGET_RESOLUTION_DRIFT", "target resolver validation"
    if root_class == "hidden_human_decision_dependency":
        return "DEPENDENCY_MODEL_GAP", "bead template dependency encoding"
    if root_class == "sync_gap":
        return "SYNC_GAP", "Dolt sync preflight"
    if root_class == "formula_deadlock":
        return "FORMULA_DEADLOCK", "formula progress witness"
    return "ROUTER_MISCLASSIFICATION", f"{source} routing"


def command_rollup_upstream(args: argparse.Namespace) -> None:
    classifications, provenance = load_records(Path(args.input))
    groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for record in classifications:
        if not record["root_cause"]["repair_candidate"]:
            continue
        prov = provenance.get(record["bead_id"], {})
        dispatch = prov.get("dispatch", {})
        source = dispatch.get("source") or record["root_cause"]["suspected_source"]
        formula_or_target = dispatch.get("formula") or dispatch.get("target") or "unknown"
        if source == "unknown":
            formula_or_target = "unknown"
        key = (
            source,
            formula_or_target,
            record["root_cause"]["class"],
            record["root_cause"]["fingerprint"],
        )
        groups[key].append(record)

    rows = []
    for (source, formula_or_target, root_class, fingerprint), items in sorted(groups.items()):
        bead_ids = sorted({item["bead_id"] for item in items})
        if len(bead_ids) < args.threshold:
            continue
        failure_class, target = repair_target(source, root_class, fingerprint)
        rows.append(
            {
                "schema": "lost-bead-upstream-repair-candidate.v1",
                "kind": "upstream_repair_brief",
                "failure_class": failure_class,
                "suspected_source": source,
                "formula_or_target": formula_or_target,
                "root_cause": root_class,
                "fingerprint": fingerprint,
                "repair_target": target,
                "count": len(bead_ids),
                "bead_ids": bead_ids,
                "decision": "file upstream repair brief for repeated lost-bead failure pattern",
            }
        )
    write_jsonl(Path(args.output), rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate")
    validate.add_argument("path")
    validate.set_defaults(func=command_validate)

    downstream = sub.add_parser("rollup-downstream")
    downstream.add_argument("--input", required=True)
    downstream.add_argument("--threshold", type=int, default=3)
    downstream.add_argument("--output", required=True)
    downstream.set_defaults(func=command_rollup_downstream)

    upstream = sub.add_parser("rollup-upstream")
    upstream.add_argument("--input", required=True)
    upstream.add_argument("--threshold", type=int, default=3)
    upstream.add_argument("--output", required=True)
    upstream.set_defaults(func=command_rollup_upstream)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
