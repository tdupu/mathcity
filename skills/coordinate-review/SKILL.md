---
name: coordinate-review
description: >-
  Run an artifact through an iterative create/review loop until it converges to
  an approved state. Can start from scratch (given a spec) or from an existing
  artifact. Each iteration spawns a `critical-review` subagent to find problems,
  then a `create-artifact` or `revise-artifact` subagent to fix them.
  Convergence is gated by the META-FP formula (`ops/meta-fp-cycle` in
  gascity-packs) — monotone shrink-OR-split + APPROVING quality floor + cap=10 +
  15min wall-time. Works on any artifact: SKILL.md files, plans, theorems,
  LaTeX, code, specifications. Use when you want to systematically create or
  improve something through a structured critic-creator loop. Trigger on phrases
  like "coordinate review of X", "iterate this to a fixed point", "run the
  review loop on", "improve this skill through review", "use the review process
  on", "apply coordinate-review to", "create X and review it", or whenever the
  user wants a multi-round quality improvement process on an artifact. Also use
  proactively when a user hands over a SKILL.md or plan and says "this is messed
  up" or "clean this up".
---

> **Canonical copy**: `mathcity.coordinate-review` in this mathcity pack. Materialized agent-skills copies are fallback only.

# coordinate-review

You orchestrate a create-review loop on an artifact until the META-FP framework formula says terminate. The artifact may already exist (you're improving it) or start as a spec (you're creating it).

You drive the loop. The critic and creator/revisor are subagents. The META-FP formula owns the convergence decision per iteration.

## Convergence guarantee

Per [[as-bb5]] + the human adjudicator 2026-06-25 verdict on as-h7r:

- **Mathematical**: each accepted iteration strictly shrinks the artifact's char-count OR factors a chunk into a sibling skill. Char-count is bounded below by 0; bounded-monotone → convergent in finite rounds.
- **Defense-in-depth**: cap=10 rounds + 15min wall-time gate per iteration. Both enforced by the formula.
- **Quality floor**: a revision wins ONLY if shorter AND APPROVING. Prevents trivial-deletion gaming.

You do NOT make this judgment in-skill. After each revisor finishes, you call `gc formula run meta-fp-cycle` and branch on its verdict.

## Inputs

- **spec** (required if no artifact): description of what to create.
- **artifact** (optional): existing file path or text block to improve. If provided, skip to the critic step.
- **brief_id** (optional): the `type=decision` bead behind the artifact, when the
  artifact is a brief. Enables the brief-artifact pre-check below.
- **reviewer_persona** (optional): a lens for the critic.
- **creator_persona** (optional): context for the creator/revisor.
- **store_beads** (optional, default false): write a bead file each iteration in `docs/beads/review-<artifact-basename>-<timestamp>/`.

## Setup

Initialize iteration counter to **N = 1**. Stamp `WALL_START=$(date -u +%FT%TZ)` for the META-FP wall-time gate.

**Determine artifact mode.** If **artifact** is provided:
- If it looks like a file path: read it. If you cannot find it, stop and ask. Then snapshot: `cp <artifact-path> <artifact-path>.bak`. Record `PREV_CHARS=$(wc -c < <artifact-path>)`.
- If it is a text block: hold it in memory. Record `PREV_CHARS=$(printf %s "<text>" | wc -c)`. Wrap-up will skip the `diff` step.

**Find and read the skill files** you will embed in subagent prompts — do this once before the loop. For each skill, check both locations with Bash, use whichever exists, then Read the file:

    ls <mathcity-pack-root>/skills/critical-review/SKILL.md \
      || ls ~/.claude/skills/critical-review/SKILL.md
    ls <mathcity-pack-root>/skills/create-artifact/SKILL.md \
      || ls ~/.claude/skills/create-artifact/SKILL.md
    ls <mathcity-pack-root>/skills/revise-artifact/SKILL.md \
      || ls ~/.claude/skills/revise-artifact/SKILL.md

If a path does not exist, stop and ask. Strip the YAML frontmatter (`---` … `---`) before embedding.

