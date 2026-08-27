---
name: adjudicate-brief
description: Use whenever a STANDALONE decision needs to be recorded persistently in a bd-managed rig — human adjudications, architecture choices, policy locks, gate-criterion additions. EXCEPTION — brief verdicts: under the one-bead model (brief-system POLICY.md B2.2, 2026-07-12) a brief bead IS the decision bead; its verdict is recorded ON the brief bead and the bead is closed — do NOT create a second decision bead for a brief. Enforces the `bd create -t decision` canonical primitive per the bd-decision-canonical architecture principle (gascity triage 2026-06-26, LD #10 + AP2). Refuses to write decisions to non-`bd decision` stores (no markdown files, no custom jsonl writes, no `bd remember`-with-decision-content). Trigger phrases include "record a decision", "log this decision", "file the verdict", "this needs to be a decision-record", "preserve this for posterity", or any moment when an agent or human surfaces a verdict / rationale / chosen-alternative that should survive across sessions and be queryable by future work.
---

> **Canonical copy**: `mathcity.adjudicate-brief` in this mathcity pack. Materialized agent-skills copies are fallback only.

# adjudicate-brief

## FORK WRAPPER — calling agent's only job

**adjudicate-brief is a fork-composition.** The calling agent MUST immediately fork a subagent to do all recording/dispatch work, then report one line and stop. The calling agent executes NO `bd` or `mctl` commands itself — it only launches the fork.

### Step 1 — collect from invocation args + context

- `BRIEF_BEAD` — the brief's bead ID (from frontmatter `brief_bead:` or brief file, e.g. `he-dvwa`)
- `ARTIFACT` — the `artifact:` frontmatter field (e.g. `hecke#233`, `he-p4x5`)
- `VERDICT` — one of: `approve` / `reject` / `defer` / `revise`
- `RATIONALE` — the human adjudicator's stated reason (from invocation args, one line)
- `DEFER_UNTIL` — date string if verdict=defer (e.g. `2026-08-05`), else omit
- `RIG_DIR` — local rig directory (e.g. `<repos-root>/hecke` for `he-*` beads)

### Step 2 — launch fork

```
Agent(
  subagent_type: "fork",
  name: "adj-<BRIEF_BEAD>-<VERDICT>",
  description: "Adjudicate <BRIEF_BEAD> → <VERDICT>",
  prompt: "You are a fork executing adjudicate-brief. Record the human adjudicator's verdict on brief bead <BRIEF_BEAD> (artifact: <ARTIFACT>): verdict=<VERDICT>, rationale='<RATIONALE>'[, defer_until=<DEFER_UNTIL>], rig=<RIG_DIR>. Execute the FORK BODY section of the adjudicate-brief skill now in your inherited context. Route the verdict through bin/mctl (briefs adjudicate / briefs defer) — no raw bd writes. If verdict=approve, dispatch with mctl work dispatch. Report one summary line INCLUDING every MCTL-TRACE id when done."
)
```

### Step 3 — report and stop

Emit exactly: `"Fork launched: <BRIEF_BEAD> → <VERDICT>. Session free."`

Do NOT wait for the fork. Do NOT run any bd commands. Stop here.

---

## FORK BODY — recording and dispatch

*You are a fork. Execute the following:*

### 0. Resolve the mctl entry point

Brief verdicts are canonical bead state. `mctl` owns the write — the bead
update **and** every redundant cache artifact that has to move with it
(`decisions/<brief>.toml`, `stack/.index.jsonl`). See
`template-fragments/mctl-entry-point.md`.

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

# Bead prefix -> rig NAME registered in city.toml.
case "$BRIEF_BEAD" in
  he-*)  RIG=hecke ;;   gsp-*) RIG=gascity-packs ;;  gs-*) RIG=gascity ;;
  as-*)  RIG=agent_skills ;;  mc-*) RIG=mathcity ;;  lm-*) RIG=lmfdb ;;
  tgi-*) RIG=tdupu_github_io ;; ho-*) RIG=homog ;;   ja-*) RIG=jacobi ;;
  dv-*)  RIG=differential_valuations ;;
  mca-*) RIG=magma_clifford_algebras ;; mda-*) RIG=magma_diff_alg ;;
  *)     RIG="" ;;
