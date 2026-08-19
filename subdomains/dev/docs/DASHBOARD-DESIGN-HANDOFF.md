# Brief dashboard — design session handoff

Paste this into the new session. It is everything the interface work needs and
nothing it does not.

## What the thing is

A local operator dashboard for adjudicating **briefs** (decisions awaiting a
human verdict) in a multi-rig "Gas City" workspace.

- Code: `assets/scripts/mctl_dashboard/` in `<repos-root>/mathcity`
- **All CSS + markup is in `render.py`** — one `<style>` block with a CSS-variable
  palette at `:root` (`--bg --panel --ink --muted --line --accent --shade`, plus
  `--info --warn --error --fatal --review`). Restyling is one file.
- Stdlib `http.server`, server-rendered HTML, **no dependencies, no build step,
  works with JavaScript off.** Keep that — the repo's stated stack is stdlib-only
  and a `npm install` would be rejected.
- Run: `bin/mctl dashboard serve --city ~/gt` → `http://127.0.0.1:8471`
- Data arrives over MCP tool calls, not shell. Do not add shell-outs.

Views today: `/` overview, `/briefs` list, `/briefs/<id>` detail, `/diagnostics`,
`/validate`, `/work`, `/trace`.

## Real data, measured 2026-08-19 — design against these numbers

```
200 briefs across 16 registered rigs (5 have any briefs)

decision_state:  pending 114 · malformed 76 · adjudicated 10

per-rig:  hecke 114 · gascity-packs 69 · gascity 11 · agent_skills 5 · differential_valuations 1
          (11 further rigs are registered and empty — they must still render)

diagnostics city-wide:  7 actionable  ·  634 under review
                        (MBRF021 ×400, MBRF004 ×158, MBRF005 ×76)
```

A brief record carries: `bead_id`, `brief_id`, `rig_id`, `title`, `status`,
`decision_state`, `labels[]`, `created_at`, `updated_at`, `canonical_source`,
`policy_references[]`, `redundant_artifacts[]`.

Real titles run long and unglamorous — *"[onboarding-decision] gamma0-aia-s27:
authorize in-session live repair on aia-s27 (66 del, 172 rename, 7 recompute)"*.
Design for that, not for short labels.

## The screen that matters most, and it does not exist yet

Adjudication. This is the whole point of the tool and it is unbuilt. Required
shape, from the owner:

```
verdict  (dropdown — everything is a dropdown)
  APPROVE
  REJECT   → reveals a sub-dropdown; "moot" has several distinct flavors:
               moot — already executed
               moot — superseded (decision recorded on another bead)
               moot — withdrawn / killed
               close / kill
  REVISE   → includes "aimed at the wrong rig, re-target"
  DEFER
  OTHER    → reveals a textarea: specific instructions for this bead

[ ] no-brainer      ← tick-box, ORTHOGONAL to verdict. Does not exist today and
                      is explicitly wanted. Combines with any verdict.

rationale (one line, required)
```

**One step. No preview.** The owner: *"I don't need to be able to preview an
adjudication."* An earlier design had preview→confirm with a stale-preview guard;
that two-step flow is being removed for this path.

`OTHER` vs `REVISE`: REVISE sends the brief back to be rewritten. OTHER approves
an action the owner specified themselves instead of picking an offered option —
nothing goes back, work proceeds on their terms.

Adjudication is refused on most of the live queue (`MBRF004` gates 88 pending
briefs). **The refusal is correct behavior and needs a good empty/blocked state** —
it is what the operator will hit most often, so it deserves real design attention
rather than a red box.

## Four honesty properties — do not design these away

These were expensive to establish and a prettier UI is the most likely way to
lose them.

1. **`MBRF021`, `MBRF004`, `MBRF005` are NOT actionable.** They render **with
   their codes visible**, in a separate "under review" region, excluded from
   actionable counts, **with no repair affordance anywhere**. 634 vs 7 — if the
   under-review region is styled to look like a problem list, the operator will
   try to fix 634 things that are fine.
2. **The malformed count carries an inline caveat.** "Malformed" means *closed
   with no verdict field* — not damaged. The caveat must stay adjacent to the
   number, not behind a tooltip.
3. **`artifact_trust` renders BOTH ways**, per rig — so "trusted" is visually
   distinct from a page that forgot to say. Currently false on all 16 rigs.
4. **A degraded rig is a named row with its reason**, never a silently smaller
   total. "Never collapse this to a count."

## Model correction worth knowing

Adjudicated is **binary** — per POLICY, a brief is *"in exactly one of two
adjudication states: adjudicated or not adjudicated."* The verdict is a separate
field, and `no-brainer` is a third, orthogonal axis. Do not model
superseded/withdrawn/transferred as peer *states*; they are REJECT/REVISE
subtypes in the dropdown above.

## Constraints

- stdlib only, no JS required, no build step
- loopback only — this is not going on a routable interface
- desktop **and** mobile (375×812 verified today); wide tables scroll inside
  their own container, page body never scrolls horizontally
- diagnostic **codes** always visible; severity may be color, but color is never
  the only carrier
- do not edit `subdomains/brief-system/POLICY.md` (a separate audit owns it)
- commits: mathcity P5.5 **forbids `Co-Authored-By: Claude`** — use
  `[autogenerated by Claude <model> on <date>]`

## Where to start

`git rebase main` first — worktrees branch from a stale `origin/main` (~60
commits behind, nothing pushed). Then `render.py`.
