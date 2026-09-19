# LATEX.md — canonical tex files and declared siblings

<!-- TEMPLATE (mathcity-repo-docs). Instantiate into a repo root, fill
     the tables, delete this comment. The repo's copy is owned by the
     repo: amend only through new-repo-latex-policy. Checked by
     check-layout (shared with LAYOUT.md). -->

| Field | Value |
| --- | --- |
| Repo | `<repo-name>` |
| Status | Draft |
| Date | `<YYYY-MM-DD>` |
| Approved by | `<human name>` |
| Checked by | `check-layout` |
| Amended by | `new-repo-latex-policy` |

Enumerates every real `.tex` file, names the canonical file per
directory, and declares any aspirational files. The canonical-text
invariant (design ADR 0003) binds every writing skill: **in place or
nowhere** — edits land in the canonical file; an undeclared sibling
`.tex` is a violation, and markdown output goes to `scratch/`, never a
second `.tex`.

The invariant has a consequence worth stating here, because it is the one
most often broken in the wrong direction. A result established by the work
belongs in the canonical file whether it is positive or negative: a
refutation, a counterexample, or a disproved expectation is content, not
bookkeeping, and leaving it in a `scratch/` report while the claim it
refutes is deleted from the canonical file loses the finding that survived.
Document quality — including that obligation, stated in full as ST11 of the
STYLE.md template — is governed by this repo's `STYLE.md`; where a mathcity
pack is installed, `subdomains/latex/POLICY.md` (LX-rules) is the shared
floor beneath it. This file only declares which files exist.

## Real files [C]

Every `.tex` under version control **outside `scratch/`**, one row
each (scratch tex is transient, governed by LAYOUT.md LY3, never
canonical). Canonicity is per
tier: at most one canonical `notes`-tier file and one canonical
`manuscript`-tier file per directory (a directory holding both tiers —
`main.tex` beside `notes.tex` — is normal).

| Path | Tier | Canonical? | Purpose |
| --- | --- | --- | --- |
| `<dir>/notes.tex` | notes | yes | expository sandbox |
| `<dir>/<main>.tex` | manuscript | yes | `<venue/target>` |

Tiers: `notes` (expository sandbox; self-containedness default per
design ADR 0004) or `manuscript`. Promotion is one-way:
`scratch/report.md → notes.tex → manuscript`; manuscript-tier promotion
is human-initiated.

Pass: `git ls-files '*.tex'` minus `scratch/` paths equals the table's
Path column; per
directory, at most one canonical row per tier. Fail: any tracked `.tex`
with no row (**undeclared sibling variant** — the fork-not-merge
mechanism), or two canonical files of the same tier in one directory.

## Aspirational files [C]

The ONLY mechanism for declaring a `.tex` that does not exist yet. A
new sibling may be created only if declared here first, with human
approval recorded in the Change Log.

| Planned path | Purpose | Declared | Approved by |
| --- | --- | --- | --- |

Pass: every `.tex` created since the last check either had a Real-files
row or an Aspirational row at creation time. Fail: any other new `.tex`.

## Brownfield note

Pre-existing undeclared siblings found at first instantiation are NOT
retro-declared here; they go through the `triage-variants` disposition
flow (merge into the canonical file, demote to a scratch report, or
delete — one human approval per file), then this table is updated to
match the surviving state.

## Change Log

| Date | Change | Approved by |
| --- | --- | --- |
| `2026-09-19` | Record that refutations belong in the canonical file (ST11), and state the quality floor without requiring a pack | `Taylor, explicit conversation request` |
| `<YYYY-MM-DD>` | Instantiated from mathcity-repo-docs template | `<name>` |
