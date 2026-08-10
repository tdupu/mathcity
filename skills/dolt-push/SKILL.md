---
name: dolt-push
description: >-
  Commit any pending beads changes and push to the Dolt remote. Scope is
  either a single rig (by name or current directory) or all rigs in the city.
  Default when unspecified: all rigs. Handles non-fast-forward
  automatically by pulling first, then retrying the push. Trigger phrases:
  "dolt push", "push beads", "sync beads to remote", "push dolt", "bd push",
  "push all dolts", "sync all rigs".
---

# dolt-push

Commit pending bead changes and push to the Dolt remote, with automatic
conflict resolution for non-fast-forward rejections.

## Step 0 — Determine scope

If the user's request names a specific rig (e.g. "push gascity-packs", "push
gsp") or you are standing in a rig directory, use that rig.

**Default (no scope specified): push ALL rigs in the city** — parse
`.gc/site.toml` and push every declared rig. "dolt push", "push beads", or
"push globally" all mean all rigs. Only ask if the user explicitly names a
scope that is ambiguous.

## Step 1 — Discover rig paths

For a **single rig**: resolve the path from `.gc/site.toml` or use the
current working directory if it is a registered rig.

For **all rigs**: parse `.gc/site.toml` in the city root to enumerate every
`[[rig]]` entry and its `path`. Example:

```bash
# List rig paths from site.toml (one per line)
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

### 2b. Commit pending changes

```bash
bd dolt commit -m "auto-commit before push [mathcity.dolt-push]"
```

If `bd dolt commit` reports "nothing to commit", proceed — this is not an
error.

If commit fails with dirty internal config keys (issue_prefix, types.custom),
commit is a no-op for those keys; continue anyway — the push will still
capture committed data.

### 2c. Push

```bash
bd dolt push origin main
```

### 2d. Auto-resolve non-fast-forward

If push fails with a non-fast-forward or diverged-history error:

```bash
bd dolt pull origin main   # merge remote into local
bd dolt push origin main   # retry
```

If the retry also fails (genuine conflict that dolt cannot auto-merge), report
the conflict to the user and STOP for this rig — do not retry further.

## Step 3 — Report

For each rig, report one line:

```
✓ gascity-packs  pushed (3 new commits)
✓ agent-skills   pushed (already up to date)
✗ hecke          FAILED — non-auto-resolvable conflict (manual intervention needed)
```

## Security invariant

Never push to a public GitHub repo. Before the first push to any remote,
confirm with:

```bash
gh repo view <owner>/<repo-name>-dolt --json isPrivate | jq -r .isPrivate
```

If `false`, HALT and warn the user — do not push bead data to a public repo.

## Hard rules

- **Never run `bd dolt push` more than twice** per rig per invocation
  (one attempt + one retry after pull). If two attempts fail, stop and report.
- **Never force-push** (`--force`). Dolt push is append-only; force-push
  destroys remote history.
- **Never skip the commit step.** Uncommitted local changes are not pushed;
  silently losing them is worse than a failed push.
