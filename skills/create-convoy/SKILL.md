---
name: create-convoy
description: Create a properly configured OWNED convoy for an epic bead — the fan-out container for one WIP-dispatcher slot. Use when an agent holds an epic bead and needs the convoy set up before fanning sub-beads out ("create a convoy for this epic", "set up the fan-out convoy", "create-convoy for <epic-id>"). Sets --owned (blocks background auto-close), the target integration branch, and tree metadata (root_bead, feature_branch, merge_strategy). Counterpart of fan-out, which creates sub-beads and populates this convoy. Works for any agent that can run gc and bd.
version: "0.1"
---

# create-convoy

Create the owned convoy that carries an epic's fan-out. One epic bead = one
WIP-dispatcher slot; the convoy is the container for its sub-beads. Members of
an owned convoy do NOT consume additional dispatcher slots.

## When to use / not use

| Situation | Action |
| --- | --- |
| You hold an epic bead (`metadata.dispatch.type == epic`) and are about to fan out | **Use this skill** |
| Bead is atomic (no `dispatch.type=epic`) | Don't — work it directly, no convoy |
| Convoy already exists for this epic (check `gc convoy list`) | Don't — reuse it, go to `fan-out` |
| You want ephemeral operational work (health checks, one-shot ops) | Don't — use wisps, not a convoy |

## Inputs

- `EPIC` — root epic bead ID (e.g. `gt-abc1`)
- `BRANCH` — feature/integration branch name (e.g. `feature/pull-dispatcher`)

## Steps

1. **Create the owned convoy.** `--owned` blocks background auto-close
   (`gc convoy check` will skip it); the epic worker controls termination
   via `gc convoy land`. `--target` sets the branch child work beads inherit.

   ```bash
   gc convoy create <epic-slug> --owned \
     --target <BRANCH> \
     --merge local \
     --owner "$GC_AGENT"
   # note the convoy ID it prints, e.g. gc-42
   ```

   Merge strategy default is `local` (integration-branch style: leaves merge
   into <BRANCH>, refinery lands <BRANCH> later). Use `direct` or `mr` only
   if the epic explicitly calls for it.

2. **Bake tree metadata onto the convoy bead.** There is no `--var` flag on
   `gc convoy create`; set metadata with `bd update`:

   ```bash
   bd update <convoy-id> \
     --set-metadata root_bead=<EPIC> \
     --set-metadata feature_branch=<BRANCH> \
     --set-metadata merge_strategy=integration_branch
   ```

3. **Link the epic.** Record the convoy on the epic bead so any agent (or the
   deacon) can walk epic → convoy → members:

   ```bash
   bd update <EPIC> --set-metadata convoy_id=<convoy-id>
   ```

4. **(Optional) Create the integration branch on origin** so leaf branches
   have a parent to merge into:

   ```bash
   git push origin HEAD:<BRANCH>   # creates the branch if it doesn't exist
   ```

5. **Output the convoy ID** — the caller (usually the `fan-out` skill, step 3)
   uses it for `gc convoy add <convoy-id> <sub-bead-id>`.

## Key invariant

Convoy members carry `dispatch.slot=free` metadata (set by `fan-out` at
sub-bead creation). The WIP patrol counts only the root epic bead against the
global slot budget (N=6). The convoy and all its members ride on the epic's
one slot.

## Verify

```bash
gc convoy status <convoy-id>       # owned, target branch, 0/N members
bd show <convoy-id> --json | grep -E "root_bead|feature_branch"
```
