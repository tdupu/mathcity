---
name: search-lmfdb
description: Query the LMFDB (L-functions and Modular Forms Database) via its MCP server. Use this skill whenever the user asks about LMFDB data, wants to look up Bianchi modular forms, elliptic curves, number fields, L-functions, or any other mathematical objects stored in the LMFDB. Also use it when the user wants to cross-reference computed data against LMFDB entries, check eigenvalues, verify labels, or explore what data is available for a given mathematical object. Trigger on phrases like "check the LMFDB", "look up in LMFDB", "what does LMFDB say about", "compare with LMFDB", "search for forms", "eigenvalues from LMFDB", or any request to query mathematical databases.
---

# LMFDB Query Skill

The LMFDB MCP server gives read-only SQL access to the LMFDB's PostgreSQL devmirror. Tools are available as `mcp__lmfdb__*`.

## Dependency check

The lmfdb MCP server must be connected. Verify with `claude mcp list` — should show `lmfdb: ✓ Connected`.

If the `mcp__lmfdb__overview` tool is not available in this session:

```
I'm sorry, I can't do that — the lmfdb MCP server is not connected.
Configure it once with: claude mcp add --transport http lmfdb https://mcp.lmfdb.org/mcp
Then restart your Claude Code session.
```

## Prerequisites

The MCP must be configured. If tools aren't available, run once per project:
```bash
claude mcp add --transport http lmfdb https://mcp.lmfdb.org/mcp
```
Then restart the session. Verify with `claude mcp list` — should show `lmfdb: ✓ Connected`.

## Available tools

| Tool | Purpose |
|------|---------|
| `mcp__lmfdb__overview` | Curated map of all table groups — start here |
| `mcp__lmfdb__list_tables` | List all table names |
| `mcp__lmfdb__describe_table(name)` | Schema + column descriptions for a table |
| `mcp__lmfdb__search_knowls(keywords)` | Search documentation for a concept or column name |
| `mcp__lmfdb__sample_rows(table, n)` | Sample rows without writing SQL |
| `mcp__lmfdb__run_sql(sql)` | Arbitrary SELECT (max 100k rows, 120s timeout) |
| `mcp__lmfdb__count_rows(table, where)` | Fast count with optional filter |
| `mcp__lmfdb__table_stats(table)` | Row count + index info |
| `mcp__lmfdb__export_query(sql, format)` | Bulk download via URL (bypasses 100k row cap) |

## Standard workflow

1. **`overview()`** — identify the right table group for the question
2. **`describe_table(name)`** — confirm columns and types before writing SQL
3. **`run_sql(sql)`** — targeted query with WHERE clauses; avoid full-table scans

For column discovery when `describe_table` isn't enough: `search_knowls("frobenius traces")` or similar.

## Table naming conventions

Prefix indicates the mathematical area:

| Prefix | Area |
|--------|------|
| `bmf_` | Bianchi modular forms (over imaginary quadratic fields) |
| `mf_` | Classical modular forms |
| `ec_` | Elliptic curves over Q |
| `g2c_` | Genus 2 curves |
| `nf_` | Number fields |
| `gps_` | Groups (abstract, Galois, etc.) |
| `lfunc_` | L-functions |
| `artin_` | Artin representations |
| `av_fq_` | Abelian varieties over finite fields |

`_counts` and `_stats` siblings of each table are metadata tables — don't query them for mathematical data.

## Key tables for Clifford-Bianchi work

### `bmf_forms` — Bianchi modular newforms

Columns relevant to us:
- `field_disc` (smallint): discriminant of the imaginary quadratic field. Q(i) = −4, Q(√−3) = −3, Q(√−7) = −7, etc.
- `field_label` (text): LMFDB field label, e.g. `2.0.4.1` for Q(i)
- `level_norm` (bigint): norm of the level ideal — corresponds to `pdet` in our gamma0 label scheme
- `level_label` (text): e.g. `65.2` (norm 65, second ideal class of that norm)
- `level_ideal` (text): generator of the level ideal, e.g. `(4+7i)`
- `level_gen` (text): same generator without parentheses
- `label` (text): full LMFDB label, e.g. `2.0.4.1-65.2-a`
- `dimension` (smallint): dimension of the Hecke eigenspace (= 1 for rational forms)
- `bc` (smallint): 0 = not base change, 1 = base change from a classical form
- `hecke_eigs` (jsonb): list of Hecke eigenvalues, ordered by rational prime then ideal

