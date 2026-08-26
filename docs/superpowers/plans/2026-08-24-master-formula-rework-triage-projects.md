# Master Formula Rework Triage Projects

Parent: [Master Formula Rework Exploratory Handoff](./2026-08-24-master-formula-rework-exploratory-handoff.md)

Status: exploratory candidate queue, not an approved implementation plan.

Date: 2026-08-24

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
| 1 | A1 | Known sharp edge in current typed dispatch; small blast radius. |
| 2 | A3 and A4 | Directly improves commission brief trust without new runtime substrate. |
| 3 | A2 | Replaces fresh-work hand work with typed dry-run/apply/provenance while preserving `work-briefed`. |
| 4 | B1 | Cheap guardrail against future overclaiming. |
| 5 | B2/B3 | Introduce dispatch-program validation without changing live routing. |
| 6 | C1/C2 | Add policy vocabulary after callable artifacts are understood. |
| 7 | Later C/D work | Only after evidence says the smaller slices are stable. |

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

