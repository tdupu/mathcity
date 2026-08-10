---
name: dolt-pull
description: >-
  Commit any pending beads changes locally, then pull from the Dolt remote.
  Scope is either a single rig (by name or current directory) or all rigs in
  the city. Default when unspecified: all rigs. Dolt auto-merges
  most conflicts; irresolvable conflicts are reported for human intervention.
  Trigger phrases: "dolt pull", "pull beads", "sync beads from remote",
  "pull dolt", "bd pull", "pull all dolts", "sync all rigs", "refresh beads".
---

# dolt-pull

Commit local pending changes, then pull from the Dolt remote. Dolt handles
most merges automatically; this skill reports the ones it cannot.

## Step 0 — Determine scope

If the user's request names a specific rig (e.g. "pull gascity-packs", "pull
gsp") or you are standing in a rig directory, use that rig.

**Default (no scope specified): pull ALL rigs in the city** — parse
`.gc/site.toml` and pull every declared rig. "dolt pull", "pull beads", or
"pull globally" all mean all rigs. Only ask if the user explicitly names a
scope that is ambiguous.

## Step 1 — Discover rig paths

For a **single rig**: resolve the path from `.gc/site.toml` or use the
current working directory if it is a registered rig.

For **all rigs**: parse `.gc/site.toml` in the city root to enumerate every
`[[rig]]` entry and its `path`. Example:

```bash
grep -A1 '^\[\[rig\]\]' "$(gc city --json 2>/dev/null | jq -r .root || echo ~)/.gc/site.toml" \
  | grep '^path' | sed 's/path = "//' | sed 's/"//'
```

## Step 2 — For each target rig

Run the following sequence in the rig's directory (`cd <rig-path>`):

### 2a. Safety check

```bash
bd dolt status
```

Verify a remote named `origin` is configured. If no remote exists, STOP for
this rig and report: "No remote configured for <rig-name> — run dolt-init
first." Continue to the next rig if operating on all.

### 2b. Commit local pending changes

Preserve local work before the pull overwrites working state:

```bash
bd dolt commit -m "auto-commit before pull [mathcity.dolt-pull]"
```

If nothing to commit, proceed. If commit fails on dirty internal config keys,
continue anyway — those keys do not conflict with incoming remote data.

### 2c. Pull

```bash
bd dolt pull origin main
```

### 2d. Conflict handling

Dolt auto-merges the vast majority of beads conflicts (different rows edited
independently). If `bd dolt pull` reports unresolved conflicts:

1. Report the conflict to the user with the conflicting table and row IDs.
2. STOP for this rig — do not attempt further pulls or pushes until resolved.
3. Suggest: "Run `bd dolt status` to inspect, then resolve manually and
   `bd dolt commit -m 'resolve merge conflicts'` before retrying."

Do NOT auto-resolve by blindly picking `--ours` or `--theirs` — bead data
conflicts (two agents closing the same bead differently) require human
judgment.

## Step 3 — Report

```
✓ gascity-packs  pulled (12 new commits — 4 beads updated)
✓ agent-skills   pulled (already up to date)
✗ hecke          CONFLICT — manual resolution needed (see bd dolt status in <city-root>/hecke)
```

## Hard rules

- **Always commit before pulling.** Uncommitted local changes can be silently
  overwritten by the pull; the commit preserves them in dolt history.
- **Never auto-resolve bead conflicts.** Picking `--ours` or `--theirs`
  blindly destroys one agent's writes. Stop and surface to the user.
- **Never pull without a remote.** A pull to an uninitialized remote corrupts
  nothing but wastes time; check `bd dolt remote list` first.
