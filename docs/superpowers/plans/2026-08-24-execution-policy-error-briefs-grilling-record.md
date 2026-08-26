# Execution Policy and Error Briefs Grilling Record

Parent: [Master Formula Rework Exploratory Handoff](./2026-08-24-master-formula-rework-exploratory-handoff.md)

Date: 2026-08-24

Status: recorded design conversation, not an implementation plan.

This file preserves the questions and decisions from the grilling session about
`commission-work-briefed`, composed work formulas, dispatch programs, execution
policy, error attribution, and error briefs. The next implementation plan should
use this as source material rather than trying to reconstruct the conversation
from the chat transcript.

## Source Baseline

These points came from checking the source and are the foundation for the design.

- `work-briefed` is the current live router. It classifies source work into
  `COMMISSION`, `SIMPLE_CONTINUE`, `FULL_CONTINUE`, or `EXPLICIT_CONTINUE`, then
  slings a child formula. It delegates work rather than implementing the work
  itself.
- `commission-work-briefed` currently designs a dispatch graph and files an
  approval brief. It does not execute the designed work before approval.
- `brief-decision-dispatch` executes approved `commission-dispatch.v1`
  continuations. The current continuation contract is a single `gc_sling`
  action against one formula, with vars.
- Formula cook behavior is not general runtime programming in the way a normal
  interpreter is. Formula v2 conditions are evaluated at cook time, bounded loops
  expand at cook time, and `loop until` is recorded but not consumed by the
  current runtime as a repeated loop.
- `gc formula cook --attach` is the late-bound append primitive, but attaching
  work to the currently executing bead can deadlock closure. The safer pattern is
  to attach generated work to a stable root or control bead, with explicit bounds.
- `gc sling --on <formula>` is the current way a formula is started on a bead.
- `GC_BEAD_ID` is available to formula workers as the current bead id.
- Molecule closure is currently unreliable enough that finishing policy cannot
  depend only on root closure as proof of success.
- The lost-bead conservation rule says work may be closed, deferred, superseded,
  reslung, or held, but it cannot silently disappear.

## Original Questions To Preserve

| # | Question | Recorded Answer Or Decision |
|---|---|---|
| 1 | In the design phase of `commission-work-briefed`, can formulas act like programs that compose smaller formulas? | Partly, but the current formula runtime is not a full interpreter. Composition exists through cooking, attaching, slinging, and dispatching formulas, but current `commission-work-briefed` only emits a simple continuation contract. |
| 2 | In a loop like `x = 0; while x <= 10; x = x + 1; return x`, can one cooked formula call another and append it to the molecule? | A bounded cook-time expansion can be represented, and a worker can call `gc formula cook --attach`, but unbounded runtime looping is not currently first-class in formula TOML. |
| 3 | When a bead asks to cook or apply a formula, how does the result get connected to the original bead? | Cooking alone produces a workflow artifact. To execute it, the result must be attached and/or slung so the scheduler can claim and run the produced beads. |
| 4 | What happens if there are more steps between the current bead and the next generated bead? | The current bead must finish its own step sequence. Generated child work should be attached to a stable parent/control bead or slung as a child. If attached to itself in a blocking way, closure can deadlock. |
| 5 | Can a Collatz-style workflow be represented without `formula-creator-math`? | As a theoretical toy example, yes, using a bounded or self-composing formula pattern. As a live Gas City formula, it must respect current cook/attach/sling semantics and avoid pretending `loop until` is active runtime recursion. |
| 6 | Can a string-building example mutate a bead description from `hello` to `helloworld` and write `hw.txt`? | As a toy example, yes. In live Gas City, it would need explicit bead updates and a final file-writing step, with clear attachment/execution semantics. |
| 7 | Is `commission-work-briefed` good enough to replace `work-briefed`? | No, not yet. `work-briefed` is live-proven as the router. `commission-work-briefed` is a promising design/approval path but needs stronger program representation, execution policy, error handling, and feedback loops before becoming the default for more routes. |
| 8 | Do all formula types need to be available by default? | Yes, the design should expose the needed route types by default, but not by naively routing everything through unproven commissioned execution. |
| 9 | What are `drain` and `on_complete`? Can `on_complete` file a brief? | They are fan-out/completion concepts for downstream continuation. The desired design is that completion can trigger a brief through a finishing policy, but that needs typed support rather than hand-waving. |
| 10 | Should the middle step classify the requested program shape? | Yes. `commission-work-briefed` should classify whether a request is a direct formula call, a bounded composition, a generated dispatch program, a recursive/revision path, or something requiring human design. |

## Prime And Composite Formula Decisions

