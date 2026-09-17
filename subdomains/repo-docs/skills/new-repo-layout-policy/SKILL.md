---
name: new-repo-layout-policy
description: Sole write path for a repository's LAYOUT.md (LY rules) — tree, placement, clean-tree, scratch discipline. Use on "add a layout rule", "amend LAYOUT.md", "declare a new directory", when a check skill's remediation points here, or to instantiate LAYOUT.md from the pack template into a repo. Every change is proposed, human-approved in conversation, and recorded in the doc's Change Log. Companion checker: check-layout. NOT for any other repo doc, any .tex, or the pack templates.
---

# new-repo-layout-policy

Owns exactly one document: the repo's **`LAYOUT.md`**. Editing it any
other way is the RED-baseline failure this skill exists to prevent
(`baselines-phase1.md` scenario D; D3: acceptance is a human act).

## Procedure

Follow `subdomains/repo-docs/AMENDMENT.md`: resolve the
repo's `LAYOUT.md` (on miss, instantiate
`subdomains/repo-docs/templates/LAYOUT.md` — the instantiation is
itself the proposal) → draft the structured proposal → **human gate,
mandatory** → apply to `LAYOUT.md` only, with a Change Log row → verify
with the companion checker → pathspec-scoped commit only with explicit
authority.

## This skill's specifics

- Tree changes (new directory, relocation, new gitignored-but-keep
  pattern) update the tree (LY1/LY2 re-evaluate mechanically) in one
  proposal.
- Register lifecycle: proposals add/update/remove Brownfield-register
  rows using LAYOUT.md's disposition vocabulary; remove a row only
  after the cleanup actually happened.
- Never move existing files as a side effect: the proposal changes the
  CONTRACT; moves are separate, human-approved work items under
  Downstream.
