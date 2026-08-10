# Briefs Pack Dogfood Plan

Author: outside planning agent (for the human adjudicator) · Date: 2026-07-11
Status: LIVING DOCUMENT — T4 confirmed 2026-07-16 (gsp-7x9f); D2 path proven; this plan updated to reflect settled mechanism status.

## Executive Summary

The brief-system pack (`mathcity/subdomains/brief-system` + `mathcity/assets/brief-pipeline` + 16 formulas/orders + 5 skills) is structurally complete but has never processed its **own** development work: all live traffic runs in the hecke rig against math artifacts, the post-decision half of the pipeline (decision records, file-or-sendback log, no-brainer execution) has effectively never fired, and mechanical gate check scripts are not installed where the formulas expect them. Dogfooding means routing the pack's own open development beads (gsp-98d, gsp-1pv, gsp-n9u, gsp-zjc chain, …) through the full idea → brief → present → verdict → route loop, which simultaneously exercises every pipeline stage and produces the ≥3 real classification examples that `catch-no-brainer`'s FP-convergence follow-up (he-ahfr) is explicitly gated on.

## Research Findings

### Brief Workflow (End-to-End)

Sources: `<mathcity-pack-root>/subdomains/brief-system/POLICY.md`, `mathcity/assets/brief-pipeline/{gates,paths,thresholds}.toml`, `mathcity/formulas/brief-*.toml`, `mathcity/orders/`, skills `brief-prep`, `catch-no-brainer`, `create-brief`, `present-it`, `present-briefs`, bead `he-xkq3`, live state in `<city-root>/.beads/briefs/`.

1. **Idea / source** — a bead, branch, PR, GH issue, or diff.
2. **Produce** — `brief-prep` (skill, and formula `brief-prep.toml`): classify artifact → run tests (G1 evidence: command + scope + exit code + date; G16 base ref) → run `catch-no-brainer` (steps: G5 server-touching → G5b user-skill-touching → capability-blocker → he-lele 5-criterion cat-A/B/C/D → 3 new v0.2 paths: defer-ratify-held, close-done-cited-commit, execution-confirmation-proof → else "candidate") → draft per `create-brief` with the **Decision-at-Top INVARIANT** (B1.1: first content = "What is being decided"), compact form only when all four B1.3 conditions hold → self-review → external `coordinate-review` gate (G4, cap 4 rounds) → bookkeeping (G8: `[brief-record]` tracker bead, follow-up beads) → **submit to `.pile/`** (producers never write the stack).
(For factory work slunged via `build-basic-briefed`, the terminal slot runs `brief-prep` automatically — no manual `gc sling … brief-prep --formula` required. Mechanism B above covers non-convoy / manual backfill cases. T4 confirmed, gsp-7x9f, 2026-07-16.)
3. **Promote** — `brief-shuffle` (order `brief-shuffle-pile`): single-writer under `.shuffle.lock`, one item per run, applies the gate registry via `brief-gate-keep` (profiles: `standard` = G1–G16 incl. G5b; `no_brainer` = 10 gates; `test_execution` = 7; `experiment` = 8; all `fail_closed`), then promotes to `stack/` + appends `stack/manifest.jsonl`, or rejects to `.pile/.rejected/`.
4. **No-brainer branch** — `no-brainer-classify` formula / `catch-no-brainer` skill copies `no_brainer:true` briefs into `.pile/.no-brainer/`; auto-execute runs by DEFAULT per Adopted N5 (2026-07-12) unless a kill switch is engaged — city `<city-root>/.beads/auto_merge_enabled`, then rig `<city-root>/hecke/.beads/auto_merge_enabled` (paths.toml `kill_switch_city`/`kill_switch_rig`): a flag that exists and reads `false` halts; **absent or `true` = ON**. Stop gates G5/G5b fire before G12 is even consulted.
5. **Refill** — `brief-watchdog-refill` keeps stack between `low_water = 2` and `high_water = 5` (thresholds.toml), max 3 new briefs/run, 30m cooldown; `brief.stack_low` event rings when the combo signal ≤ 1.
6. **Present** — the outside clerk (or Mayor) runs the `present-briefs` skill (accumulate-and-drain per HQ decision gt-3x2d): one run drains all pending stack briefs; no-brainers collapse to one-line items in a consolidated block; writes `presentations/<slug>-presented.toml` per brief. Presentation is human-facing and cannot be staffed by a gc order — the retired `brief-present-next` order never resolved a presenter. Clerk presents; Mayor never grills the human adjudicator directly.
7. **Adjudicate** — the human adjudicator issues `approve | reject | revise | defer` (the only verdict vocabulary; brief-system POLICY.md reuses it for pack rules).
8. **Record** — the `adjudicate-brief` skill (formerly `record-decision`): writes the verdict onto the brief bead (plus a redundant `decisions/<slug>.toml`), archives the run, and emits `brief.decided`, firing the machine cascade on the `mathcity.brief-operator` pool.
9. **Route (two consumers of `brief.decided`)** —
   - `brief-decision-dispatch`: ACTS (reassign source bead, route to refinery, defer); appends `decisions-dispatched.jsonl`.
   - `file-or-sendback-route`: logs `FILE` (successor bead exists → fire brief-prep on it) or `SEND-BACK` (self-contained → emit `brief.archive_requested`) to `decisions/file-or-sendback.jsonl` (append-only audit spec in `file-or-sendback-log-spec.md`).
