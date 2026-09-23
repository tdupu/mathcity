---
name: latex-course-notes
description: Use when given scanned or handwritten course notes to transcribe into LaTeX, including incomplete notes and instructor annotations; also responds to latex-lecture-notes.
---

# LaTeX course notes

Default: transcribe, independently review, correct, and post beside the course topic. `prepare-only` stops at reviewed source/PDF for a caller to publish. A no-publication request overrides the default.

1. Resolve the course, lecture date/topic, all scan pages, instructor annotations, canonical notes destination and webpage. Read applicable policies and templates. Inspect every scan visually; OCR is an aid, not evidence sufficient to settle an ambiguous symbol. For existing typeset notes, use their source and provenance instead. If neither scans nor usable notes exist, request them rather than inventing a lecture.
2. Invoke `using-latex` within the existing coordinator's plan. Preserve mathematical content, order and notation while improving legibility. Track uncertain readings and gaps with page/region references in private review notes. Instructor corrections override the scan when explicit. Distinguish transcription from supplied explanation or reconstructed arguments.
3. Complete only bounded gaps that can be justified and checked against the course context. Verify new mathematical arguments through `using-math` within the same plan. Never guess an unreadable quantifier or silently supply a substantial theorem/proof. Ask targeted questions and continue independent sections. For intentionally incomplete notes, preserve explicit gaps; hold publication if ambiguity changes the mathematical meaning unless the instructor approves a clearly labeled incomplete version.
4. Build and visually inspect the PDF using local conventions. Give an independent high-capability review agent the scan, annotations, LaTeX, rendered PDF and uncertainty list. Select the strongest available suitable reviewer; do not silently substitute a lower-capability review. Ask it to check fidelity, hypotheses, correctness of arguments/completions, omissions, clarity and layout. Missing source access or unavailable review means review incomplete, not approval.
5. Correct supported findings and have the reviewer recheck affected content in the final artifact. Allow at most three review/correction rounds; unresolved substantive findings or compilation/rendering failures leave a draft and block publication. Keep the private provenance/review notes separate from student-facing material.
6. Return source/PDF paths and review status. In `prepare-only`, stop here. Otherwise pass the approved public PDF and exact topic/date to `update-course-webpage`, which owns the single scoped commit/push. Do not publish raw scans, private annotations or LaTeX sources unless requested. Verify the link targets this reviewed version; do not post duplicate links on reruns.

Do not call `post-lecture-notes` from this leaf. Report transcription gaps, added explanations and anything not independently checked; compilation alone is not mathematical review.
