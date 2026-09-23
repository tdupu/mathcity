---
name: find-the-technique
description: Search the literature for publications using a technique surfaced by an agent, return pinpoint citations, and optionally update a manuscript after the user confirms the target file.
---

# Find The Technique

Use this when the user wants to identify whether a proof technique, argument
pattern, citation trail, or manuscript move surfaced by an agent already appears
in the literature.

## Workflow

Start by extracting the technique precisely. If the user names a manuscript,
read the relevant local context first, including nearby comments, citation
markers, and bibliography style. Reduce the technique to searchable mathematical
phrases, theorem names, hypotheses, and proof-step orderings.

Search broadly enough to avoid confirmation bias:
- Use local bibliography and repository search first when a manuscript is
  provided.
- Use scholarly search tools, arXiv, MathSciNet-style metadata, publisher
  pages, Stacks Project, or ordinary web search as available.
- Prefer primary sources: papers, books, preprints, or authoritative reference
  projects. Treat secondary pages as leads, not citation evidence.
- Try several formulations of the technique, including theorem names and the
  sequence of proof moves.

For each plausible source, verify the actual text around the candidate result.
Return only references where the cited location genuinely supports the claimed
technique or a clearly stated component of it. Give pinpoint citations with the
most specific stable locator available: theorem, proposition, lemma,
definition, remark, section, tag, equation, and page number when the source has
pages. Say explicitly when a source is only analogous rather than the same
argument.

## Output

Report the findings in a form the user can use directly in a manuscript:
- a short description of the matched technique;
- the strongest references first;
- full pinpoint citations for each source;
- any caveats about scope, hypotheses, or whether the source proves only part of
  the technique;
- BibTeX entries or bibliography text when the user asks for manuscript-ready
  material or when a manuscript update is likely.

Do not invent page numbers or proposition labels. If a source has no stable
pagination, use stable theorem numbers, section numbers, tags, or arXiv page
numbers from the PDF and label them accordingly.

After presenting the references, ask the user whether they have a manuscript
they would like updated. If they confirm and identify the file, update the
manuscript hygienically:
- preserve the document's citation style and bibliography mechanism;
- replace relevant TODO or author-comment markers without disturbing unrelated
  comments;
- add or update BibTeX and inline bibliography entries consistently;
- use pinpoint optional arguments in citations;
- run the relevant LaTeX build or citation audit when available;
- report any remaining unresolved citation markers or build warnings.
