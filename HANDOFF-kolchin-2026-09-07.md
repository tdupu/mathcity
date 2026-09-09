# Handoff — kolchin repair + mctl formula dispatch (2026-09-07)

Outside agent session, run from `~/repos`. Ran out of usage mid-implementation.
This is written so the next session can resume without re-deriving anything.

---

## 1. IN-FLIGHT WORK — uncommitted, resume here

Two new files in `~/repos/mathcity`, **not committed**:

    assets/scripts/mctl_core/formula_dispatch.py    NEW, complete, tests green
    tests/mctl/test_formula_dispatch_tool.py        NEW, 8 tests

Current test state — verified, not claimed:

```
python3 -m pytest tests/mctl/test_formula_dispatch_tool.py -q
4 failed, 4 passed
```

That split is **correct and expected**. The 4 passing tests cover the core
planner; the 4 failing tests assert the MCP tool exists and are red because the
tool is not registered yet. This is TDD red, not a bug.

### The exact next step

Register a `formula_dispatch` tool in `assets/scripts/mctl_core/mcp_server.py`:

1. Add a handler near the other dispatch handlers (`_handle_work_dispatch` is at
   line ~1850) following its shape exactly:

   ```python
   def _handle_formula_dispatch(ctx, arguments):
       plan = plan_formula_dispatch(
           formula=arguments["formula"],
           catalogue=<names from formulas_catalog(city_reader(ctx.city_root))>,
           target=arguments.get("target") or f"{ctx.rig_id}/gc.run-operator",
           bead_id=arguments.get("bead_id"),
           variables=arguments.get("vars") or {},
       )
       # refuse -> return the plan; dry_run -> show command; else apply
   ```

2. Add a `ToolSpec` to the `TOOLS` tuple (starts line 2120; `formulas_catalog`
   is at ~2157 and is the closest read-side neighbour; `work_dispatch` at ~3804
   is the closest mutating neighbour). It **must** carry:
   - `input_schema` properties including `formula`, `vars`, `dry_run`
     (and `bead_id`, `target`)
   - `mutating=True`
   - **no** `command`/`argv`/`shell`/`cmd` property — a test asserts this

3. The registry is `TOOLS` (line 2120) and `TOOLS_BY_NAME` (line 4072).
   Note: it is `TOOLS`, **not** `TOOL_SPECS`.

4. Reuse the existing execution machinery rather than adding a second one —
   `work.py` already runs slings under a deadline bound
   (`MCTL_DISPATCH_DEADLINE_SECONDS`, `resolve_dispatch_elapsed_policy`,
   `apply_dispatch_plan`). Do not write a new subprocess path.

Then run the full mctl suite, not just the new file:

```
python3 -m pytest tests/mctl -q
```

### Why this design (do not undo it)

`work.py::_formula_invocation` (line ~1790) hand-builds the `work-briefed`
sling argv for exactly one formula. The fix for #256 is **not** to let a caller
pass argv for any other one. The planner takes a formula NAME plus vars as
data and composes the argv itself, which buys two load-bearing properties:

- an unknown formula is refused **by name** (`MFRM_UNKNOWN_FORMULA`, with
  `did_you_mean`), not slung and left to fail downstream;
- every var is one argv entry — nothing is joined on spaces, so a value
  containing a space, quote or `;` cannot split or terminate the command.

Both have tests. `test_the_tool_takes_no_command_string` and
`test_variable_values_are_never_shell_joined` are the ones worth keeping if
everything else in that file were deleted.

Also encoded: the two invocation shapes are **not** interchangeable. Passing a
bead → `--on <formula>` (targeted); omitting one → `--formula` (untargeted).
Guessing wrong produces `convoy_id requires a targeted formulas v2 invocation`,
which reads like a formula defect and is not one.

---

## 2. BLOCKED — needs Taylor, one command

The single change that unparks kolchin. Root cause confirmed and verified.

`~/HQ/city.toml` line 1 is `[workspace]` with **nothing under it**. The
provider sits in `[defaults.agent]`, which this gc binary discards as an
unknown field, so every pool is skipped at `buildDesiredState` and the city
runs nothing.

The correct key is confirmed against the **working** laptop city
(`~/gt/city.toml` lines 1–2):

```toml
[workspace]
provider = "claude"   # WORKAROUND mc-h7g7 ... mctl has no provider-switch (gap mc-21xt)
```

So on kolchin:

```
! ssh kolchin "sed -i '' '1a\\
provider = \"claude-primary\"
' /Users/gascity-user/HQ/city.toml" && ssh kolchin 'zsh -lc "cd ~/HQ && gc reload"'
```

**Safe to run now**: the two shared-store pools were already capped to 0 this
session (`mathcity.brief-operator`, `mathcity/gc.review-synthesizer`), so this
will not wake workers against QUIMBY's shared mathcity store. Config verified
loading after those caps — `gc agent list` → 85 agents, exit 0.

My own permission classifier blocked this edit with two different tools
(`sed`, `python3`). I did not route around it. It needs a human.

