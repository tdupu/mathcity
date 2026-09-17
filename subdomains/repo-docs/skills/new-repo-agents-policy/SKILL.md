---
name: new-repo-agents-policy
description: Sole write path for a repository's AGENTS.md (AG rules) — agent entry point — pointers, task-tracking contract, mirror discipline. Use on "amend AGENTS.md", "update the agent instructions", "point agents at X", when a check skill's remediation points here, or to instantiate AGENTS.md from the pack template into a repo. Every change is proposed, human-approved in conversation, and recorded in the doc's Change Log. Companion checker: check-layout. NOT for any other repo doc, any .tex, or the pack templates.
---

# new-repo-agents-policy

Owns exactly one document: the repo's **`AGENTS.md`**. Editing it any other
way — "just fixing a typo", writing conventions into other files —
is the RED-baseline failure this skill exists to prevent
(`baselines-phase1.md`, scenario D; design D3: acceptance is a human
act).

## Procedure

Follow `subdomains/repo-docs/AMENDMENT.md` end to end: resolve the
repo's `AGENTS.md` (on miss, instantiate
`subdomains/repo-docs/templates/AGENTS.md` — the instantiation is
itself the proposal) → draft the structured proposal → **human gate,
mandatory** → apply to `AGENTS.md` only, with a Change Log row → verify
with the companion checker → conservative, pathspec-scoped commit only
with explicit authority.

## This skill's specifics

- AGENTS.md points; it does not restate (AG1). A proposal that copies
  rule text from LAYOUT/LATEX/STYLE/ADR into AGENTS.md is refused —
  offer the pointer form instead.
- Task-tracking contract changes (bd store, dolt remote) must state the
  verified reality (store exists? remote reachable?) — never leave
  boilerplate the repo does not satisfy.
- Mirror discipline (AG2) changes ripple to .claude/.codex sync — name
  the sync step in Downstream.
