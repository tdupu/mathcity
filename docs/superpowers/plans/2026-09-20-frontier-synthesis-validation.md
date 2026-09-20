# Selected research synthesis: validation record

Parent: [skill index](../../../README-skills.md).
Design: [shared synthesis contract](../../../skills/math-workflow/references/synthesis.md).
Fixtures: [research synthesis](../../../tests/research-synthesis/README.md).

## Scope

This change composes the existing context, prototype, filling, proof, writer
and review skills. It adds no parser, status database, research backend or
general-purpose orchestration engine. Both powers routers use math-workflow.
The make-outline responsibility is absorbed by rapid-prototype; the old browser
harvest implementation is preserved in the companion agent-skills archive.

Outline, presentation-source and integrated-manuscript acceptance are distinct.
The last requires independent review of the actual integrated version and its
build/PDF; unchanged proof audits may be reused only with their recorded limits.

## Correction: resolve undetermined mathematics, or fail loudly

The earlier trials below are historical evidence, not certification of this
strengthened rule. In particular, the original case 03 forbade a local proof
attempt and tested a saved research handoff, not resolution. Its limited PASS
does **not** satisfy the current case 03; missing proof must now go through an
actual `using-mathpowers` attempt. Unsuccessful resolution triggers the shared
[visible failure gate](../../../skills/math-workflow/references/execution.md#undetermined-mathematics-is-work-not-a-disposition),
blocking dependent delivery and any overall completion claim. Untested integration,
PDF inspection and external audits remain untested, not silently successful.

### E — Alternatives and hygiene

This is a repo-side correction to the existing mathcity skill sources and
their tests/docs, not a new solver, backend, policy or runtime installation.
`check-wheel`: adapt `using-mathpowers`, the existing execution/retry contract
and PROVERS backend; reject a parallel resolver or a prompt-only handoff as the
completion rule. Existing skills, formulas, orders and test sources were surveyed;
the gap is mandatory consumption and immediate failure visibility, not a missing
solver. Live city and Beads history are not a source of mathematical resolution;
Beads access is unavailable in this isolated checkout. Magma, database and new
Python tooling are unnecessary for the workflow change.

`check-plan-hygiene`: source edits stay in the owned pack, preserve inputs and
review history, introduce no imports or new skill identities, and leave live
activation/push human-gated. Three instruction files share one resolution gate;
no host values or sink edits are introduced. P6.1-P6.3 require visible failure,
falsifiable tests and distinct deadline reporting. Documentation follows this
source change; historical review hashes do not approve the changed tuple.

### Executed resolution-phase regression

Two fresh actors received only their exported project, selected report and
installed skills, not evaluator expectations. They could reason locally and
write scratch evidence; external research, backend calls, manuscript edits and
worker-owned review were disallowed. This is a bounded phase test, not a full
synthesis run. The coordinator separately dispatched the proof reviewer.

- **Solvable gap:** the cubes actor actually invoked mathpowers, supplied the
  missing general induction algebra and a second telescoping proof. An independent
  `doubt` reviewer inspected the exact source and candidate and returned SOUND,
  checking quantifiers, the empty sum, both proofs and every algebraic step.
  Candidate SHA-256: `e6097d9c56f7d84e98c77833a748c2b8432c044972fb1d72a246c131ada53712`.
  This closes the mathematical proof gap; it does not close the separately unrun
  literature, promotion, manuscript, build or PDF gates.
- **Missing-data case:** the second actor selected the particular symmetric
  matrix from experiment R, whose entries/certificates are unavailable. It tried
  a direct quadratic-form argument, then exhibited compatible matrices with
  different definiteness. This diagnoses insufficient evidence, not a refutation
  of the actual matrix. Its native execution trace shows the visible
  `ERROR — mathematical resolution incomplete` immediately after the witness
  check and before final evidence/report writing. The alert names the missing
  data/certificate and blocked promotion. **Mathematical target BLOCKED;
  fail-loud behavior PASS.** These verdicts must not be conflated.
- **Negative discriminator:** the retained original case-03 artifact explicitly
  says no worker ran and no local proof attempt supplied the missing equality.
  It fails the revised actual-resolution criterion. This re-scores an observed
  historical artifact; it is not a randomized before/after model benchmark.
- Both selected originals and both copies of `notes.tex` remained byte-identical.
  No false backend, review, literature-search, cost or manuscript-acceptance
  claims are accepted as test success.

The phase runs used the initial correction tuple. Subsequent interface-review
changes and their validation are recorded separately; these observations do not
certify Fable execution, hard-deadline cancellation or integrated manuscripts.

### Correction interface review

Three independent instruction critics found six actionable interface problems:
automatic unresolved manuscript stubs, conflict investigation versus human
adoption, Fable freshness/delegation, initial backend output permissions,
hard/advisory deadline handling, and a finite allowance shared across retries
and review-triggered repairs. A separate revisor centralized their resolution
in execution.md and linked the two consumers to it. No backend leaf was changed.

The driver measured substantive strict shrink in all three revised files:
execution 10,769 to 10,702 bytes, synthesis 7,765 to 7,748, and fill 5,751 to
5,654. Fresh per-path critics each returned zero-finding APPROVING after checking
the actual adjacent contracts. This is static instruction review, not execution
of Fable or hard-deadline cancellation. The proof and fail-loud observations
above retain their initial-tuple scope.

A final two-byte execution edit rephrased the one-writer list to avoid a
portability scanner false positive; it changed no ownership or dispatch rule.
The driver verified the exact single-sentence delta and strict shrink to 10,700
bytes. All three final per-path critics again returned zero-finding APPROVING.
The final tuple revisor answered exactly `NO`; the bounded three-round correction
loop reached mutual approval with no factoring.

| Final instruction | SHA-256 |
| --- | --- |
| execution.md | `9026f09194ab1223ffb3f4a3ebc00568b96ec1e24528b1007265c87940f18f0e` |
| synthesis.md | `bb678c6d258370a42ff805285805c191f084c01baaf00d0faf56882422b84060` |
| fill-in-prototype/SKILL.md | `c8ddefb914fd45b491a121a43234c6d5c4a64b78f825939b4ce032d6510fa7b9` |

Raw critic, revisor, proof-review and native-alert records remain alongside
the isolated trials in the task's external review directory. Neither source
approval nor an auxiliary proof of insufficient evidence is a proof of the
missing matrix's definiteness.

### Correction mechanical and documentation checks

The final tuple passed fixture packaging (eight cases), both skill frontmatter
validators, portability scans, diff whitespace checks and secrets scans of both
changed skill roots and the fixture suite. All 37 local Markdown links and six
anchors across the eight changed Markdown files resolved. The changed request
and oracle explicitly reject the historical prompt-only completion rule and
separate mathematical resolution from successful failure handling.

`improve-documentation` updated the skills index's usage/Example Coverage,
proof-assist guide, fixture instructions/oracle and this record; it added missing
parent links to the two touched test guides. The adopted documentation policy's
diff audit is PASS-WITH-NOTES: changed examples/tests and navigation agree with
source; no skill identities, formulas or subdomain roots changed. The index's
pre-existing create-issue row still names a repository owner (DOC1.2 scan);
it is outside this correction. Beads remains unavailable, so no issue or remote
sync is claimed. These are scoped checks, not a whole-pack documentation audit.

## Execution limits

Validation uses native Codex agents in the same model family. Independent roles
are not independent models, formal verification, or human approval. Model/token
usage counters and prices are unavailable; no totals or costs are inferred.
No paid external research backend or literature search is part of these trials.
Behavioral test inputs are elementary, synthetic project fixtures.

## Historical package mechanical checks

- Fixture packaging checks: eight input/oracle pairs; selected sources and
  attachments; canonical TeX inventories; audience variants; withheld follow-ups;
  retained prior source. Passed. This does not test agent behavior.
- Companion retirement integrity: all 70 original payload files and modes,
  including 40 fixtures, preserved; eight SKILL entry points and seven packaged
  distributions renamed out of discovery. Corruption and mode-change negative
  tests passed. The companion archive includes the recovery manifest.
- Portability scan of all seven modified mathcity skill trees passed.
- All seven mathcity frontmatters and 36 local Markdown links across their
  complete skill trees passed. Diff whitespace checks passed.
- Secrets scans passed for the eight changed skill trees, behavioral fixtures,
  design note and retirement archive (including nested distributions).
- The three distinct canonical fixture documents compiled successfully;
  the existing-label fixture was built twice. Logs had no remaining warnings.
  These are input-fixture builds, not integrated-output acceptance.
- Exporting into an existing trial directory was correctly refused.

## Historical fixed-point review

Design review found two handoff defects: scratch-only drafting was ambiguous
with canonical writer execution, and integrated acceptance needed an explicit
independent gate. A separate revisor corrected both, reducing the shared
reference from 7,492 to 7,481 bytes. The driver verified the byte counts and
substantive delta; exact-version re-review approved the correction.

Package review additionally corrected frontier-dump's accounting write boundary
and its treatment of zero negative findings (7,896 to 7,874 bytes), and removed
a stale contract count in math-workflow (4,086 to 4,081 bytes). All other
reviewed files retained their initial approved text. No factoring was needed.

Every one of the ten instruction files received zero-finding APPROVING review.
The independent final tuple revisor answered exactly `NO`; the two-round
package loop reached mutual approval. The driver verified structured receipts
for all eight skill roots. See [retained reports and exact hashes](2026-09-20-frontier-synthesis-reviews.md).
This stabilizes skill contracts, not general mathematical judgment.

## Historical behavioral execution

Requests and raw inputs are in the fixture suite; expected outcomes were withheld
from the actors. An independent evaluator received them afterward. Isolation was
instruction-based, not an OS access boundary. One actor handled the eight dry-run
probes in a shared context; a separate actor ran the live candidate-only case.
These are bounded regression observations, not repeated model benchmarks.

| Case | Executed observation | Boundary |
| --- | --- | --- |
| 01, selected subset | Corrected product criterion and its refutation retained; unrelated geometry excluded | Drafting/decision probe |
| 02, target first | Exact nonnegative-integer target, empty sum and complete induction retained; notation backfilled | Drafting/decision probe |
| 03, missing proof | Unsupported PROVED label rejected; focused research request saved; independent recurrence explained | No backend dispatch; missing proof stays open |
| 04, two audiences | Beginner enumerates six pairs; advanced gives a two-to-one count; both preserve boundary cases | Two drafting probes in the same actor context |
| 05, target override | Existing exposition.tex and its Parity section chosen consistently | No live canonical insertion |
| 06, candidate only | Real spec/prototype, independent O1 ACCEPT, filled candidate, independent P2 source ACCEPT, then stop | No TeX edits, SOUND, build or PDF claim |
| 07, legacy | Authored proof, generated correction, counterexample, history and dependency definitions retained | Migration-planning probe, not destructive stripping |
| 08, rerun | Turn 1 reconciles historical review; turn 2 chooses a semantic no-op; turn 3 refutes the broadened claim and invalidates affected acceptance | Three bounded turns passed; no live integration |

The first evaluator pass scored seven probes PASS and one INCOMPLETE, with no
observed failures. The incomplete result came from an overbroad harness ban on
reading review outputs: the actor also avoided the supplied historical review.
After clarifying that this project input was permitted, it read and assessed the
actual record; independent re-evaluation passed turn 1. Turns 2 and 3 also passed.
This was a test-harness clarification, not an unrecorded skill repair.

Final bounded score: all eight initial probes passed after that clarification;
both later turns passed, with no observed failure. Turn 3 retained both
counterexamples, the valid restricted theorem and the independently proved
all-real equality equation, without transferring the earlier review to them.

The live case used two separate non-author referees. O1 checked all eight mapped
items and accepted the exact prototype; P2 independently checked the filled
proof and exposition, again with zero findings. The actor consumed both actual
returns and completed the requested candidate-only delivery. The one selected
corrective finding and all three worked examples survived. Exact SHA-256 values:

| Artifact | SHA-256 |
| --- | --- |
| Selected source | `afbdfee2ebf2a8ab58c3ad3b7c1a8e6b8437a17434fb153f576eb939f4fe07e5` |
| Spec | `ce547d3ae056be6b9dab69ec68fb9fe26a18de9902dbb6ad6f3bc5f9c76baf97` |
| O1 prototype | `5647d3d3bdf0634e2db703ce149179a228ed2f77769ad189598aeff82005d0bd` |
| P2 filled candidate | `e899f9fa07fd82cc7ba8937bd4fbc55b08d9e0a2a9d5da93f21b3273e9c92927` |
| Unchanged notes.tex | `3e4af819d176cd05c2fbe3ddb6f575c9072a718c65f92ea867b27dd98ec68add` |

The driver and referees verified 35 P2 frozen inputs and reconstructability of
all 21 O1 inputs, including retained bytes for two later-updated accounting
records. Source approval was not transferred to a nonexistent integrated
version. No new TeX file was created. The offline literature audit remained
unperformed and explicit; no novelty or publication-readiness claim follows.
The independent evaluator checked the artifact state; the coordinator separately
observed native dispatch/returns and the author's final delivery after P2.

All 88 baseline files across nine projects were byte-identical before the
deliberate R2 source replacement for turn 3. The exporter withheld that revision
until earlier turns were scored, and R1 was verified against its retained copy
before replacement. Actual reviewed integration, PDF inspection, live backend
dispatch and publication remain unexercised by these bounded trials.
