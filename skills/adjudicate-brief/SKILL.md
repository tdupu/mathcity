---
name: adjudicate-brief
description: Use whenever a STANDALONE decision needs to be recorded persistently in a bd-managed rig — human adjudications, architecture choices, policy locks, gate-criterion additions. EXCEPTION — brief verdicts: under the one-bead model (brief-system POLICY.md B2.2, 2026-07-12) a brief bead IS the decision bead; its verdict is recorded ON the brief bead and the bead is closed — do NOT create a second decision bead for a brief. Enforces the `bd create -t decision` canonical primitive per the bd-decision-canonical architecture principle (gascity triage 2026-06-26, LD #10 + AP2). Refuses to write decisions to non-`bd decision` stores (no markdown files, no custom jsonl writes, no `bd remember`-with-decision-content). Trigger phrases include "record a decision", "log this decision", "file the verdict", "this needs to be a decision-record", "preserve this for posterity", or any moment when an agent or human surfaces a verdict / rationale / chosen-alternative that should survive across sessions and be queryable by future work.
---

> **Canonical copy**: `mathcity.adjudicate-brief` in this mathcity pack. Materialized agent-skills copies are fallback only.

# adjudicate-brief

## FORK WRAPPER — calling agent's only job

**adjudicate-brief is a fork-composition.** The calling agent MUST immediately fork a subagent to do all recording/dispatch work, then report one line and stop. The calling agent executes NO bd commands itself — it only launches the fork.

### Step 1 — collect from invocation args + context

- `BRIEF_BEAD` — the brief's bead ID (from frontmatter `brief_bead:` or brief file, e.g. `he-dvwa`)
- `ARTIFACT` — the `artifact:` frontmatter field (e.g. `hecke#233`, `he-p4x5`)
- `VERDICT` — one of: `approve` / `reject` / `defer` / `revise`
- `RATIONALE` — the human adjudicator's stated reason (from invocation args, one line)
- `DEFER_UNTIL` — date string if verdict=defer (e.g. `2026-08-05`), else omit
- `RIG_DIR` — local rig directory (e.g. `<repos-root>/hecke` for `he-*` beads)

### Step 2 — launch fork

```
Agent(
  subagent_type: "fork",
  name: "adj-<BRIEF_BEAD>-<VERDICT>",
  description: "Adjudicate <BRIEF_BEAD> → <VERDICT>",
  prompt: "You are a fork executing adjudicate-brief. Record the human adjudicator's verdict on brief bead <BRIEF_BEAD> (artifact: <ARTIFACT>): verdict=<VERDICT>, rationale='<RATIONALE>'[, defer_until=<DEFER_UNTIL>], rig=<RIG_DIR>. Execute the FORK BODY section of the adjudicate-brief skill now in your inherited context. Run all bd commands. If verdict=approve, dispatch via mathcity.work. Report one summary line when done."
)
```

### Step 3 — report and stop

Emit exactly: `"Fork launched: <BRIEF_BEAD> → <VERDICT>. Session free."`

Do NOT wait for the fork. Do NOT run any bd commands. Stop here.

---

## FORK BODY — recording and dispatch

*You are a fork. Execute the following:*

### 1. Add verdict comment to the brief bead

```bash
cd <RIG_DIR> && bd comments add <BRIEF_BEAD> \
  "<VERDICT> (the human adjudicator $(date +%Y-%m-%d) via clerk). Rationale: <RATIONALE>"
```

### 2. Close or defer the bead

```bash
# verdict = approve / reject / revise → close:
bd close <BRIEF_BEAD> --reason "<VERDICT>: <RATIONALE>"

# verdict = defer → defer with date, leave open:
bd defer <BRIEF_BEAD> --until=<DEFER_UNTIL> \
  --reason="<RATIONALE>"
```

### 2b. Sync the decisions-track file + manifest (decision-briefs — MANDATORY when present)

If this verdict resolves a `decisions-to-briefs` file-brief — a
`<NN>-<slug>-brief.md` in `<city-root>/.beads/decisions-track/` with a
`manifest.jsonl` entry — you MUST update **both** the file frontmatter
`status:` line **and** the manifest entry in the same step. Updating only one
diverges the two records: `present-briefs` Method 3 trusts the manifest, but
any file-status scan re-surfaces the resolved decision. (Observed 2026-08-04:
17 briefs marked `adjudicated` in the manifest still read
`status: ready-for-adjudication` in-file, re-presenting decided decisions —
this step is the fix.)

`BRIEF_FILE` = the decisions-track path this verdict resolves (the clerk /
present-briefs passes it; if the brief has no decisions-track file, skip 2b).

```bash
DTRACK="$HOME/gt/.beads/decisions-track"
BRIEF_FILE="<path to NN-slug-brief.md, or empty>"
if [ -n "$BRIEF_FILE" ] && [ -f "$BRIEF_FILE" ]; then
  N=$(basename "$BRIEF_FILE" | sed -E 's/^0*([0-9]+)-.*/\1/')
  # defer keeps it ripe (resurfaces after its interval); every other verdict is terminal
  if [ "$VERDICT" = "defer" ]; then FS="ready-for-adjudication"; MS="ready"; else FS="adjudicated"; MS="adjudicated"; fi
  # (1) file frontmatter status: line (macOS BSD sed needs the '' arg)
  sed -i '' -E "s/^status:.*/status: $FS/" "$BRIEF_FILE"
  # (2) manifest entry: status (+ verdict/rationale/date when terminal), rewritten in place
  python3 - "$DTRACK/manifest.jsonl" "$N" "$MS" "$VERDICT" "$RATIONALE" "$(date +%Y-%m-%d)" <<'PY'
import json, sys
path, n, ms, verdict, rat, today = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
out = []
for line in open(path):
    s = line.strip()
    if not s: continue
    d = json.loads(s)
    if d.get("n") == n:
        d["status"] = ms
        if ms != "ready":
            d["verdict"] = verdict; d["verdict_note"] = rat; d["adjudicated_at"] = today
    out.append(json.dumps(d))
open(path, "w").write("\n".join(out) + "\n")
PY
fi
```

Invariant: after 2b, the file's `status:` and the manifest `status` for this
brief are equal. Never leave one `ready`/`ready-for-adjudication` while the
other is `adjudicated`.

### 3. If verdict = approve → dispatch via mathcity.work (MANDATORY)

Scope `artifact_root` per bead — never omit it or pass the bare rig root, or
concurrent runs on the same rig silently overwrite each other's stage
artifacts (gsp-1bmxuz):

```bash
gc sling hecke/gc.run-operator <ARTIFACT> --on build-basic-briefed \
  --var interaction_mode=autonomous --var review_mode=agent \
  --var drain_policy=separate --var push=false --var open_pr=false \
  --var artifact_root=<city-root>/hecke/.gc-builds/<ARTIFACT>
```

Verify assignee within ~60s:

```bash
bd show <ARTIFACT> | grep -i assignee   # must be non-empty
```

If assignee is empty after 60s, escalate to mayor.

### 4. Report

Emit one line: `"Adjudicated <BRIEF_BEAD>: <VERDICT>. [closed/deferred] [<ARTIFACT> dispatched if approve]"`

---

## For STANDALONE decisions (not brief verdicts)

When to use: a verdict that closes deliberation with recorded rationale — architecture choices, policy locks, gate-criterion additions, push/kill-switch authorizations.

**NOT for brief verdicts** (those go through the fork body above). NOT for ephemeral observations, cross-session facts (`bd remember`), or work items (`bd create --type task`).

### Canonical command

```bash
bd create "<title>" --type decision \
  --description "$(cat <<'EOF'
## Decision

<one-sentence summary of what was decided>

## Rationale

<why this was chosen — the substantive reasoning>

## Alternatives Considered

- **<alt 1>**: <why rejected>
- **<alt 2>**: <why rejected>

## Affects

- <bead IDs, files, or area descriptions>

EOF
)"
```

After creation, link affected beads:

```bash
bd dep add <decision-id> <affected-bead-id> --type related
```

### Supersede pattern

```bash
NEW_ID=$(bd create "<title>" --type decision --description "..." --silent)
bd dep add $NEW_ID <old-decision-id> --type related
bd comments add <old-decision-id> "Superseded by $NEW_ID: <brief reason>"
bd close <old-decision-id> --reason "Superseded by $NEW_ID"
```

### Refuse-and-explain

If asked to record a decision via non-canonical path:

> "Per the bd-decision-canonical architecture principle (gascity triage 2026-06-26), all decisions go through `bd create -t decision`. Let me reformulate: `bd create '<title>' --type decision --description ...`"

---

## What this skill does NOT do

- ❌ Write decisions to a markdown file
- ❌ Write to `<city-root>/<rig>/.beads/decisions.jsonl` directly (legacy — do not extend)
- ❌ Use `bd remember "<decision text>"` (that's for facts, not verdicts)
- ❌ Create a "decision" bead with `--type task` + title-marker (use `--type decision`)
- ❌ Skip the Decision / Rationale / Alternatives / Affects template

## Why this skill exists

Prior to grill-2 (2026-06-26), decisions were scattered across 3 `.jsonl` files + bd memories + title-marker beads + markdown files. The session locked `bd decision` as canonical (LD #10 + AP2). The fork-wrapper pattern (added 2026-07-22) keeps the calling session's context free during recording + dispatch — heavy bd + sling work runs in a background fork.

## What stays in the legacy stores (do NOT migrate)

`<city-root>/hecke/.beads/decisions.jsonl` (29 records), `<city-root>/hecke/.beads/briefs/decisions.jsonl` (301 records), `<city-root>/.gc/agents/mayor/decisions.jsonl` (23 records) — LEGACY, preserved via off-machine backup. Do not extend. Opportunistic backfill only when a historical decision surfaces in work.
