---
name: revise-artifact
description: Apply a set of action items to an artifact (SKILL.md, plan, code, LaTeX, theorem, etc.) and produce a revised version. Takes the current artifact and a list of action items (typically from `critical-review`) and outputs a corrected artifact with a resolution summary. Use whenever you have review feedback to apply: "apply these action items", "revise this based on the review", "fix the issues in this skill", "incorporate the critique", or when `coordinate-review` spawns a revision subagent. Trigger on a user handing over a document plus a non-trivial list of structured changes (not for single-line edits the user could state directly). Binary/non-text artifacts (images, compiled binaries, etc.) are out of scope — this skill handles text-based artifacts only.
---

# revise-artifact

You have been given an artifact and a list of action items. Your job: apply the action items to produce a revised artifact.

## Inputs you'll receive

1. **The artifact** — either an absolute file path (e.g., `/workspace/project/skills/supervise-agents/SKILL.md`) or the text content directly. Binary or non-text files are out of scope; stop and tell the user if you receive one.
2. **Action items** — a prioritized list, typically from `critical-review`, in the format:
   ```
   [BLOCKING] Description of issue
   [MAJOR] Description of issue
   [MINOR] Description of issue
   ```
   Or a free-form list from the user.

**If either input is absent, stop immediately and ask the user to supply it.** For partially-specified inputs, apply a pragmatic threshold: if you have enough to perform a meaningful revision (e.g., action items without severity tags, or a file path without explicit artifact text), proceed and note any assumptions in the resolution summary. Stop only when proceeding would require guessing at the user's intent — for example, if the action items are too vague to act on, or the artifact path does not resolve to a readable file.

## Before you start

Count the total number of action items. A compound bullet that contains two distinct fixes counts as two items — split and track them separately. Every item must appear in the resolution summary; `items_resolved + items_partial + items_skipped` must equal this total. Note: `[ALREADY-SATISFIED]` dispositions count toward `items_skipped` in the numeric totals. Track your count as you work.

## How to approach the revision

**Work through action items in priority order**: BLOCKING first, then MAJOR, then MINOR. Within each tier, tackle items that are most load-bearing first. For free-form (untagged) lists, treat all items as MAJOR and process them in the order given.

If two items in the same tier directly contradict each other, **stop and ask the user to resolve the conflict** rather than picking unilaterally. Note the conflict in the resolution summary and mark both items [SKIPPED] pending user clarification. Exception: if one of the conflicting items is BLOCKING and you have a clear, auditable safety or correctness reason to prefer it, you may resolve in its favor — but document the reasoning explicitly so it can be reviewed.

**Be surgical**: fix what's broken, preserve what works. Don't rewrite a working section because you have a different stylistic preference — that's noise. Make the minimum change that resolves each action item.

**For each action item, decide:**
- **Resolved** — you made a change that addresses it. Note what you changed.
- **Already satisfied** — the artifact already addresses this item correctly; no change needed. Note why it was already correct.
- **Partially resolved** — you improved it but couldn't fully address it without more context. Note what you did and what's still open.
- **Skipped with rationale** — you chose not to address it. Explain why (e.g., "this would require information not in the artifact", "fixing this conflicts with a BLOCKING fix already made").

Don't silently skip items. Every action item needs an explicit disposition in the resolution summary.

## Writing the revised artifact

### File-based artifacts

**Step 1 — Read first (mandatory).** Use the Read tool on the absolute file path before making any edits. Do not proceed to edits without confirming the current content.

**Step 2 — Edit in place using targeted edits.** Use the Edit tool for targeted, surgical changes — it only replaces the specified string and is safer than a full-file overwrite. Use the Write tool (full overwrite) only when the changes are so pervasive that individually specifying each old/new string pair would be more error-prone than rewriting the whole file (a useful heuristic: if more than roughly half the lines change). The caller (`coordinate-review` or the user) is responsible for versioning — you write the improved version in place.

**Step 3 — Verify after editing.** After each edit, confirm the change is semantically correct in context — not just that the new string is present. If you cannot confirm the edit is correct (e.g., the tool reported an error, or the surrounding context looks wrong), stop editing, mark the affected item [PARTIAL] in the resolution summary, and report the exact issue. Do not continue applying further edits to a file whose state is uncertain.

**Step 4 — Multi-file artifacts.** If action items span multiple files, handle each file in turn using the same Read → Edit → Verify cycle. List every file you modified in the resolution summary.

**Step 5 — Partial-failure note.** If you complete some edits but encounter an error before finishing, stop and report: which action items were applied, which were not, and the exact error. Do not silently leave the file in a partially-revised state.

### Text-block artifacts

Output the full revised content first, then the resolution summary below it. For large artifacts (over ~300 lines), consider whether a file-based approach would be clearer — ask the user to save the content to a file, since outputting very long revised text in-line makes it hard to write correctly and hard for the user to review.

Preserve the artifact's format: if it's YAML-frontmatter + markdown, keep that. If it's LaTeX, keep the LaTeX structure. Don't switch formats.

## Self-review pass

After applying all action items, re-read the revised artifact as a skeptical reader who did not perform the revision — not as the editor who knows what was intended. Two questions to answer:

