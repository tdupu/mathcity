# Mayor Workflow Refactor Evidence

Date: 2026-08-16

Purpose: preserve the evidence and design findings from the Mayor workflow
brainstorming session. This is not an implementation plan. It is an evidence
brief for a future designer who will refactor `mayor-math-prime`,
`mayor-math-handoff`, and their interaction with the planned `mctl` control
plane.

## Executive Summary

Two concrete defects triggered this investigation.

First, `mayor-math-prime` and `mayor-math-handoff` have grown into a combined
prompt, state database, history index, operating doctrine, handoff procedure,
evaluation ledger, and behavioral correction system. The current restart
prompt measured 51,220 bytes during the discussion. Its largest rendered
sections were prior session summaries, the full handoff bead, and the prior
objective evaluation table. The static Jinja template itself was only 8,531
bytes, so the primary growth source is accumulated rendered history and
handoff data, not static instructions alone.

Second, `mayor-math-handoff` already records `objectives_eval` and explicitly
names a future `check-mayor-objectives` skill, but that skill was never built.
As a result, 19 Mayor sessions accumulated objective-evaluation records without
the promised feedback loop being processed. The system collected evidence about
what worked and failed, but did not turn that evidence into new steering rules.

The core finding is that the Mayor should be treated as production control for
a factory, not as a free-form worker with an ever-growing prompt. The Mayor
needs a minimal bootstrap prompt, typed context tools, quantitative activity
metrics, and a standard shift routine. Routine measurement, linting, rendering,
history search, and objective validation should be scripts or `mctl` calls.
The agent should supply judgment only where interpretation is required.

## Evidence Sources

Local evidence used during the brainstorming session:

- `<city-root>/mathcity-mayor/session-catalog.json`
- `<city-root>/mathcity-mayor/session-catalog-recent.json`
- `<city-root>/mathcity-mayor/restart/PROMPT-mayor-restart.txt`
- `<city-root>/mathcity-mayor/restart/PROMPT-mayor-restart.j2`
- `<city-root>/mathcity-tests/run-log/S43.md`
- `<repos-root>/mathcity/skills/mayor-math-prime/SKILL.md`
- `<repos-root>/mathcity/skills/mayor-math-handoff/SKILL.md`
- `<repos-root>/mathcity/subdomains/dev/docs/plans/mcp/MCTL-MCP-IMPLEMENTATION-PLAN.md`
- `<repos-root>/mathcity/subdomains/dev/docs/plans/mcp/SKILL-IMPACT-REGISTER.md`
- GitHub issue `tdupu/mathcity#41`: `mctl` CLI, MCP, and dashboard control plane
- GitHub issue `tdupu/mathcity#40`: brief-shuffle fast-drain contract

Measured prompt and catalog sizes from the session:

| Artifact | Bytes |
| --- | ---: |
| Restart prompt text | 51,220 |
| Restart prompt Jinja template | 8,531 |
| Full session catalog | 150,667 |
| Recent session catalog | 43,923 |
| S43 run-log shard | 9,601 |

Rendered restart prompt section sizes:

| Section | Bytes |
| --- | ---: |
| Background | 3,875 |
| Work done by previous Mayor sessions | 21,194 |
| Current objectives | 1,719 |
| Prior objective evaluation | 5,873 |
| Full handoff bead | 13,674 |
| State of the city | 180 |
| Repo-side helper | 259 |
| Standing rules | 1,929 |
| Current charge | 2,128 |

## Current Workflow Problem

The current Mayor workflow mixes several different responsibilities:

1. Identity and role definition.
2. Standing doctrine.
3. Current state rendering.
4. Full historical memory.
5. Objective setting and evaluation.
6. Handoff narrative.
7. Evidence validation.
8. Brief and work operations.
9. Agent coordination.
10. Behavioral correction from past failures.

Putting all of these into the restart prompt creates a failure mode: the Mayor
receives a large narrative, but the actual control loop is weak. The evidence is
present, but it is not enforced.

The refactor should separate:

