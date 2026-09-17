---
name: new-repo-layout-policy
description: Sole write path for a repository's LAYOUT.md (LY rules) — repository layout contract — tree, placement, clean-tree, scratch discipline. Use on "add a layout rule", "amend LAYOUT.md", "change where X goes", "declare a new directory", when a check skill's remediation points here, or to instantiate LAYOUT.md from the pack template into a repo. Every change is proposed, human-approved in conversation, and recorded in the doc's Change Log. Companion checker: check-layout. NOT for any other repo doc, any .tex, or the pack templates.
---

# new-repo-layout-policy

Owns exactly one document: the repo's **`LAYOUT.md`**. Editing it any other
way — "just fixing a typo", writing conventions into other files —
is the RED-baseline failure this skill exists to prevent
(`baselines-phase1.md`, scenario D; design D3: acceptance is a human
act).

## Procedure

Follow [../../AMENDMENT.md](../../AMENDMENT.md) end to end: resolve the
repo's `LAYOUT.md` (on miss, instantiate
[../../templates/LAYOUT.md](../../templates/LAYOUT.md) — the instantiation is
itself the proposal) → draft the structured proposal → **human gate,
mandatory** → apply to `LAYOUT.md` only, with a Change Log row → verify
with the companion checker → conservative, pathspec-scoped commit only
with explicit authority.

## This skill's specifics

- Tree changes (new directory, relocation, new gitignored-but-keep
  pattern) update the tree AND any rule the tree feeds (LY1/LY2) in one
  proposal.
- Never propose moving existing files as a side effect: the proposal
  changes the CONTRACT; file moves are separate, human-approved work
  items listed under Downstream.
