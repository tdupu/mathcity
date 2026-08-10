# mathcity — Expanded Structure Working Draft (2026-07-08)

> ⚠️ **Terminology correction (2026-07-21):** this draft's "gate = GC `[steps.check]`
> primitive / hurdle = mathcity checklist entry" framing is **wrong** — `[steps.check]`
> is natively a **check**, and "gate" is the control-flow checkpoint role. Do not adopt
> "hurdle." See **`TERMINOLOGY-check-vs-gate.md`**.

**Status:** WORKING DRAFT for the human adjudicator's review. Do not treat as committed design.
**Author:** expansion / planning agent.
**Basis:** JJ's initial sketch + existing pack survey + `HURDLES-RENAME-PLAN`,
`BRIEF-DOCUMENT-MODEL-PLAN`, `DRAINS-ANALYSIS` (all 2026-07-08), `check-latex`
skill + `latex-gate.toml` formula, and the `gates.toml`/`paths.toml` assets.

This draft folds three of the human adjudicator's in-flight decisions into JJ's sketch:

1. the **gate → hurdle** rename (GC reserves "gate" for `[steps.check]` — see
   `HURDLES-RENAME-PLAN`), so throughout this document "hurdle" = mathcity
   brief-policy checklist entry, "gate" = GC `[steps.check]` primitive;
2. **check-latex becomes a formula** with ~5 hurdles, not merely a skill;
3. the **document model moves out of `.beads/briefs`** into a GC artifact_root
   with typed front matter (see `BRIEF-DOCUMENT-MODEL-PLAN`).

---

## 0. What exists today (survey)

Pack dir: `<mathcity-pack-root>/` (renamed from `mathematics`; some
internal prose and paths still say `mathematics/` — the rename is mid-flight).

- `pack.toml` — v0.2.0, schema 2, **does NOT yet import gc**. It declares a
  `[providers.codex]` block instead. This is the single biggest gap vs. a
  GC-native domain pack (bmad/gstack both open with `[imports.gc]`).
- `agents/` — only `codex-worker/` (Codex fallback worker, `permission_mode =
  "suggest"`, fired only by explicit `codex-dispatch` pours).
- `formulas/` — 17 formulas, all brief-pipeline / codex / experiment plumbing
  (`brief-prep`, `brief-shuffle`, `brief-gate-keep`, `brief-present-next`,
  `brief-record-decision`, `brief-decision-dispatch`, `brief-archive-sweep`,
  `brief-watchdog-refill`, `no-brainer-classify`, `file-or-sendback-route`,
  `decision-enforce`, `on-merge-brief-record`, `test-execution-request`,
  `upf-experiment-dispatch`, `brief-review-patrol`, `codex-dispatch`,
  `brief-present-next`).
- `gates/` — 5 hurdle-formulas awaiting rename to `hurdles/`: `latex-gate`,
  `server-touching-safety-override`, `stale-claim`, `test-evidence`,
  `test-execution`.
- `assets/brief-pipeline/` — `gates.toml` (the 16-hurdle registry, → renames to
  `hurdles.toml`), `paths.toml`, `thresholds.toml`, `file-or-sendback-log-spec.md`.
- `assets/scripts/checks/` — 26 `[steps.check]` scripts (fail-closed poka-yoke).
- `skills/` — 24 skills including `check-latex`, `brief-prep`, `coordinate-review`,
  `critical-review`, `record-decision`, `present-briefs`, `is-good-experiment`,
  plus several GC-native skills already copied in (`create-convoy`, `fan-out`,
  `dolt-init`, `repo-to-city`, `prime-outsider`, `get-best-apis`, etc.).
- `orders/` — 10 orders wiring formulas to triggers (event / condition / cooldown
  / manual).

**Reference packs** `bmad/pack.toml` and `gstack/pack.toml` are both minimal:
```toml
[pack]
name = "bmad"
version = "0.1.0"
schema = 2

[imports.gc]
source = "../gascity"
```
They import gc and let GC-native agents/formulas/drains do the heavy lifting.
mathcity is far richer than either; the target is to keep mathcity's richness
while adopting the `[imports.gc]` + typed-agent + drain conventions those packs
model.

---

## A. `pack.toml` target state

```toml
[pack]
name = "mathcity"
version = "0.3.0"
schema = 2
description = "GC-native mathematical work pack: the brief pipeline (hurdles, formulas, orders), check-latex, and the five math sub-domains."

[imports.gc]
source = "../gascity"

# Codex remains available as a fallback provider for cross-model review.
# Keep it, but it is now secondary to gc-native run targets.
[providers.codex]
base = "builtin:codex"

[metadata]
maintainer = "the human adjudicator"
domain = "mathematics"
subdomains = ["brief-system", "computing", "proof-assist", "latex", "lmfdb"]
hurdle_registry = "assets/brief-pipeline/hurdles.toml"
artifact_root = "~/.gc/mathcity/briefs"
rename_lineage = "mathematics -> mathcity (gsp-2c0 hurdle rename, gsp-1pv doc-model move)"
```

