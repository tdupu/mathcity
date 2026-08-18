# Gascity Bugs Brief MCTL PERT Implementation Plan

Parent: [Dev README](../../../README.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the two gascity lifecycle fixes safely, prove the new MathCity brief system end to end, add deterministic brief fast-drain behavior, and only then start MCTL.

**Architecture:** Treat this as a dependency-ordered PERT, not one large feature branch. Gascity fixes are upstream PRs with self-contained MREs and source-built `gc` binaries tested from the live city root. MathCity brief work stays source-side in `mathcity`, with existing unified-pipeline work on `main` as the baseline and MCTL delayed until the pile-to-stack contract is proven.

**Tech Stack:** Go and `go test` for gascity; `GOFLAGS=-tags=gms_pure_go make install` for local `gc` source builds; Gas City runtime commands from `<city-root>`; MathCity TOML formulas/orders, Python 3 standard library scripts, shell smoke tests, Beads/GitHub issue trackers, and Codex-backed Gas City workers when Anthropic usage is constrained.

## Global Constraints

- Current date for this plan is 2026-08-16.
- The 20X Anthropic account is at about 95% usage. Any live-city testing must be very efficient or routed through Codex-backed agents.
- Do not let provider scarcity drive broad config churn. Prefer existing Codex-pinned workers or a narrow temporary provider override using `switch-city-worker-provider`.
- `update-gascity-from-source` does not select an AI provider. It syncs `/Users/tdupuy/repos/gascity`, builds, installs `gc`, and verifies `/Users/tdupuy/gt`.
- Provider selection for existing cities is config-driven: per-agent `provider = "codex"`, `[agent_defaults] provider = "codex"`, legacy `[workspace] provider = "codex"`, or targeted `patches.agent.provider`.
- New cities can be initialized with `gc init --default-provider codex`, but `/Users/tdupuy/gt` is an existing city and currently has `[workspace] provider = "claude"`.
- MathCity already registers `[providers.codex]` in `pack.toml`, and `agents/codex-worker/agent.toml` uses `provider = "codex"`.
- Build and test gascity PR candidates from `/Users/tdupuy/repos/gascity`; start/stop/runtime verification runs from `/Users/tdupuy/gt`.
- Do not mutate live `.beads` or city runtime state for MRE proof unless the step explicitly says it is a controlled canary.
- Every upstream gascity issue and PR must state that the intended lifecycle policy is not fully specified yet, and must describe the policy assumption the fix implements.
- MCTL starts only after the new brief system has been tested end to end and the fast-drain plan has been reconciled with that evidence.

---

## Source References

| Item | Tracker | Branch / Plan | Current State |
| --- | --- | --- | --- |
| `gc start` false fatal after reload timeout | fork issue [tdupu/gascity#26](https://github.com/tdupu/gascity/issues/26), related fork WARN issue [tdupu/gascity#25](https://github.com/tdupu/gascity/issues/25), upstream issue [gastownhall/gascity#5333](https://github.com/gastownhall/gascity/issues/5333), upstream PR [gastownhall/gascity#5332](https://github.com/gastownhall/gascity/pull/5332) | `tdupu/gascity:fix/gc-start-reload-timeout-success-upstream` at `5edc31ef3`; older local integration branch `fix/gc-start-reload-timeout-success` | Hygienic issue filed; clean upstream PR open; focused tests and local `make lint-affected` passed; upstream CI re-running after lint cleanup |
| `gc start` WARN tickers for slow waits | [tdupu/gascity#25](https://github.com/tdupu/gascity/issues/25) | follow-on branch after false-fatal behavior is stable | Issue exists; implementation intentionally not started |
| `gc stop` launchd restart false positive | [tdupu/gascity#24](https://github.com/tdupu/gascity/issues/24), upstream issue [gastownhall/gascity#5324](https://github.com/gastownhall/gascity/issues/5324), upstream PR [gastownhall/gascity#5334](https://github.com/gastownhall/gascity/pull/5334) | `tdupu/gascity:fix/supervisor-stop-launchd-durable-upstream` at `fe91bd02f`; older local integration branch `fix/supervisor-stop-launchd-durable` | Clean upstream PR open; MRE/focused tests and local `make lint-affected` passed; upstream CI re-running after lint cleanup |
| Brief shuffler fast drain | [tdupu/mathcity#42](https://github.com/tdupu/mathcity/issues/42), external [tdupu/mathcity#40](https://github.com/tdupu/mathcity/issues/40), PR [tdupu/mathcity#43](https://github.com/tdupu/mathcity/pull/43) | [BRIEF-SHUFFLE-FAST-DRAIN-PLAN-2026-08-16.md](./BRIEF-SHUFFLE-FAST-DRAIN-PLAN-2026-08-16.md), branch `feat/brief-shuffle-fast-drain` including the final fix wave | Deterministic fast-drain implementation, source-local three-track E2E proof, docs update, and direct live-cache pile -> stack -> present canary passed; order/reload runtime canary intentionally not run while the city is stopped |
| MCTL | [tdupu/mathcity#41](https://github.com/tdupu/mathcity/issues/41) | [MCTL-MCP-IMPLEMENTATION-PLAN.md](./MCTL-MCP-IMPLEMENTATION-PLAN.md) | Plan exists; intentionally waits for brief E2E and fast-drain proof |
| Stale gate-profile branch | local `unified-brief-pipeline-gate-profiles` | pruned at `2885a42` | Superseded by `main`; no further action |
| Merged proof5 branch | local `feat/brief-pipeline-proof5-option-a` | pruned at `dd104207402832daca9a01aa94ba1950c4c97633` | Already merged into `main`; no further action |

## Execution Order

| PERT ID | Phase | Depends On | Output |
| --- | --- | --- | --- |
| 0 | Provider and usage preflight | none | Confirm whether Codex-backed workers can carry live E2E testing today |
| 1A | `gc start` false-fatal upstream issue and PR | 0 | Upstream issue, clean upstream branch, MRE, PR |
| 1B | `gc start` WARN tickers | 1A policy decision | Tests and branch update or follow-on PR |
| 1C | `gc stop` durable stop PR | 0 | Refreshed upstream branch, MRE, PR for #5324 |
| 2A | New brief system E2E across all three tracks | 1A and 1C source-build stability | Evidence that pile -> stack -> present works for all tracks |
| 2C | MathCity README/docs update | runs with 2A | Docs aligned with the tested brief system |
| 2B | Brief shuffler fast drain | 2A | Deterministic pile -> stack drain implementation and tests |
| 3 | MCTL implementation | 2A, 2B, 2C | MCTL starts against a proven brief cache contract |

## Task 0: Provider And Usage Preflight

**Files:**
- Read: `/Users/tdupuy/repos/gascity/docs/reference/cli.md`
- Read: `/Users/tdupuy/repos/gascity/docs/reference/config.md`
- Read: `/Users/tdupuy/repos/gascity/docs/tutorials/02-agents.md`
- Read: `/Users/tdupuy/repos/mathcity/subdomains/dev/skills/switch-city-worker-provider/SKILL.md`
- Read: `/Users/tdupuy/gt/city.toml`

**Interfaces:**
- Consumes: current city config and provider readiness.
- Produces: a decision on whether to run live E2E under current Claude workers, existing Codex workers, or a narrow temporary Codex override.

- [ ] **Step 1: Verify provider docs and resolved provider specs**

Run:

```bash
cd /Users/tdupuy/gt
gc config explain --provider codex --json
gc config explain --provider claude --json
```

Expected: both providers resolve. Codex should resolve to command `codex`; Claude should resolve to command `claude`.

- [ ] **Step 2: Verify MathCity Codex worker exists**

Run:

```bash
cd /Users/tdupuy/repos/mathcity
sed -n '1,40p' pack.toml
sed -n '1,80p' agents/codex-worker/agent.toml
```

Expected: `pack.toml` contains `[providers.codex]`; `agents/codex-worker/agent.toml` contains `provider = "codex"`.

- [ ] **Step 3: If live E2E needs workers today, smoke a Codex worker first**

Use `/Users/tdupuy/repos/mathcity/subdomains/dev/skills/switch-city-worker-provider/SKILL.md` exactly. Prefer Step 2 of that runbook, which proves an existing Codex worker spawn without editing `city.toml`.

Expected: a scratch bead starts a `provider=codex` session and closes or blocks loudly.

- [ ] **Step 4: Only if the smoke passes and usage requires it, apply a narrow temporary provider override**

Use the runbook's Step 4 only for the named worker needed for E2E, such as `mathcity.brief-operator`. Snapshot `city.toml` first and roll back after the test window.

Expected: no whole-city provider migration. The evidence directory records before/after agent and session state.

## Task 1A: `gc start` False-Fatal Upstream Issue And PR

**Files:**
- Modify upstream branch: `/Users/tdupuy/repos/gascity/cmd/gc/cmd_supervisor.go`
- Modify upstream branch: `/Users/tdupuy/repos/gascity/cmd/gc/cmd_supervisor_city.go`
- Modify upstream branch: `/Users/tdupuy/repos/gascity/cmd/gc/cmd_supervisor_city_test.go`

**Interfaces:**
- Consumes: fork branch `tdupu/gascity:fix/gc-start-reload-timeout-success` at `16339194a`.
- Produces: upstream issue in `gastownhall/gascity`, upstream PR branch based on `gastownhall/main`, and MRE evidence.

- [ ] **Step 1: File the upstream hygienic issue**

Target repo: `gastownhall/gascity`.

Issue must say:

```text
`gc start` can report failure when supervisor reload acknowledgement times out,
even though the city later reaches ready. Desired policy: a reload timeout is
not fatal to `gc start` if the city becomes ready inside the later readiness
wait. The command should fail only when readiness fails, or when the supervisor
reload error is a real non-timeout failure.
```

Also include:

```text
Related fork issue: https://github.com/tdupu/gascity/issues/25
Candidate branch: tdupu/gascity:fix/gc-start-reload-timeout-success
Candidate commit: 16339194a
```

- [ ] **Step 2: Create a clean upstream PR branch**

Run from `/Users/tdupuy/repos/gascity`:

```bash
git fetch origin --prune
git fetch fork --prune
git worktree add /private/tmp/gascity-pr-start-false-fatal origin/main -b pr/gc-start-reload-timeout-success
cd /private/tmp/gascity-pr-start-false-fatal
git cherry-pick 16339194aae1b003f8f2a7c638790b1b41428ceb
```

Expected: cherry-pick applies cleanly.

- [ ] **Step 3: Run focused unit evidence**

Run:

```bash
cd /private/tmp/gascity-pr-start-false-fatal
GOFLAGS=-tags=gms_pure_go go test ./cmd/gc -run TestRegisterCityWithSupervisorTreatsReloadTimeoutAsAsyncStart -count=1
```

Expected: PASS.

- [ ] **Step 4: Build and install the candidate `gc`**

Run:

```bash
cd /private/tmp/gascity-pr-start-false-fatal
GOFLAGS=-tags=gms_pure_go make install
gc version
go version -m "$(go env GOPATH)/bin/gc"
```

Expected: installed binary `vcs.revision` matches the PR branch HEAD and `vcs.modified=false`.

- [ ] **Step 5: Run a self-contained runtime MRE from the city root**

Run from `/Users/tdupuy/gt`, not from the source checkout. The MRE must use a temporary test city or fake supervisor endpoint. It must not start/stop the production city unless the test step explicitly asks for a controlled live canary.

Acceptance:

```text
Before fix: reload acknowledgement timeout makes `gc start` return failure even when city readiness later succeeds.
After fix: same scenario returns success when city readiness succeeds, with no false fatal.
```

- [ ] **Step 6: Push fork PR branch and open upstream PR**

PR body must include:

```text
Policy note: gascity currently does not fully specify whether supervisor reload
ack timeout is fatal when later city readiness succeeds. This PR adopts the
policy that readiness is authoritative for `gc start`; reload timeout is an
async reconcile condition unless readiness also fails.
```

## Task 1B: `gc start` WARN Tickers

**Files:**
- Modify upstream branch: `cmd/gc/cmd_supervisor_city.go`
- Modify upstream branch: `cmd/gc/cmd_supervisor_city_test.go`

**Interfaces:**
- Consumes: upstream policy decision from Task 1A and fork issue [tdupu/gascity#25](https://github.com/tdupu/gascity/issues/25).
- Produces: tests proving slow waits emit `WARN:` lines without changing success/failure semantics.

- [ ] **Step 1: Decide branch shape**

If Task 1A PR is not open yet, implement WARN tickers on `pr/gc-start-reload-timeout-success`. If Task 1A is already in review, create a follow-on branch from Task 1A.

- [ ] **Step 2: Write focused tests**

Tests must cover:

```text
slow supervisor reload wait emits periodic WARN while waiting
slow city-readiness wait emits periodic WARN while waiting
eventual success remains success
final readiness failure remains failure
stop/unregister paths do not inherit start warning text
```

- [ ] **Step 3: Implement testable warning cadence**

Use a small helper or local timer logic with production cadence around 30s. Tests may shrink existing timeout variables; do not sleep 30s in unit tests.

- [ ] **Step 4: Run focused tests and update PR or follow-on PR**

Run:

```bash
GOFLAGS=-tags=gms_pure_go go test ./cmd/gc -run 'Test.*Reload.*Warn|Test.*Readiness.*Warn|TestRegisterCityWithSupervisorTreatsReloadTimeoutAsAsyncStart' -count=1
```

Expected: PASS.

## Task 1C: `gc stop` Durable Stop PR

**Files:**
- Modify upstream branch: `/Users/tdupuy/repos/gascity/cmd/gc/cmd_supervisor.go`
- Modify upstream branch: `/Users/tdupuy/repos/gascity/cmd/gc/cmd_supervisor_lifecycle.go`
- Modify upstream branch: `/Users/tdupuy/repos/gascity/cmd/gc/cmd_supervisor_test.go`

**Interfaces:**
- Consumes: fork branch `tdupu/gascity:fix/supervisor-stop-launchd-durable` at `e40b94a4`.
- Produces: refreshed upstream PR branch, MRE evidence, and PR against `gastownhall/gascity#5324`.

- [ ] **Step 1: Create a clean upstream branch**

Run:

```bash
cd /Users/tdupuy/repos/gascity
git fetch origin --prune
git fetch fork --prune
git worktree add /private/tmp/gascity-pr-stop-launchd origin/main -b pr/supervisor-stop-launchd-durable
cd /private/tmp/gascity-pr-stop-launchd
git cherry-pick e40b94a42938f620db53c01882f2d855b2b4576b
```

Expected: conflict in `cmd/gc/cmd_supervisor_test.go` is possible. Preserve upstream test additions and add the durable-stop tests from the fork commit.

- [ ] **Step 2: Resolve the test-file overlap narrowly**

Do not merge the old fork base. Keep only the single durable-stop patch plus whatever edits are required for current `origin/main` tests.

Acceptance:

```text
git diff origin/main...HEAD
```

shows only the supervisor durable-stop code/test changes, not fork-main drift.

- [ ] **Step 3: Run focused unit evidence**

Run:

```bash
GOFLAGS=-tags=gms_pure_go go test ./cmd/gc -run 'TestUnloadSupervisorService|TestSupervisorStop|Test.*Launchd' -count=1
```

Expected: PASS for the durable-stop tests and neighboring supervisor lifecycle tests.

- [ ] **Step 4: Build and install the candidate `gc`**

Run:

```bash
GOFLAGS=-tags=gms_pure_go make install
gc version
go version -m "$(go env GOPATH)/bin/gc"
```

Expected: installed binary matches the PR branch HEAD and `vcs.modified=false`.

- [ ] **Step 5: Run a self-contained stop MRE from `/Users/tdupuy/gt`**

The MRE should fake or isolate launchd state so it proves durable stop behavior without risking the production supervisor. If a live canary is needed, it must use a temporary test city and record the exact launchd label/plist path before and after.

Acceptance:

```text
Before fix: `gc stop` can report success while launchd remains able to restart preserved sessions.
After fix: `gc stop` fails closed when platform stop/unload/disable is not durable.
```

- [ ] **Step 6: Open upstream PR**

PR target: `gastownhall/gascity`.

PR body must include:

```text
Fixes https://github.com/gastownhall/gascity/issues/5324

Policy note: gascity currently does not fully specify whether `gc stop` means
"best-effort stop request sent" or "the platform supervisor cannot immediately
restart the city." This PR adopts the durable-stop policy for launchd/systemd
registration paths and fails closed when the platform stop is not durable.
```

## Task 2A: Brief System End-To-End Baseline

**Files:**
- Inspect and test: `/Users/tdupuy/repos/mathcity/formulas/*brief*.toml`
- Inspect and test: `/Users/tdupuy/repos/mathcity/orders/*brief*.toml`
- Inspect and test: `/Users/tdupuy/repos/mathcity/skills/present-briefs/SKILL.md`
- Inspect and test: `/Users/tdupuy/repos/mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`
- Update docs with Task 2C.

**Interfaces:**
- Consumes: current MathCity `main`, including the unified brief pipeline work already merged through PR #37 and proof5.
- Produces: evidence that all three brief tracks move from pile to stack and are presentable.

- [ ] **Step 1: Commit or branch the existing dirty brief-system runtime repair bundle**

The dirty bundle is real work, not ignore noise. It includes:

```text
producer-failure backfill
decision gate evidence
terminal stack filtering
repair-rollup routing
local test-runner plumbing
README/testing-guide updates
```

Create a hygienic branch before further E2E work, such as:

```bash
cd /Users/tdupuy/repos/mathcity
git switch -c fix/brief-feedback-runtime-repair
```

- [ ] **Step 2: Run the targeted smoke tests that already passed in investigation**

Run:

```bash
cd /Users/tdupuy/repos/mathcity
bash tests/test-runner/test_runner_failure_propagation.sh
bash tests/decisions-to-briefs-gate-evidence/smoke_test.sh
bash tests/producer-decision-gate-profiles/smoke_test.sh
bash tests/brief-quality-failure-record-backfill/smoke_test.sh
bash tests/present-briefs-unified-source/smoke_test.sh
bash tests/producer-repair-e2e-red/red_test.sh
git diff --check
```

Expected: all commands pass.

- [ ] **Step 3: Define the three tracks explicitly before live E2E**

The E2E must include:

```text
Track 1: normal artifact or work brief
Track 2: decision-shaped brief from a producer such as planning, issue, PR, formula, commission, or smoke-test briefed
Track 3: producer-repair or rejected-brief feedback track
```

- [ ] **Step 4: Prove pile -> stack -> present for each track**

For each track, record:

```text
source bead id
brief bead id
pile path before shuffle
stack path after shuffle or fast-drain candidate
present-briefs output evidence
final decision or deliberate non-decision state
```

Do not run broad worker fleets under Claude while the 20X account is at 95%. Use Task 0's Codex route if live workers are needed.

## Task 2C: README And Documentation Update

**Files:**
- Modify: `/Users/tdupuy/repos/mathcity/README.md`
- Modify: `/Users/tdupuy/repos/mathcity/README-development.md`
- Modify: `/Users/tdupuy/repos/mathcity/SETUP.md`
- Modify: `/Users/tdupuy/repos/mathcity/docs/testing-guide.md`
- Modify: related plan files under `/Users/tdupuy/repos/mathcity/subdomains/dev/docs/plans/mcp/`

**Interfaces:**
- Consumes: Task 2A evidence.
- Produces: documentation that matches the tested brief-system behavior.

- [ ] **Step 1: Run the `update-README` or `improve-documentation` path after E2E evidence exists**

Use the existing MathCity documentation skill for the pass. The docs must not claim all three tracks work until Task 2A evidence exists.

- [ ] **Step 2: Replace ad hoc smoke loops with the local runner where appropriate**

Use:

```bash
bash scripts/run-local-tests.sh
```

Expected: README and testing docs point to the local runner for source-side MathCity checks.

- [ ] **Step 3: Record provider/usage constraints in the E2E handoff, not in general user docs**

The 95% Anthropic usage note belongs in this plan and execution handoffs. Do not turn it into a permanent README claim.

## Task 2B: Brief Shuffler Fast Drain

**Files:**
- Plan: [BRIEF-SHUFFLE-FAST-DRAIN-PLAN-2026-08-16.md](./BRIEF-SHUFFLE-FAST-DRAIN-PLAN-2026-08-16.md)
- Expected implementation files are listed in that plan.

**Interfaces:**
- Consumes: Task 2A E2E baseline.
- Produces: deterministic pile -> stack drain behavior for valid briefs.

- [ ] **Step 1: Re-read the fast-drain plan after Task 2A evidence**

Confirm the plan still matches the tested brief lifecycle. If the E2E finds a different authoritative cache contract, update the fast-drain plan before code changes.

- [ ] **Step 2: Create the implementation branch**

Use:

```bash
cd /Users/tdupuy/repos/mathcity
git switch -c feat/brief-shuffle-fast-drain
```

Expected: branch starts from a clean, tested brief-system baseline.

- [ ] **Step 3: Implement only the deterministic drain**

Do not redesign gate profiles, clear old live roots, move `.beads` ownership, or let producers write directly to `stack/`.

- [ ] **Step 4: Test both local fixtures and one controlled live canary**

Local tests must prove multi-item drain, locking, manifest/index preservation, rejected invalid briefs, and idempotence.

Live canary must record:

```text
input pile count
drained count
stack index rows
present-briefs sees the promoted briefs
no unrelated live roots deleted
```

## Task 3: MCTL Implementation

**Files:**
- Plan: [MCTL-MCP-IMPLEMENTATION-PLAN.md](./MCTL-MCP-IMPLEMENTATION-PLAN.md)
- Related plan: [BRIEF-SHUFFLE-FAST-DRAIN-PLAN-2026-08-16.md](./BRIEF-SHUFFLE-FAST-DRAIN-PLAN-2026-08-16.md)

**Interfaces:**
- Consumes: tested brief-system E2E, updated docs, and fast-drain cache contract.
- Produces: `mctl` CLI, then MCP, then dashboard, following the existing MCTL plan.

- [ ] **Step 1: Re-read MCTL after Tasks 2A, 2B, and 2C**

Expected: MCTL treats pile, stack, indexes, and brief cache files as derived state to inspect and validate. The bead store remains the source of truth.

- [ ] **Step 2: Update MCTL plan if the fast-drain implementation changes cache semantics**

Only update the plan. Do not start implementation until the updated plan is internally consistent and references the final fast-drain behavior.

- [ ] **Step 3: Start MCTL Slice 1**

Start with the MCTL context resolver and CLI skeleton from the MCTL plan. Do not build MCP or dashboard surfaces first.

## Verification Before Completion

This plan is complete only when:

- Both gascity bug branches are either upstream PRs or explicitly blocked with issue-linked MRE evidence.
- The `gc start` upstream issue exists and references `fix/gc-start-reload-timeout-success`.
- The `gc stop` PR references `gastownhall/gascity#5324`.
- Gascity runtime verification uses a source-built binary from `/Users/tdupuy/repos/gascity` and city commands from `/Users/tdupuy/gt`.
- MathCity brief-system E2E evidence covers all three tracks.
- The fast-drain implementation starts after, not before, the E2E baseline.
- MCTL starts after the fast-drain contract is known.
- Any temporary Codex provider override is rolled back or explicitly extended by the human adjudicator.
