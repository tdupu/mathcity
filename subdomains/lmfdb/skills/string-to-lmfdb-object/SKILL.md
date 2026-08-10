---
name: string-to-lmfdb-object
description: Restore an LMFDB wrapper object from a pipe-delimited string. Use whenever the user has a raw data string and wants the LMFDB object back, asks "how do I deserialize this line", is implementing a load function, or is composing the string-to-magma pipeline.
---

# string-to-lmfdb-object

**Purpose:** Parse a pipe-delimited LMFDB string into the appropriate LMFDB wrapper type.

## Key intrinsics

```magma
X := load_lmfdb_clifford_order(line)      // → LMFDBCliffOrd
X := load_lmfdb_sl2(line)                 // → LMFDBGrpSL2Cliff
X := load_lmfdb_gamma0(line)              // → LMFDBGrpSL2CliffGamma0
X := load_lmfdb_hecke_matrices(line)      // → LMFDBHeckeMatrices
X := load_lmfdb_conj_intersection(line)   // → LMFDBConjugateIntersection
```

All take an optional `sep` parameter (default `"|"`).

## How it works internally

```
Split(line, "|": IncludeEmpty := true)  → data[i] for each attribute
LoadAttr(attr, data[i], X)              → typed Magma value via LoadJsonb / LoadBool / etc.
\N                                      → None()
```

Attributes are loaded in the same alphabetical order they were saved (`*_ATTRS`).

## Minimal example

```magma
lines := [H : H in Split(Read(path), "\n") | #H gt 0];
lmfdb_ords := [load_lmfdb_clifford_order(l) : l in lines];
```

## Higher-level read_lmfdb_* wrappers

These combine `/textfile-to-string` + `/string-to-lmfdb-object` in one call:

```magma
read_lmfdb_clifford_orders(cl)        // → SetIndx of LMFDBCliffOrd
read_lmfdb_sl2(cl)                    // → SetIndx of LMFDBGrpSL2Cliff
read_lmfdb_gamma0(O)                  // → SetIndx of LMFDBGrpSL2CliffGamma0
read_lmfdb_gamma02(SL2O, alpha)       // → single LMFDBGrpSL2CliffGamma0 (v2 per-file)
read_lmfdb_conj_intersection(fname)   // → LMFDBConjugateIntersection
```

## Edge cases

- `load_lmfdb_sl2` restores `matrix_to_fpgroup` as a `List`, not `SeqEnum[Tup]`. Comparing two `LMFDBGrpSL2Cliff` objects with `eq` will error — see bug #161.
- `IncludeEmpty := true` is essential for `Split` so that `\N` (null) fields are not skipped.
- Error if `#data ne #attrs` — means the line has wrong column count (schema mismatch).
