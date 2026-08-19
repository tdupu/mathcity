# Deprecated `gascity-packs/mathcity` — Salvage Audit

| Field | Value |
| --- | --- |
| Date | 2026-08-19 |
| Bead | `mc-dlq` (extends the repos-side surface audit recorded there) |
| Deprecated copy | `<repos-root>/gascity-packs/mathcity` @ `f2c5c20` |
| Canonical copy | `<repos-root>/mathcity` (`tdupu/mathcity`) @ `3ba30b4` |
| Scope | Repos-side working trees, all `gascity-packs` branches, stashes. Read-only; nothing modified. |

## 1. Verdict

**Safe to retire. Nothing must be forward-ported.** All 141 differing files are
standalone-newer; there are zero deprecated-newer and zero genuinely-divergent
files, and the salvage list is empty.

## 2. How the direction was established

Timestamps were not trusted. Every file was placed in exactly one content-based
class, listed below in descending order of evidential strength. The five classes
partition all 141 files:

1. **`ANCESTOR-BLOB` (70 files).** The deprecated file's blob hash is byte-identical
   to an object already in the canonical repo's history
   (`git cat-file -e <hash>` against `<repos-root>/mathcity`). The deprecated content
   *is* a past state of the canonical file. This is conclusive.
2. **`SPLIT-REWRITE` (29 files).** The deprecated file is byte-identical to the
   canonical repo's **initial commit** `7715c4f` ("Initial standalone mathcity pack",
   2026-08-10 11:53:32 -0400) once the split's path rewrites are normalized
   (`<repos-root>/gascity-packs/mathcity` → `<mathcity-pack-root>`,
   `gascity-packs/mathcity/` → `mathcity/`). The canonical repo started from this
   content and moved on.
3. **`SPLIT-REWRITE-RESIDUAL` (33 files).** As above, but with a small residue
   (1–7 lines) that the normalizer did not cover. Every residual line was read
   by hand. All are the split's own rewrites — the canonicality banner
   (`"Canonical copy: … in gascity-packs"` → `"… in this mathcity pack"`),
   remaining path forms, and pack-source rewrites in `pack.toml`
   (`source = "../gascity"` → a pinned `https://…` URL + `version = "sha:…"`).
   No residual line carried behaviour.
4. **`RESCOPED-AT-SPLIT` (2 files).** See §5.
5. **`CACHE-ARTIFACT` (7 files).** `__pycache__/*.pyc` and `.pytest_cache/*`.
   Build/test cache, not content; the generating sources are parity-checked above.

A fourth, independent sweep backed this up: every deprecated-only line across all
141 files was normalized and searched against an index of **every line in the
canonical working tree** (71,160 unique lines). The only lines found nowhere were
those belonging to the two rescoped files and to documentation the canonical repo
deliberately restructured after the split (§5) — never content the canonical side
had not first possessed.

The reverse test also came back clean: for all 141 files, the **canonical** content
appears nowhere in `gascity-packs` history. The deprecated copy never held a newer
version of anything.

## 3. Is work still landing on the deprecated copy?

**The practice has stopped.** The last write to `mathcity/` in `gascity-packs` was
**2026-08-10**, nine days ago. The canonical repo has taken **106 commits** and is
active through today.

Commits touching `mathcity/` in `gascity-packs`, most recent first:

| Commit | Timestamp | Subject |
| --- | --- | --- |
| `f2c5c20` | 2026-08-10 22:02:34 | docs: align mathcity dev policy with standalone source |
| `5005882` | 2026-08-10 10:30:06 | fix(mathcity): prepare pack for registry review |
| `84ea02d` | 2026-08-10 09:45:15 | Merge upstream/main into main |
| `313d954` | 2026-08-07 03:44:47 | fix(mathcity): default work-briefed review_mode agent->report |
| `70dddcd` | 2026-08-05 22:34:56 | docs(mathcity): correct README-skills parent-pack count 49->50 |

