> ## ARCHIVED — UNADJUDICATED DESIGN, NOT ADOPTED POLICY
>
> **This document was never adjudicated and nothing in it is in force.** It
> describes a proposal, not a decision. Do not cite it as policy, precedent,
> or an approved plan.
>
> - **Source commit:** `b4151a3acbac86711cb731a7bb8c2146fcdd5fcf` (legacy `~/gt/gascity-packs` detached-HEAD worktree
>   population — the `#121` 56-commit salvage set), 2026-08-04, 415 lines.
> - **Archived:** 2026-08-14 under decisions-track brief **#148**, Option (A).
>   Taylor's verdict: *"unadjudicated-design-docs-disposition, do they have any
>   value at all? If not then file them away."*
> - **Value assessment (brief #148):** **GENUINELY VALUABLE (not a duplicate of `3e2f9cd3`)** — sibling framing of the same design. NOT contained in `3e2f9cd3`: it alone states the invariant as a machine-checkable query predicate, adds the primary/backstop de-duplication guard, resolves an ambiguous verdict by send-back rather than escalation, and extends the backstop to adjudicated-without-recorded-direction. It lacks the visible-pause marker that `3e2f9cd3` has. Neither contains the other.
> - Nothing was deleted from the legacy tree; retirement is separately gated
>   under `gt-0g9die`. Full comparative assessment:
>   [`ARCHIVED-DESIGNS-INDEX-2026-08-14.md`](./ARCHIVED-DESIGNS-INDEX-2026-08-14.md).

---

# Surface-and-Ask: anti-silent-failure loop for unresolvable dependencies

**Bead:** gsp-460s7p (design item) — source task `gsp-u9s2`, workflow `gsp-ov0nle`
**Date:** 2026-08-04
**Status:** DRAFT (design/proposal — **not** an implementation)
**Author:** gascity-packs implementation worker (design-only build)
**Rollback:** remove this file (`git rm mathcity/subdomains/dev/docs/SURFACE-AND-ASK-DESIGN-2026-08-04.md`) — the doc is the only artifact; nothing else references it yet.

---

## Scope note (design-only)

This is a **design/proposal**. It specifies a loop; it does **not** add code,
hooks, order/patrol TOML, `brief-decision-dispatch` edits, a prompt compiler, or
any formula/skill change. Every component below is marked **exists today** or
**added by this design** (§8). Implementation is explicitly deferred (§9).

**Diff-scope proof (plan-review Note 1).** This build's only diff is this file:

```
git diff --name-only <base>..HEAD
# expected — exactly one line:
mathcity/subdomains/dev/docs/SURFACE-AND-ASK-DESIGN-2026-08-04.md
```

---

## §1 — Invariant & scope

**The anti-silent-failure invariant (AC-8), stated as a checkable guarantee:**

> **INV.** No inside (gascity-managed) worker that hits an **unresolvable
> dependency** may terminate in a *silent* state. Every such event MUST leave a
> machine-checkable trace on the step bead (`gc.outcome=fail`,
> `gc.failure_class=unresolvable-dependency`, `gc.blocked_on.*`) **and** result
> in exactly one linked **brief** on the stack. A closed-with-fail bead that
> carries `failure_class=unresolvable-dependency` and has **no** linked brief is
> itself a detectable violation the control plane repairs (the backstop, §3).

The invariant is *mechanical*: it is expressed entirely in bead metadata and a
brief link, so it can be audited by a query rather than by reading prose. §3
argues it holds on both the primary path (the worker files the brief) and the
backstop path (a control-plane sweep files it), which together are exhaustive
over "the worker filed it / the worker died first."

**Scope.** A **missing or unresolvable dependency** hit by an inside worker at
run time, in three kinds:

| `gc.blocked_on.kind` | Meaning | Example |
| --- | --- | --- |
| `skill` | a named skill the task requires does not resolve / is shadowed | task says "use skill `foo`"; `foo` not in the sink |
| `config` | a required config value / import / rig setting is absent | formula references an unimported pack; a rig var is unset |
| `tool` | a required CLI / MCP tool / credential is unavailable in-session | `gh auth` missing; an MCP server unreachable |

**Out of scope** (restated from requirements, load-bearing here): implementing
the loop; changing *who* adjudicates or *how* verdicts form; auto-resolving a
dependency without a decision; redesigning the brief pipeline; fixing the
historical incidents beyond covering their shape (§7). This design covers
**detection → surface → adjudicate → clean-prompt → re-dispatch**, generalized
across the three kinds. *(frames REQ-002, REQ-008)*

**Loop stages and their owners** (AC-7 — every stage names owner / trigger /
input / output / failure-handling; detailed per stage in §2–§6):

| Stage | Owner | §  |
| --- | --- | --- |
| Detect | the inside worker (claim/first-use) | §2 |
| Surface + file brief | the inside worker; backstop: control-plane sweep | §3 |
| Adjudicate | Taylor / Mayor (existing pipeline) | §4 |
| Clean-prompt compile | `unblock` action in the `brief-decision-dispatch` family | §5 |
| Re-dispatch + resume | dispatch layer (`gc sling`) + a fresh worker | §6 |

---

## §2 — Detection *(REQ-001, AC-1)*

**Goal:** turn "unresolvable dependency" from an *undifferentiated stall* into a
**distinct, catchable condition** with a uniform record.

**Two detection points, uniform across skill/config/tool (resolves OQ1):**

1. **Preflight at claim/prepare time.** Right after a worker claims a step and
   resolves its prompt, it checks that every *declared* dependency resolves:
   named skills materialize in the sink, referenced packs/configs are imported,
   named tools/creds answer a cheap probe. A declared dependency that does not
   resolve is caught **before** any work begins.
2. **First-use catch.** Not every dependency is declared; some surface only when
   invoked. The first attempt to use a skill/config/tool that fails to resolve is
   caught at the call site and mapped to the same condition.

Both points converge on **one** condition and **one** record, so downstream
stages never branch on *where* it was caught.

**Owner:** the inside worker.
**Trigger:** a declared dependency fails preflight, **or** first use of an
undeclared dependency fails to resolve.
**Input:** the claimed step bead + its resolved prompt (the declared/required
dependencies).
**Output — the uniform failure record on the *step* bead:**

```
gc.outcome            = fail
gc.failure_class      = unresolvable-dependency
gc.blocked_on.kind    = skill | config | tool
gc.blocked_on.name    = <the specific dependency, e.g. "foo" / "imports.mathcity-superpowers" / "gh-auth">
gc.blocked_on.detail  = <one-line: what was attempted and how it failed>
```

Then the worker **closes the step per the normal lifecycle** (it never idles or
lets the lease silently expire) — this reuses the exact worker close contract
already in force (`gc.outcome=fail` + `gc.failure_class` + reason). **Detection
does not itself unblock the work**; it makes the block *loud and typed*.

**Failure-handling (of detection itself):** if the worker cannot even write the
record (e.g., it dies mid-close), the step's lease expires with no `gc.outcome`.
That case is caught by the **backstop** in §3 (lease-expiry / closed-without-brief
sweep), so detection failure degrades to the backstop rather than to silence.

---

## §3 — Surface / file the brief *(REQ-002, REQ-003, AC-2)*

**Goal:** the typed failure becomes a **loud, adjudicable brief** carrying the
*situation* and the *specific ask* — reusing the existing brief pipeline, never a
parallel channel.

### Primary path — the worker files the brief

The worker (or the immediate closing step) files a brief via the existing
**`create-brief`** shape:

- **Decision-at-Top** (B1.1 invariant): the first content is the **specific ask**
  — e.g. *"skill `foo` is missing; decide: (a) use alternative skill `bar`,
  (b) approve installing `foo`, or (c) re-scope the task without it."*
- **Situation** is **auto-generated from the failure context** (resolves OQ2):
  the `gc.blocked_on.{kind,name,detail}` fields, the source/step bead ids, and
  the original task contract populate the situation section, so the worker only
  has to author the *ask*. The brief **links the blocked source/step bead**.

### Unification with the existing capability-blocker shape (resolves OQ6 — "unify, don't duplicate")

This is **not** a new brief type. An unresolvable-dependency brief **is** a
[`catch-no-brainer`](../../../skills/catch-no-brainer/SKILL.md) **`capability-blocker`**
shape: "a disposition that would otherwise be mechanical, blocked by a
capability/permission gap the worker could not resolve in-session." The design
only **generalizes** that shape's trigger from the current examples (`gh auth`
missing, credentials, unreachable service) to the full skill/config/tool set,
detected via the same `capability_blocker:` frontmatter field (populated from
`gc.blocked_on.detail`).

