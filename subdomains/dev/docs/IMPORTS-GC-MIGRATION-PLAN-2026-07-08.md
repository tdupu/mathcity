# mathcity → imports.gc Migration Plan

**Bead:** gsp-eu2
**Date:** 2026-07-08
**Status:** DRAFT (investigation + planning; no pack edits made)
**Author:** outside-auditor planning agent

---

## 0. Executive summary & a required reconciliation

the human adjudicator's mission statement for this migration is: *"migrate from a standalone
parallel workflow engine to a GC-native domain pack that uses `[imports.gc]`;
no more polecats, no more refineries, no more gastown dependencies; build on
gascity instead"* — plus JJ's recommended agent split into five specialized
domain agents and the conversion of mechanical checks to check scripts.

There is a **standing independent verdict that partially disagrees** and must
be reconciled before execution. `METHODOLOGY-PACK-VERDICT-2026-07-08.md`
(now at `mathcity/METHODOLOGY-PACK-VERDICT-2026-07-08.md`) concludes:

- The pack is a **domain-automation pack**, not a build-methodology pack.
  Score 0/6 against the methodology-pack contract — *by design*.
- **Recommendation: keep it structurally as-is.** Do NOT extend `build-base`,
  do NOT emit `gc.build.*` schemas, do NOT add `[metadata.gc.methodology]`.
