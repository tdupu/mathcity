# Dolt Remote Setup

Parent: [../README-dolt.md](../README-dolt.md)

Root quickstart: [README-dolt.md](../README-dolt.md).

Each rig runs a Dolt-backed bead store. Beads hold internal operational
context — decision records, brief history, bead metadata — that must not be
exposed publicly even when the code repo is public. Back up bead data to a
dedicated **private** repository that is separate from the code repository.

## Naming Convention

Use a dedicated private repository name such as:

```text
<repo>-dolt
```

Never share the beads repository with the code repository for public code
repositories. Keep code and bead data on separate remotes.

## Setup Steps

**1. Create a private GitHub repo.**

```bash
gh repo create <owner>/<repo>-dolt --private
```

Verify it is private before continuing. A public beads repo is a hard error.

**2. Configure the Dolt remote.**

```bash
bd dolt remote remove origin    # drop any stale remote
bd dolt remote add origin git+ssh://git@github.com/./<owner>/<repo>-dolt.git
```

The `./` after `github.com` is required by the Dolt SSH protocol; omitting it
breaks the push.

**3. Push bead data.**

```bash
bd dolt push
```

Dolt writes to `refs/dolt/data`, a non-standard ref that is separate from git
branches. It will not appear in the branch list and will not pollute the
repo's branch history.

**4. Verify.**

```bash
git ls-remote origin refs/dolt/data
```

A SHA line in the output confirms the push landed. If the output is empty,
re-check the remote URL and SSH key access.

## Two-Sided Sync

If a workflow keeps both a city-side rig checkout and a repo-side working copy,
point both bead stores at the same private Dolt remote. Sync is manual and
on-demand:

- Pull bead data at the start of repo-side work.
- Push bead data when repo-side work is finished.
- Let the city side push independently when its patrols or agents update the
  same bead store.

Critical: bead data must NEVER be pushed to the code repositories. Ensure that
code remotes do not carry `refs/dolt/data` or `__dolt_remote_info__`.

## Dolt Server Mode

Embedded mode has a failure class where mutations can land in bd's live layer
without reaching the Dolt tables, causing `bd dolt push` to sync stale data.
Server mode avoids this by running one long-lived `dolt sql-server` for the
stores and routing bd writes through SQL into the Dolt layer.

The exact data directory, service manager, port, and owner-specific remote
names are local operations details. Keep them in the repository's local
`CONTEXT.md` rather than in public README files.

## Restore From Backup

To restore a rig's bead store from its private GitHub backup into a fresh
directory:

```bash
mkdir -p /path/to/restore-dir
cd /path/to/restore-dir
bd init --remote "git+ssh://git@github.com/./<owner>/<repo>-dolt.git" --non-interactive
```

`bd init --remote` clones the full Dolt database from `refs/dolt/data` and
adopts the project identity. It downloads all bead chunks and makes `bd list`
immediately functional.

**After restore:** the cloned database does not auto-configure a push remote.
Before pushing from a disaster-recovery clone, re-add the remote explicitly:

```bash
bd dolt remote add origin "git+ssh://git@github.com/./<owner>/<repo>-dolt.git"
bd dolt push
```

**Delta on restore is normal:** beads created after the last `bd dolt push`
will be missing from the restore. The delta equals the beads created since the
last backup push.
