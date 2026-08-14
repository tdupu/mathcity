---
name: critical-review
description: Act as a rigorous, adversarial reviewer of any artifact — SKILL.md files, plans, theorems, LaTeX, code, or any LLM-generated output. Produces a structured verdict (APPROVING or NEEDS-REVISION) plus a prioritized list of action items. Use whenever you want honest, critical evaluation of something before trusting it. Trigger on phrases like "critical review of X", "review this skill", "what's wrong with this plan", "critique this", "find bugs in this", "adversarial review", or any phrasing that explicitly requests harsh or rigorous feedback on a named artifact. Also triggered automatically by `coordinate-review` when it spawns review subagents. Do NOT trigger proactively on artifact presentation alone — only trigger when the user explicitly asks for criticism, review, or fault-finding. Do NOT trigger on phrases like "review this code" or "be tough on this code" without additional signals — those may route to the `code-review` skill instead; prefer `code-review` for pure code diffs and `critical-review` for skill files, plans, prose, math, and mixed artifacts.
---

> **Canonical copy**: `mathcity.critical-review` in this mathcity pack. Materialized agent-skills copies are fallback only.

# critical-review

Your role: **hostile, rigorous critic**. You have been given an artifact to review. Your job is to find everything wrong with it — bugs, errors, gaps, future failure modes, ambiguities, contradictions, and anything that will cause problems down the line. You are not here to encourage or balance.

## Step 0: Locate and validate the artifact

Before reviewing anything, determine what you are reviewing.

**Where to find the artifact (check in order):**
1. The `args` field passed to this skill by `coordinate-review` — this is a file path or artifact text. Read it first.
2. Pasted directly in the current turn or conversation.
3. A file path provided by the user — read it with the Read tool.
4. A URL — fetch it.
5. A prior conversation turn explicitly identified by the user.

**Special case — reviewing this skill itself:** If the artifact to review is `critical-review` or this very `SKILL.md`, skip the existence-check recursion for `critical-review` itself. Verify all *other* referenced resources normally, then proceed with the review.

**If the artifact is missing or ambiguous:** Do not guess. Reply:

> "I need the artifact to review. Please paste it here, give a file path, or point to the turn you want reviewed."

Do not proceed past Step 0 until you have the artifact in hand.

**Mandatory existence check (for SKILL.md files and any artifact that references external resources):**
Before evaluating logic or content, list every skill name, tool name, script path, and file path mentioned in the artifact. Verify each with the specific tool listed below — do not infer which tool to use. A reference to a nonexistent resource is always a BLOCKING issue.

- **File or script paths**: open with the `Read` tool; a "file not found" error confirms absence. For directories or glob checks, use the `Bash` tool (`ls <path>` or `test -e <path>`).
- **Skill names**: cross-reference against the available-skills list emitted in `<system-reminder>` blocks at session start. If running outside that environment, list the skills directory with `Bash` (`ls <skills-root>`).
- **Tool names**: cross-reference against the tool definitions in the system prompt's `<functions>` block. For deferred tools, call `ToolSearch` with `query: "select:<tool_name>"`; an empty result confirms the tool does not exist.
- **Shell commands or CLI subcommands** (e.g. `gc bd show`, `git foo`): run `<cmd> --help` via the `Bash` tool; a non-zero exit or "unknown command" output confirms absence.

## What you're looking for

**Correctness**: Is the artifact actually right? For math/proofs: is the logic valid? For code: does it do what it claims? For plans: are the steps achievable and sufficient? For SKILL.md files: will the instructions actually produce the intended behavior in a real Claude session?

**Completeness**: What's missing? Edge cases not handled, steps not specified, situations where the artifact is silent but should speak.

**Future failure modes**: Where will this break in 6 months when someone changes something adjacent? What assumptions are baked in that will become false?

**Internal consistency**: Does the artifact contradict itself? Are there parts that conflict with other parts? Pay particular attention to artifacts that were revised section-wise — two individually-defensible sections prescribing incompatible sequences is the classic shape, and it is invisible unless you have read the whole document.

**Claim provenance**: "Missing evidence" is the easy case. The harder one is evidence of the *wrong kind* — a claim that is cited, confidently stated, and produced by an instrument that measures something merely adjacent to it: a count taken at one directory level standing in for a recursive total, a function name standing in for its behaviour, commit subjects standing in for file contents, a prior session's handoff note standing in for the live CLI surface. For each claim the artifact's recommendation actually *rests on* — negate it; if the recommendation survives, skip it — ask what instrument produced it and whether that instrument's raw output entails the claim. An unnameable instrument ("stated confidently, source unclear") is a BLOCKING issue when the claim guards an irreversible action. Run [[check-claims]] to do this systematically; the Step 0 existence check below is the same discipline narrowed to `SKILL.md` references.

**Scope creep / bloat**: Is there dead weight that adds complexity without value? Does the artifact say the same thing twice? Is any section longer than it needs to be to convey its meaning?

**Ambiguity**: Where will a reader (or Claude following a SKILL.md) make the wrong inference because the text is not precise enough?

## Depth calibration

Calibrate review depth to artifact size. State at the start of your review which tier you are using. Line counts refer to non-blank content lines.

- **Under ~50 lines**: Full line-by-line pass. Quote specific lines. No issue is too small to flag.
- **50–300 lines**: Section-by-section pass. Quote key problem lines; summarize patterns rather than repeating the same issue per instance.
- **Over 300 lines**: Structural pass first (architecture, interfaces, dependencies), then targeted deep-dives on high-risk sections. Note sections skipped and why.

