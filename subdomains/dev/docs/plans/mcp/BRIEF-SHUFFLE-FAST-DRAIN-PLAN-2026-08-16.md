# Brief Shuffle Fast Drain - Implementation Plan

Parent: [Dev README](../../../README.md)

> **For agentic workers:** REQUIRED SUB-SKILL: use
> `superpowers:executing-plans` to implement this plan task-by-task. If multiple
> agents are active, use `communicate-with-other-agent` before editing overlapping
> files and keep issue #40 as the coordination anchor.

**Goal:** Fix the slow and disconnected brief-presentation path where valid
briefs can sit in `.beads/briefs/.pile` for hours because `brief-shuffle` is
LLM-driven, single-item, and blocked by old open workflow roots.

**Architecture:** Add a deterministic fast-drain order and script that owns the
mechanical `.pile -> stack` boundary. Keep producers forbidden from writing the
stack directly. Disable new dispatches of the old slow `brief-shuffle-pile`
order, but do not delete or close existing live roots.

**Tech Stack:** gascity orders and formulas, Python 3 standard library
(`tomllib`, `pathlib`, `json`, `fcntl` where available), bash smoke tests,
existing brief policy and gate profile files.

Related plan: [MathCity mctl MCP Hardening](./MCTL-MCP-IMPLEMENTATION-PLAN.md). The MCTL plan should treat this fast-drain work as the concrete `.pile -> stack` cache-writer contract for brief inspection, validation, MCP, and dashboard surfaces.

