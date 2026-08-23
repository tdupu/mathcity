# `mathcity.work` commissioning contract

**Status:** Draft · **Issue:** tdupu/mathcity#6 · **Governs:** `commission-work-briefed`

## What kind of document this is

**Prescriptive.** Every clause states an obligation the implementation must meet,
and names a **violating case** — a concrete situation in which the clause fails.

**A clause with no violating case is descriptive and does not belong here.** A
contract derived from what the implementation already does cannot be violated:
every future change is automatically compliant, because compliance was defined
as whatever the code happens to do. That is a check that cannot fail, promoted
to the document that governs the code.

**Consequence, accepted deliberately:** clauses below are **failed by
`commission-work-briefed` as it stands today.** That is the contract working.
A clause is not softened to make the current implementation pass; the
implementation changes, or the clause is shown to be wrong on its merits.

**Grep is not evidence.** All five of `#6`'s acceptance criteria match by string
search against the formula today — including one whose command takes 43 seconds
and cannot serve an interactive request. **Presence is not performance (CT13.1).**

---

## C1 — Two modes, and the boundary is decidable

`mathcity.work` distinguishes **continue known work** from **commission fresh or
ambiguous work**, and the decision is made from inspectable state, not from a
model's read of the request.

**Violating case:** an implementation where the same input can enter either mode
depending on phrasing, with no recorded reason. If two invocations with the same
bead and the same objective can diverge, the boundary is not decidable.

**Today:** PASSES — the formula names both modes and routes on bead state.

---

## C2 — Fresh or ambiguous work cannot reach dispatch without a brief

Work classified fresh or ambiguous **must** produce an approval brief and be
adjudicated before any dispatch call is made.

**Violating case:** any path from classification to `work_dispatch` that does not
pass through an adjudicated brief. A direct-dispatch escape hatch, a `--force`
flag, or a fallback that dispatches when brief creation fails all violate this.

**Today:** PASSES — CT4.5 and the formula both require the brief first.

---

## C3 — The catalog is enumerated at runtime, **within a stated budget**, and
degrades to a named state rather than blocking

Commissioning reads the live formula catalog rather than a hardcoded list. The
read carries an explicit time budget, and on exceeding it reports a named
`unreachable` state — **never an empty catalog, and never an unbounded wait.**

**Violating case:** an unbounded `gc formula list`. **Measured 43 s in-city on
2026-08-23**, against a `gc` whose per-invocation cost was separately measured at
28–89 s across one night. An interactive caller cannot wait that long, and a
catalog that returns empty because the read failed is indistinguishable from a
city with no formulas.

**Today: FAILS.** `commission-work-briefed` calls `gc formula list` unbounded.

**Why this clause exists:** `orders_status` shipped to `main` on 2026-08-23
registered, schema-correct, and with 1,198 passing tests — and hung for 120 s,
because the same class of call was unbounded. The tests injected a fake reader,
so the suite never paid the cost. **This clause is that defect written down
before it recurs.**

---

## C4 — Existing work is reconciled before a new graph is proposed

Commissioning searches for work already covering the objective and reports what
it found, **including when it found nothing**, before proposing a dispatch graph.

**Violating case:** a reconciliation step whose "no existing work" result is
indistinguishable from "reconciliation did not run." If the brief cannot show
which of those occurred, the step is unfalsifiable.

**Today: FAILS** — verified against the formula, not assumed.
`reconcile-existing-work` is mandatory and requires appending:

```
- `## Existing Work Reconciliation`
- Existing beads/issues/briefs/branches FOUND
- Whether each item is attached, reused, superseded, or irrelevant
- Any duplicate-work risk that approval must see
```

**Every bullet is about items found. Nothing requires the step to state that it
searched and found nothing.** So a genuine null result and a step that silently
did not run produce the same brief section — an empty or absent one. A judge
reading the brief cannot tell "no duplicate work exists" from "nobody looked."

**The fix is one line in the step:** require the searches run and their result
recorded even when empty — `bd search <kw>: 0 matches` is a reported result;
silence is not.

---

## C5 — The approval brief carries every element a judge needs, and each is
independently checkable

The brief contains: objective, existing-work reconciliation, proposed graph,
selected formulas, test gates, brief gates, continuation metadata.

**Violating case:** a brief that satisfies this by naming empty sections. A
`## Test gates` heading with no gates under it passes any presence check and
tells a judge nothing. **Each element must be checkable for content, not
presence** — the same distinction as C3.

**Today:** UNVERIFIED — the formula produces all seven sections; whether any can
be empty and still pass has not been tested.

---

## How to change this document

**Raise a bound only when a larger cost has been MEASURED**, never to make a
failing call pass. **Delete a clause only by showing it is wrong**, never because
the implementation does not meet it.

**If a clause acquires no violating case, delete it** — it has become
descriptive, and a descriptive clause certifies whatever exists.