- context generation,
- operational control,
- measurement,
- history search,
- objective validation,
- shift handoff,
- agent judgment.

## Principle: No Information Dumping

The Mayor should not be primed with the full session history, full handoff
bead, full evaluation table, or full policy corpus. The Mayor should receive a
small, bounded prime packet and retrieve extra context through typed tools.

The proposed prompt shape is:

1. Minimal identity and role.
2. Available typed tools.
3. Current steering state.
4. Current bottleneck or shift target.
5. Blocking diagnostics.
6. Links or commands for additional context.

Everything else should be available on demand through context tools or `mctl`.

## Information Baskets

The handoff and prime currently contain or point to multiple kinds of
information. These should become separate context bundles, not one large
prompt.

| Basket of information | Use it when |
| --- | --- |
| Static Mayor identity | Every prime; should be tiny. |
| Standing doctrine | Every prime as short identifiers; full text on demand. |
| Current objectives or shift target | Every prime and every work-selection decision. |
| Objective evaluation history | During objective proposal and validation, not inline. |
| Failure lessons | Before diagnosis, dispatch, or handoff. |
| Current city snapshot | Before deciding "stalled", "healthy", or "ready". |
| Pending briefs | When Taylor input or clerk/app work is needed. |
| Work queue | When feeding the machine or identifying the bottleneck. |
| Current handoff bead | Prime, excerpt only; full bead on demand. |
| Latest run-log shard | When continuing prior session work. |
| Full session history | Search only. Never inline all sessions. |
| Policies and playbooks | On demand by action type: bring-up, test, dispatch, dogfood. |
| Agent and inbox state | At prime and before concluding work is stalled. |
| Source evidence | Before claims, closures, fixes, and config changes. |
| Carryover ledger | During objective or shift-target setting. |

These baskets are also the natural Mayor prompt fragments:

| Prompt or bundle | Static or dynamic | Update rule |
| --- | --- | --- |
| `mayor-core.static` | Static | Rare role/doctrine changes only. |
| `mayor-doctrine.static` | Mostly static | Policy or bead-rule changes. |
| `mayor-prime.generated` | Dynamic | Every prime. |
| `mayor-objectives.generated` | Dynamic | Prime and handoff. |
| `mayor-state.generated` | Live | On command, short TTL. |
| `mayor-failures.generated` | Dynamic | After catalog/run-log update. |
| `mayor-history.searchable` | Index | Updated from catalog and run-log shards. |
| `mayor-handoff.generated` | Dynamic | End of session. |

## Scriptable Mayor Functions

The rule should be: if a task has structured inputs, deterministic checks, and
structured outputs, a script or typed `mctl` call should perform it. The Mayor
agent should not spend context doing routine measurement, linting, rendering,
searching, or reference checks.

| Function | Proposed replacement | Why Python or bash can do it | Covered by current `mctl` plan |
| --- | --- | --- | --- |
| Resolve city, rig, and source context | `mctl context` | Read cwd, config, rig metadata, and source path; emit typed context or diagnostics. | Yes |
| Brief list/show/options/doctor/adjudicate/defer | `mctl briefs ...` | Parse canonical bead state and redundant brief artifacts; use effect plans for mutations. | Yes |
| Work ready/status/provenance/dispatch | `mctl work ...` | Query bead/work state and dispatch provenance; use typed inputs and trace IDs. | Yes |
| Trace/audit lookup | `mctl trace ...` | Read trace records and render structured output. | Yes |
| Render prime context under budget | `mctl mayor context prime --budget 8kb` | Assemble known sections, count bytes/tokens, omit or link over-budget sections. | No, add Mayor namespace |
| Validate catalog/recent/prompt consistency | `mctl mayor catalog lint` | Validate JSON schema, contiguous sessions, recent/full drift, and handoff match. | No |
| Analyze objective failures | `mctl mayor objectives check` | Apply classifier and validator rules over `objectives_eval` rows. | No |
| Propose next objectives | `mctl mayor objectives propose` | Use failure history, carry counts, current state, and blocking diagnostics to draft candidates. | No |
| Generate handoff scaffold | `mctl mayor handoff scaffold` | Generate required JSON fields, prior objective rows, run-log template, and prompt input. | No |
| Validate handoff draft | `mctl mayor handoff doctor` | Resolve bead IDs, paths, command names, prompt budget, and catalog shape. | Partly `check-zero`, but not typed |
| Search history/run-log/catalog | `mctl mayor history search` | Index local JSON and markdown; return source-linked hits. | No |
| Generate failure digest | `mctl mayor failures digest` | Count recurring failure classes and open unresolved lessons. | No |
| Current city snapshot | `mctl mayor state snapshot` | Aggregate `tmux`, `bd`, `gc`, brief, inbox, and Dolt sources with source labels. | Partly context/work, needs aggregate |
| Prompt size and context budget | `mctl mayor prompt budget` | Count bytes and reject or warn above thresholds. | No |
| Displacement log | `mctl mayor displacement-log` | Record planned work displaced by emergencies and assign a disposition. | No |

