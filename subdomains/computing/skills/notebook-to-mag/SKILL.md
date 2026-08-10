---
name: notebook-to-mag
description: Pull fixes and new code from a modified Jupyter notebook back into a versioned .mag file with an incremented index, then git add it. Use this skill whenever the user says "notebook to mag", "pull from notebook", "save the notebook as a mag file", "increment the mag", or has been iterating in Jupyter and wants to checkpoint their work as a tracked .mag file. This is the return leg of the mag-to-notebook → edit in Jupyter → notebook-to-mag iteration cycle.
---

# notebook-to-mag

Extract all cell code from a modified `.ipynb` notebook, write it as a new `.mag` file with an incremented index, and `git add` it.

## When to use

The user has been iterating on code in Jupyter (fixing bugs, adding cells, modifying logic) and wants to save that work as the next versioned `.mag` file in the sequence.

## Steps

### 1. Identify the source notebook

If the user named a file, use that. Otherwise infer from context — the notebook corresponding to the `.mag` file most recently discussed, or the most recently modified `.ipynb` in `magma/test/`.

### 2. Parse the notebook

Read the `.ipynb` JSON and extract source from every code cell in order:

```python
import json

with open(notebook_path) as f:
    nb = json.load(f)

cell_sources = []
for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        src = "".join(cell["source"])
        if src.strip():   # skip empty cells
            cell_sources.append(src)
```

### 3. Determine the new filename

Parse the index from the source notebook's name:

- Pattern: `<stem>-<NN>.ipynb` where `<NN>` is a zero-padded integer (e.g., `test-snf-bug-03.ipynb` → index 3)
- New index = old index + 1, zero-padded to same width (e.g., 3 → `04`)
- New filename: `<stem>-<NN+1>.mag` in the same directory

Examples:
- `test-snf-bug-03.ipynb` → `test-snf-bug-04.mag`
- `test-canonicalization-01.ipynb` → `test-canonicalization-02.mag`

If the filename doesn't match `<stem>-<NN>` exactly, ask the user what the output filename should be.

### 4. Assemble the .mag file

Join the cell sources with a blank line between each:

```python
mag_content = "\n\n".join(cell_sources) + "\n"
```

Do not add any extra headers, comments, or metadata — the cell content is the full file. The user controls what goes in each cell.

### 5. Write the .mag file

Write to the new path. If the file already exists, stop and ask the user before overwriting.

### 6. git add

```bash
git add <new-mag-path>
```

Run from the repo root (not `magma/test/`). Confirm the file was staged.

### 7. Report

Tell the user:
- The new `.mag` filename
- How many cells were merged
- That the file is staged (`git add`ed) — they can commit when ready with `/claude-commit`

## Notes

- The notebook may contain experimental or incomplete cells the user left at the bottom. Include them — the user put them there intentionally. If they're clearly scratch/debug cells the user wants excluded, they'll tell you.
- Cell outputs (stdout from prior runs) are in `cell["outputs"]` — ignore those entirely. Only `cell["source"]` matters.
- The new `.mag` file should be runnable as-is with `magma <file>` from `magma/test/`. If the notebook cells use relative paths like `"../<project>.spec"` they're already correct for that directory.
- This skill does not commit — it only stages. Use `/claude-commit` for the full commit-pull-push cycle.
