# GC Drains and the Brief Pipeline — Analysis (2026-07-08)

Audience: the human adjudicator. Purpose: understand how GC drains work before deciding whether
and how to use them when converting mathematics to a GC-native domain-automation
pack with `[imports.gc]`.

---

## 1. How GC Drains Work

### What a drain is

A drain is a formula step that consumes every member of a convoy (a set of
related work beads) by spawning a sub-formula run per member. The step block
looks like this in TOML:

```toml
[[steps]]
id = "implement"
condition = "{{drain_policy}} == separate"
metadata = { "gc.run_target" = "{{implementation_target}}" }

[steps.drain]
context = "separate"         # or "shared"
formula = "do-work"          # formula to run for each member
member_access = "exclusive"  # lock semantics
```

The GC runtime reads `[steps.drain]`, finds all convoy members, and pours one
instance of `formula` per member. The parent formula step does not complete
until every member formula completes (fan-in). There is no drain syntax for
"pick one item at a time" vs "all in parallel" — that is controlled by
`context`.

### The two drain contexts

| `context` | What GC does | When to use |
|-----------|-------------|-------------|
| `separate` | Each member gets its own session (parallel, isolated) | Independent work items; no shared state across items |
| `shared` | All members run in one session, one at a time (`single_lane = true` + `on_item_failure = "skip_remaining"`) | Items need shared worktree/context; serial execution |

`separate` is the default and the common case. `same-session` exists for
workflows where workers need a shared conversation or shared filesystem state
across items.

### What a drain consumes and produces

- **Consumes**: the convoy identified by `convoy_id` (injected by GC core at
  runtime). Each convoy member becomes one invocation of `formula`.
- **Produces**: per-member formula outputs (artifacts, bead closures). The
  parent step waits for all members to complete.
- **Evidence contract**: each member formula must write implementation evidence
  (e.g., `gc.build.implementation-summary.v1`) per the base contract. The
  `summarize` step that follows the drain reads those artifacts and rolls them
  up.

### Drain vs convoy-step

`implementation_strategy = "drain"` means the pack uses the built-in drain
mechanism. `implementation_strategy = "convoy-step"` means the pack replaces
the drain entirely with its own internal logic (may sequence, batch, or fan
out). Convoy-step packs set `allowed_drain_policies = []` because they own the
dispatch themselves.

Drains are declared in formula TOML; convoy-steps are arbitrary formula graphs
that happen to consume a convoy. The difference matters because GC enforces
drain metadata in tests.

### Where drains live in the existing pack ecosystem

Every build-methodology pack (gascity, bmad, gstack, superpowers, compound-
engineering) uses the same pattern:

1. Top-level build formula declares `allowed_drain_policies = ["separate", "same-session"]` and `implementation_strategy = "drain"`.
2. Two `[[steps]]` with mutually exclusive `condition` clauses (`drain_policy == separate` vs `drain_policy == same-session`).
3. `separate` step drains with a "full item" formula (e.g. `do-work`, `bmad-story-development`, `gstack-work`).
4. `same-session` step drains with a "single-lane item" formula (e.g. `do-work-item`, `bmad-story-development-item`) that has `single_lane = true`.

Mathematics currently uses none of this. Its formulas are order-triggered event
handlers, not convoy consumers.

---

## 2. How the 6 Brief-Pipeline Stages Map to GC Drain Steps

The brief pipeline:

```
produce → shuffle → present → decide → dispatch → archive
```

**None of these stages is currently a convoy drain.** Let me map each:

