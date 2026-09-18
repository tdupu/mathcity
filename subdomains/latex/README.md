# mathcity-latex

Parent: [../../README-subdomains.md](../../README-subdomains.md)

Notes-tier `.tex` screening, LaTeX-bead workflow policy, and literature
search.

Import alias convention (ADR 0002): skills materialize as
`mathcity-latex.<skill>`.

## Policy

[POLICY.md](POLICY.md) — the LaTeX Subdomain Policy (rule prefix **LX**,
Draft): what LaTeX work is a bead, stage taxonomy (labels on real bd types),
quality-gate semantics, atomization rules, LMFDB coupling, merge discipline,
compile-failure MREs, computation dependencies, and named anti-patterns.
Composes brief-system L1–L4 (gate G6) and the he-jwmy gate charter; bead-side
counterpart is POLICY-beads.md BP7.

## Documents

| File | Role |
| --- | --- |
| [WRITERS.md](./WRITERS.md) | Shared mechanics for every tex-writing skill: resolution, canonical target, contradiction/doubt gates, ST5 tagging, ledger postamble, loud refusal |

## Using the workflow

Start with `using-latexpowers prove X and put a stub in notes.tex`, or name an
existing declared manuscript destination. Proof obligations route through
`using-mathpowers`; unresolved claims remain conjectural stubs.
Both entry points use [math-workflow](../../skills/math-workflow/SKILL.md).
See the [examples and coverage](../../README-skills.md) for prerequisites and
behavioral validation; shorter aliases also resolve.

## Skills

| Skill | Purpose |
| --- | --- |
| `add-figure` | Insert a verified figure at the passage it explains, with caption, unique label, prose reference, provenance, and optional linked example |
| `check-labels-and-refs` | Scan LaTeX files for label/reference consistency, orphan labels/refs, and non-pinpoint cross-references (hurdle H2); composed by `check-latex` |
| `check-latex` | The runnable latex-gate (G6/F1b) evidence engine: compile check, semantic diff summary, approve/reject evidence block (`check-latex-report.{json,md}`) |
| `check-latex-hygiene` | Read-only LX-rule auditor: bead linkage, stage labels, atomization, LMFDB coupling, merge discipline, MREs, computation deps, anti-patterns; consumes `check-latex` reports |
| `explain-experiment` | Scratch dump report -> notes-tier exposition a hostile reader can follow; re-runnable pointers |
| `garbage-collect` | HUMAN-GATED pre-submission strip of retained editorial machinery; enumerate -> approve -> strip -> verify |
| `generate-graphics` | Reproducible Sage graphics: editable source, exact or numerical checks, provenance manifest, vector output and preview |
| `merge-latex-sections` | PLACEHOLDER — merge/reorder sections preserving label/ref integrity; F2 implementation deferred until F1 completes (gsp-fby HOLD) |
| `new-latex-bead` | Create a LaTeX work bead well-formed under LX/BP7 from birth (root target, coverage declaration, stage label, dep edges, gate-evidence acceptance criteria); also performs stage-label advances |
| `new-latex-policy` | Propose and apply an amendment to the LaTeX Subdomain Policy (LX-rules) — sole write path for LX-rule changes; every proposal is approved by a human in conversation and recorded in the policy Change Log; companion to `check-latex-hygiene` |
| `rapid-prototype` | Skeleton a discussion into conjecture/definition stubs in the canonical notes file; statuses agent-side |
| `referee-report` | Adversarial referee-grade review of OUR draft at prover level, to scratch; never edits tex; a green build resolves nothing mathematical (mechanism 5) |
| `resolve-dependencies` | Include-what-you-use walk of a proof: present/imported/missing per item; ledger depends-on; placement is the human's |
| `revise` | Apply an ACCEPTED review report item-by-item as tagged edits with an item-to-region map; bulk rewrites refused |
| `track-down-reference` | Find the actual source for a claim and verify by opening it — pinpoint cite, verbatim quote, hypothesis-match note; no opened source, no citation (mechanism-7 fix) |
| `using-latex` | Compatibility alias for `using-latexpowers` |
| `using-latexpowers` | Entry point with shared planning, research, execution, review, and cleanup; see `math-workflow` |
| `write-definition` | Draft one definition, notation-collision-checked against the repo's standing conventions |
| `write-example` | One self-contained worked example or counterexample with explicit hypotheses, evidence and optional linked figure |
| `write-introduction` | Introduction/abstract LAST behind a hard refusal gate (markers, VERIFY, LX4, contradictions, ledger-proved only) |
| `write-materials-and-methods` | Software/Acknowledgements/AI-disclosure section from the ai-usage/tokens trail; trail-facts only |
| `write-proposition` | Draft one proposition (statement + LX4/ST6 proof) from an evidenced claim into the canonical file |
| `write-remark` | Draft one remark; claim-shaped content is routed to write-proposition |

## Graphics and worked examples

Use `using-latexpowers add a figure explaining this computation in notes.tex`
to reuse the manuscript workflow. `generate-graphics` creates the Sage source,
checked graphics, and provenance; `write-example` explains a finite case;
`add-figure` places its captioned and referenced graphic in the relevant
passage. Each manuscript leaf follows [WRITERS.md](./WRITERS.md). Existing
talk images are reviewed for mathematical relevance and provenance before
inclusion; colors and geometric placement need evidence before they acquire
mathematical meaning.

The [cycle template](skills/generate-graphics/assets/cycle_graph.py) is a
small runnable example, not research data. From the pack root, choose a new
output directory and run:

```bash
sage -python subdomains/latex/skills/generate-graphics/assets/cycle_graph.py <new-output-dir>
bash tests/latex-graphics/smoke_test.sh
```

### Example Coverage

| Example | Runner | Prerequisites | Command | Test path | Status | Issue |
|---|---|---|---|---|---|---|
| Exact four-cycle graphic and provenance | Local | SageMath with matplotlib on PATH | `sage -python subdomains/latex/skills/generate-graphics/assets/cycle_graph.py <new-output-dir>` from pack root | `tests/latex-graphics/smoke_test.sh` | Sage fixture exercised; semantic rerun, provenance and no-overwrite behavior checked | N/A — local fixture |
| Explanatory figure linked to a worked case | Agent | Installed skills, project contracts, evidenced computation, SageMath and configured TeX toolchain | `using-latexpowers write an example for this computed graph and add its figure in notes.tex` | `tests/latex-graphics/scenarios.md` | Behavioral scenario supplied; execution is recorded in the active task's review report | N/A — per-task writer validation |

## Concerns

- **check-latex / latex-hurdle**: the five-hurdle formula (compiles,
  labels-refs, citations, style, human approval) that screens covered
  `.tex` diffs before push. The parent-pack gate
  `mathcity/gates/latex-gate.toml` invokes
  `subdomains/latex/skills/check-latex/check-latex.sh`.
- **lit-search**: arXiv/MathSciNet/citation discovery feeding the
  citation-hygiene hurdle H3.
