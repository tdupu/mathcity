# Beads Deep Dive — mathcity GC-Native Redesign

**Date:** 2026-07-08
**Tracker:** `<repos-root>/gascity-packs/.beads/` (embedded Dolt, prefix `gsp-`)
**Author:** deep-research agent (outside-agent, read-only — no bead edits, no commits)
**Scope:** all open / in-progress / blocked beads, assessed against the human adjudicator's plan to
expand mathcity into 5 sub-domains (brief-system, computing, proof-assist,
latex/literature-search, lmfdb) as a GC-native domain pack.

---

## ⚠️ TOOLING ANOMALY — read first

`bd list` and `bd ready` return **only 3 beads**, but `bd stats` reports
**72 total / 27 open / 1 in-progress / 44 closed**. The two disagree by ~24 open beads.

- `bd list --status=open --json --limit 500` → 3 records.
- `bd list --all --json --limit 500` → 3 records.
- `bd stats` → 27 open.
- `bd search <term>` and `bd show <id>` **do** reach the missing beads (gsp-2c0,
  gsp-1pv, gsp-eqk*, gsp-7lc, …), so they are real, open, and in the DB.
- There is **no `.beads/issues.jsonl`** export (0-byte `interactions.jsonl` only);
  data lives in `.beads/embeddeddolt`. `bd sql` is "not supported in embedded mode".

**Interpretation:** `bd list`/`ready` appear to be reading a stale or partial index
(likely a Dolt working-set / index-skew situation, cf. the `gc_binary_staleness`
memory pattern). This inventory was therefore reconstructed via `bd search` +
`bd show`, so it may be **incomplete** — treat the count below as a lower bound.
**Recommend:** the human adjudicator/clerk verify `bd version` (1.1.0 here) against the canonical
lockstep build and consider `bd dolt` reconcile before trusting `bd list`/`ready`
for planning. This anomaly is itself a candidate bead (see Section 4).

---

## Section 1: Bead Inventory

Enumerated via `bd search` across ~40 terms + `bd show`. Grouped by theme.

### 1a. Core mathcity GC-native migration (the plan's spine)

| ID | P | Type | Title / tracks | Pack-structure assumption |
|----|---|------|----------------|---------------------------|
| **gsp-eu2** | P0 | feature | Migrate mathcity to `imports.gc`: remove gastown deps, add gc-native agents + formulas | Pack is currently a standalone workflow engine w/ gastown deps (polecats, refineries) + a generic `codex-worker`. Target: `[imports.gc]`, specialized agents (brief-preparer, critical-reviewer, experiment-reviewer, decision-recorder, review-synthesizer), `[steps.check]` scripts, orders→formulas. |
| **gsp-20u** | P1 | feature | Working draft: redesign mathcity to GC-native structure | The design doc for gsp-eu2. Enumerates the target: `[imports.gc]`; 5 specialized agents; formulas w/ `[steps.check]`; typed artifacts under gc `artifact_root` (NOT `.beads/briefs`); skills check-latex/coordinate-review/record-decision; **5 planned sub-domains: brief-system, computing, proof-assist, latex/literature-search, lmfdb**; check-latex → multi-step formula w/ **~5 hurdles**; **hurdles replace gates throughout**. |
| **gsp-1pv** | P1 | feature | Document model: move brief pipeline out of `.beads/` into gc `artifact_root` | Briefs currently under `.beads/briefs/` (staging/pile/stack/archive/decisions/manifest.jsonl). Target `artifact_root` = `~/.gc/mathcity/briefs/` w/ front-matter schema + bead metadata keys. Plan doc: `mathcity/BRIEF-DOCUMENT-MODEL-PLAN-2026-07-08.md`. |
| **gsp-2c0** | P2 | task | Rename `gates` → `hurdles` throughout mathcity | Pack has `gates/` (5 TOML) used as brief-policy checklist (G1–G16). Collides w/ GC's "gate" = `[steps.check]`. Plan doc: `mathcity/HURDLES-RENAME-PLAN-2026-07-08.md`. |

