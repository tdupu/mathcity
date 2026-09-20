# Canonical LaTeX files and retained historical input

| Field | Value |
| --- | --- |
| Status | Adopted |
| Approved by | Fixture project owner, as initial scenario state |

| Path | Tier | Canonical? | Purpose |
| --- | --- | --- | --- |
| notes.tex | notes | yes | Elementary exposition |
| legacy/chunk-parity.tex | archival input | no | Retained historical fragment |

The legacy fragment is declared only for preservation and reading; do not compile
or edit it. There are no aspirational or working .tex files. Candidates go into
Markdown under ai/ or scratch/. Integrate before Closing note in notes.tex and
preserve human annotations. Build notes.tex with two pdflatex passes under build/
and inspect its PDF; missing tools remain reported limitations.
