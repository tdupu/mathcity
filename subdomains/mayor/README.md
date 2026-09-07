# The Mayor pack — an opt-in city Mayor

Parent: [../../README-subdomains.md](../../README-subdomains.md)

This pack ships a city-scope **Mayor** agent for a mathcity city: the agent
definition, its prompt (mathcity doctrine and the continuity loop), an Opus
provider, and the mctl MCP surface. The rulebook is
[POLICY.md](./POLICY.md); this README is the guided tour.

## Importing it does not start a Mayor

This is the important property, so it is stated first.

A Gas City agent only *runs* when a city declares a named session for it.
That declaration lives in the **city's own** `pack.toml`, not here:

```toml
# <city-root>/pack.toml — the city's choice, not the pack's
[[named_session]]
  template = "mayor"
  mode = "always"
```

This pack contains **no** `[[named_session]]` and **no** `mode = "always"`.
So:

| City | Result |
| --- | --- |
| does not import this pack | no Mayor |
| imports it, declares no named session | **no Mayor** |
| imports it and declares one | a Mayor runs |

A mathcity user who does not want a Mayor does not get one, and there is
nothing to opt out of. That is by construction, not by configuration — which
is why the agent lives in a separate subdomain pack instead of in the mathcity
root pack, where it would be forced on every consumer.

## What you get

| Piece | File | Notes |
| --- | --- | --- |
| Agent | `agents/mayor/agent.toml` | `scope = "city"`, one session, `wake_mode = "fresh"` |
| Prompt | `agents/mayor/prompt.template.md` | doctrine, boundaries, continuity, dispatch discipline |
| MCP | `agents/mayor/mcp/mctl.template.toml` | the mctl typed surface, including `formula_dispatch` |
| Model | `pack.toml` → `[providers.claude-opus]` | Opus, without touching the city's shared providers |

### Why Opus

The Mayor's work is judgment under incomplete information: deciding what the
city should do next, reading contradictory signals, and refusing work that
should not run. That is the one role where model capability changes the
*answer* rather than the latency. Worker roles are not pinned here.

The provider sets only the model. `base = "builtin:claude"` inherits whatever
`CLAUDE_CONFIG_DIR` the city's own Claude provider supplies, so a city running
its agents under a particular account keeps that account for the Mayor.

### Why the MCP definition looks the way it does

`bin/mctl` is the only supported entry point for the control CLI — the shim
owns checkout resolution and `mctl_core/context.py` owns city/rig discovery
(see [`template-fragments/mctl-entry-point.md`](../../template-fragments/mctl-entry-point.md),
enforced by `tests/mctl-shim-callsite/`). But its path is machine-local, and
pack content may not carry absolute home paths, so the definition resolves it
at launch:

1. `$MATHCITY_PACK_ROOT`
2. `source_checkout` in the city's `city.toml`

Ordinary `[imports.mathcity] source` is deliberately not consulted: on a city
that pins the pack by URL it holds `https://github.com/...`, and joining that
onto a filesystem path produces the nonsense that `tdupu/mathcity#265` is filed
for. If neither source resolves, the server refuses to start and says what to
set — resolving to garbage is worse than resolving to nothing.

## Setup

```bash
# 1. import the pack into the city
gc import add mathcity-mayor \
  https://github.com/tdupu/mathcity/tree/main/subdomains/mayor

# 2. declare the session in <city-root>/pack.toml (this is the opt-in step)
#    [[named_session]]
#      template = "mayor"
#      mode = "always"

# 3. verify
gc mcp list --agent mayor      # should name the mctl server
gc status                      # the mayor should materialize
```

If `gc mcp list --agent mayor` reports "No projected MCP servers", the MCP
directory was not picked up — gc discovers it by convention at
`agents/<name>/mcp` (`internal/config/agent_discovery.go`).

## Continuity

The Mayor is expected to hand off rather than die with its context:

- `mayor-math-handoff` — writes the chained handoff bead, extends the run log,
  updates the restart prompt. Run at session end.
- `mayor-math-prime` — renders that prompt and re-primes. Run at session start.
- `mayor-math-restart` — handoff, clear, prime.
- `gc handoff "<summary>" "<context>"` — the built-in fast path; mails the
  successor and restarts. Prefer the skills when the session produced findings
  worth keeping, because mail is not a durable record and a bead is.

## One operating rule worth reading before you run this

A pool session can park forever on an interactive approval prompt — nothing
answers it, nothing reaps it, and the city reports it as healthy work. **The
remedy is to kill the session, not to answer its prompt.** Killing means the
guarded operation does not happen; answering means it happens without the
human the prompt was asking for.

This is not theoretical. One such prompt on a live host was an agent
attempting to delete an entire rig directory; the prompt was the only thing
that stopped it, and `Yes` was the highlighted default. The prompt text is in
the Mayor's own doctrine for this reason.