`catch-no-brainer` already emits, for this shape,
`{category:"capability-blocker", reason:"resolve <blocker>, then re-classify",
compact_eligible:false, requires_taylor_adjudication:false}` and **stops** —
leaving "route the blocker for resolution" to the Mayor/dispatcher. Today that
**resolution path is named but undefined**: `brief-system/POLICY.md` rule **N4**
("Capability-blocker shape routes to resolution, not compact") says *where not to
send it* but not *where to send it*.

> **This design defines the N4 capability-resolution path** as exactly the
> surface-and-ask loop §4→§6: adjudicate → compile a clean prompt → re-dispatch.
> N4 is the *router*; §4–§6 are the *destination*. No second classifier, no
> second brief lane.

### Backstop — the invariant's guarantee (AC-8)

The primary path can fail (the worker dies before filing). A **control-plane
sweep** (NAMED here, implemented later — §8/§9) periodically queries for beads
that are **closed with `failure_class=unresolvable-dependency` and no linked
brief** (also catching lease-expired steps with the typed record but no close),
and files the brief on the worker's behalf from the same `gc.blocked_on.*`
context. Primary ∪ backstop is exhaustive over "worker filed / worker didn't,"
which is what makes INV (§1) hold mechanically rather than by good behavior.

**Owner:** the inside worker (primary); the control-plane sweep (backstop).
**Trigger:** a step closed/closing with `failure_class=unresolvable-dependency`
(primary at close time; backstop for any such bead lacking a linked brief).
**Input:** the `gc.blocked_on.*` record + the original task contract + bead links.
**Output:** one stack-eligible brief (capability-blocker shape) linked to the
blocked bead, carrying situation (auto) + specific ask (authored).
**Failure-handling:** if the worker does not file → the backstop files it; a
*duplicate* (worker + backstop both file) is de-duplicated by the "no **linked**
brief" guard (the sweep only fires when no brief links the bead).

