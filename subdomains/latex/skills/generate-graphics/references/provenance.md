# Graphics provenance manifest

Parent: [generate-graphics](../SKILL.md).

Store `<figure-stem>.json` beside the exported graphics, or use the project's
existing equivalent schema. These are provenance records, not TeX status text.
Paths are relative to a declared project root or to the manifest directory;
state which. A null value means unknown or inapplicable, with a reason. Never
invent a software version, run identifier, timing, or successful check.

| Field | Meaning |
|---|---|
| `figure_id`, `purpose` | Stable identifier and the mathematical question illustrated |
| `evidence_kind` | `exact-computation`, `numerical-computation`, `schematic`, or `imported-asset`; identify mixed cases explicitly |
| `source` | Editable script/notebook path and SHA-256; source revision when known |
| `inputs` | Each input path and SHA-256, or explicit finite inline input data; imported images include attribution/license when known |
| `reproduce` | Working-directory convention, exact command or argument vector, dependencies, and relevant configuration |
| `software` | Actual Sage/Python and plotting-library versions |
| `randomness` | Random seeds for arithmetic, sampling, layout and plotting, or a reason randomness is unused |
| `arithmetic` | Exact ring/field, or numerical precision, error/tolerance conventions and rounding |
| `semantics` | Vertex/edge conventions or axis/units, weights, multiplicity, normalization, color key, and layout meaning |
| `scope` | Field/parameters, complete range versus sample, filtering, exceptions and exclusions |
| `checks` | Check descriptions, expected and observed results, pass/fail, and evidence paths where needed |
| `artifacts` | Output paths, MIME/format, SHA-256, dimensions when relevant |
| `limitations` | What the graphic does not prove and any missing provenance |
| `render_review` | Inspection status and observed defects; leave `pending` until someone actually inspects it |

For a numerical spectrum specify the operator and basis, eigenvalues versus
singular values, multiplicities, precision, the treatment of imaginary parts,
and any rescaling. For a graph specify loops, parallel edges, orientation,
weights, quotienting, and whether visual separation has mathematical meaning.
A force-directed layout's distance between vertices is not an invariant.

Keep exhaustive finite computation distinct from sampling and from a general
proof. A certified finite counterexample can refute a universal statement;
a collection of positive examples does not prove one. Source and input hashes
establish which files were used, not that their mathematics is sound.
