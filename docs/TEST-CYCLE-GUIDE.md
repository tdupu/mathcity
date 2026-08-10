# mathcity brief-and-work system — test suite & triage

> **DO NOT ABRIDGE OR TRUNCATE THE CONTENTS OF THIS FILE WITHOUT EXPLICIT USER AUTHORIZATION.**
> Correct errors in place (P5.4); every section has been verified correct across multiple Mayor sessions.

**Owner:** Mayor session (outside agent, <city-root> city side) · **Started:** S6, 2026-07-15
**Purpose:** get mathcity's brief↔work system to a state we can TRUST — every
lifecycle edge, every rig, a human verdict processed under load within a bound,
fail-loud. Source of truth is code behaviour (P5.4): input X → output Y, seen
with our own eyes.

This folder is **untracked** (`.gitignore` = `*` + `.git/info/exclude`). It is a
scratch harness, not shipped pack content.

## Files
| File | Role |
|---|---|
| `README-test.md` | THIS — test matrix, defect classification, action PERT, run-instructions |
| `run-log.md` | living run-log (tabular command→result); append every run. Seeded from S4 e2e log |
| `probes/` | python test scripts, one per edge/component (specs below; filled as city comes up) |

Legend (matches run-log): ✅ pass · ❌ fail/bug · ⚠️ finding/caveat · 🔬 diagnostic · ⛔ blocked · ▶ ready · ⏳ in-progress

---

## 1. The system under test (two layers + the wires)

- **WORK layer:** beads, dispatch pool, orders/formulas (gc core + mathcity pack).
- **BRIEF layer:** brief stack, present/adjudicate, verdict recording.
- **The wires (coupling edges)** are what "end-to-end" means. There are **5**:
  1 work→brief (intake) + 4 brief→work (the verdict dispositions).

## 2. TEST MATRIX

| # | Edge / component | What it verifies | The test (input → expected output) | Blocked-by | Result |
|---|---|---|---|---|---|
| T0 | boot | city boots green | `gc start` → `gc doctor` all config checks green | repo-side landing agent Q1 ACK | ⛔ |
| T1 | **E-up** (work→brief) | intake arc fires for **every** rig (gs-5wf regression) | closed `needs-decision` bead on an idle non-hecke rig → brief-record appears in ITS OWN store | T0 | ⛔ |
| T2 | **E-approve** no-branch | approve verdict settles work, closes brief (gt-yv8p2 escape) | approve a no-branch brief → work dispatched, brief bead closed, no dangling retry | T0,T8, **gsp-rqv0** (non-he/as/gsp rigs only) | ⛔ |
| T3 | **E-approve** branch | approve → publisher-handoff dispatch | approve a branch-bearing brief → publisher-handoff fires, correct rig | T0,T8,gsp-rqv0 | ⛔ |
| T4 | **E-reject** | reject archives + follow-up scoped to correct rig | reject a brief → archive; any follow-up lands in the SOURCE rig store (not HQ) | T0,T8,gsp-rqv0 | ⛔ |
| T5 | **E-revise** (re-draft) | revise → `[revise]` follow-up re-draft, rig-scoped | revise a brief → re-draft follow-up created **in source rig** (repo-side landing agent: same unscoped `gc bd create` as reject → pre-fix lands at HQ); **this is the he-naqz3 case that FAILED** | T0,T8, **gsp-rqv0** (for rig-scoping) | ⛔ |
| T6 | **E-revise-with-work** | revise that mandates prerequisite WORK, not re-draft (gsp-vuv8) | revise citing "premise out of order, do X first" → prerequisite-work follow-up, brief parked | T0,T8,gsp-vuv8 | ⛔ |
| T7 | **E-defer** | defer → hold, no dispatch | defer a brief → brief parked/deferred, no work dispatched | T0,T8 | ⛔ |
| T8 | **write-decision** | brief-record-decision write step ACTUALLY runs + emits `brief.decided` | record a verdict → `gc events --type brief.decided` shows the event; gt-zayiw-class hang does NOT recur | T0, root-cause A5 | ⛔ |
| T9 | **verdict-under-load** (TRUST test) | human verdict processed within a BOUND while patrol churns (gsp-kljg) | queue a verdict while brief-review-patrol floods the pool → verdict claimed+recorded ≤ bound (e.g. 1 in-flight step) | fix A6 | ⛔ |
| T10 | N-classify | no-brainer classifier returns correct verdict JSON | run catch-no-brainer on sample briefs (server-touching, user-skill, plain) → correct category | T0 | ⛔ |
| T11 | N-compact | compact-form brief path | catch-no-brainer compact-eligible → present-it `--compact` shape | T0 | ⛔ |
| T12 | **no-brainer AUTO-EXEC** | kill-switch OFF → classified no-brainer auto-executes + archives | with kill-switch disengaged, drop a safe no-brainer → auto-sling + archive to `.pile/.no-brainer` | T0, A11 decision | ⛔ |
| T13 | backpressure | Dolt-storm / patrol flood does not stall verdicts indefinitely (gsp-12rf) | induce patrol churn → verdict still lands (paired with T9) | fix A9 | ⛔ |

