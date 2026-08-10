# bmad and gstack, Explained — and How mathcity Is Analogous (2026-07-08)

*Audience: the human adjudicator, who has never seen bmad or gstack. Written to explain what
these two packs ARE and to draw precise analogies to the mathcity pack, so that
mathcity's redesign as a GC-native domain pack can borrow the right patterns.*

**One caveat up front, because it matters for every analogy below.** bmad and
gstack are *build-methodology* packs: they wrap a software-development lifecycle
(write requirements → plan → decompose → implement → review → ship). mathcity is
a *research decision-routing* pack: it wraps the flow of getting a finished piece
of math work in front of you with evidence attached, then acting on your verdict.
A prior independent review in this same repo
(`mathcity/METHODOLOGY-PACK-VERDICT-2026-07-08.md`) concluded that mathcity
scores **0 of 6** on the structural markers that define a methodology pack — and
that this is correct and intended. So the analogies here are analogies of
*shape and technique*, not of *category*. Where the shape genuinely matches
(agents, gates, artifacts, GC imports), mathcity should copy bmad/gstack.
Where it doesn't (the whole prepare→…→publish spine), forcing the analogy would
be a mistake. The last two sections are about exactly that boundary.

---

## What is bmad? (explained for a mathematician)

**The problem it solves.** Imagine you hand a competent-but-junior assistant a
one-line goal — "add a `--json` flag to the export command" — and you want the
work done *with discipline*: no code written until there's a written spec, an
agreed design, and a checklist of small tasks; every task individually
implemented, self-checked, and audited against its acceptance criteria; and then
the whole thing torn apart by several adversarial reviewers before it's declared
done. bmad automates that disciplined, document-first process end to end. The
analogy for a mathematician: it's like insisting on a full statement of the
theorem and a proof sketch *before* anyone writes a line of the proof, then
proving each lemma separately, then having four different referees attack the
result from four different angles.

**What "BMAD Method" is.** [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD)
is an existing, third-party, document-first software delivery process (an MIT-licensed
open-source methodology — a set of prompts/skills, not GC-native). Its stages are:

1. **PRD** — write a Product Requirements Document (what are we building and why).
2. **Architecture** — design the system before coding.
3. **Epics & Stories** — decompose the architecture into small implementable "stories."
4. **Implementation-readiness gate** — a hard checkpoint: are the stories actually ready to code? If not, block.
5. **Story-by-story implementation** — implement each story, self-check it, audit it against its acceptance criteria, fix.
6. **Adversarial code review** — four parallel reviewer "lanes" (blind-hunter, edge-case, acceptance-audit, gap-analysis), then synthesize and fix.

The bmad *pack* takes that upstream methodology (which it "vendors" — copies in
as reference material under `bmad/vendor/` and `bmad/skills/`) and re-expresses
it as durable Gas City machinery, so every stage is a bead in a graph that Gas
City can retry, observe, pause, and resume.

**In GC terms — formulas, agents, steps.**

- The top-level **formula** is `bmad-build` (`bmad/formulas/bmad-build.formula.toml`).
  It `extends = ["build-base"]` (the shared Gas City lifecycle contract) and
  overrides the meaning of each stage.
- The **stages** (steps) are, in order: `prepare` → `requirements` (=PRD) →
  `plan` (=architecture) → `plan-review` → `decompose` (=epics/stories) →
  `implementation-readiness` (the one pack-added gate) → `implement` (story drain)
  → `review` (the 4-lane adversarial loop) → `finalize` → `publish`.
- Each step names a specialized **agent** to run it, via the metadata key
  `gc.run_target`. bmad ships ten pack-local agents (`bmad/agents/*/`):
  `bmad.prd-writer`, `bmad.architect`, `bmad.epic-story-decomposer`,
  `bmad.readiness-reviewer`, `bmad.story-implementer`, `bmad.story-self-checker`,
  `bmad.acceptance-auditor`, `bmad.blind-hunter-reviewer`, `bmad.edge-case-reviewer`,
  `bmad.bmad-review-synthesizer`.
