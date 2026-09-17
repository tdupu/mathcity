# ADR.md — decision record

<!-- TEMPLATE (mathcity-repo-docs). Instantiate into a repo root, delete
     this comment. The repo's copy is owned by the repo: entries are
     added only through new-repo-adr-policy (human-approved). Checked by
     check-adr. -->

| Field | Value |
| --- | --- |
| Repo | `<repo-name>` |
| Status | Draft |
| Date | `<YYYY-MM-DD>` |
| Approved by | `<human name>` |
| Checked by | `check-adr` |
| Amended by | `new-repo-adr-policy` |

One lightweight file per repo, append-only, newest entry last. Records
decisions about the repo's mathematics, writing, and organization that a
future reader would otherwise re-litigate. Not a task tracker (beads)
and not a rule book (that is LAYOUT/LATEX/STYLE — a decision that
creates a standing checkable rule ALSO lands there via its amendment
skill, with the ADR entry as its rationale).

## Rules

**AR1 — Shape [C].** Every entry has exactly: heading
`## ADR-<n> — <title>`, then `Date`, `Status`
(accepted / superseded by ADR-<m>), `Decision` (one to three
sentences), `Why`, and optionally `Alternatives rejected`.
Pass/Fail: mechanical parse of every entry.

**AR2 — Append-only, monotone numbering [C].** Entries are never
deleted or renumbered; superseding is a new entry plus a Status edit on
the old one. Pass: numbering is 1..n with no gaps; git history shows no
entry deletions.

**AR3 — Decisions live here, once.** A decision is recorded in this
file and pointed at from elsewhere — never restated in AGENTS.md,
READMEs, or ad-hoc files (CONVENTIONS.md and the like are the
anti-pattern; the RED baseline for this trinity produced exactly that).

**AR4 — Human-approved.** Entries record decisions a human made or
approved in conversation; an agent may draft an entry but the entry
states who decided.

## Entries

## ADR-1 — <title>

- Date: `<YYYY-MM-DD>`
- Status: accepted
- Decision: `<what was decided>`
- Why: `<rationale>`

## Change Log

| Date | Change | Approved by |
| --- | --- | --- |
| `<YYYY-MM-DD>` | Instantiated from mathcity-repo-docs template | `<name>` |
