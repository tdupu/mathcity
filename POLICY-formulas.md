# Formula Policy

Parent: [README.md](./README.md)

| Field | Value |
|---|---|
| Version | 1.5 |
| Status | Draft |
| Date | 2026-07-24 |
| Prefix | F |
| Subordinate to | `mathcity/subdomains/dev/POLICY.md` |
| Applies to | All formula TOMLs in every mathcity pack (mathcity/ and all subdomains) |
| Enforced by | `check-formula-hygiene` |
| Amended by | `new-formula-policy` |

Governs the authorship and runtime behavior of gascity formula TOMLs in the
mathcity pack family. Every new formula and every formula-creation skill must
pass all F-rules before human adjudication.

---

## Pillar 1 — Agent-tier separation

*Planning belongs to high-tier agents. Execution belongs to low-tier agents.
Neither substitutes for the other.*

**F1.1 — Planning steps must route to high-tier named sessions.**
Any formula step whose purpose is planning, design, requirements gathering,
or architectural judgment must set `gc.run_target` to a high-tier fleet
address (`gc.design-author`, `gc.review-synthesizer`,
`gc.requirements-planner`, or equivalent Opus-class session).

Pass: all planning-role steps have `metadata = { "gc.run_target" = "<high-tier-address>" }`.
Fail: a planning step routes to `gc.run-operator`, `gc.implementation-worker`,
or any execution-tier address.

**F1.2 — Execution steps must route to execution-tier named sessions.**
Steps that run shell commands, write files, execute deterministic operations,
or implement a plan already specified in prior steps must route to
`gc.run-operator`, `gc.implementation-worker`, or a functionally equivalent
low-tier named session.

Pass: execution-role steps have a low-tier `gc.run_target`.
Fail: a deterministic execution step routes to a high-tier session when a
low-tier one would do (wastes Opus quota unnecessarily).

**F1.3 — `gc.run_target` must be a named session fleet address, never a model name.**
Values like `"fable"`, `"opus"`, `"sonnet"`, `"haiku"` are model names, not
fleet addresses. Gascity resolves `gc.run_target` by looking up a registered
named session; model names have no registry entry and produce a runtime error
("unknown formulas v2 target 'fable'").

Pass: every `gc.run_target` value in every step is a dot-namespaced fleet
address (e.g., `gc.run-operator`, `gc.design-author`,
`mathcity.brief-operator`).
Fail: any step (or any `[vars]` default / enum entry) contains a bare model
name as a `gc.run_target` candidate.

Note: the policy `fable-plans-haiku-executes` (bd memory) describes how
named sessions are *internally configured* — it does NOT permit passing model
names as `gc.run_target` values. F1.3 makes this explicit.

---

## Pillar 2 — Clean-up discipline

*Formulas must not leave slop. Every artifact a formula creates must have a
declared owner and a declared teardown.*

**F2.1 — Temp files must be cleaned up within the formula.**
A formula that writes to `/tmp/`, `$TMPDIR`, or any other transient path
must either (a) clean up those paths in its terminal step, or (b) explicitly
document in the step description that the agent is responsible for removing
the path after use, with the exact `rm` command shown.

Pass: terminal step or a dedicated `teardown` step removes every `/tmp/<x>`
path created earlier.
Fail: formula writes to `/tmp/<x>` and no step removes it.

**F2.2 — Cloned repositories must be scoped and bounded.**
A formula that clones an external repository must (a) use a temp path with a
predictable name, (b) document the path in the step description, and (c)
clean up the clone in the terminal step or document an explicit handoff to a
named artifact owner.

Pass: clone path documented; cleanup or handoff instruction present in terminal step.
Fail: formula clones a repo to an undocumented or unbounded path with no teardown.

**F2.3 — Shared paths must not be silently modified.**
A formula must not silently modify files under `<city-root>/`, `<repos-root>/`, or other
shared workspace paths as a side-effect of a step. Side-effects on shared
paths must be declared in the step `title` and `description`, approved in the
decision brief, and cleaned up or committed in the same step.