Notes:
- The one load-bearing change is adding `[imports.gc]` — it is what makes drains,
  convoys, typed run targets, and `gc.run_target` routing resolve against the
  gascity core rather than being free-text.
- `[metadata]` is advisory (GC does not require it) but documents the 5 subdomains
  and pins the hurdle registry + artifact_root so tooling can find them without
  reading formulas. **OPEN:** confirm GC does not reject unknown `[metadata]` keys
  under schema 2 (see G).
- Bump to `0.3.0` to mark the gc-import + hurdle-rename + doc-model epoch.

---

## B. Agents

All five agents live under `agents/<name>/agent.toml` (+ `prompt.template.md`),
mirroring the existing `agents/codex-worker/` layout. Each registers a
`gc.run_target` of the form `mathcity.<name>` so formula steps can route to it via
`metadata = { "gc.run_target" = "mathcity.<name>" }`.

The design principle: **agents carry the judgment that scripts can't.** Every
mechanical check is a `[steps.check]` script (a GC gate); every place where a
human-like judgment call is needed becomes an agent run target. The 16 hurdles
split cleanly this way — `mechanical` hurdles are gates, `review` hurdles route to
agents.

### 1. `mathcity.brief-preparer`
- **Role (judgment):** turn a raw artifact (branch/bead/PR/diff) into a
  decision-ready brief — decide *what is actually being decided*, surface the
  assumptions and alternatives a reader needs, enforce the Decision-at-Top
  invariant, and choose full-form vs compact shape. Scripts cannot decide "is
  this the real decision" or "is this assumption load-bearing."
