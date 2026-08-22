# Handoff — City-operations dashboard → `mctl` backend

**Design artifact:** `City Dashboard.dc.html` (HTML prototype, fixture-backed — not production code)
**Design docs it implements:** `uploads/dashboard-screens.md`, `dashboard-object-model.md`, `dashboard-requests.md`, `dashboard-fixtures.md`
**Prior art / companion:** the briefs dashboard (`assets/scripts/mctl_dashboard/`) — same shell, same tokens, same knowl pattern
**Aspiration + gap:** `MATHCITY-TARGET-STATE.md` Part V (§60–62, §68) and `dashboard-gap-analysis.md`

> **Read this first.** The prototype is deliberately designed against the *ideal*
> `mctl`, not the current one. Where the page asks for something the backend does
> not have, the page is the specification and the backend is the work. The one
> thing you must not do is make the page lie: every honesty rule below is load
> bearing, and a plausible empty result is worse than a refusal.

---

## 0. The short list — what is needed

**New typed MCP tools** (names follow target-state §60; add to `mctl_core/mcp_server.py::TOOLS` and to `mctl_dashboard/client.py::ALLOWED_TOOLS`):

| # | Tool | Lights up |
|---|---|---|
| 1 | `molecules_list` | The Molecules table on every page; census counts; population filters |
| 2 | `molecules_show` | Molecule page: step DAG, step bar, spine, properties |
| 3 | `steps_show` | Step page; the five-link evidence chain |
| 4 | `fleet_sessions` | Agents table + agent pages; capacity occupancy |
| 5 | `queue_status` | The QUEUE column and the ready/blocked/tail/starved/deferred populations |
| 6 | `city_health` | Health block, three-valued data plane, flood alarm |
| 7 | `liveness_board` | Orders-as-canaries table, `alive / idle / dead / unknown` verdict |
| 8 | `orders_status` + `orders_history` | Orders class page, Recent firings table with `last n` |
| 9 | `formulas_catalog` + `formulas_profile` | Formula pages: DAG overlays, by-step failures, outcome mix |
| 10 | `gates_status` + `gates_evaluations` | Gate pages, per-rig pass rates, evaluation list |
| 11 | `worktrees_status` | Worktrees class + worktree pages |
| 12 | `capacity_status` + capacity mutations | Capacity bar, N(R)/pool levers |
| 13 | `costs_summary` (tokens over time) | Tokens plot, meta-work ratio, effort grouping |
| 14 | `events_list` (tiered) | Live tape, Events page, cause/response pairing |

**New recording (nothing records these today — instrumentation, not plumbing):**

1. `step.expected_artifacts` — **the keystone**; without declared intent, completion cannot be derived
2. The five-link evidence log per step: claimed → agent active → commit → artifact → step closed
3. `molecule.why` — dispatch **cause** (order / human sling / brief verdict / commission / retry / supersession), recorded at sling time
4. Worktree ownership — `created_by`, `step`, at creation
5. `agent.account` + quota remaining (`usage.window_remaining`, `weekly_remaining`, `resets_at`)
6. `city.uptime` — on/off transitions **with reason**, including `unknown`
7. `Resources.flood_conditions` — fd/disk thresholds with trend
8. `canary.last_outcome` — the order's result, not just its fire time
9. Event `tier` + `cause`/`response` pairing

**Derivations the backend owns (front end must never re-derive):**
`molecule.state` (5 values incl. `stranded` vs `dormant`) · `evidence.broken_at` · `limit_state` · `staleness` · step `layer` from `needs` · `is_complete` from artifacts · worktree `is_orphan` / `is_registered` · gate "never failed in N" suspicion flag · `next_up_is_prediction`.

---

## 1. What already exists — do not rebuild it

Verified in `assets/scripts/mctl_core/` at the commit this handoff was written against:

| Capability | Where | Note |
|---|---|---|
| Typed tool surface, schema-validated in/out | `mcp_server.py::ToolSpec`, `TOOLS`, `request_schema` / `response_schema` | 18 registered tools; the dashboard is allowed 16 |
| No-passthrough guarantee | `mcp_server.py::FORBIDDEN_TOOL_NAMES` (import-time `RuntimeError`) | Keep it. New tools must be typed domain tools |
| Response envelope | `schemas.py` — `diagnostics`, `trace_id`, `artifact_trust`, `untrusted_diagnostics` **required** | Every new tool inherits this |
| Cross-rig fan-out + degraded rigs as named rows | `city.py::for_each_rig`, `merge_outcomes`, `RigProgress`, `rig_timeout_diagnostic` / `rig_partial_diagnostic` / `rig_unreadable_diagnostic` | This is already the "never a silently smaller total" machinery |
| `all_rigs` opt-in and its declared arrays | `mcp_server.py::CROSS_RIG_ARRAYS`, `ALL_RIGS_PROPERTY` | Cross-rig **mutation** is refused at import — keep that |
| Effect plans, dry-run default, preconditions | `effects.py::plan_*`, `apply_effect_plan`, `dry_run_payload`; `_dry_run()` treats absent as dry run | The page's plan → apply → observe flow maps onto this directly |
| Phased trace | `trace.py::fold`, `read_rows`; `planned / applied / aborted` + `actual_effects` | `plan.observe()` in the design = a second read against the applied trace |
| Diagnostics registry | `diagnostics.py::Diagnostic` (typed fields incl. `policy_ref`, `data_location`, `suggested_next_command`); `assets/mctl/diagnostics.toml` | The page keys knowls on `code`; keep codes stable |
| Three-valued data-plane probe | `liveness.py::probe_city` (endpoint probe) and `probe_control_plane` (`gc status --json`) | Already distinguishes "cannot tell" (`None`) from down |
| Dispatch provenance | `provenance.py` — `dispatch-provenance.v1` | Records the *command*; the page needs the *cause* (see §4.3) |
| Client boundary + allowlist | `mctl_dashboard/client.py::ALLOWED_TOOLS` (cross-checked by `tests/mctl/test_dashboard_views.py`) | Add new tool names here explicitly, not by deriving from the registry |
| URL-as-state, no-JS | `mctl_dashboard/state.py` | The city page's SCOPE multi-select, POPULATION filter, sort key, token window and `last n` all belong in the query string the same way |
| Visual tokens | `mctl_dashboard/theme.py`; knowl in `knowl.py` | The prototype uses these exact values; no new colors |

**Consequence for scheduling:** the contract layer (target-state Slice 0) is essentially built. The work is new objects on top of it, plus the recording in §4.

---

## 2. Screen → call map

Every element of the prototype, the call it wants, and today's status (`EXISTS` / `UNWRAPPED` = data is in `gc`/`bd`, needs a typed wrapper / `ABSENT` = nothing records it).

### City-and-rigs page (one page type, scoped by a rig multi-select)

| Element | Needs | Status |
|---|---|---|
| SCOPE multi-select | `context_rigs` (already) + every list accepting a rig set, not just `all_rigs: bool` | **PARTIAL** — extend `ALL_RIGS_PROPERTY` to accept `rigs: string[]` |
| Capacity bar (`6 of 15 slots busy`) | `capacity_status` → per rig `N_target`, `running`, `free`, `pool_desired`, `pool_max` | **UNWRAPPED** (`city.toml` + pool state) |
| Headline counts | `molecules_list` aggregate — the same call the table renders | **ABSENT** |
| Molecules table (+ POPULATION filters, QUEUE column, EVIDENCE chain codes) | `molecules_list` + `queue_status` | **ABSENT** / **PARTIAL** |
| Agents table | `fleet_sessions` | **UNWRAPPED** (`gc session list`) |
| Worktrees table | `worktrees_status` | **ABSENT** |
| Rigs-in-scope table (SLOTS/MOLECULES/OPEN BEADS/WORKTREES) | `capacity_status` + `molecules_list` + `beads.py` + `worktrees_status` | mixed |
| Tokens plot + window selector | `costs_summary(bucket, window)` | **PARTIAL** (`gc costs` = spend; needs bucketing) |
| Health / usage / uptime block | `city_health`, `usage`, `uptime_log` | **UNWRAPPED** / **ABSENT** / **ABSENT** |
| Live tape (sidebar, city-wide) | `events_list(tier=…, limit=…)` | **UNWRAPPED** (`gc events`) + **ABSENT** tier vocabulary |
| Levers box | `capacity.set_target`, `add_agents`, `close`, `drain`, `disable_formula`, `order.run_now`, `rig.suspend` | **UNWRAPPED** writes, no mctl mutation path |

### Object pages

