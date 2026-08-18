# Archived unadjudicated designs — index and value assessment (brief #148)

**Status: ARCHIVED, UNADJUDICATED, NOT ADOPTED.** The four `ARCHIVED-*.md`
documents indexed here are **proposals that were never decided**. Nothing in
them is in force. Do not cite them as policy, precedent, or approved plans.
They are preserved because their content exists nowhere else — not because
anyone endorsed it.

Archived 2026-08-14 under decisions-track brief **#148**, Option (A).
Taylor's verdict, verbatim:

> *"unadjudicated-design-docs-disposition, do they have any value at all? If
> not then file them away."*

Source: four commits in the legacy `~/gt/gascity-packs` detached-HEAD worktree
population (the `#121` 56-commit salvage set). **Nothing was deleted from the
legacy tree**; retirement is separately gated under `gt-0g9die`.

## The four documents

| File | Commit | Date | Lines | Assessment |
|---|---|---|---|---|
| `ARCHIVED-SURFACE-AND-ASK-DESIGN-3e2f9cd3-2026-08-04.md` | `3e2f9cd3` | 2026-08-04 | 479 | **Genuinely valuable** |
| `ARCHIVED-SURFACE-AND-ASK-DESIGN-b4151a3a-2026-08-04.md` | `b4151a3a` | 2026-08-04 | 415 | **Genuinely valuable** (not a duplicate) |
| `ARCHIVED-FEED-THE-MACHINE-REFACTOR-728ed71f-2026-07-24.md` | `728ed71f` | 2026-07-24 | 304 | **Historically interesting / superseded** |
| `ARCHIVED-FEED-THE-MACHINE-REFACTOR-c94cd9d1-2026-08-04.md` | `c94cd9d1` | 2026-08-04 | 237 | **Genuinely valuable — partly landed, partly still actionable** |

---

## Part 1 — SURFACE-AND-ASK (`3e2f9cd3`, `b4151a3a`)

Both specify one run-time loop for an inside worker that hits an unresolvable
dependency: **detect → surface → adjudicate → clean-prompt → re-dispatch**,
with a uniform failure record `gc.failure_class=unresolvable-dependency` +
`gc.blocked_on.{kind,name,detail}` over three kinds (`skill` / `config` /
`tool`).

### The sharp question: does it address today's silent-failure class?

Brief #148 §3 noted the subject matter is live — 2026-08-14 produced a run of
silent-failure-shaped defects. Tested against them, the answer is **mostly no
on the mechanism, yes on one transferable principle**. This is the most
important thing recorded here, because the shared vocabulary is misleading.

**The two classes are opposites.** SURFACE-AND-ASK's scope is a **hard
block**: a worker *cannot proceed* because something is *absent*. Its whole
invariant is that a **detected** unresolvable dependency never ends in a
silent *stall*. Today's defects were the mirror image: the system **did**
proceed, produced a **wrong** result, and **reported success**. Nothing was
absent — things resolved, to the wrong thing.

Per defect:

| Defect | Covered? | Why |
|---|---|---|
| `work_query` returned the wrong set without erroring (`tdupu/mathcity#22`) | **No** | Nothing failed to resolve. A wrong-but-non-empty result is invisible to a preflight that only asks "does this resolve / is it non-empty". |
| Store-scope mismatch, 18 beads unaddressable, nothing reporting (`#149` / `#23`) | **No** (claimed, not delivered) | Both docs map the `gs-vj2d` shadowed-override case to `kind=config`, but §2's actual probe is only "is the required `gc.var.*` non-empty". A value resolved from the wrong layer is non-empty and passes. `3e2f9cd3` is honest about this and defers shadow-detection (D-3/OQ-3); `b4151a3a` §7 overclaims it. |
| Guard at `work-briefed.toml:116` passed while the target was wrong | **No** | The guard is `gc formula list 2>/dev/null \|\| true` into a shell-local var. Even the `config`-kind preflight cannot see it: the detection layer probes the sink, `gc.var.*` and `PATH`, not step-internal shell state. |
| Affinity strands invisible to both discovery paths (`gt-pr2ek3`) | **No** | No worker hit a missing dependency; the backstop sweep is scoped to beads already carrying `failure_class=unresolvable-dependency`. |
| A fork finished and told no one (`#200`) | **No** on detection, **adjacent** on rendering | See the visible-pause marker below. |
| `.github/ISSUE_TEMPLATE` referenced in ten places, never committed, degrading every filing silently (`#24`) | **No** | Closest fit of the six, but a missing template file is none of `skill`/`config`/`tool`, and the degradation was silent precisely because the tool *succeeded* with a blank fallback — so first-use catch never fires either. |