- **Receives:** `source` artifact ref, `brief_slug`, `brief_type`, `artifact_root`.
- **Produces:** `~/.gc/mathcity/briefs/.staging/<slug>/brief.md` with typed front
  matter (see F) and a populated `Hurdle Evidence` section (formerly "Gate
  Evidence"). Artifact type: `mathcity.brief/1`.
- **Run target:** `mathcity.brief-preparer`.
- **Workflow file:** `assets/workflows/math-brief-prep/prepare-brief.md`.

### 2. `mathcity.critical-reviewer`
- **Role (judgment):** adversarial read for correctness risks, policy misses, and
  missing/weak evidence. Emits `APPROVING` / `NEEDS-REVISION` with prioritized
  action items. This is the human-substitute reviewer behind hurdle **G4
  critical-review**. Wraps the existing `mathcity.critical-review` skill.
- **Receives:** the staged `brief.md` (or any artifact under review), plus the
  hurdle profile so it knows which review hurdles apply.
- **Produces:** a review verdict artifact
  `~/.gc/mathcity/briefs/.staging/<slug>/critical-review.md` (`APPROVING`/`NEEDS-
  REVISION` + action items), and updates the `G4` line in `Hurdle Evidence`.
- **Run target:** `mathcity.critical-reviewer`.
- **Workflow file:** `assets/workflows/math-brief-review/critical-review.md`.

### 3. `mathcity.experiment-reviewer`
- **Role (judgment):** pre-flight for experiment/test proposals — "is this a
  well-designed probe before we spend compute?" and "does this test meaningfully
  answer *does X work*?" Backs hurdles **G2 good-test** and the `experiment`
  profile's design review. Wraps `mathcity.is-good-experiment` + `is-good-test`.
- **Receives:** an experiment/test proposal (bead + proposed command/scope) or a
  brief of `brief_type = experiment | test-execution`.
- **Produces:** a design verdict `.../<slug>/experiment-review.md` (well-designed
  / redesign-needed + specific defects) and updates `G2`/experiment hurdle lines.
- **Run target:** `mathcity.experiment-reviewer`.
- **Workflow file:** `assets/workflows/math-experiment-dispatch/review-experiment.md`.

### 4. `mathcity.decision-recorder`
- **Role (judgment):** translate the human adjudicator's verdict on a presented brief into the
  canonical `bd decision` record, choosing the correct outcome encoding
  (approve/reject/defer/revise), the source-bead linkage, and the alignment
  rationale. Judgment: mapping free-form human adjudication onto the decision
  schema without fabricating intent. Wraps `mathcity.record-decision`.
- **Receives:** presented brief slug + the human adjudicator's verdict text.
- **Produces:** a `bd create -t decision` record + `.../decisions/<slug>/decision.toml`
  + rings the `brief.decided` event. Sets `mathcity.brief.decision_outcome` and
  `mathcity.brief.decision_at` on the source bead.
- **Run target:** `mathcity.decision-recorder`.
- **Workflow file:** `assets/workflows/math-decision-record/record-decision.md`.

### 5. `mathcity.review-synthesizer`
- **Role (judgment):** roll up the per-member outputs of a drain (see C /
  `DRAINS-ANALYSIS`) into a single coherent recommendation — the fan-in step
  after `critical-reviewer` / `experiment-reviewer` run per convoy member.
  Judgment: reconcile conflicting per-item verdicts, decide whether the *set*
  clears, and write one summary rather than N. This is the natural drain
  `summarize` step.
- **Receives:** the per-member review artifacts produced by a drain
  (`critical-review.md` / `experiment-review.md` for each convoy member).
- **Produces:** `.../<convoy>/review-synthesis.md` — a single consolidated verdict
  + the manifest of which members cleared. Artifact type
  `mathcity.review-synthesis/1`.
- **Run target:** `mathcity.review-synthesizer`.
- **Workflow file:** `assets/workflows/math-brief-review/synthesize-reviews.md`.

**Agent naming note:** the existing `codex-worker` stays as-is (cross-model
fallback, explicit pours only). The five above are the domain-judgment agents;
`codex-worker` is infrastructure.

---

## C. Formulas

Four formulas per JJ's sketch, each recast so that **mechanical hurdles are
`[steps.check]` gates** and **review hurdles route to agents via `gc.run_target`**.
Drain vs convoy strategy follows `DRAINS-ANALYSIS`: use a built-in **drain** when
each item is independent (`context = "separate"`), a **convoy-step** (own dispatch
logic) when the pipeline must process one-at-a-time under a single-writer lock
(the shuffler pattern).

### C.1 `math-brief-prep.formula.toml`

Producer side. Single-brief, no convoy. Terminal: submit to `.pile` (the shuffler,
a separate order, owns promotion — so this formula **does not drain**).

Steps:
1. `initialize-staging` — target `mathcity.dog` (operator); create staging dir,
   write front matter stub. No check.
2. `draft-brief` — **routes to `mathcity.brief-preparer`**; writes `brief.md`.
3. `attach-test-evidence` — `mathcity.brief-preparer`; **`[steps.check]` →
   `hurdle-test-evidence.sh`** (formerly `gate-test-evidence.sh`; G1).
4. `coordinate-review` — **routes to `mathcity.critical-reviewer`** (and
   `mathcity.experiment-reviewer` when `brief_type ∈ {experiment,test-execution}`);
   fills G2/G4/G6/G9.
5. `submit-to-pile` — `mathcity.dog`; **`[steps.check]` →
   `brief-pile-entry-required.sh`**. **Terminal:** no drain; the brief sits in
   `.pile` until the `brief-shuffle-pile` order fires.

```toml
formula = "math-brief-prep"
version = 1
[imports.gc]        # inherited from pack; shown for clarity
[[steps]]
id = "draft-brief"
metadata = { "gc.run_target" = "mathcity.brief-preparer", "gc.brief.path" = "{{artifact_root}}/.staging/{{brief_slug}}/brief.md" }
# ...
[[steps]]
id = "attach-test-evidence"
needs = ["draft-brief"]
metadata = { "gc.run_target" = "mathcity.brief-preparer" }
[steps.check]
max_attempts = 3
[steps.check.check]
mode = "exec"
path = ".../assets/scripts/checks/hurdle-test-evidence.sh"
timeout = "2m"
[[steps]]
id = "coordinate-review"
needs = ["attach-test-evidence"]
metadata = { "gc.run_target" = "mathcity.critical-reviewer" }
[[steps]]
id = "submit-to-pile"
needs = ["coordinate-review"]
metadata = { "gc.run_target" = "mathcity.dog" }
[steps.check]
max_attempts = 2
[steps.check.check]
mode = "exec"
path = ".../assets/scripts/checks/brief-pile-entry-required.sh"
```
(This is `brief-prep.toml` reshaped: agent run targets replace the `gastown.mayor`
/ `gastown.dog` free-text targets, and "gate" prose → "hurdle".)

### C.2 `math-brief-review.formula.toml`

The hurdle-keep + review side. **This is where the drain lives** when a batch of
briefs/beads must be reviewed. Strategy: **convoy-step** for the single-writer
shuffle (one item per run, `.shuffle.lock`), then an internal **drain**
(`context = "separate"`) for parallel per-member critical/experiment review, with
`mathcity.review-synthesizer` as the fan-in `summarize` step.

Steps:
1. `acquire-lock` — `mathcity.dog`; take `{{artifact_root}}/.shuffle.lock`.
   **`[steps.check]` → `brief-pile-nonempty.sh`**.
2. `run-hurdle-registry` — `mathcity.dog`; run mechanical hurdles.
   **`[steps.check]` → `brief-mechanical-gates-required.sh`** (→ rename
   `brief-mechanical-hurdles-required.sh`).
3. `review-members` — **drain**, `context = "separate"`, per member routes to
   `mathcity.critical-reviewer` / `mathcity.experiment-reviewer`.
4. `synthesize` — **routes to `mathcity.review-synthesizer`**; fan-in.
   **`[steps.check]` → `brief-shuffle-result-required.sh`**.
5. `promote-or-reject` — `mathcity.dog`; promote to `stack/` (write bead metadata
   `mathcity.brief.stage=stack`) or reject to `.pile/.rejected/`.
   **`[steps.check]` → `brief-manifest-current.sh`**.
6. `release-lock` — `mathcity.dog`; drop `.shuffle.lock`. **Terminal.**

```toml
formula = "math-brief-review"
version = 1
[[steps]]
id = "review-members"
needs = ["run-hurdle-registry"]
[steps.drain]
context = "separate"
formula = "math-brief-review-one"      # per-member reviewer formula
member_access = "exclusive"
metadata = { "gc.run_target" = "mathcity.critical-reviewer" }
[[steps]]
id = "synthesize"
needs = ["review-members"]
metadata = { "gc.run_target" = "mathcity.review-synthesizer" }
[steps.check]
mode = "exec"
path = ".../checks/brief-shuffle-result-required.sh"
```

### C.3 `math-decision-record.formula.toml`

Records the human adjudicator's verdict; single-brief, no drain (one decision per run).

Steps:
1. `present-verdict` — `mathcity.decision-recorder`; capture the human adjudicator's verdict.
2. `record-decision` — `mathcity.decision-recorder`; write `bd decision` +
   `decisions/<slug>/decision.toml`. **`[steps.check]` →
   `decision-record-exists.sh`**.
3. `stamp-bead` — `mathcity.dog`; set `mathcity.brief.decision_outcome/at` on the
   source bead; ring `brief.decided`. **`[steps.check]` →
   `decision-alignment-check.sh`**. **Terminal** (event fan-out to
   `brief-decision-dispatch` + `post-decision-file-or-sendback` orders happens
   downstream, not inside this formula).

### C.4 `math-experiment-dispatch.formula.toml`

Dispatches experiments/tests that carry compute cost. Uses a **drain**
(`context = "separate"`) when a convoy of experiments is dispatched to a rig
(e.g., UPF); `context = "shared"` (single-lane) when the experiments need one
shared worktree.

Steps:
1. `preflight-review` — **routes to `mathcity.experiment-reviewer`** (G2 good-test
   / experiment design). **`[steps.check]` →
   `gate-test-execution-declaration.sh`** (→ `hurdle-test-execution-declaration.sh`).
2. `authorize` — `mathcity.decision-recorder`; require explicit authorization for
   risky/high-cost runs (G14 test-execution-silent). **`[steps.check]` →
   `gate-test-execution-evidence.sh`** (→ `hurdle-test-execution-evidence.sh`).
3. `dispatch` — **drain**, `context = "separate"` (or `shared`), per member routes
   to the compute rig run target (`upf.*`); each member leaves a **breadcrumb**
   (G11).
4. `breadcrumb-and-summarize` — `mathcity.review-synthesizer`; roll up per-member
   evidence. **`[steps.check]` → `brief-breadcrumb-required.sh`**. **Terminal.**

```toml
formula = "math-experiment-dispatch"
version = 1
[[steps]]
id = "preflight-review"
metadata = { "gc.run_target" = "mathcity.experiment-reviewer" }
[steps.check]
mode = "exec"
path = ".../checks/hurdle-test-execution-declaration.sh"
[[steps]]
id = "dispatch"
needs = ["authorize"]
[steps.drain]
context = "separate"
formula = "run-one-experiment"
member_access = "exclusive"
```

**Drain/convoy summary table:**

| Formula | Convoy? | Strategy | Terminal |
|---|---|---|---|
| math-brief-prep | no | single brief → `.pile` | submit-to-pile (no drain) |
| math-brief-review | yes | convoy-step (lock) + inner `separate` drain | release-lock |
| math-decision-record | no | single decision | stamp-bead (events fan out downstream) |
| math-experiment-dispatch | yes | `separate` (or `shared`) drain | breadcrumb-and-summarize |

---

## D. check-latex as a FORMULA (~5 hurdles)

check-latex is already half a formula: `gates/latex-gate.toml` is the formula, and
`skills/check-latex/check-latex.sh` is its evidence engine. The human adjudicator's plan is to
promote it to a first-class `check-latex.formula.toml` with ~5 explicit hurdles,
renamed under the hurdle vocabulary as `latex-hurdle` (per `HURDLES-RENAME-PLAN`
§H). The current formula has effectively 2 hurdles (evidence + hard-gate); the
following expands to five, drawn from what `check-latex.sh` already measures and
the `check-latex` SKILL's "sub-skills composed when present."

### Proposed 5 hurdles

| # | Hurdle | Kind | Backed by | Fail-closed condition |
|---|---|---|---|---|
| H1 | **compiles** | mechanical | `check-latex.sh` compile status | status ∈ {`pass`, `pass-with-undefined-refs`} OR explicit `toolchain-unavailable` (never faked). `fail` blocks. |
| H2 | **labels-and-refs clean** | mechanical | `check-labels-and-refs` sub-skill | no orphan labels/refs, no non-pinpoint cross-refs, `\input`/`\include` closure resolved to depth ≤ 2. |
| H3 | **citations pinpoint + hygienic** | mechanical | `check-citations`/`clean-citations` | every `\cite` resolves; pinpoint (page+atom) policy met; no broken bibtex. |
| H4 | **notation/style clean** | review | `check-latex-style` sub-skill (→ agent) | theorem-env + notation style verdict is clean, or defects enumerated. Judgment → `mathcity.critical-reviewer`. |
| H5 | **the human adjudicator per-diff approval (HARD/STOP)** | stop | `latex-hurdle-approval-required.sh` | covered notes-tier `.tex` diff requires `latex-approval.toml` naming the human adjudicator with `approved_diff_sha` matching `tex.diff` sha; fails closed. N/A only if the diff touches no covered file. |

H1–H3 are mechanical (GC `[steps.check]` gates). H4 is a review hurdle (agent). H5
is the existing STOP hurdle — the one that must never auto-pass. This mirrors the
16-hurdle registry's mechanical/review/stop taxonomy at the check-latex scale.

### Sketch: `formulas/check-latex.formula.toml` (a.k.a. `latex-hurdle`)

```toml
formula = "latex-hurdle"          # renamed from "latex-gate" per HURDLES-RENAME §H
version = 1
[catalog]
name = "latex-hurdle"
description = "Screen a covered notes-tier .tex diff through 5 hurdles; block push/merge until the human adjudicator approves the specific diff."

[vars.tex_file]   # required
[vars.bead_id]    # required — locates evidence dir
[vars.base_ref]   # default HEAD
[vars.evidence_dir]  # default {{env.HOME}}/gt/tmp-for-review/{{bead_id}}
[vars.operator_target]  # default mathcity.dog
[vars.review_target]    # default mathcity.critical-reviewer

# H0/evidence — produce the block (unchanged engine)
[[steps]]
id = "produce-evidence"
metadata = { "gc.run_target" = "{{operator_target}}" }
# invokes skills/check-latex/check-latex.sh ...

# H1 compiles
[[steps]]
id = "hurdle-compiles"
needs = ["produce-evidence"]
[steps.check]
mode = "exec"
path = ".../checks/latex-hurdle-compiles.sh"      # NEW: asserts compile.status != fail

# H2 labels-and-refs
[[steps]]
id = "hurdle-labels-refs"
needs = ["produce-evidence"]
[steps.check]
mode = "exec"
path = ".../checks/latex-hurdle-labels-refs.sh"   # NEW: wraps check-labels-and-refs

# H3 citations
[[steps]]
id = "hurdle-citations"
needs = ["produce-evidence"]
[steps.check]
mode = "exec"
path = ".../checks/latex-hurdle-citations.sh"     # NEW: wraps check-citations

# H4 notation/style — JUDGMENT
[[steps]]
id = "hurdle-style"
needs = ["produce-evidence"]
metadata = { "gc.run_target" = "{{review_target}}" }
# routes to critical-reviewer running check-latex-style; no [steps.check]

# H5 the human adjudicator per-diff approval — STOP
[[steps]]
id = "hurdle-approval"
needs = ["hurdle-compiles","hurdle-labels-refs","hurdle-citations","hurdle-style"]
metadata = { "gc.run_target" = "{{review_target}}", "gc.hurdle.kind" = "stop", "gc.hurdle.blocks" = "auto-dispatch,auto-merge,push" }
[steps.check]
max_attempts = 1
[steps.check.check]
mode = "exec"
path = ".../checks/latex-hurdle-approval-required.sh"   # renamed from latex-gate-approval-required.sh

# disposition
[[steps]]
id = "hurdle-disposition"       # renamed from gate-disposition
needs = ["hurdle-approval"]
metadata = { "gc.run_target" = "{{operator_target}}" }
# stamps G6 LaTeX-hurdle: PASS/N/A/BLOCKED on the brief/bead
```

**New check scripts to write:** `latex-hurdle-compiles.sh`,
`latex-hurdle-labels-refs.sh`, `latex-hurdle-citations.sh` (H1–H3). These read
`check-latex-report.json` from the evidence dir and assert the relevant field —
they do not re-run the analysis, keeping `check-latex.sh` the single evidence
engine. `latex-gate-approval-required.sh` → `latex-hurdle-approval-required.sh`
(rename only). H4 has no script (it is the agent-judgment hurdle).

**Note on H1's degrade path:** `toolchain-unavailable` must PASS H1 (the engine
explicitly refuses to fake a compile); only `fail` blocks. This preserves the
existing "never fake a compile" contract.

