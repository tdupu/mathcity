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

### Mctl Entry Point

`bin/mctl` is the only supported entry point for the control CLI. It is a thin
`sh` shim that resolves its own path through any symlink chain, derives the repo
root from its own location, and `exec`s `python3 assets/scripts/mctl.py "$@"`.

Do not invoke `assets/scripts/mctl.py` directly. The shim owns repo-root
resolution and `mctl_core/context.py` owns city/rig discovery; calling the
script by path bypasses the first and makes the invocation depend on the
caller's working directory. The shim deliberately does not `cd` (the working
directory is load-bearing for city discovery), does not default `--city` or
`--rig`, and does not pin an interpreter — it uses `python3` from `PATH`, which
must be 3.11 or newer for `tomllib`. See [LAYOUT.md](./LAYOUT.md) for the
`bin/` convention and `tests/mctl/test_bin_mctl_shim.py` for the contract that
holds the shim and the script to identical argv, stdout, stderr, and exit code.

Subcommands: `context`, `briefs`, `trace`, `mcp`, `dashboard`, `work`. Every
leaf except `mcp serve` and `dashboard serve` accepts `--city`, `--rig`, and
`--json`; the mutating leaves (`briefs adjudicate`, `briefs defer`,
`briefs create`, `work dispatch`) also accept `--dry-run`.

### Mctl Context

Resolve an explicit local fixture context with:

```sh
bin/mctl context --city tests/mctl/fixtures/city_root --rig mathcity --json
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
bin/mctl briefs list --status open --city <city-root> --rig mathcity --json
bin/mctl briefs show mc-abc --city <city-root> --rig mathcity --json
bin/mctl briefs options mc-abc --city <city-root> --rig mathcity --json
bin/mctl briefs doctor --city <city-root> --rig mathcity --json
bin/mctl briefs doctor --brief mc-abc --city <city-root> --rig mathcity --json
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
bin/mctl briefs adjudicate mc-abc --verdict approve --reason "ready" --dry-run --city <city-root> --rig mathcity --json
bin/mctl briefs adjudicate mc-abc --verdict approve --reason "ready" --city <city-root> --rig mathcity --json
bin/mctl briefs defer mc-abc --reason "waiting on owner" --until 2026-08-20 --dry-run --city <city-root> --rig mathcity --json
bin/mctl briefs defer mc-abc --reason "waiting on owner" --until 2026-08-20 --city <city-root> --rig mathcity --json
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
bin/mctl briefs create --title "Decide dispatch policy" --body-file /tmp/body.md --source mc-src --dry-run --city <city-root> --rig mathcity --json
bin/mctl briefs create --title "Decide dispatch policy" --body-file /tmp/body.md --source mc-src --city <city-root> --rig mathcity --json
bin/mctl briefs validate mc-abc --city <city-root> --rig mathcity --json
bin/mctl briefs validate --all --city <city-root> --rig mathcity --json
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
bin/mctl work ready --city <city-root> --rig mathcity --json
bin/mctl work status mc-abc --city <city-root> --rig mathcity --json
bin/mctl work provenance mc-abc --city <city-root> --rig mathcity --json
bin/mctl work dispatch mc-abc --dry-run --city <city-root> --rig mathcity --json
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

**Known defect — dispatch does not scope `artifact_root` per bead.**
`_formula_invocation` passes `artifact_root=<rig-root>/.beads/briefs`, a shared
rig-level root, while `formulas/work-briefed.toml` documents the var as *"For
builds, scope per bead (for example `<rig-root>/.gc-builds/<bead>`)"* and hands
it straight to `build-basic-briefed` on the FULL_CONTINUE route. Two concurrent
FULL_CONTINUE dispatches in one rig therefore share a stage-artifact root — the
gsp-1bmxuz hazard, inside the typed command that was meant to remove it. Found
while wiring the skills in Slice 7 (`tests/artifact-root-scoping/smoke_test.sh`
is what caught the wrong assumption); the skills document it and say to
serialize approvals on one rig. Fixing it belongs here, in `mctl_core`.

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
bin/mctl trace show <trace-id> --city <city-root> --rig mathcity --json
```

`trace show` reads local JSONL only, so it stays available when the city is
down. Both mutation paths write through `mctl_core/trace.py` so they cannot
drift apart again.

### Mctl MCP Server

The MCP server is the second adapter over the same core the CLI uses. It
never shells out to `bin/mctl`; both front ends call the same `context.py` /
`briefs.py` / `work.py` / `effects.py` / `trace.py` functions, so there is
one set of semantics and one mutation path.

