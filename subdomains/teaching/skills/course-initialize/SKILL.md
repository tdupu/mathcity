---
name: course-initialize
description: >-
  Initialize or roll forward one course and its current offering using existing
  syllabi and earlier course materials. Establish layout, LaTeX, course-format,
  syllabus, assessment, and webpage policies; organize references; link the
  course webpage checkout; and record confirmed course decisions.
---

# Initialize a course

Initialize one course at a time, including the current offering-specific layer.
Create working policies that another agent can use to write materials and
maintain the course webpage. Start from the instructor's actual syllabus,
materials, decisions, and directory structure. Earlier offerings are evidence
for proposals; they do not automatically govern a new term.

This is personal teaching tooling, not a mathematics-research or city-dispatch
workflow. The `using-latexpowers` → `init-repo-docs` pattern is the model for
explicit repository contracts, not a dependency on research-paper rules.
Do not initialize unrelated courses merely because they share a teaching
repository. Creating this skill does not itself initialize a course directory.

## 1. Establish the offering and inspect reality

Read the nearest applicable `AGENTS.md` and any declared policy locations before
editing. Resolve the teaching root, the selected course root, course identity
(including former numbers), current offering, existing syllabus, and website
repository. Discover these from local files, remotes, and course pages before
asking. Ask only for unresolved choices that change the result; use
`grill-with-docs` when available, one question at a time with a recommendation.
Continue independent discovery while waiting.

Use the vocabulary in [CONTEXT.md](CONTEXT.md). Inspect existing policy documents,
ADRs, material READMEs, source files, generated outputs, symlinks, and git status.
Preserve existing work and established paths. If the teaching repository holds
multiple courses, constrain all writes to the selected course and its shared
policy/index files. Never apply one course's assessment rules to another.

Use [references/sources-and-webpage.md](references/sources-and-webpage.md) to:

- locate the current and relevant previous offerings, including old course numbers;
- identify the canonical syllabus and website source, with conflicting candidates;
- assemble an indexed `references/` directory from the materials actually needed;
- resolve the local website checkout and intended symlink target.

## 2. Reconcile sources before extracting policies

Read the selected syllabi and representative materials, not only filenames or
search excerpts. Compare the syllabus with accepted ADRs, course pages, assessment
READMEs, and existing policies. Record each proposed rule with its source and
offering. Explicitly surface contradictions: do not use file modification time,
the newest-looking filename, or a blanket source hierarchy to settle them.

Use [references/syllabus-confirmation.md](references/syllabus-confirmation.md)
for the review matrix. Separate:

- **Confirmed** — the instructor approved the value for this offering, including
  approval already given in the current conversation or applicable accepted records.
- **Proposed** — a recommendation derived from sources, awaiting confirmation.
- **Unresolved** — missing, inconsistent, or unverifiable information.
- **Historical** — describes an earlier offering and has not been carried forward.

When confirmed records conflict with the student-facing syllabus, show the exact
disagreement and affected artifacts. Obtain a decision on the change and how it
will be communicated; do not silently rewrite a syllabus already in use.

## 3. Draft the course and offering contracts

Follow [references/policy-documents.md](references/policy-documents.md) for
document responsibilities, minimal starting structure, and policy metadata.
Create missing documents as Draft and propose focused amendments to existing
ones. Default shared course policies to the course root and offering-specific
policies to the offering root, adapting to an established layout. Do not reset
adopted documents on reruns.

Initialize or connect:

- course-scoped `LAYOUT.md`, `LATEX.md`, `STYLE.md`, and `AGENTS.md` for
  navigation, canonical materials, build instructions, and writing conventions;
- offering-specific `FORMAT.md`, `SYLLABUS.md`, and `WEBPAGE.md`;
- `EXAMS.md` and/or `QUIZZES.md` only for the assessments that offering uses;
- `ADR.md` as the decision index/conventions, preserving existing `docs/adr/`;
- an indexed `references/` folder and a symlink to the canonical offering page
  in the website checkout.

Example applicability: Abstract Algebra may need exam policies and Fundamentals
of Mathematics may need quiz policies; both need syllabus policies. Discover and
confirm the actual current assessment model instead of hardcoding these examples.

The same confirmed fact should have one policy owner. Other policies link to it;
student-facing documents may restate it, and must be checked for agreement.
`FORMAT.md` describes how the class runs, not its typesetting.

## 4. Confirm concrete syllabus items and decisions

