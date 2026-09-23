# Syllabus confirmation and generation

Read when extracting syllabus policies, preparing confirmation, or generating
a syllabus without a separate `generate-syllabus` skill.

## Review matrix

Populate this from the actual sources before asking the instructor to decide:

| Item | Prior/current source and locator | Proposed value for this offering | State | Change/conflict | Confirmation |
| --- | --- | --- | --- | --- | --- |

Use Confirmed, Proposed, Unresolved, and Historical as defined in `SKILL.md`.
Confirmation records who decided, when, and the applicable scope. Existing
approval counts; elapsed time, silence, and old-course inclusion do not.
Store the matrix in `SYLLABUS.md` or an existing linked review artifact.

Cover the following as applicable:

- Course number/title, term, section, credits, instructor/contact, prerequisites.
- Meeting pattern, room/modality, term dates, holidays, office hours.
- Texts and exact editions; topic order, learning goals, included/omitted sections.
- Class activities, expected outside work, homework's role, optional components.
- Assessment types/counts, points, design/allowed time, coverage, and schedules.
- Grade components/weights, rounding, dropped scores, replacement formulas, curves.
- Missed work, makeups, quiz/exam redos, excused absences, accommodations, and the
  purpose and schedule of any final-exam meeting.
- Collaboration, academic integrity, devices, and AI use; any truthful disclosure
  of assistance actually used in this offering.
- Current institutional required statements, policy links, support information.
- Course webpage/material links, communication channels, and publication status.

The list is a coverage aid, not permission to invent institution-specific rules.
Verify official dates and requirements from authoritative current sources;
confirm discretionary instructor choices. Ask one focused question at a time
when interviewing. A compact batch can confirm unchanged, nonconflicting rows.

## Reconcile before adopting

Compare current syllabi with ADRs, policy docs, material READMEs, webpages, and
older offerings. Show contradictory values together with their sources and
student-facing consequences. Distinguish an internal construction rule (such as
designing a quiz for five minutes) from allowed student time (such as ten minutes).

Do not silently choose "most recent file wins" or let a draft policy override a
syllabus already issued to students. Record the instructor's resolution in the
policy owner and an ADR when it changes a substantive course decision. Apply
approved changes consistently to the affected artifacts in the authorized scope.

## Generate or revise a syllabus

Generation is idempotent within one offering: reconcile existing artifacts
before writing. Unchanged sources and confirmed decisions require no persistent
changes, repeated approvals, duplicate review rows/ADRs, refreshed dates, or new
output versions. Preserve unresolved rows rather than appending them again.
Changed inputs require only affected revisions and confirmations. Rebuild only
for changed dependencies, missing/stale outputs, or necessary validation; use a
temporary build for a recheck and do not replace an unchanged canonical PDF merely
because its build timestamp differs. A new term is a distinct offering with its
own confirmation scope. An explicitly requested rewrite is itself a new input.

When the user requests a syllabus:

1. Resolve the offering policies, selected baseline syllabus, reference index,
   review matrix, and accepted ADRs. If policies are missing, derive and confirm
   the necessary ones using this workflow; do not require a repository-wide
   reorganization before drafting a syllabus.
2. Adapt the existing source/template and comply with local `LATEX.md`/`STYLE.md`
   where applicable. Preserve content that remains correct. Do not invent a
   room, date, grading rule, textbook edition, or institutional requirement.
3. Draft all supported sections while missing inputs are pending. Clearly label
   unresolved values and the document as Draft; retain an existing adopted
   syllabus until its replacement is approved. An unresolved draft is not a
   final syllabus and must not be published as one.
4. Present the complete draft and the exact changed/pending items for instructor
   confirmation. Approval already given for unchanged items remains valid.
5. Apply confirmed decisions to policy owners and affected materials. Record
   substantive changes and offering scope in ADRs; update the syllabus version
   and date using local conventions.
6. Verify weights/points/formulas and worked grading examples, assessment counts
   and dates, term/calendar agreement, edition/section references, links, and
   alignment with course-format and assessment policies. Check an ordinary and
   boundary case for nontrivial drop/replacement rules.
7. Build using the documented command, inspect errors/references, and visually
   inspect the resulting PDF for overflow, page breaks, tables, and readable
   links. If required tools are unavailable, report the unperformed check.
8. Return the source and rendered syllabus, approval status, and unresolved
   items. Update the public website only when authorized, using `WEBPAGE.md`.

Separate the syllabus's student policies from private assessment-construction
details. Never copy instructor-only questions or answer keys into a syllabus
or public page. Do not repeat old assertions such as "I read every line" or a
particular model attribution unless they accurately describe the current work.
