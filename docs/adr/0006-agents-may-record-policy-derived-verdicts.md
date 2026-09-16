# ADR 0006: Agents May Record Policy-Derived Verdicts

Parent: [../TECHNICAL-SPEC.md](../TECHNICAL-SPEC.md)

## Status

Proposed (2026-09-15, drafted by QUIMBY 70 from Taylor's nine live rulings in a
grill session). Not adopted. The policy amendments it describes still require
their own proposals, check-zero, and Taylor's per-document sign-off.

## Context

Three hundred and three briefs were pending across the city, three of them in the
stack. Taylor's instruction: *"if an adjudication follows from policy, it should be
adjudicated, ruled a no-brainer, and the policy should be cited. If we can't make
any progress, chances are our policies are too weak and we need to modify them."*

The rule he was asking for already existed and was adopted: a question whose
answer is determined by an adopted rule must be resolved by derivation and must
never be surfaced to the human — surfacing it is itself a violation. The pile was
evidence the rule was not being applied. The policy-policy's own proposed
successor rule says why: derivation *"has been effectively unenforceable while it
requires every agent to hold the whole policy set in working memory and apply it
identically."*

So the gap was never missing intent. Four things were actually in the way, and
each was found by measurement rather than by reading the narrative:

**A reviewed, approved, unpublished security fix appeared to forbid the whole
idea.** It closes the hole by which *"an agent session can create a brief, approve
its own brief, and dispatch the approved work — three calls, no human anywhere."*
Reading its predicate at source dissolved the conflict: it tests whether the
**same** agent authored and approved, and its refusal text asks for *"an
independent adjudicator"* — not for a human. An agent adjudicating another
author's brief was never what it blocked.

**Verdicts recorded today cannot be trusted later.** The attested-adjudicator
field exists in five files on that fix's anchor and in zero files on main. Every
verdict recorded before it lands is unattested and fails closed at dispatch, and
its own docstring states there is no migration: *"there is no migration that can
invent attestation for a verdict nobody witnessed."*

**The derivation basis is far smaller than the policy set looks.** Of the written
rules, 148 govern; 169 sit in Draft documents and govern nothing — including all
54 bead rules and all 18 formula rules, the two domains covering most of the pile.
Adoption, not authorship, was the constraint.

**Adoption is per rule, not per document.** Twenty-seven individually-PROPOSED
rules live inside documents marked Adopted. One of them explicitly forbids any
check skill or gate from citing it. A guard that checked document status would
have admitted all twenty-seven — committing, through the guard itself, the
violation the guard exists to prevent.

### Prior art: Taylor already built this, eight days earlier

A check-zero pass on this ADR's own idea found it is **substantially a
reinvention**. On 2026-09-07 Taylor ruled four keystone principles with QUIMBY 67,
recorded as a decision bead whose stated purpose is verbatim:

> *"Purpose: stop re-deciding instances. A brief that cites one of these is a
> DERIVATION, not a judgment, and does not need Taylor again."*

And whose scope clause is, independently, the same guard this ADR arrived at:

> *"These rulings settle PRINCIPLES. They do not adjudicate any individual brief,
> and no agent may close a brief merely by pointing at this bead — the derivation
> must be written out and must name which ruling eliminates which option, so a
> reader can falsify it."*

That bead names roughly **42 briefs its rulings resolve**, and the mechanism has
already been exercised: the preceding Mayor derived nine identity-cluster verdicts
from its second ruling. So the capability is not new and did not need inventing.

**What this ADR actually adds, stated narrowly so the overlap is not obscured:**
a typed surface that enforces the written-derivation requirement instead of
trusting it; a rule-level adoption check; the attestation ordering; inheritance of
the existing stop gates and kill switch; and the duplicate/record fork. The core
act — an agent deriving from a recorded ruling and citing it — was Taylor's, and
predates this session.

**It also changes the near-term work.** The identity cluster is not seventeen
briefs needing a survivor; it is seventeen briefs asking a question Taylor
**already answered** — `assignee` is the session ID. Under the derivation rule
that is the record branch, not the duplicate branch.

