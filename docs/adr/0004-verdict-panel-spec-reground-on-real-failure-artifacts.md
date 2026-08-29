# ADR 0004 — Verdict-panel spec: one-click submit, defer stays, error/HELD re-grounded on real failure artifacts

Date: 2026-08-24 · Status: accepted (Taylor, S51 grilling) · Companion: ADR 0001

## Context

The briefs-visual fork is porting the served dashboard to the Brief Manager
design (design_handoff_brief_manager; predecessor bundle
"design_handoff_briefs_dashboard", Slice 7/8). The design's adjudication panel
was reworked heavily by Taylor in the Claude-design sessions; its CHANGELOG
items 13–18 are authoritative on panel semantics. Three design states (error
briefs, HELD, and the MC-E207/E113 auto-filing) have NO backend: the design's
own follow-up admits "today gates reject into the pile; nothing files a brief."

## Decisions

1. **Panel is option-major with two synthetic options always present**: REC
   ("Accept the recommendation as filed", built from §2) and OTHER ("propose
   your own", free-text disposition). Approve is never blocked; agreeing never
   requires declaring an alternative (design item 16). Click-to-adopt FILLS
   verdict + disposition + reason; only Submit records.

2. **Save draft stays; the two-step Review→Submit is amended OUT** (supersedes
   design item 17). The Submit button submits, one click. Dry-run effect plan:
   passive block under the panel (render-only, no extra step).

3. **Defer stays** — the design wins over #136's radio removal. Verdict radios:
   approve / revise / reject / defer, each with a one-line meaning hint
   (approve = adopt + dispatch per disposition; revise = sent back for extra
   work, returns via revise-return; reject = closed, nothing dispatches;
   defer = parked with a window, who/why recorded).

4. **Error / HELD / malformed are RE-GROUNDED on failure artifacts that exist,
   not an invented error-brief class**:
   - "Error briefs" view renders GATE REJECTIONS: `.pile/.rejected/<slug>/` +
     `rejection.json` + brief-producer-failure-record beads.
   - HELD = a brief whose slug carries a rejection newer than its deposit
     (caught at catch #2, awaiting its revise-return trip). Goes live with the
     full-form gate of ADR 0001.
   - Malformed keeps MBRF041 (= closed with no verdict field; about the
     record, not damage).
   - A read-only PILE row joins the matrix: banner + per-brief gate-state, no
     controls (actions deferred until they exist — Taylor: gate-state only
     matters "if we added more features to allow us to do something").

5. **The per-option `blast` / `reversible` / `gates` chips are DROPPED —
   confirmed fixture fiction** (Taylor: "these chips are fake... the python
   types will answer this"; verified: no such fields anywhere in the types).
   The option cards render what `ParsedDecisionOption` actually carries —
   label/title, `recommended` marker, `confidence`, `source` — and the panel's
   enabled/locked states read from `briefs_options`' `BriefOption`
   (`enabled` + typed `disabled_reason`), which is the REAL grounding for the
   HELD/struck-through rendering.

6. **Save draft is BROWSER-LOCAL** (Taylor, Q10) — same contract as the
   design's priority list: personal, machine-local, no authority, explicitly
   labeled as not following the user. NET RESULT of decisions 5+6: the port
   demands ZERO new backend — every panel element reads from types that exist
   on main today.

6. **Backend-match audit commissioned**: one table, panel control → backend
   field/tool → EXISTS / PARTIAL / ABSENT (the #87 shape scoped to this
   matrix), run as fleet work, not inline.

7. New want, filed separately: **"cancel order" for a molecule** on the
   mathcity/city dashboard (lifecycle-action family, #207-adjacent).

## Addendum — mc-31b8c adjudication-UX refinements (2026-08-28)

Five reproduced defects in the rendered panel/flow were fixed so a verdict is
one legible, honest click matching Taylor's textbox/duration spec. These refine,
not overturn, the decisions above.

- **One click, guard intact (mc-pf5pm).** A move-button submission folds the
  dry-run preview and the apply into a single request. It still runs the `_apply`
  re-plan guard atomically — re-plan (`dry_run:True`), abort if the context,
  target, or plan moved, then write (`dry_run:False`). The "Apply this
  adjudication" second button is gone from the move flow; the guard is not.
  (A direct `verdict`/`option` post without a `move` field still renders the
  two-step preview→confirm, so the guard's own test path is unchanged.)

- **Disable-and-explain, never hide (mc-x8uox).** A blocked dispatch button
  renders DISABLED with its refusal code visible at render time (e.g. `MWRK013`,
  source bead closed), read from the same readiness the `/preview` path performs.
  `briefs_options`' own `disabled_reason` answers cheaply; only an approved
  brief rings the `work_dispatch` dry run. A blocked button is never omitted.

- **Legible preview (mc-5fo2a).** The effect-plan panel no longer dumps the raw
  plan JSON (`{"trace_id":…}`) inline; the readable effect table is the plan.
  The full plan still rides on the `data-plan-json` attribute for the staleness
  digest.

- **One textbox, per Taylor's table (mc-q3m5q).**

  | move            | control                        |
  |-----------------|--------------------------------|
  | approve         | none                           |
  | revise          | one textbox, REQUIRED          |
  | no-brainer      | one textbox, REQUIRED          |
  | reject          | none unless opted in → required|
  | defer           | duration picker (days/weeks/months) |
  | any + opt-in    | one textbox, REQUIRED          |

  There is exactly one reason textbox. It is `required`; approve/reject/defer
  carry `formnovalidate` so a legal bare verdict stays expressible (mc-qlmh),
  while revise and any opt-in enforce it — authoritatively server-side
  (`MCTL_DASH_REASON_REQUIRED`), so it holds JS-off. The no-brainer is a plain
  opt-in checkbox (no textarea of its own); approve-other is a revise whose
  proposal is that one reason box. Defer takes a duration, not prose (the unit
  is converted to the tool's `days`; the picked duration is the reason when none
  is typed). The placeholder no longer says "Optional".

- **Empty "Error briefs" chip removed (mc-lre5h).** `errors` is an uncountable
  lane, so the masthead chip only ever showed a permanent em-dash; it is gone.
  The Error-briefs VIEW (Decision 4) is unaffected.

## Alternatives considered

- Invent the error-brief class as designed: rejected — no backend, and the
  rejection artifacts already carry the same information.
- Two-step submit for verdict safety: rejected by Taylor — "I just want the
  submit button to submit"; Save covers the safety need he actually has.
- Dropping defer per #136: rejected — the Deferred view's invariants are
  designed around it and briefs_defer exists on the typed surface.
