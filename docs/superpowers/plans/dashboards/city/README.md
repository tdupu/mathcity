# City-operations dashboard — design + backend handoff

**Status:** design complete, backend not built. This directory is a handoff, not an implementation.

## What is here

| Path | What it is |
| --- | --- |
| `HANDOFF.md` | **Start here.** The backend work needed to make the prototype run: 14 typed `mctl` tools, 9 new recording items, the derivations the backend must own, the honesty invariants, slice order, and where the prototype and current `mctl` disagree. |
| `prototype/city-dashboard.dc.html` | The clickable prototype. Open directly in a browser — no build step, no server. Fixture-backed. |
| `prototype/support.js` | Runtime the prototype loads. Must sit beside the HTML file. |

## What the prototype is

A companion to the briefs dashboard, in the same shell: Classical tokens read from
`assets/scripts/mctl_dashboard/theme.py`, the knowl pattern from `knowl.py`,
LMFDB object-page conventions (properties box, related objects, fixed sidebar).

One container page type — the city, or any rig subset via the SCOPE multi-select —
plus object pages for molecule, step, agent, formula, gate, order, worktree and canary.
Controls follow a blast-radius ladder: low acts at once, medium previews an effect plan,
high requires the typed target name, gated is prepared and handed to the existing approval gate.

## What it is not

- **Not production code.** It is a design artifact: client-side state, inline styles, fixture data.
  In production every interactive state belongs in the query string exactly as
  `mctl_dashboard/state.py` already does it (scope, population filter, sort key, token window,
  firings `last n`, event tiers), and the page should need no JavaScript at all.
- **Not measured data.** Values marked `[SYN]` are invented-to-be-realistic. Values traceable to
  `dashboard-fixtures.md` `[OBS]` came off the live city on 2026-08-20 and are the right thing to
  test layout against. Do not cite a `[SYN]` number as a measurement.

## Source documents

`dashboard-screens.md`, `dashboard-object-model.md`, `dashboard-requests.md`,
`dashboard-fixtures.md`, `dashboard-gap-analysis.md`, and
`MATHCITY-TARGET-STATE.md` Part V (§60–62, §68).

## Two things to decide first

1. **Molecule identity.** `mctl_core` has no Molecule object. Nothing else on the page works until
   that noun exists — see `HANDOFF.md` §3.1.
2. **`EffectPlan.blast_radius`.** Not in the payload today; the entire control-safety ladder reads off it.
