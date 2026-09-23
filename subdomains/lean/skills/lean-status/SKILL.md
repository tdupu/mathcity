---
name: lean-status
description: Use when asked what is formalized, where Lean work is blocked, how much remains or whether a formalization result is still current.
---

# Report scoped progress

Input: requested scope, source map and current evidence. Output: a read-only
mathematical status report, not a new plan or a build claim from memory.

Reconcile source records with live declarations and the
[evidence contract](../lean-workflow/references/evidence.md). Check snapshot
currency. Absent evidence means unverified; absent records mean uninventoried,
not false. Request `lean-verify`/`lean-fidelity` when current confirmation is
needed; report unavailable checks plainly.

Separate three views: selected-source coverage; the main theorem's prerequisite
closure; and distance to an unconditional result. List conditional assumptions,
admissions, stale reviews, missing definitions and actual mathematical blockers.
If giving counts, name the denominator and list exclusions. Do not count
declarations as equally sized units of mathematical progress.

State the strongest supported conclusion and the next concrete obligation.
An independently verified theorem can remain valid while another requested
module is incomplete. A false source claim survives as a refuted result with
its counterexample; a corrected theorem has a separate status.

Example: “Three of four selected claims are FORMALIZED; the fourth is conditional
on compactness absent from the source” is informative. “Build green, manuscript
verified” is not justified by that evidence.
