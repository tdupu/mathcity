# LAYOUT.md — repository layout contract

<!-- TEMPLATE (mathcity-repo-docs). Instantiate into a repo root, fill
     every <angle> field and the tree, delete this comment. The repo's
     copy is then owned by the repo: amend it only through
     new-repo-layout-policy. Checked by check-layout. -->

| Field | Value |
| --- | --- |
| Repo | `<repo-name>` |
| Status | Draft |
| Date | `<YYYY-MM-DD>` |
| Approved by | `<human name — required before Status: Adopted>` |
| Checked by | `check-layout` |
| Amended by | `new-repo-layout-policy` |

One document per repository, at the root. It answers: what goes where,
what is canonical, what is kept-but-ignored, and what must never appear.
Model: the hecke root layout tree.

## Tree

Declare the full intended tree, annotated. Every top-level directory and
tracked root file appears here; a real object with no row here is a
finding (LY2).

```
<repo-name>/
├── <dir>/          ← <purpose>
├── scratch/        ← ALL transient/agent output (LY3); see below
├── LAYOUT.md  LATEX.md  STYLE.md  ADR.md  AGENTS.md
└── ── gitignored but KEEP on disk ──
    <pattern>       ← <why it exists and why it is not tracked>
```

## Rules

**LY1 — Clean-tree test [C].** A collaborator opening the repo finds
only the published artifact, its documentation, and the five repo docs.
No agent or orchestration scaffolding outside `scratch/`.
Pass: every tracked path matches a tree row. Fail: any tracked path
with no row.

**LY2 — The tree is total [C].** Every top-level directory and tracked
root file has a tree row; every "gitignored but keep" pattern is listed.
Pass/Fail: mechanical diff of `git ls-files` + root listing vs the tree.

**LY3 — Transient output goes to scratch/ [C].** Anything a tool or
agent writes that is not the artifact goes under
`scratch/YYYY-MM-DD-<slug>/`, containing at least `report.md`,
`ai-usage.md`, and `tokens.md` when the work was agent-performed (the
astra-dump contract; see that skill for the file contracts).
Pass: no transient files outside `scratch/`; dump dirs follow the
naming. Fail: stray `.md`/`.mag`/notes at root or elsewhere.

**LY4 — Tex placement.** `.tex` files live only in the directories the
tree marks for LaTeX; which files are canonical there is `LATEX.md`'s
concern (see it; check-layout enforces both together).

**LY5 — Repo docs present [C].** `LAYOUT.md`, `LATEX.md`, `STYLE.md`,
`ADR.md`, `AGENTS.md` exist at the root and `AGENTS.md` points at the
other four. Pass/Fail: existence + pointer check.

## Change Log

| Date | Change | Approved by |
| --- | --- | --- |
| `<YYYY-MM-DD>` | Instantiated from mathcity-repo-docs template | `<name>` |
