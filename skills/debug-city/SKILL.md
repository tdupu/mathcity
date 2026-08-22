---
name: debug-city
description: >
  Diagnose a Gas City that will NOT COME UP, or whose control plane is
  unreachable, or whose instruments disagree with each other. Establishes ground
  truth from probes known to be trustworthy before proposing any fix, and
  refuses to repeat remedies that prior sessions measured as failures. Use when
  `gc start` fails, when every MCP call returns `MCTL_CITY_NOT_ACTIVE`, when two
  status surfaces contradict each other, or when a lifecycle command's output
  does not match what the system is actually doing. Trigger phrases: "the city
  won't start", "debug the city", "debug-city", "city is down", "gc start
  failed", "MCTL_CITY_NOT_ACTIVE", "the city won't come up", "is the city
  actually down", "these two probes disagree", "did stop actually work".
  NOT for a city that is up with an idle fleet — that is `wake-city`. NOT for a
  routine snapshot — that is `city-status`.
---

# debug-city

The city is not coming up, or you cannot tell whether it is up. This skill gets
you to a **defensible statement of what is true** before anyone changes
anything.

## Task boundary

| Situation | Skill |
| --- | --- |
| City is UP, fleet is asleep / not claiming work | `wake-city` |
| Routine "what is running" snapshot | `city-status` |
| Dispatch runs but work does not | `triage-dispatch-errors` |
| **City will not start, or you cannot trust what you are seeing** | **this skill** |

`wake-city` assumes a live control plane. If `bd` and the MCP cannot reach the
bead store at all, its diagnosis steps cannot run — start here, then hand off.

## THE CENTRAL RULE

**Most time lost to a down city is lost to believing a lying instrument, not to
the outage.** Establish ground truth first. Do not act on a single probe, and do
not act on a probe from the untrusted column.

### Instrument trust table — measured, not assumed

| Probe | Trust | Known failure |
| --- | --- | --- |
| `mcp__mctl__mayor_city_state` | **TRUSTED** | Reported `down` + `MAYOR_FLEET_HOST_ABSENT` correctly during a total outage |
| `tmux -L gt ls` | **TRUSTED** | Direct observation of the fleet host |
| `ps` on the supervisor / dolt pids | **TRUSTED** | Direct observation |
| `lsof -nP -iTCP:<port> -sTCP:LISTEN` | **TRUSTED** | Direct observation of a listener |
| `gc dolt health` | ok, three-valued | exit 2 = quarantined, NOT down (see `wake-city` step B) |
| `mcp__mctl__city_health` | **DO NOT TRUST** | Reported `data_plane: healthy` and 17/17 rigs healthy while every bead read returned FATAL. Also maps `rig_id` to directory name naively and reports real stores as missing |
| `gc status` | **DO NOT TRUST** | Times out and renders as "stopped / 0 sessions" (`gs-0cy2`) |
| `gc stop` final line | **DO NOT TRUST** | Printed "City stopped." with the supervisor still running |
| `gc restart` readiness line | **DO NOT TRUST** | Printed "supervisor did not become ready" for a supervisor that became ready seconds later |
| `gc dolt start` output | **DO NOT TRUST** | Printed a FATAL-shaped "cannot resolve runtime port" and exited 0, having succeeded |

**A lifecycle command reports the outcome of the step it ran, not the state of
the subsystem it names.** On a fast install those coincide. Under load they do
not — which is exactly when you are reading them.

## Step 0 — Pre-flight

Read-only. Nothing here changes state.

```bash
# Fleet host — nothing spawns without it
tmux -L gt ls

# Supervisor: alive? how long? which build?
ps -eo pid,lstart,etime,command | grep '[g]c supervisor run'

# Dolt: is anything actually listening?
lsof -nP -iTCP -sTCP:LISTEN | grep dolt
```

Then the trusted typed probe:

```
mcp__mctl__mayor_city_state(rig=<any registered rig>)
```

`state` is four-valued. **`unknown` means a load-bearing probe did not answer and
MUST NOT be read as `down`.**

## Step 1 — Classify the regime before diagnosing

| Observation | Regime | Go to |
| --- | --- | --- |
| MCP reads return `MCTL_CITY_NOT_ACTIVE` | data plane unreachable | Step 2 |
| MCP reads work, `state: down`, 0 panes, `MAYOR_FLEET_HOST_ABSENT` | fleet host absent | Step 3 |
| MCP reads work, panes > 0, no work claimed | **not this skill** | `wake-city` |
| `gc start` exits non-zero | start path failure | Step 4 |

## Step 2 — Data plane unreachable

`MCTL_CITY_NOT_ACTIVE` means the bead store could not be read. It does **not**
mean Dolt is absent. Distinguish:

```bash
lsof -nP -iTCP -sTCP:LISTEN | grep dolt     # is a server listening at all?
```

- **Nothing listening** → Dolt is genuinely down. Escalate; do not start it
  yourself unless that is explicitly your lane.
- **Listening but reads fail** → Dolt is *wedged*, not down. Look for the
  circuit breaker in the caller's stderr:

