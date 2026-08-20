---
name: gate-test-execution-silent
description: >-
  G14 gate (test-execution-silent). Pure check: emits PASS or FAIL with
  one-sentence reason. Input is a brief markdown path. FAILS when the brief
  carries no test-execution tri-state declaration AND no resolvable execution
  evidence in §5. Trigger on "run G14", "check test-execution gate",
  "gate-test-execution-silent <path>", or when gate-keep invokes G14 from the
  registry. Never edits the brief; never closes beads. See improve-test-execution-silent
  for auto-repair.
---

> **Canonical copy**: `mathcity.gate-test-execution-silent` in this mathcity pack.
> Materialized agent-skills copies are fallback only; never edit those copies directly.

# gate-test-execution-silent (G14)

Gate G14 — `test-execution-silent` — from the brief-pipeline registry
(`<mathcity-pack-root>/assets/brief-pipeline/gates.toml`).

**Policy spec**: bead `he-8akk` (the human adjudicator 2026-06-23 12:08 −10; promoted to registry 2026-06-23 15:02 −10).

**What it catches**: briefs that are *silent* on whether tests were run — no
tri-state declaration, no evidence in §5. Distinct from G1 (which checks that
if tests *are* claimed, the evidence is structured correctly).

## Input

Brief markdown file path. Accepts any of:

- Explicit argument: `gate-test-execution-silent /path/to/brief.md`
- Environment: `GC_BRIEF_PATH` or `gc.brief.path` bead metadata
- Fallback: first `.beads/briefs/.staging/*/brief.md` found

## Check procedure (two steps)

Both check scripts ship in the pack at `<mathcity-pack-root>/assets/scripts/checks/`.
No rig carries a `.gc/scripts/checks/` — nothing in gascity installs one — so resolve
`<mathcity-pack-root>` at runtime from the `Source:` line of
`gc order show brief-review-patrol`. It is the city.toml import source, which is not
necessarily `<city-root>/mathcity`.

### Step 1 — declaration check

If the check script exists, run it:

```sh
GC_BRIEF_PATH="<path>" sh <mathcity-pack-root>/assets/scripts/checks/gate-test-execution-declaration.sh
```

If the script is unavailable, apply the grep directly:

1. **Accept** if the brief frontmatter contains a top-level `test-execution:` line matching:
   ```
   ^test-execution:[[:space:]]+(PASSED|NOT APPLICABLE|REQUIRED)
   ```
   (dash or em-dash separator allowed after the state word).

2. **Also accept** the legacy `gate_status` block format (briefs produced before the
   tri-state field was codified):
   ```yaml
   gate_status:
     G14_test_execution_silent: PASS
   ```
   Any `G14_test_execution_silent: PASS` value (case-insensitive match) is treated as PASS; `FAIL` or any negative value is FAIL.

3. **FAIL** with `gate_blocked_reason: test-execution-unstated` when:
   - No `test-execution:` line exists AND no `G14_test_execution_silent` key exists.
   - A `test-execution:` line exists but does not match any accepted state.
   - `G14_test_execution_silent: FAIL` or any non-PASS value.

### Step 2 — evidence check (PASSED claims only)

Only when step 1 found `test-execution: PASSED` or `G14_test_execution_silent: PASS`, verify
that §5 (or a cited artifact) contains all three evidence fields. Run:

```sh
GC_BRIEF_PATH="<path>" sh <mathcity-pack-root>/assets/scripts/checks/gate-test-execution-evidence.sh
```

Or grep directly for:

1. **Command** — a fenced code block, `Command:`, `Cmd:`, `magma -b`, `Attach(`, or `LoadPackage(`.
2. **Exit code** — `exit 0`, `exit: 0`, `Exit code: 0`, `returned 0`, or any `exit[: ]+<digit>` pattern.
3. **Wall time** — `real <N>`, `Elapsed:`, `Wall time:`, `wall: <N>`, or ISO-8601 `PT<N>S`.

"The test file exists at <path>" is **not** execution evidence. Absent evidence FAILS with
`gate_blocked_reason: test-execution-evidence-incomplete`.

Step 2 is **skipped** when step 1 found `NOT APPLICABLE` or `REQUIRED`.

## Output

Emit exactly one of:

```
PASS — test-execution declaration found: <state>
FAIL — gate_blocked_reason: test-execution-unstated — <one-sentence reason>
FAIL — gate_blocked_reason: test-execution-evidence-incomplete — missing: <fields>
```

No other output. Do NOT print a verdict for the brief as a whole; this gate
reports only G14 status.

## Throwback signal

When this gate emits FAIL, the shuffler or gate-keep orchestrator MUST:

1. Move the brief to `.beads/briefs/.pile/.rejected/test-execution-silent/`.
2. Append one entry to `.beads/briefs/decisions/decisions.jsonl`:
   `{"brief": "<slug>", "verdict": "gate-blocked-test-execution-silent", "at": "<ISO-8601>"}`.
3. Nudge the brief-prep author to re-run tests and attach evidence OR add
   `test-execution: NOT APPLICABLE — <reason>` if genuinely inapplicable.
4. No human adjudication; this gate is a no-brainer auto-throwback.

## Exempt classes

| Class | Condition | Treatment |
|---|---|---|
| Pure-docs / policy / inventory | Brief artifact is a policy or docs-only bead with no code/test changes | `NOT APPLICABLE — docs-only` is a valid declaration |
| Test-execution-request brief-type | Brief is a `test-execution-request-*` brief (asking *for* a test run, not reporting one) | `REQUIRED — pending request <slug>` is valid; gate passes step 1, skips step 2 |
| Prior `gate_status.G14_test_execution_silent: PASS` | Brief was produced before tri-state field was codified | Accept as PASS (backwards-compatible); no re-check needed |

## Version history

- **v1.0** (2026-07-12, `he-8akk`): initial implementation.
  Detection: tri-state `test-execution:` frontmatter + legacy `gate_status.G14_test_execution_silent` compat.
  Evidence check delegates to `<mathcity-pack-root>/assets/scripts/checks/gate-test-execution-evidence.sh`.
