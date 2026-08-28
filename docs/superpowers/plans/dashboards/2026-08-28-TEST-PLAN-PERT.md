# TEST PLAN (PERT) — companion to `2026-08-28-MASTER-pipeline-return-path-and-drain-PERT.md`

**Author:** clark-fork, 2026-08-28 · **Base:** `<city-root>/mathcity` @ `51ddb27` (named per the
standing rule: quote the SHA, name the checkout)

## §0. WHY THIS DOCUMENT EXISTS

The MASTER PERT is a sound plan with a hole in it: **44 tasks, zero test specifications.**
Its exit criteria are phase-level traversals — correct, but they gate the phase, not the
task. Nothing in it says what a given task must prove before its branch is allowed to land,
so "done" is currently decided per-agent, per-task, by whoever wrote it.

That is the gap this document fills. It does not re-plan the work; it PERTs the *testing* of
the work and makes landing conditional on it.

**It also carries one measurement the MASTER PERT lists as unresolved.** §13 records "four
mutually inconsistent test counts for one suite (1702 / 1718 / 1795 / 1802); 1795 traces to no
artifact." That is resolved in §2 below. It was never a contradiction.

---

## §1. THE RULE EVERY TASK INHERITS

Four rules bind every task in the MASTER PERT. They are not new policy — they are existing
mathcity policy (P6.2, P1.19) plus two failure modes measured on this codebase in the last
week — but they were nowhere in the plan, so they were not binding anything.

**R-1 — RED FIRST, and a red that could have been green.**
Before any fix, a test must fail *because of the defect*. Capture the failing output. If no
test can be made to fail, the correct verdict is **ALREADY-FIXED**, and it is a success, not a
failure. The MASTER PERT contains **four** tasks discovered to be already done — V1, R6, and
two more caught in review. Every one was caught by a second party measuring, none by the
author re-reading. Red-first makes that check automatic instead of dependent on diligence.

**R-2 — every guard ships with a control that fails when the guard is removed.**
POLICY P6.2: *a check that could not have failed must not render as a check that passed.* Its
mirror is equally bad — a diagnostic that cannot pass. The concrete danger in this plan: R2,
R8 and R3 all *loosen* a gate. A loosened gate that now passes everything also passes its own
test. The control is the only thing standing between "fixed" and "disabled".

**R-3 — assert the consequence, never the flag.**
Measured on this repo, 2026-08-22/23: a dry run returning `applied: false` while mutating the
disk passes any assertion about the flag. Assert that no directory appeared. Likewise a test
that greps source for the string `--append-notes` proves nothing about whether notes survive.

**R-4 — a test count is a triple, not a number: (scope, commit, checkout).**
See §2. Any report of "N tests pass" that does not name all three is unreproducible.

---

## §2. RESOLVED — the "four conflicting test counts"

The MASTER PERT §13 lists this as an open unknown. Measured today, it is not a conflict; it
is the plan's own M3 defect class — **a count that does not declare its scope** — appearing in
the plan's own instrumentation.

Two independent axes were being collapsed into one number:

| base commit | `tests/mctl` | `tests/` (all) |
|---|---|---|
| `a1c8e9f` | 1804 | 1936 |
| `53522a4` | 1808 | 1940 |
| `51ddb27` (current main) | **1817** | **1949** |
| `fix/mc-6i9gm-zombie-stop` (the working checkout) | 1703 | 1835 |

**Both axes move the number, and neither was ever quoted.** `tests/` exceeds `tests/mctl` by a
constant 132. And the working checkout differs from main by 114 tests.

### The second finding, which is the one that matters

**`<city-root>/mathcity` is checked out on a branch that is 22 commits BEHIND `origin/main`.**

    git rev-list --count fix/mc-6i9gm-zombie-stop..origin/main   ->  22
    git rev-list --count origin/main..fix/mc-6i9gm-zombie-stop   ->   3   (docs only)

