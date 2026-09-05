# Master Formula Rework Triage Projects

Parent: [Master Formula Rework Exploratory Handoff](./2026-08-24-master-formula-rework-exploratory-handoff.md)

Status: exploratory candidate queue, not an approved implementation plan.

Date: 2026-08-24 (amended 2026-08-27: Course A gains **A6**, the P3.2 repo-scope guard on
`create_github_issue` — bead `mc-lhd66`. The amendment is preceded by running the
`SURFACE-STATUS.md` §3 probe that could have made A6 unnecessary; it did not. Live `mctl`
dry-run reads were used as evidence for that probe only — reading or triaging this packet
still requires no live-city operation.)

## How To Use This File

This file breaks the master formula rework into smaller projects that can be
triaged and, if accepted, commissioned separately. The goal is to preserve the
working city while extracting useful ideas from the larger execution-policy and
error-brief plan.

Each candidate is sized as a possible forkable event. A triage agent should
mark each candidate as `use`, `adapt`, `defer`, or `abandon candidate` before
turning it into an implementation plan.

## Release Posture

| Constraint | Consequence |
| --- | --- |
| Preserve `mathcity.work -> work-briefed` | First slices harden the current route instead of replacing it. |
| Keep commissioning approval-gated | Fresh or ambiguous work still files a commission brief before implementation dispatch. |
| Prefer MCP/CLI typed surfaces | Replace hand-authored shell/provenance only when typed effects preserve the same checks. |
| Keep live-city operations out of docs triage | No restart, drain, `gc`, `bd`, `mctl`, dashboard, or live smoke test is required to read or triage this packet. |
| Separate current behavior from planned behavior | Do not document future policy/program/error surfaces as current. |

## Course A: Current Router, Better MCP Surface

Recommendation: use first.

This course keeps `work-briefed` as the executable boundary and improves the
typed control surface around it.

| ID | Candidate Project | Triage Bias | Objective | Main Files | Acceptance Shape |
| --- | --- | --- | --- | --- | --- |
| A1 | Bead-scoped artifact root for `mctl work dispatch` | Use | Stop `mctl work dispatch` from passing a shared rig-level artifact root into `work-briefed` build paths. | `assets/scripts/mctl_core/work.py`, `tests/mctl/test_work_cli.py`, dispatch-family tests, docs mentioning the gap | Dry-run effect plan uses a per-bead artifact root; existing dispatch safety tests still pass; docs no longer warn that the typed path recreates the shared-root hazard. |
| A2 | Typed `work_commission` MCP/CLI path | Use | Add a typed operation for fresh work that plans and optionally applies the current path-B `gc sling ... --on work-briefed`, verifies claim, and records dispatch provenance. | `mctl_core/work.py`, `mctl_core/cli.py`, `mctl_core/mcp_server.py`, schema snapshots, `skills/work/SKILL.md` | Fresh work has a dry-run-first typed path; applying requires the same live-dispatch arming discipline; provenance is written through existing `dispatch-provenance.v1`. |
| A3 | Bounded catalog evidence in `commission-work-briefed` | Use | Make catalog enumeration bounded and explicit so a slow or failed catalog read is not rendered as an empty catalog. | `formulas/commission-work-briefed.toml`, `tests/commission-work-briefed/smoke_test.sh`, `docs/COMMISSIONING-CONTRACT.md` | Commission briefs must distinguish catalog present, catalog unreachable, and formula unavailable. No unbounded `gc formula list` requirement remains in the formula prompt. |
| A4 | Content-level commission brief requirements | Use | Require non-empty content for objective, reconciliation, graph, selected formulas, test gates, brief gates, and continuation evidence. | `formulas/commission-work-briefed.toml`, commission smoke tests, possibly brief validation docs | A heading alone does not count as evidence; "searched and found 0" is an explicit valid result. |
| A5 | Commissioning path docs cleanup | Use | Update the docs and skills so the current two paths are clear: approved brief-backed work uses `mctl work dispatch`; fresh work uses typed commission once A2 exists. | `skills/work/SKILL.md`, `README.md`, `README-development.md`, `LAYOUT.md` if placement changes | No instructions route around the typed path once it exists; current and planned behavior are separated. |
| A6 | P3.2 repo-scope guard on `create_github_issue` | Use | Refuse `create_github_issue` (and `standardize_github_issue`, which publishes to an upstream issue by the same `GithubWrite` route) when the target repo is OUTSIDE the owned set and no APPROVED brief id is supplied. P3.2 forbids filing an upstream issue without an approved `create-issue-briefed` brief, and the typed surface today ships the verb that bypasses that gate while omitting the one that enforces it. Amendment to landed #185 code (`b7d7a50`), not a new tool and not a new workstream. | `assets/scripts/mctl_core/effects.py` (`plan_create_github_issue`), `mctl_core/issue_standardize.py`, `mctl_core/mcp_server.py` (schemas gain an optional `brief_id`), `mctl_core/verdicts.py` (reuse the existing approval read — do not add a second notion of approved), `tests/mctl/test_create_github_issue.py` (which already holds the `MGHW_TEMPLATE_SECTION_MISSING` cases to model on) and `tests/mctl/test_standardize_github_issue.py`, schema snapshots, `docs/SURFACE-STATUS.md` | A new FATAL `MGHW_UPSTREAM_BRIEF_REQUIRED` raised BEFORE the plan is built and before any subprocess runs — same call-site, same `MGHW_*` family and same severity as the existing `MGHW_TEMPLATE_SECTION_MISSING`, never a soft return (P6.1). Three observed cases, not one: (1) FAILING — a `gastownhall/*` target with no `brief_id`, refused, no `gh` invoked (P6.2: the guard must be seen refusing); (2) PASSING-UNCHANGED — `tdupu/mathcity` with no `brief_id`, plan built exactly as today, so the owned case Plan A was designed around is not regressed; (3) PASSING-GATED — a `gastownhall/*` target WITH an approved brief id, admitted. A `brief_id` that exists but is not approved must refuse, or the check could not have failed. The refusal's `suggested_next_command` names the compliant path (`gc sling <rig>/<agent> create-issue-briefed --formula …`, POLICY.md:348), because the typed surface cannot route there itself. |