10. **Archive / patrol** — `brief-archive-sweep` (dog pool) archives on request; `brief-review-patrol` scans the stack for `review_gate: pending` stragglers and files escalations.

Events are best-effort wake-ups; durable state (decision records, route log, bead metadata) is the source of truth.

### Current Pain Points / Breakdown Analysis

Observed in `<city-root>/hecke/.beads/briefs/` (read-only inspection, 2026-07-11):

1. **The pipeline dies at adjudication.** 9 briefs presented 2026-07-08 (`presentations/*.toml`, drained by mayor workflow gt-yuh0p), but `decisions/` is **empty**, the last verdict in `decisions.jsonl` is 2026-07-03, and `decisions/file-or-sendback.jsonl` **does not exist** — the post-decision gate (file-or-sendback-route) has never produced its audit log in the live rig. Everything downstream of "present" is untested in production.
2. **Stack saturation stalls the front end.** Stack depth 9 (manifest) / 11 (files) > high_water 5, so the watchdog correctly idles ("no refill") — but with no verdicts coming, the whole loop is wedged in steady state. Throughput is bounded by adjudication, and nothing surfaces that fact as a defect.
3. **No-brainer automation is inert.** One brief (`he-h3p2-catch-no-brainer-v0-delivery-brief.md`) has sat in `.pile/.no-brainer/` since early July; the pile-processor (he-x3se) is not shipped; the kill switch is absent (correctly OFF); `catch-no-brainer` is still PRELIMINARY v0.2 DRY-RUN, and its FP-convergence bead **he-ahfr is explicitly gated on ≥3 dogfood examples**. N6 ("a no-brainer surfacing at the human adjudicator is a regression") cannot be measured because no-brainers never complete the loop.
4. **Mechanical gate validators are not installed.** Formulas reference `mode = "exec"` checks at `.gc/scripts/checks/brief-*.sh`, but `<city-root>/hecke/.gc/` contains only `settings.json` and `tmp/` — no checks directory anywhere in the rig or city `.gc/scripts/`. The pack ships 10 check scripts in `mathcity/assets/scripts/checks/`, but they are not synced to where formulas exec them. Gate enforcement is therefore trust-based frontmatter self-declaration, exactly what he-xkq3 flags as "future: tighten with runnable validators."
5. **`review_gate` frontmatter is free-text.** The 2026-07-08 patrol found values like `taylor-approved-direct`, `self-review-only`, `dual-pass APPROVING`, `approved-iter-2` — the patrol only greps for `pending`, so two `self-review-only` briefs (violating B1.8/G4: external review required on every full-form brief) read as "healthy." Non-enumerated status vocabulary defeats the patrol. *Recurrence-prevention invariant (P1.17): `brief-gate-keep` validates `review_gate` against an explicit closed enum defined in `gates.toml` (e.g. `review_gate_values = ["pending","self-review-only","dual-pass","approved"]`) before promoting to stack; any unrecognized value → `.pile/.rejected/`. The fix bead must include a `gates.toml` amendment and a `brief-gate-keep` update.*
6. **Bookkeeping drift in the stack (G8).** `he-p4x5-clifford-euclidean-bubbles-brief.md` appears twice (plus a `.bak`), stack has 11 files vs 9 manifest entries, and every manifest entry carries `unlock_count: 0` — the prioritization signal from review-order-by-unlock-count is computed but unused. *Recurrence-prevention invariant (P1.17): `brief-shuffle` holds `.shuffle.lock` and writes to `stack/manifest.jsonl` atomically before writing the stack file; the post-shuffle step asserts `wc -l < stack/manifest.jsonl` == `ls stack/*.md | wc -l`. Any mismatch → abort with a G8 error before releasing the lock. The manifest-repair bead must include this assertion in the formula logic.*
7. **Portability defects block dogfooding anywhere but hecke.** `brief-prep/SKILL.md` and `catch-no-brainer/SKILL.md` hardcode `<city-root>/hecke/.beads/briefs/` (tracked by gsp-n9u: "De-hardcode 27 absolute <home>/ paths in mathcity pack"). The formulas are portable (rig-relative `artifact_root` var), the skills are not. No other rig (`<city-root>/gascity-packs`, `<city-root>/gascity`, `<city-root>/lmfdb`, `<city-root>/agent_skills`) has a `.beads/briefs/` root at all.
8. **State-location architecture is contested.** gsp-1pv (P1) wants the pipeline out of `.beads/` into a gc `artifact_root` (`~/.gc/mathcity/briefs/` per its notes) — the referenced plan doc (`mathematics/BRIEF-DOCUMENT-MODEL-PLAN-2026-07-08.md`) is missing from `<repos-root>/gascity-packs`, itself a breadcrumb (G11) failure.

