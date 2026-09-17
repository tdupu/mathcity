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

## Skills

| Skill | Purpose |
| --- | --- |
| `check-latex` | The runnable latex-gate (G6/F1b) evidence engine: compile check, semantic diff summary, approve/reject evidence block (`check-latex-report.{json,md}`) |
| `check-labels-and-refs` | Scan LaTeX files for label/reference consistency, orphan labels/refs, and non-pinpoint cross-references (hurdle H2); composed by `check-latex` |
| `check-latex-hygiene` | Read-only LX-rule auditor: bead linkage, stage labels, atomization, LMFDB coupling, merge discipline, MREs, computation deps, anti-patterns; consumes `check-latex` reports |
| `new-latex-bead` | Create a LaTeX work bead well-formed under LX/BP7 from birth (root target, coverage declaration, stage label, dep edges, gate-evidence acceptance criteria); also performs stage-label advances |
| `merge-latex-sections` | PLACEHOLDER — merge/reorder sections preserving label/ref integrity; F2 implementation deferred until F1 completes (gsp-fby HOLD) |
| `track-down-reference` | Find the actual source for a claim and verify by opening it — pinpoint cite, verbatim quote, hypothesis-match note; no opened source, no citation (mechanism-7 fix) |
| `explain-experiment` | Scratch dump report -> notes-tier exposition a hostile reader can follow; re-runnable pointers |
| `garbage-collect` | HUMAN-GATED pre-submission strip of retained editorial machinery; enumerate -> approve -> strip -> verify |
| `rapid-prototype` | Skeleton a discussion into conjecture/definition stubs in the canonical notes file; statuses agent-side |
| `referee-report` | Adversarial referee-grade review of OUR draft at prover level, to scratch; never edits tex; a green build resolves nothing mathematical (mechanism 5) |
| `resolve-dependencies` | Include-what-you-use walk of a proof: present/imported/missing per item; ledger depends-on; placement is the human's |
| `revise` | Apply an ACCEPTED review report item-by-item as tagged edits with an item-to-region map; bulk rewrites refused |
| `write-definition` | Draft one definition, notation-collision-checked against the repo's standing conventions |
| `write-introduction` | Introduction/abstract LAST behind a hard refusal gate (markers, VERIFY, LX4, contradictions, ledger-proved only) |
| `write-materials-and-methods` | Software/Acknowledgements/AI-disclosure section from the ai-usage/tokens trail; trail-facts only |
| `write-proposition` | Draft one proposition (statement + LX4/ST6 proof) from an evidenced claim into the canonical file |
| `write-remark` | Draft one remark; claim-shaped content is routed to write-proposition |
| `new-latex-policy` | Propose and apply an amendment to the LaTeX Subdomain Policy (LX-rules) — sole write path for LX-rule changes; every proposal is approved by a human in conversation and recorded in the policy Change Log; companion to `check-latex-hygiene` |

## Concerns

- **check-latex / latex-hurdle**: the five-hurdle formula (compiles,
  labels-refs, citations, style, human approval) that screens covered
  `.tex` diffs before push. The parent-pack gate
  `mathcity/gates/latex-gate.toml` invokes
  `subdomains/latex/skills/check-latex/check-latex.sh`.
- **lit-search**: arXiv/MathSciNet/citation discovery feeding the
  citation-hygiene hurdle H3.
