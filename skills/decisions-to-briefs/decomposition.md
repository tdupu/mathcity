---
schema: gc.build.decomposition.v1
workflow:
  id: gsp-ycmp6
  formula: build-basic-briefed
methodology:
  pack: gascity
  name: build-basic
producer:
  formula: build-basic
  stage: decompose
  attempt: 1
status: approved
trace:
  upstream:
    - path: mathcity/skills/decisions-to-briefs/requirements.md
      hash: sha256:2bd2dabb3b397541dedc7c51c128d22d4f9233e20eeb097648af43e9c8d081f2
      ids:
        - REQ-001
        - REQ-002
        - REQ-003
        - REQ-004
        - REQ-005
        - REQ-006
    - path: mathcity/skills/decisions-to-briefs/implementation-plan.md
      hash: sha256:1d9f9b77b295878a3cbfed378fccaf4f90cf6e341df7314f717900ef781b89bb
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

# Decomposition: decisions-to-briefs SKILL.md — git-op action-block prohibition

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

Decomposes the approved implementation plan into 5 work-item beads and one
implementation convoy. All changes target a single file:
`mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`.

Changes 1–4 are 4 independent atomic edits (each a distinct `Edit` call to a
named location in the file). WI-005 is a post-edit verification step that
runs the 5 acceptance-criterion grep tests and a backward-compat critical
review to close AC-6.

## Selected Downstream Formulas

| Formula | Purpose |
|---|---|
| `do-work-item` | Implements each atomic edit (WI-001 through WI-004) |
| `do-work-item` | Runs verification pass (WI-005) |

Implementation target: `gc.implementation-worker`

## Implementation Convoy

**Convoy ID:** gsp-qv29d
**Title:** decisions-to-briefs-impl

| Bead | Title | Traces to |
|---|---|---|
| gsp-w3wqq | Change 1: Update stays-out row to call out git writes explicitly | REQ-005 / AC-5 |
| gsp-k0n3o | Change 2: Add PROHIBITED action-item types table to SKILL.md | REQ-003 / AC-3 |
| gsp-vywei | Change 3: Extend HARD SAFETY INVARIANT prohibited list and add autonomous-fork rule | REQ-001 / AC-1, REQ-002 / AC-2 |
| gsp-4viam | Change 4: Add local-commit rationalization row to red flags table | REQ-004 / AC-4 |
| gsp-ev1rr | Verify: Run all 5 AC grep tests and critical-review for backward compat | REQ-006 / AC-6 |

## Work Items

### WI-001 — gsp-w3wqq: §Shape classification git-write call-out (Change 1)

**Traces to:** REQ-005 / AC-5

**File:** `mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`

**Location:** `stays-out` row in the Shape classification table.

**Edit:** Replace the Symptoms column text from:
```
irreversible, server-live-write, or user-skill-touching consequence
```
to:
```
irreversible, server-live-write, user-skill-touching, or any git write
(commit / push / merge / cherry-pick / rebase / tag / branch-delete)
```

**Verify:** `grep -A 6 "stays-out" SKILL.md | grep -i "git"` must match.

---

### WI-002 — gsp-k0n3o: §Action-item types PROHIBITED table (Change 2)

**Traces to:** REQ-003 / AC-3

**File:** `mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`

**Location:** After the §Action-item types table, before `## HARD SAFETY INVARIANT`.

**Insert:**
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

**Verify:** `grep -i "prohibited" SKILL.md` must match.

---

### WI-003 — gsp-vywei: §HARD SAFETY INVARIANT prohibited list + autonomous-fork rule (Change 3)

**Traces to:** REQ-001 / AC-1, REQ-002 / AC-2

**File:** `mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`

**Location:** "Concretely, NO auto-action for:" paragraph in §HARD SAFETY INVARIANT.

**Replace current paragraph** (beginning "Concretely, NO auto-action for: git push / force-push") **with:**
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

**Verify:**
- `grep -i "git commit" SKILL.md` must match (AC-1)
- `grep -i "autonomous" SKILL.md` must match (AC-2)

---

### WI-004 — gsp-4viam: Rationalization table "local commit" row + versioning (Change 4)

**Traces to:** REQ-004 / AC-4

**File:** `mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`

**Location:** Red flags rationalization table in §HARD SAFETY INVARIANT — append fifth row.

**Add row:**
```
| "It's just a local commit, not a push" | A commit IS a git write. `git push` makes it public; the commit is already irreversible from Taylor's audit trail. Cherry-pick, rebase, and merge --ff-only are the same category. |
```

**Also add** v0.2 versioning entry in the Versioning section:
```
- **v0.2 — git-op action-block prohibition** (2026-07-18, gsp-iska2 / gsp-ycmp6):
  Close Q18 loophole (gt-hjk388): extend prohibited list to include git commit
  and equivalents; add autonomous-fork invariant; add PROHIBITED type table;
  update shape classification and rationalization table.
```

**Verify:** `grep -i "local commit" SKILL.md` must match.

---

### WI-005 — gsp-ev1rr: Verification — all 5 AC grep tests and backward-compat critical review

**Traces to:** REQ-006 / AC-6

**Depends on:** WI-001, WI-002, WI-003, WI-004 all applied.

**Task:** Run the following acceptance-criterion checks against the updated SKILL.md:

```bash
SKILL=~/repos/gascity-packs/mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md
grep -i "git commit" "$SKILL"                        # AC-1
grep -i "autonomous" "$SKILL"                        # AC-2
grep -i "prohibited" "$SKILL"                        # AC-3
grep -i "local commit" "$SKILL"                      # AC-4
grep -A 6 "stays-out" "$SKILL" | grep -i "git"      # AC-5
```

Confirm the following existing valid type names still appear (backward compat):
- `sling-bead`, `file-follow-up-brief`, `wire`, `close-supersede`, `run-skill`, `external-reminder`, `snooze`

Run critical-review on the updated SKILL.md to confirm no breakage of existing
action-item types (AC-6). All checks must pass before this bead is closed.