## Setup step: brief-artifact pre-check (only when the artifact is a brief)

coordinate-review is artifact-agnostic — SKILL.md files, plans, theorems, LaTeX,
code. **One artifact type has canonical state behind it**: a brief. When
[[brief-prep]] Phase 5 or [[create-brief]] gate 3 calls this skill, the file
under review is (or will become) the cache side of a `type=decision` bead, and
the critic cannot see that bead. Run the two read-only mctl reports first and
hand them to the critic as evidence.

Skip this whole section when the artifact is not a brief. It reads only; it
mutates nothing and needs no trace id.

```bash
CITY_ROOT="${CITY_ROOT:-$HOME/gt}"

# `bin/mctl` is the ONLY supported entry point for the MathCity control CLI.
# Never invoke assets/scripts/mctl.py directly — the shim owns repo-root
# resolution, and mctl_core/context.py owns city/rig discovery.
PACK_ROOT="${MATHCITY_PACK_ROOT:-$(
  sed -n '/^\[defaults.rig.imports.mathcity\]/,/^\[/p' "$CITY_ROOT/city.toml" \
    | sed -n 's/^source *= *"\(.*\)"/\1/p' | head -1
)}"
MCTL="$PACK_ROOT/bin/mctl"
[ -x "$MCTL" ] || { echo "mctl entry point not found at $MCTL"; exit 1; }

# BRIEF_ID is the decision bead; RIG is the rig that owns it.
"$MCTL" briefs doctor --brief "$BRIEF_ID" --city "$CITY_ROOT" --rig "$RIG" --json
"$MCTL" briefs options "$BRIEF_ID" --city "$CITY_ROOT" --rig "$RIG" --json
```

- **`briefs doctor`** reports where canonical bead state and the cache artifacts
  disagree. A critic reviewing prose cannot detect that the brief it is polishing
  is already adjudicated, or that its stack row points at a file that moved.
- **`briefs options`** enumerates the actions the brief actually enables. It is
  the mechanical check on §4 *"alternatives named"*: a brief whose prose offers
  three options while `options` reports one is not a well-formed brief, and that
  finding belongs in the critic's action items rather than in a later
  `MOPT001` failure at adjudication time.

**Fold the output into the critic prompt as evidence, under a
`## Canonical brief state` heading. Do NOT branch the loop on it.** These are
read commands; `mctl` never repairs drift and neither does this skill.
Specifically:

> **Drop `MBRF021`, `MBRF004`, and `MBRF005` before you hand anything to the
> critic.** All three are known-untrustworthy today — `MBRF021` is a mass false
> positive (66 of 70 briefs in one rig), and `MBRF004`/`MBRF005` are
> instrumentation under review where `malformed` means *closed with no verdict
> field*, not damaged. A critic handed these will spend rounds "fixing" findings
> that are artifacts of the reader. See
> `template-fragments/mctl-entry-point.md` and
> `subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md`.

