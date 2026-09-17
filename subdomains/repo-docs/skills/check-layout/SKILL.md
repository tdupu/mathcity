---
name: check-layout
description: Read-only audit of a research repository against its own LAYOUT.md and LATEX.md (plus AGENTS.md pointer conformance) — placement, clean-tree, canonical tex files, and undeclared sibling-.tex detection. Use when the user says "check layout", "check-layout", "audit this repo's organization", "which tex file is real", "is the tex situation healthy", before instantiating repo docs into a brownfield repo, or as the conformance gate after any skill created files. Companions: new-repo-layout-policy / new-repo-latex-policy (sole write paths). NOT for document quality (LX floor: check-latex, check-latex-hygiene) and NOT for fixing — it only reports.
---

# check-layout

Audits a repo against its **own** `LAYOUT.md` (LY rules), `LATEX.md`
(LT rules), and `AGENTS.md` pointers (AG rules). RED baseline:
`baselines-phase1.md` scenario A in the design record — unguided agents
invent standards and reorganize without approval (survey mechanisms 12,
1; D1/D3 violations). This skill exists so that never happens again.

## Step 0 — Resolve

Run the shared preamble: [../../RESOLUTION.md](../../RESOLUTION.md)
(repo-local-first; on miss instantiate
[../../templates/](../../templates/) and interrupt; Status semantics;
instruments-must-fail). No approved resolution → verdict DEFER, stop.

## Step 1 — Enumerate (counts are evidence)

```bash
git ls-files                      # tracked reality
git status --short -uall          # untracked/dirty reality
git ls-files '*.tex'; ls <root>   # tex + root inventory
```

Report every count. Zero `.tex` in a repo whose LATEX.md declares some
is `EVIDENCE-ABSENT`, not a pass (RESOLUTION.md §5).

## Step 2 — Check, per rule ID

Cite IDs; the rules live in the repo docs, not here (pointer-not-copy):

- **LY1/LY2** — tracked reality vs the declared tree, both directions.
- **LY3** — transient/agent output outside `scratch/`; dump-dir naming.
- **LY5/AG1/AG2** — five docs present; AGENTS.md points, doesn't
  restate; mirrors are real files and byte-match canonical.
- **LT (Real files)** — `git ls-files '*.tex'` vs the table; exactly
  one canonical per directory. Any tracked `.tex` with no row =
  **`UNDECLARED-SIBLING`** — the fork-not-merge mechanism. Report it;
  route disposition to `triage-variants` (one human approval per file).
  Never move, rename, repair, or delete it yourself.
- **LT (Aspirational)** — new `.tex` since last check had a row at
  creation.

## Step 3 — Report

One block, to stdout and (only if asked) `scratch/`:

```
CHECK-LAYOUT <repo> <date>
Resolution: <docs found | instantiated+approved | DEFER>
Checked: <N tracked, N tex, N docs>  (zero-counts flagged)
Findings: <rule-ID>: <path>: <one line>   (or "0 violations in N objects")
Verdict: PASS | ADVISORY-PASS | FAIL | DEFER   (ADVISORY when Status: Draft)
Remediation: <finding → owning skill: triage-variants | new-repo-*-policy | human>
```

## Hard rules

- Read-only: never fixes, moves, renames, deletes, stages, or commits —
  the baseline failures did all five.
- Findings against the floor docs (LX) belong to `check-latex-hygiene`;
  report `FLOOR-BREACH` and point there.
- Never weaken a verdict to make an existing state pass; surprises go
  to the human.
