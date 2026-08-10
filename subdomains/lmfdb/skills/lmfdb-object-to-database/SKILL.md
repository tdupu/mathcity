---
name: lmfdb-object-to-database
description: Insert or update an LMFDB wrapper object directly into the lmfdb PostgreSQL schema, bypassing the DATA/ flat-file step. Use whenever the user has a live LMFDBXxx object and wants to persist it to the database without writing a file first, or when asked to "save this to the database" after computing something.
---

# lmfdb-object-to-database

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

```magma
Z := Integers(); Q := Rationals();
AttachSpec("hecke.spec");
SetLMFDBRootFolder(".");

db := OpenDB("clifford_bianchi_local");

// Single object insert (errors if label already exists):
AddLMFDB(db, "LMFDBCliffOrd", [X]);

// Upsert (overwrite existing row):
AddLMFDB(db, "LMFDBCliffOrd", [X] : overwrite := true);

// Batch insert:
AddLMFDB(db, "LMFDBPSL2GrpCliffSub", subs);

// Generic low-level insert (Assoc-level):
Add(db, "clifford_orders", [Dictionary(X)] : overwrite := true);
```

`AddLMFDB` checks that each object has a non-empty `label` attribute before inserting. With `overwrite := false` (default), the INSERT will error if any label already exists in the table — this prevents accidental data corruption. Use `overwrite := true` to replace existing rows.

**Typename → table mapping:**
| typename | table |
|---|---|
| `LMFDBCliffOrd` | `clifford_orders` |
| `LMFDBGrpSL2Cliff` | `clifford_sl2` |
| `LMFDBGrpSL2CliffGamma0` | `clifford_gamma0` |
| `LMFDBPSL2GrpCliffSub` | `clifford_subgroups` |

## Legacy approach (pre-package-textfiles / pre-package-database)

**Purpose:** Serialize an LMFDB wrapper object to a pipe-delimited string, then INSERT (or
UPDATE on conflict) directly into the appropriate `lmfdb.*` table. Shortcut for
`/lmfdb-object-to-textfile` + `/textfile-to-database` when you don't need the DATA/ file.

### Step 1 — Serialize to pipe string in Magma

```magma
line := SaveLMFDBObject(X);   // works for any LMFDBXxx type
```

Or use the `*_ATTRS`-ordered manual serializer:
```magma
line := &cat[SaveAttr(attr, X``attr, X) * "|" : attr in LMFDBCliffOrd_ATTRS];
line := line[1..#line-1];  // strip trailing pipe
```

### Step 2 — Write the pipe string to a temp file

```magma
print_file("/tmp/lmfdb_obj.txt", line: overwrite := true);
```

### Step 3 — Load into the database via Python

Use `db_load.py` pointed at a single-file temp directory, or use the Python helper below.

**Option A — db_load.py (recommended for batches):**
```bash
mkdir -p /tmp/lmfdb_insert/orders
cp /tmp/lmfdb_obj.txt /tmp/lmfdb_insert/orders/2.1
cd magma/python
python3 db_load.py --data-root /tmp/lmfdb_insert --only orders
python3 db_migrate.py --action populate_ledger
python3 db_migrate.py --action promote_to_lmfdb
```

**Option B — direct psycopg2 (for single objects):**

Write a small Python snippet using the pipe-delimited string and psycopg2's COPY:

```python
import io, db_config
from db_load import ORDERS_ATTRS, _staging_cols, _preprocess_field

def insert_lmfdb_object(pipe_line, table, attrs, source="manual"):
    conn = db_config.get_connection()
    cols = _staging_cols(attrs)
    fields = pipe_line.rstrip("\n").split("|")
    proc = [_preprocess_field(col, f) for col, f in zip(attrs, fields)]
    proc += [source, "manual"]          # source, source_path
    line = "|".join(proc) + "\n"
    buf = io.StringIO(line); buf.seek(0)
    col_list = ", ".join(cols)
    with conn.cursor() as cur:
        cur.copy_expert(
            f"COPY {table} ({col_list}) FROM STDIN "
            f"WITH (FORMAT TEXT, DELIMITER '|', NULL '\\N')",
            buf,
        )
    conn.commit(); conn.close()

# Example: insert a single order
insert_lmfdb_object(line, "staging.orders_src", ORDERS_ATTRS)
```

### Step 4 — Promote to lmfdb schema

```bash
cd magma/python
python3 db_migrate.py --action populate_ledger
python3 db_migrate.py --action promote_to_lmfdb
```

`promote_to_lmfdb` uses `ON CONFLICT (label) DO UPDATE`, so re-inserting an already-stored
object updates its fields in place. No duplicate entries.

### Column order reference

The SELECT / INSERT must use the exact `*_ATTRS` alphabetical order. The critical aliasing:
- `order_label` in SQL ↔ `order` in Magma ATTRS (SQL reserved word)
- Staging column is `order_label_old`; lmfdb column is `order_label`

### When to use this vs. lmfdb-object-to-textfile

| Use `/lmfdb-object-to-database` | Use `/lmfdb-object-to-textfile` |
|----------------------------------|----------------------------------|
| One-off updates, no file needed  | Archiving computed data to DATA/ |
| After `/database-update`         | After a make-*.mag script        |
| Fast iteration during dev        | Batch generation, reproducibility|

### Next step

Verify with:
```sql
SELECT label, dimension, discriminant FROM lmfdb.clifford_orders WHERE label = '<new_label>';
```

## When to use legacy vs. new

Use `AddLMFDB` (new) for any insert or upsert that can be performed within a single Magma session — it skips the temp-file round-trip, the Python staging pipeline, and the `db_migrate.py` promotion step entirely. Fall back to the legacy approach only when working with a batch large enough to warrant `db_load.py`'s bulk COPY performance, when a staging-to-lmfdb promotion step is already part of an established pipeline, or when `AddLMFDB` is not yet available in the attached package version.