A `gt-*` brief lives in the city-root HQ store, addressed by the `hq` rig
(`--rig hq`) — the resolver synthesizes `hq` from the city root and does not
declare it in `city.toml`, so it looks absent there but resolves clean (verified
2026-08-27). If you ever see `MCTL_CONTEXT_UNKNOWN_RIG` it means the wrong `--rig`
value, not an error in the brief; review without the pre-check either way.
(Corrected 2026-08-27: prior text called this a "known HQ-store gap / not a
registered rig" — false; `gt-*` is reachable via `--rig hq`.)

## Step 0 (only if no artifact): Initial creation

Spawn a **creator** (`create-artifact`) subagent:

    You are a skilled artifact creator. Apply the following instructions to produce a first draft.

    ## Creator instructions
    <body of create-artifact/SKILL.md, frontmatter stripped>

    ## Creator persona
    <creator_persona, or "Experienced artifact author">

    ## Target file path
    <the target output path, if user specified; omit otherwise for text-block mode>

    ## Spec
    <the spec>

Parse the `---ARTIFACT-HEADER---` block. The artifact content follows the `---END-HEADER---` line.

**Determine workflow mode from the header:**
- `file_path` is a real path → file workflow. Write to that path, then `cp <file_path> <file_path>.bak`. Set `PREV_CHARS=$(wc -c < <file_path>)`.
- `file_path == "text-block"` → text-block workflow. Hold in memory. Set `PREV_CHARS=$(printf %s "<text>" | wc -c)`. Wrap-up prints text.

If the creator's `self_review` starts with `ISSUES-REMAIN`, proceed to Step 1 (do not skip the critic).

If store_beads=true, store a creation-pass bead now (template in Step 4) with N=0 and "N/A — creation pass" for the revision summary.

## Step 1: Critic subagent

If file-based: re-read the artifact file before spawning the critic (do not rely on a stale in-memory copy).

Spawn a **critic** (`critical-review`) subagent:

    You are a rigorous, adversarial reviewer. Apply the following review instructions.

    ## Review instructions
    <body of critical-review/SKILL.md, frontmatter stripped>

    ## Reviewer persona
    <reviewer_persona, or "General-purpose adversarial reviewer">

    ## Artifact to review
    File path: <path, or "text-block">
    Iteration: <N>

    <full current content>

Parse `---REVIEW-VERDICT---`. Extract `verdict`, `blocking_count`, `major_count`, `minor_count`, action items.

If `verdict: UNABLE-TO-REVIEW`: stop. Report the obstruction. Do not continue.

## Step 2: Revisor (if NEEDS-REVISION)

If `verdict: APPROVING`, set `REVIEW_VERDICT=APPROVING` and skip to Step 3 (the formula will TERMINATE_CONVERGED on the next call).

Else spawn a **revisor** (`revise-artifact`) subagent:

    You are a skilled artifact revisor. Apply the following instructions.

    ## Revisor instructions
    <body of revise-artifact/SKILL.md, frontmatter stripped>

    ## Creator/Revisor persona
    <creator_persona, or "Experienced artifact author">

    ## Convergence rule (binding)
    Your revision MUST strictly shrink the artifact's character count vs the previous iteration, OR factor a chunk into a NEW sibling skill at `<repos-root>/agent-skills/skills/<sibling-name>/SKILL.md` (source) + `~/.claude/skills/<sibling-name>/SKILL.md` (install). Per as-bb5: each sibling must be APPROVING in isolation, carry a distinct named responsibility, and be ≥40 lines OR ≥1 distinct intrinsic concept. No trivial "see-parent" stubs.

    ## Artifact (current version)
    File path: <path, or "text-block">

    <full current content>

    ## Action items from the critic (iteration N)
    <action items>

    ## Previously observed issues (carry forward)
    <OBSERVED: items from prior revisor outputs, or "none">

Parse the output. Extract `---REVISION-SUMMARY---`. Then:
- **File-based**: the revisor wrote the file. Confirm (file exists, newer than `.bak`). Do not re-write.
- **Text-block**: extract revised text (everything before `---REVISION-SUMMARY---`) and hold as new current artifact.

Scan the entire output (including `---RESOLUTIONS---`) for `OBSERVED:` lines to carry forward.

Record:
- `NEW_CHARS = wc -c` of the revised artifact.
- `SPLIT_PRESENT = "true"` iff revisor created a sibling skill directory.
- `CREATE_VERDICT` from the revisor's own self-review block: `APPROVING` if revisor flagged no remaining issues, else `NEEDS-REVISION`.

## Step 3: META-FP gate

Invoke the META-FP formula with the iteration envelope:

    META_FP_ARTIFACT_PATH="<path or 'text-block'>" \
    META_FP_ITERATION="<N>" \
    META_FP_PREV_CHARS="<PREV_CHARS>" \
    META_FP_NEW_CHARS="<NEW_CHARS>" \
    META_FP_SPLIT_PRESENT="<true|false>" \
    META_FP_REVIEW_VERDICT="<APPROVING|NEEDS-REVISION>" \
    META_FP_CREATE_VERDICT="<APPROVING|NEEDS-REVISION>" \
    META_FP_WALL_START="<WALL_START>" \
    gc formula run meta-fp-cycle

The formula emits one JSON line on stdout with `verdict ∈ {ACCEPT_REVISION, SPLIT_INTO_SIBLING, TERMINATE_CONVERGED, TERMINATE_CAP, REJECT_AND_RETRY}`. Branch:

- **TERMINATE_CONVERGED**: Wrap-up with `status=converged`.
- **TERMINATE_CAP**: Wrap-up with `status=cap-hit`. Surface the best-scoring candidate AND the cap-hit signal (artifact + gates need tuning).
- **ACCEPT_REVISION** or **SPLIT_INTO_SIBLING**: set `PREV_CHARS=NEW_CHARS`, increment `N`. **Before the next iteration, run `/compact` to free context** — this summarizes prior iterations and resets the working memory for the next critic-revisor cycle. Then loop back to Step 1.
- **REJECT_AND_RETRY**: the revision broke the math gate or quality floor. Do NOT accept it. Restore from `.bak` (file mode) or revert in-memory (text mode). Re-spawn the revisor (Step 2) with the same critic action items + an extra OBSERVED line explaining the rejection (`reason` field of the formula verdict). Increment a retry counter; if 3 consecutive REJECT_AND_RETRY on the same iteration → Wrap-up with `status=cap-hit` (stuck).

Per as-h7r §1 criterion 4: NEVER silently continue past TERMINATE_CAP or stuck REJECT_AND_RETRY. The HAND-OFF is mandatory.

## Step 4: Store bead (if store_beads=true)

For text-block artifacts, use `text-block` as the basename.

Directory: `docs/beads/review-<artifact-basename>-<YYYYMMDDTHHMMSS>/` (use `date -u +%Y%m%dT%H%M%S` via Bash).

Write `<bead-dir>/iteration-<N>.md`:

    # Review bead — <artifact-basename> iteration N

    artifact: <path or "text-block">
    iteration: N
    timestamp: <ISO 8601>
    verdict: <verdict>
    blocking: <count>
    major: <count>
    minor: <count>
    meta_fp_verdict: <formula verdict>
    prev_chars: <PREV_CHARS>
    new_chars: <NEW_CHARS>
    split_present: <true|false>

    ## Action items from critic
    <action items>

    ## Resolutions from revisor
    <revision summary, or "N/A — creation pass">

    ## Observed (carried to next iteration)
    <OBSERVED: items, or "none">

Beads are evidence. Do not edit them after writing.

## Step 5: Next iteration

Run `/compact` between iterations N and N+1 — clears the prior critic/revisor transcript from your context before the next round so the loop does not grow unbounded.

Increment N. Go to Step 1.

## Wrap-up

When the META-FP formula returns TERMINATE_* (or stuck REJECT_AND_RETRY):

1. **Report status** to the user:
   - `converged`: APPROVING + APPROVING; X iterations; final artifact at <path or printed below>.
   - `cap-hit`: hit `META_FP_VERDICT.reason` (`iteration > 10`, `wall_time exceeded`, or `stuck REJECT_AND_RETRY ×3`). Surface the best candidate seen. Signal that the artifact + gates need tuning.
2. **Single next-action** (criterion 4 HAND-OFF EXPLICITLY): one of:
   - `accept current and merge` (if converged or cap-hit but usable)
   - `factor a chunk into a sibling skill named <NAME>` (if shrink gate keeps failing)
   - `revert to v1` (`cp <path>.bak <path>` for file mode; restore in-memory for text mode)
   - `surface remaining BLOCKING items to caller and stop`
   Pick exactly ONE. Never multiple. Never silent.
3. **Show changes**:
   - File-based: `diff <artifact-path>.bak <artifact-path>`. Empty diff is not an error (first-iteration APPROVING).
   - Text-block: print the final text.
4. **List remaining BLOCKING items** if not converged.
5. **Ask before committing.** Do not auto-commit.
