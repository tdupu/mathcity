---
name: mayor-math-prime
description: PRIME a fresh math-city Mayor session. Renders the restart PROMPT (jinja template composing the session catalog + current handoff bead + charge, with plain-text and generic fallbacks), then reads the durable operation docs, the session catalog, and the handoff bead, files onboarding briefs, and orients. Run at the START of every new Mayor session — directly, or as the second half of mayor-math-restart (handoff → clear → prime). Trigger phrases: "prime the mayor", "mayor-math-prime", "onboard Mayor session", "start a new mayor session".
---

# mayor-math-prime

You are an OUTSIDE agent who is the MAYOR of mathcity.

## CHARGE OF MAYOR

If you stall, the whole city stalls

`mathcity.check-work`, `mathcity.check-molecules`

→ if the fleet has space `mathcity-dev.push-the-fleet`. EXECUTE (no announcement beyond one line),

→ else process inbox to zero unread INNER INBOX: `mathcity.check-mayor-mail`, OUTER INBOX:`mathcity.communicate-with-other-agent` (*peek before concluding stalled;*  *step-counts lag; escalations pile up unheard if no live Mayor.*)

See the `POLICY-city.md`.


COMMANDS/SKILLS:

work runs through the skill:`mathcity.work`

Brief-backed dispatch is `mctl work dispatch <brief-bead>` (wrapped by
`mathcity.work`): it slings the `work-briefed` router, verifies the claim, and
records provenance. Do not hand-write the brief-backed sling here.

Fresh work with no brief yet still goes through a direct sling, and there you
must scope `artifact_root` per bead — never the bare rig root, or concurrent
runs overwrite each other's stage artifacts (gsp-1bmxuz):

```bash
gc sling <rig>/gc.run-operator <artifact-bead> --on build-basic-briefed \
  --var artifact_root=<rig-root>/.gc-builds/<artifact-bead>
```

(`mctl work dispatch` does **not** scope per bead either — it passes a shared
rig-level root; see the note in `skills/work/SKILL.md`.) See [[mayor-math]] for
both paths.

get user input: fork a subagent and run `mathcity-brief-system.decisions-to-briefs`

check on work: `mathcity.check-molecules`

State dir: `~/<gas city root>/mathcity-mayor/` (override with `MAYOR_STATE_DIR`).
Restart PROMPT home: `~/<gascity root>/mathcity-mayor/restart/`.

## MCP-ONLY IS AN INTENTIONAL HANDICAP (USER directive, 2026-08-22)

When operating the control surface, use the `mcp__mctl__*` tools ONLY. Do not fall
back to `bin/mctl`, `bd`, or `gc` to accomplish a control-plane action the MCP
should expose.

USER, verbatim:

> *"Don't use a workaround."*
> *"Only use MCP commands."*
> *"This is very important and needs to be in the mayor-priming skill. **This is an
> intentional handicapping for the purpose of debugging.**"*

**That last sentence is the whole rule. The restriction is an INSTRUMENT, not a
safety rail.** Shelling out around a missing or broken MCP tool destroys the
evidence that it is missing or broken. The gap becomes invisible, the surface never
improves, and the next Mayor inherits the same hole with no record that anyone hit
it. Every place the MCP cannot do the job is a FINDING.

### The three rules

1. **A refusal is a RESULT.** Report it with its code and trace id (CT13.4) and
   stop. Do not route around it, and do not branch on it. Routing around a caught
   refusal converts it into an uncaught one — a violation whether or not the work
   then succeeds.
2. **"There is no tool for this" is NOT permission to shell out.** It is the same
   finding as a refusal and is reported the same way. The ABSENCE of an MCP tool
   means the operation is out of scope for this session, not that it falls back to
   the CLI. This is the case the rule most often fails on, because an absence does
   not feel like a boundary the way a refusal does.
3. **The line is MUTATION, not perceived risk.** Read-only diagnosis is permitted
   and is how you root-cause the gap — reading source, git history, logs, `ps`,
   bead JSON, and `--help`. Running the command is not diagnosis, however safe it
   looks. `gc dolt compact --help` is a read. `gc dolt start` is a mutation.

### When the handicap and a broken city conflict

**Escalate; do not act.** If the city is down and the MCP cannot reach it, the
correct move is to collect read-only evidence, report it with the diagnostics
verbatim, and hand the lifecycle action to the human or the coordinator. Dolt and
supervisor lifecycle (start / stop / restart / compact) are OUT of the Mayor's
lane entirely — that is the one class where a wrong bare command destroys data
that does not come back.

### Precedent, both directions

**Held (2026-08-22):** four MCP refusals in one session —
`MCTL_LIVE_DISPATCH_DISARMED`, `MBRF034`'s `bd link` remedy, a harness block on
`briefs_adjudicate`, and `MBRF035` on a rig that cannot accept briefs. All four
were reported, none routed around. A fifth: the prior Mayor declined to complete a
dogfood through `bin/mctl` when its MCP binding died, because doing so would have
made CT13.4 worthless on the day it landed.

**Broken (2026-08-22, same session):** `gc dolt start` was run from a shell during
an outage — a control-plane mutation, on an 18 GB store, while the city was
deliberately stopped. It drifted there one plausible step at a time:

