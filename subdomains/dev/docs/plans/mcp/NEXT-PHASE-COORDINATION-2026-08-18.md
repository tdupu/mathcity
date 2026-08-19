# mctl / MCP Next Phase — Coordination Plan

Parent: [Dev README](../../README.md) ·
Related: [MCTL implementation plan](./MCTL-MCP-IMPLEMENTATION-PLAN.md) ·
[Open design questions](../OPEN-DESIGN-QUESTIONS.md)

**Date:** 2026-08-18 · **Author:** repo-side-mctl-agent (36db5d4e)
**Status:** proposal — nothing here is started

**Goal:** decide what happens before the city restarts, what gets filed as
issues, how the remaining mctl/MCP work divides across agents, and whether the
proposed slice order is actually vertical.

---

## 1. Where things stand

Slices 1–4 are on `main` and hardened. All nine findings from the 2026-08-18
review are closed, plus two defects found while presenting and one found by
coordinating with the agent doing city stop/start testing.

- `main` = `14b48e3`, 30 commits merged today, **32/32 shell + 20 pytest files
  green**, verified on `main` with the city both up and down.
- mctl test count went 42 → 128.
- Not started: Slice 5 (briefs create/validate), Slice 6 (MCP server), Slice 7
  (skill refactor), Slice 8 (dashboard).
- Zero skills call mctl. There is no `bin/mctl`. The problem statement on
  issue #41 — "brief and work operations depend on loose prompt-skill command
  chains" — is therefore **not yet addressed at all**; only the core beneath it
  is correct.

### The blocker nobody has scheduled

`gc dolt health` does not resolve on this machine. It is not a stale PATH and
not a wrong binary in the fragment: the command ships as a **shell command pack**
at `gascity/examples/bd/dolt/commands/health/run.sh`, and that pack is not
installed in this city. The compiled `gc` has only hyphenated `dolt-*` commands
(`dolt-cleanup`, `dolt-state`, `dolt-config`, `dolt-gc`), no `dolt` parent.

Consequence: the P1.14 pre-flight block that ~18 skills copy verbatim aborts
with *"Dolt is unreachable"* whenever it runs, regardless of city state.

**This gates the first step of the proposed plan.** See §3.

---

## 2. Answering the MCP question

Taylor's proposal: the "check" skills, the "work" skills, the "new policy"
skills, anything shaped like *"run one of these bash blocks"*, plus
`prime-clerk` / `prime-mayor-math` and `communicate-with-other-agent`, should
become MCP tools rather than prose instructions.

**This is the right direction, and it is a bigger idea than the MCTL plan
currently contains.** The MCTL plan scopes MCP to brief/work operations
(Slice 6). Taylor's proposal is a general refactor of the skill surface. Those
are different sizes of project and should not be conflated.

### What MCP actually buys

A skill is prompt text: an agent reads it and decides what to do. An MCP tool
is a typed function: the agent calls it and receives structured data or a
structured error it cannot skim past. The three concrete wins:

1. **Errors stop being prose.** A shell block that prints "Dolt is unreachable"
   is advisory — an agent can misread it, or proceed anyway. A tool that returns
   an error is not optional.
2. **The dispatch table becomes machine-readable.** The "skill | reach for
   when" tables are a hand-maintained index that an agent reads and matches
   against fuzzily. Tool descriptions are that same index, consumed natively.
3. **One implementation per operation.** The same DRY argument that settled the
   stack-index writer question (Q2).

### What MCP does NOT buy, and this matters

**It would not have fixed P1.14.** Wrapping a broken probe in a typed tool
returns a loud, well-structured, *wrong* answer. The probe is the bug. Any
"convert to MCP" work that does not also fix the underlying probes just
relocates them.

This is the trap to avoid: MCP makes failures *legible*, not *correct*.

### "Would the Mayor become an MCP rather than a skill?"

Partly, and the split is the interesting part. Decompose any skill into:

- **Mechanism** — the commands, state transitions, file writes, queries.
  Belongs in tools. Deterministic, testable, typed.
- **Judgment** — what to dispatch, how to weigh a tradeoff, when to escalate,
  what to say to a human.
  Belongs in prompt text. Not expressible as a tool call.