### 1b. LaTeX gate / literature-search sub-domain (epic gsp-eqk)

| ID | P | Type | Title / tracks | Assumption |
|----|---|------|----------------|-----------|
| **gsp-eqk** | P1 | epic | F1 — LaTeX gates (check-latex SKILL + latex-gate.toml formula) | "Wait until city online" (the human adjudicator 2026-06-30 "this looks good"). Plan: `2026-06-26-gascity-triage/ACTION-ITEMS`. |
| **gsp-eqk.1** | P1 | task | F1a check-latex SKILL.md (umbrella: check-latex-style + check-citations + check-labels-and-refs) | Skill lives at `<repos-root>/agent-skills/skills/check-latex/` (canonical copy `mathcity.check-latex`). STATUS=PRELIMINARY DRY-RUN. Closes he-hsoc. |
| **gsp-eqk.2** | P1 | task | F1b `latex-gate.toml` formula (calls F1a) | **Assumes path `mathcity/gates/latex-gate.toml`** — i.e. still `gates/`, and a `gate` not a `hurdle`. Blocks polecat/he-d4l per he-86wu. |
| **gsp-fby** | P2 | epic | F2 — LaTeX merge (merge-latex-sections SKILL + mol-latex-merge formula) — **HOLD** | future-deliverable, hold. |
| **gsp-fby.1** | P2 | task | F2a merge-latex-sections SKILL.md | at `<repos-root>/agent-skills/skills/merge-latex-sections/`. |
| **gsp-fby.2** | P2 | task | F2b `mol-latex-merge.toml` (calls F2a, composes F1b) | **Assumes `mathcity/formulas/mol-latex-merge.toml`.** |
| **gsp-jas** | P2 | task | Thread check-citations + clean-citations into mathematics-pack formulas | Blocked by he-bb3p (skills ship first). Composition-first-then-wrap; pack composes, does not re-implement. Related to gsp-k6w. |

### 1c. Brief-system sub-domain (pipeline consolidation)

| ID | P | Type | Title / tracks | Assumption |
|----|---|------|----------------|-----------|
| **gsp-7lc** | P1 | epic | "mergers-and-acquisitions" formula (PR pipeline: brief-gated merge + GitHub approval signal) | Merge to main via GitHub API + brief approval gate + status-check "approval icon". deferred-post-city-restart. |
| **gsp-40g** | P2 | task | Approach C brief-cycle consolidation — impl plan anchor | Reuse REAL cargo on unmerged branches (polecat/gsp-xhc file-or-sendback gate @8631612; polecat/gsp-i9j stack-low trigger @a1cb9d7); RE-IMPLEMENT gsp-6bk (review-synthesizer agent) + gsp-itx (refinery post-merge hooks). Spec landed 51c1e09. |
| **gsp-3fn** | P2 | task | Review/land mol-mayor-q-brief ops branch | brief-pipeline ops. |
| **gsp-y2y** | P3 | task | DEFERRED: beads-canonical brief pipeline state (Approach B) | Explicitly deferred alternative to the artifact_root model (gsp-1pv). |

### 1d. Wave-2 math-pack codification (epic gsp-7nh)

| ID | P | Type | Title / tracks |
|----|---|------|----------------|
| **gsp-7nh** | P1 | epic | Wave 2 — Math-pack codification fill |
| **gsp-7nh.11** | P1 | task | W2.smoke — smoke-test W2.1–W2.10 codex-implemented work |
| **gsp-7nh.12** | P1 | task | W2.params — parameter-tuning W2 work |

### 1e. Pack health / substrate (adjacent, not core-migration)

| ID | P | Type | Title / tracks |
|----|---|------|----------------|
| **gsp-k6w** | P1 | task | Health check on the new mathematics pack (loads cleanly? activated? drift from architecture?) |
| **gsp-1uh** | P1 | task | DOCS: Substrate map — agent classes + gastown formulas + pool sizing + usage signal |
| **gsp-8w6** | P2 | task | P2.6 Witness branch hygiene: delete merged polecat branches + TTL for stale |

