# Quality-control review — kolchin, 2026-09-10 → 2026-09-17

**Author:** kolchin-monitor · **Date:** 2026-09-17 · **Status:** report only, no repairs made
**Scope:** kolchin (`gascity-user@kolchin`) — city `~/HQ`, rigs `~/repos/{mathcity,gascity,mathcity-testrig}`
**Companion:** QUIMBY 71 holds the ritt (`~/gt`) half. Window agreed with them; artifacts belong to the box whose filesystem holds them.

---

## Headline

**Kolchin's repositories are clean. Its *work queue* is not.**

Every slop category that concerns source control comes back healthy here — no stray branches, no unpushed commits, no detached-HEAD worktree population. The damage is elsewhere: **49 abandoned workflows holding 441 step beads of which 67 completed**, and a **forensic trail of ~18 policy violations** sitting in plain sight as backup files.

The contrast with ritt is stark and is itself a finding. See §7.

---

## 1. Worktrees — CLEAN

```
mathcity          1 worktree      gascity   1 worktree
mathcity-testrig  2 worktrees     prunable: 0
```

No orphans, nothing prunable. **Kolchin does not use the worktree-per-item dispatch pattern**, which is why it has none of ritt's 68-worktree exposure.

## 2. Branches — CLEAN

One branch per rig (`main`), zero ahead of origin, zero without upstream. Nothing stranded.

## 3. Unpushed work — CLEAN

```
mathcity  0 unpushed    gascity  0 unpushed    mathcity-testrig  0
```

Verified with `git rev-list origin/main..HEAD --count`. Everything kolchin produced in the window reached the remote. Bead data likewise: `bd dolt push` verified by remote ref advance `2dac8690 → 9f4dc8e3`.

## 4. Files out of place — MINOR

```
untracked + unignored : 1   (.beads/identity.toml)
stray .bak in tree    : 2   (.beads/identity.toml.bak, .beads/metadata.json.bak)
city.toml backups     : 22  ← see below
mathcity-testrig dirty: 226 (materialized skill sinks — regenerable, P1.3 says do not hand-edit them; not slop)
```

## 5. The 22 city.toml backups are evidence of ~18 policy violations — FINDING

`~/HQ` holds 22 `city.toml.bak-*` files. **Four are mine**, produced by `provider_set`'s typed write path. **Eighteen predate me**, dated Sep 6–8, with hand-chosen names:

```
bak-poolraise      bak-poolraise2     bak-poolcap       bak-poolzero
bak-agexswitch     bak-workspaceprov  bak-providerfix   bak-fixsession
bak-latchlivelock  bak-srccheckout    bak-rigpath       bak-preplin
bak-briefopcap     bak-pooltest       bak-testrig       …
```

Each name records a hand-edit to `city.toml`. **P1.2 forbids exactly that** — *"never a one-off hand-edit to `city.toml`… city.toml changes come from pack updates, not hand-edits."* So the backup trail is a **forensic record of roughly eighteen P1.2 violations**, left by agents doing the responsible thing (backing up) while doing the forbidden thing (hand-editing).

Two sub-findings:

- **Nothing enforces P1.2.** No mechanical check was found. The rule is adopted and unpoliced, which is why eighteen violations accumulated visibly without anyone stopping.
- **No retention policy.** Even the compliant path — my four — accumulates without bound. `provider_set` creates a backup per apply and nothing ever reaps them.

## 6. Abandoned work — THE MAIN FINDING

```
open workflow roots        : 49  (of 114 total)
created 2026-08            : 44
created 2026-09            :  5
untouched since before 09-10: 49   ← all of them
child step beads           : 441
child steps CLOSED         :  67   ← real partial progress, then stopped
```

By formula:

| formula | open roots |
|---|---|
| `work-briefed` | 18 |
| `do-work` | 12 |
| `commission-work-briefed` | 8 |
| `build-basic-briefed` | 7 |
| `create-issue-briefed` | 3 |
| `brief-shuffle` | 1 |

