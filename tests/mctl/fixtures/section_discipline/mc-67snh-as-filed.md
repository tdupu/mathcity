## §1 — What is being decided

gc hook --claim hands workflow LATCH ROOTS to normal pool workers, which execute-and-close them, false-terminating live workflows and orphaning ~35 open steps. Which direction do we fix it? WHAT IS ALREADY RULED OUT: claim-lane exclusion of gc.kind=workflow. graphroute.go:562-588 stamps gc.routed_to on the root DELIBERATELY so it stays claimable — the code comment reads "without it... never claimed... idle-reaped (fixes #2763)". Excluding roots from the claim lane reverts #2763 and hands them to the idle-reaper. The root is CLAIMABLE BY DESIGN; that is not the bug, and a full day of work on that direction is discarded. WHAT MAKES IT P0: the terminal-root gate (runtime.go:297) fires on status==closed REGARDLESS of outcome, so teardown is convergent with no recovery path. Worse, the close arrives via graph-worker.md step 4 as gc.outcome=PASS — a FALSE SUCCESS. The workflow reports that it completed. Any fix that only guards the failure path misses this entirely. RECURRENCE, and it is the load-bearing evidence: mc-03o11 is a second independent instance (different role, different formula) that has recurred THREE TIMES on one pool. gc hook --claim returns existing_assignment; lease expiry does NOT release the assignment; there is no abandon flag. Each misdelivery removes one pool from service permanently until cleared by hand, so the symptom is CAPACITY LOSS — pools dropping out one at a time while siblings work normally — not a whole-city stall. Resetting a specific bead buys exactly ONE lane-slot before the hook hands over the next, which makes bead-reset triage rather than remedy. EXPLICITLY NOT EVIDENCE: the S58 demand_claim_divergence bucket. I proposed it as a second evidence stream, it was checked against the gs store, and 24 of 25 divergence beads are ordinary housekeeping churn with no gc.kind. Refuted and withdrawn; gt-68htfw stays closed. CONFIDENCE NOTE the adjudicator should price in: this defect has been re-framed six times in fourteen hours, four of those reversals mine. Every claim that survived came from reading source; none survived re-derivation or restatement. The options below are scoped from source reads, but the routing option in particular rests on an assumption nobody has yet checked.

## §2 — Recommended answer

None recorded. This brief transports a question to be decided; `decisions_to_briefs` deposits it UNDECIDED (#194) and the human adjudicator supplies the verdict.

## §3 — Assumptions surfaced

None surfaced at composition -- this brief was composed from a decision statement and its open source bead, not from a reviewed artifact.

## §4 — Alternatives named

None enumerated at composition. Authored decision options, when present, appear in the Options section below; the adjudicator may propose another.

## §5 — Risks foregrounded

None surfaced at composition. The decision has not yet been reviewed for breakage or downstream commitment; that is the adjudication.

## §6 — Supporting evidence

This decision is about `mc-k4t1s`, an open bead in this rig. The source resolves, is not closed, and is unassigned -- the pair requirement an adjudicated brief needs to be dispatchable.

## §7 — Plan membership, blocking, and required gates

Blocking: adjudicating this brief unblocks `mc-k4t1s`.

### Gate Evidence

Checked before this brief was written; each corresponds to a dispatch blocker in `work.py` that was tested and did not fire:

- source `mc-k4t1s` resolves in this rig (MDTB002 did not fire)
- source is not closed, so the brief is dispatchable (MDTB003 did not fire)
- source has no active assignee (MDTB004 did not fire)
- source has no open child workflow (MDTB005 did not fire)

## §4 — Options

- **(A) CODE INTERLOCK — refuse to close a workflow root that still has open steps** *(recommended)* Narrowest change that sits exactly at the point of damage (runtime.go:297). Binds regardless of which prompt renders, which agent claims, or which rig overrides what — it is a structural refusal, not an instruction. Preserves #2763 completely: the root stays claimable, it just cannot be destroyed. Catches the gc.outcome=PASS false-success path, which a failure-path-only guard would miss. REQUIRED COMPANION: a defined behaviour for the refused close — a worker told 'no' with no alternative loops, which is the livelock we already have wearing a different hat. That companion is the main design work and the main risk.
- **(B) ROUTING — do not route workflow roots to normal pool workers; route to a controller/dispatcher** Structural and arguably the most principled: the root is a control object, so a control agent should hold it. Preserves #2763 (the root stays claimable, by someone else). UNCHECKED ASSUMPTION, and it is load-bearing: do controllers/dispatchers actually implement root-advancement? Nobody has verified this. If they do not, this relocates the stall rather than fixing it. Blast radius is every workflow root city-wide, which is the widest of the options.
- **(C) PROMPT GUARD — tell the claimant to advance/finalize, never close-as-work** RECOMMEND AGAINST, and it is listed only because it was on the table for most of a day. graph-worker.md ALREADY carries such a guard at :113-118, and mc-upgv was closed anyway. A guard that is already present and already failed is not a fix. It is also behavioural rather than structural: prompts can be overridden per-rig, and the terminal-root gate fires on close regardless of what any prompt said.
- **(D) DEFER the direction; ship containment only** You already approved bead_hold / bead_release (mc-qcnaz). Ship that, contain instances by hand as they appear, and take the direction decision later with better information — specifically after someone checks the controller-capability question that option B rests on. Honest about the state of the evidence given six reframes in fourteen hours. Cost: capacity keeps leaking one pool at a time, and containment is manual and per-instance.
