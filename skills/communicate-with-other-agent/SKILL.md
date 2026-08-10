---
name: communicate-with-other-agent
description: |
  Send and read messages between concurrent Claude Code agents via the V2
  daily-folder inbox under <city-root>/.claude/inbox/. Use for "tell the other agent",
  "message agent X", "send this to <UUID>", "check the agent inbox".
---

# communicate-with-other-agent (V2 — username/date layout)

Inbox base: `<city-root>/.claude/inbox/`.
Your UUID: `$CLAUDE_CODE_SESSION_ID`, else the stem of the newest
`*.jsonl` in `~/.claude/projects/<hash>/`. Format `[a-f0-9-]{36}`.

## Layout (the human adjudicator ruling 2026-07-22)

Every message is ONE file. `agent-send.sh` writes two paths:

- **Canonical** (read this): `<city-root>/.claude/inbox/<name>/<YYYY-MM-DD>/<HH-MM-SS>-from-<sender>-<subject-slug>.md`
  where `<name>` is the **recipient's** human-readable role name (`repo-side-landing-agent`,
  `mayor`, `clerk`, ...) from the UUID-to-name map. Unknown
  UUIDs fall back to their 8-char prefix, so routing never fails.
- **Flat backward-compat** (legacy monitors): `<city-root>/.claude/inbox/<TO-UUID>.md`
  — appended. The `to:` line still carries the raw UUID, so
  `grep '^to:.*<UUID>'` keeps working during cutover.

To add/rename a role without editing the script, append a line
`<uuid> <name>` to `<city-root>/.claude/inbox/.agent-names.map`.

## STEP 0 — Monitor your inbox dir (do first, keep alive)

Watch YOUR canonical folder for new message files (one file per message).
Resolve `<yourname>` from the map (e.g. `repo-side-landing-agent`). Single-shot byte/existence
watch, re-armed each pause — do NOT stack monitors:

```bash
DIR=<city-root>/.claude/inbox/<yourname>/$(date +%Y-%m-%d)
before=$(ls -1 "$DIR" 2>/dev/null | wc -l)
# re-check at each pause; when count grows, Read the newest file:
ls -1t "$DIR" 2>/dev/null | head
```

Backup tail-check on the flat path (still appended):
`grep -n "^to:.*<YOUR_UUID>" <city-root>/.claude/inbox/<YOUR_UUID>.md | tail`

The monitor dies on harness kills / session recovery — re-arm before each send.

## Send

Write the body with the Write tool (never `>>`), then send. Run from `<city-root>`
so the CWD walk-up resolves the inbox base to `<city-root>/.claude/inbox/`:

```bash
cd <city-root>
bash ~/.claude/scripts/agent-send.sh "$FROM_UUID" "$TO_UUID" "Subject" /tmp/body.md
```

Args: `FROM_UUID  TO_UUID  "Subject"  BODY_FILE  [INBOX_DIR_OVERRIDE]`. The 5th
arg is **optional** — omit it and the script resolves the inbox base via
`$CLAUDE_INBOX_DIR` or the CWD walk-up. (Do NOT pass the old shared
`.agent-inbox.md` file as a 5th arg — that was V1.)

## Read

`Read` the newest file in your canonical folder, or filter the flat path:
`grep -A30 "^to:.*<YOUR_UUID>" <city-root>/.claude/inbox/<YOUR_UUID>.md`.

## Conventions

- Subject ≤80 chars (it becomes the filename slug). Sign the last line
  `-- <uuid-prefix> (<name>)`.
- One topic per message. ACK proposals before acting.
- Don't start cross-agent threads without user approval.