### Pack State Assessment

- **Spec layer: strong.** POLICY.md (adopted 2026-07-11) is precise, rule-ID'd, and testable; gates.toml is a clean registry with profiles; the file-or-sendback log spec is well-defined.
- **Formula layer: complete but partially unverified.** 16 formulas / 10 orders cover the whole lifecycle; produce → shuffle → watchdog → present → patrol have real run records; record-decision → dispatch → file-or-sendback → archive have almost none.
- **Skill layer: functional but hecke-hardcoded and version-skewed** (skills carry `he-*` bead references and hecke absolute paths; canonical copies now live in gascity-packs but agent-skills fallbacks persist).
- **Existing dogfood-shaped bead:** gsp-zjc "Phase 1e: End-to-end proof — synthetic brief + Sigma_18 real cargo" already specifies prep → shuffle → present → approve → refinery merge → close, but is blocked by 5 open Phase 1a–1d deps (gsp-l9w, gsp-nxi, gsp-ev2, gsp-7u1, gsp-61s). This plan is complementary: it dogfoods on pack-development cargo rather than math cargo, and can start before the Phase 1 chain lands.

## Dogfood Concept

### What "Dogfooding" Means Here

**The brief-system pack adjudicates its own development.** Every meaningful change to the pack — de-hardcoding paths, shipping the pile-processor, migrating the artifact root, fixing manifest drift — becomes a source bead that must travel the full pipeline: `brief-prep` produces a gated brief on it, the shuffler promotes it under the G1–G16 registry, `catch-no-brainer` classifies it, the clerk presents it, the human adjudicator issues a verdict, `brief-record-decision` records it, and `file-or-sendback-route` logs FILE/SEND-BACK. The pack's development history becomes the pipeline's test suite.

Primary dispatch path (D2): Route work through a build-basic-briefed convoy; the terminal publish slot fires brief-prep automatically and deposits the brief into the pile. No manual gc sling … brief-prep step required for convoy-tracked work.

Universal firing intent (designed/pending): A Mayor sling-wrapper skill and dispatch doctrine will make every convoy fire a brief by default. This is designed but not yet shipped. Until then, the convoy must be explicitly launched with build-basic-briefed rather than build-basic.

This is qualitatively better than synthetic testing because pack-dev work naturally spans the classifier's category space (mechanical renames = cat-A, doc-only updates = cat-D, close-with-cited-commit shapes, capability-blockers when creds/permissions are missing, and user-skill-touching overrides when SKILL.md files change — G5b will fire on real inputs). Each cycle emits durable evidence (decision toml, route-log line, presentation record) that doubles as regression fixtures.

## Pilot Candidates

Ordered by fit. All are open beads in the gascity-packs rig (gsp-\*) as of 2026-07-11.

