---
name: post-lecture-notes
description: Use when asked to post or publish lecture notes to a course webpage, especially scanned notes needing transcription and review first.
---

# Post lecture notes

Reuse one plan and publish once:

1. For scans or unreviewed notes, invoke `latex-course-notes` in `prepare-only` mode. Pass instructor annotations and the exact course/date/topic. Its review and publication-readiness requirements still apply.
2. For already prepared notes, verify the current PDF corresponds to the reviewed source; changed or unreviewed content returns to the preparation/review step.
3. Only after readiness, invoke `update-course-webpage` with the approved public PDF and matching topic. It owns commit, immediate push and publication verification. Respect draft-only/no-push instructions throughout.

`latex-lecture-notes`/`update-webpage` mean `latex-course-notes`/`update-course-webpage`. A no-op requires an unchanged matching link and published PDF matching the reviewed version. Publish changed PDFs at existing links. Never publish via both leaf and wrapper.
