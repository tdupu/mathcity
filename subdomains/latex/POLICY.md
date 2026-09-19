# LaTeX Document Quality Policy

Parent: [README.md](./README.md)

| Field  | Value      |
| ------ | ---------- |
| Status | Draft      |
| Date   | 2026-09-19 |
| Prefix | LX         |

What makes a LaTeX document in this project correct and well-formed.
Every rule below is self-contained: read it, check it, done.
Bead/workflow mechanics live in `latex-bead-guide.md` (a guide, not a policy).

---

## Rules

**LX0 -- Check for typos **

**LX1 — Every reference resolves.**
Every `\ref{}`, `\eqref{}`, and `\cref{}` points at a `\label{}` defined in the document (or its input closure), and no label is defined twice.

- Pass: zero undefined references and zero multiply-defined labels in the compile log.
- Fail: any `??` in output, any "Reference undefined" or "multiply defined" warning.

**LX2 — Every citation is pinpoint.**
Every `\cite` carries a locator: a page number (`\cite[p.~12]{key}`) or a result number (`\cite[Thm.~3.4]{key}`, `\cite[Prop.~2.1]{key}`, `\cite[§5]{key}`).
- Pass: no bare `\cite{key}` anywhere in the document.
- Fail: at least one `\cite{key}` with no optional locator argument.

**LX3 — Bibliography keys use JabRef auto-simplify format.**
Every BibTeX key has the form `FirstAuthorLastNameYEARa` — capitalized author surname, 4-digit year, then the first significant word of the title, lowercase (e.g. `Smith2010a`, `Serre1973a`, `Serre1973b`). The citation should be complete like a clean version of mathscinet. There capitalization of the names in the titles etc must be correct. 

- Pass: every key in the `.bib` file matches `[A-Z][a-zA-Z]*[0-9]{4}[a-z]+`.
- Fail: any key in another format (e.g. `smith-10`, `MR123456`, `mykey`).

**LX4 — Every theorem-class statement is backed.**
Every `theorem`, `proposition`, `lemma`, `corollary`, or `conjecture` environment has exactly one of:
(a) a `proof` environment following it in the document;
(b) a pinpoint citation (per LX2) at the end of, or immediately after, the statement;
(c) a "general knowledge" note — the result is standard enough to appear in at least one graduate level textbook (some remark in the comments is appreciated)

- Pass: each theorem-class environment satisfies (a), (b), or (c). Conjectures satisfy (b) or (c) by attribution, or are explicitly marked as new.
- Fail: any theorem-class statement with no proof, no reference, and no textbook citation.

**LX5 — The document compiles clean.**
The root `.tex` file compiles to PDF with zero errors on a standard engine (pdflatex/xelatex/lualatex), including the BibTeX/biber pass. Check the logs for errors and warnings!

- Pass: full compile cycle exits without errors; a PDF is produced.
- Fail: any compile error, missing `.bib` file, or bibliography pass failure.

**LX6 — No dead bibliography entries.**
Every entry in the `.bib` file is cited at least once in the document. 

- Pass: every bib key appears in some `\cite` (or the file is a declared shared bibliography noted in the preamble).
- Fail: uncited entries in a document-local `.bib` with no such declaration.

**LX10 — Definitions precede theorem-class statements.**
Across every repository and document tier, introduce mathematical terms,
objects, constructions, and notation in a separate definition, construction,
or notation paragraph before the result that uses them. A theorem,
proposition, lemma, corollary, claim, conjecture, or equivalent custom
statement environment states hypotheses and conclusions; it must not also
serve as a definition. This includes inline or parenthetical definitions,
"where ... means", "put", "write ... for", and defining assignments such as
`:=`, not just nested `definition` environments.

Ordinary quantification and hypotheses ("Let $G$ be a finite group") remain
in the statement. Recalling already defined notation and asserting an
identity, characterization, existence, uniqueness, or well-definedness is
allowed; these are not definitions. If a construction requires such a
result, give its recipe with the needed conditions before the statement,
then prove that it works; do not silently assume the conclusion. A purely
local abbreviation inside a proof may stay there, but terminology used
outside that proof belongs before its first use.

- Pass: enumerate every theorem-class environment (including custom aliases
  and starred forms), review each body in context, and report the number
  checked and zero embedded definitions. A keyword scan alone cannot pass.
- Fail -> **revise**: quote each embedded definition with file and line;
  move it before the result, retain all hypotheses and mathematical claims,
  and check notation collisions, labels, references, and compilation.