---

## E. Expansion plan — 5 sub-domains

Recommendation up front: **keep all five as sub-namespaces within a single
`mathcity` pack, not separate packs.** Rationale: they all feed one brief pipeline,
share the hurdle registry, the artifact_root, and the same review agents. Separate
packs would fork the hurdle registry and duplicate the review agents. The subdomain
boundary is a *directory + run-target namespace* convention (`mathcity.<subdomain>.*`),
not a pack boundary. (Revisit only if one subdomain grows its own independent
lifecycle — see G.)

Directory convention within the pack:
```
mathcity/
  formulas/            # cross-cutting: brief pipeline + check-latex
  agents/              # the 5 judgment agents + codex-worker
  subdomains/
    brief-system/
    computing/
    proof-assist/
    latex/
    lmfdb/
```
Each subdomain dir holds its own `formulas/`, optional `agents/`, `assets/`, and a
`README.md`. Run targets namespace as `mathcity.<subdomain>.<agent>`.

### E.1 brief-system
- **Does:** the decision pipeline itself — the current 17 formulas + 16-hurdle
  registry + orders. This is the *spine*; the other four feed briefs into it.
- **Pack vs sub-namespace:** sub-namespace (it IS the pack core; effectively lives
  at `formulas/` top-level rather than under `subdomains/`).
