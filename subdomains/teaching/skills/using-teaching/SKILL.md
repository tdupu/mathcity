---
name: using-teaching
description: Use when managing course materials or planning teaching work, including syllabus changes, quizzes, exams, course webpages, scanned course notes, and lecture-note publication.
---

<SUBAGENT-STOP>
If assigned a bounded subtask, follow that assignment; do not start a second teaching workflow.
</SUBAGENT-STOP>

# Using teaching

Invoke the matching leaf before acting. If the route is wrong, switch rather than forcing it. Announce the route. For changes, first read [workflow control](references/workflow.md); reuse an active plan and its confirmed inputs. Read-only questions need no edit plan or publication.

| Request | Skill |
|---|---|
| Initialize or roll forward a whole offering | `course-initialize` |
| Create/revise a syllabus | `generate-syllabus` |
| Create a quiz, exam, assessment or key | `assessment-creator` |
| Change an existing page, e.g. office hours or one date | `update-course-webpage` |
| Create a new course webpage | `create-course-webpage` |
| Transcribe scans into reviewed course notes | `latex-course-notes` |
| Post lecture notes, including preparation if needed | `post-lecture-notes` |

Explicitly named skills win ties. Otherwise posting notes uses the wrapper; it delegates preparation without publication, then publishes once. Multiple deliverables share one dependency-ordered plan, not competing controllers. Leaves call math/LaTeX workflows only for relevant work; they do not restart this router. Locate dependencies through the active skill catalog; report missing dependencies without pretending to invoke them.

System/developer instructions, applicable repository instructions and direct user requests outrank this skill. Do not infer new publication authority from routing.
