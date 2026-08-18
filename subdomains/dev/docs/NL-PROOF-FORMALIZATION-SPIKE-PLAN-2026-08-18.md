# NL-Proof → Formalization Spike Plan — 2026-08-18

**Status:** Approved as a spike (throwaway); adoption NOT approved.
**Owner:** Taylor Dupuy. **Prepared by:** outside agent session, 2026-08-18.
**Subdomain:** `mathcity-proof-assist`. **Bead:** `mc-7h1`. **GitHub:** [tdupu/mathcity#49](https://github.com/tdupu/mathcity/issues/49).

Prepared from: Abouzaid, *How do AI systems prove math theorems?* (First Proof /
Stanford, ICARM 2026, `~/Downloads/icarm-ai.pdf`, 50 slides); the `1stproof`
GitHub org; `CBirkbeck/mathlib-quality` command frontmatter; `CBirkbeck/TauCeti`
`formalization.yaml` v0.2; `math-solve` `dag-schema.json` v5; and this pack's
existing [proof-assist README](../../proof-assist/README.md).

## Executive summary

`mathcity-proof-assist` today ships only the **search** half of proof support
(Loogle / arXiv / Stacks / Scholar) and names `formalize-claim` + `proof-check`
formulas that do not exist. This plan fills the **production** half: First Proof's
`math-solve` ensemble produces a natural-language proof as a verified DAG, and
Chris Birkbeck's `mathlib-quality` plugin carries that DAG into Lean 4.

The two artifact schemas are near-isomorphic — four of five `math-solve` DAG node
fields map directly onto what `mathlib-quality`'s `/develop` and `/blueprint`
require. **That mapping is the thing this spike tests.** The output is a written
report plus a how-to README, not adopted code.

## What is being decided (open — Taylor)

| # | Question | Default if unanswered |
| --- | --- | --- |
| Q1 | Spike scope: **A** as-scoped / **B** add `/beastmode` / **C** one problem / **D** swap the should-fail problem / **E** other | A |
| Q2 | May the `mathlib-quality` plugin be installed **scoped to the scratchpad project** (not globally)? It ships `/beastmode`, which by design does not stop to ask permission | blocked until answered |
| Q3 | Licensing (see § Licensing) — deferred until adoption, but it does not go away | defer |

## The two problems

Chosen to bracket Mathlib coverage, per Taylor: "one that should perform well and
one that shouldn't."

| Slot | Problem | Area | Writers | Why chosen |
| --- | --- | --- | --- | --- |
| should-work | **Batch-2 Problem 3** — a weighted Bernoulli sum exceeding its mean | Discrete probability | Aleksa Milojević; Benny Sudakov | Finite sums + inequalities; Mathlib `Finset.sum` / probability basics are real |
| should-fail | **Batch-2 Problem 5** — unique invariant measure for a singular SPDE | Stochastic PDE | Oleg Butkovsky; Jonathan C. Mattingly; Lorenzo Zambotti | Mathlib has essentially nothing for singular SPDEs / regularity structures |

**UNVERIFIED (verify at run start):** the problem↔number mapping is taken from
slide 3 of the deck. The published `.tex` files yielded only LaTeX preamble on
inspection. Also note the deck's §7 case study is headed "Problem 8" and concerns
polyhedral Lagrangian surfaces in R^4, while slide 4 lists Problem 8 as
Payne–Wang on a matroid's Dressian — one of those numberings is from a different
batch. Resolve before quoting either.

### Input artifacts (already public — do NOT re-run math-solve)

Running `math-solve` fresh costs ≈ $300/problem (deck slide 20: $1,817 for 6
problems on Opus). Use the published outputs instead:

```
https://github.com/1stproof/batch-2
  batch-2-AI-solutions/problem-03/submission-{A,B,C,D}.{tex,pdf}   # the four harnesses
  batch-2-AI-solutions/problem-05/submission-{A,B,C,D}.{tex,pdf}
  batch-2-human-solution/problem-03/human-solution.tex             # ground truth
  batch-2-human-solution/problem-05/human-solution.tex
```

Licensed **CC-BY-SA-4.0** per the repo's `DATA-LICENSE.md`. Confirmed present
2026-08-18.

## Naming: `firstproof`, not `1stproof`

The mathcity folder and every identifier derived from it use **`firstproof`**. The
upstream project styles itself **First Proof** and its GitHub org is **`1stproof`**;
our spelling is deliberately not an exact match. A leading digit is awkward in pack
identifiers and skill aliases (`mathcity-1stproof.math-solve`), and renaming after
scaffolding would mean redoing P1.8 exposure for every skill.

Upstream URLs, org references, and repo names keep their real spelling — only *our*
directory and identifiers are normalized.

## Repositories

| Repo | License | Role |
| --- | --- | --- |
| [1stproof/math-solve-skill-FP](https://github.com/1stproof/math-solve-skill-FP) | AGPL-3.0 code / CC-BY-SA-4.0 prompts | Claude Code skill ensemble; source of the DAG schema |
| [1stproof/math-solve-oss-FP](https://github.com/1stproof/math-solve-oss-FP) | AGPL-3.0 / CC-BY-SA-4.0 | Python + OpenRouter port; open-weights variant |
| [1stproof/math-typo-oss-FP](https://github.com/1stproof/math-typo-oss-FP) | AGPL-3.0 / CC-BY-SA-4.0 | Prompts only — typo/minor-error detection. Out of spike scope; candidate for `mathcity-latex` |
| [1stproof/batch-2](https://github.com/1stproof/batch-2) | CC-BY-SA-4.0 (data) | The input proofs |
| [CBirkbeck/mathlib-quality](https://github.com/CBirkbeck/mathlib-quality) | **MIT** | Claude Code plugin — 22 commands, the Lean side |
| [CBirkbeck/MQSlim](https://github.com/CBirkbeck/MQSlim) | **none stated** | Slim shadow of the same workflows |
| [CBirkbeck/TauCeti](https://github.com/CBirkbeck/TauCeti) | Apache-2.0 | `formalization.yaml` v0.2 schema; roadmap governance model |
| [CBirkbeck/TauCetiRoadmap](https://github.com/CBirkbeck/TauCetiRoadmap) | Apache-2.0 | Human-owned roadmaps |
| [CBirkbeck/LeanBridge](https://github.com/CBirkbeck/LeanBridge) | Apache-2.0 | LMFDB ↔ Lean. **Deferred** — pairs with `mathcity-lmfdb`, not this spike |
| [eth-sri/proof-council](https://github.com/eth-sri/proof-council) | MIT | ProofStack `ACWorkflow`. Reference only |

## The seam

`math-solve` `dag.json` schema v5 — one node per lemma. Required fields:

```
kind (lemma|definition) · title · statement · assumptions[] · conclusion
definitions[] · proof_md · parents[] · children[] · citations[]
status (pending|correct|wrong) · rounds
p_statement_false · p_argument_gap · last_author_model
```

Mapping onto the Lean side:

| DAG field | Consumer | Notes |
| --- | --- | --- |
| `statement`, `conclusion` | `/develop` Lean statement; `/blueprint` `:::theorem` prose | direct |
| `proof_md` | `/develop` numbered proof sketch; `:::proof` block | direct |
| `children[]` | `/blueprint` `{uses "label"}[]` dep-graph edges | direct |
| `citations[]` | `/develop`'s **verbatim source quote per leaf** (binding — it refuses to proceed without one) | direct |
| `status`, `p_argument_gap` | **NO CONSUMER** | The gap. `/develop` assumes a source that is right; `math-solve` ships calibrated per-node doubt |

**The `p_argument_gap` orphan is the most interesting finding to report on.** A
node at `p_argument_gap = 0.80` and one at `0.02` enter `/develop` identically.

## Skills and commands used

### Input side — `1stproof/math-solve-skill-FP` (consumed, not run)

`math-solve` SKILL.md (the Mastermind; owns `dag.json` / `state.json` /
`log.jsonl`) + subagents `math-dreamer`, `math-fetcher`, `math-solver`,
`math-checker`, `math-referee`, `math-patcher`; validators
`lib/validate_dag.py`, `lib/dag_helper.py`.

### Lean side — `CBirkbeck/mathlib-quality`

| Command | Used? | What it does |
| --- | --- | --- |
| `/develop` | **YES** | **The NL→Lean door.** Planning-only. Searches Mathlib, designs the API, writes the prose proof, decomposes into ordered lemmas, writes every lemma as a `:= by sorry` declaration that must `lake build` clean, tensions each leaf against sources with a verbatim quote + Lean↔source match paragraph, saves `decomposition.md` |
| `/blueprint` | **YES** | Verso blueprint: `:::theorem "label" (lean := "Foo.bar")`, `{uses}` edges, `:::proof` sketches; status auto-computed from Lean (no `\leanok` drift) |
| `/mathlibable` | **YES** | Five-bucket verdict on Mathlib fit, gated on exhaustive search. Our should-work/should-fail discriminator |
| `/unformalise` | **YES** | Lean → mathematics. Round-trip check: does the Lean still say what the NL proof said? |
| `/expert-review` | **YES** | Self-contained mathematical briefing, no Lean/paths — the report-out format |
| `/beastmode` | **Q1-dependent** | Marathon ticket execution. No depth/time cap; stops only on DONE / scope error / off-track / broken baseline |
| `/decompose-proof` | no | Lean→Lean helper splitting. **Not** the NL entry point (corrected 2026-08-18) |
| `/cleanup`, `/buzz`, `/pre-submit`, `/self-review`, `/taupr`, `/contribute`, `/teach`, `/generalise`, `/split-file`, … | no | Quality + PR machinery, out of scope |

### Already in this pack (reuse, don't rebuild)

`search-mathlib` (Loogle), `search-arxiv`, `search-stacks`, `search-scholar` —
see [proof-assist README](../../proof-assist/README.md). `/develop`'s Mathlib-search phase and
`/mathlibable`'s literature sweep should route through these.

## Run procedure

Everything lands in the session scratchpad. **No writes to `~/repos` (LP1 lane),
no city config changes, no `gc import` edits.**

```bash
# 1. workspace
mkdir -p "$SCRATCH/nl-formalization-spike" && cd "$SCRATCH/nl-formalization-spike"

# 2. inputs (CC-BY-SA-4.0)
gh api /repos/1stproof/batch-2/contents/batch-2-AI-solutions/problem-03/submission-A.tex \
  --jq '.content' | base64 -d > p03-submission-A.tex
gh api /repos/1stproof/batch-2/contents/batch-2-human-solution/problem-03/human-solution.tex \
  --jq '.content' | base64 -d > p03-human.tex
# ...repeat for problem-05

# 3. schema reference
gh api /repos/1stproof/math-solve-skill-FP/contents/skills/math-solve/dag-schema.json \
  --jq '.content' | base64 -d > dag-schema.json

# 4. Lean side — GATED ON Q2
git clone https://github.com/CBirkbeck/mathlib-quality
git clone https://github.com/CBirkbeck/TauCeti          # for formalization.yaml v0.2
```

Then, per problem: reconstruct a DAG from the prose → run `/develop` with that DAG
as the reference → `/blueprint` → `/mathlibable` on the leaves → `/unformalise`
round-trip → record what broke.

## Attribution

Carrier: **`formalization.yaml` v0.2** (TauCeti, Apache-2.0). Required fields —
`project.{name,authors,license}` and per source `title`, `authors`, `id`, `type`,
`license`, `author_contacted`, `prior_work`; plus `automation.{method,models,
framework,cost}`.

A First Proof proof becomes a `sources[]` entry: `type: blueprint`, `license:
CC-BY-SA-4.0`, `authors:` **the problem's human writers** (e.g. Milojević and
Sudakov for Problem 3), `id:` the batch-2 URL, and `prior_work:` naming both
First Proof and the harness that produced the submission. `author_contacted:` is
honest — `no` unless Taylor has actually contacted them.

Every adopted skill additionally carries upstream credit in its SKILL.md and in
the subdomain README, following the pattern already set for `search-arxiv`
(adopted from `blazickjp/arxiv-mcp-server`).

## Licensing (unresolved — blocks adoption, not the spike)

`gascity-packs` has **no LICENSE file**. `math-solve-*` is **AGPL-3.0**;
`mathlib-quality` is MIT; TauCeti is Apache-2.0; MQSlim states none. Vendoring
AGPL source into an unlicensed repo pushed to a public fork is cheaper to get
right now than to unwind. Likely resolution: submodule or symlink adoption rather
than copying — which also satisfies **P1.9** (one real copy anywhere).

## Documentation and tests

- **README (running, written during the spike):** `FORMALIZATION-TOOLCHAIN.md`,
  scratchpad first, then this `docs/` directory. Records what happened, not what
  was planned.
- **Subdomain README:** [proof-assist README](../../proof-assist/README.md) currently advertises
  `formalize-claim` and `proof-check` formulas that do not exist. Fix in the same
  change as any adoption; run the `update-README` skill (P1.8).
- **Tests:** `tests/<name>/red_test.sh` is the house shape. A DAG→Verso
  mapping is mechanical and testable; a red test asserting the four-field mapping
  should precede any adoption code.

## Gates

| Gate | Status |
| --- | --- |
| `check-plan-hygiene` **with Codex** | **REQUIRED before any adoption plan.** Not required for the spike — nothing enters the owned pack set. Standing rule: never run it solo |
| P1.8 / P1.9 (skill exposure, one real copy) | Not yet triggered; binds the moment anything lands in `mathcity/` |
| P1.2 (`city.toml` via packs, never hand-edits) | Applies to adoption |
| P1.10 (no private values in pack content) | Applies to adoption |
| `improve-README`, LaTeX hard gate | N/A — no Magma repo, no `notes.tex` |

## Tracking

Bead: **`mc-7h1`** (P1, open) — `bd show mc-7h1`. GitHub: [tdupu/mathcity#49](https://github.com/tdupu/mathcity/issues/49). Follow-ups to file if the
spike recommends adoption: subdomain scaffolding, licensing decision, README
repair, red test, `math-typo-oss` → `mathcity-latex`, LeanBridge → `mathcity-lmfdb`.

## Attribution for this plan

Describes third-party work by **Mohammed Abouzaid** and the First Proof
Foundation (1stproof.org), and by **Chris Birkbeck** (`mathlib-quality`,
TauCeti — the latter incubated with the Lean FRO and the Mathlib Initiative).
Neither has been contacted about this adoption. All repos are public; licenses
are recorded above and must travel with any adopted content.
