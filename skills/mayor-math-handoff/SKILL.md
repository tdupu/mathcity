---
name: mayor-math-handoff
description: SESSION-END handoff for the math-city Mayor. Writes the chained handoff bead, expands the run-log, adds the session-catalog entry, and updates the restart PROMPT so the next Mayor session can prime from it. Run at the END of every Mayor session — directly, or as the first half of mayor-math-restart (handoff → clear → prime). Trigger phrases: "mayor-math-handoff", "hand off the mayor session", "end the Mayor session", "write the mayor handoff".
---

# mayor-math-handoff

The Mayor session SESSION-END procedure — the first half of the restart cycle
(**`mayor-math-handoff`** → `/clear` → `mayor-math-prime`). Do ALL FIVE steps,
in this order (the catalog entry must exist before the PROMPT is regenerated):

State dir: `<city-root>/mathcity-mayor/` (override with `MAYOR_STATE_DIR`).
Restart PROMPT home: `<city-root>/mathcity-mayor/restart/` (moved from
`~/Documents/misc/PROMPT-mayor-restart.txt` on 2026-07-16).

## 0. Check-zero gate (before writing anything)

Run `/check-zero` on the draft content for the handoff bead body and the
PROMPT update BEFORE committing either to disk or bd. This catches
hallucinated commands, fabricated bead IDs, mathematical claims without
source, and ZFC violations before they propagate to the next session.

Minimum checks:
- Every bead ID cited in the body resolves via `bd show <id>`.
- Every command cited (`mctl work dispatch`, `gc sling`, `git push`, etc.)
  actually exists in the city surface (`bin/mctl --help`, `gc --help`,
  `git --help`).
- Every `mcp__mctl__*` tool cited is one of the real mctl tools. The canonical
  live roster is `tools/list` on a connected server, mirrored by the checked-in
  snapshot `tests/mctl/fixtures/mcp_tool_schemas.json`; `template-fragments/mctl-entry-point.md`
  maps the CLI-mirrored ones. Verify against that roster (never a hand-written
  count — `#162`), and **not** against your current tool list: the MCP is absent
  from most sessions by design, so "not in my tools right now" does not mean the
  tool does not exist, and the next session may well have it.
- No mathematical claims appear that were not verified at source this session.
- No file paths are cited that do not exist on disk (`ls <path>`).

Fail → revise the draft. Do not proceed to step 1 until the draft is clean.

## 0b. Session self-assessment (fill this before writing anything else)

Collect the four self-assessment inputs that feed the catalog entry and the
PROMPT. Do this by introspection — you lived this session.

**Session metadata** (estimate honestly):
- `hours_active`: wall-clock hours from prime to handoff (e.g. `"~3h"`)
- `compactions`: number of context compactions this session (check the
  `/clear` count or conversation structure; if unknown write `"unknown"`)

**Objective evaluation table** — read `charge_for_next` from the PREVIOUS
session's catalog entry (the one that charged YOU). For each objective
listed there, fill one row:

| Objective | Completed? | Remarks | How to improve |
|---|---|---|---|
| <verbatim from prior charge_for_next> | yes / partial / no | what made it easy or hard | concrete suggestion |

Be honest about partial completions and blockers. If an objective was never
attempted, say why (superseded, blocked, deprioritized). These rows feed the
`objectives_eval` field of your catalog entry AND the future
`check-mayor-objectives` skill.

**Additional work log** — list things worked on that were NOT in the
`charge_for_next`. One line each:
- `<what>: <why it was needed or picked up>` (e.g. `"WS-B critical-review
  revision: design docs needed a second pass before mathcity.work dispatch"`)

This reveals scope creep, emergent blockers, and objectives that were too
coarse or too granular.

**Draft new objectives** for the next session — TWO lists:

- `objectives_short` (what Mayor session N+1 should finish in one session):
  list 3–7 concrete, completable items. Write them as action verbs.
  Too large = requires multiple sessions. Too small = trivially done in
  minutes. Sweet spot = a full session's worth each.

- `objectives_long` (multi-session or persistent goals Mayor session N+1 should
  advance but not necessarily finish): list 2–4 strategic objectives.
  These frame the short-term list.

