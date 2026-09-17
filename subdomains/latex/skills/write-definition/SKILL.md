---
name: write-definition
description: Draft ONE definition into the repo's canonical tex file, consistent with the repo's standing notation. Use when the user says "add a definition", "define X in the notes", or when resolve-dependencies reports a missing definition to fill. NOT for claims (write-proposition) or remarks (write-remark). Refuses on notation collision with the repo's declared conventions.
---

# write-definition

Runs [../../WRITERS.md](../../WRITERS.md) preamble and postamble in full. This leaf's middle:

## Drafting

- Check the repo's standing notation FIRST (STYLE.md's repo-specific
  conventions section and its pointers, e.g. a phase plan's standing
  conventions). A symbol already meaning something else → refuse and
  propose alternatives; never silently overload.
- Definition environment; the defined term bold or emphasized per the
  document's existing practice; every symbol in the definiens already
  defined or standard for the declared audience.
- If the definition is imported: provenance per track-down-reference
  (opened source), cited at the definition.
- Cross-reference: where the term is already used undefined in the
  document, list those sites for the human — do not edit them.

## Red flags

| Thought | Reality |
|---|---|
| "This notation is standard, no need to check the repo's" | The repo's conventions outrank the literature's (floor tightening). |
| "I'll also fix the places that use it informally" | List the sites; touching them is separate, gated work. |
