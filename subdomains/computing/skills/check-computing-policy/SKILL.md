---
name: check-computing-policy
description: >-
  Audit computation code, a diff, or a project against the Computing Policy
  (mathcity/subdomains/computing/POLICY.md, C1.x–C4.x rules). Use when the
  user says "check computing policy", "run check-computing-policy", "is this
  code compliant", "audit caching / test coverage / DRY / regression suite",
  before merging a branch that touches computation logic or test infrastructure,
  or when a blast-radius or caching concern is raised. Read-only: reports
  drift but never mutates bead state, files, or config (PP1.3). Returns
  approve / revise / fail with violated C-rule IDs and triggering files.
  Companion to new-computing-policy (sole write path). Policy home:
  mathcity/subdomains/computing/POLICY.md.
---

# check-computing-policy

Audit computation code against the C-rules of
[POLICY.md](../../POLICY.md). Read the policy first — it is the
authoritative source. This skill checks WHAT IS, not what was planned.

> **Status guard (PP2.1):** If `POLICY.md` header shows `Status: Draft`,
> the policy is not yet enforceable. Run this audit informally and report
> any clearly non-compliant items as informational findings only.
> Return **defer** on the overall verdict until the human adjudicator adopts the policy.

> **Magma overlap:** Where a finding could be cited under both C-rules and
> M-rules (e.g., test coverage), cite BOTH (PP6.1 precedence: M-rules win
> for Magma packages; C-rules are the general baseline). This skill audits
> the C-rule surface only — run `check-magma-hygiene` for the M-rule surface.

---

## Scope

Determine the audit target from context:

| Shape | What to check |
| --- | --- |
| Single file | That file's caching patterns (C1), duplication (C2), test coverage (C3) |
| Diff / branch | Every touched `.mag`, `.py`, `.sh`, `make/`, `test/` file; check C1–C4 on the diff surface plus its obligations |
| Whole project | Full `magma/`, `scripts/`, `make/`, and `magma/test/` trees |

---

## Step 0 — Discover project layout

```bash
PROJECT=<repos-root>/hecke   # or the project in scope
ls "$PROJECT"/magma/package-*.mag 2>/dev/null | wc -l
ls "$PROJECT"/magma/test/ 2>/dev/null | wc -l
ls "$PROJECT"/magma/test/README-tests/ 2>/dev/null | wc -l
ls "$PROJECT"/magma/make/ 2>/dev/null | head -10
ls "$PROJECT"/scripts/ 2>/dev/null | head -10
```

If the project has no `magma/` directory, adapt paths to the project's
documented layout (check its CLAUDE.md).

---

## Check 1 — Caching and memoization (C1.x)

### C1.1 / C1.2 — Cache existence checks

Look for expensive operations (nested loops, calls to `Kernel`, `SNF`,
`SmithForm`, `Eigenvalues`, `FundamentalDomain`, or any call that appears
with a comment like `// slow`) that do not check for a cached file first:

```bash
# Find Magma files that compute expensive things without a cache guard
grep -rn "SmithForm\|Kernel\|FundamentalDomain\|SNF\|Eigenvalues" \
  "$PROJECT"/magma/package-*.mag \
  "$PROJECT"/magma/make/ 2>/dev/null \
  | grep -v "if.*Exists\|Open.*DATA\|Read.*DATA\|PrintFile.*DATA" \
  | head -20
```

For each hit: does the surrounding context check for a `DATA/` file before
calling? If no guard → flag as C1.1 / C1.2 candidate (require human
inspection to confirm; these are signals, not automatics).

### C1.3 — Cache key determinism

```bash
# Check for generic cache filenames not parameterized by level/discriminant/etc.
grep -rn 'PrintFile.*"result\|PrintFile.*"output\|PrintFile.*"cache\|PrintFile.*"data"' \
  "$PROJECT"/magma/ 2>/dev/null | head -10
```

Generic names in cache writes → C1.3 finding.

### C1.6 — Cache contract documented

For each script or intrinsic that writes to `DATA/`, confirm its README
entry mentions the cache location. Quick check: grep README(s) for `DATA/`:

```bash
grep -n "DATA/" "$PROJECT"/README*.md "$PROJECT"/magma/README*.md 2>/dev/null | head -20
```

---

## Check 2 — DRY / Code factoring (C2.x)

### C2.1 — Three-copy rule

Look for code blocks repeated ≥3 times across files:

