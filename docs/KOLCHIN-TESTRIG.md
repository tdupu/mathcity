# The kolchin test rig — an isolated city lane for exercising formulas

> Written 2026-09-07 from a live run on `kolchin`. Every claim below cites the
> command or artifact that produced it; per P6.2 an unexercised thing is named
> `NOT PROBED` rather than assumed to work.
> Companion: [FORMULAS-STATUS.md](./FORMULAS-STATUS.md) (per-formula census).

## 1. Why a test rig exists

Exercising formulas needs a lane where a mistake costs nothing. The obvious
candidates were not that lane:

- **The `mathcity` rig on kolchin is a replica of the store the other city
  works.** Its history was flattened by the `mol-dog-compactor` order on
  2026-09-06 23:25 (`kolchin-bot`, "compaction: flatten history", 2 commits
  remaining), so it can no longer pull, and any work done in it is stranded.
  At the time of writing it held 114 beads routed to `mathcity/gc.run-operator`
  and 20 to `mathcity/gc.implementation-worker` — other agents' work.
- **The `gascity` rig on kolchin is empty** and is prefix `ga`, while the
  canonical gascity rig is prefix `gs`. Different namespace; see §6.

So `mathcity-testrig` was created as a lane that cannot touch either.

## 2. What it is

| Property | Value |
|---|---|
| Path | `/Users/gascity-user/repos/mathcity-testrig` |
| Bead prefix | `mt` |
| Dolt database | `mt` (on the shared city server, port 14315) |
| Dolt remote | **none** |
| Git remote | **none** |
| Registered in | `~/HQ/city.toml` (`[[rigs]]`) + `~/HQ/.gc/site.toml` (path binding) |

### Isolation, verified four ways

Re-checked at the start and end of every run:

```
bd list                 # returns only mt- beads
bd show ma-1            # not found — the mathcity database is unreachable from this rig
bd dolt remote list     # no remotes; nothing syncs outward
git remote -v           # empty
```

Isolation is at the **database** level, not the process level: this rig shares
the city's Dolt server process with `hq` and `ma`. That is the honest
description — `mt` is a separate database on a shared server, and the prefix
cannot collide with `ga` or `ma`.

### Pools

The rig carries the full mathcity agent roster. It is deliberately **not**
covered by the pool-cap patches that pin `mathcity`/`gascity` run-operators to
zero, so it inherits default capacity and can actually run work.

## 3. Standing it up surfaced two rig-creation defects

Both filed; both had to be worked around by hand.

