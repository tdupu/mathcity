# Change log — Brief Manager design, session 1

There was no previous version: no dashboard existed in `tdupu/mathcity` when this started (no
HTML/CSS/JS UI files in the repo). Everything below was decided during this session, most of it in
response to review comments. Grouped so the backend list can be split off and worked separately.

## A. Brief content and structure

1. Briefs rebuilt to the `present-it` **full-form** shape: §1 what is being decided (first content,
   Decision-at-Top invariant), §2 recommended answer, §3 assumptions each with its evidence,
   §4 alternatives, §5 risks (both flavours), §6 evidence (purpose, files, test commands with exit
   codes and wall time, mathematics), §7 plan / blocking / gates, then the required-gates summary.
2. **Compact form** for no-brainers: DECISION / CONTEXT / RECOMMEND / CONFIRM `y` / `n` /
   `grill-me-further`, with the `brief-prep` authorization shown (`compact_eligible`,
   `server_touching`, `user_skill_touching_override`, not capability-blocker).
3. Attribution corrected: artifacts are written by **create-brief, composed by brief-prep**;
   `present-it` supplies the section structure only and is *not invoked* by the dashboard. The
   output shape is decided at production time, not at presentation.
4. `grill-me-further` now means "request full-form preparation" — the brief leaves the stack until
   re-filed — rather than a UI expand.
5. §4 shows **every** alternative at once, plus an explicit **E · Other** with a free-text field.
   Option-major rows (not columns).
6. **Click to adopt** on §2 and on every option row: sets verdict + disposition + a reason quoting
   it, then scrolls to the panel.
7. §5, §6, §7 rendered as tables. Timeline moved out of §6 evidence into §7. "Why it was created"
   → **Purpose**. "Risks foregrounded" → **Risks**.
8. Provenance panel **How this was made** sits under the title, above the rule: producer formula,
   step, actor, initiating call, gates evaluated, artifacts, trace and operation ids.
9. **Knowls** (LMFDB pattern) on every policy rule, bead id and diagnostic code, wherever it
   appears in prose or tables. Policy knowls show the rule text, why it exists, related rules, the
   enforcing gate with its `rules = [...]` entry, and adoption date. Bead knowls that are stacked
   briefs link through to them.
10. §7 Blocks / Blocked-by state **why** the edge blocks, or say "reason not recorded on the edge".

## B. Error briefs (new concept)

11. Invariant violations became a **first-class brief class**, auto-filed on detection, with their
    own recommendation, named repair options, and a diagnostic block (severity, code, data
    location, detected-by, filed-by, trace, what it blocks). Two fixtures: MC-E207 (source
    dependency missing, B2.4) and MC-E113 (verdict outside the bead, B3.4).
12. The brief an error blocks is **HELD**: it offers no adjudication, only a route to the error
    brief. The previous acknowledge-and-continue checkbox was removed — it let a violation be
    ratified.
13. When HELD, the panel goes red and **locks**: `approve`, `revise`, `defer` are struck through
    and inert; **reject** is the only available verdict. Adjudicating the error brief unlocks it.
14. Error-brief verdict set: `repair` / `waive` / `reject source brief` / `defer`, and the panel is
    titled "Repair this violation" with a scope line naming the brief it releases.

## C. Adjudication panel

15. **No bare verdict**: a brief with named alternatives cannot be approved without saying which.
16. Briefs with no alternatives preselect **Accept the recommendation as filed** — agreeing with
    the producer must never require declaring an alternative to it. Records as
    `--accept-recommendation` / `disposition accepted-as-filed`.
17. **Save draft** plus a two-step **Review verdict → Submit and advance**, with the DRY RUN effect
    plan shown before anything is written. Submit advances to the next brief in your order.
18. Leak flag simplified to **No-brainer**; ticking it opens a reason box prefilled with a guess,
    unticking hides it. Recorded as a classifier signal, separate from the verdict.
19. `bd update` line in the effect plan states bead **fields**, not CLI flags.

## D. Queue and ordering