1. **gsp-n9u — De-hardcode 27 absolute paths in mathcity pack (P1).** Best first cargo. It is mostly-mechanical (strong cat-A/cat-D classifier exercise), it is a *prerequisite* for running the pipeline outside hecke, and its diff touches skill files → **G5b user-skill-touching override should fire**, testing the most safety-critical stop gate on a real input. Has two input convoys already (gsp-8eb, gsp-jnb).
2. **gsp-1pv — Move brief pipeline out of `.beads/` into gc artifact_root (P1).** Architecture-class → guaranteed full-form brief, exercises the judgment path, alternatives section, and `defer` verdict plausibly. Also directly fixes pain point 8. Its missing plan doc is a bonus: the brief must reconstruct or re-stage it (G7/G11 exercise).
3. **gsp-98d — Produce drain with fan-in before shuffle (P1).** Formula-engineering cargo; its brief must carry G1 evidence for formula validation and exercises the single-writer shuffle invariant reasoning.
4. **Manifest/stack repair (new small bead).** Remove the `.bak` and duplicate `he-p4x5` stack entries, reconcile manifest (9) vs files (11). Trivially cat-A/cat-C — an ideal candidate to be the **first end-to-end no-brainer**, and a live test of N6.
5. **Check-script installation (new bead).** Sync `mathcity/assets/scripts/checks/brief-*.sh` into the location formulas exec (`.gc/scripts/checks/` or corrected paths). Converts trust-based gates into mechanical ones; its own brief is the first to be mechanically validated.
6. **gsp-61s — Land polecat/gsp-i9j stack-low watchdog trigger (P2)** and **gsp-7u1 — linear step-bead chain (P2).** Feed the gsp-zjc Phase 1e proof; adjudicating them via the pipeline advances both this dogfood and the existing end-to-end plan.
7. **(Stretch) drain the existing 9 presented hecke briefs.** Not pack cargo, but recording their verdicts is the single highest-leverage act: it unwedges the live stack and gives file-or-sendback-route its first real inputs. Requires the human adjudicator time; treat as a parallel track.

## Metrics & Success Criteria

Primary counters (all derivable read-only from pipeline state):

