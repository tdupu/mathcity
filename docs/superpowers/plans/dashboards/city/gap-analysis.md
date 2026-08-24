# City dashboard — object-model gap analysis (#87)

**The master inventory. Everything else schedules against it.**
*"The gap between [the object model] and the running city is the development plan —
closing it, in vertical slices, is the work."*

**Verified against `tdupu/mathcity` origin/main `4d12140` on 2026-08-24**, by reading
`assets/scripts/mctl_core/` and the registered MCP `TOOLS` directly — not a manifest,
and not the earlier `~/Documents/misc/dashboard-gap-analysis.md` spike (2026-08-20/21),
which this supersedes. That spike's own closing caveat is the reason this re-verification
exists: *"a gap analysis is exactly the shape of artifact that can produce a confident wrong
answer: I searched for names."* Several of its `ABSENT` rows have since landed and were
reclassified here by confirming the tool answers, not by trusting the old table.

Source design docs: `dashboard-object-model.md`, `dashboard-screens.md`,
`dashboard-fixtures.md`, `dashboard-requests.md` (in `~/Documents/misc/`), and the
in-repo `HANDOFF.md` beside this file. `[SYN]` fixture values are invented — never cited
here as measurements; `[OBS]` came off the live city 2026-08-20.

---

## Taxonomy — four availability buckets, two axes

lumby specified `EXISTS / PARTIAL / ABSENT`. `PARTIAL` hides an order-of-magnitude cost
split, so it is broken into `PARTIAL` (reshape) vs `UNWRAPPED` (plumbing over `gc`/`bd`).

| Status | Meaning | Cost |
|---|---|---|
| **EXISTS** | mctl exposes it today, correct shape | none |
| **PARTIAL** | exposed, wrong shape or scope | small — reshape |
| **UNWRAPPED** | data lives in `gc`/`bd`/the store; mctl does not expose it | cheap — plumbing |
| **ABSENT** | nothing anywhere records it | expensive — new instrumentation |

Second axis — *why not*, which decides how a finding is filed:
**DEFECT** (does the wrong thing → a bug) · **GAP** (correct but missing/unused → a gap) ·
**NEVER-BUILT** (a capability nobody attempted → a feature, designed not blamed).

---

## What changed since the 2026-08-20 spike — reclassified by confirming the tool answers

The spike predates the MCP tool surface landing. Verified now in `mcp_server.py::TOOLS`:

| Object surface | Spike said | Now (origin/main 4d12140) | Landed by |
|---|---|---|---|
| `molecules_list` / `molecules_show` | ABSENT | **EXISTS** — `mctl_core/molecules.py`, both registered | #109/#111 |
| `orders_status` (+ `last_outcome`) | ABSENT | **EXISTS** — `mctl_core/orders.py`, folds outcome from event log | #156 |
| `formulas_catalog` | ABSENT | **EXISTS** | #156 |
| `fleet_sessions` | UNWRAPPED | **EXISTS** — slice 2 | #112 |
| `city_health` (three-valued) | UNWRAPPED | **EXISTS** — slice 4 | #114 |
| `gates_status` | ABSENT | **EXISTS** — `mctl_core/gates.py` | #119 |
| `blast_radius_registry` | n/a | **EXISTS** | #110 |
| `mayor_city_state` / `mayor_boot` / `mayor_conservation` | not modelled | **EXISTS** | — |
| `step.expected_artifacts` **declaration** | ABSENT | **PARTIAL** — declared as `gc.expected_artifacts.v1` step metadata; **no Python reads it** | #142 (506bbdb) |

