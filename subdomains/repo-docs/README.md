# mathcity-repo-docs

Parent: [../../README-subdomains.md](../../README-subdomains.md)

Default repo-doc templates and their trinities: the contracts a research
repository declares about itself (layout, canonical tex files, writing
style, decisions, agent entry point), the read-only checkers that audit
a repo against its own instantiated copies, and the human-gated
amendment skills that are the sole write paths.

Import alias convention (ADR 0002): skills materialize as
`mathcity-repo-docs.<skill>`.

Binding design record: `mathpowers-latexpowers-design` (Taylor's docs
tree) — ADRs 0001 (repo-local-first resolution), 0003 (canonical-text
invariant), 0004 (tex purity / agent-side ledger). RED baselines:
`baselines-phase1.md` there.

## Documents

| File | Role |
| --- | --- |
| [RESOLUTION.md](./RESOLUTION.md) | Shared check-skill preamble: repo-local-first, import-and-interrupt, floor and Status semantics, instruments-must-fail |
| [AMENDMENT.md](./AMENDMENT.md) | Shared amendment procedure: proposal → human gate → apply + Change Log → verify → conservative commit |
| [LEDGER.md](./LEDGER.md) | Agent-side claim-ledger convention (ADR 0004): five-way status taxonomy, dependencies, doubt records; never authoritative, reconciled by tex rescan |
| [templates/LAYOUT.md](./templates/LAYOUT.md) | Default layout contract (LY rules) |
| [templates/LATEX.md](./templates/LATEX.md) | Default canonical-tex declaration (LT rules) |
| [templates/STYLE.md](./templates/STYLE.md) | Default writing contract (ST rules; style variables; machine-tag format) |
| [templates/ADR.md](./templates/ADR.md) | Default decision record (AR rules) |
| [templates/AGENTS.md](./templates/AGENTS.md) | Default agent entry point (AG rules; pointer-only) |

Templates are **instantiated-then-owned**: the pack copy is a seed and
floor; a repo's copy is the contract, amended only through the skills
below. Templates ship Status: Draft; adoption is a human act.

## Skills

| Skill | Purpose |
| --- | --- |
| `check-layout` | Audit vs LAYOUT.md + LATEX.md + AGENTS.md pointers; undeclared-sibling-.tex detection (routes to triage-variants) |
| `init-repo-docs` | Instantiate the five contracts AND make the repo hygienic: register brownfield, one human-approved disposition batch, execute (git mv / scratch / gitignore), verify with check-layout |
| `triage-variants` | Disposition each undeclared sibling .tex (merge / demote / declare / delete), one human approval per file; emits contradiction reports; never adjudicates math |
| `check-style` | Audit .tex vs STYLE.md (statement discipline, markers, agent tags, commit discipline) |
| `check-adr` | Audit ADR.md shape/numbering; detect decision text scattered outside it |
| `new-repo-layout-policy` | Sole write path for a repo's LAYOUT.md |
| `new-repo-latex-policy` | Sole write path for a repo's LATEX.md (incl. aspirational-file declarations) |
| `new-repo-style-policy` | Sole write path for a repo's STYLE.md |
| `new-repo-adr-policy` | Sole write path for a repo's ADR.md (entries, supersessions, migrations) |
| `new-repo-agents-policy` | Sole write path for a repo's AGENTS.md |

## Division of labor

- Document QUALITY (.tex refs, citations, statement backing, compile):
  `subdomains/latex` — the LX floor. These skills never fork it.
- Bead-side LaTeX workflow: LX rules / `new-latex-bead`.
- City-side decisions: bd decision beads; ADR.md is the repo-side
  record.
- Brownfield sibling-variant disposition: `triage-variants`
  (mathpowers/latexpowers Phase 2), one human approval per file.
