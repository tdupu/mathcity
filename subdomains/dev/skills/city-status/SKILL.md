---
name: city-status
description: Gas City fleet and work-queue status snapshot — checks fleet liveness, active sessions, in-progress beads, molecule step tables (steps done, change in last hour, start/completion times), brief pipeline state, and Dolt health. Use when the user says "city status", "what's running", "fleet health", "what is the city doing", "how is the city", "are things getting done", "what beads are in progress", or "check the pipeline". Read-only: never dispatches, slingshoots, or modifies beads. Recommended model: Sonnet (mechanical read + light diagnosis).
---

# city-status

Read-only snapshot of Gas City fleet and pipeline. Run before any dispatch
decision and after city restart to confirm health. Never commits, slingshoots,
or modifies any bead.

## Pre-flight

```bash
gc dolt health 2>&1 | head -3
```

If Dolt is unreachable: report `DOLT DOWN — most bd commands will fail`.
Continue with tmux/session checks only.

## Procedure

### 1 — Fleet liveness

```bash
tmux -L gt ls 2>&1
gc session list --state active 2>&1
```

**CRITICAL**: `gc status` lies about agent count (bug gs-0cy2 — probe times
out, reports 0). Use tmux + session list as ground truth.

Report:
- Number of live tmux sessions (non-zero = city alive)
- Active session IDs, templates, worktdirs, age, last-active

### 2 — In-progress beads (per-rig)

For each major rig the user works in (hecke, gascity-packs, agent_skills, gt):

```bash
cd <city-root>/<rig> && bd list --status in_progress 2>/dev/null | head -20
```

For any in-progress bead with a suspiciously old heartbeat:
```bash
bd show <bead-id> 2>&1 | grep -E "Lease|heartbeat|Assignee|Updated"
```

**Lease expiry note**: expired leases on implementation workers are NORMAL
when the city was recently restarted (heartbeat gap = city downtime) or when
a long Magma computation is running. Check `gc session peek <session-id>` to
confirm the worker is actually computing:

```bash
gc session peek <session-id> 2>&1 | tail -10
```

An active Magma process (non-zero CPU, growing cpu-time) = computing, not
stuck.

### 3 — Active molecules (top 10, step table)

Identify all active `gc.run-operator` and `gc.implementation-worker` sessions.
For each, extract the bead ID from the worktdir name and query step progress.

```bash
# List sessions with worktdir
gc session list --state active 2>&1 | grep -E "gc\.run-operator|gc\.implementation-worker"
```

Extract bead ID from each worktdir: `basename <worktdir>` gives
`<bead-id>-<formula-name>`. The bead ID is the leading `<prefix>-<6chars>`,
e.g. `gsp-06gg` from `gsp-06gg-build-basic-briefed`.

For each bead ID, determine the Dolt DB by prefix:
- `he-*` → `hecke`
- `gsp-*` → `gascity_packs`
- `gt-*` → `hq`
- `gs-*` → `gs`
- `as-*` → `agent_skills`

Query step counts via the `dolt` CLI directly (steps are linked via `dependencies.type='tracks'`,
NOT via a `parent_id` column in `issues`). Dolt data lives at `<city-root>/.beads/dolt/<db>/`:

```bash
cd <city-root>/.beads/dolt/<db> && dolt sql -q "
SELECT
  COUNT(*) AS total_steps,
  SUM(CASE WHEN i.status='closed' THEN 1 ELSE 0 END) AS done_steps,
  SUM(CASE WHEN i.status='closed'
    AND i.closed_at > DATE_SUB(NOW(), INTERVAL 1 HOUR) THEN 1 ELSE 0 END) AS recent_steps,
  MIN(i.created_at) AS first_step,
  (SELECT closed_at FROM issues WHERE id='<bead-id>') AS completed_at,
  (SELECT title FROM issues WHERE id='<bead-id>') AS root_title
FROM dependencies d
JOIN issues i ON i.id = d.issue_id
WHERE d.depends_on_issue_id = '<bead-id>' AND d.type = 'tracks'
" 2>&1
```

**Note**: `gc dolt sql -d` does not support a `-d` flag; use `cd <city-root>/.beads/dolt/<db> && dolt sql`.
For impl-worker beads (not build-basic-briefed runs), there are typically no tracked steps — report `n/a`.

Render a markdown table (copy-pastable, plain ASCII):