Start it over stdio:

```sh
bin/mctl mcp serve --city <city-root> --rig mathcity
bin/mctl mcp serve --city <city-root> --rig mathcity --client-class internal
```

The transport is newline-delimited JSON-RPC 2.0 (`initialize`, `ping`,
`tools/list`, `tools/call`) implemented with the standard library only — the
repository declares no Python dependencies, so an installed-but-undeclared
`mcp` package would make the suite depend on the developer's machine. Each
tool advertises an `inputSchema` and an `outputSchema` and returns
`structuredContent`.

Fifteen typed domain tools are registered:

| Group | Tools |
| --- | --- |
| context | `context_resolve` |
| briefs (read) | `briefs_list`, `briefs_show`, `briefs_options`, `briefs_doctor`, `briefs_validate` |
| briefs (mutating) | `briefs_relay_adjudication`, `briefs_defer`, `briefs_create` |
| work | `work_ready`, `work_status`, `work_provenance`, `work_dispatch` |
| trace | `trace_show`, `trace_replay_preview` |

**There is no generic command-execution tool** — no `shell`, `gc`, `bd`,
`mctl`, `exec`, or `run_command` passthrough, and no tool accepts a raw
`command` or `argv` field. That is asserted by `tests/mctl/test_mcp_server.py`,
by the schema snapshot, and by the harness, so it is checked rather than
trusted.

Mutating tools take `dry_run`, which **defaults to `true`**: omitting it
previews an `EffectPlan` and writes nothing. Pass `dry_run: false` to apply.
Applied mutations use the same phased trace helper as the CLI.

Arguments are validated against the declared input schema *before* any core
function runs. A violation is a JSON-RPC `-32602` whose `data` carries an
`MCTL_MCP_INVALID_ARGUMENTS` diagnostic and a `schema_errors` array of
`{path, keyword, expected, actual, message}` — never a traceback, never a
prose string. An unexpected exception inside a handler becomes a typed
`MCTL_MCP_INTERNAL_ERROR` for the same reason.

#### Rollout gate — current state

Per the plan's rollout controls, MCP tools stay disabled from external
clients until the surface is proven. As shipped:

| Client class | `MCTL_MCP_ENABLE_EXTERNAL_TOOLS` | Tools visible |
| --- | --- | --- |
| `external` (**default**) | unset | **none** |
| `external` | `1` / `true` / `yes` | the 11 read-only tools |
| `internal` (`--client-class internal`) | any | all 15 |

Mutating tools are `external_ready = false` and stay internal-only whatever
the environment says. `--client-class` defaults to `external`, and an
unrecognised value falls back to `external`, so a typo cannot arm a client
class. `MCTL_MCP_CLIENT_CLASS` overrides the flag. A blocked call returns
`MCTL_MCP_TOOL_DISABLED`.

#### Artifact state is reported as untrustworthy while Q5 is open

`subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md` Q5 is unresolved: mctl
resolves the brief root rig-root-relative while the live stack is
city-root-level, and looks up `<root>/.pile/<bead_id>.md` while real pile
files are named `<NN>-<slug>-brief.md` and carry the bead id in an
`artifact:` frontmatter key. Live consequence: 66 of 70 briefs falsely report
`MBRF021`.

Slice 6 does **not** fix Q5 — the per-rig-versus-city-wide question is a
pipeline policy decision — but it refuses to launder the resulting state
through a typed API. Every artifact-bearing response carries a required
`artifact_trust` object (`trusted`, `reason`, `open_question`, `reference`,
`resolved_brief_root`, `resolved_pile`, `withheld_codes`). When it is not
trusted:

- artifacts the core read as `missing` are reported with `state:
  "unverified"`, and the raw reading is preserved in
  `state_reported_by_core`;
- `MBRF021` moves out of `diagnostics` into `untrusted_diagnostics`, so
  nothing downstream treats it as actionable;
- a `MCTL_MCP_ARTIFACT_STATE_UNTRUSTED` WARN is added naming Q5.

No path resolver was changed, no city-root fallback was added, and
`paths.toml` was not edited.

#### MCP client harness

Slice 6 ships a client with the server, because a server nothing calls cannot
be demonstrated:

```sh
python3 assets/scripts/mctl_mcp_harness.py --city <city-root> --rig mathcity
python3 assets/scripts/mctl_mcp_harness.py --city <city-root> --rig mathcity --json
```

