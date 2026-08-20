# N5: dry-run as a runtime mode — proposal, and the owner's ruling

**Status: the inversion proposed here was DECLINED. ARMED remains the default
and N5 stands as adopted.** The implemented behaviour matches N5: the mode
tokens are brakes, not enablers, and an absent token means auto-execute.

**No POLICY.md amendment is required or proposed any more.** This document is
retained as the decision record for why the question was raised, what was
argued on both sides, and what was built as a result. The rejected argument is
kept in full rather than deleted — a rejected argument that is written down is
worth more than one that vanishes, and if the classifier's measured α ever
comes in badly this is the analysis someone will want.

**Date:** 2026-08-19 · **Author:** implementation agent · **Adjudicator:** the owner

## 0. The ruling

Proposed: invert N5 so an absent token means DRY-RUN, requiring a positive
token to auto-execute. **The owner declined it.** Verbatim: *"Yeah, no. That's
not the default."*

**ARMED is the default.** Unset or absent tokens mean auto-execute; a token
reading `false` pins DRY-RUN. Brakes, not enablers — which is what
`paths.toml` and N5 already said, and what the doctrine has said since
2026-06-23. This restores the stated design rather than changing it.

The argument in §2a below was relayed in full and lost on the merits.

**What shifted underneath it, and this matters:** the case for a dry-run
default rested on the gate being untrustworthy — and it was, in four separate
ways documented in §1.3. Those are now fixed. Arming a gate that refuses
category E from frontmatter, refuses unresolvable briefs, refuses missing
classifier evidence, and refuses sub-threshold confidence is a materially
different act from arming the gate that permitted all four on the morning of
2026-08-19. The safety work is what makes the default defensible; the default
was never the safety mechanism.

**Implemented accordingly:** absent → ARMED, `false` → pinned DRY-RUN
(recorded distinguishably), `false` + `expires=` → temporary pin that
auto-resumes, unreadable → DRY-RUN. Either level alone can pin, so stopping
automation stays a one-place act.

---


---

## 1. Why the question was raised

The owner's directive, as refined mid-task, is that **dry-run should be a
runtime mode that can be turned on and off** — not a designation that gets
deleted once. That reframing is the right one and it is what is implemented:
`catch-no-brainer` now runs in DRY-RUN (classify and propose, mutate nothing)
or ARMED (classify and execute), the active mode is observable on demand, and
it flips in both directions at runtime without editing any skill or formula
file. Returning to dry-run is one command and is always permitted.

What follows is the mechanism work that had to happen before ARMED was safe to
reach at all, plus the now-settled question of which mode an unconfigured city
is in (§0: ARMED). Acting on "just take it off dry-run" literally, on the
morning of 2026-08-19, would have been unsafe — for a reason that only shows
up when you look at the mechanism rather than the documents.

The `catch-no-brainer` skill carried the designation **"PRELIMINARY v0.2 —
DRY-RUN ONLY"**. That designation was, in practice, *the entire safety
mechanism*. Everything downstream of it — the N5 kill-switch hierarchy, G12,
B2.9 — was documented but under-enforced, so removing the words "DRY-RUN
ONLY" would have armed auto-execution with nothing meaningful in its way.

Three measured facts (2026-08-19, this session):

1. **The brake is in the "go" position and always was.**
   `<city-root>/.beads/auto_merge_enabled` **exists and reads `true`**
   (mtime 2026-07-15). No rig-level flag exists in **any** of the 23 rig
   `.beads/` directories under the city root. By N5's own semantics —
   *"absent or `true` → proceed"* — automation is authorized everywhere,
   city-wide, right now.

   (Note for the record: a prior framing held that the city flag was
   *absent*. It is not absent; it is present and reads `true`. The
   conclusion is the same and slightly worse — the permissive state was
   written deliberately at some point, not merely defaulted into.)