Rendering caveat (#153): several tools above are backend-only. `fleet_sessions`,
`city_health`, `gates_status`, `blast_radius_registry` render on the served `/city` page
(`app._city_operations` → `screens/city.py`). `events_list` has a core module (`ticker.py`)
but **no MCP tool**, so `/city` shows it via `city_screen.unwired()` — an honest named gap.

**Still ABSENT (no core module, zero refs) — the open build set:**
`queue_status` (#113) · `costs_summary` (#118) · `worktrees_status` (#120).
**Half-built:** the evidence core (#115) — declaration landed, derivation and chain have not.

---

## Headline findings

### 1. The molecule noun now exists (was the single largest structural gap)
`mctl_core/molecules.py` defines it: **a molecule is one execution of one formula, identity =
its root bead id** (`gc.kind == "workflow"`); steps carry `gc.root_bead_id` pointing at the
root. `describe()` deliberately **omits `state`** — `advancing/stalled/stranded/dormant`
require the evidence chain (#115), and a state it cannot derive would be a plausible-empty
result. That omission is correct and is exactly what #115 must fill honestly.

### 2. Slice 0 (the contract layer) is built — confirmed
Response envelope (`diagnostics/trace_id/artifact_trust/untrusted_diagnostics` required in
`schemas.py`), cross-rig fan-out with degraded-rig-as-named-row
(`city.py::for_each_rig`/`merge_outcomes`/`rig_*_diagnostic`), effect plans + dry-run +
`blast_radius` (`effects.py`, #110), phased trace (`trace.py`), the diagnostics registry
(`diagnostics.py` + `assets/mctl/diagnostics.toml`), three-valued probe (`liveness.py`),
`ALLOWED_TOOLS` allowlist, URL-as-state (`state.py`), theme tokens (`theme.py`). New objects
extend this; they do not rebuild it.

### 3. The evidence core (#115) is the genuine DEFECT, and it is only half-fixable today
`#142` landed the **declaration** (`gc.expected_artifacts.v1` on steps) but **no code reads
it**, and `step.is_complete` still comes from bead-closed state — the exact self-report defect
#115 was filed against. Buildable now: derive `is_complete` from declared-vs-actual artifacts.
**Not buildable honestly:** the full five-link chain — measured on the live event log, four of
five links (`claimed`, `agent_active`, `commit`, `artifact`) have **no emitter**, and
`step_started` is ~30× rarer than `step_completed`. A positional `broken_at` would blame link 1
on every healthy step — the defect inverted (P6.2). So the chain must render unrecorded links as
a distinct **"no recorder"** state, never as fired and never as the break.

---

## The classification table

Status ∈ EXISTS / PARTIAL / UNWRAPPED / ABSENT. **Bold** = the four open slices schedule here.

### City / Rig
| Property | Status | What it would take |
|---|---|---|
| `city.rigs`, `rig.name/prefix/path/beads`, `degraded_reason` | EXISTS | `context_*`, `beads.py`, `city.py` diagnostics |
| `city.molecules` / `rig.molecules` | **EXISTS** | `molecules_list` (#111) |
| `city.agents` | EXISTS | `fleet_sessions` (#112) |
| `city.health` | EXISTS | `city_health` (#114) |
| `city.worktrees` | **ABSENT** | `worktrees_status` (#120) — enumerate worktrees, `created_by`/`step` at creation |
| `city.events` | UNWRAPPED | `ticker.py` exists; no MCP tool (#116 unwired) |
| `city.formulas` | EXISTS | `formulas_catalog` |
| `city.epics`/`.convoys` | UNWRAPPED | `gc convoy list`, `bd list -t epic` |
| `city.queue` | **ABSENT (as a tool)** | `queue_status` (#113) — six populations |
| `city.capacity` | UNWRAPPED | `city.toml` + pool state; no mctl read path |
| `city.usage` / `agent.usage` (quota remaining) | ABSENT | `gc costs` is spend, not remaining |
| `city.uptime` / `city.is_alive` | ABSENT | on/off transitions with reason — NEVER-BUILT |

### Molecule / Step / Evidence (the #115 core)
| Property | Status | Note |
|---|---|---|
| `id`/`rig`/`formula`/`worker`/`artifact_root`/`convoy` | EXISTS | `molecules.describe()` |
| `steps` (id/title/status/kind) | EXISTS | `describe_with_steps()` |
| `step.needs` / `layer` | UNWRAPPED / ABSENT | in compiled formula; `layer` derivable from `needs`, uncomputed |
| `step.expected_artifacts` | **PARTIAL** | declared `gc.expected_artifacts.v1` (#142); **nothing reads it** — #115 |
| `step.artifacts` (actual) | EXISTS | `gc.build.*` metadata via `_artifacts_of()` |
| `step.is_complete` (derived) | **PARTIAL → DEFECT** | today = bead closed; must derive from declared-vs-actual — #115 |
| `molecule.state` (5 values) | **ABSENT** | needs evidence chain — #115/#88; `stranded`≠`dormant` is mctl's job |
| `evidence.*` five links | **ABSENT** | 4 of 5 have no emitter — chain NOT buildable as specified (#115 comment) |
| `evidence.broken_at`/`history`/`last_motion_at` | ABSENT | depends on the above; must not positionally false-blame |
| `molecule.why` (dispatch cause) | ABSENT | provenance stores the command, not the cause — NEVER-BUILT |

### Agent / Worktree
| Property | Status | Note |
|---|---|---|
| `agent.id/template/state/model/last_active/idle_for/worktree` | EXISTS/UNWRAPPED | `fleet_sessions` + `gc session list` |
| `agent.account`/`usage`/`limit_state` | PARTIAL/ABSENT | `limit_state` returns `unknown` honestly; account/quota not recorded |
| `agent.claims` (work history) | ABSENT | no claim history |
| Worktree — every property | **ABSENT** | `worktrees_status` (#120): path(key)/rig/branch/molecule/`created_by`/`step`/`is_orphan`/`is_registered`/`harvestable`/commits. `—` (unrecorded) ≠ "nobody". Live: 14 orphans ~119.7 GB, zero overlap with `git worktree list`; row key = path (ids repeat) |

### Queue / Costs / Health / Gates / Events
| Property | Status | Note |
|---|---|---|
| `queue.ready_unclaimed/blocked/tail/starved/deferred/next_up` | **ABSENT (as a tool)** | `queue_status` (#113). `next_up_is_prediction: true` REQUIRED — `work.py:185 ready_work()` has no ordering; dispatcher sorts `--sort oldest`, discarding priority. `deferred`≠`tail`/`starved` in the data |
| `costs.*` bucketed / meta-work ratio | **ABSENT (as a tool)** | `costs_summary` (#118). `gc costs` = per-run spend; needs bucketing by window. `unpriced_count`, never value-at-zero. Meta-work = city rigs (`gascity*`, `mathcity`) vs math rigs; trend is the alarming view. Unit tokens + worker-hours; bead count is wrong |
| `data_plane` (3-valued), `per_rig`, probes | EXISTS/PARTIAL | `city_health`, `liveness.py` |
| `resources.*` / `flood_conditions` | ABSENT | FD/disk thresholds — NEVER-BUILT |
| `canaries` / `canary.last_outcome` | PARTIAL/EXISTS | `orders_status` now folds `last_outcome`; canary is a view over orders, not a new object |
| gates (per-rig stats) | EXISTS (defs) / ABSENT (eval store) | `gates_status` lists defs; pass/fail stats deliberately absent (no eval store) not zero |
| events `tier`/`cause`/`response` | UNWRAPPED/ABSENT | `ticker.py`; no MCP tool; tier vocabulary + cause/response pairing |

---

## Schedule — what the four open slices build against this table

| Slice | Fills these rows | Status classified here |
|---|---|---|
| **#115** keystone | `step.expected_artifacts` (read), `step.is_complete` (derive), evidence links (honest) | PARTIAL → the one DEFECT |
| **#113** `queue_status` | the six queue populations + `next_up_is_prediction` | ABSENT-as-tool |
| **#118** `costs_summary` | bucketed tokens, meta-work ratio, `unpriced_count` | ABSENT-as-tool |
| **#120** `worktrees_status` | every worktree property, `created_by`/`step`, orphan/registered split | ABSENT |

Each must **render** in the served dashboard (#153): a backend tool that no page consumes is a
milestone, not a completion.

## Confidence / what was not re-verified
**Verified directly:** the `TOOLS` registry membership and handlers; `molecules.py` identity and
the deliberate `state` omission; absence of any `queue_status`/`costs_summary`/`worktrees_status`
reference in `mctl_core/`; `gc.expected_artifacts.v1` declared with no Python reader; the `/city`
render path. **Inferred, not re-run:** the live event-log link counts (from #115's owner
measurement, 2026-08-23) and the 14-orphan/119.7 GB worktree figure (2026-08-20 `[OBS]`) — cited
as prior measurements, not re-measured here (the hecke worktree freeze forbids the traversal).
