---
name: add-figure
description: Insert a verified mathematical graphic into the declared LaTeX manuscript at the passage it explains, with a substantive caption, unique label, prose reference, provenance, and an optional linked example. Preserve human annotations and the shared writer gates.
---

# add-figure

Parent: [mathcity-latex](../../README.md).

Run [WRITERS.md](../../WRITERS.md) preamble and postamble in full. This is a
manuscript-writing leaf, not a graph generator. Reuse the active plan.

## Preflight

Verify the declared TeX root, its graphic paths, build command, and supported
image formats. Confirm the asset exists and inspect it before editing. Read
its source/provenance and the nearby definitions, claims, and human markers.
Missing asset or build tool: stop that operation with a named missing
resource, a concrete recovery action, and what it enables; do not insert a
broken include or report an unrun build as successful.

For a computed figure, require evidence identifying inputs and validating its
mathematical meaning. If source or provenance is missing, try to recover it
or route to `generate-graphics`. An explicitly identified schematic or
attributed illustration may still be used when it explains a construction,
but it cannot serve as evidence for unverified numerical claims. Preserve
uncertainty in the caption and agent-side ledger.

## Placement and writing

- Choose the first substantive passage that explains the depicted phenomenon,
  after the notation/objects it needs. Include useful figures selectively;
  do not make an unexplained gallery from a talk's asset directory.
- Reuse the repository's figure environment and label convention. Normally
  use `figure`, `\centering`, `\includegraphics[width=...\linewidth]{...}`,
  `\caption{...}`, then `\label{fig:...}`. TeX chooses the float's final
  page; verify the compiled placement. Do not invent a `graphics` environment.
- Explain the figure's lesson with a precise `\ref`/`\cref`. Caption objects,
  parameters, axes or vertices/edges, colors, normalization and scope.
  Patterns are not theorems; approximations are not equalities. Explain
  non-invariant layout choices that readers could misinterpret.
- For a worked case, reuse a supplied/existing example label. If absent,
  request `write-example` once with figure insertion disabled, then resume.
  Insert once, link both ways, return without redispatch. Keep the derivation
  in the example; definitions precede results (LX10).
- Follow WRITERS' edit tags, preserve superseded prose as comments, and leave
  every human annotation untouched. Answer a human question with an adjacent
  `\agentreply{...}`, never by replacing its marker. Add verified pinpoint
  citations for imported mathematics and attribution for reused images.
- Put source/script and manifest pointers in TeX comments and the durable
  ledger. Use portable project-relative paths; keep hashes and process
  status in the manifest/ledger rather than the printed caption.

## Verify and return

Run the declared full TeX build, label/reference and citation checks, and
inspect the actual PDF page at reading size. Check the caption, prose, and
image agree; report stale or missing provenance. A passing compile alone
cannot certify the graph. Return the inserted region, figure/example labels,
asset/manifest paths, and build/render-review evidence through the shared
writer postamble. Do not declare human acceptance on the user's behalf.