| # | Question | Recorded Answer Or Decision |
|---|---|---|
| 11 | Which formulas are compositions and which are prime? | The status inventory showed many formulas are composites, including build, review, superpowers, issue-fix, and router formulas. Prime means no dependency on another formula in the same catalog. The exact inventory should be regenerated before implementation because the catalog changes. |
| 12 | Should commissioned design compose from the prime formulas? | Yes, conceptually. Prime formulas are the base cases for inductive composition. |
| 13 | Should every prime formula be exposed to generated programs? | No. Use a curated capability palette. Some prime formulas are internal, unsafe, too low-level, or not intended as public building blocks. |
| 14 | Should finishing policy be separate from design? | Yes. A dispatch program should have design, activation/execution policy, finishing policy, and revision policy as distinct concerns. |
| 15 | What is the smallest executable artifact? | The smallest practical executable artifact may be a brief. A design can end by producing a brief rather than directly modifying source work. |

## Revision Decisions

| # | Question | Recorded Answer Or Decision |
|---|---|---|
| 16 | Should revise adjudication take a program back to the drawing board? | Yes. Revision should transform an existing artifact using adjudication feedback rather than rebuilding from nothing. |
| 17 | Is revision only for dispatch programs? | No. The operator is more general: `Revise(artifact_v0, adjudication) -> artifact_v1`. The artifact may be a dispatch program, formula, brief, Python script, order, or other generated object. |
| 18 | Should revisions produce patches or full replacements? | Full replacement with lineage is acceptable. The brief should be diff-first, but the revised artifact should be complete and self-contained. |
| 19 | Should callable inventory changes be treated as material revision changes? | Yes. Adding, removing, or changing callable formulas/scripts/orders must be highlighted in a revision diff. |
| 20 | Should activation policy, finishing policy, hold/release behavior, recommendation/effect plan, source binding, and resolution basis changes be material? | Yes. These all change what will execute, what will be considered success, or what the user is approving. |
| 21 | Should there be mctl support for revision diffs? | Yes. Add `mctl programs diff` and `mctl programs validate-revision`, with MCP equivalents. |

## Error Attribution Decisions

| # | Question | Recorded Answer Or Decision |
|---|---|---|
| 22 | In large compositions, how do we know which part caused an error? | Each composed call needs a typed call identity and provenance chain: program id/version, call id, parent call id, caller formula/step, callee subject and hash, input bead, runtime vars, and output root. |
| 23 | What error classes should exist? | At least `compile_error`, `instantiation_error`, `runtime_error`, and `semantic_error`. |
| 24 | Should existing formulas also declare errors? | Yes, gradually. Existing formulas should first participate through normalized runtime errors, then add declared `[[errors]]` sections over time. |
| 25 | How should errors appear to Taylor? | Blocking/terminal errors should produce an error brief. Warnings should be visible through lightweight surfaces such as `mctl`, dashboard, and event logs without forcing every warning into adjudication. |
| 26 | Do errors need to be visible without the dashboard? | Yes. `mctl` should expose them directly. |
| 27 | Should errors automatically produce error briefs? | Terminal/blocking errors should. Warnings should not always produce briefs, but they should be listable and watchable. |
| 28 | What states should error records have? | `observed`, `warning`, `filed`, and `recovered` were accepted as a useful starting set. |
| 29 | Should warnings appear if a brief is going to be issued at the end? | Yes, but in a lighter-weight form than terminal/blocking error briefs. |
| 30 | How should repeated failures dedupe? | One instance error record/brief per root molecule plus failure fingerprint. Repeated failures across roots accumulate into a rollup. Retry attempts should not inflate distinct-root counts. |
| 31 | Should accumulated errors feed formula correction? | Yes. The rollup loop should become feedback for correcting the formula, generated program, composition, policy, or runtime component that caused the error. |
| 32 | What should the repair target be? | The thing that caused the error, not mechanically the formula that happened to be running when the error surfaced. |
| 33 | What cause kinds are needed? | Start with `formula_defect`, `composition_error`, `input_error`, `runtime_infra`, `policy_gate`, `human_revision_needed`, and `unknown`. |

## Error Brief And Conservation Decisions