```bash
# Find repeated boilerplate patterns in scripts (crude but catches obvious cases)
# Check for identical function definitions across scripts
grep -rn "^function " "$PROJECT"/scripts/ 2>/dev/null | sort | head -20
# Check for repeated 5+ line blocks in make/ scripts
# (Manual inspection required for Magma; use this as a flag list)
find "$PROJECT"/magma/make/ -name "*.mag" -exec wc -l {} \; 2>/dev/null | sort -n | head -20
```

Also check: any `function ` definitions inside `magma/test/*.mag` files
that duplicate logic from a package:

```bash
grep -rn "^function " "$PROJECT"/magma/test/*.mag 2>/dev/null | head -15
```

### C2.2 — Top-level functions in test/make scripts

```bash
grep -rln "^function " \
  "$PROJECT"/magma/test/*.mag \
  "$PROJECT"/magma/make/*.mag 2>/dev/null
```

Each hit is a C2.2 candidate — functions in test/make files that are
copied elsewhere must be promoted to a package intrinsic.

---

## Check 3 — Intrinsic and function testing (C3.x)

### C3.1 — Every public intrinsic has test coverage

```bash
# List all intrinsics declared in packages
grep -rh "^intrinsic " "$PROJECT"/magma/package-*.mag 2>/dev/null \
  | sed 's/(.*//; s/intrinsic //' | sort -u > /tmp/intrinsics-list.txt

# List all intrinsic names that appear in test files
grep -rh "intrinsic\|[A-Z][a-zA-Z]*(" "$PROJECT"/magma/test/*.mag 2>/dev/null \
  | grep -o '[A-Z][a-zA-Z]*' | sort -u > /tmp/tested-names.txt

echo "Intrinsics declared: $(wc -l < /tmp/intrinsics-list.txt)"
echo "Names appearing in tests: $(wc -l < /tmp/tested-names.txt)"
```

Cross-reference to find uncovered intrinsics (C3.1 gap):

```bash
comm -23 /tmp/intrinsics-list.txt /tmp/tested-names.txt | head -20
```

Note: this is a signal check — the grep above is imprecise; findings need
human confirmation before issuing "fail".

### C3.2 — Test code in designated folder

```bash
# Find test-NN-* files outside the canonical test directory
find "$PROJECT" -name "test-[0-9]*" \
  -not -path "*/magma/test/*" \
  -not -path "*/.claude/*" \
  -not -path "*/.git/*" 2>/dev/null | head -10
```

Any test file outside the canonical folder → C3.2 finding.

### C3.3 — Test file naming

```bash
# Find test files without the NN numeric prefix
find "$PROJECT"/magma/test -maxdepth 1 -name "test-*" \
  | grep -v "test-[0-9][0-9]*-" \
  | head -15
```

Un-numbered test files (e.g., `test-snf-quick.mag`) → C3.3 finding.

### C3.4 — Independent runnability

For each test file in the README-tests suite, confirm the header has a
run command:

```bash
for f in "$PROJECT"/magma/test/README-tests/test-*.mag; do
  if ! grep -q "// Run from\|// magma " "$f" 2>/dev/null; then
    echo "MISSING run command: $f"
  fi
done
```

### C3.5 — Assert quality

```bash
# Flag tautological asserts: assert x eq x (same var both sides)
grep -rn "assert.*\(.*\) eq \1" "$PROJECT"/magma/test/ 2>/dev/null | head -10

# Flag single-argument patterns where one example is all that runs
# (look for test files with only 1 assert)
for f in "$PROJECT"/magma/test/README-tests/*.mag; do
  n=$(grep -c "^assert\|assert " "$f" 2>/dev/null || echo 0)
  if [ "$n" -le 1 ]; then
    echo "SINGLE-ASSERT (C3.5 risk): $f ($n asserts)"
  fi
done
```

---

## Check 4 — Regression testing (C4.x)

### C4.1 / C4.2 — Blast radius coverage

Given a specific changed intrinsic (from diff context), enumerate callers:

```bash
# Replace <intrinsic_name> with the actual name from the diff
INTRINSIC="<intrinsic_name>"
grep -rln "$INTRINSIC" "$PROJECT"/magma/package-*.mag 2>/dev/null
```

For each caller package found, verify a test exists:

```bash
# Check whether the caller package has corresponding test coverage
grep -rln "$INTRINSIC\|<caller_package_topic>" \
  "$PROJECT"/magma/test/ 2>/dev/null
```

If no test found for a caller → C4.2 finding.

### C4.4 — Expected-output files in `expected/`