### 1f. Refinery / patrol / infra beads (mostly gastown-era, being migrated out)

| ID | P | Type | Title / tracks |
|----|---|------|----------------|
| **gsp-udi** | P2 | decision | Refinery merge hook: bottom-up tree contraction of complete leaves (decision record; memory `refinery-tree-contraction`) |
| **gsp-f79** | P1 | task | **IN PROGRESS** — Migrate mol-deacon-patrol formula from gt-era to gc-native (composes gt-cha) |
| **gsp-2f3** | P2 | bug | mol-refinery-patrol: next-iteration leaks open wisps (no reconcile block) |
| **gsp-bbo** | P2 | bug | mol-refinery-patrol wisps accumulate without burning (homog:7, lmfdb:6) |
| **gsp-3z8** | P3 | bug | mol-witness-patrol & mol-refinery-patrol miss `--include-infra` in wisp-reconcile bootstrap |
| **gsp-vbv** | P2 | bug | Refinery suggests canonical branch on target mismatch |
| **gsp-9q8** | P1 | bug | Pre-existing failure: 2 tests fail in github/tests/test_github_intake_service.py on main |

*(28 active beads reconstructed. `bd stats` says 27 open + 1 in-progress = 28 — this
matches, so the reconstruction is probably complete, but see the tooling anomaly.)*

---

## Section 2: Structural Assumptions

**Current pack structure (as beads + filesystem show):**
- Directory is **already renamed** on disk: `<mathcity-pack-root>/` (not
  `mathematics/`). But **beads and internal file paths still say `mathematics/`**
  (gsp-eqk.2, gsp-fby.2, gsp-k6w, gsp-jas, README, plan docs). Path drift exists.
- `pack.toml` is **minimal & pre-migration**: name=mathcity, version 0.2.0, schema 2,
  a `[providers.codex]` block — **no `[imports.gc]`**. Confirms gsp-eu2/gsp-20u premise.
- One agent: `agents/codex-worker/` (agent.toml + prompt.template.md) — the generic
  worker gsp-eu2 wants split into 5 specialized agents.
- `formulas/` (16 TOML) = brief-* pipeline + codex-dispatch + no-brainer-classify +
  decision/route/merge helpers. `orders/` (10 TOML) = brief-* orders. These are the
  "standalone workflow engine" gsp-eu2/20u target for restructuring into gc formulas.
- `gates/` (5 TOML: latex-gate, server-touching-safety-override, stale-claim,
  test-evidence, test-execution). `hurdles/` **does not exist yet** (gsp-2c0 pending).
- `skills/` (24) incl. check-latex, coordinate-review, record-decision, brief-prep,
  critical-review, is-good-test, is-good-experiment, present-briefs, etc.
- Planning docs staged in pack root (BRIEF-DOCUMENT-MODEL-PLAN, HURDLES-RENAME-PLAN,
  DRAINS-ANALYSIS, METHODOLOGY-PACK-VERDICT, CODEX-REVIEW-RESPONSE) — plans, not yet executed.

**Document model:** briefs currently `.beads/briefs/{.staging,.pile,stack,archive,
decisions}` + `manifest.jsonl` + `.shuffle.lock`. `.beads/briefs` **does not currently
exist on disk** (no live briefs), but ~10 pack files still reference the path
(gates/test-execution.toml, skills/record-decision, skills/brief-prep, etc.).
gsp-1pv migrates this to `~/.gc/mathcity/briefs/` typed artifacts; gsp-y2y is the
deferred beads-canonical alternative.

**GC integration level:** currently **standalone** (no `[imports.gc]`). The whole
gsp-eu2/gsp-20u thrust is standalone → gc-native. Half the infra beads (gsp-f79,
gsp-2f3, gsp-bbo, gsp-3z8) are mid-migration from "gt-era/gastown" to "gc-native",
so the pack straddles both worlds right now.

**Sub-domains:** Only **gsp-20u** names the 5 planned sub-domains, and only as a
requirements list inside one bead. **No sub-domain has its own epic or child beads.**
brief-system and latex/literature-search have *de facto* coverage (the brief-* and
F1/F2 beads), but they are not organized under sub-domain epics. **computing,
proof-assist, and lmfdb have zero beads** (see Section 4).

