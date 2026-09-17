---
name: init-repo-docs
description: Initialize a research repository onto the repo-doc contracts AND make it hygienic — instantiate LAYOUT/LATEX/STYLE/ADR/AGENTS from the pack templates, build the Brownfield register from what is actually in the tree, present ONE disposition batch for human approval, execute the approved moves (git mv / demote-to-scratch / gitignore), and verify with check-layout. Use when the user says "init repo docs", "init-repo-docs", "set this repo up properly", "instantiate the repo contracts here", "clean this repo and put it under contract", or when any repo-docs check skill hits the RESOLUTION.md import-and-interrupt path. NOT for repos already under contract (use the check/amendment skills) and NOT for sibling-.tex dispositions (triage-variants owns those).
---

# init-repo-docs

A LAYOUT.md nobody adheres to is decoration: this skill instantiates
the contracts AND brings the tree into line, in one gated pass. RED baseline: `baselines-phase1.md` scenario A (design record) —
unguided "cleanup" invents rules and moves files without approval.

## Step 1 — Instantiate

Copy the five `subdomains/repo-docs/templates/` into the repo root,
fill headers and the LAYOUT target tree from repo reality (Status:
Draft). Prefer the EXISTING structure where it is sane — few folders
(LY8); transcribe the intended layout, don't design a new one.

## Step 2 — Build the Brownfield register

Enumerate reality (`git ls-files` + root listing; report counts per
RESOLUTION.md §5). Everything that doesn't fit the target tree gets a
register row with a disposition from LAYOUT.md's disposition
vocabulary. Defaults: no declared home → `demote to scratch/` (never a
new folder); keep-untracked → gitignore entry + tree row; genuinely
ambiguous (artifact or junk?) → `TBD (human)`. Tex
sibling variants → register as `triage-variants` rows — this skill
NEVER moves, merges, or deletes a `.tex`.

## Step 3 — ONE approval batch (mandatory gate)

Present the instantiated docs + the full register as one batch:
each row `path → disposition`. The human may approve all, strike rows,
or change dispositions. No file moves before this approval. Unattended
→ write the batch to `scratch/<date>-init-proposal/` and STOP.

## Step 4 — Execute approved dispositions

- Moves/merges/demotions: `git mv` (history-preserving); LY7-rename in
  the same move where the name violates.
- keep-untracked: `.gitignore` entry + `git rm --cached` if tracked +
  tree row under "gitignored but keep".
- delete: only rows the human explicitly approved as delete.
- TBD rows and triage-variants rows: leave untouched, keep in register.
- Remove each COMPLETED row from the register; update the tree if the
  execution changed it.

## Step 5 — Verify and commit

Run `check-layout` (its report is the evidence). Remaining findings
must be exactly the surviving register rows + any DEFER items. Then one
pathspec-scoped commit: the five docs + moved paths + `.gitignore`,
message per repo commit hygiene (ST8 if tex moved). Push stays gated elsewhere.

## Hard rules

- The gate is Step 3; nothing moves before it, and only what it
  approved moves after it.
- Never a new top-level folder (LY8); never touch a `.tex` beyond
  register rows; never delete without an explicit per-row approval.
- Reversibility: every executed step is a git operation in one commit —
  revertable as a unit.