```bash
# Check for golden files outside the expected/ directory
find "$PROJECT"/magma/test -name "*.expected" \
  -not -path "*/expected/*" 2>/dev/null | head -10
find "$PROJECT" -name "*.expected" \
  -not -path "*/.claude/*" \
  -not -path "*/.git/*" \
  -not -path "*/expected/*" 2>/dev/null | head -10
```

### C4.5 — Slow test markers

```bash
# Find test files > 30s that lack a SLOW marker
# (As a proxy, look for tests that probe FundamentalDomain or SNF without SLOW)
grep -rln "FundamentalDomain\|SmithForm\|Eigenvalues" \
  "$PROJECT"/magma/test/ 2>/dev/null \
  | while read f; do
    if ! grep -q "// SLOW\|# SLOW" "$f"; then
      echo "POSSIBLY SLOW WITHOUT MARKER: $f"
    fi
  done
```

---

## Check 5 — Repository hygiene (C5.x)

Enforcing C5.x requires model judgment, not glob matching. The classification
of "is this file a computation output?" or "is this file runtime state?" is
a semantic property that file extensions alone cannot determine. Use a
@sonnet-tier call for judgment over `git ls-files` output.

### C5.1 — Computation output files not tracked

```bash
# Collect all tracked files in the project
git -C "$PROJECT" ls-files > /tmp/c5-tracked-files.txt
wc -l /tmp/c5-tracked-files.txt
```

Pass the file list to a model call with this prompt:
> "You are auditing a repository for computing policy C5.1. From the
> following list of tracked files (from `git ls-files`), identify any that
> appear to be computation output files: output logs, audit lists, generated
> manifests, dispatch lists, or intermediate artifacts produced by running
> a script or computation. These should NOT be in version control.
> Return only the file paths that are likely computation outputs, one per
> line. If none, return 'none'. List: [paste /tmp/c5-tracked-files.txt]"

For each identified file: flag as C5.1 finding → **revise** (add to
`.gitignore`; run `git rm --cached <file>`).

### C5.2 — Runtime queue and dispatch-config files not tracked

Using the same `git ls-files` output, pass to a model call:
> "From the following list of tracked files, identify any that appear to
> encode transient server or orchestration state: job queues, dispatch
> priority lists, process locks, or runtime configuration written by a
> server process (e.g., priority.conf, queue files, server job registries).
> These must not be committed as they change during server operation and
> block `git merge --ff-only`. Return only the file paths, one per line.
> If none, return 'none'. List: [paste /tmp/c5-tracked-files.txt]"

For each identified file: flag as C5.2 finding → **fail** (remove from
tracking immediately; add to `.gitignore`).

---

## Verdict

After each check, emit one of:
- **approve (section)** — no drift found
- **revise (section)** — specific rules violated; cite rule ID + one-line
  remediation per item
- **defer (section)** — a human call is needed; state the open question

Overall verdict = worst of per-section verdicts. **Never emit "reject"** —
that applies only to artifacts, not audits (PP2.1 verdict vocabulary).

Report format:

```
## check-computing-policy audit — <date>

### Trinity (PP1.1)
verdict: approve | revise | defer
[items if revise/defer]

### C1 — Caching
verdict: ...
[findings: C1.x — <file>:<line> — one-line description]

### C2 — DRY / factoring
verdict: ...
[findings]

### C3 — Intrinsic testing
verdict: ...
[findings]

### C4 — Regression testing
verdict: ...
[findings]

### C5 — Repository hygiene
verdict: ...
[findings: C5.x — <file> — one-line description]

## Overall: approve | revise | defer | fail
[Summary of all revise/defer/fail items with rule IDs]
```

---

## Trinity self-check

As the first step of any audit, verify the trinity is intact:

```bash
ls <mathcity-pack-root>/subdomains/computing/POLICY.md
ls ~/.claude/skills/check-computing-policy 2>/dev/null \
  || ls <repos-root>/agent-skills/skills/check-computing-policy 2>/dev/null
ls ~/.claude/skills/new-computing-policy 2>/dev/null \
  || ls <repos-root>/agent-skills/skills/new-computing-policy 2>/dev/null
```

Missing any leg → PP1.1 finding (revise: file trinity-gap bead).

---

This skill is **read-only** (PP1.3). Never run `bd close`, `bd update`,
`git commit`, or any state-mutating command during an audit. If you find a
problem, describe it and propose the fix — let the human adjudicator or `new-computing-policy`
apply it.
