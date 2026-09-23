---
name: latex-diff
description: Create a reviewed PDF comparison between two resolved manuscript versions with latexdiff; use for referee updates, revision reviews, and version-to-version .tex diffs.
---

# LaTeX diff

Use this leaf when a manuscript needs an explicit source comparison. It
produces a disposable `.tex` source and compiled PDF, and never edits either
input source.

1. Resolve the repository contracts first. Read the nearest `AGENTS.md`, the
   manuscript layout/LaTeX policy, and any local build instructions. Identify
   the exact old and new sources. If one version is in Git, resolve its commit
   and path with `git show`; do not guess from a filename or working-tree
   state. Report an ambiguous pair instead of comparing arbitrary files.

2. Check that `latexdiff` is installed and record `latexdiff --version` when
   available. The package documentation is
   <https://ctan.org/pkg/latexdiff?lang=en>. Do not install software or alter
   the manuscript repository as part of this leaf. If the command is absent,
   stop with the dependency and documentation link.

3. Materialize historical input only in a temporary location, then run the
   bundled `scripts/latex-diff-pdf.sh OLD NEW OUTPUT-DIR [BASENAME]` helper.
   It invokes `latexdiff --type=UNDERLINE --graphics-markup=none --flatten`
   and compiles the result with `latexmk`. `UNDERLINE` is explicit: additions
   render in blue and deletions render in red with strikeout. Graphics markup is
   disabled so the comparison does not require an `\includegraphics`
   definition that may exist only in one source version. Put all generated
   output under the repository's declared scratch/build directory unless the
   caller names a different destination. Keep the output names explicit, for
   example `manuscript-current-vs-previous.tex` and `.pdf`. Preserve the old
   and new inputs.

4. Validate both artifacts: the source is nonempty, contains the expected
   LaTeX preamble, and contains `\\DIFadd` or `\\DIFdel` when the inputs
   differ; the PDF exists, is nonempty, and renders successfully. Confirm the
   source contains the red/blue markup definitions and inspect representative
   rendered pages for red strikeouts and blue additions. If the files are
   identical, say so rather than fabricating a diff. Report unresolved
   references or package failures separately from the source comparison.

5. Return the exact old source, new source, resolved Git revision if relevant,
   command/version, both output paths, and validation result. A generated diff
   is not canonical manuscript source and must not be committed unless the
   user explicitly requests that disposition.

The diff is a review aid, not mathematical verification. Use the manuscript's
referee, citation, and proof-review skills for those obligations.
