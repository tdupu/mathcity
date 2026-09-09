# Live tracker campaign — kolchin city, 2026-09-08

Resolving https://github.com/tdupu/mathcity/issues by verifying each against the
**running** kolchin city (`HQ`), over real MCP stdio JSON-RPC. Opened at 117.

## Harness

`mcpcall.py` (in the mathcity checkout on kolchin, untracked) spawns
`bin/mctl mcp serve --city ~/HQ --rig <rig>` and speaks JSON-RPC on stdio —
the same path the Mayor's projected MCP uses.

    MCTL_MCP_CLIENT_CLASS=internal MCTL_CITY=$HOME/HQ MCTL_RIG=mathcity \
      python3 mcpcall.py <tool> '<json-args>'

`MCTL_MCP_CLIENT_CLASS=internal` is load-bearing. `visible_tools()` returns
`()` for an unarmed external client, so an external probe sees **zero tools**
and no explanation — which looks exactly like a broken server. The Mayor's
template sets it; ad-hoc probes must too. 56 tools register.

## The blocker found first — every rig bead read was dead

`beads_list` → `MCTL_MCP_INTERNAL_ERROR: BeadReadError`, on all rigs.

Root cause: `_resolve_rig_root` read the rig's `path` from the `city.toml`
rig entry and fell back to `<city_root>/<rig_name>`. gascity >=1.0 moved that
binding to `<city_root>/.gc/site.toml` and now **refuses** a city.toml that
still carries it — confirmed by adding the key and watching `gc rig list` exit
1 with "unsupported pre-1.0 rig.path ... move it to .gc/site.toml". So the key
is always absent and the fallback always fires. On kolchin site.toml binds
`mathcity -> ~/repos/mathcity` while the fallback named `~/HQ/mathcity`, which
does not exist.

Fixed in **b96946b** — `_site_rig_paths()` parses the `[[rig]]` array from
site.toml, consulted after the legacy key and before the fallback. Missing
site.toml returns `{}` (cities whose rigs *are* subdirectories stay correct).
Test: `test_context_reads_rig_root_from_site_toml`. Suite: 2252 passed.

This gated everything else — it is why the campaign starts here.

## Closed with live evidence

| # | Title | How it was settled |
|---|---|---|
| 245 | typed bead READ | `beads_list` 970 beads + `scope{matched, total_in_store, status_filter, statuses_excluded}`; `beads_show` full description |
| 230 | `commission_brief` NameError | No NameError. Refusal path → `MBRF036`/B1.5; success path → effect plan with `commission` label, `applied:false` |
| 229 | `briefs_list` drops body/sections | 189 briefs; `body`, `sections`, `decision_options`, `recommendation` all present and populated |
| 227 | no mathcity control-dispatcher | Live `mathcity/core.control-dispatcher` 22h; consequence refuted — 64/112 molecules closed |
| 231 | dashboard rebind never verified | First live `dashboard_restart`: pid 82466→83027, old GONE, new ALIVE on :8471, HTTP 200, `stale:false`; teardown restored state |

## Honest gaps

- **#231 `MDSH_RESTART_FAILED` not induced.** `stop_instance` escalates
  SIGTERM→SIGKILL, so the branch needs a process in uninterruptible sleep.
  Verified by reading instead: it is an early return with `applied:false`, so
  `start_instance` is unreachable. Recorded as not-induced, not as passing.
- **#227 was filed against a different city** (the `~/gt` 8-rig fleet). Closed
  on evidence that neither defect nor consequence is present now, with the
  scope difference stated in the comment.

## Live findings not yet filed

- `tools/list` returns `[]` for an unarmed external client with **no
  diagnostic**. `_gate()` explains itself on a *call*, but the empty roster is
  silent — indistinguishable from a server with no tools (P6.1).
- `beads_list` has no `limit` parameter; it returned all 970 open beads.

## Formula surface — re-swept after the pack move to 6f612be

`sweep.py` drives every catalogued formula through `formula_dispatch` on ONE
live MCP session (dry-run), so a failure is the formula's, not a cold start's.

    rig mathcity          91 catalogued -> 91 planned, 0 refused, 0 broke
    rig mathcity-testrig  91 catalogued -> 91 planned, 0 refused, 0 broke

