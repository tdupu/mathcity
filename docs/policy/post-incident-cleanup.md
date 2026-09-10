# Post-incident cleanup: work stranded by a dispatch defect

**Status:** active. Written 2026-09-10 from the `brief-shuffle-on-submit`
fan-out incident (kolchin), which stranded 14 workflow roots over 17 days
without producing a single diagnostic.

## The incident this generalizes

`brief-shuffle-on-submit` was `scope = "rig"` + `trigger = "event"`. A
rig-scoped event order fires in **every** registered rig, not only the rig
where the event originated. One `brief.submitted` in the testrig poured
`brief-shuffle` into all three rigs. Measured in `.gc/events.jsonl`:

```
74   brief-shuffle-on-submit:rig:mathcity
74   brief-shuffle-on-submit:rig:gascity
```

Exactly 74 and 74 — neither rig has a `.beads/briefs/` tree, so neither could
have originated one such event, let alone 74.

**The pour alone was survivable.** `brief-shuffle` handles a missing pile
correctly: the EMPTY-PILE ROUTE records `claim_result=empty` and exits clean.
What made it harmful was that `mathcity.brief-operator` sits at `max=0`, so
nothing ever claimed the work and the clean-exit path was never reached. The
workflows just stayed open.

## Rule 1 — Stop the pour before clearing the strand

**Never close stranded work while the mechanism that stranded it is still
running.** Closing first clears one batch and leaves the source pouring; the
next audit rediscovers the same shape and reads it as a *new* problem.

Order of operations, without exception:

1. **Identify the pour.** Which order, which trigger, which pool.
2. **Fix or disable the pour**, and pin the fix with a test.
3. **Verify the pour has stopped** — count new roots after the fix, not
   before.
4. *Then* dispose of the stranded work.

The temptation runs the other way, because the strand is what shows up in a
status view and the pour does not. Resist it.

## Rule 2 — Diagnose before disposing, and record the diagnosis

Stranded roots are **evidence**. Before closing any of them, establish and
write down:

- the **defect** that poured them (order name + the specific misconfiguration)
- the **window** — first and last strand, so the blast radius is bounded
- whether any strand did **partial work** (files written, beads mutated,
  external calls made) — those need unwinding, not just closing
- what **should** have happened had the dispatch been correct

Close with a reason that names the defect and links the fix. A bare
`bd close` on a stranded root destroys the only remaining record that the
dispatch was ever wrong.

## Rule 3 — Do not "fix" the symptom by relaxing a safety control

In this incident the stranded steps were routed to a pool capped at `max=0`,
so the strand read convincingly as *"the caps are starving the work"* —
tdupu/mathcity#274 read it exactly that way, and lifting the cap looks like
the fix.

It is the opposite of the fix. The cap is downstream. A live operator would
have claimed these and run `brief-shuffle` against a rig with no pile.
**Lifting the control would have converted stranded work into wrong work.**

When a strand appears to be caused by a limit, first ask whether the limit is
the thing *revealing* the defect rather than *causing* it. Caps, gates, and
guards are usually the messenger.

## Rule 4 — Every strand implies a missing detector

A dispatch defect that runs 17 days is not primarily a config bug; it is a
**detection** bug. The config error is one line and takes one minute to fix.
The reason it survived two and a half weeks is that nothing anywhere reported
it.

The general shape, worth stating plainly because it recurs:

> **A workflow dispatched to a pool that cannot staff it produces no
> diagnostic at any layer.** It is not an order failure — the order fired
> successfully. It is not a stuck-bead hit — the beads carry `gc.routed_to`
> and read as ordinary routed work. It is not a `gc doctor` failure. It is
> silent, and it accumulates.

For every incident of this class, ship a detector alongside the fix. At
minimum, cross-reference pool caps against the orders routed to them: any
pool at `max=0` that is still an order's `pool` target is a silent
accumulator, and every order pointed at it is a future strand.

## Rule 5 — Pin the invariant, not the instance

Fixing the one bad order file leaves the next one free to make the same
mistake. Pin the **class** with a test that sweeps every config of that kind.

`tests/mctl/test_event_orders_do_not_fan_out.py` asserts that no order is
both `trigger = "event"` and `scope = "rig"`, across the whole catalog. It
failed on exactly one file and passes on the other eight — which is also how
the "this is a singleton" claim got measured instead of eyeballed.

Include the assertion that the sweep is non-empty (P6.2): a check that could
not fail must not render as passed.

## Checklist

```
[ ] pour identified (order + trigger + pool)
[ ] pour fixed or disabled
[ ] fix pinned by a catalog-wide invariant test, sweep proven non-empty
[ ] pour verified stopped (new-root count AFTER the fix)
[ ] strand window bounded (first + last)
[ ] partial work identified and unwound, or explicitly confirmed to be none
[ ] detector shipped for the silent-failure mode
[ ] strand closed with a reason naming the defect and linking the fix
[ ] safety controls left in place, or lifted only with separate justification
```

The disposal step is last on purpose.