Pass: every shared-path modification is declared and gated by a brief step.
Fail: a formula step modifies a shared path without declaration in the title
or description.

---

## Pillar 3 — Policy conformance

*Formulas that create other formulas must check all applicable policies.
Formula-creation skills must reference this document.*

**F3.1 — Formula creation must include a policy-conformance check.**
Any formula whose output is another formula TOML (e.g., `formula-creator-math`)
must include a step that audits the draft TOML against `POLICY-formulas.md`
and any other applicable domain policies (beads, skills, hygiene) before
filing a decision brief. The check must be explicit — not implied by a
generic "validate" step.

Pass: formula has a step (or a sub-task within the validate step) that reads
`mathcity/POLICY-formulas.md` and reports PASS/FAIL for each F-rule against
the draft TOML.
Fail: no policy check step, or the check reads only syntax/catalog fields
without covering F-rules.

**F3.2 — Formula-creation skills must reference POLICY-formulas.md.**
Any skill that creates or authors formula TOMLs (e.g., `formula-creator`,
`formula-creator-math`, `formula-work`) must include a reference to
`mathcity/POLICY-formulas.md` in its procedure, directing agents to read the
policy before authoring steps and vars.

Pass: SKILL.md or the formula description section references
`POLICY-formulas.md` with an explicit read instruction.
Fail: the skill creates formula TOMLs without directing the agent to read
POLICY-formulas.md.

**F3.3 — Vars with `gc.run_target`-bound defaults must pass F1.3.**
Any `[vars]` block whose `default` or `enum` values will be interpolated into
`metadata = { "gc.run_target" = "{{var}}" }` must contain only valid fleet
addresses in both `default` and `enum`. A `[vars]` block with model names in
its enum is an F1.3 violation even if no step is using it yet.

Pass: every `[vars.x]` block with a gc.run_target-bound variable has only
fleet addresses as default and enum values.
Fail: enum or default contains `"fable"`, `"opus"`, `"sonnet"`, or `"haiku"`.

---

## Pillar 4 — Pre-brief quality gates

*Every formula must confirm the work is genuinely new and passes basic
correctness gates before the human adjudicator sees it. Reinventions and zero-state failures
must not reach the brief stack.*

**F4.1 — `/check-zero` and `/check-wheel` required before terminal brief.**
Before filing the terminal brief (`file-brief`, `brief-finalize`, or
`workflow-finalize`), every formula must include a step that runs `/check-zero`
(resource survey across all layers) and `/check-wheel` (wheel-reinvention
gate) against the formula's deliverable. The terminal brief step is
conditioned on both returning `NO REINVENTION`, or on a documented exception
recorded in the brief body.

Pass: the validate step or a dedicated pre-brief step explicitly invokes
`/check-zero` and `/check-wheel` against the deliverable; the brief artifact
includes their verdicts.
Fail: the terminal brief step fires without a prior `/check-zero` +
`/check-wheel` run, or their verdicts do not appear in the brief.

Rationale: prevents work that reinvents an existing resource from reaching
the human adjudicator's review queue. The human adjudicator should adjudicate genuinely new work, not
duplicates of what already exists. `check-zero` + `check-wheel` is the single
"is this genuinely new?" gate before the human sees the result.

---

## Pillar 5 — Pre-dispatch review gates

*Coordination and adversarial review happen before dispatch, not after.
A formula whose plan or design has not passed critical review must not
be slung to the fleet.*

**F5.1 — Coordinated review and critical review required before dispatch.**
Before a formula is dispatched (`gc sling` or equivalent), it must pass
a coordinated review via `/fp-finder` (or `/coordinate-review`) AND
`/critical-review`. Both gates must return a passing verdict. A formula
that has not cleared both gates, or that received a FAIL verdict, must not
be slung.

