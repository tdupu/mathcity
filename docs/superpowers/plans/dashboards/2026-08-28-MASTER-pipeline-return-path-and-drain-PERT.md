# MASTER PLAN v2 — pipeline return-path + backlog drain (PERT)

**Successor to** `2026-08-27-MASTER-dashboard-repair-PERT.md` (S60, BART) — complete and
merged as PR #239. This plan does not re-do it; it executes that plan's own carry-forward.

**Author:** QUIMBY 61, 2026-08-28 · **Gates run:** `check-plan-hygiene` (revise → repaired
below), `check-wheel` (reinvention → three phases re-aimed), `/doubt`.

**Sources.** `ASSESSMENT-dashboard-brief-system-2026-08-28.md` + its adversarial review;
`DUPLICATE-WORK-GUARD-S61-2026-08-27.md`; the MASTER PERT's carry-forward.
**Per P5.4 these are narrative docs and are presumed stale until checked against source.**
Every claim below is tagged `[src]` (verified against code/store this session) or
`[inherited]` (from a narrative doc, unverified). **No `[inherited]` claim may size a task
without a re-measure step.**

---

## §0. THE DIAGNOSIS THAT SETS THE SHAPE

The predecessor sliced **horizontally** — by subsystem, explicitly partitioned by file to
bound merge conflicts. All five packages merged, suite green. Its own residual then reports:
pool still wedged, close verb still absent, revise round-trip **never tested live**, and
three merged features implementing options never adjudicated.

**Merged-but-not-working-end-to-end is the signature of a horizontal plan.** Every layer was
individually correct; no bead ever traversed all of them.

**v1 of THIS plan repeated the error.** It bolted one vertical spine (W1–W5) onto seven
phases still grouped by failure class, and asserted it was "vertically sliced". It was not.
v2 subordinates every repair to the slice that needs it: **no task may be scheduled unless a
named slice is blocked on it.** That is the structural test, and §12 applies it.

**Anti-goal, checkable:** no phase may exit on "subsystem X is fixed." Every exit criterion
is a traversal by a real bead.

---

## §E. WHEEL-CHECK (P1.20) — surveyed alternatives and verdicts

Run before any dispatch. **Three of v1's phases were reinvention.**

