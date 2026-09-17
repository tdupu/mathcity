---
name: new-repo-latex-policy
description: Sole write path for a repository's LATEX.md (LT rules) — canonical-tex declaration — real files, canonical flags, aspirational files. Use on "declare a new tex file", "amend LATEX.md", "add an aspirational file", "change the canonical file", when a check skill's remediation points here, or to instantiate LATEX.md from the pack template into a repo. Every change is proposed, human-approved in conversation, and recorded in the doc's Change Log. Companion checker: check-layout. NOT for any other repo doc, any .tex, or the pack templates.
---

# new-repo-latex-policy

Owns exactly one document: the repo's **`LATEX.md`**. Editing it any other
way — "just fixing a typo", writing conventions into other files —
is the RED-baseline failure this skill exists to prevent
(`baselines-phase1.md`, scenario D; design D3: acceptance is a human
act).

## Procedure

Follow [../../AMENDMENT.md](../../AMENDMENT.md) end to end: resolve the
repo's `LATEX.md` (on miss, instantiate
[../../templates/LATEX.md](../../templates/LATEX.md) — the instantiation is
itself the proposal) → draft the structured proposal → **human gate,
mandatory** → apply to `LATEX.md` only, with a Change Log row → verify
with the companion checker → conservative, pathspec-scoped commit only
with explicit authority.

## This skill's specifics

- Declaring an aspirational file (the ONLY way a new sibling .tex may
  come to exist — design ADR 0003) is a normal proposal here: planned
  path, purpose, tier; approval recorded in the Change Log.
- Moving the canonical flag between files is architecture-class:
  present full-form, never compact.
- Brownfield: undeclared siblings are never retro-declared; they go
  through triage-variants first (one human approval per file), then the
  Real-files table is updated to the surviving state.
