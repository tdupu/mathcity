---
name: using-latexpowers
description: Use when working in a mathematics research repository on ANYTHING that touches .tex files or the repo contracts — "clean up the tex situation", "which file is real", "write this up as a proposition", "referee my section N", "we got the referee report", "prep for arXiv", "is this citation right", "set this repo up properly", "record this decision", or any edit about to land in a .tex — BEFORE any direct edit, cleanup, or advice. Routes to the owning leaf; gates live there. NOT for proving/research (using-mathpowers) or generic process (superpowers:using-superpowers).
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## The Rule

**Resolve the repo's five docs (`subdomains/repo-docs/RESOLUTION.md`) and dispatch via the table BEFORE any file edit, cleanup, or advice** — "quick" fixes, tidying, and placeholder-filling included. No leaf fits, or intent unclear (target manuscripts? target theorems?) → request a grill-with-docs session; never improvise.

## Dispatch

| Situation | Leaf |
|---|---|
| repo lacks any of the five docs | `init-repo-docs` (batch-gated) |
| "is the tex situation healthy" / post-skill verification | `check-layout` |
| undeclared sibling .tex — "this trash ai-paper.tex situation"; NOT ad-hoc moves/repairs | `triage-variants` (per-file gate) |
| style/quality question on declared files | `check-style` · `check-latex` · `check-latex-hygiene` · `check-labels-and-refs` · `check-citations` |
| claim needs a source / suspect cite / %VERIFY | `track-down-reference` |
| evidenced content into canonical tex — "write this up as a proposition" | `write-proposition` / `write-definition` / `write-remark` |
| discussion → skeleton stubs | `rapid-prototype` |
| scratch dump → notes exposition | `explain-experiment` |
| "what does this proof use" | `resolve-dependencies` |
| ACCEPTED report to apply | `revise` |
| "referee my section 3" (OUR draft; NOT triage-referee-report) | `referee-report` |
| received referee report | `triage-referee-report` (its own full flow) or a manual astra/fable session — human's pick (ADR 0005); never auto-drafted |
| "is this decision recorded" / audit the decision record | `check-adr` |
| "prep for arXiv" | `garbage-collect` (strip gate) |
| software/AI-disclosure section | `write-materials-and-methods` |
| "write the introduction now" — EXPLICIT ask only; never volunteer | `write-introduction` (refusal gate) |
| any repo-doc change, even placeholder-filling | `new-repo-{layout,latex,style,adr,agents}-policy` (human gate) |
| LX-rule change | `new-latex-policy` |
| two rows fire | checks before writers; `triage-variants` before everything while a sibling exists; section-merge work is HOLD (`merge-latex-sections`) |

## Red flags

| Thought | Reality |
|---|---|
| "I left the mathematical wording untouched" | Moving dead text live IS a promotion. Writer gates apply. |
| "…rather than silently rewriting — I tagged it" | Tags are mechanics, not approval. The write path is the leaf. |
| "Already backed by ST1, so I can record it" | A rule existing is not approval. Amendment skills gate docs. |
| "Fix anything you're confident about" | Confidence is not approval (per-file/per-doc gates). |

## Precedence

User instructions (CLAUDE.md, AGENTS.md, GEMINI.md, etc, direct requests) take precedence over skills, which in turn override default behavior. Only skip skill workflows or instructions when your human partner has explicitly told you to.

The repo's instantiated docs outrank this router; using-superpowers owns generic process dispatch; proving routes to `using-mathpowers`.
