# gascity vs mathcity — Capability & Gap Analysis (2026-07-08)

*Research/comparison for the mathcity `[imports.gc]` redesign. Read-only survey;
no pack files were edited. Files read are listed at the bottom.*

---

## TL;DR

gascity is a **build-methodology base pack**: it ships a virtual `build-base`
lifecycle contract (prepare → requirements → plan → plan-review → decompose →
implement → review → finalize → publish), a shared **artifact model** (front
matter + schemas + validator), a **drain/convoy** implementation model, a
**check framework** wired into formula steps, **neutral producer metadata keys**,
and a set of **`gc.*` role agents** to route work to.

mathcity is a **domain-automation pack** (verdict already reached in
`METHODOLOGY-PACK-VERDICT-2026-07-08.md`): it ships an **order-driven brief
pipeline** (produce → shuffle → present → decide → dispatch → archive) built on a
**16-gate registry**, a **single-writer shuffle lock**, and its own `gc.brief.*`
metadata namespace. It does **not** and **should not** extend `build-base`.

The two packs solve different problems. Adding `[imports.gc]` gives mathcity
**three concrete things nearly for free** — the artifact front-matter + validator
model, drain semantics for one stage (batch produce), and the shared check-script
convention — plus the hygiene of formally declaring the gascity primitives it
already calls (`gc bd`, `gc event emit`, `gc runtime drain-ack`, `graph.v2`).
Everything that makes mathcity *mathcity* (gates, shuffle lock, present/decide
loop, brief metadata) it still builds itself. gascity has **no** brief pipeline,
**no** gate/hurdle registry, **no** human-approval-queue primitive, **no** LaTeX
or lmfdb or theorem workflow.

---

## What gascity provides (by category)

### 1. Formula system / lifecycle contract
- **What**: `build-base` is a virtual `contract = "graph.v2"` formula defining a
  fixed anchor sequence and per-stage artifact contracts. Concrete packs extend
  it and override individual steps by `id`. Continuation entrypoints
  (`build-from-{requirements,plan,decompose,convoy,review}`) let a run start from
  whatever artifacts already exist.
- **Access via `[imports.gc]`**: a derived pack imports gascity as `gc` and either
  `extends = ["build-base"]` (methodology packs) or simply *references*
  `graph.v2` and `gc.*` targets without extending the lifecycle.
- **mathcity fit**: mathcity does **not** extend `build-base` — its unit of work is
  a *brief*, not a *build*, and its flow (produce→…→archive) is not the lifecycle.
  It only needs the **`graph.v2` runtime and formula-compiler ≥2.0**, which the
  import formalizes. **Adaptation, not direct reuse.**

### 2. Agent routing / roles
- **What**: gascity ships providerless role agents (`gc.run-operator`,
  `gc.requirements-planner`, `gc.design-author`, `gc.task-decomposer`,
  `gc.review-synthesizer`, `gc.implementation-worker`, `gc.publisher`, etc.) under
  `gascity/roles`, routed to via `metadata.gc.run_target` on each step. Agents are
  provider-neutral; a rig can patch a role to a specific provider without touching
  formulas.
- **Access via `[imports.gc]`**: import `gascity/roles` per-rig; step
  `gc.run_target` values then resolve to rig-local role agents.
- **mathcity fit**: mathcity already routes to `gastown.dog` (operator/shuffler
  bookkeeping) and `gastown.mayor` (judgment/review) — **city-native pool targets,
  not gascity role agents**. It defines its own `codex-worker` agent. mathcity does
  **not** need the gascity role set; its routing model is already complete.
  **No gap; no adoption needed.**

### 3. Artifact model (front matter + schemas + validator)
- **What**: base artifacts carry lightweight YAML front matter
  (`schema`, `workflow.{id,formula}`, `methodology.{pack,name}`,
  `producer.{formula,stage,attempt}`, `status`, `trace`). gascity owns immutable
  schema IDs (`gc.build.requirements.v1` … `gc.build.final-report.v1`) as YAML
  files under `gascity/schemas/build/`, plus one shared validator
  (`assets/scripts/validate_build_artifact.py` / `artifacts.py`) that checks front
  matter, section shape, coverage matrix, traceability, and drift hashes.
  Producer-stage validation runs after every artifact-producing step, with bounded
  schema-repair loops.
- **Access via `[imports.gc]`**: reference the shared validator and the
  `gc.build.artifact_schema` / `gc.build.artifact_path_keys` metadata pattern in
  step definitions; or model your own schema IDs on the same shape.
