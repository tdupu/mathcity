---
schema: gc.build.code-review-context.v1
workflow:
  id: gsp-ycmp6
  formula: build-basic-briefed
producer:
  step: build-basic-briefed.review.setup-build-basic-review
  bead: gsp-ikgv9
artifact_root: mathcity/skills/decisions-to-briefs
---

# Code Review Context: decisions-to-briefs SKILL.md — git-op action-block prohibition

## What Is Being Reviewed

**Changed file:** `mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`

Five atomic edits (WI-001 through WI-005) close the Q18 loophole (incident gt-hjk388)
in the `decisions-to-briefs` skill. An autonomous Fable fork committed to
`~/repos/hecke` without the `authorize-git-operation` gate because the existing
§HARD SAFETY INVARIANT only enumerated `git push / force-push / merge / branch or tag
deletion` — omitting `git commit`. This build adds the missing prohibition.

All changes are committed in worktrees (push=false, open_pr=false). The launcher
rig root (`gsp-9kxub-create-task-beads`) is unchanged; the implementation lives in
the source anchor worktrees listed below.

---

## Source Anchors / Worktrees

| WI | Bead | work_dir | Commit |
|---|---|---|---|
| WI-001 | gsp-w3wqq | `gsp-wenc9-prepare-item-worktree/worktrees/gsp-w3wqq` | `acfba4749dfcdd7c10a7001897a56c2b566ccc60` |
| WI-002 | gsp-k0n3o | `gsp-wenc9-prepare-item-worktree/worktrees/gsp-k0n3o` | `11be3272eb61be50f2c6c578da7c115aed3cf545` |
| WI-003 | gsp-vywei | `gsp-1qtqj-prepare-item-worktree/worktrees/gsp-vywei` | applied in WI-005 worktree |
| WI-004 | gsp-4viam | `gsp-wenc9-prepare-item-worktree/worktrees/gsp-4viam` | `5011b200b33b403c4663099bb565105aee07ebf5` |
| WI-005 | gsp-ev1rr | `gsp-1qtqj-prepare-item-worktree/worktrees/gsp-ev1rr` | `6ecef4d577e4549b98beae7cbd5d56ecd17fbf65` |

All paths above are relative to `/Users/tdupuy/gt/gascity-packs/`.

**Final combined commit:** `6ecef4d577e4549b98beae7cbd5d56ecd17fbf65`
(WI-005 verification worktree — all four changes applied and all 5 ACs verified)

---

## Requirements Summary

**Source:** `mathcity/skills/decisions-to-briefs/requirements.md`
**Workflow:** gsp-ycmp6 | **Root cause:** gt-hjk388 (Q18 incident)

| ID | Requirement | AC |
|---|---|---|
| REQ-001 | Enumerate `git commit` (and equivalents) in the prohibited-operations set | AC-1: `grep -i "git commit" SKILL.md` |
| REQ-002 | Named rule that autonomous forks MUST classify all git-op decisions as `external-reminder` | AC-2: `grep -i "autonomous" SKILL.md` |
| REQ-003 | `PROHIBITED` note/table in action-block schema documentation | AC-3: `grep -i "prohibited" SKILL.md` |
| REQ-004 | "Just a local commit" bypass rationalization row with reality correction | AC-4: `grep -i "local commit" SKILL.md` |
| REQ-005 | `stays-out` row explicitly references git writes | AC-5: `grep -A 6 "stays-out" SKILL.md \| grep -i "git"` |
| REQ-006 | All 7 existing valid action-item types remain intact | AC-6: counts for sling-bead, file-follow-up-brief, wire, close-supersede, run-skill, external-reminder, snooze |

---

## Implementation Plan Summary

**Source:** `mathcity/skills/decisions-to-briefs/implementation-plan.md`

Four targeted atomic edits to `mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`:

1. **WI-001** — Replace the Symptoms column of the `stays-out` row to add "or any git write (commit / push / merge / cherry-pick / rebase / tag / branch-delete)"
2. **WI-002** — Insert PROHIBITED action-item types paragraph and table (9 prohibited types) after §Action-item types table
3. **WI-003** — Extend §HARD SAFETY INVARIANT "Concretely, NO auto-action for:" paragraph to include `git commit / commit --amend / cherry-pick / rebase / merge (including --ff-only)`; add Autonomous-fork rule paragraph
4. **WI-004** — Append "It's just a local commit, not a push" rationalization row; add v0.2 versioning entry
5. **WI-005** (verification) — Run all 5 AC grep tests + backward-compat critical review

No new files added; no existing action-item types changed.

---

## Decomposition Summary

**Source:** `mathcity/skills/decisions-to-briefs/decomposition.md`
**Convoy:** gsp-qv29d (decisions-to-briefs-impl)

| Bead | Title | Traces to |
|---|---|---|
| gsp-w3wqq | Change 1: Update stays-out row | REQ-005 / AC-5 |
| gsp-k0n3o | Change 2: Add PROHIBITED table | REQ-003 / AC-3 |
| gsp-vywei | Change 3: Extend HARD SAFETY INVARIANT + autonomous-fork rule | REQ-001 / AC-1, REQ-002 / AC-2 |
| gsp-4viam | Change 4: Add local-commit rationalization row | REQ-004 / AC-4 |
| gsp-ev1rr | Verify: all 5 AC grep tests + backward compat | REQ-006 / AC-6 |

