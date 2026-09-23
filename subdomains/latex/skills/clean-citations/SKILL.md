---
name: clean-citations
description: >-
  DRY-RUN citation repair skill. Reads check-citations JSON report (or re-runs check internally), then emits PROPOSED PATCH entries in JSON/Markdown under ~/gt/tmp-for-taylor/bead-id/. No real file writes in v0. Companion write-enabled skill (v1) is planned. PRELIMINARY.
---

> **STATUS: PRELIMINARY (DRY-RUN ONLY).** This is a v0 preliminary per `he-cnat`.
> Emits PROPOSED PATCH entries as JSON/Markdown; makes **no real writes** to `.tex`
> or `.bib` files. Writes ONLY under `~/gt/tmp-for-taylor/<bead>/`. No `Edit`/`MultiEdit`/`Bash` writes/`git commit`/`git push`.
> All five safety gates (worktree check, clean baseline, audit log, confirm-ambiguous,
> `notes.tex` guard) are recorded in the proposals header, not enforced with write
> refusals. A write-enabled v1 will enforce them.

# clean-citations

DRY-RUN citation repair skill. Reads the `check-citations` JSON report for a `.tex`
file, inspects each flagged citation, proposes corrected `\cite{}` calls, and emits a
structured proposals file. Nothing is written to the source `.tex` file in v0.

## When to use

Use after `check-citations` has produced its report (or pass the `.tex` path and let
this skill re-run the check internally):

- After `check-citations` flagged `bib_match: false` or `non_pinpoint: true` entries
  and you want proposed corrections before committing to in-place writes.
- When a human or agent wants to review proposed changes before applying them.
- As a pre-flight step before running the write-enabled v1 (once available).

## Workflow

1. **Locate the `check-citations` report** — look for
   `~/gt/tmp-for-taylor/<bead>/check-citations-report.json`. If not found (or if the
   caller passes a `.tex` path directly), re-run `check-citations` internally first.

2. **Inspect the report header — record safety context** — Check the following conditions
   and write them into the proposals header (no write is gated on these in v0):
   - **Worktree check** (REQ-010): run `git rev-parse --is-inside-work-tree 2>/dev/null`
     from the directory containing the `.tex` file. Record `worktree_status: inside` or
     `worktree_status: outside`.
   - **Clean baseline** (REQ-011): run `git status --short <tex_file>` and record
     `baseline_clean: true` if the output is empty, `false` otherwise. Include the
     uncommitted file list in the header if not clean.
   - **notes.tex on main** (REQ-014): check whether the target filename is `notes.tex`
     and whether the current branch is `main` (or `master`). If both, set
     `safety_gate: BLOCKED` and note `"notes.tex on main — no writes permitted"`.
     In v0 this is a header annotation only; no write is attempted regardless.

3. **For each flagged citation** — iterate over the citations in the report where either
   `bib_match: false` or `non_pinpoint: true`. For each:

   a. **`bib_match: false`** — the `.bib` entry is missing. Propose no textual change
      (cannot invent bibliography data). Set:
      - `issue: "missing_bib_key"`
      - `proposed_after: null`
      - `confidence: low`
      - `safety_gate: MANUAL` (human must add `.bib` entry first)

   b. **`non_pinpoint: true` with `bib_match: true`** — the key exists but the citation
      lacks a pinpoint argument. The skill proposes that the caller add a pinpoint
      argument. Determine `confidence` as follows:

      - Read the `context` field (surrounding text) from the check-citations entry.
      - If the context clearly indicates a single theorem/proposition/definition/remark
        number (e.g. "by Theorem 3.2 in \cite{key}"), set `proposed_after` to
        `\cite[Theorem 3.2]{key}` and `confidence: high`.
      - If the context is ambiguous (mathematical content referenced but no specific
        item extractable from context), set `proposed_after: "\\cite[§SECTION OR THEOREM NUMBER]{key}"`
        (placeholder) and `confidence: borderline`.
      - If no mathematical context is visible within ±3 lines of the `\cite{}` call,
        set `proposed_after: null` and `confidence: low`.

   c. **`non_pinpoint: true` AND `bib_match: false`** — both issues. Set `issue: "both"` (the string literal `"both"`, not an array). Set `proposed_after: null`,
      `confidence: low`, `safety_gate: MANUAL`.