- **mathcity fit**: **This is the single strongest reuse target.** The
  `BRIEF-DOCUMENT-MODEL-PLAN` already proposes adding YAML front matter to every
  `brief.md` (`schema: mathcity.brief/1`, `workflow: brief-pipeline`, `producer`,
  `status`, `trace.*`) — a **direct structural echo** of the gascity artifact
  model. mathcity should adopt the *shape* (front matter fields + a namespaced
  immutable schema ID) but keep its **own** `mathcity.brief/N` schema, not the
  `gc.build.*` IDs (which would misrepresent the pack). **Adopt the pattern, own
  the schema.**

### 4. Convoy / drain model
- **What**: a drain step (`[steps.drain]`) consumes every member of a convoy,
  pouring one sub-formula per member; `context = "separate"` (parallel, isolated
  sessions) or `"shared"` (`single_lane`, serial, one session). `member_access =
  "exclusive"` gives lock semantics. Fan-in: parent step waits for all members.
  `implementation_strategy = "drain"` vs `"convoy-step"` (own dispatch,
  `allowed_drain_policies = []`).
- **Access via `[imports.gc]`**: `graph.v2` + import unlocks drain syntax in a
  pack's own formulas.
- **mathcity fit** (per `DRAINS-ANALYSIS`): the brief pipeline's unit of state is a
  JSONL manifest + filesystem, **not** a convoy, so most stages should not be
  drains. **shuffle** must stay single-writer (a drain would break the
  `.shuffle.lock` invariant); **present** already "drains a queue" manually in one
  session for coherent human review; **dispatch/archive** are deterministic shell
  work. The **one** genuine payoff is **batch produce**: a `separate`-context drain
  over a convoy of un-briefed `needs-decision` source beads, running `brief-prep`
  per member. **Optional; adopt only if batch production is a real need.**

### 5. Check framework
- **What**: `[steps.check.check]` with `mode = "exec"`, a script `path`, `timeout`,
  and `max_attempts`. gascity's checks live under `assets/scripts/checks/`
  (`build-artifact-valid.sh`, `design-review-approved.sh`, etc.). Control-flow
  gates belong in checks/graph steps; prompt rubrics are for qualitative judgment.
- **Access via `[imports.gc]`**: the convention is inherent to `graph.v2`; no
  special import needed beyond the runtime.
- **mathcity fit**: mathcity **already uses this pattern extensively** — 30+ check
  scripts under `assets/scripts/checks/` wired into steps with `max_attempts`.
  It's fully aligned at the primitive level; the import just formalizes the runtime
  it depends on. **Already adopted; no gap.** (One hygiene item: several check
  paths were hard-coded `<home>/...` absolute paths — a portability defect,
  not a gascity-coverage gap.)

### 6. Bead metadata keys
- **What**: gascity records **neutral producer metadata** on artifacts/root beads
  (`gc.build.artifact_schema`, `gc.build.*_path`, `gc.run_target`,
  `gc.github.*`, restart keys `gc.build.repair_status` / `gc.restart.*`). No owner
  or role fields.
- **Access via `[imports.gc]`**: reuse the neutral-metadata convention; do not
  reuse the `gc.build.*` keys unless you produce build artifacts.
- **mathcity fit**: mathcity owns a **parallel namespace** `gc.brief.*` /
  `mathcity.brief.*` (`slug`, `source`, `type`, `path`, `stage`, `gate_profile`,
  `decision_at`, `decision_outcome`). The `BRIEF-DOCUMENT-MODEL-PLAN` proposes
  making bead metadata the canonical index (replacing `manifest.jsonl`). This is
  the **same modeling philosophy** as gascity but a **distinct, correct namespace**.
  **Own the namespace; borrow the philosophy.**

### 7. Mode contracts
- **What**: `interaction_mode` (interactive / autonomous / headless) and
  `review_mode` (report / agent / interactive), honored by planning/review/
  decompose/fix/publish gates; declared in `[metadata.gc.methodology]`.
