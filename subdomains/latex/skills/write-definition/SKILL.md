---
name: write-definition
description: Draft ONE definition into the repo's canonical tex file, consistent with the repo's standing notation. Use when the user says "add a definition", "define X in the notes", or when resolve-dependencies reports a missing definition. NOT for claims (write-proposition) or remarks (write-remark). Refuses on notation collision with the repo's declared conventions.
---

# write-definition

Runs `subdomains/latex/WRITERS.md` preamble and postamble in full. This leaf's middle:

## Definition separation

Place the definition before the first theorem-class statement that uses
it (LX10), never inside that statement. When extracting an existing
definition, retain its parameter conditions and keep every hypothesis
needed by the subsequent result explicit. Do not promote a claim of
existence or well-definedness into an assumption of the definition.

### One-concept rule

One `definition` environment defines exactly one mathematical object,
construction, or term. A paired construction (for example, a jet functor and
a Greenberg functor) must use separate adjacent definitions with separate
signatures and parameter domains. Comparisons, non-identification warnings,
representability caveats, and equivalence claims belong in a following
`remark`, proposition, or theorem, never appended to the preceding
definition. Do not write a sentence such as “the corresponding ... is” inside
the first definition when it introduces a second object; start a new
definition environment instead.

Before writing, make a definition inventory with one row per concept:

| Concept | Domain/test category | Defining formula | Name of representing object |
|---|---|---|---|

The inventory must have one row for every displayed construction. The writer
must then check that each row has exactly one definition environment and that
all comparison prose has been moved to a separate remark. If two rows would
share an environment, stop and split the draft before editing the canonical
file.

### Mechanical check before closing the environment

The one-concept rule is violated far more often than it is invoked,
including by reviewers looking straight at the violation, because
nothing catches it: a consequence sentence inside a `definition`
compiles exactly as well as one outside it. Check it by hand, every
time, on the draft you are about to write:

- read the body from `\end{enumerate}` — or from the last defining
  sentence — to `\end{definition}`;
- every sentence in that span is a defect unless it is itself a
  definition. "Equivalently, ...", "We identify ... with ...", "Thus $X$
  is source-side while $Y$ is target-side", "It follows that ..." are
  consequences, conventions and observations; all of them belong after
  `\end{definition}`;
- a convention ranging wider than this one definition belongs to the
  Conventions section, not to either side of this environment.

When editing an existing definition for any reason, run the same check
over what is already there, and report violations you do not fix.

### Competing notions each get a definition

When a claim proves false because it conflated several inequivalent
notions, the repair is structural and it starts here: define each
candidate notion, with its own environment and label, placed *before*
the statement that adjudicates them (LX10). The theorem then says under
what hypotheses they agree, and examples show the hypotheses cannot be
dropped.

Do not record the conflation as a remark about a previous draft — see
write-remark. The definitions and the theorem are the record.

## Drafting

- Scan for notation collisions FIRST: the document's own preamble and
  existing definitions, plus STYLE.md's "Repo-specific standing
  conventions" section where the repo declares one. A symbol already
  taken → refuse and propose alternatives; never silently overload.
- Insert at the location the human named, or ask — never guess (D5).
- Definition environment; term bold/emphasized per document practice;
  every symbol in the definiens already defined or standard for the
  declared audience.
- A definition environment may state notation for a representing object only
  conditionally (“when representable, write ...”); it may not assert the
  representability theorem or an identification with another construction.
- Imported definition: provenance per track-down-reference (opened
  source), cited at the definition.
- Cross-reference: list sites already using the term undefined, for
  the human — do not edit them.

## Red flags

| Thought | Reality |
|---|---|
| "This notation is standard, no need to check" | The repo's conventions outrank the literature's (floor tightening). |
| "I'll also fix the places that use it informally" | List the sites; touching them is separate, gated work. |