**`check-mayor-objectives` trigger**: once 5 sessions have `objectives_eval`
rows in `session-catalog.json`, run:
```bash
# Check if 5 evaluations exist:
python3 -c "
import json
data = json.load(open('<city-root>/mathcity-mayor/session-catalog.json'))
evals = [s for s in data if s.get('objectives_eval')]
print(f'{len(evals)} eval entries found')
if len(evals) >= 5:
    print('READY: run skill-creator-math to build check-mayor-objectives')
"
```
If ready, dispatch `skill-creator-math` to build `mathcity.check-mayor-objectives`
from the accumulated evaluation corpus. The skill will: read the 5+ eval tables,
classify each objective as well-scoped / too-large / too-small / ambiguous, and
produce a revised objective template for future handoffs. Do NOT build the skill
before 5 evaluations exist.

## 0c. Capture the city's brief/work state in command-readable terms

`city_state` and `charge_for_next` are read by a session that has no memory of
yours. "brief stack looking healthy" is not a handoff; a count the next Mayor
can re-derive is. Take the numbers from the canonical bead store, per rig.

**Use whichever surface this session has.** `mcp__mctl__*` in your tool list →
`mcp__mctl__briefs_list` and `mcp__mctl__work_ready`. Otherwise the CLI block
below. The numbers are identical either way, so the handoff never depends on
which front door you had — and a missing MCP is never a reason to hand off
without counts.

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

"$MCTL" briefs list --status pending --city "$CITY_ROOT" --rig "$RIG" --json
"$MCTL" work ready --city "$CITY_ROOT" --rig "$RIG" --json
```

Record in `city_state`, in this shape, so the next session can verify it in one
command:

```
BRIEFS-PENDING: <n> (<rig>)   WORK-READY: <n> (<rig>)
HOLDS: <migration or kill-switch holds in effect, or "none">
IN-FLIGHT-TRACES: <MCTL-TRACE ids for mutations you started but did not confirm>
```

**`IN-FLIGHT-TRACES` is the load-bearing one.** Every `mctl` mutation this
session performed — a verdict, a deposit, a dispatch — reported an
`MCTL-TRACE` id. If you handed off before confirming one landed, name it here:
the next Mayor runs `"$MCTL" trace show <id>` — or `mcp__mctl__trace_show`, when
that session has the MCP — and sees exactly what was planned versus what was
applied. A half-applied mutation you did not name is invisible.

Record the bare trace ids, never the surface you happened to use to produce
them. Trace ids are core-level and resolve identically from the tool and the
CLI; a handoff that instructs the next Mayor to "run the tool" strands a
session that has no tools.

Two limits to state honestly rather than paper over:

- `--all-rigs` was specified in Slice 2 and is **not implemented**, so these are
  per-rig counts. Name the rigs you checked; do not present one rig's number as
  the city's.
- `gt-*` briefs live in the city-root HQ store, which is not a registered rig
  (`MCTL_CONTEXT_UNKNOWN_RIG`), so they are absent from these counts entirely.

Do not branch on `MBRF021` / `MBRF004` / `MBRF005` when summarising, and do not
report a `malformed` count as damage: it means *closed with no verdict field*.

## 1. Write the handoff bead (chained)

Write a `gt-` handoff bead holding this session's full arc (what was done,
what was verified at source, open threads, warnings for the next Mayor session).
Reference the prior chain (S1 gt-gnh7m → … → S12 gt-9050ks → …) so
`bd show` walks the lineage. The `/handoff-bead` skill does the mechanics.

## 2. Write a run-log shard

Write this session's `S<N>.x` rows to a **new shard file**
`<city-root>/mathcity-tests/run-log/S<N>.md` (where N is your session number).
Do NOT append to the `run-log.md` monolith — it is a frozen 190KB archive;
`mayor-math-prime` reads shards from the directory, not the monolith.

Format: begin with `## S<N> — Mayor session <N> (<date>, written by <agent>)`,
then one `S<N>.x` subsection per topic (triage, infra, math, handoff).
Never rewrite prior sessions' rows.

