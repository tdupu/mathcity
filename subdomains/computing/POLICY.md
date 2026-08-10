# Computing Policy

| Field | Value |
| --- | --- |
| Status | Draft — pending the human adjudicator adoption |
| Version | 0.1 |
| Date | 2026-07-12 |
| Decided | the pack owner |
| Applies to | All computation code in mathcity-governed projects: Magma intrinsics, Python scripts, shell scripts, data-generation pipelines, and any file in `magma/`, `scripts/`, `make/`, or `crunch/` that computes, transforms, or persists mathematical objects |
| Consumers | `check-computing-policy` (audit gate), `check-magma-hygiene` (defers caching/DRY rules here), `is-good-test`, any agent touching computational code or test infrastructure |
| Prefix | C |
| Companion policy | Magma Packages Policy (`../magma/POLICY.md`) — governs package structure, README format, and pipeline seams; this policy governs the computational logic and testing infrastructure inside and around those packages |

Governs how computation code avoids redundant work, stays DRY, is
verified, and is regression-tested. The rules here apply whenever
mathematical computation is involved — they are not Magma-specific
and cover any language or script that implements or exercises mathematical
logic in a mathcity project. Every rule has an ID (`C<pillar>.<n>`) and a
pass/fail criterion a skill can cite. `check-computing-policy` enforces
these rules.

> **Relationship to magma POLICY.md:** Pillar 3 of this policy (C3.x)
> governs test infrastructure and is computing-language-agnostic. It
> complements but does not supersede the Magma-specific testing rules
> (M3.x). Where a rule appears in both, the Magma POLICY.md wins for
> Magma packages (PP6.1 explicit precedence); this policy's rules apply
> as the general baseline for all other code.

---

## Pillar 1 — Caching and memoization (C1.x)

*Never pay twice for a result you already have. Computation is expensive;
re-running the same thing wastes time and introduces the risk of getting a
different answer if the environment has drifted.*

- **C1.1 Cache all expensive results to disk.** Any computation that takes
  more than ~5 s or is expected to run more than once must write its output
  to `DATA/` (or the project-designated cache directory) immediately on
  completion and read from that cache on subsequent runs. A computation that
  re-runs unconditionally without checking for a cached output → **revise**.

- **C1.2 Guard with an existence check before recomputing.** Cache-read
  code must check for the file's existence and non-emptiness before
  triggering the expensive computation. A function that reads and writes
  to the same cache path without a guard → **fail** (risks corruption under
  parallel runs).

- **C1.3 Cache keys must be deterministic from inputs.** The filename or
  path of a cached result must encode every parameter that affects the
  output (e.g., level, discriminant, method flag). A generic filename like
  `result.dat` shared across different inputs → **revise** (rename to
  include the distinguishing parameters).

- **C1.4 Cache invalidation is explicit, not silent.** Code that silently
  overwrites a cache file without a flag or user confirmation → **revise**.
  Provide a `--force` / `overwrite := true` escape hatch and document it.

- **C1.5 Memoize in-process for repeated calls within a session.** Intrinsics
  or functions called multiple times with the same inputs in a single Magma
  session should use `AssociativeArray` / `GetCache` patterns or equivalent
  to avoid re-computing within the same process. A function that provably
  gets called ≥3 times with identical arguments in a normal run without
  memoization → **revise** (file a performance bead, M5.2 applies).

- **C1.6 Document the cache contract in the README.** Any intrinsic or
  script with a caching side effect must state in its README entry (or
  header comment): what it caches, where, and what the file format is.
  A cached result with no documentation of the cache contract → **revise**.

---

## Pillar 2 — Code factoring and DRY (C2.x)

*If a chunk of logic appears more than once, it belongs in a named
intrinsic or function. Duplication is a maintenance liability: one fix
must be applied everywhere, and bugs hide in copies.*

- **C2.1 Three-copy rule.** Any code pattern appearing in three or more
  distinct files (or three or more non-adjacent locations in the same file)
  must be extracted into a named intrinsic or helper function. Exception:
  boilerplate that is mechanically generated (e.g., `AttachSpec` stubs) is
  exempt if a template tool produces it. Violation → **revise** (extract +
  file a bead).

- **C2.2 Intrinsics are the extraction unit.** In Magma projects, factored
  logic goes into `intrinsic` declarations inside a `package-*.mag` file.
  Ad-hoc function definitions at top-level in test or make scripts (that
  are then copied into other scripts) → **revise** (promote to a package
  intrinsic or a shared utility file, add to spec per M1.5).

