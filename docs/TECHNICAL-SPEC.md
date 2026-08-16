# Mathcity Technical Specification

Parent: [../README.md](../README.md)

Mathcity is a Gas City pack for managing mathematical work by routing all
decision-worthy work through briefed workflows. The goal is to manage agent
output with structured filters: work is dispatched, evidence is collected, a
brief is produced, gates decide whether it is ready for a human, and the human
adjudicates the next action.

## System Objects

| Object | Technical role |
| --- | --- |
| Pack | Importable bundle of formulas, skills, orders, agents, policies, and docs. |
| Rig | Managed repository with its own bead store and work context. |
| Bead | Durable work item in `bd`; the canonical unit of task state. |
| Formula | TOML workflow with ordered steps and `gc.run_target` routing. |
| Order | Scheduled or event-driven trigger that pours a formula. |
| Skill | `SKILL.md` procedure used by agents or humans. |
| Brief | Decision artifact and `type=decision` bead awaiting adjudication. |
| Gate | Mechanical, review, stop, or manual condition for brief promotion. |
| Pile | Brief staging area before gate-checked promotion. |
| Stack | Human-presentable brief queue. |
| Event | Runtime signal such as `brief.decided` or `bead.closed`. |

See [../GLOSSARY.md](../GLOSSARY.md) for concise definitions.

## Work Intake

All ordinary work enters through `mathcity.work`. The front door selects the
right briefed workflow for the bead shape:

| Shape | Current surface | Result |
| --- | --- | --- |
| Bounded one-off work | `simple-work-briefed` | Execute a small task and file a brief. |
| Full implementation lifecycle | `build-basic-briefed` | Requirements, plan, decompose, implement, review, then brief. |
| Planning/design first | `planning-briefed` | Produce a plan and brief it before implementation. |
| Smoke or artifact testing | `smoke-test-briefed` via `testing-work` | Produce test script, results, `TESTING.md`, and brief. |
| Issue body handoff | `create-issue-briefed` | Draft issue body and brief it before filing. |
| PR body handoff | `pr-pipeline-briefed` | Draft PR body and brief it before opening a PR. |

Planned surfaces:

| Planned surface | Purpose | Tracker |
| --- | --- | --- |
| `mathcity doctor` | Tiered health/test/doc/example report. | #1 |
| `create-test-briefed` | Design and create meaningful tests from feature intent. | #2 |
| `formula-work` rework | Turn formula creation into plan -> formula -> docs -> tests -> brief lifecycle. | #3 |

## Brief Lifecycle

```text
source work
  -> brief producer
  -> pile
  -> brief-gate-keep
  -> brief-shuffle
  -> stack
  -> present-briefs
  -> adjudicate-brief
  -> brief.decided
  -> brief-decision-dispatch and file-or-sendback-route
  -> archive or follow-up work
```

Briefs are decision beads. The verdict is recorded on the brief bead by
`adjudicate-brief`; follow-up work is a new bead.

## Gate Profiles

The brief gate registry defines gate profiles for standard briefs,
no-brainers, test-execution briefs, and experiment briefs. The policy source is
[../subdomains/brief-system/POLICY.md](../subdomains/brief-system/POLICY.md);
the gate registry is [../assets/brief-pipeline/gates.toml](../assets/brief-pipeline/gates.toml).

| Path | Current expectation |
| --- | --- |
| Experiment | Breadcrumbed artifacts, test evidence or explicit N/A, cost/risk disclosure, and outcome interpretation. |
| Bug / MRE | Reproducible example or explicit blocker, root-cause evidence, and regression or smoke test path. |
| Feature | Documentation, examples, tests, worktree cleanup, and briefed handoff before publication. |
| Proof / math | LaTeX/proof-assist gates when relevant, provenance, and human review for primary mathematical claims. |
| Planning | Plan artifact and review before implementation. |
| Smoke test | `smoke-test-briefed` writes test script, results, `TESTING.md`, and a decision brief. |

## Repair And Feedback Formulas

| Formula | What it does |
| --- | --- |
| `brief-producer-failure-record` | Records a producer failure when a brief is rejected by shuffle/gates. |
| `brief-producer-failure-rollup` | Groups repeated producer failures and identifies repair candidates. |
| `brief-producer-repair` | Diagnoses repeated producer failure patterns and files a repair brief. |
| `no-brainer-candidate-curate` | Collects examples that may justify new no-brainer categories or gates. |
| `no-brainer-classify` | Classifies candidate briefs and records no-brainer decisions. |
| `brief-watchdog-refill` | Watches stack depth and requests refill work when the stack falls below target. |
| `brief-review-patrol` | Finds briefs stuck in review and advances or escalates them. |
| `lost-bead-classification-rollup` | Groups lost or stuck bead classifications by fingerprint. |
| `lost-bead-upstream-repair-rollup` | Converts repeated lost-bead fingerprints into upstream repair candidates. |

These loops are the self-correction surface. They do not silently change policy
or merge code; they produce evidence and briefs for human adjudication. Runtime
constraints for city execution live in
[../subdomains/dev/POLICY-city.md](../subdomains/dev/POLICY-city.md).

## Formula Creation

Current state:

- `formula-work` is a dev skill, not a formula.
- It dispatches `formula-creator-math`.
- `formula-creator-math` drafts a formula TOML and files the decision brief.

Known gap: a formula is not done unless it has documentation and tests. The
planned rework should make formula creation start with planning, then produce
the formula, examples, tests, index updates, and a terminal brief as one
workflow.

## Testing

Existing cheap coverage:

- `tests/stuck-bead-watch/test_stuck_bead_watch.py`
- `tests/tail-end-detector/test_tail_end_detector.py`
- `bash scripts/run-local-tests.sh`

`smoke-test-briefed` is the current formula for creating and recording
lightweight smoke-test evidence. `test-execution-request` is the gate for
risky, slow, costly, or otherwise non-silent test execution.

## Human Roles

| Role | Responsibility |
| --- | --- |
| Mayor | Coordinates city progress and runtime health. See [../README-mayor.md](../README-mayor.md). |
| Clerk | Presents briefs and records human verdicts. See [../README-clerk.md](../README-clerk.md). |
| Human adjudicator | Decides approve, reject, revise, or defer. |

The Mayor should not be brought online implicitly. Runtime actions require an
explicit request.
