---
name: communicate-with-other-agent
description: |
  Send and read messages between concurrent agents. TWO channels:
  (1) the LIVE peer channel — the `SendMessage`/`ListAgents` tools, CLAUDE-CODE ↔
  CLAUDE-CODE ONLY, preferred for any Claude peer running now; (2) the DURABLE file
  inbox under <city-root>/.claude/inbox/, which reaches ANY agent — Claude or not
  (Codex, other harnesses) — and offline peers. Use for "tell the other agent",
  "message agent X", "send this to <UUID>", "check the agent inbox".
---

# communicate-with-other-agent

**First: is the peer a Claude Code session, or a non-Claude agent?**

- **Claude Code ↔ Claude Code** — both channels are available; prefer the LIVE
  channel (Part 1) when the peer is running.
- **Any non-Claude agent** (a Codex worker like `c0de0000`, or any other
  harness/tool) — the LIVE channel does **NOT** reach it. `ListAgents` only ever
  lists Claude Code peer sessions, and `SendMessage` can only target those. A
  non-Claude agent will never appear there, so the **file inbox (Part 2) is the
  ONLY way to reach it** — and only if it polls the inbox. If you can't find a peer
  in `ListAgents`, that's expected when it isn't Claude Code; don't hunt for it —
  go straight to the file inbox.

For a Claude↔Claude pair, pick a channel by whether the peer is running right now:

| | LIVE peer channel (`SendMessage`) | DURABLE file inbox (`agent-send.sh`) |
|---|---|---|
| Mechanism | in-process tools, over `/tmp/cc-socks/*.sock` | one `.md` file per message on disk |
| Reaches | only sessions **running now** (a `ListAgents` row) | any peer, even offline / not-yet-started |
| Delivery | enqueues, drains at the peer's next tool round | sits on disk until the peer's monitor reads it |
| Needs | peer to be live (+ approval, see caveat) | peer's **inbox monitor ON** (STEP 0) |
| Survives session death | no | yes |

**Default to the LIVE channel when the peer is up.** It does NOT depend on
`.agent-names.map`, so it routes around map defects (e.g. gascity #191, which lost
messages when a UUID was unmapped). Use the file inbox for durability, for peers
that are offline, or for anything that must survive session death.

---

# PART 1 — LIVE peer channel (`SendMessage` / `ListAgents`) — PREFERRED

**Claude Code ↔ Claude Code ONLY.** `ListAgents` lists only live Claude Code
sessions; `SendMessage` can target only those. Non-Claude agents (Codex, other
harnesses) are unreachable here — use Part 2 for them.

`ListAgents` and `SendMessage` are tools, not shell. No inbox, no UUID, no map.

### Send
1. **`ListAgents`** — lists every session running now. Each row is `name [ref]`
   (e.g. `QUIMBY 49 [918fb4]`, `gt-4f [9017e0]`). **The name is the address.**
2. **`SendMessage`** `{to: "QUIMBY 49", summary: "…", message: "…"}`.
   - If it errors "not an agent in this conversation, re-send with the ref",
     re-send with the ref appended: `to: "QUIMBY 49 [918fb4]"`.

### Reply
Incoming arrives as `<cross-session-message from="uds:/tmp/cc-socks/NNNNN.sock"
from-name="X">`. **Copy `from-name` as your `to`** to reply.

### ⚠️ CAVEAT — desktop-app recipients hold every message for user approval
A session's `entrypoint` decides whether it accepts live messages silently:

- **`cli` sessions** accept inbound `SendMessage` **directly** — instant, seamless.
- **`claude-desktop` sessions** (`peerFeatures: ["notify_idle"]`) **hold each
  inbound message for that tab's user to approve.** You get back a "held for the
  recipient user's approval" delivery notice; the peer's Claude sees **nothing**
  until a human clicks approve at that tab. This is per-message, not one-time — and
  **the hold expires**: if no human approves in time you get a follow-up "not
  approved before expiry" notice and the message is dropped, never delivered.

So the live channel is frictionless **CLI ↔ CLI**. To a desktop-app peer it still
works, but a human must approve each message at the destination — do **not** assume
delivery, do **not** resend (that just queues another hold that will also expire),
and tell your user the message is waiting on approval at the peer's tab. If the peer
is desktop-app and no human is watching it, **the live channel will silently expire —
use the file inbox (Part 2)** with the peer's monitor on instead.

### Resolve an anonymous `gt-XX` row → role, entrypoint, uuid
`ListAgents` names are auto-derived (`nameSource: derived`), so a row like `gt-4f`
does not say who it is. Two local files close the gap — join them on the uuid:

- `~/.claude/sessions/<pid>.json` — one per live session:
  `{sessionId (=uuid), name (the ListAgents name), entrypoint, kind, status,
  messagingSocketPath}`.
- `~/.claude/agents-roster.json` — maps role-name → uuid.

```bash
python3 - <<'PY'
import json,glob
roster={v['uuid']:k for k,v in json.load(open('/Users/tdupuy/.claude/agents-roster.json'))['agents'].items()}
print(f"{'ROW':<12}{'ROLE':<11}{'ENTRYPOINT':<16}STATUS")
for f in glob.glob('/Users/tdupuy/.claude/sessions/*.json'):
    d=json.load(open(f))
    print(f"{str(d.get('name')):<12}{roster.get(d.get('sessionId'),'-'):<11}{str(d.get('entrypoint')):<16}{d.get('status','?')}")
PY
```

Use `entrypoint` from this table to know, *before* sending, whether the peer will
accept directly (`cli`) or hold for approval (`claude-desktop`).

### Live-channel conventions
- Peers see ONLY what you put in `SendMessage` — your plain-text output is invisible
  to them. To communicate you MUST call the tool.
- One topic per message; ACK proposals before acting.
- Don't start cross-agent threads without user approval.
- Permission is per-session: never ask a peer to do something blocked in your own
  session (permission laundering) — route it back to your user.

---

# PART 2 — DURABLE file inbox (V2 — username/date layout)

The fallback for offline peers and anything that must survive session death.
**Requires the recipient's inbox monitor to be ON (STEP 0)** — a peer whose monitor
is off (common for desktop-app sessions parked between turns) will never see a file
message. If you need it read now and the peer is live, use Part 1 instead.

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

## Send (file inbox)

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

## Read (file inbox)

`Read` the newest file in your canonical folder, or filter the flat path:
`grep -A30 "^to:.*<YOUR_UUID>" <city-root>/.claude/inbox/<YOUR_UUID>.md`.

## Conventions (file inbox)

- Subject ≤80 chars (it becomes the filename slug). Sign the last line
  `-- <uuid-prefix> (<name>)`.
- One topic per message. ACK proposals before acting.
- Don't start cross-agent threads without user approval.

---

## Choosing a channel (summary)

0. Peer is **not a Claude Code session** (Codex, other harness) → **file inbox** (Part 2)
   is the only option; it must poll the inbox. `ListAgents`/`SendMessage` cannot reach it.
1. Claude peer running now AND a `cli` session → **LIVE `SendMessage`** (Part 1). Best case.
2. Claude peer running but `claude-desktop` → LIVE works, but each message is **held for
   approval at that tab**. Send once, tell your user it's awaiting approval there; or use
   the file inbox if their monitor is on.
3. Peer is offline / must survive session death → **file inbox** (Part 2), and confirm
   their monitor is on or it won't be read.
