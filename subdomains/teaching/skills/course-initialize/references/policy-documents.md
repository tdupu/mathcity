# Policy documents and starting structure

Read when drafting the repository contracts. These are teaching-specific seeds;
do not import research-manuscript constraints or invent settled course policies.

## Scope and ownership

In a multi-course teaching repository, default course policies to the selected
course root, repository policies to the teaching root only when they genuinely
apply to every course, and offering policies to the offering root. In a
single-course or single-offering repository, those paths can be at the root.
Preserve an established arrangement and document resolution in `AGENTS.md`.

Every policy starts with:

```markdown
# DOCUMENT.md — descriptive title

- Scope: repository, course, or identified course offering
- Status: Draft or Adopted
- Updated: date
- Approved by: instructor and approval date, or Pending
- Sources: reference IDs with sections/pages, plus relevant ADR IDs
- Inherits: applicable parent policy paths, or None
```

Record exceptions with their scope and approval. Do not silently infer policy
precedence from directory depth. Report conflicts with parent rules for a
decision. An existing policy's amendment procedure continues to apply unless
the user has authorized a different one.

| Document | Owns | Required content |
| --- | --- | --- |
| `LAYOUT.md` | Locations and canonical files | Actual/target tree; course-term naming; source versus build output; canonical syllabus and assessment entrypoints; historical material; reference locations; public/instructor-only boundaries; webpage link and target mapping; existing deviations |
| `LATEX.md` | Document production | Existing classes, packages, macros and shared styles; source roots; working directories and exact build commands; output/auxiliary paths; student/solution variants; page and writing-space requirements; PDF checks |
| `STYLE.md` | Writing conventions | Audience and prerequisites; notation and textbook edition; explanation/proof level; problem/solution/rubric conventions; terminology and source attribution |
| `FORMAT.md` | Course operation | Course identity/aliases and term; modality; meeting pattern; how class time is used; workload; topic sequence and omissions; assessment types; grade model; role of homework and optional components |
| `SYLLABUS.md` | Syllabus maintenance | Canonical source/output; required sections; confirmed logistics and student policies; links to the grade model and assessment rules; confirmation matrix; institutional sources; how adopted changes propagate |
| `EXAMS.md` | Exam construction | Scope/coverage per exam; assumed earlier material; design time versus allowed time; blueprint, points, difficulty and prerequisites; solutions/rubrics; practice-versus-real rules; distribution/release rules |
| `QUIZZES.md` | Quiz construction | Frequency and assessed standards; coverage window; design/allowed time; points; number of questions/parts; writing space; solutions/rubrics; absence, drop, redo/replacement rules linked to their policy owner; release rules |
| `WEBPAGE.md` | Course site maintenance | Checkout/remote and public URL; entrypoint and asset paths; chosen prior-page baseline or minimal-page decision; what the page contains; source policy for schedules and material links; explicit publishable files; `create-course-webpage` workflow; preview/build/deploy process and authorization |
| `ADR.md` | Decision navigation and conventions | Existing/new record location; ID convention; scope, status, supersession and approval requirements; index of relevant records |
| `AGENTS.md` | Agent entrypoint | Paths and scopes of the above; how to resolve offering policies; writing and website workflows; confirmation and publication boundaries |

Preserve named owners already in use. If grading is already owned by a syllabus
policy, link it from `FORMAT.md` instead of duplicating it. Check derived facts
(point totals, grade weights, dropped-score counts) against that owner.

## Example minimal tree

Adapt rather than rename a populated repository to match this example.

```text
teaching/
  course-id/
    AGENTS.md  LAYOUT.md  LATEX.md  STYLE.md  ADR.md
    CONTEXT.md                  # optional course glossary, vocabulary only
    docs/adr/                   # preserve existing course decision history
    term/
      FORMAT.md  SYLLABUS.md  WEBPAGE.md
      EXAMS.md or QUIZZES.md    # only applicable types; both if needed
      references/
        INDEX.md
        previous-offerings/    # term-labeled syllabi and useful examples
        institutional/         # current official sources or indexed links
        texts/                 # edition/section references; legal local copies
      syllabus/                # canonical source and chosen deliverable
      exams/ or quizzes/       # only directories with an actual purpose
      webpage.html -> verified website checkout/offering-page.html
```

Additional materials such as handouts and problems keep their existing homes.
An existing `texts/` directory can remain canonical; the reference index can
point to it. Avoid duplicate textbook PDFs and template-only empty directories.
Create `references/` with its index even when all sources are linked elsewhere.
Use descriptive names plus term/edition where collisions are possible.

## Populate specific policies from evidence

For Abstract Algebra, examine the current syllabus, prior exams, practice exams,
solutions, style files, and exam README to propose exam policy. Confirm the
blueprint and timing; distinguish the new-material coverage window from whether
earlier knowledge remains assumed. Do not import a pandemic-era homework grade
model just because an older syllabus uses it.

For Fundamentals of Mathematics, examine the current syllabus, quiz sources,
standards, grading notes, and prior pages to propose quiz policy. Confirm the
number of quizzes, point scale, drop calculation, and redo/final arrangement.
An old README saying "no final" cannot settle a conflict with a current syllabus
describing a final redo session. Book editions and renumbered courses also
require explicit mapping before carrying forward section or exercise numbers.

For both, derive `SYLLABUS.md` from an actual existing syllabus and current
institutional sources, then confirm its offering-specific items. Prior sources
can suggest alternatives without making them binding.

## Course decision record template

Use the existing ADR convention when present; otherwise use this format in
`docs/adr/NNNN-short-title.md`, indexed by `ADR.md`:

```markdown
# ADR-NNNN — Decision title

- Date: date
- Status: Proposed / Accepted / Superseded
- Scope: named course and term, or explicitly named shared scope
- Decided by: instructor and confirmation record, or Pending
- Sources: reference IDs and precise sections/pages
- Supersedes: prior ADR ID, or None

## Context
What changed or required a decision; relevant prior-offering behavior.

## Alternatives
The actual choices and their trade-offs.

## Decision
The exact selected rule, applicable term, and effective date where relevant.

## Consequences
Effects on teaching, grading, syllabus, assessments, and webpage.

## Affected artifacts
Policy and material paths; which already reflect the decision and which differ.
```

Do not label an agent recommendation Accepted. Preserve original decision text
when adding supersession links/statuses. A rule accepted for one year does not
become permanent for every future offering. On rollover, retain old offering
records, link proposed carry-forward rules to them, and confirm the new scope.

If a glossary exists, keep it about vocabulary; policy claims found there are
evidence to reconcile, not an excuse to rewrite the glossary during initialization.