2. **The gate that reads the brake was attached to the wrong step.**
   `brief-check.sh no-brainer-execute-safety` does read both flags. But in
   `formulas/no-brainer-classify.toml` it was wired to
   `enforce-safety-exclusions` — the *classification* step — while
   `guarded-execute`, the step that actually mutates, ran
   `brief-no-brainer-safety.sh`, which does **not** read the switches at all.
   The check was also evaluated before the classifier evidence it depends on
   existed. So the mutating step carried no switch check.

3. **The gate was fail-open in the ways that matter.** Measured by executing
   it against fixtures before any change (all of these returned exit 0 —
   i.e. *permitted*):
   - a brief with `server_touching: true` in frontmatter — category E,
     the one exclusion that is supposed to be absolute — **passed**, because
     the gate only matched the `G5 Server-touching: FAIL` token and never the
     frontmatter key that `brief-prep`'s Override 1 actually writes;
   - a brief path that does not resolve — **passed**, silently;
   - a brief with no classifier evidence at all — **passed**;
   - a brief classified `candidate`, or `known_no_brainer` at
     `confidence=0.5` — **passed**.

So the honest description of the pre-change state is: *the only thing
standing between the live brief corpus (89 files in
`<city-root>/.beads/briefs/stack/`, measured this session) and city-wide
auto-execution was a line of prose in a skill file's header.*

## 2. The argued defect in N5 as written (superseded by the ruling)

N5 says: *"automation runs unless a kill switch is ENGAGED"*, with
**absent or `true` → proceed** at both levels.

Absent-means-go is the wrong default for an irreversible action:

- **A fresh install is armed.** A new rig has no flag file, so it is
  authorized to auto-execute before anyone has considered whether it should
  be. Safety that requires an operator to *remember to add a file* is not
  safety.
- **A released brake is indistinguishable from a decision to automate.**
  `true` in `auto_merge_enabled` means "not currently halted". It does not
  record that anyone decided this classifier was good enough to act
  unattended. Those are different claims and the file conflates them.
- **It is the opposite of the doctrine this codebase already adopted
  elsewhere.** `mctl_core/work.py` gates live dispatch on
  `MCTL_ENABLE_LIVE_DISPATCH` with the comment *"Not armed: behave exactly
  like a dry run"*, and refuses when the control plane is merely *unknown*
  (`is not True`, deliberately not `is False`) because *"arming a real
  `gc sling` is irreversible, so an unknown control plane must refuse."*
  N5 asks the same class of question and answers it the opposite way.
- **The thing being armed is self-declared PRELIMINARY.** The classifier's
  category set is a v0.x heuristic, and N8's α — the empirical wrong rate
  that is supposed to justify the 0.85 threshold — has **never been
  measured**, because the ledger N8 depends on was never written. N5 grants
  unattended execution to a classifier whose accuracy is by its own policy's
  admission unknown.

## 2a. The declined argument (preserved) — why I recommended a dry-run default

There is a genuine tension here and it deserves a straight answer rather than
a silent choice.

**For "default armed":** `paths.toml` states *"Auto-execute is the DEFAULT;
the switches below are safety brakes, not enablers."* The 2026-06-23 doctrine
says a no-brainer should never be surfaced and that surfacing one is a
**pipeline regression** (N6). And the version history is genuinely damning for
the status quo: v0.0 shipped DRY-RUN on 2026-06-24, one day after the
auto-execute doctrine was decided; v0.3 (2026-07-12) then defined an
auto-execution *threshold* (`confidence >= 0.85`) and an α-measurement
substrate — for a mode that had never once been switched on. Downstream
already assumes it happened: `present-it` consumes `compact_eligible`.
Dry-run was a proving state that outlasted its purpose by two months, not a
deliberate resting place. I accept that reading.

**Recommendation (DECLINED by the owner, 2026-08-19): default DRY-RUN;
destination ARMED, per category, on measured evidence.**

The argument for "default armed" is an argument about the *destination*, and
it is correct about the destination. It is being used to settle a different
question. Two distinct defaults are being conflated:

- **(a) the default disposition of a matched no-brainer in a system that is
  trusted** — auto-execute, never surface. The doctrine is about this, and I
  agree with it.