1. **Did each `[RESOLVED]` disposition actually resolve its action item?** Find the location each fix was supposed to land and verify the issue is gone. A claimed fix that left the original problem in place is a false `[RESOLVED]` disposition — treat it as a blocking issue.
2. **Did the revision introduce new problems?** Surgical edits can leave broken cross-references, orphaned mentions, drifted identifiers, or sections that no longer cohere with their surroundings. Look for these in the changed regions and their immediate context.

Check for two classes of issues:

**BLOCKING** — issues that the revision either failed to fix or actively introduced:
- A `[RESOLVED]` disposition whose target issue is still present in the artifact.
- A rename or restructure that left dangling references to the old name elsewhere in the artifact.
- A surgical edit that broke surrounding text (truncated sentence, mismatched markup, orphaned heading).
- Internal inconsistencies created by the edits (e.g., a count cited in two places that no longer agree).

**MAJOR** — quality regressions caused by the revision that do not break the artifact outright (clumsy phrasing introduced, a section that now reads less clearly, edges of the change that could be tightened).

**MINOR** — cosmetic issues introduced by the edits (whitespace, formatting drift, minor stylistic inconsistencies).

### Fix pass rules

If you find BLOCKING issues:
1. Attempt to fix each blocking issue. For a false `[RESOLVED]` disposition, re-edit until the issue is genuinely fixed, or demote the disposition to `[PARTIAL]` or `[SKIPPED]` with a clear rationale — and update the original disposition line so the summary stays internally consistent.
2. For each blocking issue you **cannot** fix in this pass (e.g., it would require information only the requester can supply): leave it unfixed and record it as a `[SELF-OBSERVED]` line tagged `[BLOCKING-UNFIXABLE]` in the resolution summary.
3. Fix only BLOCKING issues in this one pass. Record MAJOR and MINOR as `[SELF-OBSERVED]` lines tagged with their severity. Fixing them now risks introducing new problems while resolving old ones.
4. Do not loop. Output the resolution summary after one fix pass regardless of whether all blocking issues were resolved.

**self_review header values:**
- `CLEAN` — no blocking issues found during self-review.
- `FIXED (N)` — N blocking issues found and all N fixed.
- `ISSUES-REMAIN (N unfixable)` — N blocking issues remain because they require information or changes only the requester can supply. Use this status only for unfixable issues; if a blocking issue is fixable but you chose not to fix it, that is a bug in your process — fix it.

## Output format

After the revised artifact (for text-block artifacts) or after writing the file (for file-based artifacts), produce a resolution summary in this exact format so `coordinate-review` can parse it:

    ---REVISION-SUMMARY---
    items_total: N
    items_resolved: N
    items_partial: N
    items_skipped: N
    self_review: CLEAN | FIXED (N) | ISSUES-REMAIN (N unfixable)
    ---RESOLUTIONS---
    [RESOLVED] [BLOCKING] Original action item text (verbatim) :: what you changed
    [RESOLVED] [MAJOR] Original action item text (verbatim) :: what you changed
    [ALREADY-SATISFIED] [MAJOR] Original action item text (verbatim) :: why no change was needed
    [PARTIAL] [MAJOR] Original action item text (verbatim) :: what you did :: what remains
    [SKIPPED] [MINOR] Original action item text (verbatim) :: why skipped
    [SELF-OBSERVED] [MAJOR] Issue noticed during self-review of the revision :: what you did or why deferred
    [OBSERVED] Issue you noticed but did not fix :: rationale for deferring
    ---END-REVISION---

Notes on the format:
- **Copy action item text verbatim** — do not paraphrase. Downstream parsers in `coordinate-review` correlate items by exact text match.
- Use `::` as the field separator (not ` — `) to avoid collisions with dash-containing action item text. If an action item's text itself contains `::`, replace the occurrence with ` : : ` (spaced) in the verbatim copy so the parser can split on `::` unambiguously.
- `items_total` = total number of action items given (after splitting any compound items). If the totals don't add up after recounting, output the summary anyway and add an `[OBSERVED]` line flagging the discrepancy with your best explanation.
- `[ALREADY-SATISFIED]` lines count toward `items_skipped` in the numeric totals.
- `[SELF-OBSERVED]` lines are issues found during the self-review pass — about the revision itself (missed fixes, regressions you introduced, residual MAJOR/MINOR you chose not to fix in the same pass). Tag each with `[BLOCKING-UNFIXABLE]`, `[MAJOR]`, or `[MINOR]`. They do not count toward `items_total`.
- `[OBSERVED]` lines are for ambient issues in the artifact that fall outside both the action items and the self-review pass. They do not count toward any total. Use them sparingly.
- When invoked directly by a user (not via `coordinate-review`), `[SELF-OBSERVED]` and `[OBSERVED]` lines are issues for the user to consider in a future review cycle — they are not action items for this revision.

## Things to avoid

- **Don't introduce new bugs while fixing old ones.** When you touch a section, read the surrounding context to make sure your change doesn't break something that was working.
- **Don't pad.** If an action item says "add an example," add one tight example, not three. If it says "tighten the description," cut words, don't add more.
- **Don't editorialize.** The action items are the scope. If you notice other issues while revising, record them as `[OBSERVED]` lines in the resolution summary — but don't unilaterally add them to the artifact. Let `coordinate-review` or the user decide whether to address them.
- **Don't change names, paths, or identifiers** unless an action item specifically asks for it. Renaming things is high-disruption and breaks references elsewhere.
