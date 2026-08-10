# File-or-sendback decision-review log — format spec

Canonical path: `<rig_root>/.beads/briefs/decisions/file-or-sendback.jsonl`
(registered as `route_log` in `assets/brief-pipeline/paths.toml`; rig-relative).

Append-only JSONL: one JSON object per line, one line per routed brief
decision. Never rewrite or delete lines. This log is the durable review
trail for post-decision routing — available for post-hoc review, NOT
surfaced proactively (the human adjudicator 2026-06-30 17:33: daily digest cancelled;
event-driven flow makes batch surfacing unnecessary).

## Entry schema

| Key              | Required | Type   | Meaning |
|------------------|----------|--------|---------|
| `bead_id`        | yes      | string | Source bead the decided brief was about. Empty string when the brief source was an artifact or request, not a bead. |
| `brief_slug`     | yes      | string | Slug of the decided brief (join key to `decisions/<slug>.toml`, the stack manifest, and the archive). |
| `decision`       | yes      | string | the human adjudicator's adjudication: `approve`, `reject`, `revise`, or `defer`. |
| `choice`         | yes      | enum   | `FILE` or `SEND-BACK`. |
| `target_bead_id` | for FILE | string | Successor bead that gets a new brief. Required non-empty when `choice` is `FILE`. |
| `reason`         | yes      | string | One-line justification for the choice. |
| `confidence`     | no       | enum   | `high`, `medium`, `low` — from the lean-investigation emission when present. |
| `source`         | no       | enum   | Who decided the routing: `lean-investigation`, `refinery`, or `inline-fallback`. |
| `timestamp`      | yes      | string | RFC3339 UTC. |
| `agent_id`       | yes      | string | Identity of the agent that wrote the entry. |

Validated by `assets/scripts/checks/brief-check.sh file-or-sendback-log`
(wrapper: `brief-file-or-sendback-log-required.sh`): the file must be
valid JSONL and the latest entry must carry every required key, a valid
`choice`, and a non-empty `target_bead_id` when the choice is `FILE`.

## Choice semantics

- **FILE** — a successor bead is known and ready. Downstream: pour
  `brief-prep` with `source=<target_bead_id>`. FILE only when the
  successor actually exists and is ready; filing speculative briefs is
  the token-waste this gate exists to stop.
- **SEND-BACK** — the adjudication is self-contained; no follow-up work
  is triggered and the brief archives. Downstream: ring
  `brief.archive_requested` (caught by the brief-archive-on-request
  order). Default when uncertain — but never SEND-BACK a decision whose
  record names a follow-up bead.

the human adjudicator's constraints (2026-06-30): minimize send-back/re-briefing cycles
(they cost tokens), be defensive about successor detection (never lose a
follow-up bead), and keep every choice + reason reviewable (this log).

## Writers

1. **file-or-sendback-route** formula (the post-decision gate) — the
   primary writer today. Consumes a lean-investigation emission when the
   decision record carries `route_choice` / `route_target_bead` /
   `route_reason`; falls back to inline lean rules otherwise.
2. **Refinery** (once the refinery-role expansion lands, gsp-itx) — the
   refinery calls the lean-investigation formula (gsp-cst) post-merge and
   writes its FILE/SEND-BACK outcome here. This log is the audit target
   for refinery routing decisions.

## Event contract (the bells)

| Event type                | Emitted by | Caught by |
|---------------------------|------------|-----------|
| `brief.decided`           | brief-record-decision `emit-decided-event` step; refinery post-merge (gsp-itx) | `post-decision-file-or-sendback` order → pours `file-or-sendback-route` (polecat pool) |
| `brief.archive_requested` | `file-or-sendback-route` on SEND-BACK | `brief-archive-on-request` order → pours `brief-archive-sweep` (dog pool) |
| `brief.stack_low`         | `file-or-sendback-route` stack-check step when `brief-stack-low-check.sh` exits 0 | brief-watchdog-refill event order (gsp-i9j) → refill (dog pool) |

Events are best-effort wake-ups (`gc event emit` always exits 0; the bus
does not guarantee durable persistence). Durable state — decision records,
this log, bead metadata — is the source of truth. Every consumer scans
durable state on wake, so a lost event delays work until the next bell or
cooldown backstop instead of losing it.

## Example entries

```jsonl
{"bead_id":"he-abc1","brief_slug":"he-abc1-fix","decision":"approve","choice":"FILE","target_bead_id":"he-abc2","reason":"successor he-abc2 (follow-up tests) is open and ready","confidence":"high","source":"lean-investigation","timestamp":"2026-07-01T21:04:11Z","agent_id":"gascity-packs/gastown.furiosa"}
{"bead_id":"","brief_slug":"skill-cleanup-brief","decision":"reject","choice":"SEND-BACK","reason":"self-contained rejection; no follow-up bead referenced","source":"inline-fallback","timestamp":"2026-07-01T21:09:42Z","agent_id":"gascity-packs/gastown.furiosa"}
```
