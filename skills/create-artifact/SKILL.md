---
name: create-artifact
description: Dispatched by coordinate-review (payload contains a spec field and an optional artifact_type field, no action_items field) to produce a new artifact from a spec, or triggered directly by user phrases like "draft a skill for X", "draft a plan for Y", "write a SKILL.md for", "produce a first draft of X". Produces any LLM-generated artifact from scratch — SKILL.md files, plans, theorems, LaTeX, code, specifications — with self-review baked in. For revision tasks (applying action items to an existing artifact), use revise-artifact instead.
---

# create-artifact

You produce new artifacts from a spec or description. After producing the artifact, you run a self-review pass and fix any blocking issues before handing back.

For revision tasks (existing artifact + action items), use `revise-artifact`, not this skill.

## Mode determination

This skill operates in CREATE mode. The one exception: if you receive an existing artifact **plus a list of action items**, you are in the wrong skill. Output this error block, then stop:

    ---ARTIFACT-ERROR---
    error: WRONG-SKILL
    redirect: revise-artifact
    reason: Received existing artifact with action items; this is a revision task.
    ---END-ERROR---

After emitting the error block, do not produce an artifact. If you are running in an interactive user session (not coordinator-dispatch), also tell the user: "This input is a revision task. Please invoke revise-artifact and pass the artifact and action items to it."

If you receive an existing artifact *without* action items (e.g., "here's my current SKILL.md, improve it"), treat the artifact as the spec — you are producing a replacement from scratch. **Before doing so, summarize the existing artifact in one sentence and state that you are replacing it, so the requester can correct you if that is not the intent.** In coordinator-dispatch context, skip the confirmation and proceed; flag the replacement in `interpretations`.

## Distinguishing context: coordinator-dispatch vs. interactive user session

Use these heuristics to determine which context you are in:

- **Coordinator-dispatch**: your input arrives as a structured payload (e.g., JSON or YAML with a `spec` key and possibly `artifact_type`), or the invoking message contains no conversational framing (no "please", no questions, no chat context). Interactive clarification is not possible.
- **Interactive user session**: input is a natural-language message from a human user. You can ask clarifying questions and receive answers.

When ambiguous, treat the context as interactive (the safer default).

This distinction affects two behaviors:
1. **Underspecified spec** (see below) — ask questions in interactive; emit UNDERSPECIFIED error in coordinator-dispatch.
2. **Replacement confirmation** — prompt the user in interactive; proceed silently in coordinator-dispatch.

## Minimum-spec threshold

If the spec is so underspecified that a reasonable interpretation cannot be formed — for example, "write something interesting" with no artifact type, domain, or purpose — do not guess.

**Interactive session**: ask one or two clarifying questions to establish at minimum: (1) artifact type and (2) the artifact's purpose or audience. Once you have enough to make a reasonable interpretation, proceed and document it in `interpretations`.

**Coordinator-dispatch context**: output this error block and stop:

    ---ARTIFACT-ERROR---
    error: UNDERSPECIFIED
    redirect: none
    reason: <one sentence describing what is missing>
    ---END-ERROR---

## Creating from scratch

**You receive**: a description or spec of what the artifact should be. Optionally: the artifact type (SKILL.md, plan, LaTeX proof, Python script, etc.) and any domain context.

**You produce**: a complete, well-formed artifact.

1. **Understand the spec.** If the spec contains internal contradictions, do not silently produce a self-contradictory artifact. State the contradiction in `interpretations`, choose the interpretation most consistent with the apparent intent, and note what you chose. If the spec is ambiguous but not contradictory, make a reasonable interpretation and state it in `interpretations`.

2. **Identify artifact type and apply its conventions:**
   - **SKILL.md**: YAML frontmatter with `name` and `description` fields (description: one paragraph, triggering-language-first); markdown body opened with `# <name>` heading matching the `name` field. No additional required YAML fields beyond `name` and `description`.
   - **Plan**: numbered steps, each with a clear action verb and explicit output. State dependencies inline at each step that has them (e.g., "Depends on step 2 output"), not in a separate section.
   - **LaTeX theorem/proof**: `\begin{theorem}...\end{theorem}` / `\begin{proof}...\end{proof}`; all hypotheses stated before the proof body.
   - **Python**: module docstring, typed function signatures, all imports present at the top of the file, no undefined names at module level.
   - **Other code**: follow the target language's idioms; no syntax errors; no undefined variables.
   - **Spec/design doc**: title, purpose, scope, decisions with rationale, open questions section.
   - **Anything else**: state the conventions you are choosing to follow in `interpretations`.

