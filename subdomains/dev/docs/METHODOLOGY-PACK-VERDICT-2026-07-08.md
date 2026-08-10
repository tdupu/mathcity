# Is the mathematics pack a methodology pack? — Verdict (2026-07-08)

*Independent outside-agent review. Files read listed at bottom.*

---

## TL;DR

**No — and it should not be.** The mathematics pack is a **domain-automation pack**,
not a build-methodology pack. It shares *zero* of the six structural markers that
define a methodology pack. The codex reviewer's observation — "not just slightly
off, a different mental model" — is **correct and is a feature, not a bug.** These
are two different pack *kinds* that happen to live in the same monorepo. The pack
should stay as-is structurally; the only real defect is that nothing *declares*
its kind, so reviewers keep measuring it against the wrong ruler.

---

## 1. What the mathematics pack actually is

Read against its own files, the pack implements a **brief pipeline** — a decision-
routing automation for math-research work. Its own README says so in the first
line: *"Codifies the brief pipeline… that routes math research decisions
(branches, PRs, experiments) from artifact to adjudication."*

The actual workflow it implements is **not** prepare→plan→implement→review. It is:

```
produce → shuffle → present → decide → dispatch → archive
```

- **produce**: `brief-prep` turns a source artifact (bead/branch/PR/diff) into a
  gated brief in `.beads/briefs/.pile/`.
- **shuffle**: `brief-shuffle` is a single-writer that promotes one pile item at a
  time into `stack/` (or rejects it), guarded by a `.shuffle.lock`.
- **present**: `brief-present-next` drains the stack and renders briefs to the
  human for adjudication.
- **decide**: the human approves/rejects/defers/revises; `brief-record-decision`
  writes a `bd decision` record and emits a `brief.decided` event.
- **dispatch**: `brief-decision-dispatch` (event-triggered on `brief.decided`)
  *acts* — reassigns the source bead to the refinery on approve, creates a
  follow-up bead on reject/revise, no-ops on defer. Sibling
  `file-or-sendback-route` routes the brief itself to re-brief or archive.
- **archive**: `brief-archive-sweep` cleans up.

The primitives it is built from are the **order system** (event / condition /
cooldown / manual triggers, `scope = city|rig`, `pool = gastown.dog`) and a
**gate registry** (`assets/brief-pipeline/gates.toml`, 16 gates G1–G16 with
fail-closed profiles). Its formulas are ledger-driven idempotent event handlers,
not lifecycle stages. `brief-decision-dispatch` is a ~300-line embedded bash
reconciler with retry/terminalization semantics — that is the shape of a
**daemon/automation pack**, not a build-methodology pack.

**Problem it solves:** getting research decisions in front of the human adjudicator with evidence
attached, and mechanically executing the routing once the human adjudicator decides. It is brief
routing + gate enforcement, full stop. It is not a software-build workflow.

## 2. What a methodology pack requires (from build-base + reference packs)

A build-methodology pack (per `gascity/formulas/build-base.formula.toml` and the
`superpowers` reference implementation) must:

1. **Import gascity as `gc`** — `superpowers/pack.toml` has `[imports.gc] source = "../gascity"`.
2. **Ship a top-level formula that `extends = ["build-base"]`** — `superpowers-build.formula.toml` line 10.
3. **Preserve the anchor sequence** prepare → requirements → plan → plan-review →
   decompose → implement → (summarize) → review → finalize → publish, overriding
   individual steps by `id`.
4. **Ship a formula trio** — planning / decomposition / implementation families
   (superpowers ships `superpowers-planning`, `-decomposition`, `-implementation`,
   `-review`, `-fix-loop`, `-development`…).
5. **Produce the build artifact schema IDs** — `gc.build.requirements.v1`,
   `gc.build.plan.v1`, `gc.build.decomposition.v1`, `gc.build.review.v1`,
   `gc.build.final-report.v1`, wired via `gc.build.artifact_schema` metadata.
6. **Declare methodology metadata** — `[metadata.gc.methodology]` with
   `allowed_drain_policies`, `implementation_strategy`, `interaction_modes`,
   `review_modes`.

## 3. Gap analysis (per criterion)

