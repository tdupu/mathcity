---
name: setup-bead-drift
description: Create the machine-local bead-drift conf that bead-drift-report.sh reads, and optionally install the weekly launchd job that runs it. Use when the user says "setup bead drift", "set up the drift report", "configure bead-drift", "install the weekly drift job", on a fresh machine before first use of the drift report, or when bead-drift-report.sh reports "no bead-drift conf at ...". Creates ~/.gc/bead-drift.conf from assets/bead-drift.conf.example; never commits real values.
---

# setup-bead-drift

Create the machine-local configuration that
[`scripts/bead-drift-report.sh`](../../scripts/bead-drift-report.sh) reads, so a
fresh machine goes from `git clone` to a working drift report without
reverse-engineering the conf (POLICY.md P1.12).

Endpoint and database values live ONLY in the generated file — never in pack
content, the conversation transcript, or git history (P1.10). The conf is
written under `~/.gc`, which is outside every git repo, so it cannot be
committed anywhere. Do **not** relocate it into a repo and gitignore it: a
gitignore is a rule someone can override, a path outside the repo is not.

## Dependency check

```bash
CONF="${HOME}/.gc/bead-drift.conf"
if [ -f "$CONF" ]; then
  echo "I'm sorry, I can't do that — $CONF already exists."
  echo "Nothing to set up. To reconfigure, back it up and remove it:"
  echo "  cp \"$CONF\" \"${CONF}.bak\" && rm \"$CONF\""
  exit 1
fi
```

## Procedure

**Step 1 — Gather the values.** Ask the user for each, showing the example
file's comment as the prompt. Never guess an endpoint; a wrong port produces a
`READ_FAIL` row that looks like drift tooling working when it is not.

| Value | What it is | How to find it |
| --- | --- | --- |
| `MYSQL_BIN` | mysql client executable | `brew --prefix mysql-client`/bin/mysql. Dolt ships no `dolt sql --host` and no `dolt sql-client`, so an external client is required; it must support `--ssl-mode=DISABLED` (NOT `--skip-ssl`). |
| `REPOS_ROOT`, `GT_ROOT` | the two store roots | the parents of the paired bead stores |
| `REPOS_PORT`, `GT_PORT` | Dolt sql-server TCP ports | each server's `--config` yaml, or `lsof -nP -iTCP -sTCP:LISTEN` on its PID |
| `MYSQL_USER` | connecting user | usually `root` for a local Dolt sql-server |
| `TWIN_ALIASES` | `repos_db:gt_db` pairs | see Step 2 |

**Step 2 — Derive `TWIN_ALIASES` rather than asking for it.** Stores pair by
`dolt_database`; an alias is needed only where the two sides disagree. Print
both sides and add a pair for each mismatch:

```bash
for p in "$REPOS_ROOT"/*/ "$GT_ROOT"/*/; do
  m="${p}.beads/metadata.json"; [ -f "$m" ] || continue
  printf '%-34s %s\n' "$p" "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('dolt_database',''))" "$m")"
done
```

Every entry is a store whose two sides should be reconciled instead. An empty
map is the goal state — report the count to the user as outstanding work, not
as configuration.

**Step 3 — Write the conf.** Copy
[`assets/bead-drift.conf.example`](../../assets/bead-drift.conf.example), fill
in the values, then restrict it:

```bash
mkdir -p "${HOME}/.gc" && chmod 600 "$CONF"
```

**Step 4 — Verify by running it.** `sh scripts/bead-drift-report.sh`. A
correct setup prints one row per store and exits 0 or 1. Treat any `READ_FAIL`
row as a setup failure, not a result: it means an endpoint or database name is
wrong. Do not report success while a `READ_FAIL` stands.

## Optional — the weekly job

The report is **read-only by design**: every data-plane op (`bd dolt pull`,
`bd import`, push) requires the `authorize-git-operation` gate, which an
unattended job cannot obtain, and a proxied-mode store refuses sync outright.
So the job measures and reports; a human runs the gated union per flagged
store. Never extend this job to move bead data.

Write `~/Library/LaunchAgents/com.gascity.bead-drift.plist`, substituting the
real script path and an absolute `PATH`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.gascity.bead-drift</string>
  <key>ProgramArguments</key><array>
    <string>/bin/sh</string><string>PACK_ROOT/scripts/bead-drift-report.sh</string>
  </array>
  <key>StartCalendarInterval</key><dict>
    <key>Weekday</key><integer>1</integer>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>17</integer>
  </dict>
  <key>StandardOutPath</key><string>HOME/.gc/bead-drift.log</string>
  <key>StandardErrorPath</key><string>HOME/.gc/bead-drift.log</string>
</dict></plist>
```

Then load it and **confirm it is loaded** — the step that matters:

```bash
launchctl unload ~/Library/LaunchAgents/com.gascity.bead-drift.plist 2>/dev/null
launchctl load   ~/Library/LaunchAgents/com.gascity.bead-drift.plist
launchctl list | grep com.gascity.bead-drift || echo "NOT LOADED — the job will never run"
```

A plist on disk is not a running job. The sibling
`com.gascity.dolt-remotes-sync` sat unloaded for 80 days after its script path
was corrected, logging 164 KB of `No such file or directory` that nobody read,
because the edit was never followed by a load and a `launchctl list` check.
Verify the load, and read the first log line the job writes.

## See also

- `scripts/bead-drift-report.sh` — the report this configures
- `assets/bead-drift.conf.example` — the placeholder it is generated from
- `authorize-git-operation` — the gate every union the report recommends must pass