- This is a binding default quality floor for existing and new repositories,
  even when their local STYLE.md predates ST10. Local policies may tighten
  it, never omit or weaken it. See `definition-separation.md` for examples
  and the review procedure.

**LX11 — Negative results are results, and are stated as such.**
A refutation, counterexample, disproved expectation, or closed-off approach
that the underlying work established is *content*, not bookkeeping. Whenever
the evidence trail behind a document (agent reports, reviews, audits,
ledgers, scratch packages, prior drafts) records that a claim was refuted, an
expected behaviour failed, a proposed definition was ill-posed, or a natural
transplant of a known theorem is false, the canonical document states that
finding as a numbered theorem-class statement, or — when it is not yet proved
— as an explicitly labelled question or conjecture. Deleting a wrong claim
together with its refutation is a violation: the refutation is the result
that survives.

Write the finding as the story it is. Name the expectation, then the fact:
"it is natural to expect $X$; in fact $Y$", with the hypotheses under which
$Y$ holds and the proof or counterexample that establishes it. An
intuition-correcting result is stated at the strength it has — neither
softened into an aside nor inflated into a general theorem.

- Pass: enumerate every refutation, counterexample, and abandoned expectation
  in the document's evidence trail; for each, exhibit the numbered statement,
  question, or conjecture in the document that carries it, with both
  locators. Report the count checked and zero unrecorded findings. A keyword
  scan alone cannot pass.
- Fail -> **revise**: list each refuted expectation present in the evidence
  trail and absent from the document; add it with the expectation named, the
  correct statement, and its proof or counterexample; re-check labels,
  references, and compilation.
- Scope: this is a binding default quality floor for existing and new
  repositories and for every document tier. Local policies may tighten it,
  never omit or weaken it. It applies symmetrically to the document's own
  earlier claims: a statement this document previously asserted and later
  disproved is recorded as a refutation, not silently dropped.

**LX12 — Derived outputs carry the negative results forward.**
Any skill or workflow whose output is produced *from previous work* — a
synthesis, a dump, a digest, a revision, an introduction, an exposition, a
merge, a referee response, a handoff, a summary — transfers the negative
results of that previous work, not only its positive results. Insight gained
by discovering that something is false is the most easily lost and the most
expensive to re-derive; it is transferred first, not last.

- Pass: the derived artifact names every refutation, counterexample, and
  failed-expectation finding of its inputs, or explicitly records, per
  finding, the authorized reason it was excluded from this artifact's scope.
  The check enumerates the input findings and reports the count carried and
  the count excluded with reasons.
- Fail -> **revise**: name each input finding absent from the derived
  artifact and from its exclusion list; carry it forward.
- Applies to (non-exhaustive): `frontier-dump`, `using-latexpowers` and every
  writer it dispatches, `revise`, `fp-finder-latex`, `explain-experiment`,
  `write-introduction`, `merge-latex-sections`, `create-exposition`,
  `referee-report`, `triage-referee-report`, and any handoff or session-end
  skill that renders prior work into a new document.


---

new: 

Check for labels and references for both theorems and subsections. No "by the previous theorem".

Don't use "by the above" etc. 



---

## Trinity status

| Artifact        | Path                                           | Status  |
| --------------- | ---------------------------------------------- | ------- |
| Policy          | `subdomains/latex/POLICY.md` (this file)       | Draft   |
| Check skill     | `subdomains/latex/skills/check-latex-hygiene/` | Written |
| Amendment skill | `subdomains/latex/skills/new-latex-policy/`    | Written |

Check-labels-and-refs



---

## Change Log

| Date       | Change                                                                                                                                   |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-09-19 | Add LX11 (negative results are stated as results, with the expectation they refute named) and LX12 (derived outputs carry input negative results forward). Requested by Taylor Dupuy in conversation 2026-09-19: refutations are "very important learning moments" and the arithmetic-jet work had produced intuition-correcting results that a synthesis pass had dropped rather than reported. |
| 2026-09-17 | Add LX10: definitions precede theorem-class statements in every repository and tier; explicitly requested by Taylor in conversation (he-oj8ve). LX7–LX9 belonged to the superseded draft and are not reused. |
| 2026-07-12 | Full rewrite: policy is now self-contained document-quality rules only (LX1–LX6); bead workflow content moved to `latex-bead-guide.md`; aspirational ideas archived to `../../docs/beads-and-latex-scratch.md`. |
| 2026-07-12 | Initial draft (LX1–LX9, 36 workflow rules) — superseded by the rewrite above.                                                          |
