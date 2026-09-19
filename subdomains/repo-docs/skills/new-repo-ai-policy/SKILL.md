---
name: new-repo-ai-policy
description: Sole write path for a repository's AI-POLICY.md and its AI-POLICY-SHORT.md companion (AI rules) — the AI-usage and software-citation contract. Use on "add an AI rule", "amend AI-POLICY.md", "change the disclosure requirements", "add a declared tool to the policy", when latex-ai-statement reports a finding no AI-rule covers, or to instantiate AI-POLICY.md from the pack template into a repo. Every change is proposed, human-approved in conversation, and recorded in the doc's Change Log. Companion checker: latex-ai-statement. NOT for recording what a task actually used (update-ai-usage) or what it cost (update-tokens) — those write the records, not the contract — and NOT for any other repo doc, any .tex, or the pack templates.
---

# new-repo-ai-policy

Owns the repo's **`AI-POLICY.md`** and its `AI-POLICY-SHORT.md` companion.
Editing them any other way — "just adding the model we used", writing
disclosure rules into a manuscript or a skill — is the RED-baseline failure
this skill exists to prevent (`baselines-phase1.md`, scenario D; design D3:
acceptance is a human act).

**Trinity role:** `AI-POLICY.md` (source of truth) + `latex-ai-statement`
(read-only auditor) + this skill (sole write path).

## Procedure

Follow `subdomains/repo-docs/AMENDMENT.md` end to end: resolve the repo's
`AI-POLICY.md` (on miss, instantiate
`subdomains/repo-docs/templates/AI-POLICY.md` — the instantiation is itself
the proposal) → draft the structured proposal → **human gate, mandatory** →
apply to `AI-POLICY.md` (and its SHORT companion) only, with a Change Log
row naming the approver → verify (below) → conservative, pathspec-scoped
commit only with explicit authority.

## This skill's specifics

- **Declared-tools rows are the common case.** Adding a tool, model, or
  skill to the table is a one-row proposal, but it obliges a `.bib` entry
  and a pinpoint citation wherever the tool is used (AI2, AI3) — name that
  in Downstream.
- Placement changes (AI12) ripple into every manuscript in the repo; a
  journal requirement that overrides placement is recorded as such, not as
  a weakening of the rule.
- Pricing conventions live in AI16 and are implemented by `update-tokens`;
  a proposal changing the rate source or the estimate-labelling convention
  must say what happens to existing rows (never silently re-priced).
- **Keep the SHORT companion in step.** Every rule added, reworded, or
  deprecated updates its indexed line in `AI-POLICY-SHORT.md` in the same
  amendment. The companion is an index, never a second source of truth.

## Verification (Step 4)

**First run the coverage check** —
`python3 subdomains/repo-docs/scripts/check-ai-coverage.py`. It asserts that
every rule marked `[C]`, `[R]`, or `[F]` has an owner that names it: `[C]` a
row in `latex-ai-statement`'s table, `[R]` a mention in `update-ai-usage` or
`update-tokens`, `[F]` a matching line in the SHORT index. Three review
rounds each shipped a rule whose enforcement point did not mention it; this
is the check that ends that. A non-zero exit blocks the amendment.

Then the manuscript pass. Run `latex-ai-statement` in
policy-verification mode on the amended `AI-POLICY.md`, then on each `.tex`
in the repo, and report the manuscript count — a repo with no manuscript
reports "checked 0 manuscripts", never a silent pass. AI15/AI16 amendments
touch the records, not a `.tex`: verify those against `update-ai-usage` and
`update-tokens` instead.

## Floors

The template marks floors `[F]`. Read them there — this skill does not
restate the set, because a second copy is how the list drifts. A proposal
that weakens or deletes an `[F]` rule is refused, not presented; a repo whose
instantiated copy predates a floor is not exempt, and the remedy is an
amendment adding it.

## Refuse and escalate

Route to the owning **skill**, never to the document — editing another
domain's policy in place is the sole-write-path violation this trinity
exists to prevent.

| Finding belongs to | Route to |
| --- | --- |
| LX floor (`subdomains/latex/POLICY.md`) | `new-latex-policy` |
| Repo `STYLE.md` / `LAYOUT.md` / `AGENTS.md` | `new-repo-style-policy` / `new-repo-layout-policy` / `new-repo-agents-policy` |
| Repo `ADR.md` / `LATEX.md` | `new-repo-adr-policy` / `new-repo-latex-policy` |
| What a task used or cost (`ai-usage.md`, `tokens.md`) | `update-ai-usage` / `update-tokens` — records, not contract |
| The pack templates themselves | stop and put it to the human as a pack-side change; no skill owns this |