Candidate command family:

```text
mctl mayor context prime --budget 8kb
mctl mayor catalog lint
mctl mayor objectives check
mctl mayor objectives propose
mctl mayor objectives set --dry-run
mctl mayor history search <query>
mctl mayor failures digest
mctl mayor state snapshot
mctl mayor handoff scaffold
mctl mayor handoff doctor
mctl mayor activity report
mctl mayor activity compare --from S25 --to S43
```

## Agent-Required Mayor Functions

The agent remains necessary where judgment, interpretation, or coordination is
the core task.

| Function | Why an agent is still needed |
| --- | --- |
| Choose priorities under conflicting instructions | Taylor's live instruction can override the handoff. |
| Identify the current bottleneck | Requires interpreting metrics and deciding what matters. |
| Judge causality and evidence quality | Scripts collect evidence; the agent identifies the load-bearing cause. |
| Write honest narrative and retractions | Handoff needs synthesis and accountability. |
| Coordinate with Taylor, BART, clark, Codex, and fleet agents | Requires protocol and social judgment. |
| Decide whether a repeated failure needs policy, code, bead, or no action | This is system design, not a deterministic check. |
| Handle mathematical or source-code claims | Requires reasoning beyond state inspection. |
| Frame good objectives or shift targets | Tooling can validate, but the agent chooses intent. |
| Notice stale generated warnings | A generated digest may be obsolete or superseded. |

The desired model is "agent in a cage": the agent can reason and decide, but it
must operate through typed tools and fail-closed checks for state mutation.

## MCTL Alignment

The planned `mctl` work is the correct control plane for this refactor. The
future designer should avoid building separate Mayor, Clerk, brief, and
dashboard MCP systems. That would recreate today's prompt-skill drift in tool
form.

Recommended design:

- One `mctl` core.
- One typed MCP server over that core.
- Namespaced tools for `context_*`, `briefs_*`, `work_*`, `trace_*`.
- A narrow Mayor namespace for session lifecycle, context, objectives, history,
  activity metrics, and handoff validation.
- No generic `run_shell`, `run_gc`, `run_bd`, or `run_mctl(command: string)`
  tool.

Operations that belong in the existing `mctl` plan:

- context resolution,
- brief read/doctor/options,
- brief adjudication/defer/create/validate,
- work ready/status/provenance/dispatch,
- trace lookup and replay preview.

Operations to add as Mayor-specific `mctl` extensions:

- prime context generation,
- objective checking/proposal,
- handoff scaffold/doctor,
- history search,
- failure digest,
- activity and plant-status reports,
- displacement logging,
- prompt budget enforcement.

## Scripted Mayor Shape

Long-term, the Mayor session can be run through scripted shift-start and
shift-end routines.

Prime routine:

```text
mctl mayor run prime
  -> resolve context
  -> lint catalog/prompt
  -> generate compact context
  -> check objective or shift-target quality
  -> snapshot city
  -> list ready briefs/work
  -> compute bottleneck candidates
  -> ask agent only for priority judgment
```

Handoff routine:

