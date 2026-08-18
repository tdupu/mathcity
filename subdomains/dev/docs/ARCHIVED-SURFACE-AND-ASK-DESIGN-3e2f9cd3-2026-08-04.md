---
title: "SURFACE-AND-ASK: run-time surface-and-ask loop for unresolvable worker dependencies"
kind: design-proposal
status: decision-ready
date: 2026-08-04
source_task: gsp-u9s2
workflow: gsp-0sutol
requirement_frame: 12-REQ (REQ-001…REQ-012)
routes_to: present-it / adjudicate-brief   # NOT brief-prep
rollback: "Remove this single file — it adds no code path, so deletion is a complete revert."
---

> ## ARCHIVED — UNADJUDICATED DESIGN, NOT ADOPTED POLICY
>
> **This document was never adjudicated and nothing in it is in force.** It
> describes a proposal, not a decision. Do not cite it as policy, precedent,
> or an approved plan.
>
> - **Source commit:** `3e2f9cd3af131d9112bf156a02edfd57d77182c3` (legacy `~/gt/gascity-packs` detached-HEAD worktree
>   population — the `#121` 56-commit salvage set), 2026-08-04, 479 lines.
> - **Archived:** 2026-08-14 under decisions-track brief **#148**, Option (A).
>   Taylor's verdict: *"unadjudicated-design-docs-disposition, do they have any
>   value at all? If not then file them away."*
> - **Value assessment (brief #148):** **GENUINELY VALUABLE** — complete, implementation-ready spec for a gap that is still open today (brief-system POLICY.md N4's capability-resolution path is still named-but-undefined). Its two transferable mechanisms — the query-auditable invariant + backstop sweep, and the `awaiting-direction` visible-pause marker — generalize past its own scope. Its detection layer does NOT cover today's wrong-answer-reported-as-success defects; see the index.
> - Nothing was deleted from the legacy tree; retirement is separately gated
>   under `gt-0g9die`. Full comparative assessment:
>   [`ARCHIVED-DESIGNS-INDEX-2026-08-14.md`](./ARCHIVED-DESIGNS-INDEX-2026-08-14.md).

---


# SURFACE-AND-ASK — run-time surface-and-ask loop for unresolvable worker dependencies

> **This is a DESIGN / PROPOSAL. Produce the design; do NOT execute it.** No
> detection-hook code, patrol/order TOML, `brief-decision-dispatch` edits,
> prompt-compiler code, worker-lifecycle changes, or formula/skill edits are
> made by this deliverable. The diff is this one document.

## Header — decision frame, scope, rollback

**What is being decided.** Whether to adopt the run-time loop specified below —
**detect → surface → adjudicate → clean-prompt → re-dispatch → unblock** — as the
sanctioned way an inside (gascity-managed) worker handles an *unresolvable
dependency* (a missing skill, config value, or tool it needs at run time), so it
**files a help-request and visibly pauses** instead of silently stalling; and to
confirm (or override) the seven design positions consolidated in
[§9 Open decisions for Taylor](#9-open-decisions-for-taylor-ac-10-req-012).

**Rollback (one line).** This deliverable adds a single design document and no
code path; rollback = remove
`mathcity/subdomains/dev/docs/SURFACE-AND-ASK-DESIGN-2026-08-04.md`.

**Diff-scope proof.** From the build branch,
`git diff --name-only <base>..HEAD` MUST list exactly one path:
`mathcity/subdomains/dev/docs/SURFACE-AND-ASK-DESIGN-2026-08-04.md` (base =
this branch's fork point, `b880ed3`). No formula, skill, TOML, or code path is
touched.

**Requirement frame.** This document answers the **12-requirement** frame
(REQ-001…REQ-012) of workflow `gsp-0sutol`, the superset that adds four deltas
over the sibling 8-REQ frame: (a) a worked **non-skill** example, (b) an explicit
**`brief-prep` exclusion**, (c) the **visible-pause** specification, (d) the
**`gsp-ioek` + `gsp-6szg` R10/R11** cross-reference. Requirement → section map is
in [§10](#10-requirement-coverage).

**Convergence note.** A sibling workflow (`gsp-ov0nle`, writing item `gsp-460s7p`,
closed `shipped`) targets this same path. Before authoring, the convergence
protocol was run: the file was searched across every git ref and the working
disk and found **absent** everywhere → this is the *Absent → build* branch. See
[§11 Convergence accounting](#11-convergence-accounting).

---

## §1 Invariant and scope (REQ-004, REQ-006, REQ-012 framing)

**Invariant.** *A detected unresolvable dependency can never end in a silent
stall — every such event either files a help-request brief, or trips the
control-plane backstop that files one.* Surfacing is not best-effort; it is the
property the whole loop exists to guarantee, and it is defended twice (primary +
backstop, §3) so it does not depend on the failing worker succeeding at anything.

**Scope.** An **inside (gascity-managed) worker**, at **run time**, cannot
resolve a dependency it needs to proceed. One class — *unresolvable dependency* —
with three instantiations:

- **skill** — a skill the step is told to invoke is not materialized in the
  worker's skill sink;
- **config** — a value the step needs (`gc.var.*` / rendered
  `gc.graphv2_vars.v1`) is absent or resolves empty;
- **tool** — an executable the step must run is not on `PATH`.

**Explicitly out of scope** (design boundary, REQ-012): implementing the loop;
redesigning the **plan-time P1.14** pre-flight (referenced as the run-time
boundary only, §2/§7); using **`brief-prep`** on this path (charge exclusion,
§4); auto-resolving dependencies (never silently install or invent — *surface and
ask*); and *fixing* the motivating incidents (`gsp-9biz`, `gs-vj2d`,
never-recorded-verdict, `gsp-ioek`) beyond covering their failure mode (§7).

---

## §2 Detection (REQ-001, REQ-002, REQ-003)

> **Owner:** gc-core **worker lifecycle layer** (the failure contract).
> **Trigger:** (a) claim/prepare-time preflight finds a declared dependency
> missing, or (b) first-use — the worker is instructed to use `X` and `X` does
> not resolve. **Input:** the step bead's contract + the worker's live runtime
> (sink contents, resolved `gc.var.*`, `PATH`). **Output:** a uniform structured
> failure record (below), step closed `fail`. **Failure-handling:** if the worker
> dies before recording, the §3 backstop sweep catches the orphaned bead; if
> detection is ambiguous (missing dep vs. ordinary task error), default to an
> ordinary `fail` (do not over-file) — the backstop only ever fires on the
> explicit `unresolvable-dependency` class.

**Detection layer decided (REQ-002): the gc-core worker lifecycle layer.**
This is the *one* layer that (i) can see the worker's actual runtime — its sink,
its resolved `gc.var.*`, its `PATH` — for **all three** kinds uniformly, and
(ii) already owns the fail-and-close contract, so it can attach structured
blocker metadata without a parallel mechanism.

**Rejected alternatives:**

- **Skill-invocation wrapper.** Sees only skills. It is blind to config and tool
  dependencies, so it would need a second, unrelated mechanism for the other two
  kinds — which defeats REQ-001's *one class* generalization. Rejected.
- **Pack layer (the skill's own body, à la P1.14).** A skill can probe *its own*
  declared deps and print a graceful error (that is exactly P1.14), but it cannot
  see the worker lifecycle, cannot file-and-close uniformly, and cannot cover
  dependencies that are not a skill's declared deps (e.g. a `gc.var` the *formula*
  needed but no skill declares). Every pack would also reinvent it. Rejected as
  the *owning* layer (retained as a frequency-reducing complement, §7).

**Layered detection (both layers, one contract):**

- **(a) Claim / prepare-time preflight.** Before the worker spends a run, check
  the dependencies the step declares/needs: required skills present in the sink,
  required `gc.var.*` non-empty, named tools resolvable on `PATH`. Catches
  known-missing dependencies early.
- **(b) First-use catch.** The condition *"instructed to use `X`; `X` does not
  resolve"* is recognized as **this** class, not folded into an ordinary error.
  This catches whatever the preflight could not predict.

**Uniform detection output** (the record that makes the class mechanically
catchable by the control plane):

```
gc.outcome              = fail
gc.failure_class        = unresolvable-dependency
gc.blocked_on.kind      = skill | config | tool
gc.blocked_on.name      = <the specific missing identity>
gc.blocked_on.detail    = <what was attempted + why it did not resolve>
```

The step then closes per the normal lifecycle. The *distinctness* of a
surface-and-ask event lives entirely in `gc.failure_class` +
`gc.blocked_on.*` — no new close path is invented.

**Run-time vs. plan-time boundary (REQ-003).** **P1.14** (dev POLICY.md:142)
is *authoring-time* discipline: every skill probes its external deps at the top
of its body and exits with a graceful, human-readable *"I'm sorry, I can't do
that — &lt;what is missing&gt;"* message. P1.14 (i) reduces the **frequency** of
run-time surprises and (ii) yields a clean local error — but it **stops at a
terminal message**: it does not file an adjudicable ask, does not get the worker
unblocked, and covers only a *skill's declared* deps. The run-time loop is the
**complementary catch-all**: whatever slips past pre-flight (missing config the
formula needed, a tool a P1.14-less skill shelled out to, a skill absent from the
sink) becomes an **adjudicable, unblockable** event. Both are needed — P1.14 is
the graceful-local-error; this loop is the surface-and-resume. **(OQ-5 position:
run-time detection is *independent* of P1.14 — it does not assume the pre-flight
ran; where P1.14 did run, its terminal message is exactly the
`gc.blocked_on.detail` the loop captures.)**

---

## §3 Surface — file the help-request (REQ-004, REQ-005, REQ-006)

> **Owner:** the detecting worker (**primary**); the control-plane sweep
> (**backstop**). **Trigger:** a `gc.failure_class=unresolvable-dependency`
> detection. **Input:** the failure context (blocked step bead id, root/workflow
> id, `gc.blocked_on.*`, what was attempted). **Output:** a help-request brief on
> the normal stack + an awaiting-direction marker on the source bead.
> **Failure-handling:** if the worker cannot file (it died), the backstop files
> the brief from bead metadata — the invariant never rests on the failing worker.

**Primary path.** The detecting worker files the brief **before closing**, using
the existing **`create-brief`** shape:

- **Decision-at-Top = the specific ask** (the [[present-it]] Decision-at-Top
  invariant): *"Worker on `<bead>` needs `<kind>` `'<name>'` to proceed —
  provide it, substitute an alternative, redirect the approach, or abandon the
  step?"*
- **Situation auto-generated** from the failure context (step bead id,
  root/workflow, `gc.blocked_on.*`, attempted resolution). No human writes it.
- **Inapplicable gates N/A'd.** Test-evidence and good-test gates do not apply to
  a capability ask; they are marked N/A rather than blocking.

**Brief type decided (REQ-005 / OQ-1): reuse `create-brief`, classified
`capability_blocker`; a new lighter brief type is REJECTED.** `catch-no-brainer`
already defines a **`capability_blocker`** classification state
(SKILL.md + `fixtures/capability-blocker.md`) that emits
`category:"capability-blocker"` and `compact_eligible:false`, and whose documented
downstream is *"dispatch the capability-resolution path, not the
brief-presentation path."* That IS the light path. A parallel `help-request`
brief type would duplicate the classifier's job and fork the pipeline (xkcd-927).
**This design DEFINES the brief-system POLICY.md N4 "capability-resolution
path."** N4 (POLICY.md:387) mandates that a capability-blocker *"must route
through the capability-resolution path first"* — but that path is **named and
nowhere defined**. §3→§6 of this document **are** that path; adopting this design
closes the N4 gap.

**Backstop (the second guarantee, REQ-004).** A control-plane **sweep**
(patrol/order shape — *design-specified only*) scans for any **closed** bead
carrying `gc.failure_class=unresolvable-dependency` with **no linked help
brief**, and files the brief from the bead's metadata. This is what makes the
invariant hold even if the worker crashed or its lease expired before it could
file. (It also subsumes the "never-recorded" failure mode, §7.)

**Visible pause — delta (c) (REQ-006).** Surfacing must be **loud**. The blocked
source bead carries an explicit **awaiting-direction marker**:

- a label `awaiting-direction`, and/or metadata `gc.awaiting_direction=<brief-id>`
  linking the bead to its open help brief;
- fleet/status surfaces (`city-status`, the dashboard) render this as a **visible
  pause** — *awaiting direction*, not *idle/asleep*;
- the marker is **set** when the brief is filed and **cleared on re-dispatch**
  (§6). A blocked bead with no marker and no brief is exactly the anomaly the
  backstop sweep exists to catch.

There is **no silent-stall path** left: a detected event either files a brief
(primary), or is swept into one (backstop), and in both cases the bead visibly
shows *awaiting direction*.

---

## §4 Adjudication (REQ-007)

> **Owner:** Taylor (or the Mayor within delegated authority). **Trigger:** a
> `capability_blocker` help-request present on the stack. **Input:** the help
> brief (situation + specific ask). **Output:** a recorded verdict via
> `adjudicate-brief` — one of *provide / substitute / redirect / abandon*.
> **Failure-handling:** until a verdict arrives, the §3 awaiting-direction marker
> keeps the bead surfaced; staleness/escalation policy is a Taylor decision (§9,
> D-6).

The brief enters the **normal stack** and is surfaced via **`present-it`** / the
presenter flow. Taylor records the verdict via **`adjudicate-brief`** — under the
one-bead model the brief bead **is** the decision bead, so the direction is
recorded on the brief bead and the bead is closed (no second decision bead).

**`brief-prep` is EXPLICITLY EXCLUDED — delta (b) (REQ-007).** `brief-prep` is
the heavyweight *prepare-a-full-brief-with-bookkeeping* pipeline worker. This
path is a fast capability ask that is **already classified** (`capability_blocker`)
and needs a **direction**, not a prepared full-form artifact with test-evidence
gates. Per the charge, this path routes **only** through `present-it` /
`adjudicate-brief`. Using `brief-prep` here is a design error, not merely
unnecessary.

**Storage-agnostic.** The design references the brief by **id** and its verdict
by the **`adjudicate-brief` primitive**, never by a storage location, so it stays
valid across the in-flight `gsp-jgq2` brief-storage migration (file-stack today ↔
one-bead model). Nothing in §3–§6 assumes where the brief physically lives.

---

## §5 Clean-prompt compile (REQ-008)

> **Owner:** a new **`unblock` routing action** in the `brief-decision-dispatch`
> family (named as the integration point — **NOT** implemented here).
> **Trigger:** a recorded `capability_blocker` verdict carrying a direction
> (i.e. not *abandon*). **Input:** the adjudicated brief (verdict + directions) +
> the blocked bead's original contract + `gc.blocked_on.*`. **Output:** a
> self-contained prompt artifact recorded as `gc.unblock_prompt_path`.
> **Failure-handling:** *abandon* → no prompt, source bead closed terminal,
> marker cleared; a compile that cannot produce a self-contained prompt (e.g.
> the original contract is unrecoverable) **fails closed** and escalates to the
> Mayor rather than dispensing a partial prompt.

`brief-decision-dispatch` already executes routing actions off recorded verdicts,
idempotently, with a dispatch ledger. This design adds one **named** action,
`unblock`, whose compile is **deterministic** — a fixed **four-part template**
written to `<artifact_root>/unblock/<source-bead>.prompt.md`:

1. **Original task contract, verbatim** — what the worker was asked to do.
2. **What was blocked** — `gc.blocked_on.{kind,name,detail}`.
3. **The adjudicated direction, rewritten as executable instructions** — e.g.
   *"the skill is unavailable; use `<substitute>` instead"* / *"the config value
   is `<X>`; it is now set — proceed"* / *"skip the `<tool>` step and hand-write
   the result as follows…"*.
4. **The boundary** — *"do not re-attempt the missing dependency except as
   directed; if it still does not resolve, surface again (subject to the
   loop-guard, §6)."*

**Self-containedness criterion.** A fresh worker with **no session history** can
execute from the prompt alone. **(OQ-6 position:** the §2/§3 structured field
contract — `kind` / `name` / `detail` + the original contract — is precisely what
makes this compile deterministic; nothing needs to be reconstructed from a live
session.**)** The direction "re-enters the convoy" as a file on disk plus one
metadata key, both durable across worker death.

---

## §6 Re-dispatch and resume (REQ-009)

> **Owner:** the dispatcher (`gc sling`) driven by the `unblock` action.
> **Trigger:** a compiled `gc.unblock_prompt_path` on the source bead.
> **Input:** the source bead + the clean prompt. **Output:** a re-slung step
> (fresh worker by default) whose contract includes reading
> `gc.unblock_prompt_path`; the §3 awaiting-direction marker is **cleared** as
> part of re-dispatch. **Failure-handling:** the loop-guard below.

**Re-entry mechanics (OQ-2 position: existing sling path + the named `unblock`
action — no new dispatch affordance).** The blocked work is re-slung through the
**normal `gc sling` path** with the clean prompt attached (the prompt path rides
as a var/metadata; the re-dispatched step's contract is *"read
`gc.unblock_prompt_path` and execute it"*). The worker resumes **at the point it
was blocked**, now with the direction it lacked.

- **Fresh worker is the default.** No session is presumed to survive the pause.
- **Session affinity** is honored **only** when the blocked step carries
  `gc.session_affinity=require` **AND** the original session is still live. There
  is **no lease resurrection** — leases follow the normal claim rules.
- **Marker lifecycle:** re-dispatch **clears** the `awaiting-direction` marker, so
  the visible pause resolves exactly when work resumes.

**Loop-guard (failure-handling).** `gc.surface_ask_count` per source bead, **cap
2** (design default — a Taylor knob, §9 D-5). If a re-slung worker surfaces the
*same* class again past the cap, the loop **hard-fails**
`gc.failure_class=unresolvable-dependency-loop` and **escalates to the Mayor**
(`[ESCALATE HIGH]` mail). This mirrors the bounded-attempt pattern already in the
system (Ralph `gc.attempt` / `gc.max_attempts`), so a mis-adjudicated direction
cannot spin forever.

---

## §7 Generalization and incident mapping (REQ-001, REQ-003, REQ-011)

**One class, three kinds — the uniform `gc.blocked_on.*` instantiation
(REQ-001).** The loop body is identical across kinds; only `kind` differs:

| `kind` | example `name` | `detail` (attempted → why) | preflight probe (§2a) | first-use symptom (§2b) |
| --- | --- | --- | --- | --- |
| `skill` | `create-brief` | told to invoke skill → not in sink | is the skill materialized in the sink? | *"Unknown skill: create-brief"* |
| **`config`** | `gc.var.<X>` (e.g. an output path / DSN) | step needs the value → resolved empty | is the required `gc.var.*` non-empty? | write against an empty value → no target / no-op |
| `tool` | `magma` | step must run the tool → not on `PATH` | `command -v magma` resolves? | *"command not found: magma"* |

**Worked NON-SKILL example — delta (a).** A worker's step needs a config value
`gc.var.<X>` — say the output path a later stage writes to, or a database DSN —
but the **resolved value is empty**. Preflight (§2a) catches it: required
`gc.var` empty → `gc.blocked_on.kind=config`, `name=gc.var.<X>`,
`detail="resolved empty; step cannot proceed"`. It files the **same** brief
(*"needs config `gc.var.<X>` — provide the value, point at the right config, or
redirect?"*), goes through the **same** `present-it`/`adjudicate-brief`, gets the
**same** four-part clean prompt (*"the value is now `<...>`; proceed"*), and is
**re-slung** identically. Only `kind` changed — this is REQ-001 generalization
made concrete: the mechanism is not skill-specific.

**Incident map (REQ-011) — the shared "surface and ask" theme:**

- **`gsp-9biz`** (missing-skill silent stall) → **§2 first-use catch + §3 brief**:
  the archetype the loop was built for. Instead of sleeping, the worker records
  `kind=skill` and files the ask.
- **`gs-vj2d`** (shadowed-override silent divergence) → **§2 preflight,
  `kind=config`**: config resolution surfaces the shadowing override (the value
  that silently won) as a **config blocker** rather than diverging silently.
  *Cousin* — dedicated shadow-detection mechanics beyond the config-kind preflight
  are **deferred** (OQ-3).
- **never-recorded-verdict** → **§4/§5 + §3 backstop**: the ledgered
  verdict-consuming edge (`brief-decision-dispatch` + `unblock`) is where a
  verdict must be recorded to act; a **missing** ledger line is *exactly* the
  "closed unresolvable-dependency bead with no linked brief" the **§3 backstop
  sweep** catches. The never-recorded case cannot hide.
- **`gsp-ioek`** (skill-resolution: inside GC agents must never hit *"Unknown
  skill"*) — **cross-ref, delta (d)**: `gsp-ioek` is the *authoring-time*
  guarantee that the canonical skills **resolve**; this loop is the *run-time*
  backstop for whatever still does not. Complementary, not overlapping.
- **`gsp-6szg` regression suite, R10/R11 — cross-ref, delta (d)**: R10/R11 in the
  executable regression suite (R0–R12) are the guards of this exact theme —
  **R11 asserts the surfacing behavior this design mandates**. The design's
  behavior is what R11 tests; when the loop is implemented, **R11 is its
  acceptance probe**. Design and future test are bound here so neither drifts.

**P1.14 relationship, restated (REQ-003).** The **config-kind preflight** (§2a)
is the *run-time analog* of P1.14's *authoring-time* probe. Both are needed:
P1.14 gives a graceful **local error** when a skill's own dep is missing; the
loop gives an **adjudicable surface** for whatever reaches run time unresolved.

---

## §8 Integration points and deferred work (REQ-010, REQ-012)

**The loop end-to-end (REQ-010), as one traceable flow:**

```
[worker hits missing skill/config/tool]
   → §2 DETECT (gc-core lifecycle): record failure_class + gc.blocked_on.*
   → §3 SURFACE: worker files capability_blocker brief  (backstop sweep if it can't)
                 + set awaiting-direction marker on source bead   ← visible pause
   → §4 ADJUDICATE: present-it → adjudicate-brief  (NOT brief-prep)
   → §5 CLEAN-PROMPT: `unblock` action compiles 4-part prompt → gc.unblock_prompt_path
   → §6 RE-DISPATCH: gc sling with clean prompt; clear marker; loop-guard cap 2
   → [worker resumes at the blocked point]           ← loop closes
```

**Integration seams — each marked *exists today* / *added by this design*:**

| Seam | Status | Added by this design |
| --- | --- | --- |
| Worker failure contract (gc-core lifecycle) | exists | `unresolvable-dependency` failure_class + `gc.blocked_on.*` fields + the §2 preflight/first-use catch |
| Brief-pipeline entry (`create-brief` + `catch-no-brainer` `capability_blocker`) | exists | the auto-generated help-request template + the **definition** of N4's capability-resolution path |
| Visible-pause marker (label/metadata + status surfaces) | partial (labels, metadata, `city-status`) | the `awaiting-direction` marker convention + its rendering/clearing |
| Adjudication surface (`present-it` / `adjudicate-brief`) | exists | *nothing* — reused as-is; **`brief-prep` excluded** |
| Verdict-dispatch edge (`brief-decision-dispatch` family) | exists | the `unblock` routing action + the four-part clean-prompt compiler |
| Re-dispatch (`gc sling` + affinity/leases) | exists | the `gc.unblock_prompt_path` var contract + the `gc.surface_ask_count` loop-guard |
| Control-plane backstop sweep (patrol/order) | pattern exists | the sweep that files briefs for orphaned `unresolvable-dependency` beads |
| Escalation (Mayor mail `[ESCALATE HIGH]`) | exists | the loop-guard escalation trigger |

**Deferred implementation follow-ups (explicitly NOT built here, REQ-012).**
Each becomes its own future build: the detection-hook code; the patrol/order TOML
for the backstop sweep; the `brief-decision-dispatch` `unblock` action + the
prompt-compiler; the worker-lifecycle field additions; and the cousins'
**dedicated** detection (`gs-vj2d` shadow-override, verdict-ledger) beyond the
config-kind preflight. This document names the seams; it changes none of them.

**Deliverable form (OQ-4 position).** This dated design doc under
`mathcity/subdomains/dev/docs/` is the deliverable form; the factory's terminal
decision brief carries it to adjudication — itself a live demonstration of the
very pipeline this design reuses.

---

## §9 Open decisions for Taylor (AC-10, REQ-012)

Every design question is resolved as a **stated position** with its alternative,
so adjudication is *confirm or override* — nothing is left dangling.

| # | Decision | Design position (recommended) | Alternative to weigh |
| --- | --- | --- | --- |
| **D-1** (OQ-1, REQ-005) | Brief type | **Reuse `create-brief`, classify `capability_blocker`**; define N4's capability-resolution path as §3–§6 | Introduce a lighter `help-request` brief type — **rejected** (duplicates the classifier; forks the pipeline) |
| **D-2** (OQ-2, REQ-009) | Re-entry affordance | **Existing `gc sling` path + named `unblock` action**; clean prompt rides as var/metadata | A new dispatch affordance / bespoke re-enter-at-step metadata |
| **D-3** (OQ-3, REQ-011) | Cousins in scope | **Reference `gs-vj2d` / never-recorded as motivating cases**; only config-kind preflight covers `gs-vj2d`; deeper mechanics deferred | Specify dedicated shadow-override + verdict-ledger detection now |
| **D-4** (OQ-5, REQ-003) | P1.14 assumption | **Run-time loop independent of P1.14** (does not assume pre-flight ran); complementary | Assume P1.14 caught known deps; loop handles only residual surprises |
| **D-5** (§6) | Loop-guard cap | **`gc.surface_ask_count` cap = 2**, then hard-fail + Mayor escalation | A different cap, or unbounded-with-alerting |
| **D-6** (§4) | Stale-verdict policy | **Marker keeps it surfaced via normal stack aging** (no new mechanism) | A dedicated staleness timeout that escalates un-adjudicated help-requests |
| **D-7** (OQ-4, REQ-012) | Deliverable form / adjudicator | **This dated docs doc + terminal decision brief; Taylor adjudicates** | A decision brief as the primary artifact instead of a docs file |

---

## §10 Requirement coverage

| ID | Status | Where satisfied |
| --- | --- | --- |
| REQ-001 | covered | §1 scope; §7 uniform table + worked non-skill (config) example |
| REQ-002 | covered | §2 detection layer = gc-core lifecycle, with rejected alternatives |
| REQ-003 | covered | §2 + §7 run-time vs plan-time P1.14 boundary (both needed) |
| REQ-004 | covered | §1 invariant; §3 primary + backstop (no silent-stall path) |
| REQ-005 | covered | §3 reuse `create-brief`/`capability_blocker`; lighter type rejected |
| REQ-006 | covered | §3 visible awaiting-direction marker + status rendering (delta c) |
| REQ-007 | covered | §4 present-it / adjudicate-brief; `brief-prep` excluded (delta b) |
| REQ-008 | covered | §5 four-part self-contained clean-prompt compile |
| REQ-009 | covered | §6 re-sling with augmented prompt + resume + loop-guard |
| REQ-010 | covered | §8 end-to-end flow; §2–§6 owner/trigger/input/output/failure each |
| REQ-011 | covered | §7 gsp-9biz, gs-vj2d, never-recorded, gsp-ioek, gsp-6szg R10/R11 |
| REQ-012 | covered | design-only throughout; §9 open decisions; §11 accounting |

**Acceptance-criteria self-check (AC-1…AC-10):** AC-1 → §7 (skill/config/tool +
worked non-skill); AC-2 → §2 (one layer + rejected alternatives); AC-3 → §2/§7
(P1.14 relationship); AC-4 → §1/§3 (help-request + backstop + visible pause, no
silent stall); AC-5 → §3 (brief type + rationale); AC-6 → §4 (present-it /
adjudicate-brief; brief-prep excluded); AC-7 → §5/§6 (clean-prompt + re-sling
mechanics); AC-8 → §8 + §2–§6 (single traceable loop, per-stage
owner/trigger/input/output/failure); AC-9 → §7 (related failures situated);
AC-10 → §9 + this document (design-only; every choice resolved or surfaced).

---

## §11 Convergence accounting

Per the binding convergence protocol (satisfied→verify / partial→gap-fill /
absent→build / never-clobber→namespace), run **before** authoring:

- **Built vs. verified vs. gap-filled: BUILT (fresh).** The target path
  `mathcity/subdomains/dev/docs/SURFACE-AND-ASK-DESIGN-2026-08-04.md` was searched
  across **every git ref** (`git log --all` + per-ref `git ls-tree` over
  `refs/heads` and `refs/dolt`) **and** the working disk
  (`find … -name 'SURFACE-AND-ASK-DESIGN*'`) and found **absent everywhere**. The
  sibling `gsp-460s7p` closed `shipped`, but no reachable artifact exists on any
  branch or on disk → this is the **Absent → build** branch. Nothing to verify or
  gap-fill against; this document is authored to the full §1–§8 specification of
  the 12-REQ frame.
- **Superset satisfaction.** Because this is a fresh build to the 12-REQ frame, all
  four deltas the frame adds over the sibling 8-REQ frame are present by
  construction: (a) worked non-skill example (§7), (b) explicit `brief-prep`
  exclusion (§4), (c) visible-pause specification (§3), (d) `gsp-ioek` + `gsp-6szg`
  R10/R11 cross-reference (§7).
- **No gate-artifact clobber.** This deliverable is a **source** design doc, not a
  `.gc-builds` gate artifact; it occupies no sibling gate path, so
  rule-4 root-namespacing does not apply to it. (The plan and plan-review reports
  already namespaced under `gsp-0sutol/` per that rule.)
- **Diff scope.** Only this file is added — see the header's diff-scope proof.
