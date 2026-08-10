---
name: check-labels-and-refs
description: Scan LaTeX files for label/reference consistency, orphan labels/refs, and non-pinpoint cross-references
status: PRELIMINARY (DRY-RUN ONLY)
---

# Check LaTeX Labels and References

Scans LaTeX documents for `\label{}`, `\ref{}`, `\eqref{}`, `\autoref{}` patterns to identify:
- **Orphan labels**: Labels defined but never referenced
- **Orphan refs**: References to undefined labels
- **Non-pinpoint refs**: Bare text references (e.g., "see Section 2" instead of `\ref{sec:foo}`)

Handles `\input` and `\include` closure up to depth 2.

## Usage

```bash
check-labels-and-refs <tex-file-path> [output-dir]
```

### Arguments
- `<tex-file-path>` — Root LaTeX file to scan (required)
- `[output-dir]` — Output directory for JSON report (optional, defaults to <city-root>/tmp-for-review/)

### Output

Produces `check-labels-and-refs-report.json` with structure:

```json
{
  "file": "<path-to-root-file>",
  "sha": "<git-sha-of-file>",
  "scan_depth": 2,
  "verdict": "PASS|FAIL",
  "labels": {
    "<label-name>": {
      "location": "<file>:<line>",
      "referenced_from": ["<file>:<line>", ...]
    }
  },
  "references": {
    "<label-name>": {
      "locations": ["<file>:<line>", ...],
      "label_found": true|false,
      "reference_type": "ref|eqref|autoref"
    }
  },
  "orphan_labels": ["<label-name>", ...],
  "orphan_refs": ["<label-name>", ...],
  "non_pinpoint_refs": [
    {
      "file": "<file>",
      "line": <line-number>,
      "context": "<quoted-text>",
      "pattern": "bare-section|bare-theorem|bare-equation"
    }
  ],
  "counts": {
    "total_labels": <int>,
    "total_refs": <int>,
    "orphan_label_count": <int>,
    "orphan_ref_count": <int>,
    "non_pinpoint_count": <int>
  }
}
```

## Implementation

The skill uses bash/grep to scan LaTeX files. For each `.tex` file:

1. **Collect labels**: Extract all `\label{<name>}` patterns
2. **Collect references**: Extract all `\ref{<name>}`, `\eqref{<name>}`, `\autoref{<name>}` patterns
3. **Cross-reference**: Match refs to labels
4. **Detect orphans**: Find labels with no refs and refs with no labels
5. **Detect non-pinpoint**: Grep for bare-text patterns like "Section \d+", "Theorem \d+", "Equation \d+"
6. **Handle closure**: Recursively scan `\input{<file>}` and `\include{<file>}` up to depth 2

## Limitations

- **Depth cap**: Only scans `\input`/`\include` to depth 2. References to depth-3+ files are silently ignored. Report header documents this cap.
- **Comments**: Does not skip LaTeX comments (`%...`), so commented-out `\label{}`/`\ref{}` may be incorrectly counted.
- **\cite{}**: Does NOT scan citation patterns (`\cite{}`). That is the domain of check-citations skill.
- **Macros**: Does not expand LaTeX macros, so references inside macro expansions may be missed.
- **Non-ASCII**: Assumes UTF-8 encoding.

## Notes

- Non-pinpoint detection ships with examples only in v0. FP-converge refines enumeration.
- Verdict = FAIL if any-of: orphan_label_count > 0, orphan_ref_count > 0, non_pinpoint_count > 0.
- Cross-ref-parity-depth-2 is union of three detectors: orphan-label + orphan-ref + non-pinpoint.

---

## Examples

### Example 1: Hyperboloid.tex Test

```bash
ROOT=$HOME/gt/.gc/worktrees/hecke/polecats/gc.run-operator/worktrees/he-d4l
check-labels-and-refs $ROOT/latex/notes/hyperboloid.tex <city-root>/tmp-for-review/he-ja26/
# Produces: <city-root>/tmp-for-review/he-ja26/check-labels-and-refs-report.json
```

Expected checks:
- Scans hyperboloid.tex + \input closure
- Reports orphan labels (labels without refs)
- Reports orphan refs (refs to undefined labels)
- Flags non-pinpoint patterns
- Verdict: PASS (no orphans or non-pinpoint issues) or FAIL (issues found)
