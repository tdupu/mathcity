---
name: track-down-reference
description: Find the actual source for a mathematical claim and VERIFY BY OPENING it — a citation counts only when the source was opened and the claim found at a pinpoint locator. Delivers bibkey (LX3 format), pinpoint cite, verbatim quote, and a hypothesis-match note. Use when the user says "track down this reference", "find a source for X", "is this citation actually right", on a %VERIFY marker, on check-citations findings, or for ST6 notes-tier self-containedness. NOT for broad literature review (research-SOH / astra-dump), citation formatting (clean-citations), or inserting the cite into tex (the write-* skills). Unobtainable source = UNVERIFIED report, never cite-anyway.
---

# track-down-reference

Mechanism 7's fix (design record, survey 2026-09-18): citation drift —
right author, wrong paper/theorem; %VERIFY markers multiplying under
generated prose. The rule here is absolute: **no opened source, no
citation.**

## Step 0 — Inputs

The claim (verbatim), any candidate citation, and the repo's LATEX.md/
STYLE.md context (notes tier ⇒ ST6 applies). Resolve local reference
corpora first: the repo's `references/`, `refs/`, or equivalents from
LAYOUT.md.

## Step 1 — Search, local first

1. Local PDFs (filename + full-text where possible) — report how many
   files were searched (a 0-file search is EVIDENCE-ABSENT, not "not
   found locally").
2. Then as fits the claim: `search-scholar`, `search-arxiv`,
   `search-stacks`, `search-mathlib`, `search-lmfdb`.
3. Exhausted without a candidate → delegate a deep hunt per the
   harness: astra-dump (works everywhere); on Claude harnesses the
   fable package pipeline is the alternative (design ADR 0005).

## Step 2 — Open it

Read the actual source (local PDF, arXiv, publisher page). If it
cannot be opened (paywall, dead link, missing scan): the deliverable is
an UNVERIFIED report stating exactly what was tried — never a citation
on faith, never "citation needed" silently dropped.

## Step 3 — Locate and match

Find the claim IN the opened source: theorem/proposition/section/page.
Quote the statement verbatim. Compare hypotheses and conclusion with
the claim as used in OUR text: exact match, weaker/stronger
hypotheses, or merely adjacent — say which; a mismatch is reported,
never papered over (the wild failure was citing the right author's
wrong theorem).

## Step 4 — Deliver

- Bibkey in LX3 JabRef form (`AuthorYEARword`), full entry data.
- Pinpoint citation per LX2 (`\cite[Thm.~3.4]{key}` form).
- The verbatim quote + locator + hypothesis-match note.
- Notes tier (ST6): recommend writing the proof out with the pinpoint,
  not the bare cite.
- Verification line: WHERE it was opened and WHAT was matched. This
  skill edits no tex; the requesting writer inserts.

## Red flags

| Thought | Reality |
|---|---|
| "It's certainly in Ritt somewhere" | Somewhere is not a locator. Open it. |
| "The arXiv abstract confirms it" | Abstracts state, sources prove. Open the paper. |
| "Same author, same topic — close enough" | That is exactly mechanism 7. Match the theorem. |
