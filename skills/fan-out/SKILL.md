---
name: fan-out
description: >-
  Delegate independent parts of a task to subagents, recursively when useful,
  then integrate and verify their work. Also fan a Gas City epic bead into
  convoy sub-beads without consuming more dispatcher slots. Use for "fan out
  this task", "fan-out epic", or "split this work among agents".
---

# fan-out

The invoking agent owns integration, verification, and cleanup.

## Delegate agent work

1. Split useful parallel work into bounded, reviewable assignments. Identify
   dependencies, shared files, the integration target, and acceptance checks.
   Ask each child to report changed paths, branch/worktree, commits, checks,
   and unresolved issues.
2. Choose each child's model and reasoning effort for its difficulty,
   uncertainty, cost, and latency, subject to runtime instructions. Any child
   may delegate independent parts; this skill sets no depth or child-count
   limit. Each child integrates and verifies its descendants' work.
3. For concurrent code edits, use separate branches and worktrees when changes
   may overlap or need isolation. Record who created each and its merge target.
   If agents share a checkout, assign disjoint paths or serialize writes.
   Preserve others' uncommitted work.
4. Review each child's changes. As children finish, integrate in dependency
   order, resolve conflicts, and check the combined result. Repair, reassign,
   or report failed and blocked work.
5. Once integrated, safely remove worktrees and branches created for this
   fan-out under repository Git rules. Retain any with unmerged or uncommitted
   work. The invoking agent checks every descendant's outcome, verifies the
   final result, and reports any retained worktree or branch.

For a Gas City epic, also follow the convoy procedure below.

## Gas City epic beads

One claimed epic bead occupies one dispatcher slot; its sub-beads implement
that slot. An atomic bead worker may delegate to subagents without creating
another bead fan-out.

| Bead check | Action |
| --- | --- |
| `bd show <bead> --json` has `metadata.dispatch.type == "epic"` | Use the convoy steps below. |
| No `dispatch.type=epic` | Work the bead directly; subagent delegation remains available. |
| Sub-bead of another epic | Do not create a nested convoy; subagent delegation remains available. |

**Every convoy sub-bead needs `dispatch.slot=free`.** The dispatcher tracks the
root epic; missing metadata can double-count a slot.

1. Confirm the epic metadata with `bd show <EPIC> --json`.
2. Use `create-convoy` to create an owned convoy if the epic has no
   `metadata.convoy_id`. It provides `CONVOY` and the feature branch.
3. Create one sub-bead per task. Set its target explicitly: convoy membership
   does not make the convoy its parent. Leave `branch` unset so the worker's
   formula can create and record a branch. Never name a new branch
   `<feature-branch>/...`; Git cannot hold it alongside the integration ref.

   ```bash
   bd create --title="<sub-task>" -t task \
     --parent=<EPIC> \
     --metadata '{"parent_bead":"<EPIC>","is_leaf":true,"target":"<feature-branch>","dispatch":{"slot":"free"}}' \
     --description="<what done looks like for this sub-bead>"
   gc convoy add <CONVOY> <sub-bead-id>
   ```

4. Verify each sub-bead's `metadata.target` is the integration branch before
   dispatch. Send it to an idle worker with
   `gc sling <rig>/<worker> <sub-bead-id> --no-convoy`, or through the rig's
   polecat work formula with
   `gc sling <rig>/polecat <sub-bead-id> --on mol-polecat-work`.
   Those workers may use subagents recursively under the delegation rules
   above; this does not create extra convoy members.
5. Monitor the members and integrate their work through the rig's active
   merge route. Confirm the integration branch contains the intended changes
   and passes the combined checks before closing the epic:

   ```bash
   gc convoy status <CONVOY>      # verify every member is closed
   gc convoy land <CONVOY>        # never use --force casually
   bd close <EPIC> --reason "fan-out complete, convoy landed"
   ```

   Closing the epic frees its dispatcher slot. Account for and clean up
   task-created worktrees and branches after integration, subject to the
   repository's Git rules.

## Failure recovery

- A stuck member remains open until its work is repaired, reassigned, or
  explicitly resolved; do not force-land a convoy with genuine work open.
- If a sub-bead lacks `dispatch.slot=free`, set it with
  `bd update <id> --set-metadata dispatch.slot=free`.
- If a task branch or target is wrong, correct its metadata and verify the
  intended merge destination before integrating it.
