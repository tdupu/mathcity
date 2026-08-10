---
name: configure-server
description: Interactively create the project-local lmfdb-server.conf by walking through each SSH and compute-server connection value one at a time (REMOTE_HOST, REMOTE_USER, REMOTE_REPO, SSH_JUMP, SSH_KEY, MAX_PARALLEL, ALERT_EMAILS). Gitignores the result. Run once per project before using server skills (push-to-server, pull-data-from-server, push-data-to-server, UPF skills). Companion setup skill per POLICY.md P1.12. Trigger phrases: "configure server", "set up the server conf", "configure the SSH connection", "the server skills can't find their conf", or on a fresh clone.
---

# configure-server

Create the project-local gitignored conf that SSH/compute-server skills read.
Real hostnames, users, and keys never enter git (POLICY.md P1.10).

## Dependency check

```bash
CONF="$(git rev-parse --show-toplevel 2>/dev/null)/lmfdb-server.conf"
if [ -f "$CONF" ]; then
  echo "I'm sorry, I can't do that — lmfdb-server.conf already exists at $CONF."
  echo "Diff existing keys against the example before reconfiguring:"
  echo "  diff <(grep '^[A-Z_]*=' \"$CONF\" | cut -d= -f1 | sort) \\"
  echo "       <(grep '^[A-Z_]*=' <mathcity-pack-root>/subdomains/lmfdb/assets/lmfdb-server.conf.example | cut -d= -f1 | sort)"
  echo "To start fresh: cp \"$CONF\" \"${CONF}.bak\" && rm \"$CONF\""
  exit 1
fi
```

## Procedure

1. **Check for existing conf.** Look for `lmfdb-server.conf` at the project root
   (`$(git rev-parse --show-toplevel)/lmfdb-server.conf`). If it exists, diff its
   keys against the example; do not overwrite.
2. **Copy the example.**
   ```bash
   cp <mathcity-pack-root>/subdomains/lmfdb/assets/lmfdb-server.conf.example \
      "$(git rev-parse --show-toplevel)/lmfdb-server.conf"
   ```
3. **Fill in values interactively** (one at a time, AskUserQuestion where available):
   - `REMOTE_HOST` — hostname of the compute server
   - `REMOTE_USER` — your username on the server
   - `REMOTE_REPO` — absolute path to the project on the server
   - `SSH_JUMP` — jump/bastion host (leave empty if none)
   - `SSH_KEY` — path to your SSH private key (default: `~/.ssh/id_ed25519`)
   - `MAX_PARALLEL` — parallel computation slots (default: `4`)
   - `ALERT_EMAILS` — email(s) for completion alerts (comma-separated)
   Never echo values or use them in argv.
4. **Gitignore the conf.**
   ```bash
   git -C "$(git rev-parse --show-toplevel)" check-ignore lmfdb-server.conf && echo ignored
   ```
   If not ignored, add the entry and re-verify.
5. **Optional SSH smoke test** (only with the human adjudicator's go-ahead):
   ```bash
   ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE_USER@$REMOTE_HOST" true
   ```
6. **Report** which server skills are now usable.

## Output

`ready` or `blocked` with the exact failing step. Never print conf contents.

## See also
- `assets/lmfdb-server.conf.example` — the shipped template
- `mathcity-lmfdb.configure-database` — sets up the database/pipeline side
- POLICY.md P1.10 (no private values), P1.12 (setup skill required)
