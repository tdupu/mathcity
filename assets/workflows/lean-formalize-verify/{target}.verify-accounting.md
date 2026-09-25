# Reconcile sorries, gap entries and beads

## The three-count invariant

    count(sorry/admit in the Lean project)
      == count(named gap entries in the gap document)
      == count(open beads for those gaps)

All three MUST be equal. This is the definition of done for a bounded formalization
scope: every hole is named in the manuscript and tracked as work.

## What to do

1. Count `sorry` and `admit` occurrences in the project. Use an uncapped search —
   do not pipe through `head`, which silently truncates and manufactures a low
   count that makes the invariant appear satisfied.
2. Count named gap entries in `gap_document` (**{{gap_document}}**).
3. Count open beads for those gaps.
4. Compare. If they differ, create what is missing — a gap entry, a bead — or
   remove what is stale. Then recount.

## Report

The three counts, whether they match, and the full list pairing each `sorry` with
its file:line, its gap entry and its bead id. If they do not match after
reconciliation, report FAIL and say which are unmatched. Do not report a match you
did not verify by counting.
