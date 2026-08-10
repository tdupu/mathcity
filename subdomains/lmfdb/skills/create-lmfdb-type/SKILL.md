---
name: create-lmfdb-type
description: >
  Scaffold a new LMFDB data type in the Clifford-Bianchi Magma codebase
  (package-LMFDB.mag, package-IO.mag, schema.md). Use this skill whenever the
  user wants to add a new serializable data object — e.g. "I want to store X in
  the database", "add a new LMFDB type for Y", "create read/write/load/save
  intrinsics for Z", or any time new attributes, a new schema table, or new make
  scripts are needed for a Magma LMFDB object. Trigger on any mention of LMFDB
  types, new data tables, serialization, or "create_lmfdb_object".
---

# create-lmfdb-type

Scaffold a complete new LMFDB serializable type for the Clifford-Bianchi codebase.
See `references/schema-template.md` for the schema section template. The best
reference implementation in the codebase is `LMFDBPSL2GrpCliffSub` in
`package-LMFDB.mag` (subgroups section of `schema.md`).

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

## Inputs to collect from the user

Before writing any code, confirm you have all of:

1. **Type name** — the Magma type name, e.g. `LMFDBConjugateIntersection`. By convention it starts with `LMFDB`.
2. **Attributes with column types** — for each attribute: name, column type (Text, Integer, Jsonb, Bool, etc.), example value, and a one-line description. There MUST be a `label` attribute (TextCols).
3. **Label scheme** — how the label is constructed (dot-separated components, hashes, underscore prefixes, etc.). Document it explicitly.
4. **DATA path layout** — where files live under `DATA/`. Two common patterns:
   - *One file per order* (all entries appended): `DATA/<type_dir>/<order_label>`
   - *One file per entry*: `DATA/<type_dir>/<order_label>/<entry_label>`
   Choose based on how loading will be used: per-entry loading → one file per entry.
5. **Populating intrinsics** — the Magma intrinsics or functions that compute the data (names and signatures).
6. **Caching** — does the object need to be cached on a Magma type as an attribute? If yes, which type and attribute name.
7. **Make scripts** — should data-generation scripts be written now, or filed as a GitHub issue?
8. **Database columns** — Step 10 (`update-schema`) will wire the new type into the full DB pipeline: `schema.md`, `db_schema_staging.sql`, `db_schema_lmfdb.sql`, `db_load.py`, and `db_migrate.py`. Confirm all column names and types are final before running Step 10 — changing them afterwards requires a data migration.

If any of these are missing, ask before proceeding.

## Output checklist

Produce all of the following, in this order:

- [ ] Type declaration and ATTRS in `package-LMFDB.mag`
- [ ] `Print` intrinsic in `package-LMFDB.mag`
- [ ] `load_lmfdb_<name>` intrinsic in `package-LMFDB.mag`
- [ ] `'eq'` intrinsic in `package-LMFDB.mag`
- [ ] Path function(s) in `package-LMFDB.mag`
- [ ] `read_lmfdb_<name>` intrinsic(s) in `package-LMFDB.mag`
- [ ] `write_lmfdb_<name>` intrinsic in `package-LMFDB.mag`
- [ ] `create_lmfdb_<name>` intrinsic in `package-LMFDB.mag`
- [ ] Column registration in `package-IO.mag`
- [ ] All schema files via `update-schema` skill (covers schema.md, db_schema_staging.sql, db_schema_lmfdb.sql, db_load.py, db_migrate.py — see Step 10)
- [ ] Caching attribute on Magma type (or GitHub issue)
- [ ] Make script (or GitHub issue)

---

## Step 1 — Type declaration and ATTRS

Insert after the last existing `declare type` / `ATTRS` block in `package-LMFDB.mag`.

```magma
declare type LMFDBXXX;
declare attributes LMFDBXXX:
    attr1,
    attr2,
    label,
    timing;

LMFDBXXXAttr_ATTRS:=Sort(["attr1","attr2","label","timing"]);//ALWAYS ALPHABETICAL!
```

**Critical:** the ATTRS list drives serialization order. It MUST be `Sort([...])` and the
comment `//ALWAYS ALPHABETICAL!` is required so future editors don't break it.
Every attribute name in the `declare attributes` block must appear in the ATTRS list
and vice versa.

---

## Step 2 — Print intrinsic

```magma
//##########################
intrinsic Print(X::LMFDBXXX)
//##########################
{Print LMFDBXXX}
    printf "LMFDBXXX %o:\n", Get(X, "label");
    // print a few key fields for quick inspection
    printf "  order %o\n", Get(X, "order");
end intrinsic;
```

---

## Step 3 — load_lmfdb_xxx

Deserializes one pipe-delimited line. Always use `attrs := LMFDBXXX_ATTRS` to
drive the loop so column order stays in sync with the ATTRS list.