4. **Write the proposals** — create `~/gt/tmp-for-taylor/<bead>/`:
   ```
   clean-citations-proposals.json   — JSON proposals object
   clean-citations-proposals.md     — human-readable Markdown summary
   ```

   **JSON structure:**
   ```json
   {
     "tex_file": "<absolute path>",
     "run_date": "<ISO date>",
     "safety_header": {
       "worktree_status": "inside|outside|unknown",
       "baseline_clean": true,
       "uncommitted_changes": [],
       "notes_tex_on_main": false,
       "safety_gate": "OK|BLOCKED"
     },
     "proposals": [
       {
         "key": "smith1984",
         "issue": "non_pinpoint|missing_bib_key|both",
         "tex_line": 47,
         "before": "\\cite{smith1984}",
         "proposed_after": "\\cite[Theorem 3.1]{smith1984}",
         "confidence": "high|borderline|low",
         "safety_gate": "OK|MANUAL|BLOCKED"
       }
     ],
     "summary": {
       "total_flagged": 3,
       "proposals_high": 1,
       "proposals_borderline": 1,
       "proposals_low_or_null": 1
     }
   }
   ```

   **Markdown format:**
   ```markdown
   # clean-citations proposals

   tex_file: <path>
   worktree_status: inside   baseline_clean: true   safety_gate: OK

   | Line | Key | Issue | Before | Proposed after | Confidence |
   |------|-----|-------|--------|----------------|------------|
   | 47 | smith1984 | non_pinpoint | \cite{smith1984} | \cite[Theorem 3.1]{smith1984} | high |
   ```

5. **Empty / all-clean case** — if the check-citations report has no entries with
   `bib_match: false` or `non_pinpoint: true`, write reports with
   `proposals: []` and summary `"nothing to fix"`.
   Do NOT raise an error.

## Idempotence (REQ-016)

In v0 (proposals mode), idempotence is naturally satisfied: the same check-citations
report input produces the same proposals output. Running the skill twice on the same
source file produces the same proposals JSON.

## Output files

- `~/gt/tmp-for-taylor/<bead>/clean-citations-proposals.json`
- `~/gt/tmp-for-taylor/<bead>/clean-citations-proposals.md`

Use the current bead ID from context as `<bead>`. If no bead is active, use a slug
like `clean-citations-<yyyy-mm-dd>`.

## DRY-RUN constraint

This skill is **entirely non-writing in v0**:
- Use `Read` and `Bash` (read-only: `grep`, `find`, `git status`, `git rev-parse`) only.
- Write ONLY the two proposals files under `~/gt/tmp-for-taylor/<bead>/` via `Write`.
- Never call `Edit`, `MultiEdit`, or write anything to the source `.tex` file.
- Never run `git commit`, `git push`, `git add`, or `git checkout`.
- Never call `bd update` or any bead-mutation command.

## Cross-reference

`check-citations` is the producer of the report this skill consumes. Run it first:

```
/check-citations <path-to-tex>   → produces check-citations-report.json
/clean-citations                  → reads that report, emits clean-citations-proposals.json
```

## Examples

**Non-pinpoint citation with context — high confidence:**
```
check-citations report: {key: "jones2020", bib_match: true, non_pinpoint: true,
  context: "...by Theorem 2.3 in \\cite{jones2020}..."}
→ proposal: {before: "\\cite{jones2020}",
             proposed_after: "\\cite[Theorem 2.3]{jones2020}",
             confidence: "high"}
```

**Ambiguous context — borderline:**
```
context: "...see \\cite{jones2020} for details..."
→ proposal: {proposed_after: "\\cite[§SECTION OR THEOREM NUMBER]{jones2020}",
             confidence: "borderline"}
```

**Missing bib key — manual intervention needed:**
```
check-citations report: {key: "smith1984", bib_match: false}
→ proposal: {proposed_after: null, confidence: "low", safety_gate: "MANUAL"}
```

**Nothing to fix:**
```
check-citations report: all citations bib_match: true, non_pinpoint: false
→ clean-citations-proposals.json: {proposals: [], summary: "nothing to fix"}
```

**notes.tex on main detected:**
```
tex_file: /path/to/notes.tex   branch: main
→ safety_header: {notes_tex_on_main: true, safety_gate: "BLOCKED"}
→ proposals: []   (no proposals emitted when BLOCKED)
```