- **C2.3 Factored intrinsics follow the full package lifecycle.** An
  intrinsic extracted under C2.1 or C2.2 must: (a) live in the correct
  package per M1.1; (b) have a README entry per M2.1–M2.2; (c) have test
  coverage per C3.1. Extracting to avoid duplication but skipping the
  lifecycle steps → **revise**.

- **C2.4 No copy-paste of parameter blocks.** Repeated patterns of
  `declare attributes` or argument-parsing setup copied verbatim across
  packages or scripts → **revise** (consolidate into a shared setup
  intrinsic or documented default pattern).

- **C2.5 Script-level DRY.** Shell scripts and Python scripts are subject
  to the same three-copy rule (C2.1). Common patterns (retry loops,
  dispatch boilerplate, path resolution) must be extracted into a sourced
  helper or shared module. Repetitions detected by `diff`-based inspection
  across three or more script files → **revise**.

---

## Pillar 3 — Intrinsic and function testing (C3.x)

*Every intrinsic that a user or downstream code can call must have at
least one piece of test code. Tests must be runnable, must fail when the
thing they test is broken, and must live where they can be found and
re-run.*

- **C3.1 Every public intrinsic has test coverage.** A public intrinsic
  (one documented in a README or callable from outside its package) must
  be exercised by at least one test assertion in the project's test suite.
  An intrinsic documented in the README but absent from every test file →
  **fail** (C3.1 is the computing-policy floor; M3.2 is the Magma-specific
  elaboration).

- **C3.2 Test code lives in the designated test folder.** All test files
  for a project live under the project's canonical test directory (hecke:
  `magma/test/`; other projects: designated in their CLAUDE.md). Test code
  scattered in the repo root, `scripts/`, or `make/` without a link from
  the test folder → **revise** (move or symlink).

- **C3.3 Test files are named and numbered.** Test files follow the
  `test-NN-<topic>.<ext>` naming scheme (per M1.2 for Magma; same
  convention for shell: `test-NN-<topic>.sh`). An un-numbered test file
  (`test-foo.mag`, `quick_check.mag`) not prefixed with a number →
  **revise** (rename using the next free NN).

- **C3.4 Each test must be independently runnable.** Running a test file
  in isolation (from its directory, with no prior setup beyond the
  documented boilerplate) must produce either a pass line or a meaningful
  error. A test that requires another test to run first, or that silently
  passes when the environment is wrong → **revise**.

- **C3.5 Tests use assert-with-expected-value.** Assertions must compare
  computed values against known expected values (not just against each
  other or against trivial identities). Tests with only tautological
  assertions (`assert x eq x`) or with a single trivial input → **revise**
  (per M3.3: assert-by-accident and single-input tests are both findings).

- **C3.6 New intrinsic → new test in the same change.** Adding or modifying
  a public intrinsic without a corresponding new or updated test assertion
  in the same branch/PR is a gate failure (this rule is the
  computing-policy expression of M3.2; both apply for Magma packages). The
  test need not be in a separate file if it fits naturally in an existing
  file — what matters is that coverage exists before merge.

---

## Pillar 4 — Regression testing (C4.x)

*When a computation changes, everything downstream that could be affected
must be checked. The blast radius of a change is the set of all
packages/functions that transitively import or call the changed code.*

- **C4.1 Define blast radius before touching shared code.** Before
  modifying an intrinsic that is called by more than one package, the
  agent or developer must enumerate the blast radius: run
  `grep -r "<intrinsic_name>" magma/` (or equivalent) and list every
  caller. A PR that modifies a shared intrinsic without a documented blast
  radius → **revise** (add a "Blast radius" section to the bead or brief).

- **C4.2 Regression suite covers the blast radius.** For every file in
  the blast radius (C4.1), at least one passing test must exist that
  exercises that caller's use of the changed intrinsic. If a downstream
  caller has no test, the test must be written before the change lands
  (C3.1 applies). A change merged without blast-radius coverage → **fail**.

- **C4.3 Regression tests are re-runnable from the test directory.** All
  regression test files reside in the designated test folder (C3.2) and
  are runnable with no manual setup (C3.4). A regression test that requires
  a special environment not documented in the test header → **fail**.