```magma
//####################
intrinsic load_lmfdb_xxx(line::MonStgElt: sep:="|") -> LMFDBXXX
//####################
{}
    attrs := LMFDBXXX_ATTRS;
    data  := Split(line, sep: IncludeEmpty := true);
    error if #data ne #attrs, "Wrong size data line for LMFDBXXX";
    X := New(LMFDBXXX);
    for i in [1..#data] do
        attr := attrs[i];
        X``attr := LoadAttr(attr, data[i], X);
    end for;
    return X;
end intrinsic;
```

---

## Step 4 — eq intrinsic

```magma
//#####################
intrinsic 'eq'(X1::LMFDBXXX, X2::LMFDBXXX) -> BoolElt
//#####################
{}
    return X1`label eq X2`label;
end intrinsic;
```

---

## Step 5 — Path functions

Use `SetColumns(0)` and `get_data_folder()` in every path function.

**One-file-per-order pattern:**
```magma
//###############################
intrinsic get_lmfdb_xxx_path(order_label::MonStgElt) -> MonStgElt
//###############################
{}
    SetColumns(0);
    Folder := get_data_folder();
    return Sprintf("%oxxx/%o", Folder, order_label);
end intrinsic;

// Convenience overloads:
intrinsic get_lmfdb_xxx_path(O::CliffOrd) -> MonStgElt
{}  return get_lmfdb_xxx_path(get_label(O)); end intrinsic;

intrinsic get_lmfdb_xxx_path(SL2O::GrpPSL2Cliff) -> MonStgElt
{}  return get_lmfdb_xxx_path(get_label(get_clifford_order(SL2O))); end intrinsic;
```

