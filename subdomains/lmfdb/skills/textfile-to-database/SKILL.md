---
name: textfile-to-database
description: Load DATA/ flat files into the local PostgreSQL database (clifford_bianchi_local). Use whenever the user says "load data into the database", "put DATA/ in postgres", "populate staging", "load local/upf subgroups", or any time a DATA/ source needs to be ingested into postgres.
---

## Dependency check

```bash
# Discover conf: project root first, hecke fallback
CONF=""
for candidate in \
    "$(git rev-parse --show-toplevel 2>/dev/null)/lmfdb-pipeline.conf" \
    "magma/scripts/data-generation.conf"; do
  [ -f "$candidate" ] && { CONF="$candidate"; break; }
done
if [ -z "$CONF" ]; then
  echo "I'm sorry, I can't do that — no database pipeline conf found."
  echo "Run /configure-database (mathcity-lmfdb.configure-database) to create lmfdb-pipeline.conf at your project root."
  echo "(This conf holds your PostgreSQL and DATA_DIR settings for the LMFDB pipeline.)"
  exit 1
fi
source "$CONF"
```

## New: incremental single-object loads via `Add` (package-database)

For writing individual objects or small batches to the database during live computation
(without the full staging pipeline):

```magma
Z := Integers(); Q := Rationals();
AttachSpec("hecke.spec");
SetLMFDBRootFolder(".");

db := OpenDB("clifford_bianchi_local");

// Load objects from DATA/ and insert:
objs := load_textfiles("LMFDBPSL2GrpCliffSub");
records := [Dictionary(X) : X in objs];
Add(db, "clifford_subgroups", records);  // errors if any label already exists

// Or use AddLMFDB for the typed interface:
AddLMFDB(db, "LMFDBPSL2GrpCliffSub", objs);

// Export entire DB table back to DATA/ (reverse direction):
PrintToTextfile(db, "clifford_subgroups");
```

`Add` / `AddLMFDB` write directly to `lmfdb.*` tables (no staging, no `db_migrate.py`).
`overwrite := false` (default) errors if any label already exists.
`overwrite := true` upserts.

Use the `db_load.py` + `db_migrate.py` pipeline below for **bulk initial loads** — when
ingesting all of `DATA/` at once, with ledger tracking and UPF provenance.

---

# textfile-to-database

**Purpose:** Ingest Magma-serialized flat files from `DATA/` into the local PostgreSQL staging tables, then optionally promote to the `lmfdb` schema. Implemented in `magma/python/db_load.py` and `magma/python/db_migrate.py`.

## Prerequisites

```bash
pg_isready                                          # PostgreSQL running?
python3 -c "import psycopg2; print('ok')"          # psycopg2 installed?
```

If psycopg2 is missing: `pip3 install --user --break-system-packages psycopg2-binary`

## Step 1 — Create database and apply schemas (first time only)

```bash
createdb clifford_bianchi_local

cd magma/python
psql clifford_bianchi_local -f db_schema_staging.sql
psql clifford_bianchi_local -f db_schema_lmfdb.sql
```

Verify:
```sql
\dn                   -- should list: lmfdb, migration, staging
\dt staging.*         -- orders_src, sl2_src, gamma0_src, subgroups_local, subgroups_upf
\dt migration.*       -- ledger
\dt lmfdb.*           -- clifford_orders, clifford_sl2, clifford_gamma0, clifford_subgroups
```

## Step 2 — Load DATA/ files into staging

```bash
cd magma/python
python3 db_load.py --data-root ../DATA

# load only one type:
python3 db_load.py --data-root ../DATA --only orders
python3 db_load.py --data-root ../DATA --only sl2
python3 db_load.py --data-root ../DATA --only gamma0
python3 db_load.py --data-root ../DATA --only subgroups

# load UPF server data alongside local:
python3 db_load.py --data-root ../DATA --upf-root ../data-upf
```

Verify row counts:
```sql
SELECT COUNT(*) FROM staging.orders_src;
SELECT COUNT(*) FROM staging.sl2_src;
SELECT COUNT(*) FROM staging.gamma0_src;
SELECT COUNT(*) FROM staging.subgroups_local;
SELECT COUNT(*) FROM staging.subgroups_upf;

-- jsonb type check (catches SaveJsonb double-quoting bug):
SELECT COUNT(*) FROM staging.orders_src WHERE jsonb_typeof(basis) != 'array';
-- should be 0
```

## Step 3 — Populate the migration ledger

```bash
python3 db_migrate.py --action populate_ledger
```

Verify:
```sql
SELECT object_type, source, COUNT(*), array_agg(DISTINCT status)
FROM migration.ledger
GROUP BY object_type, source
ORDER BY object_type;
-- all status values should be 'pending'
```

## Step 4 — Promote to lmfdb schema

```bash
python3 db_migrate.py --action promote_to_lmfdb
```

Verify FK integrity and counts:
```sql
SELECT COUNT(*) FROM lmfdb.clifford_orders;
SELECT COUNT(*) FROM lmfdb.clifford_sl2;
SELECT COUNT(*) FROM lmfdb.clifford_gamma0;
SELECT COUNT(*) FROM lmfdb.clifford_subgroups;

-- FK check: should all be 0
SELECT COUNT(*) FROM lmfdb.clifford_sl2
  WHERE order_label NOT IN (SELECT label FROM lmfdb.clifford_orders);
SELECT COUNT(*) FROM lmfdb.clifford_subgroups
  WHERE order_label NOT IN (SELECT label FROM lmfdb.clifford_orders);
```

## Idempotency

All steps are safe to re-run:
- `db_load.py` appends to staging (duplicate rows in staging are OK; promotion deduplicates)
- `populate_ledger` skips labels already in the ledger
- `promote_to_lmfdb` uses `ON CONFLICT (label) DO UPDATE`

## Known issue: jsonb double-quoting

`SaveJsonb` in Magma wraps pre-serialized JSON strings in an extra layer of `"..."`.
`db_load.py::_preprocess_field` strips this before COPY. If `jsonb_typeof(basis) = 'string'`
(not `'array'`), the fix is not working — check `_preprocess_field` in `db_load.py`.

## Stubs (not yet available)

```bash
python3 db_migrate.py --action relabel_orders    # raises NotImplementedError (issue #164)
python3 db_migrate.py --action relabel_subgroups # raises NotImplementedError
python3 db_migrate.py --action enrich_subgroups  # raises NotImplementedError
```
