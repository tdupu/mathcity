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

There is also no *safe* inverse. `bd dolt stop` does exist (`bd dolt
start`/`stop`/`status`), but it is not the per-project lever it appears to be:
its only guard is a remote-host check (`beads/cmd/bd/dolt.go`, stop command),
which does not fire on 127.0.0.1. A rig's `.beads/dolt-server.port` here points
at 58506 — the gc-supervisor-managed process — while `bd dolt show` self-reports
"Mode: per-project". So `bd dolt stop` from a rig would likely signal the shared
server under the wrong lifecycle owner.

*(Amended 2026-08-18: an earlier revision of this entry claimed there was no
`bd dolt stop` at all, then briefly claimed it was a safe per-project lever.
Both were wrong. It exists and is not safe to use here.)*

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

## Q5 — Is the brief stack per-rig or city-wide? `paths.toml` and reality disagree

**Status:** **RESOLVED** (direction set; implementation deliberately deferred) ·
**Owner:** Taylor · **Raised:** 2026-08-19 · **Decided:** 2026-08-19

### Decision (Taylor, 2026-08-19)

**Storage is per-rig. Reporting is city-wide.**

> "The brief stack was originally a single stack but I think a better design is
> per rig and having the agents/application report on the city-wide status. From
> a user's perspective, I want all the briefs at the same time."

So `paths.toml`'s rig-relative declaration and `artifact_layout()`'s rig-relative
resolution are **correct as designed**. The live city-root cross-rig stack is the
drift, not the contract. Option (b) below wins.

The user-facing need that motivated the single stack — seeing every brief at
once — is satisfied at the **presentation** layer, not the storage layer: the
dashboard and the reporting skills aggregate across rigs. That decouples "where
a brief lives" from "what a human sees", which is the property the single-stack
design was really buying.

**On the pile lookup:**

> "I don't care how the pile look-up goes. I guess the briefs are supposed to be
> decision beads so it should be however beads are looked-up."

Bead identity is canonical. The artifact lookup should follow bead identity
rather than invent a second addressing scheme — which is also what B2.4/B2.8
already say (the bead store is canonical; files are cache).

### Deliberately NOT being implemented yet

> "If everything is working right now, I would file a separate issue on
> everything before uprooting."

Nothing is uprooted on this pass. The current state works: reads are correct,
adjudication works, and the artifact mismatch is contained behind honest
reporting (`artifact_trust`, `untrusted_diagnostics`). Migrating 101 city-root
briefs into per-rig trees is a separate, larger, riskier change and gets its own
issue.

**Interim contract stands unchanged:** `MBRF021` remains a mass false positive
and must not drive repair; `briefs create` still aborts with `MBRF035` rather
than materializing a tree.

### Consequent work, tracked separately

1. **Dashboard must aggregate city-wide.** It is currently `--rig`-scoped, which
   does not meet the stated need. This is the direct consequence of the decision
   and the most user-visible gap.
2. **Migration of the live city-root stack to per-rig trees**, plus reconciling
   `paths.toml`, the shuffler's `--brief-root` argument, and the pile filename
   convention with bead identity.

**Blocks:** the live-rig e2e slice remains held until (2) lands, since artifact
assertions against the current layout would prove nothing.

---

*Original analysis retained below for the evidence.*

**Prior status:** OPEN · **Blocked:** live-rig e2e (pink), and any mctl code that
trusts artifact state

**Observed.** `assets/brief-pipeline/paths.toml` declares, in its own header:

> Paths are RIG-RELATIVE (resolve against `<rig_root>`), matching the live pilot
> layout at `<rig_root>/.beads/briefs/` (hecke pilot: `<city-root>/hecke`).

`mctl_core/redundant_state.artifact_layout()` implements exactly that, resolving
every path through `_rig_relative(ctx.rig_root, ...)`.

**The declared layout does not exist.** Measured 2026-08-19:

| path | state |
|---|---|
| `<city-root>/.beads/briefs/stack` | **101 entries** |
| `<city-root>/gascity-packs/.beads/briefs/stack` | absent |
| `<city-root>/hecke/.beads/briefs/stack` | absent |
| `<city-root>/mathcity/.beads/briefs/stack` | absent |

