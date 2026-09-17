---
name: revise
description: Apply an ACCEPTED review report to the canonical file item-by-item as tagged edits, delivering an item-to-tagged-region map; unclear or unaccepted items are skipped and listed. Use when the user says "apply the accepted report", "work in the review items", "make the approved changes". NOT for producing reviews (referee-report), referee-response sessions (manual astra/fable per ADR 0005), or bulk rewrites — bulk passes are refused.
---

# revise

Runs [../../WRITERS.md](../../WRITERS.md) preamble and postamble in full. This leaf's middle:

## Item-by-item

- Input: the report plus the human's acceptance (which items, any
  modifications). No acceptance record → refuse (acceptance is a human
  act, D3).
- One ST5-tagged region per item (or explicitly grouped items); the
  deliverable includes the map `item → file:tag-slug` so the human can
  accept each region independently.
- Skipped items (unclear, contradicts another item, requires evidence
  that does not exist) are listed with reasons — never silently
  dropped, never guessed at.
- The anti-pattern this leaf exists to prevent (mechanism 4): a bulk
  rewrite that regenerates the file and erases markers — anabelian2
  deleted 182 \taylor{} markers in one pass and needed a 197-row
  disposition table to recover. Edits here are surgical or refused.

## Red flags

| Thought | Reality |
|---|---|
| "Faster to regenerate the section than patch it" | Regeneration erases markers and tags. Surgical or refuse. |
| "Item 7 probably means..." | Probably = skip and list. The human clarifies. |
