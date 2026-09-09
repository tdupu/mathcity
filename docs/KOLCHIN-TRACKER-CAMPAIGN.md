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

## Sixth tranche — the city diagnosed its own defect

### #219: the §1–§7 step is blocked, and the blocker is real

`test_the_python_rule_and_the_shell_rule_agree` asserts every rule in
`required-sections.toml` appears verbatim in `brief-check.sh`. That guard is
why #35 cannot recur, and it means a create-time rule cannot be added without
its drain-time counterpart. The `action_block` rule was safe because
`^action_block:[[:space:]]*$` already existed at brief-check.sh:188.

§1–§7 have no shell counterpart, so adding them turns on retroactive drain
enforcement against briefs already in the pile:

    kolchin testrig: 12 brief files, 9 full-form, 3 compact  (25%)
    corpus figure in section-discipline.toml: 59 of 178      (33%)

Turning that on without a migration auto-rejects all of them — the #96 harm,
re-created. #219's own title names the answer ("failure routes to
revise-return"), which made #209 a hard prerequisite.

### #209: driven live, and the run-operator found the bug

Created `mt-3ezn`, relayed `verdict: revise`. The verdict recorded correctly,
the brief closed (correct — `post-decision-file-or-sendback` archives the
original by design), `brief.decided` rang, the revise-return order fired, its
wisp `mt-t71o` was claimed and closed — **and no brief was re-deposited.**

`revise-return.toml:137` resolved the pack root with ONE dirname. `Source:` is
the ORDER FILE, so it yielded `<pack-root>/orders` and LIB pointed at
`<pack-root>/orders/assets/scripts/revise-return-lib.sh`. The P1.14 guard fired
and the step exited 1 **before any scan**. The formula's own comment said "the
parent of the orders/ directory" — code and comment disagreed.

Live proof against the real pack cache:

    one dirname:  .../repos/<hash>/orders
    two dirnames: .../repos/<hash>        lib exists? YES

**The run-operator that executed the formula diagnosed this**, verified both
paths on disk, and reported the fix in its close notes — including that the
comment's claim to mirror brief-decision-dispatch's resolution is inaccurate
(every other formula uses a literal placeholder; this was the pack's only
dirname-chain, so it had no sibling to be checked against). Both the fix and
that correction are now at the call site.

This is the dogfooding the campaign was for: the city found a defect in its own
pack that I had walked past twice.

## Seventh tranche — the keystone chain, demonstrated

### #180: every arrow but the first, run live

    commission_brief          -> mt-f1ep [commission], gh.issue: tdupu/mathcity#180
    work_status               -> BLOCKED, MWRK010 "no approving verdict"   <-- correct
    (adjudicate approve)      -> readiness "ready", blockers []
    work_dispatch             -> MCTL_LIVE_DISPATCH_DISARMED               <-- correct
    (arm for one call)        -> exit_code 0, applied true, claim "observed"
                                 molecule mt-7mlq  in_progress  work-briefed

Both refusals are the system working. A commission that dispatched without
approval would break the two-catch model; a dispatch that ran without arming
would make every dry-run rehearsal live. Arming is a PER-PROCESS env var
(`MCTL_ENABLE_LIVE_DISPATCH=1`), not a city switch, so it cannot be left open.

Arrow 1 (mint the source bead FROM the issue) was not run: `gh` is
unauthenticated for `gascity-user` on kolchin. Used an existing bead instead.

### #179: the edge exists as a skill

`skills/github-issues-to-briefs/SKILL.md` runs standardize -> create_issue_bead
-> briefs_create -> back-pointer comment -> adjudication -> close-on-resolution.
Two properties make it safe rather than merely automatic: work commissioning is
never auto-approved, and an approved brief whose work is still in flight leaves
the issue open.

That skill is, structurally, what I have been doing by hand against this tracker
all session — including its rule "Never close what could not be verified —
report `unknown` instead."

### #211: fixed, plus a second defect found inside it

Per-template matching landed (a body conformant to ONE template is conformant).
And `config.yml` — the chooser, requiring nothing — made `all()` vacuously true,
so EVERY body passed, including a 13-byte one. Fixed by filtering on the
PROPERTY (`if reqs`) rather than the filename: "A template requiring nothing is
not a bar a body can clear; it is the absence of a bar."

## Blocked, needs the repo owner

- **Pack pin.** The city runs formulas from `sha:af9455f`, which predates every
  fix landed today. Advancing it needs a `city.toml`/`pack.toml` edit, which the
  classifier denies. `gc import upgrade` cannot do it — an exact sha has no
  constraint range, and it reports "Upgraded import" for what is a no-op.