```text
mctl mayor run handoff
  -> scaffold catalog entry
  -> require objective/shift-target evaluation
  -> validate claims and references
  -> record production numbers
  -> record displacement
  -> propose next objectives or shift target
  -> reject bad objectives
  -> render next compact prompt
```

This shape keeps the Mayor from free-form context drift. Scripts handle the
routine work; the agent handles interpretation and steering.

## Operations Engineering Model

The best abstraction is to treat MathCity as a factory and the Mayor as
production control.

Value stream:

```text
demand -> triage -> brief/issue -> dispatch -> execution -> review -> merge/close -> validation
```

Factory-management tools that apply:

| Factory tool | Mayor equivalent |
| --- | --- |
| Value stream mapping | Map brief/work/PR lifecycle from request to done. |
| Theory of Constraints | Identify and protect the current bottleneck. |
| Kanban / CONWIP | Discover all work, but limit active WIP at the bottleneck. |
| Little's Law | Track WIP, throughput, and lead time. |
| Andon cord | Escalate when a tool lies or a queue breaches SLA. |
| Standard work | Script prime and handoff as shift routines. |
| Statistical process control | Watch trends, not anecdotes. |
| A3 / 5 Whys | Require structured root cause for recurring failures. |
| RACI / DRI | Every work item has one owner and one decision authority. |
| First-pass yield | Measure quality and rework in briefs and work items. |
| CAPA | Convert repeated failures into corrective and preventive actions. |

Important distinction: adding more tasks to the backlog should not reduce
throughput if the system is pull-based and bottleneck-protected. The limit is
not backlog discovery. The limit is uncontrolled active WIP.

## Mayor Standard Work

Standard work identified from the current Mayor logs:

At prime:

1. Resolve runtime/source context.
2. Read compact steering packet.
3. Check city health and active runtime state.
4. Check pending briefs and decisions.
5. Check active work and molecules.
6. Check inbox and agent coordination state.
7. Identify current bottleneck.
8. Choose one primary shift target.

During the shift:

1. Do not hand-work unless it removes the bottleneck or reduces critical risk.
2. Pull from the highest-cost queue.
3. Dispatch or escalate only through typed tools.
4. Trigger an Andon event if instruments disagree.
5. Convert interruptions into explicit displacement records.
6. Keep the Mayor available for Taylor and high-leverage decisions.

At handoff:

1. Record production numbers.
2. Evaluate the shift target.
3. Record bottleneck movement.
4. Record defects and rework.
5. Record displaced work and its disposition.
6. Propose the next shift target from measured state.
7. Validate claims, paths, commands, beads, and prompt budget.

The steering primitive:

```text
What is the current bottleneck?
What evidence says so?
What is the smallest action that increases throughput or reduces risk?
What work is displaced by this choice?
```

This is stronger than asking only whether the Mayor completed the inherited
objectives.

## Quantitative Activity Ledger

Objectives are not enough to describe a session. A Mayor can miss objectives
while doing valuable emergent work, or complete trivial objectives while not
improving the factory. The refactor needs a quantitative activity ledger.

Metrics to track:

| Metric | Why it helps |
| --- | --- |
| Beads created / closed / reopened | Measures work graph churn and completion. |
| Beads by status/type/priority | Shows backlog shape and whether Mayor is creating or reducing WIP. |
| Objectives yes/partial/no | Keeps intended work visible. |
| Additional-work count | Measures displacement. |
| GitHub issues opened/closed/commented | Tracks public repo output. |
| PRs opened/merged/closed | Tracks integration throughput. |
| Commits pushed | Tracks source movement. |
| Worktrees opened/closed/purged | Tracks cleanup discipline. |
| Briefs created/promoted/adjudicated/rejected/deferred | Tracks clerk and decision flow. |
| Molecules dispatched/completed/failed | Tracks fleet throughput. |
| Agent messages sent/acked | Tracks coordination load. |
| Runtime incidents opened/resolved | Tracks interruption pressure. |
| Prompt bytes/context bytes | Tracks Mayor bloat directly. |
| Median and 95th percentile lead time | Tracks flow health. |
| WIP age by queue | Reveals hidden stuck work. |
| First-pass yield | Tracks quality. |
| Rework count | Tracks bad upstream specs or weak gates. |
| Blocked work count | Tracks coordination drag. |
| Instrument disagreement count | Tracks reliability risk. |
| Emergency displacement count | Tracks planning instability. |

