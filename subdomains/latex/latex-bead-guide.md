# LaTeX Bead Workflow Guide

How LaTeX work moves through the bead system. This is a how-to guide, not a
policy — document quality rules live in `POLICY.md`.

## When to create a LaTeX bead

- Any change to a tracked `.tex` file that will be pushed or merged gets a bead.
- Inline tags (`\todo`, `\reviewer`, `\note`, …) are fine for point fixes within
  one session. If the work outlives the session, file a bead and put its ID in
  the tag: `\todo{he-xxxx: reconcile with §3.2}`.
- No shadow TODO lists — no `TODO.md`, no `% TODO` comment blocks, no
  `todo.tex`. Beads are the tracker.
- Scratch/fixture `.tex` needs no bead until it is promoted into the real
  document tree; the promotion itself is a bead.

## Stage labels

A LaTeX bead carries exactly one stage label, and stages only move forward:

1. `latex-draft` — content being written; compile may fail.
2. `latex-compilation-ready` — compiles clean; labels/refs resolve.
3. `latex-submitted` — content shipped to its target (merged, arXiv, journal).
4. `latex-published` — permanent identifier recorded (DOI, arXiv version).

If something regresses (referee bounce, reverted merge), open a NEW bead
linked to the old one — never downgrade a stage label.

## Scoping a bead (atomization)

- **Default atom: one section of one document.** Name the root `.tex` file and
  the section scope in the bead body; keep the diff inside that scope.
- **Document-scale work is an epic**, decomposed into per-section child beads
  BEFORE work starts.
- **Adjudicability cap:** if the diff would exceed ~200 changed lines or ~3
  sections, split it before review.
- **Split cleanly:** every intermediate bead should leave a compiling document
  with no dangling refs.
- Figures and tables ride with their section. Typos and cosmetic fixes batch
  into one chore bead per document per pass — no per-typo beads.
- A single theorem gets its own bead only when other beads genuinely depend on
  it (real `bd dep` edge); otherwise it rides with its section.

## Anti-patterns

- **The monolith** — one bead, whole-document diff, single adjudication.
  Decompose into an epic first.
- **The mixed-concern diff** — content edits + restyle + restructure in one
  bead. Split by concern so each gets a clean verdict.
- **No compilation target** — a bead that never names the root `.tex` file it
  compiles against. Fragments name their root document.
- **No owner past draft** — anything at `latex-compilation-ready` or beyond
  has an assignee.
- **The gate dodge** — hiding a real edit in "scratch" files or screening it
  as unbeaded to skip review.
