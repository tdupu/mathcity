# Dolt Backup Setup

Parent: [README.md](./README.md)

Mathcity uses Dolt-backed bead stores for operational state: beads, brief
records, decisions, links, and dispatch metadata. That data can contain private
work context even when the code repository is public, so bead data must be
backed up to a dedicated **private** Dolt remote, separate from the code repo.

## Naming

Use one private backup repository per code repository:

```text
<owner>/<repo>-dolt
```

For this repository, `<repo>` is `mathcity`, so the expected backup repository
name is:

```text
<owner>/mathcity-dolt
```

Do not push bead data to the code repository. In particular, the code repo must
not receive `refs/dolt/data` or `__dolt_remote_info__`.

## Create The Backup Repo

Create the Dolt backup repository as private:

```bash
gh repo create <owner>/<repo>-dolt --private
```

Verify privacy before pushing any bead data:

```bash
gh repo view <owner>/<repo>-dolt --json isPrivate
```

If the result is not private, stop and fix the repository visibility before
continuing.

## Configure The Remote

From the checkout whose bead store you are backing up:

```bash
bd dolt remote remove origin 2>/dev/null || true
bd dolt remote add origin git+ssh://git@github.com/./<owner>/<repo>-dolt.git
bd dolt remote list
```

The `./` after `github.com` is required by Dolt's SSH remote syntax.

## Push A Backup

Commit pending bead changes and push the Dolt data:

```bash
bd dolt status
bd dolt commit -m "backup bead changes"
bd dolt push origin main
```

Verify that the Dolt ref exists on the backup remote:

```bash
git ls-remote git@github.com:<owner>/<repo>-dolt.git refs/dolt/data
```

A SHA line means the backup landed.

## Two-Sided Sync

If you keep both a city-side rig checkout and a repo-side working clone, point
both bead stores at the same private `<repo>-dolt` remote.

Use this rhythm:

- Pull bead data before repo-side work:
  ```bash
  bd dolt pull origin main
  ```
- Push bead data after repo-side work:
  ```bash
  bd dolt push origin main
  ```
- Let city-side agents push their own bead updates independently.

When both sides edit the same bead, Dolt may report a conflict. Do not pick
ours/theirs blindly; bead conflicts are decision data and need human review.

## Restore

To restore bead data into a fresh directory:

```bash
mkdir -p <restore-dir>
cd <restore-dir>
bd init --remote "git+ssh://git@github.com/./<owner>/<repo>-dolt.git" --non-interactive
bd list
```

After restoring, configure the push remote explicitly before writing new bead
data from the restored clone:

```bash
bd dolt remote add origin "git+ssh://git@github.com/./<owner>/<repo>-dolt.git"
bd dolt push origin main
```

Any beads created after the last successful `bd dolt push` will not be present
in the restored copy.

## Local Operations Details

Machine-specific paths, service-manager details, port numbers, server-mode
configuration, SSH identity choices, and owner-specific remote names belong in
local `CONTEXT.md` files, not in shipped README files.

See also: [docs/DOLT-REMOTE-SETUP.md](./docs/DOLT-REMOTE-SETUP.md).
