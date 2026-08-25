# SURFACE-STATUS §4 Decomposition — Index of Distinct Plans

> Commissioned by Taylor 2026-08-23 (QUIMBY 50 session): *"divide this into distinct plans and
> record the plan in the mathcity/docs folder."* Source table: `docs/SURFACE-STATUS.md` §4,
> the in-flight/prospective census orphaned by lumby's departure. Each plan below is a separate
> file in this directory, independently dispatchable through the brief pipeline
> (one commission brief per plan; `check-plan-hygiene` gates each before any sling).

## The division

| Plan | File | Scope | Issues | Gated on |
|---|---|---|---|---|
| **A — mctl intake surfaces** — **LANDED `b7d7a50`→`83962df` (S50)** | `2026-08-23-plan-a-mctl-intake-surfaces.md` | `create_github_issue` · `create_defect_bead` · `standardize_github_issue` | #185, #52 (anti-dependency), #199 | live by attrition |
| **B — pool pressure & visibility** — **Phase 1 CODE DONE** (fork branch `c608add0a`, deploy parked on city-up + gate; SCOPE CORRECTED per P5.4: real #99 gap is suppression at `build_desired_state.go:866`, not the ~2403 term) | `2026-08-23-plan-b-pool-pressure-and-visibility.md` | #99 core fix, then the 4 read tools | #99, #197 | deploy bundles #29 cherry-pick; Phase 2 after deploy |
| **C — mctl event participation** — **CODE LANDED `a95eff1` (S50)**; live acceptance (Task 4) still gated on the #204 unlatch | `2026-08-23-plan-c-mctl-event-participation.md` | mctl emits `brief.submitted` on deposit and `brief.decided` on adjudication | #202, #204 (sequencing) | unlatch for live acceptance |
| **D — commission adapter completion** — **Tasks 1+#181 LANDED in `83962df`**; Tasks 2–3 (hand-lap + wrapper) still gated on B-deployed | `2026-08-23-plan-d-commission-adapter-completion.md` | the reusable issue→bead→brief→molecule adapter | #179, #180, #181 ✅, #192 ✅ | Plan B deploy |
| **E — drain formula repair** | `2026-08-23-plan-e-drain-formula-repair.md` | **CLOSED — ALREADY SATISFIED** (S50): both #73 bugs fixed on main since `2adc84b` (Aug 20, "Closes #73"); plan was authored on a stale premise (mc-quq open + S49 ledger). E-subagent caught it via P5.4, zero edits, existing tests verified. Bug 1's HELD ruling is moot (code on main, stack-index impact measured null pre-ship). The fix is LIVE for future firings (formulas load at sling time). Residue: close stale bead mc-quq | #73 (CLOSED Aug 20) | — |
| **F — small instrument fixes** *(added S50, Taylor)* | `2026-08-23-plan-f-instrument-fixes.md` | #181 dispatch budget (deconflicted with Plan D — first taker wins) + #205 mayor_boot handoff honesty. #206 priority mapping deliberately NOT here — ships in Plan A Task 2 | #181, #205, (#206→A) | nothing |

## Explicit retirement (recorded here, not planned)

**`assign_molecule_to_pool` / `assign_molecule_to_session` — RETIRED, on evidence.**
`gc.routed_to` is stamped on every routable step at cook time by `ApplyGraphRouteBinding`;
hecke proved it live (`he-e6cnz1` closed 07:28 with worker `gc__run-operator-gt-9e1jpg`).
The missing thing was never an assignment write. Do not build these unless new evidence
overturns the cook-time stamping. A dropped plan is information (§4 house rule) — this row
stays retired with its evidence rather than deleted.

## Dependency order

```
A (intake)  ──────────────────────────────┐
B (#99 → pool tools) ──┐                  ├── loop step 1 + step 7 both repaired
                       ├── D (adapter E2E)┘
#181 (budget, BART) ───┘
#204 unlatch + #29 deploy (in flight, decision table) ── C (events)
```

A and B are independent and can run in parallel. C waits for the unlatch to land so its
acceptance test can observe a real order firing. D is the capstone: it is *verified*, not
built — its remaining work is one blocked step plus wrapping, and it becomes the city's
first repeatable issue→molecule lap.

## Standing constraints (apply to every plan)

- **P5.4:** truth is code + behavior; each plan's premises carry the S50 measurement that
  grounds them, and an executor must re-verify any premise older than a day.
- **B2.8:** the bead store is canonical; no plan writes governed brief paths by hand.
- **#199:** registering one MCP tool touches six hand-maintained rosters — every plan that
  adds a tool budgets for all six and reuses the #203 served-response schema test pattern.
- **#52:** `standardize_github_issue` must NOT be built on `update-issue` semantics
  (consolidation destroys agent-tracker history).
- Landings are repo-side (BART's lane) behind Taylor's `authorize-git-operation` gate.
- Every anomaly encountered while executing these plans gets a row in the S50 dogfood run
  log in `SURFACE-STATUS.md` at the moment it is hit.

[recorded by QUIMBY 50 (Mayor session cc5a7b66), 2026-08-23]
