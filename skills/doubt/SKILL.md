---
name: doubt
description: Adversarial background fact-checker — triggered whenever anyone expresses doubt about a claim made in the current session. Forks a subagent that is told the current agent is WRONG and tasked with finding falsehoods, errors, and weaknesses. The fork runs non-blocking so the main conversation continues. Use when the user says "I doubt that", "I doubt X", "that doesn't seem right", "that seems wrong", "I'm skeptical", "are you sure about that", "doubt it", "that can't be right", "I question whether", or simply invokes /doubt followed by the claim. The doubt agent aggressively argues the opposite position whether or not the original claim is actually wrong — the point is to surface any weakness. Recommended model: Haiku (fast adversarial probe; Opus for high-stakes claims where the user says "really doubt this").
---

# doubt

Background adversarial fact-checker. When someone doubts a claim, fork a
subagent to attack it from all angles. Main session never waits.

## Trigger detection

This skill fires when the conversation contains ANY of:
- "I doubt that ..."
- "doubt that ..."
- "I doubt [something]"
- "that doesn't seem right" / "that can't be right"
- "are you sure about that?"
- "I'm skeptical of ..."
- "I question whether ..."
- Explicit invocation: `/doubt <claim>`

Extract the **specific claim being doubted** from context. If ambiguous, take
the most recent substantive assertion made by the agent (not by the user).

## What to fork

Use the `Agent` tool with `subagent_type: "fork"`.

**Why fork?** The fork inherits all context but runs silently in the
background. The main session continues without interruption. The fork's
tool output stays out of the parent's context.

**Model**: Default to `haiku` for speed. For high-stakes claims (the human adjudicator
explicitly says "really doubt this" or the claim is load-bearing for a
decision), use `opus`.

## Fork prompt template

Construct the fork prompt as follows. Fill in `CLAIM` and `CONTEXT`:

```
You are an adversarial fact-checker. Your job is to find everything wrong
with a specific claim.

CRITICAL FRAMING: The agent that made this claim is WRONG. Your job is to
find the falsehoods, errors, weak assumptions, and gaps. Do not give the
benefit of the doubt. Attack the claim from every angle.

CLAIM TO ATTACK:
<CLAIM — the specific assertion being doubted>

CONTEXT (what the agent was doing when it made this claim):
<CONTEXT — 1-3 sentences summarizing the surrounding conversation>

YOUR TASK:
1. State the claim precisely in your own words.
2. List every way this claim could be wrong:
   - Factual errors (check against known sources, source code, or math)
   - Hidden assumptions that might not hold
   - Edge cases the claim ignores
   - Alternative interpretations that contradict it
   - Missing caveats that would weaken it
3. If you find something concretely wrong, state it bluntly with evidence.
4. If after aggressive searching you cannot find a real error, say so
   explicitly: "Adversarial check complete — claim appears sound despite
   attack." Do NOT manufacture weaknesses that aren't there.
5. Rate the claim: SUSPECT (likely wrong), WEAK (real issues found but
   possibly still true), SOUND (survived adversarial probe).

Be rigorous. Be specific. Cite line numbers, file paths, or exact values
when attacking code or data claims. This agent may have made an error —
find it.
```

## Execution

1. Identify the claim from context (see Trigger detection above).
2. Build the fork prompt with CLAIM and CONTEXT filled in.
3. Launch the fork immediately with `Agent` tool:
   - `subagent_type: "fork"`
   - `model: "haiku"` (or `"opus"` for high-stakes)
   - `description: "adversarial doubt-check: <first 8 words of claim>"`
   - `prompt: <the filled template above>`
4. Tell the user: "Doubt-check running in background — will surface findings
   when complete." Do NOT wait. Return to the main conversation.
5. When the fork notification arrives, surface the verdict inline:
   ```
   🔍 doubt-check: <CLAIM (truncated to 60 chars)>
   Verdict: SUSPECT | WEAK | SOUND
   <Key finding in 1-3 sentences>
   ```

## check-zero result (pre-ship)

- `critical-review`: closest existing skill — adversarial, but synchronous
  and artifact-focused (SKILL.md files, plans, LaTeX, code). `doubt` is
  conversationally triggered and claim-focused, not artifact-focused.
- No existing skill runs adversarial checks non-blocking in background.
- No reinvention. Gap confirmed.

## What this skill does NOT do

- Does not block the main session — fork only, always
- Does not require an artifact (works on conversational claims)
- Does not always find something wrong (reports honestly when claim is sound)
- Does not replace `critical-review` (use that for full artifact review)
- Does not send results to repo-side landing agent or the mayor — surfaces inline to invoking session
