---
name: magma-to-lmfdb-object
description: Convert a native Magma object (CliffOrd, GrpPSL2Cliff, Gamma0, etc.) into its LMFDB wrapper type. Use this skill whenever the user wants to wrap a Magma object for serialization, asks "how do I create an LMFDB object", wants to set timing, or needs to populate LMFDB attributes from a live computation.
---

# magma-to-lmfdb-object

**Purpose:** Wrap a native Magma object in its LMFDB type so it can be serialized.

## Key intrinsic

```magma
create_lmfdb_object(X)                   // CliffOrd → LMFDBCliffOrd
create_lmfdb_object(PSL2O)               // GrpPSL2Cliff → LMFDBGrpSL2Cliff
create_lmfdb_object(SL2O, alpha)         // Gamma0 → LMFDBGrpSL2CliffGamma0
create_lmfdb_object(MS, beta)            // ModSymCliff + matrix → LMFDBHeckeMatrices
create_lmfdb_conj_intersection(SL2O, sigma_label, PSigma, alpha, CI_grp)
                                         // → LMFDBConjugateIntersection
```

All `create_lmfdb_object` variants accept an optional `timing` keyword (default `" "`):
```magma
T0 := Cputime();
X  := create_lmfdb_object(O: timing := Sprintf("%o", Cputime(T0)));
```

## Minimal example

```magma
O     := load_clifford_orders(cl)[1];
X     := create_lmfdb_object(O);        // LMFDBCliffOrd
Y     := create_lmfdb_object(PSL2O);    // LMFDBGrpSL2Cliff
alpha := levels(PSL2O)[1];
Z     := create_lmfdb_object(PSL2O, alpha); // LMFDBGrpSL2CliffGamma0
```

## What gets populated

Attributes are filled from the live Magma object — label, generators, relations, abelianization, coset representatives, etc. The full attribute list for each type is stored in the `*_ATTRS` constant in `package-LMFDB.mag` (always sorted alphabetically).

## Edge cases

- `create_lmfdb_object(SL2O, alpha)` requires that `SL2O\`gamma0fp_dict[alpha]` is already computed (i.e., `Gamma0_fp(SL2O, alpha)` has been called).
- Timing defaults to `" "` (a space, not empty) because an empty string fails to register.
- See `/magma/package-LMFDB.mag` for all `create_lmfdb_object` overloads.

## Next step

Pass the result to `/lmfdb-object-to-string` or `/lmfdb-object-to-textfile`.
