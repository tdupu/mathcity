# DRAFT upstream issue — NOT FILED

**Target:** `gastownhall/gascity` · template `bug_report.yml`

**Status: draft only.** P3.2 requires an approved `create-issue-briefed` brief
before any upstream issue is filed, and **that path is currently unavailable on
this fleet**: the formula needs a source bead (writes blocked on
`~/repos/mathcity` by its v64/v67 skew, denied on kolchin) and its terminal step
runs on `mathcity.brief-operator`, which `gc status` reports as
`scaled (min=0, max=0) stopped` (tdupu/mathcity#274). So the body is drafted
here, template-complete, for whoever can run the briefed path. **Nothing has
been filed.**

Body below is paste-ready against `bug_report.yml`, whose required sections are
`Before you continue`, `Gas City version`, `Environment`, `Reproduction`,
`Expected behavior`, `Actual behavior`.

---

### Before you continue

- [x] Searched open and closed issues for `compact quarantine`, `compact-quarantine`, `notify_count`, `unknown recipient`, `ResolveSessionIDByExactID`.
- [x] Measured on a live city, not inferred — kolchin HQ, 2026-10-01.
- [x] The alerting feature itself is present and its release gate records all criteria PASS, which is what makes this a delivery defect rather than a missing feature.

### Gas City version

`gc version` → `dev` (same on both machines in this fleet). Compact-alert slice
corresponds to the release gate `ga-uz6mr1-compact-quarantine-alerts-v2`,
reviewed head `29f847304baaf02497735833b77c12917cafce52`.

### Environment

macOS. City `HQ` at `/Users/gascity-user/HQ`, supervisor-managed (PID 51181,
alive 16d). Dolt pack per-project mode. Mayor agent template `mayor.mayor`,
live session id `hq-v0ciy`.

### Reproduction

1. Let a `dolt compact` run write a quarantine marker — here
   `~/HQ/.gc/runtime/packs/dolt/compact-quarantine/hq`, created
   `2026-09-08T01:34:36Z`.
2. Let the compact script's alert path run on subsequent compactions. It is
   designed to alert on *existing* markers too, per the release gate's criterion
   2 ("alerts on fresh quarantine markers, existing quarantine markers in
   flatten/bare-GC paths, and stale pending-push markers").
3. Read the marker.

Observed after 23 days:

```
seen_count=285
notify_count=0
last_notified_ts=
last_notified_reason=
last_notify_error=gc mail send: unknown recipient "mayor": session not found: "mayor"
```

### Expected behavior

The operator is alerted that a Dolt compact quarantine exists on the `hq`
database. The release gate's criterion 2 records validator coverage for exactly
this case, including `TestCompactScriptFreshQuarantineMarkerAlertsDefaultMayor`
and `TestCompactScriptExistingQuarantineMarkerAlertsDefaultMayorBeforeFlattenAndBareGC`.

### Actual behavior

**285 alert attempts over 23 days produced 0 deliveries.** Deterministic, not
intermittent — `notify_count` never left 0 and `last_notified_ts` is empty.

The alerter's default recipient is the **agent** name `mayor`
(`GC_DOLT_COMPACT_ALERT_TO` default). `gc mail send`'s recipient resolution goes
through `resolveMailRecipientIdentityCached` (`cmd/gc/cmd_mail.go:1054`), whose
first step is `session.ResolveSessionIDByExactID` — a **session** lookup. There
is no session named `mayor`; the live session id is `hq-v0ciy`.

Note `internal/mail/resolve.go::ResolveRecipient` *would* accept bare `"mayor"`:
it matches on `AgentEntry.Name` and canonicalises to the qualified
`mayor.mayor`. That resolver is not the one the send path calls. So the two
recipient resolvers in the codebase disagree about whether an agent name is a
valid recipient, and the alerter was written against the permissive one.

**Why the tests did not catch it:** they assert the "default mayor" recipient in
an environment where that recipient resolves. On a live city the same string
does not, so the gate passed on a contract production does not honour. This is
the shape where a feature ships, its tests are green, and the live path has
never once succeeded.

**One hypothesis not confirmed, flagged rather than asserted:** the inner error
text `session not found` matches `internal/runtime/tmux/tmux.go`'s
`ErrSessionNotFound`, and on this host `tmux` is installed at
`/usr/local/bin/tmux` but is **absent from the non-login `PATH`**. If the
compact script's environment lacks tmux, *every* recipient would fail this way,
not just `mayor`. That would also explain the perfect determinism. Confirming it
requires a `gc mail send` from the script's own environment, which was not
available to the reporter.

**Suggested directions** (not a prescription — the maintainers own the choice):

1. Have the send path fall back to `internal/mail/resolve.go::ResolveRecipient`
   when an identifier is not a session id, so an agent name is a first-class
   recipient and the alerter's default works as its tests assume.
2. Make a failed alert loud at the point of failure rather than recorded only in
   `last_notify_error` inside the marker it is trying to announce. A notifier
   whose failure is visible only in the artifact nobody has been told about is
   unobservable by construction — 285 sightings produced no signal anywhere a
   human looks.
3. Add a validator case that resolves the recipient the way the live path does,
   so a green test implies a deliverable alert.

Item 2 is the one worth doing regardless of how 1 is resolved: it is the reason
this went 23 days unnoticed rather than being caught on the first compaction.