- **Agents:** all five (§B) — brief-preparer, critical-reviewer,
  experiment-reviewer, decision-recorder, review-synthesizer.
- **Formulas:** the four §C formulas + the existing pipeline formulas
  (shuffle/present/archive/watchdog/dispatch).
- **Integration:** it is the pipeline; everything else produces artifacts that
  enter via `math-brief-prep`.

### E.2 computing
- **Does:** dispatch + track heavy computations (Magma/Sage/PARI runs, UPF rig
  jobs). Wraps `upf-experiment-dispatch` + `test-execution-request`.
- **Pack vs sub-namespace:** sub-namespace `mathcity.computing.*`.
- **Agents:** `mathcity.computing.dispatcher` (decides rig/queue/priority) — or
  reuse `experiment-reviewer` for design + a thin dispatcher run target. Likely
  reuse `experiment-reviewer` + `review-synthesizer`; add one dispatcher.
- **Formulas:** `compute-dispatch` (the drain-based §C.4 specialization),
  `compute-result-collect` (fan-in of rig outputs into a brief).
- **Integration:** experiment/test results become `brief_type = experiment` briefs
  via `math-brief-prep`; breadcrumb hurdle (G11) links artifacts back.

### E.3 proof-assist
- **Does:** Lean/Coq/Isabelle proof checking — the escalation target for prose-math
  correctness that embeddings/reviewers can't settle (cf. `compare-artifacts` skill
  note: "escalate to a build (Lean)"). A build here is a *ground-truth* hurdle.