**These are not inert.** 67 of 441 steps completed before stopping — unlike the `ma-v7h`/`ga-333` strand, which never started. Work was done and then stranded.

**And they cannot resume:**

```
routed to mathcity/gc.run-operator : 35   ← pool capped at max_active_sessions = 0
no routing at all                  : 13   ← orphaned
routed to mathcity.brief-operator  :  1   ← also capped at 0
```

**Thirty-five are aimed at a pool that cannot staff them, and thirteen are aimed at nothing.** This is the silent-accumulation class: a workflow dispatched to a capped pool produces no error at any layer — not an order failure, not a stuck-bead hit, not a `gc doctor` failure. It simply sits.

Detector shipped for this during the window: `assets/scripts/check_silent_accumulators.py`. It reports FOUND on kolchin today.

## 7. Lost mathematics — NONE ON KOLCHIN, BUT SEE RITT

Kolchin runs no mathematics rigs; Magma is not installed and heavy computation is deliberately sited elsewhere. **Zero exposure here.**

Handed to QUIMBY 71 for the ritt half, measured before the scope split: **`hecke` carries 91 commits across 28 branches with no upstream** — the largest stranded pool found anywhere. Whether any encode unique mathematics is a content question left open.

## 8. Untested / undocumented code — ONE SELF-FINDING

Code shipped in the window, with its test files:

| commit | code files | test files | subject |
|---|---|---|---|
| `639e967` | 8 | 6 | `provider_set` — the write half of #197 |
| `10ad346` | 2 | 2 | `--for-provider` |
| `2443159` | 2 | 2 | `--from-provider` |
| `b29a12b` | 2 | 2 | fix wrong-tool schema + fake verify |
| `eb54b39` | 2 | 1 | lost-update guard |
| `1f21a6c` | 2 | 1 | fan-out fix |
| `7be2edb` | 1 | **0** | policy + provider switcher |

**`assets/scripts/check_silent_accumulators.py` is referenced in 0 test files.** I verified it by hand against fixture cities, including negative controls, and never added a suite test. It is a **detector**: if it silently breaks, nothing reports that, and its output is exactly the kind of thing people trust. This is my slop and it is the same shape as the defects it was written to find.

`mcp_server.py` by contrast is referenced in 57 test files.

## 9. Work that was done and is not live — FINDING

The `brief-shuffle` fan-out fix (`1f21a6c`, committed 2026-09-10) **is still not running on kolchin seven days later.** All six materialized copies under `~/.gc/cache/repos/*/orders/` still read `scope = "rig"`.

Cause is structural, not negligence: the pack is imported at a pinned SHA, that SHA is declared **six times** (`pack.toml:18`, `packs.lock:29-30`, four `[rigs.imports.mathcity]` blocks in `city.toml`), and `gc import add --version` refuses the partial bump with *"incompatible pinned versions"* while `gc import install` has no update or force flag.

**A city cannot currently adopt a pack update without a hand-edit that P1.2 forbids.** Tracked as `ma-g2h`.

---

## Summary table

| Category | Kolchin verdict | Evidence |
|---|---|---|
| Messy worktrees | **clean** | 1–2 per rig, 0 prunable |
| Stray branches | **clean** | 1 per rig, 0 without upstream |
| Unpushed work | **clean** | 0 commits, bead push verified |
| Files out of place | **minor** | 1 untracked, 2 `.bak`, 22 config backups |
| Untested code | **1 instance** | `check_silent_accumulators.py`, 0 tests |
| Undocumented code | **none found** | every shipped commit carries prose |
| Lost mathematics | **N/A** | no math rigs on this box |
| Abandoned work | **SEVERE** | 49 workflows, 441 steps, 67 done, none resumable |
| Policy violations | **~18** | `city.toml` hand-edit trail |
| Shipped-but-not-live | **1** | fan-out fix, 7 days, pin gap |

---

## What this is not