| Stage | Current GC primitive | Could be a drain? | Notes |
|-------|---------------------|-------------------|-------|
| **produce** (`brief-prep`) | Manual/on-demand formula pour | Only if brief production is batched across many source items simultaneously | Currently: one brief per pour. A drain would be useful only if you want to produce N briefs in parallel from a convoy of pending source beads. |
| **shuffle** (`brief-shuffle`) | Condition-triggered order, one item per run, serial with `.shuffle.lock` | No — intentionally NOT a drain | Shuffle must be single-writer. A drain would spawn parallel runs and corrupt the lock-guarded manifest. |
| **present** (`brief-present-next`) | Manual-triggered order, drains the manifest queue in one session | Closest thing to a drain already — it "drains the stack" but does so in a single agent pass, not via GC's drain mechanism | Brief-present-next already implements the "drain a queue" UX manually by reading `manifest.jsonl` and presenting all pending slugs. Converting it to a GC drain would require the stack to be structured as a convoy, not a JSONL file. |
| **decide** | Human interaction — adjudication happens | Not a drone-able step; requires human | N/A for drains. |
| **dispatch** (`brief-decision-dispatch`) | Event-triggered order, phase=vapor, one shell script processes all rigs | Could be a drain, but the current shape is better | The formula already scans all rigs and dispatches iteratively inside one session. A drain would be appropriate if each rig's dispatch were an independent sub-formula; the current monolithic shell script is equivalent but uses `gc runtime drain-ack` directly. |
| **archive** (`brief-archive-sweep`) | Cooldown-triggered order, phase=vapor, single shell script | No benefit to a drain | File moves with no convoy dependency. A drain adds structure without value. |

**Summary**: The brief pipeline's stages do not map onto GC drains because the
brief pipeline's unit of parallelism is not a convoy. The pipeline is a
decision queue (a JSONL manifest + file system state), not a GC convoy of
beads. Drains operate on convoys.

---

## 3. Same-Session Drain vs Separate-Session Drain

### Definitions (from GC core)

**Separate-session drain** (`context = "separate"`):
- GC spawns one independent agent session per convoy member.
- Members run in parallel (subject to convoy dependency graph).
- Each member gets its own worktree, conversation, and execution environment.
- Member failures are isolated — one failed item does not block others.
- Used by all default build-methodology packs.

**Same-session drain** (`context = "shared"`):
- GC runs all members sequentially inside one shared agent session.
- `single_lane = true` enforces one-at-a-time ordering.
- `on_item_failure = "skip_remaining"` stops on first failure rather than
  attempting remaining members.
- Members share the same worktree and conversation context.
- Used when items have ordering dependencies or need shared accumulated state.

### Which brief-pipeline stages need which

If the mathematics pack were restructured to use GC drains (which requires the
unit of work to be a convoy), the mapping would be:

| Stage | Which drain context | Rationale |
|-------|-------------------|-----------|
| **produce** (batch N briefs from a convoy of source beads) | `separate` | Each brief-prep is independent; parallel production makes sense. |
| **shuffle** | Neither — single-writer, must stay serial | The shuffle lock prohibits concurrent writers. |
| **present** | `shared` (same-session) | Presenting all briefs needs to happen sequentially in one conversation so the human adjudicator sees them in one coherent block. The current `brief-present-next` already does this manually. |
| **decide** | Human, not a drain | N/A. |
| **dispatch** | `separate` | Each rig's dispatch is independent; could parallelize by rig. But the current single-pass shell loop is simpler and already correct. |
| **archive** | Neither — no convoy | File moves; no benefit. |

**Key insight**: The only stage where a GC drain is genuinely attractive is
**produce**, if you ever want to batch-produce N briefs in parallel from a
convoy of pending source beads. All other stages either need serial/single-
writer discipline or have no convoy structure.

---

## 4. Formula Steps vs Drains — Where Each Belongs

### Stages better modeled as formula steps (not drains)

- **shuffle**: Single-writer, lock-guarded. Must remain a single formula step
  (or phase=vapor shell) that processes one item atomically. A drain would
  break the single-writer invariant.
- **present**: Already implements its own "drain the manifest" logic by reading
  `manifest.jsonl` in one session. Converting to a GC drain would require
  restructuring the stack as a GC convoy — significant effort for no user-
  visible benefit.
- **decide**: Human interaction. Not automatable via drains.
- **dispatch**: The current phase=vapor shell scans all rigs and dispatches
  serially. Converting to a separate-context drain across rigs is possible but
  would require the rig list to be a convoy — overhead with marginal benefit.
- **archive**: Deterministic file moves. No convoy structure. Phase=vapor shell
  is the right primitive.

### Stages that could use a drain if restructured

