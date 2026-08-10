---
name: textfile-to-magma
description: Restore a native Magma object directly from DATA/ in one pipeline. Use whenever the user wants to load a cached Magma object from disk, asks "how do I restore a CliffOrd / GrpPSL2Cliff / Gamma0 from file", or needs the full textfile-to-lmfdb-object + lmfdb-object-to-magma pipeline.
---

# textfile-to-magma

**Purpose:** Read from DATA/, deserialize through the LMFDB layer, and return the live Magma object. This is `/textfile-to-lmfdb-object` followed by `/lmfdb-object-to-magma`.

## High-level load intrinsics (preferred)

```magma
SetLMFDBRootFolder(".");

// CliffOrd — load a single order directly by its LMFDB label
O := clifford_order(label);                  // → CliffOrd  (e.g. "3.1_a.m1600.160.80.1.100.10.1.1")

// CliffOrd — load all maximal orders for a Clifford algebra
ords  := load_clifford_orders(cl);           // → SetIndx[CliffOrd]

// GrpPSL2Cliff — load from label (reads DATA/orders/ and DATA/sl2/)
PSL2O := clifford_bianchi_group(label);      // → GrpPSL2Cliff
PSL2O := load_clifford_bianchi_group(O);     // convenience: label = get_label(O)

// GrpFP (Gamma0) — fast single-entry load by full LMFDB gamma0 label (preferred)
// Label format: <order_label>.<pdet>.<index>  e.g. "3.1_2.m64.32.16.1.4.2.1.1.12.5"
// File lives at DATA/gamma0/<order_label>/<gamma0_label>
gamma0, map, gens := load_Gamma0_fp_from_label(SL2O, gamma0_label);

// GrpFP (Gamma0) — load by matrix (fast, if you already have the AlgMatElt)
gamma0, map, gens := load_Gamma0_fp(SL2O, alpha);

// GrpFP (Gamma0) — load and cache ALL Gamma0s for the order, return one by label (SLOW)
gamma0, map := Gamma0_fp(SL2O, alpha_label); // reads the full gamma0 file before returning

// Hecke matrices — populate MS`hecke_matrices_tf
hecke_dict := load_hecke_matrices_tf(MS, beta);

// LMFDBCBMFGamma0Eigenform — load one file or all files for an order
ef  := read_lmfdb_cbmf_gamma0_eigenform(path);       // → LMFDBCBMFGamma0Eigenform
efs := read_lmfdb_cbmf_gamma0_eigenforms(SL2O);      // → SetIndx[LMFDBCBMFGamma0Eigenform]

// LMFDBCBMFSubEigenform — load one file or all files for an order
ef  := read_lmfdb_cbmf_sub_eigenform(path);           // → LMFDBCBMFSubEigenform
efs := read_lmfdb_cbmf_sub_eigenforms(SL2O);          // → SetIndx[LMFDBCBMFSubEigenform]
```

## Manual pipeline

```magma
// Step 1: textfile-to-lmfdb-object
lmfdb_obj := read_lmfdb_clifford_orders(cl)[1];

// Step 2: lmfdb-object-to-magma
O := clifford_order(lmfdb_obj);
```

## Typical script pattern

```magma
Z := Integers(); Q := Rationals();
AttachSpec("hecke.spec");
SetLMFDBRootFolder(".");
cl    := clifford_algebra(Q, [-1]);
O     := load_clifford_orders(cl)[1];
PSL2O := load_clifford_bianchi_group(O);
alpha := levels(PSL2O)[10];
gamma0, map := load_Gamma0_fp(PSL2O, alpha);
```

## Edge cases

- `clifford_order(label)` is the **direct** loader by full order label (`package-LMFDB.mag:2734`) — prefer this over `load_clifford_orders(cl)` + label filter when you already know the label.
- `load_clifford_orders(cl)` returns a `SetIndx` — index with `[1]`, `[2]`, etc.
- **Single-entry-by-label fast path:** Use `load_Gamma0_fp_from_label(SL2O, gamma0_label)`. The full LMFDB gamma0 label (`<order_label>.<pdet>.<index>`) is the filename under `DATA/gamma0/<order_label>/`. The intrinsic builds the path, reads the single file, coerces `defining_element` (`dejsonify_matrix` returns `GrpMatElt` — coercion via `M2 ! [D_grp[i][j] ...]` is handled internally), and delegates to `load_Gamma0_fp`.
- `Gamma0_fp(SL2O, alpha_label)` loads **all** Gamma0 entries for the order (reads full file, breaks early on first match) and caches them in `SL2O\`gamma0fp_dict`. Slow on large gamma0 files.
- `clifford_bianchi_group(label)` requires DATA/orders/ and DATA/sl2/ to both exist.
- `SetLMFDBRootFolder` must be called before any read; the root should be the repo root (the parent of DATA/).
- After `load_Gamma0_fp`, access cached data via `SL2O\`gamma0fp_dict[alpha]` = `<gamma0, inclusion, gens>`.
- `read_lmfdb_cbmf_gamma0_eigenform(path)` reads a single file by absolute path; `read_lmfdb_cbmf_gamma0_eigenforms(SL2O)` scans `DATA/cbmf_gamma0_eigenforms/<order_label>/` and returns all files as a `SetIndx`.
- `read_lmfdb_cbmf_sub_eigenform(path)` / `read_lmfdb_cbmf_sub_eigenforms(SL2O)` — same pattern for sub-eigenforms under `DATA/cbmf_sub_eigenforms/<order_label>/`.

## File format note — orders/

`write_textfile("LMFDBCliffOrd", X)` writes to `DATA/orders/<X`label>` where `X`label` is the **full LMFDB order label** (e.g., `3.1_1.m64.1.2.1.4.2.1.1`), not the algebra label (`3.1_1`).

`read_lmfdb_clifford_orders(cl)` constructs the path `DATA/orders/<algebra_label>` and reads it. If no single file exists at that path (new per-order format), it falls back to listing all files in `DATA/orders/` that start with `<algebra_label>` as a prefix. Both formats are handled transparently.
