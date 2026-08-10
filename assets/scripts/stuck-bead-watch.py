#!/usr/bin/env python3
# mathcity/assets/scripts/stuck-bead-watch.py
"""Detect routed beads that never made progress; escalate past a
priority-scaled grace window into the existing lost-bead-classification
pipeline. Pure-Python, stdlib only — no LLM/session cost per tick.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_GRACE_WINDOWS = {
    0: 5 * 60,
    1: 10 * 60,
    2: 20 * 60,
    3: 45 * 60,
    4: 45 * 60,
}
DEFAULT_MIN_AGE_SECONDS = 3 * 60

# CT1.8 (mathcity/subdomains/dev/POLICY-city.md): routed work is anything
# carrying ANY of these metadata keys, including formula/order-internal
# step beads -- not just gc.routed_to.
ROUTED_METADATA_KEYS = ("gc.routed_to", "gc.run_target", "gc.execution_routed_to")

# lost-bead-schema.toml's dispatch_sources enum has no entry for a raw
# gc.routed_to/run_target/execution_routed_to VALUE (pool/worker names like
# "mathcity.brief-operator" aren't in it) -- every bead this detector finds
# is, by construction, formula/order-routed work, so "formula" is the
# correct schema-valid classification. The actual worker/pool target is
# preserved separately under [stuck_bead_watch], outside the
# schema-validated root_cause block.
SUSPECTED_SOURCE = "formula"

_RELATE_ATTEMPTS = 3

# P6.1 (fail loud, never silent/frozen): every subprocess call must be
# time-bounded, or a hung `gc`/`bd` invocation freezes this 90s-cooldown
# order indefinitely -- turning the CT1.8 safety net into its own stuck
# patrol. Originally set to 15s off mail-reported Dolt health advisories
# (1-6s latency this session). REVISED 2026-07-28 (QUIMBY 33, gt-jzb8n
# live-verification pass): directly timed `gc dolt health` at 14.44s/
# 14.92s/15.99s across 3 consecutive real runs -- the 15s value was
# already at/over that observed latency, causing the preflight call
# itself to spuriously time out under real (not even degraded-per-the-
# health-advisory-threshold) conditions. 30s keeps comfortable headroom
# above the highest directly-observed run while staying well inside the
# order's own 60s `timeout` budget for the single preflight call (the
# other up-to-5 sequential calls a run can make -- 3x gc bd list + gc
# session list + bd create/dep relate -- are not all gated behind this
# same 30s ceiling simultaneously in the common case: preflight fails
# fast on to `fail()` before those run at all if Dolt is genuinely down).
SUBPROCESS_TIMEOUT_SECONDS = 30


def fail(message: str) -> None:
    print(f"stuck-bead-watch: {message}", file=sys.stderr)
    raise SystemExit(1)


def _run(cmd: list[str], **kwargs):
    """subprocess.run wrapper that fails loud (P6.1) on a hang instead of
    letting a TimeoutExpired propagate as an unhandled traceback."""
    try:
        return subprocess.run(cmd, timeout=SUBPROCESS_TIMEOUT_SECONDS, **kwargs)
    except subprocess.TimeoutExpired:
        fail(
            f"command timed out after {SUBPROCESS_TIMEOUT_SECONDS}s: {' '.join(cmd)}\n"
            "Check `gc dolt health` -- a hung gc/bd call usually means Dolt is "
            "degraded or unreachable."
        )


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def grace_window_seconds(priority: int, windows: dict[int, int]) -> int:
    return windows.get(priority, windows.get(4, 45 * 60))


def real_idle_age_seconds(bead: dict, now: datetime) -> float:
    """The bead's TRUE idle age = seconds since its last real activity.

    gsp-2bowrk: the priority-scaled grace window must measure how long the
    BEAD has actually been idle, NOT wall-clock since this detector first
    observed it. A bead already stranded for days, when first seen, has a
    large real idle age and must escalate immediately -- the grace must not
    be re-counted from first-observation (that double-counts the grace
    against wall-clock-since-detection and never escalates old strands).

    `updated_at` is the last time anything touched the bead (creation,
    routing, claim, note); for a stranded/never-progressed bead it is the
    moment progress stopped. Fall back to `created_at` when `updated_at`
    is absent (bd always emits both today; verified 2026-08-04)."""
    ts = bead.get("updated_at") or bead.get("created_at")
    if not ts:
        return 0.0
    return (now - _parse_ts(ts)).total_seconds()


def should_escalate(bead: dict, entry: dict | None, now: datetime, windows: dict[int, int]) -> bool:
    """Escalate once the bead's REAL idle age (or, as a secondary signal,
    the wall-clock time since this detector first observed it) crosses the
    bead's priority grace window. Taking the max of the two means an old
    strand escalates on the first detection pass (real idle age already
    over the window), while a genuinely fresh strand still waits out its
    full window measured against real idle time."""
    if entry is not None:
        seconds_since_first_seen = (now - _parse_ts(entry["first_seen_stuck"])).total_seconds()
    else:
        seconds_since_first_seen = 0.0
    age = max(real_idle_age_seconds(bead, now), seconds_since_first_seen)
    window = grace_window_seconds(bead.get("priority", 4), windows)
    return age >= window


def find_stuck_candidates(
    beads: list[dict],
    sessions: list[dict],
    now: datetime,
    min_age_seconds: int,
) -> list[dict]:
    live_session_names = {
        s.get("session_name") or s.get("name")
        for s in sessions
        if s.get("state") == "active"
    }
    candidates = []
    for bead in beads:
        if bead.get("status") not in ("open", "in_progress"):
            continue
        metadata = bead.get("metadata") or {}
        if not any(metadata.get(key) for key in ROUTED_METADATA_KEYS):
            continue
        created_at = bead.get("created_at")
        if not created_at:
            continue
        age_seconds = (now - _parse_ts(created_at)).total_seconds()
        if age_seconds < min_age_seconds:
            continue
        assignee = bead.get("assignee")
        if assignee and assignee in live_session_names:
            continue
        candidates.append(bead)
    return candidates


def read_cache_entry(cache_dir: Path, bead_id: str) -> dict | None:
    path = cache_dir / f"{bead_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def write_cache_entry(cache_dir: Path, bead_id: str, first_seen_stuck: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{bead_id}.json"
    path.write_text(json.dumps({"first_seen_stuck": first_seen_stuck}))


def clear_cache_entry(cache_dir: Path, bead_id: str) -> None:
    path = cache_dir / f"{bead_id}.json"
    if path.exists():
        path.unlink()


def _escalation_marker_path(cache_dir: Path, bead_id: str, fingerprint: str) -> Path:
    return cache_dir / "escalated" / f"{bead_id}__{fingerprint}.json"


def read_escalation_marker(cache_dir: Path, bead_id: str, fingerprint: str) -> dict | None:
    path = _escalation_marker_path(cache_dir, bead_id, fingerprint)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def write_escalation_marker(
    cache_dir: Path, bead_id: str, fingerprint: str, event_id: str, linked: bool
) -> None:
    path = _escalation_marker_path(cache_dir, bead_id, fingerprint)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"event_id": event_id, "linked": linked}))


def _default_bd_create_event(title: str, description: str) -> str:
    result = _run(
        ["bd", "create", "-t", "event", "--title", title, "--description", description, "--silent"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _default_bd_dep_relate(event_id: str, bead_id: str) -> None:
    # P1.19 — "append a new linked bead": bidirectional relates_to, not just a
    # prose bead_id reference inside the TOML body.
    _run(["bd", "dep", "relate", event_id, bead_id], capture_output=True, text=True, check=True)


def classify_and_escalate(
    bead: dict,
    cache_dir: Path,
    classification_root: Path,
    observed_at: str,
    bd_create_event=_default_bd_create_event,
    bd_dep_relate=_default_bd_dep_relate,
) -> str:
    bead_id = bead["id"]
    metadata = bead.get("metadata") or {}
    routed_key = next((k for k in ROUTED_METADATA_KEYS if metadata.get(k)), ROUTED_METADATA_KEYS[0])
    routed_target = metadata.get(routed_key, "unknown")

    assignee = bead.get("assignee")
    if assignee:
        lost_class = "immediate_strand"
        evidence = [f"assignee '{assignee}' has no matching active session at escalation time"]
        fingerprint = "orphaned_claim_dead_session"
        reason = "ASSIGNEE_DEAD"
    else:
        lost_class = "immediate_strand"
        evidence = ["post-sling verify-assignee never became non-empty within the grace window"]
        fingerprint = "empty_assignee_after_verified_sling"
        reason = "ROUTED_UNCLAIMED"

    # Idempotency (finding #3): a bead can re-enter the waiting room on a
    # later tick under the SAME underlying condition (same fingerprint).
    # Don't emit a second event for it -- reuse whatever this exact
    # (bead_id, fingerprint) pair already produced, whether or not the
    # link succeeded last time.
    marker = read_escalation_marker(cache_dir, bead_id, fingerprint)
    if marker and marker.get("linked"):
        clear_cache_entry(cache_dir, bead_id)
        return marker["event_id"]

    toml_body = f'''schema = "lost-bead-classification.v1"
bead_id = "{bead_id}"
observed_at = "{observed_at}"
observer = "stuck-bead-watch"

[finding]
lost_class = "{lost_class}"
evidence = {json.dumps(evidence)}

[disposition]
recommendation = "resling"
rationale = "The bead is still valid, but no live worker holds the dispatch after the priority-scaled grace window."
reversible = true

[root_cause]
class = "no_worker_claimed"
suspected_source = "{SUSPECTED_SOURCE}"
repair_candidate = true
fingerprint = "{fingerprint}"

[stuck_bead_watch]
reason = "{reason}"
routed_metadata_key = "{routed_key}"
routed_target = "{routed_target}"
'''

    classification_root.mkdir(parents=True, exist_ok=True)
    (classification_root / f"{bead_id}.toml").write_text(toml_body)

    if marker:
        # A prior run already created the event but couldn't link it
        # (bd dep relate failed after exhausting retries). Reuse that
        # event -- do NOT create a second one -- and just retry the link.
        event_id = marker["event_id"]
    else:
        event_id = bd_create_event(
            f"stuck-bead-watch: {bead_id} stuck past grace window",
            toml_body,
        )

    linked = False
    for _ in range(_RELATE_ATTEMPTS):
        try:
            bd_dep_relate(event_id, bead_id)
            linked = True
            break
        except Exception:
            continue

    write_escalation_marker(cache_dir, bead_id, fingerprint, event_id, linked)
    if linked:
        clear_cache_entry(cache_dir, bead_id)
    else:
        print(
            f"stuck-bead-watch: WARNING event {event_id} for {bead_id} was created "
            "but bd dep relate did not succeed after retries -- will retry the "
            "link (not create a duplicate event) on the next run",
            file=sys.stderr,
        )
    return event_id


def _gc_bd_list_routed() -> list[dict]:
    # --has-metadata-key is a server-side filter AND the only way to get
    # assignee/metadata included in the response — the default `gc bd list
    # --json` (no metadata filter) omits both fields entirely (verified
    # live 2026-07-28). Filtering server-side on each of the 3 CT1.8 routed
    # keys also avoids pulling every open bead city-wide on every 90s tick.
    # --has-metadata-key takes one key at a time, so query once per key and
    # merge by id (a bead carrying more than one routed key is deduped).
    merged: dict[str, dict] = {}
    for key in ROUTED_METADATA_KEYS:
        result = _run(
            ["gc", "bd", "list", "--all", "--has-metadata-key", key, "--json", "--limit=0"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            fail(f"gc bd list failed for --has-metadata-key {key}: {result.stderr.strip()}")
        for bead in json.loads(result.stdout):
            merged[bead["id"]] = bead
    return list(merged.values())


def _gc_session_list_active() -> list[dict]:
    result = _run(
        ["gc", "session", "list", "--state", "active", "--json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        fail(f"gc session list failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    return data.get("sessions", data if isinstance(data, list) else [])


def _preflight() -> None:
    result = _run(["gc", "dolt", "health"], capture_output=True, text=True)
    if result.returncode != 0:
        print(
            "I'm sorry, I can't do that — Dolt is unreachable.\n"
            "Run 'gc dolt start' and retry.\n"
            "(stuck-bead-watch needs Dolt to read bead/session state.)",
            file=sys.stderr,
        )
        raise SystemExit(1)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache-dir", type=Path, default=Path(".beads/stuck-bead-watch"))
    parser.add_argument("--classification-root", type=Path, default=Path(".beads/lost-bead-classifications"))
    parser.add_argument("--min-age-seconds", type=int, default=DEFAULT_MIN_AGE_SECONDS)
    parser.add_argument("--grace-p0", type=int, default=DEFAULT_GRACE_WINDOWS[0])
    parser.add_argument("--grace-p1", type=int, default=DEFAULT_GRACE_WINDOWS[1])
    parser.add_argument("--grace-p2", type=int, default=DEFAULT_GRACE_WINDOWS[2])
    parser.add_argument("--grace-p3", type=int, default=DEFAULT_GRACE_WINDOWS[3])
    parser.add_argument("--grace-p4", type=int, default=DEFAULT_GRACE_WINDOWS[4])
    args = parser.parse_args(argv)

    windows = {0: args.grace_p0, 1: args.grace_p1, 2: args.grace_p2, 3: args.grace_p3, 4: args.grace_p4}

    _preflight()
    now = datetime.now(timezone.utc)
    observed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    beads = _gc_bd_list_routed()
    sessions = _gc_session_list_active()
    candidates = find_stuck_candidates(beads, sessions, now, args.min_age_seconds)
    candidate_ids = {c["id"] for c in candidates}

    escalated = []
    entered_waiting_room = []

    for bead in candidates:
        entry = read_cache_entry(args.cache_dir, bead["id"])
        # gsp-2bowrk: gate on REAL idle age (updated_at), so a bead already
        # idle longer than its priority grace window escalates on this FIRST
        # detection pass -- not first-detection + a fresh grace window.
        if should_escalate(bead, entry, now, windows):
            event_id = classify_and_escalate(bead, args.cache_dir, args.classification_root, observed_at)
            escalated.append((bead["id"], event_id))
        elif entry is None:
            # Genuinely fresh strand under its window: record first-observation
            # and let it wait out the remainder of its window.
            write_cache_entry(args.cache_dir, bead["id"], observed_at)
            entered_waiting_room.append(bead["id"])

    if args.cache_dir.exists():
        for cache_file in args.cache_dir.glob("*.json"):
            bead_id = cache_file.stem
            if bead_id not in candidate_ids:
                clear_cache_entry(args.cache_dir, bead_id)

    print(f"stuck-bead-watch: {len(candidates)} candidates, "
          f"{len(entered_waiting_room)} entered waiting room, "
          f"{len(escalated)} escalated")
    for bead_id, event_id in escalated:
        print(f"  escalated {bead_id} -> event bead {event_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
