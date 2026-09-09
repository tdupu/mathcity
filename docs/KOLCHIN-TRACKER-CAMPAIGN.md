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

## Third tranche — verifying the "cited in code" set

Triage signal that worked: grep the pack for `#<n>` where `n` is an open issue.
33 open issues are named in **code** (not just docs), usually in a comment
recording the fix. That set is dense with already-fixed-never-closed work.

| # | How it was settled |
|---|---|
| 226 | `briefs_pile_state` live: testrig `{state: healthy, rejected_count: 2}`; mathcity `{state: unreachable, counts: null}` with the path named |
| 183 | CLI renders `next: mctl briefs create --source ...` on a real MBRF034 refusal |
| 192 | Same refusal left **no** stray bead — `bd search "probe 183"` → none |
| 188 | Dry run on a rig with no brief root: directories absent before AND after |
| 185 | `create_defect_bead` plans cleanly; labels mapped to `defect.labels` metadata, which the schema says ("mapped, not landed") |
| 162 | `test_roster_docs_defer_to_live.py` 6 passed; 56 tools live vs the 16 the docs froze |
| 215 | `if offered and normalized == "approve"` — the option gate scopes to approve |
| 208 | `MBRF_RECOMMENDATION_UNKNOWN_OPTION` on `recommendation: "Z"`; `no_brainer`/`no_brainer_reason` on the adjudication schema |

### #168 — the one that looked closeable and is not

`_cache_updates` plans `CacheUpdate("stack_index", ...)` guarded on the index
existing, so the obvious reading is "the testrig has no index yet." I tested
that: created an empty `.index.jsonl` in the testrig stack dir, re-ran
`briefs_create`, and got **0 stack_index mentions**. The live plan is still the
exact five effects #168 reported — bead_create, pile_markdown,
`decision_toml` cache_update, event_write, trace_write.

So the guard is not what suppresses it; the create path does not reach that
seam. `_cache_updates` is called from `_plan`; `plan_create_brief` evidently is
not routed through it. The index file was removed afterwards.

**Lesson worth keeping: a fix cited in a comment is not a fix observed.** Every
close in this campaign that rested on source reading alone should be treated as
weaker than one with a live payload behind it.

## Fourth tranche — two real fixes, not just verification

| # | How it was settled |
|---|---|
| 181 | The 120s kill became a warn threshold; `MEASURED_SLING_WORST_SECONDS = 243.51`, UNKNOWN codes replace the verdict |
| 194 | `decisions_to_briefs` live: plans `pile_markdown` + `decision_toml` + event + trace + bead, `applied: false` |
| 124 | `mayor_conservation` live: 113 molecules, roots_dangling 0, categories reported separately, `readable` distinct from `clean` |
| 123 | kolchin hq census: 1676 beads, 26 root pointers, **0 dangling**; 147 molecules across three rigs, 0 dangling |
| 94 | `disarm_no_brainer` withholds only the RIG token when the rig root is unresolved, keeps the city token, and says which half is pinned |
| 265 | **Fixed** — see below |
| 85 | **Fixed** — see below |

### #265, found by hitting it

`mayor_conservation --rig hq` died with

    MCTL_CONTEXT_MISSING_PATHS_TOML
    path: <city>/https:/github.com/tdupu/mathcity/tree/main/assets/brief-pipeline/paths.toml

`Path("https://...")` is not absolute, so the non-absolute branch joined the URL
onto the city root. The harm is second-order: it surfaced as a MISSING-FILE
error naming a path nobody configured, telling the reader to restore a file,
when the rig's real problem is having no local checkout at all.

`_is_remote_source()` now recognises http(s)/git/ssh/git+ssh/git+https and
scp-style `git@host:path`, and the resolver raises
`MCTL_CONTEXT_SOURCE_CHECKOUT_NOT_LOCAL` naming the source and the remedy.
Live after deploy: `hq` refuses with the remedy; mathcity (113), testrig (33)
and gascity (1) all still resolve clean.

The first full run FAILED `test_every_emitted_code_is_registered` — I had
emitted a code without registering it in `assets/mctl/diagnostics.toml`. That
is #199's guard catching a real omission in the change that cites it.

### #85, and a gate that had been dark

The skill had zero `mctl` mentions. Step 7, TS-3 and TS-4 now route through
`decisions_to_briefs` / `briefs_relay_adjudication` instead of writing
`.pile/*.md`, appending `manifest.jsonl`, and `mv`-ing to `.no-brainer/`.

While verifying, `tests/mctl-shim-callsite/smoke_test.sh` turned out to be
**failing on a clean tree**: step 10e grepped whole files for
`(if |case |...).*mcp__mctl__`, and a bare `if ` matches English. It was tripping
on the sentence "if a brief/bead exists for it, `mcp__mctl__briefs_relay_...`".
Now it extracts fenced code blocks and greps those — verified it still fails on
a real injected `if grep -q mcp__mctl__...; then`.

## Left open deliberately

- **#96** — the testrig shows `pending 0 / rejected 2`, and `mt-3k7g` is
  "stranded in .rejected/ on a mechanical gate". That is this issue's shape,
  not its absence.
- **#168** — verified still broken (see third tranche).
- **#99** — needs upstream pool-scaling knowledge; I would be guessing.
- **#204** — my kolchin evidence is confounded by a local `max=0` patch;
  retracted the "reproduced" framing on the issue.

## Fifth tranche — building, and one correction that mattered

### #168 was working as designed, and my earlier comment was wrong

I had said the gap was "which planner the create path uses" and suggested
routing `plan_create_brief` through `_plan` so it would emit a stack row.
Following that would have introduced a policy violation. The docstring says so
at the top of the function:

    The presentable stack index is deliberately NOT written:
    B2.10 makes brief-shuffle the single `.pile -> stack` writer.

POLICY.md:373 confirms it. A brief reaches the front end by brief-shuffle
promoting it, not by its creator writing a stack row. Retracted on the issue.

### #96 — fixed, after walking into it

`mt-yftq` — the brief I created through `briefs_create` earlier in this
session, which returned `applied: true` — was found in `.pile/.rejected/`:

    mt-yftq             | decision brief missing action_block
    rig-scope-live-test | G8 Brief-record: BLOCKED

The create gate checked ONE rule (`## Gate Evidence`); the drain gate also
requires `action_block:` with on_approve/on_reject/on_defer. Creation reports
success, the shuffler bounces it — the CT13.4 shape.

Fixed by giving `required-sections.toml` profile-scoped rules and adding the
action_block rule scoped to `decision`. The scoping is load-bearing:
`check_action_block` is reached from `check_decision_profile` alone, so an
unscoped rule would refuse `lost_bead_filter` and `producer_repair` briefs.
`decisions_to_briefs` now emits an action_block too — its own output was a
decision brief without one.

Live: `gate_profile: decision` + no action_block -> MBRF036 with a remedy
naming the SHAPE; `lost_bead_filter` -> not refused; no profile -> unchanged.

### The 44-test measurement

The scoped rules only fire when the body declares a profile — and bodies
arriving at `briefs_create` carry none, because `_created_document` stamps the
frontmatter later. Defaulting to `decision` is factually right
(`plan_create_brief` mints `issue_type="decision"` unconditionally) and **44
tests fail on it**, each a producer that composes no action_block.

That is not test debt. It is #219's scope, measured: making the create gate
real means teaching every producer the full form FIRST, then defaulting the
profile. Tried it, measured it, reverted it, left the finding at the call site.
