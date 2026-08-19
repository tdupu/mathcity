# Handoff: MathCity Briefs Dashboard

## Overview

A clerk-facing dashboard for adjudicating MathCity briefs. It covers the whole pipeline the
`mctl` plan describes: what is in the pile, what is on the stack ready for a human verdict,
what is deferred, what has already been adjudicated, and the invariant violations that block
individual briefs. The adjudication surface implements the `present-it` full-form brief
(7 grill-ordered sections, Decision-at-Top), the compact form for no-brainers, an explicit
disposition requirement, draft saving, a dry-run effect plan, and a two-step submit.

This design corresponds to **Slice 7 / Slice 8** of
`subdomains/dev/docs/plans/mcp/MCTL-MCP-IMPLEMENTATION-PLAN.md` — the dashboard that ships
after the CLI and MCP semantics are stable. It is a client of the shared core: it does not
re-parse state, and every mutation is preview-first.

## About the design files

`Briefs Dashboard.dc.html` is a **design reference written in HTML**, not production code.
It is a self-contained prototype with hard-coded fixture data standing in for `mctl` output.
The task is to recreate it in the target environment — for this repo that means a Python-backed
service calling the shared core, with whatever frontend the dashboard slice settles on — using
that codebase's established patterns. Do not ship the HTML.

Specifically, everything in the file that looks like data is fixture data and must be replaced
by real core calls:

| Fixture in the file | Real source |
| --- | --- |
| `BRIEFS` | `briefs_list` / `BriefRecord` |
| `PI` (per-brief §1–§7 content) | the brief artifact body, parsed per `present-it` structure |
| `PILE` | pile contents + gate evaluation results |
| `DEFERRED` | deferred briefs with defer windows |
| `ADJUDICATED` | closed decision beads |
| `RULES`, `POLICIES` | `PolicyIndex` (rule ID → file, line, text) |
| `BEADS` | bead store lookups |
| `DIAG` | diagnostic code registry |
| effect-plan strings | `EffectPlan` from the shared core |

## Fidelity

**High-fidelity.** Colors, typography, spacing and interaction states are final and should be
recreated faithfully. Layout structure is deliberate: it follows LMFDB's conventions
(`lmfdb/templates/style.css`) so it feels native to people who use LMFDB daily — fixed left
sidebar, dense `.ntdata`-style tables with a 2px rule under `thead` and alternating rows, a
right-hand properties box on detail pages, and the *knowl* pattern (dotted-underline term that
expands an inline panel) for policy rules, bead ids and diagnostic codes.

## Screens / views

### 1. Header (persistent)

- Brand "MathCity / Briefs" — Cormorant Garamond 25px/600, the `/` in accent `#b68235`.
- Context line, mono 11.5px: `city ~/gt · rig mathcity · store .beads (dolt)`. This is the
  resolved runtime context and must come from `context_resolve`. Source-checkout invocations
  hard-error (MC-E101) rather than resolving a plausible-but-wrong rig.
- Right side, clickable counts: `pile`, `stack`, `deferred`, `error briefs`, plus a `keys`
  toggle that reveals the keyboard map. Every count derives from the same query as the view it
  opens — a chip must never disagree with its destination.

### 2. Sidebar (186px, `--color-surface`, 1px right divider)

Two labelled sections with dark headers (`--color-neutral-900` bg, `--color-accent-200` text,
13px/600 uppercase, 0.06em tracking):

- **Pipeline** — where the pipeline says each brief is: Stack — ready for you / Pile — awaiting
  gates / Error briefs / Adjudicated — closed / No-brainers — DRY RUN. Each row shows a mono count.
- **Priority list** (header itself is clickable) — the user's own ordering over the stack, with
  the next five bead ids listed beneath, or "next up — nothing queued".
- **Importance** — four sliders (unlock_count, convoy/epic, age, priority) feeding the score.
  These are deliberately adjustable: no policy defines importance, so the ordering is a working
  hypothesis the clerk experiments with.
- Shuffle / Rank by comparison buttons appear **only** on the priority list with >1 item.

### 3. Brief stack (default view)

Dense sortable table. Twelve available columns, eight on by default, all toggleable via a
**Columns** picker: Brief, Rig, Artifact, Unlock, Score, Age, Priority, Type, Producer, Opts,
Health, Source, Rec.

- `table-layout: fixed`; every column except the title has an explicit width; the title column
  takes the remainder and clamps to 2 lines. **The table's `min-width` must be derived from the
  sum of visible column widths + ~290px for the title** — a static min-width starves the title
  column when columns are toggled. Wrapper is `overflow-x: auto`.
- Click any heading to sort (▾/▴ marker in accent; headings need ~14px of padding so the arrow
  never clips). Score sorts by the weighted score.
- Leading cell: a tick checkbox + row number. Trailing cell: an **add to queue** button that
  becomes "✓ queued 3" showing its position. Ticking several reveals a bulk "Add N to queue".
- Keyboard: `j`/`k` move the cursor, `enter` opens, `q` queues, `a`/`v`/`x` set verdicts,
  `s` saves a draft, `esc` returns to the queue, `?` toggles the key map.
