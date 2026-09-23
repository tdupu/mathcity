# Failure modes

Parent: [create-roadmap](../SKILL.md).

Every entry below is a defect that actually occurred in a roadmap built this way.
Each names the check that now prevents it.

**Provenance, stated exhaustively because two entries here are about records that
misstate their own contents.** Thirteen review passes produced findings: three
bounded reviews, one coordinator self-review, six of seven per-deliverable
adversarial forks, and three skill-file critics. Four further passes were
dispatched and produced nothing — three died on a usage limit, one when its host
slept mid-run. An earlier version of this line said "thirteen review passes —
three bounded reviews and seven forks", which does not add up; the count was
right and the list was partial.

**Ids are append-only.** A new entry takes the next free number regardless of
which section it joins, so section ranges are non-contiguous by design. Do not
renumber to tidy them: FM-01 has external referrers in this skill's other files,
and renumbering breaks them silently. This is the same rule the specification
states for target ids, applied to this file's own.

Read this before recording any status. The catalogue is the point: these are not
hypothetical, and several recurred *after* being fixed once.

## The gates

**FM-01 — the `established` gate accepted a review with no proof.**
The evidence requirement was a single set `{adversarial-review, referee-report}`
tested by intersection, so one review row with no formal artifact passed — while
the transition table, the renderer and the design document all said "a complete
proof **and** an independent review". The most load-bearing sentence in the
schema, printed into every rendered roadmap, was unenforced in the gate meant to
enforce it.
*Check:* evidence requirements are a list of sets, all of which must be met.

**FM-02 — three "reductions" were interderivable with what they replaced.**
Two hypothesis interfaces were inhabited exactly when their conclusion held; a
third was a roundtrip identity with the field it was meant to refine, provable by
case-split-and-reflexivity. All three were presented as axiom reductions, and each
was caught only by adversarial review *after* reaching the project's census and
README — twice after reaching the manuscript.
*Check:* assessed interface strength requires a named witness theorem. Before
building an interface, attempt `Nonempty (Interface i) ↔ <conclusion>`, where `i`
is whatever the interface is indexed by. If it goes through with no hypotheses the
interface is *equivalent to its conclusion* — the worst of the three assessed
values, and distinct from merely *restating* the field it replaced.

**FM-03 — a rule keyed on free text, so it was one typo from silent.**
Three separate rules each fired only on a field's exact spelling — an interface
grade cap, a status gate and a grade-A requirement — and the fields were free
strings. Setting a field to `Interface` rather than `interface` evaded the cap
entirely.
*Check:* closed vocabularies for every field any rule keys on. Not "documented
values" — enumerated, and rejected when absent.

**FM-04 — documented rules were never implemented, and enforcing one moved the
plan.** Two rules lived in prose and in no validator: the interface grade cap, and
the transition cost "no unresolved assumption of kind statement". Implementing the
second demoted the roadmap's own recommended first target, because that target had
exactly such an assumption open.
*Check:* every rule you state, and every transition cost you declare, gets a
validator test in the same change. Then re-read your recommendations: a newly
enforced rule can invalidate the advice you were about to give.

## The checks themselves

**FM-05 — an acceptance check that failed on the clean tree.** An unanchored
substring search for a forbidden keyword matched ordinary prose in three
docstrings.
*Check:* run every acceptance **command** you write, on the current tree, before
recording it — and know which outcome you expect. A *regression* command must exit
zero now. A *forward* command must run cleanly and **fail** now, because its work
is not done; if it passes, see FM-07. Only `machine` checks can be run this way;
`fidelity`, `review` and `human` checks are discharged by a reader.

**FM-06 — an acceptance check that could not fail.** A command whose output was
informational always exited zero, so four machine checks asserting "no
non-standard axiom" enforced nothing.
*Check:* for each check, ask what makes it *fail*. If you cannot answer, it is not
a check.

**FM-07 — a check that passed before the work was done.** It searched for a field
being assigned, which matched the pre-existing assignment from a hypothesis — so
it could not distinguish a discharge from a pass-through.
*Check:* a forward check names the *new* artifact, not the old one's shape, and it
must fail today. FM-05 and this entry are one rule in two halves: run it now, and
expect failure now.

