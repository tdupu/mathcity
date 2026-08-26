# Mathcity Repository Layout

Parent: [README.md](./README.md)

A map of how this repository is organized: what lives at the root, what each
top-level directory holds, and the sub-pack pattern the `subdomains/` tree
follows. This document is **descriptive** — it records the structure as it is,
so contributors know where things go and reviewers can spot a file that has
landed in the wrong place. It does not define enforceable rules; the pack's
conventions live in the `POLICY-*.md` documents (see
[Governance](#governance-documents) below) and are governed by
[POLICY-POLICY.md](./POLICY-POLICY.md).

Mathcity is a composable [Gas City](https://github.com/gastownhall/gascity)
pack. The top level is the `mathcity` pack itself; `subdomains/` holds the
mathematical sub-packs it composes.

## Top-level tree

```text
mathcity/
├── pack.toml              # pack manifest (name, version, imports, providers)
├── packs.lock             # resolved import lockfile
├── .gitignore             # never-track list (see Never tracked, below)
│
├── README.md              # entry point + Documentation Map
├── ABOUT.md               # what mathcity is, for newcomers
├── ONBOARDING.md          # getting started as a contributor
├── SETUP.md               # installation / activation
├── GLOSSARY.md            # shared vocabulary
├── README-*.md            # topic guides (beads, dolt, formulas, skills,
│                          #   mayor, clerk, subdomains, development)
├── POLICY-*.md            # pack-root policy documents (see Governance)
│
├── agents/                # agent definitions (agent.toml per agent)
├── skills/                # pack-level skills (one directory per skill)
├── formulas/              # TOML workflow templates (plan→implement→review→brief)
├── orders/                # order definitions dispatched by the city
├── gates/                 # gate policy registry (*.toml)
├── template-fragments/    # reusable doc/prompt fragments included by skills
├── tests/                 # smoke tests (one directory per behavior)
├── docs/                  # reference docs, plans/specs, ADRs, filters,
│                          #   rule-prefix registry
├── assets/                # scripts, images, and other static assets
├── bin/                   # executable entry points (thin shims, e.g. mctl)
├── scripts/               # repo-level maintenance scripts
├── subdomains/            # mathematical sub-packs (see Subdomain pack model)
└── .github/               # GitHub issue templates and labels
```

## Directory reference

| Path | Holds | Notes |
| --- | --- | --- |
| `agents/` | One directory per agent, each with an `agent.toml` | e.g. `brief-operator/`, `codex-worker/`. Pool sizing and wake mode live here. |
| `skills/` | One directory per skill, each with a `SKILL.md` | The pack-level skill store. Subdomain-specific skills live under their subdomain instead. |
| `formulas/` | `*.formula.toml` workflow templates | Compose skills and agents into structured sequences. |
| `orders/` | Order definitions | Units of dispatchable work the city routes to agents. |
| `gates/` | `*.toml` gate definitions | The gate policy registry (e.g. `test-execution.toml`, `test-evidence.toml`, `stale-claim.toml`). Gate entries cite rule IDs per `POLICY-POLICY.md` PP4.x. |
| `template-fragments/` | Reusable Markdown fragments | Canonical blocks included by multiple skills (e.g. `dolt-preflight.md`, `escalation-protocol.md`). |
| `tests/` | One directory per behavior, each with a `smoke_test.sh` | Fast, self-contained checks; keep green before any push. |
| `docs/` | Reference material and planning artifacts | Active plans and specs live under `docs/superpowers/`; ADRs live under `docs/adr/`; repair filters live under `docs/filters/`; `docs/rule-prefix-registry.md` is authoritative for rule prefixes. |
| `assets/` | Static assets | Scripts, images, and other non-source support files. |
| `bin/` | Executable entry points | Thin shims callers invoke by path (e.g. `bin/mctl` over `assets/scripts/mctl.py`). Logic belongs in `assets/`, not here. |
| `scripts/` | Repo maintenance scripts | e.g. `dolt-remotes-sync.sh`. |
| `.github/` | Issue templates + `LABELS.md` | GitHub-side scaffolding for the mathcity-owned issue workflow. |

## Plans and specs

Use the Superpowers tree as the single intake point for new planning artifacts:

| Path | Holds | Notes |
| --- | --- | --- |
| `docs/superpowers/plans/` | Exploratory plans, implementation plans, PERTs, handoffs, triage packets, evidence bundles | This is the default home for new planning work, including cross-cutting formula, MCP, skill, dashboard, and workflow reworks. Prefer date-prefixed filenames. |
| `docs/superpowers/specs/` | Approved or stabilized design specs | Use this after an exploratory plan has converged into a design that should guide implementation. If a spec is later moved to a subdomain as durable reference material, leave a pointer at the original Superpowers path. |
| `docs/superpowers/plans/<topic>/` | Large plan clusters with prototypes or multiple handoff files | Use a topic subdirectory only when one flat file would be hard to navigate. Examples include dashboard design handoffs. |

Do not add new planning trees under `subdomains/dev/docs/plans/` or directly
under a subdomain `docs/` directory. Existing plan-looking files in those
locations are historical placement; when they are touched, either leave them as
history or replace them with pointers to the canonical Superpowers location.
Subdomain `docs/` directories remain the right place for durable reference
documentation owned by that subdomain, not for new exploratory planning packets.

## Subdomain pack model

Each directory under `subdomains/` is a self-contained mathematical sub-pack
with its own manifest. See
[docs/adr/0002-mathcity-subdomain-pack-model.md](./docs/adr/0002-mathcity-subdomain-pack-model.md)
for the design rationale.

Current subdomains: `brief-system`, `computing`, `dev`, `latex`, `lmfdb`,
`magma`, `proof-assist`.

A subdomain follows the same internal shape as the root pack, scoped to its
concern:

```text
subdomains/<name>/
├── pack.toml       # sub-pack manifest
├── README.md       # what this subdomain is for
├── POLICY.md       # subdomain policy (optional; e.g. dev, brief-system)
├── skills/         # subdomain-specific skills
├── orders/         # subdomain orders            (when present)
├── docs/           # subdomain docs              (when present)
├── scripts/        # subdomain scripts           (when present)
└── assets/ | mcp/  # subdomain-specific support  (when present)
```

Not every subdomain has every directory — only `skills/`, `README.md`, and
`pack.toml` are universal. The `dev` subdomain is the fullest example (it
carries `orders/`, `docs/`, `scripts/`, and multiple policy files); `magma`
and `computing` are minimal (`skills/` + `README.md` + `POLICY.md`).

## Governance documents

Placement, naming, and clean-tree conventions are defined — and enforced — by
the policy documents, not by this map. Pack-root policies use the
`POLICY-<domain>.md` name; subdomain policies are a `POLICY.md` inside the
subdomain directory (per `POLICY-POLICY.md` PP5.4).

| Document | Governs |
| --- | --- |
| [POLICY-POLICY.md](./POLICY-POLICY.md) | What a policy document is; how rules are structured, numbered, and amended. Wins on conflict. |
| [POLICY-skills.md](./POLICY-skills.md) | Skill placement and structure. |
| [POLICY-formulas.md](./POLICY-formulas.md) | Formula authoring and lifecycle. |
| [POLICY-beads.md](./POLICY-beads.md) | Bead conventions and the state/file split. |
| [subdomains/dev/POLICY.md](./subdomains/dev/POLICY.md) | Pack portability and subdomain boundaries. |

The authoritative index of rule-ID prefixes and their home paths is
[docs/rule-prefix-registry.md](./docs/rule-prefix-registry.md).

## Manifest and lockfiles

- `pack.toml` — the pack manifest: name, version, `[imports.*]` (gascity core
  and superpowers), and providers.
- `packs.lock` — the resolved lockfile for those imports.

## Never tracked

Per `.gitignore`, the following are deliberately kept out of version control —
they are local state, not source:

- `.beads/`, `.beads.gate.lock`, `*.gate.lock*`, `.beads/proxieddb/` — bead
  workflow and lock state (bead data syncs through the Dolt remote, not the
  code repo).
- `.dolt/`, `*.db`, `.beads-credential-key` — Dolt working state and
  credentials.
- `__pycache__/`, `*.py[cod]`, `.pytest_cache/` — Python build/cache artifacts.
