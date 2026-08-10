---
name: lmfdb-object-to-textfile
description: Write an LMFDB wrapper object directly to its data file in one step. Use whenever the user wants to persist an LMFDB object, asks "how do I save this to disk", is writing a make script, or wants the combined lmfdb-object-to-string + string-to-textfile workflow.
---

## New: uniform `write_textfile` (package-textfiles)

For a typename-agnostic one-liner, use `write_textfile` from `package-textfiles.mag`:

```magma
// Works for any LMFDB typename — no need to know the type-specific write_lmfdb_* name:
write_textfile("LMFDBCliffOrd",           X);
write_textfile("LMFDBGrpSL2Cliff",        X);
write_textfile("LMFDBGrpSL2CliffGamma0",  X);
write_textfile("LMFDBPSL2GrpCliffSub",    X);
```

`write_textfile` always uses `overwrite := true` (replaces the existing file).
Path logic follows the same DATA/ conventions as the type-specific `write_lmfdb_*` intrinsics.

Use the type-specific intrinsics below when you need `overwrite := false` (append) or need
the path separately.

---

# lmfdb-object-to-textfile

**Purpose:** Serialize an LMFDB object and write it to the correct DATA/ file in one call. This is `/lmfdb-object-to-string` followed by `/string-to-textfile`.

## Preferred: use the write_lmfdb_* intrinsics

```magma
write_lmfdb_clifford_order(cl, X: overwrite := false)  // LMFDBCliffOrd
write_lmfdb_sl2(cl, X: overwrite := false)             // LMFDBGrpSL2Cliff
write_lmfdb_gamma0(X: overwrite := false, timing := " ") // LMFDBGrpSL2CliffGamma0
write_lmfdb_conj_intersection(X: overwrite := false)   // LMFDBConjugateIntersection
```

Convenience overloads that accept the raw Magma object exist for some types — see `/magma-to-textfile`.

## Manual pattern (when no write_lmfdb_* exists)

```magma
data := SaveLMFDBObject(X);
path := get_lmfdb_<type>_path(...);
print_file(path, data: overwrite := false);
```

## Overwrite semantics

- `overwrite := false` (default): appends the line to an existing file, or creates a new file.
- `overwrite := true`: deletes the file and writes fresh. Use for single-object files (gamma0 v2, CI, hecke) when recomputing.
- For multi-line files (orders, sl2) with `overwrite := false`, duplicate entries are possible if you call twice — guard with a label check first.

## Edge cases

- `write_lmfdb_gamma0(X)` uses `get_lmfdb_gamma0_path(O)` (old multi-line scheme); for the v2 per-file scheme use `write_lmfdb_gamma02(X)`.
- Hecke: use `write_lmfdb_hecke(MS, alpha)` which wraps `create_lmfdb_object(MS, alpha)` + `print_file`.
- Always call `SetLMFDBRootFolder(".")` (or the appropriate root) before writing.