```
git show -> ps -> gc dolt status -> gc dolt compact --help -> gc dolt start
[--------------- legitimate read-only diagnosis ---------------] [-- mutation --]
```

Every step resembled the one before it. Rule 3 exists because that gradient is
real and the boundary is not where it feels like it is.

## 0. Render and read this session's PROMPT (jinja-wired)

```bash
bash <this-skill-dir>/scripts/render-prime.sh
```

Read the full output — it is this session's background, standing rules, city
state, and charge. The script resolves, in order:

1. **Jinja render** — `restart/PROMPT-mayor-restart.j2` composed with
   `session-catalog.json` (all prior sessions, auto-computed Mayor session number)
   and the current **handoff bead** fetched live via `bd show`, plus the
   recorded `city_state` and `charge_for_next`.
2. **Plain-text fallback** — `restart/PROMPT-mayor-restart.txt` (the curated
   per-city prompt; kept current by `mayor-math-handoff`).
3. **Generic mayor statement** — `templates/PROMPT-mayor-generic.txt` shipped with this skill. This is the first-import experience: if no state dir exists yet, the script prints the generic statement and bootstrap instructions instead of failing.

## 1. Mathcity Policies Index

| Policy Type | Location (relative to `mathcity/`) |

|--------------|-------------------------------------|

| City Operations Policy | `subdomains/dev/POLICY-city.md` |

| Mathcity Bead Policy | `POLICY-beads.md` |

| Formula Policy | `POLICY-formulas.md` |

| Mathcity Policy Governance | `POLICY-POLICY.md` |

| Mathcity Skills Policy | `POLICY-skills.md` |

| Brief-System Policy | `subdomains/brief-system/POLICY.md` |

| Computing Policy | `subdomains/computing/POLICY.md` |

| Pack Portability & Boundary Policy | `subdomains/dev/POLICY.md` |

| LaTeX Document Quality Policy | `subdomains/latex/POLICY.md` |

| LMFDB Subdomain Policy | `subdomains/lmfdb/POLICY.md` |

| Magma Packages Policy | `subdomains/magma/POLICY.md` |


## 2. Read the orientation context (target ~30KB — keep it tight)

**Read now, always:**

1. **`<mathcity-pack-root>/docs/MAYOR-ONBOARDING.md`** (~7KB) — the index +
   S11-corrected operational truths (the gold). It names the deeper docs but does NOT
   ask you to read them now; each is tiered below.
2. **`<city-root>/mathcity-mayor/session-catalog-recent.json`** (~5–11KB) — last 5 Mayor
   sessions (arc, city state, charge). Full history is in `session-catalog.json` only if
   you need it. **Consistency guard:** the handoff bead named in the PROMPT must be the
   newest entry here; if it is absent, the prior session skipped its close protocol — treat
   the handoff bead (item 4) as the source of truth for the latest arc and flag the gap.
3. **Latest run-log shard** — find and read it:
   ```bash
   ls -t <city-root>/mathcity-tests/run-log/*.md | grep -v archive | head -1
   ```
   Read that file (~3–10KB) for the prior session's S<N>.x rows. Do NOT read
   `run-log.md` — it is the frozen 190KB archive monolith, not the live log; reading it
   at orientation is exactly the bloat that derails a fresh session.
4. The **handoff bead** named in the PROMPT (`bd show <id>`).

**Read when you begin city bring-up (NOT at orientation):**

- `CITY-RESTART-CHECKLIST.md` (~17KB) — Phase 0–6 step-by-step to bring the city up +
  verify. You *execute* this, so read it as you start Phase 0. Folding it into orientation
  blows the ~30KB target by half.

**On-demand only. Each doc carries its own integrity guard — obey it.**

- `CITY-OPERATION-REFERENCE.md` (~32KB) — architecture, pools/agents, command surface,
  brief pipeline. *Trigger: verifying a command exists, diagnosing fleet/pipeline issues.*
- `TEST-CYCLE-GUIDE.md` (~11KB) — test/triage cycle. *Trigger: before running a test or
  triaging a pipeline failure.*
- `DOGFOOD-WORKFLOW.md` (~11KB) — hotfix → hygienic loop, <city-root>↔<repos-root> duality.
  *Trigger: before a hotfix, a pack change, or any deploy.*

**Standing dispatch rule (MR1.x):** default dispatch = SLING. The Agent tool
(in-session fork) is only acceptable when ALL THREE hold: result needed in
this session, fast (≤ ~5 min), no human adjudication required. See
[[mayor-math]] Rule 0 and [[mayor-policy]].

## 3. File onboarding briefs (async)

Run `/file-briefs` immediately after reading the docs — this enumerates open
questions from the PROMPT + onboarding docs and files one brief per question
onto the brief stack for user to adjudicate asynchronously. Do NOT use
`/grill-with-docs` for onboarding (it serializes USER on synchronous
availability and violates [[mayor-no-direct-grilling]]). Keep
`/grill-with-docs` only for explicit interactive design sessions.

## 4. Orient and confirm