It is worth stating plainly: **almost none of what was found is careless output.** The abandoned workflows contain completed steps. The ritt branches handed to QUIMBY are well-tested (`dashboard-register-s65`: 36 files, 19 tests). The eighteen hand-edits each took a backup first.

The failure mode is not sloppiness. It is **work that was done properly and then became unreachable** — by a capped pool, an unpushed branch, an unbumped pin, or a rule nobody enforces. "AI slop" in the sense of low-quality generation is not what this audit found. What it found is a system that loses good work silently.

That distinction should drive the remedy: **detection and reachability, not more review.**

---

# Proposed course of action

Ranked by *damage prevented per unit of work*. Nothing here has been executed; all of it awaits approval.

## A. Decide the 49 abandoned workflows — BIGGEST, AND NEEDS A HUMAN

441 step beads, 67 completed, none resumable. Three dispositions and they are not interchangeable:

1. **Resume** — requires lifting `mathcity/gc.run-operator` above 0. **Do not do this blind.** The cap carries a recorded justification (shared-store contention), and 13 of the 49 have no routing at all, so lifting the cap resumes 35 and orphans 13 regardless.
2. **Close with reason**, citing the cap and the age, preserving the 67 completed steps as record.
3. **Triage**: salvage the 67 completed steps' artifacts, then close.

**This is yours to rule.** It is 49 units of someone's work and the right answer depends on whether that work still matters, which no measurement answers.

My recommendation: **(3)**, because it is the only option that does not discard the 67 completed steps, and because closing without salvage repeats the defect this audit is about.

## B. Build the P1.2 check — HIGHEST LEVERAGE, NO HUMAN NEEDED

Eighteen violations accumulated visibly over three days because nothing looks. The check is cheap and the evidence is already on disk:

```bash
ls <city>/city.toml.bak-* | wc -l      # each is a hand-edit fingerprint
```

Better: a check that compares `city.toml`'s mtime against the last `gc import install`, and fails when the file is newer. Ship it as a `gc doctor` check or an mctl tool so it runs unprompted.

**Pair it with retention**: reap `city.toml.bak-*` older than N days, keeping the most recent k. My `provider_set` should do this on write rather than accumulating.

## C. Test `check_silent_accumulators.py` — SMALL, AND MINE

It has none. Port the fixture cities I built by hand (kolchin shape, empty sweep, healthy city, disabled-order control) into `tests/mctl/`. The empty-sweep case matters most: it must assert `CANNOT VERIFY`, never a pass.

**I would do this first regardless of the rest**, because shipping an untested detector while auditing for untested code is not a position I want to hold.

## D. Close the pin-bump gap — UNBLOCKS `ma-g2h` AND EVERY FUTURE PACK UPDATE

A city cannot adopt a pack update without violating P1.2. The fix is a typed operation that bumps all six declarations atomically, validates the target commit exists and contains what is claimed, and verifies every materialized copy after `gc import install`.

This is the same class as `provider_set` and should live beside it on the mctl surface. **It is worth more than the fan-out fix it would deploy**, because it recurs on every pack update forever.

## E. Raise the B3.1 reachability gap with QUIMBY — CROSS-CITY, NOT MINE ALONE

Ritt's 13 closed-bead branches **cite B3.1 acceptance and are still unreachable**. B3.1 asks whether acceptance was verified; it never asks whether the artifact is reachable. A closure limb along the lines of *"the artifact is reachable from a ref that outlives this worktree"* would have caught all 13 and `mc-cwz0w`'s six.

That is a policy amendment and must go through `new-brief-policy`, with QUIMBY as co-author since the evidence is ritt-side.

## Ordering

```
C  (test the detector)      — immediate, mine, no approval needed beyond this report
B  (P1.2 check + retention) — next, unblocks nothing but stops the bleeding
D  (pin-bump mechanism)     — then, unblocks ma-g2h and all future updates
A  (49 workflows)           — needs your ruling; do not start without it
E  (B3.1 amendment)         — slowest, needs QUIMBY and a policy proposal
```

## What I am explicitly NOT proposing