- Sub-workflows are their own formulas: `bmad-planning`, `bmad-decomposition`,
  `bmad-implementation`, `bmad-review`, `bmad-fix-loop`, plus the per-story
  `bmad-story-development` and the review expansion `bmad-code-review-flow`.

**What a bmad run looks like end to end.**

```sh
gc bd create "Add a --json flag to the export command"
gc sling gc.run-operator <bead-id> --on bmad-build \
  --var artifact_root=plans/json-flag/build \
  --var drain_policy=separate
```

Gas City then walks the stages: the PRD writer produces a requirements doc, the
architect produces an architecture doc and a handoff review, the decomposer
produces epics/stories, the readiness reviewer gates whether coding may begin,
the story drain implements each story in its own git worktree (with self-check +
acceptance audit + fix loop per story), the four review lanes fan out and a
synthesizer folds their findings back into a fix loop until approved, then
finalize writes a summary and publish optionally pushes/opens a PR. All artifacts
land under `artifact_root`. By default it's *interactive* — it halts at BMAD
checkpoints for your input and you can `gc session attach` to answer.

---

## What is gstack? (explained for a mathematician)

**The problem it solves.** Same broad shape as bmad — take a goal, ship reviewed
code — but with a **founder/startup flavor and the strictest pre-ship gating** of
any of these packs. Where bmad's front end is a formal PRD, gstack's front end is
a *YC-office-hours interrogation*: it grills you about demand ("is there real
demand?"), the status quo, exactly who the user is, the narrowest useful wedge,
surprises you observed, and future fit — before it will even plan. And where
bmad stops after code review, gstack adds two extra gates *after* review and
*before* finalize: a **QA** stage (browser-oriented QA + regression-test evidence)
and a **release-readiness** stage (docs, ship readiness, deployment readiness).
Nothing ships without passing both.

**What "garrytan/gstack" is.** [garrytan/gstack](https://github.com/garrytan/gstack)
is a third-party (MIT-licensed) Claude Code skills pack modeling a founder-style
sprint. Its recognizable arc is:

> **Think → Plan → Build → Review → Test → Ship → Reflect**

Its roles — YC Office Hours, CEO/founder review, engineering review, design
review, staff review, QA, CSO security, documentation, release engineering —
hand work to each other. The gstack *pack* turns those roles into providerless
Gas City agents and turns their handoffs into Gas City fanouts.

**In GC terms — formulas, agents, steps.**

- Top-level **formula** `gstack-build` (`gstack/formulas/gstack-build.formula.toml`),
  also `extends = ["build-base"]`.
- **Stages**: `prepare` → `requirements` (office-hours intake) → `plan` (autoplan) →
  `plan-review` (a *fanout*: founder-scope, design, engineering, developer-experience
  lanes) → `decompose` → `implement` (drain) → `review` (fanout: staff, QA-evidence,
  CSO-security, gap-analysis) → **`qa`** (pack-added) → **`release-readiness`**
  (pack-added) → `finalize` → `publish`.
- **Agents** (`gstack/agents/*/`, thirteen of them): `gstack.office-hours`,
  `gstack.founder-reviewer`, `gstack.design-reviewer`, `gstack.eng-reviewer`,
  `gstack.devex-reviewer`, `gstack.decomposer`, `gstack.implementer`,
  `gstack.staff-reviewer`, `gstack.security-officer`, `gstack.qa-lead`,
  `gstack.release-engineer`, `gstack.docs-engineer`, `gstack.review-synthesizer`.
- **Distinctive trait**: gstack defaults *both* `interaction_mode` and
  `review_mode` to `interactive` (bmad only defaults interaction to interactive),
  because raw gstack is intentionally conversation-heavy.

**What a gstack run looks like end to end.**

```sh
gc bd create "Add CSV export to the reports page"
gc sling gc.run-operator <bead-id> --on gstack-build \
  --var artifact_root=plans/csv-export/build \
  --var drain_policy=separate
```

The office-hours agent interrogates you into a requirements doc, autoplan drafts
a plan, the plan-review fanout critiques it from four business/eng perspectives,
the decomposer builds an implementation convoy, the drain implements the work,
the review fanout attacks the code, then the two extra gates (QA, then
release-readiness) must each pass before finalize writes the sprint report and
publish optionally ships.

---

## How bmad/gstack use gascity (the concrete technical pattern)

This is the reusable machinery. Five ingredients:

### 1. `[imports.gc]` — pull in the base pack

Both packs' `pack.toml` is tiny. The entire "how do I get the Gas City lifecycle,
base formulas, and role agents" answer is one import block:

```toml
# bmad/pack.toml  (gstack/pack.toml is identical modulo name)
[pack]
name = "bmad"
version = "0.1.0"
schema = 2

[imports.gc]
source = "../gascity"
```

That import binds the local alias `gc` to the gascity pack. Everything
`gc.*`-namespaced (the `build-base` formula, `gc.run-operator`, `gc.publisher`,
the `gc-role-worker` prompt fragment, the `gc.build.*` artifact schemas) becomes
available transitively. In production the `source` is a git URL; contributors
working locally point it at `../gascity`.

### 2. `extends = ["build-base"]` — inherit the lifecycle, override the steps

The build formula declares it is a *specialization* of the shared contract:

```toml
# bmad/formulas/bmad-build.formula.toml
formula = "bmad-build"
extends = ["build-base"]
target_required = true
```

`build-base` (in the gascity pack) defines the canonical anchor sequence
`prepare → requirements → plan → plan-review → decompose → implement →
review → finalize → publish`. `extends` means: keep that spine, but let me
*override individual steps by id*. bmad re-defines `requirements`, `plan`,
`plan-review`, `decompose`, `implement`, `review` (each keeping its base id, so
nothing is renamed or reordered) and *inserts* exactly one new step,
`implementation-readiness`, between `decompose` and `implement`. gstack does the
same and inserts two new steps (`qa`, `release-readiness`) between `review` and
`finalize`. The compatibility ledgers (`bmad/REQUIREMENTS.md`,
`gstack/REQUIREMENTS.md`) contain a Python proof that the base anchors are
preserved. This is the "extend, don't fork" discipline: you inherit retry,
resume, artifact plumbing, and drain semantics for free.

### 3. `metadata.gc.run_target` — route each step to a specialized agent

Every step names the agent that runs it, inline in step metadata:

```toml
[[steps]]
id = "requirements"
title = "BMAD PRD requirements"
needs = ["prepare"]
metadata = { "gc.run_target" = "bmad.prd-writer", "gc.build.artifact_schema" = "gc.build.requirements.v1", "gc.build.artifact_path_keys" = "gc.build.requirements_path,gc.var.requirements_path" }
description_file = "../assets/workflows/bmad-build/requirements.md"
```

`gc.run_target = "bmad.prd-writer"` says "run this step as the `bmad.prd-writer`
agent." The agent itself is *registered simply by existing on disk* — there is no
central registry file. Its directory `bmad/agents/prd-writer/` contains an
`agent.toml` (barely more than a description) and a `prompt.template.md`:

```toml
# bmad/agents/prd-writer/agent.toml
description = "BMAD PRD requirements writer"
scope = "rig"
fallback = true
```

```markdown
# bmad/agents/prd-writer/prompt.template.md
# BMAD PRD Writer

{{ template "gc-role-worker" . }}

Use the shared `bmad-prd`, `bmad-brainstorming`, and `bmad-spec` skills ...
Do not invoke provider-native subagents, slash commands, task tools, or the
upstream BMAD runtime. ...
```

Note: the agents are **providerless** (no `provider = ...` pin) — they run on
whatever model the run supplies. The name `bmad.prd-writer` is the pack name
(`bmad`) plus the agent directory name (`prd-writer`). The prompt pulls in the
shared `gc-role-worker` fragment (which carries the Gas City claim protocol) via
the `{{ template "gc-role-worker" . }}` include.

### 4. `[steps]` blocks — route the work as a graph

Steps route work three ways. (a) A **plain step** runs one agent (the
`requirements` example above). (b) A **drain** step fans one formula out over many
beads:

```toml
[[steps]]
id = "implement"
title = "Drain BMAD story development"
needs = ["implementation-readiness"]
condition = "{{drain_policy}} == separate"
metadata = { "gc.run_target" = "{{implementation_target}}" }

[steps.drain]
context = "separate"
formula = "bmad-story-development"
member_access = "exclusive"
```

(c) An **expand** step substitutes a whole sub-formula (used for the fanout review
loops):

```toml
[[steps]]
id = "review"
title = "BMAD code review"
needs = ["summarize-implementation"]
metadata = { "gc.run_target" = "bmad.bmad-review-synthesizer", "gc.build.artifact_schema" = "gc.build.review.v1" }
expand = "bmad-code-review-flow"
expand_vars = { implementation_target = "{{implementation_target}}", review_mode = "{{review_mode}}" }
```

`needs = [...]` is the dependency edge that makes this a DAG rather than a script.

### 5. Check scripts attached to steps

A step can carry a `[steps.check]` block whose `[steps.check.check]` runs an
executable gate with a bounded retry count. bmad and gstack both attach the same
shared validator to every artifact-producing step:

```toml
[steps.check]
max_attempts = 3

[steps.check.check]
mode = "exec"
path = ".gc/scripts/checks/build-artifact-valid.sh"
timeout = "5m"
```

That script validates the produced artifact against its declared
`gc.build.*.v1` schema. gstack's `qa` / `release-readiness` gates and bmad's
`implementation-readiness` gate are the *judgment* equivalents — steps whose
agent must emit an approve/iterate verdict before the graph advances.

---

## Analogies to mathcity (the most important section)

Read these as "what plays the same *role* in mathcity," not "these are the same
category of thing." mathcity's pipeline is
`produce → shuffle → present → decide → dispatch → archive`, not
`prepare → … → publish`.

### bmad → mathcity

| bmad concept | mathcity analog | Notes |
|---|---|---|
| `bmad.prd-writer` (writes the spec that starts the process) | `mathcity.brief-prep` skill + the `brief-prep` formula's `draft-brief` step | Both are the *intake authors*: they turn a rough source (a goal / a finished branch or bead) into the structured document the rest of the pipeline consumes. bmad writes a PRD; mathcity writes a brief. |
| `bmad.architect` (reviews the plan before it proceeds) | `mathcity.critical-review` skill (adversarial reviewer) | Both are the "is this good enough to move forward" judgment layer. bmad's plan-review gates the design; critical-review gates the brief/artifact quality. |
| `bmad.readiness-reviewer` + the `implementation-readiness` gate | `mathcity.catch-no-brainer` + the 16-gate registry (`assets/brief-pipeline/gates.toml`) | Both are the *hard checkpoint that decides whether the item may advance*. readiness gates "may we start coding"; the gate registry + no-brainer classifier gate "may this brief be promoted / can it be collapsed to one line." |
| Story implementation drain (`bmad-story-development`, per-story) | `brief-decision-dispatch` formula (acts per decided brief) | Both are the *execution* stage that does the real mutating work per item — bmad implements a story; dispatch reassigns the source bead / creates a follow-up / merges after your verdict. |
| The 4-lane adversarial review + `bmad.bmad-review-synthesizer` | `mathcity.coordinate-review` (create/review loop) + `mathcity.critical-review` | Both are the fan-out-then-synthesize quality loop. bmad runs four reviewer lanes and folds findings; coordinate-review alternates critical-review and revise until convergence. |
| `bmad-build` top-level formula (`extends build-base`) | `brief-prep` + the order-triggered pipeline as a whole | **The analogy breaks here** — see the boundary section. bmad has *one* lifecycle formula; mathcity has a *family of order-driven handlers* with no single spine. |
| `gc.run_target = "bmad.prd-writer"` step routing | `gc.run_target = "{{review_target}}"` / `"{{prep_target}}"` in `brief-prep.toml` | Identical mechanism. mathcity already routes steps to run targets exactly like bmad — it just routes to `gastown.mayor` / `gastown.dog` roles rather than pack-local `mathcity.*` agents. |

### gstack → mathcity

| gstack concept | mathcity analog | Notes |
|---|---|---|
| `gstack.office-hours` intake (interrogate into requirements) | brief creation via `grill-and-present` / `brief-prep` | Both *grill the source into a decision-ready document by asking pointed questions*. gstack grills demand/wedge/user; mathcity's `grill-and-present` grills ambiguity in the artifact. This is the closest single analogy in either pack. |
| `plan-review` fanout (founder/design/eng/devex lanes) | `critical-review` / `coordinate-review` step | Both are the multi-perspective critique before proceeding. gstack fans out four business lanes; mathcity uses an adversarial reviewer converging to APPROVING. |
| `gstack.qa-lead` QA-review gate (evidence before ship) | `is-good-test` / `is-good-experiment` skills + the test/experiment gates | Both are the *empirical-evidence gate*: "show me it actually works." gstack demands browser QA + regression output; mathcity demands a well-designed test/experiment before compute is spent (`test-execution-request`, `upf-experiment-dispatch`). |
| `release-readiness` gate (docs/ship/deploy readiness) | `brief-record-decision` + the stop/manual gates in the registry | Both are the *final human-authorization checkpoint before the irreversible action*. release-readiness blocks finalize; mathcity's stop gates fail closed unless human authorization is recorded, and `record-decision` writes the `bd decision`. |
| `gstack.decomposer` → implementation convoy | `brief-shuffle` (pile → stack promotion) + `brief-present-next` (stack drain) | Loosely: both turn a batch into an ordered, singly-processed queue. gstack decomposes into a convoy of work items; mathcity shuffles briefs one-at-a-time into a stack and drains them for presentation. |
| gstack default `interaction_mode = interactive` (conversation-heavy) | mathcity's whole posture: nothing auto-merges; every brief goes to you | Both are *deliberately human-in-the-loop*. gstack asks questions during the run; mathcity's entire reason to exist is to put a human decision point in the middle. |

---

## What mathcity should copy directly from bmad/gstack

Concrete, path-level list. These are the patterns where the shape genuinely
matches, so copying is safe and idiomatic.

1. **Add the `[imports.gc]` block to `mathcity/pack.toml`.**
   - Copy from: `bmad/pack.toml` lines 6–7 (`[imports.gc]` / `source = "../gascity"`).
   - Why: mathcity's formulas already call `gc`-namespaced skills and `gc bd`,
     but `mathcity/pack.toml` has *no imports block at all* (only
     `[providers.codex]`). The verdict doc flags this as the one real convention
     drift. Adding the import makes the dependency explicit and lets mathcity
     resolve `gc.*` primitives cleanly. Change: point `source` at `../gascity`
     (local) or the git URL (published).

2. **Convert mathcity's brief-pipeline roles into pack-local `mathcity.*` agents.**
   - Copy from: the `bmad/agents/<name>/` layout — `agent.toml` (description +
     `scope` + `fallback`, no provider pin) plus `prompt.template.md` that opens
     with `{{ template "gc-role-worker" . }}`.
   - Why: mathcity currently routes steps to generic roles (`gastown.mayor`,
     `gastown.dog`) via string vars. bmad/gstack instead ship *named, specialized,
     providerless* agents (`bmad.prd-writer`, `gstack.qa-lead`). mathcity has clear
     candidates that deserve first-class agents: a `mathcity.brief-preparer`, a
     `mathcity.critical-reviewer`, an `mathcity.experiment-reviewer`. This makes
     the routing self-documenting and lets each role carry its own prompt +
     skill list.
   - Adapt, don't copy verbatim: mathcity DOES want a provider pin in at least
     one case — its existing `codex-worker` agent (`agents/codex-worker/agent.toml`)
     legitimately sets `provider = "codex"` for cross-model review. Keep that
     pattern for the codex role; use the providerless pattern for the rest.

3. **Copy the shared prompt-fragment discipline.**
   - Copy from: `bmad/template-fragments/gc-role-worker.template.md` and the
     `{{ template "gc-role-worker" . }}` include in every agent prompt.
   - Why: it standardizes the claim/worker protocol across all agents. mathcity
     already has a `template-fragments/` dir; wire every new `mathcity.*` agent to
     it the way bmad does.

4. **Copy the check-script-on-step pattern for gates that are mechanical.**
   - Copy from: the `[steps.check]` / `[steps.check.check]` block in
     `bmad-build.formula.toml` (the `build-artifact-valid.sh` gate).
   - Why: mathcity's 16-gate registry already splits mechanical vs review vs
     stop vs manual. The *mechanical* gates should attach to formula steps as
     `mode = "exec"` checks exactly like bmad's artifact validator, rather than
     living only in a separate registry — this is the idiomatic GC way to make a
     deterministic gate block advancement with bounded retries.

5. **Copy gstack's "extra gate inserted before the terminal step" pattern —
   *conceptually*, for the evidence gates.**
   - Copy from: gstack's `qa` and `release-readiness` steps, each `needs` the
     prior and rewires `finalize` to `needs` them.
   - Why/adapt: mathcity's `is-good-test` / `is-good-experiment` and its
     stop-gates play the same "block the irreversible action until evidence +
     authorization exist" role. If any mathcity formula ever grows a linear
     spine, model those gates as gstack-style inserted steps. (If it stays
     order-driven, keep them as gate-registry entries — see boundary section.)

6. **Copy the compatibility-ledger habit.**
   - Copy from: `bmad/REQUIREMENTS.md` / `gstack/REQUIREMENTS.md` structure
     (claims + evidence commands + a machine-checkable proof).
   - Why: mathcity's verdict doc recommends *declaring the pack's kind*. A
     mathcity `REQUIREMENTS.md` should assert the *domain-automation* contract it
     actually satisfies (idempotent order handlers, fail-closed gates, single-writer
     shuffle discipline, `gc bd` for state) with reproducing commands — the
     mirror image of bmad's methodology ledger.

---

## What makes mathcity different from both (where the analogy breaks)

**bmad and gstack are software-development methodologies; mathcity is a research
decision-routing workflow.** The break is structural, not cosmetic:

- **No prepare→…→publish spine.** bmad/gstack both `extends = ["build-base"]` and
  live or die by preserving that anchor sequence. mathcity has *zero* formulas
  that extend build-base and *zero* `gc.build.*` artifact schemas. Its formulas
  are order-triggered, idempotent, ledger-driven *event handlers*
  (`brief-decision-dispatch` is a ~300-line embedded bash reconciler with
  retry/terminalization), not lifecycle stages. Forcing a build-base spine onto
  it would misrepresent the pack — the verdict doc says explicitly: *do not add
  build-base steps, `gc.build.*` schemas, or a `[metadata.gc.methodology]` block.*

- **The human decision is the product, not a side effect.** In bmad/gstack the
  human is an optional checkpoint (`interaction_mode` can be `headless`). In
  mathcity, getting a decision *out of you* with evidence attached is the entire
  point; the pipeline's terminal act is `bd decision`, not a merged PR. There is
  no "autonomous, no human" mode that makes sense.

- **Genuinely unique to math research, no software analog:**
  - **Cost-gated compute.** `upf-experiment-dispatch` and `test-execution-request`
    gate *running an experiment on real compute* because compute is expensive and
    the result may be undecidable in advance. Software builds have nothing like a
    "should we even spend the cycles to find out?" gate — a test either passes or
    fails cheaply.
  - **The no-brainer / gate-review feedback loop.** mathcity classifies your
    approvals as "no-brainers" and, every 10 of them, *reviews its own gate
    process* to auto-catch that class next time. This is a self-tuning
    attention-economizer with no methodology-pack counterpart; bmad/gstack gates
    are static.
  - **Adjudication over undecidable-in-advance artifacts.** A brief can be about
    a conjecture, a computed table, or an experiment whose "correctness" is a
    matter of mathematical judgment, not a passing test suite. The pipeline routes
    to *human mathematical judgment* as a first-class terminal, whereas bmad/gstack
    always terminate in mechanically-checkable "reviewed code."

- **Where it must go its own way:** the ordering primitive. mathcity's backbone
  is the **order system** (event / condition / cooldown / manual triggers,
  `scope`, `pool`) and a **gate registry**, not a formula DAG with a fixed spine.
  That is the correct primitive for "react to work finishing and route it," and
  it has no bmad/gstack analog because those packs are *launched at a goal* and
  run to completion, whereas mathcity is *ambient* — always listening for
  `bead.closed`, `brief.decided`, pile-non-empty, etc.

---

## the human adjudicator's starting-point recommendation

**Start from gstack, not bmad — but borrow the *packaging mechanics* from either.**

gstack is the closer model for two reasons that matter to mathcity specifically:

1. **It is unapologetically human-in-the-loop.** gstack defaults *both*
   interaction and review to `interactive` because it's conversation-heavy — the
   same posture as mathcity, where a human verdict is the product. bmad defaults
   to interactive too but treats it as one axis among several; gstack treats
   conversation as the point.

2. **Its "grill the source into a document" intake (`gstack.office-hours`) is the
   single closest existing analog to mathcity's `grill-and-present` / `brief-prep`
   front end.** If you want to see how a GC-native pack turns "interrogate a rough
   input into a structured, evidence-bearing artifact" into agents + prompts +
   steps, `gstack/agents/office-hours/` is the file to read first.

**Concrete first files to open, in order:**

1. `gstack/pack.toml` and `bmad/pack.toml` — see how tiny a GC-native pack's
   manifest is, and copy the `[imports.gc]` block into `mathcity/pack.toml`.
2. `gstack/agents/office-hours/agent.toml` + `prompt.template.md` — the template
   for turning a mathcity brief-pipeline role into a first-class `mathcity.*`
   agent (providerless, `gc-role-worker` fragment, skill list, "no upstream
   runtime" guard).
3. `bmad/agents/prd-writer/` — a second, minimal agent example to confirm the
   pattern generalizes.
4. `bmad/formulas/bmad-build.formula.toml` — read *only* to learn the
   `gc.run_target`, `[steps.check]`, `needs`, `drain`, and `expand` mechanics.
   Do **not** copy its build-base spine; mathcity's formulas stay order-driven.
5. `bmad/REQUIREMENTS.md` — as the template for a mathcity `REQUIREMENTS.md`
   that *declares mathcity's kind* (domain-automation) with reproducing evidence,
   which is the verdict doc's #1 recommended fix.

**In one sentence:** copy gstack/bmad's *packaging* (the `[imports.gc]` block,
the providerless `pack.foo` agents, the `gc.run_target` routing, the
check-on-step gates, the compatibility ledger) — but keep mathcity's
*architecture* (order-driven handlers + gate registry + human-decision terminal),
because mathcity is a domain-automation pack, not a build-methodology pack, and
the prior verdict is right that it should stay that way.