- **Pack vs sub-namespace:** sub-namespace `mathcity.proof-assist.*`.
- **Agents:** `mathcity.proof-assist.formalizer` (turns a claimed theorem into a
  checkable statement — judgment: what to formalize, how faithfully) +
  `critical-reviewer` for the informal↔formal fidelity check.
- **Formulas:** `proof-check` (mechanical hurdle: the Lean build passes) +
  `formalize-claim` (agent step → build gate).
- **Integration:** a `brief_type = standard` theorem brief can carry a proof-check
  hurdle; a passing Lean build is the strongest possible G4 evidence.

### E.4 latex / literature-search
- **Does:** two coupled things — (a) the check-latex formula (§D) for notes-tier
  `.tex` screening; (b) literature search (arXiv / MathSciNet / citation discovery)
  feeding the citation-hygiene hurdle H3.
- **Pack vs sub-namespace:** sub-namespace `mathcity.latex.*`.
- **Agents:** `mathcity.latex.lit-searcher` (judgment: relevance, which references
  are load-bearing) + `critical-reviewer` for style hurdle H4.
- **Formulas:** `check-latex` / `latex-hurdle` (§D); `lit-search` (find + rank
  candidate references, emit a bibtex candidate set); optionally
  `citation-reconcile` (match cited claims to sources).
- **Integration:** `latex-hurdle` is the runnable form of registry hurdle G6;
  lit-search output feeds H3's bibtex hygiene and can attach to a brief's evidence.

