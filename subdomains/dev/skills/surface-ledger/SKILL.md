---
name: surface-ledger
description: Show the surface-status ledger — exactly two tables, MCP commands and skills, with their working/broken status, defect description, bead, GitHub issues, brief, adjudication, molecule and molecule outcome. Reconciles the ledger against tools actually exercised this session BEFORE displaying, so a surface used but never recorded cannot render as absent. Trigger on "surface-ledger", "surface status", "show me surface status", "show the surface ledger", "what's working in the MCP", "which tools are broken".
---

# surface-ledger

Display the surface-status ledger. **Two tables. Nothing else.**

Ledger file: `docs/SURFACE-STATUS.md` (pack-relative).

## What the operator wants to see

Taylor, 2026-08-23, verbatim:

> *"When I say 'surface-status', I just want to see the main table that I described."*
> *"Ok, I want two tables, one for the skills and one for the MCP commands."*

So the output is **two tables and a one-line tally under each.** Do NOT print the legend, the
`### MCP surface gaps` table, the `## Cross-cutting findings` section, the scope note, or the
changelog. They live in the file; they are not this skill's output.

## Columns (both tables, identical)

| Column | Content |
|---|---|
| Command / Skill | the surface's name |
| Working? | `WORKS` · `BROKEN` · `DEGRADED` · `NOT PROBED` · `DECLINED` |
| What's broken | the defect, concretely. Empty only when the status is `WORKS` and there is no caveat. |
| Bead | bead id, if the defect has one |
| GitHub | related issue numbers |
| In briefs | brief id, or why it is deliberately not filed |
| Adjudicated | verdict, or what it is waiting on |
| Molecule | molecule root id |
| Mol. done | whether the molecule finished |
| Brief produced | the brief the molecule emitted |

## Status vocabulary — this is the load-bearing part

| value | means |
|---|---|
| `WORKS` | **exercised in this city** and returned a correct answer |
| `BROKEN` | exercised and returned a wrong answer, or a right answer by a wrong mechanism |
| `DEGRADED` | works, with a named defect that does not stop the primary use |
| `NOT PROBED` | **never exercised — NOT a pass** |
| `DECLINED` | a probe was proposed and the human declined it. Not a tool fact. |

**Never render `NOT PROBED` as blank, and never infer `WORKS` from "no issue filed".** That
recreates P6.2 — *a check that could not have failed must not render as a check that passed.*
An unexercised tool with a clean tracker is `NOT PROBED`, full stop.

## Procedure

### 1. Reconcile before displaying — this is what makes the ledger self-updating

The standing rule is: *every time an MCP tool is used, if it is not in the ledger, add it.*
This skill enforces it at read time, so a stale ledger cannot be displayed as current.

1. Review the session for every `mcp__mctl__*` call made since the ledger was last reconciled.
2. For each one, compare against its row:
   - **absent** → add the row, status from the observed result
   - **present but stale** (status changed, defect found or cleared, bead/issue/brief/molecule
     now known) → update the changed cells
   - **present and current** → leave it
3. Do the same for any skill exercised or read at source.
4. If nothing changed, say so in one line. A no-op reconcile is a valid result, not a failure.

### 2. Read the ledger

Read `docs/SURFACE-STATUS.md`. The file is canonical — **do not reconstruct either table from
memory or from conversation.** If a row is in conversation but not in the file, that is a
reconcile miss: fix the file in step 1, then read it again.

### 3. Print

Print the MCP table, then the skills table, each followed by a one-line tally:

```
N exercised · N declined · N not probed. N BROKEN, N DEGRADED.
```

Sort each table so actionable rows come first: `BROKEN`, then `DEGRADED`, then `WORKS`,
then `DECLINED`, then `NOT PROBED`. Within a status group, keep related surfaces adjacent.

**Keep the two tables separate even when a skill and an MCP command share a name.**
`decisions-to-briefs` (skill) and `decisions_to_briefs` (command) each get their own row in
their own table. The pairing is a finding — the skill has the correct authorization and the
wrong plumbing, the command the reverse — and splitting them is what makes it visible.

## After printing

Add at most **two sentences** if, and only if, a row changed during reconcile — say which and
why. Otherwise print nothing after the tables. This skill is a display surface; analysis belongs
in the conversation that prompted it.

## Related

- [add-to-surface-ledger](../add-to-surface-ledger/SKILL.md) — update a row, then run this skill
- [gascity-ledger](../gascity-ledger/SKILL.md) — the sibling ledger for `gc`-layer problems

## Scope boundary

`gc`-layer problems — supervisor, tmux fleet host, lifecycle, claim latency, Dolt — are **not**
in this ledger. They belong to `docs/GASCITY-ISSUES.md`. The dividing line is #98's own wording:
*"This is gc source behaviour, not a mathcity pack change."*
