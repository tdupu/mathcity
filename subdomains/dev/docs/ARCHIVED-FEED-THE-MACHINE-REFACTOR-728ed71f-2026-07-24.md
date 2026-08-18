> ## ARCHIVED — UNADJUDICATED DESIGN, NOT ADOPTED POLICY
>
> **This document was never adjudicated and nothing in it is in force.** It
> describes a proposal, not a decision. Do not cite it as policy, precedent,
> or an approved plan.
>
> - **Source commit:** `728ed71ff8b7dadeebef8ffea94fb1a9a400a247` (legacy `~/gt/gascity-packs` detached-HEAD worktree
>   population — the `#121` 56-commit salvage set), 2026-07-24, 304 lines.
> - **Archived:** 2026-08-14 under decisions-track brief **#148**, Option (A).
>   Taylor's verdict: *"unadjudicated-design-docs-disposition, do they have any
>   value at all? If not then file them away."*
> - **Value assessment (brief #148):** **HISTORICALLY INTERESTING / SUPERSEDED** — its central premise — "the common case has no skill" — is factually wrong and was refuted by its own sibling `c94cd9d1`, which found the incumbent (`math-city-work`, now `mathcity.work`) already carried the trigger phrase "feed the machine". Acting on this document would have minted a duplicate skill (xkcd-927). Kept for the record of how the misdiagnosis was reached and corrected.
> - Nothing was deleted from the legacy tree; retirement is separately gated
>   under `gt-0g9die`. Full comparative assessment:
>   [`ARCHIVED-DESIGNS-INDEX-2026-08-14.md`](./ARCHIVED-DESIGNS-INDEX-2026-08-14.md).

---

# Feed-the-Machine Refactor Proposal

**Source:** gsp-vpry — Taylor 2026-07-15  
**Status:** PROPOSAL — naming/structure decision to Taylor before any skill is written/renamed  
**Scope:** mathcity-owned skills only; upstream core.gc-work fix proposed but not executed  
**Acceptance criterion:** a fresh QUIMBY session boots already knowing how to feed the machine

---

## 1. Inventory + Map — the current dispatch-skill family

### 1.1 core.gc-work (UPSTREAM — read-only)

**What it claims:** "Finding, creating, claiming, and closing work items (beads)"  
**What it actually does:** teaches `bd create/list/claim/close` — pure bead CRUD. Mentions
`gc sling` twice in passing but never teaches the invocation, rig-scoping, or convoy
shape. Loading it in a fresh Mayor session did NOT give the Mayor the sling workflow —
had to be rediscovered by hand (gsp-vpry session evidence).  
**Location:** cached at `~/.gc/cache/repos/<hash>/…` (git-URL import, read-only)  
**Failure mode:** The Mayor loads it expecting to learn how to dispatch work to agents,
but it only covers bead management. The sling step is entirely absent.

### 1.2 immediate-work (mathcity-owned)

**What it claims:** "In-session synchronous dispatch — spawn the right agent NOW in the
current session to complete a specific bead or task. No pool, no queue, no sling."  
**What it actually does:** uses the `Agent` tool to spawn a subagent inline. The result
comes back in the current conversation. The work runs in the same session context.  
**Trigger phrases:** "immediate work", "do this now", "spawn now for X"  
**Failure mode:** Name "immediate" conflates urgency with in-session scope. A Mayor
wanting "fast dispatch" might grab this and be surprised the work is in-session (not
fleet). Also: this is NOT "feeding the machine" — it runs inside the Mayor's context.

### 1.3 priority-work (mathcity-owned)

**What it claims:** "Async targeted dispatch — bump a bead to P0 and dispatch it
explicitly to a NAMED agent… bypassing queue order."  
**What it actually does:** bumps priority to P0 AND names a specific agent target
(e.g. a polecat or codex session). No pool. Named target only. Async.  
**Trigger phrases:** "priority work", "bump this to the front", "dispatch this to <agent> now"  
**Failure mode:** Conflates TWO things: priority-bumping and named-agent dispatch.
A Mayor wanting "fleet dispatch at normal priority" gets neither. Also, the "priority"
in the name implies P0-urgency, but sometimes the Mayor just wants to send to the fleet
at normal queue order.

### 1.4 sling-new-bead (agent-skills, NOT mathcity)

**What it claims:** Relay user's idea for a new bead to the Mayor (create + dispatch).  
**What it actually does:** user-facing entry point — composes `communicate-with-mayor`
with a structured mayor-instruction payload. The Mayor then files the bead and sllings it.  
**Location:** `~/.agents/skills/sling-new-bead/` (agent-skills, not mathcity pack)  
**Failure mode:** Direction confusion — this is USER→Mayor, not Mayor→fleet. The name
"sling-new-bead" sounds like it sllings work, but it's asking the Mayor to sling.
Also wrong pack ownership (agent-skills, not mathcity).

### 1.5 mayor-math (mathcity supplement)

**What it claims:** "Supplement to gc.mayor for Gas Town context. Provides the correct
rig-scoped sling mechanics for build-basic convoy workflows."  
**What it actually does:** THIS is where the actual sling workflow lives — the canonical
invocation, rig-prefix→coordinator table, and build-basic constraints. But it's buried
as a mayor SUPPLEMENT, not a dispatch skill. A fresh Mayor session may not have loaded
mayor-math before needing to sling.  
**Failure mode:** The fleet-sling mechanics are coupled into a mayor orientation
supplement. They're not discoverable via "how do I dispatch work to the fleet?"

### 1.6 Adjacent skills (for completeness)

| Skill | What it does | Relationship to dispatch |
|---|---|---|
| **fan-out** (mathcity) | Decompose an epic bead into sub-beads WITHOUT consuming WIP slots | Post-dispatch — used AFTER slinging an epic to decompose it |
| **communicate-with-mayor** (agent-skills) | Send a mail message UP to the Mayor | Infrastructure, not dispatch |
| **coordinate-agents** (agent-skills) | Multi-agent coordinator role | Separate concern; routes peer messages |

---

## 2. Diagnosis — Why "they haven't worked"

### D1 — Missing the common case

The Mayor's core loop needs ONE thing: "I have a bead, dispatch it to the fleet right
now at normal priority." No skill teaches this. The correct command is:

```bash
gc sling gascity-packs/gc.implementation-worker <bead-id>
```

…but core.gc-work doesn't mention it, immediate-work explicitly says "no sling",
priority-work requires P0 and a named target, and mayor-math buries it in a supplement.
The Mayor rediscovers `gc sling` by hand every session.

### D2 — Wrong axes for the names

The real axes for "how to dispatch work" are:
1. **Execution context**: in-session (Agent tool) vs fleet-pool (gc sling → pool claim) vs fleet-named (gc sling → specific agent)
2. **Priority**: normal-queue vs P0-bumped

The current names ("immediate", "priority") map to urgency intuitions, not dispatch
architecture. A Mayor maps "I want this done immediately" to `immediate-work` but
the right tool for "I want it done now via the fleet" is something else entirely.

### D3 — Pack boundary confusion

`sling-new-bead` and `communicate-with-mayor` live in agent-skills, not mathcity.
They're not visible to city agents loading mathcity skills, and they're not under the
math city hygiene boundary. The user-facing "ask Mayor to sling" pattern should
live in mathcity so it ships with the pack.

### D4 — Priming gap

`mayor-math-restart` (the new QUIMBY session orientation skill) does not reference any
dispatch skill. After QUIMBY reboots, it reads the durable docs and onboarding briefs
but there's no guaranteed "you know how to feed the machine" step. The sling mechanics
arrive only if the Mayor has loaded mayor-math, and only then by reading through the
full supplement to find the one canonical invocation.

### D5 — Upstream gap stays unaddressed

`core.gc-work` is the most natural place for "how to dispatch work to the fleet" to live.
But it's upstream (read-only cached). We need a mathcity supplement that fills the gap
explicitly, not implicitly through mayor-math.

---

## 3. Proposed Refactored Family

### 3.1 Axis table

| Axis | Choices |
|---|---|
| Execution context | `in-session` (Agent tool) / `fleet-pool` (gc sling → pool) / `fleet-named` (gc sling → named agent) |
| Priority | `normal` (normal queue order) / `urgent` (P0-bumped) |
| Who triggers | `mayor/worker` (Mayor or agent dispatching work) / `user-relay` (user asking Mayor to dispatch) |

### 3.2 Proposed skill names

| Proposed name | Status | Old name | What it covers |
|---|---|---|---|
| **feed-the-machine** | NEW | — | The common case: bead → `gc sling <rig>/gc.implementation-worker` → fleet pool, normal priority. One-page skill, Mayor-facing. |
| **immediate-work** | KEEP (description update) | immediate-work | In-session synchronous: Agent tool in THIS conversation. Clarify description: "in-session, no fleet, no pool". |
| **priority-work** | KEEP (description update) | priority-work | Async named-agent dispatch + P0 bump. Clarify: "named target only, always P0, always async". Remove misleading overlap with feed-the-machine. |
| **sling-idea-to-mayor** | RENAME + move to mathcity | sling-new-bead | User→Mayor relay: user has an idea, Mayor files + dispatches. Move from agent-skills to mathcity/skills/. |
| **core.gc-work supplement** | NEW (supplement pattern) | — | mathcity-owned `gc-work-dispatch.md` doc (or thin skill) filling the sling gap in core.gc-work. Referenced from feed-the-machine. |

**Skills left unchanged:**
- `fan-out` — correct name, unrelated to this refactor
- `communicate-with-mayor` — correct name, infrastructure
- `coordinate-agents` — unrelated concern
- `mayor-math` — REFACTORED (see §3.3)

### 3.3 mayor-math refactor

`mayor-math` currently bundles: (a) rig-prefix → coordinator table, (b) sling
invocation, (c) build-basic convoy rules, (d) QUIMBY onboarding pointers.

**Proposed split:**
- **mayor-math** (KEEP, trimmed): remove the sling invocation block; replace it with
  `[[feed-the-machine]]` reference. Keep rig-prefix table and build-basic convoy rules.
- **feed-the-machine** (NEW): owns the canonical sling invocation. One-liner trigger.

This makes `mayor-math` a "rig table + fleet rules" skill and `feed-the-machine` the
"how to pull the trigger" skill. Separation of concerns.

### 3.4 feed-the-machine — proposed skill shape

**Trigger phrases:** "feed the machine", "sling this to the fleet", "dispatch to the fleet",
"normal dispatch", "sling this bead", "workers should do this", "route this to the city"

**Core workflow (one canonical path):**

```bash
# 1. Ensure a bead exists
bd create -t task --title "<title>" --description "<done condition>" --priority 1

# 2. Sling to the implementation-worker fleet (normal priority)
gc sling gascity-packs/gc.implementation-worker <bead-id>
```

**When to use vs siblings:**

| Situation | Use |
|---|---|
| Normal work, fleet, pool claim | **feed-the-machine** |
| Urgent, P0, named specific agent | **priority-work** |
| Watch it run in this conversation | **immediate-work** |
| User has an idea, needs bead + dispatch | **sling-idea-to-mayor** |

**Rig-prefix → coordinator** (pointer to mayor-math table, not duplicated here):
`gsp-` → `gascity-packs/gc.implementation-worker` (default for pack work)
`he-` → `hecke/gc.implementation-worker`
(full table in `[[mayor-math]]`)

---

## 4. Migration

### 4.1 How renames land (hygiene path)

All owned-skill changes follow DOGFOOD-WORKFLOW.md:
1. Author new/renamed SKILL.md in `~/gt/gascity-packs/mathcity/skills/<name>/SKILL.md`
2. Commit + push from `~/gt/gascity-packs` (QUIMBY lane)
3. BART pulls into `~/repos/gascity-packs` and rebuilds the live city
4. BART updates symlinks in `~/gt/.claude/skills/` and `~/.claude/skills/`

`sling-new-bead` moves from agent-skills to mathcity:
- New path: `mathcity/skills/sling-idea-to-mayor/SKILL.md`
- Old path: agent-skills `sling-new-bead` → RETIRE (mark retired; a redirect or
  wrapper in agent-skills pointing to the new mathcity skill)

### 4.2 Trigger backward compatibility

Old trigger phrases (`sling new bead`, `sling-new-bead`) can be added to
`sling-idea-to-mayor`'s trigger list to preserve muscle memory.

`immediate-work` and `priority-work` keep their names and all existing triggers.

### 4.3 core.gc-work gap (upstream)

**Option A — mathcity supplement skill (recommended for now):** write
`mathcity/skills/gc-work-fleet/SKILL.md` (or reference it from `feed-the-machine`).
Supplements core.gc-work with the fleet-sling idiom. No upstream PR required.

**Option B — upstream PR to gastownhall/gascity-packs:** add the fleet-sling section
to `core/skills/gc-work/SKILL.md`. Correct long-term solution but requires BART to
submit and a maintainer to merge. Flag for follow-up.

**Decision needed from Taylor:** Option A or B (or both in sequence)?

### 4.4 mayor-math-restart coordination (HOMER)

`mayor-math-restart` is HOMER's in-progress work. This proposal NAMES the required
edit (see §5 Priming Integration) but does NOT implement it. HOMER lands the edit
after Taylor approves the proposal. Do not clobber HOMER's working tree.

---

## 5. Priming Integration (acceptance criterion)

**Requirement (Taylor 2026-07-15):** "a new QUIMBY boots already knowing how to feed
the machine." This means the sling mechanics must arrive at orientation, not on-demand.

### 5.1 Required edits to mayor-math

Add to the "Current dispatch pattern" block of `mayor-math/SKILL.md`:

```
**Feeding the machine (common case — normal priority, fleet pool):**
See [[feed-the-machine]]. The canonical invocation:
  gc sling gascity-packs/gc.implementation-worker <bead-id>
Load this skill whenever you need to dispatch work to the city fleet.
```

### 5.2 Required edit to mayor-math-restart (HOMER's skill)

After loading the canonical onboarding docs and session catalog, add a priming step
that loads `feed-the-machine`:

```
## Fleet dispatch (loaded at every QUIMBY session start)
- Load [[feed-the-machine]] — the canonical "bead + sling to fleet" skill.
  Trigger: "feed the machine", "sling to fleet", "dispatch to city workers".
  If this skill is not loaded, a fresh Mayor must rediscover `gc sling` by hand.
```

The edit to mayor-math-restart is flagged to HOMER; QUIMBY must not land it
uncoordinated.

### 5.3 Verification of the acceptance criterion

After the refactor lands, a fresh QUIMBY session running `mayor-math-restart` will:
1. Load `mayor-math` (existing step)
2. Load `feed-the-machine` (new step per §5.2)
3. Receive a dispatch request from Taylor → trigger phrase "sling this to the fleet"
   → routes to `feed-the-machine` → Mayor has the canonical `gc sling` command
   → no hand-discovery needed

---

## 6. Hygiene (check-plan-hygiene mental run)

- **P1.3 / Pillar 2-3**: no editing upstream cache. core.gc-work supplement is a NEW
  mathcity skill, not a hand-edit of `~/.gc/cache/…`. ✓
- **P1.13 README rows**: every new/renamed skill needs a row in mathcity README and
  relevant subdomain README. Specifically: `feed-the-machine`, `sling-idea-to-mayor`,
  `gc-work-fleet` (if Option A). Flag for `update-README` after Taylor approves.
- **Pack boundary**: all new/moved skills land in `mathcity/skills/`. `sling-idea-to-mayor`
  moves from agent-skills (outside the pack) to mathcity (owned). ✓
- **No gastown-vocab-as-identity**: new skills do not adopt gastown roles.
- **DOGFOOD-WORKFLOW.md path**: all edits go through QUIMBY→BART loop per §4.1. ✓

---

## 7. Decision surface — what Taylor decides

1. **Naming**: accept `feed-the-machine` as the new skill name, or choose an alternative
   (options: `fleet-work`, `dispatch-to-fleet`, `sling-to-workers`)?
2. **sling-idea-to-mayor** vs keep `sling-new-bead` (pack move only, no rename)?
3. **core.gc-work gap**: Option A (mathcity supplement) vs Option B (upstream PR) vs both?
4. **mayor-math split**: accept the split (feed-the-machine owns the sling invocation,
   mayor-math keeps the rig table) or keep mayor-math as-is and just add a reference?
5. **mayor-math-restart priming edit**: flag to HOMER to land after this decision, or
   Taylor coordinates directly?

No skill is created or renamed until these decisions land.
