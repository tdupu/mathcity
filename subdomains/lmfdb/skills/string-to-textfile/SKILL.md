---
name: string-to-textfile
description: Write a pipe-delimited LMFDB string to the correct data file on disk. Use whenever the user wants to persist a serialized LMFDB string, asks "how do I write this string to DATA/", needs to understand file paths or overwrite behavior, or is building a make script.
---

# string-to-textfile

**Purpose:** Given an LMFDB string, find the right file path and write it to disk.

## Step 1 — Find the path

```magma
// Orders (one file per algebra, many lines)
path := get_lmfdb_clifford_order_path(cl);     // DATA/orders/2.1

// SL2 groups (one file per algebra, many lines)
path := get_lmfdb_sl2_path(cl);                // DATA/sl2/2.1

// Gamma0 (v2: one file per object)
path := get_lmfdb_gamma0_path2(SL2O, alpha);   // DATA/gamma0/<order_label>/<gamma0_label>

// Hecke (one file per Gamma0)
path := get_lmfdb_hecke_path(MS, beta);        // DATA/gamma0_hecke/<order_label>/<gamma0_label>

// Conjugate intersection (one file per CI)
path := get_lmfdb_conj_intersection_path(X);   // DATA/conj_intersection/<order>/<sigma>/<alpha>
```

## Step 2 — Write to disk

```magma
print_file(path, data);                        // append if exists
print_file(path, data: overwrite := true);     // replace file
```

`print_file` creates the directory if needed (`mkdir -p`), touches the file, then calls `PrintFile`. If `overwrite := true`, the old file is `rm`-ed first.

## Storage conventions

| Type | Path | Lines per file |
|---|---|---|
| `LMFDBCliffOrd` | `DATA/orders/<alg_label>` | many (one per order) |
| `LMFDBGrpSL2Cliff` | `DATA/sl2/<alg_label>` | many (one per group) |
| `LMFDBGrpSL2CliffGamma0` (v2) | `DATA/gamma0/<order_label>/<gamma0_label>` | 1 |
| `LMFDBHeckeMatrices` | `DATA/gamma0_hecke/<order_label>/<gamma0_label>` | 1 |
| `LMFDBConjugateIntersection` | `DATA/conj_intersection/<order>/<sigma>/<alpha>` | 1 |

## Edge cases

- For multi-line files (orders, sl2), `overwrite := false` appends a new line; to replace a specific entry you must rewrite the whole file.
- `SetLMFDBRootFolder(".")` must be called before any path intrinsic.
- `SetColumns(0)` is called inside path intrinsics to avoid line wrapping in paths.