Every rig-root brief tree is gone. The live stack is city-root-level and
**cross-rig** — it carries briefs from several rigs in one directory.

**Why this went unnoticed for a month.** The shuffler never reads `paths.toml`.
`assets/scripts/brief-stack-index.py` takes `--brief-root` as an explicit
**required** argument, so the caller supplies the city root and the declared
contract is bypassed entirely. mctl is the only component that reads the
contract and resolves it, which is why the drift surfaced the moment mctl
looked. This is not "mctl disagrees with the shuffler" — it is "the config
disagrees with reality, and only mctl was listening."

**The question.** Which is canonical?

- **(a) City-wide cross-rig** — matches the live 101-entry stack. Implies
  `paths.toml` is stale and should be rewritten city-relative, and that
  `artifact_layout()` should resolve against `ctx.city_root`. Also implies the
  stack is a single adjudication queue across rigs, which is arguably the point
  of a brief *stack*.
- **(b) Per-rig** — matches the declared contract and the original hecke pilot.
  Implies the live layout is drift to be repaired, and that 101 briefs need
  redistributing to their owning rigs.

The live evidence points hard at (a), and a cross-rig queue reads like an
intentional design change that was never written down. But (b) is what every
document says, so this cannot be settled by an implementer picking the one that
matches the filesystem.

**Consequences while it is open.**

- `scan_artifacts` reports `missing` for every artifact against the live city.
  Any e2e built on the current model would assert `missing`, pass, and prove
  nothing. pink is holding the live-rig e2e for this reason.
- Slice 5's `briefs create` writes redundant artifacts through the same
  resolver. Unguarded, it would have `mkdir -p`'d a **parallel shadow brief tree
  under each rig root**, diverging from the real stack with nothing downstream
  noticing until the two disagreed.

**Interim guard (implemented, Slice 5).** `briefs create` aborts with `MBRF035`,
naming the resolved path, when the brief root does not exist — rather than
creating it. One resolver is retained; no city-root fallback was added, and
`paths.toml` was not edited. That converts the open question into a visible
error instead of silent corruption, and both callers inherit the fix once the
root is decided.

**Live measurement, 2026-08-19 (city UP, supervisor running).** Running the
merged mctl against the real `gascity-packs` rig:

```
mctl briefs validate --all --rig gascity-packs
  70 briefs
  MBRF021 ("no redundant cache artifact") x 66
```

66 of 70 briefs report a missing artifact. The artifacts are not missing.

**And the root is only half of it — the filename convention is wrong too.**
mctl looks for `<brief_root>/.pile/<bead_id>.md`. The live pile holds 68 files
named `<NN>-<slug>-brief.md`, carrying the bead id in frontmatter:

```
$ ls <city-root>/.beads/briefs/.pile/ | head -2
19-mc-x6a-dead-target-router-beads-brief.md
20-migration-merged-gated-ungated-populations-brief.md

$ head -3 19-mc-x6a-dead-target-router-beads-brief.md
---
artifact: mc-x6a
```

So `scan_artifacts` would fail to find these files **even if it were pointed at
the correct root**. Resolving Q5 requires deciding the root *and* the lookup:
by filename, or by scanning frontmatter for `artifact:`.

**This makes the question urgent rather than academic.** `MBRF021` is a
B2.8 violation code — "canonical and redundant state disagree". Its documented
remedy is to repair the filesystem to match the bead store. Acting on the
current 66 hits would mean *creating* 66 artifacts that already exist, under
different names, in a different tree. Nothing should act on `MBRF021` until this
resolves.

**What resolving it looks like.** Decide (a) or (b); update `paths.toml` and
`artifact_layout()` together; keep them the single source of truth; and give the
shuffler a reason to consult the contract rather than take a root by argument,
or the same drift recurs.


## Q4 — Should the P1.14 pre-flight distinguish "the probe cannot run" from "the server is down"?

**Status:** OPEN (narrowed) · **Owner:** Taylor (mathcity side) ·
**Raised:** 2026-08-18 · **Substantially corrected 2026-08-18**

