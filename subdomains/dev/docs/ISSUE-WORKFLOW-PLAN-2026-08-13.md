# MathCity Issue Workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development`
> or `superpowers:executing-plans` to implement this plan task-by-task.

> **HISTORICAL RECORD — superseded in two places (2026-08-14).** This plan is kept
> as-written because it records what was built on 2026-08-13; do not read it as the
> current state of the pack.
>
> 1. The interactive skill named `write-issue-targeted` throughout this document was
>    **renamed to `create-issue`** (`skills/create-issue/SKILL.md`,
>    alias `mathcity.create-issue`) for verb-consistency with `create-issue-briefed`.
>    One skill, renamed — not a second surface.
> 2. The Global Constraint *"Do not author `.github/ISSUE_TEMPLATE/*.yml` — this
>    workflow consumes them"* was scoped to this plan, and has since been discharged:
>    `tdupu/mathcity` had **no** `.github/` at all, so every "reads the target's live
>    template" claim in this workflow pointed at nothing. The templates
>    (`bug_report.yml`, `feature_request.yml`, `docs_report.yml`, `config.yml`) plus
>    `.github/LABELS.md` now exist in the repo and make those claims true.

**Goal:** Give MathCity its own issue-filing workflow that carries `write-issue`'s
investigation rigor, takes the target repo as a declared parameter defaulting to
`tdupu/mathcity`, consumes the target repo's live issue templates, and never files
an issue before a human approves the exact body.

**Architecture:** One shared standard (`template-fragments/issue-investigation-standard.md`)
read by two surfaces — an interactive skill (`write-issue-targeted`) and a
dispatchable formula (`mathcity-issue-briefed`). The formula is a thin adapter over
the existing `create-issue-briefed`, following the `github-issue-fix` /
`github-issue-triage` adapter-over-base shape: it overrides only the vars and the one
step it customizes, and inherits the terminal `file-brief` step.

**Tech Stack:** gascity formula TOML (`formula_compiler >= 2.0.0`), Claude skill
Markdown, bash smoke tests, `gh` CLI.

