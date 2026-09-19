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
├── scratch/        ← ALL transient/agent output (LY3); see below
├── LAYOUT.md  LATEX.md  STYLE.md  ADR.md  AGENTS.md
  AI-POLICY.md  AI-POLICY-SHORT.md  ai-usage.md  tokens.md
└── ── gitignored but KEEP on disk ──
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

**LY1 — Clean-tree test [C].** A collaborator opening the repo finds
only the published artifact, its documentation, the six repo docs (`AI-POLICY.md` carrying its
`AI-POLICY-SHORT.md` companion), and the two AI records (`ai-usage.md`, `tokens.md`).
No agent or orchestration scaffolding outside `scratch/`.
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
Pass: no transient files outside `scratch/`; dump dirs follow the
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

## Change Log

| Date | Change | Approved by |
| --- | --- | --- |
| `<YYYY-MM-DD>` | Instantiated from mathcity-repo-docs template | `<name>` |
