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

---

## §0 — The backlog this plan closes

| Src | Request | Slice |
|---|---|---|
| Q45 00:01 | `briefs_create` is a dumb insert, no gates | A |
| Q45 00:44 | refactor `briefs_adjudicate` revise-path | B |
| Q45 00:35 | path-B order provenance is non-atomic | E |
| Q45 00:47 | two issues never filed | G |
| Q47 16:55/17:58 | MCP-only handicap must go in `mayor-math-prime` | D |
| Q47 19:01 | `city_health` is a SEPARATE defect from #159 | C |
| Q47 19:41 | `decisions-to-briefs` as a typed MCP tool | F |
| Taylor D1 | ARM LIVE DISPATCH | F0 (coordinator) |
| Taylor D2 | `MBRF034` -> FATAL; creation refuses instead of minting a brick | A |
| Taylor D3 | rename `briefs_adjudicate` -> `briefs_relay_adjudication` | B |
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

**Owner:** QUIMBY 47 (author) · **Worktree:** `.claude/worktrees/quimby` · **Reviewer:** brad

Taylor, verbatim, relayed twice and still not in the skill:

> *"Don't use a workaround." / "Only use MCP commands." / "This is very important and
> needs to be in the mayor-priming skill. **This is an intentional handicapping for the
> purpose of debugging.**"*

- [ ] Write it into `skills/mayor-math-prime/SKILL.md`, quoting verbatim
- [ ] Include the conflict case: what to do when the handicap and a dead city collide
      (QUIMBY's own 18:33 self-report — it ran `gc dolt start` and disclosed it)
- [ ] Land `debug-city` (220 lines, authored, hygiene-validated) in the same worktree

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

### F0 — ARM LIVE DISPATCH (coordinator, gated on Taylor)
`MCTL_ENABLE_LIVE_DISPATCH=1` in the MCP server process environment. **No typed tool
can set it — it is a session-launch property.** In front of Taylor as an explicit
decision. **Nothing else in this plan is blocked by it.**

## Slice G — QUIMBY 45's two unfiled issues

**Owner:** QUIMBY 47 · **Blocked on:** content. The original message carried no
paste-ready blocks and QUIMBY 45's context is gone. **Either 47 reconstructs them from
45's message, or we declare them lost and say so** — an unfiled issue that nobody can
reconstruct is a real loss and gets recorded as one, not quietly dropped.

---

## Hourly check

The coordinator verifies each slice hourly: issue open/closed, branch+SHA, reviewer
named, and whether the definition of done is observable yet. **A slice with no
movement for two consecutive hours gets its owner asked what is blocking, not chased.**