---

## §4 — Adjudication *(REQ-004, AC-3)*

**Goal:** the brief is decided by the **existing** adjudication pipeline — no new
policy, no new decider.

The capability-blocker brief flows through the normal stack: `present-it` /
`present-briefs` surfaces it (full-form — N4/`capability-blocker` is never
compact), and **Taylor/Mayor** adjudicate via `adjudicate-brief`, producing a
**verdict + directions** (e.g. "use `bar` instead"; "approved — install `foo`
via …"; "re-scope: drop the `foo` step").

**Storage-agnosticism (acceptance requirement).** The verdict + directions are
recorded on the **brief record**, and the design references it abstractly as
"the adjudicated direction attached to the brief," valid under **both** brief
storage models:

- **file-stack model** (today): the decision lands in the brief's
  `decisions/<slug>/decision.toml` under the brief root.
- **one-bead model** (`gsp-jgq2` migration, in flight; B2.9/N7): the brief bead
  **is** the decision bead — the verdict + directions are recorded *on the brief
  bead itself*; no separate decision bead is created.

§5's compiler reads "the adjudicated direction for brief X" through whichever
model is active; nothing downstream hard-codes a path or a bead shape.

**Owner:** Taylor / Mayor (unchanged).
**Trigger:** the capability-blocker brief reaches the stack.
**Input:** the brief (situation + ask + blocked-bead links).
**Output:** a verdict + directions recorded on the brief record (model-agnostic).
**Failure-handling:** if adjudication stalls, the brief sits on the stack as a
*visible* pending item (already loud — INV satisfied); the loop-guard (§6) bounds
the *re-dispatch* side, not the human decision.

---

## §5 — Clean-prompt compile *(REQ-005, AC-3)*

**Goal:** turn raw verdict notes into a **self-contained clean prompt** a fresh
worker can execute with zero prior context.

**Owner (resolves OQ3):** a new **`unblock` routing action in the
`brief-decision-dispatch` family** (NAMED, not implemented). It is deterministic
compile — no judgment — mirroring the existing post-decision routing actions
(`file-or-sendback-route`), so it belongs in that family rather than as a new
skill.

**Output location & handle:** a self-contained prompt written to
`<artifact_root>/unblock/<source-bead>.prompt.md`, whose absolute path is
recorded on the source/step bead as **`gc.unblock_prompt_path`**. (Precedent for
"a compiled artifact path recorded on the bead": `gc.attempt_log`.)

**The 4-part clean-prompt template** (guarantees self-containment):

1. **Original contract** — the blocked task's own description/result contract,
   copied verbatim so the re-dispatched worker needs nothing else.
2. **What was blocked** — the `gc.blocked_on.{kind,name,detail}` record (why the
   first attempt could not proceed).
3. **Adjudicated direction, as instructions** — the verdict's directions
   rewritten as imperative steps ("use `bar`; do not attempt `foo`"), not raw
   decision notes.
4. **Boundary** — what remains out of scope / what NOT to do (e.g. "do not
   install anything; do not re-file a brief for this dependency").

**Trigger:** a capability-blocker brief transitions to adjudicated with directions.
**Input:** the adjudicated direction (via §4, model-agnostic) + the original
contract + the `gc.blocked_on.*` record.
**Output:** `<artifact_root>/unblock/<source-bead>.prompt.md` +
`gc.unblock_prompt_path` on the bead.
**Failure-handling:** if compile cannot produce a *self-contained* prompt
(e.g. the direction is ambiguous), it does **not** emit a prompt; it routes the
brief back to adjudication (sendback), incrementing nothing — an ambiguous
verdict is a human re-decide, not a loop iteration.

---

## §6 — Re-dispatch & resume *(REQ-006, AC-4)*

**Goal:** dispense the clean prompt to a **(re)dispatched** worker so the exact
blocked work resumes — unblocked via a clean dispatch, never an ad-hoc mutation
of a dead session.

**Mechanism:** the dispatch layer re-slings the blocked source bead through the
**normal** path (`gc sling` / the standard routing), **with the clean prompt
attached** (the worker reads `gc.unblock_prompt_path`, exactly as the current
"External Prompt Required" beads read a `description_file`). A **fresh** worker
claims it under normal lease/claim rules.

**Identity/affinity (resolves OQ4):** the work goes to a **fresh** worker by
default. Session **affinity is honored only when** `gc.session_affinity=require`
**AND** the prior session is still live; otherwise a fresh session is correct
(the original session is typically gone). Leases follow the normal claim rules —
no lease is "reattached" to a dead session.

**Loop-guard (resolves OQ5) — this is what keeps surface-and-ask from becoming
surface-and-ask-forever:**

- A counter **`gc.surface_ask_count`** on the source bead increments each time
  the bead re-enters the loop (each new capability-blocker brief for the *same*
  bead).
- **Cap = 2** (default). On exceeding the cap, the loop **hard-fails**:
  `gc.failure_class = unresolvable-dependency-loop`, and it escalates to the
  Mayor with **`[ESCALATE HIGH]`** (per the mail/escalation doctrine). It does
  **not** silently retry — the escalation is itself a loud surface, so INV still
  holds at the terminal boundary.

**Owner:** the dispatch layer (`gc sling`) + a fresh worker.
**Trigger:** `gc.unblock_prompt_path` is set on the bead (a clean prompt exists).
**Input:** the source bead + the clean prompt.
**Output:** a running re-dispatched worker executing the unblocked contract;
`gc.surface_ask_count` incremented.
**Failure-handling:** if the dependency is *still* unresolvable after re-dispatch,
the worker re-enters §2 — bounded by the cap, which converts an infinite loop
into a single loud `[ESCALATE HIGH]`.

---

## §7 — Generalization & incident mapping *(REQ-007, AC-5)*

The loop is **one** mechanism over the uniform `gc.blocked_on.kind ∈
{skill, config, tool}` record (§2). The three named silent-failure incidents map
onto the **detection** stage as follows:

| Incident | Kind | Where it is caught by this design |
| --- | --- | --- |
| `gsp-9biz` missing-skill stall | `skill` | §2 preflight (declared skill fails to materialize) or first-use catch → typed record → brief |
| `gs-vj2d` shadowed-override loss | `config` | §2 preflight: the *effective* dependency differs from the intended one (a shadow/override resolves to the wrong layer) → typed as `config`, `detail` names the shadowing layer → brief |
| never-recorded-verdict | (backstop) | not a worker-detect case: a verdict that was decided but never recorded. Caught by the **§3 backstop** class of "closed/decided without the required durable link" — the same sweep that files a brief for a fail-closed bead with no linked brief also flags an adjudicated brief with no recorded direction. INV's "no silent end" extends to it. |

**Boundary vs. plan-time P1.14 pre-flight.** This design is **run-time**: it
catches a dependency that is unresolvable *when a worker actually hits it*. It is
the complement of any *plan-time* pre-flight (checking a plan's dependencies
before dispatch): plan-time pre-flight reduces how often §2 fires; this loop
guarantees that when it *does* fire at run time, it surfaces. They are additive,
not alternatives — neither makes the other redundant.

---

## §8 — Integration points *(REQ-008, AC-6)*

Concrete seams, each marked **exists today** or **added by this design**:

| Seam | Status | Note |
| --- | --- | --- |
| Worker-lifecycle failure contract (`gc.outcome=fail` + `gc.failure_class` + reason at close) | **exists today** | §2 reuses it; adds the `gc.blocked_on.*` sub-keys |
| `gc.blocked_on.{kind,name,detail}` typed record | **added by this design** | the uniform detection output |
| Brief-pipeline entry (`create-brief` / `brief-prep`) | **exists today** | §3 primary path files here |
| `catch-no-brainer` `capability-blocker` shape + POLICY **N4** | **exists today** | §3 unifies with it; this design *defines N4's resolution destination*, generalizes the trigger to skill/config/tool |
| Adjudication (`present-it` / `adjudicate-brief`) | **exists today** | §4, unchanged |
| Brief-record storage (file-stack **and** `gsp-jgq2` one-bead model) | **exists / in flight** | §4 reads directions model-agnostically |
| `unblock` action in the `brief-decision-dispatch` family + `gc.unblock_prompt_path` | **added by this design** | §5 clean-prompt compile |
| `<artifact_root>/unblock/<source-bead>.prompt.md` output | **added by this design** | §5 artifact |
| `gc sling` re-dispatch carrying the clean prompt | **exists today** (prompt-attach pattern) | §6 reuses the "External Prompt Required" bead pattern |
| Loop-guard `gc.surface_ask_count` + cap + Mayor `[ESCALATE HIGH]` | **added by this design** | §6 |
| Control-plane backstop sweep (fail-closed-without-brief) | **added by this design** | §3 backstop — the INV guarantee |

---

## §9 — Deferred implementation follow-ups (explicit)

Design-only; these are the concrete build items a downstream plan would create
(named here, **not** implemented):

1. The `gc.blocked_on.*` detection hook (preflight + first-use) in the worker
   lifecycle.
2. Generalizing `catch-no-brainer`'s `capability_blocker` trigger to
   skill/config/tool and wiring POLICY **N4** to route to the §4–§6 path.
3. The `unblock` action in the `brief-decision-dispatch` family (the clean-prompt
   compiler + the 4-part template + `gc.unblock_prompt_path`).
4. The re-dispatch prompt-attach + `gc.surface_ask_count` loop-guard + the
   `unresolvable-dependency-loop` escalation.
5. The control-plane backstop sweep (fail-closed-without-brief; adjudicated-
   without-recorded-direction).

---

## Acceptance walkthrough (AC-1 … AC-8)

| AC | Requirement | Satisfied by |
| --- | --- | --- |
| AC-1 | REQ-001 detection as a distinct, catchable condition | §2 (two detection points; uniform `gc.blocked_on.*` record) |
| AC-2 | REQ-002/003 surface via brief (existing pipeline) with situation + ask | §3 (primary path; auto situation + authored ask; `create-brief`) |
| AC-3 | REQ-004/005 normal adjudication + clean-prompt compile | §4 + §5 (unchanged adjudication; `unblock` action + 4-part template) |
| AC-4 | REQ-006 dispense clean prompt to re-dispatched worker | §6 (re-sling with `gc.unblock_prompt_path`; fresh worker; resume) |
| AC-5 | REQ-007 generalize + map the 3 incidents | §7 (one mechanism; `gsp-9biz` / `gs-vj2d` / never-recorded-verdict mapped) |
| AC-6 | REQ-008 design-only + concrete integration points | §8 (exists-today / added-by-design table) + §9 deferrals |
| AC-7 | reviewability — each stage has owner/input/output | §2–§6 each close with owner / trigger / input / output / failure-handling |
| AC-8 | anti-silent-failure invariant | §1 INV, argued mechanically via primary ∪ backstop (§3) |

**Storage-agnosticism verified against BOTH models:** §4 records directions on
"the brief record," realized as `decisions/<slug>/decision.toml` (file-stack) or
on the brief bead itself (one-bead `gsp-jgq2` model); §5's compiler reads the
adjudicated direction through whichever is active. No stage hard-codes a brief
storage path or bead shape.

**Diff-scope check (Note 1):** `git diff --name-only <base>..HEAD` lists exactly
`mathcity/subdomains/dev/docs/SURFACE-AND-ASK-DESIGN-2026-08-04.md`.

---

## Open-question resolutions (design decisions recorded, per autonomous mode)

- **OQ1 detection point** → both claim/prepare-time preflight **and** first-use
  catch; uniform across skill/config/tool (§2).
- **OQ2 brief authorship** → situation auto-generated from `gc.blocked_on.*`; the
  worker authors only the specific ask; filed via `create-brief` (§3).
- **OQ3 clean-prompt compiler** → the `unblock` action in the
  `brief-decision-dispatch` family; 4-part self-contained template;
  `gc.unblock_prompt_path` (§5).
- **OQ4 re-dispatch identity/affinity** → fresh worker by default; affinity only
  when `gc.session_affinity=require` **and** session live; normal leases (§6).
- **OQ5 loop-guard** → `gc.surface_ask_count`, cap 2, then hard-fail
  `unresolvable-dependency-loop` + Mayor `[ESCALATE HIGH]` (§6).
- **OQ6 relationship to existing gates** → **unify**: the brief is a
  `capability-blocker` shape; POLICY **N4** routes it to this design's §4–§6 path.
  No duplicate classifier or channel (§3, §7).

---

## Requirement Coverage

| ID | Status |
| --- | --- |
| REQ-001 | covered |
| REQ-002 | covered |
| REQ-003 | covered |
| REQ-004 | covered |
| REQ-005 | covered |
| REQ-006 | covered |
| REQ-007 | covered |
| REQ-008 | covered |