esac
```

**`gt-*` beads have no route through `mctl`.** The city-root HQ store is not a
registered rig in `city.toml`, so `--rig gt` fails with
`MCTL_CONTEXT_UNKNOWN_RIG`. For an unmapped prefix, stop and hand the verdict
to a human rather than improvising a second write path — recording a `gt-*`
verdict by hand is exactly the redundant write this skill no longer does.

### 1. Preview the verdict before applying it

`--dry-run` renders the full `EffectPlan` — the bead update and every cache
write — without touching anything. Run it first on any verdict you are not
certain of:

```bash
"$MCTL" briefs adjudicate "$BRIEF_BEAD" --verdict "$VERDICT" \
  --reason "$RATIONALE" --city "$CITY_ROOT" --rig "$RIG" --dry-run --json
```

### 2. Record the verdict

`approve` / `reject` / `revise` close the brief bead with the verdict recorded
on it (one-bead model, B2.2). `defer` leaves it open with a defer window.

```bash
if [ "$VERDICT" = "defer" ]; then
  out=$("$MCTL" briefs defer "$BRIEF_BEAD" \
          --reason "$RATIONALE" --until "$DEFER_UNTIL" \
          --city "$CITY_ROOT" --rig "$RIG" --json); rc=$?
else
  out=$("$MCTL" briefs adjudicate "$BRIEF_BEAD" \
          --verdict "$VERDICT" --reason "$RATIONALE" \
          --city "$CITY_ROOT" --rig "$RIG" --json); rc=$?
fi
TRACE_ID=$(printf '%s' "$out" \
  | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("trace_id",""))