`check-briefs` is almost pure mechanism → becomes a tool.
The Mayor is mostly judgment with a mechanism tail → stays a skill that *calls*
tools. So: the Mayor's bash blocks become MCP; the Mayor does not.

### The philosophical question: when are skills better than an MCP?

Taylor asked when a collection of skills beats an MCP that organizes them. A
real answer, not a hedge — skills win when:

- **The work is judgment-dense.** Tools have fixed signatures; judgment needs
  open-ended reasoning over context that will not fit in parameters.
- **The procedure changes faster than a schema can follow.** Editing prose is
  cheap; changing a tool contract breaks callers. Early-stage or frequently
  revised workflows are better as text until they stabilize.
- **The agent must be able to deviate.** A skill can say "usually X, but if Y,
  reconsider." A tool either runs or does not.
- **Discovery matters more than execution.** An agent browsing skill
  descriptions to figure out *what is even possible* is doing something tools
  support worse than a curated index does.

And MCP wins when the operation is mechanical, repeated, safety-critical, or
needs to fail in a way the agent cannot ignore.

The honest rule: **stabilize as a skill, then harden into a tool.** Converting
too early freezes a contract you have not learned yet. That is exactly what the
MCTL plan says about Slice 6 waiting for CLI-proven behavior — and it
generalizes to Taylor's larger proposal.

---

## 3. Verticality check on the proposed order

Taylor asked whether each slice can be tested end-to-end. Proposed order was:

> `bin/mctl` shim + route `check-briefs` through it → Slice 5 → Slice 6 →
> Slice 7 → live-rig e2e + sling canary → Slice 8

Assessment per step:

| Step | Vertical? | Notes |
|---|---|---|
| `bin/mctl` + `check-briefs` | ❌ **BLOCKED** | `check-briefs` embeds the P1.14 block twice (`skills/check-briefs/SKILL.md:20,22`). It aborts before reaching mctl. Cannot be demonstrated end-to-end until the dolt pack is installed. |
| Slice 5 create/validate | ✅ | Real CLI surface, real bead writes, testable against an embedded-Dolt store exactly like `test_real_bead_store.py`. |
| Slice 6 MCP server | ⚠️ **partial** | A server with no client is not end-to-end. Needs a client harness in the same slice, or it is horizontal scaffolding — the thing the plan explicitly forbids. |
| Slice 7 skill refactor | ✅ | Per skill, demonstrable: invoke skill, observe typed call, observe result. |
| live-rig e2e + canary | ✅ | Highest-value missing coverage. Needs a live registered rig and a real sling. |
| Slice 8 dashboard | ✅ | Visible surface, browser-testable. |

**Two corrections to the order:**

1. **Install the dolt command pack first.** It is not in the plan at all, it
   unblocks ~18 skills, and it is a precondition for step 1 being testable.
2. **Slice 6 must include a client harness** in the same slice, or it is not
   vertical. Suggest: a minimal MCP client script that lists tools and calls
   `briefs_list`, asserting a typed round trip.

Everything else in the order is sound, and putting `bin/mctl` + one real caller
first is right — it is the cheapest thing that proves the surface is usable
before Slice 6 freezes schemas on top of it.

---

## 4. Before the city restarts

Restarting is safe and nothing below blocks it. These are ordered by what makes
the restart *informative* rather than confusing.

- [ ] **Install the `examples/bd/dolt` command pack** (or decide the fragment
      should tolerate its absence — see Issue A). Without this, every `check-*`
      and `work` skill will claim "Dolt is unreachable" the moment the city is
      up, and that message will be wrong. Expect this to be the single largest
      source of confusion post-restart.
- [ ] **Do not run `bd dolt stop`** against any rig whose `.beads/dolt-server.port`
      points at 58506. Source reading (`beads/cmd/bd/dolt.go`, stop command)
      shows its only guard is a remote-host check, which does not fire on
      127.0.0.1 — so it would likely signal the gc-supervisor-managed PID.
      Q1 in the design register is being amended accordingly.
- [ ] **Know that mctl is independent of all of this.** Reads verified with the
      city up and with it down. Adjudication through mctl works today; only 4 of
      36 pending `gascity-packs` briefs are adjudicable, the other 32 blocked by
      `MBRF004` (no source dependency) — a data problem, not a tool problem.