- **`gh auth login`** on kolchin: three typed tools and arrow 1 of #180.
- **`gc dolt restart`**: the 15s read_timeout (#263) is still unapplied.

---

# Final state

**117 open at start → 60. 57 closed, 24 code fixes, 7 platform defects re-homed.**

Every close carries a live payload or a passing pinned test. Every issue left
open carries a measurement, a specified next step, or the named decision it is
waiting on.

## The failure class that dominated

Seven of the fixes were one shape: **a check that cannot evaluate must say so
rather than substitute the safe answer**, and its inverse, **a check that fires
on prose trains people to ignore it.**

| # | what it was reporting instead of "I cannot tell" |
|---|---|
| 94 | disarm wrote a rig token to whatever the cwd happened to be |
| 107 | `no-brainer-mode` said DRY-RUN when it meant UNKNOWN |
| 191 | an unresolved recipient delivered to a directory nobody watches |
| 196 | one refused socket fails the whole city closed |
| 252 | a `bd link` TIMEOUT reported as "nothing was written" |
| 178 | a path-B run reported as "never dispatched" |
| 195 | a gate that fired on a comment mentioning a governed path |

Two more were checks that had gone **dark**: the shell-branch gate (matching the
English word "if") and `test_inbox.sh`, which exited 1 after 2 of 7 sections
having printed no failure at all.

## What live testing found that reading would not

- **#209** — the run-operator executing the formula diagnosed the one-dirname
  pack-root bug itself, in its close notes. I had read past that line twice.
- **#96** — the brief I created earlier in the session was sitting in
  `.pile/.rejected/` for the exact defect.
- **#266** — a "rotation never fires" bug that was a test asserting the SENDER
  rotates. The code was right; the docs never said who rotates.
- **#191** — the suite that would have caught the bug was dying silently.

## Three retractions

Posted and corrected on the issues: #168 (my proposed fix would have violated
B2.10), and #209 twice (conflated a two-day-old wisp with my own run; read a
file-count difference as a starved scan root). Each was caught by checking
rather than by reasoning further.

## Blocked on one command each

    pack pin              -> 24 fixes live, closes #209
    superpowers binding   -> unblocks 4 formulas, closes #261
    gh auth login         -> 3 typed tools, arrow 1 of #180
    gc dolt restart       -> applies read_timeout=600000 (#263 half 1)

`gc import upgrade` cannot advance an exact sha pin — it reports
"Upgraded import" for a no-op.

## Two things worth knowing

- **#145 costs more than its title suggests.** `bd list --json` omits null
  fields, so an absent key cannot be told from an empty one. It blocked a
  measurement #67 needs. `bd dep list` is the workaround. It currently has
  nowhere to be filed: the beads fork has issues disabled.
- **#219's second half needs #220 first.** The §1-§7 rules are `create_only`
  because drain-side enforcement would auto-reject the compact-form briefs
  already in the pile. Four producers still compose partial forms.

---

# Session 2 — 2026-09-09

117 → 52 open. 70 closed. Five follow-ups filed (#267 #268 #269 and two
upstream), so nothing was dropped rather than closed.

## What closed, and what it took

| # | Finding |
|---|---|
| 90 | `stack/.index.jsonl` was the only registered artifact still on derived matching — the mechanism behind the `manifest.jsonl` collision |
| 102 | `manifest-current` passed on a stale index; the deferred design question **dissolved** once framed as divergence |
| 163 | `blast_radius` absent from every `EffectPlan`; enforcement still blocked at **3 of 13** operations classified |
| 233 | B3.1 audit: **0 of 640** closed beads carried acceptance |
| 72 | 13 adjudicated briefs whose beads never closed, incl. two P0s |
| 238 | 20 reaping violations with no open survivor, across three stores |
| 197 | `pools_status`: **16 of 18 rigs have no session ceiling** |
| 22 | Fixed upstream; the recommended fix would now be a **regression** |
| 80 | Re-homed: reaper CTE joins on `JSON_EXTRACT` — unindexable |
| 148 | Untrust condition had gone stale after `mc-crc4o` fixed the lookup it guarded |
| 67 | `PASS|N/A` cannot match `PASSED` — the gate rejected what POLICY mandates |

## The pattern in the tracker

Six issues framed as **decisions** or **NEVER-BUILT** had mechanical answers:

    #148  untrust guarding a failure the resolver had already fixed
    #67   a word-boundary bug, not a policy question
    #16   the delete-cascade EXISTS, is installed, holds a live store at 0
    #99   ready-depth IS read — clamped to 1, and no agent configures scale_check
    #105  unlock_count IS consumed — by the skills, not by mctl/gc
    #5    68% "uncovered" is 57 plain backlog beads + 8 non-work beads

In five of six the original measurement was **correct** and only the inference
from it was wrong. #105 checked mctl and gc, found nothing, and generalised to
"the city". **A negative result is scoped to where you looked.**

## The pattern in my own tools — four false positives, all on unfamiliar data

Every audit written this session was green on its fixtures and wrong on the
first real store it had not been developed against:

    1. eight phantom "bead not in its store"  — one prefix, several stores
                                                 (~/repos/X vs its ~/gt twin)
    2. BP4.4(d) flagged two human adjudications as automated reaping
                                                 — matched intent from prose
    3. one bead counted three times            — deduped rows, not beads
    4. a `verdict: revise` scored as a stall   — never read the verdict field

(4) is the costly one: it would have inflated **the exact population #209 needs
measured**, in the same measurement someone would use to size #209.

Structural checks ("was there an open survivor AT CLOSE TIME") produced zero
false positives on the same data. Intent-matching ones produced all four.

**Fixtures prove a check runs. Only unfamiliar data proves it measures the
right property.** This is the strongest argument for the goal's "test on a live
city" clause, and it was learned the hard way four times.

## A contradiction that nearly shipped a policy inversion

`brief-record-decision.toml` asserted both:

    step record-decision:  ".toml is a redundancy channel (B2.8: files are
                            cache), NOT the canonical record"
    step archive:          "Keep the decision record in decisions/ as the
                            indexable CANONICAL record"
    description:           "Write a canonical decision record..."

