---
name: textfile-to-string
description: Read raw pipe-delimited LMFDB strings from disk. Use whenever the user wants to load data from DATA/ as strings, asks "how do I read a data file", needs to locate the right file path, or is building a restore/load pipeline.
---

# textfile-to-string

**Purpose:** Locate the right DATA/ file and return the pipe-delimited line(s) as Magma strings. These strings can then be passed to `/string-to-lmfdb-object`.

## Step 1 — Find the path

```magma
SetLMFDBRootFolder(".");
path := get_lmfdb_clifford_order_path(cl);          // DATA/orders/2.1
path := get_lmfdb_sl2_path(cl);                     // DATA/sl2/2.1
path := get_lmfdb_gamma0_path2(SL2O, alpha);        // DATA/gamma0/<order>/<gamma0_label>
path := get_lmfdb_hecke_path(MS, beta);             // DATA/gamma0_hecke/<order>/<gamma0_label>
path := get_lmfdb_conj_intersection_path(X);        // DATA/conj_intersection/<order>/<sigma>/<alpha>
```

## Step 2 — Read and split

```magma
// Multi-line files (orders, sl2): one object per line
lines := [H : H in Split(Read(path), "\n") | #H gt 0];

// Single-object files (gamma0 v2, CI, hecke)
lines := [H : H in Split(Read(path), "\n") | #H gt 0];
assert #lines eq 1;
line  := lines[1];
```

## Filter by label (multi-line files)

```magma
target := "2.1.m4.1W6TEV";
matched := [l : l in lines | Split(l, "|")[<label_col_index>] eq target];
```

The label is always the first alphabetical attribute — check `*_ATTRS` for the column index.

## Checking existence before reading

```magma
if OpenTest(path, "r") then
    lines := ...
else
    // file does not exist
end if;
```

## Edge cases

- Empty trailing newlines from `Split` must be filtered (`| #H gt 0`).
- `Read(path)` errors if the file does not exist — guard with `OpenTest`.
- For CI directories (all alphas for a given sigma), use `get_lmfdb_conj_intersection_dir` + `Pipe("ls ...")` to enumerate files.
- `SetColumns(0)` is called inside path intrinsics; call it yourself if building a path manually.
