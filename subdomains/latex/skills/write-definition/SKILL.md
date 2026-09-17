---
name: write-definition
description: Draft ONE definition into the repo's canonical tex file, consistent with the repo's standing notation. Use when the user says "add a definition", "define X in the notes", or when resolve-dependencies reports a missing definition. NOT for claims (write-proposition) or remarks (write-remark). Refuses on notation collision with the repo's declared conventions.
---

# write-definition

Runs `subdomains/latex/WRITERS.md` preamble and postamble in full. This leaf's middle:

## Drafting

- Scan for notation collisions FIRST: the document's own preamble and
  existing definitions, plus STYLE.md's "Repo-specific standing
  conventions" section where the repo declares one. A symbol already
  taken → refuse and propose alternatives; never silently overload.
- Insert at the location the human named, or ask — never guess (D5).
- Definition environment; term bold/emphasized per document practice;
  every symbol in the definiens already defined or standard for the
  declared audience.
- Imported definition: provenance per track-down-reference (opened
  source), cited at the definition.
- Cross-reference: list sites already using the term undefined, for
  the human — do not edit them.

## Red flags

| Thought | Reality |
|---|---|
| "This notation is standard, no need to check" | The repo's conventions outrank the literature's (floor tightening). |
| "I'll also fix the places that use it informally" | List the sites; touching them is separate, gated work. |
