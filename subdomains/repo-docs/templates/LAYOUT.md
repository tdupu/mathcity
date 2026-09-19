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
Model: the hecke root layout tree. The tree is the TARGET state: in a
brownfield repo, current deviations go in the Brownfield register —
registered with a disposition, never blessed as contract.

## Tree

Declare the full intended tree, annotated. Every top-level directory and
tracked root file appears here; a real object with no row here is a
finding (LY2).

```
<repo-name>/
├── <dir>/          ← <purpose>
├── ai/             ← durable agent-generated investigations; dated dirs,
│                    own descriptive LAYOUT.md, holds ai-usage.md + tokens.md
├── scratch/        ← genuinely transient output (LY3); disposable
├── LAYOUT.md  LATEX.md  STYLE.md  ADR.md  AGENTS.md
├── AI-POLICY.md  AI-POLICY-SHORT.md
├── ai-usage.md  tokens.md
└── ── gitignored but KEEP on disk ──
```

Every instantiated repo carries this `.gitignore` stanza (LY9); it is type-shaped
so relocation cannot evade it:

```gitignore
# LY9 — never tracked, wherever they sit
*.pdf
*.aux
*.log
*.out
*.toc
*.bbl
*.blg
*.fls
*.fdb_latexmk
*.synctex.gz
*.nav
*.snm
*.vrb
    <pattern>       ← <why it exists and why it is not tracked>
```

## Brownfield register (pending cleanup — NOT part of the contract)

| Current state | Target disposition |
| --- | --- |

Register entries surface in check-layout as KNOWN-DIRTY findings (not
new violations, not passes). A row is removed only after its cleanup
actually happened. Delete this section only in a genuinely clean repo.
Disposition vocabulary: move to <declared dir> | merge into <path> |
demote to scratch/ | keep-untracked (= add a `.gitignore` entry AND a
gitignored-but-keep tree row) | delete (human-approved) | TBD (human).
When no declared home fits, the disposition is scratch/ — never a new
folder. `init-repo-docs` executes dispositions at instantiation.

## Rules

**Non-canonical trees.** `scratch/` (transient) and `ai/` (durable agent
investigations) are both **non-canonical**: their contents are not the
repository's published artifact. Every audit that scopes itself by excluding
non-canonical content excludes **both**. Renaming or adding such a tree means
updating this definition and every predicate that cites it — a predicate naming
only one of them silently starts auditing the other as canonical.

**LY1 — Clean-tree test [C].** A collaborator opening the repo finds
only the published artifact, its documentation, the six repo docs (`AI-POLICY.md` carrying its
`AI-POLICY-SHORT.md` companion), and the two AI records (`ai-usage.md`, `tokens.md`).
No agent or orchestration scaffolding outside the non-canonical trees.
Pass: every tracked path matches a tree row. Fail: any tracked path
with no row.

**LY2 — Tree + register are total [C].** Every top-level directory and
tracked root file has a tree row or a register row; every "gitignored
but keep" pattern is listed. Pass/Fail: mechanical diff of
`git ls-files` + root listing vs tree ∪ register.

**LY3 — Transient output goes to scratch/ [C].** Anything a tool or
agent writes that is not the artifact goes under
`scratch/YYYY-MM-DD-<slug>/`, containing at least `report.md`,
`ai-usage.md`, and `tokens.md` when the work was agent-performed (the
frontier-dump contract; see that skill for the file contracts).
Pass: no transient files outside the non-canonical trees; dump dirs follow the
naming. Fail: stray `.md`/`.mag`/notes at root or elsewhere.

**LY4 — Tex placement.** `.tex` files live only in the directories the
tree marks for LaTeX; which files are canonical there is `LATEX.md`'s
concern (see it; check-layout enforces both together).

**LY5 — Repo docs present [C].** `AI-POLICY.md` (with its
`AI-POLICY-SHORT.md` companion), `LAYOUT.md`, `LATEX.md`, `STYLE.md`,
`ADR.md`, `AGENTS.md` exist at the root and `AGENTS.md` points at the
other four. Pass/Fail: existence + pointer check.

**LY6 — Bloat guard [C].** Each repo doc stays within its cap: `AI-POLICY.md`
≤ 260 content lines (a rule set carrying a mechanical Pass/Fail criterion per
rule; factor prose, never the criteria), every other doc ≤ 120
content (non-blank) lines. Over = finding; trim or factor before
adding.

**LY7 — Naming [C].** New file and folder names: lowercase,
hyphen-separated, no spaces. Existing violators go in the Brownfield
register.

**LY8 — Few folders; scratch is the default [C].** Creating a top-level
directory requires a LAYOUT amendment first. Anything with no declared
home goes to `scratch/` — never a new folder, never loose at root.

**LY9 — PDFs and build byproducts are never tracked [C].**
The rule is on what a file **is**, not where it sits. No `.pdf` is tracked
anywhere in the repository — not under `refs/`, not under `scratch/`, not
beside the `.tex` that produced it. A path-shaped ban is evaded by writing the
same file somewhere else, which is exactly what happened: a `refs/`-shaped rule
was in place while PDFs accumulated under `scratch/.../evidence/`. LaTeX
byproducts are untracked on the same principle: `.aux` `.log` `.out` `.toc`
`.bbl` `.blg` `.fls` `.fdb_latexmk` `.synctex.gz` `.nav` `.snm` `.vrb`.
- Pass: `git ls-files '*.pdf'` returns nothing, and likewise per byproduct
  extension. Mechanical, and unevadable by relocation.
- Fail: any match, wherever it sits.
- Remediation: `git rm --cached <path>` plus a `.gitignore` entry — the file
  stays on disk as keep-untracked (LY3's vocabulary), it is not deleted. A
  PDF that genuinely must be archived (a submitted manuscript of record) is a
  release artifact attached to a tag, never a tracked file.
- Deliberately NOT extended to image types: `generate-graphics` and
  `add-figure` produce legitimately tracked figures, and a blanket image ban
  would break them. Page renders under `scratch/` are covered by LY3.

## Change Log

| Date | Change | Approved by |
| --- | --- | --- |
| `<YYYY-MM-DD>` | Instantiated from mathcity-repo-docs template | `<name>` |
