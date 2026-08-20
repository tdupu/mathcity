---
schema: gc.build.plan.v1
workflow:
  id: gsp-ycmp6
  formula: build-basic-briefed
methodology:
  pack: gascity
  name: build-basic
producer:
  formula: build-basic-briefed
  stage: plan
  attempt: 1
status: approved
trace:
  upstream:
    - path: mathcity/skills/decisions-to-briefs/requirements.md
      hash: sha256:2bd2dabb3b397541dedc7c51c128d22d4f9233e20eeb097648af43e9c8d081f2
    - path: mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md
      hash: git:8b879c51dc4d4661ee1cc36bf3850f9cd68c5c26
  coverage:
    - id: REQ-001
      status: covered
    - id: REQ-002
      status: covered
    - id: REQ-003
      status: covered
    - id: REQ-004
      status: covered
    - id: REQ-005
      status: covered
    - id: REQ-006
      status: covered
---

# Implementation Plan: decisions-to-briefs SKILL.md — git-op action-block prohibition

## Coverage

| ID | Status |
| --- | --- |
| REQ-001 | covered |
| REQ-002 | covered |
| REQ-003 | covered |
| REQ-004 | covered |
| REQ-005 | covered |
| REQ-006 | covered |

## Summary

During incident gt-hjk388, an autonomous Fable fork executing `decisions-track`
action-blocks committed directly to `~/repos/hecke` without passing through the
`authorize-git-operation` gate. The existing §HARD SAFETY INVARIANT listed
`git push / force-push / merge / branch or tag deletion` as prohibited, but omitted
`git commit`, creating an exploitable loophole ("local commits are reversible dispatch").

This plan updates the single source file —
`mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md` — with four
targeted edits that close the loophole without altering any existing valid
action-item type or non-git decision flow.

## Current System

**File:** `mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md` (v0.1, 169 lines)

Key locations in the current file:

| Section | Location | Current state | Gap |
|---|---|---|---|
| §Shape classification table | Lines 50–57 | `stays-out` row cites "irreversible, server-live-write, or user-skill-touching" | Does not call out git writes by name |
| §Action-item types table | Lines 87–95 | Lists 6 valid types; no PROHIBITED category | No mention of prohibited type values |
| §HARD SAFETY INVARIANT — prohibited list | Lines 108–110 | `git push / force-push / merge / branch or tag deletion` | Missing: `git commit`, `git cherry-pick`, `git rebase`, `git merge --ff-only`, `git commit --amend` |
| §HARD SAFETY INVARIANT — red flags table | Lines 114–122 | 4 rationalization rows | Missing: "it's just a local commit" bypass row |
| §HARD SAFETY INVARIANT — autonomous fork rule | (absent) | No named rule for autonomous forks | No explicit prohibition text scoped to headless workers |

## Proposed Implementation

All changes are to one file:
`mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`

### Change 1 — §Shape classification: add explicit git-write call-out (REQ-005)

**Location:** `stays-out` row in the Shape classification table (current lines 50–57).

**Current `stays-out` cell (Symptoms column):**
```
irreversible, server-live-write, or user-skill-touching consequence
```

**Replace with:**
```
irreversible, server-live-write, user-skill-touching, or any git write
(commit / push / merge / cherry-pick / rebase / tag / branch-delete)
```

This makes the shape classification self-contained: a reader does not need to
cross-reference §HARD SAFETY INVARIANT to know that a git write is `stays-out`.
Closes REQ-005 / AC-5.

### Change 2 — §Action-item types: add PROHIBITED block (REQ-003)

**Location:** After the §Action-item types table (after current line 95), before
the `## HARD SAFETY INVARIANT` heading.

**Insert the following paragraph and table:**

```markdown
**PROHIBITED action-item types.** The following values MUST NOT appear as
`type` in any auto-executable action-item. A brief that uses them is malformed
and must be downgraded to `external-reminder` before deposit:

| Prohibited type | Reason |
|---|---|
| `git-commit` | git write — local commit is irrevocable from Taylor's audit trail |
| `git-commit-amend` | git write — rewrites commit history |
| `git-push` | server-live-write |
| `git-force-push` | server-live-write, destructive |
| `git-merge` | git write |
| `git-cherry-pick` | git write |
| `git-rebase` | git write, rewrites history |
| `git-tag` | git write |
| `git-branch-delete` | git write, destructive |
```

Closes REQ-003 / AC-3.