- **C4.4 Expected-output regression artifacts.** For computations whose
  output is too large to inline (`assert` on a 1000-element list is
  impractical), capture the expected output as a `.expected` file in
  `<test-dir>/expected/` and compare with a diff step. Ad hoc golden files
  elsewhere in the repo → **revise** (move to `expected/`; per M3.7).

- **C4.5 Slow regressions are marked `// SLOW` (or `# SLOW`).** Regression
  tests that take more than ~30 s must carry a slow marker so CI can gate
  them separately (per M3.5 for Magma; C4.5 extends this to all languages).
  An unmarked test that reliably exceeds 30 s → **revise**.

- **C4.6 Breaking-change PRs must pass the full regression suite.** A PR
  that modifies any intrinsic appearing in the spec file's load order must
  demonstrate that the full README-tests suite still passes. Partial
  regression evidence (only the directly-touched test) is insufficient for
  breaking changes → **revise** (run the full suite, or document why only
  a subset is needed with explicit blast-radius evidence).

---

## Pillar 5 — Repository hygiene for computation artifacts (C5.x)

*Files produced by running processes have no place in version control.
A file that changes when a computation runs is a runtime artifact, not
source code — tracking it creates merge conflicts on every server where
computations execute, and misleads readers into thinking the file is
authored rather than generated.*

- **C5.1 Computation output files must not be tracked.** Any file whose
  contents are determined by a running computation process at runtime —
  output logs, audit lists, generated manifests, or intermediate artifacts —
  must not appear in `git ls-files`. Such files belong in `.gitignore` or
  in a directory already covered by a wildcard ignore rule. Whether a file
  is runtime-generated is a model-judgment call on its path, naming, and
  location relative to computation directories. Presence of such a file in
  `git ls-files` → **revise**.

- **C5.2 Transient server and orchestration state must not be committed.**
  Any file that encodes transient server or orchestration state — job
  queues, dispatch priority lists, process locks, runtime configuration
  written by a server process — must not appear in `git ls-files`. Such
  files block `git merge --ff-only` on any server where they are modified
  locally. Presence in `git ls-files` → **fail**. `.gitignore` absence for
  a known queue or dispatch-config path → **revise**.

---

## Anti-patterns (quick audit list)

Any of these in a diff or audit is an automatic finding:

| Anti-pattern | Rule |
| --- | --- |
| Expensive computation runs unconditionally, no cache check | C1.1, C1.2 |
| Cache file with generic name shared across different inputs | C1.3 |
| Same logic copy-pasted ≥3 times | C2.1 |
| Ad hoc top-level function in a test/make script, copied elsewhere | C2.2 |
| Public intrinsic with no test assertion anywhere | C3.1 |
| Test file outside the canonical test folder | C3.2 |
| Tautological or single-input assertion | C3.5 |
| New intrinsic merged without any new or updated test | C3.6 |
| PR touching shared intrinsic with no blast-radius audit | C4.1 |
| Blast-radius caller with no regression test | C4.2 |
| Ad hoc expected-output golden file outside `expected/` | C4.4 |
| Slow regression test (>30 s) with no slow marker | C4.5 |
| Computation output file present in `git ls-files` | C5.1 |
| Runtime queue or dispatch-config file tracked in git | C5.2 |

---

## Enforcement and companions

- **`check-computing-policy`** (this subdomain) — audits a diff, a
  package, or a whole project against the C-rules; returns approve / revise
  / fail with rule IDs and triggering files. Read-only (PP1.3).
- **`new-computing-policy`** (this subdomain) — the sole write path for
  C-rules (PP1.4). Use for adding, amending, or deprecating C-rules.
- **`check-magma-hygiene`** (`../magma/skills/`) — audits M-rules; defers
  to C-rules for caching and DRY findings.
- **`is-good-test`** (mathcity skills) — the quality bar behind C3.x;
  wraps `is-good-experiment` on the question "does X work?".
- **`profile-magma`** (this subdomain) — the harness for C1.5 performance
  bead evidence.

---

## Change Log

| Date | Change | Rationale |
| --- | --- | --- |
| 2026-07-12 | Initial draft, 17 rules across 4 pillars | the human adjudicator directive: computing/testing policy for mathcity; scaffolded by outside-agent session |
| 2026-07-19 | Add Pillar 5 (C5.1–C5.2): repository hygiene for computation artifacts | the human adjudicator approved; motivated by hecke #335 server incident — 4 tracked log files blocked `git merge --ff-only` on aia-s27 |
