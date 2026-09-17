---
name: new-repo-adr-policy
description: Sole write path for a repository's ADR.md (AR rules) — decision record — new entries, supersessions, migrations of scattered decision text. Use on "record a decision in the repo", "add an ADR", "supersede ADR-N", "migrate this convention into ADR.md", when a check skill's remediation points here, or to instantiate ADR.md from the pack template into a repo. Every change is proposed, human-approved in conversation, and recorded in the doc's Change Log. Companion checker: check-adr. NOT for any other repo doc, any .tex, or the pack templates.
---

# new-repo-adr-policy

Owns exactly one document: the repo's **`ADR.md`**. Editing it any other
way — "just fixing a typo", writing conventions into other files —
is the RED-baseline failure this skill exists to prevent
(`baselines-phase1.md`, scenario D; design D3: acceptance is a human
act).

## Procedure

Follow [../../AMENDMENT.md](../../AMENDMENT.md) end to end: resolve the
repo's `ADR.md` (on miss, instantiate
[../../templates/ADR.md](../../templates/ADR.md) — the instantiation is
itself the proposal) → draft the structured proposal → **human gate,
mandatory** → apply to `ADR.md` only, with a Change Log row → verify
with the companion checker → conservative, pathspec-scoped commit only
with explicit authority.

## This skill's specifics

- New entries append per AR1 shape at the next number; supersession
  is a new entry plus a Status tombstone on the old one (AR2).
- Migrations: when check-adr flags decision text scattered elsewhere,
  the proposal lists each quote, its proposed ADR entry, and the
  deletion of the stray copy — one human approval covers the batch,
  but the deletions still land only in the files the human approved.
- ADR entries record decisions; a decision that creates a standing
  checkable rule ALSO goes to the owning doc via its own amendment
  skill, citing the ADR entry as rationale.
