# Source-to-Lean correspondence

Read the whole selected statement, its definitions and its proof, not an abstract
or an earlier summary. Capture the exact quantifiers, domain, finiteness,
nonemptiness, characteristic, topology, choice of equality and conventions.
An omitted assumption discovered while formalizing is a mathematical finding.

Use the source's argument as the initial decomposition. For each step record a
precise source locator and what the Lean step must establish. A short quotation
can help when permitted; a locator and faithful paraphrase suffice. Original
bridging lemmas are marked original and proved, never assigned fictitious source
text. A different proof is permissible when it proves the same statement and its
changed dependency argument is recorded and checked.

Separate independently provable conclusions when it improves reuse, retaining
a source-level assembly theorem when useful for correspondence. Do not split
`∃ x, P x ∧ Q x` into two unrelated witnesses. Mutual induction may require a
joint auxiliary result with public projections; the dependency graph is acyclic
over those jointly proved groups. An iff is not a license to drop one direction.

For each proposed dependency, test the actual application/composition term.
Several declarations ending in `by sorry` only check their individual signatures;
they do not show that the planned proof composes. Include core logic, hypotheses,
and existing project results as valid leaves, alongside Mathlib applications.

When a source claim is false, preserve its exact identity and counterexample.
A corrected statement gets a distinct record and an explicit scope decision.
When only a special case is formalized, give the original claim partial status
and report that special case precisely. Search without a hit establishes neither
novelty nor absence from Mathlib.

For example, an injective idempotent self-map satisfies `f (f x) = f x`;
injectivity gives `f x = x`, and extensionality gives `f = id`. The pointwise
lemma, the function-equality theorem and an image/fixed-point characterization
are different claims. Keep their hypotheses and completion records separate.

Round-trip review states the Lean result in ordinary mathematics, then compares
that statement with the source. Inspect definition bodies, instance choices,
coercions and implicit parameters. Compilation is necessary evidence about the
formal statement; it does not perform this semantic comparison.
