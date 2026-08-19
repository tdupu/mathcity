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

### Retracted: there is no P1.14 blocker

An earlier revision of this plan claimed `gc dolt health` was uninstalled and
that ~18 skills were aborting on a healthy data plane, and made that the gate on
step 1. **That was wrong and is withdrawn.**

`gc dolt` is a **city-scoped command pack**. From a Gas City root it resolves and
exits 2 (standing compaction quarantine); from `~/repos/mathcity` the `dolt`
parent is never registered and `gc` exits 1 — the code the contract reserves for
"Dolt is down". The original finding was produced by running the probe from a
non-city directory.

The pre-flight itself was fixed weeks ago by `ae6e871` and is covered by a test:

```
$ bash tests/dolt-preflight-exit-codes/smoke_test.sh
ok: 17 call sites, all exit-code-aware
ok: exit 2 -> warns, names hecke/hq, points at gc dolt compact, proceeds
ALL DOLT-PREFLIGHT EXIT-CODE CHECKS PASSED
```

What survives is small and already documented as a *Known limitation* in
`template-fragments/dolt-preflight.md`: outside a city root the abort message
names the wrong cause and the wrong remedy. See Q4 in the design register.
**Nothing blocks step 1.**

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
| `bin/mctl` + `check-briefs` | ✅ | Not blocked — see the retraction in §1. `check-briefs` runs its pre-flight and proceeds. Invoke the skill, observe a real `mctl` call, observe the table. |
| Slice 5 create/validate | ✅ | Real CLI surface, real bead writes, testable against an embedded-Dolt store exactly like `test_real_bead_store.py`. |
| Slice 6 MCP server | ⚠️ **partial** | A server with no client is not end-to-end. Needs a client harness in the same slice, or it is horizontal scaffolding — the thing the plan explicitly forbids. |
| Slice 7 skill refactor | ✅ | Per skill, demonstrable: invoke skill, observe typed call, observe result. |
| live-rig e2e + canary | ✅ | Highest-value missing coverage. Needs a live registered rig and a real sling. |
| Slice 8 dashboard | ✅ | Visible surface, browser-testable. |

**One correction to the order:**

1. **Slice 6 must include a client harness** in the same slice, or it is not
   vertical. Suggest: a minimal MCP client script that lists tools and calls
   `briefs_list`, asserting a typed round trip. Otherwise "Slice 6 done" means
   "a server nobody has ever called."

(A second correction — "install the dolt command pack first" — was withdrawn;
see §1.)

Everything else in the order is sound, and putting `bin/mctl` + one real caller
first is right — it is the cheapest thing that proves the surface is usable
before Slice 6 freezes schemas on top of it.

---

## 4. Before the city restarts

Restarting is safe and nothing below blocks it. These are ordered by what makes
the restart *informative* rather than confusing.

- [ ] **Nothing to install.** The pre-flight is correct; the earlier claim that
      every `check-*` skill would falsely report "Dolt is unreachable" after the
      restart is withdrawn (§1). What agents *will* see is the exit-2 warning
      naming the standing `hecke` (33d) / `hq` (36d) compaction quarantine. That
      is accurate and non-fatal — do not treat it as a restart failure.
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

### Issue A — WITHDRAWN

The original Issue A ("P1.14 pre-flight aborts on a healthy data plane, ~18
skills affected, install the command pack") rested on a finding that turned out
to be a working-directory artifact. It is not filed. See §1 and Q4.

**What could still be filed, much smaller:** outside a Gas City root the
pre-flight's `*` branch reports *"Dolt is unreachable — run `gc dolt start`"*
when the true cause is *"you are not in a city"*. One extra branch in the
canonical fragment plus its 17 embedded copies. Diagnosability, not an outage —
and already recorded as a *Known limitation* in the fragment itself, so filing
it is optional rather than owed.

**Separately worth a decision:** issue **#8** is OPEN while **#7** — same fix,
`ae6e871` — is CLOSED. The mathcity-owned half of #8 is satisfied and tested.
The upstream compaction race (`gastownhall/gascity#3341`) and the standing
33-day quarantine are real and unfixed, but are not mathcity's to fix. Decide
whether #8 closes or stays open tracking the quarantine.

### Issue B — Convert mechanical skills to MCP tools

- **Problem:** skills that are pure mechanism are prose, so their failures are
  advisory and their dispatch table is hand-maintained.
- **Scope:** the `check-*` family, the work skills, the `new-*-policy` family,
  `communicate-with-other-agent`, and the bash-block sections of `prime-clerk`
  and `prime-mayor-math`.
- **Constraint from §2:** converting a skill whose underlying probe or command
  is broken produces a well-typed wrong answer. Verify each probe actually works
  before wrapping it — that principle survives even though the specific P1.14
  instance that motivated it did not.
- **Constraint from §2:** convert mechanism, not judgment. The Mayor's bash
  blocks become tools; the Mayor does not.
- **Sequencing:** this is downstream of Slice 6 existing at all.

---

## 6. Division of work

Three tracks, chosen so they do not touch the same files.

**Track 1 — WITHDRAWN.** There is no pre-flight to unblock (§1). If the
cwd-diagnosability branch from Issue A is ever taken up, it keeps this track's
shape — it edits many files shallowly and must run alone — but it is no longer
first, and no longer blocks anyone.

**Track 2 — Slice 5 (briefs create/validate).** Entirely inside
`assets/scripts/mctl_core/` and `tests/mctl/`. No overlap with Track 1. Can run
concurrently. The `test_real_bead_store.py` harness already demonstrates the
pattern to copy.

**Track 3 — `bin/mctl` shim + first real caller.** No longer blocked on
anything. Build the shim, route `check-briefs` through it, demonstrate the skill
end-to-end. Touches a new `bin/mctl` and `skills/check-briefs/SKILL.md` only —
and must NOT touch that skill's P1.14 block, which is covered by
`tests/dolt-preflight-exit-codes/smoke_test.sh`.

Slices 6–8 are sequential after these and should not be parallelized — Slice 6
freezes schemas that 7 and 8 consume.

**Not parallelizable, keep with one agent:** anything touching
`mctl_core/effects.py` or `work.py`, which changed heavily today.

---

## 7. Self-review

**Coverage:** every question Taylor raised is addressed — MCP direction (§2),
skills-vs-MCP (§2), Mayor-as-MCP (§2), verticality (§3), pre-restart (§4),
issues (§5), agent division (§6). The `bd dolt stop` correction is in §4.

**Revision, 2026-08-18 (same day).** The P1.14 finding that shaped §1, §3, §4,
§5, and §6 of the first revision was wrong — produced by running `gc dolt health`
from outside a Gas City root. Every conclusion that rested on it is retracted
inline above rather than deleted. Net effect: the plan got simpler. Nothing is
blocked, one track disappears, and the proposed order survives with a single
change (Slice 6 needs a client harness).

**Known gaps, stated rather than hidden:**
- `MCTL_CITY_NOT_ACTIVE` has never been verified against the real Dolt going
  down — only against a closed port in fixtures. `bd dolt stop` is not a safe
  way to get that coverage (§4).
- No live-registered-rig e2e exists. The isolated embedded-Dolt tests are
  faithful but do not exercise the shared server path.
- Slice 6's client-harness requirement (§3) is a recommendation, not a designed
  artifact — someone still has to specify what the harness asserts.