- Row colors are a stoplight scale (see Design tokens). A **Key** below the table explains
  every color and the WARN/OK meanings.
- Default scope is the resolved rig only. An `--all-rigs` checkbox performs the cross-rig read;
  mutations stay single-rig.

### 4. Brief detail

Two-column flex row: content column (`flex: 1 1 auto; min-width: 0; max-width: 640px`) and a
254px Properties column (`flex: none`). **Do not float the properties box** — a float only
shortens following line boxes, so bordered blocks render underneath it.

Order down the page:

1. Breadcrumb: `← queue`, slug, bead id, "brief 3 of 8".
2. Title — Cormorant Garamond 30px/600.
3. **How this was made** — provenance panel. One always-visible summary line (producer formula,
   step, actor, source bead) expanding to the full trace: initiating call, gates evaluated,
   drafted-by (`create-brief`, composed by `brief-prep`), output shape, structure defined in
   `present-it` (reference only — not invoked), input/output artifacts, trace and operation ids.
   For error briefs it reads "Filed automatically by brief-gate-keep on detection — no human
   asked for this brief."
4. 2px `--color-neutral-900` rule.
5. If HELD: a red banner naming the diagnostic code, what it means, and a button through to the
   error brief. No acknowledge-and-continue affordance.
6. If this *is* an error brief: the diagnostic block — severity + code, message, then data
   location / detected by / filed / trace / what it blocks, and the policy reference as a knowl.
7. If compact: the COMPACT FORM card — DECISION / CONTEXT / RECOMMEND, the `brief-prep`
   authorization line (`compact_eligible: true`, `server_touching: false`,
   `user_skill_touching_override: false`, shape ≠ capability-blocker), and CONFIRM `y` / `n` /
   `grill-me-further`. `y` and `n` prefill the panel; grill-me-further requests full-form
   *preparation* (the brief leaves the stack until re-filed) and shows the full form badged
   "FULL FORM — as brief-prep would re-file it".
8. **§1 What is being decided** — first content, per the Decision-at-Top invariant.
9. **§2 Recommended answer** — a click-to-adopt card: transparent background, 3px accent left
   edge, "▸ Click to adopt — approve of option B, fills the panel below". Hover tints the box
   and underlines the line. Clicking sets verdict + option + a reason quoting the recommendation,
   then scrolls the panel into view.
10. **§3 Assumptions surfaced** — bullets indented 26px, each a claim plus its evidence.
11. **§4 Alternatives named** — option-major table: one row per option (Option label | title,
    prose, and a mono `radius · reversible · gates` line). Every option is shown at once,
    including **E · Other**. Each row is click-to-adopt like §2. Option-major *columns* do not
    work here — five columns in a ~420px content column crush the prose to ~9 characters a line.
12. **§5 Risks** — one table, each risk a row tagged BREAKS (red) or COMMITS US TO (gold).
13. **§6 Supporting evidence** — table: Purpose / Files changed / Test evidence (path, exact
    command, exit code, wall time) / Mathematics. Never omitted; "N/A — pure engineering change"
    where it doesn't apply.
14. **§7 Plan membership, blocking, required gates** — table: Timeline / Plan / Blocks /
    Blocked by / Gates. Blocks and Blocked-by rows show the dependent bead (id knowl + title)
    with the reason on its own line, or "reason not recorded on the edge" where the data has none.
    *Backend note: the dependency edge should carry a reason field.*
15. Required gates summary one-liner.
16. The adjudication panel.

### 5. Adjudication panel

- Header bar: "Adjudicate" (or "Repair this violation" on error briefs), with a draft stamp
  ("draft saved 12s ago" / "no draft saved" / "written to bead").
- On an error brief, a scope line: "You are deciding the invariant here, not mc-71p9 — that
  brief unblocks when you submit."
- Verdict chips: approve / revise / reject / defer — or repair / waive / reject source brief /
  defer on error briefs.
- **No-brainer** checkbox. Ticking reveals a reason textarea prefilled with a plausible guess;
  unticking hides it and keeps the text for a re-tick. Recorded as a classifier signal, separate
  from the verdict.
- **Disposition** — required, no bare verdict. Chips for every named option plus E · Other
  (which opens a textarea). Briefs with no named alternatives preselect "Accept the
  recommendation as filed" and label the group "accepted as filed unless you change it" —
  agreeing with the producer must never require declaring an alternative to it.
- Reason textarea (required, >2 chars).
- **Save draft** + **Review verdict →**. Review shows the DRY RUN effect plan, then
  **Submit and advance** writes the verdict and opens the next brief in the current order.
- **Locked state:** while a brief is HELD the panel turns red (red border, red title bar,
  `#fdf5f4` body) with a LOCKED badge, and every verdict except `reject` is struck through and
  inert — approving a brief that reached the stack through a failed gate would ratify the
  violation.

### 6. Pile

Table of produced-but-unpromoted briefs: title, slug, a paragraph on what is actually holding it,
state (PROMOTABLE green / WAITING yellow / GATE REJECT red), the gate it waits on, next step, and
time in pile. A SHUFFLER panel shows lock state and the next window. Footnote: a gate reject is a
producer problem, not a decision.