**Trust definition (all must hold):** T1–T8 pass on ≥2 rigs incl. one non-hecke;
T9 passes with a stated numeric bound; failures are LOUD (surfaced, not silent).

## 3. DEFECT CLASSIFICATION (fix-at-source triage — P5.4)

Each defect → **PACK** (mathcity edit, our/repo-side landing agent pack lane) · **REBUILD** (gc/bd core, repo-side landing agent) · **INFRA** (Dolt/host).

**⚠️ THIS TABLE WAS REWRITTEN S6.3 — the original A4 "FIFO priority" framing was REFUTED by live reproduction. See run-log.md S6.3/S6.4.**

| Bead | Defect (corrected) | Class | Fix path | Status |
|---|---|---|---|---|
| **gsp-12rf** | **ROOT CAUSE of S5 failure.** `brief-review-patrol idempotent=true` → open-work-gate query times out under Dolt latency → `gateFailClosed` fails OPEN ("dispatching anyway" #2893) bypassing single-flight, ×16 per-rig instances fanning into 1 pool → churn flood starves real work | **PACK** | drop/re-gate `idempotent=true` + collapse 16 per-rig into one shared/condition-gated patrol. Source-verified (order_dispatch.go:2062-2068). | HOTFIX applied (paused); **durable fix = repo-side landing agent, HOLD** |
| gt-zayiw | NOT a separate defect — the verdict was BLOCKED behind its finalize dep because its frontier work (write-decision iteration) starved in the gsp-12rf-flooded pool. Verdict content was captured, workflow instantiated. | — | resolves when gsp-12rf fixed + pool drains | diagnosed |
| gsp-kljg | **DE-SCOPED** — NOT the S5 cause. All pool items are P2, so "claim honors priority" changes nothing. Priority-blindness is a *latent* concern only. | — | no action for S5 trust | de-scoped |
| gsp-rqv0 | dispatch rig-resolution hardcoded he/as/gsp → approve/reject fail other rigs + unscoped follow-ups → HQ | **PACK** | fix `brief-decision-dispatch.toml`; plan gate-approved; needs the human adjudicator GO | valid, HOLD |
| gsp-vuv8 | revise-with-work disposition unmodeled | **PACK** | design new disposition (re-draft vs do-prereq-work) | to design |
| gsp-mbon | installed pack content = unpinned working-tree symlinks (dispatch pinned @717b9fb; ~126 formulas symlink the repo-side tree) | **REBUILD** (+PACK contract) | pin installed content to a committed ref | repo-side landing agent, HOLD |
| gsp-ntoi | Dolt storm = idempotent-bypass churn (coupled to gsp-12rf) + store divergence + orphan + 2nd city | **INFRA** | reconcile ✅ DONE, orphan ✅ killed; re-enable backups AFTER idempotent fix; 2nd-city = the human adjudicator | mostly DONE |

## 4. ACTION ITEMS — corrected PERT + live status

```
DONE ✅
  A0  consensus w/ repo-side landing agent ...................... lanes agreed
  A1  safe `gc start` (dolt-remotes-patrol off, source-verified) ... city GREEN
  REPRO reproduce S5 failure LIVE ........... root cause OVERTURNED (not FIFO;
        it's gsp-12rf idempotent-bypass fan-in flood). A4 SHELVED.
  HOTFIX pause all 16 brief-review-patrol instances (the human adjudicator-authz) . containment
  BEADS corrected: gsp-kljg de-scoped, gsp-12rf P1 + source-verified mechanism
  repo-side landing agent: reconcile both diverged stores + kill orphan ... DONE (his lane)

IN PROGRESS ⏳
  DRAIN  watch pool drain the 48-item backlog now that refill is stopped
  TEST-VERDICT  run ONE synthetic non-hecke verdict end-to-end (T5/T8) to
        confirm real work now flows through a de-flooded pool

PENDING — repo-side landing agent lane (HOLD until complete picture; the human adjudicator-gated) ⛔
  gsp-12rf durable fix: drop idempotent=true + collapse patrol fan-in (PACK)
  gsp-rqv0 dispatch rig-resolution fix (PACK) — needs the human adjudicator GO
  gsp-mbon pin installed pack content (REBUILD)
  gsp-ntoi: re-enable backups + patrols AFTER idempotent fix; syncer flock guard
  HOMER hygiene 1-3: beads 109 behind; gascity-packs upstream merge; push 717b9fb

PENDING — my lane / pack PRs ▶
  T1 regression (E-up all-rigs) + T2-T7 edges (needs de-flooded pool)
  on-merge-brief-record: assess same idempotent-bypass (12 wisps) — it's the
        E-up edge, so fix carefully, don't just disable
  T12 no-brainer: verify auto_merge_enabled/bd-coupling → the human adjudicator activation →
        test. AFTER churn fixed + pipeline trusted (NOT a fix for the flood).
  HOMER hygiene 4-5: nudge-city commit + 4 missing README rows (gascity-packs PR)

PENDING — human decisions 🅣
  2nd city ~/gascity-city-example-owner retire-vs-keep (gsp-ntoi)
  gsp-rqv0 GO (bundled push)
  no-brainer activation (after fix)
  [A4 Option-1-vs-2: RESOLVED by reproduction — no longer needed]
```

**Corrected critical path:** `REPRO ✅ → HOTFIX ✅ → verify DRAIN → TEST-VERDICT → gsp-12rf durable fix (repo-side landing agent) → re-enable patrols → RE-TEST edges → TRUST`.
Everything hecke/#335 stays DOWNSTREAM of TRUST and is dogfood — not this round.

**Policy gates (check-plan-hygiene, S6):**
- **A6-Option-1 & gsp-mbon are OUTSIDE the owned set** (gc core / materialization machinery) → MUST route through the pr-pipeline (`mol-pr-from-issue`), never a direct push (P3.1/P3.2); rebuild via `update-gascity-from-source` (P1.6). Route through the repo-side landing lane, outside-agent context (P3.5).
- **A7 (gsp-rqv0) is INSIDE the owned set** (`mathcity/formulas/brief-decision-dispatch.toml`) — direct edit OK, but the installed copies are pinned real files (gsp-mbon) → a live change needs a deliberate copy-refresh of the 32 pinned files (repo-side landing agent, S5).
- **Patrol-off (city.toml override)** cleared as a NAMED WORKAROUND (P1.17): root cause = gsp-ntoi, re-enable tracked on that bead, disable source-verified.

## 5. PROBE SPECS (python, filled as city comes up)

Each probe: idempotent, self-cleaning (tracks scratch bead IDs, closes/removes them),
prints a single `PASS`/`FAIL: <reason>` line, appends a row to `run-log.md`.

| Probe | Drives | Notes |
|---|---|---|
| `probes/edge_up.py` | T1 | create+close needs-decision bead on a target rig; poll rig store for brief-record on `metadata.source_bead`; assert appears ≤ bound |
| `probes/edge_verdict.py <disposition>` | T2-T7 | record a verdict of the given disposition; assert the correct downstream (dispatch/archive/redraft/defer) + `brief.decided` event |
| `probes/write_decision.py` | T8 | isolate the write-decision step; assert event emission (gt-zayiw regression) |
| `probes/verdict_under_load.py` | T9,T13 | spawn patrol churn, queue a verdict, measure claim latency vs bound |
| `probes/no_brainer.py` | T10-T12 | run classifier on fixtures; with kill-switch off, assert auto-exec+archive |

Run instructions and per-probe usage go here once written. Until then, runs are
manual and recorded in `run-log.md`.
