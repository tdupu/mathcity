# Handoff: Brief Manager dashboard

## Overview

The Brief Manager is the adjudication surface for MathCity's brief pipeline. A clerk uses it to
work a **stack** of decision briefs — read what is being decided, record a verdict, and keep an
ordering of what to do next. Alongside the stack it exposes the other pipeline states (pile,
error briefs, deferred, adjudicated, malformed) and a personal priority list.

The design's governing principle is **epistemic honesty**: the dashboard must never let a missing
read look like a real value. Empty cells, dashes, "not readable" banners and DRY RUN badges are
deliberate, and each one says whether it means *zero* or *unknown*. Preserve this when
implementing — it is the point of the design, not decoration.

## About the design files

`Brief Manager Dashboard.dc.html` in this bundle is a **design reference written in HTML**. It is
a prototype that shows intended look and behavior; it is not production code to lift. The task is
to **recreate it in the target codebase's own environment** (React, Vue, SwiftUI, native, whatever
is established) using that codebase's routing, state, component and styling conventions. If no
frontend environment exists yet, pick the framework that best fits the project and build it there.

All data in the file is fixture data. Every value is invented — see **Data sources** below for what
each column must eventually read from.

## Fidelity

**High fidelity.** Colors, typography, spacing, row heights, column widths, hover states and
keyboard behavior are all final and specified exactly below. Recreate the UI to match, using the
codebase's existing primitives where they can hit these values.

Two caveats:
- The typographic identity (Cormorant Garamond + Lora, warm parchment neutrals) is intentional and
  document-like rather than app-like. If the host codebase has a design system, ask before
  overriding it — this is a deliberate visual argument, not a default.
- Six columns are permanently dashed because the core does not expose them yet. That is correct
  behavior today, not an unfinished state.

## Screens / views

Seven views share one persistent header and sidebar. There is no router in the prototype — view is
a single state value. In a real app these should be routes.

### Shell

**Header** (`#f8f4f4`, `padding: 12px 20px 10px`, `border-bottom: 2px solid #2d2b2b`,
`display:flex; align-items:baseline; gap:18px; flex-wrap:wrap`)
- Wordmark "Brief Manager" — Cormorant Garamond 600, 25px, `letter-spacing: 0.01em`.
- Context line — monospace 11.5px: `city ~/mathcity · rig hecke · store .beads/hecke.db`.
  Labels `#7d7979`, values `#605d5d`, separators `#bab6b6`.
- Right group (`margin-left:auto; gap:14px`): live counts as links — `pile —`, `stack 9`,
  `deferred 0`, `error briefs 1`, and `keys`. 12px, `#605d5d`, `border-bottom: 1px dotted #a06f24`.
  **Every count must come from the same query as the view it opens.**
- `pile —` carries a tooltip explaining the dash is "not readable," not zero.

**Keyboard strip** — a `<details id="mc-keys">` under the header, `background:#fff3e4`,
`padding: 6px 20px`. Summary "keyboard" (mono 11px). Expanded: `j` next row, `k` previous row,
`enter` open the brief under the cursor, plus the note that these three are the only part of the
dashboard needing JavaScript and each duplicates something clickable.

**Sidebar** (`width: 186px`, `background: #eae9e9`, `border-right: 1px solid rgba(32,31,29,0.16)`)
Two sections, each with a dark bar header (`#2d2b2b` bg, `#ffe3bf` text, Cormorant 13px 600,
uppercase, `letter-spacing: 0.06em`, `padding: 9px 12px`) and an italic 11px `#7d7979` explainer:

