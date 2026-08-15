---
name: present-briefs
description: Present briefs one at a time in full form, maintaining a pre-loaded hot queue so the next brief is always ready the moment a decision is made. Use when the user wants to process briefs, says "next", "next brief", "Next", "continue", "what's next", "present my next brief", "next from queue", "show me the queue", "I'm ready for the next one", "keep the queue warm", or wants to churn through a backlog of briefs. Always presents one brief at a time in full — no summarizing, no batching multiple briefs in one response.
---

# present-briefs

Presents briefs **one at a time, in full**, while pre-loading the next brief in the background so the human adjudicator never waits between decisions.

**Origin:** the human adjudicator 2026-06-30 — "You should have a queue. This is dumb. We should be ready to go." — after watching a session manually fan out parallel subagents to pre-load briefs. Updated 2026-07-22: one brief at a time, always full form.

## When to use

- "Next" / "Next brief" / "Continue" / "What's next" — any brief-advance signal after a verdict
- "Present my next brief"
- "Next from the ripe queue"
- "Show me the brief queue"
- "I'm ready for the next one" → present pre-loaded brief + pre-load the one after
- Any time the human adjudicator wants to process a backlog without waiting between briefs

## Inputs

Via args (space-separated or comma-separated):

| Arg | Default | Meaning |
|-----|---------|---------|
| `--artifacts a,b,c` | (ripe queue) | Explicit artifact list; bypasses queue discovery |
| `--queue-path <dir>` | auto-discover | Override brief-stack directory |
| `--include-legacy-decisions` | false | Include eligible decisions-track records during the migration safety window |

Examples:
- `/present-briefs` → present top brief from ripe queue, pre-load next
- `/present-briefs --artifacts he-wzn,he-x8dk` → present he-wzn, pre-load he-x8dk

## Queue Discovery

When no explicit artifact list is given, the default ripe queue is the unified brief stack at `<rig-root>/.beads/briefs/stack`. The decisions-track scan is legacy fallback only: run it only when `--include-legacy-decisions` is passed or when no migration marker exists. If a decisions-track item appears in `stack/.index.jsonl` as `legacy_source`, suppress the legacy copy.

### Method 1 — stack index (default)

The stack index is the authoritative presentation queue. It carries the promoted brief path and its priority, so do not fall back to scanning arbitrary markdown files. Select ready entries from `stack/.index.jsonl`; a future `defer_until` is skipped, while a malformed date deliberately fails open:

```bash
STACK_DIR="${BRIEF_QUEUE_PATH:-$HOME/gt/.beads/briefs/stack}"
python3 - "$STACK_DIR" <<'PY'
import json, os, sys
from datetime import date

stack_dir = sys.argv[1]
index = os.path.join(stack_dir, ".index.jsonl")
try:
    lines = open(index)
except OSError:
    sys.exit(0)
with lines:
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        defer_until = entry.get("defer_until")
        if defer_until:
            try:
                if date.fromisoformat(defer_until) > date.today():
                    continue
            except (TypeError, ValueError):
                pass  # Malformed defer is fail-open.
        path = entry.get("path")
        if not isinstance(path, str) or not path:
            continue
        print(f'{entry.get("unlock_count", 0)} {path}')
PY
```

### Method 2 — decisions-track legacy fallback

`<rig-root>/.beads/briefs/migrations/2026-08-15-decisions-track-inventory.jsonl` is the default migration marker; override it with `BRIEF_MIGRATION_MARKER` if the migration batch differs. `INCLUDE_LEGACY_DECISIONS=1` represents `--include-legacy-decisions`. The selector returns nothing while the marker exists unless that flag is set. The legacy manifest remains authoritative for lifecycle state, and future defers are skipped while malformed defers fail open.

```bash
DECISIONS_DIR="${DECISIONS_TRACK_PATH:-$HOME/gt/.beads/decisions-track}"
STACK_INDEX="${BRIEF_STACK_INDEX:-${BRIEF_QUEUE_PATH:-$HOME/gt/.beads/briefs/stack}/.index.jsonl}"
MIGRATION_MARKER="${BRIEF_MIGRATION_MARKER:-$HOME/gt/.beads/briefs/migrations/2026-08-15-decisions-track-inventory.jsonl}"
INCLUDE_LEGACY_DECISIONS="${INCLUDE_LEGACY_DECISIONS:-0}"
export STACK_INDEX MIGRATION_MARKER INCLUDE_LEGACY_DECISIONS
python3 - "$DECISIONS_DIR" <<'PY'
import glob, json, os, sys
from datetime import date

decisions_dir = sys.argv[1]
stack_index = os.environ.get("STACK_INDEX", "")
marker = os.environ.get("MIGRATION_MARKER", "")
include_legacy = os.environ.get("INCLUDE_LEGACY_DECISIONS") == "1"
if os.path.exists(marker) and not include_legacy:
    sys.exit(0)

legacy_sources = set()
try:
    with open(stack_index) as index:
        for line in index:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict) and isinstance(entry.get("legacy_source"), str):
                legacy_sources.add(entry["legacy_source"])
except OSError:
    pass

try:
    manifest = open(os.path.join(decisions_dir, "manifest.jsonl"))
except OSError:
    sys.exit(0)
with manifest:
    for line in manifest:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict) or entry.get("status") != "ready":
            continue
        defer_until = entry.get("defer_until")
        if defer_until:
            try:
                if date.fromisoformat(defer_until) > date.today():
                    continue
            except (TypeError, ValueError):
                pass  # Malformed defer is fail-open.
        n = entry.get("n")
        if not isinstance(n, int):
            continue
        candidates = (glob.glob(os.path.join(decisions_dir, f"{n:02d}-*-brief.md"))
                      + glob.glob(os.path.join(decisions_dir, f"{n}-*-brief.md")))
        if not candidates:
            continue
        path = candidates[0]
        relative_path = f"decisions-track/{os.path.basename(path)}"
        if relative_path in legacy_sources or path in legacy_sources:
            continue
        print(f'{entry.get("unlock_count", 0)} {path}')
PY
```

