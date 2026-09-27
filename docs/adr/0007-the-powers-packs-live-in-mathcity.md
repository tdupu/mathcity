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
`mathcity/subdomains/proof-assist/skills/roadmap-draft/references/` as
reference-tier files with no SKILL.md precisely so they would move freely
whichever way this went, and `kolchin-monitor` declined to act on the question
relayed through the Mayor at all. (Path corrected — see Amendment 1.)

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
  `subdomains/proof-assist/skills/roadmap-draft/references/` (`repos/mathcity`
  `7460137`, 827 lines) are already in the right place. They were positioned
  not to presume this answer; the answer happens to keep them where they are.
  (Path corrected — see Amendment 1.)
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

## Amendment 1 — the path this ADR cited was stale within the hour

Date: 2026-09-23

As first written, this ADR twice cited
`subdomains/proof-assist/skills/using-roadmaps/references/`. That path was
correct when verified at `7460137` and **dead two commits later**:

```
3e8e3d9  Rename using-roadmaps to roadmap-draft to match its frontmatter
1e7256c  Add the roadmap-draft leaf, justified by a 2/2 failing baseline
7460137  Record the roadmap-construction references      <- what was verified
```

Live path: `subdomains/proof-assist/skills/roadmap-draft/` — now `SKILL.md`
plus the same three references. Every sibling in that subdomain has
directory == frontmatter name; this one was the sole exception, because the
directory had been named for a router `roadhog` then decided not to build.
Corrected in both places above.

**Why this is recorded rather than quietly fixed.** The mechanism is the same
one this ADR's Context section already describes twice: a claim true of one
container, read as a property of the system. Here the container was *time* — a
verified path is a statement about the moment of verification, and nothing
re-checks a record when the thing it cites moves underneath it. Verifying at
source is necessary and is not sufficient; a shared path needs re-checking at
use, not only at write.

`roadhog` caught this and reported it against its own rename, which is the only
reason it was caught at all. It reported two further instances of the identical
shape in the same hour — a `pcf` handoff asserting an urgent defect at a HEAD
that had already moved (`0d9eaa1`), and two false Mathlib-absence claims
corrected at `0219847`. Its own `process.md` phase 6 names this failure, and it
produced one within an hour of writing that phase. The catalogue of the same
mechanism across the night runs to six variants and is being maintained by
`kolchin-monitor` as `ma-n0d`.

The ruling in this ADR is unaffected.

## Amendment 2 — the path was stale a second time, and the skill now has one name in two repos

Date: 2026-09-25

**Amendment 1 fixed the leaf name and missed a subdomain move.** It corrected
`using-roadmaps` → `roadmap-draft` while leaving `subdomains/proof-assist/`
in place. The skill had already moved to `subdomains/lean/`. So the first
correction was itself partially stale when written — the same mechanism, caught
one layer down, one day later.

**Taylor then ruled the naming, 2026-09-25:** the skill is `draft-roadmap`, and
both copies carry that name. Live state:

```
repos/mathcity    subdomains/lean/skills/draft-roadmap/     SKILL.md + references/{process,schema,failure-modes}.md
repos/agent-skills skills/draft-roadmap/                    same four files, byte-identical
                   skills/using-leanpowers/SKILL.md         two routing rows added
                   plugins/leanpowers/skills.json           27 -> 28 entries
```

`draft-roadmap` is verb-first, matching agent-skills' convention and the skill's
own H1, which already read "# Draft a roadmap". The commit subjects quoted in
Amendment 1 (`3e8e3d9`, `1e7256c`) are historical and are deliberately left
naming `roadmap-draft` — they record what those commits said, not where the
skill lives.

**Two copies, one name, deliberately kept byte-identical.** The agent-skills
copy gained a paragraph on confirming a probe could have found something, plus
the zsh `NOMATCH` trap and a warning against "fixing" it with `NULL_GLOB` — all
measured 2026-09-22/25. That content was synced back to the mathcity copy the
same day, so the two do not diverge. **Two same-named skills with different
bodies would be the container failure this ADR keeps documenting**, in its most
direct form: an agent reads one, cites it, and the reader opens the other.

Whether one copy should eventually be a pointer to the other is not decided
here. What is decided is that while both exist they stay identical.

**Count.** This ADR has now been stale about the same skill three times in three
days — `using-roadmaps` → `roadmap-draft` → subdomain move → `draft-roadmap`.
Each correction was accurate when written. The lesson is not to write more
carefully; it is that **a record citing a path someone else owns is a standing
liability**, and the only real fix is to cite as little of it as the record can
survive on.

[autogenerated by Claude Opus 5 v2.1.231 (Claude Code) on 2026-09-22;
 Amendment 1 on 2026-09-23; Amendment 2 on 2026-09-25]
