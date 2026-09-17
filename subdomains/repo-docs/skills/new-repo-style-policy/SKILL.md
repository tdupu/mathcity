---
name: new-repo-style-policy
description: Sole write path for a repository's STYLE.md (ST rules) — mathematical writing contract — statement discipline, markers, tags, style variables. Use on "add a style rule", "amend STYLE.md", "change the terseness/audience", "new writing convention", when a check skill's remediation points here, or to instantiate STYLE.md from the pack template into a repo. Every change is proposed, human-approved in conversation, and recorded in the doc's Change Log. Companion checker: check-style. NOT for any other repo doc, any .tex, or the pack templates.
---

# new-repo-style-policy

Owns exactly one document: the repo's **`STYLE.md`**. Editing it any other
way — "just fixing a typo", writing conventions into other files —
is the RED-baseline failure this skill exists to prevent
(`baselines-phase1.md`, scenario D; design D3: acceptance is a human
act).

## Procedure

Follow `subdomains/repo-docs/AMENDMENT.md` end to end: resolve the
repo's `STYLE.md` (on miss, instantiate
`subdomains/repo-docs/templates/STYLE.md` — the instantiation is
itself the proposal) → draft the structured proposal → **human gate,
mandatory** → apply to `STYLE.md` only, with a Change Log row → verify
with the companion checker → conservative, pathspec-scoped commit only
with explicit authority.

## This skill's specifics

- Style-variable changes (kind/terseness/audience) are one-row
  proposals but ripple into every future write — name that in
  Downstream.
- The LX floor and Tag 02BZ authority cannot be weakened from here;
  proposals that try are refused with the floor named.
- The machine-tag format (ST5) is shared vocabulary across repos —
  changing it locally needs a pack-side discussion first; refuse and
  escalate.