The presentation queue is Method 1, optionally followed by Method 2, sorted by `unlock_count` descending:

```bash
{ stack_selector_output; legacy_selector_output_if_enabled; } | sort -rn | awk '{print $2}' | awk '!seen[$0]++'
```

If queue is empty: report "No ripe briefs in unified stack. Run /brief-prep, or /decisions-to-briefs to file a decision brief into the pile." and exit.

## Execution

### Phase 1 — discover and select

1. Run queue discovery (above).
2. Take the top item (the next unpresented brief).
3. Log: "Presenting: [artifact-id] (unlock_count=N) · [M remaining in queue]"

### Phase 2 — pre-load next in background

While presenting the current brief, immediately start pre-loading the next one:

```javascript
// Fire and forget — loads while the human adjudicator reads
agent(`Read the brief file for <next-artifact> at <path> and return its complete contents verbatim.`,
      { label: `preload:${nextArtifact}` })
```

### Phase 3 — present current brief in FULL

**Present the complete brief text verbatim.** No summarizing. No condensing. No omitting sections. The full `.md` file content, rendered as-is, inside the header/footer block:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BRIEF · <artifact-id> · unlock_count=<int>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<complete brief text — every section, every line>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUEUE: [artifact-id] presented · [M] remaining
Pre-loading: [next-artifact-id]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Brief quality gate:** If the brief has fewer than 7 sections (§1–§7 minimum), do NOT present it — send it back for brief preparation with: "Brief [artifact] has only [N] sections — returning to prep queue. Run /brief-prep on [artifact]."

### Phase 4 — wait for verdict, then cycle

When the human adjudicator gives a verdict:
1. Look up the full slug from the stack index (`stack/.index.jsonl` entry where `source == artifact_id`; use its `slug` field)
2. Invoke `brief-record-decision` via `gc sling`:
   ```bash
   gc sling <rig>/gc.run-operator brief-record-decision --formula \
     --var brief_slug=<slug> \
     --var decision=<approve|reject|revise|defer> \
     --var reason="<the human adjudicator's stated reason, or empty string>"
   ```
   Map the human adjudicator's words: "approve"/"yes"/"ship it" → `approve`; "reject"/"no"/"drop it" → `reject`; "revise"/"fix it"/"update it" → `revise`; "defer"/"later"/"not now"/"skip" → `defer`.
   If the human adjudicator says the brief is a no-brainer that should not have surfaced, keep the ordinary verdict as `approve`, `reject`, `revise`, or `defer`, and pass `--var no_brainer_leak=true --var no_brainer_leak_reason="<the human adjudicator's reason>"` to `brief-record-decision`.
3. Acknowledge: "Decision recorded: [artifact] → [choice]"
4. Present the pre-loaded next brief immediately (use the content already fetched in Phase 2 — no wait)
5. Start pre-loading the brief after that

## Tracking state (in-session)

```
presented:    [set of artifact IDs already shown this session]
hot:          [next pre-loaded (artifact, brief-text) pair — always 1 ahead]
queue:        [remaining artifacts not yet presented, in priority order]
```

On each decision: `hot` → present immediately; `queue.pop(0)` → fan out to refill `hot`.

## Error handling

| Situation | Action |
|-----------|--------|
| Brief has fewer than 7 sections | Return to prep queue; skip to next |
| Artifact brief `status` is not `approved` | Skip with note; continue to next |
| Decision brief promoted into the stack | **Present it** — decision briefs use the decision-at-top + action-block shape; do NOT apply the artifact-only gate below |
| Decision brief has fewer than 7 §-sections | Present anyway — decision-briefs follow the `decisions-to-briefs` shape (decision-at-top + action-block), not the artifact §1–§7 template; the 7-section gate binds artifact briefs only |
| Brief source bead has `Status: HELD` | Skip with note; continue to next |
| Queue empty at startup | "No ripe briefs. Run /brief-prep on pending artifacts first." |
| Queue drains mid-session | "Queue exhausted — [N] presented, 0 remaining." |

## Invariants

- **One brief per response**: never present more than one brief in a single response
- **Full text always**: present the complete brief verbatim — no summarizing, no condensing
- **Hot pre-load**: always have the next brief pre-loading while the human adjudicator reads the current one
- **Sort order**: unlock_count descending (highest unblocking value first)
- **No double-presentation**: track presented IDs to avoid re-presenting in same session

## Composes with

- **`/adjudicate-brief`** — records the human adjudicator's verdict and closes the brief bead
- **`/mathcity.work`** — dispatches approved artifacts (clerk runs this after approve)
- **`/brief-prep`** — upstream producer that populates the ripe queue with approved briefs
- **`/decisions-to-briefs`** — files new decision briefs into the unified pile (`<city-root>/.beads/briefs/.pile/`), from which `brief-shuffle` promotes them to the stack
- **Brief-pipeline substrate** — the unified `.beads/briefs/.pile -> stack` lifecycle this skill consumes; decisions-track is legacy fallback only during migration

## What this skill does NOT do

- Does not create or modify briefs (that's `/brief-prep`)
- Does not record decisions unilaterally — the human adjudicator's verdict is the trigger
- Does not call `bd close` on any bead directly
- Does not push any commits
- Does not present multiple briefs in one response
