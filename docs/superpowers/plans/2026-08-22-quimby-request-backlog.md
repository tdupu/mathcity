# QUIMBY Request Backlog — Multi-Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`
> or `superpowers:executing-plans`. Steps use `- [ ]` for tracking.

**Goal:** Close every outstanding request the Mayor sessions (QUIMBY 45/46/47) made
of the coordinator, plus the four directives the pack owner routed through them,
as vertical slices that each end in something demonstrably true.

**Architecture:** Seven slices. Each has ONE named owner, ONE tracking issue, ONE
bead, and a definition of done that is observable — a passing red-first test, a
rendered page, or a refused call with a named code. No slice closes on "the tool
exists" (#153).

**Spec:** the QUIMBY request table (this document §0) + `docs/city-dashboard/HANDOFF.md`
for the honesty invariants.

## Global Constraints

- **`CT13.1`** — an operation must COMPLETE through the MCP, not merely be exposed.
- **`CT13.4`** — a refusal is a result: named code + severity + `suggested_next_command`.
  A refusal is reported, never routed around, and never branched on.
- **`CT4.5`** — a hygienic brief is filed BEFORE dispatch; auto-adjudication permitted (B2.9).
- **`P6.2`** — a check that could not have failed must not render as a check that passed.
- **Red-first**: every fix ships with a test that fails when the fix alone is reverted.
- **Review**: named reviewer's verdict at the exact SHA, reviewer != author. Verdicts go
  to the AUTHOR first, coordinator second.
- **`tdupu/mathcity` is PUBLIC** — sanitize absolute home paths. No `Co-Authored-By` (P5.5).
- **`~/repos/mathcity` is coordinator-only.** Work in your own worktree; ask for one.
- **THE PAIR REQUIREMENT (repo owner, 2026-08-22).** Any mctl command that creates work
  MUST produce a dispatchable **pair**: an ADJUDICATED BRIEF (closed + approving verdict)
  carrying a source dependency on an OPEN SOURCE BEAD (status NOT closed). **Either half
  alone is permanently undispatchable.** All six gates must pass for `readiness: "ready"` —
  `MWRK010` (brief closed + approving verdict), `MWRK011` (declares a source dependency),
  `MWRK012` (that id resolves), `MWRK013` (that bead is NOT closed), `MBRF004` (passes
  brief-doctor), and the unnamed no-active-assignee double-dispatch guard.
  **Acceptance, not design note:** a test that creates work and asserts only that the call
  succeeded does NOT satisfy this — the created pair must be shown dispatchable via
  `work_status` returning `readiness: "ready"`, `blockers: []`.
- **QUIMBY's lane is mayor API, MCP, and dispatch.** It coordinates; it does not implement.
  Do not assign it slices. (Coordinator error, corrected by the repo owner 2026-08-22.)

---

## §0 — The backlog this plan closes

| Src | Request | Slice |
|---|---|---|
| Q45 00:01 | `briefs_create` is a dumb insert, no gates | A — **#169**, **#168** already open |
| Q45 00:44 | refactor `briefs_adjudicate` revise-path | B |
| Q45 00:35 | path-B order provenance is non-atomic | E — filed **#178** |
| Q45 00:47 | two issues never filed | G |
| Q47 16:55/17:58 | MCP-only handicap must go in `mayor-math-prime` | D |
| Q47 19:01 | `city_health` is a SEPARATE defect from #159 | C — filed **#176** |
| Q47 19:41 | `decisions-to-briefs` as a typed MCP tool | F — filed **#177** |
| Taylor D1 | ARM LIVE DISPATCH | F0 — **blocked on the repo owner**, see below |
| Taylor D2 | `MBRF034` -> FATAL; creation refuses instead of minting a brick | A |
| Taylor D3 | rename `briefs_adjudicate` -> `briefs_relay_adjudication` | B — filed **#175** |
| Taylor D4 | `#147`/`MBRF035` is URGENT | C0 |

---

## Slice A — Creation refuses instead of minting a brief its own approval will brick

**Owner:** mutt · **Issues:** #173, #169, #168 · **Reviewer:** stick-dog

