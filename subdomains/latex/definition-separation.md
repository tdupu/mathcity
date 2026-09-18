# Definition separation — LX10 review procedure

Parent: [POLICY.md](./POLICY.md#rules). LX10 is the rule source.
Every writing leaf runs this through WRITERS.md; check-style and
check-latex-hygiene enforce it even if a local STYLE.md lacks ST10.

## Review

1. Resolve the canonical files and their input closure, or the explicitly
   requested scope. Read the preamble for `\newtheorem`, starred forms,
   aliases, and custom statement wrappers. Ignore commented-out history.
2. Enumerate all theorem-class bodies. Record their count and locations.
   Read each body in context, not only sentences containing a keyword.
3. For each introduction of a term, object, map, construction, or symbol,
   ask whether it specifies meaning or asserts a mathematical property.
   New meaning belongs before the statement. Bound variables, hypotheses,
   reminders of earlier definitions, and proved characterizations stay.
4. Record each candidate's disposition with a quote and location. Any
   embedded definition means revise. An unreviewed body means incomplete,
   not pass. Neither a successful compile nor zero keyword hits is evidence
   of semantic conformance.
5. On an authorized revision, place the definition or construction before
   first use. Retain the parameters, hypotheses, source attribution, and
   scope. Preserve theorem labels on their claims. Give a new definition
   its own label when cross-references need one. Do not insert definitions
   in theorem titles, footnotes, or parenthetical clauses as a workaround.
6. Compare old and new mathematical content. If a recipe may fail to
   descend, converge, exist, or be independent of choices, state it with
   that qualification; its well-definedness remains a conclusion to prove.
   Check notation collisions, author markers, labels, references, and the
   build after extraction. A compile pass is not a mathematical proof.

## Example

Embedded definition — **revise**:

```tex
\begin{proposition}
Let $\Gamma$ be finitely generated. Define
$c(\Gamma)=\max\{s:\Gamma\twoheadrightarrow F_s\}$.
Then $c(\Gamma)\le b_1(\Gamma;\mathbb Q)$.
\end{proposition}
```

Separated definition and result — **pass** for LX10:

```tex
\begin{definition}
For a finitely generated group $\Gamma$, its corank is
$c(\Gamma)=\max\{s:\Gamma\twoheadrightarrow F_s\}$,
where $F_s$ is the free group of rank $s$.
\end{definition}
\begin{proposition}
Let $\Gamma$ be finitely generated.
Then $c(\Gamma)\le b_1(\Gamma;\mathbb Q)$.
\end{proposition}
```

This example illustrates separation only; proof and citation checks are
separate requirements.

## Regression cases

When changing the writers or checkers, apply the procedure to these cases
and retain the actual verdicts in the agent-side report.

| Case | Required LX10 verdict |
| --- | --- |
| Definition nested in a theorem | Revise; extract it. |
| `put`, `write ... for`, `called`, or `where ... means` introduces a new notion inside a result | Revise; prose definitions count. |
| A starred custom theorem contains only `N(x):={y:d(x,y)<=1}` and a property | Revise; no keyword is needed. |
| “Let G be a finite group and H a subgroup. Then the order of H divides the order of G.” | Pass; quantification and hypotheses are permitted. |
| Already-defined center Z(A), with a theorem computing Z(A) for a Clifford algebra | Pass; an identity computing an existing object is a conclusion. |
| A recipe is given before the result, which proves it descends or is well-defined | Pass if its conditions and proof obligation are preserved. |
| Proof-local abbreviation, unused outside that proof | Pass; it is local to the proof. |
| Local STYLE.md has only ST1–ST9; global policy header is Draft | Still enforce LX10 as the binding quality floor. |
| Clean PDF and a keyword scan, without reading every body | Incomplete; cannot report pass. |