| # | Question | Recorded Answer Or Decision |
|---|---|---|
| 34 | Does the conservation filter allow an error brief? | Yes. A failed molecule/root has an overarching bead that has failed with a particular error. An error brief is a valid catch artifact under conservation. |
| 35 | How should error brief producer failures avoid loops? | Error briefs should self-exclude from recursive producer-failure loops unless the error is specifically that the error-brief producer is broken. |
| 36 | What should an error brief contain? | It should report the error and recommend a further course of action. |
| 37 | Should an approved error-brief action execute automatically? | Yes. Approval should execute the typed effect plan through `mctl`. Likely actions include revise, retry, repair, waive, reject source, defer, file issue, escalate, and route-disable where allowed. |
| 38 | Should the failed source/root remain held after an error brief is approved? | Yes, until a follow-up resolution basis is accepted. Approval of the error brief starts the next action; it does not by itself erase the failed work. |
| 39 | Is an MRE required to close an error? | Prefer an MRE when possible, but allow waiver with strong evidence. Some failures are hard to reproduce; sustained clean operation, replacement success, or human acceptance can be enough. |
| 40 | Is this about users deciding what to do? | Yes. The system should not tie the user's hands with one rigid closure rule. |
| 41 | What should the default hold scope be? | The rig of the dispatched work. Escalation to formula-wide or city-wide should require explicit recommendation/adjudication. |

## Execution Policy Decisions

| # | Question | Recorded Answer Or Decision |
|---|---|---|
| 42 | Should this be wrapped in Python with `mctl`? | Yes. `mctl` should make typing easier and provide the shared core for CLI, MCP, dashboard, and formula integrations. |
| 43 | Should `disable_route` be automatic when repeated failures accumulate? | Only human-approved, except for extremely narrow pre-approved no-brainer rules. |
| 44 | Should route-disable target composition edges before whole formulas? | Unclear. Composition-edge disable may be too fine-grained for the current system. Formula/subject-level policy should be the first implementation target. |
| 45 | Should route-disable and policy controls appear in dashboard and `mctl`? | Yes. They should be available in both. |
| 46 | Can some policy changes be done directly? | Yes. Some lower-risk changes can be direct operator actions. Higher-risk changes must remain brief-gated or admin-gated. |
| 47 | Where should the policy docs live? | Probably in the dev section, with live state stored in city artifacts/beads and exposed through `mctl`. |
| 48 | Should all of this be wrapped in `mctl`? | Yes. The CLI and MCP should share the same Python core. |
| 49 | What should the policy check command be named? | The formula-specific command should be `policy_check_formula`. |
| 50 | Should the internal policy model be formula-only? | No. Internally it should be generalized, because it may apply to formulas, Python scripts, orders, generated programs, and skills. |
| 51 | Should the first public implementation still be formula-specific? | Yes. Start with `policy_check_formula`, backed by a generalized subject model. |
| 52 | Should policy checks happen at design time and runtime? | Both. Design-time checks prevent bad programs from being approved. Runtime checks catch policy drift before execution. |
| 53 | What happens if policy drifts after approval? | Runtime policy wins. Execution should block or require a new approval, and a policy-blocked error brief should be filed when appropriate. |
| 54 | Should exceptions pin subject hashes? | Yes, by default. A hash mismatch should block or require refreshed approval. |
| 55 | Which policy wins when multiple policies match? | The most restrictive matching policy wins. Exceptions must be at least as narrow as the blocking policy. |
| 56 | Does execution policy apply transitively through generated programs? | Yes. A generated program must carry and check its callable inventory. |
| 57 | What if the callable graph is incomplete? | Be conservative. Missing or unbounded callable inventory should raise the activation floor to brief-gated or manual, depending on risk. |
| 58 | Are dynamic callable names allowed? | Yes, only when bounded by policy, such as a finite allowlist. Open dynamic calls should raise the activation floor. |
| 59 | Where does the callable inventory live? | In the generated program artifact as authoritative data, with a projected copy in the design brief. |

## Open Items For The PERT

These are not blocked by the grilling session, but they need concrete treatment
in the implementation plan.

- Pick canonical file paths for the new typed artifacts and their live state.
- Decide which existing formulas are enrolled first in normalized error capture.
- Define the exact `mctl` command surface for errors, programs, and policy.
- Define MCP tool names that mirror the `mctl` core without bypassing it.
- Decide how much dashboard UI is included in the first implementation phase.
- Decide whether Gas City core itself should eventually enforce policy for
  direct `gc sling`, or whether first enforcement stays in MathCity wrappers.
- Define the canonical artifact/reference pattern for generated dispatch
  programs: embedded artifact, linked artifact, or linked artifact with digest.
- Reconcile finishing policy with the known molecule/root closing trouble.

## Carry-Forward Principle

The big implementation plan should not present this as a magic formula builder.
The design must explicitly account for the current runtime behavior: formulas
compose through cook, attach, sling, and brief-approved continuations, while
runtime recursion and arbitrary program execution require new typed support.
