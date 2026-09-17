---
name: check-adr
description: Read-only audit of a repo's ADR.md decision record (AR rules) — entry shape, append-only numbering, decisions-live-here-once, no ad-hoc decision files. Use when the user says "check adr", "check-adr", "is this decision recorded", "audit the decision record", or when a review finds decision text scattered across README/AGENTS/CONVENTIONS files. Companion: new-repo-adr-policy (sole write path). NOT for creating entries and NOT for bead-tracked decisions (bd decision beads are the city-side channel; ADR.md is the repo-side record).
---

# check-adr

Audits the repo's **own** `ADR.md` against its AR rules. RED baseline:
`baselines-phase1.md` scenario C in the design record — unguided agents
invent CONVENTIONS.md, restate decisions into AGENTS.md, and commit
unprompted (survey mechanism 12; AR3 drift). This skill detects exactly
that.

## Step 0 — Resolve

Run the shared preamble: `subdomains/repo-docs/RESOLUTION.md`.
On miss: instantiate `subdomains/repo-docs/templates/ADR.md`
and interrupt. No approved resolution → DEFER, stop.

## Step 1 — Enumerate

Count ADR entries; `git log --follow ADR.md` for history. Zero entries
is legitimate in a fresh repo — report the count, not a violation.

## Step 2 — Check, per rule ID

- **AR1** — parse every entry: heading shape, Date, Status, Decision,
  Why. Quote malformed entries.
- **AR2** — numbering 1..n, no gaps; git history shows no deletions or
  renumbering; superseded entries tombstoned, not removed.
- **AR3** — scan the repo (`grep -ril 'decided\|convention\|policy'`
  over README*, AGENTS.md, CONVENTIONS*, docs/) for decision text whose
  home should be ADR.md or that restates an ADR entry. Ad-hoc decision
  files (CONVENTIONS.md and kin) are findings with a migration
  recommendation. Report match counts per RESOLUTION.md §5.
- **AR4** — entries name who decided; agent-drafted entries with no
  human attribution are findings.

## Step 3 — Report

```
CHECK-ADR <repo> <date>
Resolution: <found | instantiated+approved | DEFER>
Checked: <N entries, N candidate decision-texts scanned>
Findings: <rule-ID>: <location>: <one line>
Verdict: PASS | ADVISORY-PASS | FAIL | DEFER
Remediation: <finding → new-repo-adr-policy (migrate/record) | human>
```

## Hard rules

Read-only: never writes an entry (that is `new-repo-adr-policy`, human-
approved), never deletes ad-hoc files it flags, never commits. Whether
scattered decision text is truly a decision is the human's call — quote
it, don't adjudicate it.