- `[imports.gc]` is endorsed **as a hygiene item** (Recommendation #3), because
  the formulas already call `gc bd`, `gc event emit`, `gc runtime drain-ack`,
  and `gc`-namespaced skills — but the pack currently declares no import.

`DRAINS-ANALYSIS-2026-07-08.md` reinforces this: of the six pipeline stages
(`produce → shuffle → present → decide → dispatch → archive`), **only
`produce` is a genuine fit for a GC drain**; the rest must stay
single-writer / human-interactive / deterministic-shell.

**How this plan reconciles the two.** This migration does everything the human adjudicator
asked *that does not contradict the verdict*, and flags the two places where
they collide as **Open Questions for the human adjudicator** (§10) rather than silently
picking a side:

1. **`[imports.gc]` — DO IT.** Both sources agree. (§2)
2. **Remove gastown deps (polecat/refinery/witness/deacon/`gastown.dog`/
   `gastown.mayor` run targets) — DO IT.** This is the heart of "no more
   gastown dependencies." Each has a gc-native replacement (§1). This is
   *orthogonal* to the methodology-pack question — it is pure decoupling.
3. **Split codex-worker into 5 specialized agents — DO IT.** (§3) Independent
   of methodology-vs-domain: the pack currently routes judgment work to
   `gastown.mayor` and utility work to `gastown.dog`; both must be replaced
   by pack-local agents anyway once gastown is removed.
4. **Convert mechanical checks to `[steps.check]` — MOSTLY ALREADY DONE.** The
   gate formulas already use `[steps.check]` with exec scripts. (§5)
5. **Restructure `orders/` into gc formulas** — the orders ARE already gc
   orders that pour formulas; the only change is the `pool =` target. Do NOT
   collapse them into a build-base lifecycle. (§4) **This is Open Question 1.**
6. **Drains** — adopt for `produce` only, if batch production is a real need.
   **This is Open Question 2.** (§4)

Everything below assumes the reconciled position: **GC-native + gastown-free,
but still a domain-automation pack, not a methodology pack.**

---

## 0.1 Live-tree caveat (read first)

At the time this plan was written the working tree of `<repos-root>/gascity-packs`
was **mid-mutation by another process**: the `mathematics/` directory had been
emptied (104 tracked files showing as deleted in `git status`) and a new
untracked `mathcity/` directory contained the relocated pack (the rename step
of this very migration). `HEAD` (commit `4ea722f`) still contains the full
`mathematics/` tree, so nothing is lost, but the on-disk canonical location is
now `mathcity/`. This plan file is therefore written into `mathcity/`, not
`mathematics/`. Confirm the rename is committed before executing any step here.

Related in-flight artifacts already on disk:
- `mathematics/BRIEF-DOCUMENT-MODEL-PLAN-2026-07-08.md` (bead gsp-1pv)
- `mathematics/DRAINS-ANALYSIS-2026-07-08.md`
- `mathcity/METHODOLOGY-PACK-VERDICT-2026-07-08.md`
- `mathcity/CODEX-REVIEW-RESPONSE-2026-07-08.md`
- Bead `gsp-2c0`: rename `gates` → `hurdles` (plan at
  `HURDLES-RENAME-PLAN-2026-07-08.md`). This migration and gsp-2c0 touch the
  same files; sequence them (see §8).

---

## 1. Gastown dependencies found, and their gc-native replacements

### 1.1 What was found

Surveyed with:
`grep -rn "gastown\.|polecat|refinery|witness|deacon|patrol|wisp|drain|convoy"`
over `mathcity/{formulas,orders,gates}` plus the pack README/skills.

There are **two distinct classes** of gastown coupling:

**A. Run-target coupling (hard dependency — MUST change).** Every formula
routes work to one of two gastown pack agents:

| Gastown run target | Meaning | Used in |
|---|---|---|
| `gastown.dog` | deterministic utility/recovery operator | `brief-shuffle`, `brief-prep` (`prep_target`), `brief-review-patrol`, `brief-gate-keep`, `on-merge-brief-record`, `file-or-sendback-route`, `brief-record-decision`, `brief-watchdog-refill`, `test-execution-request`, `decision-enforce`, `latex-gate` (`operator_target`); orders `pool = "gastown.dog"` in all 10 orders |
| `gastown.mayor` | judgment/coordination role | `brief-prep` (`review_target`), `brief-present-next`, `brief-gate-keep`, `file-or-sendback-route`, `test-execution-request`, `decision-enforce`, `no-brainer-classify`, `upf-experiment-dispatch`, `latex-gate` (`review_target`) |

Plus `codex:codex-worker` (the pack's own codex pool) in `codex-dispatch`.

**B. Role/concept coupling (prose + one live reassignment — MUST change).**

| Gastown concept | Where | Nature |
|---|---|---|
| **refinery** | `brief-decision-dispatch.toml:289-291` runs `gc bd update <src> --assignee "$rig_name/gastown.refinery"` on approve; `decision-enforce.toml:121` requires approve→assign to `<rig>/gastown.refinery`; prose in `brief-record-decision`, `file-or-sendback-route`, `on-merge-brief-record` | **LIVE dependency** — dispatch physically reassigns approved work to the gastown refinery role for merge. |
| **polecat** | `brief-decision-dispatch.toml` (existing `branch` metadata from a polecat), `brief-review-patrol.toml` (brief-prep polecats), `latex-gate.toml` (branch stays on `polecat/` namespace), `file-or-sendback-route.toml` (route mol to polecat pool), README/skill prose | Mostly the dispatch *worker* role + the `polecat/<bead>` branch-namespace convention. |
| **witness / deacon / patrol / wisp** | patrol orders (`brief-review-patrol`, `brief-archive-sweep`), `drain-ack`, phase=vapor prose | Gastown's rig-scoped maintenance roles + the wisp/drain-ack runtime idioms. |

### 1.2 Replacement mapping

| Gastown thing | gc-native replacement | Notes |
|---|---|---|
| `gastown.dog` run target | **`gc.run-operator`** | gascity ships `gascity/agents/run-operator/` = "Run operator for deterministic setup, validation, gates, metadata, and finalization." This is the exact gc-native equivalent of the dog for deterministic/bookkeeping steps. Every `gastown.dog` becomes `gc.run-operator`. |
| `gastown.mayor` run target | **A pack-local specialized agent** (see §3), NOT a single generic replacement | The mayor is doing three different jobs across the formulas: (a) judgment review of a brief, (b) presenting to the human, (c) classifying no-brainers. These fan out to `mathcity.critical-reviewer`, `mathcity.review-synthesizer`, and `mathcity.brief-preparer` respectively. The one job that is *genuinely a human hand-off* (present + adjudicate) stays a human-interactive step; the agent only prepares it. |
| `codex:codex-worker` (generic) | The **five specialized agents** in §3 | The codex provider stays (`[providers.codex]`), but the single generic worker is replaced by role-specific agents. `codex-dispatch.toml` can remain as an explicit cross-model escape hatch (see §3.6). |
| **refinery** (approve→merge assignee) | **A pack-owned merge lane** — a `mathcity.decision-recorder`-emitted follow-up bead routed to a gc convoy/formula, OR keep assigning to a rig-local merge agent the *city* declares (not the gastown refinery) | This is the one **real behavioral dependency**. The pack must stop assigning to `gastown.refinery`. Cleanest gc-native form: on approve, `brief-decision-dispatch` reassigns to a city-declared merge target (e.g. a `mergers-and-acquisitions` formula — note existing epic **gsp-7lc** designs exactly a "brief-gated merge" M&A formula; this migration should route approve→M&A instead of approve→refinery). **Open Question 3.** |
| **polecat** (dispatch worker + branch namespace) | gc-native: work poured to `gc.run-operator` or a pack agent; branch namespace `polecat/<bead>` → a neutral namespace (`brief/<bead>` or `mathcity/<bead>`) | The `polecat/` branch prefix is baked into `latex-gate` and dispatch prose. Renaming the namespace is cosmetic but should be decided (Open Question 4). |
| **witness / deacon patrol orders** | gc **condition/cooldown orders** poured to `gc.run-operator` | The patrols (`brief-review-patrol`, `brief-archive-sweep`) are already ordinary gc orders; they just need `pool = gc.run-operator` and the prose de-gastowned. No witness/deacon agent is required — the order trigger *is* the patrol. |
| `gc runtime drain-ack` / phase=vapor / wisp | **Keep** — these are gc-core runtime primitives, not gastown | `drain-ack` is `gc runtime`, not gastown. The DRAINS-ANALYSIS confirms drains are a gc-core feature. No change needed except confirming they resolve under `[imports.gc]`. |

**Bottom line:** the gastown coupling is overwhelmingly the two run-target
strings (`gastown.dog`, `gastown.mayor`) plus **one** live behavioral edge
(approve → `gastown.refinery`). Removing the run-target strings is mechanical;
the refinery edge needs a design decision (route to M&A formula per gsp-7lc).

---

## 2. pack.toml changes (minimal)

Current `mathcity/pack.toml`:

```toml
[pack]
name = "mathcity"
version = "0.2.0"
schema = 2
description = "..."

[providers.codex]
base = "builtin:codex"
```

Target:

```toml
[pack]
name = "mathcity"
version = "0.3.0"
schema = 2
description = "..."

[imports.gc]
source = "../gascity"

# Declare pack kind so reviewers stop applying the methodology rubric
# (METHODOLOGY-PACK-VERDICT Recommendation #1). Use whatever key the
# platform blesses; proposed:
[metadata.gc.pack]
kind = "domain-automation"

[providers.codex]
base = "builtin:codex"
```

- `[imports.gc] source = "../gascity"` — identical to `bmad/pack.toml` and
  `gstack/pack.toml`. This makes `gc.run-operator`, `gc.review-synthesizer`,
  and the gc runtime primitives resolvable, and lets pack formulas reference
  `gc.*` run targets.
- `[metadata.gc.pack] kind = "domain-automation"` — from the verdict. **Verify
  the platform recognizes this key** before shipping (Open Question 5); if not
  yet blessed, ship `[imports.gc]` alone and file the taxonomy bead.
- Keep `[providers.codex]` — the codex agents still need it.
- Do **NOT** add `[metadata.gc.methodology]` or any `build-base` extension.

---

## 3. Agent split: codex-worker → 5 specialized agents

Current: one `mathcity/agents/codex-worker/` (agent.toml + prompt.template.md),
a generic "claim a step, do whatever the bead says, close it" worker with
`provider = "codex"`, `fallback = true`, `permission_mode = "suggest"`.

Model after `bmad/agents/*` and `gstack/agents/*`: each agent is a directory
`agents/<name>/{agent.toml, prompt.template.md[, template-fragments/]}`, and
formulas target it via `metadata = { "gc.run_target" = "mathcity.<name>" }`.
Agent `agent.toml` carries `description`, `scope`, `fallback`, provider, and
option defaults; the run-target name is `<pack>.<agent-dir-name>`.

### 3.1 `mathcity.brief-preparer`
- **Does:** the producer side — turns a source artifact into a staged, gated
  brief; drafts the brief with the Decision-at-Top invariant; classifies
  no-brainers (absorbs the `no-brainer-classify` judgment currently sent to
  `gastown.mayor`); selects full vs compact form.
- **Replaces:** `gastown.mayor` in `brief-prep` (`review_target`, draft-brief +
  coordinate-review steps) and `no-brainer-classify`; the drafting half of the
  generic codex-worker.
- **Prompt assets:** `prompt.template.md` composing the existing pack skills
  `mathcity.brief-prep`, `mathcity.catch-no-brainer`, `mathcity.create-brief`,
  `mathcity.present-it` (form selection). Reuse the fixtures under
  `skills/catch-no-brainer/fixtures/`.
- **Run target:** `mathcity.brief-preparer`.

### 3.2 `mathcity.critical-reviewer`
- **Does:** adversarial judgment review of a brief/artifact — the G2/G4/G6/G9
  judgment gates; runs `critical-review`, produces APPROVING / NEEDS-REVISION
  verdicts written into the brief's Gate Evidence.
- **Replaces:** the judgment portion of `gastown.mayor` in `brief-prep`
  (coordinate-review step), `brief-gate-keep`, `decision-enforce`.
- **Prompt assets:** composes `mathcity.critical-review`,
  `mathcity.coordinate-review`, `mathcity.compare-artifacts`.
- **Run target:** `mathcity.critical-reviewer`.

### 3.3 `mathcity.experiment-reviewer`
- **Does:** experiment- and test-execution-specific judgment — the
  `is-good-experiment` / `is-good-test` gates, test-evidence adequacy, the
  `upf-experiment-dispatch` and `test-execution-request` judgment steps.
- **Replaces:** `gastown.mayor` in `upf-experiment-dispatch` and
  `test-execution-request`.
- **Prompt assets:** composes `mathcity.is-good-experiment`,
  `mathcity.is-good-test`; references `gates/test-evidence.toml`,
  `gates/test-execution.toml`.
- **Run target:** `mathcity.experiment-reviewer`.

### 3.4 `mathcity.decision-recorder`
- **Does:** records the human adjudicator's adjudication as a canonical `bd decision`, writes
  the decision `.toml`, emits `brief.decided`, and stamps
  `mathcity.brief.decision_*` bead metadata. Deterministic — no judgment.
- **Replaces:** the bookkeeping half of `gastown.dog` in `brief-record-decision`
  and the decision-emission in `decision-enforce`.
- **Prompt assets:** composes `mathcity.record-decision`; references the brief
  front-matter model from BRIEF-DOCUMENT-MODEL-PLAN (gsp-1pv).
- **Run target:** `mathcity.decision-recorder`.
- **Note:** could alternatively be a `gc.run-operator` step since it is purely
  deterministic. Made a named agent per JJ's list; if the human adjudicator prefers, fold into
  `gc.run-operator` (Open Question 6).

### 3.5 `mathcity.review-synthesizer`
- **Does:** rolls up multi-reviewer output into a single presentation for the
  human (the "present" stage prep), and synthesizes patrol/sweep findings.
  Mirrors `bmad.bmad-review-synthesizer` / `gstack.review-synthesizer` /
  `gascity.review-synthesizer`.
- **Replaces:** `gastown.mayor` in `brief-present-next` (the *preparation* of
  the presentation; the actual human adjudication stays a human step).
- **Prompt assets:** composes `mathcity.grill-and-present`, `mathcity.present-it`;
  can extend `gascity.review-synthesizer` via `[imports.gc]`.
- **Run target:** `mathcity.review-synthesizer`.

### 3.6 What happens to codex-worker / codex-dispatch
- Delete the generic `agents/codex-worker/`; its two jobs (draft, bookkeep)
  are absorbed by the five agents above + `gc.run-operator`.
- **Keep `codex-dispatch.toml`** as the explicit cross-model escape hatch (it
  is "never fired by an automated order; pour explicitly for cross-model
  review"). Repoint its `codex_target` default from `codex:codex-worker` to a
  retained minimal codex pool, or to one of the five agents with
  `provider = codex`. Decision: keep a thin codex pool vs. give each of the 5
  agents a codex fallback (Open Question 7).

### 3.7 Deterministic steps → `gc.run-operator` (no named agent needed)
All remaining `gastown.dog` steps that are pure bookkeeping (staging init,
pile/stack moves, manifest/index writes, archive sweeps, patrol-state records,
dispatch reassignment) become `gc.run_target = "gc.run-operator"`. No new agent.

---

## 4. Formula restructuring

**Guiding principle (from the verdict + drains analysis): do NOT convert the
order-driven brief pipeline into a build-base methodology.** Keep the formulas
as domain-automation formulas. The restructuring here is (a) run-target
substitution, (b) de-gastowning prose, (c) one optional new `produce` drain.

### 4.1 Orders (10) — pool substitution only
Each `orders/*.toml` currently has `pool = "gastown.dog"`. Change to
`pool = "gc.run-operator"`. Triggers/scopes/conditions are already correct gc
orders. (The BRIEF-DOCUMENT-MODEL plan separately proposes `scope rig→city`
after the artifact_root moves to `~/.gc/mathcity/briefs`; sequence that with §6.)

| Order | Trigger | Formula poured | Change |
|---|---|---|---|
| brief-shuffle-pile | condition | brief-shuffle | pool→gc.run-operator |
| brief-decision-dispatch | event `brief.decided` | brief-decision-dispatch | pool→gc.run-operator; **refinery edge** (§1.2) |
| brief-review-patrol | cooldown/condition | brief-review-patrol | pool→gc.run-operator; de-polecat prose |
| brief-archive-sweep | cooldown | brief-archive-sweep | pool→gc.run-operator |
| brief-watchdog-refill | condition | brief-watchdog-refill | pool→gc.run-operator |
| brief-present-next | manual | brief-present-next | pool→gc.run-operator (prep); present stays human |
| brief-archive-on-request | manual | brief-archive-sweep | pool→gc.run-operator |
| no-brainer-process | ? | no-brainer-classify | pool→gc.run-operator |
| on-merge-brief-record | event | on-merge-brief-record | pool→gc.run-operator; de-refinery prose |
| post-decision-file-or-sendback | event | file-or-sendback-route | pool→gc.run-operator; de-polecat prose |

### 4.2 Formulas (16/17) — run-target substitution + de-gastown
For each formula, edit the `[vars]` defaults:
- `prep_target = "gastown.dog"` → `gc.run-operator`
- `review_target = "gastown.mayor"` → the specialized agent from §3
  (per-formula: brief-prep→brief-preparer+critical-reviewer;
  brief-present-next→review-synthesizer; test/experiment→experiment-reviewer;
  gate-keep/decision-enforce→critical-reviewer;
  record-decision→decision-recorder; no-brainer-classify→brief-preparer).
- `operator_target = "gastown.dog"` (latex-gate) → `gc.run-operator`.
- Remove the `gc bd update --assignee ".../gastown.refinery"` line in
  `brief-decision-dispatch` and `decision-enforce`; replace with the M&A /
  merge-lane routing (§1.2, Open Question 3).

Existing `[steps.check]` blocks stay (see §5). Existing `gc runtime drain-ack`,
phase=vapor, event emit stay (gc-core, not gastown).

### 4.3 Brief-pipeline stages as gc formula steps
The six stages `produce → shuffle → present → decide → dispatch → archive`
stay as **separate order-triggered formulas**, NOT collapsed into one
lifecycle formula (the verdict is explicit that build-base's
prepare→…→publish anchor does not fit). The stage↔formula map is already
correct; this migration only changes *who runs each step*, not the topology.

### 4.4 Drains — adopt for `produce` only, gated on a real need
Per DRAINS-ANALYSIS: the only stage that benefits from a GC drain is
**produce** (batch N briefs in parallel from a convoy of pending source beads),
and only if inflow regularly outpaces manual pours. If the human adjudicator wants it:
- Add a `collect-source-beads` step that writes a convoy (e.g. beads labeled
  `needs-decision` not yet briefed).
- Add a `[steps.drain]` with `context = "separate"`, `formula = "brief-prep"`
  (or a `brief-prep-item` variant), running `mathcity.brief-preparer` per member.
- Add a post-drain `shuffle` step; protect the single-writer `.shuffle.lock`
  from concurrent produce+shuffle (drain `member_access = "exclusive"` or rely
  on the lock — DRAINS-ANALYSIS Decision 4).
- shuffle/present/decide/dispatch/archive stay **non-drain** (single-writer /
  human / deterministic). This is **Open Question 2** — do not build the drain
  unless batch production is a confirmed need.

---

## 5. Check scripts: hurdle checks → `[steps.check]` (mostly already done)

The mechanical "hurdle" (formerly "gate") checks are **already** exec
`[steps.check]` blocks calling scripts under
`mathcity/assets/scripts/checks/`. No conversion from a different mechanism is
needed — this part of the mission is largely complete. What remains:

| Formula / gate | `[steps.check]` script (existing) | Migration action |
|---|---|---|
| `gates/test-evidence.toml` (G1) | `checks/gate-test-evidence.sh` | keep; de-hardcode path (§7); rename gate→hurdle per gsp-2c0 |
| `gates/test-execution.toml` (G14) | `checks/gate-test-execution-*.sh` | keep; de-hardcode path |
| `gates/stale-claim.toml` | `checks/stale-claim-check.sh` | keep; de-hardcode path |
| `gates/latex-gate.toml` (G6) | `checks/latex-gate-approval-required.sh` | keep; de-hardcode; repoint operator/review targets |
| `gates/server-touching-safety-override.toml` | `checks/brief-server-touching-safety.sh` | keep |
| `brief-prep` attach-test-evidence | `checks/brief-test-evidence-required.sh` | keep; de-hardcode path |
| `brief-prep` submit-to-pile | `checks/brief-pile-entry-required.sh` | keep; de-hardcode path |
| `brief-review-patrol` record | `checks/brief-review-patrol-record-required.sh` | keep |
| `brief-present-next` drain | `checks/../brief-drain-manifest.sh` | replace w/ `bd list --meta` query per BRIEF-DOCUMENT-MODEL §"Replacing manifest.jsonl" |
| decision-enforce / decision-record | `checks/decision-alignment-check.sh`, `checks/decision-record-exists.sh` | keep; de-hardcode path |

The three JJ-named mechanical checks map to existing scripts:
- **LaTeX compiles** → `check-latex` skill + `latex-gate-approval-required.sh`
  (already a `[steps.check]` in `gates/latex-gate.toml`).
- **required-evidence** → `gate-test-evidence.sh` / `brief-test-evidence-required.sh`.
- **stale-claim detection** → `stale-claim-check.sh` (already `[steps.check]`).

So §5's real work is: **(a) rename gate→hurdle (gsp-2c0), (b) de-hardcode the
27 `<home>` absolute paths (§7).** The `[steps.check]` conversion itself
is essentially done.

---

## 6. Brief document model (cross-reference gsp-1pv)

Handled by **BRIEF-DOCUMENT-MODEL-PLAN-2026-07-08.md** (bead gsp-1pv). Summary
of what it decides, and how it interacts with THIS migration:

- Move brief storage `.beads/briefs/` → `~/.gc/mathcity/briefs/` (rig-local,
  out of git, out of `bd` data). Add YAML front matter (`schema: mathcity.brief/1`,
  `status`, `trace`). Index via bead metadata keys `mathcity.brief.*` instead of
  `stack/manifest.jsonl`. Keep the `.shuffle.lock` (moved), move the
  `ALLOW_NO_BRAINER_AUTO_EXECUTE` kill-switch.
- **Interaction with imports.gc migration:** the `~/.gc/mathcity/briefs`
  artifact_root is the natural GC-native operational-state location and pairs
  well with `[imports.gc]`. The `bd list --meta mathcity.brief.stage=stack`
  index replaces `brief-drain-manifest.sh` (§5). The `scope rig→city` order
  change (§4.1) depends on the absolute artifact_root landing first.
- **Sequencing:** do the document-model move (gsp-1pv) either just before or
  bundled with this migration's order/formula edits so paths change once, not
  twice. This plan does NOT re-decide the storage location — gsp-1pv owns it.

---

## 7. Absolute-path issue (cross-reference)

There were **27 files under `mathcity/` with hard-coded `<home>/` paths**
(check-script paths in `[steps.check].path`, the escalate.sh reference in the
codex-worker prompt, evidence-dir defaults in latex-gate). These have been
replaced with `~/`, `$HOME/`, or repo-relative paths (bead gsp-n9u).

This migration MUST NOT hard-code new absolute paths, and should de-hardcode
existing ones as it touches each file (use `{{env.HOME}}`, pack-relative
resolution, or `.gc/scripts/checks/...` like the bmad/gstack materialized
pattern `path = ".gc/scripts/checks/implementation-review-approved.sh"`).

No dedicated absolute-path bead exists yet — **file one** (child of gsp-eu2 or
standalone) so the de-hardcoding is tracked separately and can be done in one
mechanical sweep rather than piecemeal. This is **Open Question 8**.

Note: the bmad/gstack convention resolves check scripts at `.gc/scripts/checks/`
(materialized location), NOT via an absolute source path. Adopting that
convention is the clean fix and is enabled by `[imports.gc]`.

---

## 8. Migration sequencing (keep the pack functional at each step)

Each step should leave the pack lint-clean and test-passing before the next.

1. **Land the rename** `mathematics/` → `mathcity/` (already in flight on disk —
   commit it first; this plan assumes it as the baseline). Verify HEAD contains
   `mathcity/` and `mathematics/` is gone.
2. **gsp-2c0: gate → hurdle rename.** Do this BEFORE the run-target edits so
   the `[steps.check]` / metadata churn happens once. (Directory `gates/`→
   `hurdles/`, `gc.gate.*`→`gc.hurdle.*`, `gate_profile`→`hurdle_profile`.)
3. **pack.toml: add `[imports.gc]`** (+ `[metadata.gc.pack] kind` if blessed).
   Lint. This alone changes no behavior but makes `gc.*` targets resolvable.
4. **Run-target substitution — deterministic first.** Replace every
   `gastown.dog` / `operator_target` with `gc.run-operator` across formulas +
   `pool =` in orders. Lint + smoke-test one order (brief-shuffle-pile). The
   pack is still functional because `gc.run-operator` now resolves.
5. **Create the 5 agents** (`agents/{brief-preparer,critical-reviewer,
   experiment-reviewer,decision-recorder,review-synthesizer}/`). They can exist
   before any formula references them.
6. **Run-target substitution — judgment.** Replace `gastown.mayor` /
   `review_target` with the mapped specialized agent per §4.2. Lint + smoke.
7. **De-gastown the refinery edge** (Open Question 3). Until resolved, keep the
   approve→assignee behavior but point it at a city-declared merge target, NOT
   `gastown.refinery`. This is the only step that can change *behavior*; gate it
   on the human adjudicator's answer.
8. **Delete `agents/codex-worker/`; retain/adjust `codex-dispatch`.**
9. **De-hardcode absolute paths** (§7, its own bead) — sweep `<home>`.
10. **(Optional) Document-model move (gsp-1pv)** and the `scope rig→city`
    order change, if bundling here rather than separately.
11. **(Optional) produce-drain** (§4.4), only if batch production is confirmed.
12. Final: `gc lint mathcity/` + `pytest`; smoke-test one full brief cycle.

Steps 3–6 and 8–9 are pure decoupling with no behavior change — safe to land
incrementally. Step 7 and 11 need human decisions.

---

## 9. What to KEEP unchanged

- **All domain logic and the brief format** — the 7-section / compact brief
  shape, Decision-at-Top invariant, the `mathcity.brief-prep` /
  `catch-no-brainer` / `create-brief` skills.
- **The hurdle checks themselves** (G1–G16 registry semantics, fail-closed
  profiles, the check-script logic). Only their *names* (gate→hurdle) and
  *paths* (de-hardcode) change, not their behavior.
- **The order + gate + event substrate** — condition/event/cooldown/manual
  triggers, idempotent ledger-driven handlers, single-writer shuffle lock,
  phase=vapor, `gc runtime drain-ack`. The verdict is explicit this is the
  correct primitive-level alignment for a domain-automation pack.
- **The six-stage pipeline topology** — do NOT collapse into a build-base
  lifecycle.
- **`[providers.codex]`** and the `codex-dispatch` cross-model escape hatch.
- **The gate registry `assets/brief-pipeline/gates.toml`** (renamed per gsp-2c0).

---

## 10. Open questions for the human adjudicator

1. **Methodology vs domain-automation (the core tension).** The mission says
   "gc-style formulas/drains/agents"; the independent verdict says "keep it a
   domain-automation pack, do NOT extend build-base." This plan follows the
   verdict (imports.gc + gastown removal + specialized agents, but NO build-base
   conversion). **Confirm this is the intended scope**, or state that you DO
   want a build-base methodology (which the verdict argues against).

2. **Batch brief production drain?** Only `produce` benefits from a GC drain,
   and only if inflow outpaces manual pours. Build the produce-drain (§4.4) or
   leave production on-demand?

3. **Refinery replacement (the one live behavioral edge).** On approve,
   `brief-decision-dispatch` currently reassigns to `gastown.refinery` for
   merge. Replace with: (a) the M&A "brief-gated merge" formula from epic
   **gsp-7lc**, (b) a city-declared rig-local merge agent, or (c) just emit a
   follow-up merge bead and stop auto-assigning? This is the only change that
   alters behavior.

4. **Branch namespace.** `polecat/<bead>` is baked into latex-gate + dispatch.
   Rename to `brief/<bead>` / `mathcity/<bead>`, or keep the string as an
   inert convention?

5. **`[metadata.gc.pack] kind = "domain-automation"`** — is this key blessed by
   the platform yet? If not, ship `[imports.gc]` alone and file the taxonomy
   doc bead (verdict Recommendation #2).

6. **decision-recorder: named agent or fold into `gc.run-operator`?** It is
   purely deterministic. JJ lists it as a named agent; a `gc.run-operator` step
   would be simpler.

7. **codex pool shape.** Keep a thin `codex:codex-worker` pool for
   `codex-dispatch`, or give each specialized agent a codex fallback and drop
   the standalone pool?

8. **Absolute-path de-hardcoding.** 27 files carry `<home>` paths, and
   there is no bead tracking this. File a dedicated bead and adopt the
   bmad/gstack `.gc/scripts/checks/` materialized-path convention?

---

### Files/beads consulted
- `mathcity/pack.toml`, `bmad/pack.toml`, `gstack/pack.toml`
- `bmad/formulas/bmad-review.formula.toml`, `bmad-story-development.formula.toml`
- `gascity/agents/run-operator/agent.toml`, `gascity/formulas/implement.formula.toml`
- `gastown/pack.toml` + `gastown/agents/{dog,mayor,refinery,polecat,witness,deacon}`
- `mathcity/agents/codex-worker/{agent.toml,prompt.template.md}`
- `mathcity/formulas/*` (brief-prep, codex-dispatch, brief-shuffle, latex-gate, …)
- `mathcity/orders/*` (all 10)
- `mathcity/gates/{test-evidence,latex-gate,...}.toml`
- `mathcity/METHODOLOGY-PACK-VERDICT-2026-07-08.md`
- `mathematics/DRAINS-ANALYSIS-2026-07-08.md`
- `mathematics/BRIEF-DOCUMENT-MODEL-PLAN-2026-07-08.md` (gsp-1pv)
- Beads: gsp-eu2 (this), gsp-1pv (doc model), gsp-2c0 (hurdles rename),
  gsp-7lc (M&A merge formula epic), gsp-k6w (pack health check)