Exactly **one** commit lands after the split (`7715c4f`, 11:53:32):
`f2c5c20` at 22:02:34 — one second after the canonical repo's own `2521fc8`
(22:02:33). Its subject, *"align mathcity dev policy with standalone source"*,
states the direction, and the content confirms it: it is a **back-port from the
canonical repo into the deprecated one**, not original work. Of the 17 files it
touched, every one that still differs is classified `ANCESTOR-BLOB` — it
introduced nothing the canonical side lacks.

Other landing sites checked and clear:

- **Uncommitted changes** under `gascity-packs/mathcity/`: none (0 entries).
- **All branches**: `git log --all --since='2026-08-10 11:53:32' -- mathcity/`
  returns only `f2c5c20`. No post-split landings on any branch.
- **Stranded branches from `mc-dlq`**: `codex/mathcity-registry-review` carries
  `cf157e7` (10:30:06) and `95d911a` (10:33:53) — both **pre-split**. `cf157e7`
  reached main as `5005882`. `95d911a` ("scrub legacy local README references")
  did not reach that branch's main, but its effect is present on **both** sides:
  all 8 files it touched have zero `~/gt` / `~/repos` leaks in either copy.
  `fork/quimby/skill-fixes-checkwork-pushfleet-mail` is entirely 2026-08-05,
  pre-split, and `mc-dlq` already confirmed its skills are in the canonical copy.
- **`_to_delete/`** (untracked, dated 2026-08-10): vendored upstream
  `mattpocock-skills` and a notes file. Third-party vendor content, not mathcity
  work product, and already staged for deletion by its own directory name.

## 4. Salvage list

**Empty.** No file, hunk, or line in the deprecated copy needs to move to the
canonical repo before retirement.

The three files that exist *only* in the deprecated copy are all junk, and one of
them independently confirms the lag direction:

| Path | Assessment |
| --- | --- |
| `helloworld.txt` | Stray file. The canonical repo **deleted** it in `383c49c` (2026-08-14); the deprecated copy still carries it — the deprecated side is behind, not ahead. |
| `subdomains/proof-assist/mcp/scholar/src/scholar_mcp/__pycache__` | Python bytecode cache. |
| `subdomains/proof-assist/mcp/stacks/src/stacks_mcp/__pycache__` | Python bytecode cache. |

One further artifact, not a salvage item: `skills/file-briefs/file-briefs` in the
deprecated copy is a **broken symlink** pointing at
`../../gascity-packs/mathcity/skills/file-briefs`, which does not resolve from its
own location. It is dead weight that retirement removes.

## 5. The two files rewritten at the split

These are the only files whose difference is not a simple path rewrite or a later
canonical edit. Both were **deliberately rescoped by the split commit itself**, and
both were checked for dropped content.

**`docs/INSTALL.md`** — 698 lines (deprecated) → 195 at the split → 196 today.
The deprecated file is *"Gas City Packs — Installation & User Guide"*: a
`gascity-packs`-wide manual covering `gc`/`bd`/Dolt installation, base-pack import,
a brief-system tutorial, the Mayor dispatch model, and troubleshooting. The
canonical file is *"Mathcity Installation Guide"*, scoped to this pack. This is a
correct scope narrowing — most of the dropped material documents Gas City itself,
not mathcity. Three deprecated sections have no canonical counterpart:
"Inside vs. outside agents", "Dependency Matrix", and the "Briefs stuck in
`.pile/`" troubleshooting entry. The first is covered by city-level `CLAUDE.md`;
the other two are genuinely gone, but they document the *installer's* environment
rather than pack behaviour, and they are recoverable from `gascity-packs` history
at any time. **Not blocking** — flagged here as a documentation-coverage
observation, not a salvage item.

**`skills/formula-creator/SKILL.md`** — 241 lines → 149 at the split. A
condensation, not a truncation: every section survives in renamed form
(pack/name → Inputs, TOML skeleton, steps, pool routing, validation, commit
discipline, "what this skill does NOT do"). The one section that looked dropped —
*"Run the surface-test quality gate (mathcity formulas only)"* — is present in the
canonical `skills/formula-creator/SKILL.md` and indexed in `README-skills.md`.
Nothing lost.

## 6. The known lag instance (`work-briefed.toml`)

