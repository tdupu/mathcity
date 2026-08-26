# Mathcity-Dashboard Status — the city observability slices (HANDOFF design)

> Part 2 of the dashboard census (Taylor's split, 2026-08-23; BART concurred).
> Part 1: [BRIEFS-DASHBOARD-STATUS.md](./BRIEFS-DASHBOARD-STATUS.md). Index:
> [DASHBOARD-STATUS.md](./DASHBOARD-STATUS.md).
> **#153's rule attaches to every row: done = renders in the served dashboard.**
>
> **Division of authority (BART 6689255, 2026-08-23):** IMPLEMENTATION STATUS (built vs
> designed-not-built) is canonical in `docs/superpowers/plans/dashboards/README.md` — defer to
> it on any disagreement. THIS file carries the coordination layer only: PERT, waves,
> critical path, dependency ordering.

## Issues

| # | State | What | PERT deps | Unlocks |
|---|---|---|---|---|
| 87 | OPEN | gap analysis: every object-model property EXISTS/PARTIAL/ABSENT — "everything else schedules against it" | — | 4 |
| 115 | OPEN | **KEYSTONE** (lumby): step.expected_artifacts at authoring + A–E evidence log; is_complete derived from artifacts, never self-report | #87 | 3 |
| 113 | OPEN | slice 3: queue_status (six populations, next_up_is_prediction) | #115, #87 | 0 |
| 118 | OPEN | slice 8: costs_summary (token bucketing, meta-work ratio) | #87 | 0 |
| 120 | OPEN | slice 9b: worktrees_status (+ created_by/step at creation) | #87; #115 soft | 0 |
| 88 | OPEN | A–E chain + molecule.state spec — likely superseded by #115. NOT code-measurable (BART): needs a side-by-side body read; BART offered to do it | — | 0 |
| 153 | OPEN | the process rule: five merged slices render NOWHERE; backend-only counted as progress | — | governs all |
| 109, 110 | CLOSED | D1/D2 blockers (Molecule identity; blast_radius in EffectPlan) | — | — |
| 111, 112, 114, 119, 121 | CLOSED | slices 1, 2, 4, 9a + FE port — **per #153, verify each actually renders** | — | — |
| 89 | CLOSED | step.expected_artifacts authoring intent | — | — |

## Sequencing (PERT, S51)

Wave 1: **#87** (unlocks all four open slices). Wave 2: **#115** (after #87 confirms gaps).
Wave 3: **#113**. Wave 4: **#118, #120**. Parked: **#88** pending the supersession read.
