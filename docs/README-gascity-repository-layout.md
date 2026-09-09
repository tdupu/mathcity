# Gascity Repository Layout

Parent: [../README-development.md](../README-development.md)

This document explains how gascity rig repositories and the HQ repository (where `gc init` is run) differs from a remote repository where gascity operates. Suppose that we have two repositories `<workspace>/repo1` and `<workspace>/repo2` that we are working on and that we create a new directory `<workspace>/HQ` where we will run `gc init` to create our gascity.

---

> **⚠️ CORRECTION (2026-07-31 — verified against gascity source + `git` behavior; supersedes the `.repo.git` claims below):**
> 1. **`.repo.git` is NOT bare.** It's a stock git *separate git directory* (`git init --separate-git-dir`) — non-bare, `core.worktree=..`.
> 2. **`gc rig add` does NOT create `.repo.git`.** Nothing in gascity renames `.git`→`.repo.git`; `gc rig add` leaves a **normal `.git`**, and `gascity-packs` runs as a rig on a normal `.git` in production. The `.repo.git` rigs were hand-created / legacy.
> 3. **The `.repo.git` NAME is a latent hazard, not a feature.** Git hard-protects the literal name `.git` (refuses to ever track it); `.repo.git` is an ordinary name, so a branch can commit `.repo.git/**` and a later `checkout` overwrites the live database — the hecke "checkout-bomb" (2026-07-31). **Prefer a normal `.git`** (what `gc rig add` produces, inherently safe). Convert a `.repo.git` rig with `rm .git && mv .repo.git .git`.
>
> A rig needs its own git marker only so `git worktree` doesn't walk up to a parent repo; a normal `.git` does that identically. Cross-ref `gt-08ddnd` (the parallel `~/gt` git-on-a-dolt-repo violation).
>
> <sub>Ported from the legacy `gascity-packs/mathcity` tree 2026-09-09 (tdupu/mathcity#19). The correction was written there on 2026-07-31 and never reached this canonical copy, so this document carried the refuted "bare" claim — and the hazard in point 3 — for five weeks after it was known to be wrong.</sub>

## The core pattern: `.repo.git` + linked worktrees

Every rig uses a **split git layout**: the bare git database lives at `<rig>/.repo.git/` and the rig root becomes a linked worktree of it. Agent beads each get their own additional worktree under `.gc/worktrees/<rig>/<bead-id>/`. All worktrees share the same `.repo.git` object store — different branches, same history.

The key insight: **agents never fight over the working tree.** Each bead gets its own branch in its own worktree directory, but they all share one git history in `.repo.git`.

---

## Step-by-step: what the `gc` commands do

### `gc init <workspace>/HQ`

This is the first command you run. It creates the city in `<workspace>/HQ/`:

- `city.toml` — city config and rig registry; the presence of this file marks a directory as a gascity HQ
- `.gc/` tree — the RuntimeRoot (worktrees, cache, agents, supervisor socket, event log)
- `.beads/` — HQ-level bead store (city-wide issues)
- `formulas/`, `orders/`, `prompts/`, `hooks/` — pipeline and automation config

Nothing is touched in `repo1` or `repo2` yet.

### `gc rig add <workspace>/repo1`

Registers `repo1` as a rig in the city. What happens inside `repo1`:

1. If a `.git/` **directory** already exists (i.e. `repo1` is a normal git repo), gascity restructures it:
   - Moves `.git/` → `.repo.git/` (making it a bare repo in place)
   - Writes a `.git` **file** (not a directory) containing `gitdir: ./.repo.git` — this turns the repo root into the "main" linked worktree of its own bare repo
2. Initializes `.beads/` in the rig root (rig-scoped issue tracking)
3. Registers the rig in `city.toml` — written **last** so any earlier failure leaves the config unchanged

Run the same command for `repo2`.

### `gc sling repo1/<agent> <bead-id>`

Spawns an agent on a bead. What happens:

1. Runs `git -C <workspace>/repo1 worktree add <workspace>/HQ/.gc/worktrees/repo1/<bead-id> <branch>`
2. The agent's `work_dir` is set to that worktree path
3. A spawn-time guard (`ValidateAncestorWorktreesNotStale()`) checks for stale `.git` file pointers on ancestor directories before the `worktree add` call

---

## HQ layout (`<workspace>/HQ/`)

```
<workspace>/HQ/
├── city.toml                     ← city config + rig registry (the city marker)
├── .gc/                          ← RuntimeRoot: gascity runtime directory
│   ├── worktrees/                ← WorktreesRoot (override: $GC_WORKTREES_DIR or $T3CODE_HOME)
│   │   ├── repo1/
│   │   │   └── <bead-id>/        ← each agent bead gets a git worktree here
│   │   │       ├── .git          ← FILE: "gitdir: <workspace>/repo1/.repo.git/worktrees/<bead-id>"
│   │   │       └── <checked-out files on that bead's branch>
│   │   └── repo2/
│   │       └── ...
│   ├── cache/packs/              ← local pack materializations (city-local only)
│   │                                git-URL imports cache to ~/.gc/cache/repos/<hash>/ (user-global)
│   ├── agents/                   ← agent session bookkeeping
│   ├── controller.sock           ← supervisor UNIX socket
│   │                                (falls back to /tmp/gascity-controller/<sha256>.sock
│   │                                 when the city path length exceeds 100 chars)
│   ├── events.jsonl              ← city event log
│   ├── nudges/
│   └── tmp/
├── .beads/                       ← HQ-level bead store
│   ├── metadata.json
│   └── config.yaml
├── formulas/                     ← formula definitions (TOML)
├── orders/                       ← order definitions (TOML)
├── prompts/
└── hooks/
```

---

## Rig layout (`<workspace>/repo1/`)

```
<workspace>/repo1/
├── .git                          ← FILE (not a dir): "gitdir: ./.repo.git"
│                                    ↑ makes the rig root itself a linked worktree
├── .repo.git/                    ← BARE git repo: actual object database
│   ├── HEAD
│   ├── config                    ← remotes, etc.
│   ├── objects/                  ← all commits, trees, blobs
│   ├── refs/
│   └── worktrees/                ← git's own worktree tracking
│       └── <bead-id>/
│           ├── gitdir            ← points back to HQ/.gc/worktrees/repo1/<bead-id>/.git
│           └── commondir         ← "../../" (back to .repo.git itself)
├── .beads/                       ← rig-level bead store
│   ├── metadata.json
│   └── config.yaml
├── latex/                        ← your research files (tracked by git)
├── python/
└── sage/
```

---

## The worktree pointer chain (bidirectional)

The link between HQ and a rig worktree is maintained in both directions:

```
HQ/.gc/worktrees/repo1/<bead-id>/.git
    → "gitdir: <workspace>/repo1/.repo.git/worktrees/<bead-id>"

repo1/.repo.git/worktrees/<bead-id>/gitdir
    → "<workspace>/HQ/.gc/worktrees/repo1/<bead-id>/.git"
```

Breaking either side without `git worktree remove` leaves a stale pointer. `ValidateAncestorWorktreesNotStale()` checks for this at spawn time before any new worktree is added.

---

## Where Dolt/beads live

| Location | What's there |
| --- | --- |
| `<workspace>/HQ/.beads/` | City-wide / HQ-scope issues |
| `<workspace>/repo1/.beads/` | Rig-scoped issues for repo1 |
| `<workspace>/repo2/.beads/` | Rig-scoped issues for repo2 |
| `~/.dolt-data/` | Dolt's actual data files — **never touch `.dolt/` inside here** |
| `dolt-server.port` (topology) | Which port the shared Dolt server is on (3307 by default) |

One Dolt process on port 3307 serves **all** databases — HQ and all rigs share the same server.

---

## Concrete analogy: one HQ plus one rig

A concrete city with one rig maps directly onto this pattern:

```
<city-root>/<rig-name>/.git              → FILE: "gitdir: ./.repo.git"
<city-root>/<rig-name>/.repo.git/        → bare git database for the rig
<city-root>/.gc/worktrees/<rig-name>/
    <bead-id>/
        .git                             → FILE pointing to <rig-name>/.repo.git/worktrees/<bead-id>
        <checked-out files>              ← agent's branch checkout
    <worker-pool>/
        .git                 → same pattern
    <merge-queue>/
        .git                 → same pattern
```

Local-path pack imports can be materialized into the consuming agent's skill
directory and read live from a checked-out pack root. Git-URL imports get
cached under the user-global Gas City cache; that is the only kind that uses
the CacheRoot.
