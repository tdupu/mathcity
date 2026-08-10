---
name: update-schema
description: Update the LMFDB database schema across ALL affected files for the hecke/Clifford-Bianchi codebase. Use this skill whenever the user wants to add, remove, or modify columns, table definitions, storage paths, label schemes, or LMFDB object attributes — even if they just say "add X to the schema" or "schema needs a column for Y". Touches schema.md, package-LMFDB.mag, package-IO.mag, db_schema_staging.sql, db_schema_lmfdb.sql, db_load.py, and db_migrate.py to keep everything in sync. After editing, commits and pushes via the claude-commit skill.
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
  echo "(This conf holds your PostgreSQL and DATA_DIR settings for the LMFDB pipeline.)"
  exit 1
fi
source "$CONF"
```

## Overview

A schema change touches **seven files** that must all stay in sync. This skill walks through every one. Never update just `schema.md` in isolation — a column added to the documentation but missing from `package-IO.mag` or `db_load.py` will silently break serialization or loading.

## Step 0 — Parse the instructions

The user will describe what to change. Common cases:
- Adding or removing a column on an existing LMFDB type
- Adding a new LMFDB object type (see `create-lmfdb-type` skill for full scaffolding)
- Changing a label scheme or storage path
- Fixing documentation, examples, or **Not implemented** annotations

Clarify before proceeding if:
- The **column type** is ambiguous (Text / Integer / Bool / Jsonb)
- The **LMFDB type name** is unclear (e.g. which `*_ATTRS` list it belongs to)
- The change touches `db_migrate.py` INSERT/UPDATE logic in a non-obvious way

## Step 1 — Read all affected files

Read these in parallel before making any edits:

1. `magma/schema.md`
2. `magma/package-LMFDB.mag` — type declaration and `*_ATTRS` list
3. `magma/package-IO.mag` — `TextCols`, `IntegerCols`, `BoolCols`, `JsonbCols` at the top
4. `magma/python/db_schema_staging.sql`
5. `magma/python/db_schema_lmfdb.sql`
6. `magma/python/db_load.py` — `*_ATTRS` Python lists and `_TEXT_COLS` / `_INTEGER_COLS` / `_BOOL_COLS` sets
7. `magma/python/db_migrate.py` — INSERT column lists and ON CONFLICT SET clauses

## Step 2 — Apply changes to each file

Work through every file below. For each one, note what changed and why.

---

### 2a. `magma/schema.md`

- **Tables**: GitHub-flavored pipe-delimited markdown. Columns: `Column | Type | Example | Notes`. Align pipes.
- **Section order**: Orders → Clifford Bianchi Groups → Gamma0 Subgroups → Hecke Matrices → Low Index Subgroups → Modular Forms → Conjugate Intersections → Label Scheme
- **Storage paragraphs**: bold `**Storage:**` prefix, path pattern, one-file-per-object vs multi-line, concrete example path.
- **Section separators**: `---` horizontal rule between every section.
- **Not implemented** notes: italicized or bold if columns are defined but not yet coded.

---

### 2b. `magma/package-LMFDB.mag`

Locate the `declare attributes LMFDBXXX` block and the corresponding `LMFDBXXX_ATTRS` list for the type being changed.

**Adding a column:**
1. Add the attribute name to the `declare attributes` block (alphabetical order).
2. Add the attribute name to the `Sort([...])` in `LMFDBXXX_ATTRS`. The comment `//ALWAYS ALPHABETICAL!` must remain.
3. If the attribute can be absent (optional/nullable), update `load_lmfdb_xxx` to handle `\N` (the backward-compat pattern: check `#data eq #attrs - 1` and insert `"\\N"` at the right position).
4. Update `create_lmfdb_xxx` to populate the new attribute.

**Removing a column:**
1. Remove from `declare attributes` and from `LMFDBXXX_ATTRS`.
2. Remove from `load_lmfdb_xxx` (no special handling needed — the field will no longer be read).
3. Remove from `create_lmfdb_xxx`.

**Critical invariants:**
- `ATTRS` must be `Sort([...])` — never hand-sort.
- Every name in `declare attributes` must appear in `ATTRS` and vice versa.
- Never edit `.sig` files.

---

### 2c. `magma/package-IO.mag`