Pass: the dispatch decision brief includes passing verdicts from
`/fp-finder` (or `/coordinate-review`) and `/critical-review`.
Fail: formula is slung without documented passing verdicts from both gates,
or a FAIL verdict was overridden without a human APPROVE exception recorded
in the brief.

Rationale: coordination and adversarial review before dispatch catch
false-positive designs, integration conflicts, and critical flaws before
they consume fleet resources. Reviews after the sling are too late to
prevent wasted work.

**F5.2 — Formula plan must pass critical review before execution begins.**
The plan produced within a formula's planning step must pass `/critical-review`
before any execution steps begin. A formula whose plan has not been critically
reviewed must not proceed past the planning step into implementation or
execution steps.

Pass: a `/critical-review` step explicitly follows the planning step (or is
embedded as a sub-task within it); execution steps declare
`needs = ["critical-review"]` or equivalent ordering.
Fail: execution steps begin without a `/critical-review` of the plan, or
the planning step has no downstream critical-review gate before the first
execution step.

Rationale: a plan that has not been adversarially reviewed can silently
embed wrong assumptions. Catching plan errors before execution prevents
expensive downstream rework.

---

## Pillar 6 — Testing discipline

*Every formula must have at least one test. Tests start basic and grow;
the smoke test is the non-negotiable minimum.*

**F6.1 — New formulas require a basic smoke test before dispatch.**
Every new formula must be accompanied by at least one smoke test before it
is considered deployable. The smoke test must exercise the formula's minimal
happy path — can it be invoked with valid vars and reach the terminal step
without error? It does not need to verify mathematical correctness. Tests
grow over time; the smoke test is the minimum bar, not the ceiling.

Pass: a smoke test file exists for the formula in `mathcity/tests/` or a
co-located `tests/` directory; the file is documented (path noted) in the
brief; the test has been run and passed before the brief is filed.
Fail: a new formula is briefed or dispatched with no associated smoke test,
OR a test file exists but has never been run and its result is not recorded
in the brief.

Rationale: a formula with no test has no evidence it works. Requiring only
a minimal smoke test — not a full correctness proof — keeps the compliance
bar low while establishing a test surface that can grow incrementally. This
prevents "tests later" from becoming never.

---

## Pillar 7 — Dispatch idempotency

*Dispatching the same work twice must be a no-op. Competing dispatch attempts
must resolve gracefully, not race. The city detects and aborts duplicate
dispatch rather than accumulating redundant workers.*