- **No worktree pruning anywhere.** `mc-cwz0w`'s six commits live only in worktree reflogs and all six beads read CLOSED, so any reaper keyed on bead status destroys them. CT10.2 would automate exactly that; it is PROPOSED and should be adjudicated with that in mind.
- **No cap lifting** without (A) being decided first.
- **No back-catalogue enforcement.** A B3.1 or P1.2 check applied retroactively fails most of the existing store — measured at ~10% limb-nameable on 493 closed beads. New writes only.

---

# Corrections and additions, post-publication

## C1 — the stranded-commit figure was overstated by 30%

I reported ritt's unpushed branches as carrying **67 commits**, from `git rev-list --count main..$b`. QUIMBY 71 re-derived with `git cherry main $b | grep -c '^+'` and found **47 are patch-unique**; twenty are already in main by patch-id. On `hecke`, **91 raw against 59 patch-unique** — 32 duplicates.

Raw-ahead answers "how many commits does this branch carry that main's history lacks". Patch-unique answers "how much work would be lost". **The loss figure is the second one.** Both numbers are correct measurements of different questions and I published the wrong one for the claim I was making.

Corrected: **ritt mathcity 47 commits of unique work stranded; hecke 59.**

## C2 — mathcity stopped using pull requests on 2026-08-29

Measured on `tdupu/mathcity`:

```
most recent PR           : #255, created 2026-08-29, merged
PRs in the fetched window: 30, all dated 2026-08
historical merge commits : 167
commits on main 09-10→09-17 : 11
merge commits in that window:  0
```

This is **not** "mathcity has no PR discipline". It had it, heavily — 167 merges — and **stopped nineteen days ago**. Since then `main` advances by direct push.

**I am part of this.** Every commit I landed this week (`1f21a6c`, `639e967`, `10ad346`, `2443159`, `b29a12b`, `eb54b39`, `7be2edb`) went straight to `main` via `git push origin main`. I did not open a single PR, did not notice the practice had lapsed, and am the author of several of the 11 direct pushes I just counted as evidence of the regression.

That changes the finding's character. It is not a lapse by absent agents; it is a practice that stopped and that **every subsequent participant, including the auditor, silently inherited**. A regression nobody chose is harder to fix than one somebody decided, because there is no decision to revisit.

For contrast: `hecke`, the mathematics rig, shipped **14 PRs in the same window, 9 merged**. The discipline is alive on that rig and dead on this one.

## C3 — kolchin commit-claim survey returns empty, and that is not a clean bill

QUIMBY 71's P3 — classify every commit SHA claimed by beads closed in the window — returns **0 claims from 6 closed beads** on kolchin. Their ritt run found 62 claims of which 50 are on zero branches, 14 carrying `gc.verified_commit`.

Kolchin's zero is **not** evidence of health. Those six beads are five workflow-chain steps and one scratch probe, none of which would carry a commit. The population is wrong for the question. **Kolchin has no comparable evidence in either direction**, and the report should not claim it passed a test it never took.

---

# Slop-control design (grilled, 2026-09-17)

Four decisions were put to Taylor one at a time. **Three of the four answers were invalidated by exploration after being chosen**, which is the grilling working: each answer sent me to measure something, and the measurement moved the design.

## The decisions, and what measurement did to them

**Q1 — where to enforce.** Chosen: *mctl write-time refusal, plus detectors for states with no write to intercept.*
Exploration had already ruled out the obvious vehicle: the existing gate mechanism rejects into `.pile/.rejected`, which **adopted B2.16 forbids** (*"MUST NOT remove the brief from any pile, index, queue, view, or presentation surface"*). So a new gate would have built on a mechanism already in violation.

**Q2 — what to refuse.** Chosen: *refuse a close whose claimed commit is contained by zero branches.* This is the right rule. B3.1 already asks whether acceptance was verified, and ritt's thirteen closed-bead branches answer it truthfully while the artifact sits unreachable. **Reachability is the unasked question.**