- **PIPELINE** — "Where the pipeline says each brief is. Produced briefs land in the pile; gates
  promote them to the stack." Items, in order, each `padding: 6px 12px`, 13px, label left / count
  right:
  | Item | Count source |
  |---|---|
  | Stack — ready for you | briefs visible in scope `stack` |
  | Pile — awaiting gates | `—` (not readable) |
  | Error briefs | scope `errors` |
  | Adjudicated — closed | closed decision beads |
  | No-brainers — DRY RUN | scope `nobrainer` |
  | Deferred — none open | 0 (a real zero) |
  | Malformed — no verdict field | malformed rows |

  Active item: `color:#5a3b0a; font-weight:600; border-left: 3px solid #a06f24` (inactive items
  carry `border-left: 3px solid transparent` so nothing shifts). Hover:
  `background:#e0dcdc; color:#5a3b0a`.

- **PRIORITY LIST** — clickable bar (turns `#7d5411` when its view is active) + explainer "Your
  ordering over the same stack — nothing here changes pipeline state." Then either the next five
  queued bead ids (mono 10.5px) or `next up — nothing queued`.

- **IMPORTANCE** — four sliders (`unlock_count` 8, `convoy / epic` 5, `age` 3, `priority` 4;
  range 0–10, `accent-color:#a06f24`) under the caveat that no policy defines importance, plus a
  warning box that the Score column they drive has no value for any brief yet.

**Footer** — `background:#eae7e7`, mono 10.5px `#7d7979`: "mctl briefs — read paths never mutate;
verdicts fail closed on ERROR" and the DRY RUN legend.

### 1. Stack (default) — also Error briefs and No-brainers

One table component rendered under three scopes; only the heading, the scope filter and the count
change. Heading is Cormorant 27px 600 with a mono 12px subtitle
`all rigs · N briefs · sorted by {column} {ascending|descending}`, then a `2px solid #2d2b2b` rule.

Controls row: **Columns** toggle button, a `rig` chip reading `all rigs` (display only in the
prototype — should become a multi-select), and a primary **Open top brief →** button
(`background:#a06f24; border:1px solid #7d5411; color:#f8f4f4`, hover `#7d5411`).

**Table.** `table-layout: fixed`, `border-collapse: collapse`, 12.5px, in an `overflow-x:auto`
wrapper with `border-bottom: 2px solid #2d2b2b`. **Every cell needs `box-sizing: border-box`** —
without it each explicit width silently grows by its padding and the title column collapses.

- Header row: `background:#eae7e7`, `border-bottom: 2px solid #2d2b2b`, cells mono 10.5px 600
  uppercase `letter-spacing:0.06em`, `padding: 6px 12px`. Every heading is a sort link
  (hover: `color:#5a3b0a` + underline); the active one is `#5a3b0a` with a `▾`/`▴` marker.
  Health and Rec. carry tooltips explaining their dashes.
- Twelve columns, all toggleable. Widths in px; `numeric` right-aligns and sets mono 11.5px;
  `default` is the initial visible set:

  | key | label | width | numeric | default |
  |---|---|---|---|---|
  | slug | Brief | 290 | no | yes |
  | rig | Rig | 86 | no | yes |
  | artifact | Artifact | 124 | no | no |
  | unlock | Unlock | 78 | yes | yes |
  | score | Score | 74 | yes | yes |
  | age | Age | 64 | yes | yes |
  | prio | Priority | 82 | no | yes |
  | kind | Type | 96 | no | no |
  | nopts | Opts | 62 | yes | yes |
  | sev | Health | 78 | no | yes |
  | source | Source | 82 | no | no |
  | rec | Rec. | 88 | no | yes |

- Leading cell: tick checkbox (`accent-color:#a06f24`) + row number (mono 10px `#9b9797`).
- Title cell: Cormorant 14.5px 600 `#201f1d`, single line, `text-overflow: ellipsis`. An untitled
  brief renders `Untitled — {bead}` — the same fallback must be used everywhere the title appears.
- Unlock, Score, Priority, Type, Opts and Rec. always render an em dash. The note under the table
  says why, and "An empty cell here means no value was read, not a value of zero."