- **(b) the value an unset configuration flag takes on a machine nobody has
  configured.** This is not a claim about no-brainers at all; it is a claim
  about what *unset* means.

`paths.toml` collapses (a) into (b). The consequence is that every rig that
has never been thought about arrives pre-armed, and a flag that is absent
because nobody considered the question is indistinguishable from a flag that
is absent because somebody decided. A default that cannot be told apart from
an un-made decision is not a default; it is an accident with a rationale
attached.

Three things decide it:

1. **The policy that mandates auto-execute also forbids assuming it is safe.**
   N8, same rule set, says the 0.85 threshold's calibration is *"an empirical
   question answered from the audit ledger, not assumed"*, and that a category
   whose α exceeds `S/(S+T)` is net-negative and must be raised or removed.
   The ledger has **zero rows** — it was never written. So N5's default has
   been resting on a measurement N8 explicitly refuses to assume.
2. **The costs are asymmetric, and so the default should be.** Defaulting to
   dry-run costs exactly what N6 describes: some obvious briefs get surfaced
   and the human says "why am I seeing this". That cost is visible, cheap, and
   self-correcting — the complaint *is* the repair signal. Defaulting to armed
   costs a wrong irreversible execution whose defining property is that nobody
   was looking. Symmetric defaults for asymmetric costs is the error.
3. **"Brake it if it misbehaves" needs someone to notice.** The toggle makes
   this argument stronger than it used to be — rollback is now one command —
   and I want to concede that honestly. It still fails on the initial default,
   because you can only brake what you observed, and the failure mode of a bad
   auto-execution is precisely that it was never surfaced to anybody.

**What flips my recommendation, concretely.** This is not "never":

- Run unarmed over live traffic. Every evaluation now writes a `REFUSED /
  not_armed` audit line carrying the category and confidence that *would* have
  executed. That is shadow mode at zero risk, and it is the ledger N8 has
  always required.
- Compute α per category from those rows and compare against `S/(S+T)`.
- Arm one rig, one category set, with an `expires=` token measured in days.
- For any category whose measured α clears the N8 bar, **flip that category's
  default to armed** — at which point "auto-execute is the DEFAULT" becomes a
  measured statement rather than an aspiration, and N6 gets the behaviour it
  has been asking for since June.

The mode being a toggle is what makes this cheap: choosing dry-run today does
not cost a code change later, it costs one file.

## 3. What was built (N5-conformant, no amendment needed)

N5's switch model is unchanged in substance — brakes, not enablers — and gains
a two-position runtime mode with an observable state and a one-command
rollback. The text below describes the implemented behaviour. It is NOT a
proposed policy edit; it is here so the mechanism is written down somewhere
normative-looking without pretending to be policy.

> **Auto-execution is a runtime mode; ARMED is the default; the tokens and
> kill switches are brakes.**
> When the classifier returns a confident registry-backed classification AND
> all stop gates pass, the brief auto-executes without surfacing to the human
> adjudicator **only if the executing rig is ARMED**. Otherwise the brief
> stays on the human presentation path — unarmed behaves exactly like a dry
> run.
>
> - **Mode tokens (brakes).**
>   `<city-root>/.beads/no_brainer_auto_execute_armed` and
>   `<rig_root>/.beads/no_brainer_auto_execute_armed`. **Absent → ARMED**;
>   `true` → ARMED (explicit, same effect); `false` → DRY-RUN pinned;
>   `false` with `expires=<ISO-8601-utc>` → DRY-RUN until that instant, then
>   the ARMED default resumes on its own; anything unreadable → DRY-RUN.
>   **Either level alone** can pin DRY-RUN, so stopping automation is a
>   one-place act.
> - **Unreadable is not consent.** An absent token means "take the default";
>   a malformed one means "somebody tried to say something we cannot read".
>   Those are different claims, and only the first is a default. mctl's live
>   dispatch resolves the same ambiguity the same way.
> - **The mode toggles in both directions at runtime**, with no edit to any
>   skill or formula file, and the active mode MUST be answerable on demand
>   (`brief-check.sh no-brainer-mode`). Pinning DRY-RUN is always permitted,
>   needs no authorization, takes effect immediately, and has a one-command
>   form (`brief-check.sh no-brainer-disarm`) that works from any rig.
>   Returning to ARMED is a deliberate `rm` of the tokens. The easy direction
>   is the safe one.
> - **Stop gates outrank the mode entirely.** Category E / server-touching,
>   G5b user-skill-touching, L4, and `classifier_state=safety_blocked` refuse
>   regardless of mode or switch state, and are evaluated before either is
>   read. This is the property the armed default rests on.
> - **A pinned DRY-RUN is recorded distinguishably** from an unreadable token
>   and from the absent default, in both the audit trail and the mode report,
>   so an operator can confirm a rollback landed instead of inferring it.
> - **Executor check order:** (1) resolve the brief, refuse if unresolvable;
>   (2) stop gates; (3) classifier evidence; (4) kill switches; (5) mode;
>   (6) execute. A refusal at any step is audited and never silent.