**This entry originally claimed the P1.14 pre-flight was broken and that ~18
skills were aborting on a healthy data plane. That was wrong.** Both the
evidence and the root cause below are retracted; what survives is a much smaller
question. The retraction is kept rather than deleted because the reasoning error
is the interesting part.

### What was actually observed, and why it misled

```
$ cd ~/repos/mathcity && gc dolt health >/dev/null 2>&1; echo $?
1                      <- "server unreachable"

$ cd ~/gt/mathcity && gc dolt health >/dev/null 2>&1; echo $?
2                      <- reachable, standing compaction quarantine
```

Same binary (`~/go/bin/gc`) both times. `gc dolt` is a **city-scoped command
pack** — `gc dolt --help` from `~/gt` prints *"Commands from the dolt import"*
and lists `health`, `status`, `compact`, `restart`, and the rest. Outside a Gas
City root the `dolt` parent is never registered, so `gc` exits 1, which is
exactly the code the contract reserves for "Dolt is down".

The original entry ran the probe from a non-city directory, saw exit 1, and
concluded the command pack was absent from the install. It is not absent. The
conclusion was an artifact of the working directory.

### Retracted claims

- ❌ *"The installed `gc` has no `dolt` subcommand at all."* It has one, inside a
  city root.
- ❌ *"That pack is not installed in this city."* It is installed.
- ❌ *"Roughly 18 call sites abort before doing any work."* None of them do.
- ❌ *"This is the issue #7/#8 bug in a new costume."* Those issues are fixed.

### What is actually true

`ae6e871 fix(mathcity): make Dolt pre-flight gates honor gc dolt health's exit
contract` already converted every gate to the three-valued `case`. Verified:

```
$ bash tests/dolt-preflight-exit-codes/smoke_test.sh
ok: 17 call sites, all exit-code-aware
ok: exit 0 -> proceeds silently
ok: exit 2 -> warns, names hecke/hq, points at gc dolt compact, proceeds
ok: exit 1 / 78 / 127 -> aborts with the P1.14 message
ALL DOLT-PREFLIGHT EXIT-CODE CHECKS PASSED
```

The contract works. The city's real exit code today is **2** — a standing
compaction quarantine on `hecke` (33d) and `hq` (36d) — and the gates correctly
warn and proceed rather than aborting.

### The question that remains

`template-fragments/dolt-preflight.md` already documents the cwd-dependence
under **Known limitation**, and scopes it out of #7/#8. So the open design
question is only this:

> Should a probe that *cannot run* produce the same abort, with the same
> remediation, as a server that is *unreachable*?

A skill invoked from outside a city root today prints *"Dolt is unreachable —
run `gc dolt status` / `gc dolt start`"*, which is false and unactionable; the
true remediation is *"cd into the city root"*. That is one extra branch in the
`*` case — detect the unknown-command shape and say so — but it is a change to
the canonical fragment plus 17 embedded copies, so it wants a decision, not a
drive-by edit.

**Not a blocker for anything.** Skills are invoked from the city root in normal
operation. This is a diagnosability improvement, not an outage.

### Related, still open

Issue **#8** is still OPEN while **#7** (same fix) is CLOSED. The mathcity-owned
half of #8 — *"mathcity discards the one signal upstream provides"* — is
satisfied by `ae6e871` and the smoke test. The upstream compaction race
(`gastownhall/gascity#3341`) and the standing 33-day quarantine are **not**
fixed and are not mathcity's to fix. Someone should decide whether #8 closes on
the mathcity half or stays open tracking the quarantine.

### What mctl does instead

mctl does not use this fragment. It TCP-connects to the endpoint named in
`.beads/dolt-server.port` and gates bead commands on that. That is a boolean
probe of the kind the fragment warns against, and it was written without
knowledge of the P1.14 contract. Because it probes the endpoint directly rather
than shelling out to `gc`, it is immune to the cwd problem above — but it also
cannot see a quarantine, which the canonical contract can. Reconciling the two
remains open: mctl should probably consume the canonical contract, and the
canonical contract should probably grow the fourth branch.


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
