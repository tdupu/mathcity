# LaTeX Document Quality Policy

Parent: [README.md](./README.md)

| Field  | Value      |
| ------ | ---------- |
| Status | Draft      |
| Date   | 2026-09-17 |
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
| 2026-09-17 | Add LX10: definitions precede theorem-class statements in every repository and tier; explicitly requested by Taylor in conversation (he-oj8ve). LX7–LX9 belonged to the superseded draft and are not reused. |
| 2026-07-12 | Full rewrite: policy is now self-contained document-quality rules only (LX1–LX6); bead workflow content moved to `latex-bead-guide.md`; aspirational ideas archived to `../../docs/beads-and-latex-scratch.md`. |
| 2026-07-12 | Initial draft (LX1–LX9, 36 workflow rules) — superseded by the rewrite above.                                                          |
