# Canonical LaTeX files

| Field | Value |
| --- | --- |
| Status | Adopted |
| Approved by | Fixture project owner, as initial scenario state |

| Path | Tier | Canonical? | Purpose |
| --- | --- | --- | --- |
| notes.tex | notes | yes | Elementary mathematical exposition |

There are no aspirational or working .tex files. Prototypes and candidates may
be Markdown with LaTeX excerpts. Integrate within the declared document, before
its end. Use the existing relevant section or insert a section before Closing
note; the owner authorizes routine ordering and insertion within the requested
topic. Preserve unrelated sections and human comments and markers.

Build the declared target using pdflatex, with two passes for references, with
output under build/. Inspect the resulting PDF when a viewer is available.
Unavailable build or PDF tools must be reported; source review alone is not
final manuscript acceptance.