### One real dispatch, end to end

Planning is not execution, so `brief-archive-sweep` was dispatched for real in
the isolated testrig (`dry_run: false`):

    formula_dispatch -> exit_code 0, outcome "dispatched"
      argv: gc sling mathcity-testrig/gc.run-operator brief-archive-sweep --formula
      wisp root: mt-ed6l

Then, observed live:

    +25s   mt-ed6l  OPEN
    +70s   mt-ed6l  IN_PROGRESS, assignee mathcity-testrig/gc.run-operator
           (the pool materialized session hq-v3rlp on demand)
    +190s  lease heartbeat stale 4m -- NOT a wedge; the pane showed an active
           LLM turn with bypass-permissions on, mid-"Bloviating (2m48s)"
    +290s  mt-ed6l  CLOSED, gc.outcome: pass

That is MCP -> sling -> wisp -> pool materialization -> claim -> execute ->
close, with the formula reading `gc.var.artifact_root: ~/.gc/mathcity/...`
through the tilde expansion added to this formula earlier.

**The argv looked wrong and is not.** `gc sling <target> <name> --formula`
puts a bare `--formula` last; `gc sling --help` documents exactly that form
(`gc sling mayor code-review --formula`) — the flag is a boolean saying the
positional is a formula name.

## Still open, with fresh evidence

| # | Verdict |
|---|---|
| 244 | **Reproduced** on kolchin: /queue 1.08s idle -> 5.69s during /city (5.3x). Lock is per MCP call, not per request — inflation scales with rig count |
| 22 | Config gap real (no `work_query` anywhere) but 0 hold-labelled beads of 970, and the label convention is retired upstream. Needs a decision, not a patch |
| 19 | Legacy `gascity-packs/mathcity` tree still present — genuinely open |

## Second tranche — the tool surface

| # | How it was settled |
|---|---|
| 203 | `orders_status` returns a valid payload; no `MCTL_MCP_OUTPUT_SCHEMA_VIOLATION`. 52 outcomes, all string values, one INFO diagnostic |
| 206 | `priority=priority_from_labels(issue.labels)` is wired in; mapping verified p0-p4 in the live module |
| 202 | `_emit_brief_submitted` attached as an `on_apply` hook; a real `briefs_create` minted `mt-yftq` with no WARN advisory |
| 214 | `trace_show` on a FAILED dispatch returns `outcome: "refused"` with the full diagnostic — not `MCTL_TRACE_NOT_FOUND` |
| 212 | `MWRK003` is `Severity.WARN` at its single emit site, with "recheck rather than retry" |
| 213 | Provenance written before the claim check; pre-sling detector matches the leftover synthetic convoy |
| 228 | `_walk_sources` skips in-flight sources; `execution.work_associated` is now the claim signal, not `assignee` |

### #204 is reproducing, and the mechanism is narrower than filed

    total order-run beads: 7      by status: {'open': 7}
    every order fired exactly once, across 2026-09-06 .. 09-09
    gc doctor -> order-firing-current: scheduled orders are stale
    orders_status -> 27 completed / 25 failed

Not one order-run bead has ever closed. But a root-only wisp is **not**
inherently uncloseable: `brief-archive-sweep` is a vapor formula without
`pour = true` (gc says so on dispatch), and the copy I slung through
`formula_dispatch` closed cleanly. The difference is who is on the other end —
a slung wisp reaches a pool that materialises an operator; an order-run wisp is
minted by the order runner and nobody claims it. The fix surface is the order
runner's run-bead lifecycle, not root-only wisps.

## Host gap that blocks three tools

`gh` is unauthenticated for `gascity-user` on kolchin (no `~/.config/gh/hosts.yml`,
no `GH_TOKEN`). git works — that is the SSH key. So `create_issue_bead`,
`create_github_issue` and `standardize_github_issue` all fail at the fetch with
a loud `MISS004` naming the cause. Needs an interactive `gh auth login`.