Metrics that can be computed now or nearly now:

| Statistic | Can compute now? | Source |
| --- | --- | --- |
| Objective yes/partial/no | Yes | Session catalog. |
| Additional work per session | Yes | Session catalog. |
| New objectives per session | Yes | Session catalog. |
| Prompt size | Yes | Prompt file. |
| Brief pile/stack counts | Likely | `.beads/briefs`. |
| Bead status counts | Maybe | `bd`/Dolt or passive export. |
| Beads closed per day | Maybe | `bd`/Dolt. |
| Issue/PR opened/closed | Yes | `gh`. |
| Commit count by session window | Yes if time windows are reliable | Git history. |
| Lead time per brief/bead | Only if timestamps are available | Beads/brief artifacts. |
| First-pass yield | Needs gate/rejection records | Brief/work outcome data. |
| Rework rate | Needs linked failure/remediation records | Producer-failure and remediation records. |
| Instrument disagreement count | Needs explicit incident records | New instrumentation. |

## Little's Law

Little's Law gives the Mayor a way to test whether the factory's promise is
plausible:

```text
WIP = throughput * lead_time
lead_time = WIP / throughput
```

For briefs:

```text
WIP = count(.pile + stack + in-review + ready-deferred)
throughput = briefs adjudicated or promoted per day
lead_time = adjudicated_at - created_at
```

For work:

```text
WIP = open or in-progress molecule roots plus active beads
throughput = closed beads or completed molecules per day
lead_time = closed_at - created_at
```

If WIP is 30 and throughput is 6 per day, expected lead time is 5 days. This
turns "soon" into a measurable claim.

## First-Pass Yield

First-pass yield should be tracked for both briefs and work.

For briefs:

```text
FPY = briefs accepted or promoted without rejection/remediation
      / total briefs submitted
```

Needed fields:

- brief created timestamp,
- gate result,
- rejection/remediation records,
- eventual accepted/promoted state.

For work:

```text
FPY = dispatched work items completed without revise/rework/failure
      / total dispatched
```

Needed fields:

- dispatch event,
- terminal outcome,
- failure/revision/remediation links.

This matters because throughput without quality is not improvement. Low first
pass yield points to upstream brief/spec quality, weak gates, or poorly scoped
dispatches.

## Objective Tracking Study

The session catalog currently has 43 normalized Mayor/Quimby entries. Strictly
by key:

| Key | Count |
| --- | ---: |
| `quimby` | 31 |
| `mayor_session` | 13 |
| Both keys | 1 |
| Neither key | 0 |
| Normalized sessions | 43 |

Objective tracking begins at S25.

| Metric | Count |
| --- | ---: |
| Sessions with `objectives_eval` | 19 |
| Objective rows | 105 |
| Completed | 24 |
| Partial | 31 |
| No | 49 |
| Unknown | 1 |
| Additional work items recorded | 123 |
| New short objectives proposed | 107 |

Longitudinal table:

| Mayor | Started | Complete | Partial | No | Unknown | Additional | New short objectives | New long objectives |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S25 | 3 | 0 | 2 | 1 | 0 | 4 | 5 | 3 |
| S26 | 5 | 0 | 1 | 4 | 0 | 5 | 6 | 3 |
| S27 | 6 | 4 | 1 | 1 | 0 | 5 | 6 | 3 |
| S28 | 5 | 0 | 0 | 5 | 0 | 5 | 5 | 3 |
| S29 | 5 | 2 | 1 | 2 | 0 | 6 | 6 | 3 |
| S30 | 6 | 0 | 1 | 5 | 0 | 7 | 6 | 3 |
| S31 | 6 | 1 | 1 | 4 | 0 | 8 | 6 | 4 |
| S32 | 6 | 2 | 2 | 1 | 1 | 7 | 7 | 4 |
| S33 | 7 | 1 | 5 | 1 | 0 | 8 | 6 | 4 |
| S34 | 6 | 4 | 0 | 2 | 0 | 5 | 5 | 3 |
| S35 | 6 | 1 | 4 | 1 | 0 | 7 | 5 | 3 |
| S36 | 5 | 0 | 1 | 4 | 0 | 4 | 4 | 4 |
| S37 | 4 | 1 | 1 | 2 | 0 | 6 | 5 | 4 |
| S38 | 5 | 0 | 0 | 5 | 0 | 8 | 6 | 3 |
| S39 | 6 | 0 | 2 | 4 | 0 | 7 | 6 | 4 |
| S40 | 6 | 1 | 4 | 1 | 0 | 7 | 6 | 4 |
| S41 | 6 | 2 | 2 | 2 | 0 | 10 | 6 | 4 |
| S42 | 6 | 1 | 2 | 3 | 0 | 8 | 6 | 4 |
| S43 | 6 | 4 | 1 | 1 | 0 | 6 | 5 | 4 |

Interpretation:

- Additional work is common and often valuable.
- Objective miss rate is high.
- The dominant problem is not that Mayors do no work; it is that emergent work
  displaces planned work without a sufficiently formal displacement protocol.
- Quantitative production metrics are needed alongside objective evaluation.

## Failed Objective Classification

The 49 failed objectives (`completed: "no"`) were classified into one primary
failure reason each, using the row's own `remarks` and `improve` fields.

| Rank | Failure class | Count | Frequency | Sessions |
| ---: | --- | ---: | ---: | --- |
| 1 | Displaced by emergent work/crisis | 26 | 53.1% | S25, S26, S28, S29, S31, S33, S34, S35, S36, S37, S38, S39, S41, S42, S43 |
| 2 | External precondition or blocked | 6 | 12.2% | S30, S31, S32, S37, S42 |
| 3 | Missing monitor or surfacing mechanism | 5 | 10.2% | S26, S27, S28, S38 |
| 4 | Obsolete, stale, or false premise | 5 | 10.2% | S38, S39, S40, S41, S42 |
| 5 | Watchdog or special-session mode | 4 | 8.2% | S30 |
| 6 | Quick check skipped | 3 | 6.1% | S26, S28, S29 |

Class details:

### 1. Displaced by emergent work/crisis

Count: 26/49.

Examples:

- S25.2 `WS-B: 2 Opus design forks`
- S28.1 `Adjudicate Phase 0 brief when gsp-f4yx1 molecule completes`
- S35.3 `Scientific-method handoff via formula-work`
- S41.2 `Locate the sql.OpenDB call site behind #17`
- S42.2 `Fix #211`
- S43.4 `Resolve #251 step 0`

Interpretation: the Mayor often performs valuable emergent work, but planned
objectives are displaced without a formal disposition. This class requires a
displacement log, not more prompt prose.

### 2. External precondition or blocked

Count: 6/49.

Examples:

- S30.2 depended on BART confirmation.
- S31.3 and S31.6 were blocked by city/bd/Dolt availability.
- S32.5 was correctly gated on downstream live output.
- S42.3 was correctly blocked by its own precondition, `#211`.

Interpretation: these should not be counted as ordinary failures. They need
explicit preconditions, blocked status, and unblocking criteria.

### 3. Missing monitor or surfacing mechanism

Count: 5/49.

Examples:

- S26.5 `Monitor gsp-bvme8 for brief`
- S28.2 `Adjudicate WS-A #3 brief when gsp-766ah completes`
- S28.3 `Verify he-helfif completed`
- S38.3 `Confirm c1 dogfood file-brief deposited`

Interpretation: "check when X lands" should not be a prose objective. It should
be a monitor, dashboard query, or `mctl` surfacing rule. This class is directly
fixable by objective screening: objectives need measurable conditions and
pollable targets.

### 4. Obsolete, stale, or false premise