## 3. Add the session-catalog entry (BOTH files)

Append ONE JSON entry to **both** catalog files in the same close step —
they must never drift (a missing recent-catalog entry trips the next
session's consistency guard):

- `<city-root>/mathcity-mayor/session-catalog.json` — full history
- `<city-root>/mathcity-mayor/session-catalog-recent.json` — keep last 5 entries only

Entry shape:

```json
{
  "mayor_session": <N>,
  "bead": "<your-handoff-bead-id>",
  "date": "<YYYY-MM-DD>",
  "hours_active": "<e.g. ~3h>",
  "compactions": <integer or "unknown">,
  "summary": "<what was done this session>",
  "city_state": "<city state for the next Mayor session>",
  "objectives_eval": [
    {
      "objective": "<verbatim from prior charge_for_next or objectives_short>",
      "completed": "yes | partial | no",
      "remarks": "<what made it easy or hard>",
      "improve": "<concrete suggestion for next time>"
    }
  ],
  "additional_work": [
    "<what: why it was needed>"
  ],
  "objectives_short": [
    "<action-verb objective completable in one session>"
  ],
  "objectives_long": [
    "<multi-session strategic goal>"
  ],
  "charge_for_next": "<one-paragraph synthesis of objectives_short for the next Mayor session>"
}
```

Keep `summary` and `city_state` ≤ ~40 words each. `charge_for_next` is a
prose synthesis of `objectives_short` — write it for a Mayor session that will read
only the PROMPT (no catalog JSON visible directly). The structured fields
(`objectives_eval`, `objectives_short`, `objectives_long`) are for the
`check-mayor-objectives` skill and the evaluation table in the PROMPT.

**Sizing guidance for `objectives_short`:**
- Too large: requires multiple sessions or human decisions not yet made.
- Too small: can be done in <30 min without coordination.
- Sweet spot: a 2–4h focused block that produces a verifiable artifact
  (brief deposited, bead closed, skill committed, formula dispatched).
- If all short-term objectives were completed AND significant additional
  work happened, the objectives were too small — expand for next session.
- If 0–1 objectives were completed, they were too large or the session was
  derailed — split or add blockers-first objectives.

To update `session-catalog-recent.json` (keep last 5):
```bash
python3 -c "
import json, pathlib
p = pathlib.Path('<city-root>/mathcity-mayor/session-catalog-recent.json')
data = json.loads(p.read_text())
data.append({NEW_ENTRY})
data = data[-5:]
p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
"
```

## 4. Update the restart PROMPT

Home: `<city-root>/mathcity-mayor/restart/PROMPT-mayor-restart.txt`.

Update it for the next session: refresh the S<N>→S<N+1> update block, state
of the city, standing rules (only if they changed), the charge, and the
handoff-bead chain. Two acceptable ways:

- **Regenerate (preferred when Jinja is current):** after step 3, render:
  ```bash
  bash <mathcity-pack-root>/skills/mayor-math-prime/scripts/render-prime.sh \
    > <city-root>/mathcity-mayor/restart/PROMPT-mayor-restart.txt
  ```
  This automatically includes the objectives and evaluation table from the
  catalog entry you just wrote in step 3.

- **Curated edit:** edit the file directly. If curating, you MUST include
  these two sections near the top (after STANDING RULES, before CHARGE):

  ```
  ######
  YOUR OBJECTIVES THIS SESSION:
  ######

  SHORT-TERM (finish this session):
  - <item from objectives_short>
  ...

  LONG-TERM (advance but not necessarily finish):
  - <item from objectives_long>
  ...

  ######
  PRIOR SESSION OBJECTIVE EVALUATION (how Q<N> did):
  ######
  | Objective | Completed? | Remarks | Improvement |
  |---|---|---|---|
  | <from objectives_eval> | yes/partial/no | ... | ... |
  ```

  Omitting these sections from the plain-text fallback defeats the
  whole point of the evaluation system.

Do NOT write to `~/Documents/misc/PROMPT-mayor-restart.txt` — that location
is retired (a pointer file remains there).
