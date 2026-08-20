---
schema: gc.build.plan-review.v1
workflow:
  id: gsp-ycmp6
  formula: build-basic-briefed
producer:
  formula: build-basic-briefed
  stage: plan-review
  attempt: 1
status: approved
plan_path: mathcity/skills/decisions-to-briefs/implementation-plan.md
---

# Plan Review: decisions-to-briefs SKILL.md — git-op action-block prohibition

**Verdict: APPROVED — ready for decomposition. No blockers identified.**

## Requirements Traceability

All 6 REQ IDs are covered. Plan trace.coverage and the Markdown coverage table
are consistent with the requirements document. Each requirement maps to at least
one named plan change with an explicit acceptance criterion:

| REQ | Plan Change | AC |
|---|---|---|
| REQ-001 (enumerate git commit) | Change 3 — extend prohibited list | AC-1 |
| REQ-002 (autonomous-fork rule) | Change 3 — add autonomous-fork paragraph | AC-2 |
| REQ-003 (PROHIBITED table) | Change 2 — insert after action-item types table | AC-3 |
| REQ-004 (local-commit red flag) | Change 4 — add fifth rationalization row | AC-4 |
| REQ-005 (stays-out cites git writes) | Change 1 — update stays-out Symptoms cell | AC-5 |
| REQ-006 (backward compat) | Non-changes section + AC-6 critical-review | AC-6 |

OQ-1 (`git commit --amend` treatment) is resolved in the plan body (same shape
as a fresh commit, covered by Changes 2–3). OQ-2 (machine-readable prohibited
list in front matter) is deferred as prose-sufficient for v0.2 — appropriate.

## Task Boundaries

All changes target one file:
`mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`

Each change identifies a specific location with before/after text:

- **Change 1**: single cell in the `stays-out` row — surgical.
- **Change 2**: insert a paragraph + table between the action-item types table
  and `## HARD SAFETY INVARIANT` — one logical block.
- **Change 3**: replace one paragraph, add one paragraph — two contiguous
  edits in the same section.
- **Change 4**: append one table row — atomic.

Each change is independently implementable as a distinct `Edit` call. The
non-changes section explicitly enumerates the 7 preserved action-item types,
giving the implementer a clear diff target.

**Minor line-reference note (non-blocking):** Change 2 says "after current
line 95" but line 94 holds the last table row and line 95 is blank. The
semantic description ("after §Action-item types table, before ##
HARD SAFETY INVARIANT") is unambiguous; the implementer should use it, not
the line number.

## Test Commands

Grep tests for AC-1 through AC-5 are concrete and runnable against the post-edit file:

```bash
grep -i "git commit" SKILL.md          # AC-1
grep -i "autonomous" SKILL.md          # AC-2
grep -i "prohibited" SKILL.md          # AC-3
grep -i "local commit" SKILL.md        # AC-4
grep -i "git" SKILL.md                 # AC-5 (verify match is in shape table row)
```

AC-5's verification description ("inside the shape table context") is slightly
loose as written; a sharper formulation is:

```bash
grep -A 6 "stays-out" SKILL.md | grep -i "git"
```

Either form is functionally adequate. AC-6 (backward compat) uses
`critical-review`, which is the right tool for a prose/skill artifact. No
blocked or missing test commands.

## Risk Assessment

| Concern | Disposition |
|---|---|
| Risky files | One file, text only. No infrastructure, database, or API surface. |
| Public interfaces | Action-block YAML schema is unchanged. Existing `type` values are untouched. |
| Rollback | `git revert` on the single commit is sufficient. |
| Regression | Non-changes section explicitly lists 7 preserved types; AC-6 confirms via critical-review. |
| Migration | None required. |

Overall risk: **LOW**. The plan is conservative by design — closes a safety
loophole by adding prohibition text, not by removing or restructuring existing
capability.

## Pre-Decomposition Readiness Summary

All four readiness checks pass:

1. **Requirements traceability** ✓ — every REQ maps to a plan change and an AC.
2. **Task boundaries** ✓ — 4 atomic edits to one file, each with named location and before/after.
3. **Test commands** ✓ — 5 grep tests + critical-review; AC-5 phrasing slightly loose but functional.
4. **Risk** ✓ — single text file, no public interface changes, trivial rollback.

Ready to proceed to decomposition.
