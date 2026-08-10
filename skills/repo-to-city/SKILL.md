---
name: repo-to-city
description: Reference skill mapping repository names to their city rig (<city-root>/<name>) and working copy (<repos-root>/<name>). Use when you need to know where a repo lives in the city, its beads prefix, or whether it is registered as a gc rig. Trigger phrases: "which rig", "where is the rig for", "is X a rig", "what prefix does X use", "repo to city mapping", "add a new rig".
---

# repo-to-city

Every repository tracked by Gas City has **two checkouts** and a **beads database** in each:

| Location | Purpose |
|---|---|
| `<city-root>/<repo-name>` | City-managed rig — gc agents (mayor, polecats, refinery) work here |
| `<repos-root>/<repo-name>` | Outside-agent working copy — clerk and the human adjudicator's direct commands |

Both checkouts share the same git remote (`git@github.com:<github-owner>/<repo-name>.git`) and
the same Dolt remote (`git+ssh://git@github.com/./<github-owner>/<repo-name>-dolt.git`).
Bead changes sync via `bd dolt push/pull`.

## Check if a rig is registered

```bash
( cd <city-root> && gc rig list )
```

Or inspect `<city-root>/rigs.json` directly.

## Known repo ↔ rig mappings

| Rig name | GitHub repo | Beads prefix | Status |
|---|---|---|---|
| agent_skills | <github-owner>/agent-skills | as | active |
| cliff-part2 | <github-owner>/cliff-part2 | cp2 | active |
| differential_valuations | <github-owner>/differential-valuations | dv | active |
| gascity | <github-owner>/gascity (fork of gastownhall) | gs | active |
| gascity-packs | <github-owner>/gascity-packs (fork of gastownhall) | gsp | active |
| hecke | <github-owner>/hecke | he | active |
| homog | <github-owner>/homog | ho | active |
| jacobi | <github-owner>/jacobi | ja | active |
| lmfdb | <github-owner>/lmfdb | lm | active |
| magma_clifford_algebras | <github-owner>/magma-clifford-algebras | mca | active |
| magma_diff_alg | <github-owner>/magma-diff-alg | mda | active |
| <github-owner>_github_io | <github-owner>/<github-owner>.github.io | tgi | active |
| diff_alg_public | <github-owner>/diff-alg-public | da_pub | suspended |
| diff_alg_problems | <github-owner>/diff-alg-problems | da_prob | suspended |
| dupuy_cv | <github-owner>/dupuy-cv | dc | suspended |

## Adding a new rig

See `/dolt-init` for the Dolt setup. The full sequence for a brand-new rig:

```bash
REPO=<repo-name>
PREFIX=<2-4 letter prefix>

# 1. Clone into the city (if not already present)
git clone git@github.com:<github-owner>/${REPO}.git <city-root>/${REPO}

# 2. Register with gc (creates city.toml entry + installs hooks)
cd <city-root> && gc rig add <city-root>/${REPO} --name ${REPO} --prefix ${PREFIX}

# 3. Init beads + dolt remote in BOTH checkouts (see /dolt-init)
```

Update this table whenever a new rig is added.