- Trailing cell (184px): a queue chip (`add to queue` / `✓ queued N`) and, on rows that qualify, a
  quick action. **All chips stay on one line — rows must be a uniform 33px.**
  - `kind === 'nobrainer'` → `resolve →`
  - no title and no body → `reject →`
  Both are outlined `#8f2c22`, fill `#8f2c22` / `#fdeedd` on hover, and carry a tooltip stating
  why the action is the honest one. Firing either removes the brief from the stack, drops every
  count that includes it, and writes a preview banner above the table.

- Row states (`box-shadow: inset 3px 0 0 {edge}` + background):
  | state | background | edge |
  |---|---|---|
  | error brief | `#fbeceb` | `#8f2c22` |
  | ERROR diagnostic | `#fdeedd` | `#d98322` |
  | WARN diagnostic | `#fbf4d5` | `#d4b02c` |
  | clean | transparent | transparent |
  | keyboard cursor | `outline: 2px solid #a06f24; outline-offset: -2px` | — |

  Whole row is clickable (`cursor: pointer`) and hovers to
  `background: rgba(160,111,36,0.10)` — a translucent overlay so each row keeps its own tint. The
  checkbox cell and the action cell must stop propagation so ticking or resolving does not navigate.

Below the table: **Add ticked to priority list** + the reminder that ticking changes nothing until
added; then the colour key (ERROR / HELD / WARN / OK / cursor, each a 22×13 swatch, items
`white-space: nowrap`); then the six-columns-are-empty note.

### 2. Brief detail

Two columns, `gap: 22px`. Body `max-width: 640px`; `Properties` aside 254px.

- Title Cormorant 30px 600 (`Untitled — {bead}` when absent), bead id mono 11.5px `#7d7979`.
- Status banner (`background:#f8f4f4`, 3px left border, 12.5px) — one of four, and it must never
  contradict the stack row's quick action:
  | condition | lead | border |
  |---|---|---|
  | no title and no body | "Nothing to adjudicate." + "No title and no body — reject is the only honest verdict." | `#8f2c22` |
  | open | "Ready to adjudicate." + "Go to the verdict panel ↓" | `#a06f24` |
  | held | "Adjudication is held." + code + "— a gate failed before this reached the stack." | `#8f2c22` |
  | refused | "This brief cannot be adjudicated yet." + code + "— this check is under review." | `#bab6b6` |
- `2px solid #2d2b2b` rule, then sections: marker (mono 11px `#7d5411`) + heading (Cormorant 17px
  600) + body (`text-wrap: pretty`, `#2d2b2b`).
- **Adjudicate panel** — bordered box, `max-width: 640px`. Title bar `#2d2b2b`/`#ffe3bf`, or
  `#8f2c22`/`#fdeedd` titled "Repair this violation" when held.
  - Blocking notice, when held / refused / empty: label, one-line message, explanatory paragraph,
    and a **"Report {code} on the mathcity issue tracker →"** button that opens a prefilled GitHub
    issue against `tdupu/mathcity` — title `{code}: {message} ({bead})`, body carrying bead, rig,
    brief title, diagnostic and the explanation, labels `brief-manager,{code}`.
  - Verdict radios: `approve` / `revise` / `reject` / `defer`. When held or empty, the three
    non-reject options are `line-through` `#bab6b6` and inert — reject is the only live verdict.
  - Disposition text input ("Option letter, or leave blank to accept as filed"), Reason textarea.
  - **Review verdict →** with the hint that it shows the DRY RUN effect plan first and writes
    nothing; disabled with the hint "no verdict can be recorded while this is unresolved" when locked.
- Properties aside: dark bar header + Rig / Source / Artifact / Created rows.
- `← Back to the stack`.

### 3. Priority list
Personal ordering, empty by default, kept in the browser. Explains it is not a fact about the
briefs and will not follow the user to another machine. Rows: drag handle glyph, index, title,
`move up` / `move down`. Empty state: dashed box, "Nothing here yet", → **Go to the stack**.

