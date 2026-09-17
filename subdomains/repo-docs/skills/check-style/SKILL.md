---
name: check-style
description: Read-only audit of a repo's .tex sources against the repo's own STYLE.md (ST rules) — statement discipline, 80-char lines, marker/tag discipline, tex purity, commit discipline. Scopeable to named files. Use when the user says "check style", "check-style", or as the style hurdle before any notes/manuscript promotion. Companion: new-repo-style-policy (sole write path). NOT for compile/label/citation quality (LX floor: check-latex, check-labels-and-refs, check-latex-hygiene) and NOT for fixing — it only reports.
---

# check-style

Audits `.tex` sources against the repo's **own** `STYLE.md`. RED
baseline: `baselines-phase1.md` scenario B — unguided agents reduce
"style" to compile-fixing plus personal preference, editing the
canonical file untagged (mechanism 12; D5).

## Step 0 — Resolve

Run the shared preamble: `subdomains/repo-docs/RESOLUTION.md`.
Resolve the repo's `STYLE.md` (and `LATEX.md` for scope — canonical
files and declared siblings only). On miss: instantiate
`subdomains/repo-docs/templates/STYLE.md` and interrupt. No
approved resolution → DEFER, stop. Read the style variables first;
they parameterize every judgment.

## Step 1 — Enumerate

Scope parameter: default repo-wide (the repo's declared `.tex` files);
the caller may scope to named files (WRITERS.md composes it
single-file). Report the count; zero repo-wide where LATEX.md declares
files is `EVIDENCE-ABSENT` (RESOLUTION.md §5).

## Step 2 — Check, per rule ID

Cite IDs; rules live in the repo's STYLE.md (pointer-not-copy).
Mechanical clauses ([C]) get commands; judgment clauses get quotes:

- **ST1** — `grep -n 'begin{lemma}\|begin{corollary}'` on diffs/files
  in scope.
- **ST2** — quote each statement whose hypotheses are not introduced in
  its opening sentence; never rewrite it.
- **ST3** — line-length scan, per file, with counts.
- **ST4/ST5** — marker + tag discipline: agent edits inside `agent-*`
  tag lines; no human marker (`\taylor{}`, `\todo{}`) or human tag
  created, deleted, or edited by an agent; `\agentreply{}` only
  adjacent to the marker it answers. Check `git log -p` when the diff
  is agent-attributed.
- **ST6** — notes-tier imported results: proof + pinpoint present once
  the source was found (source-verification: `check-citations` /
  track-down-reference).
- **ST7** — no status-taxonomy comments demanding attention.
- **ST8** — `git log` scan: AI-disclosure line present when applicable;
  no `Co-Authored-By`.
- **ST9** — titles-last: introduction/abstract present while results
  carry unresolved markers or undischarged proofs, or without human
  initiation → finding; new-file names use LY7 slugs.

Floor breaches (LX territory: unresolved refs, bare cites, unproved
statements) → `FLOOR-BREACH`, pointed at `check-latex-hygiene`.

## Step 3 — Report

```
CHECK-STYLE <repo> <date>
Resolution: <docs found | instantiated+approved | DEFER>
Variables: <kind/terseness/audience as declared>
Checked: <scope; N files, N statements, N agent-attributed commits>
Findings: <rule-ID>: <path:line>: <one line or quote>
Verdict: PASS | ADVISORY-PASS | FAIL | DEFER
Remediation: <finding → new-repo-style-policy | revise | human>
```

## Hard rules

Read-only — never edits a `.tex`, never "fixes while here", never
resolves a `\taylor{}` question, never commits. Style judgments not
derivable from STYLE.md + Tag 02BZ are DEFER items for the human, not
opinions.