## 4. What is implemented, and what is policy

The mode and the gate are **implemented and tested**: `brief-check.sh
no-brainer-execute-safety` (the gate), `no-brainer-mode` (observe),
`no-brainer-disarm` (roll back), with 33 cases in
`tests/brief-no-brainer-arming/test_no_brainer_arming.sh` — including the
toggle proven in both directions, a full armed → dry-run → armed → dry-run
round trip, category E refused across toggles, and the audit contract.

**`POLICY.md` is untouched and needs no amendment.** The implementation now
matches N5 as adopted, which is the whole point of the ruling: the earlier
divergence (a conservative arming requirement) has been removed rather than
regularised. `paths.toml`, `gates.toml` G12, the formula, the skill,
`CITY-OPERATION-REFERENCE.md` and `DOGFOOD.md` all state the ARMED default.

## 5. Consequence of the ruling: the install gap is now load-bearing

Under a dry-run default, one caveat was minor. Under an armed default it is
the whole safety story, and it should be tracked as its own work:

**The gate scripts are installed in one rig.** Formulas exec their checks at
`<rig_root>/.gc/scripts/checks/…`. That directory exists in **hecke and
gascity-packs only** — and only hecke actually carries
`brief-no-brainer-execute-safety.sh`. It is **absent from every
`mathcity.brief-operator*` rig**, which is the pool the `no-brainer-process`
order actually runs in. Flagged as D9 in the 2026-08-19 drift audit and
originally in `DOGFOOD.md` on 2026-07-11.

**Reading of the runner says this fails closed** (gascity
`internal/convergence/condition.go::ResolveConditionPath` errors on a
non-existent path — its own comment: *"a dangling or unresolvable
conditionPath must fail gate resolution here"* — and
`internal/dispatch/ralph.go` returns that error to the caller without ever
reaching `GatePass`). **This was NOT executed**: the gascity module does not
build in this environment (`go-icu-regex` needs ICU headers that are not
installed), so the claim rests on code reading plus an upstream test that
asserts the error return, not on a run.

Two things follow:

1. **Install the checks into every rig that runs the pool**, so the gate's
   protection does not depend on the runner's failure mode at all. This is
   the real fix and it is a one-line consequence of D9.
2. Until then, the pack-side invariant is pinned by test 31: no formula in
   this pack may reference a check script the pack does not ship. That closes
   the drift this repo controls; it does not close the install gap.

## 6. Where the declined argument would become relevant again

Not a re-litigation, a tripwire. The audit ledger now being written
(`decisions/no-brainer-execution.jsonl`) records category and confidence on
every PERMITTED line, which makes N8's α computable for the first time. If α
for any category exceeds `S/(S+T)`, N8 already requires that category's
threshold be raised or the category removed — no amendment needed, that is
adopted policy. §2a is the analysis to reach for if that happens.

Nothing in this branch armed or disarmed anything in the live city: no mode
token exists anywhere under the city root, `<city-root>/.beads/auto_merge_enabled`
is untouched at its 2026-07-15 mtime, and no brief, bead, or order was executed.
