# Building a roadmap — the process

The order below is not a style preference. Each phase exists because skipping it
produced a specific defect that survived into a committed artifact; the incident
is named at each step and catalogued in `failure-modes.md`. `schema.md` defines
what the artifact *is*; this file is how you arrive at one.

**The governing rule, which outranks every phase below:** never record a claim as
a theorem because it appears in a manuscript or because it compiles. A manuscript
proof and a Lean build are two independent pieces of evidence about two different
propositions, and neither is the other. Nearly every expensive defect in the
catalogue is an instance of forgetting this.

## Phase order

    0. census          what does the corpus assume?
    1. boundary        what does the library already have?
    2. targets         literal inputs, literal outputs, acceptance
    3. edges           typed, then cycle-checked over the right union
    4. grades          a dispatch decision, not a difficulty rating
    5. validate        on your own draft, expecting failure
    6. review          per-dimension, adversarial, re-verified after commit
    7. dispatch one    the only measurement that counts

Phases 0–4 are construction; 5–7 are the gates. Do not reorder 0 and 1 — grading
before the boundary check is how a target gets blocked on a false premise.

---

## 0. Census before graph

Do not begin by drawing a dependency graph. Begin by enumerating, with an id per
row, everything the corpus **assumes but does not prove**. Sources: hypotheses
that appear in proofs without appearing in statements, structure fields, `sorry`
and its dialects, appeals to "standard" results, and citations whose target you
have not read.

A roadmap built before its census produces targets that cannot be stated, because
the thing a target must reduce *to* has no name yet. Two observed forms:

- A target named a library concept that does not exist in the pinned version at
  all — zero occurrences under grep. It was not hard; it was **not statable**, and
  no amount of grading surfaces that distinction.
- An assumption lived in a structure field, where `#print axioms` cannot see it.
  A build that reports no axioms is not a build with no assumptions. Field-carried
  hypotheses are invisible to every axiom-level check and must be censused by
  reading the structure.

The census is a separate artifact with its own ids, and target records cite those
ids. Do not inline assumptions into target prose; an assumption cited from two
places and edited in one is the multiple-copies failure, and it recurred three
times in one session.

## 1. Boundary check before grading

For every intended target, establish what the **pinned** library version actually
contains, by grep or search against that pin — not by recall.

This phase exists because of a symmetric pair of failures, both expensive:

| Direction | Observed | Cost |
|---|---|---|
| Believed absent, actually present | Scheme-level normalization was taken to be missing; it is in the library | one target graded hardest, **two downstream targets blocked on a false premise** |
| Believed present, actually absent | Henselization assumed available to state against; zero hits in the pin | a target that cannot be written at all, discovered late |

Both are cheap to prevent and expensive to carry. Record the pin — toolchain and
revision — in the roadmap itself, because a boundary result is only true relative
to a version, and an unpinned boundary claim silently rots.

Corollary: five named library declarations in one draft did not exist. Treat every
declaration name you write as a claim requiring evidence, at the same standard as
a mathematical one.

## 2. Targets: the literalness test

A target record's `inputs` and `outputs` must be **literal**: a declaration name
that greps, a tag that fetches, a file path that exists. Not a description of the
kind of thing that would go there.

The test is mechanical — can a validator resolve it? If not, it is a lead, not an
input. The degenerate case is real: one input in a committed draft was a literal
ellipsis, and it passed human reading twice because prose scans as intent.

Each target also carries an **acceptance check**: the command or statement that
decides doneness, written before the work, by someone who is not going to do it.

One more trap, observed: a target whose acceptance criterion **its own content
cannot reach**. A numerical target proposed distinguishing two variants that first
differ at n = 3, while the computation it specified was only valid below that. The
target was internally consistent, well-formed, validator-clean, and unachievable.
Check that the acceptance criterion is reachable *by the declared method*, not
merely well-defined.

## 3. Edges: type them, then pick the cycle union deliberately

Edges are typed. The distinction that carries the most weight is between an edge
that **discharges** an obligation and one that merely **restates** it, because
only the first reduces the work and both look identical in prose.

Then the decision that actually bites: **which edge types enter cycle detection.**
Cycle detection over a subset of edge types will not find a cycle that runs
through an excluded type. This happened, and it was the single most consequential
defect found in the whole effort: a genuine circularity between two targets was
invisible because the edge type connecting them was excluded from the check. The
graph validated clean while an entire spine of the roadmap — every target from
layer 4 to layer 8 — was undispatchable, because nothing in it could be started
without something downstream of it.

State the union explicitly in the validator, and justify each exclusion. An
excluded edge type is a hole you have chosen; choose it on purpose.

## 4. Grade for dispatch, not difficulty

