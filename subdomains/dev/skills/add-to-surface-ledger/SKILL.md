---
name: add-to-surface-ledger
description: Record what we just learned about an MCP command or a skill into the surface-status ledger — update the affected cells for the surface under discussion, then immediately display the ledger by running surface-ledger. Trigger on "add to surface ledger", "record this in the surface ledger", "update the surface ledger", "log this tool result", "that goes in the ledger", or whenever an MCP tool or skill is exercised and its row would change.
---

# add-to-surface-ledger

Update the row for the surface under discussion, then **immediately run
[surface-ledger](../surface-ledger/SKILL.md)** so the operator sees the result of the edit
without asking twice.

Ledger file: `docs/SURFACE-STATUS.md` (pack-relative).

## When this fires

The standing rule (Taylor, 2026-08-23):

> *"Every time you use an MCP tool, if it hasn't been added to the .md ledger, add it."*

So: any time an `mcp__mctl__*` tool is called, or a skill is exercised or read at source, and
what we learned changes a cell. Do not wait to be asked. Do not batch a session's worth of
findings into one late write — a ledger written from memory hours later is the thing this
skill exists to prevent.

## Which table

Two tables, and the surface's **kind** decides which:

| The surface is… | Row goes in |
|---|---|
| an `mcp__mctl__*` command | the **MCP commands** table |
| a skill (`SKILL.md`) | the **Skills** table |

A skill and a command that share a name get **two separate rows in two separate tables** —
`decisions-to-briefs` and `decisions_to_briefs` are different artifacts with different defects.
Never merge them.

If the finding is about `gc start` / `gc stop` / `gc restart`, the supervisor, the tmux fleet
host, claim latency, or Dolt, **it does not belong here at all** — use
[add-to-gascity-ledger](../add-to-gascity-ledger/SKILL.md).

## Procedure

### 1. Identify the surface and the cells that changed

Name the exact command or skill. Then change only what the new evidence supports:

| Cell | Update when |
|---|---|
| Working? | the status changed — see the vocabulary below |
| What's broken | a defect was found, characterised further, or cleared |
| Bead | a bead now tracks it |
| GitHub | a related issue was found or filed |
| In briefs | it entered the brief system, or there is a reason it deliberately has not |
| Adjudicated | a verdict landed, or the thing it waits on changed |
| Molecule / Mol. done / Brief produced | a molecule was dispatched, finished, or emitted a brief |

### 2. Set the status honestly

| value | means | do NOT use it for |
|---|---|---|
| `WORKS` | **you exercised it** and it returned a correct answer | "it has no open issues" |
| `BROKEN` | exercised, wrong answer — or right answer by a wrong mechanism | a suspicion |
| `DEGRADED` | works, with a named defect that does not stop the primary use | an unnamed worry |
| `NOT PROBED` | never exercised. **Not a pass.** | anything you actually ran |
| `DECLINED` | a probe was proposed and the human declined | a tool that failed |

**Promoting a row to `WORKS` requires that you ran it and read the result.** A clean tracker is
not evidence. This is the single most common way a ledger like this goes wrong.

### 3. Write the defect description so it survives the session

The "What's broken" cell is read by someone with none of today's context. Give it:

- the **mechanism**, not the symptom alone — *"hardcodes `verdict=\"approve\"` on every call"*,
  not *"approves things it shouldn't"*
- the **observable** that proves it — a field value, a count, a returned status
- `[measured]` vs `[inferred]` where the distinction is live, and never blur them

### 4. Record retractions in place — do not silently overwrite

If this update contradicts something the ledger previously asserted, **say so in the cell**.
A ledger that quietly rewrites itself teaches the next reader to distrust all of it. Precedent
already in the file: the S49 molecule count was corrected from 7 to 8 with the arithmetic shown.

### 5. Run surface-ledger — always, immediately

Invoke [surface-ledger](../surface-ledger/SKILL.md). Do not summarise the tables yourself and do
not skip it because the change was small. The point of pairing them is that the operator sees the
current ledger every time it moves.

## Hard stops

- Do not mark a surface `WORKS` you did not exercise.
- Do not record a `gc`-layer problem here — it goes to the gascity ledger.
- Do not delete a row. A surface that stopped being broken becomes `WORKS` **with the former
  defect noted**, so the history stays legible.
- Do not merge the skill and MCP rows for a same-named pair.
