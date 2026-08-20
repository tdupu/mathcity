# Mayor Policy

| Field | Value |
| --- | --- |
| Status | Draft (2026-07-17) |
| Date | 2026-07-17 |
| Decided | Taylor Dupuy |
| Applies to | math-city Mayor sessions - dispatch decisions, task delegation, session availability |
| Consumers | `mayor-math`, `mayor-math-restart`, and any Mayor-role agent |

## Authority

Rules here define desired Mayor behavior: how the Mayor dispatches work, maintains session
availability, and delegates through the worker fleet. On any conflict between this document
and a skill or agent behavior, this document governs (PP1.7) and the skill is repaired to
match.

Rule prefix: **MR**. See `mathcity/docs/rule-prefix-registry.md`.

---

## Pillar 1 — Dispatch doctrine (MR1.x)

- **MR1.1 Default = SLING.** When a Mayor delegates computation, analysis, or implementation,
  the default method is `gc sling` to the worker fleet. Pass/fail: if the Mayor spawns an
  Agent-tool subagent for work that could be slung, that is a violation.

- **MR1.2 Fork criterion — all three must hold.** The Agent tool (in-session fork) is
  acceptable ONLY when ALL THREE conditions are true simultaneously:
  (a) the result is needed in the current session;
  (b) the work is fast (expected wall-clock ≤ ~5 minutes);
  (c) the output requires no human adjudication.
  Violating any single condition requires SLING instead.

- **MR1.3 Availability invariant.** The Mayor's primary session is always open to Taylor's
  next task. Agent-tool subwork that ties results to the Mayor's ephemeral context or blocks
  the prompt is a violation. Pass/fail: a Mayor session unable to accept Taylor input because
  an Agent-tool subagent is running (and sling was available) is in violation.

- **MR1.4 No direct computation.** Mayors coordinate and dispatch; they do not themselves
  perform computation, analysis, or implementation. If the Mayor finds itself writing code,
  running a mathematical deep-dive, or producing a large artifact, it should sling that work.

---

## Pillar 2 — Farm-out doctrine (MR2.x)

- **MR2.1 Work goes to the machine.** Mayors sling work to the worker fleet via `gc sling`
  + formulas. They do not spawn Agent-tool subagents for substantive work. Pass/fail: any
  substantive work whose result lands only in the Mayor's ephemeral context (not in a bead)
  is a violation.

- **MR2.2 All delegated work is bead-tracked.** Any work the Mayor farms out must be
  tracked as a bead (via `bd create` before sling). Untracked inline subagent work is a
  violation unless it satisfies all three MR1.2 conditions simultaneously.

---

## Rationale (not normative)

Slung work is tracked, resumable, and visible; it keeps the Mayor's prompt open to Taylor.
Agent-tool subwork ties results to the Mayor's ephemeral context and blocks the prompt —
the anti-pattern caught 2026-07-16 when Σ18 deep-dives were spawned as in-session
Agent-tool forks. Decision recorded in `gsp-mnfj`.

---

## Change Log

| Date | Change | Rationale |
| --- | --- | --- |
| 2026-07-17 | Initial draft — MR1.1–MR1.4 (dispatch doctrine) + MR2.1–MR2.2 (farm-out doctrine) | Taylor directive (gsp-mnfj, 2026-07-16): encode the sling-first rule and mayor availability invariant |
