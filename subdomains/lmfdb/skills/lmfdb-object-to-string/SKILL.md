---
name: lmfdb-object-to-string
description: Serialize an LMFDB wrapper object (or list of objects) to a pipe-delimited string. Use whenever the user wants to convert an LMFDB object to its text representation, asks "how do I get the string for an LMFDB object", needs to inspect the serialized form, or is about to write data to disk.
---

# lmfdb-object-to-string

**Purpose:** Convert an LMFDB object into the pipe-delimited string that goes on one line of a data file.

## Key intrinsic

```magma
s := SaveLMFDBObject(X);          // Any LMFDB type → MonStgElt
s := SaveLMFDBObject(X: sep:="|"); // explicit separator (default is |)
```

Attributes are saved in **alphabetical order** (matching the `*_ATTRS` constant). Each field is encoded by `SaveAttr`/`SaveJsonb`:

| Magma type | Encoding |
|---|---|
| `BoolElt` | `"t"` / `"f"` |
| `RngIntElt` | decimal string |
| `SeqEnum`, `List`, `Tup` | JSON array via `SaveJsonb` |
| `MonStgElt` (text col) | raw string |
| `NoneType` | `\N` |

## Minimal example

```magma
X := create_lmfdb_object(O);
s := SaveLMFDBObject(X);
s;  // "[[[1,0],1],...]|[[1]]|2|-4|t|t|t|2.1.m4.1W6TEV| "
```

## For a list of objects

```magma
lines := [SaveLMFDBObject(x) : x in lmfdb_list];
data  := Join(lines, "\n");
```

## Edge cases

- The final field (usually `timing`) is often `" "` (a space), making the string end with `| `. This is intentional — empty string would register as missing.
- `DefaultAttributes(Type(X))` returns the sorted attribute list used by `SaveLMFDBObject`; you can override with the `attrs` parameter.
- Column types (`TextCols`, `IntegerCols`, `BoolCols`, `JsonbCols`, etc.) are defined in `package-IO.mag` — add new attributes there when extending a type.

## Next step

Pass the string to `/string-to-textfile` or use directly in `/lmfdb-object-to-textfile`.