### A6 note — the measurement that put this in Course A rather than beside it

`docs/SURFACE-STATUS.md` §3 carried, `NOT PROBED` since 2026-08-23, the one measurement that
could have made this candidate unnecessary: *whether a Mayor restricted to the MCP can sling a
formula that files issues — if yes, #185 surface 1 may not need building at all.*

**Probed 2026-08-27. The answer is NO on two independent grounds [measured]:**

1. **Nothing typed can sling a NAMED formula.** The running server's `work_dispatch` schema is
   `{brief_id, city, dry_run, rig}` with `additionalProperties: false`; a live dry-run
   (`brief_id=mc-q5s4`, trace `e9bb9e9a`) planned `--on work-briefed`. `work.py:1154
   _formula_invocation` hardcodes the literal, and the sole `gc sling` subprocess site
   (`work.py:515`) runs only what that function built. Of 41 tools the only other `formula`
   argument belongs to `work_dispatch_event`, which RECORDS a sling rather than performing one.
2. **Neither briefed formula files an issue anyway.** `create-issue-briefed` is terminal at
   `file-brief` and states four times that it NEVER runs `gh issue create`;
   `mathcity-issue-briefed` extends it and inherits that terminal step. Filing happens after
   adjudication, by the verdict-executing agent. Zero files under `formulas/` or `orders/` name
   either formula as a step, so `work-briefed` cannot reach them by composition either.

So the guard must **refuse**; it cannot **redirect**. The best it can do is name the compliant
`gc sling` in its diagnostic. That is why A6 is an amendment to the landed verb rather than a new
typed briefed-issue tool.

**Why A6 and not a sixth course.** Course A is "keeps `work-briefed` as the executable boundary,
improves the typed control surface" — A6 improves the typed surface without touching the router,
which is exactly the course's shape. **A2 is the near-miss and does not cover this:** it plans a
typed `work_commission` that still slings the hardcoded `--on work-briefed`, so it gives the typed
surface a briefed *work* path and no briefed *issue* path. Grepping every doc under
`docs/superpowers/plans/` for `P3.2` returns zero hits; nothing else in this plan claims it.

