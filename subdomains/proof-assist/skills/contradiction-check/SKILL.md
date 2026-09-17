---
name: contradiction-check
description: Detect and LOUDLY report any later mathematical claim that contradicts an earlier one across a repo's canonical tex, scratch reports, and agent-side ledger — structured contradiction report plus refusal of the triggering operation; silent supersession is prohibited. Use when the user says "check for contradictions", "contradiction-check", "does this contradict what we have", before promoting any claim into notes.tex, when a harvested proof package conflicts with a recorded claim, or when a revision changes a stated formula or hypothesis. NEVER adjudicates which side is right (that is the human's, optionally via doubt); NOT source verification (track-down-reference) and NOT single-claim truth-probing (doubt).
---

# contradiction-check

Mechanism 2's fix (design record, survey 2026-09-18): the observed
wild failure is "the manuscript supersedes the conflicting claims in
the earlier sections of this report" — history silently overwritten.
Here a contradiction is a loud, recorded
event, and the operation that surfaced it stops.

## Step 0 — Scope

Claim sources, in authority order: the repo's canonical `.tex`
(LATEX.md's declared files — ground truth), scratch reports'
claim sections, the agent-side ledger if present (never authoritative;
reconcile by rescanning the tex — design ADR 0004).

## Step 1 — Collect

For a TARGETED check (a claim being promoted/written/harvested):
gather every recorded statement about the same objects/invariants.
For a SWEEP ("check the repo"): enumerate statement environments and
scratch claim lists. Report counts (RESOLUTION.md §5 in
`subdomains/repo-docs/` — zero claims collected where claims exist is
EVIDENCE-ABSENT, not a pass).

## Step 2 — Scan

Pairwise over the collected set: direct negation; incompatible
formulas for the same invariant; silently changed hypotheses (same
conclusion, weaker assumptions, no acknowledgement); a "corrected"
claim whose predecessor is still live anywhere. Quote BOTH sides with
file:line provenance. Classification is mechanical; truth is not
yours.

## Step 3 — On any contradiction: loud refusal

1. STOP the triggering operation (promotion, write, harvest) — it
   does not proceed (sweep mode: no operation to halt — 3.2 and 3.3
   still fire).
2. Write the contradiction report to
   `scratch/<date>-contradictions/report.md`: both quotes, provenance,
   which downstream claims depend on each side, and the refused
   operation. Never edit either side; never mark a winner.
3. Surface to the human: the report path plus a one-line statement per
   contradiction. Resolution (supersede via tagged revision, retract,
   or rule the claims compatible) is a human act; a doubt run may be
   suggested, never auto-launched as the resolution.

## Step 4 — Clean result

"0 contradictions among N claims checked (sources: …)" — counts
always; never a bare all-clear.

## Red flags

| Thought | Reality |
|---|---|
| "The newer result is obviously the corrected one" | Newer is a timestamp, not a verdict. Report both. |
| "I'll just update the old statement to match" | That is silent supersession — the prohibited move. |
| "It's only in a scratch report, not the tex" | Scratch claims feed promotions. In scope. |
