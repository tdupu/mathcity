---
name: triage-variants
description: Disposition each undeclared sibling .tex in a repository — merge into the canonical file, demote to a scratch report, declare as legitimate, or delete — with ONE human approval per file. Use when the user says "triage variants", "triage-variants", "which tex file is real", when check-layout reports UNDECLARED-SIBLING, or per LATEX.md's Brownfield note. Brownfield repair only: NOT for declared files (new-repo-latex-policy), referee revision copies (triage-referee-report), in-file section merging (merge-latex-sections, HOLD), or document quality (LX floor). Never adjudicates mathematics.
---

# triage-variants

The fork-not-merge repair (design ADR 0003 rule 4). RED baseline:
`baselines-phase1.md` scenarios A+D — unguided agents relocate, rename,
repair, or normalize variant files on their own authority. Every
disposition is a human act; this skill prepares evidence and executes
exactly what was approved.

## Step 0 — Resolve

[../../RESOLUTION.md](../../RESOLUTION.md). Requires the repo's
LATEX.md (no docs → run `init-repo-docs` first, which registers
variants and routes back here).

## Step 1 — Enumerate

Variants = tracked `.tex` outside `scratch/` minus LATEX.md's
Real-files and Aspirational rows. Report counts (RESOLUTION.md §5);
zero variants → report "0 variants in N tex files" and stop.

## Step 2 — Evidence dossier per variant (read-only)

For each: provenance (`git log --follow`, author/date/attribution);
diff-vs-canonical summary at statement level (which
propositions/definitions exist only here, which CONTRADICT the
canonical file — quote both sides, adjudicate nothing); marker census
(`\taylor{}`, `\todo{}`, tags); compile-independence; size/overlap
estimate. On a contradiction, invoke contradiction-check; a hit blocks
the merge/declare disposition per its Step 3 (silent supersession is
prohibited).

## Step 3 — ONE approval PER FILE (mandatory gate)

Present each dossier with a recommendation and options: **merge**
(named content into the canonical file) / **demote** (to a dated
scratch dump, content preserved) / **declare** (genuinely legitimate →
route to `new-repo-latex-policy` to add its row) / **delete** /
**defer**. One file, one decision; approval never transfers between
files; batch approval only if the human says "all".
Unattended: write dossiers + recommendations to
`scratch/<date>-triage-variants/` and STOP.

## Step 4 — Execute exactly what was approved

- **merge**: insert the approved material into the canonical file as
  ST5-tagged blocks (`agent-<harness>` tags), superseded canonical text
  commented out, never deleting human markers or comments; then
  `git rm` the variant in the same commit.
- **demote**: move the file into `scratch/<date>-triage-variants/`
  with a report.md noting provenance and why.
- **declare**: hand off to `new-repo-latex-policy` (its own gate).
- **delete**: `git rm`, only on that file's explicit delete approval.
- **defer**: leave in place; it stays an UNDECLARED-SIBLING finding.

## Step 5 — Reconcile and verify

Update LATEX.md (Real-files / Change Log) via `new-repo-latex-policy`
for the surviving state; run `check-layout` — expected:
`0 UNDECLARED-SIBLING` except deferred rows. Merge dispositions
additionally run `check-latex` + `check-style` scoped to the touched
canonical file. One pathspec-scoped commit per repo's ST8.

## Red flags

| Thought | Reality |
|---|---|
| "Fix anything you're confident about" | Confidence is not approval. Step 3 gates every file. |
| "It looks like AI output — relocate it" | Looking AI-made is a dossier fact, not a disposition. |
| "I'll repair it so it at least compiles" | Repairing a variant normalizes the fork. Dossier, don't fix. |
| "git add -A to wrap up" | Stage the approved paths only. |
