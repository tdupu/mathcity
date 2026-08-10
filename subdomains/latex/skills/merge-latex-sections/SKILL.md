---
name: merge-latex-sections
description: >-
  STATUS: PLACEHOLDER — full F2 implementation deferred until F1 (latex-hurdle
  five-hurdle formula) is complete. See gsp-fby HOLD. Merge or reorder LaTeX
  sections in notes-tier .tex files while preserving label/ref integrity and
  satisfying the latex-hurdle H2 (labels-and-refs clean) and H5 (the human adjudicator
  approval) requirements.
---

# STATUS: PLACEHOLDER

**Full implementation is deferred until F1 (the latex-hurdle five-hurdle formula) is complete.**

See bead gsp-fby (HOLD) for the deferral record.

## Intended scope (F2)

When implemented, this skill will:
1. Accept a target `.tex` file and a merge plan (sections to combine, reorder, or split).
2. Apply the merge while preserving all `\label`/`\ref`/`\cite` integrity (verified by `check-labels-and-refs`).
3. Produce a diff for human approval via the H5 latex-hurdle stop gate before any commit.

Do not invoke this skill until the F2 implementation bead is opened and closed.