**F7.1 — Pre-dispatch assignee check required before any `gc sling`.**
Before a formula step (or any dispatching agent) executes a `gc sling` or
equivalent dispatch, it must verify the target bead has no active, non-stale
assignee. The check: `bd show <bead_id>` must show an empty Assignee field OR
a stale claim (per `mathcity/gates/stale-claim.toml` criteria: lease expired
OR heartbeat older than `STALE_CLAIM_WINDOW_SECONDS`, default 3600s).
If the bead has an active non-stale Assignee, the dispatch step must:
(a) emit a visible signal ("ALREADY DISPATCHED — bead `<id>` has active
    assignee `<agent>`; aborting duplicate sling"), and
(b) exit cleanly without launching a competing workflow.
Staleness determination is delegated to the existing stale-claim gate; the
dispatch step calls it and respects its exit code.

Pass: every dispatch step invokes a pre-sling bead-state check; exit code
from the assignee check gates whether the sling proceeds; abort path emits a
visible signal per P6.1.
Fail: a formula dispatch step slings a bead without checking for an active
existing assignee, enabling competing workers on the same bead; or the
dispatch step swallows a "bead already assigned" condition and proceeds
silently.

Note: this rule operates at the formula and dispatch-skill level. Substrate-
level serialization (`bd update --claim` atomicity) is NOT a substitute —
it provides last-resort recovery for races that get past this gate; it does
not prevent the Mayor from launching a second sling in the first place.

**F7.2 — Formula steps that create beads must prevent logical duplicates.**
A formula step whose purpose is to create a new bead (work item, convoy
member, or derivative bead) must search for an existing bead covering the
same work before creating. Minimum check: `bd search <keywords>` for a title
match with status ≠ closed. If a live match is found, the step must surface
the conflict (visible signal or return value to the Mayor) and exit without
creating a duplicate bead. The check is required even when the bead ID is
generated deterministically — deterministic IDs do not prevent logical
duplicates across sessions or rigs.

Pass: bead-creating steps include a prior-bead search; conflicts are surfaced
to the Mayor; no duplicate beads are created for the same logical work unit.
Fail: a formula creates a new bead for work that an open bead already tracks,
without surfacing the match to the Mayor.

---

## Pillar 8 — Briefed terminal discipline

*Every `-briefed` formula exists to route work through a human decision
brief. Its final step must be part of the brief cycle — never a bare
implementation, push, or merge step. The brief IS the gate before anything
is merged or published.*

**F8.1 — Every `-briefed` formula must terminate in the brief cycle.**
A formula whose name ends in `-briefed` must have a terminal step that either
(a) files or produces a decision brief, or (b) is a router step that delegates
to another `-briefed` formula. The allowed terminal step ids are:

| Terminal step id | Meaning |
|---|---|
| `file-brief` | Files a decision brief to the brief stack for adjudication |
| `brief-finalize` | Post-file finalization record + drain |
| `workflow-finalize` | Combined brief-file + drain (1–3 step formulas) |
| `publish` | `build-basic-briefed`'s decision-brief terminal slot |
| `route` | Router terminal that delegates to a `-briefed` formula (e.g. `work-briefed`) |

Pass: the last step's `id` is in the allowed set above.
Fail: a `-briefed` formula's terminal step is a bare implementation step
(`git-push`, `run-script`, `commit`, `implement`, or any step that merges or
publishes without a brief gate).

Enforced by: `formula-creator-math` Step 5 hygiene gate (which carries the
same allowed set) and `check-formula-hygiene`. When the allowed set changes,
amend BOTH this rule and the `formula-creator-math` gate in the same commit so
they never drift.

Rationale: the `-briefed` suffix is a promise that the formula ends at a
human decision gate. A briefed formula that ends in a raw push or merge
silently bypasses adjudication — the exact failure the brief pipeline exists
to prevent.

---

## Change Log

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-07-23 | Initial draft — three pillars (F1–F3), six rules (F1.1–F1.3, F2.1–F2.3, F3.1–F3.3). Prefix F registered. The human adjudicator directive (Mayor session Q27). |
| 1.1 | 2026-07-23 | Add F4.1 — /check-zero + /check-wheel required before terminal brief (Pillar 4: Pre-brief quality gates). The human adjudicator directive (Mayor session Q27). |
| 1.2 | 2026-07-23 | Add F5.1 + F5.2 — Pillar 5 pre-dispatch review gates (/fp-finder or /coordinate-review + /critical-review before sling; /critical-review on plan before execution). The human adjudicator directive (Mayor session Q27). |
| 1.3 | 2026-07-23 | Add F6.1 — Pillar 6 testing discipline: new formulas require a basic smoke test before dispatch. The human adjudicator directive (Mayor session Q27). |
| 1.4 | 2026-07-23 | Add F7.1 + F7.2 — Pillar 7 dispatch idempotency: pre-sling assignee check required; bead-creating steps must prevent logical duplicates. The human adjudicator directive (Mayor session Q27). |
| 1.5 | 2026-07-24 | Add F8.1 — Pillar 8 briefed terminal discipline: every `-briefed` formula must terminate in the brief cycle (allowed terminals: file-brief, brief-finalize, workflow-finalize, publish, route). Reconciles the stale formula-creator-math allowed-set (adds publish + route). The human adjudicator directive. |
