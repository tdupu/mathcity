---
name: dolt-init
description: Initialize the bd (beads) Dolt database and set the dolt remote in BOTH <city-root>/<repo-name> and <repos-root>/<repo-name>. The Dolt repo on GitHub MUST be named exactly <repo-name>-dolt — if it is not, HALT and tell the user to rename it before continuing. Trigger phrases: "dolt init", "set up dolt remote", "initialize beads for", "wire up dolt for", "bd dolt remote add", "init bd for".
---

# dolt-init

Sets up the Dolt-backed beads database for a repo in both the city rig
(`<city-root>/<repo-name>`) and the working copy (`<repos-root>/<repo-name>`).

## Naming invariant — HARD GUARD

The Dolt repo on GitHub **MUST** be named exactly `<repo-name>-dolt`.

Before running any step, verify:

```bash
REPO_NAME="<repo-name>"                        # e.g. cliff-part2
EXPECTED_DOLT="<github-owner>/${REPO_NAME}-dolt"        # e.g. <github-owner>/cliff-part2-dolt
echo "Expected private Dolt repo: ${EXPECTED_DOLT}"
```

If the user named the repo anything other than `<repo-name>-dolt`, **STOP** and say:

> "The dolt repo must be named `<repo-name>-dolt` (got `<actual-name>`).
> Please rename the GitHub repo to `<github-owner>/<repo-name>-dolt` (private) and try again."

Do not proceed until the name matches.

## Prerequisites

1. User has created a **private** GitHub repo named `<github-owner>/<repo-name>-dolt`.
2. `<city-root>/<repo-name>` exists and is registered as a gc rig.
3. `<repos-root>/<repo-name>` exists as the working-copy clone.

## Steps

```bash
REPO="<repo-name>"      # e.g. cliff-part2
PREFIX="<prefix>"       # e.g. cp2
DOLT_URL="git+ssh://git@github.com/./<github-owner>/${REPO}-dolt.git"
# NOTE: the ./ before <github-owner> is REQUIRED — the URL is rejected without it.

# Step 1 — Init bd in city rig
cd <city-root>/${REPO}
bd init --prefix ${PREFIX}

# Step 2 — Set dolt remote in city rig
bd dolt remote add origin "${DOLT_URL}"

# Step 3 — Init bd in working copy
cd <repos-root>/${REPO}
bd init --prefix ${PREFIX}

# Step 4 — Set dolt remote in working copy
bd dolt remote add origin "${DOLT_URL}"

# Step 5 — Verify both sides
echo "=== city rig ===" && cd <city-root>/${REPO} && bd dolt remote list
echo "=== working copy ===" && cd <repos-root>/${REPO} && bd dolt remote list
# Both should show:
#   origin    git+ssh://git@github.com/./<github-owner>/<repo-name>-dolt.git

# Step 6 — Initial push from city rig
cd <city-root>/${REPO}
bd dolt push origin main
```

## Security

- The dolt repo **MUST** be private. Confirm with `gh repo view <github-owner>/${REPO}-dolt --json isPrivate`.
- If it is public, **HALT immediately** and alert the user — do not push any bead data.
- Never run `bd dolt push` to a public repo.

## See also

- `/repo-to-city` — full mapping of repo names to city rigs and prefixes
- `bd dolt push/pull` — sync between city rig and working copy
- `bd backup init/sync` — DoltHub backup (separate from the GitHub dolt remote)