### E.5 lmfdb
- **Does:** query the LMFDB (elliptic curves, modular forms, number fields,
  L-functions) via the `search-lmfdb` skill / `mcp__lmfdb__*` tools; cross-check
  computed data against the database.
- **Pack vs sub-namespace:** sub-namespace `mathcity.lmfdb.*`. (This one is the
  *strongest candidate to eventually split* into its own pack, because it has an
  external MCP dependency and a self-contained query surface — see G.)
- **Agents:** `mathcity.lmfdb.querier` (judgment: translate a math question to the
  right table/join; the LMFDB MCP `overview()`→`describe_table`→`run_sql` workflow
  is genuinely judgment-heavy) — or drive the existing `search-lmfdb` skill from a
  formula step.
- **Formulas:** `lmfdb-verify` (cross-check a computed object against LMFDB; hurdle:
  labels/eigenvalues match), `lmfdb-lookup` (fetch + format for a brief).
- **Integration:** an LMFDB cross-check becomes evidence in a `standard` brief; a
  mismatch is a hard correctness flag surfaced to `critical-reviewer`.

**Subdomain summary:**

| Subdomain | Pack or namespace | New agents | Key formulas | Feeds pipeline via |
|---|---|---|---|---|
| brief-system | core (namespace) | the 5 §B agents | the 4 §C formulas + existing | IS the pipeline |
| computing | namespace | dispatcher (+reuse exp-reviewer) | compute-dispatch, result-collect | experiment briefs + G11 breadcrumb |
| proof-assist | namespace | formalizer (+critical-reviewer) | proof-check, formalize-claim | strong G4 evidence |
| latex | namespace | lit-searcher (+critical-reviewer) | latex-hurdle, lit-search | G6 hurdle + H3 citations |
| lmfdb | namespace (split candidate) | querier | lmfdb-verify, lmfdb-lookup | correctness evidence in standard briefs |

---

## F. Document-model migration path

Fully specified in `BRIEF-DOCUMENT-MODEL-PLAN-2026-07-08.md` (gsp-1pv); summarized
and reconciled with this draft below.

### Where briefs live
**Out of `.beads/briefs/`, into `~/.gc/mathcity/briefs/`** (rig-local, user-home,
never git-tracked, never DoltHub-synced). This cleanly separates the *brief
document* (ephemeral operational input) from the *decision record* (durable output,
which stays in the bead store as a `bd decision`).

```
artifact_root = ~/.gc/mathcity/briefs
  .staging/<slug>/   brief.md, evidence.toml, breadcrumb.toml
  .pile/             <slug>.md
  .pile/.rejected/<slug>/
  stack/             <slug>.md, .index.jsonl   (derived cache, not source of truth)
  archive/<slug>/
  decisions/<slug>/  decision.toml
  .shuffle.lock
kill_switch = ~/.gc/mathcity/ALLOW_NO_BRAINER_AUTO_EXECUTE   (one level up)
```

### Front matter (typed artifact)
Every `brief.md` gains YAML front matter — this is what makes it a GC typed
artifact rather than a loose file:
```yaml
---
schema: mathcity.brief/1
workflow: brief-pipeline
producer: <bead-id or formula-run-id>
status: staging | pile | stack | archive | decided | rejected
trace:
  source: <bead-id | branch | PR | GH-issue>
  brief_type: standard | test-execution | experiment | no-brainer | decision
  slug: <slug>
  created_at: <ISO 8601>
  updated_at: <ISO 8601>
---
```

### Staging/pile/stack/archive → bead metadata
The **source bead is the index** (replaces `stack/manifest.jsonl` as primary). Set
on the source bead at each transition:

| Key | Value |
|---|---|
| `mathcity.brief.slug` | `<slug>` |
| `mathcity.brief.stage` | `staging`/`pile`/`stack`/`archive`/`decided`/`rejected` |
| `mathcity.brief.path` | `~/.gc/mathcity/briefs/stack/<slug>.md` (stack only) |
| `mathcity.brief.type` | brief_type |
| `mathcity.brief.hurdle_profile` | profile name from `hurdles.toml` (was `gate_profile`) |
| `mathcity.brief.decision_at` / `.decision_outcome` | set at decision |

Directory position stops being the status signal; `status` front-matter +
`mathcity.brief.stage` metadata are the two synchronized sources (front matter for
the document, bead metadata for the index/query).

### The shuffle mechanism becomes…
- **Lock:** unchanged semantics, moves to `~/.gc/mathcity/briefs/.shuffle.lock`.
  Still a filesystem mutex; the `math-brief-review` formula (§C.2) is the
  single-writer convoy-step that holds it.
- **manifest.jsonl → bead-metadata query:** `stack/manifest.jsonl` becomes a
  derived `.index.jsonl` cache; the canonical "what's on the stack" is
  `bd list --meta mathcity.brief.stage=stack`. `brief-drain-manifest.sh` shrinks
  to a thin wrapper (or is deleted) around that query.