- **`gc rig add` aborts the config write after creating the store**
  ([#260](https://github.com/tdupu/mathcity/issues/260)). It refuses to rewrite
  `city.toml` while the file contains keys the running binary does not
  recognise, but only *after* initialising the beads database — leaving a
  half-registered rig. Worked around by appending the binding to
  `~/HQ/.gc/site.toml` directly.
- **A new rig resolves Dolt port 0** ([#260](https://github.com/tdupu/mathcity/issues/260))
  while its generated `config.yaml` claims `gc.endpoint_status: verified`.
  Fixed by writing `.beads/dolt-server.port` (`14315`) by hand, as the other
  rigs have.

## 4. What was repaired to make formulas execute at all

### 4.1 Provider resolution — the city ran nothing

[#257](https://github.com/tdupu/mathcity/issues/257). `~/bin/mathcity-provider`
writes the provider into `[defaults.agent]`, which this `gc` binary discards as
an unknown field. Every pool was therefore skipped:

```
buildDesiredState: pool "...": unknown provider: provider is required;
  set agent.provider or workspace.provider to a key in [providers] (skipping)
```

This was misread twice as a pool-capacity problem. It is not: **pools are
skipped before capacity is consulted**, so raising a cap changes nothing. The
fix is `[workspace] provider = "<name>"`, the form the working city uses.

The bug bites one layer deeper than the run-operator: it also skips every
*role* a formula's steps route to (`gc.implementation-worker`, `gc.gap-analyst`,
`gc.publisher`, `gc.task-decomposer`, `gc.implementation-reviewer`). Patching
only the run-operator left six workflow roots stalled with no assignee.

Evidence it was the cause: after setting the workspace provider, the `mayor`
named session materialised for the first time and `bd.dog` woke — both had been
in the skipped set.

### 4.2 mctl was unusable on kolchin entirely

[#265](https://github.com/tdupu/mathcity/issues/265). `_resolve_source_checkout`
treats a rig's pack `source` as a filesystem path unconditionally. A URL source
is not absolute, so it is joined onto the city root:

```
path: /Users/gascity-user/HQ/https:/github.com/tdupu/mathcity/tree/main/assets/brief-pipeline/paths.toml
```

and the error blames a missing `paths.toml` — a real file, so the reader goes
looking for it (copying one in changes nothing; the resolver was never going to
look there). The diagnostic reports a consequence as the cause.

Worked around by setting `source_checkout` on each rig in `city.toml`, which
the resolver consults **before** the imports, so version pins are untouched.

## 5. The `formula_dispatch` surface

[#256](https://github.com/tdupu/mathcity/issues/256) — `formulas_catalog` could
list every formula and nothing on the typed surface could run one, so dispatch
meant leaving the surface for a hand-typed `gc sling`.

Now exposed on both adapters, through **one** resolver
(`mctl_core/formula_dispatch.py`), so the CLI and the MCP cannot disagree about
what a dispatch is:

```
mctl formula list
mctl formula dispatch <name> [--var k=v]... [--on <bead>] [--target <agent>] [--dry-run]
```

MCP tool `formula_dispatch` — mutating, dry-run by default (an agent gets the
preview-first default; a human at a shell who typed the name does not).

### What it refuses, and why that is the point

It takes a formula **name** and variables **as data**, and composes the argv
itself. It accepts no `command`/`argv`/`shell` parameter — a caller-supplied
command would run with the typed surface's authority while being audited less
than the shell it replaced. Asserted by
`tests/mctl/test_formula_dispatch_tool.py::test_the_tool_takes_no_command_string`.

Two consequences, both tested:

- an unknown formula is refused **by name** against the same catalogue
  `formulas_catalog` reads, with `did_you_mean` (`brief-prp` → suggests
  `brief-prep`);
- every variable is one argv entry — nothing is joined on spaces, so
  `report_path=a b; rm -rf /` survives as a single argument.

### The two invocation shapes are not interchangeable

```
gc sling <target> <bead> --on <formula>    targeted    (--on / bead_id)
gc sling <target> <formula> --formula      untargeted
```

A formula referencing `{{convoy_id}}` or carrying a drain step **requires** the
targeted form and fails instantiation with `convoy_id requires a targeted
formulas v2 invocation` otherwise. The caller's data selects the shape rather
than the tool guessing, because guessing wrong produces an error that reads
like a defect in the formula.

### Registration

Adding a tool trips ten guard tests demanding registration in five places. All
five were updated (none weakened); the guard's own failure message enumerates
them. Suite after: **2251 passed, 0 failed**.

## 6. What was NOT done, and why

- **kolchin's `gascity` rig was left empty.** It is prefix `ga`; the canonical
  rig is prefix `gs` (563 beads live; the upstream `tdupu/gascity-dolt` is a
  stale 448 on a legacy schema `bd` refuses to open). Populating it means a
  second clone of a store mid-migration — the #4259 silent-fork case. Left
  alone deliberately.
- **The shared-store pools were kept asleep.** `mathcity.brief-operator`,
  `mathcity/gc.review-synthesizer`, `mathcity/gc.implementation-worker` and both
  `gc.run-operator` pools are capped to 0, so setting the city-wide provider
  could not wake workers onto another agent's beads.
- **`superpowers-*` review formulas remain unbuildable** —
  [#261](https://github.com/tdupu/mathcity/issues/261).

## 7. Operating note: wedged operator sessions

[#264](https://github.com/tdupu/mathcity/issues/264). A pool-spawned operator
can park **forever** on an interactive approval prompt; the session is detached
with no human at the pane, so nothing answers and nothing reaps it. The bead
stays `in_progress` and `gc status`, `bd list` and the dashboard all show it as
healthy work. Observed twice, ~3h apart, one session parked 33min and another
over 2h.

**The safe remedy is to kill the session, not to answer its prompt.** Killing
means the guarded operation does not happen and the claim returns to the queue;
answering means it happens without the human the prompt was asking for. This is
not pedantry — the second wedge was:

```
Dangerous rm operation on statically-unresolvable target:
/Users/gascity-user/repos/mathcity-testrig/*
```

An operator had tried to delete the entire rig. Any fix shaped like
"auto-approve so unattended work proceeds" would have executed it. Fail-closed
is the only safe default; the deadlock is the lesser of the two failures.

```
tmux -L HQ kill-session -t <session>     # pool respawns, work resumes
```

Note the socket is `-L HQ` (named for the city), not the default socket. The
default socket has no entry and `tmux ls` reports "no server running", which
reads as a dead fleet when the fleet is fine.

## 8. Run log

Per-run detail lives in the rig itself, committed there:

- `FORMULA-TEST-LOG.md` — the first sweep (invocation taxonomy across 88
  formulas; 11/13 workflows completed)
- `MCP-SWEEP-LOG.md` — every catalogued formula exercised through the MCP tool
- `SMOKE-TEST.md` — the first end-to-end molecule, written by the agent that
  ran it, including the `mol-do-work` close-ordering defect it found
  ([#258](https://github.com/tdupu/mathcity/issues/258))