- [ ] **Optional, high value:** with the city UP, run one armed dispatch canary
      on a throwaway bead to exercise `gc sling` for real. That path has never
      run end-to-end against a live supervisor.

---

## 5. Issues to file

Both are drafted for `mathcity.create-issue` and are meant to be handed to
another agent.

### Issue A — P1.14 pre-flight aborts on a healthy data plane

- **Problem:** `gc dolt health` does not resolve; the P1.14 block treats its
  exit 1 as "server unreachable"; ~18 skills abort with wrong remediation.
- **Evidence:** `gc --help` shows no `dolt` parent; source at `16fbca8d7`
  declares only `dolt-*` hyphenated commands; the health command lives in
  `examples/bd/dolt/commands/health/run.sh`, an uninstalled command pack.
- **Blast radius:** `check-briefs`, `check-work`, `push-the-fleet`, `wake-city`,
  `simple-work`, `check-molecules`, `city-status`, `testing-work`,
  `strand-sweep`, `formula-work`, `create-bead-manifest`, and more.
- **Quick fix:** install the pack.
- **Hygienic fix:** the pre-flight must distinguish *"the probe is
  unavailable"* from *"the server is unreachable."* A probe that cannot run is
  not evidence the thing it probes is down. That is a contract change to
  `template-fragments/dolt-preflight.md` plus every embedded copy.
- **Do not** swap to `bd dolt health` — it is not a subcommand, bd prints help
  and exits **0**, which the same contract reads as "healthy". That converts a
  fail-closed lie into a fail-open lie.

### Issue B — Convert mechanical skills to MCP tools

- **Problem:** skills that are pure mechanism are prose, so their failures are
  advisory and their dispatch table is hand-maintained.
- **Scope:** the `check-*` family, the work skills, the `new-*-policy` family,
  `communicate-with-other-agent`, and the bash-block sections of `prime-clerk`
  and `prime-mayor-math`.
- **Constraint from §2:** converting a skill whose underlying probe or command
  is broken produces a well-typed wrong answer. Fix Issue A first.
- **Constraint from §2:** convert mechanism, not judgment. The Mayor's bash
  blocks become tools; the Mayor does not.
- **Sequencing:** this is downstream of Slice 6 existing at all.

---

## 6. Division of work

Three tracks, chosen so they do not touch the same files.

**Track 1 — unblock the pre-flight (Issue A).** Smallest, highest leverage,
unblocks everyone else. Touches `template-fragments/dolt-preflight.md` and
~18 skill files. Needs someone comfortable deciding the three-valued contract's
fourth case. **Do this first and alone** — it edits many files shallowly and
will conflict with anything else touching skills.

**Track 2 — Slice 5 (briefs create/validate).** Entirely inside
`assets/scripts/mctl_core/` and `tests/mctl/`. No overlap with Track 1. Can run
concurrently. The `test_real_bead_store.py` harness already demonstrates the
pattern to copy.

**Track 3 — `bin/mctl` shim + first real caller.** Blocked on Track 1 for its
*demonstration* (check-briefs must run), but the shim itself can be built
first. Suggest building the shim under Track 3 and wiring the caller once
Track 1 lands.

Slices 6–8 are sequential after these and should not be parallelized — Slice 6
freezes schemas that 7 and 8 consume.

**Not parallelizable, keep with one agent:** anything touching
`mctl_core/effects.py` or `work.py`, which changed heavily today.

---

## 7. Self-review

**Coverage:** every question Taylor raised is addressed — MCP direction (§2),
skills-vs-MCP (§2), Mayor-as-MCP (§2), verticality (§3), pre-restart (§4),
issues (§5), agent division (§6). The `bd dolt stop` correction is in §4.

**Known gaps, stated rather than hidden:**
- `MCTL_CITY_NOT_ACTIVE` has never been verified against the real Dolt going
  down — only against a closed port in fixtures. `bd dolt stop` is not a safe
  way to get that coverage (§4).
- No live-registered-rig e2e exists. The isolated embedded-Dolt tests are
  faithful but do not exercise the shared server path.
- Slice 6's client-harness requirement (§3) is a recommendation, not a designed
  artifact — someone still has to specify what the harness asserts.
