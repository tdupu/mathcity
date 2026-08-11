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

## Skills

| Skill | Purpose |
| --- | --- |
| `check-latex` | The runnable latex-gate (G6/F1b) evidence engine: compile check, semantic diff summary, approve/reject evidence block (`check-latex-report.{json,md}`) |
| `check-labels-and-refs` | Scan LaTeX files for label/reference consistency, orphan labels/refs, and non-pinpoint cross-references (hurdle H2); composed by `check-latex` |
| `check-latex-hygiene` | Read-only LX-rule auditor: bead linkage, stage labels, atomization, LMFDB coupling, merge discipline, MREs, computation deps, anti-patterns; consumes `check-latex` reports |
| `new-latex-bead` | Create a LaTeX work bead well-formed under LX/BP7 from birth (root target, coverage declaration, stage label, dep edges, gate-evidence acceptance criteria); also performs stage-label advances |
| `merge-latex-sections` | PLACEHOLDER — merge/reorder sections preserving label/ref integrity; F2 implementation deferred until F1 completes (gsp-fby HOLD) |
| `new-latex-policy` | Propose and apply an amendment to the LaTeX Subdomain Policy (LX-rules) — sole write path for LX-rule changes; every proposal is approved by a human in conversation and recorded in the policy Change Log; companion to `check-latex-hygiene` |

## Concerns

- **check-latex / latex-hurdle**: the five-hurdle formula (compiles,
  labels-refs, citations, style, human approval) that screens covered
  `.tex` diffs before push. The parent-pack gate
  `mathcity/gates/latex-gate.toml` invokes
  `subdomains/latex/skills/check-latex/check-latex.sh`.
- **lit-search**: arXiv/MathSciNet/citation discovery feeding the
  citation-hygiene hurdle H3.