**Scope caveat, stated rather than assumed.** The predicate "outside the owned set" is not settled
by this plan — see the open question below. The `standardize_github_issue` inclusion is not scope
creep: it carries the identical bypass through the identical `GithubWrite` path, and a guard that
leaves the adjacent hole open is not a guard.

**Open question for adjudication (`mc-lhd66` is explicitly not settled on this).** Should the
predicate be *narrow* — refuse only `gastownhall/*`, the three repos P3.2 names — or *fail-closed*
— refuse any repo not on an owned allowlist (`tdupu/*`)? Narrow matches P3.2's literal text and
cannot over-block. Fail-closed matches P3.1/P4.1's "anything outside the owned set" and needs no
amendment when a new upstream appears, at the cost of refusing a third-party repo the policy never
considered. **Recommendation: fail-closed with an explicit allowlist**, because the failure it
prevents is irreversible (a published issue) and the failure it causes is a one-line refusal that
names the fix.

#### A6 §E — wheel-check (P1.20 shape, recorded even though A6 is code not design)

| # | Alternative surveyed | Verdict | Why |
| --- | --- | --- | --- |
| 1 | Route the verb to `create-issue-briefed` / `mathcity-issue-briefed` | **rule out** | Measured 2026-08-27: unreachable from the MCP, and neither formula files an issue. This is the row-152 probe above. |
| 2 | Parameterize `_formula_invocation` so the typed surface can sling a named briefed formula | **rule out** | An unconstrained formula parameter opens a WIDER bypass than it closes — a caller could sling a non-briefed formula through the typed surface. `SURFACE-STATUS.md` row 1 already owned this fork on 2026-08-23. |
| 3 | New `create_issue_briefed` MCP tool that drafts and files the decision brief without posting (`mc-lhd66` option 1) | **defer, not adopt now** | Strictly larger than a guard; restates `create-issue-briefed`'s three steps inside the typed surface; and on its own it does not stop the unbriefed verb from being reached. A guard is the necessary half and does not preclude this later. |
| 4 | Remove `create_github_issue` | **rule out** | Correct for `gastownhall/*`, wrong for `tdupu/*`, where #185 deliberately removed the human gate — and §2 records the verb in production use (six filings, #211–#216). |
| 5 | Reuse the existing `MGHW_TEMPLATE_SECTION_MISSING` refusal at the same call site | **adopt** | This is the wheel. The pre-subprocess refusal position, the FATAL severity, the `MGHW_*` family and the `suggested_next_command` field all already exist in `plan_create_github_issue`. |
| 6 | Reuse `verdicts.read_verdict` / `work.py:1182 _approved_for_dispatch` for "approved" | **adopt** | A second notion of what counts as approved would drift from the dispatch path's. #160 already learned that reading fixed metadata keys against bare words is wrong. |
| 7 | Enforce P3.2 in a skill or hygiene gate instead of in code | **rule out** | A skill gate binds only agents that read it; the MCP verb is reachable without it. P6.2: a gate the bypassing path never invokes could not have failed. |

**P3.5 (agent context).** A6 executes as an **inside worker** in the `mathcity` rig, dispatched
through the normal brief-backed path. It edits only `mathcity/` (owned set); no upstream repo is
touched, so Pillar 3's PR route is not engaged by the build itself.

**P3.6 (documentation).** A6 is a user-facing behavior change to a live typed verb, so it must
run `improve-documentation`: the MCP roster docs, `docs/SURFACE-STATUS.md` §2, and any skill that
tells an agent to reach for `create_github_issue` must state the new refusal and name the
compliant `gc sling`. An `N/A` here would be a fail.

