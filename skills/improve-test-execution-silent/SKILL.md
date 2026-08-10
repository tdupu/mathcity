---
name: improve-test-execution-silent
description: >-
  G14 improve step (test-execution-silent). Given a brief that failed the
  gate-test-execution-silent check, attempt auto-repair: if the brief is
  simply silent (no declaration), add an explicit `test-execution: REQUIRED —
  not yet run` line so the gate-block is stated rather than absent. If the
  brief claimed PASSED but evidence is incomplete, emit ESCALATE (cannot
  auto-run tests). Companion to gate-test-execution-silent. Trigger on "improve
  G14", "fix test-execution-silent gate failure", or when gate-keep invokes the
  improve step after a G14 FAIL. Identity on passing input: re-running on a
  brief that already passes G14 is a no-op. Never runs tests; never closes
  beads; never pushes commits.
---

> **Canonical copy**: `mathcity.improve-test-execution-silent` in this mathcity pack.

# improve-test-execution-silent (G14 repair)

Companion to `gate-test-execution-silent`. Implements the `improve-X` half of
the gate-keep trinity for G14. Operates on a brief that just failed the gate
check and either auto-repairs the brief OR emits `ESCALATE`.

**Policy spec**: bead `he-8akk`.

## Inputs

1. **brief path** — absolute path to the failing brief markdown file.
2. **fail reason** — the `gate_blocked_reason` string emitted by `gate-test-execution-silent` (one of: `test-execution-unstated`, `test-execution-evidence-incomplete`).

## Identity-on-passing-input rule

Before attempting any repair, run `gate-test-execution-silent` on the brief.
If it already emits PASS, return `PASS — already passing; no edit needed`.
Do not modify the brief.

## Repair procedure

### Case A — `test-execution-unstated` (silent brief)

The brief carries no `test-execution:` field and no `gate_status.G14_test_execution_silent`
entry. The repair adds an explicit gate-block declaration.

**Steps:**

1. Locate the brief's YAML frontmatter block (the `---` ... `---` section at the top).
2. Insert one line immediately after the last `---` opening or before the closing `---`,
   in the frontmatter:
   ```yaml
   test-execution: REQUIRED — not yet run
   ```
3. Verify the repaired brief now passes step 1 of `gate-test-execution-silent`.
4. Return `PASS — added test-execution: REQUIRED — not yet run declaration`.

**Rationale**: a brief that silently omits the declaration is ambiguous.
`REQUIRED — not yet run` is an honest state that makes the gap explicit and
triggers the auto-throwback flow cleanly. The brief-prep author sees the
explicit gate-block and re-submits with actual evidence.

Do NOT add `PASSED` or fake evidence. The author must re-run the tests themselves.

### Case B — `test-execution-evidence-incomplete`

The brief declared `PASSED` but §5 is missing one or more of: command, exit
code, wall time.

**Action**: emit `ESCALATE — cannot auto-produce test execution evidence; brief-prep author must re-run tests and record command + exit code + wall time`.

Do NOT modify the brief. The repair requires actual test execution that this
skill cannot perform.

## Output

One of:

```
PASS — already passing; no edit needed
PASS — added test-execution: REQUIRED — not yet run declaration
ESCALATE — cannot auto-produce test execution evidence; brief-prep author must re-run tests and record command + exit code + wall time
```

After a successful repair, the gate-keep orchestrator MUST re-run
`gate-test-execution-silent` to confirm the repair resolved the failure.

## Version history

- **v1.0** (2026-07-12, `he-8akk`): initial implementation.
  Case A: insert `REQUIRED` declaration. Case B: ESCALATE.
