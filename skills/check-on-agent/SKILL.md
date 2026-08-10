---
name: check-on-agent
description: Check in on ONE running gc-managed worker session to answer "what is it doing right now / did its artifact land / is it stalled?" — using the least-invasive tool the need actually requires. Observe first (peek/logs/ps + read-only git); escalate to messaging (submit/nudge/mail) only when observation shows activity has genuinely stopped. Use when the user says "check on agent X", "is the worker stalled", "what is session X doing", "check in on the pr-pipeline worker", "did the commit land yet", "is X still working or hung". NOT a fan-out revive of the whole fleet (that is nudge-city) and NOT inter-agent messaging composition (that is communicate-with-other-agent). Recommended model: Sonnet (mechanical read + light diagnosis).
---

# check-on-agent

Check in on a **single** running gc-managed worker session, at the smallest
cost the need actually requires. The default outcome is *observation only*: an
active worker almost never needs to be messaged — watching it answers the
question, and a redundant `submit`/`nudge` is noise that can also interrupt a
worker at a bad boundary.

Companion to [[nudge-city]] (fleet-wide revive of stalled sessions) and
[[communicate-with-other-agent]] (inter-agent inbox messaging). This skill is
the "look at ONE worker and decide if it even needs a poke" front door.

## The governing rule

> **An active worker does not get messaged.** Observe first. Escalate to
> messaging only when peek/logs/process-state show activity has actually
> **stopped for a bounded window** — not merely that an artifact hasn't landed
> yet. A slow gate (build, codegen pre-commit hook, test suite) looks identical
> to a hang from the bead layer; only process/transcript observation
> distinguishes them.

## Step 1 — Observe (default; always safe, no side effects)

Start here every time. Most check-ins should *stop* here.

```bash
# Recent transcript — what is the agent actually saying/doing?
gc session peek <session-id> --lines 80

# Recent structured log tail
gc session logs <session-id> --tail 20

# Session liveness (state + last_active; compare last_active to now)
gc session list --json | python3 -c "import json,sys;[print(s['id'],s['state'],s.get('last_active')) for s in json.load(sys.stdin)['sessions'] if s['id']=='<session-id>']"

# Did the artifact land? (read-only git in the worker's worktree)
git -C <worktree> status --short
git -C <worktree> log --oneline <BASE>..HEAD
```

**If "active but no artifact yet", find out WHY before concluding anything.**
A worker can be genuinely busy inside a slow subprocess (a build, a codegen
pre-commit hook, a test run). Trace the process tree to tell *churning* from
*wedged*:

```bash
# Find the worker's blocking process (e.g. a parked `git commit`) and walk its children.
ps aux | grep -E 'git commit|pre-commit|go run|go build' | grep -v grep
pgrep -P <blocking-pid>          # repeat down the tree
ps -p <pid> -o pid,etime,command # etime shows how long each stage has run
```

Forward progress = **new** sub-processes/stages appearing over successive
checks (stage A → stage B), or the transcript advancing. Same single process
pinned with no children spawning across a bounded window = candidate stall →
report the exact process tree/stage and **ask before interrupting**.

## Step 2 — Interact, only if observation says you must

Pick the lightest tool that meets the need. Escalating cost top-to-bottom:

| Need | Tool | Notes |
| --- | --- | --- |
| Agent must **do or report** something, and it is responsive | `gc session submit <id> "…" --intent follow_up` | Injected message handled at the next safe boundary. **Preferred** over attach/mail. |
| Short "what's your state right now?" poke, terminal-style | `gc session nudge <id> "…" --delivery wait-idle` | Delivered when idle; lighter than submit. |
| Non-urgent async coordination | `gc mail send <id> -s "…" -m "…"` | Inbox-style; unreliable for "what are you doing *right now*" unless the agent checks mail. |
| Last resort | `gc session attach <id>` | Heaviest — can resurrect a suspended/dead session. **Never a first probe.** |

## Decision rule (apply explicitly)

1. Run Step 1. If the worker is **active with forward progress**, you are done
   — report the observed state (stage/artifact) and stop. Do not message it.
2. If activity has **stopped for a bounded window** (no transcript movement, no
   new sub-processes), report the exact evidence (last_active, process tree,
   last transcript line) and escalate to the *lightest* Step-2 tool that fits —
   usually `gc session submit … --intent follow_up`.
3. If the session is **dead/suspended** and the work must continue, that is a
   revive concern → hand off to [[nudge-city]], not a per-worker poke here.

## Scope / boundaries

- **Read-first, single-worker.** This skill does not mutate beads, force-claim,
  force-close, restart the city, or fan out over the fleet.
- Interrupting an actively-progressing worker is a defect, not diligence — the
  cost of a mistimed message (broken boundary, lost work) exceeds the cost of
  waiting one more observation cycle.
- If a check-in reveals a real blocker in the worker's output (bad commit,
  hygiene violation, wrong base), that is a finding to report/route through the
  normal review path — not something this skill resolves in place.
