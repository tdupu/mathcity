---
name: xkcd-927
description: Reconcile or fix an issue that is spread across several beads / plans / PERTs / policy docs that duplicate, contradict, or prose-supersede each other — by CONSOLIDATING into the single existing source of truth, NEVER by writing a fresh artifact to "settle it" (that fresh artifact becomes competing standard N+1). Named for xkcd 927 ("14 competing standards → soon: 15 competing standards"). Trigger phrases: "reconcile these beads/plans without making a new standard", "avoid xkcd 927", "consolidate the competing PERTs/plans", "don't create a 15th standard", "fix these beads without proliferating", "pick one source of truth", "these plans disagree — settle it without adding another". NOT for building genuinely-new capability (no incumbents to compete with = not a 927 situation); only when the fix risks adding to a pile of competitors. Companion to adjudicate-brief (record the reconciling decision) and gc-recycle-bead (absorb/archive superseded content).
---

# xkcd-927

**The trap (xkcd 927):** N artifacts already claim to be the source of truth
for the same thing (competing PERTs, duplicate beads, a plan §X vs a newer
decision bead, a policy vs a handoff note). You are tempted to write a fresh
doc that "reconciles" them. That fresh doc does not replace the N — it sits
beside them as **standard N+1**. The pile grows; the next reader has one more
thing to disagree with.

**The rule:** fix the issue by **consolidating into one existing incumbent**
(or the bead graph itself) and **retiring the rest with additive edges** —
never by minting a new competitor. If a durable artifact is genuinely needed,
it must **supersede** the ones it absorbs, not join them.

## Procedure

1. **Enumerate the competitors** (mechanical). List every bead / plan / PERT /
   doc that currently claims authority over the same question. Read each at
   source — status, deps, body, notes (P5.4: trust the store, not the
   narrative).

2. **Select the canonical source of truth** (REASONING — this is a judgment
   call, not a rule). Decide *by reasoning about the specific situation* which
   incumbent should be authoritative. There is no fixed formula — "newest
   wins" / "highest-priority wins" / "longest doc wins" are all wrong as
   defaults. Weigh: which one is machine-visible to the consumers that
   actually dispatch/read it, which is closest to source truth, which the
   graph already points at. **Strongly prefer the bead graph itself** as
   canonical when possible — edges are machine-visible to a fresh session;
   prose in a `.md` is skipped by a reboot.

3. **Reconcile with additive edges** (mechanical execution of the reasoned
   plan; append-don't-edit). File the edges + dispositions that make the
   canonical authoritative and mark the rest superseded:
   - `bd dep add <canonical> <competitor> --type related` (or a supersede
     link where the store supports it)
   - `bd close <competitor> --reason "Superseded by <canonical>: <why>"` for
     true duplicates, or defer/re-scope where it still holds partial value
     (see gc-recycle-bead to ABSORB unique content before closing).
   - Record the reconciling decision itself via adjudicate-brief (one
     `bd decision`), so the *why* is queryable.
   Never rewrite a competitor's body — append edges and status only.

4. **The N+1 check** (mechanical guard). Before you write ANY new file, ask:
   *"Does this artifact become another competitor?"* If yes, don't write it —
   push the truth into the graph (step 3) instead. If a doc is truly
   unavoidable (a runbook, a reconciliation record), it MUST explicitly name
   and supersede every artifact it consolidates in its first lines, and those
   artifacts must be edge-marked superseded in the same pass. A consolidating
   doc that does not retire its inputs has just made standard N+1.

## Why the bead graph beats a new doc

A fresh reconciliation `.md` is invisible to the machinery that dispatches
work and to a rebooted session that reads the graph, not your prose. Edges
(`supersede`, `related`, missing `dep`) are what actually stop a future agent
from dispatching a stale/duplicate/frozen bead. Encode the reconciliation
where the consumer looks: the graph.

## check-zero note (ZFC)

This skill keeps reasoning in the model and mechanics in the shell:

- **Selecting the canonical SSOT (step 2)** and **deciding what supersedes
  what (step 3)** are model-based judgments — defer to reasoning about the
  specific artifacts. They must NEVER become keyword/heuristic routing (no
  "title contains 'PERT' → canonical", no "newest timestamp wins" rule). Such
  a rule is a V2/V4 ZFC violation and defeats the purpose.
- **Enumerating competitors, filing edges, the N+1 file-count guard** are
  mechanical — safe as deterministic steps.

## Composes with

- **adjudicate-brief** — record the "X is canonical, Y/Z superseded" verdict
  as a `bd decision`.
- **gc-recycle-bead** — ABSORB unique content from a competitor into the
  canonical before closing it, so consolidation loses nothing.
- **append-don't-edit** (P1.19) — this skill's edges are additive; bodies are
  never rewritten.

## What this skill does NOT do

- ❌ Write a new competing PERT/plan/standard to "settle" a disagreement.
- ❌ Rewrite or delete a competitor's body (edges + status only; absorb via
  gc-recycle-bead first).
- ❌ Pick the canonical by a fixed rule — the choice is always reasoned.