---

## Section 3: Impact of GC-Native Migration

Tags: **UNCHANGED** / **NEEDS-UPDATE** / **SUPERSEDED** / **VALIDATES**.

| ID | Tag | Rationale |
|----|-----|-----------|
| gsp-eu2 | **VALIDATES** | This bead *is* the migration. Should become the parent epic for the whole redesign. |
| gsp-20u | **VALIDATES** (needs promotion) | The design draft. Given the 5-sub-domain expansion, this should spawn child beads per sub-domain rather than remain one flat requirements list. |
| gsp-1pv | **VALIDATES** | Artifact_root move is a core requirement of the gc-native model (req #4 of gsp-20u). Aligned. |
| gsp-2c0 | **VALIDATES** | Hurdle rename is req #8 of gsp-20u. Directly serves the migration. Should run BEFORE latex-gate formula work (gsp-eqk.2) so that formula lands as a hurdle, not a gate. |
| gsp-eqk | **NEEDS-UPDATE** | Latex-gate epic = the latex/literature-search sub-domain seed. Re-parent under the redesign; re-frame "gate" as "hurdle." |
| gsp-eqk.1 | **NEEDS-UPDATE** | check-latex SKILL survives, but gsp-20u wants check-latex as a **multi-step formula with ~5 hurdles**, not just a skill. The skill becomes the callee; a new formula wraps it. Update AC. |
| gsp-eqk.2 | **NEEDS-UPDATE** | Hard-codes `mathcity/gates/latex-gate.toml`. After gsp-2c0 + formula redesign, path/kind changes to a hurdle-bearing formula. Update path + kind. |
| gsp-fby, .1, .2 | **NEEDS-UPDATE** | HOLD epic; F2b path `mathcity/formulas/mol-latex-merge.toml` and composition of F1b need the post-rename, post-imports.gc shape. Revisit after gsp-eqk lands. |
| gsp-jas | **NEEDS-UPDATE** | "thread into *mathematics* pack formulas" — path is now `mathcity`; composition target is the redesigned formula set. Still valid (composition-first), just re-point. |
| gsp-7lc | **UNCHANGED** (verify) | mergers-and-acquisitions PR-pipeline formula is orthogonal to pack internal structure; but if it must live in mathcity as a gc formula it should be authored gc-native from the start. Confirm home pack. |
| gsp-40g | **NEEDS-UPDATE** | Approach-C consolidation reuses branch cargo (file-or-sendback, stack-low) and re-implements the **review-synthesizer agent** (gsp-6bk) + **refinery post-merge hooks** (gsp-itx). The review-synthesizer is EXACTLY one of the 5 specialized agents gsp-eu2 wants — merge these efforts so it's built once, gc-native. High overlap risk. |
| gsp-3fn | **UNCHANGED** | Review/land an ops branch; independent of structure. |
| gsp-y2y | **SUPERSEDED** (soft) | Beads-canonical brief state (Approach B) is the rejected alternative to gsp-1pv's artifact_root model. Already DEFERRED; the gc-native decision effectively supersedes it. Consider closing with a pointer to gsp-1pv. |
| gsp-7nh, .11, .12 | **NEEDS-UPDATE** | Wave-2 codification "fill" + smoke/param tests were scoped against the OLD (standalone) pack. Post-migration, re-scope what's still worth smoke-testing vs. obsoleted by the restructure. |
| gsp-k6w | **NEEDS-UPDATE / VALIDATES** | Health check explicitly checks "drift from math-pack architecture." Post-migration it becomes the acceptance check FOR gsp-eu2 (does it load cleanly under gc? formulas parse?). Re-target to the new structure. |
| gsp-1uh | **UNCHANGED** | Docs/substrate map; adjacent. |
| gsp-8w6 | **UNCHANGED** | Witness branch hygiene; infra, not pack structure. |
| gsp-udi | **UNCHANGED** (VALIDATES infra) | Refinery tree-contraction decision; independent of mathcity structure. Recorded as memory. |
| gsp-f79 | **VALIDATES** | Already a gt→gc-native migration; same direction as gsp-eu2. |
| gsp-2f3 / gsp-bbo / gsp-3z8 / gsp-vbv | **UNCHANGED** | Refinery/witness patrol bugs; gastown-infra layer, not the pack. Note gsp-bbo references an `lmfdb` rig wisp queue — infra, not the planned lmfdb sub-domain. |
| gsp-9q8 | **UNCHANGED** | Pre-existing github test failure; unrelated. |

---

## Section 4: Missing Beads

Confirmed absent (searched lmfdb / proof / computing / sub-domain / rename / mathematics):

1. **lmfdb sub-domain** — NO bead. The only lmfdb hit (gsp-bbo) is an unrelated
   refinery-wisp bug. There is a live `mcp__lmfdb__*` MCP server + `search-lmfdb`
   skill, so the sub-domain has tooling but no tracked pack work.
2. **proof-assist / theorem sub-domain** — NO bead (0 hits for "proof").
   No Lean/Coq/theorem-checking pack work tracked.
3. **computing sub-domain** — NO bead (0 hits for "computing"). No Magma/Sage
   computing-workflow pack work tracked, despite many computing skills existing
   (profile-magma, notebook-to-package, improve-README, is-good-experiment).
4. **latex/literature-search sub-domain epic** — PARTIAL. Latex is covered by
   gsp-eqk/gsp-fby, but "literature-search" (the other half of the named sub-domain)
   has NO bead. No arXiv/citation-discovery/lit-review pack work tracked.
5. **check-latex as a formula with 5 hurdles** — NO dedicated bead. gsp-20u mentions
   it as one requirement line; gsp-eqk.1 tracks the SKILL only. The "make check-latex
   a multi-step formula with ~5 hurdles" deliverable needs its own bead.
6. **Pack rename mathematics → mathcity** — NO bead, yet the dir is ALREADY renamed
   on disk while beads/paths still say `mathematics/`. Either a rename bead is needed
   to sweep the stale `mathematics/` path references (gsp-eqk.2, gsp-fby.2, gsp-jas,
   gsp-k6w, README, plan docs) OR the rename is being treated as folded into gsp-eu2.
   Right now it's an untracked half-done rename.
7. **5 specialized agents** — NO per-agent beads. gsp-eu2 lists brief-preparer,
   critical-reviewer, experiment-reviewer, decision-recorder, review-synthesizer as
   one line. review-synthesizer partially overlaps gsp-40g/gsp-6bk. Each agent likely
   deserves a child bead.
8. **`[imports.gc]` + `[steps.check]` conversion** — tracked only as prose inside
   gsp-eu2; no discrete executable child beads.
9. **Sub-domain epic scaffolding** — NO parent epics for the 5 sub-domains. The plan
   would benefit from 5 epics (brief-system, computing, proof-assist,
   latex/literature-search, lmfdb) to re-home existing beads and expose the gaps.
10. **bd list/ready index anomaly** — should be a tracked infra bug (see top warning):
    `bd list` returns 3 while `bd stats` reports 27 open. Planning off `bd ready` is
    currently unreliable.

---

## Section 5: Priority Order & Critical Path

The redesign is a rename+restructure that everything else should land ON TOP of, so
order it so downstream authoring doesn't get redone.

**Phase 0 — Unblock planning (do first)**
- Fix the `bd list`/`ready` vs `bd stats` anomaly (new infra bead). Without it,
  `bd ready`-driven execution will silently skip ~24 beads.

**Phase 1 — Design + structural decisions (blockers for everything)**
1. **gsp-20u** (P1, design draft) — expand to cover the 5 sub-domains + spawn child
   epics. This is the spec; nothing gc-native should be authored before it settles.
2. **gsp-2c0** (P2, gate→hurdle rename) — cheap, mechanical, and it changes the
   vocabulary/paths that later formula work depends on. Do BEFORE authoring any new
   gate/hurdle-bearing formula (gsp-eqk.2, gsp-fby.2).
3. **gsp-1pv** (P1, artifact_root doc model) — decide brief storage before touching
   brief formulas/orders; supersede gsp-y2y.

**Phase 2 — Core migration (the P0)**
4. **gsp-eu2** (P0) — `[imports.gc]`, split codex-worker → 5 specialized agents,
   `[steps.check]`, orders→formulas. Depends on Phase 1 decisions (esp. gsp-20u,
   gsp-2c0, gsp-1pv). **Fold the pack-rename path sweep in here.**
   - Coordinate with **gsp-40g** so the **review-synthesizer** agent (gsp-6bk cargo)
     is built once, gc-native — not twice.

**Phase 3 — Sub-domain fill (after the frame exists)**
5. **latex/literature-search:** gsp-eqk → gsp-eqk.1 (check-latex skill) →
   NEW "check-latex-as-formula-with-5-hurdles" bead → gsp-eqk.2 (formula, now a
   hurdle) → gsp-jas (thread citations) → gsp-fby* (merge, HOLD).
6. **brief-system:** gsp-40g (consolidation) → gsp-3fn → gsp-7lc (M&A formula).
7. **computing / proof-assist / lmfdb:** create epics first (Section 4), then scope.

**Phase 4 — Verify**
8. **gsp-k6w** (health check) — becomes the acceptance gate for gsp-eu2.
9. **gsp-7nh.11 / .12** (smoke + param) — re-scoped to the new structure.

**Critical path:** anomaly-fix → gsp-20u → {gsp-2c0, gsp-1pv} → gsp-eu2 → gsp-k6w.
Infra/refinery bugs (gsp-2f3, gsp-bbo, gsp-3z8, gsp-vbv, gsp-9q8, gsp-udi, gsp-f79)
run on a **parallel independent track** — they don't block the pack redesign.

---

## Section 6: Open Questions for the human adjudicator

1. **bd list anomaly:** `bd list`/`bd ready` show 3 beads; `bd stats` shows 27 open.
   Is this a known index-skew (reconcile needed), or is the DB genuinely split?
   Planning is unsafe until resolved.
2. **Pack rename bookkeeping:** dir is already `mathcity/` but ~6 beads + README +
   plan docs still say `mathematics/`. New rename bead, or fold the path sweep into
   gsp-eu2's AC?
3. **Sub-domain epics:** create 5 parent epics now (brief-system, computing,
   proof-assist, latex/literature-search, lmfdb) and re-home existing beads, or keep
   the flat list in gsp-20u for now?
4. **gsp-20u granularity:** should it stay one omnibus design bead, or fan out into
   per-agent / per-formula / per-sub-domain child beads under gsp-eu2?
5. **review-synthesizer double-build:** gsp-eu2 (5 agents) and gsp-40g/gsp-6bk both
   produce a review-synthesizer. Merge into one gc-native effort? Which bead owns it?
6. **gate vs hurdle in formula TOML:** HURDLES-RENAME-PLAN flags an unresolved
   question — does GC's formula `[steps.check]` "gate" kind need renaming too, or only
   the mathcity brief-policy "gate" checklist? (frontmatter `review_gate`,
   `gc.brief.gate_profile` key.) Decide before executing gsp-2c0.
7. **check-latex shape:** keep as SKILL (gsp-eqk.1) AND add a formula wrapper with
   5 hurdles (gsp-20u), or replace the skill's gate role with the formula? Need the
   5 hurdles enumerated.
8. **gsp-y2y disposition:** the beads-canonical brief-state (Approach B) is the
   rejected alternative to gsp-1pv's artifact_root. Close it as superseded?
9. **computing / proof-assist / lmfdb scope:** these sub-domains have tooling
   (Magma/Sage skills, lmfdb MCP) but zero pack beads. What's the first deliverable
   for each — or are they deferred placeholders in the plan?
10. **gsp-7lc home:** does the mergers-and-acquisitions PR-pipeline formula live in
    mathcity (brief-system sub-domain) or a separate ops pack?
