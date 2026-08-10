#!/usr/bin/env python3
# mathcity/assets/scripts/tail-end-detector.py
"""Catch READY-BUT-NEVER-DISPATCHED work beads (the "tail end").

stuck-bead-watch.py catches beads that WERE dispatched (carry routing
metadata) then froze. This detector catches the complementary lost class named
on gsp-2bowrk's CONSERVATION INVARIANT: beads that are ready+unblocked, were
never slung (no routing metadata), and have sat idle past the >3d age trigger.

It reuses the existing lost-bead pipeline (Fork 2): it emits the SAME
`lost-bead-classification.v1` records that `lost-bead-classification-rollup`
consumes, under distinct fingerprints, so the rollup turns them into
resling/close decision briefs. No parallel pipeline.

Design (docs/superpowers/specs/2026-08-04-tail-end-detector-design.md):
- Fork 1 real idle age = max(created_at, updated_at, last_activity); a
  genuinely-3-day-idle bead registers on the FIRST scan (no waiting room).
- Fork 3 classification split (real supersession detector, gsp-beo9sy): a
  never-dispatched idle bead is superseded ONLY when a real signal fires --
  (1) its parent epic/convoy is closed, (2) it carries a non-blocking
  relational edge (related/tracks/...) to a closed bead, or (3) its title/
  description is a near-duplicate of a closed bead or a strictly-newer open
  one. No signal -> resling ("genuinely wanted, just old"). Age alone never
  supersedes -- a wrong auto-close silently discards work, so the default is
  the reversible resling. Both buckets are batch-capped, oldest-first, so a
  large tail drains at a fleet-absorbing cadence and never dumps at once.
- Fork 4 fail-loud (P6.1): subprocess timeouts -> nonzero exit; the
  actionable-tail count is a heartbeat -- if it GROWS or the run errors, emit
  a visible event bead; the count is printed every run.

Pure-Python, stdlib only -- no LLM/session cost per tick.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---- configuration / defaults -------------------------------------------

DEFAULT_MIN_IDLE_DAYS = 3
DEFAULT_RESLING_BATCH_CAP = 10
DEFAULT_SUPERSEDE_BATCH_CAP = 25

# ---- supersession-detector tuning (gsp-beo9sy) --------------------------
# Deliberately conservative: a wrong auto-close silently discards real work,
# a wrong resling is cheap to undo. So the duplicate signal needs a HIGH
# similarity floor and a minimum count of meaningful tokens -- generic
# repeated titles ("Finalize build-basic") must never trip an auto-close.
DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_MIN_SIMILARITY_TOKENS = 4

# Non-blocking relational edges. A closed target on one of these means "the
# work this bead points at is already done" -> subsumed. `blocks` and
# `parent-child` are deliberately excluded: a satisfied *blocker* merely
# unblocks a bead (it does not finish the bead's own work), and parent-child
# is handled by the dedicated parent-epic-closed signal.
SUBSUMING_REL_TYPES = ("related", "relates-to", "tracks", "discovered-from")

# Tokens with no discriminating power for duplicate detection: English
# stopwords + gascity workflow filler. Stripped before similarity scoring so
# only content words count toward the min-token guard and the Jaccard score.
STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "at", "by",
    "with", "from", "into", "as", "is", "are", "be", "this", "that", "it",
    "its", "via", "per", "then", "now", "new", "run", "do", "make", "add",
    "update", "fix", "finalize", "produce", "generate", "build", "basic",
    "task", "bead", "work", "step", "review", "until", "approved",
})

DEFAULT_RIGS = (
    "gascity-packs", "hecke", "agent_skills", "lmfdb",
    "jacobi", "homog", "magma_clifford_algebras",
)

# Never-dispatched == carries none of these routing keys. Same set
# stuck-bead-watch keys off; excluding them makes the two detectors' target
# sets disjoint (dedup) and encodes "never dispatched".
ROUTED_METADATA_KEYS = ("gc.routed_to", "gc.run_target", "gc.execution_routed_to")

# A "work bead" is an independently-slingable issue, not a molecule/convoy
# internal step or a meta bead (spec/convoy/epic/event/decision/session).
WORK_TYPES = ("task", "bug", "feature")

SCAFFOLD_WORDS = ("patrol", "deacon", "witness", "refinery", "polecat")
GATE_WORDS = ("human-gated", "gh-auth")

OBSERVER = "tail-end-detector"

SUBPROCESS_TIMEOUT_SECONDS = 30  # matches stuck-bead-watch (Dolt latency headroom)

# Distinct fingerprints so the rollup groups tail records apart from
# stuck-bead-watch's, and apart from each other by bucket.
FINGERPRINT_SUPERSEDED = "ready_idle_tail_superseded"
FINGERPRINT_RESLING = "ready_idle_tail_resling"
FINGERPRINT_GROWING = "ready_idle_tail_growing"

# Per-bucket lost-bead-classification.v1 field mapping. suspected_source is
# "unknown" because a never-dispatched bead has no dispatch provenance;
# repair_candidate is False for both so these stay OUT of the upstream
# (fix-the-producing-formula) rollup -- an un-slung bead is not a formula
# defect -- and only feed the downstream resling/close rollup.
BUCKETS = {
    "superseded": {
        "lost_class": "stale_or_duplicate",
        "recommendation": "close_moot",
        "root_class": "duplicate_or_superseded_source",
        "repair_candidate": False,
        "fingerprint": FINGERPRINT_SUPERSEDED,
        "rationale": (
            "Ready+unblocked but never dispatched, and a supersession signal "
            "fired (parent epic closed / relational edge to a closed bead / "
            "near-duplicate of a closed-or-newer bead); the work is almost "
            "certainly already done or obsolete -- recommend close as moot "
            "(gated through a close brief, not auto-closed)."
        ),
    },
    "resling": {
        "lost_class": "immediate_strand",
        "recommendation": "resling",
        "root_class": "no_worker_claimed",
        "repair_candidate": False,
        "fingerprint": FINGERPRINT_RESLING,
        "rationale": (
            "Ready+unblocked and never dispatched, with no supersession "
            "signal -- valid work that was simply never slung; recommend "
            "resling at a fleet-absorbing cadence."
        ),
    },
}


def fail(message: str) -> None:
    print(f"tail-end-detector: {message}", file=sys.stderr)
    raise SystemExit(1)


def _run(cmd: list[str], **kwargs):
    """subprocess.run wrapper that fails loud (P6.1) on a hang instead of
    letting TimeoutExpired propagate as an unhandled traceback."""
    try:
        return subprocess.run(cmd, timeout=SUBPROCESS_TIMEOUT_SECONDS, **kwargs)
    except subprocess.TimeoutExpired:
        fail(
            f"command timed out after {SUBPROCESS_TIMEOUT_SECONDS}s: {' '.join(cmd)}\n"
            "Check `gc dolt health` -- a hung gc/bd call usually means Dolt is "
            "degraded or unreachable."
        )


# ---- pure core (unit-tested) --------------------------------------------

def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def real_idle_seconds(bead: dict, now: datetime) -> float:
    """Fork 1: idle age keyed off the newest of created/updated/last_activity,
    never a first-observation timestamp."""
    stamps = [
        bead.get("created_at"), bead.get("updated_at"), bead.get("last_activity"),
    ]
    parsed = [parse_ts(s) for s in stamps if s]
    if not parsed:
        return 0.0
    return (now - max(parsed)).total_seconds()


def is_scaffolding(bead: dict, rig_names=DEFAULT_RIGS) -> bool:
    title = (bead.get("title") or "").strip()
    low = title.lower()
    if any(word in low for word in SCAFFOLD_WORDS):
        return True
    if re.search(r"-rig-", bead.get("id", "")):
        return True
    if low in {r.lower() for r in rig_names}:  # bare rig-name title
        return True
    return False


def is_gated(bead: dict) -> bool:
    low = (bead.get("title") or "").lower()
    return any(word in low for word in GATE_WORDS)


def is_work_type(bead: dict, work_types=WORK_TYPES) -> bool:
    return bead.get("issue_type") in work_types


def find_actionable_tail(
    open_beads: list[dict],
    ready_ids: set[str],
    routed_ids: set[str],
    now: datetime,
    min_idle_seconds: float,
    work_types=WORK_TYPES,
    rig_names=DEFAULT_RIGS,
) -> list[dict]:
    """Never-dispatched actionable-idle work beads, sorted oldest-first."""
    out = []
    for bead in open_beads:
        if bead.get("status") not in ("open", None):
            continue
        if bead["id"] not in ready_ids:
            continue                      # blocked -> correctly waiting, not us
        if bead["id"] in routed_ids:
            continue                      # dispatched -> stuck-bead-watch's domain
        if not is_work_type(bead, work_types):
            continue
        if is_scaffolding(bead, rig_names):
            continue
        if is_gated(bead):
            continue
        if real_idle_seconds(bead, now) < min_idle_seconds:
            continue
        out.append(bead)
    out.sort(key=lambda b: real_idle_seconds(b, now), reverse=True)
    return out


# ---- supersession detector (gsp-beo9sy) ---------------------------------

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize_tokens(text: str) -> frozenset[str]:
    """Content-token set for similarity: lowercase, split on non-alnum, drop
    stopwords / short filler tokens. Order- and duplicate-insensitive."""
    tokens = _TOKEN_RE.findall((text or "").lower())
    return frozenset(t for t in tokens if len(t) > 1 and t not in STOPWORDS)


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def parent_of(bead: dict) -> str | None:
    """Parent id from the scalar `parent` field, or a parent-child dep edge
    (issue_id == this bead -> depends_on_id is the parent)."""
    parent = bead.get("parent")
    if parent:
        return parent
    for edge in bead.get("dependencies") or []:
        if edge.get("type") == "parent-child" and edge.get("issue_id") == bead.get("id"):
            return edge.get("depends_on_id")
    return None


def subsuming_refs(bead: dict) -> list[str]:
    """Ids this bead points at via a non-blocking relational edge (a closed
    such target means the pointed-at work is done -> this bead is subsumed)."""
    out = []
    for edge in bead.get("dependencies") or []:
        if edge.get("type") in SUBSUMING_REL_TYPES and edge.get("issue_id") == bead.get("id"):
            out.append(edge.get("depends_on_id"))
    return out


class DedupIndex:
    """Corpus lookup for the three supersession signals. Built once per run
    from the full open+closed bead set across all scanned rigs.

    - closed_ids: every closed bead id (parent-closed / subsumed-ref checks).
    - entries: (id, tokens, is_closed, created_at) for every bead with enough
      content tokens to be a safe duplicate target.
    - inverted: token -> [entry index] so a candidate only scores against
      beads that share at least one content token (keeps it near-linear on a
      1000+ bead tail instead of O(N*M) full pairwise)."""

    def __init__(self, beads: list[dict], min_tokens: int):
        self.closed_ids: set[str] = set()
        self.entries: list[tuple[str, frozenset[str], bool, datetime | None]] = []
        self.inverted: dict[str, list[int]] = {}
        for bead in beads:
            bid = bead.get("id")
            if not bid:
                continue
            is_closed = bead.get("status") == "closed"
            if is_closed:
                self.closed_ids.add(bid)
            tokens = normalize_tokens(
                f"{bead.get('title') or ''} {bead.get('description') or ''}"
            )
            if len(tokens) < min_tokens:
                continue  # too generic to be a safe duplicate target
            created = None
            raw = bead.get("created_at")
            if raw:
                try:
                    created = parse_ts(raw)
                except ValueError:
                    created = None
            idx = len(self.entries)
            self.entries.append((bid, tokens, is_closed, created))
            for tok in tokens:
                self.inverted.setdefault(tok, []).append(idx)


def build_dedup_index(beads: list[dict],
                      min_tokens: int = DEFAULT_MIN_SIMILARITY_TOKENS) -> DedupIndex:
    return DedupIndex(beads, min_tokens)


def find_duplicate(
    bead: dict,
    index: DedupIndex,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    min_tokens: int = DEFAULT_MIN_SIMILARITY_TOKENS,
) -> tuple[str, float] | None:
    """Best superseding duplicate of `bead`: a CLOSED bead, or a strictly
    NEWER open bead, whose content-token Jaccard >= threshold. Returns
    (matched_id, score) or None. Guarded by min_tokens so short/generic
    titles never match."""
    tokens = normalize_tokens(f"{bead.get('title') or ''} {bead.get('description') or ''}")
    if len(tokens) < min_tokens:
        return None
    bid = bead.get("id")
    created = None
    if bead.get("created_at"):
        try:
            created = parse_ts(bead["created_at"])
        except ValueError:
            created = None
    best: tuple[str, float] | None = None
    seen: set[int] = set()
    for tok in tokens:
        for idx in index.inverted.get(tok, ()):
            if idx in seen:
                continue
            seen.add(idx)
            other_id, other_tokens, is_closed, other_created = index.entries[idx]
            if other_id == bid:
                continue
            # only a closed bead, or a strictly-newer open bead, can supersede
            if not is_closed:
                if created is None or other_created is None or other_created <= created:
                    continue
            score = jaccard(tokens, other_tokens)
            if score >= threshold and (best is None or score > best[1]):
                best = (other_id, score)
    return best


def classify_bead(bead: dict, index: DedupIndex,
                  threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
                  min_tokens: int = DEFAULT_MIN_SIMILARITY_TOKENS) -> tuple[str, dict]:
    """Return (bucket, evidence). bucket in {superseded, resling}. Signals are
    checked strongest-first; the first to fire wins. No signal -> resling.

    Signal 1  parent_epic_closed          -- parent epic/convoy is closed.
    Signal 2  subsumed_by_closed_ref      -- relational edge to a closed bead.
    Signal 3  duplicate_of_closed_or_newer-- near-duplicate title/description.
    """
    parent = parent_of(bead)
    if parent and parent in index.closed_ids:
        return "superseded", {"signal": "parent_epic_closed", "matched_bead": parent}

    for ref in subsuming_refs(bead):
        if ref in index.closed_ids:
            return "superseded", {"signal": "subsumed_by_closed_ref", "matched_bead": ref}

    dup = find_duplicate(bead, index, threshold, min_tokens)
    if dup is not None:
        return "superseded", {
            "signal": "duplicate_of_closed_or_newer",
            "matched_bead": dup[0],
            "similarity": round(dup[1], 3),
        }

    return "resling", {"signal": None}


def select_batches(
    candidates: list[dict],
    now: datetime,
    index: DedupIndex,
    resling_cap: int,
    supersede_cap: int,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    min_tokens: int = DEFAULT_MIN_SIMILARITY_TOKENS,
) -> tuple[list[dict], list[dict]]:
    """Split into (superseded, resling), each oldest-first and capped so a
    large tail drains steadily instead of being dumped (Fork 3). Superseded
    beads carry their signal evidence under `_supersession` so the downstream
    close brief is auditable."""
    superseded, resling = [], []
    for bead in sorted(candidates, key=lambda b: real_idle_seconds(b, now), reverse=True):
        bucket, evidence = classify_bead(bead, index, threshold, min_tokens)
        if bucket == "superseded":
            bead["_supersession"] = evidence
            superseded.append(bead)
        else:
            resling.append(bead)
    return superseded[:supersede_cap], resling[:resling_cap]


def render_record(bead: dict, kind: str, now: datetime, observed_at: str) -> str:
    """Emit a lost-bead-classification.v1 TOML record for the given bucket."""
    spec = BUCKETS[kind]
    idle_days = real_idle_seconds(bead, now) / 86400
    evidence = [
        "ready+unblocked in `bd ready` but carries no routing metadata "
        f"({'/'.join(ROUTED_METADATA_KEYS)}) -- never dispatched",
        f"idle {idle_days:.1f} days (real max of created/updated/last_activity), "
        "past the >3d tail trigger",
    ]
    signal = bead.get("_supersession") if kind == "superseded" else None
    if signal and signal.get("signal"):
        matched = signal.get("matched_bead", "?")
        detail = {
            "parent_epic_closed":
                f"supersession signal: parent epic/convoy {matched} is closed",
            "subsumed_by_closed_ref":
                f"supersession signal: relational edge to closed bead {matched} "
                "(pointed-at work is done)",
            "duplicate_of_closed_or_newer":
                f"supersession signal: near-duplicate (jaccard "
                f"{signal.get('similarity', '?')}) of closed-or-newer bead {matched}",
        }.get(signal["signal"], f"supersession signal: {signal['signal']} ({matched})")
        evidence.append(detail)
    title = (bead.get("title") or "").replace("\\", "/").replace('"', "'")
    title = re.sub(r"\s+", " ", title).strip()  # collapse newlines/tabs -> TOML-safe
    tail_section = (
        "[tail_end_detector]\n"
        f'bucket = "{kind}"\n'
        f'title = "{title}"\n'
        f'idle_days = {idle_days:.1f}\n'
    )
    if signal and signal.get("signal"):
        tail_section += f'supersession_signal = "{signal["signal"]}"\n'
        tail_section += f'matched_bead = "{signal.get("matched_bead", "")}"\n'
        if signal.get("similarity") is not None:
            tail_section += f'similarity = {signal["similarity"]}\n'
    return (
        'schema = "lost-bead-classification.v1"\n'
        f'bead_id = "{bead["id"]}"\n'
        f'observed_at = "{observed_at}"\n'
        f'observer = "{OBSERVER}"\n'
        "\n"
        "[finding]\n"
        f'lost_class = "{spec["lost_class"]}"\n'
        f"evidence = {json.dumps(evidence)}\n"
        "\n"
        "[disposition]\n"
        f'recommendation = "{spec["recommendation"]}"\n'
        f'rationale = "{spec["rationale"]}"\n'
        "reversible = true\n"
        "\n"
        "[root_cause]\n"
        f'class = "{spec["root_class"]}"\n'
        'suspected_source = "unknown"\n'
        f"repair_candidate = {str(spec['repair_candidate']).lower()}\n"
        f'fingerprint = "{spec["fingerprint"]}"\n'
        "\n"
        + tail_section
    )


# ---- edge I/O ------------------------------------------------------------

def _bd_json(rig_dir: Path, *args: str) -> list[dict]:
    result = _run(
        ["bd", *args, "--json", "--readonly", "--limit", "0"],
        cwd=str(rig_dir), capture_output=True, text=True,
    )
    if result.returncode != 0:
        fail(f"bd {' '.join(args)} failed in {rig_dir}: {result.stderr.strip()}")
    data = json.loads(result.stdout or "[]")
    return data if isinstance(data, list) else data.get("issues", [])


def gather_rig(base_dir: Path, rig: str) -> tuple[list[dict], set[str], list[dict]]:
    """Return (open_beads, ready_ids, closed_beads) for a rig. Closed beads
    feed the supersession index (parent-closed / subsumed-ref / duplicate
    signals) -- they are never candidates themselves."""
    rig_dir = base_dir / rig
    opens = _bd_json(rig_dir, "list", "--status", "open")
    ready = {b["id"] for b in _bd_json(rig_dir, "ready")}
    closed = _bd_json(rig_dir, "list", "--status", "closed")
    return opens, ready, closed


def gather_routed_ids(base_dir: Path) -> set[str]:
    """City-wide routed id set (all rigs) via `gc bd list --has-metadata-key`.
    Metadata is omitted from plain `bd list --json`, so this is the only way to
    identify dispatched beads server-side."""
    routed: set[str] = set()
    cwd = str(base_dir / DEFAULT_RIGS[0])
    for key in ROUTED_METADATA_KEYS:
        result = _run(
            ["gc", "bd", "list", "--all", "--has-metadata-key", key,
             "--json", "--limit=0"],
            cwd=cwd, capture_output=True, text=True,
        )
        if result.returncode != 0:
            fail(f"gc bd list --has-metadata-key {key} failed: {result.stderr.strip()}")
        for bead in json.loads(result.stdout or "[]"):
            routed.add(bead["id"])
    return routed


def _preflight() -> None:
    result = _run(["gc", "dolt", "health"], capture_output=True, text=True)
    if result.returncode != 0:
        print(
            "I'm sorry, I can't do that - Dolt is unreachable.\n"
            "Run 'gc dolt start' and retry.\n"
            "(tail-end-detector needs Dolt to read bead/ready state.)",
            file=sys.stderr,
        )
        raise SystemExit(1)


def _default_bd_create_event(title: str, description: str) -> str:
    result = _run(
        ["bd", "create", "-t", "event", "--title", title,
         "--description", description, "--silent"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _default_bd_dep_relate(event_id: str, bead_id: str) -> None:
    _run(["bd", "dep", "relate", event_id, bead_id],
         capture_output=True, text=True, check=True)


def read_heartbeat(cache_dir: Path) -> int | None:
    path = cache_dir / "tail-heartbeat.json"
    if not path.exists():
        return None
    try:
        return int(json.loads(path.read_text()).get("actionable_count"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def write_heartbeat(cache_dir: Path, count: int, observed_at: str) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "tail-heartbeat.json").write_text(
        json.dumps({"actionable_count": count, "observed_at": observed_at})
    )


def emit_growth_heartbeat(
    prev: int, current: int, observed_at: str,
    bd_create_event=_default_bd_create_event,
) -> str:
    """Fork 4 / P6.1: the tail is a heartbeat -- if it grows, escalate loudly."""
    body = (
        f'schema = "tail-end-heartbeat.v1"\n'
        f'observer = "{OBSERVER}"\n'
        f'fingerprint = "{FINGERPRINT_GROWING}"\n'
        f'observed_at = "{observed_at}"\n'
        f"previous_actionable = {prev}\n"
        f"current_actionable = {current}\n"
        f"delta = {current - prev}\n"
    )
    return bd_create_event(
        f"tail-end-detector: actionable tail GREW {prev} -> {current}", body,
    )


def _write_records(classification_root: Path, records: list[tuple[str, str]]) -> None:
    classification_root.mkdir(parents=True, exist_ok=True)
    for bead_id, toml_text in records:
        # `.tail.toml` still matches the rollup's `*.toml` glob but never
        # clobbers stuck-bead-watch's `{bead_id}.toml` records (P4.2).
        (classification_root / f"{bead_id}.tail.toml").write_text(toml_text)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", type=Path, default=Path("."),
                        help="City root containing the rig checkouts.")
    parser.add_argument("--rigs", nargs="+", default=list(DEFAULT_RIGS))
    parser.add_argument("--cache-dir", type=Path,
                        default=Path(".beads/tail-end-detector"))
    parser.add_argument("--classification-root", type=Path,
                        default=Path(".beads/lost-bead-classifications"))
    parser.add_argument("--min-idle-days", type=float, default=DEFAULT_MIN_IDLE_DAYS)
    parser.add_argument("--similarity-threshold", type=float,
                        default=DEFAULT_SIMILARITY_THRESHOLD,
                        help="Jaccard floor for the duplicate supersession signal.")
    parser.add_argument("--min-similarity-tokens", type=int,
                        default=DEFAULT_MIN_SIMILARITY_TOKENS,
                        help="Min content tokens before a title can match as a "
                             "duplicate (guards generic repeated titles).")
    parser.add_argument("--resling-cap", type=int, default=DEFAULT_RESLING_BATCH_CAP)
    parser.add_argument("--supersede-cap", type=int, default=DEFAULT_SUPERSEDE_BATCH_CAP)
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute + classify + report; write no records, "
                             "create no beads.")
    args = parser.parse_args(argv)

    min_idle = args.min_idle_days * 86400

    if not args.dry_run:
        _preflight()
    now = datetime.now(timezone.utc)
    observed_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    routed_ids = gather_routed_ids(args.base_dir)
    candidates: list[dict] = []
    corpus: list[dict] = []
    for rig in args.rigs:
        opens, ready, closed = gather_rig(args.base_dir, rig)
        corpus.extend(opens)
        corpus.extend(closed)
        candidates.extend(
            find_actionable_tail(opens, ready, routed_ids, now, min_idle)
        )

    index = build_dedup_index(corpus, args.min_similarity_tokens)
    superseded, resling = select_batches(
        candidates, now, index, args.resling_cap, args.supersede_cap,
        args.similarity_threshold, args.min_similarity_tokens,
    )
    actionable = len(candidates)

    records: list[tuple[str, str]] = []
    for bead in superseded:
        records.append((bead["id"], render_record(bead, "superseded", now, observed_at)))
    for bead in resling:
        records.append((bead["id"], render_record(bead, "resling", now, observed_at)))

    prev = read_heartbeat(args.cache_dir)
    grew = prev is not None and actionable > prev

    print(
        f"tail-end-detector: {actionable} actionable-idle never-dispatched "
        f"({len(superseded)} superseded-close, {len(resling)} resling this batch; "
        f"caps {args.supersede_cap}/{args.resling_cap}) "
        f"[prev_tail={prev} {'GROWING' if grew else 'steady/first'}]"
    )
    if args.dry_run:
        print(f"tail-end-detector: DRY-RUN, wrote nothing; total candidates={actionable}")
        return 0

    _write_records(args.classification_root, records)
    if grew:
        event_id = emit_growth_heartbeat(prev, actionable, observed_at)
        print(f"tail-end-detector: HEARTBEAT tail grew {prev}->{actionable} -> event {event_id}")
    write_heartbeat(args.cache_dir, actionable, observed_at)
    print(f"tail-end-detector: wrote {len(records)} classification records "
          f"to {args.classification_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
