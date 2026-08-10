---
name: audit-recent-work
description: Produce a full accounting of work adjudicated in a session or date range — brief-record beads, decision beads, stack archives, and in-flight molecules — across all rigs. Use when the human adjudicator says "where did all the work go", "show me what was adjudicated today", "I need an accounting", "nothing is showing up on the stack", or "where are my briefs". Answers whether work is missing vs. mid-flight in a build-basic-briefed molecule (which only deposits a brief at the terminal publish step). Read-only by default.
---

# audit-recent-work

Produce a table of every item adjudicated or slung in a given session or
date, with timestamps, current state, and evidence of where each piece
went (brief produced, in-flight, or genuinely missing).

## When to invoke

- the human adjudicator says "where did all the work go" or "nothing is showing up"
- After a long session to verify nothing fell through the cracks
- When the brief pile looks empty but work was definitely adjudicated
- When investigating whether build-basic-briefed molecules produced briefs

## Key concept: briefs land LATE

Work routed via `--on build-basic-briefed` goes through the full
lifecycle: requirements → plan → plan-review → decompose → implement →
review → finalize → **brief**. The brief only lands at the terminal
publish step. Mid-flight molecules look like "missing work" until they
finish. This skill distinguishes the two cases.

## Procedure

**Step 1 — Check the brief stack for recent entries.**

```bash
# Named brief files (stack + pile)
ls -lt <city-root>/hecke/.beads/briefs/*.md 2>/dev/null | head -20
ls -lt <city-root>/hecke/.beads/briefs/.pile/*.md 2>/dev/null | head -20
ls -lt <city-root>/tmp-for-review/ 2>/dev/null | head -20

# decisions.jsonl — what was actually adjudicated (most recent first)
tail -50 <city-root>/hecke/.beads/briefs/decisions.jsonl 2>/dev/null
```

**Step 2 — Check bd for all beads updated/created today across all rigs.**

Supply a date in YYYY-MM-DD format. Omit `--updated-after` to get all
open/recent beads.

```bash
DATE="<today>"   # e.g. 2026-07-16
bd list --rig=hecke        --updated-after="$DATE" 2>/dev/null | head -60
bd list --rig=gascity-packs --updated-after="$DATE" 2>/dev/null | head -60
bd list --rig=agent_skills  --updated-after="$DATE" 2>/dev/null | head -40
```

For each bead in the results, check its status:
```bash
bd show <id> 2>/dev/null | grep -E "status|step|brief|assignee|verdict" | head -10
```

**Step 3 — Check in-flight molecules.**

Find molecule roots (open beads with molecule children):
```bash
gc session list 2>/dev/null | grep -E "run-operator|task-decomposer|implementation" | head -20
```

For each known build root (e.g. `he-teka1`, `gsp-ql6pd`):
```bash
bd show <root-id> 2>/dev/null | grep -E "status|step|publish|brief" | head -10
ls ~/.gc/worktrees/*/plans/ 2>/dev/null | grep "<root>" | head -5
```

Check for publish/brief step artifacts:
```bash
find ~/.gc/worktrees/ -name "brief*.md" -newer ~/.gc/worktrees/ 2>/dev/null | head -10
```

**Step 4 — Check agent-skills/gascity-packs for non-hecke brief trails.**

```bash
ls -lt <city-root>/gascity/.beads/briefs/ 2>/dev/null | head -10
ls -lt <city-root>/agent_skills/.beads/briefs/ 2>/dev/null | head -10
tail -20 <city-root>/gascity/.beads/briefs/decisions.jsonl 2>/dev/null
tail -20 <city-root>/agent_skills/.beads/briefs/decisions.jsonl 2>/dev/null
```

**Step 5 — Check the inbox for brief-ready notifications.**

```bash
grep -i "brief\|adjudicat\|verdict\|stack\|publish" \
  <city-root>/.claude/.agent-inbox.md | grep "$DATE" | tail -30
```

**Step 6 — Check the build-basic-briefed formula for the terminal brief step.**

To confirm where briefs land when the molecule completes:
```bash
find <repos-root>/gascity-packs -name "*.toml" | xargs grep -l "briefed\|brief-step\|publish" 2>/dev/null | head -5
# Then read the formula to find the publish/brief terminal step and its output path
```

## Output format

Produce three sections:

### 1. Adjudicated items table

```
| ID | Rig | Subject | Timestamp | Verdict | Brief produced? | Evidence |
```

Fill in from decisions.jsonl + bd show results. Mark "in-flight" for
molecules that haven't hit the publish step yet (NOT "missing").

### 2. In-flight molecules

```
| Root bead | Formula | Steps done/total | Brief step status | ETA signal |
```

These are NOT missing — they will produce a brief when the publish step fires.

### 3. Genuine gaps (if any)

Items with no trail in decisions.jsonl, no bd record, and no molecule
step — i.e. work that was slung but has no evidence of dispatch or
progress. These need investigation.

## Verdict

End the report with:
- Total adjudicated: N items
- Briefs landed: N
- In-flight (will produce briefs): N
- Genuine gaps: N (list IDs)
- Pending human verdicts: N (list IDs)

## What this skill does NOT do

- Does not modify any beads or files (read-only)
- Does not re-sling stuck work (surface gaps to the human adjudicator; the human adjudicator decides)
- Does not diagnose fleet health — for that, use `gc doctor` or check
  the supervisor log directly
