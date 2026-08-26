# Formulas Status — every formula in mathcity's live catalog

> Census 2026-08-24 (S51) from `formulas_catalog` (94 names, state healthy) + descriptions
> parsed from the formula TOMLs at their source packs. **`NOT PROBED` is load-bearing** —
> it means no recorded exercise in the run-log/ledger, and is never a pass (P6.2).
> "Tested" cites the session or artifact that exercised it; a blank claim is not allowed here.
> Companions: [SURFACE-STATUS.md](./SURFACE-STATUS.md) (MCP tools),
> [GASCITY-ISSUES.md](./GASCITY-ISSUES.md) (gc-layer).

## 1. Work routing & the -briefed entry points (the trusted core)

| Formula | Src | What it does | Tested | Open issues/beads |
|---|---|---|---|---|
| work-briefed | mathcity | THE router: reads the bead, picks COMMISSION / SIMPLE_CONTINUE / FULL_CONTINUE / EXPLICIT_CONTINUE, slings the child | **LIVE-PROVEN S51** (mc-e90d: routed mc-7d0 → COMMISSION, step closed) | step-8 assignee verify is premature (same class as #212); #149 store-scope fix landed |
| commission-work-briefed | mathcity | Fresh/ambiguous work → normalize objective, check existing work, design dispatch graph, file approval brief; NO implementation before approval | **RUNNING LIVE S51** (mc-7f4p in-progress; interrupted by the 00:17 crash, resumes) | #192 orphan-on-failed-create (fixed); mc-7po orphan preserved as evidence; #182 Q5 unanswered |
| build-basic-briefed | mathcity | build-basic whose terminal publish slot files a decision brief instead of pushing | **PROVEN S10–S14** (D2-primary; preferred feed, policy gsp-fhdnu) | artifact_root must be scoped per bead (gsp-1bmxuz); FINDING#1 detached-head worktrees at publish |
| simple-work-briefed | mathcity | Bounded task on a configurable model, then file a brief | EXERCISED S25–S27 (created S25; work-briefed verified S27) | simple-work-repair CT7.1 history (reverted S29) |
| planning-briefed | mathcity | PERT/decomposition/design artifact, gated by a decision brief; Opus-level planners | EXERCISED (rank-epic era) | /tmp bug found S29, fix sent to BART — landing UNVERIFIED |
| revise-return | mathcity | Re-deposit a fresh brief from a revise verdict's instructions (Plan H, #209) | LANDED, **LIVE E2E PENDING** — six S51 revises are its first real test | #209 (closes only on unattended observation); gascity#32 (lost brief.decided may starve its trigger) |
| smoke-test-briefed | mathcity | Smoke-test a mathcity artifact + brief with test evidence (F6.1) | NOT PROBED live (created S26) | — |
| pr-pipeline-briefed | mathcity | Compose a template-complete upstream PR body from commit + test evidence | EXERCISED S33 (#4843 advanced through the fixed pipeline) | — |
| create-issue-briefed | mathcity | Draft a template-complete upstream issue and file it as a decision brief | NOT PROBED | #185 alternative-A question mooted by create_github_issue landing |
| mathcity-issue-briefed | mathcity | Same, adapter for a declared target repo (default tdupu/mathcity) | NOT PROBED | same |

## 2. Brief pipeline

| Formula | Src | What it does | Tested | Open issues/beads |
|---|---|---|---|---|
| brief-shuffle | mathcity | Promote or reject ONE brief from .pile per the gate registry (the sole .pile→stack writer, B2.10) | EXERCISED (S10 glob fix 3f5c146; lockless redesign S28–S29 gsp-89yli) | stale-lock history; single-writer invariant |
| brief-shuffle-fast-drain | mathcity | Mechanically promote/reject a bounded batch of pile briefs (condition-triggered) | **fired ≤1×/rig EVER** — post-unlatch rig-scoped firing STILL UNOBSERVED | **#204 drain verdict PENDING**; #40; #73 (fixed) |
| brief-gate-keep | mathcity | Apply the formal gate registry to a staged/piled brief | EXERCISED (gates fired correctly when poked, S50 MBRF036) | gate-keep architecture he-jyfv |
| brief-prep | mathcity | Draft brief-bundle + gate evidence, submit to pile | PROVEN S10 (producer fix 2442300) | — |
| math-brief-prep | mathcity | Fan-out brief-prep per source bead, single-writer shuffle | EXERCISED (brief-pipeline era) | — |
| brief-decision-dispatch | mathcity | Dispatch approve/reject/revise/defer actions from decision records | **EXERCISED S51** (the order behind work_dispatch) | #212/#213/#214 (dispatch-layer defects, filed S51) |
| brief-record-decision | mathcity | Canonical decision record + archive artifacts | EXERCISED (gt-zayiw saga S5–S6) | — |
| brief-present-next | mathcity | Drain pending stack briefs to the adjudicator | EXERCISED (present-briefs era) | — |
| brief-review-patrol | mathcity | Auto-advance briefs stuck at review_gate | **PAUSED since S6** (churn flood) | gsp-12rf (fan-in ×16 + fail-open) |
| brief-watchdog-refill | mathcity | Keep the stack above low-water | EXERCISED (HIGH_WATER=5 era) | — |
| brief-archive-sweep | mathcity | Tidy rejected/decided artifacts without deleting records | NOT PROBED | — |
| brief-producer-failure-record / -rollup / -repair | mathcity | Record → roll up → repair repeated producer gate-failures | NOT PROBED individually | — |
| on-merge-brief-record | mathcity | Post-merge hook: brief-record when a closed bead carries needs-decision | **produced ZERO organic briefs ever** (S9); self-trigger runaway fixed | gt-xvxvu/gsp-e62n (fixed); mechanism-A structural race gsp-510c |
| file-or-sendback-route | mathcity | Log FILE/SEND-BACK for decided briefs, fire downstream | NOT PROBED | — |

## 3. No-brainer & decision enforcement

| Formula | Src | What it does | Tested | Open issues/beads |
|---|---|---|---|---|
| no-brainer-classify | mathcity | Apply the he-lele 5-criterion filter without bypassing stop gates | EXERCISED (S6 enforcement verified; ARMED default) | trigger=MANUAL — one of only 2 manual orders (5b) |
| no-brainer-candidate-curate | mathcity | Summarize leak/candidate patterns, file repair brief | fired 1×/rig (pre-latch) | same MANUAL trigger; #204 family |
| decision-enforce | mathcity | Verify bd decision record exists + source state matches verdict | NOT PROBED | — |

## 4. Build family (gascity pack)

| Formula | Src | What it does | Tested | Open issues/beads |
|---|---|---|---|---|
| build-basic | gascity | Full lifecycle requirements→review→optional publish | superseded in mathcity use by build-basic-briefed | — |
| build-base / build-basic-review | gascity | Virtual contract / review expansion | via children | — |
| build-from-requirements / -plan / -decompose / -convoy / -review (+ -base each) | gascity | Continue a build from each entry stage | NOT PROBED individually (exercised implicitly via build-basic chains) | — |
| publish | gascity | Explicit opt-in push + PR creation | EXERCISED (push=false default in all mathcity use) | FINDING#1: does not auto-recover detached-head worktree commits |
| implement / same-session-implement | gascity | Launch implementation for an approved convoy / same-session policy helper | NOT PROBED individually | — |
| gap-analysis | gascity | Compare implementation artifacts to approved requirements | NOT PROBED | — |
| review / design-review / code-review-base / fix-loop-base / fix-convoy | gascity | Review + fix-loop machinery | EXERCISED via build chains | — |
| planning-base / decomposition-base / implementation-base / implementation-item-base | gascity | Virtual methodology contracts | via children | — |
| do-work / do-work-item | gascity | One-convoy full lifecycle / shared-drain item | NOT PROBED individually | — |

## 5. Molecule / worker shapes (gc core + packs)

| Formula | Src | What it does | Tested | Open issues/beads |
|---|---|---|---|---|
| mol-do-work | gc core | Read the bead, do what it says, close it | EXERCISED (fleet baseline) | — |
| mol-scoped-work | gc core | Graph-first worktree lifecycle | NOT PROBED individually | — |
| mol-dog-stale-db | gc core | Detect/clean stale Dolt DBs + orphan servers | **fired 22:00:16 S50/S51 — the city-scope latch confirmation** | mol-dog-compactor order.failed 23:28 (adjacent, unfiled) |
| mol-polecat-base / -commit / -report | gc core | Polecat work variants (shared steps / direct-commit / report-only) | EXERCISED historically (polecat era) | — |
| mol-prompt-synth | gc core | Generate agent prompt template | NOT PROBED | — |
| mol-review-quorum | gc core | Review quorum scaffold | NOT PROBED | — |
| mol-contributing-find-work / -plan-implementation / -map-blast-radius / -fine-tune / -review | contributing | The gastownhall/gascity contributor lifecycle as dispatchable steps | NOT PROBED | — |

## 6. GitHub / PR adapters (gascity pack)

| Formula | Src | What it does | Tested | Open issues/beads |
|---|---|---|---|---|
| github-issue-fix (+ -base, -design-review-work) | gascity | Issue → triage → plan → build → review → optional PR | NOT PROBED in mathcity records | — |
| github-issue-triage (+ -base) | gascity | Triage an issue through the adapter workflow | NOT PROBED | — |
| github-pr-review | gascity | Review a PR through the adapter | NOT PROBED | — |

## 7. Superpowers ports

| Formula | Src | What it does | Tested | Open issues/beads |
|---|---|---|---|---|
| superpowers-build | superpowers | build-base with vendored Superpowers skills (brainstorm→finalize) | NOT PROBED | — |
| superpowers-{brainstorming, planning, plan-review, decomposition, implementation, development, development-item, fix-loop, code-review, review, task-review} | superpowers | Per-stage Superpowers implementations of the base contracts | NOT PROBED (pack installed, gc-superpowers) | — |

## 8. Domain & misc dispatch (mathcity)

| Formula | Src | What it does | Tested | Open issues/beads |
|---|---|---|---|---|
| codex-dispatch | mathcity | Route a task to the codex-worker for cross-model review/design | EXERCISED S12 (he-afo proved via codex) | codex is CLI not MCP (corrected #220 memory) |
| upf-experiment-dispatch | mathcity | Qualify + dispatch an experiment to the UPF server with breadcrumbs | EXERCISED S19 (aia-s27 dispatch live) | dispatcher no-infinite-loop policy |
| test-execution-request | mathcity | Classify, review, record explicit test-execution requests | NOT PROBED live | — |
| formula-creator-math | mathcity | Create a mathcity formula TOML with briefed-terminal enforcement, gated by a brief | EXERCISED S26 (fleet-address bug fixed) | — |
| lost-bead-classification-rollup / lost-bead-upstream-repair-rollup | mathcity | Group lost-bead fingerprints → filter-rule / repair-brief candidates | EXERCISED S36–S37 (reclaim filter era) | — |

## Reading rules

- **LIVE-PROVEN / EXERCISED** cite a session or artifact; anything else is `NOT PROBED` and
  must not be read as working.
- A formula's presence in the catalog does NOT mean the typed surface can sling it:
  `work_dispatch` hardcodes `work-briefed`; other formulas are reached through the router's
  four routes or direct `gc sling`.
- The full pack universe is larger (~150 TOMLs incl. bmad/compound/gstack/pr-review/ops
  packs not imported into this city's catalog); this file tracks only the 94 the city serves.