**One-file-per-entry pattern** (preferred when loading is per-entry):
```magma
//###############################
intrinsic get_lmfdb_xxx_path(SL2O::GrpPSL2Cliff, entry_label::MonStgElt) -> MonStgElt
//###############################
{Path: DATA/xxx/<order_label>/<entry_label>}
    SetColumns(0);
    Folder := get_data_folder();
    order_label := get_label(get_clifford_order(SL2O));
    return Sprintf("%oxxx/%o/%o", Folder, order_label, entry_label);
end intrinsic;

intrinsic get_lmfdb_xxx_path(X::LMFDBXXX) -> MonStgElt
{}
    // derive order_label from label (first 4 dot-components)
    parts := Split(X`label, ".");
    order_label := parts[1] cat "." cat parts[2] cat "." cat parts[3] cat "." cat parts[4];
    Folder := get_data_folder();
    SetColumns(0);
    return Sprintf("%oxxx/%o/%o", Folder, order_label, X`label);
end intrinsic;
```

Note: never use `get_label(SL2O)` — there is no single-argument overload for
`GrpPSL2Cliff`. Always use `get_label(get_clifford_order(SL2O))`.

---

## Step 6 — read_lmfdb_xxx

**One-file-per-order:**
```magma
//###########################
intrinsic read_lmfdb_xxx(fname::MonStgElt) -> SetIndx
//###########################
{}
    lines := {@ H : H in Split(Read(fname), "\n") | #H gt 0 @};
    return {@ load_lmfdb_xxx(line) : line in lines @};
end intrinsic;

intrinsic read_lmfdb_xxx(SL2O::GrpPSL2Cliff) -> SetIndx
{}
    fname := get_lmfdb_xxx_path(SL2O);
    return read_lmfdb_xxx(fname);
end intrinsic;
```

**One-file-per-entry:**
```magma
//###########################
intrinsic read_lmfdb_xxx(fname::MonStgElt) -> LMFDBXXX
//###########################
{Read one entry from a single-line file.}
    lines := {@ H : H in Split(Read(fname), "\n") | #H gt 0 @};
    assert #lines eq 1;
    return load_lmfdb_xxx(lines[1]);
end intrinsic;

intrinsic read_lmfdb_xxxs(SL2O::GrpPSL2Cliff) -> SetIndx
{Read all entries for this order from the per-entry directory.}
    dir   := get_lmfdb_xxx_dir(SL2O);
    fnames := Split(Pipe("ls " * dir * " 2>/dev/null", ""), "\n");
    return {@ read_lmfdb_xxx(dir * "/" * f) : f in fnames | #f gt 0 @};
end intrinsic;
```

---

## Step 7 — write_lmfdb_xxx

```magma
//#############################
intrinsic write_lmfdb_xxx(X::LMFDBXXX: overwrite := false)
//#############################
{}
    SetColumns(0);
    file := get_lmfdb_xxx_path(X);
    data := SaveLMFDBObject(X);
    print_file(file, data: overwrite := overwrite);
end intrinsic;
```

`print_file` handles mkdir, touch, and overwrite logic. `SaveLMFDBObject` uses
`DefaultAttributes` which reads the ATTRS list — this is why alphabetical order matters.

---

## Step 8 — create_lmfdb_xxx

This is the main constructor. It takes the Magma objects that hold the raw data
and populates the LMFDB type.

```magma
//########################
intrinsic create_lmfdb_xxx(SL2O::GrpPSL2Cliff, <other inputs> : timing:=" ") -> LMFDBXXX
//########################
{}
    X := New(LMFDBXXX);
    X`label   := <compute label>;
    X`order   := get_label(get_clifford_order(SL2O));
    X`timing  := timing;
    // ... populate remaining fields using jsonify_* helpers for Clifford objects
    return X;
end intrinsic;
```

Use `jsonify_matrix`, `jsonify_matrix_list`, `jsonify_integer_matrix` for Clifford
algebra matrix data. Use plain Magma sequences for integer/word data.

**CRITICAL — never call `SaveJsonb()` when assigning to LMFDB attributes.** Assigning
`X\`attr := SaveJsonb(v)` wraps `v` in an extra `"..."` layer that `db_load.py`
will not strip, corrupting every jsonb field in the stored file (#174). Assign the
raw Magma value directly: `X\`attr := jsonify_matrix(m)`. `SaveAttr` (called inside
`SaveLMFDBObject`) handles encoding.

---

## Step 9 — Column registration in package-IO.mag

Add each new attribute name to the appropriate column list at the top of `package-IO.mag`.
The column type determines how `LoadAttr` and `SaveAttr` handle (de)serialization:

| Column list    | Magma type stored             | Notes                              |
|----------------|-------------------------------|------------------------------------|
| `TextCols`     | `MonStgElt`                   | Always includes `label`            |
| `IntegerCols`  | `RngIntElt`                   |                                    |
| `BoolCols`     | `BoolElt`                     | Serialized as `t`/`f`              |
| `JsonbCols`    | Sequences, nested lists, dicts| Clifford matrices, word sequences  |

Add to the `Sort([...])` call in the appropriate list — keep it sorted to avoid
confusing diffs. Do NOT create new column type lists unless truly necessary.

---

## Step 10 — Database schema (all seven files)

Invoke the `update-schema` skill. This is where the **database pipeline** gets wired
in. `update-schema` covers all seven files that must stay in sync:

| File | What changes |
|------|-------------|
| `magma/schema.md` | New section documenting the type (use `references/schema-template.md`) |
| `magma/package-LMFDB.mag` | Already done in Steps 1–8 |
| `magma/package-IO.mag` | Already done in Step 9 |
| `magma/python/db_schema_staging.sql` | New `CREATE TABLE IF NOT EXISTS staging.<type>_src` block |
| `magma/python/db_schema_lmfdb.sql` | New `CREATE TABLE IF NOT EXISTS lmfdb.clifford_<type>` block |
| `magma/python/db_load.py` | New `*_ATTRS` list + column type sets; new `--only <type>` path |
| `magma/python/db_migrate.py` | New `INSERT INTO lmfdb.clifford_<type>` block in `promote_to_lmfdb` |

Pass `update-schema`:
- The new type name and Magma type (`LMFDBXXX`)
- The DATA path layout (from Step 4)
- All attributes with their column types, examples, and descriptions
- The label scheme (dot-component count, construction rule)
- That this is a **new type** (so it needs new tables, not just new columns)

`update-schema` will also handle archiving any existing DATA/ flat files and
regenerating them with `\N` for the new columns. Since this is a brand-new type
there will be no existing files to migrate.

See `references/schema-template.md` for the section format `update-schema` should use.

---

## Step 11 — Caching and make scripts

**Caching:** If the object should be cached on a `GrpPSL2Cliff` or other Magma
type, add the attribute to the `declare attributes` block in the relevant package
and populate it in a `load_xxx` intrinsic in `package-modular-symbols.mag`.
If this is deferred, file a GitHub issue with the attribute name, type, and
populating intrinsic.

**Make scripts:** If computation is expensive or involves a loop over many objects,
create a make script. Place it in the right subdirectory:

- **New pipeline step** (runs repeatedly in the bomb.sh/crunch.sh loop): `magma/make/crunch/make-xxx.mag`
- **One-off migration or data repair** (manual invocation only): `magma/make/one-offs/make-xxx-1.mag`

Do NOT create scripts at bare `magma/make/make-xxx.mag` — that directory now only
holds `make-config.conf` and the `crunch/`, `dispatch/`, `one-offs/` subdirectories.

Pattern for crunch/ scripts: read `MAGMA_DIM` and `MAGMA_ORDER` env vars, load existing
data, check per-entry file existence with `OpenTest`, skip if found (restartable), compute,
create, write, print `SUMMARY dim=N written=W skipped=S`. If deferred, file a GitHub issue
referencing the populating intrinsics and blocking dependencies.

---

## Invariants to preserve

- **Never edit `.sig` files.** They are auto-generated.
- **ATTRS must be `Sort([...])`** with `//ALWAYS ALPHABETICAL!` comment.
- **`get_label(SL2O)` does not exist.** Use `get_label(get_clifford_order(SL2O))`.
- **`adj` is a Magma reserved word.** Use `adjacent` or similar.
- **Clifford algebra arithmetic is non-commutative.** Never assume `a*b == b*a`.
- **Do not add Claude as Co-Authored-By in commits.**