| Metric | How measured | Pass bar (pilot) |
|---|---|---|
| Full-loop completions | briefs with pile→stack→presented→`decisions/<slug>.toml`→route-log line | ≥ 3 (matches he-ahfr's dogfood-example gate) |
| Route-log liveness | `decisions/file-or-sendback.jsonl` exists, valid per spec/check script | ≥ 3 valid entries, 0 schema violations |
| Gate-evidence completeness | all 16 standard-profile gates present (evidence or N/A) per B1.4 in each deposited brief | 100% of pilot briefs |
| Stop-gate correctness | G5b fires on the gsp-n9u brief (skill-touching); no compact form ships for it | 1/1, zero false negatives |
| Classifier accuracy | catch-no-brainer verdict vs the human adjudicator's reaction; N6 regressions ("why am I seeing this?") | ≥ 1 correct no-brainer, 0 N6 regressions unfixed |
| Decision-at-Top compliance | first content after header is "What is being decided" (grep first ~10 lines) | 100% |
| Latency: deposit → verdict | timestamps: manifest `created_at` → decision toml | median < 72h during pilot (vs current ∞) |
| Bookkeeping consistency (G8) | manifest entries == stack files; tracker bead per brief; no orphaned `.bak` | 0 drift at pilot end |
| Send-back rate | SEND-BACK / total routed | recorded (no target; the human adjudicator's constraint is *minimize*, so trend matters) |

Qualitative pass signals: the human adjudicator can adjudicate each pilot brief in one sitting without follow-up questions (the B-pillar's stated purpose); the patrol report distinguishes healthy from non-compliant `review_gate` values; at least one classifier or gate defect is found *and fixed via its own brief* (the recursive win condition).

## Pilot Steps

Phase 0 — baseline (read-only, no authorization needed):

**Executor: Homer (or any read-only agent) — no fleet writes; the human adjudicator reviews the baseline snapshot output.**

0. **Adopt `brief-system/POLICY.md` before gates enforce it (PP2.1).** The policy is currently `Status: Draft revision` — a Draft policy may not be cited in check skills or gate formulas. Run `/new-brief-policy` with a version-bump micro-proposal (no rule changes) to flip Status to Adopted and record the human adjudicator's sign-off. This step is a prerequisite for all downstream gate enforcement. The human adjudicator's approval in *this session* satisfies PP2.2.
1. Snapshot current state: `ls <city-root>/.beads/briefs/{stack,.pile,.pile/.no-brainer,decisions,presentations}` and `wc -l stack/manifest.jsonl decisions.jsonl`; save to `<city-root>/tmp-for-review/briefs-dogfood-baseline/`.
2. human decision (itself a mini-brief): **which rig hosts the dogfood** — (a) hecke (works today, paths already match) or (b) gascity-packs (cleaner: pack adjudicates itself in its own rig, but requires gsp-n9u first and `mkdir .beads/briefs/{.pile,stack,archive,decisions,.staging}` scaffolding). Recommendation: start in hecke (option a), migrate after gsp-n9u lands.

Phase 1 — minimal viable dogfood (1 brief, 1 verdict, 1 route):

**Executor: Clerk runs `brief-prep`, `brief-shuffle-pile`, `catch-no-brainer`, and the `present-briefs` skill (presentation is human-facing, not a gc order). adjudication happens and issues the verdict; the `adjudicate-brief` skill (formerly `record-decision`) records it and rings `brief.decided`, firing the machine cascade on the `mathcity.brief-operator` pool, which runs `file-or-sendback-route`.**

3. File the manifest/stack-repair bead (candidate 4). Verify: `bd show <id>`.
4. Run `brief-prep source=<id>` → brief lands in `.pile/`. Verify: file exists, frontmatter has both safety booleans, first line after header is the decision.
5. Run the shuffle (order `brief-shuffle-pile` or manual formula pour). Verify: `grep <slug> stack/manifest.jsonl` and gate-evidence section lists all 16 gates.
6. Run `catch-no-brainer` on it. Expected: `no_brainer:true, category:cat-A/C, compact_eligible:true`; copy appears in `.pile/.no-brainer/`. **Kill switch stays absent — no auto-execute.**
7. Present via the `present-briefs` skill (clerk/Mayor); adjudication happens; run the `adjudicate-brief` skill (formerly `record-decision`). Verify: the verdict is on the brief bead and `decisions/<slug>.toml` exists.
8. Confirm `file-or-sendback-route` fires on `brief.decided`. Verify: `decisions/file-or-sendback.jsonl` exists and `bash mathcity/assets/scripts/checks/brief-file-or-sendback-log-required.sh` (run from a checkout with correct cwd) exits 0.

Phase 2 — full-scale pass (3–5 briefs, category coverage):

**Executor: Same as Phase 1 — Clerk (formula runs + `present-briefs` skill), the human adjudicator (verdicts + `adjudicate-brief`), gc worker on the `mathcity.brief-operator` pool (file-or-sendback-route, check-script installation). The check-script installation bead additionally requires the human adjudicator's git push authorization before commit goes to remote.**

9. Repeat for gsp-n9u (expect G5b stop → full-form → the human adjudicator adjudication), gsp-1pv (architecture full-form; plausible `defer` → tests defer path), and the check-script installation bead (its merge makes gates mechanical). **For the check-script installation bead specifically:** the replay-able implementation path (P1.1) is to update the formula gate paths to reference `mathcity/assets/scripts/checks/brief-*.sh` by their canonical pack-asset path — NOT to copy scripts into `.gc/scripts/checks/` via a one-off sync, which violates P1.1 (not re-derivable from imports). If the formula layer requires absolute paths, the alternative is a `setup-brief-checks` gc formula/order step that installs them as part of `gc import install` mechanics. Resolve which approach before slinging the check-script bead; the bead must state the chosen mechanism and a P1.1 compliance note.
10. After the check scripts land: re-run `brief-gate-keep` on one already-promoted brief to confirm exec-mode checks pass where frontmatter previously self-declared.
11. One FILE routing: adjudicate a brief whose record names a successor bead (e.g., gsp-61s → gsp-zjc) and verify the route log carries `choice:FILE, target_bead_id:<successor>` and a new brief-prep fires.
12. Compute the metrics table; write the pilot report as a breadcrumb (G11) under `latex/scratch/` or `<city-root>/tmp-for-review/`; file follow-up beads for every defect found (each becomes future dogfood cargo).

Phase 3 — decision point:

**Executor: Clerk produces briefs via the pipeline (naturally). adjudication happens. Each decision is a separate brief routed through the full loop.**

13. Brief the human adjudicator (via the pipeline, naturally) on: enable no-brainer auto-execute for cat-A only? migrate artifact root per gsp-1pv? adopt an enumerated `review_gate` vocabulary? Each is one brief (B1.2: one decision per brief).

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| the human adjudicator adjudication bandwidth is the real bottleneck (root cause of the current wedge); pilot adds more briefs to an unread stack | Cap pilot at ≤ 3 concurrent stack additions; use compact form wherever legitimately eligible; schedule one explicit adjudication sitting per phase; the latency metric makes the bottleneck visible instead of silent |
| Accidental no-brainer auto-execution during pilot | Under Adopted N5 auto-execute is ON by default; to halt it during the pilot, ENGAGE a kill switch (write `false` to `<city-root>/.beads/auto_merge_enabled` city-wide or `<city-root>/hecke/.beads/auto_merge_enabled` rig-level — the human adjudicator authorization recorded as a decision bead); verify switch state before each phase |
| gsp-n9u brief touches user skills → an erroneous merge has pool-wide blast radius | That is exactly why it is a pilot candidate: G5b must route it to the human adjudicator; treat any compact-form emission for it as an automatic pilot FAIL and classifier bug |
| Dogfood briefs pollute hecke's math-brief stack (mixed cargo confuses the clerk/the human adjudicator queue) | Prefix slugs `gsp-…-brief`; present in a separate drain batch; move to the gascity-packs rig as soon as gsp-n9u lands |
| Formula exec-checks fail hard (missing `.gc/scripts/checks/`) and block the shuffle mid-pilot | Known defect (pain point 4); Phase 1 uses manual verification alongside formula runs; the fix is itself pilot cargo (candidate 5) |
| Conflict with the in-flight Phase 1a–1e chain (gsp-zjc deps) — double-building the same hooks | This plan only *adjudicates* those beads, it does not implement them; coordinate via Mayor so refinery hooks (gsp-l9w) land through, not around, the pipeline |
| Dual-copy drift (`<repos-root>/gascity-packs` vs `<city-root>/gascity-packs`) corrupts which pack version the city runs | Record `git rev-parse HEAD` of both checkouts in every pilot brief (G16 spirit); sync via the normal GitHub exchange before each phase |
| Route-log spec vs paths mismatch discovered mid-pilot (e.g., decisions.jsonl at root vs decisions/ dir duality) | Treat as a finding, not a blocker: file a bead, brief it, fix it through the loop |

## Live Grounding: Hecke Campaign (2026-07-11, from Mayor session/Mayor)

This section was added after initial drafting, based on Mayor session's 14:17 message with real in-flight context from the hecke repair campaign. It sharpens pilot ordering and the concrete first deliverable.

### The he-714x7 convoy (5 HUMAN_OK_REQUIRED beads)

The #335 gamma0 repair campaign has 5 open beads that each require explicit the human adjudicator authorization before any polecat can execute server work on aia-s27:

| Bead | Action | Risk |
|---|---|---|
| he-w38gm | DRY_RUN classification sweep over full DATA/gamma0/ | Reads full server dataset |
| he-6mi84 | Smoke test 4 items | Writes to DATA/ |
| he-besry | Route 2 contradiction records via transversal | Writes to DATA/ |
| he-9n0ki | Queue 3 deleted items for Gamma0_fp(:redo:=true) | Days-long server jobs |
| he-ce5sw | Mass label rename on-disk files in DATA/ | Mass rename |

Today "HUMAN_OK_REQUIRED" lives only as a string in each bead's description. No `decisions.jsonl` entry exists for any of them. When a polecat picks up he-w38gm and asks "was this approved?", there is nothing to check — authorization is conversation-only and evaporates.

**This is exactly Priority 1 in the plan's roadmap:** `adjudicate-brief` (formerly `record-decision`) + `decisions.jsonl` must run before this convoy can move safely.

### Concrete first deliverable: he-w38gm

`present-it` + `adjudicate-brief` (formerly `record-decision`) in combination for **he-w38gm** is the single most leveraged first exercise. Steps:
1. Run `present-it` on he-w38gm — surface what's being decided (DRY_RUN scope, risk, assumptions)
2. The human adjudicator issues a verdict (yes/no/conditions)
3. `brief-record-decision` writes `decisions/<slug>.toml`
4. Polecat pre-flight for any server-touching bead checks for this record before executing

This completes one loop in hecke cargo, gives file-or-sendback-route its first real input, and unblocks the entire he-714x7 convoy — concrete returns before gsp-n9u even lands. Recommend running this in parallel with Phase 0 baseline snapshot.

### Three stray-bead cases (catch-no-brainer illustration)

From a stray-bead sweep this session, three beads landed with three different correct dispositions:

- **he-xr82h**: 4 unique items, otherwise duplicate of he-besry → absorb + close. **No-brainer (cat-A)** — catch-no-brainer should auto-route this without the human adjudicator.
- **he-66vr**: A month of the human adjudicator routing directives, quarantine calls, ops warnings, exception-handling policy, inflight registry. Research journal, NOT a task. Almost closed as "done" and would have permanently lost all of it. → **Needs ARCHIVED bead lifecycle state** (see below).
- **he-t5uq**: Live work due ~2026-07-16, script already written, needs convoy slot. → Ordinary dispatch, but required Mayor analysis to reach that conclusion.

All three looked identical in `bd show`. Without catch-no-brainer: 3 full Mayor analyses. With a working classifier: he-xr82h auto-routes (cat-A), only he-66vr and he-t5uq reach the human adjudicator. The pilot is already confirming the classifier's value on real traffic.

### ARCHIVED bead lifecycle state (new gap, not in original plan)

he-66vr reveals a gap not currently in the brief-system spec or pilot plan: a lifecycle state between OPEN and CLOSED meaning "not actionable, a research record — searchable, never dispatched." Today there is no way to mark this; it either stays open (confuses dispatch and patrol) or gets closed (destructive — the record is gone).

**Recommendation:** File a bead for `ARCHIVED` state support in bd. Add a Phase 3 brief for this decision. Do not route he-66vr to any formula until the state exists; mark it `[RESEARCH_JOURNAL — HOLD FOR ARCHIVED STATE]` in description as a human signal.

### Revised priority ordering (incorporating live context)

| Priority | Component | Forcing function |
|---|---|---|
| 1 | `adjudicate-brief` (formerly `record-decision`) + `decisions.jsonl` | he-714x7 convoy blocked; server work executing without audit trail |
| 2 | `present-it` for single HUMAN_OK bead | he-w38gm: DRY_RUN sweep needs formal structured OK |
| 3 | `catch-no-brainer` (classifier running) | he-xr82h = unnecessary the human adjudicator load; he-ahfr gated on ≥3 dogfood examples |
| 4 | G5/G5b stop-gate enforcement | he-besry, he-9n0ki, he-ce5sw all server-touching; gate must reject without decisions.jsonl |
| 5 | ARCHIVED bead state | he-66vr; without it, research journals get closed destructively |

The original plan's Phase 1 (manifest repair as first no-brainer) is still the right gsp-side first step. On the hecke side, he-w38gm is the parallel first step. Both can start immediately.

## Rollback / Abort Criteria

Abort the pilot (and file a single post-mortem bead) if any of:

- **Any auto-execution occurs** while the kill switch is absent — hard stop, security-class defect, immediate escalation to the human adjudicator.
- **A G5/G5b stop gate fails open** (server- or skill-touching brief ships compact or auto-routes) — hard stop.
- Two consecutive pilot briefs sit > 7 days presented-without-verdict → the bandwidth assumption is wrong; pause intake, keep the wedge analysis as the deliverable.
- The shuffle lock or manifest becomes inconsistent in a way manual repair can't restore from `archive/` + git history → freeze pipeline writes, restore from baseline snapshot (Phase 0 step 1).
- Pilot uncovers > 5 blocking defects before one full loop completes → downgrade to defect-burn-down mode; the pipeline is not ready for cargo.

Rollback is cheap by construction: all pilot artifacts are additive files under `.beads/briefs/` (briefs, toml records, JSONL appends) plus ordinary beads. Rolling back = archiving pilot briefs to `.pile/.rejected/` or `archive/`, closing pilot beads with a supersession note, and deleting nothing that predates the baseline snapshot. Bead state changes are reversible via `bd update`; no code merges happen except through the human adjudicator-approved verdicts, which are themselves the audit trail.