except Exception: print("")')
echo "MCTL-TRACE: $TRACE_ID"
```

Add `--option <LABEL>` when the brief offers more than one option; without it
a multi-option brief fails closed with `MOPT001`, which is the gate working.

**A non-zero exit is a refusal, not a crash.** `mctl` fails closed when the
brief's invariants do not hold, and it prints the blocking diagnostic. Relay
the diagnostic verbatim and stop.

**What blocks is exactly `ERROR` and `FATAL`.** `effects.py::_blocking_preconditions`
filters on `{Severity.ERROR, Severity.FATAL}` and nothing else, so a `WARN` or an
`INFO` never blocks a mutation — it is reported alongside the applied plan. Read the
severity in the diagnostic, never the code. In particular:

> **`MBRF004` ("Brief bead has no source dependency", B2.1) fires at `WARN`, and
> therefore does NOT block adjudication.** [measured 2026-08-27: `assets/mctl/diagnostics.toml`
> `[MBRF004] severity = "WARN"`; `mctl_core/briefs.py` emits it as `Severity.WARN`;
> a live `mctl briefs doctor --brief <id> --json` returns `"severity": "WARN"`; and a
> live `mctl briefs adjudicate --dry-run` on an `MBRF004`-carrying brief returns
> `effect_plan.preconditions == []`.] It is still worth fixing — the remedy is a real
> source link (`bd dep add <brief> <source-bead> --type related`), decided by a human —
> but it is an advisory, not a gate.
>
> **CORRECTION, 2026-08-27.** This paragraph previously read *"`MBRF004` … is an `ERROR`,
> and `effects.py::_blocking_preconditions` refuses any mutation carrying one … it
> currently fires on 146 of 185 live briefs, including 88 that are `pending` and
> otherwise healthy — so most of the live queue will refuse adjudication."* **That was
> true before tdupu/mathcity#137, which downgraded `MBRF004` to `WARN` and closed
> 2026-08-22; the text was never updated.** The counts (146 / 185 / 88) come from the
> 2026-08-19 audits (`subdomains/dev/docs/MBRF004-TRIAGE-2026-08-19.md`,
> `MALFORMED-BRIEF-TRIAGE-2026-08-19.md`) and describe the pre-#137 world. **Do not use
> `MBRF004` as a filter.** A session that reads it as one empties its own queue and
> concludes — wrongly — that there is nothing to adjudicate.
>
> Codes that genuinely do block today include `MOPT001` (multi-option brief adjudicated
> without `--option`, `ERROR`) and `MBRF034` (`FATAL`). If a refusal cites a code, check
> its severity in `assets/mctl/diagnostics.toml` before believing this file about it.
>
> Do **not** branch on `MBRF004`, `MBRF005`, or `MBRF021` — see
> `template-fragments/mctl-entry-point.md`.

### 2b. LEGACY-DECISIONS-TRACK sync — `mctl` does this now; do nothing here

**Step 2 is the whole write.** `mctl briefs adjudicate|defer` updates the bead,
`decisions/<id>.toml`, `stack/.index.jsonl`, the brief document's own
frontmatter, **and** the legacy `decisions-track/manifest.jsonl` row when the
brief has one. There is no hand-written cache sync left in this skill, and no
declared exemption. Run step 2 and go to step 3.

The manifest row is written only for a brief that **already has** one — the
decision record is split by track:

| track | where the decision is recorded |
| --- | --- |
| stack-track brief | `.beads/briefs/decisions/<bead_id>.toml` |
| legacy decisions-track brief | a row in `.beads/decisions-track/manifest.jsonl` |

A stack-track brief has no manifest row and is never given one; `mctl` resolves
the join from the migration's own record (`legacy_n` / `legacy_source` on the
stack index row), so absence is silent rather than an error. A brief whose index
row points at a manifest row that is missing or duplicated degrades to a
per-brief `MCTL_DECISIONS_TRACK_ROW_UNWRITABLE` **WARN**; the bead, the decision
TOML, the index row and the frontmatter still land.

The invariant is unchanged and is now enforced by one writer instead of two:
after a verdict, the brief document's `status:` and its manifest `status` agree.
Never `ready`/`ready-for-adjudication` on one and `adjudicated` on the other.

#### Superseded — the hand-written sync this step used to perform

**The reasoning below was correct about the divergence and wrong about who
should fix it. Kept for the record, struck rather than deleted.**

The measured problem is real and is why the write exists at all: on 2026-08-04,
17 briefs read `adjudicated` in the manifest while their files still read
`status: ready-for-adjudication`, so `present-briefs` re-presented decided
decisions.

What the argument missed is that **the skill is not the only caller.** When the
owner adjudicates from the dashboard, `mctl` runs and this skill does not — so a
write placed *after* `mctl` runs on exactly one of the four routes into the same
act, and the other three leave the row stale. A second writer behind the
canonical writer does not close the gap; it relocates it. Both writes are now in
`mctl_core/effects.py::plan_adjudication`, which every caller goes through.

> ~~**This is the one cache write this skill still performs by hand, and it is a
> declared exemption rather than an oversight.** Run it only when this verdict
> resolves a `decisions-to-briefs` file-brief — a `<NN>-<slug>-brief.md` under
> `<city-root>/.beads/decisions-track/` with a `manifest.jsonl` row. If the brief
> has no decisions-track file, **skip 2b entirely**; the modern lane is finished
> at step 2.~~
>
> ~~Why it survives the Slice 7 refactor:~~
>
> - ~~`mctl briefs adjudicate|defer` writes the bead, `decisions/<id>.toml`, and
>   `stack/.index.jsonl`. It does **not** touch the legacy decisions-track
>   inventory, and it should not: `#38` is actively changing how that tree's
>   non-terminal statuses are classified, and the plan holds bulk live migration
>   until proof 5 is green and authorized.~~
> - ~~Dropping the sync here does not hand the job to `mctl`; it hands it to
>   nobody.~~
>
> ~~So: `mctl` is the canonical writer, this runs **after** it, and it touches
> only the decisions-track tree — never the pile, never `stack/.index.jsonl`.~~
>
> ~~`BRIEF_FILE` = the decisions-track path this verdict resolves (the clerk /
> present-briefs passes it; empty means skip).~~
>
> ~~(1) rewrote the brief file's `status:` line with an in-place `sed`, and (2)
> re-serialised every row of `manifest.jsonl` to set `status`, `verdict`,
> `verdict_note` and `adjudicated_at` on the row whose `n` matched the brief
> file's `NN-` prefix. `mctl` now performs both — and rewrites only the target
> row, leaving every other line byte-identical, which the re-serialising loop
> did not.~~

**Do not restore a hand-written sync here.** `#38` still owns the legacy tree
and bulk migration is still held; that is a reason for `mctl` to write one row
in place when a verdict lands, not a reason for a second writer to exist.

