---
name: plan-an-lmfdb-webpage
description: Plan the full task breakdown and PERT chart for adding a new mathematical object type to the LMFDB website. Use this skill whenever the user wants to stand up LMFDB webpages for a new object type, create a Flask Blueprint for a new math object, plan LMFDB web integration, or asks "what needs to be done to add X to the LMFDB". Also use when the user says "plan an LMFDB webpage" or "LMFDB webpage plan for X". Assumes data pipeline (Magma types, make scripts, DB schema, db_load.py, db_migrate.py) is already done. Focuses entirely on the web layer: Blueprint, web data class, routes, templates, integration testing, and beta migration.
---

## Dependency check

```bash
CONF=""
for candidate in \
    "$(git rev-parse --show-toplevel 2>/dev/null)/lmfdb-pipeline.conf" \
    "magma/scripts/data-generation.conf"; do
  [ -f "$candidate" ] && { CONF="$candidate"; break; }
done
if [ -z "$CONF" ]; then
  echo "I'm sorry, I can't do that — no database pipeline conf found."
  echo "Run /configure-database (mathcity-lmfdb.configure-database) to create lmfdb-pipeline.conf at your project root."
  echo "(This conf holds your PostgreSQL and DATA_DIR settings needed to query the data pipeline.)"
  exit 1
fi
source "$CONF"
```

## What this skill does

Given a mathematical object type the user wants to add to LMFDB, this skill:

1. Identifies the closest analog module already in the LMFDB repo
2. Reads the existing DB schema to understand available data fields
3. Produces a fine-grained, agent-farmable task list (Tracks F–L)
4. Outputs a Mermaid PERT chart with dependencies and critical path

**Assumption:** The data pipeline is complete — the `lmfdb.*` PostgreSQL table for this object type already exists and is populated. The task here is purely web: Flask Blueprint → web data class → routes → templates → testing → beta.

**Context — what came before (not covered by this skill):**
The data generation pipeline (Tracks A–E in the full LMFDB development process) must already be done:
- **Track A** — Define/fix the serialization type (e.g., a Magma LMFDB type with ATTRS, or a Python/Sage data class)
- **Track B** — Make script to generate `DATA/` flat files from computed mathematical objects
- **Track C** — Schema documentation (currently split across `magma/schema.md` and `magma/python/schema_lmfdb.md`; these will eventually be merged into one)
- **Track D** — SQL schema (`db_schema_staging.sql`, `db_schema_lmfdb.sql`)
- **Track E** — Python pipeline (`db_load.py`, `db_migrate.py`, end-to-end test)

Note: data generation is not always in Magma. For example, isogeny classes of abelian varieties over finite fields are computed in Sage. The serialization language doesn't affect the web layer at all — by the time this skill runs, data is already in PostgreSQL.

---

## Step 1: Gather context from the user

Ask: "What mathematical object type are you adding, and what is the name of the PostgreSQL table it lives in (e.g., `clifford_modular_forms`)?"

Also ask (or infer from context):
- What URL prefix should the Blueprint use? (e.g., `/ModularForm/CliffordBianchi/`)
- Are there natural sub-objects that need their own pages? (e.g., a "space" grouping forms by level, vs. individual eigenforms)
- What are the key searchable fields?

If this is being run in the hecke project context, the user probably already has answers — extract from the conversation rather than asking redundantly.

---

## Step 2: Research the LMFDB repo

Read the LMFDB repo at your local clone of `https://github.com/LMFDB/lmfdb` (e.g. `<repos-root>/lmfdb/lmfdb/`) to find the closest analog module. Good analogs:

| Object type | Analog module |
|---|---|
| Modular forms over imaginary quadratic fields | `bianchi_modular_forms/` |
| Classical modular forms / newforms | `classical_modular_forms/` |
| Elliptic curves over Q | `elliptic_curves/` |
| Elliptic curves over number fields | `ecnf/` |
| Abelian varieties over finite fields | `abvar/fq/` |
| Number fields | `number_fields/` |
| L-functions | `lfunctions/` |

For the chosen analog, read:
- `<analog>/__init__.py` — how the Blueprint is defined and registered
- `<analog>/templates/` — list all template files and their purposes
- The main route file (e.g., `bianchi_modular_form.py`) — scan for all `@<blueprint>.route(...)` decorators
- The web data class (e.g., `web_BMF.py`) — what DB tables it queries and what properties it exposes

This tells you exactly what routes and templates you'll need to create.

---

## Step 3: Read the schema

Read the schema documentation to understand the columns available in the DB table for this object. Currently the schema lives in two files (`magma/schema.md` and `magma/python/schema_lmfdb.md`) that will eventually be merged — check both and treat them together as the single source of truth. The columns listed there become the properties of the web data class.

Also check recent git commits (`git log --oneline -20`) for context on what was just built.

---

## Step 4: Generate the task list

