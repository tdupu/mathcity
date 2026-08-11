# mathcity

Mathcity is a [Gas City](https://github.com/gastownhall/gascity) pack for
mathematical work. It manages agent output by routing work through structured
briefs: an agent does work, records evidence, files a brief, gates check that
the brief is clean enough to read, and a human adjudicates what happens next.

The design goal is to manage slop with workflow. Experiments need documented
questions, outcomes, breadcrumbs, and test evidence. Bugs need reproducible
examples or explicit blockers. Features need documentation, examples, tests,
and clean handoff paths. Formula, skill, bead, and documentation drift are
fed back into repair workflows instead of becoming invisible background debt.

All ordinary work should enter through `mathcity.work`, which routes beads to
the appropriate briefed formula. Nothing in mathcity silently merges, opens a
PR, files a GitHub issue, or starts the Mayor without an explicit request and
the relevant human-adjudicated path.

## Documentation Map

The display below is hierarchical, but the link graph is intentionally not a
tree: documents link upward via `Parent:` links and sideways when another doc
is the better source of truth.

```text
README.md
├── Start Here
│   ├── SETUP.md
│   ├── docs/INSTALL.md
│   └── README-dolt.md
├── System Model
│   ├── GLOSSARY.md
│   ├── docs/TECHNICAL-SPEC.md
│   ├── README-beads.md
│   ├── README-mayor.md
│   └── README-clerk.md
├── Catalogs
│   ├── README-formulas.md
│   ├── README-skills.md
│   └── README-subdomains.md
├── Development
│   ├── README-development.md
│   ├── POLICY-POLICY.md
│   ├── POLICY-formulas.md
│   ├── POLICY-beads.md
│   └── subdomains/dev/
└── Subdomains
    ├── subdomains/brief-system/
    ├── subdomains/computing/
    ├── subdomains/dev/
    ├── subdomains/latex/
    ├── subdomains/lmfdb/
    ├── subdomains/magma/
    └── subdomains/proof-assist/
```

## Important Documents

| Document | Purpose |
| --- | --- |
| [SETUP.md](./SETUP.md) | Setup from first principles for supported operator environments. |
| [docs/INSTALL.md](./docs/INSTALL.md) | Command-level installation guide. |
| [README-dolt.md](./README-dolt.md) | Private bead backup and Dolt remote setup. |
| [GLOSSARY.md](./GLOSSARY.md) | Canonical vocabulary. |
| [docs/TECHNICAL-SPEC.md](./docs/TECHNICAL-SPEC.md) | Precise system mechanics: formulas, gates, feedback loops, roles, and current/planned surfaces. |
| [README-formulas.md](./README-formulas.md) | Canonical formula index. |
| [README-skills.md](./README-skills.md) | Canonical skill index. |
| [README-subdomains.md](./README-subdomains.md) | Canonical subdomain index. |
| [README-development.md](./README-development.md) | Development workflow, policies, handoffs, tests, and documentation discipline. |
| [README-mayor.md](./README-mayor.md) | Mayor role and boundaries. |
| [README-clerk.md](./README-clerk.md) | Outside clerk role and adjudication loop. |

## Core Workflow

```text
bead or artifact
  -> mathcity.work
  -> briefed formula
  -> brief in pile
  -> brief-gate-keep
  -> brief-shuffle
  -> stack
  -> present-briefs
  -> adjudicate-brief
  -> decision dispatch or follow-up work
```

The technical details live in [docs/TECHNICAL-SPEC.md](./docs/TECHNICAL-SPEC.md).

## Current Work Paths

| Work shape | Current surface | Notes |
| --- | --- | --- |
| Bounded task | `simple-work-briefed` | Lightweight execute-and-brief path. |
| Full feature work | `build-basic-briefed` | Requirements, plan, decompose, implement, review, and terminal decision brief. |
| Planning first | `planning-briefed` | Produces a plan/design/PERT brief before implementation. |
| Testing | `testing-work` and `smoke-test-briefed` | Generates/runs smoke tests and files test evidence. |
| Issue handoff | `create-issue-briefed` | Drafts a GitHub issue body as a decision brief; never files it directly. |
| PR handoff | `pr-pipeline-briefed` | Drafts a PR body as a decision brief; never pushes or opens a PR directly. |
| Formula creation | `formula-work` -> `formula-creator-math` | Current path drafts a formula and briefs it; planned rework in #3 should add formula planning, docs, and tests as first-class steps. |

Planned surfaces are tracked in the issue tracker and summarized in
[docs/TECHNICAL-SPEC.md](./docs/TECHNICAL-SPEC.md).

## Example Coverage

| Example | Runner | Prerequisites | Command | Test path | Status | Issue |
| --- | --- | --- | --- | --- | --- | --- |
| Run cheap local tests | local shell | Python with `pytest`; shell | `python3 -m pytest tests/stuck-bead-watch/test_stuck_bead_watch.py tests/tail-end-detector/test_tail_end_detector.py` | `tests/stuck-bead-watch/test_stuck_bead_watch.py`; `tests/tail-end-detector/test_tail_end_detector.py` | current | none |
| Run smoke scripts | local shell | shell plus optional tools used by individual smoke tests | `for t in tests/*/smoke_test.sh; do bash "$t"; done` | `tests/*/smoke_test.sh` | current | none |
| Draft an issue body brief | Gas City formula | configured city, `gc`, `bd`, imported mathcity pack | `gc sling <rig>/gc.run-operator create-issue-briefed --formula --var source_bead=<bead> --var brief_slug=<slug>` | `tests/create-issue-briefed/smoke_test.sh` | current | none |
| Draft a PR body brief | Gas City formula | configured city, source bead with branch/evidence context | `gc sling <rig>/gc.run-operator pr-pipeline-briefed --formula --var source_bead=<bead> --var brief_slug=<slug>` | `tests/pr-pipeline-briefed/smoke_test.sh` | current | none |
| Verify work routing | local shell | shell | `bash tests/work-briefed-routing/smoke_test.sh` | `tests/work-briefed-routing/smoke_test.sh` | current | none |
| Audit documentation policy | Codex or Claude Code | mathcity checkout | `/check-documentation-policy` | acceptance check in this documentation refactor | current | none |

## Development And Tests

Run cheap local checks from the pack root:

```sh
python3 -m pytest \
  tests/stuck-bead-watch/test_stuck_bead_watch.py \
  tests/tail-end-detector/test_tail_end_detector.py

for t in tests/*/smoke_test.sh; do
  bash "$t"
done
```

Documentation must stay source-aligned. For feature, formula, skill, policy,
setup, or workflow changes, run `mathcity-dev.improve-documentation`, then
audit with `mathcity-dev.check-documentation-policy`.

## Policies

| Policy | Scope |
| --- | --- |
| [POLICY-POLICY.md](./POLICY-POLICY.md) | How policy domains and rule IDs work. |
| [POLICY-formulas.md](./POLICY-formulas.md) | Formula TOML rules and formula-creation constraints. |
| [POLICY-beads.md](./POLICY-beads.md) | Bead typing, research-bead lifecycle, and stale-bead handling. |
| [subdomains/dev/POLICY.md](./subdomains/dev/POLICY.md) | Pack portability, ownership boundaries, and development hygiene. |
| [subdomains/dev/POLICY-city.md](./subdomains/dev/POLICY-city.md) | Runtime city operations. |
| [subdomains/dev/POLICY-documentation.md](./subdomains/dev/POLICY-documentation.md) | Documentation quality, examples, setup, and navigation. |

## Subdomains

See [README-subdomains.md](./README-subdomains.md) for the complete table.

| Subdomain | Purpose |
| --- | --- |
| `brief-system` | Brief lifecycle, gates, and decision pipeline. |
| `computing` | Heavy computation and test/result workflows. |
| `dev` | Pack development, hygiene, policy, documentation, and city operations. |
| `latex` | LaTeX and notes-tier review. |
| `lmfdb` | LMFDB lookup and data pipeline workflows. |
| `magma` | Magma package policy and hygiene. |
| `proof-assist` | Proof assistant and mathematical search surfaces. |