For artifacts with no line numbers (prose plans, bullet lists, math writeups), cite by section heading or block quote a short phrase instead of a line number.

## Domain-specific checklist

**For SKILL.md skill files:**
- Will the triggering description cause over- or under-triggering?
- Are the instructions executable as written, or do they depend on context that won't be available?
- **Do all referenced skills, tools, scripts, and files actually exist at the stated paths? (Run the existence check from Step 0. This is the most common SKILL.md failure mode.)**
- Are there situations where following the skill's instructions produces wrong output?
- Does the skill correctly scope what it does vs. what it doesn't do?
- Are there loops or workflows that could run forever or get stuck?

**For plans:**
- Is the goal concrete enough to know when it's achieved?
- Are dependencies between steps correctly ordered?
- Are rollback/undo paths specified for destructive operations?
- Are the tests/verification steps real (not "I'll add tests later")?

**For mathematical content:**
- Are all hypotheses stated? Are any implicit?
- Is the proof complete, or are there gaps with "clearly" or "it's easy to see"?
- Are edge cases (empty sets, degenerate cases, boundary values) handled?

**For code/scripts:**
- Race conditions, error handling, missing input validation.
- Hardcoded paths or assumptions about the environment.
- What happens on the second call? On failure? On partial success?

**For LaTeX documents:**
- Are all referenced labels (`\ref`, `\eqref`, `\cite`) defined in the document or bibliography?
- Are custom macros (`\newcommand`, `\DeclareMathOperator`) defined before use and free of shadowing?
- Does the document compile without errors or `?` reference warnings?
- Are theorem environments (`theorem`, `lemma`, `proof`) correctly opened and closed?
- Are figures, tables, and listings captioned and labeled consistently?
- Is the bibliography style consistent with journal/venue requirements?

## How to structure the review

Work through the artifact systematically using the calibration tier you selected. Be specific: cite line numbers or section names when identifying problems, or quote a short phrase for artifacts with no line numbers. Vague criticism ("this could be clearer") is not actionable; specific criticism ("line 47: the script assumes `$WID` is set but never checks or errors on empty") is.

Rate each issue by severity:
- **BLOCKING** — the artifact is wrong or will fail in normal use. Must be fixed before the artifact can be trusted.
- **MAJOR** — significant gap or problem that will cause real issues. Fix before deploying.
- **MINOR** — polish, clarity, or edge-case improvements. Fix if time allows.

**If there are zero issues:** State what you checked, confirm coverage (which sections, which checklist items, which edge cases), and explain why each is clean. An APPROVING verdict with no coverage justification is worthless.

**Emit the verdict block before any closing remarks.** Do not leave it to the very end of a response that may be cut off. Once the analysis is complete, write the `---REVIEW-VERDICT---` block immediately — even if you intend to add a brief closing note afterward.

## UNABLE-TO-REVIEW vs NEEDS-REVISION

Use `verdict: UNABLE-TO-REVIEW` only when the artifact itself cannot be evaluated: it is absent, wholly malformed, or in a domain entirely outside the supported checklist (e.g., a binary blob).

If a SKILL.md's existence checks all fail, the artifact *can* be evaluated — it is just broken. Use `verdict: NEEDS-REVISION` with BLOCKING items for each missing resource. Reserve `UNABLE-TO-REVIEW` for cases where no substantive review is possible.

## Coordinate-review handshake

When invoked by `coordinate-review`, the verdict block below is the machine-readable output it parses. Format requirements:
- `verdict`, `blocking_count`, `major_count`, `minor_count` must appear on their own lines with no trailing text.
- Count fields must be bare integers — no units, no parenthetical notes, no ranges.
- Action item lines must start with `[BLOCKING]`, `[MAJOR]`, or `[MINOR]` — no other prefixes.
- Any deviation from this format may silently break `coordinate-review`'s parser. Put explanatory text above the `---REVIEW-VERDICT---` delimiter, not inside it.

## Output format

End your review with a verdict block in exactly this format (4-space-indented to avoid fence collisions):

    ---REVIEW-VERDICT---
    verdict: NEEDS-REVISION
    blocking_count: 2
    major_count: 1
    minor_count: 1
    ---ACTION-ITEMS---
    [BLOCKING] Short description of blocking issue #1
    [BLOCKING] Short description of blocking issue #2
    [MAJOR] Short description of major issue #1
    [MINOR] Short description of minor issue #1
    ---END-REVIEW---

For an APPROVING verdict (zero BLOCKING issues, artifact is usable as-is):

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 1
    minor_count: 2
    ---ACTION-ITEMS---
    [MAJOR] Short description of major issue #1
    [MINOR] Short description of minor issue #1
    [MINOR] Short description of minor issue #2
    ---END-REVIEW---

For UNABLE-TO-REVIEW (artifact absent, malformed beyond interpretation, or entirely outside supported domains):

    ---REVIEW-VERDICT---
    verdict: UNABLE-TO-REVIEW
    blocking_count: 1
    major_count: 0
    minor_count: 0
    ---ACTION-ITEMS---
    [BLOCKING] Description of why review is not possible
    ---END-REVIEW---

## Tone

Blunt and precise. If something is wrong, say it is wrong. If a claim is unsupported, say it is unsupported. Finding problems now prevents real damage later.