- **produce** (`brief-prep`): If the pack gains a formula that creates a convoy
  of source beads (e.g., "all beads with `needs-decision` label not yet
  briefed"), then a `separate`-context drain over that convoy running
  `brief-prep` per member would be natural GC idiom. This would require:
  1. A "collect source beads" step that writes a convoy.
  2. A drain step that calls `brief-prep` (or a math-specific item formula) per
     member.
  3. A post-drain shuffle step to promote pile items.

  This is the one place where adopting GC drain semantics has real payoff:
  parallel brief production from many source beads.

---

## 5. Key Decisions the human adjudicator Needs to Make Before Implementing Drains

### Decision 1: Does the pack import gascity?

The METHODOLOGY-PACK-VERDICT-2026-07-08.md recommends adding `[imports.gc]`
for hygiene (the pack already references `gc bd`, `gc event emit`, `gc runtime
drain-ack`). This import is the prerequisite for using GC drains at all —
drains are a `contract = "graph.v2"` feature, and graph.v2 formulas need the
GC runtime.

**Current state**: `pack.toml` has no `[imports]` block.
**Required for drains**: Add `[imports.gc]` pointing at the gascity pack.

### Decision 2: Is batch brief production a real need?

The only stage where a GC drain adds genuine value is batch-producing briefs
from a convoy of source beads. This matters only if:
- The inflow of `needs-decision` beads regularly outpaces manual brief-prep
  pours, AND
- Parallel production (multiple briefs simultaneously) is desirable.

If the answer is no — the human adjudicator produces briefs one at a time on demand — there is
no benefit to converting `brief-prep` to drain idiom. The current on-demand
formula pour is correct.

### Decision 3: Is the stack's data structure open to change?

GC drains operate on convoys (bead sets). The brief stack is currently a JSONL
manifest + filesystem. Draining the present stage would require either:
(a) Converting the stack to a GC convoy (significant restructuring, changes
    external tooling), or
(b) Keeping the current manifest and continuing to "drain" it manually inside a
    single formula session (current approach — already working).

Option (b) is recommended. Do not restructure the stack as a convoy unless
there is a specific platform benefit that justifies the migration cost.

### Decision 4: Does the single-writer shuffle need protection from concurrent drains?

If drain-based batch production is ever added, the shuffle's single-writer lock
becomes critical. The drain (produce) and the shuffle (promote) must not run
concurrently against the same `.pile/` directory. GC does not automatically
coordinate between drains and condition-triggered orders. The human adjudicator needs to
decide: rely on the existing `.shuffle.lock` to serialise, or use a GC
serialization primitive (e.g., `member_access = "exclusive"` on the drain step)
to prevent overlapping produce+shuffle runs.

### Decision 5: Does brief-decision-dispatch need per-rig parallelism?

The current dispatch formula processes all rigs serially in one shell script.
If the number of rigs grows or dispatch latency becomes a problem, converting
to a `separate`-context drain across a rig convoy is the GC-native approach.
This requires:
- A step that enumerates rigs and writes a GC convoy.
- A drain step that runs a per-rig dispatch formula per member.
- A post-drain step that aggregates results.

At the current scale (a handful of rigs), the monolithic shell is simpler.
Only worth the restructuring if per-rig parallelism is measurably needed.

---

## Summary

GC drains are the right primitive for **parallel convoy consumption** — each
convoy member gets its own formula run. They are not the right primitive for
the brief pipeline's existing stages because:

1. The pipeline's unit of state is a JSONL manifest + filesystem, not a GC convoy.
2. The shuffle must remain single-writer (drain would break the lock invariant).
3. The present stage is already doing the "drain a queue" pattern manually,
   which is the correct shape for human-interactive adjudication.
4. The dispatch and archive stages are deterministic shell work with no convoy.

The one place where a GC drain is genuinely the right idiom is **batch brief
production**: if a convoy of pending source beads needs parallel `brief-prep`
runs, a `separate`-context drain over that convoy is exactly the GC pattern.
All other stages should stay as they are.

Before implementing anything, the human adjudicator should decide whether to add `[imports.gc]`
(the gascity prerequisite) and whether batch production is an actual need, not
just a theoretical one.