Count: 5/49.

Examples:

- S40.1 was obsolete on arrival because Taylor immediately overrode it.
- S41.3 referenced a nonexistent `gc dolt stop` subcommand.
- S42.5 inherited "backups dead" despite conflicting instruments.

Interpretation: false premises should become validators, not warning
paragraphs. If a premise recurs, add a check that marks it as `verify` until
confirmed.

### 5. Watchdog or special-session mode

Count: 4/49.

All four were in S30.

Interpretation: watchdog sessions should have a different evaluation mode. A
watchdog session is not a normal execution shift, so it should record monitored
state and carry-forward disposition rather than being evaluated as if it were a
normal Mayor work session.

### 6. Quick check skipped

Count: 3/49.

Examples:

- S26.2 verify formula exists in `gc formula list`.
- S28.5/S29.5 verify BART pushed a policy commit.

Interpretation: cheap checks should be run by prime scripts in the first five
minutes. This is directly fixable by objective screening and scripted standard
work.

## Objective Screening Rules

Several failure classes can be prevented or reduced by screening objectives
before they are accepted.

Proposed validator codes:

| Code | Catches |
| --- | --- |
| `MO_AUTHORITY` | Objective asks Mayor to perform Taylor/clerk/BART/fleet-owned action. |
| `MO_COMPOUND` | Objective contains unrelated verbs or dependent steps that should split. |
| `MO_REPEATED_CARRY` | Objective carried multiple sessions without attempt. |
| `MO_STALE_TARGET` | Objective points to volatile brief numbers or stale references. |
| `MO_HYPOTHESIS_LEAK` | Diagnosis is stated as fact without evidence status. |
| `MO_DONE_MISSING` | Objective lacks measurable artifact, state change, or monitor condition. |
| `MO_SOURCE_OF_TRUTH` | Objective lacks source-of-truth or comparison target for verification. |
| `MO_BOUNDARY_REQUIRED` | Objective touches data plane, destructive cleanup, or external authority without boundary. |
| `MO_MONITOR_NEEDED` | Objective says "check when X lands" instead of creating a monitor. |
| `MO_QUICK_CHECK` | Objective is a cheap verification that belongs in prime standard work. |

Objective schema fields that support screening:

```json
{
  "title": "Resolve or retire #251 step 0",
  "kind": "investigate",
  "owner": "mayor",
  "targets": [{"type": "github_issue", "id": "251"}],
  "first_action": "verify merge failure against source",
  "done_when": ["issue closed or re-scoped", "blocked beads have route"],
  "evidence_required": ["merge failure reproduced", "blocked beads counted"],
  "hypotheses": [{"claim": "merge aborts on tracked skill", "status": "verify"}],
  "constraints": ["single-session objective"],
  "carry_count": 2
}
```

Objectives should not be accepted unless they have:

- stable target,
- owner/authority,
- first action,
- done condition,
- evidence requirement,
- carry policy,
- hypothesis status when a claim is inherited,
- monitor condition if the action is event-driven.

## False Premises and Instrument Hardening

One high-leverage lesson from the discussion:

```text
If one false premise keeps recurring, add a validator, not another warning paragraph.
```

Examples:

- `gc dolt stop` did not exist, but entered an objective.
- `#214 blocks everything` was only partly true.
- `backups dead` conflicted with another live advisory.

The refactor should include a false-premise registry:

| Field | Meaning |
| --- | --- |
| Claim | The repeated premise. |
| Status | `unverified`, `verified`, `retracted`, `disputed`, `superseded`. |
| Source | Where the claim came from. |
| Required check | Command, query, or source file needed to confirm it. |
| Last checked | Timestamp or session. |
| Validator | Rule that blocks reuse until verified. |

Tool or instrument definition:

A tool/instrument is any command, script, dashboard query, API/MCP call, agent
report, prompt-provided instruction, or status display that claims to report
operational state.

Examples:

- `gc status`
- `gc doctor`
- `gc dolt health`
- `gc order history`
- `bd show`
- `bd ready`
- `tmux -L gt ls`
- GitHub issue/PR status
- brief stack index
- handoff prompt text
- agent report