| Page | Needs | Status |
|---|---|---|
| Molecule | `molecules_show` — step DAG, progress with **stated denominator**, spine with durations + longest gap, `why`, cost/budget, worker, worktree, convoy | **ABSENT** |
| Step | `steps_show` — `needs`, `layer`, `expected_artifacts` vs `artifacts`, evidence chain, `broken_at` | **ABSENT** |
| Rig | scoped container page (same call set as the city, filtered) | mixed |
| Agent | `fleet_sessions` + `agent_claims` (work executed: closed claims with formula, finish time, tokens, outcome) | **UNWRAPPED** / **ABSENT** |
| Formula | `formulas_catalog` + `formulas_profile` (`failure_by_step`, `duration_by_step`, `cost_by_step`, `tier_by_step`, outcome mix, invocations over time) | **UNWRAPPED** / **ABSENT** |
| Gate | `gates_status` (per-rig evaluated/passed/rate, registered date, beads failing now, enforcement in/out per rig with authorization) + `gates_evaluations` (itemized list behind a rate) | **ABSENT** |
| Order | `orders_status` + `orders_history(limit)` — with `last_outcome` and the response each firing produced | **UNWRAPPED** + **ABSENT** (`last_outcome`) |
| Worktree | `worktrees_status` detail — path, rig, branch, molecule, `created_by`, step, merged state, age, size, orphan/unregistered, harvestable, commits | **ABSENT** |
| Canary | derived view over `orders_status` — **a canary is an order read by its silence**, not a second object | **PARTIAL** |

---

## 3. Proposed tool shapes

Follow the existing conventions exactly: `request_schema(...)` / `response_schema(...)`, `ToolSpec(scope=RIG_SCOPE|CITY_SCOPE)`, handler in a new `mctl_core/` module, entry in `CROSS_RIG_ARRAYS` if it fans out, `mutating=True` + `external_ready=False` for writes.

### 3.1 `molecules_list` — the highest-value missing surface

```python
ToolSpec(
    name="molecules_list",
    title="List molecules",
    description=(
        "Every molecule in scope — one execution of one formula — unfiltered. "
        "`state` is derived from evidence, never self-reported, and carries the "
        "inputs that produced it. An open root is not a fault: "
        "`open-root-by-design` is a distinct state from `stranded`."
    ),
    input_schema=request_schema({
        "state": nullable_string("Filter by derived state; omit for all."),
        "formula": nullable_string("Filter by formula name."),
        "all_rigs": ALL_RIGS_PROPERTY,          # extend to accept rigs[]
        "limit": {"type": ["integer", "null"]},  # page size, and it is STATED
    }),
    output_schema=response_schema({"molecules": {"type": "array", "items": MOLECULE_SCHEMA}},
                                  ["molecules"]),
    handler=_handle_molecules_list,
)
```

`MOLECULE_SCHEMA` (new, in `schemas.py`):

| Field | Type | Notes |
|---|---|---|
| `root_bead_id`, `rig_id`, `formula`, `formula_version` | str | identity |
| `state` | enum `advancing \| stalled \| stranded \| dormant \| complete` | **derived** |
| `state_evidence` | object | `W`, `P`, `P_measured_between` (two observation times), the bound used |
| `steps_total`, `steps_completed`, `percent`, `counts_what` | int/str | `counts_what` states what the denominator counts, so a stalled denominator is visible |
| `worker_session_id` | str \| null | null means none, not unknown |
| `evidence_summary` | object | the five links, each `{fired, at, source}` — the page renders `CLM AGT CMT ART CLS` from this |
| `broken_at` | enum \| `"none"` | **the diagnosis** |
| `queue_state` | enum | `claimed`, `ready_unclaimed`, `blocked(on)`, `tail(age)`, `starved`, `deferred(until)` |
| `why` | object | `{kind, trigger, at, chain[]}` — see §4.3 |
| `age`, `last_progress_at` | str | never synthesised |
| `worktree`, `branch`, `artifact_root` | str \| null | |
| `convoy`, `epic`, `cost`, `budget`, `eta` | | `eta` may be null; `budget` null means not set |
| `url` | str | every object exposes one |

**Molecule identity is the first design decision.** `mctl_core` has no Molecule (verified: the string appears in zero files under `mctl_core/`). The cheapest honest definition: a molecule is a **workflow root bead** carrying `gc.root_bead_id` / a formula invocation, and its steps are the beads that `tracks` it. Whatever you choose, put it in one place and name it — the census is one row per molecule and nothing else in the page works until that noun exists.

### 3.2 `molecules_show` / `steps_show`

