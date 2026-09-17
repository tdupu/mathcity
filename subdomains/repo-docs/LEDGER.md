# LEDGER.md — the agent-side claim ledger convention

Parent: [README.md](./README.md). Design ADR 0004 binds: the ledger is
agent-side markdown, NEVER authoritative — humans edit tex freely and
will not update it; skills treat the tex as ground truth and reconcile
the ledger by re-reading the tex, never the reverse. Nothing here is
visible in any PDF or demands human attention.

## Location

`scratch/LEDGER.md` in the repo (gitignored with scratch/ where the
repo ignores scratch). One file per repo; rebuilt by rescan whenever
stale — deletion by a human must never break a workflow.

## Row format

One row per tracked claim:

```
| id | statement (short) | where | status | evidence | depends-on | doubt |
```

- **id**: stable slug (`ord-sharp-formula`).
- **where**: file:label or scratch report path — the tex location is
  the identity; the row is cache.
- **status**: proved / conditional / computational / conjectural /
  imported — the five-way taxonomy lives ONLY here and in scratch
  reports (astra-dump's contract); the tex stays binary (proved or
  not, LX4).
- **evidence**: paths — proof package, computation, opened-source
  verification from track-down-reference.
- **depends-on**: ids this claim's proof uses (resolve-dependencies
  maintains).
- **doubt**: path + verdict of the recorded doubt run, or empty.
  Promotion of a claim into notes.tex REQUIRES a recorded doubt run
  (router gate).

## Reconciliation rule

Any skill reading the ledger first spot-checks k rows against the live
tex (the `where` field); a mismatch invalidates the row set for the
affected file and triggers a rescan of that file before proceeding.
Contradictions surfaced during rescan go to `contradiction-check`, not
to silent row edits.