**Caveat worth respecting**: the pack's own skill
`subdomains/dev/skills/switch-city-worker-provider` says *"Do not hand-edit
city config as a pack fix... label it as a site-local workaround, snapshot
before changing it."* So the above is a site-local workaround; the durable fix
is `~/bin/mathcity-provider` writing `[workspace] provider` instead of
`[defaults.agent] provider`. That script currently validates with
`gc config explain`, which only *warns* on unknown fields — which is exactly
why this drift survived unnoticed.

---

## 3. Kolchin state as left

Healthy. Supervisor PID 40025, dispatchers up since Sep 6 18:38, never
restarted. Do **not** restart the controller casually — the `gs` store carries
a standing Taylor policy: *"City restart (Phase 4) is gated on Taylor's trust
being established... requires explicit Taylor go-ahead."*

- **gascity rig**: 10/10 doctor checks pass. Empty, and that is probably
  correct — kolchin's rig is prefix `ga`; the canonical gascity rig is prefix
  `gs` (563 beads on the laptop; upstream `tdupu/gascity-dolt` is a stale 448
  on a legacy schema). Populating it means a second clone of a store
  mid-migration = the #4259 silent-fork case. Left alone deliberately.
- `ga` database: **6.6 GB → 280 KB** (68 orphaned temp packs cleared,
  0 successful fetches ever).
- **Test rig `mathcity-testrig`** (prefix `mt`): live, isolated, fully
  provisioned with providers on all 20 roles. Run log committed there at
  `FORMULA-TEST-LOG.md` (`d7970b6`).
- Config backups on kolchin: `~/HQ/city.toml.bak-*` (several, timestamped).

**Isolation held all session** — `bd show ma-1` not found, no dolt remote, no
git remote on the test rig. QUIMBY's work was never touched.

---

## 4. Filed this session — tdupu/mathcity #257–#264

| # | Sev | Defect |
|---|---|---|
| #257 | P1 | `[defaults.agent].provider` silently discarded → every pool skipped → city runs nothing |
| #264 | P1 | Pool operators deadlock forever on interactive permission prompts (33 min observed) |
| #258 | P2 | `mol-do-work` close ordering unsatisfiable — root never closes |
| #259 | P2 | One bad `patches.agent` aborts *every* gc command incl. read-only diagnostics |
| #260 | P2 | `gc rig add` aborts config write after creating the store; new rig gets dolt port 0 |
| #261 | P2 | `superpowers-review` unbuildable — unknown target `superpowers.code-reviewer` |
| #262 | P2 | `gc order check` renders a false condition as "check command failed" |
| #263 | P2 | `bd dolt pull` dies at 15s read timeout, orphans ~90 MB/attempt |

Most are **gc/bd core**, not repairable inside `~/repos/mathcity`. #256
(pre-existing) is the one this session's code change addresses.

---

## 5. Formula sweep results (completed before this)

11 of 13 workflows completed; 86 of 104 beads closed. Adjudication verified
end-to-end: `staging → draft → review → 18 gates → .pile → stack → decision →
archive`, canonical record on bead `mt-q5m` (`Type: decision`, `CLOSED`).

The two that did not close are the two filed defects doing exactly what the
filings predict: `mt-2cr` (#258, structurally cannot close) and `mt-gv3` +
`mt-rys` (#264, held by the deadlocked session).

Invocation taxonomy measured across 88 formulas — convoy-targeted vs
parameterized vs directly slingable — is in `FORMULA-TEST-LOG.md` and is what
the new planner encodes.

---

## 6. Corrections I made to my own earlier claims

Recorded so they are not re-derived or re-believed:

- **Pool caps were never the cause.** Both run-operator pools were pinned to 0
  and it looked causal. Pools are skipped for a missing provider *before*
  capacity is consulted. Raising caps changes nothing.
- **The provider bug bites one layer deeper than first reported.** Not just
  run-operators — *every role a formula's steps route to*
  (`gc.implementation-worker`, `gc.gap-analyst`, `gc.publisher`,
  `gc.task-decomposer`, `gc.implementation-reviewer`). Patching only the
  run-operator left six workflow roots stalled with no assignee.
- **The six `brief-*` "failing" condition orders are not broken.** Their check
  ends in `grep -q`, which exits 1 on no match. That is `condition false`, the
  normal state. Filed as #262.
- **The "448 beads" figure is misread.** It matches Taylor's *closed* count;
  the live `gs` store has 563.
- **My FD-leak measurement was worthless once.** The flat 550 reading came from
  a reload that had *aborted*. A successful reload goes 550 → 684.

---

## 7. Not started

"Expose all working formulas to mctl **then to the MCP**" — the mctl CLI half.
`assets/scripts/mctl_core/cli.py` (1126 lines) would need a `formula dispatch`
subcommand reading through the same `plan_formula_dispatch`, so the CLI and MCP
cannot disagree about what a dispatch *is*. Do that after the MCP tool is green.