```
| Molecule           | Steps      | +1h | Status                         | Started     | Completed   |
|--------------------|------------|-----|--------------------------------|-------------|-------------|
| <id> (<label>)     | <done>/<N> ✓| +N  | ✅ complete / ⏳ running / ❌   | <time>      | <time> / —  |
```

- Steps column: `<done>/<total> ✓` if done == total (complete), else `<done>/<total>`
- +1h column: steps closed in the last hour (progress rate signal)
- Status: ✅ complete if root bead closed; ⏳ running if root open; ❌ if stalled (no progress in 2h+)
- Completed: root bead `closed_at` if closed, else `—`

Show top 10 most recently active (by session last-active timestamp).
If no run-operator or implementation-worker sessions exist, report "No active molecules".

Also check recently completed molecules (closed within last 4h) from any rig for completeness:
```bash
gc dolt sql -d <db> -q "
SELECT id, title, closed_at
FROM issues
WHERE issue_type = 'molecule' AND status = 'closed'
  AND closed_at > DATE_SUB(NOW(), INTERVAL 4 HOUR)
ORDER BY closed_at DESC LIMIT 5
" 2>&1
```

### 4 — Brief pipeline

```bash
ls <city-root>/.beads/briefs/.pile/*.md 2>/dev/null | wc -l
ls <city-root>/.beads/briefs/stack/*.md 2>/dev/null | wc -l
gc session list --template mathcity.brief-operator 2>&1 | head -10
```

Report:
- `.pile/` count — briefs waiting to be shuffled
- `stack/` count — briefs awaiting human adjudication
- Active brief-operator sessions

**Shuffler lock check**:
```bash
ls -la <city-root>/.beads/briefs/.shuffle.lock 2>/dev/null && echo "LOCK HELD" || echo "lock free"
```

A held lock lasting > 30 min without an active brief-operator session
processing is a stall (lock theft cascade bug gt-v3pisq). Remediation:
`rm <city-root>/.beads/briefs/.shuffle.lock` — only if no active session holds it.

**Top 10 recently added to stack** (for context on what's waiting):
```bash
ls -lt <city-root>/.beads/briefs/stack/*.md 2>/dev/null | head -10 | awk '{print $NF}' | xargs -I{} basename {}
```

### 5 — Dolt health detail

```bash
gc dolt health 2>&1
```

Key metrics to surface:
- Latency (warn ≥ 1000ms, critical ≥ 3000ms)
- Connections (warn ≥ 50, critical ≥ 200)
- Disk (warn ≥ 1G per DB)

High latency during concurrent `gc sling` runs is NORMAL and transient.
Sustained high latency with low connection count warrants `gc dolt logs`.

### 6 — READY queue

```bash
cd <city-root> && bd ready 2>&1 | head -20
cd <city-root>/hecke && bd ready 2>&1 | head -20
```

Report count of ready beads per rig. Many READY beads + no active
implementation workers = dispatch gap (run `/mathcity.work` on the highest
priority item).

## Output format

Use rendered GitHub-flavored markdown. Bold section headers, real markdown tables.
Example structure:

---

**• City Health Check — 10:41 AM HST (20:41 UTC)**

---

**1. Fleet:** N tmux sessions — stable/STALLED. N dispatchers, N brief-operators, N run-operators, N impl-workers.

**2. Dolt:** ✅ Nms — healthy. / ⚠️ Nms — WARN latency. / ❌ DOWN.

**3. Molecules:**

| Molecule | Steps | +1h | Status |
|---|---|---|---|
| `<id>` (<label>) | N/M ✓ | +N | ✅ complete |
| `<id>` (<label>) | N/M | +0 | ⏳ running |

**4. Brief stack:** N in pile, N on stack.

| Time | Brief | Notes |
|---|---|---|
| HH:MM | filename.md | note |

**5. Stale sessions:** None — all sessions LAST ACTIVE < 2h. / ⚠️ `<session-id>` stale Nh — `<diagnosis>`.

---

**IN-PROGRESS BEADS**

- `<rig>`: `<bead-id>` — title — lease: ok/expired — [computing/stuck/unknown]

**STALLS / BLOCKERS**

- [list any real stalls with diagnosis, or "no stalls detected"]

## What this skill does NOT do

- Does not dispatch or sling any beads
- Does not reclaim leases or kill sessions
- Does not release the shuffler lock automatically
- Does not interpret brief contents or adjudicate
- Does not run gc status (lying metric — gs-0cy2)
