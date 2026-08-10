# V2 Design Notes — per-recipient inbox + hybrid rotation

Resolves bead `as-3mv` ("Improve inbox: per-agent rotation + faster cycle").

## Problem (V1)

The original transport (`.claude/.agent-inbox.md`) was a single shared file rotated on calendar-day change. Two failure modes had accumulated:

1. **Cross-talk in reader context.** Every agent's `read` pulled the whole shared file even when filtering by `to: <uuid>`. With ~5 agents and ~hundreds of entries per day, the cost was significant context burn per check.
2. **Slow rotation.** Calendar-day rotation meant a single busy session could grow the inbox unboundedly for ~24h before rotation kicked in. The bead notes "contributes to context degradation".

## V2 changes

**Per-recipient inbox file.** Each recipient gets `.claude/inbox/<recipient-uuid>.md`. Readers open only their own file; cross-talk into reader context drops to zero. Senders write to the recipient's file, not a shared file.

**Hybrid rotation trigger.** First-fire-wins:

| Trigger | Threshold | Rationale |
|---|---|---|
| Time | 4 hours since file's first entry | Caps staleness at ~quarter-day, ~6× faster than V1 daily |
| Entries | 30 entries | Caps per-file reads at a small bounded size |
| Day | most recent `at:` is from prior calendar day | Safety net retained from V1 for low-traffic projects |

`30` and `4h` were chosen as a Goldilocks point: small enough that a `read --last 10` on a freshly-rotated file is almost never truncated, large enough that a moderately busy agent rotates once or twice a day rather than every few minutes. Both numbers are settable in `agent-inbox-rotate.sh` if a project needs different tuning.

**Archive layout.** Rotated files go to `.claude/inbox/archive/<uuid>-<YYYY-MM-DD-HHMM>.md`. The per-recipient prefix means a single archive grep across many recipients is just `grep ... .claude/inbox/archive/*.md`.

**Reserved `.acked/` directory.** V2 creates `.claude/inbox/.acked/` empty. This reserves the path for V3's per-message-file transport (`.claude/inbox/<recipient>/<unix_ts>-<sender>.md` with `.acked/` as the post-process landing zone). Doing this now means V3 doesn't require another path migration.

## Backwards compatibility

- **Auto-detect:** if `.claude/inbox/` doesn't exist but `.claude/.agent-inbox.md` does, `agent-send.sh` upgrades on the fly (creates `.claude/inbox/`, prints `LEGACY_INBOX_DETECTED` advisory).
- **Legacy `read` fallback:** if the per-recipient file is empty/missing AND the legacy `.agent-inbox.md` exists, `read` greps the legacy file for `to: <self-uuid>` and prefixes results with `LEGACY:`. Lets agents drain V1 messages without forcing migration.
- **One-shot migration:** `agent-inbox-migrate.sh` splits a V1 inbox into per-recipient V2 files in one pass, then renames the legacy file to `.agent-inbox-migrated-<stamp>.md` so the auto-detect path stops firing. Idempotent.

## Tradeoffs vs alternatives considered

| Alternative | Rejected because |
|---|---|
| **Per-message file** (`.claude/inbox/<recipient>/<ts>-<sender>.md`) — the next-step transport documented in V1 | Bigger jump than the bead asks for. V2 is the smallest change that fixes both failure modes. Reserved as V3 via the `.acked/` directory. |
| **Suffix-only naming** (`.claude/.agent-inbox-<uuid>.md`) | Forces an `ls .claude/*.md` glob to discover inboxes; clutters the project's `.claude/` dir with many files. Subdirectory groups them cleanly. |
| **Pure-time rotation** (every N hours) | Doesn't cap file size; a burst of 200 messages in 10 minutes still bloats reads. Entry count trigger handles bursts. |
| **Pure-size rotation** (every N entries) | A quiet inbox with 5 entries that sat for a week would never rotate, accumulating stale context. Time trigger handles slow drift. |
| **Per-role mailbox** (`.claude/inbox/role/<role>.md`) | Useful for broadcasts but needs an ack protocol so multiple readers don't double-process. Out of scope for this bead; can layer on later as `role-<name>.md` files since the routing layer is by file. |

## What is NOT changed

- Entry format inside the file (`---\nfrom:\nto:\nat:\nsubject:\n---\nbody`) is byte-for-byte identical to V1. Any parser that read V1 archives still reads V2 archives.
- The `to:` line stays in the entry header even though it's now implied by the filename. Keeps archives self-describing and lets a misroute be detected at read-time.
- `agent-chat.md` (the casual sibling) is untouched. It was never the source of the cross-talk problem.
- The mandatory tempfile-then-script send pattern is unchanged; it solves a permission-prompt issue orthogonal to the V1/V2 split.

## Deployment

The reference scripts in this skill folder (`scripts/agent-*.sh`) are the canonical implementations. The live invocation paths in `SKILL.md` examples and in `~/.claude/settings.json` permission allowlists still point at `~/.claude/scripts/agent-*.sh` — the user-scope copies must be synced with the in-skill references for V2 to be live in real coordination work. Until that sync happens, `agent-send.sh` keeps writing to the V1 shared file. Track the sync as a separate operations bead (filed alongside this PR).

## Test coverage

`tests/test_inbox.sh` exercises (each line maps to one PASS):

1. `send` creates a per-recipient file with correct `from:`/`to:`/`subject:`/body
2. Sending to two recipients yields two isolated files (no cross-talk)
3. Entry-count rotation trigger fires after 30+ entries
4. `migrate` splits a V1 inbox into per-recipient V2 files with correct entry counts and renames legacy file
5. `migrate` is idempotent (re-running on already-migrated project is a no-op)
6. Legacy auto-detect fires on first send into a project that still has `.claude/.agent-inbox.md`

Not yet covered (and noted as follow-ups, not blocking this PR):

- The 4-hour age trigger (requires either time-travel or a configurable threshold; the count trigger covers the same code path in practice).
- `agent-monitor.sh` restart behaviour (needs a long-running test harness).
- A concurrent-writer race on `rotate` (`mv` is atomic but two writers can both observe pre-rotation state; the existing `mv` failure handling already suppresses double-rotation).