```
[mysql] read tcp 127.0.0.1:PORT: i/o timeout
[circuit-breaker] 127.0.0.1:PORT/<db>: closed -> open (tripped after N failures)
```

**The breaker flapping open/closed is the signature of a slow database, not a
dead one.** The database named in those lines is the one to investigate — it is
usually the largest store.

## Step 3 — Fleet host absent

Supervisor alive, no tmux server, `pane_count: 0`. Nothing can spawn.

`mayor_city_state` emits `MAYOR_FLEET_HOST_ABSENT` with
`suggested_next_command: gc restart` — this is the documented fix and has worked
across multiple sessions.

**Verify the outcome by observation, not by the command's own output** (see the
trust table):

```bash
tmux -L gt ls                                   # a server should now exist
ps -eo pid,etime,command | grep '[g]c supervisor run'   # note the NEW pid + elapsed
```

A supervisor whose elapsed time is shorter than the readiness wait means the
command's failure message was wrong and it actually succeeded.

## Step 4 — Start path failure

Read the error for **which operation** failed, then check whether the timeout
that bounded it is reachable by configuration.

```
init: beads lifecycle: init rig "<rig>" beads: exec beads init: context deadline exceeded
```

**`providerOpTimeout` is hardcoded and reads no config**
(`cmd/gc/beads_provider_lifecycle.go`): `120s` for `start` / `recover` / `init`,
`30s` otherwise. **No `--timeout` flag, no `city.toml` key, and no unbounded
outer wait can raise it.** If you see `context deadline exceeded` on one of those
three ops, config changes will not help and the fix is upstream in `gc`.

Note the two layers are independent and can disagree in the same run:

```
"no readiness deadline set (pass --timeout on gc start)"   <- OUTER wait, unbounded, correct
"init ...: context deadline exceeded"                      <- INNER per-op, hardcoded, the wall
```

Levers that ARE reachable when init is the blocker:

- **Suspend the failing rig.** A suspended rig's agents are skipped by the
  reconciler, so its `init` never runs. Fully reversible.
- **Reduce concurrent load on the shared Dolt server** before starting, so each
  `init` fits inside its fixed budget.

## Step 5 — KNOWN-FAILED REMEDIES — do not repeat these

Each was measured by a prior session. Re-running them costs hours and can make
things worse.

| Remedy | Verdict | Evidence |
| --- | --- | --- |
| `CALL DOLT_GC()` on the large store to shrink it | **FAILED** | Store stayed the same size, latency did not improve **and then degraded**. The size is *referenced data, not collectable garbage* — GC cannot touch it |
| Raising `setup_timeout` alone | **DEAD CONFIG** | `startup_timeout` binds first and caps it. Set **both**, and note `supervisor reload` no-ops the change — a full restart is required |
| `--timeout` on `gc start` to fix an `init` deadline | **CANNOT WORK** | `providerOpTimeout` reads no config (Step 4) |
| Restarting to get ahead of a resource leak | **COSTS MORE THAN IT SAVES** | A stop/start cycle spends more of the resource than the leak does over the same window |
| Blaming the largest store because it is largest | **NOT ESTABLISHED** | At least one prior session filed this as a root cause and retracted it the same session. Size correlates with slowness; it is not automatically the cause |

## Step 6 — Verify by watching the failure MODE change

The single most productive diagnostic move in this city's history: **apply one
change and watch whether the failure changes shape.** A wall that moves is a
different wall.

```
BEFORE:  outcome=provider_error     duration=31.7s / 33.9s / 36.7s
AFTER:   outcome=deadline_exceeded  duration=1m0.036s / 1m0.030s
```

That shift — error class changed, duration went flat — is what revealed a
timeout inversion that four earlier hypotheses had missed. A fix that changes
nothing about the failure shape did not address the cause, however plausible it
was.

## Guardrails

- **Never `rm -rf` anything under a Dolt data directory**, including `LOCK`
  files. This causes unrecoverable corruption.
- **Never send signals to a Dolt process.** There is no safe stack-dump signal.
- **Collect diagnostics BEFORE restarting.** A blind restart destroys the
  evidence that would have identified the cause.
- **Retry a probe before reporting its verdict.** A single timeout is not a
  diagnosis; more than one session has nearly reported an outage from one
  timed-out call that succeeded instantly on retry.
- **Report a refusal; never route around it.** If a command or tool declines,
  that refusal is a result. Working around it converts a caught error into an
  uncaught one — a violation whether or not the work then succeeds.
- **Two facts side by side are not a cause.** A count and a list do not
  establish a link between them. Measure the link.

## Handoff

Record, in terms the next session can re-derive:

- Which probes you trusted and which you rejected, with their outputs
- The regime you classified (Step 1) and what moved you off it
- Every remedy attempted and whether the failure **shape** changed
- Any trace ids from typed-tool calls

Once the control plane is reachable and panes exist, hand off to `wake-city` for
fleet revival and `city-status` to confirm work is being claimed.
