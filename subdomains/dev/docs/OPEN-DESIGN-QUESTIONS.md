# Open Design Questions

Parent: [Dev README](../README.md)

Questions about **intent** that came out of implementation work and that the
code cannot answer on its own. Each one is a place where an observed behavior
is either deliberate-and-undocumented or accidental, and where guessing wrong
produces a plausible-looking bug.

This register exists because these were being discovered one at a time, buried
in commit messages and agent transcripts, and re-derived by whoever hit them
next. Recording the question is cheap; re-deriving it is not.

## How to use this file

- **Add a question** when you find behavior whose *intent* you cannot determine
  from source, tests, or docs — especially when you had to pick a reading in
  order to keep moving. Record the reading you picked.
- **Owner** is who can actually answer, not who found it. Upstream questions
  about Gas City / beads belong to their author.
- **Resolve** by recording the answer inline and moving the entry to Resolved,
  with the date and who decided. Do not delete entries — the reasoning is the
  value.
- Questions needing a durable adjudication get a `bd` decision bead too; this
  file is the index, not a replacement for the bead.

Status vocabulary: `OPEN` · `ASKED` (routed to owner, awaiting answer) ·
`RESOLVED`.

---

## Q1 — Is the Gas City control-plane / data-plane lifecycle split intentional?

**Status:** OPEN · **Owner:** Chris Sells (Gas City upstream) · **Raised:**
2026-08-18, from mctl liveness work

**Observed.** `gc stop` / `gc supervisor stop` brings down the supervisor and
city controller but leaves the managed Dolt SQL server running. Dolt is
supervised by its own watchdog process (`gc __gc-managed-dolt-scope-watchdog`),
not by the supervisor. Verified live: `gc supervisor status` reporting
"Supervisor is not running" while `lsof -i :58506` showed `dolt` PID 25668 in
LISTEN, and `bd`-backed reads continued to answer normally.

There is also no supported inverse. There is no `gc dolt stop`; the only lever
is `gc dolt restart`, which bounces the data plane shared by every rig on the
machine. So the control plane has a clean stop and the data plane effectively
does not.

**The question.** Is that asymmetry intended?

- If **intended** — presumably so bead state stays readable while the control
  plane is restarted, which is a genuinely useful property — then it should be
  documented, because "is the city up?" reads as one question and is two.
- If **not intended**, then `gc stop` leaves a process running that a user
  reasonably believes they stopped.

Either way, is there a supported way to stop *only* the data plane for one
city, or is the shared-Dolt blast radius considered acceptable by design?

**Why it matters / what it already broke.** mctl modeled liveness as a single
boolean computed by probing the Dolt port. In the state above it reported the
city as active with no supervisor running — correct for reads, since `bd`
talks to Dolt directly and `briefs list` answered in 0.25s, but wrong for
dispatch, which shells out to `gc sling` and had nothing to route to.

**Reading we adopted.** Two independent probes: reads gate on the data plane
(`MCTL_CITY_NOT_ACTIVE`), armed dispatch additionally gates on the control
plane (`MCTL_CONTROL_PLANE_NOT_ACTIVE`). This is correct for mctl regardless of
how upstream answers, but the answer determines whether other tools should be
doing the same thing.

**Note on testing.** Fixtures can express "endpoint closed" but not "endpoint
open with nothing behind it," which is the state `gc stop` actually produces.
This class of bug is not reachable without a live city.

---

---

## Q4 — The P1.14 Dolt pre-flight reports a healthy data plane as unreachable

**Status:** OPEN · **Owner:** Taylor (mathcity side) + Gas City upstream ·
**Raised:** 2026-08-18

**Observed.** `template-fragments/dolt-preflight.md` defines the canonical
three-valued pre-flight every mathcity skill copies verbatim. It calls
`gc dolt health` and treats exit 1 as "server unreachable — the only value that
means Dolt is down", routing everything else to the same abort branch.

The installed `gc` has **no `dolt` subcommand at all**:

```
$ gc dolt health
gc: unknown command "dolt"
$ gc dolt health >/dev/null 2>&1; echo $?
1
```

Both binaries on PATH (`~/go/bin/gc`, `~/.local/bin/gc`) behave identically.
Exit 1 is precisely the code the contract reserves for "Dolt is down", so the
canonical block, run verbatim, currently prints:

```
I'm sorry, I can't do that — Dolt is unreachable (bd cannot resolve beads).
```

while Dolt is demonstrably **up** — listening on 127.0.0.1:58506, with `bd`
resolving 9,570 beads and mctl reading 66 briefs off it in the same session.

**Blast radius.** Roughly 18 call sites embed the block, including
`check-briefs`, `check-work`, `push-the-fleet`, `wake-city`, `simple-work`,
`check-molecules`, `city-status`, `testing-work`, `strand-sweep`. Each aborts
before doing any work.