**Confirmed, and it is representative.** The prior finding — a store-scope fix
routing a formula step to a bare run target reached 36 of 38 copies, and the two
stragglers were both `gascity-packs/mathcity` copies — still holds on the
repos-side copy:

| Copy | `metadata` run target | `[vars] … default` |
| --- | --- | --- |
| Deprecated `gascity-packs/mathcity` | `"mathcity.brief-operator"` (old target) | `"work-briefed"` |
| Canonical `<repos-root>/mathcity` **and all 11 canonical worktrees** | `"gc.run-operator"` (bare) | `"mathcity.work"` |

The deprecated copy is the lone straggler across all 13 repos-side copies, and it
lags on a second axis too (`work-briefed` vs the renamed `mathcity.work`).
`formulas/work-briefed.toml` classifies as `ANCESTOR-BLOB`, so this is not
divergence — it is simply an older state.

**Is the deprecated copy uniformly behind, or behind in some places and ahead in
others?** Uniformly behind. Across all 141 differing files the direction never
inverts once.

One apparent inversion was checked and dismissed: the deprecated copy has **zero**
`~/gt` / `~/repos` home-path leaks while the canonical copy has **12** files
containing them. All 12 are canonical-only files authored *after* the split
(design docs under `subdomains/dev/docs/`, `subdomains/brief-system/docs/`, and
`subdomains/dev/skills/check-documentation-policy/SKILL.md`). This is fresh
P1.10 drift on the canonical side, not content the deprecated copy could supply —
it is a separate hygiene item, and retiring the deprecated copy neither causes nor
fixes it.

## 7. Full classification — all 141 differing files

Direction is `standalone-newer` for every row. The evidence column is the test
from §2 that established it.