3. **Draft the artifact** following those conventions. Keep it concise — say what needs to be said and stop. Do not pad.

4. **Self-review** (see below).

5. **Output**: write the header block first (see Output format), then the artifact. Return the full artifact inline. If the requester explicitly provided an absolute file path and asked you to write to disk, also write the file using the Write tool; set `file_path` in the header to that path. In all other cases, set `file_path` to `text-block`.

## Self-review pass

After producing the artifact, re-read it as a skeptical reader who did not write it — not as the author who knows what was intended. Your job is to find things that will break, not to confirm that your intentions were good.

Check for two classes of issues:

**BLOCKING** — things that cause the artifact to fail in normal use:
- **SKILL.md**: instructions impossible to follow, circular references to nonexistent scripts, triggering language that will never match real user phrasing.
- **Plans**: missing steps that make the plan unexecutable, circular dependencies.
- **Proofs/theorems**: logical gaps, missing hypotheses, steps that do not follow from prior steps.
- **Code**: syntax errors, undefined variables or functions, obvious logic errors.
- **Specs**: contradictory requirements, undefined terms in normative statements.

Note: "circular references to nonexistent scripts" is a content-level check (does the artifact reference a tool or file by name that clearly cannot exist?), not a filesystem verification. If the artifact references a specific absolute path, you may use the Read tool to verify it exists; for general script names, apply judgment.

**MAJOR** — issues that reduce quality significantly but do not break the artifact outright (missing edge-case handling, incorrect tone, misleading structure, etc.).

**MINOR** — cosmetic or low-impact issues (phrasing, minor omissions, style).

### Fix pass rules

If you find BLOCKING issues:
1. Attempt to fix each blocking issue.
2. For each blocking issue you **cannot** fix (e.g., missing information that only the requester can supply): leave it unfixed and record it in `self_observed` as `[BLOCKING-UNFIXABLE] <description>`.
3. Fix only BLOCKING issues in this one pass. Fixing MAJOR and MINOR issues in the same pass risks introducing new problems while resolving old ones; record them in `self_observed` instead so the caller can decide whether to iterate.
4. Do not loop. Output the artifact after one fix pass regardless of whether all blocking issues were resolved.

**self_review header values:**
- `CLEAN` — no blocking issues found.
- `FIXED (N)` — N blocking issues found and all N fixed.
- `ISSUES-REMAIN (N unfixable)` — N blocking issues remain because they require information or changes only the requester can supply (truly unfixable in this pass). Use this status only for unfixable issues; if a blocking issue is fixable but you chose not to fix it, that is a bug in your process — fix it.

MAJOR and MINOR issues spotted during self-review: note them in `self_observed` with their severity tag (`[MAJOR]` or `[MINOR]`). Do not add them to the artifact.

## Output format

The header block must appear first — emit it before any other output, including explanatory prose. In an interactive user session, you may add a brief explanatory note *after* the `---END-HEADER---` line.

    ---ARTIFACT-HEADER---
    mode: CREATE
    artifact_type: <choose one: SKILL.md | plan | theorem | code | spec | other:specify>
    file_path: <absolute path if written to disk, "text-block" if returned inline>
    self_review: CLEAN | FIXED (N) | ISSUES-REMAIN (N unfixable)
    self_observed: <issues noticed but not fixed, tagged [MAJOR] or [MINOR] or [BLOCKING-UNFIXABLE], or "none">
    interpretations: <spec ambiguities or contradictions and how you resolved them, or "none">
    ---END-HEADER---

Then the artifact itself (full content, never truncated).

## Practical notes

**Preserve format**: if the spec says YAML-frontmatter + markdown, produce that. If it says LaTeX, produce LaTeX.

**Do not editorialize**: your scope is the spec. Issues beyond the spec go in `self_observed`, not silently into the artifact.

**Do not rename things** unless the spec says to. This applies to names within the artifact (identifiers, field names, headings, YAML keys) and to the artifact's own file name or `name` field. Do not rename things simply because you would choose a different name.
