---
name: notebook-to-package
description: Promote Magma functions from a Jupyter notebook into proper package intrinsics in the appropriate package-*.mag file. Use this skill whenever the user says "promote to package", "move to intrinsic", "notebook to package", "add to package-order", "make this an intrinsic", "package this up", or names specific notebook functions they want to turn into intrinsics. This is the final step after iterating and testing a function in Jupyter.
---

# notebook-to-package

Promote one or more tested `function`/`end function` definitions from a Magma Jupyter notebook into proper `intrinsic`/`end intrinsic` blocks in the correct `package-*.mag` file, then create a test `.mag` file exercising them.

## When to use

The user has been developing and testing Magma functions in a `.ipynb` notebook, they work, and the user now wants them promoted to first-class intrinsics in a package file.

---

## Step 1: Identify inputs

**From the user or conversation context, collect:**

- **Source notebook**: the `.ipynb` file containing the function definitions. Infer from recent discussion if not specified (most recently discussed `.ipynb` in `magma/test/`).
- **Function names to promote**: the user names them explicitly. If not named, ask before proceeding.

---

## Step 2: Read and extract the function definitions

Parse the notebook JSON and search all code cells for the named functions:

```python
import json, re

with open(notebook_path) as f:
    nb = json.load(f)

all_code = "\n".join(
    "".join(cell["source"])
    for cell in nb["cells"]
    if cell["cell_type"] == "code"
)
```

For each target function name `fname`, find its full definition using a pattern like:

```
function fname\(.*?\)[\s\S]*?end function;
```

Extract the parameter list and the body (everything between the opening `\n` after the signature and `end function;`).

---

## Step 3: Convert to intrinsic syntax

Magma intrinsic syntax:

```magma
////////////////////
intrinsic fname(param1::Type1, param2::Type2) -> ReturnType1, ReturnType2
////////////////////
{
One-line description of what this intrinsic computes.
}
    body...
end intrinsic;
```

**Key conversion rules:**

1. **Type annotations**: every parameter must have `::Type`. Infer from usage in the body or nearby code:
   - 2×2 matrices: `AlgMatElt`
   - Clifford orders: `CliffOrd`
   - Clifford order elements: `CliffOrdElt`
   - Clifford algebra elements: `CliffAlgElt`
   - Sequences: `SeqEnum`
   - Integers: `RngIntElt`
   - Rationals/field elements: `FldRatElt`
   - Booleans: `BoolElt`
   - If uncertain, read the package file for how nearby intrinsics annotate similar parameters, then use that convention. Ask the user if still unclear.

2. **Return type**: infer from the function's `return` statements. Multiple returns → `-> T1, T2, ...`. If void → omit `->`.

3. **Docstring**: `{ one-sentence description }` immediately after the signature line (before the body). Write a concise mathematical description — what it computes, not how.

4. **`require` guards**: add these at the top of the body when applicable:
   - `require is_norm_euclidean(O) : "Order O must be norm-Clifford-euclidean.";`
   - `require is_star_invariant(O) : "Order O must be closed under the star involution.";`
   Check whether the existing function body assumes these properties. If yes, add the guards. If the package has a pattern for guards, match it.

5. **Separator style**: surround the `intrinsic` keyword line with `////////////////////` dividers, matching the package file's own style.

6. **Do NOT touch `.sig` files.** Never edit `package-*.sig`. They are auto-generated.

---

## Step 4: Find the insertion point in the package file

Determine which `magma/package-*.mag` file should receive the intrinsic:

- SNF, orders, units, coordinates → `package-order.mag`
- Groups, generators, Farey graph, rotation_matrix → `package-grpcliff.mag`
- Modular symbols, Hecke operators → `package-modular-symbols.mag`
- Clifford algebra arithmetic → `package-cliff.mag`
- When in doubt, read nearby intrinsics in the notebook context to find which package file they live in, then insert in the same file.

**Finding the right line**: search the package file for the most closely related existing intrinsic (e.g., if promoting a canonical SNF function, search for `smith_normal_form`). Insert the new intrinsic immediately after the last related intrinsic's `end intrinsic;` line.

---

## Step 5: Insert the intrinsics

Edit the package file by inserting the converted intrinsic block(s) at the identified insertion point, separated by a blank line from surrounding code.

Read the file first, locate the exact insertion line, and use Edit (not Write) to avoid overwriting the file.

---

## Step 6: Create a test .mag file

Determine the next index for the test file:

- Find existing `test-<stem>-<NN>.mag` files in `magma/test/`
- New index = max existing index + 1, zero-padded to same width

Write `magma/test/test-<stem>-<NN+1>.mag` that:
1. Has the standard preamble:
   ```magma
   Z := Integers();
   Q := Rationals();
   AttachSpec("../hecke.spec");
   SetLMFDBRootFolder("../");
   ```
2. Sets up the necessary algebra/order (e.g., `cl := clifford_algebra(Q, [-1,-1]); O := ...`). Mirror the setup from the source notebook.
3. Calls each new intrinsic with representative inputs — both a simple case and any edge case exercised in the notebook.
4. Prints clear PASS/FAIL lines, ideally using `assert` or explicit comparison with `print "SUCCESS."` / `print "FAIL"`.
5. Matches the testing style of the source notebook (e.g., exhaustive orbit checks, certificate checks).

---

## Step 7: git add

From the repo root:

```bash
git add magma/package-*.mag magma/test/test-<stem>-<NN+1>.mag
```

Do **not** add `.sig` files. Do **not** commit — only stage.

---

## Step 8: Report

Tell the user:
- Which package file was modified and where the intrinsic(s) were inserted
- The new test `.mag` filename and how many intrinsics it tests
- That files are staged — they can commit when ready with `/claude-commit`

---

## Domain knowledge (Hurwitz/Gaussian context)

- `units(O)` returns 4 values: `(clifford_units, all_units, matrix_group, repn_units)`
  - Use `clifford_units` (first return, 24 elements, full binary tetrahedral group, closed under multiplication)
  - `all_units` (20 elements) is **not** closed under multiplication — do not use it as the orbit group
- `rotation_matrix(u::CliffOrdElt)` from `package-grpcliff.mag`: returns `Matrix(2,2,[u_elt, 0, 0, star(u_elt)^(-1)])`; for Hurwitz units this equals `diag(u,u)`
- Type coercion pattern for matrix entries: `O ! (cl ! (E[1][1]))` where `cl := clifford_algebra(O)`
- `cmpeq false` is the Magma idiom to check an uninitialized comparison variable (not `eq false`)
- `get_order_coordinates(x::CliffOrdElt)` returns Z-basis coordinates; use `Eltseq(...)` for lex comparison
- `adj` is a Magma reserved word — never use it as a variable name; use `adjacent` or `nbrs`
