---
name: fan-out
description: Fan an epic bead out into sub-beads (convoy members) WITHOUT consuming additional WIP-dispatcher slots. Use when an agent has claimed an epic bead from the pull-dispatcher and needs to decompose it ("fan out this epic", "fan-out <epic-id>", "decompose my epic into sub-beads", "split this slot into sub-tasks"). Encodes the tree metadata (parent_bead, is_leaf, branch naming, dispatch.slot=free) that lets the refinery contract the branch tree bottom-up and lets the WIP patrol ignore sub-beads. Companion to create-convoy. Works for any agent that can run gc and bd.
version: "0.1"
---

# fan-out

You claimed an epic bead. That epic = **one** dispatcher slot. Fan the work out
into sub-beads inside an owned convoy; the sub-beads are the *implementation*
of your slot, not new slots. When all sub-beads close, land the convoy, close
the epic, and the slot frees.

## When to use / not use

| Check | Result |
| --- | --- |
| `bd show <bead> --json` → `metadata.dispatch.type == "epic"` | **Fan out (this skill)** |
| No `dispatch.type=epic` on the bead | Atomic — work it directly, do NOT fan out |
| Sub-bead of someone else's epic | You are a leaf — just do the work, never re-fan |

## Key invariant

**Sub-beads with `dispatch.slot=free` do NOT consume WIP slots.** The
dispatcher (N=6 global) tracks only the root epic bead. Never create a
sub-bead without this metadata, or the WIP patrol will double-count.

## Steps

1. **Confirm you hold an epic slot.**

   ```bash
   bd show <EPIC> --json | grep -o '"dispatch[^,}]*'   # expect type: epic
   ```

2. **Create the convoy** (skip if `metadata.convoy_id` already set on the
   epic). Use the `create-convoy` skill — it sets `--owned`, the target
   branch, and `root_bead`/`feature_branch` metadata, and returns `CONVOY`.

3. **Create sub-beads with tree metadata.** One per sub-task. Branch names
   encode the tree: `<feature-branch>/<subtask-slug>` — the refinery infers
   parent/child from branch names.

   ```bash
   bd create --title="<sub-task>" -t task \
     --parent=<EPIC> \
     --metadata '{"parent_bead":"<EPIC>","is_leaf":true,"branch":"<feature-branch>/<subtask-slug>","dispatch":{"slot":"free"}}' \
     --description="<what done looks like for this sub-bead>"
   ```

4. **Add each sub-bead to the convoy.**

   ```bash
   gc convoy add <CONVOY> <sub-bead-id>
   ```

5. **Dispatch the sub-bead work.** Sub-beads run concurrently but ride on your
   slot. Either sling each to an idle worker (`--no-convoy` prevents a second
   auto-convoy wrapping the bead):

   ```bash
   gc sling <rig>/<worker> <sub-bead-id> --no-convoy
   ```

   or pour a wisp per sub-bead via the rig's polecat work formula:

   ```bash
   gc sling <rig>/polecat <sub-bead-id> --on mol-polecat-work
   ```

6. **Monitor and land.** The deacon fires convoy-completion when all members
   reach `status=closed`, triggering the refinery's bottom-up contraction:
   complete leaves merge into `<feature-branch>`, which may itself become a
   new leaf. Your final act as the epic worker — ONLY after all members are
   closed:

   ```bash
   gc convoy status <CONVOY>      # verify N/N closed
   gc convoy land <CONVOY>        # terminate owned convoy (never --force casually)
   bd close <EPIC> --reason "fan-out complete, convoy landed"
   ```

   Closing the epic frees your dispatcher slot.

## Failure modes

- Stuck member → fix or `bd close` it with a reason; do not `land --force`
  while work is genuinely open.
- Slot double-count → a sub-bead is missing `dispatch.slot=free`; patch with
  `bd update <id> --set-metadata dispatch.slot=free`.
- Refinery can't find the parent branch → sub-bead `branch` metadata doesn't
  follow `<feature-branch>/<slug>`; rename and update metadata.
