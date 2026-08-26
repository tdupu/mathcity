# Master Formula Rework Exploratory Handoff

Parent: [Mathcity Repository Layout](../../../LAYOUT.md)

Status: exploratory triage packet, not an approved implementation plan.

Date: 2026-08-24

## Source Artifacts

This handoff summarizes and re-scopes two source artifacts:

- [Execution Policy and Error Briefs PERT](./2026-08-24-execution-policy-error-briefs-pert.md)
- [Execution Policy and Error Briefs Grilling Record](./2026-08-24-execution-policy-error-briefs-grilling-record.md)

Those files are preserved as source material. They are broader than the next
safe implementation slice and should not be read as committed direction.

## Triage Purpose

The useful work is to extract key ideas from the large PERT without breaking
the city. Another agent may triage this packet, adapt it, split it further, or
discard parts of it. The immediate goal is not to build the entire execution
policy and error-brief system.

The top invariant is:

> Preserve the working `mathcity.work -> work-briefed` path. Harden around it
> before replacing or generalizing it.

## Current Working Baseline

The source review found this baseline:

- `work-briefed` is the current live router. It classifies work into
  `COMMISSION`, `SIMPLE_CONTINUE`, `FULL_CONTINUE`, or `EXPLICIT_CONTINUE`,
  then slings a child formula.
- `commission-work-briefed` is planning-only. It normalizes the request,
  reconciles existing work, proposes a dispatch graph, reviews it, and files a
  commission brief. It does not execute implementation work before approval.
- `brief-decision-dispatch` executes approved `commission-dispatch.v1`
  continuations. The current executable continuation is a single `gc_sling`
  action with vars.
- MCP `work_dispatch` dispatches approved brief-backed work through
  `work-briefed`. It is not currently the path for fresh unbriefed
  commissioning.
- Fresh work still uses the path-B `gc sling ... --on work-briefed` described
  in the `mathcity.work` skill, then records dispatch provenance through
  `mctl work dispatch-event`.

## Main Risk

The large PERT bundles several things that are individually useful but risky
when landed as one critical path:

- generated dispatch-program artifacts;
- formula execution policy;
- runtime policy gates;
- normalized error records;
- error briefs and rollups;
- revision validation;
- dashboard controls.

The city is already working through the existing router. The risk is replacing
or over-constraining that route before the smaller support pieces have been
proven.

## Key Ideas To Preserve

These are the ideas worth keeping even if the large plan is rejected:

| Idea | Why It Matters |
| --- | --- |
| Keep `work-briefed` as the live router | It is the proven boundary between ambiguous work and executable work. |
| Commissioning is approval-gated planning | Fresh or ambiguous work should produce a commission brief before implementation dispatch. |
| MCP should expose typed work operations | A typed `work_commission` path would remove raw path-B sling/provenance hand work without changing the router's semantics. |
| Generated programs need callable inventory | If `commission-work-briefed` designs a composed program, a reviewer needs to know exactly which formulas/scripts may execute. |
| Design-time and runtime checks are separate | Design approval should not override later policy drift. |
| Error attribution needs call provenance | Large compositions need program id, call id, callee, source bead, vars, and output root to diagnose failures. |
| Error briefs should recommend typed actions | Terminal failures should not disappear; they should produce a decision surface with an effect plan. |
| Warnings should stay lightweight | Not every warning should become a human adjudication burden. |

## Recommended Course

Start with MCP-first current-router hardening:

1. Fix known sharp edges in the existing `mctl work dispatch` path.
2. Add a typed MCP/CLI commission path for fresh work that still slings
   `work-briefed`.
3. Harden `commission-work-briefed` brief content and bounded catalog evidence.

This makes the current city safer without asking Gas City formulas to become a
general runtime program interpreter.

## Courses Of Action

| Course | Description | Recommendation |
| --- | --- | --- |
| A | Current router, better MCP surface | Use first. Lowest blast radius and directly improves the existing workflow. |
| B | `dispatch-program.v1` substrate | Use second. Valuable once the current commissioning surface is typed and reliable. |
| C | Formula execution policy gate | Defer until Course B or until there is an urgent safety reason. |
| D | Full policy/error-brief/dashboard PERT | Treat as umbrella roadmap, not next implementation. |

Details for forkable candidate projects live in
[Master Formula Rework Triage Projects](./2026-08-24-master-formula-rework-triage-projects.md).

## Explicit Non-Goals

- Do not bring down, restart, drain, or otherwise touch the running city for
  this documentation packet.
- Do not replace `work-briefed` as the default router in the first slice.
- Do not make `commission-work-briefed` execute generated programs directly.
- Do not claim formula TOML has runtime recursion or arbitrary interpreter
  behavior today.
- Do not introduce dashboard controls before CLI/MCP behavior is proven.
- Do not turn every warning into a decision brief.

## Triage Instructions For The Next Agent

Use the source artifacts as background, but triage from this handoff and the
project list first. Mark each candidate as one of:

| Triage Mark | Meaning |
| --- | --- |
| Use | Safe and useful enough to commission as a small event. |
| Adapt | Keep the idea, but shrink or rewrite the acceptance shape. |
| Defer | Good idea, wrong time or dependent on an earlier slice. |
| Abandon candidate | Too risky, too speculative, or superseded by the current working system. |

For any selected project, preserve this release posture:

- docs and fixture tests before live behavior;
- dry-run-first effects where possible;
- no raw command passthrough in MCP;
- no direct `gc sling` replacement unless the typed path records equal or
  better provenance;
- no city restart or live fleet command unless a separate operator-approved
  implementation plan requires it.

