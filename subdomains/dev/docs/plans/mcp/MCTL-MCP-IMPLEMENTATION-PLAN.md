# MathCity mctl MCP Hardening Implementation Plan

Parent: [Dev README](../../../README.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a shared MathCity command core, `mctl` CLI, typed MCP server, and later dashboard so brief and work operations stop depending on loose prompt-skill command chains.

**Architecture:** Put all domain behavior in a Python shared core with typed adapters around `gc`, `bd`, brief cache files, policy indexes, and traces. Expose the core first through `mctl`, then through MCP tools, then through a dashboard service with no duplicate state parsing.

**Tech Stack:** Python 3.11+ standard library (`argparse`, `dataclasses`, `enum`, `json`, `subprocess`, `tomllib`, `uuid`, `pathlib`), `pytest`, shell smoke tests, existing Gas City commands (`gc`, `bd`), existing TOML/JSONL assets.

Related plan: [Brief Shuffle Fast Drain](./BRIEF-SHUFFLE-FAST-DRAIN-PLAN-2026-08-16.md). That plan owns the immediate deterministic `.pile -> stack` cache-drain fix; this plan treats those cache artifacts as derived state to inspect, validate, and expose through CLI/MCP/dashboard surfaces.

## Global Constraints

- The source repository is `<repo-root>`; implementation work happens there, not in deprecated `gascity-packs/mathcity`.
- Before implementation, fetch `origin` and confirm whether the branch is behind `origin/main`; this work depends on recently changing brief-system behavior.
- The CLI name is `mctl`.
- `mctl` is a MathCity domain tool, not a generic shell, `gc`, or `bd` wrapper.
- Build a shared MathCity core first, CLI first, MCP second, dashboard later.
- Runtime scope comes from a Gas City city/rig context, not from the pack source checkout.
- Running ordinary brief or work commands from `<repo-root>` must hard-error unless an explicit registered runtime rig context is supplied.
- Plain commands operate on exactly one resolved rig.
- Cross-rig reads require an explicit option such as `--all-rigs`.
- Cross-rig mutations are forbidden until a command-specific batch mode is designed and reviewed.
- The bead store is the canonical source of truth for brief state.
- A brief is a `bd type=decision` bead; the brief bead is the decision bead.
- Markdown files, frontmatter, pile, stack, indexes, presentation files, archives, decision TOML files, and legacy `.beads/decisions-track` rows are cache, redundancy, migration input, or audit history.
- Read commands must not silently repair contradictions.
- Mutating commands must fail closed when invariant checks fail.
- Severity classes are exactly `INFO`, `WARN`, `ERROR`, and `FATAL`.
- Structured diagnostics include severity, stable code, message, city path, rig name/path, bead id or brief slug when available, data location, policy reference, implementation provenance, trace id, and suggested next command.
- Every top-level CLI command and MCP tool call receives a `trace_id`.
- Mutating commands are factored around an internal `EffectPlan`; CLI mutations may apply directly, while tests, MCP approval review, and dashboard confirmation can preview effects.
- MCP tools are typed domain tools. Do not expose `run_shell`, `run_gc`, `run_bd`, or `run_mctl_command(command: string)`.
- `#38` blocks or changes commands that import, list, or reason about legacy `.beads/decisions-track` rows. Until the proof/canary is green and authorized, legacy rows are read as migration input only.
- Do not bulk-migrate live decisions-track data in this implementation plan.
- Tests must not mutate live production beads unless a specific canary and rollback/audit procedure is approved.
- MathCity commits must not contain `Co-Authored-By` trailers.

---

## 1. Dream End-State

The dream system has one typed domain core with four front ends:

1. `mctl`, the human/operator CLI.
2. MCP tools, for assistant and app integrations.
3. A dashboard service, for visual brief review and controlled adjudication.
4. Thin skills, retained only where human orientation still has value.

The operator can run:

```bash
mctl context
mctl briefs list --status pending
mctl briefs show gsp-71p9fz-approach-a-blast-radius --compare-options
mctl briefs doctor
mctl briefs adjudicate gsp-71p9fz-approach-a-blast-radius --verdict revise --reason "reduce blast radius"
mctl work status mc-3ig
mctl work dispatch mc-3ig
mctl trace show 018f1f39-6ef2-7d8d-8ad2-f662d9058167
```

Every command is context-aware and produces either concise human output or structured JSON with diagnostics. A bad runtime context, a stale stack row, a missing brief bead, a missing source dependency, an ambiguous option verdict, or a deferred brief inside its defer window blocks output or mutation with a stable error code.

The dashboard is not a second parser. It shows the same `BriefRecord`, `BriefOption`, `DoctorReport`, `EffectPlan`, and `TraceRecord` objects as the CLI and MCP server. It can save adjudication drafts, show policy references inline, and submit verdicts through the same core.

## 2. Domain Model And Source-Of-Truth Model

### Canonical Objects

The shared core exposes these dataclasses:

```python
class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"

@dataclass(frozen=True)
class Diagnostic:
    severity: Severity
    code: str
    message: str
    trace_id: str
    city_path: str | None = None
    rig_name: str | None = None
    rig_path: str | None = None
    bead_id: str | None = None
    brief_slug: str | None = None
    data_location: str | None = None
    policy_ref: str | None = None
    provenance_ref: str | None = None
    suggested_next_command: str | None = None

@dataclass(frozen=True)
class RuntimeContext:
    city_path: Path
    rig_name: str
    rig_prefix: str
    rig_path: Path
    scope_kind: Literal["city", "rig"]
    source_checkout_path: Path | None

@dataclass(frozen=True)
class BriefRecord:
    slug: str
    bead_id: str | None
    source_beads: tuple[str, ...]
    status: Literal["pending", "deferred", "adjudicated", "cache_only", "malformed"]
    title: str
    markdown_path: Path | None
    stack_index_path: Path | None
    unlock_count: int | None
    priority: str | None
    gate_profile: str | None
    diagnostics: tuple[Diagnostic, ...]

@dataclass(frozen=True)
class BriefOption:
    label: str
    heading: str
    start_line: int
    end_line: int
    raw_text: str
    confidence: Literal["explicit", "inferred"]

@dataclass(frozen=True)
class EffectPlan:
    trace_id: str
    operation: str
    target: str
    planned_effects: tuple[str, ...]
    blocking_diagnostics: tuple[Diagnostic, ...]

@dataclass(frozen=True)
class TraceRecord:
    trace_id: str
    operation_id: str
    command: str
    initiated_at: str
    actor: str
    city_path: str
    rig_name: str
    source_beads: tuple[str, ...]
    brief_bead: str | None
    brief_slug: str | None
    planned_effects: tuple[str, ...]
    actual_effects: tuple[str, ...]
```

### Source Of Truth

`BeadStoreAdapter` owns canonical state:

- brief identity and lifecycle from `bd` decision beads,
- source links from the bead dependency graph,
- defer state from bead defer metadata,
- verdict fields from bead metadata/notes,
- work status, assignee, and dispatch provenance.

`BriefCacheAdapter` owns derived artifacts:

- `.beads/briefs/.pile`,
- `.beads/briefs/stack`,
- `.beads/briefs/stack/.index.jsonl`,
- `.beads/briefs/decisions/*.toml`,
- `.beads/briefs/archive`,
- legacy `.beads/decisions-track` inventory rows.

When adapters disagree, the core reports drift. Read commands never repair it. Explicit repair commands are allowed only after doctor reports the exact issue and the repair command presents an `EffectPlan`.

## 3. Full Command, MCP, And Dashboard Control Surface

### CLI Surface

Initial implemented groups:

```bash
mctl context [--city <path>] [--rig <name>] [--json]

mctl briefs list [--status pending|deferred|adjudicated|malformed] [--all-rigs] [--json]
mctl briefs show <brief> [--option <label>] [--compare-options] [--json]
mctl briefs options <brief> [--json]
mctl briefs doctor [<brief>] [--json]
mctl briefs adjudicate <brief> --verdict approve|revise|reject --reason <text> [--option <label>] [--dry-run] [--json]
mctl briefs defer <brief> --days <n> --reason <text> [--dry-run] [--json]
mctl briefs create --source-bead <bead> --title <text> [--body <path>] [--json]
mctl briefs create --source-kind manual --title <text> --body <path> [--json]
mctl briefs validate <brief-or-path> [--json]

mctl work ready [--json]
mctl work status <bead> [--json]
mctl work dispatch <bead> [--dry-run] [--json]
mctl work provenance <bead> [--json]

mctl trace show <trace-id> [--json]
mctl trace replay-preview <trace-id> [--json]
```

Naming choices:

- Use `adjudicate`, not `verdict`, as the canonical write verb because the planning prompt names adjudication as the canonical action.
- Keep `defer` separate because defer is not adjudication under `POLICY.md` B2.7.
- Do not add `approve`, `reject`, or `revise` aliases in the first implementation; aliases would expand audit surface before the stable command path is proven.

### MCP Surface

MCP tool names and read/mutate status:

| Tool | Mutates | Input schema highlights |
| --- | --- | --- |
| `context_resolve` | no | optional `city_path`, optional `rig_name` |
| `briefs_list` | no | `status`, `all_rigs` |
| `briefs_show` | no | `brief`, optional `option`, `compare_options` |
| `briefs_options` | no | `brief` |
| `briefs_doctor` | no | optional `brief` |
| `briefs_adjudicate` | yes | `brief`, `verdict` enum, optional `option`, `reason`, `dry_run` |
| `briefs_defer` | yes | `brief`, `days`, `reason`, `dry_run` |
| `briefs_create` | yes | `source_kind` enum, `source_bead` or `body_path`, `title`, `dry_run` |
| `briefs_validate` | no | `brief_or_path` |
| `work_ready` | no | optional `rig_name` |
| `work_status` | no | `bead` |
| `work_dispatch` | yes | `bead`, `dry_run` |
| `work_provenance` | no | `bead` |
| `trace_show` | no | `trace_id` |
| `trace_replay_preview` | no | `trace_id` |

Tool annotations must match behavior: read-only tools marked read-only, mutating tools marked non-read-only, destructive hints conservative, idempotent hints set only where repeated calls are safe, and open-world hints false for enum-bound domain tools.

### Dashboard Surface

The dashboard ships after CLI and MCP semantics are stable. It provides:

- current context panel,
- pending/deferred/malformed brief list,
- full brief view,
- option tabs for `(A)`, `Option A`, `Alternative A`, and `Verdict A`,
- option comparison view,
- adjudication reason editor,
- no-brainer leak marker,
- draft verdict storage,
- doctor diagnostics inline with policy refs,
- trace/provenance view,
- submit button that calls the same core effect planner as CLI and MCP.

## 4. Diagnostics, Invariants, Traceability, And Logging Model

Stable diagnostic code prefixes:

| Prefix | Meaning |
| --- | --- |
| `MCTX` | runtime context resolution |
| `MBRF` | brief read/cache/bead invariants |
| `MOPT` | option parsing and option-aware verdicts |
| `MPOL` | policy mapping/index failures |
| `MEFF` | effect-plan blocking failures |
| `MWRK` | work dispatch/status/provenance |
| `MTRC` | trace store |
| `MMCP` | MCP schema/tool failures |

Core invariants:

- `MBRF001`: stack index row points at a missing file.
- `MBRF002`: brief file exists with no matching decision bead.
- `MBRF003`: brief bead is not `type=decision`.
- `MBRF004`: brief bead has no source dependency.
- `MBRF005`: closed brief bead has no recorded verdict.
- `MBRF006`: closed/adjudicated brief appears in presentable stack.
- `MBRF007`: deferred brief appears before defer expiry.
- `MBRF008`: legacy decisions-track row is non-terminal and not migration-visible. This stays blocked on #38 proof/canary.
- `MOPT001`: brief has multiple options and adjudication omitted `--option`.
- `MOPT002`: the named option is not one this brief offers.

**Naming note.** This plan defines `BriefOption` twice, incompatibly: §2
defines a *decision* option parsed from brief markdown (label, heading, line
span, raw text, confidence), while Slice 2 defines an *enabled action*
(adjudicate / defer / validate) and tells `briefs options` to compute those.
The code implements the Slice 2 sense as `BriefOption`, and the §2 sense as
`BriefDecisionOption`. `--option`, `--compare-options`, and `MOPT001`/`MOPT002`
all refer to the §2 decision option. Renaming one of them in this plan would
remove the ambiguity.
- `MWRK001`: bead already has an active assignee.
- `MWRK002`: open child workflow already exists for the same source.
- `MWRK003`: dispatch command returned success but assignee verification failed.
- `MWRK010`: brief has no approving verdict for work dispatch.
- `MWRK011`: approved work dispatch requires a source bead dependency.
- `MWRK012`: the source bead named by the brief dependency was not found.

`MWRK001`-`MWRK003` are dispatch-safety invariants and are reserved for that
meaning. Readiness checks live at `MWRK010`+. The registry in
`assets/mctl/diagnostics.toml` is the machine-checkable source of truth for
this list; `tests/mctl/test_diagnostics_registry.py` keeps them in step.

Trace storage:

- Store JSONL under `<rig_root>/.beads/mctl/traces/YYYY-MM-DD.jsonl`.
- Each command appends a `TraceRecord` before mutation.
- Mutating commands append actual effects after mutation or append blocking diagnostics if they abort.
- `mctl trace replay-preview` reconstructs the `EffectPlan` and reports what would be run today. It does not apply effects.

## 5. Vertical-Slice Implementation Ladder

This ladder is intentionally vertical. Each slice lands one end-to-end user-visible capability across the shared core, CLI, diagnostics, tests, and documentation before moving on. Horizontal scaffolding only appears inside a slice when that slice needs it to make a command work.

Each slice has a commit boundary. A later slice may extend contracts introduced by an earlier slice, but no slice should leave an advertised command, MCP tool, or dashboard control as a stub.

### Slice 1: Context Resolution And `mctl context`

#### User-visible result

From a terminal in a registered city, an operator can run:

```bash
mctl context --json
mctl context --rig mathcity --json
mctl context --city <city-root> --rig mathcity --json
mctl context --explain
```

The command prints the resolved city root, rig id, source checkout, bead database name, paths from `paths.toml`, applicable gates from `gates.toml`, and a trace id. From `<repo-root>`, ordinary runtime commands fail with a precise error unless `--city` and `--rig` are supplied.

#### Files to create or edit

- Create `assets/scripts/mctl.py` as the thin local CLI entry point.
- Create `assets/scripts/mctl_core/__init__.py`.
- Create `assets/scripts/mctl_core/cli.py`.
- Create `assets/scripts/mctl_core/context.py`.
- Create `assets/scripts/mctl_core/diagnostics.py`.
- Create `assets/scripts/mctl_core/trace.py`.
- Create `tests/mctl/test_context_cli.py`.
- Create `tests/mctl/fixtures/city_root/city.toml`.
- Create `tests/mctl/fixtures/source_checkout/README.md` if a source-checkout fixture is needed to prove fail-closed behavior.
- Edit `README-development.md` to document the local invocation used by tests.

This matches the current repository convention: executable Python lives under `assets/scripts/`, while behavior tests live under `tests/<behavior>/`. If a more formal package home is added later, update `LAYOUT.md` and this plan before moving these files.

#### Core interfaces

Implement these concrete interfaces first because every later slice uses them:

```python
@dataclass(frozen=True)
class MctlContext:
    city_root: Path
    rig_id: str
    rig_db: str
    source_checkout: Path
    paths_toml: Path
    gates_toml: Path
    invocation_cwd: Path
    trace_id: str
    warnings: tuple[Diagnostic, ...]

class ContextError(Exception):
    code: str
    diagnostic: Diagnostic


def resolve_context(
    cwd: Path,
    *,
    city: Path | None,
    rig: str | None,
    require_runtime_city: bool,
    env: Mapping[str, str],
) -> MctlContext:
    ...
```

`Diagnostic` must carry `severity`, `code`, `message`, `hint`, and `facts`. `trace_id` must be generated for every invocation and propagated to logs and JSON output.

#### Implementation steps

1. Add the package skeleton and a single `mctl` CLI entry point that dispatches with `argparse` or the repository-preferred CLI library.
2. Implement city discovery from explicit `--city`, then current working directory ancestry, then environment only if an existing city convention supports it.
3. Parse `city.toml` using a TOML parser, not ad hoc string matching. Resolve the rig by explicit `--rig` or by the only registered rig when exactly one is present in test fixtures.
4. Resolve `paths.toml` and `gates.toml` from the selected rig's source checkout, using the already-read repository contracts:
   - `assets/brief-pipeline/paths.toml`
   - `assets/brief-pipeline/gates.toml`
5. Detect source-checkout execution. If `cwd` is under `<repo-root>` and `--city` is missing for a runtime command, return `FATAL MCTL_CONTEXT_SOURCE_CHECKOUT` with a hint to pass `--city <city-root> --rig mathcity`.
6. Implement `mctl context --json` and `mctl context --explain` only. No other command names should be accepted in this slice.
7. Add deterministic JSON rendering with stable key order for tests.
8. Add stderr diagnostic rendering for failures.
9. Update README-development with the exact command used to run this package locally from a checkout.

#### Tests

Write failing tests before implementation for:

- `mctl context --json` resolves a registered city fixture and includes `city_root`, `rig_id`, `rig_db`, `source_checkout`, `paths_toml`, `gates_toml`, and `trace_id`.
- `mctl context --explain` includes the selected discovery path and any non-fatal warnings.
- Running from a source-checkout fixture without `--city` exits non-zero and returns `MCTL_CONTEXT_SOURCE_CHECKOUT`.
- Passing an unknown rig exits non-zero with `MCTL_CONTEXT_UNKNOWN_RIG`.
- Missing `paths.toml` or `gates.toml` exits non-zero with a FATAL diagnostic.

#### Verification commands

```bash
cd <repo-root>
python3 -m pytest tests/mctl/test_context_cli.py
git diff --check -- assets/scripts/mctl.py assets/scripts/mctl_core tests/mctl README-development.md
```

#### Commit boundary

Commit message: `mctl: add city-aware context command`.

The commit is ready only when the user can run `mctl context` locally and receive a meaningful answer or a meaningful fail-closed diagnostic.

### Slice 2: Read-Only Brief Inspection With `briefs list`, `show`, `options`, And `doctor`

#### User-visible result

An operator can inspect the canonical brief state without mutating anything:

```bash
mctl briefs list --status open --json
mctl briefs show mc-abc --json
mctl briefs options mc-abc --json
mctl briefs doctor --json
mctl briefs doctor --brief mc-abc --json
```

The output identifies the canonical decision bead, related redundant artifacts, drift status, source policy references, and available next actions. Read commands never repair drift.

#### Files to create or edit

- Create `assets/scripts/mctl_core/beads.py`.
- Create `assets/scripts/mctl_core/briefs.py`.
- Create `assets/scripts/mctl_core/redundant_state.py`.
- Create `assets/scripts/mctl_core/policy_refs.py`.
- Edit `assets/scripts/mctl_core/cli.py`.
- Create `tests/mctl/test_briefs_read_cli.py`.
- Create `tests/mctl/fixtures/brief_state/beads.jsonl`.
- Create `tests/mctl/fixtures/brief_state/briefs/*.toml` as cache fixtures only, not as canonical fixtures.
- Edit `README-development.md` with read-only brief inspection examples.

#### Core interfaces

Add these interfaces behind the CLI:

```python
@dataclass(frozen=True)
class BriefRecord:
    brief_id: str
    bead_id: str
    title: str
    status: str
    decision_state: str
    labels: tuple[str, ...]
    created_at: str | None
    updated_at: str | None
    redundant_artifacts: tuple[RedundantArtifact, ...]

@dataclass(frozen=True)
class BriefOption:
    id: str
    label: str
    description: str
    enabled: bool
    disabled_reason: Diagnostic | None


def list_briefs(ctx: MctlContext, filters: BriefFilters) -> tuple[BriefRecord, ...]:
    ...


def show_brief(ctx: MctlContext, brief_id: str) -> BriefRecord:
    ...


def brief_options(ctx: MctlContext, brief_id: str) -> tuple[BriefOption, ...]:
    ...


def doctor_briefs(ctx: MctlContext, brief_id: str | None) -> DoctorReport:
    ...
```

`BriefRecord.bead_id` and `BriefRecord.brief_id` are the same identifier for current decision beads. Keep both fields for operator clarity and future migrations, but document that the bead is canonical.

#### Implementation steps

1. Implement a bead reader that can read from `.beads/issues.jsonl` fixtures and, when available in real runtime, shell out to `bd` through a small adapter with explicit timeout and JSON parsing.
2. Treat only `type=decision` beads and the brief labels/status conventions from the impact register as canonical brief rows.
3. Add redundant artifact scanning for the paths named in `paths.toml`: pile, stack index, decision TOML cache, and legacy decisions-track. Mark each artifact as `present`, `missing`, `stale`, or `inconsistent` without editing it.
4. Implement `briefs list` with filters for `--status`, `--label`, and `--json`.
5. Implement `briefs show` with canonical bead fields, redundant artifact inventory, and policy source references.
6. Implement `briefs options` so it computes enabled actions from bead state and diagnostics. Examples: `adjudicate`, `defer`, `validate`, `dispatch-work`.
7. Implement `briefs doctor` to check invariants from Section 4 and return severity counts plus per-brief diagnostics.
8. Include `MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED` when legacy decisions-track state is required but #38 proof is not present.
9. Ensure read commands never call repair or write paths.
10. Document examples and the no-repair guarantee.

#### Tests

Write failing tests before implementation for:

- `briefs list --json` returns only decision beads from a fixture with mixed bead types.
- `briefs show` reports the bead as canonical and the file artifacts as redundant.
- `briefs options` disables mutation actions when `doctor` has ERROR or FATAL diagnostics.
- `briefs doctor` reports inconsistent cache state but does not rewrite fixture files.
- `briefs doctor` emits `MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED` for legacy decisions-track dependency without #38 proof.
- All JSON outputs include the same `trace_id` shape introduced in Slice 1.

#### Verification commands

```bash
cd <repo-root>
python3 -m pytest tests/mctl/test_context_cli.py tests/mctl/test_briefs_read_cli.py
git diff --check -- assets/scripts/mctl.py assets/scripts/mctl_core tests/mctl README-development.md
```

#### Commit boundary

Commit message: `mctl: add read-only brief inspection`.

The commit is ready only when an operator can inspect brief state, see drift clearly, and trust that no read command repairs or mutates redundant artifacts.

### Slice 3: Decision Mutations With `briefs adjudicate` And `briefs defer`

#### User-visible result

An operator can safely adjudicate or defer a brief through a dry-run-first path:

```bash
mctl briefs adjudicate mc-abc --decision accept --dry-run --json
mctl briefs adjudicate mc-abc --decision accept --reason "ready" --json
mctl briefs defer mc-abc --reason "waiting on owner" --until 2026-08-20 --dry-run --json
mctl briefs defer mc-abc --reason "waiting on owner" --until 2026-08-20 --json
```

The dry run returns the exact bead update, redundant cache update, event log append, and trace record that would occur. The real run fails closed if diagnostics are ERROR or FATAL.

#### Files to create or edit

- Create `assets/scripts/mctl_core/effects.py`.
- Create `assets/scripts/mctl_core/events.py`.
- Edit `assets/scripts/mctl_core/briefs.py`.
- Edit `assets/scripts/mctl_core/beads.py`.
- Edit `assets/scripts/mctl_core/cli.py`.
- Create `tests/mctl/test_briefs_mutation_cli.py`.
- Create `tests/mctl/fixtures/mutation_state/`.
- Edit `formulas/brief-record-decision.toml` only if the existing formula needs a narrow compatibility hook for the new event fields.
- Edit `subdomains/dev/docs/plans/mcp/MCTL-MCP-IMPLEMENTATION-PLAN.md` if implementation discovers a contract mismatch that changes this plan.

#### Core interfaces

```python
@dataclass(frozen=True)
class EffectPlan:
    operation: str
    target_brief_id: str
    preconditions: tuple[Diagnostic, ...]
    bead_updates: tuple[BeadUpdate, ...]
    cache_updates: tuple[CacheUpdate, ...]
    event_writes: tuple[EventWrite, ...]
    trace_writes: tuple[TraceWrite, ...]


def plan_adjudication(ctx: MctlContext, brief_id: str, decision: str, reason: str | None) -> EffectPlan:
    ...


def plan_deferral(ctx: MctlContext, brief_id: str, reason: str, until: str | None) -> EffectPlan:
    ...


def apply_effect_plan(ctx: MctlContext, plan: EffectPlan) -> ApplyResult:
    ...
```

All mutation commands must build an `EffectPlan` first. The same plan object backs dry-run output, real mutation, logs, and tests.

#### Implementation steps

1. Extend `briefs options` from Slice 2 so it names the exact preconditions for adjudication and deferral.
2. Implement `EffectPlan` construction for adjudication and deferral without applying changes.
3. Encode fail-closed rules:
   - no mutation with ERROR or FATAL doctor diagnostics;
   - no mutation when the brief bead cannot be proven canonical;
   - no mutation when #38 decisions-track migration proof is required and absent;
   - no mutation from source checkout without explicit city and rig.
4. Implement bead updates through the bead adapter. Prefer existing `bd update` JSON semantics if available; otherwise isolate command construction in `beads.py` and test it as data.
5. Implement redundant cache updates only after the bead update succeeds. The bead remains canonical if cache update fails, and the failure is reported as `ERROR MCTL_REDUNDANT_CACHE_UPDATE_FAILED`.
6. Append a structured event row containing trace id, operator command, brief id, operation, pre-state summary, post-state summary, and redundant write results.
7. Add dry-run output that includes all planned effects and no applied effects.
8. Add real-run output that includes applied effects and post-run doctor status.
9. Document the dry-run-first mutation workflow.

#### Tests

Write failing tests before implementation for:

- `adjudicate --dry-run` returns bead/cache/event effects and does not mutate fixture state.
- `adjudicate` applies the bead update before redundant cache updates.
- `defer --dry-run` requires a non-empty reason.
- mutation fails with `MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS` when doctor reports ERROR or FATAL.
- mutation fails with `MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED` when legacy decisions-track proof is required and absent.
- applying a plan records the same trace id in command output and event log.
- failed redundant cache update reports an ERROR while preserving canonical bead state.

#### Verification commands

```bash
cd <repo-root>
python3 -m pytest tests/mctl/test_context_cli.py tests/mctl/test_briefs_read_cli.py tests/mctl/test_briefs_mutation_cli.py
for t in tests/decisions-track-migration/smoke_test.sh tests/brief-decision-dispatch/smoke_test.sh; do bash "$t"; done
git diff --check -- assets/scripts/mctl.py assets/scripts/mctl_core tests/mctl formulas/brief-record-decision.toml subdomains/dev/docs/plans/mcp/MCTL-MCP-IMPLEMENTATION-PLAN.md
```

#### Commit boundary

Commit message: `mctl: add safe brief decision mutations`.

The commit is ready only when the dry-run and real-run paths use the same effect plan and mutations fail closed under every known drift condition.

### Slice 4: Work Readiness, Status, Provenance, And Dispatch

#### User-visible result

An operator can move from a brief decision to work dispatch without switching tools:

```bash
mctl work ready --json
mctl work status mc-abc --json
mctl work provenance mc-abc --json
mctl work dispatch mc-abc --dry-run --json
mctl work dispatch mc-abc --json
```

The command surface exposes ready work, current dispatch status, dispatch provenance, and a dry-run-first dispatch operation. Dispatch is blocked if brief policy gates, context checks, or provenance schema checks fail.

#### Files to create or edit

- Create `assets/scripts/mctl_core/work.py`.
- Create `assets/scripts/mctl_core/provenance.py`.
- Edit `assets/scripts/mctl_core/effects.py`.
- Edit `assets/scripts/mctl_core/cli.py`.
- Create `tests/mctl/test_work_cli.py`.
- Create `tests/mctl/fixtures/work_state/`.
- Edit `formulas/work-briefed.toml` if the formula needs a narrow compatibility hook.
- Edit `formulas/commission-work-briefed.toml` if dispatch handoff output needs a narrow compatibility hook.
- Edit `orders/brief-decision-dispatch.toml` if the order contract must expose a stable `mctl` provenance field.
- Edit `assets/bead-filter/dispatch-provenance-schema.toml` only for additive schema fields required by `mctl work provenance`.
- Edit `README-development.md` with work command examples.

#### Core interfaces

```python
@dataclass(frozen=True)
class WorkItem:
    brief_id: str
    bead_id: str
    title: str
    readiness: str
    blockers: tuple[Diagnostic, ...]
    provenance: DispatchProvenance | None


def ready_work(ctx: MctlContext, filters: WorkFilters) -> tuple[WorkItem, ...]:
    ...


def work_status(ctx: MctlContext, brief_id: str) -> WorkItem:
    ...


def work_provenance(ctx: MctlContext, brief_id: str) -> DispatchProvenance:
    ...


def plan_dispatch(ctx: MctlContext, brief_id: str) -> EffectPlan:
    ...
```

#### Implementation steps

1. Load dispatch provenance schema from `assets/bead-filter/dispatch-provenance-schema.toml` and validate provenance records through a structured parser.
2. Implement `work ready` from canonical decision beads plus brief policy gates, not from redundant cache state alone.
3. Implement `work status` as a join of brief state, dispatch gate state, and existing provenance.
4. Implement `work provenance` with schema validation diagnostics and source references.
5. Implement `work dispatch --dry-run` as an `EffectPlan` that shows bead updates, provenance write, event write, and formula/order invocation payload.
6. Implement real dispatch only after dry-run output is already covered by tests.
7. Block dispatch when decisions-track migration proof is required and absent.
8. Block dispatch when provenance schema validation emits ERROR or FATAL.
9. Keep formula/order edits minimal and backwards-compatible. This slice should wrap existing dispatch machinery rather than replace it wholesale.
10. Document how `mctl work` maps onto the existing `work-briefed`, `commission-work-briefed`, and `brief-decision-dispatch` artifacts.

#### Tests

Write failing tests before implementation for:

- `work ready` lists only canonical decision beads whose gates pass.
- `work status` reports blockers from policy, diagnostics, and provenance validation.
- `work provenance` accepts a valid schema fixture and rejects an invalid one with a stable error code.
- `work dispatch --dry-run` returns formula/order payloads without mutating fixture state.
- `work dispatch` writes provenance and event rows sharing the command trace id.
- dispatch is blocked by #38 migration uncertainty when legacy decisions-track data is in play.

#### Verification commands

```bash
cd <repo-root>
python3 -m pytest tests/mctl/test_context_cli.py tests/mctl/test_briefs_read_cli.py tests/mctl/test_briefs_mutation_cli.py tests/mctl/test_work_cli.py
for t in tests/decisions-track-migration/smoke_test.sh tests/brief-decision-dispatch/smoke_test.sh; do bash "$t"; done
git diff --check -- assets/scripts/mctl.py assets/scripts/mctl_core tests/mctl formulas/work-briefed.toml formulas/commission-work-briefed.toml orders/brief-decision-dispatch.toml assets/bead-filter/dispatch-provenance-schema.toml README-development.md
```

#### Commit boundary

Commit message: `mctl: add brief-driven work dispatch controls`.

The commit is ready only when an operator can see why work is or is not ready and can dispatch through the same effect-plan safety model used for brief decisions.

### Slice 5: Brief Creation And Validation

#### User-visible result

An operator can create and validate a brief through the canonical bead-first path:

```bash
mctl briefs create --title "Decide dispatch policy" --body-file /tmp/body.md --dry-run --json
mctl briefs create --title "Decide dispatch policy" --body-file /tmp/body.md --json
mctl briefs validate mc-abc --json
mctl briefs validate --all --json
```

Creation writes the decision bead first, then redundant artifacts. Validation proves canonical and redundant state still agree.

#### Files to create or edit

- Edit `assets/scripts/mctl_core/briefs.py`.
- Edit `assets/scripts/mctl_core/effects.py`.
- Edit `assets/scripts/mctl_core/cli.py`.
- Create `tests/mctl/test_briefs_create_validate_cli.py`.
- Create `tests/mctl/fixtures/create_validate_state/`.
- Edit `formulas/brief-prep.toml` if a compatibility hook is needed for CLI-created briefs.
- Edit `formulas/math-brief-prep.toml` if the math variant needs the same hook.
- Edit `subdomains/brief-system/POLICY.md` only if implementation reveals an ambiguity in canonical creation policy; otherwise do not change policy.
- Edit `subdomains/brief-system/README.md` with the new operator command examples.

#### Core interfaces

```python
@dataclass(frozen=True)
class BriefCreateInput:
    title: str
    body: str
    labels: tuple[str, ...]
    requested_by: str | None


def plan_create_brief(ctx: MctlContext, request: BriefCreateInput) -> EffectPlan:
    ...


def validate_brief(ctx: MctlContext, brief_id: str | None) -> ValidationReport:
    ...
```

#### Implementation steps

1. Implement title/body/label validation using brief-system policy. Do not duplicate policy prose in code; map code checks to policy section references.
2. Implement `briefs create --dry-run` as an effect plan with bead creation, redundant cache writes, and event writes.
3. Implement real creation through the bead adapter, with cache writes after bead creation succeeds.
4. Implement `briefs validate` by composing `briefs doctor` with stricter per-brief invariants needed for creation and mutation workflows.
5. Support `--all` only after single-brief validation is fully covered.
6. Add compatibility hooks to `brief-prep` and `math-brief-prep` only if existing formulas need to consume CLI-created briefs.
7. Document creation examples and explicitly say the decision bead is the source of truth.

#### Tests

Write failing tests before implementation for:

- `briefs create --dry-run` returns a bead-first effect plan and writes nothing.
- `briefs create` writes a decision bead before redundant artifacts.
- creation rejects empty title, empty body, and labels that violate policy with stable codes.
- `briefs validate <id>` succeeds for consistent canonical and redundant state.
- `briefs validate <id>` reports stale redundant artifacts without modifying them.
- `briefs validate --all` returns aggregate severity counts.

#### Verification commands

```bash
cd <repo-root>
python3 -m pytest tests/mctl/test_context_cli.py tests/mctl/test_briefs_read_cli.py tests/mctl/test_briefs_mutation_cli.py tests/mctl/test_work_cli.py tests/mctl/test_briefs_create_validate_cli.py
for t in tests/decisions-track-migration/smoke_test.sh tests/brief-decision-dispatch/smoke_test.sh; do bash "$t"; done
git diff --check -- assets/scripts/mctl.py assets/scripts/mctl_core tests/mctl formulas/brief-prep.toml formulas/math-brief-prep.toml subdomains/brief-system/POLICY.md subdomains/brief-system/README.md
```

#### Commit boundary

Commit message: `mctl: add bead-first brief creation and validation`.

The commit is ready only when brief creation, inspection, mutation, validation, and work dispatch all use the same canonical bead-first model.

### Slice 6: Typed MCP Server Over The Completed Core

#### User-visible result

An MCP client can perform the same completed CLI workflows through typed tools:

- `context_resolve`
- `briefs_list`
- `briefs_show`
- `briefs_options`
- `briefs_doctor`
- `briefs_adjudicate`
- `briefs_defer`
- `briefs_create`
- `briefs_validate`
- `work_ready`
- `work_status`
- `work_dispatch`
- `work_provenance`
- `trace_show`
- `trace_replay_preview`

The server exposes typed task tools, not a generic shell, `gc`, `bd`, or `mctl` passthrough.

#### Files to create or edit

- Create `assets/scripts/mctl_core/mcp_server.py`.
- Create `assets/scripts/mctl_core/schemas.py`.
- Create `tests/mctl/test_mcp_server.py`.
- Create `tests/mctl/test_mcp_schema_snapshots.py`.
- Edit `assets/scripts/mctl.py` or future repository-standard package metadata to expose the MCP server entry point.
- Edit `README-development.md` with local MCP startup and smoke-test commands.

#### Core interfaces

`schemas.py` should contain the request and response models shared by CLI JSON and MCP responses. If the implementation uses Pydantic or dataclasses, choose one and use it consistently. The MCP layer should call the same `context.py`, `briefs.py`, `work.py`, `effects.py`, and `trace.py` functions already proven by CLI tests.

#### Implementation steps

1. Choose the MCP SDK already used in this workspace if one exists; otherwise add the smallest local dependency-free server layer compatible with the target runtime.
2. Define schemas for all request and response payloads. Include diagnostic arrays and trace ids in every response.
3. Implement `context_resolve` first and prove it returns the same payload shape as `mctl context --json`.
4. Add read-only brief tools by wrapping Slice 2 core functions.
5. Add mutation brief tools by wrapping Slice 3 and Slice 5 effect-plan functions. Support explicit dry-run fields.
6. Add work tools by wrapping Slice 4 core functions.
7. Add trace tools that expose recorded trace entries and replay previews without reapplying effects.
8. Add schema snapshot tests so accidental breaking changes are visible.
9. Document that the MCP server has no generic command-execution tool.

#### Tests

Write failing tests before implementation for:

- every MCP tool has a schema snapshot;
- `context_resolve` returns the same key fields as CLI context JSON;
- `briefs_show` returns canonical bead and redundant artifact fields;
- mutation tools respect dry-run and fail-closed behavior;
- `work_dispatch` returns the same effect-plan shape as CLI dispatch;
- no tool named `shell`, `gc`, `bd`, `mctl`, `run_command`, or `exec` is registered.

#### Verification commands

```bash
cd <repo-root>
python3 -m pytest tests/mctl
git diff --check -- assets/scripts/mctl.py assets/scripts/mctl_core tests/mctl README-development.md
```

#### Commit boundary

Commit message: `mctl: expose typed MCP tools`.

The commit is ready only when every MCP tool is a thin typed wrapper around a CLI-proven core workflow.

### Slice 7: Skill Refactor And Audit On Top Of `mctl`

#### User-visible result

The relevant skills stop hand-rolling brief/work state transitions and either call `mctl` or explicitly document why they remain manual. Running the impacted workflows produces `mctl` trace ids in their output or logs.

#### Files to create or edit

- Edit each skill listed in `SKILL-IMPACT-REGISTER.md` whose disposition becomes `wrap-with-mctl` or `replace-with-mctl`.
- Create or edit skill tests under the repository's existing skill test location if present; otherwise add focused smoke tests beside the changed skill wrappers.
- Edit `SKILL-IMPACT-REGISTER.md` with final dispositions and migration notes.
- Edit `README-development.md` with the skill audit command sequence.

#### Skill disposition targets

| Skill | Target disposition |
| --- | --- |
| `brief-prep` | wrap `mctl briefs create` or document formula-only exception |
| `create-brief` | replace direct creation with `mctl briefs create` |
| `adjudicate-brief` | replace direct adjudication with `mctl briefs adjudicate` |
| `coordinate-review` | wrap `mctl briefs options` and `mctl briefs doctor` |
| `work` | wrap `mctl work ready/status/dispatch` |
| `immediate-work` | wrap `mctl work dispatch` where brief-backed |
| `priority-work` | wrap `mctl work ready` filtering |
| `brief-prep` math variant | wrap `mctl briefs create` only if compatible with math-specific policy |
| any skill marked no-change | include a reason tied to Section 2 source-of-truth boundaries |

#### Implementation steps

1. Re-read `SKILL-IMPACT-REGISTER.md` at the start of the slice and classify each skill as `replace-with-mctl`, `wrap-with-mctl`, `no-change`, or `blocked-by-policy`.
2. Update one skill at a time. Each changed skill must use the typed CLI surface, not shell snippets that reconstruct bead/cache writes manually.
3. Preserve user-facing skill behavior unless the old behavior was unsafe because it bypassed canonical bead-first state.
4. Add trace id propagation to skill output where the skill performs a mutation or dispatch.
5. Run the relevant skill smoke test before moving to the next skill.
6. Update the impact register as the authoritative audit record.

#### Tests

Write failing tests or smoke cases before each skill wrapper change for:

- the skill invokes the expected `mctl` command or core wrapper;
- mutation skills expose the `mctl` trace id;
- no changed skill writes redundant brief artifacts directly;
- skills marked no-change have an explicit source-of-truth reason.

#### Verification commands

```bash
cd <repo-root>
python3 -m pytest tests/mctl
bash scripts/run-local-tests.sh
git diff --check -- SKILL-IMPACT-REGISTER.md README-development.md skills subdomains
```

Narrow `scripts/run-local-tests.sh` only if it proves too broad for local runtime, but record the exact skipped tests and why in the commit message body.

#### Commit boundary

Commit message: `skills: route brief workflows through mctl`.

The commit is ready only when the impact register and changed skills agree about which workflows now depend on `mctl`.

### Slice 8: Dashboard For Completed CLI And MCP Workflows

#### User-visible result

The dashboard provides operator controls for the same completed workflows:

- context badge and trace id search;
- brief list/show/options/doctor;
- adjudicate/defer/create/validate with dry-run preview;
- work ready/status/provenance/dispatch;
- diagnostics grouped by severity and code;
- no repair-on-read actions.

#### Files to create or edit

- Create dashboard files in the repository-standard dashboard location once identified in this slice.
- Create dashboard tests in the matching test location.
- Edit `README-development.md` with dashboard startup and smoke-test instructions.
- Edit this plan if dashboard discovery finds an existing application boundary that changes file paths materially.

#### Implementation steps

1. Identify the existing dashboard framework or confirm that no dashboard app exists.
2. Build the dashboard against MCP tools from Slice 6, not against ad hoc shell commands.
3. Show context resolution as the first visible state. The dashboard must make source checkout versus city runtime context obvious.
4. Build brief inspection views using `briefs_list`, `briefs_show`, `briefs_options`, and `briefs_doctor`.
5. Build mutation dialogs around dry-run previews. The confirmation action must apply exactly the previewed operation or force a refreshed preview.
6. Build work views using `work_ready`, `work_status`, `work_provenance`, and `work_dispatch`.
7. Add trace search and replay preview views.
8. Add visual treatment for INFO/WARN/ERROR/FATAL diagnostics without hiding the diagnostic code.
9. Verify the dashboard in desktop and mobile viewports if it is web-based.

#### Tests

Write failing tests before implementation for:

- dashboard loads and resolves context through MCP;
- brief list and detail views render canonical bead fields;
- mutation preview must be generated before an apply action is enabled;
- stale preview cannot be applied after context or target brief changes;
- diagnostic code and severity are visible in the UI;
- dashboard does not register or call generic command-execution tools.

#### Verification commands

Use the dashboard framework's local test command after the framework is identified. At minimum run:

```bash
cd <repo-root>
python3 -m pytest tests/mctl
git diff --check -- README-development.md
```

If the dashboard is web-based, also run Playwright or the repository-standard browser smoke test and capture the local URL in the handoff.

#### Commit boundary

Commit message: `dashboard: add mctl operator controls`.

The commit is ready only when the dashboard is a client of the typed MCP surface and every mutation path is dry-run preview first.

## 6. Skill Refactor And Post-Implementation Audit Plan

The skill audit happens as Slice 7 because the skills should wrap a working CLI/MCP core instead of defining the control surface themselves.

### Audit Rules

1. `SKILL-IMPACT-REGISTER.md` is the audit source of truth.
2. A skill that creates, adjudicates, defers, validates, or dispatches brief-backed work should call `mctl` unless a documented formula boundary makes that impossible.
3. A skill may remain unchanged only when it never touches brief/work state or when it is explicitly read-only and already respects the canonical bead-first model.
4. Changed skills must not write pile, stack index, decision TOML cache, or decisions-track state directly.
5. Changed skills must surface trace ids for mutation and dispatch operations.
6. The audit must record the final disposition, files changed, command surface used, and remaining risk for every impacted skill.

### Audit Output Format

Add or update a table in `SKILL-IMPACT-REGISTER.md` with these fields:

| Field | Meaning |
| --- | --- |
| Skill | Skill name and path |
| Current behavior | The direct behavior before `mctl` migration |
| Disposition | `replace-with-mctl`, `wrap-with-mctl`, `no-change`, or `blocked-by-policy` |
| MCTL surface | Exact command or core API used |
| Trace behavior | How trace id reaches logs or user output |
| Verification | Test or smoke command |
| Residual risk | Concrete remaining risk, or `none known` |

### Audit Verification

Run this audit check after Slice 7:

```bash
cd <repo-root>
rg -n "brief|adjudicate|defer|decision|dispatch|work ready|work status" skills subdomains -g 'SKILL.md'
python3 -m pytest tests/mctl
```

For every remaining direct state manipulation hit, either migrate it to `mctl` or record a no-change/blocking reason in the impact register.

## 7. Testing And Verification Plan

Testing is layered by slice. Every slice starts with failing tests for its user-visible behavior and ends with a verification command that proves that behavior works end to end.

### Per-Slice Test Gates

| Slice | Required test gate |
| --- | --- |
| Slice 1 | `python3 -m pytest tests/mctl/test_context_cli.py` |
| Slice 2 | Slice 1 tests plus `test_briefs_read_cli.py` |
| Slice 3 | Slices 1-2 tests plus `test_briefs_mutation_cli.py` and decisions-track/dispatch smoke tests |
| Slice 4 | Slices 1-3 tests plus `test_work_cli.py` and provenance schema checks |
| Slice 5 | Slices 1-4 tests plus `test_briefs_create_validate_cli.py` |
| Slice 6 | all `tests/mctl`, including MCP schema snapshots |
| Slice 7 | all `mctl` tests plus relevant skill smoke tests and impact-register grep audit |
| Slice 8 | all `mctl` tests plus dashboard framework tests and browser smoke tests if web-based |

### Existing Regression Tests To Preserve

Keep these existing gates green when touched files overlap their behavior:

```bash
cd <repo-root>
python3 -m pytest tests/stuck-bead-watch/test_stuck_bead_watch.py tests/tail-end-detector/test_tail_end_detector.py
bash scripts/run-local-tests.sh
```

If the full local runner is too broad for a local change, run the affected smoke tests explicitly and document why the rest were not run.

### Decisions-Track Migration Gate

Any command that imports, lists, reasons about, or mutates state derived from legacy decisions-track data must be blocked until #38 migration proof is present. Required checks:

```bash
cd <repo-root>
bash tests/decisions-track-migration/smoke_test.sh
```

The test must prove:

- legacy decisions-track rows are not treated as canonical brief decisions;
- commands emit `MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED` when proof is absent;
- canary fixtures pass before enabling any import or dispatch path that depends on legacy data.

### Mutation Safety Tests

For every mutation-capable command and MCP tool, prove:

- dry run writes nothing;
- real run writes canonical bead state before redundant artifacts;
- redundant write failure does not roll back or hide canonical bead state;
- event log and command output share a trace id;
- ERROR and FATAL diagnostics block mutation;
- source-checkout execution without explicit city and rig blocks mutation.

### Dashboard Tests

Dashboard tests belong to Slice 8 and must prove:

- context is resolved through MCP;
- generic command execution is unavailable;
- dry-run preview is required before apply;
- preview invalidates when context, target, or operation inputs change;
- diagnostic severity and code remain visible.

## 8. Commit And Rollout Strategy

Roll out by vertical slice. Do not create one giant horizontal branch that lands scaffolding without a working operator behavior.

### Commit Sequence

1. `mctl: add city-aware context command`
2. `mctl: add read-only brief inspection`
3. `mctl: add safe brief decision mutations`
4. `mctl: add brief-driven work dispatch controls`
5. `mctl: add bead-first brief creation and validation`
6. `mctl: expose typed MCP tools`
7. `skills: route brief workflows through mctl`
8. `dashboard: add mctl operator controls`

Each commit must include implementation, tests, docs, and verification for that slice. Avoid commits that only add dormant abstractions.

### Rollout Controls

- Enable CLI read-only commands before mutation commands.
- Keep mutation commands dry-run-first in documentation and examples.
- Keep MCP tools disabled from external clients until CLI behavior for the same core function is proven.
- Keep dashboard mutation apply buttons disabled until the dashboard can fetch and display a fresh dry-run preview.
- Keep #38 decisions-track migration blockers in place until canary proof is present.
- Record trace ids in every mutation and dispatch handoff so a failed rollout can be audited.

### Pre-Merge Checklist For Each Slice

Before merging a slice, verify:

- the user-visible command or dashboard path works from a registered city fixture;
- source-checkout runtime invocation fails closed unless explicit city and rig are supplied;
- JSON output includes diagnostics and trace id;
- tests for the slice start from failing expectations and now pass;
- `git diff --check` is clean for touched files;
- docs describe only behavior implemented in that slice;
- no unrelated user changes are reverted.

### Final Review Packet

After Slice 8, prepare a review packet with:

- command and MCP surface inventory;
- final source-of-truth statement;
- diagnostics code list;
- skill-impact register diff;
- test commands run and skipped;
- migration status for #38;
- dashboard local URL or deployment notes;
- known residual risks.
