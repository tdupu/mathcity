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

## Alternatives considered

- Invent the error-brief class as designed: rejected — no backend, and the
  rejection artifacts already carry the same information.
- Two-step submit for verdict safety: rejected by Taylor — "I just want the
  submit button to submit"; Save covers the safety need he actually has.
- Dropping defer per #136: rejected — the Deferred view's invariants are
  designed around it and briefs_defer exists on the typed surface.
