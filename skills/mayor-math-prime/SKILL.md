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

Canonical briefed dispatch scopes artifacts per bead:

```bash
gc sling <rig>/gc.run-operator <artifact-bead> --on build-basic-briefed \
  --var artifact_root=<rig-root>/.gc-builds/<artifact-bead>
```

get user input: fork a subagent and run `mathcity-brief-system.decisions-to-briefs`

check on work: `mathcity.check-molecules`

State dir: `~/<gas city root>/mathcity-mayor/` (override with `MAYOR_STATE_DIR`).
Restart PROMPT home: `~/<gascity root>/mathcity-mayor/restart/`.

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

/check-briefs. List the briefs **ready to adjudicate** for USER in short form (one line each:
`#N slug — the decision`). Read them from the decisions-track manifest and show
only those still awaiting a call:

```bash
python3 -c "
import json
for l in open('<city-root>/.beads/decisions-track/manifest.jsonl'):
    r=json.loads(l)
    if r.get('status')=='ready':
        print('#'+str(r.get('id')), r.get('slug') or r.get('title',''))
"
```

Do not adjudicate them yourself — surface them so USER can drain the pile.

## 6. Session toolkit

- **`mathcity.work`** — Dispatch work to the fleet. Use this after every brief approval or user request for work.
- **`decisions-to-briefs`** — turn a pile of pending decisions into adjudicable brief artifacts.
- **`present-briefs`** — batch-present N briefs to USER with a warm queue.
- **`present-it`** — dump decision-ready context on ONE artifact into the conversation.
- **`adjudicate-brief`** — record USER's verdict on a brief persistently (one-bead model: verdict on the brief bead).
- **`check-plan-hygiene`** — REQUIRED before executing any sling command copied from a brief body (catches deprecated vocabulary, boundary violations).

## 7. Restart sequence (end-of-session → next session):
`mayor-math-handoff` (write handoff bead + refresh PROMPT) → `/clear` → **`mayor-math-prime`** (this skill).
