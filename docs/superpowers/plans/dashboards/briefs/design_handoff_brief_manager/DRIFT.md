# Drift: this version vs. the earlier design

Two earlier builds of this dashboard exist (session 1, ~2100 lines each). The current file is a
from-scratch rebuild at roughly a third the size. Most of the difference is deliberate — a leaner,
triage-first surface — but some of it dropped invariants the first design had argued for. This file
tells you which is which, so you do not "restore" a decision or ship a regression.

## Deliberate in the current version

- **Triage-first stack.** Row-level quick actions (`resolve →`, `reject →`) let a clerk clear
  no-brainers and empty briefs without opening them.
- **Untitled/empty briefs are handled**, not dead ends: `Untitled — {bead}` everywhere, a
  reject-only verdict set, and a matching notice on the detail view.
- **Header tooltips on dashed columns**, so an intentional dash cannot read as a broken cell.
- **Malformed view**, with copy insisting the classification means *closed with no verdict field*.
- **Report-to-issue-tracker link** on blocking notices, prefilled against `tdupu/mathcity`.
- **Keyboard cursor** (`j`/`k`/`enter`) with a visible gold outline.

## Dropped, and worth restoring

These were decisions in the first design, not accidents of it:

| Dropped | Why it mattered |
|---|---|
| **Design-token system** — 422 `var(--color-*)` references became ~220 hardcoded hexes | the OKLCH-generated accent ramp was provenance-traceable; hardcoding it loses the source of truth. In a real codebase, define tokens first. |
| **Knowls** (LMFDB pattern) on every policy rule, bead id and diagnostic code | a clerk could see the rule text, why it exists, the enforcing gate and its adoption date without leaving the page. Now they are plain text. |
| **"How this was made" provenance panel** | producer formula, step, actor, initiating call, gates evaluated, artifacts, trace and operation ids. |
| **Error briefs as a first-class class** | invariant violations were auto-filed briefs with their own repair options; the blocked brief was HELD with a route *to* that error brief. HELD survives here as an inline notice with nowhere to go. |
| **Compact form for no-brainers** and `grill-me-further` (request full-form preparation) | the compact/full distinction is how the pipeline actually produces briefs. |
| **§4 alternatives + click-to-adopt** | option-major rows, an explicit "E · Other" with free text, and one click to set verdict + disposition + a reason quoting the option. |
| **Save draft, and the two-step Review → Submit and advance** | with the DRY RUN effect plan shown before anything is written. |
| **Pile gate state** (PROMOTABLE / WAITING / GATE REJECT, the gate waited on, time in pile, shuffler lock) | the pile view is now a single "not readable" banner. |
| **Deferred detail** (window, time left, who deferred and why) and **Adjudicated outcome** (verdict, disposition, follow-up bead, molecule step table) | both are now dashes or absent. |
| **Priority list shuffle and rank-by-comparison** (binary insertion, ~1 comparison per placement) | ordering a long list by hand is the tedious part. |
| **`FIXTURES · NOT LIVE DATA` badge** | the page still shows invented data. Convention F33 of the original design — every count derives from the query it opens, none are authored literals — is met again in this version, but the fixture disclosure is not. **Restore this before anyone sees the prototype.** |

## Between the two earlier versions

For completeness: the second earlier build differed from the first only by a refinement pass — a
header that wraps at narrow widths, the rig multi-select popover replacing an `--all-rigs`
checkbox, a store-health popover (engine, branch, commit, schema, doctor), an Outcome column with
expandable rows and the molecule step table on Adjudicated, and counts moved from authored literals
to computed values.