**FM-08 — a check unachievable in principle.** It asked for a lemma to appear in
the proof term of a theorem that proves through a structure field. Field values
come from whoever inhabits the structure, so no lemma used to build a witness can
ever appear there.
*Check:* trace the proof route before asserting what its term contains.

## The graph

**FM-09 — a real circularity hidden by edge typing.** Target A depended on B while
B "inhabited" A. Cycle detection ran over dependency types only, so nothing fired
— and neither target could be dispatched first, which made the whole upper half of
the roadmap unreachable. The upstream census described the coupling as a
*consequence* of doing the work, discovered afterwards; encoding it as a
prerequisite inverted the discovery order.
*Check:* the trigger is not merely mutual reference — a definition and its
non-vacuity witness may legitimately point at each other through non-dependency
edges. The trigger is **an inverted discovery order**: if the upstream record
describes the coupling as a *consequence* of doing the work, it is not a
prerequisite, and encoding it as one deadlocks both targets. Split the definition
from the obligation it creates.

**FM-10 — a dependency channel no validator read.** An assumption's "cleared by"
field named targets with no edge to back it. A dangling id sat in the file
undetected, and two real couplings were invisible to cycle detection, readiness
and dependency queries.
*Check:* every such field must resolve **and** be backed by an edge in one
direction or the other. Note the direction is not always the same: "what clears
this" usually points the opposite way from "what I depend on".

**FM-11 — targets reported ready whose own inputs named unbuilt targets**, because
the coupling was encoded as a non-dependency edge or not at all.
*Check:* every target id appearing in another's inputs needs a dependency edge.

**FM-12 — readiness and validation disagreed on "blocked".** Validation accepted an
inbound blocking edge as justification; readiness ignored that edge type.
*Check:* one definition, consulted by both.

## Sources and citations

**FM-13 — a census cited two going-down lemmas under the label "lying over".**
Neither states it. The mislabel had propagated into the roadmap.
*Check:* open every cited tag or lemma and read its statement. Retrieval metadata
is not the statement.

**FM-14 — a target was blocked on a false absence claim.** The census said the
library had no scheme-level construction for something it does in fact provide,
with the universal property the project needed. That false premise blocked two
downstream targets.
*Check:* grep the pinned library. Absence claims need the same evidence as
presence claims.

**FM-15 — five named library declarations did not exist**, one had a changed
signature, and one input was a **literal ellipsis** no executor could resolve.
*Check:* resolve every named declaration against the pinned build — by type-check,
not by recollection. Grep and type-check do different jobs and FM-14 uses the
other one: a grep hit is enough to **refute** an absence claim, but only a
type-check **confirms** that a declaration exists with the signature you need.

**FM-16 — work that already existed was scoped as new.** Two intrinsics the
roadmap planned to write had been committed ten weeks earlier, with matching
signatures and a docstring nearly identical to the target's own statement. The
roadmap had trusted a context file's "needed, to be added" line and never opened
the module.
*Check:* open the module. A document's description of a source is not the source.

**FM-17 — a quantity was named as a formalization target under the wrong
description.** An index was called a cusp count; the source table gives both and
they differ. Formalizing it as stated would have proved a false statement — in the
gate that exists to prevent that.
*Check:* for every quantity, find where the source *defines* it, not where it
appears.

**FM-18 — a quote was compressed without an ellipsis**, and elsewhere a word was
inserted inside quotation marks. Both times in documents whose subject was citation
fidelity, and once inside the fix for an earlier citation defect.
*Check:* paste quotations; do not retype them.

**FM-19 — rule numbers collided across repositories.** Two projects each had style
rules numbered identically with materially different content, and a shared document
cited one project's rule as the gate for the other's canonical file — where the
real rule was strictly stronger. Acting on it would have licensed what the other
project forbids. A related instance cited a rule that **does not exist** in one of
the two projects, and a policy whose governing document one project does not have.
*Check:* repo-qualify every rule citation. Qualifying to the wrong repository is
not a smaller error than leaving it unqualified — it looks correct.

## Records and process

**FM-20 — a report claimed its own reviews had run.** It was drafted while the
reviewers were still executing; all three then failed on a usage limit, having
produced nothing.
*Check:* write results after results arrive. Record the failure as a finding rather
than removing the claim.

