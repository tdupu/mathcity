# ADR 0007 — The `*powers` packs live in mathcity

Date: 2026-09-22 · Status: accepted (Taylor, in-session ruling, S74)

## Context

Over one evening Taylor asked, in order, for: a `tauceti/lean` pack "with
workflows like the workflow for superpowers"; then "teachingpowers and
latexpowers packs as well"; then "mathpowers would be good too"; then raised
the alternative himself — "or maybe all of these powers go into mathcity."

That last line was an open question, not a ruling, and it was left open for
about an hour while three sessions measured the ground under it. Two of them
declined to presume an answer: `roadhog` placed its roadmap references in
`mathcity/subdomains/proof-assist/skills/using-roadmaps/references/` as
reference-tier files with no SKILL.md precisely so they would move freely
whichever way this went, and `kolchin-monitor` declined to act on the question
relayed through the Mayor at all.

**What was measured while it was open**, and it changed the shape of the
question:

- **"Like superpowers" means install AND convert, layered — not install
  instead of convert.** `gascity-packs/superpowers/formulas/` holds **12
  formulas**, and `mathcity/pack.toml:11-12` declares `[imports.superpowers]`.
  Imported pack formulas are not copied into the importing city's `formulas/`
  directory, which is why `mathcity/formulas/` shows none of them. The Mayor
  initially reported the absence as a property of the system; that was wrong,
  and `kolchin-monitor` corrected it at source.
- **A domain does not need a matching gascity base to ship formulas.** 4 of the
  12 are `type = "expansion"` with no `extends`
  (`brainstorming`, `code-review`, `plan-review`, `task-review`). The other 8
  extend a base. Expansion is the default; base implementation is the special
  case. `superpowers-fix-loop` extends its base and supplies nothing but
  parameterization — so a conforming entry can be nearly empty, which is the
  floor on effort.
- **The three math-side targets are dispatch routers, not workflows.**
  `latexpowers` carries 28 routes and `mathpowers` 22. The convertible lanes sit
  one level down, in what those rows point at — `math-workflow`'s synthesis
  sequence, `triage-referee-report`'s four rounds. The realistic scope is
  "wrap three sequences", not "author 28 lanes".
- **`using-*powers` skill counts are a weak signal** (`using-latexpowers` ×1,
  `using-mathpowers` ×1, `using-leanpowers` ×4, `using-teachingpowers` ×1).
  Skills are not what a pack ships; the formulas are. An argument for
  granularity resting on skill-thinness does not survive this.
- **A `taucetipowers` plugin already exists** at
  `~/repos/agent-skills/plugins/taucetipowers` (v0.1.0), bundling
  `using-taucetipowers`, `create-issue-tauceti` and `pr-pipeline-tauceti`, with
  a condensed contract at
  `skills/pr-pipeline-tauceti/references/tauceti-contract.md`. Canonical sources
  live in `agent-skills/skills/`.

## Decision

**The `*powers` packs live in mathcity.** Taylor, verbatim: *"Let's put the
powers pack into mathcity."*

This resolves the alternative he raised himself. It covers the family under
discussion at the time — `latexpowers`, `mathpowers`, `teachingpowers`, and the
`tauceti`/`lean` work — as mathcity pack content rather than as separate
top-level packs or as `agent-skills` publications.

## Consequences

- `roadhog`'s roadmap references at
  `subdomains/proof-assist/skills/using-roadmaps/references/` (`repos/mathcity`
  `7460137`, 827 lines) are already in the right place. They were positioned
  not to presume this answer; the answer happens to keep them where they are.
- The existing `taucetipowers` plugin is a **starting point, not a competitor**.
  Its canonical sources are in `agent-skills`; bringing that work under mathcity
  is a migration question this ADR settles the destination of but does not
  schedule.
- Granularity **within** mathcity — one subdomain per powers family or one
  shared home — is NOT decided here. This ADR fixes the repository, not the
  internal layout.
- Conversion work is scoped by the measurements above: wrap the sequences the
  routers point at, using `type = "expansion"` by default, and do not assume a
  gascity base is required.

## What this ADR does not license

Editing `city.toml` to import anything. The standing rule
(`bd recall city-toml-via-packs-not-hand`, Taylor 2026-07-10) is that city.toml
changes come from pack updates through the PR pipeline. In this same session a
hand-added `[[named_session]]` for `gc.run-operator` collided with the one the
`gascity/roles` pack already declares and took every rig store down for ~90
seconds on `duplicate identity`. **A declaration absent from `city.toml` is not
absent from the city** — read the composed config, not one layer of it. That
lesson applies directly to whoever wires these packs in.

## Recording note

This ruling was given in conversation and recorded here because the typed
surface cannot record a decision that has already been made: `briefs_create`
mints only UNDECIDED briefs, and depositing a settled verdict as pending would
invert its state. That gap is `mc-c9tds` / `mc-q0nby`, and this is its third
observed instance in one session. An unrecorded ruling is, to the next session,
the same as no ruling — which is exactly how `gsp-duj6y8` came to be re-asked.

[autogenerated by Claude Opus 5 v2.1.231 (Claude Code) on 2026-09-22]