### 3. If verdict = approve → dispatch through `mctl work dispatch`

```bash
if [ "$VERDICT" = "approve" ]; then
  "$MCTL" work status "$BRIEF_BEAD" --city "$CITY_ROOT" --rig "$RIG" --json
  out=$(MCTL_ENABLE_LIVE_DISPATCH=1 "$MCTL" work dispatch "$BRIEF_BEAD" \
          --city "$CITY_ROOT" --rig "$RIG" --json); rc=$?
  DISPATCH_TRACE=$(printf '%s' "$out" \
    | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("trace_id",""))
except Exception: print("")')
  echo "MCTL-TRACE: $DISPATCH_TRACE"
fi
```

`mctl work dispatch` does mechanically what this skill used to ask the fork to
do by hand, and it does the parts the prose kept getting wrong:

- it slings through the `work-briefed` **router**, which selects the formula
  from the live catalog, instead of hardcoding `build-basic-briefed`;
- it fills `source_bead`, `brief_slug`, and `routing_path` from canonical state
  rather than from retyped prose;
- it re-reads the bead after the sling and raises `MWRK003` if the sling exited
  zero **without** the bead actually being claimed — replacing the eyeballed
  `bd show | grep -i assignee` check;
- it writes `dispatch-provenance.v1` only after that verified handoff, so a
  phantom provenance record cannot block every later retry.

**`MCTL_ENABLE_LIVE_DISPATCH=1` is required.** Unarmed, `work dispatch` returns
the dry-run payload and slings nothing. It is exported for this one command
only, deliberately — arming it session-wide would arm every later dispatch too.

`MCTL_CONTROL_PLANE_NOT_ACTIVE` means the supervisor is not confirmed running,
so a sling would have nowhere to route: run `gc start` and retry. Do not
work around it with a raw `gc sling`.

> **Known gap — `mctl` does not scope `artifact_root` per bead.**
> `mctl_core/work.py::_formula_invocation` passes
> `artifact_root=<rig-root>/.beads/briefs`, a shared rig-level root, and
> `work-briefed` hands it through to `build-basic-briefed` on the FULL_CONTINUE
> route. Two concurrent FULL_CONTINUE dispatches in one rig therefore share a
> stage-artifact root (gsp-1bmxuz). Serialize approvals on one rig rather than
> re-slinging by hand. See `skills/work/SKILL.md` for the full note.

### Direct `build-basic-briefed` dispatch (when the continuation names it)

A commission brief may carry a `commission-dispatch.v1` continuation that names
`build-basic-briefed` directly. There, scope `artifact_root` per bead — never
omit it and never pass the bare rig root (gsp-1bmxuz):

```bash
gc sling hecke/gc.run-operator <ARTIFACT> --on build-basic-briefed \
  --var interaction_mode=autonomous --var review_mode=agent \
  --var drain_policy=separate --var push=false --var open_pr=false \
  --var artifact_root=<city-root>/hecke/.gc-builds/<ARTIFACT>
```

### 4. Report

Emit one line, and keep the trace ids — they are how this fork's writes are
audited afterwards with `mctl trace show <id>`:

`"Adjudicated <BRIEF_BEAD>: <VERDICT>. [closed/deferred] [<ARTIFACT> dispatched if approve] MCTL-TRACE: <verdict-trace>[, <dispatch-trace>]"`

### What this fork no longer does, and why

- **No `bd comments add` / `bd close` / `bd defer`.** `mctl briefs
  adjudicate|defer` performs the canonical bead update through a checked
  `EffectPlan` with an `if_status` guard, so a concurrent writer loses the race
  loudly (`MCTL_BEAD_UPDATE_RACE_LOST`) instead of silently overwriting.
- **No cache writes of any kind.** `mctl_core/effects.py::_cache_updates` moves
  `decisions/<brief>.toml`, `stack/.index.jsonl`, the brief document's own
  frontmatter, and the legacy `decisions-track/manifest.jsonl` row with the
  bead, so the skill rewrites none of them. The step 2b exemption is retired —
  see the struck block there.
- **No hand-written `dispatch-provenance.v1` TOML on the approve path.**
  `mctl work dispatch` writes it, and only after the claim is verified.