---

## Implementation Summary

**Source:** `mathcity/skills/decisions-to-briefs/implementation-summary.md`
**Status:** approved

All 6 requirements covered across 5 work items. Final verification commit:
`6ecef4d577e4549b98beae7cbd5d56ecd17fbf65`

Note: WI-003 (gsp-vywei) was applied in the WI-005 verification worktree rather
than a dedicated worktree; gsp-vywei bead remains open but its content is embodied
in commit `6ecef4d577e4549b98beae7cbd5d56ecd17fbf65`.

---

## Per-Item Task Evidence

### WI-001 — gsp-w3wqq: stays-out row git-write call-out

**Source:** `mathcity/skills/decisions-to-briefs/` (no separate item summary — evidence in implementation summary)
**Commit:** `acfba4749dfcdd7c10a7001897a56c2b566ccc60`
**Worktree:** `gsp-wenc9-prepare-item-worktree/worktrees/gsp-w3wqq`

**Change:** Replaced `stays-out` Symptoms column text to explicitly enumerate git writes.

**Proof command:**
```bash
grep -A 6 "stays-out" mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md | grep -i "git"
```
**Result:** PASS (matched git write enumeration)

---

### WI-002 — gsp-k0n3o: PROHIBITED action-item types table

**Source:** `mathcity/skills/decisions-to-briefs/item-gsp-k0n3o-summary.md`
**Commit:** `11be3272eb61be50f2c6c578da7c115aed3cf545`
**Worktree:** `gsp-wenc9-prepare-item-worktree/worktrees/gsp-k0n3o`

**Change:** Inserted PROHIBITED action-item types paragraph and 9-row table
immediately after §Action-item types table, before `## HARD SAFETY INVARIANT`.

Prohibited types: `git-commit`, `git-commit-amend`, `git-push`, `git-force-push`,
`git-merge`, `git-cherry-pick`, `git-rebase`, `git-tag`, `git-branch-delete`.

**Proof command:**
```bash
grep -i "prohibited" mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md
```
**Result:** PASS

---

### WI-003 — gsp-vywei: HARD SAFETY INVARIANT + autonomous-fork rule

**Applied in:** WI-005 verification worktree (`gsp-1qtqj-prepare-item-worktree/worktrees/gsp-ev1rr`)
**Commit:** `6ecef4d577e4549b98beae7cbd5d56ecd17fbf65`

**Change:** Replaced "Concretely, NO auto-action for:" paragraph to include `git commit /
commit --amend / cherry-pick / rebase / merge (including --ff-only)`. Added
**Autonomous-fork rule** paragraph: autonomous forks MUST classify ALL git-op decisions
as `external-reminder`, no exception for "tiny", "local-only", or "reversible-seeming"
commits.

**Proof commands:**
```bash
grep -i "git commit" mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md  # AC-1
grep -i "autonomous"  mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md  # AC-2
```
**Result:** PASS (both)

---

### WI-004 — gsp-4viam: local-commit rationalization row + v0.2 versioning

**Source:** `mathcity/skills/decisions-to-briefs/item-gsp-4viam-summary.md`
**Commit:** `5011b200b33b403c4663099bb565105aee07ebf5`
**Worktree:** `gsp-wenc9-prepare-item-worktree/worktrees/gsp-4viam`

**Change:** Appended 5th rationalization row:
> "It's just a local commit, not a push" → "A commit IS a git write. `git push` makes it
> public; the commit is already irreversible from Taylor's audit trail perspective."

Also added v0.2 versioning entry tying all five changes to gt-hjk388.

**Proof command:**
```bash
grep -i "local commit" mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md
```
**Result:** PASS

---

### WI-005 — gsp-ev1rr: All-AC verification pass

**Source:** `mathcity/skills/decisions-to-briefs/item-gsp-ev1rr-summary.md`
**Commit:** `6ecef4d577e4549b98beae7cbd5d56ecd17fbf65`
**Worktree:** `gsp-1qtqj-prepare-item-worktree/worktrees/gsp-ev1rr`

Applied all 4 changes (including WI-003) and ran all 5 acceptance-criterion grep
tests. All pass. Backward-compat check confirms all 7 existing type names intact.

**Final proof commands:**
```bash
SKILL="mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md"
grep -i "git commit"  "$SKILL"                      # AC-1: PASS
grep -i "autonomous"  "$SKILL"                      # AC-2: PASS
grep -i "prohibited"  "$SKILL"                      # AC-3: PASS
grep -i "local commit" "$SKILL"                     # AC-4: PASS
grep -A 6 "stays-out" "$SKILL" | grep -i "git"     # AC-5: PASS
```

**Backward-compat type counts (AC-6):**
sling-bead:4, file-follow-up-brief:3, wire:4, close-supersede:2, run-skill:2,
external-reminder:9, snooze:2 — all 7 types present

---

## Remaining Risks

- WI-003 (gsp-vywei) bead remains open; its content was applied in the WI-005
  verification worktree. The review stage should note this for the source bead.
- Changes are NOT yet merged to main (push=false). The brief produced by this
  build will surface the changes for Taylor's explicit merge authorization.
- AC-6 backward-compat was verified by grep counts only; full critical-review
  of the updated SKILL.md is one of the three review lanes.