### 4. Pile
Single banner: the pile is not readable through the typed surface; nothing shown is a count of
zero; tracked as issue #66. No table — do not invent one.

### 5. Deferred
"No briefs are deferred. This is a real zero read from the bead store, not a gap."

### 6. Adjudicated
Banner: the verdict itself is not readable, only that one was recorded. Table Bead / Title /
Updated / Verdict, verdict column dashed with a tooltip. Closing note: decision beads are never
reopened (B3.8) — a change of mind is a new bead.

### 7. Malformed
Banner: "malformed" means *closed with no verdict field* — **not** that the brief is damaged; the
classification is under review. Table Bead / Title / Updated.

## Interactions & behavior

- **Navigation** — sidebar items, header counts and every in-copy link switch views. Prototype has
  no history; real implementation should route so the back button and deep links work.
- **Row click** opens the brief. Checkbox and action-chip cells stop propagation.
- **Keyboard** — `j`/`ArrowDown` and `k`/`ArrowUp` move a cursor (gold outline) within the current
  ordering, `enter` opens the brief under it. Only while a table view is showing; suppressed when
  focus is in an input, textarea or contenteditable. Hovering a row moves the cursor to it.
  Because the cursor indexes the *ordered* list, sorting and the cursor must read the same
  ordering function — keep it in one place.
- **Sorting** — click any heading; same key flips direction. Numeric columns start descending,
  text columns ascending. Only slug, rig, age and health have real sort values today; the rest sort
  as constants because nothing is read.
- **Column toggles** — checkbox form; columns always render in canonical order regardless of the
  order they were switched on.
- **Quick actions** and **verdict submission** are previews. Nothing mutates: submitting shows
  "Preview requested (DRY RUN) — nothing has been written."
- **Hover** — every interactive element has a state. Authoring note: in the prototype's template
  language, hover styles must be literal CSS, not computed values.
- No responsive breakpoints. The table scrolls horizontally; the header wraps.

## State

| state | initial | notes |
|---|---|---|
| `view` | `queue` | one of queue / brief / priority / pile / deferred / adjudicated / malformed |
| `scope` | `stack` | stack / errors / nobrainer — filters the queue table |
| `sortKey` / `sortDir` | `age` / `-1` | -1 descending |
| `columns` | default set | visible column keys |
| `ticked` | `{}` | bead → bool, for bulk add |
| `queued` | `[]` | priority list order; should persist per user |
| `selectedBead` | `null` | detail view subject |
| `weights` | `{unlock:8, convoy:5, age:3, prio:4}` | score sliders |
| `verdict` / `reason` | `null` / `''` | adjudication draft — should survive navigation |
| `previewMessage` | `''` | DRY RUN banner text |
| `showColumns` | `false` | column picker open |
| `resolved` | `[]` | beads cleared by a quick action |
| `cursor` | `0` | keyboard row index |

Derived, never stored: every count, the ordered row list, and all cell text.

## Data sources

Nothing in the prototype is live. Each dashed column needs a real read before it can show a value:

