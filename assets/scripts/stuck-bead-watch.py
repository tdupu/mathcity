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
import time
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

# GATE #1 (decisions-track brief #99): the detector now scans EVERY rig store,
# not just HQ -- `gc bd list` with no --rig only ever resolves the HQ (gt-*)
# store, so non-HQ rigs were invisible to detection. A wide scan is (HQ + N
# rigs) x 3 routed keys of `gc bd list` calls (~54 for ~18 rigs), while the
# order's own budget is only 60s. These caps keep a wide scan safely inside
# that budget and prevent an escalation flood on the first successful wide
# scan (cf. gsp-2bowrk, which stranded ~1000 beads):
#   * scan-budget: wall-clock ceiling on the per-tick store sweep; once
#     exhausted the remaining rig stores are skipped this tick (PARTIAL scan,
#     WARN -- not a hard failure) and picked up on subsequent ticks.
#   * max-call-timeout: a tighter per-`gc bd list` timeout than the blanket
#     SUBPROCESS_TIMEOUT_SECONDS, so one hung rig can't consume the whole
#     budget -- a timed-out store is skipped (WARN), not fatal.
#   * max-classifications-per-tick: cap on NEW escalations emitted per run;
#     the backlog drains over subsequent ticks instead of flooding in one.
DEFAULT_SCAN_BUDGET_SECONDS = 45.0
DEFAULT_MAX_CALL_TIMEOUT_SECONDS = 8.0
DEFAULT_MAX_CLASSIFICATIONS_PER_TICK = 50

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


def _run(cmd: list[str], timeout: float = SUBPROCESS_TIMEOUT_SECONDS,
         fatal_timeout: bool = True, **kwargs):
    """subprocess.run wrapper that fails loud (P6.1) on a hang instead of
    letting a TimeoutExpired propagate as an unhandled traceback.

    `timeout` overrides the blanket SUBPROCESS_TIMEOUT_SECONDS for a single
    call (the per-store rig sweep uses a tighter ceiling; GATE #1b). When
    `fatal_timeout` is False the TimeoutExpired is re-raised instead of routed
    through fail(), so the caller can treat a single hung store as a skippable
    partial-scan event rather than a fatal one."""
    try:
        return subprocess.run(cmd, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired:
        if not fatal_timeout:
            raise
        fail(
            f"command timed out after {timeout}s: {' '.join(cmd)}\n"
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


def _gc_rig_list_names() -> list[str]:
    """Enumerate the NON-HQ rig store names from `gc rig list --json`.

    `gc rig list --json` emits a single JSON object whose `rigs` array lists
    every store; the HQ/city store is the entry with `"hq": true`. HQ is
    queried through the default (no --rig) store, so it is excluded here --
    each remaining entry's `name` field is what pins that rig store via
    `gc bd list --rig <name>`. Fails loud (constraint 5) if enumeration
    fails, since a broken rig list means the scan can't know which stores
    exist and would silently narrow back to HQ-only."""
    result = _run(["gc", "rig", "list", "--json"], capture_output=True, text=True)
    if result.returncode != 0:
        fail(f"gc rig list failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    rigs = data.get("rigs", []) if isinstance(data, dict) else []
    return [r["name"] for r in rigs if not r.get("hq")]


# The rotation cursor persists (across 90s ticks) the LABEL of the store to
# start the next sweep from, and the per-store last-scan state persists a
# queryable {store -> last-scan ISO} map so coverage is observable, not just a
# stderr WARN nobody reads (cf. the Reaper failing silently for 24h).
_CURSOR_FILENAME = ".store-scan-cursor.json"
_STORE_SCAN_STATE_FILENAME = "store-scan-state.json"


def _read_scan_cursor(cache_dir: Path | None) -> str | None:
    """Return the label of the store to resume the sweep from, or None."""
    if cache_dir is None:
        return None
    path = cache_dir / _CURSOR_FILENAME
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text()).get("next_store")
    except (json.JSONDecodeError, OSError):
        return None


def _write_scan_cursor(cache_dir: Path | None, next_store: str) -> None:
    if cache_dir is None:
        return
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / _CURSOR_FILENAME).write_text(json.dumps({"next_store": next_store}))


def _update_store_scan_state(
    classification_root: Path | None, scanned_labels: list[str], observed_at: str
) -> None:
    """Stamp each actually-scanned store's last-scan time into a queryable
    JSON map under classification_root, so 'which stores are we covering?'
    is answerable by reading a file (the source of truth), not by scraping
    stderr WARNs. Stores never appearing (or with stale timestamps) are the
    coverage gaps."""
    if classification_root is None or not scanned_labels:
        return
    path = classification_root / _STORE_SCAN_STATE_FILENAME
    state: dict[str, str] = {}
    if path.exists():
        try:
            state = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            state = {}
    for label in scanned_labels:
        state[label] = observed_at
    classification_root.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True))


