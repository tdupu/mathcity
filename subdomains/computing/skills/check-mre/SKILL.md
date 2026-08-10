---
name: check-mre
description: Check whether an MRE (Minimum Reproducible Example) file submitted by an agent satisfies the project's MRE policy at .claude/MRE-POLICY.md. Use this skill whenever an agent reports they have committed or pushed an MRE for review, whenever the user says "check this MRE", "verify the MRE", "does this satisfy policy", "is this MRE acceptable", or whenever an MRE file is being prepared for attachment to an issue. Returns APPROVED if all requirements pass (then the user may merge / attach to issue / advance to the next stage), or REJECTED with a precise list of missing requirements and a pointer to the policy file.
---

# check-mre

This skill enforces the MRE policy in `.claude/MRE-POLICY.md`. It exists because agents writing MREs under time pressure tend to forget specific requirements (timing prints, affected-items list, naming convention), and the cost of a malformed MRE compounds: it ships, an agent later tries to use it for a regression check, the timing is missing so they can't tell if the bug is real, and the cycle restarts. A short policy check at submission time keeps the test corpus useful.

## What this skill does

Given the path to an MRE file (typically `magma/test/test-<N>-mre*.mag`), this skill:

1. Loads `.claude/MRE-POLICY.md` and the MRE file.
2. Checks each policy requirement against the file.
3. Returns either:
   - **APPROVED** — every requirement satisfied, MRE can advance (be attached to its issue, merged, run on UPF, etc.)
   - **REJECTED** — list the specific failed requirements with line numbers from the policy and concrete instructions on what to add.

## Inputs

Usually one of:
- An explicit file path: `magma/test/test-308-mre.mag`
- A branch name where an MRE was added: walk `git diff origin/master` to find new `test-*-mre*.mag` files
- The issue number: look for `test-<N>-mre*.mag` in `magma/test/`

If the user gives an issue number with no file path, search `magma/test/` for `test-<N>-mre*.mag` and report what was found.

## Checks (mapped to policy sections)

### 1. Naming (`§ Naming` in policy)

The filename must match `test-<issue_number>-mre[-description].mag`. If it's something like `test-OOM-ranks-gamma0-m8-11-1.mag` (no issue number prefix), flag it.

**Failure example**: `test-OOM-ranks-gamma0.mag` → reject, point to `§ Naming`, suggest `test-317-mre-ranks-gamma0-m8-11-1.mag`.

### 2. Header block (`§ Required content → Header block`)

The file must open with a `/* ... */` block containing at minimum:
- `TIMING:` line with concrete CPU/wall numbers (not a placeholder)
- `AUTHOR:` line (agent ID, session UUID, or initials)
- `LAST RUN:` line with date + machine (`local` or `aia-s27`)
- `STATUS:` line with one of: `PASSES while bug present`, `CONFIRMED FIXED <date>`, `INVERT after fix`, `REGRESSION TEST — must remain PASS`
- `AFFECTED ITEMS:` block listing every known item that exhibits the failure mode, even if the MRE only reproduces one. Each entry should have the full label and relevant metadata (pdet, hrank, conductor, index — whatever applies). This is the cross-reference target for the dispatcher shitlist.

If any of these are missing, point at the specific section in the policy and quote the required line.

### 3. Timing instrumentation (`§ Timing at first print`)

Grep the file for:
- `T0_wall := Realtime();` near the top
- `T0_cpu  := Cputime();` (or `Cputime()` capture) near the top
- An early `printf` that includes both wall and CPU using `Realtime() - T0_wall` and `Cputime(T0_cpu)` (or similar)
- A final `printf` doing the same at the end

If the first `printf` is just "starting..." without timing numbers, that's a fail.

### 4. Affected items list

