---
name: check-mayor-mail
description: Mayor-facing mail triage routine — scan the gc mail inbox, surface [ESCALATE CRITICAL/HIGH] first, and catch escalations the fleet raised into a void ("no live mayor session to receive"). Use when the user says "check the mail", "check mayor mail", "any mail for the mayor", "what's in the inbox", "any escalations", "anything the fleet is trying to tell me". Read-only triage over gc mail (the durable, bead-backed channel). NOT generic send/read reference (that is core.gc-mail) and NOT the inter-agent inbox (that is communicate-with-other-agent). Recommended model: Sonnet.
---

# check-mayor-mail

Triage the Mayor's `gc mail` inbox and surface what actually needs the Mayor —
escalations first. `gc mail` is the **durable, bead-backed** channel (survives
session death), which is exactly why the fleet routes escalations + handoffs
through it. When there is no live Mayor session, those escalations **pile up
unheard** — this routine catches them.

> Provenance: QUIMBY 36 (2026-08-05) found CRITICAL/HIGH escalations (hecke disk
> near-full; a 13GB `.repo.git` in HEAD stalling fleet-wide worktree-prep) that
> had been raised into a void — "no live mayor session found to receive it." The
> Mayor's mail is not optional to scan.

## Channel model (know which one you're reading)

| Channel | Command | Durable? | Use |
|---|---|---|---|
| **gc mail** | `gc mail inbox` / `gc mail read <id>` | YES — bead-backed, survives session death | escalations, handoffs, structured protocol messages (this skill) |
| gc nudge | `gc session nudge <id>` | NO — ephemeral | routine agent-to-agent pokes (not this skill) |
| agent inbox | `communicate-with-other-agent` | file-based | direct Mayor↔BART/clark/Codex messages (not this skill) |

Default to **nudge** for routine agent chatter; **mail** is for what must
survive (`bd recall agents-mail-vs-nudge`).

## Procedure

1. **Scan the inbox:**
   ```bash
   gc mail inbox
   ```
2. **Triage by subject tag, most-urgent first:**
   - `[ESCALATE CRITICAL]` — read immediately; the Mayor (and Overseer) are the
     intended receivers. Common: Dolt unreachable / connection storm, disk
     near-full, supervisor degraded.
   - `[ESCALATE HIGH]` — read next; actionable fleet problems (worktree-prep
     stalls, latency/timeouts, `.repo.git`-in-HEAD bloat).
   - `[HIGH]` / `[MEDIUM]` — advisories (Dolt latency, reaper anomalies, JSONL
     spikes, backup-sync failures). Skim for patterns; a repeated MEDIUM is a
     real signal.
   - `[COORDINATION]` — cross-agent reconcile requests (duplicate molecules,
     etc.) — route, don't ignore.
3. **Read the load-bearing ones in full:**
   ```bash
   gc mail read <id>
   ```
4. **Watch for the "no live mayor session" tell.** Escalations often note they
   were addressed to the Mayor but *"no live mayor session found."* Those went
   unheard while raised — treat them as a **backlog of missed alarms**, not old
   news. The root cause named in one may be actionable today (e.g. disk / bloat).
5. **Act or route** — a CRITICAL is a Mayor action (or a dispatch); an advisory
   is context. Never silently mark-read an unread CRITICAL/HIGH.

## Anti-patterns

- **Don't treat the inbox preview as the whole story** — the first-3-message
  preminder in the session banner is not triage; run `gc mail inbox` and read
  the escalations.
- **Don't dismiss a repeated MEDIUM.** N identical `Dolt health advisory` /
  `reaper anomaly` MEDIUMs is a trend (latency creep, store bloat), not noise.
- **An unheard escalation is not stale** just because it's hours old — if no
  Mayor was live to receive it, its root cause may be live right now.

## What this skill does NOT do

- ❌ Send mail / compose inter-agent messages (that is `core.gc-mail` /
  `communicate-with-other-agent`).
- ❌ Nudge or dispatch (read-only triage; acting on a finding is a separate step).
- ❌ Cover the file-based agent inbox (`communicate-with-other-agent`).