It launches a real `mctl mcp serve` subprocess and speaks the real stdio
transport, then runs six checks: `connect`, `tools_list`,
`typed_read_round_trip` (validated against the `outputSchema` the server
*transmitted*, not one compiled into the harness), `typed_schema_error`,
`no_passthrough_tool`, and `rollout_gate`. It exits non-zero if any check
fails, and `--expect-tool <name>` proves it can fail.

The harness runs in CI as `tests/mctl/test_mcp_client_harness.py`, not only
by hand. `tests/mctl/test_mcp_schema_snapshots.py` snapshots every tool
schema to `tests/mctl/fixtures/mcp_tool_schemas.json`; regenerate
deliberately with `MCTL_UPDATE_MCP_SNAPSHOT=1` and read the diff as a
client-compatibility review.

### Mctl Skill Audit

The skills are the top consumer of `mctl`, and they are prompt text executed as
shell — so they call **`bin/mctl`**, never the MCP server. The MCP surface is
for typed programmatic clients (the dashboard is one) and its rollout gate
defaults external clients to zero tools; a bash block is the wrong caller.

`subdomains/dev/docs/plans/mcp/SKILL-IMPACT-REGISTER.md` is the audit record.
Its "Final Dispositions" table classifies every audited skill as
`replace-with-mctl`, `wrap-with-mctl`, `no-change`, or `blocked-by-policy`, and
every `no-change` row cites the plan §2 source-of-truth boundary that makes it
legitimate (`BeadStoreAdapter` for canonical state, `BriefCacheAdapter` for
derived artifacts).

Run the audit in this order:

```sh
# 1. The executable gate. Parts 4-9 check the wiring, the trace ids, the
#    absence of direct cache writes, register/skill agreement, the no-change
#    reasons, and that nothing branches on the untrusted diagnostic codes.
sh tests/mctl-shim-callsite/smoke_test.sh

# 2. Which skills name mctl at all, and how often. Before Slice 7 exactly one
#    did; a skill that claims a wrap disposition and scores 0 here has not been
#    refactored.
grep -rc 'bin/mctl' skills/*/SKILL.md subdomains/*/skills/*/SKILL.md \
  | grep -v ':0$' | sort -t: -k2 -rn

# 3. Remaining direct state manipulation. Every hit is either migrated to mctl
#    or recorded in the register with a no-change / blocked-by-policy reason.
grep -rnE 'bd close|bd defer|bd update|gc sling|\.index\.jsonl|decisions-track|sed -i' \
  skills subdomains --include=SKILL.md

# 4. The retired loose surfaces named by the register's post-implementation
#    checklist.
grep -rnE 'gc dolt health|brief-record-decision|build-basic-briefed' \
  skills subdomains --include=SKILL.md

# 5. The typed core itself.
python3 -m pytest tests/mctl
bash scripts/run-local-tests.sh
```

Step 3 is the one that matters and the one that will keep producing hits: two
skills (`refine-bead-manifest`, `decisions-to-briefs`) still write the legacy
decisions-track tree, deliberately, because that inventory is #38's lane and
the plan holds bulk migration until proof 5 is green. Do not "clean them up" —
check the register row first.

Step 4 is expected to keep hitting `gc dolt health`: the P1.14 Dolt pre-flight
is a separate contract, guarded by `tests/dolt-preflight-exit-codes/smoke_test.sh`,
which fails if any call site is unclassified. **Do not add, remove, or edit a
pre-flight block while doing mctl work** — the two audits are independent.

Adding a new wired skill means three edits that must land together, or the gate
fails:

1. copy the call-site block from `template-fragments/mctl-entry-point.md` into
   the skill;
2. add its row to `WIRED` in `tests/mctl-shim-callsite/smoke_test.sh`, choosing
   `mutation` (must emit an `MCTL-TRACE: <id>` line) or `read`;
3. add its row to the register's Final Dispositions table.

#### Three diagnostic codes no skill may branch on

`MBRF021`, `MBRF004`, and `MBRF005` are untrustworthy signal today, and part 9
of the smoke test enforces that no skill branches on them:

- **`MBRF021`** is a mass false positive — 66 of 70 briefs in one rig report a
  missing redundant artifact that exists under a different name in a different
  tree (issue #58, `OPEN-DESIGN-QUESTIONS.md` Q5). Its documented remedy would
  create 66 duplicates; `mctl_core/mcp_server.py` already moves it to
  `untrusted_diagnostics`.
- **`MBRF004` / `MBRF005`** are instrumentation under review. `malformed` means
  *closed with no verdict field*, not damaged: the verdicts are in
  `close_reason`/`notes`, which the reader does not consult, and ~39 of the 74
  "malformed" beads were never briefs. See
  `subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md`.

**`MBRF004` does NOT gate `adjudicate` / `defer` / `dispatch`.** Corrected
2026-08-27; the previous text here asserted the opposite and was stale. Read the
source, not the prose: `mctl_core/briefs.py:1652` emits it at **`Severity.WARN`**,
and `_blocking_diagnostic` (`briefs.py:2124`) selects only `ERROR`/`FATAL`, so
`effects.py::_blocking_preconditions` never blocks on it. #137 made the downgrade;
this paragraph did not follow.

Measured 2026-08-27 across all 18 registered rigs: `MBRF004` fires on **149
distinct brief beads** and blocks **none** of them. The stale "146 of 185 live
briefs, 88 of them `pending`" figure came from before the downgrade and should not
be repeated. Live check on `mc-ba376` — which raises `MBRF004` — returns
`adjudicate: enabled=true, disabled_reason=null`; only `dispatch-work` is disabled,
on `MBRF011` ("no approving verdict for dispatch"), which is the correct gate for a
brief nobody has approved yet.

**Treating `MBRF004` as a filter is a live failure mode, not a hypothetical.** A
session that drops `MBRF004`-raising briefs from the queue empties it and concludes
there is nothing to adjudicate; on 2026-08-27 there were **17** adjudicable briefs
across 4 rigs at the moment that conclusion was drawn. Skills report the diagnostic
verbatim and do not branch on it — including not branching on it to *exclude*.

### Mctl Operator Dashboard

The dashboard is the operator surface over the same core, and a **client of
the MCP tools** rather than a third adapter: it launches its own
`mctl mcp serve` subprocess and every fact on every page arrives through
`tools/call`. It parses no bead store and reads no brief file.

There was no dashboard application in this repository before this slice, and
none was adopted: `gc dashboard` is upstream Gas City (and `ONBOARDING.md`
records it as broken), and the `127.0.0.1:8372` runs view named in
`subdomains/brief-system/README.md` belongs to the gascity supervisor. The
dashboard is therefore stdlib `http.server` plus server-rendered HTML, for the
same reason Slice 6 declined the installed `mcp` SDK: this repository declares
no Python dependencies, so anything needing `pip install` or `npm install`
would make the suite depend on one developer's machine. No build step, no
client-side framework, and no external bundle.

Every screen, every sort, every filter and every verdict works with JavaScript
disabled: navigation and data state live in the query string, sortable headings
are links, the column picker is a GET form, disclosure is `<details>`, and
mutations are ordinary form posts through `/preview` and `/apply`. JavaScript
is layered on top for four affordances that cannot be expressed as a link or a
form — the `j`/`k` row cursor, drag-to-reorder on the priority list, live
score-weight sliders, and locally saved verdict drafts — and each degrades to a
working no-JS path. All of it lives in `mctl_dashboard/assets.py`, in one file,
so a reviewer can read the whole of it at once.

Start it:

```sh
bin/mctl dashboard serve --city <city-root> --rig <rig>
bin/mctl dashboard serve --city <city-root> --rig <rig> --host 127.0.0.1 --port 8471
```

It prints the bound URL on stderr and defaults to `http://127.0.0.1:8471`.
`--host` defaults to loopback and is deliberately not given an
all-interfaces default; see the rollout-gate note below for why that matters.

Smoke test:

```sh
python3 -m pytest tests/mctl/test_dashboard_views.py \
  tests/mctl/test_dashboard_mutation_safety.py \
  tests/mctl/test_dashboard_transport.py
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8471/
```

`test_dashboard_transport.py` is the end-to-end smoke: it runs the shipped
path -- a real `mctl mcp serve` subprocess over stdio behind a real
`http.server` -- and drives preview-then-apply with `urllib`.

| Route | Tools it calls |
| --- | --- |
| `GET /` | `context_resolve`, `briefs_list` |
| `GET /briefs` | `context_resolve`, `briefs_list` |
| `GET /briefs/<id>` | `context_resolve`, `briefs_show`, `briefs_options`, `briefs_doctor` |
| `GET /diagnostics` | `context_resolve`, `briefs_validate` |
| `GET /validate` | `context_resolve`, `briefs_validate` |
| `GET /work` | `context_resolve`, `work_ready` |
| `GET /trace` | `context_resolve`, `trace_show`, `trace_replay_preview` |
| `POST /preview` | `briefs_relay_adjudication` / `briefs_defer` / `work_dispatch` / `briefs_create`, always `dry_run: true` |
| `POST /apply` | the same tool with `dry_run: false`, only after the freshness check |

`POST /preview` and `POST /apply` are the only routes that can write anything.
There is no route that accepts a command, and `mctl_dashboard.client`
allowlists the fifteen typed tools by name and refuses anything else before it
reaches the wire. `tests/mctl/test_dashboard_views.py` cross-checks that
allowlist against `mcp_server.TOOLS_BY_NAME` and `FORBIDDEN_TOOL_NAMES`, and
asserts that rendering a view calls no mutating tool and writes nothing under
the rig -- there is no repair-on-read anywhere in the dashboard, and no
"fix it" affordance for any diagnostic.

#### Rollout gate: the dashboard runs as an `internal` client

Slice 6 defaults external clients to **zero tools**, and mutating tools stay
`external_ready = false` however the environment is set. So an `external`
dashboard could not list a brief, let alone adjudicate one. The dashboard
spawns its MCP server with `--client-class internal` and therefore sees all
fifteen tools including the mutating four (`briefs_relay_adjudication`, `briefs_defer`,
`briefs_create`, `work_dispatch`). That is the only class in which it
can do its job, and it is why the bind address matters: the safety story is
"loopback, plus a preview-first confirm path", not the rollout gate. Do not
put this on a routable interface.

#### Mutation is preview-first, and the preview must still be true

The confirm control is rendered **only** on a preview page, never on a brief
page, so there is no apply button to come back to. Confirming re-resolves the
context, re-reads the target bead, and re-plans, then compares three
fingerprints against the ones recorded when the preview was taken:

| Fingerprint | Catches |
| --- | --- |
| context | the city registry being re-pointed under a running dashboard |
| target | the brief bead itself moving -- status, title, labels, timestamps |
| plan | everything else, e.g. a redundant cache file appearing or vanishing |

If any differs, **nothing is applied**: the confirm returns `409` with
`MCTL_DASH_PREVIEW_STALE` naming which component moved, and a *fresh* preview
of the current state replaces the stale one. Tokens are single use and are
consumed by the first confirm attempt, so a resubmitted form cannot apply
twice and a stale token cannot be retried. The plan digest redacts per-call
volatile fields (`trace_id`, `mctl_trace_id`, `adjudicated_at`,
`deferred_at`) -- otherwise every preview would be stale the instant it was
taken and the guard would become noise an operator clicks through.

#### Three diagnostic codes the dashboard refuses to make actionable

`MBRF021`, `MBRF004`, and `MBRF005` are shown in full, with their codes, and
kept out of every actionable count. Each carries the document that owns the
open question, and none has a repair control:

- **`MBRF021`** -- mass false positive, 66 of 70 briefs in one rig, cause is
  open question Q5 (`subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md`). Slice 6
  already moves it into `untrusted_diagnostics`; the dashboard renders that
  array in its own `Under review` panel rather than flattening it back in.
- **`MBRF004`/`MBRF005`** -- instrumentation under review per
  `subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md`. `malformed`
  means *closed with no verdict field*, not damaged: the verdicts are mostly
  present in `close_reason` and `notes`, which the verdict reader does not
  consult, and roughly 39 of the 74 are git-operation receipts that were never
  briefs. The decision-queue badge carries that caveat inline; a bare
  "74 malformed" count would be a defect.

Every response that reports artifact state also renders its `artifact_trust`
verdict -- **both ways**, so "trusted" is distinguishable from "this page
forgot to say". When it is false the panel names the open question and the
reference, and artifacts the core read as `missing` are shown as `unverified`
with the raw core reading preserved beside them.

Severity gets colour and a badge; the code always renders in its own
`diagnostic-code` element beside it. `MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS`
names the code that actually blocked it only in `facts`, so the dashboard
lifts that out and additionally renders the brief's own diagnostics on the
blocked page -- "blocked by ERROR diagnostics" without saying which is exactly
the friendly-message-instead-of-a-code failure this surface must not make.

Verified in a browser at 1280x800 and 375x812: the layout collapses to a
single column at the 720px breakpoint, the page never scrolls horizontally,
and wide tables scroll inside their own container.

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