**Q3 — the bypass.** Chosen: *close the 25 `bd close` call sites first.*
**INVALIDATED.** Only 5 are executable; the other 23 are skill prose, **11 of which are prohibitions** my grep counted as violations. And all 5 executable sites close `$WORK_BEAD` — bookkeeping steps (`processed=N`, `archived=N`) that carry no commit. **The reachability rule would never fire on any of them.** Migrating them buys zero coverage.

**Q4 — revised Phase 1.** Chosen: *detector first, then enforce where the detector says closers actually are.* Correct, because the bypass is not in call sites — **195 of 493 closes have no recorded closer**, consistent with interactive `bd close` that no grep can find.

## Then the design was invalidated a fourth time, by QUIMBY 71

**The gate already exists.** `gascity/cmd/gc/work_record_gate.go` — 20,499 bytes, dated 2026-09-05, ADR-0009. It does `merge-base --is-ancestor` on close and ships **warn-only** behind `GC_WORK_RECORD_ENFORCE`.

I had spent four questions designing an enforcement mechanism that ships in the binary this city runs. **That is the check-zero failure, committed while auditing for exactly that class.** It was caught by a peer, not by me.

### And arming it would be catastrophic on kolchin

```
closed beads          : 493
carry gc.work_outcome :  29   (6%)
carry gc.work_commit  :   0
would wedge if armed  : 464 of 493   (94%)
```

Two independent reasons not to flip the switch here:

1. **94% of closes would be refused** for lacking `gc.work_outcome`. That is a wedge, not a gate.
2. **Zero beads carry `gc.work_commit`**, which is the only key the gate reads — so the reachability check would **never fire even once** while 94% of work stopped. Enforcement on, everything walking through.

## What is actually proposed

**P1 — the unreachable-commit detector, three-valued.** Not two.

QUIMBY 71 reproduced the anchoring mechanism in a scratch repo rather than reasoning about it, and found that **`git branch --contains` is blind to `refs/salvage/`**. A two-valued sweep therefore re-reports every commit it already anchored, every tick, forever — **a catch rate that can never reach zero.** A detector that cannot succeed is the same family as a check that cannot fail.

```
reachable  — a branch contains it                      (fine)
anchored   — for-each-ref --contains finds any ref     (PRESERVED, not a finding)
stranded   — neither                                   (anchor now; counts)
```

And it must report **two figures that are never merged**: *new this period* (must reach zero before enforcement is licensed) and *standing anchored-not-landed* (falls only when a commit truly reaches a branch). A single number reports zero while fifty sit preserved and unlanded — B2.13 committed by the remedy itself.

**P2 — a test for `check_silent_accumulators.py`.** It has none. Port the fixture cities built by hand (kolchin shape, empty sweep, healthy city, disabled-order control) into `tests/mctl/`. The empty-sweep case is the one that matters: it must assert `CANNOT VERIFY`, never a pass.

**P3 — a P1.2 hand-edit detector.** `city.toml` newer than the last `gc import install` means a hand-edit. Cheap, and eighteen violations accumulated visibly because nothing looked. Pair it with retention on `city.toml.bak-*`.

**P4 — do NOT arm `GC_WORK_RECORD_ENFORCE`.** Record the 94% measurement against it so nobody arms it later believing it is a no-op. Revisit only when `gc.work_outcome` coverage is materially above 6%.

**P5 — the PR regression is a separate ask.** The practice stopped 2026-08-29 and every participant since, including me, inherited it silently. No detector fixes that; it needs a decision about whether `main` accepts direct pushes.

## What is explicitly not proposed

- **No new gate.** One exists. Building a second is the defect this report is about.
- **No worktree pruning.** `mc-cwz0w`'s commits live only in worktree reflogs on CLOSED beads; CT10.2 would automate their destruction.
- **No retroactive enforcement.** Measured: ~10% of 493 closes could name a B3.1 limb; 6% carry `work_outcome`. New writes only.
- **No cap lifting** before the 49 abandoned workflows are ruled on.