Beyond just appearing in the header, the AFFECTED ITEMS list should:
- Have at least one entry (it can't be empty)
- Include the order label and the item label for each entry (e.g. `2.7.m7.28.14.1.7.7.1.1.11.2`)
- Note relevant numeric metadata in brackets (`[pdet=11, hrank=23]`)

If the MRE was filed against an issue that lists multiple affected items, cross-check the issue body or comments — if items are mentioned in the issue but missing from the header, flag it. (Run `gh issue view <N> --comments` if needed.)

### 5. Polarity (`§ Polarity`)

Whatever STATUS line was declared must match the assertions:
- `PASSES while bug present` → expect `assert not IsZero(...)` or equivalent failure-witnessing assertion. There should be a comment like `// INVERT after fix lands` near the final assert.
- `REGRESSION TEST` → expect `assert ...` of a positive condition.

If STATUS says one thing but the asserts do the other, reject.

### 6. Committed (`§ Run, time, commit`)

The file must be in git history (`git log -- <path>` returns at least one commit). If it's untracked (`git status` shows it as `??`), reject — uncommitted MREs are not accepted.

### 7. File size (`§ File size target`)

Soft check: warn if > 100 lines but don't reject. If significantly over (say > 200 lines), suggest splitting into a fixture helper + the MRE.

## Output format

Use this exact structure so the user can scan it:

```
=== check-mre result for <path> ===

POLICY: .claude/MRE-POLICY.md (as of <date>)
ISSUE:  <issue number if derivable from filename>

Checks:
  [✓] Naming
  [✗] Header block — missing TIMING, AUTHOR, LAST RUN
  [✓] Timing instrumentation
  [✗] Affected items — no AFFECTED ITEMS section in header
  [✓] Polarity
  [✓] Committed (at <commit>)
  [✓] File size (<N> lines)

VERDICT: REJECTED

To fix:
  1. Add a TIMING line to the header (see policy §"Header block").
     Example: TIMING: CPU=145.3s wall=312s on aia-s27 2026-06-13
  2. Add an AUTHOR line (your session UUID or initials).
  3. Add a LAST RUN line with date + machine.
  4. Add an AFFECTED ITEMS block listing every known label that
     exhibits this failure mode (see policy §"Header block").

Re-run /check-mre <path> after fixing.
```

If everything passes:

```
=== check-mre result for <path> ===

POLICY: .claude/MRE-POLICY.md (as of <date>)
ISSUE:  #<N>

Checks:
  [✓] all 7 categories

VERDICT: APPROVED

Ready to advance:
  - Attach to issue: gh issue comment <N> --body "MRE: <path> @ <commit>"
  - Merge if on a feature branch
  - Schedule a UPF run if not already timed there
```

## Tone

Be precise but not punitive. The agent is under time pressure and may have written a working MRE that just needs a header block. Quote the policy verbatim when rejecting so they can copy-paste the fix. Don't lecture; just point.

## Edge cases

- **Bare smoke test, no MRE polarity**: if the file is more of a smoke/regression test than a bug repro, the policy still applies (STATUS becomes `REGRESSION TEST`) but the AFFECTED ITEMS list can be just the order/item it tests.
- **Probe scripts (`probe-*.mag`)**: probes are not MREs and are exempt from this policy. If the user points at a `probe-*.mag` and asks for a check, note that probes are exploratory and don't need to satisfy this policy.
- **MRE on a branch that's not yet pushed**: still check the file content; flag that it isn't pushed yet but don't treat that as a policy failure — pushing is a workflow step, not a policy requirement.
- **MRE that legitimately can't be timed locally**: if the MRE needs a 24h compute on UPF that's still running, accept a `TIMING: pending — running on aia-s27 as of <date>` placeholder ONCE; on the next check-mre pass it must be filled in with real numbers.

## What approval means

APPROVED means the MRE satisfies policy. It does NOT mean:
- The MRE actually reproduces the bug (that requires running it)
- The MRE's diagnosis is mathematically correct
- The MRE's code is bug-free

Those are separate concerns handled by peer review of the underlying PR. This skill is a structural/process gate.
