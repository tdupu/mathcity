# City dashboard — object-model gap analysis (#87)

**The master inventory. Everything else schedules against it.**
*"The gap between [the object model] and the running city is the development plan —
closing it, in vertical slices, is the work."*

**Re-verified against `tdupu/mathcity` origin/main `a2f85c3` on 2026-08-25**, by CALLING
every named tool over the live MCP surface (`mctl mcp serve --client-class internal
--city ~/gt --rig mathcity`, JSON-RPC `tools/call`) and recording each ACTUAL response —
state, diagnostics, and payload keys — not by reading `mcp_server.py::TOOLS`. This
supersedes the earlier `~/Documents/misc/dashboard-gap-analysis.md` spike (2026-08-20/21)
and corrects the prior pass of this file (`4d12140`, 2026-08-24).

That prior pass claimed the method it did not use. It says its rows were reclassified *"by
confirming the tool answers, not by trusting the old table,"* yet marked `queue_status`,
`costs_summary` and `worktrees_status` `ABSENT — no core module, zero refs` when all three
have a core module (`queue.py`, `costs.py`, `worktrees.py`), are registered in `TOOLS`, are
in the dashboard `ALLOWED_TOOLS`, and answer on call. The irony is the document's own: it
opens by quoting its predecessor — *"a gap analysis is exactly the shape of artifact that
can produce a confident wrong answer: I searched for names"* — and then searched for names.
**Registration is not answering, and answering is not reachability** — the only cure is to
call the tool the way its consumer does, which is what this pass does (both a correct
rig-scoped call and the dashboard's own rig-null path).

Source design docs: `dashboard-object-model.md`, `dashboard-screens.md`,
`dashboard-fixtures.md`, `dashboard-requests.md` (in `~/Documents/misc/`), and the
in-repo `HANDOFF.md` beside this file. `[SYN]` fixture values are invented — never cited
here as measurements; `[OBS]` came off the live city 2026-08-20.

---

## Taxonomy — five availability buckets, two axes

lumby specified `EXISTS / PARTIAL / ABSENT`. `PARTIAL` hides an order-of-magnitude cost
split, so it is broken into `PARTIAL` (reshape) vs `UNWRAPPED` (plumbing over `gc`/`bd`).
The 2026-08-25 re-verification adds `UNREACHED`: `EXISTS / PARTIAL / UNWRAPPED / ABSENT`
had no cell for a tool that is built, registered, and answers on a correct call, yet is
refused on the exact path its consuming surface uses — so the four-bucket vocabulary forced
`queue_status` and `costs_summary` into `ABSENT`, the one label that is provably false.

| Status | Meaning | Cost |
|---|---|---|
| **EXISTS** | mctl exposes it today, correct shape | none |
| **PARTIAL** | exposed, wrong shape or scope | small — reshape |
| **UNWRAPPED** | data lives in `gc`/`bd`/the store; mctl does not expose it | cheap — plumbing |
| **UNREACHED** | built + registered + answers on a correct call, but the surface that consumes it calls it on a path that refuses, so the operator sees the refusal, not the data | cheap — fix the caller's context, not the tool |
| **ABSENT** | nothing anywhere records it | expensive — new instrumentation |

`UNREACHED` is distinct from `#153` "renders nowhere" (a backend tool no page calls at all):
here the page *does* call the tool, but with the wrong context. It is a caller **DEFECT** on
the *why-not* axis, not a missing capability — the fix lives in the surface (`#113`/`#118`:
the dashboard runs `rig=null` from the source checkout, so a rig-scoped read falls back to
CWD and hits `MCTL_CONTEXT_SOURCE_CHECKOUT`), never in the tool.

Second axis — *why not*, which decides how a finding is filed:
**DEFECT** (does the wrong thing → a bug) · **GAP** (correct but missing/unused → a gap) ·
**NEVER-BUILT** (a capability nobody attempted → a feature, designed not blamed).

---

## What changed since the 2026-08-20 spike — reclassified by confirming the tool answers

The spike predates the MCP tool surface landing. Each row below was re-confirmed 2026-08-25
by CALLING the tool (`tools/call`, `--rig mathcity`) and reading its response, not by finding
it in `mcp_server.py::TOOLS` — registry membership was the prior pass's error:

| Object surface | Spike said | Now (origin/main a2f85c3) | Landed by |
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

**Corrected 2026-08-25 — the "open build set" was already built:** the prior pass listed
`queue_status`, `costs_summary` and `worktrees_status` as "Still ABSENT (no core module,
zero refs)." All three have a core module and answer on call:
- `queue_status` (#113) — **UNREACHED**. `queue.py`, registered + allowlisted; rig-scoped
  call returns `state: healthy` (ready 193 / blocked 132 / tail 40 / starved 53 / next_up 20).
  Fails ONLY on the dashboard's own path — `rig=null`, CWD in the source checkout —
  with `MCTL_CONTEXT_SOURCE_CHECKOUT`. The tool is done; the caller is the defect (#113 fix).
- `costs_summary` (#118) — **UNREACHED**, same shape. Rig-scoped `state: healthy`
  (total_tokens 714,557,893, meta_work_ratio 14.90, 58 windows; carries `MCOS_RIG_UNRESOLVED`).
  Refused on the dashboard's rig-null path with `MCTL_CONTEXT_SOURCE_CHECKOUT`.
- `worktrees_status` (#120) — **EXISTS (degraded)**, NOT unreached. `worktrees.py` answers on
  BOTH the rig-scoped and the rig-null path (`state: degraded`, 219 worktrees, harvestable 1),
  carrying completeness diagnostics `MWKT_RIG_UNREACHABLE / SIZE_UNKNOWN / ORPHAN_UNDERIVABLE /
  CREATED_BY_UNRECORDED`. It renders; it does not refuse.

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

Status ∈ EXISTS / PARTIAL / UNWRAPPED / UNREACHED / ABSENT. **Bold** = the slices that still
schedule against this table (of the original four, `#113` and `#118` are UNREACHED and `#120`
EXISTS-degraded as of 2026-08-25; only `#115` remains a true build).

### City / Rig
| Property | Status | What it would take |
|---|---|---|
| `city.rigs`, `rig.name/prefix/path/beads`, `degraded_reason` | EXISTS | `context_*`, `beads.py`, `city.py` diagnostics |
| `city.molecules` / `rig.molecules` | **EXISTS** | `molecules_list` (#111) |
| `city.agents` | EXISTS | `fleet_sessions` (#112) |
| `city.health` | EXISTS | `city_health` (#114) |
| `city.worktrees` | **EXISTS (degraded)** | `worktrees_status` (#120) answers — 219 worktrees, `state: degraded` (`MWKT_RIG_UNREACHABLE`/`SIZE_UNKNOWN`/`ORPHAN_UNDERIVABLE`/`CREATED_BY_UNRECORDED`); `created_by`/`step` still unrecorded |
| `city.events` | UNWRAPPED | `ticker.py` exists; no MCP tool (#116 unwired) |
| `city.formulas` | EXISTS | `formulas_catalog` |
| `city.epics`/`.convoys` | UNWRAPPED | `gc convoy list`, `bd list -t epic` |
| `city.queue` | **UNREACHED** | `queue_status` (#113) answers rig-scoped (`healthy`, 6 populations); dashboard's rig-null path refuses (`MCTL_CONTEXT_SOURCE_CHECKOUT`) |
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
| Worktree — every property | **EXISTS (degraded)** | `worktrees_status` (#120) answers on call — 219 worktrees, `harvestable_count: 1`, row key = path. But `state: degraded`: `MWKT_ORPHAN_UNDERIVABLE` (so the `orphans: 0` it returned is "cannot derive", NOT a measured zero), `MWKT_SIZE_UNKNOWN` (no GB figure), `MWKT_CREATED_BY_UNRECORDED`, `MWKT_RIG_UNREACHABLE`. The enumeration exists; `created_by`/`step`/size/orphan-status are the unrecorded dimensions. Prior "14 orphans ~119.7 GB" was a 2026-08-20 `[OBS]`, not reproducible from the tool today |

### Queue / Costs / Health / Gates / Events
| Property | Status | Note |
|---|---|---|
| `queue.ready_unclaimed/blocked/tail/starved/deferred/next_up` | **UNREACHED** | `queue_status` (#113) answers rig-scoped: `state: healthy`, ready 193 / blocked 132 / tail 40 / starved 53 / next_up 20, `next_up_is_prediction: true`. Refused only on the dashboard's rig-null path (`MCTL_CONTEXT_SOURCE_CHECKOUT`). `deferred`≠`tail`/`starved` in the data holds |
| `costs.*` bucketed / meta-work ratio | **UNREACHED** | `costs_summary` (#118) answers rig-scoped: `state: healthy`, total_tokens 714,557,893, meta_work_ratio 14.90, 58 windows, `unpriced_count`/`unclassified_tokens` present (carries `MCOS_RIG_UNRESOLVED`). Refused only on the dashboard's rig-null path. Bucketing by window is done; caller context is the gap |
| `data_plane` (3-valued), `per_rig`, probes | EXISTS/PARTIAL | `city_health`, `liveness.py` |
| `resources.*` / `flood_conditions` | ABSENT | FD/disk thresholds — NEVER-BUILT |
| `canaries` / `canary.last_outcome` | PARTIAL/EXISTS | `orders_status` now folds `last_outcome`; canary is a view over orders, not a new object |
| gates (per-rig stats) | EXISTS (defs) / ABSENT (eval store) | `gates_status` lists defs; pass/fail stats deliberately absent (no eval store) not zero |
| events `tier`/`cause`/`response` | UNWRAPPED/ABSENT | `ticker.py`; no MCP tool; tier vocabulary + cause/response pairing |

---

## Schedule — what still builds against this table (revised 2026-08-25)

Of the four slices the prior pass scheduled, only **#115** remains a true build. #113 and #118
are caller-side defects (the tool answers; the dashboard reaches it with the wrong context),
and #120 has landed in a degraded state.

| Slice | Fills these rows | Status classified here (2026-08-25) |
|---|---|---|
| **#115** keystone | `step.expected_artifacts` (read), `step.is_complete` (derive), evidence links (honest) | PARTIAL → the one remaining DEFECT/build |
| **#113** `queue_status` | the six queue populations + `next_up_is_prediction` | **UNREACHED** — tool answers `healthy`; fix the dashboard's rig context / add `all_rigs` (mc-72ue) |
| **#118** `costs_summary` | bucketed tokens, meta-work ratio, `unpriced_count` | **UNREACHED** — same caller fix as #113 (mc-72ue) |
| **#120** `worktrees_status` | every worktree property, `created_by`/`step`, orphan/registered split | **EXISTS (degraded)** — enumeration answers (219); `created_by`/`step`/size/orphan unrecorded |

For #113/#118 the render path already exists (`/city` calls both and renders the refusal via
`app.py`); the defect is the caller's context, not a missing consumer. The #153 rule still
holds for genuinely backend-only tools — a page that shows a tool's refusal is not a completion
either.

## Confidence / what was not re-verified
**Called and recorded first-hand (2026-08-25, origin/main `a2f85c3`, `mctl mcp serve
--client-class internal --city ~/gt --rig mathcity`):** `queue_status` (`healthy`, 6
populations), `costs_summary` (`healthy`, 58 windows), `worktrees_status` (`degraded`, 219),
`molecules_list`, `orders_status` (`unreachable`, `MORD_CATALOG_NOT_READ`), `formulas_catalog`
(`healthy`), `fleet_sessions`, `city_health`, `gates_status`, `blast_radius_registry`,
`mayor_city_state` (`up`) — each returned a response, confirming the EXISTS/UNREACHED rows by
answer, not by registry membership. The dashboard's own refusal path was reproduced directly:
`queue_status`/`costs_summary` called with `rig=null` from the source-checkout CWD return
`MCTL_CONTEXT_SOURCE_CHECKOUT` and no state.

**Corrected from the prior pass:** that pass's "Verified directly" list asserted "absence of any
`queue_status`/`costs_summary`/`worktrees_status` reference in `mctl_core/`" — false; all three
have modules (`queue.py`/`costs.py`/`worktrees.py`) and are registered + allowlisted. That single
line is the root of the three wrong rows: it verified absence-of-name, which registry membership
already contradicted.

**Not re-run:** the live event-log link counts for #115 (from its owner's 2026-08-23
measurement); the per-tool payload *correctness* beyond state/shape (e.g. whether `queue_status`
counts are themselves right — only that it answers healthy); and the `molecules_show` /
`mayor_boot` / `mayor_conservation` tools, which need specific ids and were not called.

**Every count above is a live snapshot, not a stable figure — read it with its timestamp.**
Two independent reads ~20 min apart on this same commit drifted: `queue_status` ready
187→193 / blocked 129→132; `costs_summary` total 711,156,548→714,557,893, windows 56→58,
`meta_work_ratio` 14.55→14.90 (climbing in real time). The numbers here are cited as evidence
that the tool *answers*, and for order-of-magnitude, never as fixed measurements — quoting one
back later without its timestamp would reintroduce exactly the staleness this pass corrects.
