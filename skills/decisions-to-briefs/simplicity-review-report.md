---
schema: gc.build.simplicity-review.v1
bead: gsp-8h0b7
reviewer_lane: simplicity
source_commit: 6ecef4d577e4549b98beae7cbd5d56ecd17fbf65
changed_file: mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md
verdict: iterate
---

# Simplicity & Maintainability Review: decisions-to-briefs v0.2

**Bead:** gsp-8h0b7  
**Source commit:** `6ecef4d577e4549b98beae7cbd5d56ecd17fbf65`  
**Changed file:** `mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`  
**Verdict:** **iterate**

## Summary

The v0.2 changes are tightly scoped to the Q18 loophole (gt-hjk388). No
extraneous modifications, no unnecessary abstractions introduced, no scope
creep. One concrete inconsistency between the HARD SAFETY INVARIANT's
"Concretely" list and the PROHIBITED table warrants a fix before merge.

---

## Finding F1 — HARD SAFETY INVARIANT "Concretely" list omits `git tag` creation (required fix)

**Location:** SKILL.md — HARD SAFETY INVARIANT section, "Concretely, NO
auto-action for:" paragraph; vs. PROHIBITED table.

**What the code says:**

HARD SAFETY INVARIANT prose (the "Concretely" list):
```
git commit / commit --amend / cherry-pick / rebase / merge (including --ff-only)
/ push / force-push / branch or tag deletion
```

PROHIBITED table entry:
```
| git-tag | git write |
```

**The gap:** The PROHIBITED table prohibits `git-tag` (tag *creation*). The
HARD SAFETY INVARIANT's "Concretely" list says "**branch or tag deletion**" —
covering only deletion. Tag creation is prohibited by schema but absent from
the HARD SAFETY INVARIANT's prose.

A writer checking the "Concretely" list (which says "Concretely" — implying
exhaustive) could conclude that `git tag my-release` is safe in an
auto-executable action item. The PROHIBITED table corrects this, but only if
they read both.

**Smallest fix:**

In the HARD SAFETY INVARIANT, replace:

```
/ push / force-push / branch or tag deletion
```

with:

```
/ push / force-push / tag (create or delete) / branch deletion
```

This aligns the prose enumeration with the PROHIBITED table's `git-tag` entry
and removes the ambiguity.

---

## Advisory observation (no fix required)

**Three locations enumerate prohibited git operations.** After this build,
the same operation set appears in: (1) the `stays-out` row Symptoms column,
(2) the PROHIBITED table, and (3) the HARD SAFETY INVARIANT "Concretely"
list. Each serves a different audience (routing guide / schema /
human-reasoning), so the duplication is intentional. No fix required, but a
maintainer adding a future git operation (e.g. `git stash --include-untracked`)
must update all three locations. Noting it here for the session record.

---

## Non-findings

- **Scope creep:** None. All four edits target the Q18 loophole exclusively.
- **Unnecessary abstractions:** The PROHIBITED table (schema-level) and HARD
  SAFETY INVARIANT (reasoning-level) serve distinct audiences; both warranted.
- **Accidental broad changes:** No unrelated content modified.
- **Readability:** Section headings, table structure, autonomous-fork rule
  paragraph, and rationalization rows are clear and appropriately scoped.
- **WI-003 applied in WI-005 worktree:** Content embodied in final commit;
  not a simplicity risk.

---

## Required action

Update SKILL.md in the worktree to fix F1 (one-phrase change in the HARD
SAFETY INVARIANT). The fix is independent of all other review lanes.