- **mathcity fit**: mathcity's human-in-the-loop is the **decide** stage (the human adjudicator
  adjudicates), plus fail-closed stop gates (G5/G5b/G12). This is a *different*
  human-participation model than gascity's `interaction_mode`. mathcity does not
  need `[metadata.gc.methodology]` (it isn't a methodology pack). **No adoption.**

### 8. "T3-bridge"
- **What**: **Not present in gascity.** Grep for `t3` across `gascity/` returns
  nothing. The T-tier / bridge concepts referenced in the mission are mathcity /
  planning-doc constructs, not a gascity export. **Nothing to import.**

---

## Gap analysis: mathcity needs vs gascity coverage

| Mathcity need | gascity coverage | Gap? |
|---|---|---|
| Brief routing pipeline (produce→shuffle→present→decide→dispatch→archive) | None. gascity's lifecycle is build (prepare→…→publish); no queue/adjudication model. | **Yes** — mathcity owns it entirely. |
| Human approval step | `interaction_mode=interactive` asks questions/approvals *inline within a build*; no standalone approval **queue**. | **Yes** — mathcity's present/decide loop is its own. |
| Document staging (pile/stack) | Artifacts land at fixed `artifact_root` paths; no pile/stack/promotion staging concept. | **Yes** — mathcity-specific. |
| Shuffle lock (single-writer) | `member_access = "exclusive"` on drains gives lock semantics for convoy members; **no** file-mutex primitive for a shared directory. | **Partial** — exclusive-drain could serialize a batch-produce drain, but the `.shuffle.lock` file mutex stays mathcity's. |
| Gate / hurdle policy registry | **None.** gascity has per-stage checks + approval states (draft/approved/blocked/…), but no fail-closed 16-gate registry with profiles. | **Yes** — mathcity owns the registry. |
| Per-domain agent routing | `gc.*` role agents + `gc.run_target` metadata. | **No** — pattern reusable; mathcity already routes to `gastown.dog`/`gastown.mayor` + `codex-worker`. |
| Artifact front matter | Full model: front matter fields + immutable schema IDs + shared validator + coverage/trace/drift. | **No** — mathcity should reuse the *shape* (own the schema ID). Strongest reuse. |
| Bead metadata for brief state | Neutral producer-metadata convention; `gc.build.*` keys. | **No** (philosophy reusable) — mathcity owns `mathcity.brief.*`. |
| LaTeX validation | **None.** No LaTeX awareness in gascity. | **Yes** — mathcity's `check-latex` skill + G6 latex-gate. |
| lmfdb query workflow | **None.** | **Yes** — mathcity's `search-lmfdb` skill + lmfdb MCP. |
| Theorem / proof workflow | **None.** gascity is code-build oriented. | **Yes** — mathcity's `critical-review`/`coordinate-review`/`is-good-experiment` skills. |

---

## What mathcity gets "for free" by adding `[imports.gc]`

1. **Formal `graph.v2` runtime + formula-compiler ≥2.0 dependency.** mathcity's
   formulas already declare `formula_compiler = ">=2.0.0"` and use `graph.v2`
   features (checks, metadata routing, drain-ack). The import makes that
   dependency explicit and resolvable instead of implicit.

2. **Drain semantics available in mathcity's own formulas** — specifically the one
   high-value case: a `separate`-context drain over a convoy of un-briefed source
   beads to batch-produce briefs in parallel (`brief-prep` per member), with
   `member_access = "exclusive"` to keep it from racing the shuffler.

3. **The artifact front-matter + shared-validator pattern** to model
   `mathcity.brief/1` on: reuse `gascity/assets/scripts/artifacts.py` /
   `validate_build_artifact.py` as a template (or, if the platform exposes a
   generic validator, invoke it), and adopt the neutral producer-metadata
   convention. This directly implements the `BRIEF-DOCUMENT-MODEL-PLAN` front
   matter with a battle-tested reference.

4. **The shared check-script convention** (already used) becomes an
   import-blessed dependency rather than an ad-hoc one.

5. **Hygiene / convention alignment**: the pack already calls `gc bd`,
   `gc event emit`, `gc runtime drain-ack`, and `gc.*`-namespaced skills; the
   import declares those primitives, which the `METHODOLOGY-PACK-VERDICT` flagged
   as the one genuine convention drift.

---

## What mathcity still needs to build itself

Everything that constitutes the brief pipeline — gascity provides none of it:

- **The 16-gate registry** (`gates.toml`, G1–G16) and the four gate kinds
  (mechanical / review / stop / manual) with fail-closed profiles
  (`standard`, `no_brainer`, `test_execution`, `experiment`).
- **The pile → stack → archive staging model** and the `.pile`/`stack`/`archive`/
  `decisions` directory tree.
- **The single-writer `.shuffle.lock` mutex** and stale-lock takeover logic.
- **The `manifest.jsonl` / bead-metadata index** and drain-manifest reader.
- **The present → decide → dispatch human-adjudication loop**
  (`brief-present-next`, `brief-record-decision`, `brief-decision-dispatch`,
  `file-or-sendback-route`) driven by the **order system** (event / condition /
  cooldown / manual triggers, scopes, pools) — orders are city primitives, not a
  gascity export.
- **The no-brainer classifier + kill-switch** (`ALLOW_NO_BRAINER_AUTO_EXECUTE`,
  G9/G12).
- **Its own schema ID** `mathcity.brief/N` (must NOT reuse `gc.build.*`).
- **All math-domain skills**: `check-latex`, `search-lmfdb`, `critical-review`,
  `coordinate-review`, `is-good-experiment`, `is-good-test`, `grill-and-present`,
  `present-it`, `brief-prep`, `catch-no-brainer`, `record-decision`.
- **The migration** of the brief tree from `.beads/briefs/` to
  `~/.gc/mathcity/briefs/` (per `BRIEF-DOCUMENT-MODEL-PLAN`), independent of gascity.

---

## Recommendations — minimum-viable `[imports.gc]` adoption

Ordered by value-per-rework. This deliberately does **not** convert mathcity into
a methodology pack (that would be a category error per the verdict doc).

1. **Add the `[imports.gc]` block (hygiene + prerequisite).** One block in
   `pack.toml` pointing at the gascity pack. Zero behavioral change, but it
   formalizes the `graph.v2` runtime and the `gc bd` / `gc event emit` /
   `gc runtime drain-ack` primitives the pack already uses, and it is the
   prerequisite for any drain adoption. **Highest value, lowest cost.** Pair it
   with the verdict doc's other one-liner: a `[metadata.gc.pack] kind =
   "domain-automation"` marker so reviewers stop applying the methodology rubric.

2. **Adopt the artifact front-matter shape for `brief.md`, keeping a mathcity
   schema ID.** Implement `BRIEF-DOCUMENT-MODEL-PLAN`'s YAML front matter
   (`schema: mathcity.brief/1`, `workflow`, `producer`, `status`, `trace.*`),
   modeled on the gascity artifact contract, and reuse `artifacts.py` /
   `validate_build_artifact.py` as a validator template. This is the biggest
   structural win: it makes briefs typed, validatable, and drift-aware without
   inventing a model from scratch. Do **not** use `gc.build.*` schema IDs.

3. **(Conditional) Add a batch-produce drain — only if batch production is a real
   need.** Per `DRAINS-ANALYSIS` Decision 2: if `needs-decision` inflow regularly
   outpaces one-at-a-time `brief-prep` pours, add a "collect un-briefed source
   beads → convoy" step and a `separate`-context drain running `brief-prep` per
   member, guarded by `member_access = "exclusive"` against the shuffler. If
   production stays on-demand, **skip this** — the current pour is correct.

**Do NOT adopt**: `build-base` extension, `gc.build.*` schema IDs,
`[metadata.gc.methodology]`, the `gc.*` role agents, or `interaction_mode` /
`review_mode`. None fit a brief-routing domain-automation pack, and adding them
would misrepresent what the pack does.

Net: items **1 and 2** are the minimum-viable adoption — a one-line import plus
the front-matter/validator reuse — capturing the real gascity value (runtime
formalization + artifact model) for a fraction of the rework, while every
brief-pipeline-specific mechanism stays mathcity-owned.

---

### Files read for this comparison
- `gascity/pack.toml`, `gascity/README.md`, `gascity/REQUIREMENTS.md`
- `gascity/formulas/build-base.formula.toml` (+ formula/schema/asset listings)
- `gascity/schemas/build/requirements.v1.yaml`; `gascity/assets/scripts/artifacts.py`
- `gascity/agents/run-operator/agent.toml`; `gascity/roles/pack.toml`
- `mathcity/pack.toml`, `mathcity/README.md`
- `mathcity/formulas/brief-prep.toml`, `brief-shuffle.toml` (+ full formula/skill/order/check listings)
- `mathcity/assets/brief-pipeline/paths.toml`; `mathcity/assets/brief-pipeline/gates.toml` (registry)
- `mathcity/BRIEF-DOCUMENT-MODEL-PLAN-2026-07-08.md`
- `mathcity/METHODOLOGY-PACK-VERDICT-2026-07-08.md`
- `mathcity/DRAINS-ANALYSIS-2026-07-08.md`
- (Note: `BEADS-DEEP-DIVE-2026-07-08.md` does not exist in the repo.)
