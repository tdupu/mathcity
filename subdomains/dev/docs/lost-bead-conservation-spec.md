# Lost-Bead Conservation Spec

Parent: [../README.md](../README.md)

**Date:** 2026-08-15
**Status:** Canonical. This is the intended convergence point for the ~8 overlapping
strand/reclaim mechanisms listed in §7 — it does not itself add a ninth.
**Origin:** [`gsp-2bowrk`](#references) — *"SILENT-FAILURE META-BUG: automatic lost-bead
reclaim chain is dead at 4 links, all fail silently (P6.1) — 213 strands uncaught"*
(P0, still OPEN). That bead remains the canonical *fix checklist*; this document is the
canonical *architecture record* the checklist is repairing.
**Evidence:** `gsp-2bowrk` (body + both comments), `gsp-beo9sy`, `gt-rqaqu` (+ its
adjudication comment), and live re-verification of every status claim in §4 against beads,
orders, and source on 2026-08-15 — see the "verified" notes inline.

> **Scope note.** Implementation detail for the tail-end detector lives in
> [`docs/superpowers/specs/2026-08-04-tail-end-detector-design.md`][ted-design]
> and is deliberately **not** duplicated here. This document states the invariant, the
> loop, and the wiring status; that document states how class-2 detection is built.
>
> That spec lives in a **different repository** — `tdupu/gascity-packs`, not this one — so
> the link is absolute rather than relative. As of 2026-08-15 it is present on that repo's
> `main` but **not** upstream on `gastownhall/gascity-packs`.

---

## 1. The conservation invariant

Stated by Taylor on `gsp-2bowrk`, 2026-08-04, in response to a 213-bead strand backlog:

> *"This is a silent failure bug. They should be being processed on their own."*

**The invariant.** Every bead that

1. **CAN** be worked — ready and unblocked, **and**
2. **SHOULD** be worked — not deferred, not superseded, not molecule-internal, **and**
3. **ISN'T** being worked

**must be caught by the lost filter.** The age trigger is **>3 days idle**.

The invariant is a *conservation* law in the literal sense: work does not silently leave
the system. A bead may be closed, deferred, superseded, or reslung — but it may not simply
stop existing as far as the fleet is concerned. Every exit must be an *accounted* exit.

The failure mode this guards against is not "a bead was handled wrongly." It is "a bead was
handled by nobody, and nothing said so." That is why §6 (fail-loud) is load-bearing rather
than cosmetic: an unenforced conservation law is indistinguishable from no law at all.

## 2. The two lost classes

The invariant partitions into two detection problems with genuinely different signatures.
Confusing them is what let the tail accumulate uncaught.

| | **Class 1 — dispatched-but-frozen** | **Class 2 — ready-but-never-dispatched** |
|---|---|---|
| Shape | Was slung, carries routing metadata, then froze | Unblocked and wanted, but never slung at all |
| Signal | Routing metadata present (`gc.routed_to` / `gc.run_target` / `gc.execution_routed_to`), no progress | No routing metadata, `bd ready`, idle > 3d |
| Detector | `stuck-bead-watch` | `tail-end-detector` |
| Order cadence | cooldown, 90s | cooldown, 15m |

**Class 2 is the class `stuck-bead-watch` structurally cannot see.** It keys on beads that
*were* dispatched; a bead that was never dispatched has no routing metadata to inspect and
is invisible to it. This is the gap that let the tail grow silently, and it is what
`tail-end-detector` (built 2026-08-05, commit `7834363`) now covers.

The two detectors are kept **disjoint by construction**, not by convention:
`tail-end-detector` excludes any bead carrying routing metadata, so class 1 beads never
enter its scan. Records are written as `{bead_id}.tail.toml` so they cannot clobber
`stuck-bead-watch`'s `{bead_id}.toml` records in the shared classification root.

### Magnitude

The live dry-run across 7 rigs on 2026-08-05 found **1064 actionable-idle never-dispatched
beads** (294 superseded-close / 770 resling). This figure ballooned from an earlier ~202
estimate because a same-day brief-factory run created ~1000 unrouted task beads.

That ballooning is the argument for the batch cap being **load-bearing rather than
optional**: dumping 1064 reslings at once would re-strand all of them, converting a
detection success into a fresh instance of the same bug.

## 3. The training loop

The filter is not merely a detector. Per Taylor on `gsp-2bowrk`, it has three legs, and the
third is what makes it a *loop* rather than a sweep.

### (a) CLASSIFY

Sort each caught bead into a disposition:

- **superseded → auto-close** (no-brainer path). Requires a real supersession detector; see
  §8 on `gsp-beo9sy`.
- **stranded-but-wanted → resling.**

The detector never closes a bead itself. It emits a `close_moot` classification and the
rollup files a **close brief**; the actual close stays behind a human gate. Age (or any
other signal) flags a *candidate*, never a verdict.

### (b) LEARN

A recurring fingerprint seen **≥3 times** is promoted into an automatic rule — the
`gt-rqaqu` mechanism. The grouping key is

```
lost_class + disposition.recommendation + root_cause.class + root_cause.fingerprint
```

and the threshold is the rollup script's `--threshold` (default 3).

Taylor's adjudication on `gt-rqaqu` (2026-07-30) **generalized** this: *any* grouping key a
human has validated as safe-and-reversible at threshold auto-applies its resling
disposition thereafter — the rule is not scoped to the one fingerprint that triggered it.
Critically, only the **resling ACTION** is automated. The per-occurrence
`lost-bead-classification.v1` audit trail stays fully recorded regardless, because
detection and authorization are separable: detection lives in the classification/rollup
layer, not in whether each individual resling needed a human's yes.

### (c) IMPROVE the producing formula

The failure should feed back into whatever produced the strandable bead:
`brief-producer-failure → rollup → brief-producer-repair`.

**This leg exists but is not wired.** The repair formula exists with **no consumer and no
order** driving it. Of the three legs, (c) is the one still missing its wiring — see §8.

## 4. The reclaim chain — dead links and live status

`gsp-2bowrk` recorded 4 dead links plus a meta-fix. Every status below was **re-verified on
2026-08-15**, because the bead's own status notes date from 2026-08-05 and several had
moved. Where the source bead and current reality disagree, current reality is recorded and
the drift is noted.

| # | Link | Status (verified 2026-08-15) |
|---|---|---|
| 1 | `stuck-bead-watch` — detect (90s order) | ✅ **LANDED** |
| 2 | Rollups — classify → resling | ✅ **LANDED** |
| 3 | `gt-rqaqu` auto-resling rule | ⛔ **APPROVED BUT NOT ARMED** |
| 4 | `orphan-sweep` — dead-agent reclaim | ❌ **NOT LANDED** |
| 5 | P6.1 fail-loud (meta-fix) | ◐ **PARTIAL** |

### Link 1 — `stuck-bead-watch` (detect) — LANDED

Originally broken by an exec-path bug: file-not-found every 90 seconds. Fixed in
`f45aa15`/`e89cb45` (`/code-review` CLEAN).

A second, subtler bug was fixed in `76ccf37`: `main()` gated the priority grace window on
`first_seen_stuck` — the detector's *first-observation* time — double-counting grace against
wall-clock-since-detection, so days-old strands never escalated. Escalation now gates on
real idle age derived from `updated_at`; old strands escalate on the first detection pass.
29 tests pass.

*Verified:* `76ccf37` is present in `mathcity` main (it was recorded as "committed locally,
not pushed" on 2026-08-05 — it has since landed); `should_escalate` / `real_idle_age_seconds`
are present in `assets/scripts/stuck-bead-watch.py`; the order is live at `trigger =
"cooldown"`, `interval = "90s"`.

### Link 2 — the two rollups (classify → resling) — LANDED

`lost-bead-classification-rollup` and `lost-bead-upstream-repair-rollup` were both
`trigger = "manual"` and therefore **never auto-fired**. Both are now armed on cooldowns.

*Verified:* `orders/lost-bead-classification-rollup.toml` → `trigger = "cooldown"`,
`interval = "10m"`; `orders/lost-bead-upstream-repair-rollup.toml` → `trigger = "cooldown"`,
`interval = "30m"`. Both carry the in-file note *"Auto-armed on a cooldown (gsp-2bowrk): was
trigger=manual and NEVER fired."*

### Link 3 — `gt-rqaqu` auto-resling rule — APPROVED BUT NOT ARMED

`gt-rqaqu` is CLOSED (2026-07-31) with verdict *"APPROVED (generalized) with hard activation
gate … Not yet active pending gate."* Taylor attached a **hard activation gate** in its
strongest form; the rule does not go live until **both** conditions hold.

**Gate (a) — promotion must not silently disable future resurfacing.** Promoting a
fingerprint to auto-resling must not suppress future rollup-triggering or escalation for
that fingerprint, *verified against actual script behavior rather than assumed*.

> **Verified 2026-08-15: (a) HOLDS — structurally.** `assets/scripts/lost-bead-filter.py`
> carries **no promotion-state whatsoever** — no "already promoted" memory, no suppression
> list, no dedup-against-prior-runs. `rollup-downstream` is a pure stateless
> re-derivation over the classification corpus, keyed only on `--threshold`. It therefore
> *cannot* silently disable resurfacing, because there is no mechanism by which it could.
>
> This satisfies the gate's letter, but it is worth recording *why* it holds: (a) is met by
> the **absence** of a suppression feature, not by a designed resurfacing feature. The same
> statelessness has a live cost, recorded in §8 as the LEARN-leg gap.

**Gate (b) — substrate investigations resolved or ruled out.** The three open threads for
the lost/unclaimed-bead symptom class must each be resolved or explicitly excluded as the
cause of `empty_assignee_after_verified_sling`:

| Thread | Subject | Status (2026-08-15) |
|---|---|---|
| `gt-c4g63` | claim-order / FIFO fairness starvation | **OPEN** (P1) |
| `gt-zln3z` | session/workdir identity-stamping corruption | CLOSED 2026-08-14 — superseded by `gt-38ize4`; one strand split to a successor |
| `gt-gf0tk` | `gc.continuation_group` release-race | **OPEN** (P0) |

> **Verified 2026-08-15: (b) DOES NOT HOLD.** Two of three threads remain open, including a
> P0. **Link 3 is therefore still correctly gated OFF**, and no implementation should ship
> the generalized auto-resling rule live.

The gate exists because this fingerprint is the live symptom shape of the very substrate
bugs under investigation — during adjudication, that night's own `pr-pipeline` investigation
was cited as a concrete example of this exact failure shape fooling investigators for hours.
Arming the rule before (b) clears risks auto-resling beads whose real problem is a substrate
defect that resling will not fix.

### Link 4 — `orphan-sweep` (dead-agent reclaim, CORE order) — NOT LANDED

The core `orphan-sweep` order times out with a context-deadline-exceeded error, so
dead-agent reclaim is silently dead. The fix is an upstream PR against gascity core, tracked
on `gt-efrs7d`.

*Verified 2026-08-15:* `gt-efrs7d` is **OPEN** (P1), last updated 2026-08-04 — unchanged
since `gsp-2bowrk` was written. This link has not moved.

### Link 5 / meta — P6.1 fail-loud — PARTIAL

See §6. Script-level fail-loud has landed in the pack; core order-exec-failure escalation is
still bundled into `gt-efrs7d` and therefore still outstanding.

## 5. Architecture

Two detectors, one shared record contract, one shared rollup. The reuse is deliberate: a
second parallel reclaim pipeline was explicitly ruled out during design, on the grounds that
Taylor is *de-duplicating* overlapping reclaim mechanisms and a new pipeline would be a
regression (§7).

```
  class 1                         class 2
  stuck-bead-watch                tail-end-detector
  (dispatched-but-frozen)         (ready-but-never-dispatched)
  order: cooldown 90s             order: cooldown 15m
         │                                │
         │  {bead_id}.toml                │  {bead_id}.tail.toml
         └────────────┬───────────────────┘
                      ▼
        .beads/lost-bead-classifications/
        (lost-bead-classification.v1 records)
                      │
                      ▼
        lost-bead-classification-rollup     (cooldown 10m)
        lost-bead-upstream-repair-rollup    (cooldown 30m)
          group by lost_class + recommendation
                   + root_cause.class + fingerprint
          threshold ≥3  ──▶  downstream filter-rule candidate
                      │
                      ▼
              decision brief  ──▶  human adjudication
```

**The record contract is the integration seam.** Both detectors emit
`lost-bead-classification.v1` TOML into the same `.beads/lost-bead-classifications/` root,
validated by `lost-bead-filter.py`. Distinct fingerprints keep the two sources grouped
separately in the rollup, so a shared root does not mean conflated signal.

`tail-end-detector` fingerprints: `ready_idle_tail_superseded` (→ `close_moot`) and
`ready_idle_tail_resling` (→ `resling`); plus `ready_idle_tail_growing` for the heartbeat
(§6).

**Implementation detail for `tail-end-detector` — idle measure, the classification split,
batch caps, the exclusion filter, and its test strategy — is specified in
[`docs/superpowers/specs/2026-08-04-tail-end-detector-design.md`][ted-design]. Consult that
document; it is not reproduced here.** The only points restated above are the ones the
conservation invariant itself depends on: the class-2 definition, detector disjointness, and
the load-bearing batch cap.

## 6. P6.1 fail-loud — the cross-cutting meta-fix

**The requirement.** Any order exec that **fails** *or* **never fires** must **ESCALATE** —
event bead, mail, or health signal — never log-only.

This is the meta-fix because it is the reason the other four were expensive. Each of links
1–4 was an ordinary, fixable bug. What turned four fixable bugs into an *invisible systemic
failure* was that all four failed silently: the orders logged and moved on, nothing
escalated, and 213 strands accumulated before anyone ran `stuck-bead-watch` by hand and
noticed.

A detector that fails silently is worse than no detector, because it produces the false
belief that the class is covered. Under P6.1, silence is itself a defect.

**Status.** Script-level fail-loud has landed in the pack, implemented in `tail-end-detector`
as its Fork 4:

- every subprocess is time-bounded (30s); a hang produces a nonzero exit to stderr, not a
  silent stall;
- the actionable-tail count is persisted in `tail-heartbeat.json`, and if the count **grows**
  between runs — producers outpacing reclaim — a heartbeat event bead is emitted with
  fingerprint `ready_idle_tail_growing`;
- the tail count is printed **every run**, so tail size is never silent;
- any error exits nonzero rather than logging.

**Still outstanding:** core order-exec-failure handling — an order that fails or never fires
at the *gascity core* level still does not escalate. That is upstream work, bundled with
`gt-efrs7d` (link 4). Until it lands, P6.1 is enforced by the pack's own scripts but not by
the runtime that invokes them, which leaves the "never fires" half of the requirement
substantially uncovered: a script that is never executed cannot fail loudly on its own
behalf.

## 7. xkcd-927 — the consolidation target

Roughly **8+ overlapping strand/reclaim variants** currently exist:

1. `orphan-sweep`
2. `reclaim-stale-leases`
3. `order-tracking-sweep`
4. `stuck-bead-watch`
5. `lost-bead-classification-rollup`
6. `lost-bead-upstream-repair-rollup`
7. `strand-sweep`
8. `brief-producer-*`
9. `check-molecules` (STRANDED bucket)

These **should collapse into the single canonical loop** described in §1–§5. BART raised the
canonical-vs-redundant question that prompted this consolidation target.

**This document is the intended convergence point.** That status carries an obligation
attached to it: the correct response to a gap in the reclaim story is to **extend this loop**,
not to add a tenth variant. `tail-end-detector` is the model — it was built as a new *class-2
branch of the existing pipeline*, reusing the record contract and the existing rollup, rather
than as a parallel reclaim system. A parallel pipeline was surveyed during its design and
explicitly ruled out.

Consolidation itself is **not yet performed**. The list above is the inventory to be
collapsed, and the collapse remains open work (§8).

## 8. Open items

**`gsp-beo9sy` — real supersession detector.** Filed as the P1.17 named-workaround follow-up
to `tail-end-detector`'s original 30-day age-proxy supersession heuristic (age alone does not
prove supersession). Taylor added a hard requirement on 2026-08-05: real TDD coverage,
matching the existing detector's pattern.

> **Verified 2026-08-15 — the code has landed but the bead has not been closed.**
> `classify_bead` in `assets/scripts/tail-end-detector.py` now uses three real supersession
> signals — `parent_epic_closed`, `subsumed_by_closed_ref`, and title/description
> near-duplicate scored by Jaccard against a closed-or-strictly-newer bead, guarded by a
> similarity floor and a minimum meaningful-token count. `SUPERSEDE_AGE_DAYS` no longer
> appears in the file: **age alone no longer supersedes**, and no-signal beads fall through
> to `resling`. The test file carries 30 tests (up from the original 18). The design doc's
> Fork 3 section was updated in place on 2026-08-05 to record the supersession.
>
> `gsp-beo9sy` is nevertheless still **OPEN** (P2). This is bookkeeping drift, not missing
> work — but it means the bead list overstates what is outstanding, and the bead should be
> reconciled against the code before it is used to plan anything.

**Link 3 arming (`gt-rqaqu`).** Blocked on gate (b): `gt-c4g63` (P1) and `gt-gf0tk` (P0)
remain open. Correctly gated; no action beyond resolving those threads.

**Link 4 / core P6.1 (`gt-efrs7d`).** Open, unmoved since 2026-08-04. Carries both the
`orphan-sweep` timeout and core order-exec-failure escalation.

**Training-loop leg (c) — the IMPROVE wiring.** `brief-producer-failure → rollup →
brief-producer-repair` exists as a formula with **no consumer and no order**. Nothing drives
it, so producing formulas are not currently improved by the failures they cause. This is the
one leg of §3 that is entirely unwired.

**The LEARN-leg statelessness gap** *(observed 2026-08-15, not previously recorded)*.
Because `lost-bead-filter.py` holds no promotion-state (§4, gate (a)), the rollup cannot
distinguish a *new* occurrence of a fingerprint from one that has **already been
adjudicated**. It therefore re-derives already-decided candidates indefinitely.

Live instance: the fingerprint `empty_assignee_after_verified_sling` (212 beads) was
adjudicated **approve** on `gt-1f2781`, closed 2026-08-05. On 2026-08-15 the
`lost-bead-classification-rollup` formula re-derived the identical 212-bead candidate row
**four times** — each run burning an operator session to reach the same
"already adjudicated, file nothing" verdict. The classification corpus is frozen (all 212
records carry `observed_at = 2026-08-04T22:46:55Z`), so every run regenerates a byte-identical
candidate file.

Note also that this single fingerprint carries **two** approving decisions — `gt-rqaqu`
(2026-07-31, generalized, gated) and `gt-1f2781` (2026-08-05) — which is itself a small
instance of the §7 problem.

This gap is *adjacent to but distinct from* gate (a): the same statelessness that guarantees
resurfacing also guarantees duplicate adjudication. Closing it requires the rollup to consult
a terminal-state signal (e.g. an existing closed decision bead for the fingerprint) before
emitting a candidate. **That is a design change, and is recorded here as an open item rather
than proposed as a decision** — it needs adjudication, not a unilateral fix.

**Consolidation (§7).** The 9-item inventory has not been collapsed. Unscheduled.

---

## References

| Bead / doc | Role |
|---|---|
| `gsp-2bowrk` | **Canonical source** — the "reclaim is silently dead" record + 4-link fix checklist (P0, OPEN) |
| `gsp-beo9sy` | Named-workaround follow-up — real supersession detector (P2, OPEN; code landed, see §8) |
| `gsp-m43go1` | The bead commissioning this document |
| `gt-rqaqu` | The LEARN-leg auto-resling rule + its hard activation gate (CLOSED, approved-not-armed) |
| `gt-1f2781` | Approve verdict on `empty_assignee_after_verified_sling` (CLOSED 2026-08-05) |
| `gt-efrs7d` | Link 4 — `orphan-sweep` timeout + core P6.1 escalation (P1, OPEN) |
| `gt-c4g63`, `gt-gf0tk` | Open substrate threads holding gate (b) shut |
| [`2026-08-04-tail-end-detector-design.md`][ted-design] | Class-2 detector implementation spec — **linked, not duplicated** |

[ted-design]: https://github.com/tdupu/gascity-packs/blob/main/docs/superpowers/specs/2026-08-04-tail-end-detector-design.md
