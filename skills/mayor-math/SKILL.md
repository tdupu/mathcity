---
name: mayor-math
description: Supplement to gc.mayor for Gas Town (gt HQ) context. Provides the correct rig-scoped sling mechanics for build-basic convoy workflows, including the rule that the bare gc.run-operator form doesn't resolve at HQ level and that gt-prefix beads have no worker fleet by default. Invoke alongside or after gc.mayor when about to sling work through build-basic in a Gas Town session.
---

# mayor-math

Supplement to [[gc.mayor]] with Gas Town (gt HQ) sling mechanics. The upstream gc.mayor
skill is community-shared and cannot be edited — use this skill to apply the correct
rig-scoped rules for our setup.

## Canonical operation docs — READ FIRST

The hard-won gold lives in the mathcity pack (`<mathcity-pack-root>/docs/`):
- **MAYOR-ONBOARDING.md** — index + corrected operational truths (start here)
- **CITY-RESTART-CHECKLIST.md** — Phase 0–6 step-by-step to bring the city up + verify
- **CITY-OPERATION-REFERENCE.md** — architecture, pools/agents, brief pipeline, correct command surface
- **TEST-CYCLE-GUIDE.md** + **DOGFOOD-WORKFLOW.md** — the dogfood/test cycle

**Current dispatch pattern:** sling `--on build-basic-briefed` (fires a decision brief at
the terminal step; `push=false` ships nothing) with `interaction_mode=autonomous` for
unattended pool runs. Scope `artifact_root` per bead — never omit it or pass
the bare rig root, or concurrent runs on the same rig silently overwrite each
other's stage artifacts (gsp-1bmxuz):

```
gc sling <rig>/gc.run-operator <bead> --on build-basic-briefed \
  --var interaction_mode=autonomous --var review_mode=agent \
  --var drain_policy=separate --var push=false --var open_pr=false \
  --var artifact_root=<rig-root>/.gc-builds/<bead>
```

**After slinging:** verify the sling took — `bd show <bead>` must show a non-empty
**Assignee**, or `tmux -L gt ls` shows a fresh `gc__run-operator` session. A molecule
root stays OPEN by design until its terminal step fires (count closed `✓` steps climbing
via `bd show <root>`). `gc status` "stopped / 0 sessions" is often a probe timeout —
trust `tmux -L gt ls` + rising step-counts (`gs-0cy2`).

The `build-basic` / `interaction_mode=interactive` pattern below is retained for reference.

## Rule 0 — Fork-vs-sling (gsp-mnfj, supersedes gsp-geuo "always fork")

The Mayor must ALWAYS be available to the next task.

| Situation | Decision |
|---|---|
| Adjudication required | SLING |
| Long-running task | SLING |
| Fast in-session task, no adjudication | FORK acceptable |
| DEFAULT | SLING |

Example sling command:

```
gc sling <rig>/gc.run-operator <convoy-id> --on <formula>
```

Authority: gsp-mnfj (2026-07-16). The earlier "always fork" rule (gsp-geuo) is superseded by gsp-mnfj.

## Rule 1 — Always use the rig-scoped coordinator

The bare `gc.run-operator` does NOT resolve at HQ level. Always use:

```
<rig>/gc.run-operator
```

| Bead prefix | Correct coordinator |
|---|---|
| `he-` | `hecke/gc.run-operator` |
| `gs-` | `gascity/gc.run-operator` |
| `gsp-` | `gascity-packs/gc.run-operator` |
| `as-` | `agent_skills/gc.run-operator` |
| `gt-` | `gt/gc.run-operator` (only after Phase 0 pack.toml fix) |

## Rule 2 — build-basic requires a convoy

`build-basic` has `target_required = true`. You CANNOT use `--formula`. Create a convoy,
add bead(s), then sling against the convoy ID.

## Rule 3 — gt HQ has no worker fleet by default

The `gt-` prefix HQ rig only has `bd.dog`, `claude`, `core.control-dispatcher`. Full
workers (`gc.requirements-planner`, `gc.design-author`, `gc.task-decomposer`,
`gc.implementation-worker`, `gc.implementation-reviewer`) exist only at child rigs.
File work in `he-`, `gs-`, `gsp-`, or `as-` until Phase 0 is applied.

## Rule 4 — Rig prefix must match the work's target repo

| Work targets... | File bead as... |
|---|---|
| `gastownhall/gascity` core | `gs-` |
| `gastownhall/gascity-packs` | `gsp-` |
| `gastownhall/agent-skills` | `as-` |
| `<city-root>` config repo | `gt-` |
| hecke math repo | `he-` |

## Quick sling pattern

```bash
# 1 — bead in rig with workers
bd create -t feature -p 2 -T "<title>" -m "<body>" --rig <rig>

# 2 — convoy
gc convoy create <slug> --owned --target <branch> --merge local --owner gastown.mayor
gc convoy add <convoy-id> <bead-id>

# 3 — plan artifacts (requirements.md + implementation-plan.md, status: approved)
mkdir -p <city-root>/<rig>/plans/<slug>

# 4 — sling
gc sling <rig>/gc.run-operator <convoy-id> --on build-basic \
  --var artifact_root=<city-root>/<rig>/plans/<slug> \
  --var requirements_path=<city-root>/<rig>/plans/<slug>/requirements.md \
  --var plan_path=<city-root>/<rig>/plans/<slug>/implementation-plan.md \
  --var drain_policy=separate \
  --var interaction_mode=interactive \
  --var review_mode=agent \
  --var push=false \
  --var open_pr=false
```

For atomic tasks: `gc sling <rig>/gc.run-operator <bead-id>`

## Handoff discipline (session-catalog `charge_for_next`)

Keep `charge_for_next` under 200 words. The catalog is a routing table, not a history
book. Use this format:

```
TOP: (1) <one-line priority> (2) <one-line priority>
OPEN: <bead-id> <one-line status>, <bead-id> <one-line status>
BLOCKED: <bead-id> blocked on <bead-id>
CITY: <one sentence — fleet status, Dolt ms, anything unusual>
```

No prose narratives. No incident post-mortems. No "READ THIS FIRST" warnings. If a past
incident matters, file a `bd remember` entry and cite the key — let the next Mayor session pull
context on demand rather than front-loading it.

## Reference

- [[gc.mayor]] — upstream coordinator skill
- `<city-root>/mathcity-mayor/` — Mayor session state, restart context, session catalog
