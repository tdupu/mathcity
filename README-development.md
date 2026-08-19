# Development Guide

Parent: [README.md](./README.md)

This guide explains how mathcity development is governed by policies, specs,
briefs, and tests.

## Source Of Truth

| Surface | Purpose |
| --- | --- |
| [POLICY-POLICY.md](./POLICY-POLICY.md) | How policy domains, rule IDs, check skills, and amendment skills work. |
| [POLICY-formulas.md](./POLICY-formulas.md) | Rules for formula TOMLs and formula creation. |
| [POLICY-beads.md](./POLICY-beads.md) | Bead types, labels, research-bead lifecycle, and stale-bead handling. |
| [subdomains/dev/POLICY.md](./subdomains/dev/POLICY.md) | Pack portability, ownership boundaries, upstream changes, and development hygiene. |
| [subdomains/dev/POLICY-city.md](./subdomains/dev/POLICY-city.md) | Runtime city operations. |
| [subdomains/dev/POLICY-documentation.md](./subdomains/dev/POLICY-documentation.md) | Documentation quality, examples, setup, and navigation. |

Specs should explain behavior by citing current formulas, skills, orders, and
policy. If a spec contradicts source, source wins and the spec is fixed.

## Front Door

All ordinary work should enter through `mathcity.work`. It routes by shape to
briefed formulas such as `work-briefed`, `simple-work-briefed`,
`build-basic-briefed`, `planning-briefed`, and `smoke-test-briefed`.

Formula creation currently uses `formula-work` as a dispatch skill for
`formula-creator-math`. That is a known planned improvement: formula creation
should begin with a formula plan, then produce docs, tests, and the formula
brief as one lifecycle. Track that rework in #3.

## Issue And PR Handoffs

Upstream issue and PR text is prepared by mathcity formulas, then adjudicated
before anything is published:

| Surface | Purpose |
| --- | --- |
| `create-issue-briefed` | Drafts a template-complete issue body and files it as a decision brief. |
| `pr-pipeline-briefed` | Drafts a template-complete PR body and files it as a decision brief. |

Original upstream repositories:

