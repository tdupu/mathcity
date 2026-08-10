---
name: database-to-lmfdb-object
description: Restore an LMFDB wrapper object from PostgreSQL instead of a flat file. Use whenever the user says "restore from database", "load from postgres", "get [order/sl2/gamma0/subgroup] from db", or wants to reconstruct a Magma LMFDB wrapper object from the lmfdb schema rather than from DATA/ files.
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

## New: uniform `LookUpLMFDB` / `SearchLMFDB` (package-database)

```magma
Z := Integers(); Q := Rationals();
AttachSpec("hecke.spec");
SetLMFDBRootFolder(".");

db := OpenDB("clifford_bianchi_local");

// Lookup by label — returns typed LMFDB object:
X := LookUpLMFDB(db, "LMFDBCliffOrd",           "2.1.m4.1.2.1.1.2.1.1");
X := LookUpLMFDB(db, "LMFDBGrpSL2Cliff",        "2.1.m4.1.2.1.1.2.1.1");
X := LookUpLMFDB(db, "LMFDBGrpSL2CliffGamma0",  "2.1.m4.1.2.1.1.2.1.1.4w74vb");
X := LookUpLMFDB(db, "LMFDBPSL2GrpCliffSub",    "2.1.m4.1.2.1.1.2.1.1.1");

// Search with filter — returns sequence of typed objects:
q := AssociativeArray(); q["order_label"] := "2.1.m4.1.2.1.1.2.1.1";
subs := SearchLMFDB(db, "LMFDBPSL2GrpCliffSub", q);

// Fetch one field subset:
X := LookUpLMFDB(db, "LMFDBCliffOrd", label : output_attr := ["label", "timing"]);
```

No need to know column ordering, table names, or run a `psql` command. The `DB0` layer handles schema qualification and JSONL parsing internally.

Use the legacy `psql` approach below only when debugging schema issues or when `package-database.mag` is not available on the current branch.

---

# database-to-lmfdb-object

**Purpose:** Query `lmfdb.clifford_*` tables for a given label, emit a pipe-delimited string in
the correct `*_ATTRS` column order, then pass that string to `/string-to-lmfdb-object`.

**Dependency:** Requires the lmfdb schema tables to be populated (run `/textfile-to-database` first).
Column ordering in the SELECT must exactly match the alphabetical `*_ATTRS` order from
`package-LMFDB.mag`, with `order_label` mapped back to `order`.

## Step 1 — Query the lmfdb table

Choose the query for the object type. All SELECTs return columns in `*_ATTRS` alphabetical order.

### Orders (`LMFDBCliffOrd_ATTRS`)

```sql
SELECT
    basis, clifford_algebra, dimension, discriminant,
    is_maximal, is_norm_euclidean, is_star_invariant, label, timing
FROM lmfdb.clifford_orders
WHERE label = '<order_label>';
```

### SL₂(O) groups (`LMFDBGrpSL2Cliff_ATTRS`)

```sql
SELECT
    label, matrix_generators, matrix_to_fpgroup,
    order_label AS "order", relations, timing
FROM lmfdb.clifford_sl2
WHERE label = '<sl2_label>';
```

### Gamma0 subgroups (`LMFDBGrpSL2CliffGamma0_ATTRS`)

```sql
SELECT
    abelianization, defining_element, defining_element_label,
    fp_coset_representatives, fp_generators, index, label, level_norm,
    matrix_coset_representatives, matrix_generators,
    order_label AS "order", rank, relations, timing
FROM lmfdb.clifford_gamma0
WHERE label = '<gamma0_label>';
```

### Low-index subgroups (`LMFDBPSL2GrpCliffSub_ATTRS`)

```sql
SELECT
    abelian_rank, coset_table, cusp_representatives, generators_fp, generators_matrix,
    homological_rank, index, known_conjugate_intersection, known_gamma0_level,
    known_level_pdet, label, low_index_number, manin_rank, num_cusps,
    order_label AS "order", prelabel, provisional_ordinals, relations,
    right_transversal_fp, right_transversal_matrix, timing, torsion
FROM lmfdb.clifford_subgroups
WHERE label = '<subgroup_label>';
```

## Step 2 — Emit as a pipe-delimited string

Use `psql` with `-t` (tuples only) and `-A` (unaligned) to get raw pipe-delimited output:

```bash
psql clifford_bianchi_local -t -A -F '|' -c "
    SELECT basis, clifford_algebra, dimension, discriminant,
           is_maximal, is_norm_euclidean, is_star_invariant, label, timing
    FROM lmfdb.clifford_orders
    WHERE label = '2.m1.m4.4.4.1.16.4.1.1';
"
```

Or via Python:
```python
import db_config, json

def db_to_pipe_string(label, obj_type):
    conn = db_config.get_connection()
    queries = {
        "order": ("lmfdb.clifford_orders",
                  "basis,clifford_algebra,dimension,discriminant,"
                  "is_maximal,is_norm_euclidean,is_star_invariant,label,timing"),
        "sl2":   ("lmfdb.clifford_sl2",
                  "label,matrix_generators,matrix_to_fpgroup,"
                  "order_label AS \"order\",relations,timing"),
        # ... (gamma0, subgroup analogously)
    }
    table, cols = queries[obj_type]
    with conn.cursor() as cur:
        cur.execute(f"SELECT {cols} FROM {table} WHERE label = %s", (label,))
        row = cur.fetchone()
    conn.close()
    return "|".join("\\N" if v is None else str(v) for v in row)
```

## Step 3 — Feed to `/string-to-lmfdb-object`

Pass the resulting pipe-delimited string to the `/string-to-lmfdb-object` skill, specifying the object type.

## Column-order mapping note

The lmfdb schema uses `order_label` (not `order`) to avoid the SQL reserved word. When emitting
the pipe-delimited string, alias it back to `order` in the SELECT, or document the mapping clearly
before passing to `string-to-lmfdb-object`.

## Blocking condition

This skill requires that the `*_ATTRS` ↔ lmfdb column mapping round-trips correctly:
write to DATA/ → load into staging → promote to lmfdb → query back → reconstruct Magma object →
verify invariants (label, index, abelianization) match the original.

Do not rely on this skill until that round-trip is verified on at least one order and one subgroup.