**A6 must NOT copy its sibling's predicate — measured 2026-08-27, `mc-ss24m` (P1).** A6 was
specified as "the same shape as the guard Plan A already ships". Copy that guard's POSITION
(raised before the plan is built, before any subprocess), its SEVERITY (FATAL) and its `MGHW_*`
family — **but not its predicate, which is itself unreachable.** A live dry-run of
`create_github_issue` against `gastownhall/gascity` with a 43-byte body carrying no template
heading and no brief id returned a complete `GithubWrite` plan with **zero diagnostics** (trace
`ee335ff6`): `required_template_sections` includes `config.yml`, whose required set is empty, so
`all(per_template_missing.values())` is always False and `MGHW_TEMPLATE_SECTION_MISSING` never
raises. That same probe is A6's motivating measurement — it shows there is no P3.2 gate — and it
is the reason A6's acceptance shape demands an OBSERVED refusal rather than a passing test suite.
`tests/mctl/test_create_github_issue.py` has cases for the template guard today and they do not
catch this, because their fixtures do not reproduce the live template set.

**P7.3 (interface gap filed, not routed around).** The gap is filed as `mc-lhd66` against the
typed surface itself; nothing here adds a store, filesystem or `bd` access to work around it.

## Course B: Dispatch Program Substrate

Recommendation: use after Course A, or adapt if the first implementation agent
finds a narrower artifact format.

This course introduces `dispatch-program.v1` as a reviewable artifact without
making it a general runtime interpreter.

| ID | Candidate Project | Triage Bias | Objective | Main Files | Acceptance Shape |
| --- | --- | --- | --- | --- | --- |
| B1 | Formula composition runtime baseline doc | Use | Record current cook, attach, sling, and continuation behavior so future designs do not claim unsupported runtime recursion. | `subdomains/dev/docs/FORMULA-COMPOSITION-RUNTIME-BASELINE.md` or `docs/superpowers/plans/` pointer | The doc clearly states what works today and what would require new runtime support. |
| B2 | `dispatch-program.v1` datamodel and validator | Adapt | Add a typed artifact for generated dispatch plans: program id, version, source bead, callable inventory, graph, activation policy, finishing policy, revision policy. | `assets/scripts/mctl_core/programs.py`, `schemas.py`, `tests/mctl/test_dispatch_programs.py` | Fixture validation catches missing callable inventory, open dynamic calls, and malformed graph rows. No live route changes. |
| B3 | `programs_validate` CLI/MCP tool | Defer until B2 | Expose program validation through the same core from CLI and MCP. | `cli.py`, `mcp_server.py`, schema snapshots | CLI and MCP return the same structured validation result; no shell passthrough. |
| B4 | Commission brief emits dispatch-program evidence | Defer until B2/B3 | Make `commission-work-briefed` include a program ref/digest and projected callable inventory in the approval brief. | `formulas/commission-work-briefed.toml`, commission smoke tests | Reviewer can see what will execute; compatibility `commission-dispatch.v1` remains the execution path until runtime support changes. |
| B5 | Revision diff for generated programs | Defer | Compare full replacement revisions and mark material changes, especially callable inventory, activation, finishing, source binding, and effect plans. | `programs.py`, `tests/mctl/test_program_revision_diff.py` | Diff output highlights changes that alter execution or approval meaning. |

## Course C: Formula Execution Policy Gate

Recommendation: defer unless there is an immediate safety need. It becomes
more valuable once Course B has a typed callable inventory.

| ID | Candidate Project | Triage Bias | Objective | Main Files | Acceptance Shape |
| --- | --- | --- | --- | --- | --- |
| C1 | `policy_check_formula` core | Defer | Add a formula-first policy check backed by a general subject model. | `mctl_core/policy.py`, `schemas.py`, `tests/mctl/test_execution_policy.py` | Most restrictive matching policy wins; no matching policy returns normal/pass. |
| C2 | CLI/MCP policy check | Defer | Expose `policy_check_formula` through CLI and MCP. | `cli.py`, `mcp_server.py`, schema snapshots | Both surfaces share the same core and schema validation. |
| C3 | Gate `mctl work dispatch` | Defer | Refuse dispatch when the selected formula is disabled, manual-only, or brief-gated without a matching exception. | `work.py`, `tests/mctl/test_work_cli.py` | Dry-run and apply both report policy evidence; blocked plans do not run. |
| C4 | Gate approved commission continuations | Defer | Make `brief-decision-dispatch` re-check runtime policy before executing an approved continuation. | `formulas/brief-decision-dispatch.toml`, smoke tests | Runtime policy drift wins over stale approval; failed execution is visible and held. |

## Course D: Error Briefs, Rollups, Dashboard Controls

