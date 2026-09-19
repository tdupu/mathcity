---
name: check-layout
description: Read-only audit of a repository against its own LAYOUT.md, LATEX.md, and AGENTS.md pointers — placement, clean-tree, canonical tex files, and undeclared sibling-.tex detection. Use when the user says "check layout", "check-layout", "which tex file is real", before instantiating repo docs into a brownfield repo, or as the conformance gate after any skill created files. Companions: new-repo-layout-policy / new-repo-latex-policy (sole write paths). NOT for document quality (LX floor: check-latex, check-latex-hygiene) and NOT for fixing — it only reports.
---

# check-layout

Audits a repo against its **own** `LAYOUT.md` (LY rules), `LATEX.md`
(LT rules), and `AGENTS.md` pointers (AG rules). RED baseline:
`baselines-phase1.md` scenario A — unguided agents invent standards and
reorganize without approval (mechanisms 12, 1; D1/D3).

## Step 0 — Resolve

Run the shared preamble: `subdomains/repo-docs/RESOLUTION.md`
(repo-local-first; on miss instantiate from templates/ and interrupt;
Status semantics; instruments-must-fail). No approved resolution →
verdict DEFER, stop.

## Step 1 — Enumerate (counts are evidence)

```bash
git ls-files                      # tracked reality
git status --short -uall          # untracked/dirty reality
git ls-files '*.tex' ':!scratch'  # tex, scratch/ excluded; also ls <root>
```

Report every count. Zero `.tex` in a repo whose LATEX.md declares some
is `EVIDENCE-ABSENT` (RESOLUTION.md §5).

## Step 2 — Check, per rule ID

Cite IDs; rules live in the repo docs, not here (pointer-not-copy).
Brownfield-register paths report as `KNOWN-DIRTY` with their registered
disposition, never as fresh findings:

- **LY1/LY2** — tracked reality vs the declared tree, both directions.
- **LY3** — transient/agent output outside `scratch/`; dump-dir naming.
- **LY5/AG1/AG2** — six docs present (LAYOUT, LATEX, STYLE, ADR, AGENTS, AI-POLICY + its SHORT companion) and the two AI records declared; AGENTS.md points, doesn't
  restate; mirrors are real files and byte-match canonical.
- **LY6/LY7/LY8** — per their [C] criteria in the repo's LAYOUT.md.
- **LT (Real files)** — tracked `.tex` outside `scratch/` vs the table;
  at most one canonical file per tier per directory. Any tracked `.tex`
  with no row = **`UNDECLARED-SIBLING`** — the fork-not-merge
  mechanism. Report; route to `triage-variants`. Never move, rename,
  repair, or delete it yourself.
- **LT (Aspirational)** — new `.tex` since last check had a row at
  creation.

## Step 3 — Report

One block, to stdout and (only if asked) `scratch/`:

```
CHECK-LAYOUT <repo> <date>
Resolution: <docs found | instantiated+approved | DEFER>
Checked: <N tracked, N tex, N docs>  (zero-counts flagged)
Findings: <rule-ID>: <path>: <one line>   (or "0 violations in N objects")
Known-dirty: <register rows, dispositions cited>
Verdict: PASS | ADVISORY-PASS | FAIL | DEFER   (ADVISORY when Status: Draft)
Remediation: <finding → triage-variants | new-repo-*-policy | human>
```

## Hard rules

- Read-only: never fixes, moves, renames, deletes, stages, or commits —
  the baseline failures did all five.
- Findings against the floor docs (LX) belong to `check-latex-hygiene`;
  report `FLOOR-BREACH` and point there.
- Never weaken a verdict to make an existing state pass; surprises go
  to the human.
