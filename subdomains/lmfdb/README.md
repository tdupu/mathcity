# mathcity-lmfdb

Parent: [../../README-subdomains.md](../../README-subdomains.md)

Query the LMFDB, cross-check computed mathematical data, and run the full
contribute-to-LMFDB pipeline: serialize Magma objects to flat files,
load them into a PostgreSQL `lmfdb` schema, and plan new object types for
the website.

**What is the LMFDB?** The [LMFDB](https://www.lmfdb.org/) — the database
of L-functions, Modular Forms, and related objects — is a large
collaborative database of mathematical objects (elliptic curves, number
fields, modular and Bianchi modular forms, L-functions, genus 2 curves,
groups, …) and the connections between them, organized around the
Langlands program. Each object has a stable label and a webpage; the data
is computed, verified, and cross-referenced by the community. This
subdomain's skills query it, cross-check our computed data against it, and
contribute new object types to it.

Import alias convention (ADR 0002): skills materialize as
`mathcity-lmfdb.<skill>`.

## Policy

[POLICY.md](./POLICY.md) (LM-rules) governs this subdomain: **LM1** what
makes a good LMFDB label (deterministic, machine-safe, structure-over-hash,
parent-prefix namespacing, migration-not-edit stability), **LM2** what makes
a good experiment (`is-good-experiment` gate, reproducibility artifacts,
results enter the DB only through the conversion lattice), **LM3** server
usage (reads/dry-runs free; writes gated, tagged, and authorized by decision
bead before execution; idempotency preconditions; pull-before-push), **LM4**
type creation (justification, naming, full seven-file wiring, label-first,
webpage decision). Enforced by `check-lmfdb-hygiene`; new types are created
through `new-lmfdb-type-policy`.

## Configuration — no private values in the pack

This pack uses **two** project-local, gitignored confs placed at your project
root. Private values (hostnames, users, SSH keys, schema names) never enter
pack content or git.

| Conf file | Contains | Template |
| --- | --- | --- |
| `lmfdb-server.conf` | SSH/compute-server connection (REMOTE_HOST, REMOTE_USER, etc.) | [`assets/lmfdb-server.conf.example`](./assets/lmfdb-server.conf.example) |
| `lmfdb-pipeline.conf` | Database and pipeline config (PGDATABASE, PGSCHEMA, DATA_DIR, SCHEMA_MD) | [`assets/lmfdb-pipeline.conf.example`](./assets/lmfdb-pipeline.conf.example) |

Server skills discover `lmfdb-server.conf` at the project root first, then
fall back to `magma/scripts/data-generation.conf` (hecke's existing convention)
so hecke works without any migration.

Run `mathcity-lmfdb.configure-server` and `mathcity-lmfdb.configure-database`
(or `mathcity-lmfdb.setup-lmfdb-pipeline` to run both) to create these files
interactively on a fresh clone.

**Graceful errors on missing confs (P1.14):** All conf-driven skills now probe for their
conf file before taking any action. If `lmfdb-server.conf` is absent, server skills
(`push-to-server`, `pull-data-from-server`, `push-data-to-server`) stop immediately and
direct you to run `/configure-server`. If `lmfdb-pipeline.conf` is absent, database and
conversion-lattice skills (`database-to-magma`, `textfile-to-database`,
`lmfdb-object-to-database`, `database-to-lmfdb-object`, `database-to-textfile`,
`database-update`) stop immediately and direct you to run `/configure-database`. No skill
will produce a cryptic OS error from a missing conf.

## Skills

### Setup (run once per project)

| Skill | Purpose |
| --- | --- |
| `configure-server` | Interactively create `lmfdb-server.conf` at the project root (SSH/compute-server values) |
| `configure-database` | Interactively create `lmfdb-pipeline.conf` at the project root (database/pipeline values) |
| `setup-lmfdb-pipeline` | Meta-setup: runs `configure-database` then `configure-server` in sequence |

### Query & cross-check

| Skill | Purpose |
| --- | --- |
| `search-lmfdb` | Query the LMFDB via its MCP server (`mcp__lmfdb__*`); cross-check computed data, verify labels and eigenvalues |

### Conversion lattice (Magma ⇄ string ⇄ textfile ⇄ LMFDB object ⇄ database)

The four representations of a mathematical object — native Magma object,
pipe-delimited LMFDB string, `DATA/` flat file, PostgreSQL row — and the
edges between them:

| Skill | Purpose |
| --- | --- |
| `magma-to-textfile` | Serialize a raw Magma object all the way to a `DATA/` flat file in one pipeline |
| `textfile-to-magma` | Reconstruct the native Magma object from a `DATA/` flat file |
| `magma-to-lmfdb-object` | Wrap a raw Magma object as an LMFDB wrapper object |
| `textfile-to-string` / `string-to-textfile` | Read/write raw pipe-delimited LMFDB strings on disk |
| `textfile-to-lmfdb-object` / `lmfdb-object-to-textfile` | Flat file ⇄ LMFDB wrapper object |
| `string-to-lmfdb-object` / `lmfdb-object-to-string` | In-memory string ⇄ LMFDB wrapper object |
| `database-to-magma` | Restore a native Magma object directly from the PostgreSQL schema |
| `lmfdb-object-to-database` / `database-to-lmfdb-object` | LMFDB wrapper object ⇄ PostgreSQL row (insert/update and lookup) |
| `textfile-to-database` / `database-to-textfile` | Bulk-load flat files into the schema and dump rows back out |
| `database-update` | Refresh existing database rows after recomputation |

### Policy & hygiene

| Skill | Purpose |
| --- | --- |
| `check-lmfdb-hygiene` | Audit an LMFDB-type bead/diff/experiment/type against POLICY.md (labels valid, experiment reproducible, server ops authorized, type fully wired); read-only, brief-cycle verdict |
| `new-lmfdb-type-policy` | Policy-gated type creation: justification gate, label scheme designed and human-approved BEFORE code, then drives `create-lmfdb-type` + `update-schema`, ends with a `check-lmfdb-hygiene` audit |

### Contributing new object types

| Skill | Purpose |
| --- | --- |
| `create-lmfdb-type` | Scaffold a new LMFDB object type (wrapper, serialization, schema) |
| `update-schema` | Propagate a schema change (add/remove/modify columns or tables) across ALL affected files |
| `plan-an-lmfdb-webpage` | Task breakdown + PERT chart for adding a new object type to the LMFDB website |

### Remote compute server (conf-driven, reads `lmfdb-server.conf`)

| Skill | Purpose |
| --- | --- |
| `push-to-server` | SSH to the compute server and `git pull` the latest branch |
| `pull-data-from-server` | Fetch computed `DATA/` results back from the compute server |
| `push-data-to-server` | Ship local `DATA/` files up to the compute server |

The `mathcity.lmfdb.querier` agent translates math questions into LMFDB
queries and cross-checks computed data against the database.

Note: this subdomain is the strongest candidate to eventually split into its
own pack, given its external MCP dependency and self-contained query surface
(ADR 0002). UPF-dispatch skills (`pull-data-from-upf`, `push-data-to-upf`,
`restart-upf-computations`, `dispatch-*`) remain in hecke — they are bound
to its compute-dispatch infrastructure, not the LMFDB pipeline.
