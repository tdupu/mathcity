---
name: database-to-magma
description: Restore a native Magma object (CliffOrd, GrpPSL2Cliff, etc.) directly from the PostgreSQL lmfdb schema. Use whenever the user says "restore magma object from database", "database to magma", "load native object from db", or "db to mag".
---

# database-to-magma

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

**Purpose:** Full pipeline from the lmfdb PostgreSQL schema to a live Magma object:

```
db query → pipe-delimited string → LMFDBXxx object → native Magma object
```

This replaces the `data-to-mag` pipeline (which reads flat files) once the database is the authoritative store.

**Dependency:** `/database-to-lmfdb-object` must work correctly first — the round-trip from
DATA/ → postgres → pipe string → Magma object must be verified before relying on this skill.

## Step 1 — Get the pipe-delimited string from the database

Use `/database-to-lmfdb-object` to query the lmfdb schema and emit the pipe-delimited string.

```bash
# Example: restore order with label 2.m1.m4.4.4.1.16.4.1.1
psql clifford_bianchi_local -t -A -F '|' -c "
    SELECT basis, clifford_algebra, dimension, discriminant,
           is_maximal, is_norm_euclidean, is_star_invariant, label, timing
    FROM lmfdb.clifford_orders
    WHERE label = '2.m1.m4.4.4.1.16.4.1.1';
" > /tmp/order_string.txt
```

## Step 2 — Feed the string to `/string-to-lmfdb-object`

```magma
AttachSpec("hecke.spec");
SetLMFDBRootFolder(".");

line := Read("/tmp/order_string.txt");
line := &cat[c : c in Split(line, "\n") | #c gt 0];   // strip trailing newline

lmfdb_ord := load_lmfdb_clifford_order(line);          // → LMFDBCliffOrd
```

Or use the `/string-to-lmfdb-object` skill directly with the string.

## Step 3 — Feed the LMFDB object to `/lmfdb-object-to-magma`

```magma
O := clifford_order(lmfdb_ord);                        // → CliffOrd
```

See `/lmfdb-object-to-magma` for the full intrinsic reference per object type.

## Full one-liner (Python → temp file → Magma)

```python
# Python side
import subprocess, db_config

label = "2.m1.m4.4.4.1.16.4.1.1"
conn = db_config.get_connection()
with conn.cursor() as cur:
    cur.execute("""
        SELECT basis, clifford_algebra, dimension, discriminant,
               is_maximal, is_norm_euclidean, is_star_invariant, label, timing
        FROM lmfdb.clifford_orders WHERE label = %s
    """, (label,))
    row = cur.fetchone()
conn.close()
line = "|".join("\\N" if v is None else str(v) for v in row)
with open("/tmp/db_order.txt", "w") as f:
    f.write(line + "\n")
```

```magma
// Magma side
AttachSpec("hecke.spec");
SetLMFDBRootFolder(".");
line := [H : H in Split(Read("/tmp/db_order.txt"), "\n") | #H gt 0][1];
lmfdb_ord := load_lmfdb_clifford_order(line);
O := clifford_order(lmfdb_ord);
```

## Object-type reference

| Object type       | lmfdb table              | LMFDB wrapper type         | Magma intrinsic          |
|-------------------|--------------------------|----------------------------|--------------------------|
| Order             | `clifford_orders`        | `LMFDBCliffOrd`            | `clifford_order(X)`      |
| SL₂(O) group      | `clifford_sl2`           | `LMFDBGrpSL2Cliff`         | `clifford_bianchi_group(X)` |
| Gamma0 subgroup   | `clifford_gamma0`        | `LMFDBGrpSL2CliffGamma0`   | (see `/lmfdb-object-to-magma`)  |
| Low-index subgroup| `clifford_subgroups`     | `LMFDBPSL2GrpCliffSub`     | (see `/lmfdb-object-to-magma`)  |