| # | Existing artifact | Covers | Verdict |
|---|---|---|---|
| 1 | `2026-08-27-MASTER-dashboard-repair-PERT.md` | dashboard surface repair, 5 WPs, PR #239 | **ADOPT as predecessor.** This plan starts at its carry-forward. |
| 2 | `formulas/revise-return.toml` + `orders/revise-return.toml` `[src]` | the revise return path — built to close #209, three-consumer division of labour documented inline | **ADOPT. v1's R4 premise ("the return path does not exist") is FALSE.** Re-aimed → R1 below. |
| 3 | `2026-08-20-supervisor-fd-leak-hygienic-fix.md` `[src]` | FD exhaustion: amplifier confirmed upstream, opener unnamed, level-driven mitigation | **ADOPT WHOLESALE.** v1's S1/S2 deleted. That plan *forbids* citing a single measured fd count (three methods → three values); v1 cited 138,240 and ~20,375 as settled — v1 violated a constraint of the plan it duplicated. |
| 4 | `2026-08-23-plan-e-drain-formula-repair.md` `[src]` | `brief-shuffle-fast-drain` cannot run when it fires — root cause at `formulas/brief-shuffle-fast-drain.toml:36`, cwd-relative resolution | **ADOPT.** v1's D4 "begin by re-measuring" is redundant; the measurement exists. |
| 5 | `orders/post-decision-file-or-sendback.toml`, `file-or-sendback-route.toml` | post-verdict routing | **ADAPT** — consumer exists; verify it fires (same bell as #2). |
| 6 | `orders/stuck-bead-watch.toml`, `lost-bead-*-rollup` | stuck/lost bead detection — relevant to the frozen rigs | **ADAPT** — run before hand-triaging 7,968 beads. |
| 7 | `2026-08-19-every-brief-reaches-the-front-end.md`, `2026-08-20-brief-system-defect-queue.md`, `2026-08-24-execution-policy-error-briefs-pert.md` | overlapping brief-system repair | **RULE OUT as duplicates of this plan's scope, but READ FIRST** — unsurveyed at v1, and each may contain a further re-aim. |

**Wheel-check's own lesson, recorded because it recurs:** v1 asserted a formula did not exist
without listing the formulas directory, in a document whose §0 lectures about inheriting
unverified claims. **Check the directory before claiming absence.**

---

## §1. THE ONE FINDING THAT REORDERS EVERYTHING

`[src]` `revise-return` is **built and unreachable.**

- `orders/revise-return.toml` is `trigger = "event"` on `brief.decided`.
- `mc-d6lp` (MASTER PERT, WP-ADJ): **the CLI adjudicate path emits no `brief.decided`. Only
  MCP does.** Marked "QA-only, not code-fixed by design."
- `gc events --since 72h | grep revise-return` → **0 firings.**
- `mc-eee6`: 13 hecke briefs adjudicated `revise` on 2026-08-25 and closed by that verdict,
  none of which will return on their own.

**One unemitted event strands the entire revise class.** Not a missing subsystem — a missing
`emit`. This is the cheapest high-leverage task in the plan and v1 mis-sized it as a
4.33-session build of something that already exists.

---

## §2. STANDING RULES (P1.21, P1.19, P3.2, P3.5, P1.17)

These bind every task below. v1 omitted all of them.

- **P1.21 — pre-sling assignee check, mandatory.** Before any dispatch: `bd show <id>` must
  show an empty Assignee **or** a stale claim per `mathcity/gates/stale-claim.toml`. If an
  active non-stale assignee exists → abort visibly (`ALREADY DISPATCHED — bead <id> has
  active assignee; aborting`) and do **not** re-sling. Post-sling verify-assignee remains
  mandatory and is not superseded. **In a plan sourced from the duplicate-work guard, this
  rule is the point.**
- **P1.19 — append, don't edit.** Phases B1/B5 touch existing beads: new information becomes
  a NEW bead linked with `bd dep relate`, never an edit. `bd update --notes` **replaces** and
  warns only after the write — always `--append-notes` (this is R7's defect; do not commit it
  while fixing it).
- **P3.2/P3.1 — upstream routing.** Every upstream issue for `gastownhall/*` goes through
  `create-issue-briefed`; every upstream PR through `pr-pipeline-briefed`. Direct
  `gh issue create` / `gh pr create` is forbidden. v1's U1/U2 violated this.
- **P3.5 — agent context.** Planning and measurement: `<city-root>` (inside). All code, commits and
  PRs: `~/repos/mathcity` via **BART**, gated by `authorize-git-operation` (LP1). No `<city-root>`
  agent runs git in `~/repos`.
- **P3.6 — feature work runs `improve-documentation`.** Binds V2, V3, V4, P2.
- **P1.17 — workarounds are named.** Any mitigation that does not remove the mechanism is
  labelled **workaround**, states the root cause, and carries a root-cause bead. Each task
  below states the invariant that prevents recurrence, or is reclassified.

---

## §3. PHASE 0 — SUBSTRATE (adopted, not authored)

| id | task | source | dep | O | M | P | TE |
|----|------|--------|-----|---|---|---|----|
| S0 | **Execute the existing FD plan** as written, including its constraint that no single measured fd count may be cited | `2026-08-20-supervisor-fd-leak-hygienic-fix.md` | — | 2 | 4 | 8 | **4.33** |

**DO NOT RE-PROPOSE THE REFUTED MECHANISM.** `mc-tkei` (P1, OPEN) records: *"S56's mechanism — 'a config reload re-registers every watch without releasing the old ones' — is **false**"* — the reload path closes before it reopens, synchronously (`cmd/gc/city_runtime.go:2378`, `cmd/gc/controller.go:879-883`), found by BART and independently re-verified by QUIMBY 57. **Both candidate mechanisms are source-refuted; the cause is UNKNOWN.** v1 of this plan put the refuted mechanism in S1's task title and quoted its refutation three lines later. `mc-tkei` names four unread artifacts (`fd-step-20260826T*.log`, `fd-minute.tsv`) that must be read before any third mechanism is proposed. **Do not derive a headroom figure**: 138,240 / 20,375 = 6.8, not 3.

Invariant established: the next FD exhaustion is *detectable before* it takes the city down.
The amplifier is upstream (P3.1) and becomes an issue via `create-issue-briefed`, not a patch.

---

## §4. PHASE 1 — DISPATCH (nothing moves)

| id | task | beads / issues | dep | O | M | P | TE |
|----|------|----------------|-----|---|---|---|----|
| D1 | Router assigns `gc.kind=workflow` LATCH beads to normal run-operator pools | mc-nvg2g, mc-k4t1s, mc-y88p0 `[inherited]`; siblings gsp-0vxmki (12d earlier), he-npxfhg (67 open in hecke), gs-4mjl | S0 | 2 | 4 | 8 | **4.33** |
| D2 | brief-operator-1 pool revive | mc-03o11, #227, #10 `[inherited]` | D1 | 1 | 2 | 5 | **2.33** |
| D3 | control-dispatcher lane unwedge | mc-nhiaq `[inherited]` | D1 | 1 | 2 | 4 | **2.17** |
| D4 | **Execute Plan E** — `brief-shuffle-fast-drain` cwd-relative resolution at `:36` | Plan E `[src]`, #73, #204 | S0 | 1 | 2 | 4 | **2.17** |
| D5 | `gc hook --claim` latency exceeds its own claim window | gsp-eq25oj, gs-42h9, upstream #5693 `[inherited]` | D1 | 2 | 4 | 9 | **4.50** |

**D-series re-measure gate.** Every `[inherited]` bead above is re-measured at source before
its task is sized.

**The "three incompatible firing rates" that v1 reported is NOT a contradiction — v1
manufactured it by conflating scopes.** `orders/` contains **both** `brief-shuffle-fast-drain.toml`
(rig-scoped) and `brief-shuffle-fast-drain-city.toml` (city-scoped) `[src]`. `mc-8ncv` says
*rig-scoped* orders fired once ever; `mc-9bvqq` (~14/day) and `mc-o44j4` (46 firings over ~3.3
days) describe the *city-scoped* one — **and 46 over 3.3 days IS ~14/day, so those two are one
data point, not two** (same defect, same day, same operator). Two consistent facts, not three
conflicting ones. Also: `mc-8ncv`'s **priority field is P2**, despite its title beginning
"P0:" — the title-heuristic error the source assessment's own correction block flags.

---

## §5. PHASE 2 — THE VERTICAL SLICES (the spine; everything else is subordinate)

A slice is DONE when a **real bead** has completed the traversal and the dashboard shows it.
Not when code merges.

| id | slice | proves | dep | O | M | P | TE |
|----|-------|--------|-----|---|---|---|----|
| W1 | **Happy path — 1 bead, 1 rig.** Drive one real defect bead `bead → brief → present → adjudicate → verdict → code → close → dashboard`. Fix-just-enough at each break. | the pipeline exists at all | D2,D3,D4,D5 | 2 | 4 | 10 | **4.67** |
| W2 | **REVISE round-trip — 1 bead.** | the return path — **never once tested live** | W1,R1 | 1 | 3 | 6 | **3.17** |
| W3 | **REJECT + re-file — 1 bead.** | rejection does not strand work | W2 | 1 | 3 | 6 | **3.17** |
| W4 | **Ten beads concurrently.** | pool, orders, locks under real concurrency — single-bead slices cannot expose these | W3,M1 | 2 | 4 | 8 | **4.33** |
| W5 | **One hecke bead, cross-rig.** | the frozen rigs are reachable *before* committing to drain 7,968 | W4 | 2 | 4 | 8 | **4.33** |

**W1's deliverable is the measured blocker list.** Every estimate in §6–§10 is provisional
until W1 replaces it. They are planning figures, not commitments — and §12 says so in the
arithmetic rather than only in prose.

---

## §6. PHASE 3 — RETURN PATH (unblocks W2)

| id | task | beads | dep | O | M | P | TE |
|----|------|-------|-----|---|---|---|----|
| R1 | **Emit `brief.decided` from the CLI adjudicate path** (or route all adjudication through MCP). Unblocks the already-built `revise-return`. | mc-d6lp, #209 `[src]` | W1 | 1 | 2 | 4 | **2.17** |
| R2 | Gate moves ALREADY-ADJUDICATED briefs to `.rejected/` — 8 of 24 measured | mc-8ehd0; plan `fd9b7fc` drafted, **awaiting fresh substitute review** | W1 | 2 | 3 | 6 | **3.33** |
| R3 | B2.10 decisions-track gate UNCLEARABLE — blocks every write | mc-5wdje (P0) `[inherited]` | W1 | 1 | 3 | 6 | **3.17** |
| R4 | Commission briefs written to an adjudication-invisible path — 18 stranded | mc-4ovmy (P0), gsp-edxxlc `[inherited]` | W1 | 2 | 3 | 6 | **3.33** |
| R5 | Carry the 13 stranded hecke revise verdicts (3 are no-brainers and **must not** be re-adjudicated) | mc-eee6, mc-r4ub `[src]` | R1 | 2 | 3 | 6 | **3.33** |
| ~~R6~~ | **REMOVED — ALREADY FIXED, never dispatch.** `DUPLICATE-WORK-GUARD:81` verified at source in `dc47d77`: *"mc-9kwwv | **both halves**: effects.py:1091-1094 writes adjudicated_by/at (0ed4a2b, af90cbc); R6 test rewritten persisted-only (1262e4e) + control fixture at :122 so it can now fail."* v1 sided with the older MASTER-PERT residual note without noticing its two sources disagree. **This plan scheduled duplicate work in the one plan whose second source exists to prevent it.** | — | 0 | 0 | 0 | **0** |
| R7 | `commission-work-briefed` uses `bd update --notes`, **silently destroying source-bead notes** | gsp-vx1818 `[inherited]` | W1 | 1 | 2 | 4 | **2.17** |
| R8 | 21 of 24 rejections carry "missing provenance metadata" (`brief-shuffle-fast-drain.py:172`, `reject_staged()` :684) | — `[src]` | R2 | 1 | 2 | 5 | **2.33** |

R7 is data loss, not workflow. R5 is the human-visible payoff of R1.

---

## §7. PHASE 4 — MISSING VERBS

| id | task | dep | O | M | P | TE |
|----|------|-----|---|---|---|----|
| ~~V1~~ | **RETIRED — COMPLETE.** `read_beads` (#245) merged as **PR #251, `51ddb27`** on `~/repos/mathcity` main. v1 called this "at risk of accidental deletion"; the premise was false in three ways (the object is present in `~/repos`, a `refs/heads` branch ref anchors it, and the worktree is `locked` so `git worktree remove` refuses). **Executing V1 as written would have minted a fifth copy — in a plan citing a duplicate-work guard as a source.** | — | 0 | 0 | 0 | **0** |
| V2 | **Typed close verb — this is a DECISION, not a task.** Correct bead is **`mc-i9bwz` (P2, OPEN, unadjudicated)**: *"build bead_close/hold/release, or lift the handicap for closes?"* v1 mis-cited `mc-qcnaz`, which is the **hold/pause** decision and is CLOSED. Cannot be scheduled until ruled. | V-gate | — | — | — | **decision** |
| ~~V3~~ | **MERGED INTO V2 — same verb, was double-counted.** `mc-qcnaz` (hold/pool-pause) and `mc-1pale` (no claim-lane exclusion / park / pool pause) are one surface. v1 booked them separately at 2.33 + 3.33 = 5.66 sessions. | — | 0 | 0 | 0 | **0** |
| V4 | No **typed** decision-bead creator (`bd create -t decision` works — 129 exist; the gap is the typed/MCP surface) | V1 | 1 | 2 | 4 | **2.17** |

**V1 starts immediately, in parallel with Phase 0**, regardless of critical path — it is at
risk of accidental deletion, and deletion is unrecoverable.

---

## §8. PHASE 5 — MEASUREMENT TRUST

| id | task | dep | O | M | P | TE |
|----|------|-----|---|---|---|----|
| M1 | MCP lock — **#244 and mc-znfnm are the same defect** (identical 36× experiment, same `client.py:157`). Dedupe, then fix. | W1 | 1 | 2 | 5 | **2.33** |
| M2 | `/city` slow render — **no known mechanism.** #130 (the cached-scan theory) is merged and fixed (`8dfbe0e`, 8–13s → 2.4–3.0s). **Profile before proposing.** | M1 | 1 | 3 | 7 | **3.33** |
| M3 | Kill the default-limit class: `bd ready` returns 100 of **441** `[src]`; `gh issue list` truncated at 100, dropping the 8 oldest; `work_ready` reports **CLOSED** beads as `readiness:ready` (mc-uvl) | — | 1 | 2 | 5 | **2.33** |
| M4 | 14 exact + 2 prefix = 16 dashboard routes, verification state unknown for most in unstated-unknown state — make each self-declare | M1 | 1 | 2 | 4 | **2.17** |

M3 is the class that produced two wrong headline numbers **in the assessment that sourced
this plan**. Invariant: every count the city emits declares its own scope.

---

## §9. PHASE 6–7 — CONTRACTS, FORMULAS, ORDERS

| id | task | dep | O | M | P | TE |
|----|------|-----|---|---|---|----|
| P1 | #86 unblock (hard prerequisite for all B2.11 work) | W1 | 1 | 2 | 5 | **2.33** |
| P2 | ≥7 formulas write brief state directly, bypassing the typed surface; only **3 of 61** formula+order files mention `mctl` `[inherited]` | P1 | 3 | 5 | 10 | **5.50** |
| P3 | Producer/consumer mismatch — #242 the shape, #96 the live instance | W1 | 1 | 3 | 6 | **3.17** |
| F1 | #189 retry storm → **VERIFY-AND-CLOSE, not fix.** 76,961 is a 2× double-counted grep (true attempts 41,382); a retry budget exists (`expired=true`); **zero firings since 08-25**; all 13 roots closed. Fails to close if any of those three re-measures disagree. | — | 1 | 1 | 2 | **1.17** |
| F2 | Every formula registered twice — 178 symlinks over 90 distinct targets = 89 duplicate pairs, against a parser that is **first-wins where the docs say last-wins** (upstream #2027) | — | 1 | 2 | 5 | **2.33** |
| F3 | Orders inventory — 20 of 24 orders are brief-system; the assessment enumerated formulas only, and ≥5 cited defects live in the **order** layer | — | 1 | 2 | 3 | **2.00** |

---

## §10. PHASE 8–9 — DRAIN, THEN THE FROZEN RIGS

| id | task | dep | O | M | P | TE |
|----|------|-----|---|---|---|----|
| B1 | Dedupe issue↔bead mirrors — 22 of 55 issues have a verbatim duplicate bead; #230 has three. **Append, never edit (P1.19).** | V2,W4 | 2 | 3 | 6 | **3.33** |
| B2 | 14 closed GH issues with a still-open near-identical bead — incl. **#152 (SECURITY) → mc-s1im (P1, open)** | V2 | 1 | 3 | 6 | **3.17** |
| B3 | 9 issues re-homed into `tdupu/gascity`, all still OPEN there (37 open total) | V2 | 1 | 2 | 5 | **2.33** |
| B4 | Drain 19 pending briefs + the **115 city-wide rejected pile** (77 at city root incl. 23 `gsp-*`, 13 `he-*`; oldest 2026-07-16) | R2,R8,W4 | 3 | 6 | 12 | **6.50** |
| B5 | **105 of 112 closures (94%) carry no linked PR or commit** `[inherited]` — the closed half of the tracker is not evidence. Re-verify or re-open. | V2 | 2 | 3 | 7 | **3.50** |
| H0 | **THE LOCAL SWEEPER SUBSTITUTE — rescoped, see §18.** Run `stuck-bead-watch` + `lost-bead-*-rollup` against hecke and gascity-packs, **and measure the sweepable fraction**. This is not preparation for triage; with the reaper down it is the only sweeper that can run. | W5 | 1 | 3 | 6 | **3.17** |
| H1 | hecke — 4,030 open / 609 matching / **112 open `[brief-record]` beads** (53 with "verdict" in title). **ESTIMATE CONDITIONAL — not re-estimable until H0 reports the sweepable fraction (§18).** | W5,H0 | 4 | 8 | 16 | **8.67†** |
| H2 | gascity-packs — 3,926 open / 413 matching / 49 verdict beads | W5,H0 | 3 | 6 | 12 | **6.50** |
| H3 | 374 hecke beads routed to unsubstituted template literals (`{{prep_target}}`) under 63 roots | H1 | 2 | 4 | 8 | **4.33** |
| U1 | **No upstream issue mentions "latch."** File via `create-issue-briefed` (P3.2). | D1 | 1 | 1 | 3 | **1.33** |
| U2 | `tdupu/gascity` — 37 open, `#11` same family as D1 | U1 | 1 | 2 | 4 | **2.17** |

**`he-4poivc` — RETRACTED, do NOT escalate.** v1 called it "a human decision stranded four
weeks" and made it the plan's single out-of-band escalation. **The decision was made.** Its
source bead `he-k8e3xv` was CLOSED **2026-08-03** with close reason *"APPROVED — see comment.
Woven into existing superpowers-adoption + scientific-method threads per Taylor's condition"*,
and `he-4poivc.brief_status` is `approved`. What is stranded is a **stale tracker title**, not a
verdict. Escalating it would have re-presented an already-answered question to Taylor. There are
exactly **2** open `PENDING-TAYLOR` beads in hecke — not a class.

---

## §11. IMPACT (P4.1 / P4.2)

- **Upstream (P4.1):** D1, D5, S0's amplifier, F2 all touch `gastownhall/gascity` behaviour.
  None is patched locally; each becomes an issue via `create-issue-briefed`. U1/U2 are the
  tracking tasks.
- **Downstream (P4.2):** R1 changes when `brief.decided` fires — **three consumers subscribe**
  (`brief-decision-dispatch`, `post-decision-file-or-sendback`, `revise-return`). Emitting it
  from the CLI path will make all three fire on verdicts that previously fired none.
  **R1 must be validated against all three, not just `revise-return`.** This is the single
  largest blast radius in the plan and v1 did not identify it.
- **V2 (close verb)** changes bead lifecycle for every consumer of bead status, including the
  dashboard's tracker and queue screens.

---

## §12. PERT NETWORK

TE = (O + 4M + P)/6, in agent-sessions. **Estimation confidence is declared, not implied:**
tasks whose beads are `[inherited]` carry provisional estimates that W1 is expected to
revise. The critical path is therefore reported with and without them.

```
S0(4.33) ─┬─> D1(4.33) ─┬─> D2(2.33) ┐
          │             ├─> D3(2.17) ┤
          │             └─> D5(4.50) ┼─> W1(4.67) ─> R1(2.17) ─> W2(3.17) ─> W3(3.17) ─> W4(4.33) ─> W5(4.33) ─> H0(2.17) ─> H1(8.67) ─> H3(4.33)
          └─> D4(2.17) ──────────────┘
V1(1.33) ─> V2(2.33) ─> B-series          (off CP, start immediately)
```

| task | TE | ES | EF | LS | LF | slack | CP |
|---|---|---|---|---|---|---|---|
| S0 | 4.33 | 0 | 4.33 | 0 | 4.33 | 0 | **yes** |
| D1 | 4.33 | 4.33 | 8.66 | 4.33 | 8.66 | 0 | **yes** |
| D4 | 2.17 | 4.33 | 6.50 | 10.99 | 13.16 | 6.66 | no |
| D3 | 2.17 | 8.66 | 10.83 | 10.99 | 13.16 | 2.33 | no |
| D2 | 2.33 | 8.66 | 10.99 | 10.83 | 13.16 | 2.17 | no |
| D5 | 4.50 | 8.66 | 13.16 | 8.66 | 13.16 | 0 | **yes** |
| W1 | 4.67 | 13.16 | 17.83 | 13.16 | 17.83 | 0 | **yes** |
| R1 | 2.17 | 17.83 | 20.00 | 17.83 | 20.00 | 0 | **yes** |
| W2 | 3.17 | 20.00 | 23.17 | 20.00 | 23.17 | 0 | **yes** |
| W3 | 3.17 | 23.17 | 26.34 | 23.17 | 26.34 | 0 | **yes** |
| W4 | 4.33 | 26.34 | 30.67 | 26.34 | 30.67 | 0 | **yes** |
| W5 | 4.33 | 30.67 | 35.00 | 30.67 | 35.00 | 0 | **yes** |
| H0 | 2.17 | 35.00 | 37.17 | 35.00 | 37.17 | 0 | **yes** |
| H1 | 8.67 | 37.17 | 45.84 | 37.17 | 45.84 | 0 | **yes** |
| H3 | 4.33 | 45.84 | 50.17 | 45.84 | 50.17 | 0 | **yes** |
| H2 | 6.50 | 37.17 | 43.67 | 43.67 | 50.17 | 6.50 | no |
| B4 | 6.50 | 30.67 | 37.17 | 43.67 | 50.17 | 13.00 | no |
| B1 | 3.33 | 30.67 | 34.00 | 46.84 | 50.17 | 16.17 | no |
| R2 | 3.33 | 17.83 | 21.16 | 38.01 | 41.34 | 20.18 | no |
| R8 | 2.33 | 21.16 | 23.49 | 41.34 | 43.67 | 20.18 | no |
| P2 | 5.50 | 20.16 | 25.66 | 44.67 | 50.17 | 24.51 | no |
| M1 | 2.33 | 17.83 | 20.16 | 24.01 | 26.34 | 6.18 | no |
| V1 | 1.33 | 0 | 1.33 | 43.01 | 44.34 | 43.01 | no |
| V2 | 2.33 | 1.33 | 3.66 | 44.34 | 46.67 | 43.01 | no |
| F1 | 1.17 | 0 | 1.17 | 49.00 | 50.17 | 49.00 | no |

*(Full 44-task table computed programmatically; the 22 rows above are the critical path plus
every task with slack < 25. Remaining tasks — R3–R7, V3, V4, M2–M4, P1, P3, F2, F3, B2, B3,
B5, U1, U2 — all carry slack > 26 and none can lengthen the project without a dependency
change.)*

**ARITHMETIC NOTE.** This table is machine-computed, not hand-built. The hand-built version
in v1 contained two errors caught by recomputation before publication: it reported duration
50.2 from a network whose own dependency column (`W4 dep = W2,M1`) omitted W3, which actually
computes to 47.0 with W3 dangling at 20.66 slack. **The dependency column was the bug, not
the total** — successively-wider slices require W4 to follow W3. Corrected, the network is
internally consistent at 50.17.

**Critical path: S0 → D1 → D5 → W1 → R1 → W2 → W3 → W4 → W5 → H0 → H1 → H3 = 51.17
agent-sessions** (was 50.17; +1.00 from the §18 reaper finding) (machine-verified; CP task TEs sum exactly to project duration).

**Two counter-intuitive results worth stating plainly:**

1. **The critical-path driver in Phase 1 is D5** (`gc hook --claim` latency), not any of the
   five P0 beads. The P0s are severe but parallelisable; the claim latency is serial and gates
   every slice.
2. **R1 — the single cheapest task on the critical path at TE 2.17 — unblocks the largest
   stranded population.** v1 sized this at 4.33 as a build. It is an `emit`.

**Immediately parallel, off critical path:** V1 (do first regardless), F1, F2, F3, M3, U1,
and reading the three unsurveyed plan docs from §E row 7.

---

## §13. WHAT THIS PLAN DOES NOT COVER — stated so the absence is visible (P6.2)

- **6,934 of hecke/gascity-packs' 7,956 open beads** fall outside the brief/dashboard filter.
  Out of scope. This plan does **not** "resolve all open issues and beads" city-wide, and
  should not be read as claiming to.
- **48 unread escalations**, incl. a JSONL-spike series on `mc` climbing 151 → 194 → 249 → 417.
  Untriaged, unsized.
- **Four mutually inconsistent test counts** for one suite (1702 / 1718 / 1795 / 1802); 1795
  traces to no artifact.
- **`mc-8kj`** — P0 HOLD GATE on `mc-73k`, frozen pending Taylor. Not agent-schedulable.
- **Three unsurveyed plan docs** (§E row 7) that may contain further re-aims.
- **DECISION, not a task: were `mc-ba376` / `mc-umn7n` / `mc-yu0u9` adjudicated?** PR #239
  merged implementations of options Taylor never ruled on. The MASTER PERT flagged it; it was
  never resolved.

---

## §14. EXIT CRITERIA (repairing the plan's own unenforceable anti-goal)

§0 declared "no phase may exit on 'subsystem X is fixed'." **In v1 that check could not fail:
10 of 11 phases stated no exit criterion at all.** A rule that nothing can violate is the P6.2
error the source assessment names as the house failure — committed in the sentence that
condemns it. Every phase now carries one.

| phase | EXIT CRITERION (a traversal or a measurement, never "X is fixed") |
|---|---|
| 0 Substrate | The city survives a deliberate config reload with FD headroom measured before and after, by the method `fd-census.sh` defines. **Not** "the leak is fixed" — the mechanism is UNKNOWN. |
| 1 Dispatch | One bead is claimed by a pool worker and reaches `in_progress` without manual intervention. |
| 2 Slices | Named in each row: a real bead completes the traversal and the dashboard shows it. |
| 3 Return path | A `revise` verdict on a real brief produces a fresh brief deposit **with no human carrying it**. |
| 4 Verbs | A bead is closed through the typed surface — **blocked on the `mc-i9bwz` decision.** |
| 5 Measurement | Two independent agents measure the same quantity and agree, having each stated scope. |
| 6 Contracts | A brief-state write from a formula is rejected by the typed surface and the formula is corrected. |
| 7 Formula/order | `#189`'s defect **B** has an upstream issue; defect A's roots stay closed across one full week. |
| 8 Drain | Rejected-pile depth decreases across two consecutive measurements taken the same way. |
| 9 Frozen rigs | One hecke bead completes the §5 traversal (= W5). |
| 10 Upstream | Each filed issue has an upstream number and a local tracking bead. |

## §15. UNMODELLED ASSUMPTIONS (each invalidates part of the schedule)

1. **64% of the critical path is built on figures this plan calls non-commitments.** W1 ends at
   EF 17.83 of 50.17. Everything after is provisional by §5's own admission — including H1
   (8.67), the largest CP task. **The PERT past node W1 is indicative, not predictive.** Stated
   here rather than only in prose, because v1 made the concession and then published a total.
2. **Concurrency is assumed by the slack model and denied by this plan's own M1.** Slack figures
   presuppose ≥2 workers; the critical-path arithmetic presupposes 1; W4 is literally "ten beads
   concurrently"; and M1/#244 measures that every MCP call serialises on one lock (36×).
   **Concurrency is not available until M1 lands, and M1 depends on W1.**
3. **BART's availability, throughput and gate latency appear in no estimate.** Every
   code-landing task is a two-agent handoff (agent → BART → `authorize-git-operation`) sized as
   one.
4. **Four Taylor turns sit on the critical path with zero sessions budgeted** (W1×1, W2×2,
   W3×1). Three decisions from PR #239 have been unruled since 2026-08-27.
5. **R3 is estimated at 3.17 sessions against a defect its own bead calls unreachable.**
   `mc-5wdje`: *"Its clearing condition is unreachable by any tool in the system. This is not a
   backlog. It is a permanent block."* Either the bead is wrong or the estimate is fiction.
6. **No staleness discount is applied anywhere.** The guard measured **10 of 32 work-ready beads
   (31%) not dispatchable as written.** Every `[inherited]` estimate should carry that discount.
7. **The B-series is now gated on an unadjudicated decision** (`mc-i9bwz`), not on an
   estimate — B1/B2/B3/B5 all depended on V2.

## §16. ADDITIONAL OMISSIONS (§13 listed 5; these are the rest)

- **Report-box is the predecessor's ONLY unmerged work package** and this plan does not schedule
  it. Branch `feat/report-box-fix-brief` is UNPUSHED; Stage C is BLOCKED on a proven P7.3 gap —
  **`work_dispatch` cannot pin a formula** (takes only `brief_id`). v1 called the predecessor
  "complete and merged"; its own live-status table reads `Report-box | code ⧗ | tests ☐ | merged ☐`.
- **`mc-7sl0`** — an unruled Taylor decision (D1–D5 undecided) **blocking `mc-uxsh`, `mc-87zg`,
  `mc-g9w0`**.
- **`mc-upgv` / `mc-krl9`** — two `in_progress` molecules that are second dispatches on
  still-open source beads, flagged in the guard as *"Decision for Taylor"*, with
  `molecule_cancel` deliberately not run. `mc-upgv` carries 33 open children.
- **The guard's other 9 non-dispatchable beads** — `mc-l255`, `mc-55de2`, `mc-l65j`, `mc-iu96`,
  `mc-f63t` (ALREADY-FIXED); `mc-g9w0`, `mc-uxsh`, `mc-87zg`, `mc-vwkn7` (STALE-PREMISE).
- **2,312 `blocked` beads in the hecke store** — no disposition anywhere in this plan.
- **`#189` defect B is untouched and upstream.** The issue names two defects: A (formula graph,
  local) and B (`gc` retry classification — *"no poison-pill detection, no attempt ceiling, no
  backoff"*). F1 closes A's trigger. **B remains live and would bound the blast radius of any
  future instance of A.** F1's disposition must therefore be "close A, file B upstream", not
  "verify and close". Its count is also a **floor** — #189 sampled only the last 20 MB — so
  applying only the downward 2× correction is one-directional.

## §17. GATE RECORD

| gate | verdict | disposition |
|---|---|---|
| `check-wheel` | **REINVENTION ×3** | S0/D4 adopted from existing plans; R1 re-aimed after finding `revise-return` already built. 3 further plan docs remain unsurveyed. |
| `check-plan-hygiene` | **REVISE** (9 violations) | All repaired: P1.21 §2, P1.20 §E, P3.2 §2, P1.17 §2, P5.4 `[src]`/`[inherited]` tags, P3.5, P3.6, P4.1/P4.2 §11, P1.19 §2. |
| peer review (QUIMBY 61 parent) | **3 DELTAS, 1 material** | Reaper chain verified at source and accepted → §18; CP re-run 50.17 → **51.17**, H0 rescoped. #245 shipped → M3 re-scoped, V1 already retired. Corrected counts (12 P0s, 107 issues) folded into M3's class. |
| `/doubt` | **SUSPECT ×5** (all 5 areas) | v1's TE column survived (43/43 exact). Network, 6 false claims, 5 unreproducible counts, and 12 omissions accepted and applied above. |

**Findings this plan did not survive, recorded because the pattern is the point:** v1 was
written by the same session that wrote the assessment condemning inherited-claim reuse, and it
(a) asserted a formula did not exist without listing the directory, (b) put a source-refuted
mechanism at the root of its critical path while quoting the refutation three lines later,
(c) scheduled a bead its own second source marks ALREADY-FIXED, and (d) built a false urgency
around a commit that was already merged. **Every one was caught by a second party measuring —
none by the author re-reading.**


---

## §18. THE REAPER — the frozen rigs are not frozen by neglect (added 2026-08-28T20:5xZ)

**Measured at source, not accepted on report:**

- **`gt-97l6hr`** [BUG · P1 · **OPEN since 2026-08-14**] — *"Reaper stale-workflow-root query
  TIMES OUT on the 3 biggest stores — **silent detection failure for 24h+**."* Fourteen days open.
- **`mc-0nyo5`** [**type=decision** · P2 · OPEN] — *"The reaper has not completed a run since
  2026-08-23: fix both legs (backup first), or **accept no stale-workflow reaping**?"*
- Live in the inbox this hour: `gascity_packs: stale inactive workflow issue root query failed
  … Error 1105 (HY000): row read wait bigger than connection timeout`, filed as
  **"ESCALATION: Reaper anomalies detected [MEDIUM]" on every run**, 13+ identical unread copies.

**What this changes.** §10 implicitly assumed the frozen rigs were frozen by neglect and would
yield to hand-triage. They are frozen because **the sweeper cannot run.** The recursive
workflow-descendant CTE cannot finish at those store sizes. `mc-dpby` measured 7,282; today's
re-measure is 7,956 — **the population is growing, which is exactly what an unrunnable sweeper
predicts.** Hand-draining 7,956 treats the symptom while the backlog regrows behind you.

**The escalation is itself a P6.2 violation, and it is the worst instance found this session.**
The reaper files *"anomalies detected"* on every run **while failing to run at all**. A
diagnostic that cannot pass, reporting as a diagnostic that found something. Fourteen days of
"MEDIUM anomaly" mail is fourteen days of a broken query announcing itself as a finding.

### Why the critical path LENGTHENED rather than shortened

The intuition — "fix the sweeper, shrink the drain" — does not hold, for a reason worth stating:

1. **We may not fix it.** `mc-0nyo5` is a **decision**, unadjudicated, and its second option is
   literally *"accept no stale-workflow reaping."* The query is not in the mathcity pack
   (`grep` finds it in neither `mathcity/` nor `~/repos/gascity/`), so P3.1 likely bars a local
   patch and routes it upstream via `create-issue-briefed`.
2. **So the only sweeper available is the local one.** H0 stops being "preparation before
   triage" and becomes the substitute sweeper plus the measurement that sizes H1. Rescoped
   **2.17 → 3.17**.
3. **H1 cannot be re-estimated yet.** Its 8.67 is marked `†` conditional: it is not knowable
   until H0 reports what fraction the local sweep actually clears.

**CP: 50.17 → 51.17, +1.00, and the task that moved is H0.** The finding *removed an
assumption* rather than supplying a fix, and removing a false assumption costs sessions before
it saves them.

**If `mc-0nyo5` is ruled "fix" and the sweep lands, H1 collapses and so does the total** —
H1 8.67 → 6.0 gives CP 48.50; → 3.83 gives 46.33; → 2.0 gives 44.50. **The single highest-
leverage decision in this plan is therefore `mc-0nyo5`, and it is Taylor's, not an agent's.**

### Delta 2 — the read half of the missing-verb gap has SHIPPED

`read_beads` (#245) merged as **PR #251, `~/repos/mathcity` main @ `51ddb27`** (verified in that
checkout by name, per the standing rule below). `beads_list` now reports
`matched / total_in_store / statuses_excluded`, which makes the "23 decisions, zero verdicts"
false report **unwriteable in code**. That is M3's whole thesis enforced at the surface rather
than by discipline — **M3 is now scoped to the remaining un-instrumented counts** (`bd ready`'s
441-of-100, `gh issue list`'s truncation, `work_ready` reporting CLOSED beads as ready), not to
bead reads. The **write** half (`bead_close/hold/release` — `mc-i9bwz`) remains open and is the
refusal that blocked closing `mc-j939e` five times today.

### STANDING RULE — quote the SHA and name the checkout

`origin/main` names **two different commits on this machine right now**: `<city-root>/mathcity` sits on
`fix/mc-6i9gm-zombie-stop` with `origin/main` stale at `a1c8e9f`; `~/repos/mathcity` has
`51ddb27`. The adversarial reviewer's single largest error came from measuring in `<city-root>` against
a `FETCH_HEAD` nine minutes stale and reporting a merged fix as stranded. **Five state claims
expired in transit today.** Every SHA in this plan names its checkout.