Present the filled review matrix and proposed documents before asking for
confirmation. Highlight differences from the selected prior offering. The user
can approve unchanged rows together; ask focused questions for consequential
unresolved items. Do not ask again for already established decisions.

After confirmation, record who approved what, when, and for which offering.
Mark only fully confirmed policy scopes Adopted; keep unresolved portions Draft.
Record substantive choices about pedagogy, grading, assessments, textbooks,
sequencing, and publication in ADRs with context, alternatives, decision, and
consequences. Preserve prior decisions and link superseding decisions; do not
erase last year's rationale. User-requested course decisions belong in the
record even when they would not qualify as software architecture decisions.

For existing-file reorganization, show exact source → destination changes and
apply changes already authorized by the user. Seek approval only for additional
destructive, ambiguous, or out-of-scope changes. A request to initialize does
not require moving all existing materials into the suggested example tree.

## 5. Connect the webpage, webpage workflow, and syllabus workflow

Create the local webpage symlink after verifying the checkout, course, term,
and target path. Follow the link handling rules in the source reference. A
symlink connects existing sources; it does not publish a website.

If the offering page is missing or the user asks to create or revise it, invoke
`create-course-webpage` when installed. Pass the course identity and aliases,
offering root, website checkout and destination, `WEBPAGE.md`, accepted ADRs,
current syllabus, assessment schedule, textbook references, and discovered
prior course pages. That skill owns baseline selection, minimal page content,
and idempotent reconciliation. If unavailable, follow the same rules in
[references/sources-and-webpage.md](references/sources-and-webpage.md): copy the
most recent suitable page from the same course when one exists; otherwise use a
user-selected/instruction-selected base or create a minimal page after asking.

If the user asks to create or revise the syllabus, invoke `generate-syllabus`
when installed. Pass the offering root, policy paths, selected old syllabus,
reference index, confirmation matrix, and accepted decisions. If that skill is
unavailable, follow the self-contained syllabus workflow in
[references/syllabus-confirmation.md](references/syllabus-confirmation.md).
Initialization alone does not require redrafting an already suitable syllabus.

Use `SYLLABUS.md` and `WEBPAGE.md` to make later writing and website changes
consistent with the confirmed format and assessment rules. Edit, publish,
commit, and push only within the user's authorized scope.

## Idempotence

Initialize by reconciling the selected course with the requested state.
With the same offering, sources, and decisions, a second invocation must produce
no persistent changes.

- Discover existing documents, reference IDs, approvals, ADRs, and links first.
  Fill genuine gaps; do not regenerate a starter tree over a populated one.
- Preserve adopted policies, intentional local edits, and existing draft review
  rows. Do not reset statuses, refresh dates, rephrase equivalent text, duplicate
  pending questions, or ask again about unchanged confirmed decisions.
- Reuse reference entries and verified local copies. Do not redownload unchanged
  materials or update retrieval dates solely because initialization ran. If a
  source must be rechecked for currency, change durable records only when new
  evidence changes their content, applicability, or verification state.
- Leave a correctly targeted webpage symlink unchanged. Preserve and report
  collisions; never replace them as a side effect of a rerun.
- Update only the documents and artifacts affected by changed inputs or newly
  confirmed decisions. Retain stable IDs and record each substantive decision
  once. Reconfirmation is limited to choices invalidated or introduced by the
  change. A new offering gets its own scope and term-dependent confirmations;
  previous offerings and their decisions remain intact.
- Do not touch sibling course directories during a no-op check or ordinary
  course initialization.
- An unchanged completed setup is a successful no-op. Report it without writing
  a new run report, timestamp, ADR, or other artifact solely to mark execution.
  Use the same no-op rule for any delegated syllabus generation.

Verify that a second reconciliation with identical inputs needs no file changes.
Do not call a rerun idempotent merely because overwriting files yields similar
content; preserve unchanged files and links themselves.

## 6. Verify and report

Verify real paths and links, reference completeness, current-versus-historical
labels, document scopes/statuses, and the consistency of confirmed rules across
policies, syllabus, assessment instructions, and webpage. Check that public
destinations exclude instructor-only materials. Build and visually inspect
changed LaTeX outputs when this invocation actually changes them.

A rerun should preserve decisions, stable reference IDs, and correct symlinks;
produce only the necessary additions and amendments. Report created/updated
paths, unresolved syllabus items, sources that could not be obtained, and actual
verification results. Distinguish a usable Draft from an adopted policy set.