Produce a task list organized into these tracks. Every task should be self-contained enough to hand to an independent agent with a short briefing.

### Track F — Flask Blueprint Setup

> All web development work lives in the **LMFDB repository** (`https://github.com/LMFDB/lmfdb`), not the hecke repo. The hecke repo owns the data pipeline (Tracks A–E); lmfdb owns the web layer (Tracks F–L).

- **F1** Create `lmfdb/lmfdb/<module>/__init__.py`: define the Blueprint, set URL prefix, add body-class context processor
- **F2** Register the Blueprint import in `lmfdb/lmfdb/website.py`
- **F3** Register `db.<table_name>` in `lmfdb/lmfdb/lmfdb_database.py`

### Track G — Web Data Class
- **G1** Write `lmfdb/lmfdb/<module>/web_<NAME>.py`: `Web<NAME>` class with `by_label()`, all display properties drawn from the schema columns, breadcrumbs builder, properties sidebar builder, friends/associated objects builder

### Track H — Routes
Generate one task per route. Standard set:
- **H1** Index/browse route (`GET /<prefix>/`) — dispatches to search if query params present
- **H2** Detail route (`GET /<prefix>/<...>/<label>/`) — single object page
- **H3** Random route (`GET /<prefix>/random`)
- **H4** Raw data route (`GET /<prefix>/data/<label>`)
- **H5** Search function `<name>_search(info, query)` — parses query params, builds psycodict query

Add additional routes if the analog has them (e.g., a "space" grouping route, a dimension table route, a download route). One task per route.

### Track I — Templates
**One task per `.html` file.** Standard set:
- **I1** `<module>-index.html` — browse/search landing page: search form, paginated results table, quick-stats boxes; extends `homepage.html`
- **I2** `<module>-<detail>.html` — single object detail page: properties table, key data table (e.g., Hecke eigenvalues), associated objects panel, download section; extends `homepage.html`
- **I3** `<module>-stats.html` — statistics page: counts and distributions

Add additional templates if the analog has them (e.g., `<module>-space.html` for a grouping page, a dimension table template). Look at the analog's `templates/` directory to determine what's needed — each file in the analog gets a corresponding task.

For each template task, include in the description: which route renders it, what data the `Web<NAME>` object provides, and what the key display sections are.

### Track J — Integration Testing
- **J1** Load test data into the local LMFDB dev DB (confirm `lmfdb.<table>` is reachable from the Flask dev server)
- **J2** Start local dev server, verify the index/browse page renders and returns results
- **J3** Verify the detail page renders for a known label (correct data, no missing properties)
- **J4** Verify the search function returns correct results for a few queries
- **J5** Fix bugs found in J2–J4

### Track K — Beta Migration (code)
- **K1** Code cleanup: remove debug statements, add docstrings, run `codestyle.sh`
- **K2** Submit `<module>/` Blueprint as PR to the `lmfdb/lmfdb` GitHub repo
- **K3** Add `<module>` entry to LMFDB homepage index-boxes (`lmfdb/templates/index-boxes.html`)
- **K4** Write knowls in the LMFDB knowl database (one per key concept: the object itself, its level, its Hecke/eigenvalue data if applicable)
- **K5** Address code review feedback on K2
- **K6** Merge to LMFDB beta

### Track L — Beta Migration (data)
- **L1** Export `lmfdb.<table>` as LMFDB-format upload files (pipe-delimited `.txt`)
- **L2** Submit data upload to LMFDB (via their data upload/PR process)
- **L3** Verify data appears correctly in LMFDB beta DB

---

## Step 5: Output the PERT chart

Output a Mermaid flowchart showing all task dependencies. Standard dependency rules:

- F1 → F2, F3
- F3 → G1 (table must be registered before `Web<NAME>` can use `db`)
- G1 → all H tasks (routes need the web data class)
- Each H route + its corresponding I template → its J test task
- All J tasks → J5 (bug fix)
- J5 → K1 → K2 → K3, K4, K5 → K6
- (Separately) data pipeline complete → L1 → L2 → L3
- K6 + L3 → DONE

Also note the **critical path** in prose: F1 → F3 → G1 → H(detail) + I(detail) → J(detail test) → J5 → K1 → K2 → K5 → K6. Templates (Track I) and routes (Track H) are independent of each other and can be parallelized.

**Parallelization note:** Always call out that Tracks F/G/H/I can all proceed concurrently — they have no dependency on the data pipeline being loaded into the dev DB (that's only needed for Track J). An agent can write templates while another writes the web data class.

---

## Output format

Deliver in this order:
1. One-paragraph summary of the object type, its analog module, and how many routes/templates are needed
2. Full task list (Tracks F–L), with each task on its own line as `**Fx** description`
3. Mermaid PERT chart (```mermaid flowchart LR ... ```)
4. Critical path called out in one sentence
5. Parallelization opportunities called out in one sentence
