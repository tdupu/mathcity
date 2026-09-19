# AGENTS.md — agent entry point for `<repo-name>`

<!-- TEMPLATE (mathcity-repo-docs). Instantiate into a repo root, fill
     the pointers and repo-specifics, delete this comment. The repo's
     copy is owned by the repo: amend only through
     new-repo-agents-policy. Pointer conformance is checked by
     check-layout (LY5/AG rules). -->

| Field | Value |
| --- | --- |
| Repo | `<repo-name>` |
| Status | Draft |
| Date | `<YYYY-MM-DD>` |
| Approved by | `<human name>` |
| Amended by | `new-repo-agents-policy` |

This file POINTS; it does not restate. An AGENTS.md that contains only
task-tracker boilerplate — or that restates rules whose home is another
doc — is the failure this template exists to prevent (survey mechanism
12: "agents had nothing to obey").

## The repo's contracts (read before working)

| Concern | Document |
| --- | --- |
| What goes where, clean-tree rules | [LAYOUT.md](./LAYOUT.md) |
| Which `.tex` files exist and which are canonical | [LATEX.md](./LATEX.md) |
| How mathematics is written here | [STYLE.md](./STYLE.md) |
| Decisions already made | [ADR.md](./ADR.md) |
| How AI use is disclosed and software cited | [AI-POLICY.md](./AI-POLICY.md) (index: [AI-POLICY-SHORT.md](./AI-POLICY-SHORT.md)) |

Global floor for `.tex` quality: `mathcity/subdomains/latex/POLICY.md`
(LX-rules) — repo docs tighten it, never loosen it.

## Rules

**AG1 — Pointer-only [C].** This file contains pointers, the repo's
task-tracking contract, and repo-specific run instructions; it restates
no rule whose home is one of the five docs above.
Pass: no rule text duplicated from LAYOUT/LATEX/STYLE/ADR/AI-POLICY.

**AG2 — Canonical tree and mirrors [C].** `.agents/` is the canonical
repo-local agent tree (skills at `.agents/skills/`); `.claude/` and
`.codex/` are mirrors, real files not symlinks (the hecke pattern).
`CLAUDE.md`, if present, redirects here.
Pass: mirrors byte-match canonical; CLAUDE.md is a pointer.

**AG3 — Where agents write.** Agent output that is not the artifact
goes under `scratch/` per LAYOUT.md LY3. Canonical `.tex` edits follow
STYLE.md ST4/ST5 (marker channel, comment-out-and-tag under an
`agent-*` tag).

## Task tracking

`<bd contract for this repo: store location, dolt remote, pull/push
discipline — or "no bead store; do not bd init". Never leave the
boilerplate here without verifying the store exists.>`

## Repo-specific instructions

`<build commands, working-directory rules, data-generation notes — or
pointers to the READMEs that hold them>`

## Change Log

| Date | Change | Approved by |
| --- | --- | --- |
| `<YYYY-MM-DD>` | Instantiated from mathcity-repo-docs template | `<name>` |