**Score: 0 of 6 mechanically covered.** The design shares the vocabulary
("anti-silent-failure") without sharing the failure mode.

### What in it *is* directly applicable

Two mechanisms generalize past their stated scope and are worth lifting:

1. **The invariant-as-query pattern** — `b4151a3a` §1 states it best: the
   guarantee is "expressed entirely in bead metadata and a brief link, **so it
   can be audited by a query rather than by reading prose**," and *"a bead in
   terminal state with no linked brief is itself a detectable violation the
   control plane repairs"* (the backstop sweep, §3). Generalize the predicate
   from `unresolvable-dependency` to **any terminal state must leave a
   queryable trace, and absence of the trace is itself the alarm**, and it
   covers `#200` (fork finished, told no one), `gt-pr2ek3` (strands invisible
   to both discovery paths), and `#149`/`#23` (18 beads unaddressable with
   nothing reporting). That is a real, reusable answer to today's class — it
   just is not the part of the document that is about dependencies.
2. **The `awaiting-direction` visible-pause marker** (`3e2f9cd3` §3, delta c)
   — a bead-level marker that status surfaces render as *awaiting direction*
   rather than *idle*, set on file and cleared on re-dispatch. `#200` is
   exactly a bead in a state no surface rendered.

### Why both are kept, and how they differ

The commit message on `b4151a3a` claims it *"adopted byte-for-byte"* a
canonical design already authored by a sibling. **That claim is false** — it
is a different 415-line document. Neither sibling contains the other:

**Only in `3e2f9cd3` (the 12-REQ frame):** the `awaiting-direction`
visible-pause marker and its lifecycle (`b4151a3a` has no marker at all); the
worked non-skill (`config`) example; the explicit `brief-prep` exclusion
argued as *"a design error, not merely unnecessary"*; the rejected-alternatives
analysis for the detection layer (skill-wrapper, pack layer); the
`gsp-ioek` + `gsp-6szg` R10/R11 cross-reference binding the design to its
future acceptance probe; the §9 D-1…D-7 decision table stating a position plus
its alternative for every open choice; §11 convergence accounting.

**Only in `b4151a3a` (the 8-REQ frame):** the invariant stated as a
*machine-checkable predicate* rather than prose (item 1 above); the
**de-duplication guard** for the case where worker *and* backstop both file
(`3e2f9cd3` does not address duplicate filing); a **different and arguably
better** resolution for an ambiguous verdict — send back to adjudication
incrementing nothing, *"an ambiguous verdict is a human re-decide, not a loop
iteration,"* where `3e2f9cd3` fails closed and escalates to the Mayor; the
extension of the backstop to a **second** predicate, adjudicated-brief-with-no-
recorded-direction; and a complementary example set (`gh auth`, unreachable
MCP server, unimported pack vs. DSN / `PATH` / `magma`).

Brief #148 §4(B) proposed dropping the weaker sibling. There is no weaker
sibling. Picking either one would discard real content — the same trap
#146 documented.

### Why it still has standing

The gap it was written to fill **is still open**. `brief-system/POLICY.md`
**N4** still says a capability-blocker *"must route through the
capability-resolution path first"* without defining that path, and
`catch-no-brainer` still emits `category:"capability-blocker"` and **stops**,
leaving routing to "the Mayor's job". Neither `gc.blocked_on.*`, the `unblock`
action, nor the backstop sweep exists anywhere in the live surface. These two
documents are the only written specification of that path.

---

## Part 2 — feed-the-machine (`728ed71f`, `c94cd9d1`)