Those 22 commits include PRs #241–#251: the whole `/tracker` view (#186), `beads_list`/
`beads_show` (#245), the `/queue` sentinel fix, the MCP-concurrency pin, and the port-based
dashboard stop. **Any measurement taken in `<city-root>/mathcity` right now is taken against a
checkout missing all of it** — which is exactly how a merged fix gets reported as stranded,
the single largest error the MASTER PERT's own adversarial reviewer made.

**Consequence for every task below:** baseline against `origin/main` in a fresh worktree, never
against `<city-root>/mathcity`'s working tree. The baseline is **1817 / 1949 @ `51ddb27`**.

---

### §2b. CORRECTION — the baseline was NOT green, and the gate below was written as if it were

Measured after §2 was written, and it invalidates the plainest reading of gate 4:

**`origin/main` @ `51ddb27` ships 13 FAILING tests.** All 13 are in
`tests/brief-shuffle-fast-drain`, and all have one cause:

    AssertionError: 'duplicate stack slug' not found in
                    'missing required gate G17 Section-discipline'

`assets/brief-pipeline/gates.toml` lists **G17** in the `standard` profile; the drain suite's
fixture helper stopped at G16. Every fixture brief was therefore refused for a missing gate
*before reaching the behaviour under test*. Stale fixtures, not a broken drain — established by
reading `gates.toml`, not inferred from the symptom.

Confirmed unchanged at `522f3cf`, `a7f9e32`, `ddc0a54`, `a1c8e9f`, `53522a4`, `51ddb27`, so it
predates today's merges.

**Why nobody saw it — and this is the part worth keeping.** The suite everyone quotes is
`tests/mctl` (1817, green). These 13 live in `tests/` (1949) and are *invisible from
`tests/mctl`*. That is **the same scope-declaration defect M3 exists to fix, occurring in the
project's own test instrumentation.** A subset was being reported as the whole, exactly as with
the "441 ready beads" and the "four inconsistent test counts".

Fixed on `fix/drain-fixtures-g17`: fixtures declare G17, and a **mutation-proven** control
asserts the gate still refuses a brief that fails it (flip the fixture's `G17: FAIL` to `PASS`
and the control fails, exit 1). Drain suite `13 failed / 38 passed` → **52 passed, exit 0**.

**The first version of that control was VACUOUS** — it used placeholder gate names, so the
brief was rejected for missing G1–G16 and the assertion was satisfied for the wrong reason. It
passed under mutation. Recorded because a vacuous control is indistinguishable from a real one
at a glance, and the only thing that separated them was running the mutation.

**Consequence for gate 4 below:** "not regressed from 1817/1949" was written against a baseline
assumed clean. Until `fix/drain-fixtures-g17` lands, the honest baseline is **1817 passing in
`tests/mctl`; 1936 passing and 13 failing in `tests/`**. A branch reporting "13 failed" is at
baseline, not regressed — and a branch reporting **0** failed has fixed something.

---

## §3. TEST SPECIFICATION PER TASK

`TT` = test effort in agent-sessions, PERT-weighted `(O + 4M + P)/6`, **additional to** the
MASTER PERT's implementation TE. Type: **U** unit · **I** integration · **L** live traversal ·
**C** control (required, counted inside its parent).

### Phase 0–1 — substrate and dispatch

| task | what the test must prove | type | TT |
|---|---|---|---|
| S0 FD | Headroom is measured before *and* after a deliberate config reload, by the method `fd-census.sh` defines. **The plan being adopted forbids citing a single measured fd count — three methods gave three values.** A test asserting one number contradicts its own source. | I+L | 1.50 |
| D1 latch | A `gc.kind=workflow` bead is NOT offered to a normal-role claim. **C:** a non-workflow bead still is — otherwise the exclusion has simply switched claiming off. | U+C | 1.17 |
| D4 fast-drain cwd | The drain resolves its roots from the pack root with cwd set to an unrelated directory. **The fixture must chdir somewhere hostile**; run from the repo root it passes whether or not the bug exists. | U+C | 0.83 |
| D5 claim latency | A claim completes within its own window under a store of realistic size. Fixture must state the store size it used — the competing diagnosis is that the sweep walks 18 DBs / 22G, so a small-store test cannot distinguish the two hypotheses and must not claim to. | I | 1.50 |

### Phase 2 — the vertical slices (W1–W5)

These are **live traversals**, not unit tests, and that is the point: the MASTER PERT's §0
diagnosis is that every layer was individually correct while no bead ever crossed all of them.

| task | what the test must prove | type | TT |
|---|---|---|---|
| W1 | One real bead completes `bead → brief → present → adjudicate → verdict → code → close → dashboard`, and the dashboard shows it. Not a mock at any hop. | L | 1.83 |
| W2 | A `revise` verdict produces a fresh brief deposit **with no human carrying it**. | L | 1.17 |
| W3 | A `reject` verdict leaves the work re-filable, not stranded. | L | 1.17 |
| W4 | Ten beads concurrently. **Blocked on M1** — every MCP call currently serialises on one lock (measured 36×), so a concurrency test today measures the lock, not the pipeline. Sequencing this before M1 would produce a green test that proves nothing. | I+L | 1.50 |
| W5 | One hecke bead, cross-rig, end to end. | L | 1.17 |

### Phase 3 — return path

| task | what the test must prove | type | TT |
|---|---|---|---|
| R1 `brief.decided` | The event fires from the **CLI** path, and **all three** subscribers receive it: `brief-decision-dispatch`, `post-decision-file-or-sendback`, `revise-return`. **Largest blast radius in the plan** — these will now fire on verdicts that previously fired none. A test covering only `revise-return` ships the other two untested into production. | I+C | 1.50 |
| R2 adjudicated guard | No code path moves a brief carrying a verdict into `.rejected/`. **C ×2** (specified by its own plan): the gate still rejects genuinely unfit briefs. | U+C | 1.00 |
| R3 B2.10 scope | A permitted `plan_create_brief` succeeds. **C:** the gate still refuses the writes it protects. Ruled `C+D` by Taylor at `mc-tbucy`; **option B is out of scope and a test asserting terminal status would encode a rejected verdict.** | U+C | 1.00 |
| R4 commission path | A brief created by the commission path is subsequently **found by the listing path**. Asserting a path string equals a constant proves nothing about reachability. **Two brief roots exist** (city `<city-root>/.beads/briefs`, rig `<city-root>/mathcity/.beads/briefs`); the fixture must name which. | I+C | 1.17 |
| R5 hecke revise | 13 stranded verdicts carry through. **3 are no-brainers and must NOT be re-adjudicated** — the test must assert they are *not* re-presented. | I | 1.17 |
| R7 append-notes | Pre-existing note text survives an update. **C:** the fixture catches the old replacing behaviour. Fix the P1.19 violation without committing it. | U+C | 0.83 |
| R8 provenance | Decide first whether the check or the briefs are wrong — **21 of 24 rejected on one criterion is more consistent with a broken check than 21 malformed briefs**. Then: a valid brief is accepted, **C:** an invalid one still rejected. | U+C | 1.00 |

### Phases 4–7 — verbs, measurement, contracts

| task | what the test must prove | type | TT |
|---|---|---|---|
| V2 close verb | **Blocked on decision `mc-i9bwz`.** Not testable until ruled. | — | — |
| M1 MCP lock | Concurrent calls do not serialise. #244 and `mc-znfnm` are the same defect — dedupe before writing two tests for one bug. | I | 1.00 |
| M2 `/city` render | **Profile before proposing.** No known mechanism; #130's cached-scan theory is already merged and fixed. A test written against an unidentified mechanism asserts a guess. | I | 1.17 |
| M3 scope declaration | `work_ready` does not return CLOSED beads, and every read declares `matched`/`total_in_store`/`statuses_excluded` per the shipped `beads_list` shape. **C:** a store containing a closed bead genuinely yields it before the fix. | U+C | 1.00 |
| P2 typed surface | A formula writing brief state directly is **refused**. C: a legitimate write still succeeds. | I+C | 1.50 |
| F1 #189 | Three re-measures must all agree or the close fails: attempts ≈41,382 (not the double-counted 76,961), retry budget present, zero firings since 08-25. **Defect B remains live and goes upstream** — this is "close A, file B", never "verify and close". | U | 0.83 |
| F2 symlinks | 178 symlinks over 90 targets. Test the parser's actual precedence: **first-wins where the docs say last-wins** (upstream #2027). Test observed behaviour, not documented behaviour. | U | 0.83 |

### Structural / this session's additions

| task | what the test must prove | type | TT |
|---|---|---|---|
| IDX stack index | A checker that detects index↔disk divergence **and can fail**. Run against a fixture, never the live pile. Candidate mechanism: files whose `artifact:` frontmatter bead id differs from their filename stem (live instance: `mc-cbks.md` carries `mc-g4k2`), which would inflate *both* divergence counts from one cause. **Blocked on open question Q5** — if unresolved, ship the checker and a brief, not a repair. | U | 1.17 |
| SWEEP filter | Any debris filter excludes `issue_type ∈ {bug, feature, chore}` before title matching. **C:** the 9 known-misclassified bug beads survive it. Defect `mc-0am5z` (P0), brief `mc-v5m0o`. | U+C | 0.83 |

**Total additional test effort: ≈ 27.8 agent-sessions**, against the MASTER PERT's 51.17-session
critical path. Testing is roughly **35% of total effort** — high, and correct for a system whose
defining failure is that merged code did not work end to end.

---

## §4. TEST-EFFORT ON THE CRITICAL PATH

The MASTER PERT's CP is `S0 → D1 → D5 → W1 → R1 → W2 → W3 → W4 → W5 → H0 → H1 → H3 = 51.17`.
Adding test effort to CP tasks only:

    S0 +1.50 · D1 +1.17 · D5 +1.50 · W1 +1.83 · R1 +1.50 · W2 +1.17
    W3 +1.17 · W4 +1.50 · W5 +1.17 · H0/H1/H3 +2.50 (est.)
    = +16.01

**Critical path with testing: ≈ 67.2 agent-sessions.**

Two honest qualifications:

1. **This does not re-run the network.** Adding test effort to off-CP tasks can consume their
   slack and change which path is critical. Most off-CP tasks carry slack > 20 against test
   additions under 1.5, so the CP is unlikely to move — but that is an argument, not a
   recomputation, and it is stated as such.
2. **The MASTER PERT's own §15.1 applies unchanged:** everything after W1 (EF 17.83) is
   provisional by its authors' admission. Adding test effort to provisional estimates yields
   provisional totals. The figure above is a planning number, not a commitment.

---

## §5. THE LANDING GATE

No branch is handed to BART for merge unless **all** hold. This is the enforceable part of
this document; everything above is planning.

1. **Red-first evidence** — the failing output, captured, from before the fix. Or an explicit
   `ALREADY-FIXED` verdict with the evidence that no test could be made to fail.
2. **Green after** — the same test passing.
3. **Controls present and shown failing** when the guard is removed, for every task that
   loosens a gate (R2, R3, R8 at minimum).
4. **Suite baseline stated as a triple** — scope, commit, checkout — and not regressed from
   **1817 (`tests/mctl`) / 1949 (`tests/`) @ `51ddb27`**.
5. **P5.5 footer**, and **no `Co-Authored-By: Claude` trailer**. A PR has already had to be
   amended and force-pushed over this.
6. **Symbol citations, not line numbers**, in any comment inside a file the same commit
   modifies — such a citation is wrong in the commit that contains it. Measured instance:
   `27225aa` cited `work.py:636`, correct at `27225aa~1`, wrong at `27225aa`.

**Gate 4 has a known false-pass and it is worth naming:** a branch based on the stale
`<city-root>/mathcity` checkout will baseline at 1703 and "not regress" while silently lacking 22
commits of main. Baseline in a fresh worktree from `origin/main`, or gate 4 cannot fail.

---

## §6. WHAT THIS PLAN DOES NOT TEST

Stated so the absence is visible, per P6.2 and P7.4 (a survey names its scope).

- **No performance regression suite.** M2 (`/city` render) is profiled once, not pinned. A
  future regression re-opens it.
- **No test for the FD leak's mechanism**, because the mechanism is **unknown** — both
  candidates are source-refuted (`mc-tkei`). S0 tests *detectability*, not the cause. Do not
  read a green S0 as "the leak is fixed."
- **The 6,934 hecke/gascity-packs beads outside the brief/dashboard filter** are untested and
  unscoped here, as in the MASTER PERT.
- **No upstream test coverage.** `gastownhall/gascity` defects (D1's latch, D5's claim hang,
  F2's parser precedence, #189 defect B) are filed as issues under P3.1/P3.2, not patched
  locally, so nothing here tests them.
- **BART's merge step is untested and unestimated**, as in the MASTER PERT §15.3. Every
  landing is a two-agent handoff sized as one.