One further observation, recorded because it is the pattern this ADR exists to
break: that keystone bead is itself `type: decision`, still **open**, with no
verdict recorded. The document that exists to stop decisions going unrecorded is
itself an unrecorded decision.

## Decision

**An agent may record a real verdict on a brief when an adopted rule determines
the answer.** The agent is the authorizer; the rule is the authority.

1. **It is a fifth no-brainer category**, alongside the four mechanical ones, so
   it inherits the machinery already proven there rather than growing a parallel
   set: the stop gates, the two-level kill switch, the audit trail, and the
   per-category calibration. Taylor's existing brake already covers it; there is
   no second switch to remember.

2. **The no-brainer family's definition widens** from "obvious to a skilled
   reviewer" to "resolvable without spending a human decision — by obviousness or
   by derivation." The two are genuinely different and cross-cutting: a brief can
   be obvious without any rule covering it, or forced by three composed rules that
   nobody would guess from a summary. The leak-detection rule gains a second limb
   so a leaked derived brief is caught by *"this was forced by that rule, why am I
   seeing it?"* rather than by *"this is obvious."*

3. **The verdict cites rule TEXT, never a rule ID.** It records the governing
   document and a verbatim snapshot of the rule as it read at derivation time.
   Taylor: *"we shouldn't explicitly mention the policy numbers in outside
   references… they could change and are not stable."*

4. **The guard is rule-level and mechanical.** The recording surface refuses a
   Draft document *and* an individually-PROPOSED rule inside an adopted one. It is
   a typed path that enforces this, not a discipline an agent is trusted to keep.

5. **Independence is structural.** An agent may never adjudicate a brief it
   authored. This is the existing security fix, which becomes a prerequisite
   rather than an obstacle.

6. **Answered briefs close by reference, with a hard fork.** Where a verdict
   already exists elsewhere, the brief closes citing its location and nothing is
   owed. Where N briefs ask one unanswered question, the surviving canonical brief
   must be named *first*, the others close as superseded, and **the survivor stays
   open** — the decision is still owed. A duplicate-collapse naming no survivor
   must refuse.

7. **A proposed rule never travels alone.** Any new rule offered to unlock briefs
   ships with every pending brief it would newly decide and the verdict each
   would get. Taylor ratifies the rule and its consequences together, or neither.

## Rationale

The ordering falls out of attestation. Draining first would produce verdicts that
are unattested, fail closed at dispatch, and cannot be repaired by migration —
one fresh approve owed per brief, by hand. Landing the fix first costs a delay;
draining first costs rework proportional to how well the drain went.

Independence being structural rather than procedural is what makes the grant
safe. The failure mode is not an agent deciding badly — a derived verdict names
the rule it rests on, so a wrong one is findable by re-reading that rule. The
failure mode is an agent manufacturing its own authority: writing a brief,
approving it, dispatching it. That is blocked at write time and again at
dispatch, by code, on both paths.

Citing text rather than an ID is the decision most likely to be questioned later,
because it puts stored verdicts out of step with the gate machinery, which is
ID-keyed by adopted policy. It was taken deliberately: a citation that rots is
worse than an inconvenient one, because the audit value of a derived verdict is
entirely in whether a reader can later see what the agent actually relied on.

The duplicate/record fork exists because the two shapes look alike and differ in
exactly one respect that matters — whether a decision is still owed. Collapsing a
duplicate as though it were a record would silently discard an unmade decision.
Making the survivor mandatory turns that from a discipline into an impossibility.

## Consequences

- Taylor's kill switch governs derived adjudication with no new mechanism. It
  currently reads permissive city-wide with no rig override, so the category is
  live on adoption.
- Derived verdicts are separately calibrated from mechanical ones, because the
  wrong-rate is measured per category. The two populations do not contaminate each
  other's statistics.