Hardening rule:

```text
If an instrument is contradicted twice by source evidence, mark it untrusted
for that claim type and require an independent source before acting on it.
```

Instrument registry fields:

| Field | Meaning |
| --- | --- |
| Instrument | Command or source name. |
| Claim type | What it claims to report. |
| Known failure mode | How it has lied. |
| Trust status | `trusted`, `caution`, `untrusted-for-claim`, `retired`. |
| Corroboration required | Alternate source needed before action. |
| Evidence links | Sessions, beads, files, or issues proving the contradiction. |

This converts "trust your eyes" from prompt doctrine into a system rule.

## CAPA Loop

Repeated failures should flow into a corrective and preventive action loop.

```text
recurring failure
  -> classify
  -> root cause
  -> corrective action
  -> preventive action
  -> validator or metric
  -> verify next sessions
```

Examples:

| Recurring failure | Corrective action | Preventive action |
| --- | --- | --- |
| "Check when X lands" objectives missed | Add monitor/surfacing command | `MO_MONITOR_NEEDED` validator |
| Cheap checks skipped | Add prime quick-check script | `MO_QUICK_CHECK` validator |
| False command/premise inherited | Verify commands and claims before charge | False-premise registry |
| Objectives displaced by crisis | Record displacement with disposition | Handoff requires displaced-work resolution |
| Repeated carryover | Convert to single objective, bead, or retire | `MO_REPEATED_CARRY` validator |
| Tool lies twice | Mark instrument untrusted | Instrument registry and corroboration rule |

## Proposed Documented Outputs For Future Work

The future implementation should produce or maintain:

1. A compact Mayor prime packet.
2. A Mayor plant-status report.
3. A session activity report.
4. A session diff report.
5. A displacement log.
6. An objective validation report.
7. A failure lessons digest.
8. An instrument trust registry.
9. A first-pass yield report.
10. A handoff doctor report.

Candidate commands:

```text
mctl mayor plant-status
mctl mayor bottleneck
mctl mayor wip-aging
mctl mayor activity report --session S43
mctl mayor activity compare --from S25 --to S43
mctl mayor objectives check
mctl mayor objectives propose
mctl mayor failures digest
mctl mayor displacement-log
mctl mayor handoff-report
mctl mayor improvement-actions
```

## Immediate Design Implications

For the future refactor designer:

1. Do not make `mayor-math-prime` longer.
2. Do not make `mayor-math-handoff` carry more process by prose.
3. Do not inline full history, full handoff beads, or full eval tables.
4. Do build typed context retrieval and search.
5. Do build quantitative activity metrics.
6. Do build objective validation from the 19-session eval corpus.
7. Do build a displacement protocol.
8. Do align Mayor tooling with `mctl` instead of creating a parallel control
   plane.
9. Do define and harden instruments that have lied.
10. Do track first-pass yield and rework.
11. Do treat Mayor as production control for MathCity's factory.

## Open Questions For The Refactor Design

1. Should `mctl mayor` land as part of `mctl` issue #41, or as a follow-up once
   core context/brief/work/trace commands are stable?
2. Which passive event sources are reliable enough to compute beads closed per
   session without live Dolt access?
3. Where should the instrument trust registry live?
4. Should the first version compute metrics from files only, or require live
   `bd`/Dolt?
5. What is the minimal acceptable prime packet size: 8KB, 12KB, or 30KB?
6. Should objective validation fail handoff, warn, or require explicit override?
7. How should watchdog sessions be represented so they are not evaluated like
   normal execution sessions?

## Bottom Line

The Mayor workflow already contains valuable evidence. The failure is that the
evidence is preserved as prose and not converted into controls. The refactor
should turn the Mayor into a measured, tool-constrained production-control role:

```text
minimal prime
  + typed context tools
  + quantitative activity ledger
  + objective/shift-target validation
  + displacement protocol
  + instrument trust registry
  + scripted handoff
```

That is the path from a growing prompt to a self-improving operating system.
