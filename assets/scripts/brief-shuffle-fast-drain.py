#!/usr/bin/env python3
"""Deterministically promote or reject a bounded batch of brief pile entries."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


OWNER = "brief-shuffle-fast-drain"
# Longest alternatives first: Python alternation is first-match, so `PASS`
# ahead of `PASSED` would leave `PASSED` unmatched on the trailing `\b`.
# `REQUIRED` is tokenised but never accepted — recognising it turns a
# policy-conformant "execution still owed" declaration into a precise
# rejection reason instead of a misleading "missing required gate".
STATUS_PATTERN = re.compile(
    r"^(.+?):\s*(PASSED|PASS|NOT APPLICABLE|N/A|FAIL|BLOCKED|PENDING|REQUIRED)\b",
    re.MULTILINE,
)
# POLICY B1.4: every gate carries evidence or an explicit N/A.
DEFAULT_ACCEPTED_STATUSES = ("PASS", "N/A")
# POLICY T7 mandates a tri-state declaration for G14 — PASSED / NOT APPLICABLE
# / REQUIRED — of which only the first two are passing states. The widening is
# per-gate, matching brief-check.sh's `require_gate`, so the two gate-evidence
# enforcers accept exactly the same vocabulary.
GATE_ACCEPTED_STATUSES = {
    "G14": ("PASSED", "PASS", "NOT APPLICABLE", "N/A"),
}
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
# gates.toml `kind` for the three safety gates (G5 server-touching, G5b
# user-skill-touching, G12 kill-switch). A brief tripping one is never
# auto-repairable, so the kind IS the repairable flag -- no second list.
STOP_KIND = "stop"
# The pile manifest is the fourth representation of a pile brief, beside the
# file, the rejection sidecar and the bead. `manifest` in paths.toml names the
# STACK index, not this file; the pile manifest has no paths.toml key and no
# reader in mctl, so it is resolved from --brief-root like every other pile path.
PILE_MANIFEST_NAME = "manifest.jsonl"
# flock only serializes writers holding the SAME lock file. `<dir>/.manifest.lock`
# beside the jsonl is the convention append_index already follows for the stack
# index, and <pile>/.manifest.lock already exists on the live city.
MANIFEST_LOCK_NAME = ".manifest.lock"
# POLICY B2.4: "Canonical membership is the bead query: open `type=decision`
# brief beads." B2.3: "any pile-reading process MUST filter to open brief
# beads." This is that query, byte-identical to `mctl_core.beads.BD_LIST_ARGS`
# so the two readers cannot drift into disagreeing about what a pile is. It is
# duplicated rather than imported because this script ships as a standalone
# pack asset with no `mctl_core` on its path (the same constraint
# brief-stack-index.py records at its `parse_frontmatter`).
BD_LIST_ARGS = ("bd", "list", "--all", "--limit", "0", "--json", "--readonly", "--type", "decision")
BD_TIMEOUT_SECONDS = int(os.environ.get("MCTL_BD_TIMEOUT_SECONDS", "120"))
# A bead is a pile member while it is in one of these states. Copied from
# `mctl_core.beads.Bead.is_open`. Anything else -- closed, done -- is
# adjudicated or abandoned, and its pile file is stale cache.
OPEN_BEAD_STATUSES = {"open", "hooked", "in_progress", "blocked", "review", "testing"}


@dataclass(frozen=True)
class Outcome:
    action: str
    slug: str
    reason: str = ""
    # Disposition of the pile-manifest row, reported separately from `action`:
    # the manifest is a cache, so its outcome never changes whether the brief
    # failed its gates. "" means no manifest write was attempted.
    manifest: str = ""
    manifest_detail: str = ""


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


def _is_adjudicated(metadata: dict[str, str]) -> bool:
    """Whether a human already decided this brief.

    Mirrors `mctl_core.verdicts.is_adjudicated`. Duplicated rather than
    imported: this script is a standalone scheduled order and does not import
    `mctl_core`. The two are pinned to agree by
    `tests/mctl/test_fast_drain_adjudicated_guard.py`'s drift test, which fails
    if either copy moves without the other.

    An empty `verdict:` is an ABSENT verdict, not a decision.
    """
    if str(metadata.get("verdict") or "").strip():
        return True
    return str(metadata.get("status") or "").strip().lower().startswith("adjudicated")


# Frontmatter spellings that NAME A BEAD, and therefore answer "what is this
# brief about". Copied from `mctl_core`'s own identity ladder --
# `effects._row_matches` and `redundant_state._row_id` both walk
# ("brief_bead", "brief_id", "bead_id", "slug", "id", "source") -- so the writer
# and the gate stop disagreeing about how provenance is spelled. Measured on the
# live city 2026-08-28: `.pile/.rejected/gt-3ibad0-master-methodology-design/
# brief.md` carries `bead_id: gt-3ibad0` and was rejected as unprovenanced.
#
# `slug` and `id` are DELIBERATELY EXCLUDED from mctl's ladder here, and
# `brief_slug` with them. They are the filename stem, which every producer
# writes; accepting them would satisfy this gate for every brief that has ever
# been written and leave a check that cannot fail (POLICY P6.2) -- worse than no
# check. The ladder is right for JOINING a row to a bead it already has; it is
# too wide for ASSERTING that a bead was named.
STANDARD_PROVENANCE_KEYS = (
    "source_bead",
    "artifact",
    "brief_bead",
    "brief_id",
    "bead_id",
    "source",
)


def profile_error(profile: str, metadata: dict[str, str], text: str) -> str | None:
    if profile == "standard":
        if not any(metadata.get(key) for key in STANDARD_PROVENANCE_KEYS):
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


def gate_failure(gate: Mapping[str, Any], statuses: Mapping[str, list[str]]) -> dict[str, Any] | None:
    """Judge one gate against the evidence. None means it passed.

    `repairable` is derived from the gate's own `kind`, so the repair track
    never needs a second list of which gates may be auto-repaired, and the
    gate's `repair_kind`/`repair_skill` routing rides along on the failure.
    """
    evidence_key = gate["evidence_key"]
    evidence_statuses = statuses.get(evidence_key, [])
    accepted = GATE_ACCEPTED_STATUSES.get(gate["id"], DEFAULT_ACCEPTED_STATUSES)
    if evidence_statuses and all(status in accepted for status in evidence_statuses):
        return None
    failed_status = next((status for status in evidence_statuses if status not in accepted), None)
    # Carry the gate's own repair routing onto the failure. Before this the
    # trinity keys were dead metadata -- nothing in the pack read them -- so a
    # repair pass had no way to learn what a given gate failure needs.
    # `repair_skill` is copied only when the registry declares one; an
    # unassigned gate leaves it absent rather than defaulting to a plausible
    # name that resolves to nothing.
    failure = {
        "gate": gate["id"],
        "evidence_key": evidence_key,
        "repairable": gate["kind"] != STOP_KIND,
        "repair_kind": gate.get("repair_kind", "unassigned"),
    }
    if gate.get("repair_skill"):
        failure["repair_skill"] = gate["repair_skill"]
    if failed_status:
        return {**failure, "status": failed_status, "reason": f"{evidence_key}: {failed_status}"}
    return {**failure, "status": "missing", "reason": f"missing required gate {evidence_key}"}


def evaluate(path: Path, gate_config: dict[str, Any]) -> tuple[str, str, dict[str, str], list[dict[str, Any]]]:
    """Return (profile, reason, metadata, failures).

    `failures` lists EVERY quality gate the brief failed, so one repair pass can
    clear them all. Returning on the first failure meant the sidecar named one
    gate, and a repair built from it fixes one gate per round trip.

    `reason` still names the first failure verbatim. brief-quality-failure-record
    derives `failed_gate` and `failure_fingerprint` from it and the producer
    rollup groups on that fingerprint, so its meaning is load-bearing.

    A frontmatter or profile error yields an EMPTY `failures` list: a malformed
    brief is not a brief whose gates failed, and recording it as one would
    invent a gate failure that never happened.
    """
    text = path.read_text(encoding="utf-8")
    metadata = parse_frontmatter(path)
    if not metadata:
        return "standard", "invalid or missing frontmatter", metadata, []
    # mc-8ehd0: an adjudicated brief is TERMINAL. A machine re-running its gates
    # over a decision a human already made, and rejecting it, discards that
    # decision. Measured 2026-08-28: 8 of the 24 briefs in .pile/.rejected/
    # carried a verdict (7 approve, 1 reject), and 22 of the 24 were rejected
    # for missing provenance metadata -- which an adjudicated brief has no
    # obligation to carry. Placed above the profile lookup so an unknown or
    # since-renamed gate profile cannot discard a verdict either.
    #
    # The empty-string error is deliberate: evaluate()'s contract is
    # tuple[str, str, dict, list], and process_item() branches on
    # `"promote" if not reason else "reject"`, so "" takes the promote branch
    # without changing the return type. Returning None would change it.
    if _is_adjudicated(metadata):
        return metadata.get("gate_profile", "standard"), "", metadata, []
    profile = metadata.get("gate_profile", gate_config["registry"].get("default_profile", "standard"))
    profiles = gate_config.get("profiles", {})
    if profile not in profiles:
        return profile, f"unknown gate profile: {profile}", metadata, []
    error = profile_error(profile, metadata, text)
    if error:
        return profile, error, metadata, []
    evidence = gate_evidence_section(text)
    if evidence is None:
        return profile, "missing Gate Evidence section", metadata, []
    if "G9" in profiles[profile].get("gates", []):
        error = classifier_error(evidence)
        if error:
            return profile, error, metadata, []
    statuses = gate_statuses(evidence)
    gates_by_id = {gate["id"]: gate for gate in gate_config.get("gates", [])}
    profile_gates = profiles[profile].get("gates", [])
    for gate_id in profile_gates:
        if gate_id not in gates_by_id:
            return profile, f"gate profile {profile} references unknown gate {gate_id}", metadata, []
    # Stop gates are judged first, and alone. A server-touching or kill-switched
    # brief must never be handed to an automated repair, so one tripping
    # short-circuits before any quality gate is collected. sorted() is stable,
    # so within each group the profile's own gate order is preserved.
    ordered = sorted(profile_gates, key=lambda gid: gates_by_id[gid]["kind"] != STOP_KIND)
    failures: list[dict[str, Any]] = []
    for gate_id in ordered:
        gate = gates_by_id[gate_id]
        failure = gate_failure(gate, statuses)
        if failure is None:
            continue
        failures.append(failure)
        if gate["kind"] == STOP_KIND:
            return profile, failure["reason"], metadata, [failure]
    if failures:
        return profile, failures[0]["reason"], metadata, failures
    return profile, "", metadata, []


class MembershipError(RuntimeError):
    """The canonical bead store could not be read."""


def rig_root_for(brief_root: Path) -> Path | None:
    """The directory CONTAINING `.beads`, i.e. the rig or city root.

    Same rule brief-stack-index.py serializes against, for the same reason: it
    is derivable from `--brief-root` alone, so no second convention is needed.
    A `--brief-root` with no `.beads` component is a fixture and has no rig
    root; the caller must inject beads instead of guessing a store.
    """
    resolved = brief_root.expanduser().resolve()
    parts = resolved.parts
    if ".beads" not in parts:
        return None
    return Path(*parts[: parts.index(".beads")])


def read_brief_beads(rig_root: Path | None, fixture: Path | None) -> dict[str, str]:
    """Return {brief_bead_id: status} for every `type=decision` bead.

    The fixture seam mirrors `mctl_core.beads.read_beads(fixture_path=...)`,
    and the `type=decision` narrowing applies to BOTH transports: if the
    fixture ignored the filter, every fixture-based test would be blind to a
    mistake in it.

    Raises rather than returning empty on any read failure. An empty result and
    an unreadable store are the same value in Python and opposite facts here --
    "no brief beads" would let every pile file through as unresolved, which is
    exactly the fall-back-to-the-directory behaviour this function exists to
    remove.
    """
    if fixture is not None:
        beads: dict[str, str] = {}
        try:
            for number, line in enumerate(fixture.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise MembershipError(f"{fixture}:{number} is not a JSON object")
                if row.get("issue_type", row.get("type")) != "decision":
                    continue
                bead_id = row.get("id")
                if not isinstance(bead_id, str) or not bead_id:
                    raise MembershipError(f"{fixture}:{number} has no string id")
                beads[bead_id] = str(row.get("status") or "open")
        except (OSError, json.JSONDecodeError) as error:
            raise MembershipError(f"could not read bead fixture {fixture}: {error}") from error
        return beads
    if rig_root is None:
        raise MembershipError(
            "--brief-root has no .beads component, so no rig root can be derived; "
            "pass --bead-fixture to supply canonical brief beads"
        )
    try:
        result = subprocess.run(
            list(BD_LIST_ARGS), cwd=rig_root, text=True, capture_output=True,
            check=False, timeout=BD_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise MembershipError(f"could not query beads through bd: {error}") from error
    if result.returncode != 0:
        raise MembershipError(result.stderr.strip() or f"{' '.join(BD_LIST_ARGS)} failed")
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise MembershipError(f"{' '.join(BD_LIST_ARGS)} returned invalid JSON: {error}") from error
    if not isinstance(parsed, list) or not all(isinstance(row, dict) for row in parsed):
        raise MembershipError(f"{' '.join(BD_LIST_ARGS)} did not return a JSON list of objects")
    return {
        row["id"]: str(row.get("status") or "open")
        for row in parsed
        if isinstance(row.get("id"), str) and row["id"]
    }


def resolve_brief_bead(stem: str, beads: Mapping[str, str]) -> str | None:
    """The brief bead a pile filename names, or None if it names none.

    Two deposit conventions are live, so both are honoured -- the same pair
    `mctl_core.redundant_state._pile_artifact` resolves, and for its reasons:

    - exact `<brief_id>.md` wins outright, so an unambiguous deposit is never
      reinterpreted;
    - otherwise `<brief_id>-<slug>.md`, with the `-` separator REQUIRED --
      without it `mc-ab` would claim `mc-abc-x.md`.

    Two or more prefix candidates return None rather than resolving by sort
    order. Silently taking the first would replace an honest "unknown" with a
    specific wrong bead, and this answer decides whether a brief is drained.
    """
    if stem in beads:
        return stem
    candidates = sorted(bead_id for bead_id in beads if stem.startswith(f"{bead_id}-"))
    if len(candidates) == 1:
        return candidates[0]
    return None


@dataclass(frozen=True)
class Membership:
    """One pile file's canonical membership verdict."""
    path: Path
    bead: str | None
    status: str | None

    @property
    def is_member(self) -> bool:
        # Unresolved is UNKNOWN, not closed. A file naming no brief bead is
        # still drained -- excluding it would silently strand genuinely new
        # deposits -- but it is reported, never silent.
        if self.bead is None:
            return True
        return (self.status or "").lower() in OPEN_BEAD_STATUSES


