---
name: magma-to-textfile
description: Serialize a raw Magma object (CliffOrd, GrpPSL2Cliff, etc.) all the way to disk in one pipeline. Use whenever the user wants to cache a computed Magma object, is writing a make script, asks "how do I save this object to DATA/", or wants the full magma-to-lmfdb-object → lmfdb-object-to-string → string-to-textfile pipeline.
---

# magma-to-textfile

**Purpose:** Take a live Magma object and persist it to DATA/ in one pipeline. Composes `/magma-to-lmfdb-object` → `/lmfdb-object-to-string` → `/string-to-textfile`.

## Shortcut intrinsics (preferred when available)

```magma
write_lmfdb_clifford_order(O: timing := T1)          // CliffOrd → DATA/orders/
write_lmfdb_sl2(PSL2O: timing := T1)                 // GrpPSL2Cliff → DATA/sl2/
write_lmfdb_gamma0(SL2O, beta: do_over := false)     // computes + saves Gamma0
write_lmfdb_hecke(MS, alpha: timing := T1)           // ModSymCliff → DATA/gamma0_hecke/
write_lmfdb_conj_intersection(X)                     // LMFDBConjugateIntersection → DATA/conj_intersection/
write_lmfdb_cbmf_gamma0_eigenform(ef : overwrite := false)  // LMFDBCBMFGamma0Eigenform → DATA/cbmf_gamma0_eigenforms/
write_lmfdb_cbmf_sub_eigenform(ef : overwrite := false)     // LMFDBCBMFSubEigenform → DATA/cbmf_sub_eigenforms/
```

`write_lmfdb_gamma0(SL2O, beta)` is the recommended pattern for Gamma0 — it checks existing labels to avoid duplicates, computes if missing, and saves.

For eigenforms, `write_lmfdb_cbmf_gamma0_eigenform` and `write_lmfdb_cbmf_sub_eigenform` write to `DATA/cbmf_{gamma0,sub}_eigenforms/<order_label>/`. Use `overwrite := true` when re-running a make script that may have produced stale files.

## Manual pipeline (for types without a shortcut)

```magma
T0  := Cputime();
X   := create_lmfdb_object(my_obj: timing := Sprintf("%o", Cputime(T0)));
s   := SaveLMFDBObject(X);
path := get_lmfdb_<type>_path(...);
print_file(path, s: overwrite := false);
```

## Typical make-script pattern

```magma
Z := Integers(); Q := Rationals();
AttachSpec("hecke.spec");
SetLMFDBRootFolder(".");
cl    := clifford_algebra(Q, [-1]);
T0    := Cputime();
ords  := maximal_orders(cl);
T1    := Sprintf("%o", Cputime(T0));
write_lmfdb_clifford_orders(cl, ords: timing := T1);
```

## Edge cases

- Always record CPU time with `Cputime()` before and after the expensive computation; pass the delta as `timing`.
- For Gamma0, prefer `write_lmfdb_gamma0(SL2O, beta)` over the manual pipeline — it deduplicates by label.
- `overwrite := true` is needed when recomputing an object that was previously written.
- `SetLMFDBRootFolder` must be called before any write.
