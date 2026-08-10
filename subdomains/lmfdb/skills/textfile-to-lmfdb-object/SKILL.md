---
name: textfile-to-lmfdb-object
description: Restore an LMFDB wrapper object directly from disk in one step. Use whenever the user wants to load a stored LMFDB object from DATA/, asks "how do I read an LMFDB object from file", or needs the combined textfile-to-string + string-to-lmfdb-object pipeline.
---

## New: uniform `load_textfiles` / `query_textfiles` (package-textfiles)

For bulk or filtered loads without knowing the type-specific `read_lmfdb_*` name:

```magma
// Load all stored objects of a typename:
objs := load_textfiles("LMFDBCliffOrd");
objs := load_textfiles("LMFDBPSL2GrpCliffSub");

// Filtered load:
q := AssociativeArray(); q["order"] := "2.1.m4.1.2.1.1.2.1.1";
subs := query_textfiles("LMFDBPSL2GrpCliffSub", q);

// With custom source path:
objs := load_textfiles("LMFDBCliffOrd" : source_path := "/tmp/export/DATA/orders/");
```

Equality in `query_textfiles` is tested via `Sprint()` comparison, so it handles both string and integer field values correctly.

Use the type-specific `read_lmfdb_*` wrappers below when you need finer control (e.g., loading from a specific file path, or using the v1 gamma0 multi-line scheme).

---

# textfile-to-lmfdb-object

**Purpose:** Locate the right DATA/ file, read the pipe-delimited string(s), and return LMFDB wrapper object(s). This is `/textfile-to-string` followed by `/string-to-lmfdb-object`.

## Preferred: use the read_lmfdb_* wrappers

These hide both steps:

```magma
SetLMFDBRootFolder(".");

// LMFDBCliffOrd — all orders for a Clifford algebra
lmfdb_ords := read_lmfdb_clifford_orders(cl);        // → SetIndx[LMFDBCliffOrd]
lmfdb_ords := read_lmfdb_clifford_orders(fname);     // from explicit path

// LMFDBGrpSL2Cliff — all SL2 groups for a Clifford algebra
lmfdb_sl2s := read_lmfdb_sl2(cl);                   // → SetIndx[LMFDBGrpSL2Cliff]

// LMFDBGrpSL2CliffGamma0 — all Gamma0 objects for an order (old multi-line scheme)
lmfdb_g0s  := read_lmfdb_gamma0(O);                 // → SetIndx[LMFDBGrpSL2CliffGamma0]
lmfdb_g0s  := read_lmfdb_gamma0(SL2O);
lmfdb_g0s  := read_lmfdb_gamma0(fname);

// LMFDBGrpSL2CliffGamma0 — single object (v2 per-file scheme)
lmfdb_g0   := read_lmfdb_gamma02(SL2O, alpha);      // → LMFDBGrpSL2CliffGamma0
lmfdb_g0   := read_lmfdb_gamma02(fname);

// LMFDBHeckeMatrices
lmfdb_hm   := read_lmfdb_hecke_matrices(MS, beta);  // → LMFDBHeckeMatrices

// LMFDBConjugateIntersection — single object
lmfdb_ci   := read_lmfdb_conj_intersection(fname);
lmfdb_ci   := read_lmfdb_conj_intersection(SL2O, sigma_label, alpha);

// LMFDBConjugateIntersection — all alphas for a given sigma
lmfdb_cis  := read_lmfdb_conj_intersections(SL2O, sigma_label); // → SetIndx
```

## Manual pipeline (when no wrapper exists)

```magma
path  := get_lmfdb_<type>_path(...);
lines := [H : H in Split(Read(path), "\n") | #H gt 0];
objs  := [load_lmfdb_<type>(l) : l in lines];
```

## Edge cases

- For single-object files (gamma0 v2, CI, hecke), `read_lmfdb_*` asserts `#lines eq 1`.
- `read_lmfdb_gamma0(SL2O)` prints the folder path at verbose level 1 — this is normal.
- Bug #161: comparing two `LMFDBGrpSL2Cliff` objects with `eq` after loading will error due to `matrix_to_fpgroup` type mismatch. Do not use `eq` on this type.
- Guard reads with `OpenTest(path, "r")` if the file might not exist.

## Next step

Pass the result to `/lmfdb-object-to-magma` to restore the native Magma object, or use `/textfile-to-magma` for the full pipeline.