def classify_pile_items(pile: Path, beads: Mapping[str, str]) -> list[Membership]:
    if not pile.exists():
        return []
    paths = sorted(
        (path for path in pile.iterdir()
         if path.is_file() and path.suffix == ".md" and not path.name.startswith(".")),
        key=lambda path: path.name,
    )
    rows = []
    for path in paths:
        bead = resolve_brief_bead(path.stem, beads)
        rows.append(Membership(path, bead, beads.get(bead) if bead else None))
    return rows


def selected_pile_items(memberships: list[Membership], max_items: int) -> list[Path]:
    """The bounded batch, drawn from PILE MEMBERS only.

    Non-members are skipped rather than counted against `max_items`: a batch
    filled with stale cache is a cycle in which no real brief moved, which is
    the shape the live symptom took (three closed-bead files per 8h cycle).
    """
    return [row.path for row in memberships if row.is_member][:max_items]


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


def atomic_write(path: Path, text: str) -> None:
    """Write via a same-directory temp file and os.replace.

    A rewrite interrupted between truncate and write destroys the file it was
    updating. os.replace is atomic within a filesystem, so a reader sees either
    the whole old manifest or the whole new one. Mirrors effects.py::_atomic_write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


def manifest_row_stems(row: Mapping[str, Any]) -> set[str]:
    """Every pile filename stem the deposit convention could have produced for a row.

    Candidates are generated FORWARD from the row; the stem is never stripped to
    derive a slug. A strip would have to guess whether a trailing `-brief` is the
    deposit convention or part of the slug, and on the live city rows n=14/15
    carry slugs that genuinely end in `-brief` -- so the guess is wrong exactly
    where it matters. Generating forward keeps the row's slug untouched and makes
    every comparison an anchored equality.

    Two deposit shapes are attested: `NN-<slug>-brief.md` (decisions-to-briefs
    TS-3; rows n=13, 17, 19-23) and a bare `<slug>.md` (rows n=1-12, whose slugs
    carry their own `q28-NN` numbering).
    """
    slug = row.get("slug")
    if not isinstance(slug, str) or not slug:
        return set()
    stems = {slug, f"{slug}-brief"}
    n = row.get("n")
    if isinstance(n, int) and not isinstance(n, bool):
        for prefix in (str(n), f"{n:02d}"):
            stems.add(f"{prefix}-{slug}")
            stems.add(f"{prefix}-{slug}-brief")
    return stems


def mark_manifest_rejected(brief_root: Path, stem: str, reason: str, rejected_at: str) -> tuple[str, str]:
    """Splice the pile-manifest row for `stem`; leave every other line byte-identical.

    Returns `(outcome, detail)` rather than raising on a miss: an unmatched or
    ambiguous row is a fact about the manifest, and inventing a row would assert
    a pile membership nothing recorded.

    Only the matched row is re-emitted. Pile brief 22
    (`index-jsonl-two-serialization-producers`) is on file for why: a whole-file
    rewrite under a second serialization convention is what mangled 38 rows of
    `stack/.index.jsonl`. The row is re-emitted with a plain `json.dumps` --
    default separators, insertion key order, no sorting -- the convention all 22
    live rows round-trip through byte-identically (measured 2026-08-20). That is
    NOT the stack index's compact sorted convention; different file, different
    producer.
    """
    manifest = brief_root / ".pile" / PILE_MANIFEST_NAME
    if not manifest.is_file():
        return "aborted", f"no pile manifest at {manifest}"
    lock_path = manifest.parent / MANIFEST_LOCK_NAME
    with lock_path.open("a+", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        except OSError:
            pass
        try:
            text = manifest.read_text(encoding="utf-8")
            lines = text.splitlines()
            matches: list[tuple[int, dict[str, Any]]] = []
            for position, line in enumerate(lines):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and stem in manifest_row_stems(row):
                    matches.append((position, row))
            if not matches:
                return "aborted", f"no manifest row matches {stem}"
            if len(matches) > 1:
                return "aborted", f"ambiguous: {len(matches)} manifest rows match {stem}"
            position, row = matches[0]
            if row.get("status") == "rejected":
                return "unchanged", str(row.get("slug", ""))
            # `requires_taylor_adjudication` is left as it stands: it records what
            # catch-no-brainer decided at deposit time, and overwriting it would
            # destroy producer signal the plan's "repair is not rejection"
            # constraint exists to preserve.
            row.update({
                "status": "rejected",
                "rejection_reason": reason,
                "rejected_at": rejected_at,
            })
            lines[position] = json.dumps(row, ensure_ascii=False)
            atomic_write(manifest, "\n".join(lines) + ("\n" if text.endswith("\n") else ""))
            return "updated", str(row.get("slug", ""))
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
                    "failures": [],
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


def reject_staged(staging_dir: Path, staged: Path, brief_root: Path, slug: str, profile: str, reason: str,
                  failures: list[dict[str, Any]]) -> tuple[str, str]:
    rejected_dir = brief_root / ".pile" / ".rejected" / slug
    rejected_dir.mkdir(parents=True, exist_ok=False)
    rejected_brief = rejected_dir / "brief.md"
    rejection_path = rejected_dir / "rejection.json"
    rejected_at = utc_now()
    rejection = {
        "slug": slug,
        "gate_profile": profile,
        "reason": reason,
        "source_path": f".pile/{slug}.md",
        "rejected_at": rejected_at,
        # Every failing quality gate, so one repair pass can clear them all.
        # A stop-gate failure short-circuits and appears alone, flagged
        # repairable=false -- it must never be handed to an automated repair.
        "failures": failures,
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
    # Past this point the disposition has happened: the file is out of the pile
    # and the sidecar records why. The pile manifest is a cache
    # (assets/brief-pipeline/paths.toml), so its failure is recorded and
    # reported -- never allowed to unwind a completed disposition, and never
    # allowed to strand the claim in .staging.
    try:
        manifest, manifest_detail = mark_manifest_rejected(brief_root, slug, reason, rejected_at)
    except OSError as error:
        manifest, manifest_detail = "aborted", f"pile manifest update failed: {error}"
    cleanup_own_staging(staging_dir)
    return manifest, manifest_detail


def process_item(source: Path, brief_root: Path, gate_config: dict[str, Any], apply: bool) -> Outcome:
    slug = source.stem
    profile, reason, _metadata, failures = evaluate(source, gate_config)
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
        manifest, manifest_detail = reject_staged(
            staging_dir, staged, brief_root, slug, profile, reason, failures)
        return Outcome("reject", slug, reason, manifest, manifest_detail)
    except OSError as error:
        return Outcome("skipped", slug, f"disposition failed; staged for recovery: {error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief-root", type=Path, default=Path(".beads/briefs"))
    parser.add_argument("--gate-config", type=Path, default=Path("assets/brief-pipeline/gates.toml"))
    parser.add_argument("--max-items", type=int, default=3)
    parser.add_argument(
        "--bead-fixture", type=Path, default=None,
        help="JSONL of canonical beads, replacing the `bd` query. The fixture seam "
             "`mctl_core.beads.read_beads` already uses; required for a --brief-root "
             "with no .beads component.",
    )
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
    # P6.1 fail loud, same rule as the membership error below. A relative
    # `--brief-root` resolves against the CWD, and the ralph runner's CWD is a
    # per-bead agent work dir -- never a rig root, never a city root, never a
    # brief root. Resolved there the root simply does not exist, and every
    # count below then answers from an empty directory: the drain exited 0
    # reporting `remaining_pile: 0` while the real pile sat untouched. A drain
    # that never found its pile must not render as a drain that found it empty
    # (POLICY P6.2: a check that could not have failed must not render as a
    # check that passed). The script cannot repair this itself -- only the
    # caller knows whether `{{artifact_root}}` is rig-scoped or city-scoped --
    # so it refuses instead of guessing a root.
    if not brief_root.is_dir():
        report = {
            "brief_root_error": (
                f"--brief-root {args.brief_root} does not resolve to a directory "
                f"(resolved to {brief_root.resolve()} from cwd {Path.cwd()}); "
                "pass an ABSOLUTE brief root, or one resolved against the "
                "dispatching order's scope root -- the rig root for "
                "scope=\"rig\" orders, ${GC_CITY_PATH:-${GC_CITY:-$HOME/gt}} "
                "for scope=\"city\" orders. The working directory is neither."
            ),
            "apply": args.apply,
            "promoted": [], "rejected": [], "skipped": [], "recovered": [],
            "planned_promoted": [], "planned_rejected": [],
            "reasons": {}, "manifest_updated": [], "manifest_aborted": {},
            "not_pile_members": [], "membership_unresolved": [],
            # NOT 0. Unknown is unknown; a count from a root that was never
            # seen is the defect, not the answer.
            "remaining_pile": None,
        }
        if args.json:
            print(json.dumps(report, sort_keys=True))
        else:
            print(f"brief-shuffle-fast-drain: {report['brief_root_error']}", file=sys.stderr)
        return 2
    report: dict[str, Any] = {
        "apply": args.apply,
        "promoted": [], "rejected": [], "skipped": [], "recovered": [],
        "planned_promoted": [], "planned_rejected": [],
        "reasons": {},
        # Pile-manifest disposition, reported apart from promoted/rejected: the
        # manifest is a cache, so a miss here is a fact to surface, not a
        # different outcome for the brief.
        "manifest_updated": [], "manifest_aborted": {},
        # Canonical membership, reported so a skip is never silent.
        # `not_pile_members` = the file names a brief bead that is NOT open, so
        # per B2.3/B2.4 it is not in the pile at all. `membership_unresolved` =
        # the filename names no brief bead; unknown, drained, and visible.
        "not_pile_members": [], "membership_unresolved": [],
    }
    try:
        beads = read_brief_beads(rig_root_for(brief_root), args.bead_fixture)
    except MembershipError as error:
        # P6.1 fail loud. Degrading to the directory listing is the defect --
        # the gate would answer from redundant cache while the canonical store
        # it is supposed to obey was never read.
        report["membership_error"] = str(error)
        report["remaining_pile"] = None
        if args.json:
            print(json.dumps(report, sort_keys=True))
        else:
            print(f"brief-shuffle-fast-drain: canonical bead membership unreadable: {error}", file=sys.stderr)
        return 2
    if args.apply:
        report["recovered"] = recover_owned_staging(brief_root)
    memberships = classify_pile_items(pile, beads)
    for row in memberships:
        if row.bead is None:
            report["membership_unresolved"].append(row.path.stem)
        elif not row.is_member:
            report["not_pile_members"].append(
                {"slug": row.path.stem, "bead": row.bead, "status": row.status})
    items = selected_pile_items(memberships, args.max_items)
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
        if outcome.manifest == "updated":
            report["manifest_updated"].append(outcome.slug)
        elif outcome.manifest == "aborted":
            report["manifest_aborted"][outcome.slug] = outcome.manifest_detail
    # `remaining_pile` counts PILE MEMBERS, not files: it is the operator's
    # "how much is left to drain", and counting stale cache in it is what made
    # a pile of 86 files read as 86 pending briefs.
    report["remaining_pile"] = len(selected_pile_items(classify_pile_items(pile, beads), sys.maxsize))
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print(
            "brief-shuffle-fast-drain: "
            f"promoted={len(report['promoted'])} rejected={len(report['rejected'])} "
            f"skipped={len(report['skipped'])} remaining_pile={report['remaining_pile']} "
            f"not_pile_members={len(report['not_pile_members'])} "
            f"membership_unresolved={len(report['membership_unresolved'])} "
            f"manifest_updated={len(report['manifest_updated'])} "
            f"manifest_aborted={len(report['manifest_aborted'])}"
        )
        if not args.apply:
            print("dry-run planned: " + ", ".join(report["planned_promoted"] + report["planned_rejected"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
