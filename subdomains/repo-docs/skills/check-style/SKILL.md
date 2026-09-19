---
name: check-style
description: Read-only audit of a repo's .tex sources against the repo's own STYLE.md (ST rules) — statement discipline, 80-char lines, marker/tag discipline, tex purity, commit discipline, and whether the negative results in the repo's agent-side evidence are carried into the canonical document (ST11). Scopeable to named files. Use when the user says "check style", "check-style", or as the style hurdle before any notes/manuscript promotion. Companion: new-repo-style-policy (sole write path). NOT for compile/label/citation quality (LX floor: check-latex, check-labels-and-refs, check-latex-hygiene) and NOT for fixing — it only reports.
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

- **ST10 / LX10** — always run the statement-body review in
  `subdomains/latex/definition-separation.md`, including custom aliases
  and starred forms. Quote embedded definitions, report the number of
  bodies reviewed, and record the verdict for every candidate. This
  binding floor applies even if the resolved STYLE.md lacks ST10; a
  missing local rule is not an exemption. Keywords are triage only.

- **ST11** — negative results. Enumerate the refutations,
  counterexamples, ill-posed proposals, and failed expectations recorded in
  the repo's agent-side evidence: `scratch/` reports and ledgers, review
  packages, and any superseded draft the change set under audit replaces.
  For each, locate the numbered statement, question, or conjecture in the
  canonical document that carries it, and report both locators. Report the
  number enumerated and the number carried; a finding present in the
  evidence and absent from the document is an ST11 finding, and the
  remediation is a writer, never deletion of the evidence. A keyword scan
  is triage only and cannot produce a PASS here. Also check the framing of
  each carried finding: the refuted expectation is named in the text, the
  correct statement stands at the strength actually proved, and a
  refutation has not been demoted to an unnumbered aside. When the change
  set under audit was produced by a skill that renders prior work into a new
  document — a dump, digest, synthesis, revision, introduction, exposition,
  merge, or handoff — apply the same check to that skill's inputs and report
  the counts carried and excluded with their scope reasons. This floor binds
  even if the resolved STYLE.md predates ST11.

Floor breaches (LX territory: unresolved refs, bare cites, unproved
statements, embedded definitions) → `FLOOR-BREACH`, pointed at `check-latex-hygiene`.

## Step 3 — Report

```
CHECK-STYLE <repo> <date>
Resolution: <docs found | instantiated+approved | DEFER>
Variables: <kind/terseness/audience as declared>
Checked: <scope; N files, N statements, N agent-attributed commits,
         N evidence findings enumerated / N carried (ST11)>
Findings: <rule-ID>: <path:line>: <one line or quote>
Verdict: PASS | ADVISORY-PASS | FAIL | DEFER
Remediation: <finding → new-repo-style-policy | revise | human>
```

## Hard rules

Read-only — never edits a `.tex`, never "fixes while here", never
resolves a `\taylor{}` question, never commits. Style judgments not
derivable from STYLE.md + Tag 02BZ and the mandatory LX quality floor
are DEFER items for the human, not
opinions.
