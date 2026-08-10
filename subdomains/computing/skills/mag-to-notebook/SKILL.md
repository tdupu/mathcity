---
name: mag-to-notebook
description: Convert a Magma .mag test/script file into a Jupyter notebook (.ipynb) with a Magma kernel so the user can run and iterate on it interactively. Use this skill whenever the user says "make a notebook", "make an ipynb", "convert to notebook", "I want to test this in Jupyter", or asks for a notebook version of a .mag file. The output notebook is gitignored automatically by magma/test/.gitignore.
---

# mag-to-notebook

Convert a `.mag` file into a Jupyter notebook (`.ipynb`) with a Magma kernel, split into logical cells for interactive iteration.

## When to use

The user has a `.mag` file they want to test interactively in Jupyter. They may explicitly name the file or it may be clear from context (e.g., the most recently discussed `.mag` file).

## Steps

### 1. Identify the source file

If the user named a file, use that. Otherwise infer from context (most recently created/modified `.mag` file in the conversation). Resolve relative to the working directory (`magma/test/` is the default location).

### 2. Read the .mag file

Read the full file. You need to split it into notebook cells.

### 3. Split into cells

The goal is cells that run independently in sequence, with each one doing one coherent thing. Good split points:

- **Section comment blocks** — lines like `// -----------------------------------------------------------------------` followed by description lines signal a new section → start a new cell *before* the comment block
- **Function definitions** — `function ... end function;` blocks → their own cell
- **Natural setup stages** — preamble (`Z, Q, AttachSpec, SetLMFDBRootFolder`) as cell 1; data loading (`load_gamma0_data`, `levels_by_det`) as cell 2; subsequent logic in further cells
- **Test sections** — canonicalization test, exhaustive test → separate cells so the user can run them independently

**CRITICAL — syntactic completeness:** The Magma Jupyter kernel does NOT support open blocks across cell boundaries. Every cell must be syntactically complete on its own. Never split a `for`, `while`, `if`, or `function` block across two cells — the entire block (including its `end for;`/`end while;`/`end if;`/`end function;`) must appear in the same cell. If nested loops span many lines, keep them in one cell even if it is large. After writing each cell, count opens (`for ... do`, `while ... do`, `if ... then`, `function`) and closes (`end for;`, `end while;`, `end if;`, `end function;`) — they must balance within each cell.

When in doubt, err toward fewer, larger cells rather than splitting across block boundaries. Keep the setup preamble (first 4–5 lines) as its own cell so the user can reattach the spec without re-running everything.

### 4. Build the notebook JSON

Use Python to generate the `.ipynb`. Key details:

```python
import json, uuid

def cell(source_lines):
    # Every line gets a trailing \n — including the last (required by Magma kernel)
    src = [l + "\n" for l in source_lines] if source_lines else []
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": str(uuid.uuid4()),
        "metadata": {},
        "outputs": [],
        "source": src
    }

metadata = {
    "kernelspec": {"display_name": "Magma", "language": "magma", "name": "magma"},
    "language_info": {
        "codemirror_mode": "pascal", "file_extension": ".m",
        "mimetype": "text/x-pascal", "name": "magma", "version": "2.29-2\r"
    }
}

nb = {"cells": cells, "metadata": metadata, "nbformat": 4, "nbformat_minor": 5}
with open(output_path, "w") as f:
    json.dump(nb, f, indent=1)
```

### 5. Write the output

Output path: same directory as the `.mag` file, same stem, `.ipynb` extension.  
Example: `magma/test/test-snf-bug-03.mag` → `magma/test/test-snf-bug-03.ipynb`

The file is automatically gitignored by `magma/test/.gitignore` (`*.ipynb`). No need to add it to git.

### 6. Report

Tell the user the notebook path and how many cells were created.

## Notes

- AttachSpec paths use `"../<project>.spec"` (relative, e.g. `"../hecke.spec"`) because notebooks run with the notebook's directory as cwd.
- Do not include blank trailing cells.
- Preserve comments in cell source — they provide context for interactive exploration.
- The user will likely add new cells in Jupyter; use `/notebook-to-mag` to pull those changes back into a `.mag` file.
