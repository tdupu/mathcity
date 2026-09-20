# Project layout

| Field | Value |
| --- | --- |
| Status | Adopted |
| Approved by | Fixture project owner, as initial scenario state |

- Root Markdown documents: project contracts and master AI accounting records.
- Canonical manuscript: the exact file declared in LATEX.md.
- research/: retained raw source reports and attachments; do not overwrite them.
- ai/: durable plans, spec.md, Markdown prototypes/candidates, reviews, research
  requests and returns, provenance; dated run directories may be created.
- scratch/: transient Markdown and the reconciled LEDGER.md, not a second notes
  manuscript. No new .tex files here or under ai/.
- build/: local compilation products, never publication evidence by themselves.
- legacy/ and .claude-outline/: retained historical source if present. Read them
  as evidence; they are not an active second task or claim database.

No other .tex file is declared by this layout. LaTeX excerpts can live in Markdown
until integration. Preserve inputs and review history during all cleanup.
