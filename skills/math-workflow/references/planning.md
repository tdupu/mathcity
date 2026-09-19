# Framing, research, and the claim plan

Parent: [math-workflow](../SKILL.md).

## Mathematical brainstorming

Adapt `brainstorming`: establish the target before choosing a method. Read
instructions, source, ledger, and prior attempts before consequential questions.
Use `grill-with-docs` only for sustained interviewing; suppress its
`domain-modeling` file writes. Keep provisional terms/decisions in the run
plan or scratch; durable glossary/ADR/policy changes use declared paths and
their owning amendment leaves.

Record:

- **Purpose and audience:** research decision, proof, teaching, notes, paper,
  review, or repair; reader prerequisites and desired level of detail.
- **Target:** exact objects, quantifiers, hypotheses, conclusion, notation,
  and admissible methods. Distinguish a theorem from a conjecture or question.
- **Structure:** definitions before claims; dependency graph; strongest known
  special cases, counterexamples, reductions, and circularity risks.
- **Alternatives:** compare plausible approaches and their decisive obstacles;
  reuse established results. `check-zero` before a new construction or method.
- **Deliverables:** proof/research record and, in latex mode, manuscript tier,
  canonical root file, destination and stub versus complete exposition.
- **Success and limits:** evidence needed, review scope, user budget, missing
  information, and conditions for abandoning an approach or revising the plan.

A precise “prove X” can supply the design: state the hypotheses, approach,
outputs, and uncertainties, then proceed within authorization. A target with
several inequivalent readings needs clarification before dependent proving.
Choose a promising approach without pretending its open lemmas are settled.

## Research depth

| Observable need | Investigation |
|---|---|
| Recorded status, local typo, build fault, or existing proof audit | Read the relevant local evidence; no compulsory literature campaign |
| One missing theorem, definition, or citation | Focused source search and hypothesis match |
| Survey requested, several unresolved dependencies, novelty/method question, or failed approaches leave a genuine research gap | Deep research below |

Deep research is a phase, not a dependency on a tool called “deep-research.”
Use it from either router when its predicate fires, and revisit the plan when
it changes the mathematical target or dependencies.

1. **Question map.** List the questions whose answers change the proof or
   section plan, existing knowledge, likely sources, and evidence needed.
   Inspect local references and failed attempts before searching externally.
2. **Targeted sweep.** Use `search-arxiv`, `search-scholar`, `search-stacks`,
   `search-mathlib` (lookup only), `search-lmfdb` (objects/data), and
   `find-the-technique` where their domains fit. Independent questions may
   run concurrently; do not launch every search service by default.
3. **Verify.** `track-down-reference` opens each load-bearing primary source,
   records the exact theorem/tag/page and checks its hypotheses against the
   intended use. Metadata, abstracts, snippets, and model recollections are
   leads. Inaccessible sources stay UNVERIFIED and cannot support promotion.
4. **Synthesize.** Explain what follows, what does not, competing accounts,
   and proof/section implications. Use `frontier-dump` for synthesis requiring
   a prover-level investigation, subject to backend availability. Separate
   established results, conditional arguments, computations, conjectures, and
   refutations; a search with no hit is not evidence of novelty or openness.
5. **Record and return.** Save questions, searches, primary-source pointers,
   verified matches, failed leads, and remaining gaps in the run's scratch
   artifacts. Reconcile evidence and dependencies in the claim ledger;
   run `contradiction-check` before harvest of conflicting claims. Resume the
   plan. A research leaf recommending drafting does not perform that drafting.

Stop a sweep when load-bearing questions have checked answers, the declared
budget is reached, or further searches repeat leads without changing the
gap. State unsearched scope and the next useful action; do not label a bounded
search exhaustive. Escalate difficult synthesis by capability, not by issuing
the same failing query repeatedly.

## The plan contract

This adapts `writing-plans`: exact inputs, outputs, dependencies, and checks,
without fabricated complete proof steps or mandatory software commits.

Use the declared plan location; otherwise save `plan.md` in the run's allowed
scratch directory with its evidence. Check every plan/evidence path against
layout rules before creation. Without a declared scratch root, propose
`scratch/<date>-<topic>/` and obtain required authorization. Use a unique run;
never overwrite earlier work. The plan specifies work; task state belongs
in the repository tracker, not a second checklist database.

Every nontrivial plan records the framed goal, mode, scope, permissions,
artifact manifest, relevant constraints, and this table:

| Claim or section | Inputs and evidence | Dependencies | Action and owner | Output path | Validation | Open question / stopping condition |
|---|---|---|---|---|---|---|
| One exact assertion or section purpose | Local proof, checked source, or explicitly missing evidence | Claim IDs, definitions, hypotheses | Research, prove/refute, review, draft, or check; capability level | Exact repository-relative destination | Counterexample checks, proof review, source match, or build command | The unresolved step and what will settle or block it |

For a manuscript, add a section outline mapping every planned claim to its
evidence, reader prerequisites, and dependency order. For proof-only work,
the claim graph is sufficient. For cleanup/audit, plan the concrete files,
findings, permitted changes, and checks; do not manufacture theorem tasks.

Self-review coverage, circular dependencies, hypothesis drift, shared write
conflicts, missing validators, and authorization. “Find whether lemma L holds”
is legitimate research work; “L is true; fill proof later” is not a completed
argument. Where policy requires plan approval, present the concrete plan.
Otherwise continue authorized execution; planning alone does not fulfill a
request to prove or write.
