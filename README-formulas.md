# mathcity — formulas index

**Single canonical index of every formula in the mathcity pack.**

28 formulas in `mathcity/formulas/`. This file is the ONE complete list. When in doubt, **this file wins**.

**Maintenance (single source of truth):**
- `formula-creator-math` appends the new formula's row here as a required step before filing the brief.
- `formula-work` (dispatch companion) reminds the executing agent to update this index after the human adjudicator approves and the formula is committed.
- Neither writes a parallel index. Do NOT create a competing formulas list elsewhere.

_Regenerate/verify with `/update-README`._

---

## Formulas — `mathcity/formulas/`  (28)

| Formula | Shape | What it does |
|---|---|---|
| `brief-archive-sweep` | do-work | Sweep old rejected or decided brief artifacts into archive state. |
| `brief-decision-dispatch` | do-work | For each undispatched decision record, execute the downstream event chain. |
| `brief-gate-keep` | do-work | Run the brief gate registry against one brief. |
| `brief-prep` | methodology | Prepare a policy-gated brief from source work. |
| `brief-present-next` | do-work | Drain all pending stack briefs in one session. |
| `brief-producer-failure-record` | do-work | Record producer-failure signals from brief-shuffle gate rejects. |
| `brief-producer-failure-rollup` | do-work | Roll up repeated producer-failure patterns and sling repair reviews. |
| `brief-producer-repair` | do-work | Diagnose repeated gate failures from a brief producer and file a repair brief. |
| `brief-record-decision` | do-work | Record the human decision for a presented brief and archive the run. |
| `brief-review-patrol` | do-work | Patrol the brief stack for briefs stuck at the Phase 5 review gate. |
| `brief-shuffle` | do-work | Single-writer shuffler for brief pile to stack promotion. |
| `brief-watchdog-refill` | do-work | Watch the brief stack and request refill work when the stack is below target. |
| `build-basic-briefed` | methodology | Full build lifecycle (requirements → plan → decompose → implement → review → finalize) with a decision-brief terminal slot instead of a direct merge. |
| `codex-dispatch` | do-work | Dispatch a task to the codex-worker for cross-model critical review. |
| `decision-enforce` | do-work | Enforce the bd-decision-canonical principle at formula call sites. |
| `file-or-sendback-route` | do-work | Post-decision file-or-sendback gate: log the routing choice for a decided brief. |
| `formula-creator-math` | methodology | Create a new mathcity formula TOML, enforcing the mandatory briefed-terminal-step convention. |
| `lost-bead-classification-rollup` | do-work | Group lost-bead classifications by fingerprint and prepare downstream filter-rule proposals. |
| `lost-bead-upstream-repair-rollup` | do-work | Create upstream repair-brief candidates from repeated lost-bead fingerprints. |
| `math-brief-prep` | do-work | Batch brief-prep cycle: fan-out produce across pending source beads, then file. |
| `no-brainer-classify` | do-work | Classify and optionally process no-brainer briefs. |
| `on-merge-brief-record` | do-work | Post-merge brief-record duty: inspect recently closed beads and file brief records for those that lacked one. |
| `planning-briefed` | methodology | Produce a planning artifact (PERT/decomposition/design) for a bead or epic, gated by a human decision brief. Planning steps run on Opus-level agents (gc.design-author). |
| `simple-work-briefed` | do-work | Simple-work with a brief filing terminal slot; lightweight alternative to build-basic-briefed for bounded one-off tasks. |
| `smoke-test-briefed` | do-work | Smoke-test a mathcity artifact (formula, skill, Magma, Python, script) and file a brief with test evidence and reproducibility guide (F6.1). |
| `test-execution-request` | do-work | Formal request workflow for test execution that should not happen silently. |
| `upf-experiment-dispatch` | do-work | Dispatch and breadcrumb an experiment that belongs on UPF. |
| `work-briefed` | do-work | Routing wrapper: auto-selects between simple-work-briefed and build-basic-briefed based on task shape. |

---

## Adding a new formula

Every new mathcity formula MUST have a row in this table. This is enforced by:
- `formula-creator-math` (Step 4 gate): checks that the formula name appears in this file before filing the brief.
- `formula-work` (dispatch companion): reminds the agent approving/executing the verdict to add the row.

Row format:
```
| `<formula-name>` | <methodology|do-work|proof> | <One sentence from the formula's TOML description field.> |
```

Shape vocabulary:
- **methodology** — multi-step lifecycle with planning phases; typically uses `plan_target` for high-tier fleet routing.
- **do-work** — bounded execution without a planning phase; single dispatch.
- **proof** — Opus-class adversarial proof loop.
