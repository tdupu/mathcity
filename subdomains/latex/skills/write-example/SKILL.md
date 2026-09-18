---
name: write-example
description: Write one self-contained worked mathematical example or counterexample in the declared LaTeX manuscript, with explicit hypotheses, reproducible calculation or proof, and optional linked figures. Use to explain a finite case, not to smuggle in a general theorem.
---

# write-example

Parent: [mathcity-latex](../../README.md).

Run [WRITERS.md](../../WRITERS.md) preamble and postamble in full. Use the
project's existing example environment and label convention. If it has no
such environment, use a permitted titled paragraph or make the smallest
style-compatible declaration within the authorized task; never invent a
competing manuscript. Check referenced evidence/assets and the configured
TeX toolchain before writing; missing dependencies get a named reason and a
specific recovery action, never invented output.

## Drafting one example

1. Identify the phenomenon, the earlier definition/result it illustrates,
   and the precise finite instance. State its field/ring, parameters,
   equivalence convention, and every hypothesis needed by the calculation.
   Explain why the instance satisfies those hypotheses.
2. Give reproducible intermediate work. Exact identities need a derivation,
   checked certificate or verified pinpoint reference. State computational
   range, exact/numerical arithmetic, tolerance and multiplicities/normalization.
   Keep source/data pointers in a TeX comment and ledger; consult only
   `explain-experiment`'s provenance conventions, without dispatching it.
3. State the lesson and its scope. A single instance is an example; a
   counterexample must satisfy the proposed statement's hypotheses and
   explicitly violate its conclusion. General conclusions require
   `write-proposition` or an explicitly marked conjecture through
   `rapid-prototype`. A pretty picture is not the missing derivation.
4. Introduce new terminology before any theorem-class statement (LX10).
   Keep workflow statuses in the ledger. Apply the contradiction gate and
   SOUND doubt requirement to claim promotions, including computational
   claims; relabeling a claim as an example does not evade those gates.
5. When called by `add-figure`, return the example label without a figure.
   Otherwise, for an explanatory graphic call `add-figure` once with the
   existing/reserved example label and no example redispatch. Require unique
   labels, two-way references and captioned encoding.

Preserve all human markers and prior text under the shared tagging rules.
Finish with the writer postamble, reporting the example label, dependencies,
calculation or certificate, optional figure link, and actual validation.