### 7. Deferred

Cards showing each brief, its defer window, time left, who deferred it and why. Footnote: nothing
resurfaces early — a deferred brief appearing before its window files an error brief.

### 8. Adjudicated

Closed decision beads, newest first: brief, verdict, option taken, timestamp, recorded reason,
producing formula, follow-up bead. In-session decisions appear at the top, tinted. No reopen
affordance — decision beads are immutable (B3.8); a change of mind is the follow-up bead.

### 9. Priority list

The user's own ordering. Starts **empty** with a real empty state. Drag rows to reorder. Shuffle
randomizes. **Rank by comparison** runs binary-insertion pairwise comparisons ("Which should I
adjudicate first?", ~1 comparison per placement, progress shown) and writes the resulting order.
This order drives "Submit and advance".

## Interactions & behavior

- Sorting: click cycles asc/desc; numeric columns start descending.
- Column toggles persist per user (the clerk asked for adjustable settings).
- Knowls: any rule ID, bead id or diagnostic code, anywhere in the text, is a dotted-underline
  knowl that expands an inline panel (name, source file, rule text). Bead knowls for briefs on
  the stack carry "open this brief →". Rules/beads in accent, diagnostic codes in red.
- Adopt actions scroll the adjudication panel into view (find the nearest scrollable ancestor;
  never use `scrollIntoView`).
- Drafts are keyed per brief and restored on reopen.
- Blocking is state, not styling: `blocked = exists(errorBrief) && !resolved(errorBrief)`.

## State

`view` (stack/pile/deferred/adjudicated/brief/priority), `scope`, `allRigs`, `sortKey`, `sortDir`,
`visibleColumns`, `cursor`, `picked` (bulk tick), `priorityList`, `scoreWeights`, `openBriefId`,
`verdict`, `option`, `otherText`, `reason`, `noBrainer`, `noBrainerReason`, `step`
(entry/review/done), `drafts`, `savedAt`, `resolvedErrors`, `decidedThisSession`, `openKnowls`,
`grill`, `pairwise`, `dragFrom`.

## Design tokens

From the Classical design system (`_ds/classical-…/styles.css`) — use the CSS variables, not
literals, for everything except the stoplight colors.

- Ground `--color-bg` `#f3f2f2`; surface `#eae9e9`; ink `--color-text` `#201f1d`.
- Accent `#b68235` with a 100–900 ramp (`--color-accent-100` `#fff3e4` … `-900` `#3a270d`).
  Body-size accent text uses `--color-accent-700` `#7d5411`.
- Neutrals `--color-neutral-100` `#f8f4f4` … `-900` `#2d2b2b`; `--color-divider` = ink at 16%.
- Type: `--font-heading` Cormorant Garamond (600 ceiling for UI), `--font-body` Lora,
  and `ui-monospace, Menlo, monospace` for identifiers, commands and figures.
  Tabular numerals (`font-feature-settings: 'tnum'`) on all counts and columns of figures.
- Spacing `--space-1` 4.6px … `--space-8` 36.8px; radius `--radius-sm` 2px / `-md` 4px / `-lg` 7px.
- Focus: `outline: 2px solid var(--color-accent); outline-offset: 2px` — never the default ring.

**Stoplight scale** (semantic, defined once and reused everywhere):

| State | Text | Fill | Edge |
| --- | --- | --- | --- |
| ERROR / GATE REJECT | `#8f2c22` | `#fbeceb` | `#8f2c22` |
| HELD | `#b0570f` | `#fdeedd` | `#d98322` |
| WARN / WAITING | `#856512` | `#fbf4d5` | `#d4b02c` |
| PROMOTABLE | `#3f6b3a` | `#edf3ea` | `#5d8a52` |
| OK | `--color-neutral-500` | none | none |
| Cursor | — | `--color-accent-100` | `--color-accent-600` |

A **DRY RUN** badge (10px mono, 0.08em tracking, 1px `#8f2c22` border) marks anything that is
preview or classifier output only, with a legend in the footer. It appears on the no-brainer lane
and the effect plan. Apply it to any other non-writing surface.

## Assets

None. No images or icon files — all affordances are type, rules and color. Fonts come from the
Classical design system.

## Files

- `Briefs Dashboard.dc.html` — the full prototype (template + logic in one file).
- `github.md` — repo association and the screen → source-file map.

Source material this was built from, in `tdupu/mathcity`: `skills/present-it/SKILL.md`,
`skills/catch-no-brainer/SKILL.md`, `skills/create-brief/SKILL.md`, `skills/brief-prep/SKILL.md`,
`subdomains/brief-system/POLICY.md`, `POLICY-beads.md`, `POLICY-formulas.md`, `POLICY-POLICY.md`,
`README-clerk.md`, `README-development.md`, `README-formulas.md`, `GLOSSARY.md`, and
`subdomains/dev/docs/plans/mcp/MCTL-MCP-{PLANNING-PROMPT,IMPLEMENTATION-PLAN}.md`.
Visual conventions from `roed314/lmfdb` → `lmfdb/templates/style.css`.