- **kill switch:** `ALLOW_NO_BRAINER_AUTO_EXECUTE` moves one level up to
  `~/.gc/mathcity/` so a `rm -rf briefs/` cleanup can't silently re-arm automation.

### Migration steps (condensed from gsp-1pv)
1. `mkdir -p ~/.gc/mathcity/briefs/{.staging,.pile/.rejected,stack,archive,decisions}`.
2. For each existing brief: infer stage from dir position, inject front matter,
   copy to new root, set `bd update <bead> --meta mathcity.brief.stage=<stage>`.
   (Write and run `migrate-briefs.sh` — file as a child bead.)
3. Update `assets/brief-pipeline/paths.toml` `[paths]` root + all derived paths.
4. Update every formula's `[vars.artifact_root].default` → `~/.gc/mathcity/briefs`.
5. Update order trigger `check =` conditions (`find $HOME/.gc/mathcity/briefs/.pile
   ...`); consider `scope = "city"` (absolute path resolves identically anywhere).
6. Update check scripts' `.beads/briefs` references; strip hard-coded
   `<home>/` prefixes.
7. `gc lint`, `pytest`, smoke-test one brief through the new root, then delete
   `.beads/briefs/`.

---

## G. Open questions for the human adjudicator

1. **`[imports.gc]` + `[providers.codex]` coexistence.** Does adding
   `[imports.gc]` to `pack.toml` conflict with the existing `[providers.codex]`
   block, or do they compose cleanly? (bmad/gstack have only `[imports.gc]`; no
   reference pack mixes both.) If they don't compose, does codex move to a
   gc-native provider declaration?

2. **`[metadata]` under schema 2.** Will GC reject unknown `[metadata]` keys
   (`subdomains`, `hurdle_registry`, `artifact_root`)? If schema 2 is strict, this
   metadata must live elsewhere (e.g., a `mathcity.toml` sidecar).

3. **Subdomains: namespace vs packs — final call.** This draft recommends one pack
   with `mathcity.<subdomain>.*` namespaces. Do you want lmfdb (external MCP dep)
   and/or proof-assist (external toolchain) split into their own packs now, or
   only when they earn it?

4. **Run-target names.** Are `mathcity.brief-preparer`, `mathcity.critical-reviewer`,
   etc. the run-target scheme you want, or do you prefer role-pool targets
   (`mathcity.mayor`, `mathcity.dog`) with the agent selected by prompt? The
   existing formulas use `gastown.mayor` / `gastown.dog` free-text — should those
   become `mathcity.*` or stay `gastown.*`?

5. **check-latex: exactly which 5 hurdles.** §D proposes {compiles, labels/refs,
   citations, style, human-approval}. Confirm the set. Candidates dropped: a
   *diff-size* hurdle, a *PDF-diff artifact* hurdle (he-ogkp, noted as not-yet-
   folded in the SKILL), an *unfinished-tag* (`\reviewer`/`\todo`) hurdle. Do any of
   these replace one of the five?

6. **`formula = "gate"` in `server-touching-safety-override.toml`.** Per
   `HURDLES-RENAME-PLAN` §"What NOT to Change" #2: is `formula = "gate"` a
   GC-recognized formula kind (leave it) or free-text (rename to `"hurdle"`)? This
   blocks completing the rename cleanly.

7. **`gc.brief.gate_profile` / `gc.brief.hurdle_profile` metadata key.** Is
   `gc.brief.*` a reserved GC step-metadata namespace? If GC reads these keys, the
   rename to `hurdle_profile` must be coordinated with GC; if they're pass-through,
   rename freely.

8. **`review_gate:` front-matter field.** Rename to `review_hurdle:` or keep? It's
   read by `brief-review-patrol`; renaming touches the formula + scripts. (Also:
   the new front-matter `status` field partly overlaps `review_gate` — should
   `review_gate` fold into the typed front matter entirely?)

9. **HOME/`~` expansion in formula `[vars].default`.** Does the formula engine
   expand `~`/`${HOME}` in `default = "~/.gc/mathcity/briefs"`? If not, the
   artifact_root default needs `{{env.HOME}}` templating or an env-var override.

10. **`bd update --meta` for namespaced keys.** Confirm `bd` accepts
    `mathcity.brief.stage=stack` style namespaced metadata keys; if not, choose an
    encoding before the doc-model migration relies on bead-metadata-as-index.

11. **decision-recorder vs on-merge automation.** `math-decision-record` (§C.3)
    ends by ringing `brief.decided`, which fans out to two existing event orders.
    Should the new formula own that fan-out, or stay a thin decision-writer and let
    the orders remain the fan-out layer (current design)? This draft keeps the
    orders as the fan-out layer.
```
