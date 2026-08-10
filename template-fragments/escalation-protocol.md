## Escalation Protocol

When you are blocked mid-process and cannot make progress without human input,
file an escalation bead immediately rather than spinning or halting silently.
Stalled work wastes running compute and may block a downstream chain.

Use the escalation helper script at its canonical absolute location:

```
.gc/scripts/escalate.sh \
  --title "<concise summary of the block>" \
  --body  "<detail: what you tried, what you need>" \
  --priority <N>
```

TODO(Phase 2): absolute path required — an agent's work dir is not the pack
root, so a pack-relative path cannot be resolved reliably. Replace with a
pack-root mechanism when one exists (plan Global Constraints carve-out).

The script creates a bead, flags it with the `human` label, and for P0/P1
immediately sends a mail to the human overseer and fires a macOS notification.

If the script is absent, escalate manually: `bd create --type=task
--priority=<N> --description "<detail>" "<title>"`, then
`bd label add <bead-id> human`.

### Priority bar

| Level | Meaning | Immediate ping? |
|-------|---------|-----------------|
| P0 | Critical: work is completely blocked and affects other agents or live output | yes |
| P1 | Urgent: a judgment step or formula gate cannot proceed without human clarification | yes |
| P2 | Normal: a question or ambiguity that can wait until the next review cycle | no |
| P3–P4 | Low: cosmetic or deferrable observations for the human adjudicator to review at leisure | no |

**P0/P1 bar:** use P0 or P1 only when leaving the block unresolved would waste
running compute (e.g. a looping retry) or prevent a downstream bead from
starting. For anything that can safely wait, use P2 or lower.

### When to escalate

- A formula judgment step fails and the failure mode requires the human adjudicator's decision
  (not just a retry or a skip).
- A gate is `BLOCKED` and you have no documented path to resolve it yourself.
- An external dependency (repo, service, credential) is unavailable and
  blocking all further progress on the claimed bead.

### What NOT to do

- Do not spin on a blocked step issuing repeated retries without escalating.
- Do not close your claimed bead before escalating; the open bead is evidence
  that work is in progress.
- Do not escalate for routine ambiguities you can resolve with available
  documentation or a safe default.