Per step: `id`, `title`, `needs[]`, `layer` (**computed from `needs`, by dependency depth** — the page's DAG layout and step bar both depend on it), `state`, `agent`, `model_tier`, `duration`, `expected_artifacts[]`, `artifacts[]`, `evidence[5]`, `closed_at`.

Spine: `stops[]` with `{name, at, since_previous, kind}` where `kind ∈ reached | not_yet | skipped(reason) | repeated(n)`, plus `longest_gap` marked. **Loops and back-edges must be representable** — re-dispatch is claimed→claimed, and a strictly linear spine asserts a history that did not happen.

### 3.3 `fleet_sessions`

Straight from target-state §60.1. The page renders `template` (`gc.run-operator`, `gc.control-dispatcher`, `gc.mayor`, `gc.outside-clerk`), `state`, what it holds, `model`, `account`, `limit_state`, `idle_for`, plus **empty slots** as rows. `limit_state` must be derived server-side; the page deliberately has no logic to guess it.

### 3.4 `queue_status`

The CT5.1 partition, per rig: `ready_unclaimed`, `blocked[]` with `blocked_on`, `tail[]`, `starved[]`, `deferred[]` with expiry, `next_up[]` **plus `next_up_is_prediction: true`**. The page labels it a prediction; if you can make dispatch order deterministic and exposed, flip the flag and the label follows.

### 3.5 `city_health`, `liveness_board`

`city_health`: three-valued `data_plane` (`healthy | reachable_quarantined | unreachable`), latency **with the probe's own timeout stated**, `probe_results[]` each `succeeded | timed_out | refused`, `resources` (fds used/limit/trend, disk per rig, `flood_conditions[]` with since-when and growth), `per_rig[]` with reason.

`liveness_board`: `verdict ∈ alive | idle | dead | unknown`, `canaries[]` each `{order, expected_interval (declared by the order), last_fired, last_outcome, overdue_by, healthy}`, and `last_transit`. **`healthy` requires freshness AND a non-failing outcome** — the live case is an order that fires on schedule and errors every run, which reads fresh and is broken.

### 3.6 `gates_status` / `gates_evaluations`

The page treats a gate as a first-class object with per-rig statistics, so this needs: `gate_id` (fixed position), `checks`, `rule_id`, `registered_at`, `evaluated`, `passed`, per-rig breakdown, `beads_failing_now`, `enforcement[rig] ∈ in | out(reason, authorization)`, and `suspect: true` when zero failures over a long window. `gates_evaluations(gate, rig, limit)` returns the itemized list behind a rate — that list is the only way to distinguish a gate that never fails from one that never runs.

### 3.7 `events_list`

`gc events` already exists with JSON Lines and a `/stream` endpoint, so this is plumbing plus vocabulary:

- `tier ∈ alarm | milestone | progress | chatter`, **chatter default off** (order firings alone are ~2,400/day)
- `cause` / `response[]` — pairing is the proof-of-life mechanism; a cause with no response must be representable
- `subject` resolvable to an object `url`
- retention per tier
- the ticker's vocabulary is its own derived view, not an alias for bells / event beads / the log

### 3.8 Mutations — the lever ladder

Every lever on the page is `plan → apply → observe` over `effects.py`, with the interaction decided by `blast_radius`:

| Tier | Interaction the page implements | Actions |
|---|---|---|
| `low` | one click, undo offered | nudge, wake, run order now, set priority |
| `medium` | effect plan shown, confirm to apply | set N(R), add agents, close slot, drain, defer, redispatch, retry step, disable formula, set interval |
| `high` | effect plan **+ typed target name** | suspend rig, cancel molecule, close session, stop the city |
| `gated` | **the dashboard prepares the request and hands it to the existing gate** | branch delete, worktree removal, push, merge, PR, tag, bead delete, kill-switch |

`EffectPlan` needs `blast_radius` added to its payload so the front end reads the tier rather than hardcoding it. `plan.observe()` = before/after; the page renders it as a table after apply. Every applied plan is an event attributed to the dashboard (`city.events(kind="control")`).

**Standing prohibitions inherited in full:** nothing deletes a worktree, removes a `.repo.git`, closes a research-journal bead, drops a database, or touches a data-plane internal file — not at any tier, not with any confirmation.

---

## 4. New recording, in dependency order

### 4.1 `step.expected_artifacts` (keystone)
Declared at formula-authoring time, compiled into the step. Everything else in the evidence core depends on it: `is_complete` is derived from whether declared artifacts exist, which is what fixes the one genuine **defect** in the gap analysis (self-reported completion fails silently in the direction that makes healthy work look dead).

### 4.2 The evidence log
Append-only, per step, five link kinds: `claimed`, `agent_active`, `commit`, `artifact`, `step_closed`, each `{fired, at, source, detail}`. Needs `evidence.history` too — without it you know the current state but not when it last moved, and "when did this last do anything" is what separates slow from dead. `broken_at` is computed from the sequence; **the page marks a red ✕ only on the link `broken_at` names** — never positionally — so an unreached link on a healthy molecule renders as "not yet".

### 4.3 `molecule.why` — dispatch cause
`provenance.py` writes `dispatch-provenance.v1` with `routing_reason` and `source` today; the page needs `kind ∈ order | human_sling | brief_verdict | commission | retry | supersession`, the `trigger` object, `at`, and `chain[]` so retries link back. Recorded at dispatch, not inferred later. Adding a `cause` table to the existing provenance schema is the smallest path.

### 4.4 Worktree ownership
`created_by` and `step` at creation time, plus enumeration. Keep `is_orphan` (no live session, no open bead) and `is_registered` (git still knows it) as **separate flags** — different problems, different remedies. The live case: 14 orphans, 119.7 GB, zero overlap with `git worktree list`. `—` in `created_by` must render distinctly from "nobody"; the page relies on that.

### 4.5–4.8
`agent.account` + quota remaining · `city.uptime` intervals with `reason` (including `unknown`) · `Resources.flood_conditions` · `canary.last_outcome`. All four are "the city records what it did, not what it observed" — one design pass, not four.

---

## 5. Honesty invariants the API must be able to express

The page renders each of these. If the API cannot say them, the page lies.

1. **Three-valued, never boolean, for anything probed.** `healthy | degraded | unreachable`; a timed-out probe is not a zero.
2. **`None` means "there is none"; `Unknown` means "we did not look."** Two different renderings; never collapse them.
3. **Denominators always visible**, and a stalled denominator visible rather than flattering.
4. **A failed probe never renders as a value** — not zero, not blank.
5. **Derived states carry their inputs.** `state_evidence`, `P_measured_between`, `bound`.
6. **A degraded rig is always a row with a reason**, excluded from totals explicitly rather than silently.
7. **A check that could not have failed must not render as a check that passed.** Applies to gates (100% pass rate ⇒ suspect) and canaries (fresh but failing ⇒ not healthy).
8. **Deliberate ≠ accidental.** `deferred` and `dormant` must be distinguishable from `stranded`/`starved` in the data, not just in styling.
9. **Counts must agree with the list they open.** Every count the page shows is derived from the same call as its destination; keep aggregates and lists consistent server-side.
10. **Every list states its page size** and says when truncated.
11. **Laziness is contractual.** `.count` never materializes; bodies, transcripts, diffs and commit lists are never in a roster read. A slow section degrades alone as a named row with its reason.

---

## 6. Slice order, mapped to what appears on screen

Target-state §68 order, annotated with the prototype's UI so each slice ends with something true on screen:

| Slice | Backend | Page lights up |
|---|---|---|
| 0 | envelope / registry / trace / roster (**mostly built**) | SCOPE tabs, rig roster, degraded rig row |
| 1 | `molecules_list` + `molecules_show` | Molecules table, headline counts, molecule pages, step bar, DAG-by-progress |
| 2 | `fleet_sessions` | Agents table + agent pages, capacity occupancy, empty slots |
| 3 | `queue_status` | QUEUE column, population filters (ready / blocked / tail / starved / deferred) |
| 4 | `city_health` | Health block, flood alarm, three-valued probe rendering |
| 5 | evidence log + `expected_artifacts` | The five-link evidence chain and `broken_at` — the diagnostic core |
| 6 | `events_list` tiered | Live tape and Events page, cause/response pairing |
| 7 | `orders_status` + `formulas_catalog` | Orders class + Recent firings, canary board, formula catalog |
| 8 | `costs_summary` | Tokens plot, window selector, meta-work ratio |
| 9 | `worktrees_status` + `gates_status` | Worktrees class + pages, gate pages and per-rig rates |

Definition of done per slice is unchanged from §68 (typed schemas, envelope, registered diagnostics, `suggested_next_command`, dry-run + preconditions, `all_rigs` failure direction, degraded rows, loud on failure, smoke test + how it could have failed).

---

## 7. Where the prototype and reality disagree — reconcile deliberately

| Prototype assumes | Reality | Suggested resolution |
|---|---|---|
| A `Molecule` object | None exists in `mctl_core` | Define it as a workflow root + `tracks` steps (§3.1) |
| 45 open roots, 15 with pages | Fixture truth is 45 in `gascity_packs` | Page states both; keep aggregate and page-size honest |
| Canaries are a view over orders | Orders exist, `last_outcome` does not | Add `last_outcome`; do **not** add a Canary object |
| Gate objects with per-rig stats | No gate registry surface | `gates_status` (§3.6); reuse `diagnostics.toml` codes for the knowls |
| Worktree → molecule + agent on every row | Nothing records ownership | §4.4; render `—` where unrecorded |
| Tokens per bucket over 9 windows | `gc costs` is per-run spend | Bucketed `costs_summary`; flag `unpriced_count` rather than valuing at zero |
| `EffectPlan.blast_radius` | Not in the payload | Add it; the page's whole safety ladder reads off it |
| Rig set scoping (multi-select) | `all_rigs: bool` | Extend to `rigs: string[]`, keeping the bool for compatibility |
| Events carry `tier`, `cause`, `response` | `gc events` has kinds only | Derive tier in the backend; pairing is a recording change |
| Agent `pool` | Uncertain | The page dropped the column rather than assert it — restore only when it is real |

Anything in the prototype marked `[SYN]` is invented-to-be-realistic fixture data (evidence chains, worktree ownership, dispatch causes, token series, gate enforcement matrix). **Do not cite a `[SYN]` number as a measurement.** Everything marked `[OBS]` in `dashboard-fixtures.md` came off the live city on 2026-08-20 and is the right thing to test layout against: 3,923 open beads beside 0, 13 GB beside 240 MB, 223 ms beside 92 s, 634 benign findings beside 7 real ones, 45 identical titles.

---

## 8. Front-end contract notes (for whoever ports the prototype)

- **No JavaScript required.** The prototype uses client state for demonstration; in production every one of those states belongs in the query string, exactly as `mctl_dashboard/state.py` does it: SCOPE rig set, POPULATION filter, sort key + direction, token window, firings `last n`, event tiers. Sortable headings become `<a href>`; filters become GET forms.
- **Knowls, not tooltips.** `<details>`/`<summary>`, no script — reuse `knowl.py`. The page adds vocabulary entries (molecule, step, rig, agent, formula, gate, order, worktree, canary, the five states, each gate check, each rule id). **An unresolved token stays plain text**; extend the registry rather than inventing codes. The prototype's `MC-E…`-style invented codes were never used — all diagnostic knowls key on real `MBRF*` / `MWRK_*` / `MCTL_*` codes.
- **Style is fixed.** Tokens come from `theme.py`; tables use the `.ntdata` metrics (3px 7px cells, 2px rule under `thead`); the properties box and fixed sidebar follow LMFDB convention. No new colors, no `var(--…)` invention.
- **SVG caveat that will bite you:** the prototype's DAG draws boxes and edges in SVG but renders node labels as positioned HTML, because templated text inside `<svg><text>` did not render. In a server-rendered page you can emit `<text>` directly — but keep the layout deliberate and correct on first render: there is no zoom or pan, and a 35-step molecule needs the layered algorithm, not a naive one.
- **Loopback only.** The blast-radius ladder assumes the interface is not routable and needs no authentication. If that changes, **every tier is void** and an authorization model comes first. State this wherever the interface is deployed.

---

## 9. Suggested first PR

1. `mctl_core/molecules.py` — molecule identity, step graph from `tracks` + `needs`, `layer` by depth, progress with `counts_what`.
2. `MOLECULE_SCHEMA` + `STEP_SCHEMA` in `schemas.py`.
3. `molecules_list` / `molecules_show` in `TOOLS`, `CROSS_RIG_ARRAYS`, and `client.py::ALLOWED_TOOLS`.
4. `state` derived with `state_evidence` — and `dormant` distinguished from `stranded` in that first pass, because the fixture pair (`gsp-q31ot8` dormant, `gsp-8eqb3o` stranded) is indistinguishable from bead state alone and is the whole reason the derivation belongs in the backend.
5. A smoke test over the fixture proportions in `dashboard-fixtures.md`, plus the statement of how it could have failed.

That one PR turns on the largest area of the page and proves the pattern for the other thirteen calls.
