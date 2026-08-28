# Design — dashboard "Report" box → evidence-backed fix-brief

**Status: DESIGN / revised post-hygiene (revise findings folded in). Awaiting
sign-off. Nothing built.**
Author: BART (outside agent). Grilled with Taylor 2026-08-27.
Target tree: `<repos-root>/mathcity` @ `74eeac0` (post-#57; pack `tdupu/mathcity` 0.2.1).
Hygiene: `check-plan-hygiene` run 2026-08-27 → revise; this revision addresses
P1.20, P3.6, P1.21, P7.1/P7.2, P6.2, P3.5, P4.2, P6.1/P6.3, P1.10, P5.5, scope.

## §1 — What is being decided / built

Add ONE **Report** box to the mathcity brief dashboard. The operator types a
rough description of something broken; the system produces a **hygienic,
evidence-backed decision brief** that, on approval, **slings `build-basic-briefed`
to fix it**. The bug report and the fix-commission are the SAME object (a brief
in the operator's stack) — not two records.

**Scope boundary (P3.2/P4.1):** this box is for **`tdupu/mathcity`-OWNED**
issues only. A reported bug whose fix lands in gascity/beads core (outside the
owned set) is OUT of scope here and must route through the P3.2 briefed path
(`create-issue-briefed` → `pr-pipeline-briefed`), never `build-basic-briefed`.
The intake step classifies and refuses out-of-owned-set reports with that
pointer. Landed **PR-only** to `tdupu/mathcity` (P3.1).

## §2 — Locked decisions (from grilling)

| # | Decision | Value |
|---|----------|-------|
| D1 | The record the box produces | A **brief** (not a bare defect bead) — the only lane you adjudicate-and-fix from is the Brief stack. |
| D2 | Rig | **mathcity** (`tdupu/mathcity`). |
| D3 | Dashboard write path | The existing **`/preview → /apply`** two-phase. Honors the test-asserted `MUTATION_ROUTES = ("/preview","/apply")` invariant; inherits mutation-safety (single-use token, re-plan-at-confirm, unroutable-write refusal). No third mutation route. |
| D4 | Drafting locus | A **slung agent** (the dashboard is "a client of the typed MCP tools, nothing more" — no model). Submit → dispatch (typed) → agent drafts + files → brief appears in stack → adjudicate. |
| D5 | Evidence discipline | **Always evidence-backed; fail-closed without evidence** (D5 detail in §4 Stage B; P6.2 failing case required). |
| D6 | Approve terminal | **`build-basic-briefed`** — a worker fixes the bug and opens a PR to `tdupu/mathcity`. No GitHub issue in the loop. |
| D7 | Factoring ("hard") | **Extract a shared base** owning the `file-brief` terminal + `brief-producer.v1` schema; `create-issue-briefed`, `pr-pipeline-briefed`, and the new `report-fix-briefed` all `extend` it. One code-owner of the brief-filing contract → no prose-schema drift. |

## §3 — Grounding (all source-verified, P5.4)

- **`briefs_create` is the single code-enforced brief writer** (POLICY B2.11):
  enforces the frontmatter schema, the **`MBRF034`** source-dependency refusal (a
  sourceless brief is refused at creation), and gate evidence — in code, not
  prose. The base's `file-brief` terminal writes through it (P7.1).
- **`MBRF034` makes "find related beads" load-bearing:** the brief MUST cite ≥1
  source bead. The evidence step supplies it; if none relates, it mints a
  **defect bead** (`create_defect_bead`) as the canonical source.
- **`work_dispatch` is the typed dispatch tool** the dashboard already can call
  (`self.client.call(...)`); Stage C uses it, not raw `gc sling` (P7.1/P7.2).
- **The three-step skeleton `intake → compose-body → file-brief`** is already
  shared by `pr-pipeline-briefed` and `create-issue-briefed` as siblings. F8.1:
  terminal step id = `file-brief`. `report-fix-briefed` is a third sibling.
- **Ownership verified:** `<repos-root>/mathcity/formulas/` is owned `tdupu/mathcity`
  content — no vendor tree, no upstream-owned marker. Refactoring
  create-issue-briefed / pr-pipeline-briefed is inside the owned set (P2.1/P1.7).

## §E — Check-wheel / alternatives surveyed (P1.20)

Formula & surface design. Surfaces searched: `mathcity/formulas/*`,
`mathcity/skills/{create-brief,decisions-to-briefs,github-issues-to-briefs}`,
`mctl_core` tools (`briefs_create`, `work_dispatch`, `create_defect_bead`),
`mctl_dashboard` routes.

| # | Alternative surveyed | Verdict | Why |
|---|----------------------|---------|-----|
| A | Reuse `mathcity-issue-briefed` as-is | **rule-out** | Wrong terminal (files a GitHub issue, not a fix), hard-gates on pre-recorded investigation evidence a rough report lacks, and its brief-operator pool is wedged (#10). |
| B | New standalone `report-fix-briefed`, self-contained brief-filing | **rule-out** | Re-implements brief production → prose-schema drift from the sibling family (Taylor's explicit concern). |
| C | Sibling adapter over `briefs_create`, no base refactor | **adapt** | Drift-safe (code-enforced writer) but leaves the schema re-spelled per sibling. Superseded by D on Taylor's "hard" ruling. |
| D | **Extract `brief-briefed-base`; all three siblings extend it** | **ADOPT** | One owner of the `file-brief` terminal + schema; maximal DRY. Chosen (D7). Staged to bound blast radius (§4). |
| E | Bare defect bead (`create_defect_bead`) only, no brief | **rule-out** | A task bead never enters the Brief stack — the only lane the operator adjudicates-and-fixes from. |
| F | Dispatch via raw `gc sling` from the dashboard | **rule-out** | P7.1/P7.2 — dashboard must use the typed `work_dispatch` tool. |

## §4 — The build (staged, to bound blast radius)

**Downstream impact (P4.2):** `create-issue-briefed` and `pr-pipeline-briefed`
are the **P3.2-mandated upstream contract** — the whole city's issue/PR handoffs
depend on them. The base extraction MUST (a) preserve the F8.1 terminal id
`file-brief`, (b) keep each sibling's conformance test green, (c) change no
observable output of the two existing formulas (pure refactor). Any behavior
delta → the migration is wrong.

### Stage A — extract the base (no behavior change)
- New base formula **`brief-briefed-base`** owning the `file-brief` terminal:
  deposit via `briefs_create`, `brief-producer.v1` metadata, the frontmatter/gate
  schema, `.pile` deposit (brief-shuffle stays the only `.pile → stack` writer,
  B2.10). The terminal *action* the brief commissions is a parameter
  (`file-issue` / `open-pr` / `dispatch-fix`).
- Migrate **`create-issue-briefed`** onto it (lower-risk sibling first). Its
  conformance test stays green (P4.2).
- **`extends` caveat (measured):** non-id-override child steps append AFTER
  parent steps (`mergeSteps`), pushing a new step past `file-brief` and breaking
  F8.1. Children override `intake`/`compose-body` **by id** and inherit
  `file-brief`. Do not append.

### Stage B — build `report-fix-briefed`
- `extends = ["brief-briefed-base"]`, overriding by id:
  - **`intake`** — read the report; **classify scope (owned vs upstream; refuse
    upstream with the P3.2 pointer, fail-loud per P6.1); gather evidence (repro /
    failing code location / ≥1 related bead) and FAIL-CLOSED with a visible
    signal + the missing-evidence list if it can't** (D5, P6.1). Search related
    beads → `sources`; if none, mint `create_defect_bead` as the source (MBRF034).
  - **`compose-body`** — a **fix-brief** body: §1 "Fix `<X>`?", the gathered
    evidence, related beads, recommended verdict `A = approve → dispatch
    build-basic-briefed`. Never fabricates evidence (`<unknown — needs input>`).
  - terminal action = `dispatch-fix` (approve → `build-basic-briefed`).
- **P6.2 — the evidence gate ships an observed failing case:** a fixture report
  with no repro / no locatable code / no related bead MUST be refused by the
  intake step, observed failing before the gate and passing after. Recorded in
  `tests/report-fix-briefed/`.

### Stage C — dashboard surface
- A **Report** control (placement: §5) → a form (title + comment [+ severity]).
- Submit routes through **`/preview → /apply`** (D3). `/apply`'s effect =
  mint the report source bead + **dispatch `report-fix-briefed` via the typed
  `work_dispatch` tool** (P7.1/P7.2), seeded with the operator's text. Preview
  confirms "file this report → a drafting agent will produce a brief in your
  stack." No new mutation route.
- **P1.21 pre-sling assignee check:** before dispatching `report-fix-briefed`,
  verify the freshly-minted report bead has no active non-stale assignee; abort
  with a visible "ALREADY DISPATCHED" signal rather than double-dispatch. (A new
  report bead per submit makes collisions rare, but the check is mandatory.)
  Post-sling verify-assignee gate also applies. Same discipline governs
  approve → `build-basic-briefed` (routed through `mctl work dispatch`, which
  already re-reads the bead and raises `MWRK003` on an unclaimed sling).
- **If `work_dispatch` cannot pin `report-fix-briefed`** (it may route via the
  `work-briefed` router): extend `work_dispatch` to accept the formula, filing
  that as a P7.3 mctl gap — do NOT route around it with `gc sling`.
  - **⚠ CONFIRMED AT SOURCE (BART 2026-08-27).** This condition is now PROVEN
    true, not hypothetical: `mcp_server.py::_handle_work_dispatch` (:1463) calls
    `plan_dispatch(ctx, arguments["brief_id"])` and the `work_dispatch` schema
    (:2978) accepts ONLY `{brief_id, dry_run}` — no `formula`, no seed vars. It
    dispatches an existing brief-backed bead via that bead's own routing; it
    cannot be told to use `report-fix-briefed`. `work_dispatch_event` carries a
    `formula` param but only RECORDS a `dispatch-provenance.v1` event — it does
    not sling. So the dashboard dispatch is genuinely blocked on a typed
    `work_dispatch` extension (add a `formula`/seed param, or a new typed
    dispatch-with-formula tool). **P7.3: file the gap; do not route around it.**
    Compounded by mc-1pale (STILL-REAL, clark's sweep): there is no park / hold /
    pause verb in the live roster, so a dispatch that misroutes to the
    `work-briefed` default cannot be contained after the fact — the pinning MUST
    be typed BEFORE any dispatch path ships. Stage C's dispatch half therefore
    waits on this extension (Taylor-gated) + a city up to `gc formula show`- and
    live-validate it. `work_claim` (:2986) is the typed P1.21 assignee-read the
    pre-sling check will use.

### Stage D — migrate `pr-pipeline-briefed` onto the base (LAST / may be a separate PR)
- Highest blast radius (P3.1-mandated PR path). Only after A–C are green, behind
  its own conformance tests. Deferrable to a follow-up PR + bead.

## §5 — Open items (proposed defaults; override any)

- **UI placement** — *proposed:* a global control in the dashboard chrome
  (nav/footer), pre-filling current route/rig/brief as context.
- **Form fields** — *proposed:* short title + comment + optional severity
  (severity → `priority/pN` via the existing label→priority mapper). Title feeds
  the `create_defect_bead` dup-guard, so it must be a real one-line title.
- **⚠ Dependency blocker (P6.1 loud):** the `file-brief` terminal routes to the
  **`mathcity.brief-operator`** pool, **wedged at 0 sessions (tdupu/mathcity#10)**.
  Until it has a session the briefed terminal cannot run end-to-end; the dispatch
  must **fail loud** (visible signal + escalation), never hang or silently drop
  (P6.1). Static conformance is testable without it. Tracked as a hard dependency
  bead in the convoy (not worked around — P1.17).
- **P6.3 (deadline ≠ verdict):** any wait the feature introduces (drafting-agent
  completion, dispatch ack) carries a warn threshold below its deadline and, on
  expiry, reports a distinct non-failure state (`still_running`/`deadline_exceeded`
  with elapsed) — never rendered as failure/unknown/absent.

## §6 — Execution context, policy & constraints

- **Agent context (P3.5):** the BUILD is performed by an **outside agent**
  (BART, `<repos-root>/mathcity`) under conservative git policy — no push without
  `authorize-git-operation`, PR-only to `tdupu/mathcity` (P3.1). The *drafting*
  and *fix* workers are **inside** (city-dispatched) agents; the report box only
  dispatches them via the typed surface.
- **Documentation (P3.6):** run **`improve-documentation`** before completion —
  update the formula index / README rows for `brief-briefed-base` +
  `report-fix-briefed`, dashboard docs, examples, and the planned-issue links, or
  record a precise N/A. Named as a required convoy step.
- **Commit discipline (P5.5):** commits use the `[autogenerated by …]` footer;
  **never** a `Co-Authored-By: Claude` trailer.
- **Interface (P7.1–P7.3):** no writer but `briefs_create` for the brief; the
  dashboard dispatches only via typed `work_dispatch`; any mctl shortfall is
  filed as a gap, never routed around.
- **Do NOT change the `city.toml` import key** (`context.py:463` reads the key,
  not `[pack].name`) — standing, unrelated to this feature.

## §7 — Next steps

1. Sign-off on this revision.
2. File the convoy as beads (P1.19 append-discipline; real bd types P5.3):
   base-extract / create-issue migration / `report-fix-briefed` / dashboard /
   pr-pipeline migration / brief-operator-pool dependency / improve-documentation.
3. Build Stage A→C; PR to `tdupu/mathcity`. Stage D as a follow-up PR.
