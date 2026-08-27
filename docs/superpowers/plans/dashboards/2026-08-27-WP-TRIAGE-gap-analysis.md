# WP-TRIAGE — Dashboard object-model gap analysis (source-verified)

**Bead:** `mc-1qrg` (GH #87). **Branch:** `repair/triage`. **Date:** 2026-08-27.
**Target tree:** `74eeac0`. **Verifies:** the mctl MCP surface against the
dashboard object-model spec, property by property.

**What this is.** For every object and property in the dashboard object model
(`~/Documents/misc/dashboard-object-model.md`), a classification of what
`mctl` exposes **today, verified against source** — the `TOOLS` tuple in
`mctl_core/mcp_server.py` (lines 1446–2884) and the implementation modules under
`mctl_core/`. The governing sentence, from the object model: *"The gap between
this document and the running city **is the development plan** — closing it, in
vertical slices, is the work."*

**Confirm rather than trust (P5.4 / P6.2).** This supersedes the earlier Spike 3
draft (`~/Documents/misc/dashboard-gap-analysis.md`, 2026-08-20/21), whose
headline finding — *"mctl has no Molecule. It has no Worktree, Convoy, Epic,
Session, or Order either"* — **is now stale.** Since that draft, multiple slices
landed: `molecules_list/show`, `worktrees_status`, `queue_status`,
`orders_status`, `city_health`, `costs_summary`, `gates_status`, and the Step
evidence chain all now exist. Every row below was re-checked by reading the tool
output schemas and module code on `74eeac0`, not by trusting the prior narrative
and not by name-matching. Citations are `module.py:line` or a tool name.

---

## Taxonomy — four buckets

The bead specifies `EXISTS / PARTIAL / ABSENT`. `PARTIAL` hides an
order-of-magnitude cost split, so the table keeps the Spike-3 four-way form: the
difference between *"the data exists in `gc`/`bd`, just unwired"* and *"nothing
records it"* is the difference between an afternoon and a schema change.

| Status | Meaning | Cost to close |
|---|---|---|
| **EXISTS** | An mctl tool exposes it today, correct shape | none |
| **PARTIAL** | Exposed but wrong shape/scope, or a schema field is a declared placeholder (`"unrecorded"`, `"unknown"`, always-null) awaiting an emitter | small — reshape / wire an emitter |
| **UNWRAPPED** | Data/logic exists in a module or in `gc`/`bd`, but **no MCP tool exposes it** | cheap — plumbing |
| **ABSENT** | Nothing anywhere records it | expensive — new instrumentation |

---

## Complete tool inventory (verified)

The `TOOLS` tuple exposes 42 tools: `orders_status`, `formulas_catalog`,
`queue_status`, `costs_summary`, `worktrees_status`, `context_resolve`,
`context_rigs`, `fleet_sessions`, `blast_radius_registry`, `gates_status`,
`city_health`, `dashboard_status`, `dashboard_restart`, `molecules_list`,
`molecules_show`, the `briefs_*` family (11), `commission_brief`,
`decisions_to_briefs`, `create_issue_bead`, `create_github_issue`,
`create_defect_bead`, `bead_comment`, `standardize_github_issue`,
`work_ready/status/provenance/dispatch/claim/dispatch_event`, `trace_show`,
`trace_replay_preview`, `mayor_city_state`, `mayor_boot`, `mayor_conservation`.

**There is NO tool for:** events/EventStream, capacity (read or write),
usage/quota, uptime, the liveness canary board, epics, or convoys (verified:
`grep -c 'name="(capacity|usage|uptime|events_list|epics|convoys)'` → 0).
`events.py` is a 12-line JSONL append helper; `ticker.py` (tier vocabulary +
cause→response pairing) and the canary logic are **not imported by
`mcp_server.py`** — they are built but unwired.

---

## The tables

### `City` — root
| Property | Status | Source / what it takes |
|---|---|---|
| `rigs` | **EXISTS** | `context_rigs`, `context_resolve.registered_rigs` |
| `molecules` | **PARTIAL** | `molecules_list` is **rig-scoped**; no city-wide/`all_rigs` param (mcp_server:2123). Object model requires unfiltered city-wide census |
| `agents` | **PARTIAL** | `fleet_sessions` is city-scoped but thin (see Agent) |
| `worktrees` | **EXISTS** | `worktrees_status`, city-scope (mcp_server:1746) |
| `events` | **UNWRAPPED** | `ticker.py` computes tiers + cause/response over `.gc/events.jsonl`; no tool wires it |
| `formulas` | **PARTIAL** | `formulas_catalog` returns names only (orders.py:258–273) |
| `epics` / `convoys` | **ABSENT** (as objects) | molecule row carries a raw `convoy` id string (molecules.py:389); no grouping object/tool |
| `queue` | **EXISTS** | `queue_status` |
| `capacity` | **ABSENT** | no tool; only a comment in blast_radius.py:45 |
| `health` | **EXISTS** | `city_health` |
| `usage` | **ABSENT** | fleet.py:184–186: account/window/weekly/resets all unrecorded |
| `uptime` | **ABSENT** | no module, no tool, no store read |
| `is_alive` | **PARTIAL** | `mayor_city_state` gives four-valued up/idle/down/unknown (mcp_server:2783); not the canary/transit-evidenced `is_alive` |

### `UptimeLog` — **ABSENT entirely.** No module, no tool, no store read.

### `Rig`
| Property | Status | Source |
|---|---|---|
| `name` / `prefix` / `path` | **EXISTS** | `context_rigs.rigs[].rig_id/rig_root/rig_db` |
| `state` / `degraded_reason` | **PARTIAL** | `city_health.per_rig[].state` (healthy/degraded/unreachable/unknown) + `reason` (mcp_server:2006) — health-scoped, not a lifecycle `active/suspended/degraded`; `mayor_city_state.suspended_rigs` lists suspended (2793) |
| `molecules`/`agents`/`worktrees`/`beads`/`queue`/`epics`/`convoys` | **PARTIAL** | reachable via separate rig-scoped tools, not as a `Rig` object |
| `capacity` / `dispatcher` | **ABSENT** | — |

### `Molecule` — large upgrade vs prior draft (now EXISTS as an object, #109)
| Property | Status | Source |
|---|---|---|
| `id` / `rig` / `formula` / `formula_version` | **PARTIAL** | molecules.py:370–394 has id, formula, rig, `contract`, `graph_key`; **no version field** |
| `source_bead` / `root_bead` | **PARTIAL** | id **is** the root bead; no `source_bead` link (re-dispatch mints a new root, molecules.py:8) |
| `steps` | **EXISTS** | `describe_with_steps`, `with_steps` param (molecules.py:398) |
| `progress` | **ABSENT** | no (completed,total,percent) aggregate |
| `evidence` (molecule rollup) | **PARTIAL** | per-step `evidence.links` + `broken_at` exist; no molecule-level rollup |
| `state` (advancing/stalled/stranded/dormant/complete) | **ABSENT — by ruling** | molecules.py:28–35, #115: omitted deliberately because 4 of 5 evidence links have no emitter; a state it cannot derive is a plausible-empty-result failure, so the key is omitted rather than defaulted |
| `is_*` predicates | **ABSENT** | not derivable without state |
| `worker` | **EXISTS** | `gc.session_name` (molecules.py:384) |
| `worktree` | **ABSENT** | not joined |
| `artifact_root` / `branch` | **PARTIAL** | `artifact_root` EXISTS (molecules.py:388); `branch` ABSENT |
| `why` (DispatchCause) | **UNWRAPPED** | `work_provenance`/`DispatchProvenance` records dispatch command/observer for **briefed work beads** (provenance.py); molecules carry no `why`, no kind taxonomy, no `chain` |
| `timeline` / `cost` / `budget` / `eta` | **ABSENT** | molecule carries created_at/updated_at only |
| `convoy` / `epic` | **PARTIAL** | raw `convoy` id string EXISTS (molecules.py:389); `epic` ABSENT |

### `Step` and `Evidence` — the A–E chain (the headline upgrade, #115/#142)
| Property | Status | Source |
|---|---|---|
| `id` / `title` / `status` / `kind` | **EXISTS** | `_step_view` (molecules.py:331–349) |
| `needs` / `layer` | **ABSENT** | not built |
| `expected_artifacts` | **EXISTS** | `gc.expected_artifacts.v1`, declared up front (molecules.py:145,166) — *the keystone the prior draft called ABSENT* |
| `artifacts` | **EXISTS** | `gc.build.*` (molecules.py:115) |
| `is_complete` | **EXISTS — three-valued** | complete/incomplete/**unknown**, derived from declared-vs-actual artifacts, **never from bead status** (molecules.py:178–202); carries `declared`/`present`/`missing` inputs. *This retires the prior draft's one genuine DEFECT (self-reported completion).* |
| `agent` / `model_tier` / `duration` | **ABSENT** | not built |
| `evidence.claimed` / `agent_active` / `commit` | **PARTIAL** (`not_recorded`) | all three have **no emitter** — honest tri-state placeholder (molecules.py:220,241) |
| `evidence.artifact` | **EXISTS** | recorded/not_yet from `gc.build.*` (molecules.py:248) |
| `evidence.step_closed` | **EXISTS** | recorded/not_yet from bead status (molecules.py:267) |
| `evidence.broken_at` | **PARTIAL** | only the one checkable break (closed-but-declared-artifact-missing); never names the 3 unemitted links (molecules.py:279–328) |
| `evidence.furthest` / `last_motion_at` / `history` | **ABSENT** | no timeline/history emitter |

**Reading this block:** the evidence core is now a *buildable slice*, not a
blank. Two links (`artifact`, `step_closed`) fire; three (`claimed`,
`agent_active`, `commit`) are declared placeholders awaiting an emitter. Closing
those three emitters is the single highest-leverage item on the plan — it is what
turns `molecule.state` from ABSENT-by-ruling into derivable.

### `Agent` (`fleet_sessions`, fleet.py:194–256)
| Property | Status | Source |
|---|---|---|
| id/name (`qualified_name`), `template`, `state`, `holds` | **EXISTS** | mcp_server:1835–1840 |
| `pool` | **ABSENT** | — |
| `model` | **PARTIAL** | set to session **provider**, not the model name (fleet.py:228) |
| `provider` | **PARTIAL** | conflated into `model` |
| `account` | **ABSENT** | always null (fleet.py:229; schema: "Not recorded today") |
| `usage` | **ABSENT** | fleet.py:184–186 |
| `current_step` / `current_molecule` / `worktree` | **ABSENT** | no join |
| `last_active` / `idle_for` | **EXISTS** | `idle_for_seconds` + `idle_reason` (fleet.py:220) |
| `limit_state` (none/rolling_window/weekly) | **PARTIAL** | always `"unknown"` — `MCTL_FLEET_LIMIT_STATE_UNRECORDED` (fleet.py:182) |
| `transcript` / `claims` | **ABSENT** | — |

### `Worktree` (`worktrees_status`, worktrees.py)
| Property | Status | Source |
|---|---|---|
| `path` / `rig` / `branch` | **EXISTS** | mcp_server:1693–1695 |
| `created_by` / `step` / `molecule` | **PARTIAL** | literal `"unrecorded"` sentinel — nothing records at creation (mcp_server:1700–1707). *Renders "unknown" distinctly from "nobody" — the absence-is-data rule.* |
| `created_at` | **PARTIAL** | `age_seconds` only |
| `last_activity` | **ABSENT** | — |
| `commits` | **EXISTS** | real git ancestry count (mcp_server:1720) |
| `is_orphan` | **PARTIAL** | always null — `MWKT_ORPHAN_UNDERIVABLE` (mcp_server:1711) |
| `is_registered` | **PARTIAL** | always true by construction (git-worktree-list only, mcp_server:1717) |
| `size` | **EXISTS** | `size_bytes` |
| `dirty` | **ABSENT** | not computed |
| `harvestable` | **EXISTS** | real prunable flag (mcp_server:1719) |
| `merged` (extra) | **EXISTS** | real ancestry fact |
| `url` | **EXISTS** | mcp_server:1721 |

### `Event` / `EventStream` — **ABSENT as a tool; UNWRAPPED in modules**
`at`/`tier`/`kind`/`subject`/`detail`/`cause`/`response`/`url`: the tier
classification and cause→response pairing (the proof-of-life mechanism) are fully
implemented in `ticker.py` (`TIER_BY_TYPE`, `pair_causes`, `select`, `page`), but
**no MCP tool exposes them**. `event.response` = `pair_causes` unanswered/response
(ticker.py:103). Only consumer today: `orders_status` folds `order.*` outcomes
(orders.py:88). `work_dispatch_event` *writes* a provenance event bead — not a
stream reader. **Wiring one `events`/ticker tool is the cheapest high-value item.**

### `Health` (`city_health`) — strong EXISTS
| Property | Status | Source |
|---|---|---|
| `data_plane` (three/four-valued) | **EXISTS** | healthy/reachable_quarantined/unreachable/unknown (mcp_server:1941) |
| `supervisor` / `fleet_server` / `dispatchers` | **ABSENT** | not probed as components |
| `resources.file_descriptors` | **EXISTS** | fds_used/limit vs `kern.maxfilesperproc`; `fds_trend` always "unknown" (mcp_server:1966) |
| `resources.disk` | **EXISTS** | `disk_per_rig` (mcp_server:1969) |
| `resources.flood_conditions` | **EXISTS** | resource/detail/growth/since (mcp_server:1982) |
| `per_rig` | **EXISTS** | mcp_server:2000 |
| `probes` | **EXISTS** | `probe_results` succeeded/timed_out/refused + latency (mcp_server:1945) |

### `Liveness` / canary board — mostly ABSENT, substrate UNWRAPPED
`is_alive.verdict`: **PARTIAL** via `mayor_city_state` (up/idle/down/unknown,
city-level). `canaries` / `last_transit` / `overdue_by`: **ABSENT**. But the
canary substrate is **UNWRAPPED** into `orders_status`: `interval`
(=expected_interval, orders.py:232), `last_outcome`, and `healthy =
outcome=="completed"` (orders.py:243 — the exact "fresh canary / broken machinery"
distinction) exist per-order, just not assembled into a board with
overdue/verdict/transit.

### `Capacity` — **ABSENT (read AND write).** No `capacity` tool; no
`set_target`/`add_agents`/`disable_formula`/`enable_formula`/`set_priority`; no
EffectPlan-returning capacity path. Only a motivating comment in blast_radius.py:45.

### `Usage` — **ABSENT.** provider/account/window_remaining/weekly_remaining/
resets_at/exhausted all unrecorded (fleet.py:184–186). Note `costs_summary` is
**not** this: it measures the meta-work token ratio (spend), not quota remaining
(costs.py:1–9).

### `Queue` (`queue_status`) — strong EXISTS
`ready_unclaimed`, `blocked` (`.blocked_on`), `tail`, `starved`, `deferred`
(`.until`), `next_up`, `next_up_is_prediction` (always true) all **EXISTS**
(mcp_server:1509–1592). `eta` / `depth` / `oldest_age`: **ABSENT** (`starved`
carries `idle_seconds`).

### `Formula` — PARTIAL / thin
`formulas_catalog` returns only `{name}` from `gc formula list` (orders.py:267).
`shape`/`version`/`owned`/`template`/`terminal_step`/`rehearsal`/`smoke_test`/
`invocations`/`outcomes`/**`failure_by_step`**/`duration_by_step`/`cost_by_step`/
`tier_by_step`: all **ABSENT**. `enabled` exists on the **order** row, not the
formula (orders.py:236).

### `Epic` / `Convoy` — **ABSENT** as objects/tools. Only a raw `convoy_id`
string on molecules (molecules.py:389).

### Cross-cutting envelope
| Property | Status | Source |
|---|---|---|
| `diagnostics` | **EXISTS** (mandatory) | required on every tool (schemas.py:839) |
| `trace_id` | **EXISTS** (mandatory) | schemas.py:836,839 |
| `trust` | **PARTIAL** | `artifact_trust` only on `artifact_state=True` tools (briefs/work), not every read (schemas.py:841) |
| `degraded_rigs` | **ABSENT** | not in the envelope |
| `Diagnostic.{code,severity,message,policy_ref,data_location,suggested_next_command}` | **EXISTS** | schemas.py:187–217 |
| `Diagnostic.actionable` flag | **PARTIAL** | no per-diagnostic boolean; a coarse trusted/untrusted `_partition` into `untrusted_diagnostics` exists only for artifact tools when trust fails (mcp_server:397–431) |

### Mutation / EffectPlan contract
`_EFFECT_RESPONSE` = `{applied, effect_plan}`; the plan carries `preconditions`,
`trace_id` (schemas.py:756,768). `dry_run=True` default holds across
briefs/work/create/dashboard_restart. **But** `plan.changes` /
`plan.blast_radius` tier / `plan.observe()` before-after are **not** in the
effect-plan schema; blast-radius classification lives in a separate read-only
`blast_radius_registry` (mcp_server:1873, with `awaiting_emitter` for aspirational
entries), not attached to plans. `trace_replay_preview` gives
planned_effects/replay_blockers (mcp_server:2760). No low/medium/high/gated tier
is emitted on a plan today.

---

## Deltas vs the prior draft (2026-08-20/21) — what changed, and why it matters

**Now EXISTS** (the prior draft called these ABSENT/UNWRAPPED):

- **Molecule as an object** with steps — `molecules_list`/`molecules_show` (#109).
  The prior draft's largest single finding ("the object model's central noun does
  not exist") is retired.
- **Step evidence chain, buildable slice** — `expected_artifacts` (declared,
  #142), `artifacts`, three-valued `is_complete`, all five `evidence.links` as
  honest tri-state, `broken_at` (#115). This also retires the prior draft's **one
  genuine DEFECT** (self-reported completion): `is_complete` now derives from
  declared-vs-actual artifacts and **never** from bead status.
- **Queue** six-partition including `deferred` and `next_up_is_prediction`.
- **`city_health`** four-valued + fds/disk/`flood_conditions` + probes + per_rig.
- **`worktrees_status`** with real `harvestable`/`merged`/`commits`/`size`/`url`.
- **`orders_status`** with `last_outcome`/`healthy`/`interval` (canary substrate).
- **`costs_summary`, `gates_status`, `blast_radius_registry`,
  `dashboard_status`/`dashboard_restart`, `mayor_*`** tools.

**Still genuinely ABSENT** (no store, no module, no tool):
UptimeLog; Capacity (read + all write levers + capacity EffectPlan); Usage quota
(account/window/weekly/resets/exhausted); the Liveness canary **board**
(verdict-with-canaries/transit/overdue); Epic/Convoy objects; molecule `state`
and `is_*` predicates; molecule `progress`/`timeline`/`cost`/`budget`/`eta`; the
Formula analytics (`failure_by_step` + the other three `*_by_step`, invocations,
outcomes, template DAG); Agent `account`/`current_step`/`current_molecule`/
`claims`/`transcript` and real `model`; envelope `degraded_rigs`.

**UNWRAPPED** (data/logic exists, no tool): the **EventStream** — `ticker.py`'s
tier classification and cause/response pairing over `.gc/events.jsonl` are
implemented but unwired; the three unemitted evidence links have declared slots
awaiting an emitter (molecules.py:237); DispatchCause partially present as
`DispatchProvenance` for briefed work beads only (provenance.py), not surfaced on
molecules.

---

## What it would take, grouped by cost (for WP-SURFACES)

**Cheap — wire a tool over logic/data that already exists (UNWRAPPED):**
the EventStream/ticker (tier + cause→response) · the canary board (assemble
`orders_status`' per-order `interval`/`last_outcome`/`healthy` into
verdict+overdue+transit) · city-wide `molecules` (add an `all_rigs` fan-out to
`molecules_list`) · `molecule.why` (surface `DispatchProvenance` onto the
molecule row). **This is the bulk of the remaining surface work.**

**Medium — derivation / reshape over existing data (PARTIAL):**
Rig lifecycle `state` (join health + suspended list) · formula catalog enrichment
(`gc formula show`) · Agent `model` vs `provider` de-conflation · worktree
`is_orphan` derivation · `progress` *once step totals are declared* · Diagnostic
`actionable` per-finding flag.

**Expensive — new instrumentation (ABSENT):**

1. **The three unemitted evidence links** (`claimed`, `agent_active`, `commit`) —
   the keystone. They unblock `molecule.state`, `is_*`, `broken_at`'s full
   diagnosis, and `evidence.history`. The slots already exist (molecules.py:237);
   what is missing is the recording path at claim/wake/commit time.
2. **`molecule.why`** as a first-class DispatchCause recorded at sling time (kind
   taxonomy + `chain`), beyond today's briefed-bead provenance.
3. **Worktree ownership** — `created_by`/`step` recorded at creation.
4. **`agent.account` / quota** — provider identity + remaining usage.
5. **`city.uptime`** — on/off transitions with reason.
6. **Capacity levers** — read + the five write levers, each returning an EffectPlan.
7. **Formula `*_by_step` analytics** — per-step outcome history.

**Items 1–3 are the same defect wearing three hats:** the city records what it
*did*, not what it *intended* or *observed*. They should be one design pass.

---

## Appendix — `mc-5p8v`: dashboard concurrency timing failures (findings)

**Verdict: timing-sensitive assertions, NOT live dashboard/fanout defects.**
No code change is warranted in `mctl_dashboard/`; the fan-out mechanism is
functionally correct. Recorded here per the WP-TRIAGE charge ("otherwise write
findings into your gap-analysis doc").

**Origin.** Post-execution of `mc-j6uh` reran `pytest tests/mctl -q` on
2026-08-25; the broad suite exited 1 with 1224 passed / 2 failed:
`test_city_reads_concurrently.py::test_the_city_page_does_not_serialize_its_three_reads`
and `test_dashboard_fanout.py::test_fanout_actually_overlaps`.

**The two failing tests are exactly the two wall-clock-threshold tests** — not the
correctness guards. Each file pairs a timing assertion with functional guards:

- `test_fanout_actually_overlaps` asserts 3×50ms calls finish in `< 0.12s` (a
  30ms margin below the 150ms serial floor).
- `test_the_city_page_does_not_serialize_its_three_reads` asserts elapsed
  `< serial*0.75` = `< 0.90s` for three 0.4s sleeps.

**Evidence gathered on `74eeac0`:**

1. **Both pass reliably in isolation** — 15/15 consecutive runs of the pair,
   ~1.34s each. **And within the full suite** — `pytest tests/mctl -q` →
   `1601 passed in 117.53s`.
2. **The four correctness guards always pass** —
   `test_all_three_surfaces_are_still_read`,
   `test_fanout_returns_results_in_request_order`,
   `test_a_failing_call_does_not_lose_the_others`,
   `test_a_single_spec_does_not_pay_for_a_pool`. The fan-out reads all three
   surfaces, preserves request order, rides exceptions along, and does not build
   a pool for a single spec. **The mechanism is correct.**
3. **The failure reproduces under CPU contention.** Running the tight pair 12×
   against 28 busy-loop processes on a 14-core box,
   `test_the_city_page_does_not_serialize_its_three_reads` failed once:
   *"1.17s against a 1.20s serial floor — the reads are still running in
   sequence"* (1.17s > the 0.90s threshold). The reads were **not** serialized —
   under saturation the `ThreadPoolExecutor` threads simply could not be scheduled
   promptly, so overlapping `time.sleep` calls elapsed near-serially.

**Why this is not a defect.** If fan-out were genuinely serialized, the
correctness guards would still pass while the timing tests failed — but so would
they under mere contention. What distinguishes the two is that the mechanism is
demonstrably correct (guards green) and the timing failure is reproducible purely
by loading the CPU, with no code change. That is the signature of a fragile
wall-clock threshold, not a broken fan-out.

**This is the P6.3 anti-pattern inside a test assertion** ("a deadline is not a
verdict"): the assertion renders *"the machine was too loaded to schedule my
threads promptly"* as the verdict *"the reads are still running in sequence"* —
attributing the prober's contention to the probed code, exactly the inference
P6.3 forbids.

**Recommendation (for BART/QUIMBY, not applied here).** Make the two thresholds
measure genuine **overlap** rather than wall-clock elapsed, so scheduler
contention cannot masquerade as serialization. Because `fan_out` hands each spec
to a *separate* client instance (`clone()` returns a fresh object), a shared
concurrency tracker must be injected across the pool to observe overlap directly
(the current per-instance `max_concurrent` in the fanout fixture stays 1 with 3
specs / 3 workers, which is why the test fell back to wall-clock in the first
place). Such a rewrite still ships an observed failing case (P6.2): a genuinely
serialized fan-out drives the shared tracker's peak to 1 and fails. **Not applied
in this branch deliberately** — rewriting shared timing tests mid-cluster would
risk clobbering the concurrent WP-SURFACES/WP-LIFECYCLE merges; handed to BART as
a recommendation.
