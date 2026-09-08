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

---

## 9. The Mayor (added 2026-09-07)

kolchin runs a city-scope Mayor. Two things about it are worth knowing before
you touch it.

**It was configured but dead for a long time.** `[[named_session]] template =
"mayor"` had been declared in the city's `pack.toml` all along, and `gc status`
reported it as `reserved-unmaterialized (always)`. It had never once run,
because every pool was being skipped for the missing provider
([#257](https://github.com/tdupu/mathcity/issues/257)). Fixing the provider
materialised it — so the Mayor appearing was a *symptom of the repair*, not a
new decision. Anyone reading old session notes will find "there is no Mayor
here", which was true in practice and false in configuration.

**It now comes from a pack, not from this host.** The agent, its prompt, and
its MCP definition live in `subdomains/mayor/` in the mathcity repo and arrive
by import:

    [imports.mayor]
      source = "https://github.com/tdupu/mathcity/tree/main/subdomains/mayor"

The stock 63-line city-local template was retired to
`<city-root>/agents/.mayor-retired-stock-*`. The qualified agent name is
`mayor.mayor` (`<import-key>.mayor`), which is what the city's
`[[named_session]]` and every `gc mcp list --agent` call must name.

Importing that pack does **not** create a Mayor anywhere else: the pack ships
no `[[named_session]]`, so instantiation stays the city's decision. See
[subdomains/mayor/README.md](../subdomains/mayor/README.md).

### Model and MCP on this host

| Piece | Value here |
|---|---|
| Provider | `mayor-model` → `base = "provider:claude-agexplained"`, `args_append = ["--model", "opus"]` |
| MCP | `mctl`, giving briefs / work / beads / `formula_dispatch` |
| Verified | `--model opus` on the process; mctl server running as a child of the Mayor session |

The provider is defined in **this city's** `city.toml`, not in the pack, and
that is deliberate: a working Claude provider carries an authenticated
`CLAUDE_CONFIG_DIR`, which is machine-local and an absolute home path, so pack
content may not contain it. The first attempt shipped
`base = "builtin:claude"` in the pack on the assumption it would inherit the
city's account. It does not — the Mayor came up sitting on Claude Code's
"Select login method" prompt, a session that looks alive in `gc session list`,
holds its slot, and can never do anything. If you ever see that, the provider
resolved to an unauthenticated one.

### MCP delivery needs an explicit projection

`gc reload` alone does **not** write `<city-root>/.mcp.json`. Until it is
projected, the Mayor runs with a prompt describing tools it does not have:

    gc internal project-mcp --agent mayor.mayor --workdir <city-root>

Then cycle the session (kill it — see §7) so the new session picks it up.
Confirm with `gc mcp list --agent mayor.mayor`, which reports
"No projected MCP servers" when it has not landed.

### A standing warning it emits

`gc reload` warns that `mode = "always"` with `wake_mode = "fresh"` "starts a
fresh provider session after every drain; use only for a deliberate
restart-per-cycle actor". For a Mayor that hands off each cycle that is
arguably the intended shape, but it is an open question, not a settled one.

---

## Build hygiene audit — kolchin, 2026-09-07

`check-build-hygiene` against
[subdomains/dev/POLICY.md](../subdomains/dev/POLICY.md). Read-only audit;
findings below, remediation named per item.

**Verdict: revise** — five findings, none blocking current operation.

### Clean

| Check | Result |
|---|---|
| C3 remote lockstep (P1.7) | `gascity` and `mathcity` both equal `origin/main`, 0 unpushed |
| C4 imports (P1.4) | all five imports are remote URLs pinned by sha; **no local-path imports**, so the city stands on no unpushed local content |
| C5 skill exposure (P1.8/P1.3) | 77 skills in the city sink, **0 dangling symlinks** |
| P1.11 data plane | `tdupu/gascity-dolt` and `tdupu/mathcity-dolt` both verified `isPrivate: true` |
| P1.15 dolt naming | both follow `<owner>/<rig>-dolt` |
| P5.1 vocabulary | `gc agent list` shows **0** live `gastown.*` agents |
| P1.10 pack content | no absolute home paths, keys, or emails in `subdomains/mayor/` |

### Findings

**F1 — P1.6: binaries carry no VCS stamp.** `go version -m` on both `gc` and
`bd` returns **zero** `vcs.*` lines (`mod … (devel)`), so the rule's own test —
`vcs.revision` equal to HEAD and `vcs.modified=false` — cannot be evaluated at
all. Per P6.2 this is reported as *unverifiable*, not as a pass.
*Corroboration, not proof:* the running API reports `build_id 02c9e97f8` and
`~/repos/gascity` HEAD is `02c9e97f8a94…`, so `gc` does appear to come from that
commit.
*Remediation:* rebuild through `update-gascity-from-source` /
`update-beads-from-source`, which stamp VCS metadata.

**F2 — P1.6: shadowed binaries on `$PATH`.**

    gc  ->  ~/go/bin/gc          (wins)   and  /usr/local/bin/gc
    bd  ->  ~/go/bin/bd          (wins),  ~/.local/bin/bd,  /usr/local/bin/bd

`/usr/local/bin/bd` is a Homebrew symlink into `Cellar/beads/1.2.2`, shadowed by
a Go build. Two `gc` copies are byte-identical in size and timestamp, but owned
by different users (`gascity-user` vs `tdupuy`).
*Remediation:* remove the losers, or declare which is sanctioned.

**F3 — P1.6/P1.7: no `beads` or `gascity-packs` checkouts on this host.**
`~/repos` holds only `gascity`, `mathcity`, `mathcity-testrig`. `bd`'s source is
not present, so its provenance is unverifiable *in principle* here, and the
gascity-packs fork-canonical invariant cannot be checked at all.
*Remediation:* clone both, or record that kolchin is deliberately a
consumer-only host for them and scope the rule accordingly.

**F4 — P5.2: the city has no workspace context files.** No `AGENTS.md`,
`CONTEXT.md`, or `CLAUDE.md` in the city root. P5.2(c) requires the
inside/outside agent distinction to be explicit; with no file it cannot be.
An agent arriving in the city root gets no orientation, which is precisely how
an inside agent ends up editing pack source it does not own.
*Remediation:* add a city `AGENTS.md` carrying the inside/outside distinction.
(The Mayor now carries that distinction in its own prompt, but that covers one
agent, not the workspace.)

**F5 — P1.11/P1.15: the city HQ bead store has no `sync.remote`.** The
`gascity` and `mathcity` rigs both sync; the city store does not, so `hq-*`
beads — session records, order tracking, the city's own management history —
are backed up nowhere.
*Remediation:* `bd dolt remote add` a dedicated private `-dolt` repo for the
city store, then `bd backup init`.

### Site-local workarounds carried by this host (P1.17)

These were applied during the 2026-09-07 session and are **named workarounds,
not fixes**. Each is a hand-edit to `city.toml`, which P1.2 forbids as a
behaviour change route; each is recorded here rather than presented as clean:

| Edit | Root cause | Upstream issue |
|---|---|---|
| `[workspace] provider` | the provider written to `[defaults.agent]` is discarded as an unknown field, so every pool was skipped | [#257](https://github.com/tdupu/mathcity/issues/257) |
| `source_checkout` on three rigs | a URL-form rig source is joined onto the city root and blamed on a missing `paths.toml` | [#265](https://github.com/tdupu/mathcity/issues/265) |
| pool caps on four shared-store pools | no per-rig way to keep a replica's workers asleep | — |
| `[providers.mayor-model]` | pack content may not carry an authenticated `CLAUDE_CONFIG_DIR`, so the city must supply the provider | by design; see [subdomains/mayor/README.md](../subdomains/mayor/README.md) |

Note `gc reload` warns `unknown field "rigs.source_checkout"` three times per
reload: gc discards it, and it works only because mctl parses `city.toml`
itself. That is the same silent-discard class as #257 and should not be relied
on indefinitely.