- [Gas City](https://github.com/gastownhall/gascity)
- [Gas City packs](https://github.com/gastownhall/gascity-packs)
- [Beads](https://gastownhall.github.io/beads/)

## Tests

Current cheap tests:

```sh
bash scripts/run-local-tests.sh
```

### Mctl Context

Resolve an explicit local fixture context with:

```sh
python3 assets/scripts/mctl.py context --city tests/mctl/fixtures/city_root --rig mathcity --json
```

`mctl` reads `rigs.imports.mathcity.source` (or the matching default import)
from `city.toml`. It uses an explicit rig `db` value when present; otherwise,
the resolved rig ID is the database name.

Context resolution also probes the rig's Gas City data plane and reports
`city_active` / `city_endpoint`. A rig configured for Dolt server mode
(`.beads/dolt-server.port`) whose endpoint refuses a connection is reported as
`city_active: false`, and every `briefs`/`work` command then fails immediately
with `MCTL_CITY_NOT_ACTIVE` instead of blocking on a `bd` timeout. A rig with
no server port uses embedded Dolt; it reports `city_active: null` and is never
gated. `mctl context` always answers, so it stays usable for diagnosing a
down city.

All `briefs` and `work` commands render concise human output by default and
deterministic JSON under `--json`. Human output always keeps the diagnostics
and the trace id, since those are what an operator acts on.

### Mctl Brief Inspection

Read canonical brief beads and their redundant filesystem cache without
repairing any drift:

```sh
python3 assets/scripts/mctl.py briefs list --status open --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs show mc-abc --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs options mc-abc --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs doctor --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs doctor --brief mc-abc --city <city-root> --rig mathcity --json
```

From the MathCity source checkout, brief commands require both `--city` and
`--rig`. The bead store is canonical; pile, stack, decision TOML, and legacy
decisions-track files are reported as redundant artifacts and are never
rewritten by these read-only commands.

If a command inspects a matching legacy decisions-track row, or if that legacy
manifest cannot be parsed, the JSON `diagnostics` envelope includes
`MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED`. That blocker remains until the #38
decisions-track migration proof/canary has passed and the result is explicitly
authorized; historical migration marker files alone are not trusted proof.

### Mctl Brief Mutations

Decision mutations are dry-run first and bead-first. The canonical bead update
is applied before redundant decision TOML, stack index, event, or trace writes:

```sh
python3 assets/scripts/mctl.py briefs adjudicate mc-abc --verdict approve --reason "ready" --dry-run --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs adjudicate mc-abc --verdict approve --reason "ready" --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs defer mc-abc --reason "waiting on owner" --until 2026-08-20 --dry-run --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs defer mc-abc --reason "waiting on owner" --until 2026-08-20 --city <city-root> --rig mathcity --json
```

Mutation commands refuse to run without a reason, refuse to run when `briefs
doctor` reports `ERROR` or `FATAL`, and preserve the legacy
`MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED` guard from read-only inspection.

Adjudicate and defer carry an optimistic-concurrency guard: the status
observed at plan time is passed to `bd update --if-status`, so a brief that
another actor adjudicated in the meantime is not overwritten. `bd` writes
nothing and exits 13 in that case, which maps to `MCTL_BEAD_UPDATE_RACE_LOST`
— distinct from `MCTL_CANONICAL_BEAD_UPDATE_FAILED` so a lost race is not
mistaken for a crash, and so callers know retrying the same guard is futile.

### Mctl Brief Creation And Validation

Creation is bead-first: the canonical `type=decision` bead is written first,
and the redundant artifacts follow only once `bd` has accepted it.

```sh
python3 assets/scripts/mctl.py briefs create --title "Decide dispatch policy" --body-file /tmp/body.md --source mc-src --dry-run --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs create --title "Decide dispatch policy" --body-file /tmp/body.md --source mc-src --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs validate mc-abc --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py briefs validate --all --city <city-root> --rig mathcity --json
```

`create` writes exactly two redundant artifacts — the `.pile` markdown and the
decision TOML. It deliberately does **not** touch `stack/.index.jsonl`:
brief-system POLICY B2.10 makes brief-shuffle the single `.pile -> stack`
writer, and producers write only to the pile.

Input checks map to policy sections rather than restating them: `MBRF030`
(empty title, B1.1), `MBRF031` (empty body, B1.5), `MBRF032` (a label
requesting a side or bypass pile, B2.4), `MBRF033` (a label that is not a
usable `bd` token). `--source` is optional but recommended: without it the
plan carries `MBRF034`, because B2.1 makes a brief with no source link
malformed and every downstream mctl command refuses to act on one.

If the resolved brief root does not exist, `create` aborts with `MBRF035` and
names the path it resolved, rather than creating it. `artifact_layout()`
remains the single resolver — the guard only refuses to write through a
resolution it could not confirm. This matters because
`assets/brief-pipeline/paths.toml` declares rig-relative artifact paths while
the live city keeps its brief tree at the city root, and the shuffler never
reads `paths.toml` at all (it takes `--brief-root` explicitly). Reading
through a missing root is harmless — it reports `missing` — but writing
through one would silently build a parallel shadow brief tree that nothing
downstream would notice. Which root is correct is an open policy question,
not something creation may decide.

If a redundant write fails after the bead was created, every file the
operation had brought into existence is removed and `MCTL_REDUNDANT_CACHE_ROLLED_BACK`
is reported with a non-zero exit. The bead survives — it is canonical — and a
half-written cache would read as a real invariant violation to `briefs doctor`.

`validate` composes `briefs doctor` with stricter per-brief invariants:
`MBRF020` when the decision cache disagrees with the bead, `MBRF021` when a
canonical brief has no redundant artifact to cross-check at all. It is
read-only and never repairs what it reports. `--all` reads the bead store
exactly once and threads the snapshot, so its `bd` call count does not grow
with the number of briefs (`tests/mctl/test_bd_invocation_count.py`).

### Mctl Work Controls

Inspect brief-backed work and dispatch provenance from the same explicit city
context:

```sh
python3 assets/scripts/mctl.py work ready --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py work status mc-abc --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py work provenance mc-abc --city <city-root> --rig mathcity --json
python3 assets/scripts/mctl.py work dispatch mc-abc --dry-run --city <city-root> --rig mathcity --json
```

`work ready` is derived from canonical decision beads and excludes blocked,
non-approving, already-dispatched, or invalid-provenance items. Dispatch uses
the same effect-plan model as brief mutation commands.

mctl distinguishes two planes, because they fail independently. The **data
plane** is the managed Dolt server (`.beads/dolt-server.port`); bead reads and
writes need only that, and an unreachable endpoint gives `MCTL_CITY_NOT_ACTIVE`.
The **control plane** is the Gas City supervisor; only dispatch needs it.
`gc stop` brings down the supervisor but leaves Dolt running under its own
watchdog (`gc __gc-managed-dolt-scope-watchdog`), so reads keep working while
there is nothing to route a sling to — verified live, supervisor pid=0 with
dolt still LISTENing on 58506. Armed dispatch therefore probes the supervisor
too and refuses with `MCTL_CONTROL_PLANE_NOT_ACTIVE` rather than shelling out
to a `gc sling` that has nowhere to go.

Live dispatch is armed only by `MCTL_ENABLE_LIVE_DISPATCH=1`, which is
deliberately independent of `MCTL_BEADS_FIXTURE`. Unarmed, `work dispatch`
returns the dry-run payload and writes nothing — no provenance, no event or
trace rows, no readiness change. Armed, it actually runs the `gc sling`
command and records provenance only after a zero exit; a failed sling raises
`MWRK_DISPATCH_COMMAND_FAILED` and records nothing.

This matters because provenance is what flips readiness to `dispatched` and
blocks every later attempt via `MWRK_ALREADY_DISPATCHED`. Writing it without
slinging records a handoff that never happened.

Every bead read is a full `bd list` subprocess, so core functions that already
hold a bead snapshot pass it down (`doctor_briefs(ctx, brief_id, beads)`)
rather than re-reading per brief. `work ready` reads beads once for the whole
rig; re-introducing a per-brief read makes the command scale with rig size and
is caught by `tests/mctl/test_bd_invocation_count.py`.

Redundant cache writes go through `_atomic_write` (same-directory temp file
plus `os.replace`), so an interrupted mutation leaves the previous file
intact rather than a truncated one. Decision TOML is parsed with `tomllib`
and re-emitted with typed values; the previous line-splitting writer would
rewrite any line inside a multi-line string that looked like the key being
updated, silently losing the verdict.

`stack/.index.jsonl` has a second writer — the shuffler drains it — so mctl
takes an `flock` on `<stack>/.manifest.lock` — the SAME lock file
`brief-shuffle-fast-drain.py::append_index` uses — across the whole
read-modify-write. `flock` only serializes writers holding the same lock
path, so a lock of mctl's own would have serialized mctl against mctl and
left the shuffler race open while looking handled.
**Open architecture question:** `formulas/brief-prep.toml` and the fast-drain
plan both describe the shuffler as the *single* writer of that file. The lock
makes the current two-writer reality safe, but the boundary in those two
documents still needs to be either amended deliberately or replaced by
routing mctl's updates through the shuffler.

Dispatch enforces plan §4's safety invariants: `MWRK001` blocks a source bead
that already has an active assignee, `MWRK002` blocks when an open child
workflow (`gc.root_bead_id`) already exists for the same source, and
`MWRK003` fires when the sling exits zero without actually claiming the bead
— in which case nothing is recorded, since phantom provenance would block
every retry. Readiness checks were moved to `MWRK010`+ so they stop squatting
on the reserved safety range.

Briefs can offer decision options, enumerated in the markdown cache as list
items under an Options section:

```markdown
## §4 — Options

- **(A) Do it now.** *(recommended)* Cheapest path.
- **(B) Defer it.** Costs a cycle.
```

Adjudicating a brief that offers more than one requires `--option`, or it
fails closed with `MOPT001`; an option the brief does not offer fails with
`MOPT002`. Briefs with no Options section, one option, or no markdown cache
at all are unaffected — the bead is canonical, so a missing cache never
blocks a verdict. Note the plan names both this and the enabled-action list
`BriefOption`; in code they are `BriefDecisionOption` and `BriefOption`.

### Mctl Traces

Every mutation writes two append-only rows keyed by one `trace_id`:
`planned` before anything is mutated, then exactly one of `applied` (with
the real `actual_effects`) or `aborted` (with the blocking diagnostics). A
failed or crashed mutation therefore still leaves evidence. Fold them with:

```sh
python3 assets/scripts/mctl.py trace show <trace-id> --city <city-root> --rig mathcity --json
```

`trace show` reads local JSONL only, so it stays available when the city is
down. Both mutation paths write through `mctl_core/trace.py` so they cannot
drift apart again.

### Mctl Diagnostic Codes

`assets/mctl/diagnostics.toml` is the single source of truth for stable
diagnostic codes (code, severity, meaning, policy ref, module).
`tests/mctl/test_diagnostics_registry.py` asserts every code `mctl_core`
emits is registered and every registered code is still reachable, so the
plan and the code cannot drift apart silently the way `MBRF010`-`MBRF013`
(code-only) and `MOPT001` (plan-only) did.

### Mctl Bead-Backed Tests

Most `tests/mctl` files inject `MCTL_BEADS_FIXTURE`, which bypasses the `bd`
adapter and reads static JSONL. Two suites deliberately do not:

- `tests/mctl/test_real_bead_store.py` builds an isolated embedded-Dolt store
  with `bd init` and drives mctl against real beads, including the canonical
  `bd update` write path. It never touches a production rig, and skips when
  `bd` is not installed.
- `tests/mctl/test_bd_invocation_count.py` puts a counting `bd` shim on `PATH`
  to bound how many times a command shells out.

`bd` and `gc` are external contracts mctl does not own.
`tests/mctl/test_external_command_contracts.py` pins the argv mctl builds
and checks every long flag in it against the flags the installed `bd` and
`gc` actually advertise, so a rename upstream fails the suite instead of
silently producing a broken command.

`bd` subprocess timeout defaults to 30s and is overridable with
`MCTL_BD_TIMEOUT_SECONDS`. It must stay clear of the ~1-5s a full read of a
large rig costs, since reads are slowest exactly when the data plane is
degraded and these commands are most needed.

When adding bead fixtures, prefer `related` dependencies between a brief and
its source bead — that is what live rigs use, and real `bd` refuses to close a
brief that a `blocks` dependency still blocks.

Use `testing-work` and `smoke-test-briefed` for lightweight generated smoke
tests. Use `test-execution-request` before risky, slow, or costly test
execution.

## Documentation Workflow

Run `improve-documentation` for feature, formula, skill, policy, setup, or
workflow changes. Then run `check-documentation-policy` and compare the result
against the requested documentation changes.

New features need examples and tests. Existing gaps can be tracked as backlog,
but they should not be presented as complete.

## Planned Development Surfaces

| Surface | Tracker | Current status |
| --- | --- | --- |
| `mathcity doctor` | #1 | Planned tiered health/test/documentation report. |
| `create-test-briefed` | #2 | Planned test-design workflow for example-driven certification. |
| `formula-work` lifecycle rework | #3 | Planned upgrade from dispatch wrapper to plan -> formula -> docs -> tests -> brief lifecycle. |