**Spec / Tracker:** [tdupu/mathcity#40](https://github.com/tdupu/mathcity/issues/40)

## Current Finding

The brief operator claim checks out: the system is not dead, but the effective
throughput is too low for the user-facing promise in B2.10.

Observed live-state summary:

- There are 14 open `brief-shuffle` roots in the city.
- 7 roots are untouched and 7 are partially executed.
- The current `brief-shuffle` formula processes at most one pile item per run.
- Old open roots block fresh `brief-shuffle-pile` dispatch through the `gc order`
  open-work gate.
- After an 8-brief deposit, only one brief promoted, one staged, and six remained
  in `.pile`.

This violates the intended user experience: every adjudicable brief should enter
one user-visible pipeline:

```text
.pile -> brief-shuffle gate -> stack -> present-briefs
```

The failure mode is latency and hidden backlog, not a missing pile or stack.

## Scope

Implement this on the live implementation side first:

```text
<repo-root>
```

This document is stored next to the MCTL implementation plan in the source repository so an implementation agent can consume both plans together:

```text
subdomains/dev/docs/plans/mcp/
```

Do not bulk-migrate or rewrite unrelated brief-pipeline work as part of this
issue. Issue #40 is the fast-drain and order-blocking fix only.

## Non-Goals

- Do not clear or delete the existing 14 live `brief-shuffle` roots.
- Do not let producers write directly to `stack/`.
- Do not redesign all gate profiles in this issue.
- Do not move `.beads` ownership between `<city-root>` and `<repo-root>` in this issue.
- Do not convert this into a new LLM classifier project.

## Files To Touch

Expected implementation files:

| File | Change |
| --- | --- |
| `assets/scripts/brief-shuffle-fast-drain.py` | New deterministic batch drain script. |
| `orders/brief-shuffle-fast-drain.toml` | New order with a distinct scoped name from `brief-shuffle-pile`. |
| `orders/brief-shuffle-pile.toml` | Disable or retire new dispatches from the old slow order. |
| `tests/brief-shuffle-fast-drain/test_brief_shuffle_fast_drain.py` | New focused unit or integration tests. |
| `tests/brief-shuffle-fast-drain/smoke_test.sh` | New smoke test for formula/order contract and CLI behavior. |
| `README-formulas.md` or matching order index | Document the new order, if this repo indexes orders there. |
| `subdomains/brief-system/POLICY.md` | Small clarification that `brief-shuffle-fast-drain` is the mechanical gate implementation for B2.10. |

Avoid committing unrelated dirty files. Commit only the files above unless the
implementation proves another file is directly required.

## Design

### 1. Add a deterministic fast-drain script

Create:

```text
assets/scripts/brief-shuffle-fast-drain.py
```

Required CLI:

```text
python3 assets/scripts/brief-shuffle-fast-drain.py \
  --brief-root <city-root>/.beads/briefs \
  --gate-config assets/brief-pipeline/gates.toml \
  --max-items 3 \
  --apply
```

Required flags:

| Flag | Behavior |
| --- | --- |
| `--brief-root PATH` | Root containing `.pile`, `stack`, `.staging`, and rejection directories. |
| `--gate-config PATH` | TOML gate profile file. |
| `--max-items N` | Bound each run so the order is predictable. Default should be conservative, such as `3`. |
| `--apply` | Perform moves. Without this flag, run as dry-run. |
| `--json` | Emit machine-readable summary for tests and runtime logs. |
| `--no-external` | Disable optional `gc events` or repair-bead side effects during tests. |

Dry-run must be the default. The city order should pass `--apply`.

### 2. Preserve the single-writer boundary

The fast drain is the stack writer. Producers still file into `.pile`.

For each selected pile item:

```text
.pile/<slug>.md
  -> .staging/fast-drain-<pid>-<slug>/brief.md
  -> stack/<slug>.md OR .pile/.rejected/<slug>.md
```

The staging directory must include a small marker such as:

```text
.claimed_by
```

The marker should identify `brief-shuffle-fast-drain`, host, pid, timestamp, and
source path. The script must not remove staging directories it did not create.

### 3. Evaluate gate profiles mechanically

Use `assets/brief-pipeline/gates.toml`.

Profile selection:

- Read frontmatter from the brief.
- Use `gate_profile` if present.
- Otherwise use `standard`.

Pass rule:

- Every required gate for the selected profile must have an evidence line with
  status `PASS` or `N/A`.
- If a required gate is missing, `FAIL`, `BLOCKED`, or `PENDING`, reject.
- Unknown profiles reject with a clear reason.

Recommended evidence line shape:

```text
G4 Critical-review: PASS - reviewed by ...
```

Do not omit failures. Runtime canaries and bad briefs should include explicit
failure evidence, for example:

```text
G4 Critical-review: FAIL - controlled runtime canary
```

### 4. Keep profile-specific checks

The fast drain should preserve the existing profile intent:

| Profile | Minimum check |
| --- | --- |
| `standard` | Required gate evidence, valid frontmatter, provenance present. |
| `decision` | Decision brief metadata present and ready for user presentation. |
| `lost_bead_filter` | Filter provenance and source bead metadata present. |
| `producer_repair` | Original producer or source failure metadata present. |
| `no_brainer` | Classifier evidence present; never silently skip presentation unless policy explicitly permits it. |

If these checks already exist in `assets/scripts/checks/brief-check.sh`, reuse
their semantics. Do not invent looser semantics in Python.

### 5. Append the stack index atomically

On promotion, move the brief into:

```text
.beads/briefs/stack/<slug>.md
```

Then append one JSON line to:

```text
.beads/briefs/stack/.index.jsonl
```

Required row fields:

```json
{
  "slug": "brief-slug",
  "path": "stack/brief-slug.md",
  "source": ".pile/brief-slug.md",
  "gate_profile": "standard",
  "unlock_count": 0,
  "created_at": "2026-08-16T00:00:00Z"
}
```

Use a short lock file during append:

```text
.beads/briefs/stack/.manifest.lock
```

The index append must be idempotent for an already-promoted slug.

### 6. Reject bad briefs into durable feedback

Rejected briefs move to:

```text
.beads/briefs/.pile/.rejected/<slug>.md
```

Write a rejection sidecar:

```text
.beads/briefs/.pile/.rejected/<slug>.rejection.json
```

Minimum rejection fields:

```json
{
  "slug": "brief-slug",
  "gate_profile": "standard",
  "reason": "missing required gate G4 Critical-review",
  "source_path": ".pile/brief-slug.md",
  "rejected_at": "2026-08-16T00:00:00Z"
}
```

If producer provenance is present, record the durable producer-failure signal
using the same location and shape expected by the existing producer-repair
workflow. If that location is unclear, add the rejection sidecar now and create
a follow-up bead or GitHub issue rather than blocking the fast-drain fix.

### 7. Add a new order with a new scoped name

Create:

```text
orders/brief-shuffle-fast-drain.toml
```

The important property is the order name: it must not share the old
`order-run:brief-shuffle-pile` scoped name. A distinct order avoids being
blocked by the existing open roots.

Order behavior:

- Run periodically or on the same condition used by the old pile shuffler.
- Dispatch to an appropriate local pool or zero-token worker if one exists.
- Execute the deterministic script with `--apply --max-items 3`.
- Emit a clear summary: promoted count, rejected count, skipped count,
  remaining pile count.

### 8. Disable new dispatches from the old order

Modify:

```text
orders/brief-shuffle-pile.toml
```

The old order should stop creating new slow LLM roots. Existing open roots
should be left alone.

Preferred approach:

- Add a clear disabled condition if the order format supports it.
- Add a comment naming issue #40 and the replacement order.

Fallback approach:

- Rename the old order file to a documented legacy filename only if the order
  loader treats disabled conditions poorly.

Do not close, delete, or rewrite live roots as part of this change.

## Test Plan

Write RED tests before implementation where practical.

### Focused tests

Run:

```bash
python3 -m pytest tests/brief-shuffle-fast-drain/test_brief_shuffle_fast_drain.py -v
```

Required cases:

- A valid `standard` brief with all required gate evidence promotes to `stack/`.
- A `decision` profile brief with required evidence promotes to `stack/`.
- A brief missing G4 rejects to `.pile/.rejected/`.
- A brief with explicit `G4 Critical-review: FAIL` rejects and records the
  failure reason.
- `--max-items 1` promotes or rejects only one item.
- Dry-run changes no files and reports planned actions.
- `.index.jsonl` gets one row per promoted slug.
- Re-running after promotion does not duplicate the index row.
- Unknown `gate_profile` rejects.
- Staging directories not claimed by `brief-shuffle-fast-drain` are not removed.

### Smoke tests

Run:

```bash
bash tests/brief-shuffle-fast-drain/smoke_test.sh
bash tests/lockless-brief-shuffle/smoke_test.sh
bash tests/unified-brief-pipeline-e2e/smoke_test.sh
```

The smoke test should assert:

- New order exists.
- New order uses the new script.
- New order name differs from `brief-shuffle-pile`.
- Old order no longer dispatches new slow work.
- Required gate config profiles still parse.
- Controlled bad brief fails with an explicit `FAIL` evidence line, not omitted
  evidence.

### Live test

After local tests pass, test in the live city carefully.

Commands:

```bash
gc reload
python3 assets/scripts/brief-shuffle-fast-drain.py \
  --brief-root <city-root>/.beads/briefs \
  --gate-config assets/brief-pipeline/gates.toml \
  --max-items 1 \
  --json
python3 assets/scripts/brief-shuffle-fast-drain.py \
  --brief-root <city-root>/.beads/briefs \
  --gate-config assets/brief-pipeline/gates.toml \
  --max-items 1 \
  --apply \
  --json
```

Verify:

- `.pile` count decreases by one when an eligible brief exists.
- `stack/` receives the promoted brief.
- `stack/.index.jsonl` receives exactly one row for the promoted slug.
- `present-briefs` can see the newly promoted brief.
- Bad canary brief lands in `.pile/.rejected/` with explicit rejection evidence.
- No new `brief-shuffle-pile` roots are created after reload.

### Runtime canary

Create one dedicated test-only brief with a unique slug and obvious provenance.
It should be a producer-origin standard brief failing G4.

Required markings:

```text
runtime_canary: true
test_only: true
provenance: brief-shuffle-fast-drain-runtime-canary
G4 Critical-review: FAIL - controlled runtime canary
```

Keep it as durable evidence, but clearly mark it as a runtime canary artifact.

## Rollout Plan

1. Work on a branch in `<repo-root>`.
2. Read local instructions and confirm the dirty tree before editing.
3. Add RED tests for fast-drain behavior.
4. Implement the script.
5. Add the new order.
6. Disable new dispatches from the old order.
7. Update policy or docs with a minimal note.
8. Run focused tests.
9. Run smoke tests.
10. Run the one-item live dry-run and apply test.
11. Record test evidence in `.gc/pr-body-evidence/<branch>.md`.
12. Use `pr-pipeline-briefed` directed at `<repo-root>` and
    issue #40.
13. Push the branch and open a PR to `tdupu/mathcity`.

## Coordination Notes

If another agent is implementing similar work, coordinate on these boundaries:

- One agent owns the deterministic script and tests.
- One agent owns order wiring and old-order retirement.
- One agent verifies live runtime behavior after `gc reload`.
- Nobody closes or deletes existing live roots.
- Nobody broadens issue #40 into the full unified-pipeline migration.

Questions that should be resolved before merging:

- Does the order runner support a clean disabled condition for
  `brief-shuffle-pile.toml`?
- Is there an existing zero-token or shell-run pool that should own this order?
- What exact producer-failure sidecar location is already consumed by the repair
  pipeline?
- Should the batch size be `3` or `5` for normal city runtime?

Recommended defaults if no one objects:

- Use `--max-items 3` for scheduled runtime.
- Use `--max-items 1` for the first live apply test.
- Reject unknown profiles rather than falling back to `standard`.
- Keep the old order file with a disabled condition and explanatory comments.

## Acceptance Criteria

- Valid briefs no longer wait behind old `brief-shuffle-pile` roots.
- A single scheduled run can process more than one pile item.
- Passing briefs land in `stack/` and are visible to `present-briefs`.
- Failing briefs land in `.pile/.rejected/` with durable rejection evidence.
- Controlled bad brief includes explicit failure evidence.
- Existing live roots are not destroyed.
- Focused tests and smoke tests pass.
- Live one-item drain proves the path in the running city.
- PR references issue #40 and includes test evidence.

