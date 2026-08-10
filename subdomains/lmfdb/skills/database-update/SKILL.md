---
name: database-update
description: Update a stored object in the lmfdb database by pulling it into Magma, applying user-specified recomputations or field changes, and writing it back. Use whenever the user wants to update a DB entry (e.g. relabel, enrich a field, recompute an invariant) without rerunning the full make script.
---

# database-update

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

// Lookup → mutate → upsert:
X := LookUpLMFDB(db, "LMFDBCliffOrd", "2.1.m4.1.2.1.1.2.1.1");
X`timing := Sprintf("%o", Cputime());
AddLMFDB(db, "LMFDBCliffOrd", [X] : overwrite := true);

// Generic (Assoc-level) update:
q := AssociativeArray(); q["label"] := "2.1.m4.1.2.1.1.2.1.1";
changes := AssociativeArray(); changes["timing"] := "123.4";
Update(db, "clifford_orders", q, changes);

// Batch update via SearchLMFDB:
q := AssociativeArray(); q["order"] := "2.1.m4.1.2.1.1.2.1.1";
objs := SearchLMFDB(db, "LMFDBPSL2GrpCliffSub", q);
for X in objs do
    X`timing := Sprintf("%o", Cputime());
    AddLMFDB(db, "LMFDBPSL2GrpCliffSub", [X] : overwrite := true);
end for;
```

Note: `AddLMFDB` requires `overwrite := true` when the label already exists. Default `overwrite := false` will error if the label is already in the table.

## Legacy approach (pre-package-textfiles / pre-package-database)

**Purpose:** Round-trip pipeline for updating a stored object:

```
lmfdb.* → pipe string → LMFDBXxx → native Magma object
                                          ↓
                              [user-specified update commands]
                                          ↓
                          LMFDBXxx → lmfdb.* (or DATA/ file)
```

This composes:
`/database-to-lmfdb-object` → `/lmfdb-object-to-magma` → [updates] →
`/magma-to-lmfdb-object` → `/lmfdb-object-to-database`

(Or replace the last step with `/lmfdb-object-to-textfile` + `/textfile-to-database` to also
archive to DATA/.)

### Step 1 — Pull the object from the database

Use `/database-to-lmfdb-object` to query and deserialize. Example for an order:

```magma
Z := Integers(); Q := Rationals();
AttachSpec("../hecke.spec");
SetLMFDBRootFolder("..");

// Emit pipe string from DB (run beforehand):
//   psql clifford_bianchi_local -t -A -F '|' --null='\N' -c "
//       SELECT basis, clifford_algebra, dimension, discriminant,
//              is_maximal, is_norm_euclidean, is_star_invariant, label, timing
//       FROM lmfdb.clifford_orders WHERE label = '<label>'
//   " > /tmp/db_update_obj.txt

line := [H : H in Split(Read("/tmp/db_update_obj.txt"), "\n") | #H gt 0][1];
X    := load_lmfdb_clifford_order(line);   // → LMFDBCliffOrd
```

For other object types, use `load_lmfdb_sl2`, `load_lmfdb_gamma0`, or
`load_lmfdb_psl2_grp_cliff_sub` with the corresponding SELECT from the right table.

### Step 2 — Restore the native Magma object

Use `/lmfdb-object-to-magma`:

```magma
O := clifford_order(X);                   // LMFDBCliffOrd → CliffOrd
// PSL2O := clifford_bianchi_group(X`label);  // LMFDBGrpSL2Cliff → GrpPSL2Cliff
```

### Step 3 — Apply update commands

This is the user-specified step. State clearly what is being recomputed or changed.

**Common pattern: relabel (compute new LMFDB label)**
```magma
old_label := X`label;
new_label := get_label(O);               // default method := "lmfdb"
X`label   := new_label;
printf "label map: %o -> %o\n", old_label, new_label;
```

**Common pattern: update a scalar field**
```magma
X`timing := Sprintf("%o", Cputime(T0));
```

**Common pattern: recompute a jsonb field from the native object**
```magma
X`basis := SaveJsonb(jsonify_order_basis(O));
```

**If the native object itself needs recomputation** (e.g. re-running a make step):
```magma
T0 := Cputime();
// ... expensive recomputation ...
X_new := create_lmfdb_object(O_new: timing := Sprintf("%o", Cputime(T0)));
```

### Step 4 — Serialize the updated object

Use `/magma-to-lmfdb-object` if you rebuilt the native object, or just update `X`'s attributes
directly (faster for field-only changes):

```magma
line_new := SaveLMFDBObject(X);
print_file("/tmp/db_update_obj_new.txt", line_new: overwrite := true);
```

### Step 5 — Write back to the database

Use `/lmfdb-object-to-database`:

```bash
cd magma/python
python3 -c "
import io, db_config
from db_load import ORDERS_ATTRS, _staging_cols, _preprocess_field

line = open('/tmp/db_update_obj_new.txt').read().strip()
# ... call insert_lmfdb_object(line, 'staging.orders_src', ORDERS_ATTRS)
"
python3 db_migrate.py --action populate_ledger
python3 db_migrate.py --action promote_to_lmfdb
```

`promote_to_lmfdb` uses `ON CONFLICT (label) DO UPDATE` — if the label changed (e.g. relabeling),
the old label entry remains and a new one is added. To remove the old label entry:
```sql
DELETE FROM lmfdb.clifford_orders WHERE label = '<old_label>';
-- Do this AFTER updating all FK references (clifford_sl2, clifford_gamma0, clifford_subgroups)
```

### Optional: also archive to DATA/

If you want the updated object in both the DB and DATA/:
```magma
cl := dejsonify_clifford_algebra(X`clifford_algebra);
write_lmfdb_clifford_order(cl, X: overwrite := false);
```

### Worked example: relabeling a single order

```magma
// 1. Pull from DB (run psql dump first — see Step 1)
line := [H : H in Split(Read("/tmp/db_update_obj.txt"), "\n") | #H gt 0][1];
X    := load_lmfdb_clifford_order(line);
O    := clifford_order(X);

// 2. Relabel
old_label := X`label;
X`label   := get_label(O);
printf "Relabeled: %o -> %o\n", old_label, X`label;

// 3. Serialize
print_file("/tmp/db_update_obj_new.txt", SaveLMFDBObject(X): overwrite := true);
```

Then in Python: load label_map, load new file, promote.

### Object type reference

| Object type | Load intrinsic                   | Native type    | Serialize           |
|-------------|----------------------------------|----------------|---------------------|
| order       | `load_lmfdb_clifford_order`      | `CliffOrd`     | `SaveLMFDBObject`   |
| sl2         | `load_lmfdb_sl2`                 | `GrpPSL2Cliff` | `SaveLMFDBObject`   |
| gamma0      | `load_lmfdb_gamma0`              | `GrpFP`        | `SaveLMFDBObject`   |
| subgroup    | `load_lmfdb_psl2_grp_cliff_sub`  | —              | `SaveLMFDBObject`   |

## When to use legacy vs. new

Use the new `LookUpLMFDB` / `AddLMFDB` / `Update` / `SearchLMFDB` API (new) for any update that can be expressed within a single Magma session — it avoids the psql shell round-trip, temp files, and the Python staging pipeline entirely. Fall back to the legacy approach only when you need to recompute a native Magma object mid-pipeline (e.g., a full make-step rerun), when you need to handle FK cleanup after a relabeling, or when batch-promoting via `db_migrate.py` is already part of an existing workflow.