The column type lists at the top of the file drive `LoadAttr`/`SaveAttr` dispatch. Add or remove the attribute name from exactly one of:

| List           | Use for                                      |
|----------------|----------------------------------------------|
| `TextCols`     | `MonStgElt` — always includes `label`        |
| `IntegerCols`  | `RngIntElt`                                  |
| `BoolCols`     | `BoolElt` — serialized as `t`/`f`            |
| `JsonbCols`    | Sequences, nested lists, Clifford matrices   |

Each list is a `Sort([...])` call — keep it sorted. Do NOT create new column type lists.

---

### 2d. `magma/python/db_schema_staging.sql`

Locate the `CREATE TABLE IF NOT EXISTS staging.<type>_src` block. Add or remove the column with the correct PostgreSQL type:

| Magma column type | PostgreSQL type |
|-------------------|-----------------|
| TextCols          | `text`          |
| IntegerCols       | `integer`       |
| BoolCols          | `boolean`       |
| JsonbCols         | `jsonb`         |

Column order in SQL should match the alphabetical `*_ATTRS` order (for readability — SQL doesn't require it, but it helps). The comment `-- Column order matches LMFDBXXX_ATTRS` must stay accurate.

---

### 2e. `magma/python/db_schema_lmfdb.sql`

Locate the `CREATE TABLE IF NOT EXISTS lmfdb.clifford_<type>` block. Apply the same column addition/removal with the same PostgreSQL types. Note: some column names differ from Magma (e.g. `order` → `order_label_old` to avoid the SQL reserved word).

---

### 2f. `magma/python/db_load.py`

Two places to update:

1. **`*_ATTRS` list** (e.g. `ORDERS_ATTRS`, `GAMMA0_ATTRS`): add/remove the attribute name inside the `sorted([...])` call. Must exactly match `package-LMFDB.mag`.

2. **Column type sets** (`_TEXT_COLS`, `_INTEGER_COLS`, `_BOOL_COLS`): add/remove the attribute name from the matching frozenset. JsonbCols attributes need no entry here — they are the default COPY path.

If a legacy compat format exists (e.g. `SUBGROUPS_ATTRS_LEGACY`), decide whether it also needs updating; usually legacy formats are frozen.

---

### 2g. `magma/python/db_migrate.py`

Locate the `INSERT INTO lmfdb.clifford_<type>` block(s) in `promote_to_lmfdb`. Three things to keep in sync:

1. **INSERT column list** — add/remove the column name.
2. **SELECT column list** (the `SELECT ... FROM staging.<type>_src` that feeds it) — add/remove the same name (or its alias if renamed).
3. **ON CONFLICT DO UPDATE SET** clause — add/remove `<col> = EXCLUDED.<col>`.

---

## Step 3 — Legacy data streams (read-only)

The `magma/DATA/data-legacy-01/` directory tree contains old data that does not match the current schema. Each legacy subdirectory has a `SCHEMA` file at its root (and sometimes per-subdirectory `SCHEMA` files) that document the field layout of *that specific frozen format*.

**Never modify these `SCHEMA` files.** They are the authoritative record of how legacy data was serialized and are required for migrating that data into the current database format. They describe the old format, not the aspirational one.

The `magma/schema.md` file is the **aspirational / official** schema — what the current codebase targets. The legacy `SCHEMA` files describe **historical snapshots** used by `db_load.py`'s legacy compat paths (e.g. `SUBGROUPS_ATTRS_LEGACY`). When the official schema changes, the legacy SCHEMA files and legacy ATTRS lists in `db_load.py` stay frozen.

When adding a new column: the new column will be absent from legacy files — `db_load.py` must continue to handle the old field count via its existing compat logic (inserting `r"\N"` at the new column's position). Do not assume legacy files will be regenerated.

---

## Step 4 — Migrate affected data files

After updating the code files, find all DATA/ flat files whose format has changed and archive + regenerate them.

### 4a. Identify affected files

For each table that gained or lost columns, determine which DATA/ directory holds its flat files:

| Table                    | DATA/ path pattern                            |
|--------------------------|-----------------------------------------------|
| `LMFDBCliffOrd`          | `DATA/orders/<alg_label>`                     |
| `LMFDBGrpSL2Cliff`       | `DATA/sl2/<alg_label>`                        |
| `LMFDBGrpSL2CliffGamma0` | `DATA/gamma0/<ord_label>/<gamma0_label>`       |
| `LMFDBPSL2GrpCliffSub`   | `DATA/subgroups/<ord_label>/<sub_label>`       |

Check whether any files exist for each affected type:
```bash
ls magma/DATA/<type_dir>/
```

If the directory is empty or absent, skip to Step 5.

### 4b. Archive old files

Move the outdated files into a dated legacy folder so they are preserved (not deleted). Use the date format `mm-dd-yyyy`:

```bash
mkdir -p magma/DATA/data-legacy-<mm-dd-yyyy>/<type_dir>/
mv magma/DATA/<type_dir>/* magma/DATA/data-legacy-<mm-dd-yyyy>/<type_dir>/
```

Write a `SCHEMA` file at the top of the new legacy directory documenting the old field layout — field names in order, the ATTRS list commit reference or date, and field types. This is the frozen record of the old format.

Example `SCHEMA` content:
```
# Schema: data-legacy-<mm-dd-yyyy>/<type_dir>/

Archived <date>. Format preceding addition of <new_columns>.
Corresponds to <TypeName>_ATTRS before this change.

## Field layout (N fields, pipe-delimited)

| # | Field name     | Type    |
|---|----------------|---------|
| 1 | field1         | jsonb   |
...
```

### 4c. Regenerate files with null entries

For each archived file, reload the objects and re-emit them with `\N` for every new nullable column.

**Preferred approach — Magma script:**
Write a `make/update-<type>-<N>.mag` script that:
1. Reads the archived file line by line using `load_lmfdb_<type>`
2. For each object, sets the new attribute(s) to the appropriate null/empty default (see column type defaults below)
3. Re-saves with `write_lmfdb_<type>` (or `print_file`) to the live `DATA/<type_dir>/` path

**Column-type null defaults:**
| Column type | Magma default before saving | Serialized as |
|-------------|----------------------------|---------------|
| TextCols    | `""` (empty string → skip assignment) | `\N` |
| IntegerCols | not assigned (→ `Get` returns `None()`) | `\N` |
| BoolCols    | not assigned | `\N` |
| JsonbCols   | not assigned | `\N` |

The key: `SaveLMFDBObject` calls `Get(X, attr)` which returns `None()` for unset attributes, and `SaveAttr` serializes `None()` as `\N`. So simply do not assign the new attribute when re-creating the object from old data.

**Alternative — Python one-liner** (for simple column additions where the ATTRS order is known):
```python
# insert \N at position idx (0-based) in each pipe-delimited line
for line in open("old_file"):
    parts = line.rstrip("\n").split("|")
    parts.insert(idx, r"\N")
    print("|".join(parts))
```

### 4d. Reload into staging database

After regenerating the files, run `/textfile-to-database` (or the `textfile-to-database` skill) to reload the updated files into the staging tables:

```bash
cd magma/python
python3 db_load.py --data-root ../DATA --only <type>
```

Verify the new columns are present and contain `NULL`:
```sql
SELECT COUNT(*) FROM staging.<type>_src WHERE <new_col> IS NOT NULL;
-- should be 0 for freshly-null columns
```

---

## Step 5 — Verify consistency

After all edits, do a quick cross-check:

- Column appears in `schema.md` ↔ `package-LMFDB.mag` ATTRS ↔ `package-IO.mag` type list ↔ both SQL files ↔ `db_load.py` ATTRS and type set ↔ `db_migrate.py` INSERT/SELECT/UPDATE.
- Archived files are in `DATA/data-legacy-<mm-dd-yyyy>/` with a `SCHEMA` file.
- New DATA/ files have `\N` for all new columns.
- Legacy `SCHEMA` files in `data-legacy-01/` and `*_ATTRS_LEGACY` lists in `db_load.py` are untouched.
- No `.sig` files were touched.
- `Sort([...])` and `//ALWAYS ALPHABETICAL!` comment intact in `package-LMFDB.mag`.

---

## Step 6 — Commit and push

Invoke the `claude-commit` skill. The commit message body should name every file changed and describe what column/type was added/removed/modified and why. Include a note that data files were archived to `data-legacy-<mm-dd-yyyy>/`.