**Why this is the issue #7/#8 bug in a new costume.** Those issues were about
`||` collapsing the three-valued contract so a standing *quarantine* read as a
connectivity failure. The contract was fixed to test 0 and 2 explicitly and
route everything else to abort. That fix is correct for the failure modes it
enumerates (1 unreachable, 78 port unresolved, 127 gc missing) — but a **gc
that no longer has the subcommand** lands in the same catch-all, and once again
a healthy data plane is reported as down with remediation advice
(`gc dolt start`) that cannot work.

**The question.** Did `gc dolt` move, get renamed, or get removed upstream? And
should the pre-flight distinguish "the probe itself is unavailable" from "the
server is unreachable"? A probe that cannot run is not evidence that the thing
it probes is down — the two deserve different exits and different remediation.

**What mctl does instead, and why it happens to work.** mctl does not use this
fragment. It TCP-connects to the endpoint named in
`.beads/dolt-server.port` and gates bead commands on that. That is a boolean
probe of the kind this fragment warns against, and it was written without
knowledge of the P1.14 contract — but it is the reason mctl reports Dolt
correctly today while the canonical pre-flight does not. Reconciling the two is
open: mctl should probably consume the canonical contract once the contract can
actually run.


## Q2 — Should mctl core be the single writer of the brief stack index?

**Status:** RESOLVED (direction set; implementation not started) · **Owner:**
Taylor · **Raised:** 2026-08-18, from mctl cache-write work

**Observed.** `formulas/brief-prep.toml:56-57,142` and
`BRIEF-SHUFFLE-FAST-DRAIN-PLAN-2026-08-16.md` §2 both declare the shuffler the
single writer of `stack/.index.jsonl`. mctl's adjudication path became a second
writer (Slice 3) without either document being amended.

The two writers are disjoint in operation — the shuffler only appends rows for
new slugs, mctl only mutates existing rows and never appends — but they collide
physically, because a read-modify-write can drop a concurrent append.

**Decision (Taylor, 2026-08-18).** Neither "amend the boundary to admit a
second writer" nor "have mctl submit intents to the shuffler". Instead:
**mctl's shared core becomes the single writer, and the shuffler is refactored
to call it.** Agents reach it through mctl (and later the MCP tools) rather
than writing the file themselves.

**Rationale.** One implementation of the stack-index semantics — locking,
atomicity, serialization convention — instead of one per producer. The
alternative direction (mctl submitting intents to a batch drain) would have
made an interactive adjudication wait on the next drain cycle.

**Corroboration.** The two-producer problem is already an adjudication-pending
brief: `.index.jsonl` measured at 83 rows compact + 1 spaced, from producers
disagreeing on `json.dumps` settings. A single shared writer removes that
class of drift by construction.

**Interim state.** mctl now takes the shuffler's own lock
(`<stack>/.manifest.lock`, not a lock of its own — `flock` only serializes
holders of the same file) and splices rather than re-serializing untouched
rows. That makes today's two-writer reality safe; it does not implement the
decided direction.

**Open sub-question.** The natural shape is to extract the index
read-modify-write into a small module both callers import, rather than having
the shuffler depend on `mctl_core.effects` — which would drag in city/rig
context resolution the shuffler does not have. Confirm that shape before
building.

---

## Q3 — `BriefOption` was defined twice in the MCTL plan

**Status:** RESOLVED · **Owner:** Taylor · **Raised:** 2026-08-18 ·
**Resolved:** 2026-08-18

**Observed.** `MCTL-MCP-IMPLEMENTATION-PLAN.md` defined `BriefOption` twice
with incompatible fields: §2 as a decision option parsed from brief markdown
(`label, heading, start_line, end_line, raw_text, confidence`), and Slice 2 as
an enabled action (`id, label, description, enabled, disabled_reason`).

**What it caused.** An external review proposed implementing `MOPT001` by
gating on `brief_options_report`, which returns the *action* list — always
three or more entries — so the check would have blocked every adjudication.
Neither the review nor the implementation was careless; each followed a
different half of the plan.

**Resolution.** Renamed the §2 type to `BriefDecisionOption` in the plan,
matching the implementation. `--option`, `--compare-options`, and
`MOPT001`/`MOPT002` refer to `BriefDecisionOption`; `briefs options` computes
`BriefOption`. Doc-only change; no code moved.

**Lesson worth generalizing.** The plan was the sole registry of its own
vocabulary and nothing compared it to the code. `assets/mctl/diagnostics.toml`
plus `tests/mctl/test_diagnostics_registry.py` now do that for diagnostic
codes. Type names have no equivalent check.
