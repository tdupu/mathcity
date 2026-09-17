---
name: write-introduction
description: Draft the introduction/abstract LAST — manuscript tier, human-initiated, behind a hard refusal gate: refuses while results sections carry unresolved markers, VERIFY flags, LX4 failures, or contradiction-check hits; the abstract asserts only ledger-proved claims. Use ONLY when the human explicitly asks ("write the introduction now") — the routers never volunteer it. The refusal is the skill (design D6; mechanism 3).
---

# write-introduction

Runs [../../WRITERS.md](../../WRITERS.md) preamble and postamble in full. This leaf's middle:

## The gate (checked in order; first failure = loud refusal)

1. Human initiation, this conversation, explicitly for THIS document.
2. Zero unresolved `\taylor{}` / `\todo{}` in results sections; zero
   `%\s*VERIFY`-class flags. (Count them; report the count either way.)
3. Every theorem-class statement satisfies LX4 (run check-latex /
   check-latex-hygiene; a FAIL blocks).
4. contradiction-check clean over the document's claims.
5. Ledger rows for every claim the abstract would assert read `proved`
   with recorded doubt runs.

The refusal names each failing item with location — the receipt for
this gate is ai-paper.tex: a polished abstract asserting an unproved
formula while the human draft carried 26 unresolved queries.

## Drafting (gate passed)

- The abstract asserts exactly the ledger-proved claims, in the
  document's own hypotheses — no strengthening, no "for all" beyond
  what is proved.
- Introduction structured per the declared style authority (Tag 02BZ)
  and the repo's terseness variable; titles remain working slugs unless
  the human sets one (ST9/ADR-3 in piloted repos).

## Red flags

| Thought | Reality |
|---|---|
| "The draft is basically done, intro will motivate finishing" | Introduction-first is mechanism 3. Refuse. |
| "One open marker is minor" | One marker = one unresolved question in public. Refuse. |