A–E is a **dispatch decision** — can an agent be handed this target now, with what
supervision — and not a rating of mathematical depth. The two come apart: a deep
theorem with a literal statement and a clean acceptance check is dispatchable; a
shallow lemma whose statement depends on an unresolved definitional choice is not.

Grading before the boundary check (phase 1) inverts the meaning: what you record
as "hard" is often "I did not check whether it already exists."

## 5. Run the validator on your own draft, expecting it to fail

The validator must be **executable**. A schema documented in prose is a wish; the
only version that binds is the one that runs and returns findings.

The argument for this is the strongest empirical result in the effort: the
validator, run against the draft written by the same agent that wrote the
validator, returned **eight findings** — seven data errors and one bug in the
validator itself. The data errors were statuses claimed on evidence the gate
rejects, and a conditional result naming no conditions. All eight were invisible
to careful reading, twice.

Two structural requirements follow from later failures:

- **The gate must be a typed predicate, not a plausibility judgment.** The
  evidence requirement is a list of sets, satisfied iff *every* set intersects the
  evidence non-emptily. Implemented as a single set tested by intersection, the
  strongest status in the system was reachable with **no proof evidence at all**.
- **Unknown fields are a hard error.** Silently dropped unknown fields mean a
  typo'd field name is a field that does nothing, and the record reads correct.
  One docstring claimed strictness while the code dropped silently.

Also verify the *vendored* copy, not the canonical one. A check that hashes the
canonical file while the consumer reads a vendored file detects nothing.

## 6. Review per dimension, and re-verify after the commit

Reviews are scoped to a dimension — statements, dependency structure, citation
fidelity, the mathematics itself — and run adversarially, with the reviewer asked
to refute rather than to assess. Aggregate reviews return aggregate findings.

Two process rules earned the hard way:

**Re-verify after the commit that lands the fix, not before it.** Three BLOCKING
findings in one session were *recurrences of defects already fixed*. The mechanism
is exactly this: corrections were verified in the working tree, the commit landed,
and nothing re-checked the committed state. A fix verified pre-commit is a fix you
believe in, not a fix you have.

**Re-check every sibling copy after fixing a shared file.** Same mechanism, spatial
rather than temporal.

And a rule about the review record itself: a review that did not run has no
findings, and writing its findings in advance because the dispatch is in flight
corrupts the one artifact whose whole value is accuracy. When a dispatched review
dies, record that it died and retain the brief. Do not delete the failure; a
negative record is evidence.

Related, and subtle: **never sweep pins with a regex.** A live pin that must be
updated and a historical record of what a pin used to be are textually identical.
One blanket substitution turned an accurate account of one change into a false
account of a different one.

## 7. Dispatch one target — the only measurement that counts

The decisive question about a roadmap is not whether it is well-formed, internally
consistent, or favourably reviewed. It is **whether an executor can act on one
target without coming back to ask what it means.**

That is measured by dispatching a target. It is not measured by another review.

This is the process's own worst observed failure, and it is a failure of
proportion rather than of correctness: thirteen review passes, four rounds of
findings, two validator-clean roadmaps, **zero targets dispatched, zero lines of
mathematics.** The reviews were individually justified and collectively a
substitute for the measurement. A roadmap that has been reviewed thirteen times
and executed zero times has an unknown value, and the cheapest way to learn its
value was available the whole time.

When phase 5 is clean, dispatch the target with no incoming dependency edges,
scoped hard:

> Implement only target `<ID>` at revision `<SHA>`. Read the target record and all
> declared inputs. Do not expand mathematical scope. Create only the declared
> modules and acceptance examples. If the statement is underspecified, stop and
> write a blocking report. Report files changed, declarations added, acceptance
> commands, unresolved assumptions, and downstream targets requiring review.

Two details: re-derive the revision at dispatch time rather than trusting a pin
written earlier, and treat a returned blocking report as the **success case** for
the roadmap — it located an underspecification for the price of one agent instead
of one review round.

---

## Anti-patterns, each observed

| Pattern | Why it fails |
|---|---|
| Graph first, census second | targets that cannot be stated, because what they reduce to has no name |
| Grade first, boundary second | "hard" recorded where "already exists" was true; downstream targets blocked on it |
| Prose inputs | unresolvable by any check; an ellipsis survived two readings |
| Cycle detection over a convenient edge subset | a real circularity invisible while the graph validates clean |
| One evidence set tested by intersection | the strongest status reachable with no proof evidence |
| Reviewing instead of dispatching | thirteen reviews, zero executions, value still unknown |
| Regex over pins | a historical record silently rewritten into a false one |
| Baseline control aimed at canonical files | an unguided agent told to "fix the plan" edits the real artifact |
