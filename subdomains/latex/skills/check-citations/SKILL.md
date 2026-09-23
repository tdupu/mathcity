---
name: check-citations
description: >-
  Read-only citation audit for .tex files. Scans \cite{} calls, validates each key against .bib file(s), flags non-pinpoint references (missing page number AND missing mathematical atom). Emits check-citations-report.{json,md} under ~/gt/tmp-for-taylor/bead-id/. Used as the citation sub-skill of check-latex. Read-only: no Edit/Write/git.
---

> **STATUS: PRELIMINARY (DRY-RUN ONLY).** Read-only. Writes ONLY under
> `~/gt/tmp-for-taylor/<bead>/`. No `Edit`/`Write`/`MultiEdit`/`git commit`
> /`git push`/`bd update`. This is a v0 preliminary per `he-cnat`.
> Companion write-enabled skill: `clean-citations` (proposals mode in v0).

# check-citations

Read-only citation audit skill. Scans a `.tex` file for all `\cite{}` calls,
validates each key against the project's `.bib` file(s), and flags non-pinpoint
references. Produces a structured report consumed by `clean-citations`.

## When to use

Use whenever you need to audit citation quality in a `.tex` file:
- Before pushing a notes-tier `.tex` edit (the LaTeX gate requires citation evidence)
- When `check-latex` composes you as part of its gate evidence block
- To identify broken `.bib` keys or vague citations before submitting

## Workflow

1. **Locate the .bib file(s)** — search in this order:
   - Same directory as the `.tex` file
   - A sibling `refs/` directory
   - Record `bib_files: [], note: "no .bib found"` if neither is present

2. **Enumerate citations** — scan the `.tex` file for all `\cite{...}` patterns:
   - `\cite{key}`, `\cite[optional]{key}`, `\cite{key1,key2,...}`
   - Split multi-key citations; record each key as a separate entry
   - Capture: `key`, `tex_line`, `optional_arg` (or null), `context` (surrounding text excerpt)

3. **Check bib_match** — for each cited key, check whether the key appears as
   `@...{key,` in any discovered `.bib` file. Record `bib_match: true` or `false`.

4. **Detect non-pinpoint citations** — a citation is **pinpoint** if its optional
   argument contains at least one of:
   - A **page reference**: matches `\bp\.?\s*\d`, `\bpp\.?\s*\d`, or `\bpage\b` followed by a number
   - A **mathematical atom**: any of `Theorem`, `Proposition`, `Lemma`,
     `Definition`, `Remark`, `Corollary`, `Example`, `Conjecture` (case-insensitive)
   
   A citation with no optional argument, or whose optional argument contains
   neither a page reference nor a mathematical atom, is flagged `non_pinpoint: true`.
   Otherwise record `non_pinpoint: false`.

5. **Write the report** — create `~/gt/tmp-for-taylor/<bead>/`:
   ```
   check-citations-report.json   — JSON array of citation objects
   check-citations-report.md     — human-readable Markdown table
   ```
   Use the current bead ID from context as `<bead>`. If no bead is active, use
   a slug like `check-citations-<yyyy-mm-dd>`.

   **JSON schema per entry:**
   ```json
   {
     "key": "smith1984",
     "bib_match": true,
     "non_pinpoint": false,
     "tex_line": 47,
     "optional_arg": "Theorem 3.1",
     "context": "...see \\cite[Theorem 3.1]{smith1984} for the proof..."
   }
   ```

   **Markdown table format:**
   ```markdown
   | Key | bib_match | non_pinpoint | Line | Optional arg |
   |-----|-----------|--------------|------|--------------|
   | smith1984 | ✓ | ✗ | 47 | Theorem 3.1 |
   ```

6. **Empty case** — if the `.tex` file has no `\cite{}` calls, write reports
   with `citations: []` and a note `"no citations found in <filename>"`.
   Do NOT raise an error.

## Report output contract

- The JSON report at `check-citations-report.json` has top-level structure:
  ```json
  {
    "tex_file": "<absolute path>",
    "bib_files": ["<path>", ...],
    "note": "<note if no bib found>",
    "citations": [...]
  }
  ```
- The Markdown report summarizes the same data as a table plus a brief header.
- Neither report file modifies any `.tex` or `.bib` file.

## Read-only constraint

This skill is **entirely read-only**:
- Use `Read`, `Bash` (read-only commands: `grep`, `find`, `cat`, `ls`), and
  `Write` ONLY for the two report files under `~/gt/tmp-for-taylor/<bead>/`.
- Never call `Edit`, `MultiEdit`, or any write-to-source-file pattern.
- Never run `git commit`, `git push`, `git add`, or `git checkout`.
- Never call `bd update` or any bead-mutation command.

## Cross-reference

`clean-citations` is the companion write-enabled skill. It reads
`check-citations-report.json` produced by this skill and emits proposed
citation corrections (proposals-mode in v0; in-place writes in v1).
Run `check-citations` first, then pass its report path to `clean-citations`.

## Examples

**Broken citation detected:**
```
tex: \cite{smith1984}     bib: no "smith1984" entry
→ {key: "smith1984", bib_match: false, non_pinpoint: true}
```

**Non-pinpoint citation flagged:**
```
tex: \cite{jones2020}     (no optional arg)
bib: "jones2020" entry exists
→ {key: "jones2020", bib_match: true, non_pinpoint: true}
```

**Pinpoint citation accepted:**
```
tex: \cite[Theorem 2.3]{jones2020}
bib: "jones2020" entry exists
→ {key: "jones2020", bib_match: true, non_pinpoint: false}
```

**Empty file:**
```
tex: hyperboloid.tex (0 \cite{} calls)
→ {citations: [], note: "no citations found in hyperboloid.tex"}
```
