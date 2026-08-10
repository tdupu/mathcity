# Schema Table Template

Copy and fill in this template when adding a new section to `magma/schema.md`.

---

## <Type Display Name>

The Magma type is `LMFDBXXX`. <One-sentence description of what it represents.>
Stored in `DATA/<type_dir>/<order_label>/<entry_label>` (one file per entry)
OR `DATA/<type_dir>/<order_label>` (one file per order, entries appended line by line).

| Column        | Type    | Example                        | Notes                                                              |
| ------------- | ------- | ------------------------------ | ------------------------------------------------------------------ |
| attr1         | text    | `"2.1.m4.1.2.1.1.2.1.1"`      | <description>                                                      |
| attr2         | integer | `6`                            | <description>                                                      |
| attr3         | jsonb   | `[[1, -2, 3], ...]`           | <description; for jsonb, give the nested structure>                |
| label         | text    | `"2.1.m4.1.2.1.1.2.1.1.AbCdE"` | `<label scheme formula>`                                          |
| timing        | text    | `"3.14"`                       | CPU time in seconds; `" "` if not recorded                        |

**Label scheme:** `<order_label>.<hash>` where `<order_label>` is the 11-component
LMFDB order label and `<hash>` is the base-62 hash of <defining object>.

**Notes:** <Any caveats, partially implemented columns, or planned future changes.>

---

## Label component counts (for reference)

| Object                    | Dot-components | Example                                      |
|---------------------------|---------------|----------------------------------------------|
| Clifford algebra          | 2             | `2.1`                                        |
| Order (LMFDB, current)    | 11            | `2.1.m4.1.2.1.1.2.1.1`                      |
| Order (legacy-01, deprecated) | 4         | `2.1.m4.vtir6` — do not use for new types    |
| Gamma0 (SNF label)        | 13            | `2.1.m4.1.2.1.1.2.1.1.12.4`                 |
| Subgroup (full label)     | 14            | `2.1.m4.1.2.1.1.2.1.1.6.2e3-1.a`            |
| CI label                  | 15            | `2.1.m4.1.2.1.1.2.1.1.6.2e3-1.a.XyZ12`      |