| # | Methodology-pack requirement | mathematics pack | Result |
|---|------------------------------|------------------|--------|
| 1 | Imports gascity as `gc` | `pack.toml` has **no `[imports]` block at all** — only a `[providers.codex]` block | **NO** |
| 2 | Top-level formula `extends = ["build-base"]` | `grep "extends"` across `formulas/` → **zero hits** | **NO** |
| 3 | Preserves prepare→…→publish anchor sequence | No formula contains those step ids; steps are `initialize-staging`, `draft-brief`, `scan-and-dispatch`, `acquire-lock`, etc. | **NO** |
| 4 | Planning/decomposition/implementation formula trio | None. Formulas are brief-pipeline handlers (prep, shuffle, dispatch, present, record, archive) | **NO** |
| 5 | Emits `gc.build.*` artifact schema IDs | **zero** `gc.build.*` or `artifact_schema` references. Uses its own `gc.brief.*` metadata namespace instead | **NO** |
| 6 | `[metadata.gc.methodology]` block | **absent** — no `interaction_modes` / `review_modes` / `drain_policies` anywhere | **NO** |

**Score: 0 of 6.** This is not a near-miss or a partial implementation. The pack
does not gesture at the methodology contract anywhere. It uses a parallel,
self-consistent namespace (`gc.brief.*`, the order system, the gate registry).

## 4. Verdict

**Methodology pack: NO (not partial — categorically not).**

The pack meets none of the six build-base markers and instead implements a
complete, internally coherent brief-routing pipeline on the order + gate + event
primitives. The "different mental model" the codex reviewer flagged is real: a
methodology pack *extends a lifecycle contract*, whereas this pack *is an
event-driven automation service* — different substrate, different namespace,
different unit of work (a brief, not a build).

## 5. Recommendation

**Keep it as-is structurally; do NOT convert it into a methodology pack.** Forcing
brief-routing through build-base would be a category error — there is no
requirements→plan→implement lifecycle here to model, and wrapping one around a
present-and-dispatch loop would add ceremony with no payoff. The convergence with
Gas City conventions is already correct at the primitive level: it uses real
orders, real triggers/scopes/pools, `gc bd` idioms, `bd decision` records, and a
fail-closed gate registry. That is the right kind of alignment for this kind of
pack.

The genuine gap is **taxonomic, not structural**: Gas City has a crisp, enforced
definition of "methodology pack" (build-base) but **no first-class concept for a
"domain-automation pack"** — a pack that ships its own order-driven workflow
family instead of extending a lifecycle contract. Because that category is
unnamed, every reviewer instinctively benchmarks the math pack against build-base
and reports it as "off." It isn't off; it's uncategorized.

Concrete, low-cost fixes (in priority order):

1. **Declare the pack's kind.** Add a `[metadata]` marker to
   `mathematics/pack.toml` — e.g. `[metadata.gc.pack] kind = "domain-automation"`
   (or whatever the platform blesses) — so tooling and reviewers stop applying the
   methodology rubric. One line settles the recurring "is this a methodology pack"
   question permanently.
2. **Name the category in the gascity docs.** Define "domain-automation pack"
   alongside "build-methodology pack": a pack that ships orders + formulas +
   gates implementing its own workflow, imports gascity primitives but does **not**
   extend build-base, and owns a distinct metadata namespace (here `gc.brief.*`).
   State the constraints that DO apply to such packs — idempotent order handlers,
   fail-closed gates, `gc bd` for state, single-writer discipline where it mutates
   shared stacks — all of which this pack already satisfies.
3. **Fix the one real convention drift, if any:** `pack.toml` does not import
   gascity even though its formulas call `gc`-namespaced skills
   (`mathcity.brief-prep`, `mathcity.coordinate-review`) and `gc bd`. If the
   platform expects an explicit `[imports.gc]` for any pack that references gascity
   primitives, add it. This is a hygiene item, not a methodology conversion.

Do **not** add build-base steps, `gc.build.*` schemas, or a
`[metadata.gc.methodology]` block. Those would misrepresent what the pack does.

---

### Files read for this verdict
- `<mathcity-pack-root>/pack.toml`
- `<mathcity-pack-root>/README.md`
- `<mathcity-pack-root>/formulas/` (brief-prep, brief-decision-dispatch, brief-shuffle; full listing of 17 formulas)
- `<mathcity-pack-root>/orders/` (all 10; triggers/scopes surveyed)
- `<mathcity-pack-root>/gates/` (5) + `assets/brief-pipeline/gates.toml` (G1–G16 registry)
- `<gascity-pack-root>/pack.toml`
- `<gascity-pack-root>/formulas/build-base.formula.toml`
- `<repos-root>/gascity-packs/superpowers/pack.toml`
- `<repos-root>/gascity-packs/superpowers/formulas/superpowers-build.formula.toml`
