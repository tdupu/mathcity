# Evidence: the brief gate rejects already-adjudicated briefs

**Bead:** `mc-8ehd0` (P0, open) — *"brief gate moves ALREADY-ADJUDICATED briefs to
.rejected/ — 7 of Taylor's approve verdicts bounced"*.
**Measured:** 2026-08-28, against the live city at `<city-root>/mathcity`.
**Plan:** `docs/superpowers/plans/2026-08-28-adjudicated-brief-rejection-guard.md`, Task 1.

Every number below was re-derived here. The plan carried a prior measurement of
the same figures; re-measuring was cheaper than inheriting a number that had
been relayed twice before anyone counted.

## The three counts

| # | Measurement | Value |
|---|---|---|
| 1 | Slug directories in `.beads/briefs/.pile/.rejected/` | **24** |
| 2 | Of those, briefs carrying a non-empty `verdict:` | **8** |
| 3 | Rejection records citing `"standard brief missing provenance metadata"` | **22** of 24 |

The directory **exists**. That check is load-bearing: had it been absent,
`find` would error and `wc -l` would print `0`, and a reader would conclude
"the defect does not reproduce" from a directory that was never there. That is
`unknown`, not zero (P6.2).

All 8 also carry `status: adjudicated`; the `status`-count and the
`verdict`-count agree at 8, so neither field is carrying decisions the other
misses in this corpus.

## Does it match the bead's claim of 7?

**No, and the bead is wrong in two ways.** The count of discarded human
decisions is **8**, not 7. Seven of those are `verdict: approve`; the eighth
(`mc-0nf`) is `verdict: reject`.

`mc-8ehd0`'s title — *"7 of Taylor's approve verdicts bounced"* — is right about
the approves and silently drops the reject. A discarded `reject` is the same
defect: a human decided, and the machine threw the decision away. The corrected
figure is **8 adjudicated briefs discarded, of which 7 are approvals.**

## The eight discarded decisions, verbatim

| Slug | Verdict | Rejection `source_path` | `rejected_at` | Reason recorded |
|---|---|---|---|---|
| `mc-28w3` | approve | `.pile/mc-28w3.md` | 2026-08-26T23:36:34Z | standard brief missing provenance metadata |
| `mc-0gc6` | approve | `.pile/mc-0gc6.md` | 2026-08-26T07:20:16Z | standard brief missing provenance metadata |
| `mc-2svt` | approve | `.pile/mc-2svt.md` | 2026-08-26T23:36:34Z | standard brief missing provenance metadata |
| `mc-13zb` | approve | `.pile/mc-13zb.md` | 2026-08-26T15:20:22Z | standard brief missing provenance metadata |
| `mc-0da`  | approve | `.pile/mc-0da.md`  | 2026-08-26T07:20:16Z | standard brief missing provenance metadata |
| `mc-0nf`  | **reject** | `.pile/mc-0nf.md`  | 2026-08-26T07:20:16Z | standard brief missing provenance metadata |
| `mc-0xnk` | approve | `.pile/mc-0xnk.md` | 2026-08-26T15:20:22Z | standard brief missing provenance metadata |
| `mc-13e0` | approve | `.pile/mc-13e0.md` | 2026-08-26T15:20:22Z | standard brief missing provenance metadata |

Every one of the eight has frontmatter consisting of exactly two keys:

```
---
status: adjudicated
verdict: approve
---
```

and **no** `source_bead`, `artifact`, or `brief_bead` key. That absence is the
whole mechanism, below. All eight rejections are dated 2026-08-26, in three
batches, matching the fast-drain's scheduled cadence rather than any human
action.

## The re-entry mechanism (Task 1 Step 4)

**One sentence:** an adjudicated brief whose frontmatter was rewritten down to
`status` + `verdict` sits in `.pile/`, which is the fast-drain's *input* queue,
and `main()` re-scans that whole directory on a schedule and re-gates every
`.md` in it with no notion that a verdict is terminal.

Read at source in `assets/scripts/brief-shuffle-fast-drain.py`:

- `main()` sets `pile = brief_root / ".pile"` and enumerates it. There is no
  filter for already-decided items.
- `process_item()` calls `evaluate()`, then `action = "promote" if not reason
  else "reject"`. `evaluate()` never reads `verdict` or `status`.
- `profile_error()` for the `standard` profile returns
  `"standard brief missing provenance metadata"` when none of `source_bead`,
  `artifact`, `brief_bead` is present — which is exactly the shape all 8 have.
- `reject_staged()` then moves the file to `.pile/.rejected/<slug>/brief.md` and
  writes `rejection.json` beside it.

Each rejection record's own `source_path` field says `.pile/<slug>.md`,
confirming the items were re-gated from the pile, not from a fresh producer
deposit.

**Consequence for the plan's framing (P1.17):** the root cause has two halves.
The proximate one — `evaluate()` re-judging a decided brief — is what the plan's
Task 4 fixes, and it is the one every rejection provably passes through. The
other half is *why* adjudicated briefs are sitting in the drain's intake
directory with their provenance metadata stripped; that is the intake guard
deferred in the plan's §E, and it remains open. The guard implemented here is
therefore correctly described as **the fix for the discarding**, and a
**defence in depth** with respect to the re-entry.

## What the guard must not do

A rejected brief with **no** verdict is the gate working correctly. 16 of the 24
are exactly that, and they must keep being rejected. The tests written for this
fix carry explicit negative controls on that point (P6.2): a check that could
not fail is worse than no check.
