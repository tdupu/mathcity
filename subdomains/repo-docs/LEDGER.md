# LEDGER.md — the agent-side claim ledger

Parent: [README.md](./README.md). Design ADR 0004 binds: the ledger is
agent-side markdown, NEVER authoritative — humans edit tex freely and
will not update it; skills treat tex as ground truth and reconcile by
re-reading it, never the reverse. Nothing here appears in any PDF.

## Location

`scratch/LEDGER.md` (gitignored where the repo ignores scratch/). One
per repo; rebuilt by rescan when stale — human deletion must never
break a workflow.

## Row format

One row per claim:

```
| id | statement (short) | where | status | evidence | depends-on | doubt |
```

Cells never contain a literal `|`: write `\vert` in math, a slash in
prose.

- **id**: stable slug (`ord-sharp-formula`).
- **where**: file:label or scratch report path — the tex location is
  the identity; the row is cache.
- **status**: proved / conditional / computational / conjectural /
  imported / refuted — this six-way set lives ONLY here; scratch
  reports keep astra-dump's five-way claim separation (refuted enters
  at harvest, counterexample path in evidence). The tex stays binary
  (LX4).
- **evidence**: paths — proof package, computation, opened-source
  verification (track-down-reference).
- **depends-on**: ids the proof uses (resolve-dependencies maintains).
- **doubt**: doubt-run path + verdict, or empty. Promotion into
  notes.tex REQUIRES a recorded doubt run (router gate).

## Reconciliation rule

Any skill reading the ledger first spot-checks min(3, all) rows plus
every row the current operation touches against the live tex (the
`where` field); a mismatch invalidates the affected file's rows and
triggers its rescan first. Rescan contradictions go to
`contradiction-check`, never silent row edits.