Both inventory the work-dispatch skill family and propose rename/merge/retire
against Taylor's criterion *"a fresh QUIMBY boots already knowing how to feed
the machine."* They are **not two framings of one analysis** — they reach
**contradictory conclusions**, and the later one is right.

### `728ed71f` (2026-07-24) — superseded, and its premise is wrong

Its central diagnosis (D1) is *"the common case has no skill"*, and its
headline proposal is to **create a new `feed-the-machine` skill**. That premise
is false. `c94cd9d1` checked it and found the incumbent `math-city-work`
already carried the trigger phrases *"feed the machine"* and *"feed this bead
to the fleet"* — the skill was not missing, it was **undiscoverable because it
was named after the domain rather than the action**. Acting on `728ed71f`
would have minted a competing dispatch skill (xkcd-927) alongside a working
one.

Its 5-skill inventory is a strict subset of `c94cd9d1`'s 11-skill inventory,
and every finding it makes reappears there in sharper form. It is kept as the
record of a misdiagnosis and its correction, not as a proposal.

### `c94cd9d1` (2026-08-04) — the best artifact of the four; partly landed

Checked against today's live surface:

**Landed.** The incumbent *was* renamed — to **`mathcity.work`**, not
`feed-the-machine`, so OQ-1 was effectively decided but by a different route
and to a different name. `mayor-math-prime` §6 now reads
*"**`mathcity.work`** — Dispatch work to the fleet. Use this after every brief
approval or user request for work"* — the exact anchor line `c94cd9d1` §6.1
quoted, with exactly the rename-update it prescribed applied.

**Not landed, still true today:**

- **§6.2 — `mayor-math` still duplicates the sling command inline.** Four
  `gc sling` invocations remain in `skills/mayor-math/SKILL.md`, including the
  full `--on build-basic-briefed` block the document identified as the RC-1
  drift risk. The recommended fix (replace with a reference to the owning
  skill) is still applicable verbatim.
- **§5.3 / OQ-2 — the `core.gc-work` fleet-sling gap is unfilled.** No
  `gc-work-fleet` supplement skill exists, and no upstream PR landed. A Mayor
  reasoning from the upstream "work" skill still cannot find the dispatch
  action.
- **§4.2 — `sling-new-bead` was never renamed or moved.** It still lives in
  `agent-skills`, outside the mathcity pack boundary.

**A live bug it found that nobody acted on.** `c94cd9d1` row 4 flags a
concrete defect in `sling-new-bead`: it dispatches via `gc sling mayor
--stdin`, while its own declared dependency `communicate-with-mayor` states
that `gc sling mayor` for asks *"was wrong (Taylor 2026-06-24)"* — corrected to
`gc mail send mayor`, which *"does NOT accept `--stdin`"*. Both halves are
still present on disk today: `sling-new-bead/SKILL.md` line 48 still says
`gc sling mayor --stdin`; `communicate-with-mayor/SKILL.md` lines 6 and 71
still say it is wrong and unsupported. **This is itself a silent-failure-shaped
defect** — a relay skill whose own dependency says its transport is invalid —
and it is a candidate for action, not for filing.

The rest of the document (three-axis dispatch taxonomy, five root causes, the
`Scheme A` vs `Scheme B` rename trade-off, trigger-alias continuity, P1.3 sink
rules, P1.13 README rows, the LP1 dogfood landing path) remains accurate and
would not need re-deriving if the dispatch family is revisited. `OQ-1…OQ-6` are
carried open in it; OQ-1 has since been answered by events, the rest have not.

---

## Bottom line

Three of the four have real value; one (`728ed71f`) is a corrected
misdiagnosis kept for the record. None of the four is adopted. Two live items
came out of the read and belong on beads rather than in a docs directory:

1. The `sling-new-bead` transport bug (`gc sling mayor --stdin` vs
   `gc mail send mayor`), verified still live.
2. The invariant-as-query / backstop-sweep pattern, generalized past
   `unresolvable-dependency` to *any* terminal state with no queryable trace —
   the one idea in these 1,435 lines that actually bites on the 2026-08-14
   defect run.