20. **Priority list** (was "My queue"): starts empty, drag to reorder, shuffle, and a
    **rank by comparison** pass (binary insertion, ~1 comparison per placement).
21. Add to queue from each stack row, plus tick-many and a bulk add. Next five bead ids listed in
    the sidebar. Shuffle / Rank appear only on the list page.
22. **Score** column with adjustable weights (unlock_count, convoy, age, priority) — explicitly a
    working hypothesis, since no policy defines importance.
23. Twelve sortable columns, all toggleable; sort by clicking any heading.

## E. Pipeline views

24. **Pile** view: what is there and what holds each item — gate state (PROMOTABLE / WAITING /
    GATE REJECT), the gate it waits on, next step, time in pile, and the shuffler lock state.
25. **Deferred** view: window, time left, who deferred and why.
26. **Adjudicated** view: closed decision beads, newest first, with verdict, disposition,
    follow-up bead, and an **Outcome** column. Expanding a row shows "what happened since" —
    a timestamped trail plus the **molecule step table** (steps done / running / pending with
    times). No reopen affordance (B3.8).
27. Sidebar reorganised into **Pipeline** (stack first, then pile, error briefs, adjudicated,
    no-brainers) and **Priority list**, with a one-line explanation of the difference.
28. Header counts are clickable; **rig** is a multi-select picker (default: all rigs); **store**
    opens a Dolt/bead-store panel (engine, branch, last commit, schema, connection, legacy rows,
    doctor summary).

## F. Conventions

29. **Stoplight scale**, defined once: ERROR red, HELD orange, WARN yellow, PROMOTABLE green, OK
    neutral, cursor gold. Health colours are never used for verdicts — a closed decision has no
    pipeline health.
30. **DRY RUN** badge for anything that is preview or classifier output only, with a footer legend.
31. **FIXTURES · NOT LIVE DATA** badge — nothing on the page is read from the city.
32. Colour **key** under the stack and pile tables.
33. Every count derives from the same query as the view it opens; none are authored literals.
34. Reads may span rigs; mutations are always single-rig.

## G. Backend / policy work this implies

Ordered by how much it blocks the dashboard.

1. **Error briefs must actually be filed.** The design assumes detection files a `type=decision`
   brief with a recommendation and repair options, and that the blocked brief is marked HELD until
   it is adjudicated. Today gates reject into the pile; nothing files a brief.
2. **Verdicts must carry the disposition.** `--option X` / accepted-as-filed / proposed option E
   need to land on the brief bead, or "accepted as filed" is indistinguishable from "no
   disposition recorded".
3. **Policy index: rule ID → file, line, text.** Every knowl depends on it. This is brief
   `mc-70d4` in the fixtures and PP4.1/PP4.2's join layer.
4. **Dependency edges need a reason field**, so the blocking graph explains itself.
5. **No-brainers should not stay dry-run.** They should auto-process with an audit trail and an
   undo window instead of costing a decision each. Policy change (`new-brief-policy`), gated on
   settling the N5 kill-switch scope first.
6. **Molecule step state and follow-up bead state** must be readable per decided brief for the
   progress report.
7. **Store health** (Dolt engine, branch, last commit, schema version, connection, legacy
   decisions-track rows, doctor summary) needs to be one read.
8. **Rig-scoped reads** with cross-rig support, and a single-rig guarantee on every mutation.
9. Gate results per pile item (which gate, pass/fail, what the producer must do) as structured
   data rather than prose.

## H. Known drift in this prototype

- All data is fixture data; `PI`, `BRIEFS`, `PILE`, `DEFERRED`, `ADJUDICATED`, `RULES`, `BEADS`,
  `DIAG`, `POLICIES` and every effect-plan string are invented. See the fixture → real-source table
  in `README.md`.
- Timestamps, test durations, download percentages and molecule times are illustrative.
- The score formula is invented; it is not a policy artifact.
- Compact briefs carry a full-form body in the fixtures so the grill-me-further path can be shown;
  a real compact artifact would not.