| Column / panel | Needs |
|---|---|
| Unlock | `unlock_count` from `mctl_core` (brief `he-saeno4`) |
| Priority | brief priority from `mctl_core` |
| Type | brief class (error / no-brainer / standard) |
| Opts | decision option count |
| Rec. | the recommendation itself (issue #66) |
| Score | invented formula — not a policy artifact; keep it labelled a hypothesis |
| Pile | gate state per pile item; no tool reports it (issue #66) |
| Adjudicated verdict | the option taken, reason and follow-up bead (issue #66) |
| rig chip | rig-scoped reads with cross-rig support; mutations stay single-rig |

Diagnostic codes `MBRF004`, `MBRF021`, `MBRF060`, `MBRF061`, `MBRF062` are flagged
"under review" and the UI says so wherever they appear.

## Design tokens

**Colors**

| Role | Hex |
|---|---|
| page background | `#f3f2f2` |
| surface / raised | `#f8f4f4` |
| header bar, rules | `#2d2b2b` |
| sidebar | `#eae9e9` |
| table header, footer | `#eae7e7` |
| text | `#201f1d` |
| body text | `#2d2b2b` |
| secondary text | `#444141` |
| muted text | `#605d5d` |
| faint text | `#7d7979` |
| disabled / placeholder | `#9b9797` |
| hairline | `rgba(32,31,29,0.16)` |
| divider grey | `#d7d3d3`, `#bab6b6` |
| accent (primary) | `#a06f24` |
| accent border / link | `#7d5411` |
| accent text | `#5a3b0a`, `#3a270d` |
| accent tint | `#fff3e4`, `#ffe3bf` |
| error | `#8f2c22` |
| error tint | `#fbeceb`, `#fdeedd` |
| held edge | `#d98322` |
| warn edge | `#d4b02c` |
| warn tint | `#fbf4d5` |
| row hover overlay | `rgba(160,111,36,0.10)` |

Stoplight scale, defined once and never reused for verdicts: ERROR red, HELD orange, WARN yellow,
OK neutral, cursor gold. A closed decision has no pipeline health.

**Typography**
- Display / headings: Cormorant Garamond 600 — 30px detail title, 27px view title, 25px wordmark,
  17px section heading, 13px sidebar bar, 14.5px table title cell.
- Body: Lora 400 (+ italic) — 14px base, `line-height: 1.45`; 12.5–13px in panels.
- Mono: `ui-monospace, Menlo, monospace` — 11.5px context/meta, 10.5px chips and footer, 10px
  row numbers, 10.5px uppercase table headings with `letter-spacing: 0.06em`.
- Minimum size anywhere: 10px, and only for row numbers.

**Spacing** — 2 / 4 / 5 / 7 / 9 / 12 / 14 / 18 / 20 / 22px. Table cells `5px 8px`, headings
`6px 12px`. **Radii** — 2px inputs and notices, 4px chips/buttons/cards. **Borders** — 1px
hairline, 2px section rules, 3px left accents, 5px on the held notice. No shadows except the 3px
inset row edge.

## Assets

- `CormorantGaramond-SemiBold.woff2`, `Lora-Regular.woff2`, `Lora-Italic.woff2` — bundled here,
  loaded via `@font-face`. Swap for the codebase's own font pipeline.
- No images or icons. The only glyphs are text characters (`→ ← ▾ ▴ ⋮ · —`). Don't add an icon set.

## Files

- `Brief Manager Dashboard.dc.html` — the complete design reference: all seven views, fixtures and
  behavior in one file.
- `support.js` — prototype runtime only. Not part of the design; do not port.
- Fonts, as listed above.
- `CHANGELOG.md` — the full decision record from the first design session, including the backend
  and policy work this design implies. **Read section G** before implementing: several behaviors
  here (error briefs being filed at all, verdicts carrying a disposition, the policy index) depend
  on pipeline changes that do not exist yet.
- `DRIFT.md` — what this version dropped relative to the earlier, larger design, so you know which
  absences are decisions and which are regressions worth restoring.

## Open questions

1. **No-brainers should not stay DRY RUN.** Today classification is preview-only, so every
   no-brainer still costs a decision. Intended end state: auto-processing with an audit trail and
   an undo window. Keep the lane's rendering driven by one "auto-processing enabled" flag so the
   switch from confirm-queue to audit-trail is a policy read, not a rewrite. Blocked on settling
   the N5 kill-switch scope.
2. **The rig chip is display-only.** It should be a multi-select over rigs; reads may span rigs,
   mutations must stay single-rig.
3. **Verdict submission is unwired.** The two-step Review → Submit flow, the effect plan, and
   "advance to the next brief in your order" are specified but not built.
4. **Score is a hypothesis.** No policy defines importance. Either land a policy or keep the
   sliders labelled as an experiment.