def _gc_bd_list_routed(
    scan_budget_seconds: float = DEFAULT_SCAN_BUDGET_SECONDS,
    per_call_timeout: float = DEFAULT_MAX_CALL_TIMEOUT_SECONDS,
    rig_names_fn=None,
    clock=time.monotonic,
    cache_dir: Path | None = None,
    classification_root: Path | None = None,
    observed_at: str | None = None,
) -> list[dict]:
    # THE FIX (decisions-track brief #99): `gc bd list` with no --rig only
    # ever resolves the HQ (gt-*) store, so every non-HQ rig store was
    # invisible to detection. A single city-scoped tick must scan ALL stores,
    # and `gc bd list --rig <name>` pins ONE store at a time (there is no
    # multi-rig single call), so loop store-by-store: HQ (default, no --rig)
    # plus each rig name from `gc rig list --json`.
    #
    # --has-metadata-key is a server-side filter AND the only way to get
    # assignee/metadata included in the response — the default `gc bd list
    # --json` (no metadata filter) omits both fields entirely (verified
    # live 2026-07-28). It takes one key at a time, so query once per store
    # per key and merge by id (a bead carrying more than one routed key, or
    # surfaced by more than one store, is deduped).
    #
    # COVERAGE GUARANTEE (GATE, reviewer change 1): the sweep does NOT restart
    # from a fixed store each tick -- that would leave the TAIL of the order
    # permanently unscanned whenever the budget is tight (re-creating bug #99
    # one layer up, precisely for the big/slow stores that sort last). Instead
    # a ROTATION CURSOR persists in cache_dir: each tick resumes from the store
    # after the last one attempted and wraps around. The first store of every
    # tick is always attempted (even a store slower than the whole budget), so
    # the cursor advances by >= 1 every tick and a hung store is attempted-then-
    # skipped rather than blocking rotation. Therefore, with S stores, EVERY
    # store is attempted at least once within at most S ticks, regardless of
    # per-store cost -- bounded, provably-complete coverage instead of a
    # permanent blind spot. Per-store last-scan timestamps are recorded to
    # classification_root so that guarantee is queryable (reviewer change 2).
    #
    # The between-stores budget check RESERVES one store's worst-case cost
    # (3 keys x call_timeout) so the loop never STARTS a store that could push
    # total scan time past scan_budget_seconds. Without that reserve a store
    # starting at ~44.9s could run ~24s more and blow the order's 60s HARD
    # timeout -- which kills the process mid-store BEFORE the end-of-loop
    # cursor write, so the cursor never advances and the tail is never reached
    # (the exact blind spot this cursor prevents, re-opened via a hard kill).
    # Reserving headroom guarantees a graceful partial-scan-with-cursor-advance
    # ALWAYS happens before any order-timeout pre-emption.
    if rig_names_fn is None:
        rig_names_fn = _gc_rig_list_names
    if observed_at is None:
        observed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rig_names = rig_names_fn()

    # (rig, label): rig=None is the HQ/default store (no --rig flag).
    stores: list[tuple[str | None, str]] = [(None, "HQ")]
    stores.extend((name, name) for name in rig_names)
    n_stores = len(stores)

    # Resume the rotation from the persisted cursor (by label, so the cursor is
    # robust to rigs being added/removed between ticks); default to the front.
    labels = [label for _, label in stores]
    resume_label = _read_scan_cursor(cache_dir)
    start_index = labels.index(resume_label) if resume_label in labels else 0

    # GATE #1b: cap each per-store call tighter than the blanket 30s so one
    # hung rig can't consume the whole scan budget.
    call_timeout = min(per_call_timeout, SUBPROCESS_TIMEOUT_SECONDS)
    # GATE #1a headroom: one store's worst case is all 3 keys hitting the
    # per-call timeout. The budget check RESERVES this so we never START a
    # store that could push total scan time past the budget (and thus past
    # the order's hard 60s timeout, which would kill the process before the
    # cursor write).
    max_store_cost = len(ROUTED_METADATA_KEYS) * call_timeout

    merged: dict[str, dict] = {}
    scanned_labels: list[str] = []
    timings: list[str] = []
    attempted = 0
    start = clock()
    for i in range(n_stores):
        rig, label = stores[(start_index + i) % n_stores]
        # GATE #1a: enforce the per-scan wall-clock budget BETWEEN stores. The
        # first store of the tick (i == 0) always runs -- this is what makes
        # the cursor advance every tick and gives the coverage guarantee above.
        # For every later store, stop BEFORE starting it if finishing its
        # worst case would exceed the budget, so total scan time stays <=
        # scan_budget_seconds (safely under the 60s order timeout) and a
        # graceful partial scan + cursor advance always beats the hard kill.
        if i > 0 and (clock() - start) + max_store_cost > scan_budget_seconds:
            skipped = n_stores - i
            print(
                f"stuck-bead-watch: WARNING scan budget ({scan_budget_seconds:.0f}s) "
                f"exhausted after {i} of {n_stores} stores -- skipped "
                f"{skipped} store(s) this tick (partial scan; the rotation "
                "cursor resumes there next tick)",
                file=sys.stderr,
            )
            break
        attempted += 1
        store_t0 = time.monotonic()
        store_timed_out = False
        for key in ROUTED_METADATA_KEYS:
            cmd = ["gc", "bd", "list"]
            if rig is not None:
                cmd += ["--rig", rig]
            cmd += ["--all", "--has-metadata-key", key, "--json", "--limit=0"]
            try:
                result = _run(
                    cmd, timeout=call_timeout, fatal_timeout=False,
                    capture_output=True, text=True,
                )
            except subprocess.TimeoutExpired:
                # GATE #1b: a single hung store is skipped (partial scan, WARN),
                # NOT fatal -- the tighter timeout bounds how much of the budget
                # it can burn, and the rest of the fleet still gets scanned. The
                # cursor still advances past it, so it can't block rotation.
                print(
                    f"stuck-bead-watch: WARNING store {label} timed out after "
                    f"{call_timeout:.0f}s -- skipping this store this tick "
                    "(partial scan; covered on a subsequent rotation)",
                    file=sys.stderr,
                )
                store_timed_out = True
                break
            if result.returncode != 0:
                fail(f"gc bd list failed for store {label} "
                     f"--has-metadata-key {key}: {result.stderr.strip()}")
            for bead in json.loads(result.stdout):
                merged[bead["id"]] = bead
        timings.append(f"{label}={time.monotonic() - store_t0:.2f}s")
        if not store_timed_out:
            scanned_labels.append(label)

    # Advance and persist the cursor past every store attempted this tick, so
    # the next tick resumes at the first store we did NOT reach.
    if n_stores:
        _write_scan_cursor(cache_dir, stores[(start_index + attempted) % n_stores][1])
    _update_store_scan_state(classification_root, scanned_labels, observed_at)

    # Cheap instrumentation (reviewer refinement): per-store call time is
    # non-uniform (big stores cost far more), so log it once per run to make
    # the next budget tuning data-driven rather than guesswork.
    if timings:
        print("stuck-bead-watch: per-store scan times: " + " ".join(timings),
              file=sys.stderr)
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
    # GATE #1 (decisions-track brief #99): bound the now-fleet-wide scan.
    parser.add_argument("--scan-budget-seconds", type=float, default=DEFAULT_SCAN_BUDGET_SECONDS,
                        help="wall-clock ceiling on the per-tick rig-store sweep; "
                             "remaining stores are skipped (partial scan) once exceeded")
    parser.add_argument("--max-call-timeout-seconds", type=float, default=DEFAULT_MAX_CALL_TIMEOUT_SECONDS,
                        help="tighter per-`gc bd list` timeout for the store loop so one "
                             "hung rig can't consume the whole scan budget")
    parser.add_argument("--max-classifications-per-tick", type=int, default=DEFAULT_MAX_CLASSIFICATIONS_PER_TICK,
                        help="cap on NEW escalations emitted per run; the backlog drains "
                             "over subsequent ticks instead of flooding in one")
    args = parser.parse_args(argv)

    windows = {0: args.grace_p0, 1: args.grace_p1, 2: args.grace_p2, 3: args.grace_p3, 4: args.grace_p4}

    _preflight()
    now = datetime.now(timezone.utc)
    observed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    beads = _gc_bd_list_routed(
        scan_budget_seconds=args.scan_budget_seconds,
        per_call_timeout=args.max_call_timeout_seconds,
        cache_dir=args.cache_dir,
        classification_root=args.classification_root,
        observed_at=observed_at,
    )
    sessions = _gc_session_list_active()
    candidates = find_stuck_candidates(beads, sessions, now, args.min_age_seconds)
    candidate_ids = {c["id"] for c in candidates}

    escalated = []
    entered_waiting_room = []

    cap = args.max_classifications_per_tick
    cap_hit = False
    for bead in candidates:
        entry = read_cache_entry(args.cache_dir, bead["id"])
        # gsp-2bowrk: gate on REAL idle age (updated_at), so a bead already
        # idle longer than its priority grace window escalates on this FIRST
        # detection pass -- not first-detection + a fresh grace window.
        if should_escalate(bead, entry, now, windows):
            # GATE #1c: cap escalations per tick so the first successful
            # fleet-wide scan can't flood the pipeline with ~1000 events at
            # once (cf. gsp-2bowrk). Remaining stuck beads stay candidates and
            # drain over subsequent ticks.
            if len(escalated) >= cap:
                cap_hit = True
                break
            event_id = classify_and_escalate(bead, args.cache_dir, args.classification_root, observed_at)
            escalated.append((bead["id"], event_id))
        elif entry is None:
            # Genuinely fresh strand under its window: record first-observation
            # and let it wait out the remainder of its window.
            write_cache_entry(args.cache_dir, bead["id"], observed_at)
            entered_waiting_room.append(bead["id"])

    if cap_hit:
        print(
            f"stuck-bead-watch: WARNING classification cap ({cap}) reached -- "
            "stopped escalating this tick; remaining stuck beads drain over "
            "subsequent ticks",
            file=sys.stderr,
        )

    if args.cache_dir.exists():
        for cache_file in args.cache_dir.glob("*.json"):
            # The rotation cursor lives in cache_dir but is NOT a per-bead
            # waiting-room entry -- it must survive the stale-entry sweep.
            if cache_file.name == _CURSOR_FILENAME:
                continue
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
