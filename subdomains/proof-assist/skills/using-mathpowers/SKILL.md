---
name: using-mathpowers
description: Use when any mathematical claim is asserted, relied on, questioned, or produced in a research session — "what is known about X", "is this proved?", "prove it", "find something to prove", "attack the skeleton", "I doubt that", "does this contradict what we have", "gather the background" — BEFORE answering or proving anything directly. Routes to the owning leaf, pipeline, or the ledger. NOT for writing into .tex (using-latexpowers), formalization (non-goal), or generic process work (superpowers:using-superpowers).
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, ignore this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## The Rule

**Before asserting, relying on, or producing any mathematical claim: read the repo's ledger (`scratch/LEDGER.md`, convention in `subdomains/repo-docs/LEDGER.md`) — or state that none exists — then dispatch via the table.** The claim's home is the REPO, not the web or your memory. Unclear intent (target manuscripts? target theorems?) → request a grill-with-docs session.

## Dispatch

| Situation | Route |
|---|---|
| "is X proved?" — read the ledger row; `proved` counts ONLY with its evidence path and a doubt run with verdict SOUND; no row → not proved, say so | ledger + `doubt` record |
| "what is known / open about X" | `references/research-soh.md` (the research-SOH recipe) |
| "are we reinventing the wheel" / before building | `check-zero` |
| "what could we prove here" | `find-proposition` |
| "prove it" (a specific claim) | PROVERS.md dispatch (`subdomains/proof-assist/PROVERS.md`) |
| skeleton/spec with conjectural items — "attack the skeleton" | `fill-in-prototype` |
| "I doubt that" / "are you sure" — any in-session claim | `doubt` |
| new result vs recorded claims — "does this contradict" | `contradiction-check` (refusal semantics) |
| "gather the background on X" into a spec | `create-exposition` |
| skeleton lands in tex / any write-up | `using-latexpowers` → its writers |
| two rows fire | `doubt` outranks a bare status answer on any expressed skepticism; `contradiction-check` runs before any promotion or harvest lands; PROMOTION requires a ledger row + SOUND doubt verdict (writers enforce; no shortcuts) |

## Red flags

| Thought | Reality |
|---|---|
| "Searched the web for the exact claim" (first action) | The claim lives in the repo. Ledger first, web second. |
| "The report says proved" | Reports are drafts. Ledger + doubt decide. |
| "The manuscript supersedes the conflicting claims" | Silent supersession is prohibited. contradiction-check. |
| "It's obviously true / the g=1 case generalizes" | Plausible-but-false is mechanism 6. doubt or prove. |

## Precedence

User instructions (CLAUDE.md, AGENTS.md, GEMINI.md, etc, direct requests) take precedence over skills, which in turn override default behavior. Only skip skill workflows or instructions when your human partner has explicitly told you to.

The repo's own instantiated docs outrank this router; `superpowers:using-superpowers` owns generic process dispatch; anything entering a `.tex` belongs to `using-latexpowers`.