- **Every derived verdict faces a refutation attempt before it closes.** A bad
  derivation is otherwise silent: for the mechanical categories a wrong verdict
  announces itself when something breaks, whereas a wrong derivation simply closes
  with a rule quoted beside it. Survives → closes; refuted → escalates to the human
  rather than being quietly corrected. Roughly doubles the per-verdict cost, which
  is the right trade against a one-way door.
- **A high refutation rate condemns the RULE, not the agent** — and this is the
  more valuable half of the mechanism. A refutation means two competent readers
  took one rule opposite ways, which is a defect in the rule: ambiguous,
  overreaching, or in unflagged conflict with another. It is the same shape as the
  existing no-brainer-leak rule, one layer up: repair the policy, not the actor.
  **Refutations are therefore keyed by the cited rule**, without which the signal
  is unrecoverable — you could see that derivations get refuted but never which
  rule generates them. The per-rule refutation rate is the policy-quality metric,
  and its trigger level is set from data rather than invented up front.
- Stored verdicts and the gate registry use different citation conventions —
  text-cited and ID-keyed respectively. **This split is deliberate and its
  boundary is stated:** rule IDs are kept inside the policy system (rule headings,
  policy-to-policy cross-references, the gate registry, check skills) and are
  forbidden outside it (glossaries, docs, beads, briefs, stored verdicts). The
  instability that motivated the rule bites references nobody re-checks; inside a
  policy set that is read and amended as a unit, a stale cross-reference is caught
  the next time someone reads the rule.

  The alternative — converting everything — was ruled and then reversed once
  measured: 544 policy-to-policy cross-references, against an estimate that had
  described the job as "the gate entries and the check skills." Converting them
  would also have collided with the policy-set minimality rule, since replacing
  short references with verbatim quotations inflates every document.
- A wrong derived verdict is not trapped. Adopted policy already provides the
  escape: the remedy is a new brief bead linking the old one as a source, never
  reopening. The record is permanent; the outcome is not.
- Adopting the bead policy adds a fourth stop gate — mathematical content — so no
  derived verdict could touch a research body, a claim status, or a covered `.tex`
  file. This argues for adopting that document before the drain runs.
- Nothing drains until the typed surface exists. The only current verdict-writing
  tool declares it is not an adjudication surface.

## Alternatives considered

**Pre-classify and batch-confirm.** The agent marks each brief derivable with its
answer; nothing closes without Taylor approving a batch. No agent ever records a
verdict, so the security fix stays trivially coherent. Rejected because it still
spends the attention the exercise exists to save — it converts 40 adjudications
into one batch approval, which is an improvement, not a solution.

**Split by stakes.** Auto-record reversible briefs; queue irreversible ones for
batch confirmation, using the existing stop-gate list as the split line. Rejected
as redundant: the stop gates already block the irreversible surfaces, so the extra
tier would gate a population the gates had already removed.

**A separate rule family for derivation.** Own rules, own kill switch, own audit
stream. Conceptually cleanest — deciding what to DO to an artifact and deciding an
open QUESTION genuinely are different acts. Rejected for a second brake Taylor
would have to know exists, duplicated stop-gate and audit machinery, and a
policy-minimality problem. The language was widened instead.

**Renaming the no-brainer family** to something spanning both senses. Honest, and
it removes the overload at the root. Rejected on blast radius: roughly twenty
rules, the gate registry, the classifier skill, the classifier's own metadata
fields, and the kill-switch file — wide churn for a naming gain, with every
existing artifact still carrying the old word.

**Using the existing relay tool with Taylor's grant as the authority.** It records
a verdict and who decided; the authority would be his standing grant, not the
tool. Rejected because it is precisely the reading that tool's rename was written
to foreclose, and because it would make derived verdicts indistinguishable in the
store from ones Taylor personally made — destroying the audit property the
independence machinery exists to create.

**Fixing rule-ID instability instead of routing around it.** Adopted policy
already claims IDs are permanent: deprecated rules are tombstoned rather than
deleted, and IDs survive promotion without renumbering. Rejected as sequencing:
it blocks the drain behind a policy-maintenance project of unmeasured size.
