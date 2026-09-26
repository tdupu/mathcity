# Derivation pass over the pending brief pile — 2026-09-25

Produced by `derive-verdict` (QUIMBY 74). **This is a derivation record, not a set
of recorded verdicts.** Recording is `adjudicate-brief`'s act, and ADR 0006
(*Agents May Record Policy-Derived Verdicts*) is `Status: Proposed`, not Adopted —
so nothing here has been written to a bead.

## Corpus, measured live

16 policy files on disk; **7 Adopted**: `POLICY-POLICY.md`, `POLICY-beads.md`,
`POLICY-formulas.md`, `subdomains/brief-system/POLICY.md`,
`subdomains/dev/POLICY.md`, `subdomains/dev/POLICY-city.md`,
`subdomains/dev/POLICY-documentation.md`.

**311 rule IDs** extracted across those seven. Of these, **27 are individually
PROPOSED** and therefore not citable under PP2.1, and **2 are marked
`(JUDGEMENT RULE)`** and must be refused rather than approximated. **284 citable.**
The 27 figure independently reproduces the count `derive-verdict` measured on
2026-09-18, by a different extraction — which is the only reason to trust either.

Three Adopted documents carry `**Adopted** … (Draft→Adopted …)` in their Status
cell. A containment test for "Draft" therefore matches three Adopted policies.
That is the `check-city-policy` parse defect fixed at `004842e`, and it is
load-bearing for three documents, not one.

## Population

**218 pending decision briefs**, all canonical beads:
mathcity 115 · hq 45 · hecke 30 · gascity-packs 15 · gascity 8 · lmfdb 3 · agent_skills 2.
Ages: 130 created 2026-09, 88 created 2026-08.

## Derivations

### DERIVED — `he-gdiujl` (hecke)

*"Five decision briefs are stranded in `.staging` and unreachable — recover them,
triage them, or discard them."* Options: {recover, triage, discard}.

- **B2.4** (`subdomains/brief-system/POLICY.md:296`, Adopted) — *"Unadjudicated
  briefs accumulate in exactly one pile. Canonical membership is the bead query:
  open `type=decision` brief beads with no active defer window. There are no
  side-piles, per-agent piles, or 'urgent' bypass piles."*
  `.staging` is a side-pile. **Kills: leaving them where they are.**
- **BP4.5** (`POLICY-beads.md:106`, Adopted) — *"If a sweep cannot mechanically
  establish a BP4.2 criterion … the bead is left open and surfaced to the human
  adjudicator with a **defer** verdict rather than closed."* **Kills: discard.**

Recover and triage are sequential, not alternatives. One course survives:
**recover into the single pile, then triage.** Not a human decision.

### DERIVED — `he-zene9q` (hecke), both halves leave the queue

*"Two briefs in rig hecke have no route to an adjudicator — recover them, and
which fix lands first?"*

- Recovery half: **B2.4**, as above. A brief with no route to an adjudicator
  fails B2.4's canonical-membership test by construction.
- Sequencing half: removed by Taylor's standing instruction, not by policy —
  *"Staffing, routing, and sequencing are NOT his. Who does what, who reviews
  whom, what order things merge in — the coordinator owns all of it."*

Recorded as two grounds because they are two different kinds of authority. Only
the first is a policy derivation.

### DERIVED-OUT — `he-2w4hdc` (hecke)

*"Sequencing the two coupled run-operator lifecycle fixes…"* Pure sequencing.
Same standing instruction. **No Adopted rule is cited, and none is needed** —
this never belonged in the human queue.

### DERIVED (partial) — `as-v5jd5` (agent_skills)

*"privacy-rulings.json's keep-ruling rests on a false premise (mathcity is
PUBLIC) — repair the warrant, and rule the publication boundary."*

- Repair half: **P5.4** (`subdomains/dev/POLICY.md:497`, Adopted) — *"When a
  doc's behavioral claim contradicts the code, the code wins: the claim is
  corrected in the same pass."* Verified now: `gh repo view tdupu/mathcity →
  PUBLIC`. **Already discharged** — `privacy-rulings.json:13` carries the
  correction, cites bead `as-iq5gk`, and preserves the deleted reasoning as a
  warning against reuse.
- Boundary half: **UNDETERMINED.** No Adopted rule reaches "what may be
  published". Genuine human decision.

### UNDETERMINED — `mc-tyry2` (mathcity)

Commission brief, `mc-hs3` re-sling, unlock_count 40, pending since 2026-08-17.
Its P0 — *"mc-73k is executing right now, four steps from implement"* — is
**measurably dead**: `mc-73k` CLOSED with 0 open children, `mc-35p` CLOSED,
`mc-hs3` and `gt-fqpi8a` still OPEN. The N1 stop-first gate is moot; only the
`work_query` fix survives.

**BP4.5 does not reach it.** Its trigger is *"cannot mechanically establish"*,
and supersession **was** established by measurement. Citing it would be the
fabrication constraint 4 forbids. Whether to spend fleet effort on a 41-day-stale
80,110-character commission for its one surviving fix is a judgement no Adopted
rule determines.

## A defect found by the pass, not a decision

**B2.5** (`subdomains/brief-system/POLICY.md:301`, Adopted) — *"Briefs are
ordered for presentation by `priority(brief) = unlock_count`, **read from the
stored field**."*

Measured: **7 of 218 briefs carry a stored `unlock_count`.** 211 do not. The
ordering rule governing the entire pile is unsatisfiable for 97% of it, which is
why a presenter must fall back to age and why "largest-unblock first" has not
been happening. Filed separately as a defect; it is not a question for the human.

## Honest scope

**5 briefs derived of 218.** The remaining 213 are heterogeneous engineering and
design decisions — *"pick the repair path"*, *"decide the disposition rule"*,
*"which layer normalises session-ID vs session-name"*. A subject-keyword scan
produced 41 candidates; reading them showed the keyword reaches the **location**
half of a question whose **substance** is a design choice no Adopted rule
determines. **A keyword hit is a candidate, not a derivation**, and reporting
the 41 as derived would have been the failure this skill exists to prevent.

The honest conclusion is the one Taylor anticipated: *"If we can't make any
progress, chances are our policies are too weak and we need to modify them."*
Six rules did real work here — B2.3, B2.4, B2.5, BP4.5, P5.4, CT13.4. The pile
is 218 deep because the policy set does not reach the questions in it.

[autogenerated by Claude Opus 5 v2.1.231 (Claude Code) on 2026-09-25]