### Change 3 — §HARD SAFETY INVARIANT: extend prohibited list + add autonomous-fork rule (REQ-001, REQ-002)

**Location:** The "Concretely, NO auto-action for:" paragraph (current lines 108–110).

**Current text:**
```
Concretely, NO auto-action for: git push / force-push / merge / branch or
tag deletion ([[authorize-git-operation]] territory), `gh issue close` or
other live GitHub writes, database/server writebacks, edits to user-scope
skills (`user_skill_touching_override`), credential operations, deletion of
non-regenerable data.
```

**Replace with:**
```
Concretely, NO auto-action for: git commit / commit --amend / cherry-pick /
rebase / merge (including --ff-only) / push / force-push / branch or tag
deletion ([[authorize-git-operation]] territory), `gh issue close` or other
live GitHub writes, database/server writebacks, edits to user-scope skills
(`user_skill_touching_override`), credential operations, deletion of
non-regenerable data.

**Autonomous-fork rule.** Autonomous forks (no Taylor terminal — Fable workers,
GC agents, polecats) MUST classify ALL git-op decisions as `external-reminder`
and MUST NOT auto-execute any git write. There is no exception for "tiny",
"local-only", or "reversible-seeming" commits: a local commit is a git write.
The `authorize-git-operation` gate is Taylor's terminal; the fork surfaces the
reminder and stops.
```

Closes REQ-001 / AC-1 and REQ-002 / AC-2.

### Change 4 — §HARD SAFETY INVARIANT: add "local commit" rationalization row (REQ-004)

**Location:** The red flags rationalization table (current lines 114–122).

**Add a fifth row** at the end of the table:

```
| "It's just a local commit, not a push" | A commit IS a git write. `git push` makes it public; the commit is already irreversible from Taylor's audit trail. Cherry-pick, rebase, and merge --ff-only are the same category. |
```

Closes REQ-004 / AC-4.

### Change 5 — OQ-1 resolution: git commit --amend treated as git write (implicit in Changes 1–3)

Open Question OQ-1 (`git commit --amend` same shape as fresh commit?) is
resolved yes: Change 3 lists `commit --amend` explicitly in the prohibited list,
and Change 2's `PROHIBITED` table includes `git-commit-amend` as a type.
No separate change required; no Taylor escalation needed.

### Non-changes (REQ-006 backward-compatibility)

The following existing action-item types are untouched:

- `sling-bead` — valid, reversible dispatch
- `file-follow-up-brief` — valid, reversible
- `wire` — valid, reversible graph surgery
- `close-supersede` — valid, reopenable
- `run-skill` — valid, read-only skills only
- `external-reminder` — valid, always
- `snooze` — valid, always

The Versioning section will receive a `v0.2` entry:
```
- **v0.2 — git-op action-block prohibition** (2026-07-18, gsp-iska2 / gsp-ycmp6):
  Close Q18 loophole (gt-hjk388): extend prohibited list to include git commit
  and equivalents; add autonomous-fork invariant; add PROHIBITED type table;
  update shape classification and rationalization table.
```

## Non-Goals

- Implementing the verdict-edge executor (part b of gsp-ft64) — out of scope.
- Changing the `authorize-git-operation` skill — its scope is unchanged.
- Adding new auto-executable action-item types.
- Altering how `external-reminder` semantics work beyond clarifying mandatory
  use for git ops.
- Adding machine-readable `prohibited_action_types` front matter (OQ-2) —
  prose is sufficient for v0.2; file a follow-up bead if the verdict-edge
  executor needs schema introspection.

## Verification

| Acceptance Criterion | Verification Method |
|---|---|
| AC-1: SKILL.md enumerates `git commit` in prohibited ops | `grep -i "git commit" SKILL.md` must match |
| AC-2: SKILL.md contains explicit "autonomous" forks rule | `grep -i "autonomous" SKILL.md` must match |
| AC-3: §ACTION-BLOCK schema section contains `PROHIBITED` | `grep -i "prohibited" SKILL.md` must match |
| AC-4: Rationalization table includes "local commit" row | `grep -i "local commit" SKILL.md` must match |
| AC-5: `stays-out` row in shape table references git writes | `grep -i "git" SKILL.md` returns a match inside the shape table |
| AC-6: `sling-bead` and other non-git types remain valid | Critical review of updated skill confirms no breakage |

Post-implementation: run the 5 acceptance-criterion grep tests against the
updated SKILL.md. All 5 must match. Then run `critical-review` on the updated
file to confirm REQ-006 backward compatibility.