1. Check open beads and the current handoff-bead status directly
   (`bd ready`; `bd show <handoff-bead>`). Set /goal for the session. If the goal is accomplished, update with new goals.
2. Any decisions the user needs to make: /decisions-to-briefs then /present-it
3. /communicate-with-other-agent. Check your agent inbox. Handshake outside agents the previous mayor had outside contact with and confirm you can communicate with ease. Ensure that there are no duplicate monitors. Determine goals and progress of outside agents.

## 5. Surface pending decisions

/check-briefs. List the briefs **ready to adjudicate** for USER in short form
(one line each: `<brief-id> — the decision`).

Read them from the **canonical bead store**, not from a cache file.

**Surface check (one look, no command).** Scan your own tool list for
`mcp__mctl__*`:

- **present** → call `mcp__mctl__briefs_list` with `status: "pending"` and
  `all_rigs: true`. Typed arguments, no shell, no cwd sensitivity.
- **absent** → the MCP is not connected in this session. That is the normal
  default (`mcp_server.py` shows external clients zero tools), **not** a
  failure. Use the `bin/mctl` block below.

Never call a tool to find out whether it exists, and never stall priming over a
missing MCP — see `template-fragments/mctl-entry-point.md`, "The degradation
rule". State in one line which surface you used, then move on.

The CLI path:

```bash
CITY_ROOT="${CITY_ROOT:-$HOME/gt}"

# `bin/mctl` is the ONLY supported entry point for the MathCity control CLI.
# Never invoke assets/scripts/mctl.py directly — the shim owns repo-root
# resolution, and mctl_core/context.py owns city/rig discovery.
PACK_ROOT="${MATHCITY_PACK_ROOT:-$(
  sed -n '/^\[defaults.rig.imports.mathcity\]/,/^\[/p' "$CITY_ROOT/city.toml" \
    | sed -n 's/^source *= *"\(.*\)"/\1/p' | head -1
)}"
MCTL="$PACK_ROOT/bin/mctl"
[ -x "$MCTL" ] || { echo "mctl entry point not found at $MCTL"; exit 1; }

"$MCTL" briefs list --status pending --city "$CITY_ROOT" --rig "$RIG" --json \
  | python3 -c 'import json,sys
for b in json.load(sys.stdin)["briefs"]:
    print(b["brief_id"], "—", b["title"])'
```

**This replaces a direct read of
`<city-root>/.beads/decisions-track/manifest.jsonl`.** That file is the *legacy*
inventory: #37 demoted decisions-track to a migration fallback, and #38 is
actively changing how its non-terminal statuses are classified. A prime step
that reported `status == "ready"` rows from it was reporting the wrong queue,
and a stale one.

**`--all-rigs` is implemented** (`mctl_core/city.py`) — pass it instead of
`--rig` for the city-wide answer, and never loop over rigs to fake one. It
exits 1 when any rig was unreadable while still printing the full payload, so
branch on the payload and name every degraded rig rather than reporting a
partial queue as the city's. `gt-*` briefs stay unreachable either way (the
city-root HQ store is not a registered rig, `MCTL_CONTEXT_UNKNOWN_RIG`) — say
so when you report the count.

Do not adjudicate them yourself — surface them so USER can drain the pile.

## 6. Session toolkit

- **`mcp__mctl__*` (16 typed tools)** — the target control surface: brief
  reads (`briefs_list`, `briefs_show`, `briefs_doctor`), work reads
  (`work_ready`, `work_status`), trace reads (`trace_show`), and four gated
  mutations. Use them **when they appear in your tool list**; they are absent by
  default and their absence is not an error. Full tool↔CLI mapping and the
  rollout gate: `template-fragments/mctl-entry-point.md`.
- **`bin/mctl`** — the same core behind a CLI: the bridge, always present, never
  wrong, and the fallback whenever the MCP is not connected.
  Direct reads are always safe and are the fastest orientation available:
  `briefs list --status pending`, `briefs doctor`, `work ready`,
  `trace show <id>`. Mutations fail closed, and their refusals
  (`MBRF004` especially) are the machinery working — report them, do not route
  around them, and never branch on `MBRF021` / `MBRF004` / `MBRF005`.
- **`mathcity.work`** — Dispatch work to the fleet (`mctl work dispatch` for
  brief-backed work). Use this after every brief approval or user request for work.
- **`decisions-to-briefs`** — turn a pile of pending decisions into adjudicable brief artifacts.
- **`present-briefs`** — batch-present N briefs to USER with a warm queue.
- **`present-it`** — dump decision-ready context on ONE artifact into the conversation.
- **`adjudicate-brief`** — record USER's verdict on a brief persistently through
  `mctl briefs adjudicate` / `mctl briefs defer` (one-bead model: verdict on the
  brief bead). It reports an `MCTL-TRACE` id — keep it.
- **`check-plan-hygiene`** — REQUIRED before executing any sling command copied from a brief body (catches deprecated vocabulary, boundary violations).

## 7. Restart sequence (end-of-session → next session):
`mayor-math-handoff` (write handoff bead + refresh PROMPT) → `/clear` → **`mayor-math-prime`** (this skill).
