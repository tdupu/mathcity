---
name: database-to-textfile
description: Export one or more objects from the lmfdb PostgreSQL tables back to DATA/ flat files. Use whenever the user wants to regenerate DATA/ files from the database, asks "write this DB entry to disk", or needs the combined database-to-lmfdb-object + lmfdb-object-to-textfile pipeline.
---

# database-to-textfile

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

// Export entire table to DATA/:
PrintToTextfile(db, "clifford_orders");
PrintToTextfile(db, "clifford_sl2");
PrintToTextfile(db, "clifford_gamma0");
PrintToTextfile(db, "clifford_subgroups");

// Filtered export:
q := AssociativeArray(); q["order_label"] := "2.1.m4.1.2.1.1.2.1.1";
PrintToTextfile(db, "clifford_subgroups" : query := q,
    dump_path := "/tmp/preview/");

// Export to custom path:
PrintToTextfile(db, "clifford_orders" : dump_path := "/tmp/export/");
```

`PrintToTextfile` maps the table name to its LMFDB typename, fetches all matching rows, and writes each one using `write_textfile`. It uses `overwrite := true` for each file.

## Legacy approach (pre-package-textfiles / pre-package-database)

**Purpose:** Query `lmfdb.*` for a given label (or set of labels), emit pipe-delimited rows in
`*_ATTRS` column order, and write them to the appropriate DATA/ files — exactly the format that
`load_lmfdb_*` Magma intrinsics expect.

This is `/database-to-lmfdb-object` → `/lmfdb-object-to-textfile`.

### Step 1 — Identify the label(s) and object type

Determine which table and label(s) to export. Object types:

| Object type    | lmfdb table               | DATA/ path                                          |
|----------------|---------------------------|-----------------------------------------------------|
| order          | `lmfdb.clifford_orders`   | `DATA/orders/<dim>.<form_label>`                    |
| sl2            | `lmfdb.clifford_sl2`      | `DATA/sl2/<dim>.<form_label>`                       |
| gamma0         | `lmfdb.clifford_gamma0`   | `DATA/gamma0/<order_label>/<gamma0_label>` (v2)     |
| subgroup       | `lmfdb.clifford_subgroups`| `DATA/subgroups/<order_label>/<subgroup_label>.txt` |

### Step 2 — Emit the pipe-delimited row

Use `psql` with `-t -A -F '|'` and SELECT columns in exact `*_ATTRS` alphabetical order.
For NULL values, use `--null='\N'` or coalesce in the query.

**Orders** (`LMFDBCliffOrd_ATTRS`):
```bash
psql clifford_bianchi_local -t -A -F '|' --null='\N' -c "
    SELECT basis, clifford_algebra, dimension, discriminant,
           is_maximal, is_norm_euclidean, is_star_invariant, label, timing
    FROM lmfdb.clifford_orders WHERE label = '<label>'
" > /tmp/export_order.txt
```

**SL2** (`LMFDBGrpSL2Cliff_ATTRS`):
```bash
psql clifford_bianchi_local -t -A -F '|' --null='\N' -c "
    SELECT label, matrix_generators, matrix_to_fpgroup,
           order_label, relations, timing
    FROM lmfdb.clifford_sl2 WHERE label = '<label>'
" > /tmp/export_sl2.txt
```

**Gamma0** (`LMFDBGrpSL2CliffGamma0_ATTRS`):
```bash
psql clifford_bianchi_local -t -A -F '|' --null='\N' -c "
    SELECT abelianization, defining_element, defining_element_label,
           fp_coset_representatives, fp_generators, index, label, level_norm,
           matrix_coset_representatives, matrix_generators,
           order_label, rank, relations, timing
    FROM lmfdb.clifford_gamma0 WHERE label = '<label>'
" > /tmp/export_gamma0.txt
```

**Subgroups** (`LMFDBPSL2GrpCliffSub_ATTRS`):
```bash
psql clifford_bianchi_local -t -A -F '|' --null='\N' -c "
    SELECT abelian_rank, coset_table, cusp_representatives, generators_fp,
           generators_matrix, homological_rank, index,
           known_conjugate_intersection, known_gamma0_level, known_level_pdet,
           label, low_index_number, manin_rank, num_cusps, order_label,
           prelabel, provisional_ordinals, relations, right_transversal_fp,
           right_transversal_matrix, timing, torsion
    FROM lmfdb.clifford_subgroups WHERE label = '<label>'
" > /tmp/export_sub.txt
```

Note: `order_label` in SQL → `order` in the Magma pipe string (the 4th positional field in sl2,
11th in gamma0, 15th in subgroups). Magma's `LoadAttr` reads by position, not name, so this is
transparent.

### Step 3 — Write to DATA/

Copy the `/tmp/export_*.txt` content to the appropriate DATA/ file. Use `print_file` semantics:
`overwrite := false` appends; `overwrite := true` replaces.

For orders and sl2 (multi-order files), append:
```bash
cat /tmp/export_order.txt >> DATA/orders/2.1
```

For gamma0 and subgroups (single-object files), write fresh:
```bash
mkdir -p DATA/gamma0/<order_label>
cp /tmp/export_gamma0.txt DATA/gamma0/<order_label>/<gamma0_label>
```

Alternatively: load the pipe string in Magma and use `write_lmfdb_*` intrinsics:
```magma
SetLMFDBRootFolder(".");
line := [H : H in Split(Read("/tmp/export_order.txt"), "\n") | #H gt 0][1];
X    := load_lmfdb_clifford_order(line);
cl   := dejsonify_clifford_algebra(X`clifford_algebra);
write_lmfdb_clifford_order(cl, X: overwrite := false);
```

### Bulk export

To export all objects of a type for a given order:
```bash
psql clifford_bianchi_local -t -A -F '|' --null='\N' -c "
    SELECT abelianization, defining_element, ... FROM lmfdb.clifford_gamma0
    WHERE order_label = '2.1.m4.1W6TEV'
" > /tmp/export_gamma0_all.txt
```

Then split into per-file entries or load into Magma for bulk writing.

### Next step

If the goal is to update an object before writing, use `/database-update` or `/textfile-update` instead.

## When to use legacy vs. new

Use `PrintToTextfile` (new) whenever you want to export a full table or a filtered subset of rows to DATA/ in one call — it handles the typename mapping, per-row file routing, and overwrite semantics automatically. Fall back to the legacy psql + shell approach only when you need to export with a custom column projection not covered by the standard `*_ATTRS` order, when targeting a schema other than `lmfdb.*`, or when the database intrinsics are not yet available in the attached package version.