Useful filters:
- `WHERE field_disc = -4` — Q(i) / Gaussian integers
- `WHERE field_disc = -3` — Q(√−3) / Eisenstein integers
- `AND bc = 0` — exclude base-change forms (usually what you want)

### `bmf_dims` — dimension table by level

- `field_absdisc` (integer): absolute value of discriminant (use 4 for Q(i), 3 for Q(√−3))
- `level_norm`, `level_label` — same as `bmf_forms`
- `sl2_new_totaldim` — total dimension of the SL₂ newspace at this level and weight
- `gl2_new_totaldim` — same for GL₂
- `sl2_cusp_totaldim` — total cusp space dimension (includes oldforms)

## Eigenvalue comparison pattern

When cross-referencing our computed cbmf eigenforms against LMFDB data:

**Step 1**: Identify the level norm. Our gamma0 label `2.1.4.1.65.1` has `pdet=65` → `level_norm=65` in LMFDB.

**Step 2**: Pull LMFDB eigenvalues for that level:
```sql
SELECT label, level_label, level_ideal, dimension, bc,
       hecke_eigs
FROM bmf_forms
WHERE field_disc = -4 AND level_norm = 65 AND bc = 0
ORDER BY label
```

**Step 3**: Check that our homological_rank (from `make-gamma0-ranks`) sums correctly. For each distinct `level_norm`, the LMFDB's `sl2_new_totaldim` in `bmf_dims` should match the total eigenspace dimension our computation produces across all gamma0 subgroups at that pdet.

**Step 4**: Compare eigenvalue sequences. Our `hecke_eigs` (once stored in DATA/) is indexed by prime ideals in the order; the LMFDB's `hecke_eigs` list is ordered by rational prime p (smallest first), then by the two ideals above p in the split case. The first few entries correspond to p=2,3,5,... — match against our eigenvalues for the same primes.

**Note on Galois conjugates**: Two LMFDB forms at the same `level_label` but different `level_ideal` (e.g., `(4+7i)` vs `(7+4i)`) are Galois conjugates under the automorphism of the imaginary quadratic field. Our gamma0 computation naturally produces both — label alignment uses `level_ideal` (compare the generator with the `alpha` matrix entry).

## Performance notes

- Some tables have hundreds of millions of rows. Always use `WHERE field_disc = X` or `WHERE level_norm < Y` to avoid full scans.
- For eigenvalue bulk downloads (many levels), use `export_query` instead of repeated `run_sql` calls.
- `bmf_forms` is indexed on `field_disc`, `level_norm`, `label` — these make fast WHERE clauses. Avoid filtering on `hecke_eigs` content (not indexed).

## Example queries

**Count forms by field and level range:**
```sql
SELECT field_disc, COUNT(*) as n_forms, MIN(level_norm), MAX(level_norm)
FROM bmf_forms
WHERE field_disc IN (-4, -3, -7)
GROUP BY field_disc ORDER BY field_disc DESC
```

**All non-BC forms at a specific level norm:**
```sql
SELECT label, level_label, level_ideal, dimension, hecke_eigs
FROM bmf_forms
WHERE field_disc = -4 AND level_norm = 65 AND bc = 0
```

**Total new dimension vs level norm for Q(i):**
```sql
SELECT level_norm, SUM(sl2_new_totaldim) as total_dim
FROM bmf_dims
WHERE field_absdisc = 4
GROUP BY level_norm ORDER BY level_norm LIMIT 30
```

**Find levels where dim > 1 (multi-dimensional eigenspaces):**
```sql
SELECT level_norm, level_label, COUNT(*) as n_forms, SUM(dimension) as total_dim
FROM bmf_forms
WHERE field_disc = -4 AND bc = 0 AND dimension > 1
GROUP BY level_norm, level_label ORDER BY level_norm LIMIT 20
```
