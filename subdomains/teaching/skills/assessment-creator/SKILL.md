---
name: assessment-creator
description: Use when asked to create a quiz, make a quiz, make an exam, or draft another course assessment, problem set, practice test, or assessment solution key.
---

# Create an assessment

1. Resolve the course/offering, assessment type, coverage, audience, date, allowed student time and output format from the request and repository. Read the nearest applicable instructions, adopted syllabus, assessment policies, accepted decisions, README, template and relevant recent examples. Course-specific directions govern points, headings, instructions, notation, filenames and build commands; do not copy stale examples over current policy.
2. Reuse the caller's plan or make a short one. State the item/coverage and difficulty plan. Distinguish the design-time target from the actual time allowed. Ask only for consequential missing constraints or policy conflicts; draft unaffected material while waiting. Do not invent or change grading, accommodations, permitted tools, collaboration/AI or release rules.
3. For key-only work, preserve the designated assessment's items/numbering; create no questions. Otherwise write original items aligned with taught material and policy, with explicit hypotheses, unambiguous instructions and appropriate workload. Check allowed points, totals and weights. Reuse local builds/typesetting; use `using-latex` for LaTeX within this plan.
4. Solve every item independently; check boundaries, assumptions, calculations, claimed uniqueness and rubric consistency. Flag invalid/ambiguous items in key-only work; otherwise correct them. Estimate time against policy, labeling it an estimate, not measured performance. For exams or requested independent review, obtain a capable reviewer and resolve substantive findings before marking ready; disclose reviewer unavailability.
5. For key-only work, produce only the requested private key/rubric; revise items or produce a student version only if requested. Otherwise produce student and private solution outputs required by policy. Exclude keys, notes, comments, metadata and auxiliary files from student artifacts. Build changed outputs and visually check pagination, mathematics, work space and answer leakage; source checks cannot validate PDFs.
6. Return exact paths, coverage, estimated timing, verification and unresolved choices. Unresolved substantive errors mean draft, not ready. Do not publish, email, commit or push by default. Release requires the user's authorization for the particular material; a quiz-release request does not release its key. For authorized website publication, pass only approved public files to `update-course-webpage`.

Preserve existing assessments and unrelated work. Revise selected versions in place when requested; create alternates only when asked or required by policy for new assessments. Synchronize student/key numbering. Unchanged inputs must not duplicate files or alter unrelated assessments.