Recommendation: keep as roadmap. Do not start here.

This course contains the high-value but high-blast-radius remainder of the
large PERT.

| ID | Candidate Project | Triage Bias | Objective | Main Files | Acceptance Shape |
| --- | --- | --- | --- | --- | --- |
| D1 | Normalized formula/program errors | Defer | Record terminal and warning errors with stable fingerprints and cause kinds. | `mctl_core/errors.py`, `schemas.py`, error tests | Errors are visible without the dashboard; repeated failures dedupe by root and fingerprint. |
| D2 | Error brief planning | Defer | Turn terminal/blocking errors into briefs with recommendations and typed effect plans. | `errors.py`, `effects.py`, brief tests | Failed roots remain held until a resolution basis is accepted. |
| D3 | Existing formula enrollment | Defer | Add generated `[[errors]]` declarations and prompt instructions to core formulas. | `formulas/work-briefed.toml`, `commission-work-briefed.toml`, producer-failure formulas | Existing behavior is preserved; normalized records are additional evidence, not a replacement for current handling. |
| D4 | Dashboard controls through MCP | Defer | Add policy/error/program views after the CLI/MCP surfaces are already proven. | dashboard server/frontend, MCP tool allowlists, dashboard tests | Dashboard never bypasses `mctl` and never repairs on read. |
| D5 | End-to-end policy/error smoke | Defer | Prove the integrated flow only after C and D substrates exist. | integration smoke tests | Passing E2E demonstrates policy drift blocks execution and files visible error state. |

## Abandon Or Rewrite Candidates

These are not necessarily bad ideas, but they should not be accepted as-is:

| Candidate | Concern | Safer Treatment |
| --- | --- | --- |
| Replacing `work-briefed` with `commission-work-briefed` | The current router is working; `commission-work-briefed` is not yet a proven executor. | Keep `work-briefed` as default; make commissioning produce better approval artifacts. |
| Treating formula TOML as a general runtime interpreter | Current formula behavior is cook/attach/sling/continuation oriented, not arbitrary runtime recursion. | Document the baseline; add typed generated-program support only where the runtime actually supports it. |
| Building dashboard controls before CLI/MCP | Dashboard controls increase blast radius and can hide uncertain state. | CLI/MCP first, dashboard last. |
| Auto-disabling routes from repeated failures | A wrong disable can stop useful work across a rig or city. | Require human approval except for narrow, pre-approved no-brainer rules. |
| Turning all warnings into briefs | Human attention becomes the bottleneck. | Keep warnings listable/watchable; brief only terminal or blocking failures by default. |

## Suggested Triage Order

| Order | Candidate | Reason |
| --- | --- | --- |
| 1 | A6 | Closes a live policy bypass on a verb already filing issues in production; smallest blast radius of any A candidate (one refusal at one existing call site) and the only one whose absence can publish something irreversible. |
| 2 | A1 | Known sharp edge in current typed dispatch; small blast radius. |
| 3 | A3 and A4 | Directly improves commission brief trust without new runtime substrate. |
| 4 | A2 | Replaces fresh-work hand work with typed dry-run/apply/provenance while preserving `work-briefed`. |
| 5 | B1 | Cheap guardrail against future overclaiming. |
| 6 | B2/B3 | Introduce dispatch-program validation without changing live routing. |
| 7 | C1/C2 | Add policy vocabulary after callable artifacts are understood. |
| 8 | Later C/D work | Only after evidence says the smaller slices are stable. |

## Commissioning Prompt Shape

When a candidate is accepted, commission it as a small event with this shape:

```text
Objective: <one candidate project only>
Source docs:
- docs/superpowers/plans/2026-08-24-master-formula-rework-exploratory-handoff.md
- docs/superpowers/plans/2026-08-24-master-formula-rework-triage-projects.md
- <specific source artifact or current file>
Invariant: preserve the working mathcity.work -> work-briefed path.
Non-goals: no city restart, no broad policy/error/dashboard bundle, no direct replacement of the current router.
Expected output: <docs/fixtures/tests/code depending on candidate>
Validation: local fixture/smoke tests only unless a separate approved plan requests live city operations.
```

