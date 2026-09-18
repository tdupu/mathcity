---
name: generate-graphics
description: Generate or regenerate reproducible mathematical graphics with SageMath for a manuscript, retaining source, inputs, numerical conventions, and a provenance manifest. Use for computed graph diagrams, spectra, and plots; pass manuscript insertion to add-figure.
---

# generate-graphics

Parent: [mathcity-latex](../../README.md).

Produce a SageMath graphics item, its source, and evidence sufficient to tell
what it depicts. This leaf does not edit a manuscript or establish a theorem.
Reuse the active `using-latexpowers` plan; a bounded assignment stays bounded.

## Preflight and scope

- Resolve the project's layout, computation policy, and requested destination.
  Find existing scripts, data, and figures first; extend or rerun an existing
  generator when it covers the task. Do not replace original talk graphics.
- Check `sage --version` and `sage -python -c 'import sage.all'`; use writable
  temporary `DOT_SAGE` and `MPLCONFIGDIR` if normal caches are unavailable.
  Check readable inputs and unused output paths. Missing dependency: stop
  with "I'm sorry, I can't do that — <missing resource>. <Recovery action>.
  <What it enables>." Never invent data.
- State the question illustrated, input range, and intended audience. Fix
  vertex/edge meaning, direction, multiplicity, weights, normalization, field,
  axes, units, and color meaning as applicable before choosing an attractive
  layout. A schematic is identified as schematic; its geometry is not data.

## Generation and evidence

1. Keep an editable Sage source file in the project's declared source location
   and outputs in its declared figure location. Use repository-relative paths
   and an explicit command; no hidden notebook state or absolute home paths.
   Record input hashes, software versions, exact versus numerical arithmetic,
   precision/tolerance, random seeds, and graph positions or layout seed.
   See [the manifest contract](references/provenance.md).
2. Compute the quantity before plotting it. Record a small independent check:
   e.g. vertex/edge counts and degree sums, row sums, trace/eigenvalue sum,
   exact characteristic polynomial, or an analytically known special case.
   Report disconnected pieces, dropped rows, complex eigenvalues, multiplicity,
   truncation, and sampling explicitly; never silently simplify a multigraph.
3. Save a vector PDF for a compatible TeX engine and a PNG preview. Use SVG or
   another format only when the project's build supports it. Use readable
   labels at publication size and color plus labels/shapes/line styles when a
   distinction matters. Do not use an image generator to fabricate a data plot.
4. Inspect the rendered image for clipping, collisions, tiny type, misleading
   scales, lost edge multiplicity, and colors unsupported by the data. Rendering
   successfully is not a semantic check. Rerun in a fresh output directory and
   compare the data/invariants; byte-identical PDFs are not required.
5. Write the manifest with actual check results and unresolved limitations.
   Keep its artifact hashes synchronized after every regeneration. An old
   graphic with missing source is an imported asset with incomplete provenance,
   not a newly reproduced computation.

The [runnable cycle template](assets/cycle_graph.py) demonstrates deterministic
coordinates, exact Sage checks, PDF/PNG exports, and the manifest. Run it with
`sage -python <skill-dir>/assets/cycle_graph.py <new-output-dir>`; copy and adapt
it to the project rather than importing this fixture as project research.

Return paths to source, inputs, rendered files, manifest, and a short caption
brief explaining what the picture supports and what it cannot establish.
Call `add-figure` only when manuscript insertion is requested or part of the
active plan. Use `write-example` for a self-contained finite case, and
`explain-experiment` for a broader computational investigation. Mathematical
claim promotions still require the normal contradiction/doubt gates.
