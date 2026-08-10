---
name: simple-work
description: >
  Dispatch a bounded, well-scoped task through the math-city fleet using the
  simple-work-briefed formula. Use when the work is a single operation — a
  script run, a verification pass, a database repair, a text generation — and
  does not need the full build lifecycle (no planning, decompose, or review
  stages). Trigger phrases: "dispatch this as simple work", "sling this as
  simple-work-briefed", "run this one-off and get a brief", "this is a
  bounded task, use simple-work", "simple-work-briefed", "two-step briefed".
  NOT for multi-step builds with code review (use mathcity.work /
  build-basic-briefed). NOT for adjudicating briefs (use adjudicate-brief).
---

# simple-work — dispatch a bounded task with a brief at the end

Lightweight alternative to `mathcity.work` / `build-basic-briefed` for
tasks that are single, bounded operations. The `simple-work-briefed` formula
has three steps: **execute → file brief → finalize**. No requirements, plan,
decompose, or review overhead.

## When to use this instead of mathcity.work

| Use `simple-work` | Use `mathcity.work` |
|---|---|
| Run a one-off repair script | Build a feature branch end-to-end |
| Verification / smoke-test pass | Multi-step implementation with review |
| Database update or label repair | Tasks needing plan → decompose → implement |
| Generate a report or summary artifact | Anything that may push / open a PR |
| Bounded task with a known, fixed description | Work whose scope needs planning first |

**Decision rule:** if you can describe the full task in 3–5 sentences and it
fits in one polecat session, use `simple-work`. If it needs planning or
decomposition, use `mathcity.work`.

## Pre-flight (fleet must be up)

```bash
tmux -L gt ls >/dev/null 2>&1 || {
  echo "I'm sorry, I can't do that — no tmux fleet server."
  echo "Run 'gc restart' to give the supervisor a fresh tmux server, then retry."
  exit 1
}
gc dolt health >/dev/null 2>&1 || {
  echo "I'm sorry, I can't do that — Dolt is unreachable (bd cannot resolve beads)."
  echo "Run 'gc dolt status' / 'gc dolt start' and retry."
  exit 1
}
```

## Dispatch command

```bash
gc sling <rig>/gc.run-operator <bead> --on simple-work-briefed \
  --var source_bead=<bead> \
  --var brief_slug=<bead>-<short-slug> \
  --var task="<exact description: what to do, what inputs to read, what output is expected>" \
  --var model=<haiku|sonnet|opus> \
  --var context="<optional: file paths, bead IDs, or content to read before executing>"
```

Run from the rig root so `bd` resolves (e.g. `<city-root>/hecke` for `he-*` beads,
`<city-root>/gascity-packs` for `gsp-*`).

### Required vars

| Var | What to put |
|-----|-------------|
| `source_bead` | The bead ID this work is for (same as `<bead>`) |
| `brief_slug` | Stable filename stem for the brief artifact (`<bead>-<topic>`) |
| `task` | The full task description — state what to do, what to read, what output is expected. The polecat sees ONLY this. Be specific. |

### Optional vars

| Var | Default | When to override |
|-----|---------|-----------------|
| `model` | `haiku` | Use `sonnet` when task needs light reasoning; `opus` for high-stakes judgment |
| `context` | (empty) | Pass file paths, bead IDs, or inline text the polecat needs before it starts |

### Model guidance

- **haiku** — mechanical operations (script run, file rename, grep + report).
- **sonnet** — tasks requiring light judgment (verify conditions, summarize
  findings, triage results). Default for most math-city tasks.
- **opus** — high-stakes irreversible operations (server data destructive
  repairs, production schema changes).

## MANDATORY — verify-assignee gate

**A sling you did not verify may have stranded.** Within ~30–60s of slinging:

```bash
bd show <bead> | grep -i assignee   # must be NON-EMPTY
```

If Assignee is empty after 60s, re-check molecule status and escalate to mayor:

```bash
bd show <molecule-bead> | head -5   # molecule-bead ID printed at sling time
```

## Dispatch provenance event

Record every `simple-work-briefed` sling outcome as a linked event bead using
`dispatch-provenance.v1`. The linked event bead is the canonical record; any
brief text, manifest row, or file export is a cache.

```toml
schema = "dispatch-provenance.v1"
source_bead = "<bead>"
dispatch_command = "gc sling <rig>/gc.run-operator <bead> --on simple-work-briefed ..."
formula = "simple-work-briefed"
verified_assignee = true
assignee_state = "non_empty"
classification_hint = "healthy"
fingerprint = "verified_sling_claimed"
observed_at = "YYYY-MM-DDTHH:MM:SSZ"
```

For an empty assignee after the gate, set `verified_assignee=false`,
`assignee_state="empty_after_60s"`,
`classification_hint="immediate_strand"`, and
`fingerprint="empty_assignee_after_verified_sling"` before escalating.

Create and link the event:

```bash
bd create "dispatch provenance for <bead>" --type event --event-category dispatch.provenance --event-target <bead> --event-payload '<dispatch-provenance.v1 TOML or JSON>' --silent
bd dep relate <event-bead> <bead>
```

## What happens after dispatch

1. Fleet polecat picks up the molecule (`simple-work-briefed`).
2. **Step 1** — executes the task exactly as described in `--var task`.
3. **Step 2** — files a decision brief to the brief pipeline (`.beads/briefs/`).
4. **Step 3** — finalizes and closes the molecule.
5. Brief lands on the stack → `/check-briefs` finds it → `/present-briefs`
   presents it for adjudication.

No code is pushed. No PR is opened. The brief is the gate before anything
ships. This is the same accounting closure as `build-basic-briefed` (a brief
instead of a push), just without the full build pipeline overhead.

## Example — one-off repair script

```bash
cd <city-root>/hecke
gc sling hecke/gc.run-operator he-van4p --on simple-work-briefed \
  --var source_bead=he-van4p \
  --var brief_slug=he-van4p-gamma0-repair-live-run \
  --var task="Run repair-gamma0-labels.mag on aia-s27 DATA: cd <city-root>/hecke/magma/make/one-offs && I_HAVE_A_BACKUP=1 magma repair-gamma0-labels.mag. After: dispatch 7 recompute entries to priority queue, close he-q5nah." \
  --var model=sonnet \
  --var context="Authorization: he-m7iuh. Script: magma/make/one-offs/repair-gamma0-labels.mag (66 del, 172 rename, 7 recompute on DATA/gamma0/)."
```

## Provenance

- Formula: `simple-work-briefed` (gc formula show simple-work-briefed)
- Preferred formula for full builds: `build-basic-briefed` (policy gsp-fhdnu → see mathcity.work skill)
- Fleet liveness ground truth: `tmux -L gt ls` + `bd show <molecule> | head -5`
- Verify-assignee doctrine: `he-uz9fg`