---

## For STANDALONE decisions (not brief verdicts)

When to use: a verdict that closes deliberation with recorded rationale — architecture choices, policy locks, gate-criterion additions, push/kill-switch authorizations.

**NOT for brief verdicts** (those go through the fork body above). NOT for ephemeral observations, cross-session facts (`bd remember`), or work items (`bd create --type task`).

**This half stays on `bd create -t decision`, deliberately.** `mctl briefs
create` is the *brief-pipeline* creator: alongside the decision bead it writes a
`.pile/<id>.md` artifact and a `decisions/<id>.toml` cache row, and it refuses
when the rig has no brief root (`MBRF035`). A standalone decision — a policy
lock, a kill-switch authorization — is not a brief and has no pipeline artifacts,
so routing it through `mctl briefs create` would manufacture pile entries for
decisions that will never be presented, shuffled, or adjudicated. The canonical
store is the same either way (`BeadStoreAdapter`, `bd type=decision`); only the
`BriefCacheAdapter` artifacts differ, and here there should be none.

### Canonical command

```bash
bd create "<title>" --type decision \
  --description "$(cat <<'EOF'
## Decision

<one-sentence summary of what was decided>

## Rationale

<why this was chosen — the substantive reasoning>

## Alternatives Considered

- **<alt 1>**: <why rejected>
- **<alt 2>**: <why rejected>

## Affects

- <bead IDs, files, or area descriptions>

EOF
)"
```

After creation, link affected beads:

```bash
bd dep add <decision-id> <affected-bead-id> --type related
```

### Supersede pattern

```bash
NEW_ID=$(bd create "<title>" --type decision --description "..." --silent)
bd dep add $NEW_ID <old-decision-id> --type related
bd comments add <old-decision-id> "Superseded by $NEW_ID: <brief reason>"
bd close <old-decision-id> --reason "Superseded by $NEW_ID"
```

### Refuse-and-explain

If asked to record a decision via non-canonical path:

> "Per the bd-decision-canonical architecture principle (gascity triage 2026-06-26), all decisions go through `bd create -t decision`. Let me reformulate: `bd create '<title>' --type decision --description ...`"

---

## What this skill does NOT do

- ❌ Write decisions to a markdown file
- ❌ Write to `<city-root>/<rig>/.beads/decisions.jsonl` directly (legacy — do not extend)
- ❌ Use `bd remember "<decision text>"` (that's for facts, not verdicts)
- ❌ Create a "decision" bead with `--type task` + title-marker (use `--type decision`)
- ❌ Skip the Decision / Rationale / Alternatives / Affects template
- ❌ Record a brief verdict with raw `bd close` / `bd defer` / `bd comments add`
      (brief verdicts go through `mctl briefs adjudicate|defer`)
- ❌ Rewrite `stack/.index.jsonl`, `decisions/<brief>.toml`, a brief's
      frontmatter, or the legacy `decisions-track/manifest.jsonl`
      (`mctl_core/effects.py` owns every cache write that moves with a verdict)
- ❌ Hand-sling `build-basic-briefed` on approve (use `mctl work dispatch`)

## Why this skill exists

Prior to grill-2 (2026-06-26), decisions were scattered across 3 `.jsonl` files + bd memories + title-marker beads + markdown files. The session locked `bd decision` as canonical (LD #10 + AP2). The fork-wrapper pattern (added 2026-07-22) keeps the calling session's context free during recording + dispatch — heavy write + sling work runs in a background fork.

Slice 7 (2026-08-19) moved the fork body onto `mctl`. The verdict write, the
cache artifacts that move with it, the dispatch, and the claim verification were
four separate hand-rolled steps that could each half-succeed; they are now one
checked `EffectPlan` per operation, each stamped with a trace id.

## What stays in the legacy stores (do NOT migrate)

`<city-root>/hecke/.beads/decisions.jsonl` (29 records), `<city-root>/hecke/.beads/briefs/decisions.jsonl` (301 records), `<city-root>/.gc/agents/mayor/decisions.jsonl` (23 records) — LEGACY, preserved via off-machine backup. Do not extend. Opportunistic backfill only when a historical decision surfaces in work.