| Path | Direction | Evidence |
| --- | --- | --- |
| `POLICY-POLICY.md` | standalone-newer | ANCESTOR-BLOB |
| `POLICY-formulas.md` | standalone-newer | ANCESTOR-BLOB |
| `POLICY-skills.md` | standalone-newer | ANCESTOR-BLOB |
| `README-beads.md` | standalone-newer | ANCESTOR-BLOB |
| `README-formulas.md` | standalone-newer | ANCESTOR-BLOB |
| `agents/brief-operator/agent.toml` | standalone-newer | ANCESTOR-BLOB |
| `assets/brief-pipeline/gates.toml` | standalone-newer | ANCESTOR-BLOB |
| `assets/brief-pipeline/paths.toml` | standalone-newer | ANCESTOR-BLOB |
| `assets/scripts/checks/brief-check.sh` | standalone-newer | ANCESTOR-BLOB |
| `assets/scripts/stuck-bead-watch.py` | standalone-newer | ANCESTOR-BLOB |
| `docs/MAYOR-ONBOARDING.md` | standalone-newer | ANCESTOR-BLOB |
| `docs/TEST-CYCLE-GUIDE.md` | standalone-newer | ANCESTOR-BLOB |
| `docs/beads-and-latex-scratch.md` | standalone-newer | ANCESTOR-BLOB |
| `docs/rule-prefix-registry.md` | standalone-newer | ANCESTOR-BLOB |
| `docs/testing-guide.md` | standalone-newer | ANCESTOR-BLOB |
| `formulas/brief-decision-dispatch.toml` | standalone-newer | ANCESTOR-BLOB |
| `formulas/brief-producer-failure-record.toml` | standalone-newer | ANCESTOR-BLOB |
| `formulas/brief-producer-failure-rollup.toml` | standalone-newer | ANCESTOR-BLOB |
| `formulas/brief-producer-repair.toml` | standalone-newer | ANCESTOR-BLOB |
| `formulas/brief-record-decision.toml` | standalone-newer | ANCESTOR-BLOB |
| `formulas/brief-shuffle.toml` | standalone-newer | ANCESTOR-BLOB |
| `formulas/create-issue-briefed.formula.toml` | standalone-newer | ANCESTOR-BLOB |
| `formulas/no-brainer-candidate-curate.toml` | standalone-newer | ANCESTOR-BLOB |
| `formulas/planning-briefed.formula.toml` | standalone-newer | ANCESTOR-BLOB |
| `formulas/pr-pipeline-briefed.formula.toml` | standalone-newer | ANCESTOR-BLOB |
| `formulas/smoke-test-briefed.toml` | standalone-newer | ANCESTOR-BLOB |
| `formulas/work-briefed.toml` | standalone-newer | ANCESTOR-BLOB |
| `orders/brief-producer-failure-rollup-on-record.toml` | standalone-newer | ANCESTOR-BLOB |
| `orders/brief-shuffle-pile.toml` | standalone-newer | ANCESTOR-BLOB |
| `orders/stuck-bead-watch.toml` | standalone-newer | ANCESTOR-BLOB |
| `skills/check-briefs/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `skills/check-molecules/scripts/enumerate-molecules.sh` | standalone-newer | ANCESTOR-BLOB |
| `skills/create-bead-manifest/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `skills/create-brief/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `skills/intercept-bead/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `skills/present-briefs/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `skills/refine-bead-manifest/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `skills/simple-work/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `skills/wake-city/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/brief-system/POLICY.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/brief-system/skills/decisions-to-briefs/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/computing/POLICY.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/computing/README.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/POLICY-city.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/POLICY.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/README.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/adjust-workers/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/check-build-formulas-and-skills/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/check-build-hygiene/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/check-plan-hygiene/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/city-status/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/formula-creator-math/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/formula-work/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/hourly-check/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/new-formula-policy/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/push-the-fleet/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/skill-creator-math/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/strand-sweep/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/testing-work/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/dev/skills/update-README/SKILL.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/latex/POLICY.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/latex/README.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/lmfdb/POLICY.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/lmfdb/README.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/magma/POLICY.md` | standalone-newer | ANCESTOR-BLOB |
| `subdomains/proof-assist/README.md` | standalone-newer | ANCESTOR-BLOB |
| `tests/producer-failure-rollup-routing/smoke_test.sh` | standalone-newer | ANCESTOR-BLOB |
| `tests/producer-repair-e2e-red/red_test.sh` | standalone-newer | ANCESTOR-BLOB |
| `tests/stuck-bead-watch/test_stuck_bead_watch.py` | standalone-newer | ANCESTOR-BLOB |
| `tests/work-briefed-routing/smoke_test.sh` | standalone-newer | ANCESTOR-BLOB |
| `POLICY-beads.md` | standalone-newer | SPLIT-REWRITE |
| `docs/CITY-RESTART-CHECKLIST.md` | standalone-newer | SPLIT-REWRITE |
| `docs/DOGFOOD-WORKFLOW.md` | standalone-newer | SPLIT-REWRITE |
| `formulas/brief-gate-keep.toml` | standalone-newer | SPLIT-REWRITE |
| `formulas/formula-creator-math.toml` | standalone-newer | SPLIT-REWRITE |
| `skills/check-molecules/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `skills/file-briefs/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `skills/mayor-math/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `skills/mayor-math-handoff/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `skills/mayor-math-prime/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `skills/mayor-math-prime/templates/PROMPT-mayor-generic.txt` | standalone-newer | SPLIT-REWRITE |
| `skills/mayor-math-restart/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `skills/prime-clerk/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `skills/priority-work/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `skills/work/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/brief-system/DOGFOOD.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/brief-system/skills/decisions-to-briefs/LANDING-HANDOFF.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/brief-system/skills/new-brief-policy/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/computing/skills/check-computing-policy/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/computing/skills/new-computing-policy/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/dev/docs/BEADS-DEEP-DIVE-2026-07-08.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/dev/docs/EXPANDED-STRUCTURE-DRAFT-2026-07-08.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/dev/docs/HURDLES-CLASSIFICATION-2026-07-08.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/latex/skills/new-latex-policy/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/lmfdb/skills/configure-database/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/lmfdb/skills/configure-server/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/lmfdb/skills/new-lmfdb-type-policy/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/proof-assist/skills/search-scholar/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `subdomains/proof-assist/skills/search-stacks/SKILL.md` | standalone-newer | SPLIT-REWRITE |
| `ABOUT.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `ONBOARDING.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `README-skills.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `README.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `assets/scripts/checks/lost-bead-filter-check.sh` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `docs/CITY-OPERATION-REFERENCE.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `docs/README-gascity-repository-layout.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `pack.toml` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `skills/adjudicate-brief/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `skills/brief-prep/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `skills/catch-no-brainer/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `skills/coordinate-review/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `skills/critical-review/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `skills/gate-test-execution-silent/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `skills/grill-and-present/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `skills/improve-test-execution-silent/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `skills/is-good-experiment/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `skills/is-good-test/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `skills/present-it/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `subdomains/brief-system/README.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `subdomains/brief-system/skills/check-brief-policy/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `subdomains/dev/docs/CODEX-REVIEW-RESPONSE-2026-07-08.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `subdomains/dev/docs/METHODOLOGY-PACK-VERDICT-2026-07-08.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `subdomains/dev/orders/reap-prepare-item-worktrees.toml` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `subdomains/dev/pack.toml` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `subdomains/latex/skills/check-latex/SKILL.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `subdomains/magma/README.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `tests/artifact-root-scoping/smoke_test.sh` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `tests/create-issue-briefed/smoke_test.sh` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `tests/lockless-brief-shuffle/smoke_test.sh` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `tests/pr-pipeline-briefed/smoke_test.sh` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `tests/smoke-test-briefed-self/README.md` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `tests/smoke-test-briefed-self/smoke_test.sh` | standalone-newer | SPLIT-REWRITE-RESIDUAL |
| `docs/INSTALL.md` | standalone-newer | RESCOPED-AT-SPLIT |
| `skills/formula-creator/SKILL.md` | standalone-newer | RESCOPED-AT-SPLIT |
| `.pytest_cache/v/cache/lastfailed` | standalone-newer | CACHE-ARTIFACT |
| `.pytest_cache/v/cache/nodeids` | standalone-newer | CACHE-ARTIFACT |
| `assets/scripts/__pycache__/lost-bead-filter.cpython-313.pyc` | standalone-newer | CACHE-ARTIFACT |
| `assets/scripts/__pycache__/stuck-bead-watch.cpython-313.pyc` | standalone-newer | CACHE-ARTIFACT |
| `assets/scripts/__pycache__/tail-end-detector.cpython-313.pyc` | standalone-newer | CACHE-ARTIFACT |
| `tests/stuck-bead-watch/__pycache__/test_stuck_bead_watch.cpython-313-pytest-8.3.2.pyc` | standalone-newer | CACHE-ARTIFACT |
| `tests/tail-end-detector/__pycache__/test_tail_end_detector.cpython-313-pytest-8.3.2.pyc` | standalone-newer | CACHE-ARTIFACT |

## 8. What could not be determined

- **Stash contents are not provably redundant.** `gascity-packs` `stash@{0}`
  ("pre-formula-repair-overlap", on `codex/brief-filter-repairs`) holds three
  `mathcity/` files — `assets/scripts/checks/brief-check.sh`,
  `formulas/planning-briefed.formula.toml`, `formulas/smoke-test-briefed.toml`.
  None matches a canonical blob exactly, and each differs substantially from the
  current canonical file (223 / 39 / 136 changed lines). They are **pre-split WIP**
  that the canonical files have since evolved well past, so this is almost
  certainly superseded work rather than stranded work — but "superseded" was
  inferred from the size and direction of the drift, not proven line-by-line.
  Stashes are not part of the deprecated *copy* and survive retirement of the
  `mathcity/` subtree regardless, so this does not gate the verdict.
- **City-side copy not audited.** Only the repos-side surface was in scope. A
  `<city-root>`-side copy of `gascity-packs/mathcity`, if one exists, was not
  examined. `mc-dlq` should not be closed on this report alone unless that side
  is separately cleared.
- **Binary cache files were not decompiled.** The 5 `.pyc` files and 2
  `.pytest_cache` entries were classified as regenerable cache from the parity of
  their generating sources, not by comparing bytecode.
- **Bead/Dolt stores were not compared.** This audit covers pack file content
  only. Issue-tracker state in the Dolt data plane is out of scope.
