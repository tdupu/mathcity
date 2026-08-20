# DRAFT — N5: dry-run as a runtime mode (NOT ADOPTED)

**Status: DRAFT. Not adopted. Not in force.** This document proposes an
amendment to `subdomains/brief-system/POLICY.md` rule **N5**. It must go
through `new-brief-policy` and be adjudicated before any of it becomes
policy. Nothing here has been written into POLICY.md.

**Date:** 2026-08-19 · **Author:** implementation agent · **Adjudicator:** the human adjudicator

---

## 1. Why this is being proposed

The owner's directive, as refined mid-task, is that **dry-run should be a
runtime mode that can be turned on and off** — not a designation that gets
deleted once. That reframing is the right one and it is what is implemented:
`catch-no-brainer` now runs in DRY-RUN (classify and propose, mutate nothing)
or ARMED (classify and execute), the active mode is observable on demand, and
it flips in both directions at runtime without editing any skill or formula
file. Returning to dry-run is one command and is always permitted.

What follows is about the remaining open question — **which mode an
unconfigured city should be in** — plus the mechanism work that had to happen
before ARMED was reachable at all. Acting on "just take it off dry-run"
literally would have been unsafe, for a reason that only shows up when you
look at the mechanism rather than the documents.

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

## 2. The specific defect in N5 as written

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

## 2a. The default is the real question — recommendation and reasoning

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

**Recommendation: default DRY-RUN. Destination ARMED, per category, on
measured evidence.**

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

## 3. Proposed amendment

Replace N5's switch model with **a two-position runtime mode**: brakes
(unchanged, still halt) plus a positive arming token that selects ARMED.

> **N5 Auto-execution is a runtime mode; DRY-RUN is the default; kill
> switches remain brakes.**
> When the classifier returns a confident registry-backed classification AND
> all stop gates pass, the brief auto-executes without surfacing to the human
> adjudicator **only if the executing rig is ARMED**. Otherwise the brief
> stays on the human presentation path — unarmed behaves exactly like a dry
> run.
>
> - **Arming tokens (positive, both required).**
>   `<city-root>/.beads/no_brainer_auto_execute_armed` **and**
>   `<rig_root>/.beads/no_brainer_auto_execute_armed`. A token selects ARMED
>   when its first line is exactly `true`; it MAY carry a second line
>   `expires=<ISO-8601-utc>`, past which it lapses back to DRY-RUN on its own.
>   A token reading `false` **pins** DRY-RUN. Absent, malformed, expired, or
>   pinned at either level → DRY-RUN. Both tokens are required to reach ARMED
>   so that arming is a per-rig decision and no single act can arm the whole
>   city.
> - **The mode toggles in both directions at runtime**, with no edit to any
>   skill or formula file, and the active mode MUST be answerable on demand
>   (`brief-check.sh no-brainer-mode`). Returning to DRY-RUN is always
>   permitted, needs no authorization, takes effect immediately, and has a
>   one-command form (`brief-check.sh no-brainer-disarm`). Reaching ARMED
>   takes two deliberate acts; leaving it takes one. That asymmetry is
>   intentional: the recovery path must be the easier one.
> - **A pinned DRY-RUN is recorded distinguishably from a never-armed one**,
>   in both the audit trail and the mode report, so an operator can confirm a
>   rollback actually landed instead of inferring it from silence.
> - **Kill switches (negative, retained).** `auto_merge_enabled` at city then
>   rig level: a file that exists and reads `false` halts, exactly as before.
>   A released brake is **not** an arming signal.
> - **Stop gates outrank both.** Category E / server-touching, G5b
>   user-skill-touching, L4, and `classifier_state=safety_blocked` refuse
>   auto-execution regardless of arming or switch state. This is a stop-gate,
>   not a preference.
> - **Authorization.** Creating or renewing either token requires explicit
>   human authorization recorded as a STANDALONE decision bead, on the same
>   terms N5 already requires for engaging or releasing a brake. Disarming
>   requires nothing — deleting either file is always allowed and always
>   takes effect immediately.
> - **Executor check order:** (1) resolve the brief, refuse if unresolvable;
>   (2) stop gates; (3) classifier evidence; (4) kill switches; (5) arming
>   tokens; (6) execute. A refusal at any step routes the brief to the pile
>   in compact form and is never silent.

Consequential edits if adopted: **G12** (`gates.toml`) description; **B2.9**
and **N7** to name the execution audit log; `paths.toml`
`arm_token_city` / `arm_token_rig` / `no_brainer_execution_log`; and the N5
prose in `formulas/no-brainer-classify.toml`, `skills/create-brief/SKILL.md`,
`skills/brief-prep/SKILL.md`, `docs/CITY-OPERATION-REFERENCE.md`,
`subdomains/brief-system/DOGFOOD.md`.

## 4. Relationship to what has already been implemented

The mode and the gate described above are **implemented and tested** as of
this branch — `brief-check.sh no-brainer-execute-safety` (the gate),
`no-brainer-mode` (observe), `no-brainer-disarm` (roll back) — with 30 cases
in `tests/brief-no-brainer-arming/test_no_brainer_arming.sh`, including the
toggle proven in **both** directions and a full dry-run → armed → dry-run →
armed round trip. The policy text is **not** amended.

This is a deliberate and, I think, defensible asymmetry: the implemented gate
is **strictly more conservative** than N5 as adopted. It refuses in cases
where policy would permit; it never permits where policy would refuse. A gate
that under-permits cannot cause the harm N5 exists to prevent, whereas
waiting for adjudication before fixing a fail-open execution path would leave
the fail-open path in place in the meantime.

It is still drift, and it should not be left standing. Adopting this
amendment closes it. **Rejecting** this amendment also closes it — in that
case the arming requirement should be removed from `brief-check.sh` and the
other fixes (stop-gate coverage, fail-closed brief resolution, classifier
evidence, audit trail) kept, since none of those depend on it.

## 5. Recommendation on the owner's actual request

The owner asked for a mode that turns on and off. **That exists now, in both
directions, and it is tested in both directions.** What remains is the
default, and my recommendation is to **leave the default at DRY-RUN and not
arm anything yet** — see §2a for the full argument.

The reason is no longer the switch; the switch is real now. It is N8: the
classifier is PRELIMINARY, and α has never been measured because the ledger
was never written. The audit log added in this branch
(`decisions/no-brainer-execution.jsonl`) **is** that ledger. The sequence that
gets the owner what they actually want:

1. Land this branch. Dry-run is a mode, not a designation; the gate is real;
   the mode is observable and reversible.
2. Run the pipeline in DRY-RUN over live briefs. Every evaluation writes a
   `REFUSED / not_armed` audit line carrying the category and confidence that
   *would* have executed. Shadow mode, zero risk, and it is the first time
   N8's substrate has ever existed.
3. When enough rows exist, compute α per category and compare to `S/(S+T)`.
4. Arm **one** rig with an `expires=` token measured in days. Watch the log.
   Widen on evidence, or `no-brainer-disarm` and go back to step 2.

Nothing in this branch armed anything: no arming token exists in the live
city, `<city-root>/.beads/auto_merge_enabled` is untouched, and no brief, bead,
or order was executed.