Today `briefs_create` accepts anything and `briefs_adjudicate` then closes the bead
that the dispatch gate rejects as a closed source (#173). Taylor's ruling: **raise
`MBRF034` to FATAL so creation refuses rather than minting a brief that its own
approval will brick.**

**Severity correction QUIMBY could not post itself:** `briefs_create` takes a
`sources` parameter. **The brick only fires when `sources` is OMITTED.** #173's
current severity claim is too strong and must be corrected on the issue.

- [ ] Post the `sources` correction on #173 before any code
- [ ] Red test: `briefs_create` with no `sources` must REFUSE with a named FATAL code
- [ ] Red test: an approved brief must never report both `MWRK011` and `MWRK013`
- [ ] Implement: `MBRF034` FATAL at creation; do NOT make a brief its own source (#173 candidate A)
- [ ] Verify both tests fail when the fix alone is reverted
- [ ] #169 (no structural validation) and #168 (no stack-index row) fold in here — same call, same commit or siblings

**Done when:** creating a sourceless brief is refused with a named code, and no
approved brief can reach the contradictory-diagnostic state.

## Slice B — Adjudication is named and shaped as a relay, not an authority

**Owner:** stripes · **Issues:** #152, NEW-rename · **Reviewer:** sally

Taylor, verbatim:

> *"I should be `briefs_relay_adjudication` to make it clear to agents they aren't
> making the adjudication but that they are relaying the user adjudication."*

The current name invites exactly the behaviour #152 describes. **The rename does not
fix the authority hole — it stops the tool from reading as a grant of authority it
does not carry.**

- [ ] File the rename issue, linked to #152
- [ ] Red test: the old name is gone from `TOOLS` and from `client.py::ALLOWED_TOOLS`
- [ ] Rename, with a deprecation shim only if a caller would break; state which callers
- [ ] Fold Q45's revise-path refactor here — same tool, same commit family
- [ ] `authorization_mode: commission | explicit` recorded per R3.2

**Done when:** the tool is named for what it does, and an agent reading the tool list
cannot mistake relaying for deciding.

## Slice C — The city cannot report health it never measured

**Owner:** bob · **Issues:** #159, NEW-city_health · **Reviewer:** trans

`city_health` reported `data_plane: healthy, 17/17 rigs healthy` **during a total
outage where every read was FATAL.** QUIMBY's finding: this is a SEPARATE defect from
#159. **#159 is misattribution; this is asserting health that was never probed.**

**`mayor_city_state` got it right when four other instruments lied.** Find out why
first — if it probes differently, that difference is the fix, and it is worth more
than four separate bug reports.

- [ ] File the new issue; cross-link #159 and say explicitly how they differ
- [ ] Measure why `mayor_city_state` was correct — that is step one, not step three
- [ ] Red test: with the data plane unreachable, `city_health` must NOT return `healthy`
- [ ] Three-valued, never boolean (HANDOFF §5 invariant 1); a timed-out probe is not a zero

### C0 — URGENT, ahead of C: `#147` / `MBRF035`
**Owner:** sally. Taylor: *"This is a bug that needs to be fixed and it is urgent."*
mathcity cannot accept a brief at all, so **the rig that owns mctl cannot receive its
own repair work while CT4.5 requires a brief before dispatch.** sally measured that the
resolution is CORRECT and the directory is simply ABSENT — so the fix is creation, not
resolver repair. **State what guarantees a new rig gets one.**

## Slice D — The MCP-only handicap is written where agents actually read it

**Owner:** creek (author) · **Worktree:** `.claude/worktrees/quimby` (handed over) · **Reviewer:** pink

**QUIMBY does not own this.** It is the Mayor: it coordinates, it does not implement.
Assigning it a slice was the coordinator's category error. **QUIMBY hands creek the
`debug-city` content it already authored (220 lines, hygiene-validated) and the verbatim
directive; creek lands both.**

Taylor, verbatim, relayed twice and still not in the skill:

> *"Don't use a workaround." / "Only use MCP commands." / "This is very important and
> needs to be in the mayor-priming skill. **This is an intentional handicapping for the
> purpose of debugging.**"*

**ALREADY AUTHORED AND LANDED** at `246d33f` on `quimby/debug-city-skill` (base
`8574757`, not pushed): `skills/debug-city/SKILL.md` +220 NEW, and
`skills/mayor-math-prime/SKILL.md` +65. **creek reviews; pink second-checks the
verbatim quoting specifically.** Re-authoring existing good work would be waste; the
lane correction applies going forward, not retroactively.

- [ ] creek: verdict at `246d33f` — is Taylor's directive VERBATIM, not paraphrased?
- [ ] Does it say the restriction is an INSTRUMENT, not a safety rail? A Mayor who thinks it is a guardrail routes around it; one who knows it is a measuring device reports the block
- [ ] Does it handle the conflict case: the handicap vs a dead city (QUIMBY lived it twice today)
      (QUIMBY's own 18:33 self-report — it ran `gc dolt start` and disclosed it)
- [ ] Does anything in `debug-city` tell an agent to work around a refusal? That would contradict `CT13.4`

**Done when:** a fresh Mayor session primes and knows the restriction is an instrument,
not a safety rail.

## Slice E — Path-B order provenance is atomic

**Owner:** trans · **Issue:** NEW · **Reviewer:** mutt

Q45's finding, filed nowhere: path-B dispatch records provenance non-atomically, so a
run can exist with provenance that never landed.

- [ ] File it with the measurement
- [ ] Red test: a dispatch whose provenance write fails must not read as provenanced

## Slice F — `decisions-to-briefs` becomes a typed MCP tool

**Owner:** cozy · **Issue:** NEW (link #85) · **Reviewer:** creek

QUIMBY's title suggestion: *"feat: mctl: decisions-to-briefs as a core command exposed
as a typed MCP tool."* **#85 already records that the SKILL never calls mctl** — this
is the tool that makes it possible to.

### F0 — ARM LIVE DISPATCH (blocked on the repo owner, blocks nothing else)
`MCTL_ENABLE_LIVE_DISPATCH=1` must be in the MCP server process's environment **at
launch** — no typed tool can set it. **QUIMBY located the binding**: `~/.claude.json`
-> projects -> `<city-root>` -> `mcpServers` -> `mctl`, currently `env: {}`. **Its
attempt to set it was blocked by the harness permission gate**, correctly —
`~/.claude.json` is user-scope config and no agent edits it.

**This needs the repo owner's hands.** `work_dispatch(he-8hoo)` already reached
`preflight_result: passed` and refused with `MCTL_LIVE_DISPATCH_DISARMED` — a clean
`CT13.4` refusal, and the evidence that arming is now reasonable. **Nothing else in
this plan waits on it.**

## Slice G — QUIMBY 45's two unfiled issues

**Owner:** brad · **Blocked on:** content. The original message carried no
paste-ready blocks and QUIMBY 45's context is gone. **Either brad reconstructs them from
QUIMBY 45's 00:47 message, or we declare them lost and say so** — an unfiled issue that nobody can
reconstruct is a real loss and gets recorded as one, not quietly dropped.

---

## Hourly check

The coordinator verifies each slice hourly: issue open/closed, branch+SHA, reviewer
named, and whether the definition of done is observable yet. **A slice with no
movement for two consecutive hours gets its owner asked what is blocking, not chased.**