**Spec:** [tdupu/mathcity#12](https://github.com/tdupu/mathcity/issues/12)

## Global Constraints

- Target repo is a **declared parameter**, never an assumption in prose. Default
  `tdupu/mathcity`; recognized alternatives `tdupu/gascity-packs` and
  `gastownhall/gascity`.
- Nothing in this workflow may execute `gh issue create` before a human approval
  verdict (`subdomains/dev/POLICY.md` P3.2).
- Any formula named `*-briefed` must terminate in the brief cycle
  (`POLICY-formulas.md` F8.1; allowed terminal step ids: `file-brief`,
  `brief-finalize`, `workflow-finalize`, `publish`, `route`).
- No formula step may name a model (`opus`/`sonnet`/`haiku`/`fable`) as a
  `gc.run_target` (F1.3, F3.3).
- Every new formula ships a smoke test that has been **run**, with recorded output
  (F6.1).
- Do not modify `write-issue`, `github-issue-fix`, or `github-issue-triage` — they
  are `gascity-packs`-owned and read-only to us (P2.1).
- Do not author `.github/ISSUE_TEMPLATE/*.yml` — this workflow *consumes* them.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `template-fragments/issue-investigation-standard.md` | **The one copy** of the investigation standard. Target-parameterized. Read by both surfaces. |
| `skills/write-issue-targeted/SKILL.md` | Interactive surface. Resolves the target, walks the standard, drafts against the live template, stops at the approval gate. |
| `formulas/mathcity-issue-briefed.formula.toml` | Dispatchable surface. Thin adapter `extends = ["create-issue-briefed"]`; overrides `target_repo` default + the `intake` step. |
| `tests/mathcity-issue-briefed/smoke_test.sh` | F6.1 smoke test asserting targeting, the approve-before-file gate, and the F8.1 terminal. |
| `README-formulas.md`, `README-skills.md` | Index rows (P1.13). |

---

## Task 1: The shared investigation standard

**Files:**
- Create: `template-fragments/issue-investigation-standard.md`

**Interfaces:**
- Produces: a fragment addressed by the repo-relative path
  `template-fragments/issue-investigation-standard.md`, structured as nine
  numbered stages (Triage, Duplicate search, Verify-on-main, Architectural
  alignment, MRE, Blast radius, Fix candidates, Body, Approval gate) plus an
  anti-pattern table and a pre-flight checklist. Consumers cite stage numbers.

- [ ] **Step 1:** Write the fragment with a `$TARGET_REPO` target registry table at
  the top (default `tdupu/mathcity`; alternatives `tdupu/gascity-packs`,
  `gastownhall/gascity`) and a per-target "design corpus" column so stage 4
  parameterizes instead of hardcoding `engdocs/design/`.
- [ ] **Step 2:** Port every stage of `write-issue` at full rigor — the three
  duplicate searches, the verify-on-main finding table, the architectural-alignment
  finding table, the ≥2-fix-candidate rule, the anti-pattern table, the pre-flight
  checklist. Replace each hardcoded `gastownhall/gascity` with `$TARGET_REPO`.
- [ ] **Step 3:** Replace `write-issue`'s inline body template with a pointer to the
  target repo's live `.github/ISSUE_TEMPLATE/*.yml`, and make an MRE **required**
  for `kind/bug`.
- [ ] **Step 4:** Add stage 9 — the approval gate. `gh issue create` runs only after
  a human APPROVE verdict.
- [ ] **Step 5:** Commit.

## Task 2: The interactive skill

**Files:**
- Create: `skills/write-issue-targeted/SKILL.md`
- Modify: `README-skills.md` (index row, P1.13)

**Interfaces:**
- Consumes: `template-fragments/issue-investigation-standard.md` (Task 1) by path.
- Produces: skill name `write-issue-targeted`, alias `mathcity.write-issue-targeted`.

- [ ] **Step 1:** Write frontmatter whose `description` disambiguates from upstream
  `contributing.write-issue` on the routing axis (this one for `tdupu/*` targets and
  any target passed explicitly; upstream's for external-contributor filing to
  `gastownhall/gascity`).
- [ ] **Step 2:** Write step 0 — target resolution — as the first action in the body,
  with the registry table and a fail-closed branch (P1.14 / P6.1) when the target
  cannot be resolved.
- [ ] **Step 3:** Delegate stages 1–8 to the fragment by path rather than restating
  them.
- [ ] **Step 4:** Write the approval gate section so every `gh issue create`
  occurrence in the file appears *after* it.
- [ ] **Step 5:** Add the `README-skills.md` row and bump the counts.
- [ ] **Step 6:** Commit.

## Task 3: The adapter formula

**Files:**
- Create: `formulas/mathcity-issue-briefed.formula.toml`
- Modify: `README-formulas.md` (index row)

**Interfaces:**
- Consumes: `create-issue-briefed` (existing) as the extended base; the Task 1
  fragment via the `investigation_standard` var.
- Produces: formula name `mathcity-issue-briefed`; vars `target_repo` (default
  `tdupu/mathcity`), `issue_kind`, `investigation_standard`; overridden step id
  `intake`; inherited steps `compose-body`, `file-brief`.

- [ ] **Step 1:** Write the adapter with `extends = ["create-issue-briefed"]` and
  override only `[vars.target_repo]`, the two new vars, and the `intake` step.
  **Do not append new steps** — resolved child steps append *after* the parent's,
  which would place them after `file-brief` and break F8.1
  (`gascity/internal/formula/parser.go`, `mergeSteps`).
- [ ] **Step 2:** In the overridden `intake`, validate `$TARGET_REPO` against the
  registry, pick the template by `issue_kind`, and gate on investigation evidence.
- [ ] **Step 3:** Add the `README-formulas.md` row and bump the count.
- [ ] **Step 4:** Commit.

## Task 4: Smoke test

**Files:**
- Create: `tests/mathcity-issue-briefed/smoke_test.sh`

- [ ] **Step 1:** Copy the structure of `tests/create-issue-briefed/smoke_test.sh`
  (`set -euo pipefail`, `check()`, `RESULTS[]`, PASS/FAIL counters, standalone).
- [ ] **Step 2:** Assert the default target resolves to `tdupu/mathcity`.
- [ ] **Step 3:** Assert each recognized alternative target is accepted.
- [ ] **Step 4:** Assert no line-start `gh issue create` in the formula, and that in
  the skill every `gh issue create` occurrence follows the approval-gate heading.
- [ ] **Step 5:** Assert the F8.1 terminal step id, including through `extends`.
- [ ] **Step 6:** Run it; run the whole `tests/*/smoke_test.sh` suite; run
  `gc lint . --json`. Record real output.
- [ ] **Step 7:** Commit.

---

## §E — Alternatives surveyed (check-wheel / check-zero, P1.20)

Surveyed before authoring; verdict per row.

| Alternative | Verdict | Why |
| --- | --- | --- |
| `contributing/skills/write-issue` (gascity-packs) | **adapt** | Best-in-class investigation discipline; unusable as-is because `gastownhall/gascity` is hardcoded in nine places and it lives outside the owned set (P2.1). Its rigor is ported into the shared fragment with the target parameterized. |
| Vendor `write-issue` into `mathcity/skills/` | **rule out** | P1.9 — a vendored copy is a second real copy of an upstream-owned skill, and adoption can only complete by making the origin a symlink or removing it, which P2.1 forbids for `gascity-packs`. Structurally uncompletable → fail. Also P1.7 (upstream stays pullable). |
| `gascity/formulas/github-issue-fix{,-base}` + `github-issue-triage{,-base}` | **adopt (shape only)** | The adapter-over-base shape is exactly right and is reused verbatim: thin wrapper, `extends`, override only what is customized. The formulas themselves are fix/triage-oriented, not filing-oriented, so no content is taken. |
| `mathcity/formulas/create-issue-briefed` | **adopt (as the base)** | Already ours; already drafts from the live `.github/ISSUE_TEMPLATE/*.yml`; already never files before approval. Serves as the extended base rather than being re-implemented. |
| Rename `create-issue-briefed` → `create-issue-briefed-base` to match the upstream `-base` naming convention | **rule out** | `internal/formula/parser.go` `loadFormula` resolves `extends` by name with no `-base` requirement, so the rename buys nothing; and P3.2 documents the `create-issue-briefed` command literally, so a rename breaks a policy-cited command surface. |
| A new `POLICY-issues.md` to hold the investigation standard | **rule out** | `POLICY-POLICY.md` requires a full trinity (policy + check skill + `new-*-policy` write path) for a new policy domain, and a Draft policy governs nothing until Adopted. Large scope creep for a document that is procedure, not rule. |
| A skill that the formula invokes to carry the standard | **rule out** | Formula steps dispatch to fleet agents whose skill materialization is not guaranteed; a pack-relative file path is readable unconditionally. |
| `template-fragments/` for the shared standard | **adopt** | The directory exists for exactly this (`dolt-preflight.md`, `escalation-protocol.md`), and existing skills already reference fragments by repo-relative path. One copy, both surfaces. |
| `subdomains/computing/skills/update-issue` | **rule out (no overlap)** | Rewrites an *existing* issue body and consolidates archive comments; says nothing about filing a new issue or about investigation. |
| `subdomains/computing/skills/check-mre` | **rule out (no overlap, cross-referenced)** | Validates a Magma MRE file against a project's `.claude/MRE-POLICY.md`. Different artifact, different repo class. Cross-referenced from the fragment's MRE stage rather than duplicated. |

**Verdict: NO REINVENTION.** The one genuinely new artifact is the shared standard
itself, which exists because no target-parameterized version is available anywhere.

## Known limitation

`create-issue-briefed`'s terminal `file-brief` step routes to
`mathcity.brief-operator`, a pool wedged at 0 sessions
([#10](https://github.com/tdupu/mathcity/issues/10)). `mathcity-issue-briefed`
inherits that step, so **the briefed terminal step cannot be verified end-to-end
until #10 lands.** Static conformance (F8.1 terminal id, producer-contract
metadata, targeting, the never-file guard) is verified by the smoke test; live
brief delivery is not.