**FM-21 — a fix was applied to one copy of a shared document and not the other,
and the commit message said otherwise.** The copy left untouched was the one where
the rule actually binds.
*Check:* after fixing a shared file, diff every copy. Before writing a commit
message, diff the changeset against what the message claims.

**FM-22 — a correction shipped in a state its own check rejected.** A coverage
assessment was bound to the repository HEAD, so the commit that recorded the
assessment invalidated it, and the verification target failed on the committed
tree. It had been verified before committing and not after.
*Check:* bind assessments to what they assess. Re-run verification *after* the
commit.

**FM-23 — a review record claimed a correction it had not made.** The section
asserting that a class of defect was "all corrected" had left one uncorrected — a
nonexistent library name, in the section whose subject was nonexistent library
names.
*Check:* enumerate finding ids in the record and mark each applied or not. A
finding absent from the list is a finding dropped silently.

**FM-24 — an automated pin refresh overwrote a historical record**, turning an
accurate account of one change into an account of a different one.
*Check:* exclude narrative files from mechanical sweeps. A live pin and a
historical record are indistinguishable to a regex.

**FM-25 — a validator existed in more than one place and the copies diverged.** The
surface an agent queries checked strictly less than the authoring surface; a mutant
carrying an injected cycle, a malformed id and an evidence-free status passed one
and failed the other.
*Check:* one implementation. Differential-test the surfaces against a deliberately
broken input.

**FM-26 — an integrity check hashed the wrong file.** It compared a pinned hash
against the canonical copy and never the vendored one, so the single rule it
existed to enforce — do not edit the vendored copy — was unenforced. A related
instance pinned only one of several vendored files, and one of the unpinned ones
had silently gone a version stale.
*Check:* hash the artifact the rule protects. Pin every vendored file.

**FM-27 — a destructive regenerator reverted hand-applied corrections**, and its
only warning printed *after* the write.
*Check:* put corrected data in the generator so regeneration is idempotent. A
post-hoc warning on a destructive write is not a guard.

**FM-28 — a plan was back-filled with its own reviews' findings**, so it could no
longer drive an independent re-run: a second reviewer is handed the conclusions.
*Check:* findings live in the review record. The plan holds questions.

**FM-29 — a planned review was replaced in flight by a different review**, and the
plan was not updated. Four of its checks were performed by nobody while the plan
appeared satisfied.
*Check:* compare each executed review against its brief and name every planned
check no review performed.

## Inference drawn from the catalogue

This section is **not** incident record — everything above it is. These are
conclusions drawn from the entries, and they are labelled so a reader does not
apply the "actually occurred" contract to them.

**Fixes recurred.** This the entries do show, with ids: FM-02 (a defect reached
the manuscript twice), FM-18 (an elision-as-quote defect committed *inside* the
fix for an earlier citation defect), FM-19 and FM-26 (each records "a related
instance"), FM-21 and FM-22 (a correction applied to one copy and not its sibling;
a correction shipped in a state its own check rejected), FM-23 (an uncorrected item
inside the very section claiming that class was all corrected).

An earlier version of this section said the defect rate "was not converging". That
is a claim about a rate over rounds, and this file shows no round-by-round counts,
so the instrument for it is absent. The traceable claim is the weaker one above:
fixes recurred, here are the seven ids.

**Review effort concentrates where defects are cheapest to find.** Supported by
this file's own shape: roughly twenty-two entries concern machinery and process
against five or six concerning mathematical content. So deliberately assign a
review to the mathematical content, and check that it ran — in the source
catalogue the one pass assigned to exactly that died mid-run and was not
re-dispatched for some time.

**Context-inheriting reviewers may share the author's blind spots.** This one is an
assertion, not a finding: nothing in the catalogue distinguishes which entries came
from reviewers that inherited the author's context and which did not, so treat it
as a hypothesis worth testing rather than a lesson earned. The one datum pointing
at it is FM-02, where the defect was caught only by an adversarial reviewer and had
already passed the author several times.

**The question a roadmap cannot answer about itself.** Can an executor act on it?
That is measured by dispatching one target — not by another review. The parent
skill's closing section says the same thing; it is repeated here because a reader
who arrives at this file first should not have to go back for it.