Two of three said the cache was canonical. Reading those, "teach MBRF005 to
follow the pointer" is the *correct-looking* fix — and it would have made the
gate for the whole MCP conversion set read the cache to excuse a missing
canonical record. Caught only by reading the other step. Fixed in `b273b8c`.

## Live-city facts worth carrying forward

- **kolchin's brief tree is nearly empty.** HQ has 0 decision beads of 1,738
  (1,631 are sessions). The `mathcity` rig has **193 decision beads and no
  `.beads/briefs/` directory at all**. Only `mathcity-testrig` has briefs, and
  it has one pile file and one stack file. Anything brief-pipeline-shaped
  cannot be exercised against real data on kolchin today.
- **The mctl suite leaks a dolt sql-server per run** (#269). Three generations
  found alive, oldest 2d 9h. `multi_rig.build` has 11 caller files and zero
  teardown.
- **kolchin had no pytest at all** until this session; the 2,297-test suite had
  never run there. Now at `~/.venvs/mathcity-tests`.

## Still blocked on one decision each

**One interface decision unblocks #82, #83 and #86**: do formulas call mctl
per-artifact, or does one adjudication call own all five representations? Every
author who reached it declined to choose; #86 says so verbatim.

    #16   one-time backfill delete?           (cascade already holds kolchin at 0)
    #99   scale_check: N ready -> how many?   (needs a ceiling first — 16/18 have none)
    #105  keep stored unlock_count?           (traversal returns ~0 either way)
    #148  should one bad file untrust a rig?  (false triggers now removed)
    #5    surface orphaned spec beads?        (drain-reservation class is empty)
    #268  should adjust_worker_pool exist?    (gate it needs classifies 3 of 13)
    #267  reopen 20 over-closures, or comment?


## Provenance correction — commit `9945308`

`9945308` is titled *"mathdb: read open problems into the city, on MathDB's
stated terms (Mathathon)"* and contains two files that belong to **#235**, not
to the Mathathon work:

    assets/scripts/stale-options-audit.py     122 lines
    tests/stale-options-audit/smoke_test.sh    68 lines

**Cause: two sessions, one working tree.** A forked session and this one were
both writing to `/Users/tdupuy/repos/mathcity`; the fork ran `git add -A` while
these files were unstaged and swept them into its commit.

Nothing was lost and the code is correct. The history is simply wrong about why
those files exist — which is the same class of defect this campaign spent the
day finding, arriving from a direction none of the checks watch.

Not rewritten: the commit is pushed and shared, and rewriting shared history is
worse than an inaccurate message. Recorded here and on issue #235 instead.

**The structural fix is `EnterWorktree`**, which gives a forked session its own
checkout. It should have been used before forking rather than after the
collision. Failing that, `git add <explicit paths>` instead of `git add -A`
while sessions overlap.
