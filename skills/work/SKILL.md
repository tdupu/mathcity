---
name: work
description: >
  Feed a bead into the math-city fleet through `mathcity.work`. Use whenever
  the Mayor wants to dispatch work: "mathcity.work", "feed the machine",
  "dispatch this the right way", "put this through the fleet", or "work on
  this bead". The skill invokes the work router, verifies assignment, and
  treats commissioning briefs as the required approval surface for fresh or
  ambiguous work.
---

# mathcity.work

The Mayor-facing dispatch skill. Keep this skill thin: **brief-backed dispatch
is one `mctl work dispatch` call**, which starts the `work-briefed` router,
verifies that the city claimed the bead, and records provenance. Formula
selection and dispatch-plan design belong to the formulas; readiness, claim
verification, and provenance belong to `mctl` — neither belongs to Mayor prompt
lore.

Fresh work with no brief yet still goes through a plain `gc sling` of the
router, because `mctl` models no commission path. The two are path A and path B
below.

## Pre-flight

Verify the fleet can spawn agents and Dolt can resolve beads:

```bash
tmux -L gt ls >/dev/null 2>&1 || {
  echo "I'm sorry, I can't do that — no tmux fleet server (the city can't spawn agents)."
  echo "Run 'gc restart' to give the supervisor a fresh tmux server, then retry."
  exit 1
}
# `gc dolt health` is THREE-valued: 0 healthy, 2 reachable-but-quarantined
# (non-fatal), 1/other unreachable. See template-fragments/dolt-preflight.md.
_dolt_out=$(gc dolt health 2>&1); _dolt_rc=$?
case "$_dolt_rc" in
  0) ;;
  2) ;;   # reachable; auto-GC blocked by a standing compaction quarantine.
          # NON-FATAL and NOT this skill's business: bd resolves beads normally.
          # Proceed SILENTLY — the reporting skills surface it (Variant B).
  *) echo "I'm sorry, I can't do that — Dolt is unreachable (bd cannot resolve beads)."
     echo "Run 'gc dolt status' / 'gc dolt start' and retry."
     exit 1 ;;
esac
```

## Dispatch Model

`mathcity.work` has two modes:

1. **Continue known work** — the bead already carries a clear work graph, or it
   is a bounded task whose briefed execution path is obvious. The router may
   continue directly through the appropriate briefed formula.
2. **Commission fresh work** — the request is ambiguous, design-shaped,
   duplicate-prone, or needs formula selection. The router sends it to
   `commission-work-briefed`, which files a commission brief showing the
   objective, existing work, proposed graph, formulas, test gates, brief gates,
   and approve/revise/reject/defer continuation. Actual work dispatch happens
   only after that brief is approved. Approval may be automatic for no-brainers,
   but it still flows through the brief decision machinery.

Anything accepted through `mathcity.work` must end in a commission brief, a
result brief, or a route to another graph guaranteed to produce a brief.

## Formula Catalog

Do not maintain a formula-routing table here. The live formula catalog changes.
The `work-briefed` router and `commission-work-briefed` planner enumerate the
catalog at runtime:

```bash
gc formula list 2>/dev/null | sort
```

At this surface, only verify that `work-briefed` is available before slinging.

## The mctl entry point

Brief-backed dispatch is canonical state: readiness, the source link, the
approving verdict, the claim, and `dispatch-provenance.v1` all live behind
`mctl`. Resolve the shim once (see `template-fragments/mctl-entry-point.md`):

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

RIG=<rig owning the bead>   # he-* -> hecke, gsp-* -> gascity-packs, mc-* -> mathcity, ...
```

**`gt-*` beads are addressed via `--rig hq`.** The city-root HQ store is served by
the `hq` rig — the resolver synthesizes it from the city root and does not declare
it in `city.toml`, so it looks absent there but resolves clean (verified
2026-08-27). Use `--rig hq` to read/adjudicate a `gt-*` bead; DISPATCH still uses
the commission path below, run from the city root, because gt HQ has no worker
fleet (that is a fleet boundary, not a rig-addressing one). (Corrected 2026-08-27:
prior text said `gt-*` beads were "out of reach / --rig gt fails" — `gt` is not a
rig, but `hq` is.)

**Cross-rig views do not exist yet.** `--all-rigs` was specified in Slice 2 and
is not implemented. Call one rig at a time; do not loop over rigs here.

## Which path — brief-backed or commission?

```bash
"$MCTL" work ready --city "$CITY_ROOT" --rig "$RIG" --json
```

`work ready` lists brief-backed work that is genuinely dispatchable: it excludes
blocked, non-approving, already-dispatched, and invalid-provenance items. If the
bead you were asked to work on appears there (via its approved brief), take path
A. If it does not, ask `work status` why:

```bash
"$MCTL" work status "$BRIEF_BEAD" --city "$CITY_ROOT" --rig "$RIG" --json
```

`work status` returns `readiness` plus the exact `blockers`. Read them before
deciding anything — the answer is usually one of:

| blocker | meaning |
| --- | --- |
| `MWRK010` | the brief has no approving verdict — it has not been adjudicated yet |
| `MWRK011` | the brief has no source-bead dependency, so there is nothing to dispatch |
| `MWRK001` | the source bead already has an active assignee |
| `MWRK002` | an open child workflow already exists for this source |
| `MWRK_ALREADY_DISPATCHED` | provenance exists; this is the duplicate-dispatch gate |
| `MWRK_BRIEF_NOT_FOUND` | not a brief bead — this is fresh work, take path B |

**`MBRF004` refuses nothing.** Corrected 2026-08-27 — this passage previously
said it was an `ERROR` that blocked mutation on "146 of 185 live briefs", and
that was stale by #137. `mctl_core/briefs.py:1652` emits it at `Severity.WARN`,
and `_blocking_diagnostic` (`briefs.py:2124`) selects only `ERROR`/`FATAL`, so
`_blocking_preconditions` never carries it. Measured 2026-08-27: 149 distinct
brief beads city-wide raise `MBRF004`; 0 are blocked by it.

Report it with the diagnostic verbatim. **Do not branch on `MBRF004`,
`MBRF005`, or `MBRF021`** — see `template-fragments/mctl-entry-point.md`. That
includes not branching on it to *exclude*: a session that filters `MBRF004`
briefs out of the queue empties the queue and wrongly reports nothing to do.

## Path A — brief-backed dispatch (`mctl work dispatch`)

```bash
# Preview first: the effect plan names the exact sling it would run.
"$MCTL" work dispatch "$BRIEF_BEAD" --city "$CITY_ROOT" --rig "$RIG" \
  --dry-run --json

out=$(MCTL_ENABLE_LIVE_DISPATCH=1 "$MCTL" work dispatch "$BRIEF_BEAD" \
        --city "$CITY_ROOT" --rig "$RIG" --json); rc=$?
TRACE_ID=$(printf '%s' "$out" \
  | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("trace_id",""))
except Exception: print("")')
echo "MCTL-TRACE: $TRACE_ID"
```

One command now does what this skill used to spread across three prose sections
that an agent could each get half-right:

- **the sling** — `work-briefed` through `<rig>/gc.run-operator`, with
  `source_bead`, `brief_slug`, and `routing_path` filled from canonical state
  instead of retyped;
- **the claim verification** — the bead is re-read after the sling, and
  `MWRK003` fires when the sling exits zero without the bead actually being
  claimed. This replaces `sleep 5; bd show | grep -i assignee` and the
  "if it is still empty after 30-60 seconds" judgement call;
- **the provenance event** — `dispatch-provenance.v1` is written *only after*
  that verified claim. Writing it earlier records a handoff that never happened
  and then blocks every retry with `MWRK_ALREADY_DISPATCHED`, which is exactly
  what hand-authored provenance TOML used to do.

**`MCTL_ENABLE_LIVE_DISPATCH=1` is required and is exported for this one
command only.** Unarmed, `work dispatch` returns the dry-run payload and slings
nothing — deliberately, so a fixture or a stray invocation cannot dispatch. Do
not export it for the session.

`MCTL_CONTROL_PLANE_NOT_ACTIVE` means the supervisor is not confirmed running,
so a sling would have nowhere to route. `gc stop` leaves Dolt up, so the
pre-flight above can pass while this still refuses. Run `gc start`; do not fall
back to a raw `gc sling`.

Afterwards, the provenance record is readable:

```bash
"$MCTL" work provenance "$BRIEF_BEAD" --city "$CITY_ROOT" --rig "$RIG" --json
```

> **Known gap — `artifact_root` is NOT scoped per bead on this path.**
> `mctl_core/work.py::_formula_invocation` passes
> `artifact_root=<rig-root>/.beads/briefs`, a **shared rig-level** root, while
> `formulas/work-briefed.toml` documents the var as *"For builds, scope per bead
> (for example `<rig-root>/.gc-builds/<bead>`)"* and passes it straight through
> to `build-basic-briefed` on the FULL_CONTINUE route. Two concurrent
> FULL_CONTINUE dispatches in one rig therefore share a stage-artifact root —
> the gsp-1bmxuz hazard. **Do not work around it by re-slinging by hand**; check
> `work provenance` and the effect plan's `formula_invocation.command` before
> arming a second concurrent dispatch in the same rig, and prefer to serialize
> them. Fixing the core is a `mctl_core` change, not a skill change.


## Path B — commission fresh work (no brief yet)

`mctl work dispatch` addresses an **approved brief**. Fresh, ambiguous, or
design-shaped work has no brief yet, and `mctl` models no commission path — so
this stays a `gc sling` of the router, which files the commission brief. Once
that brief is approved, dispatch goes back through path A.

Run from the source bead's rig directory so `bd` resolves the bead correctly.

**Two roots, and they are not interchangeable.** `artifact_root` is the
build/stage root and is bead-scoped, because two concurrent dispatches in one
rig otherwise share a stage root (gsp-1bmxuz). `brief_root` is the brief DEPOSIT
root and is the rig's one shared brief tree, because that is the only pile any
adjudication surface reads. Passing one value for both is mc-4ovmy: it stranded
18 complete, gate-passing briefs under `.gc-builds/<bead>/.pile/`, where nothing
looks — a brief no adjudicator can reach is, operationally, not filed.

`brief_root` is derived from the **city registry**, never from `$PWD`: the
runner's cwd is an agent work dir, which is never a rig root and never a brief
root. It is also rig-scoped, never city-scoped — mctl resolves the pile it reads
as `<rig-root>/.beads/briefs/.pile`, and the city-root tree is the separate `hq`
store, not a shared one.

```bash
SOURCE_BEAD=<bead-id>
BRIEF_SLUG="$SOURCE_BEAD-work"
ARTIFACT_ROOT=".gc-builds/$SOURCE_BEAD"

RIG_PATH="$(gc rig list --json | jq -r --arg id "$SOURCE_BEAD" '
  [(.rigs // [])[] | select(.prefix as $p | $id | startswith($p + "-"))]
  | sort_by(.prefix | length) | last // empty
  | .path // empty')"
[ -n "$RIG_PATH" ] || {
  echo "I'm sorry, I can't do that — no registered rig prefix matches $SOURCE_BEAD, so the brief deposit root cannot be resolved."
  exit 1
}
BRIEF_ROOT="$RIG_PATH/.beads/briefs"

gc formula list 2>/dev/null | awk '{print $1}' | grep -qx 'work-briefed' || {
  echo "I'm sorry, I can't do that — work-briefed is not in the live formula catalog."
  exit 1
}

gc sling <owning-rig>/gc.run-operator "$SOURCE_BEAD" --on work-briefed \
  --var source_bead="$SOURCE_BEAD" \
  --var brief_slug="$BRIEF_SLUG" \
  --var artifact_root="$ARTIFACT_ROOT" \
  --var brief_root="$BRIEF_ROOT" \
  --var child_run_target=auto \
  --var routing_path="mathcity.work"
```

Confirm the deposit root is the one the reader uses — the check that would have
caught mc-4ovmy, and the only one that could have. Ask the **MCP** surface, via
the `briefs_list` tool, and read `artifact_trust.resolved_pile`:

    mcp__mctl__briefs_list  rig=<owning-rig>   ->  .artifact_trust.resolved_pile

    must equal "$BRIEF_ROOT/.pile"

Measured 2026-08-28 for `rig=mathcity`: `resolved_brief_root` is
`<city-root>/mathcity/.beads/briefs` and `resolved_pile` is
`<city-root>/mathcity/.beads/briefs/.pile` — rig-relative, per
`assets/brief-pipeline/paths.toml`, never the city root.

**Do not reach for the CLI here.** `mctl briefs list --json` emits only
`briefs`, `diagnostics` and `trace_id`; `artifact_trust` is attached by the MCP
server layer and by nothing else, so `jq -r '.artifact_trust.resolved_pile'`
against the CLI prints `null` on a correct city and on a broken one alike. A
check that cannot fail must not be written as a check that passed (P6.2). If
only a shell is available, the honest substitute names its own weakness — it
re-derives the root instead of reading the resolver:

```bash
# WEAKER: re-derivation, not the resolver's own answer.
RIG_ROOT="$(mctl context --city "$CITY_ROOT" --rig "$RIG" --json | jq -r .rig_root)"
test "$BRIEF_ROOT/.pile" = "$RIG_ROOT/.beads/briefs/.pile"
```

If you have extra context that must not be lost in translation, pass it through:

```bash
--var context="<paths, issue URLs, or user notes>"
```

### Verify the commission sling landed

A sling you did not verify may have stranded. The check is a typed read, not a
grep:

```bash
sleep 60
"$MCTL" work claim "$SOURCE_BEAD" --window-seconds 60 \
  --city "$CITY_ROOT" --rig "$RIG" --json
```

`classification_hint` answers the question directly: `healthy` means the bead is
held, `immediate_strand` means it is not. A bead id this rig's store cannot
resolve exits 1 with `MWRK_BEAD_NOT_FOUND` rather than printing nothing — the
old `bd show … | grep -i assignee` could not tell an unclaimed bead from a
missing one, from a bead in another store, from a field bd renamed, because it
was matching lines in a human-readable rendering. Two bugs came out of that
class of matching.

On `immediate_strand`, do not assume the fleet is healthy — escalate, or run the
appropriate `mathcity.check-work` / `mathcity.check-molecules` skill.

### Path-B dispatch provenance event (required — the lost-bead filter reads it)

Path A gets `dispatch-provenance.v1` from `mctl work dispatch`, behind a verified
claim. Path B has its own mctl route, and it is not optional:
`assets/scripts/lost-bead-filter.py` and the rollup formulas key their
classification on this event, and a commission sling with no provenance event is
invisible to them.

Write it before escalating:

```bash
"$MCTL" work dispatch-event "$SOURCE_BEAD" \
  --dispatch-command "gc sling $RIG/gc.run-operator $SOURCE_BEAD --on work-briefed" \
  --formula work-briefed --window-seconds 60 \
  --city "$CITY_ROOT" --rig "$RIG" --json
```

One command, because the event bead and its edge to the source bead are only
meaningful together — an event created and left unattached is invisible to the
lost-bead filter in exactly the way an unwritten one is. It creates the
`type=event` bead carrying the `dispatch-provenance.v1` payload, attaches it with
`bd dep relate`, and then **proves from the store that the edge is there**.

Three things it does that the hand-written pair did not:

- **The classification is derived, not retyped.** `verified_assignee`,
  `assignee_state`, `classification_hint` and `fingerprint` come from the same
  canonical claim read `work claim` performs. Typed out by hand beside a grep,
  they could — and did — say `healthy` about a bead nobody held.
- **A bead this rig cannot resolve is refused before anything is written.**
  `MWRK_BEAD_NOT_FOUND`, with no orphan event bead left behind. This is the
  cross-store guard: `bd dep add <local-id> <foreign-id>` exits 0 and leaves a
  row `bd show` counts and hides, so the edge has to be refused rather than
  attempted.
- **The edge is verified after the write.** `MCTL_BEAD_RELATION_DANGLING` if it
  names a bead this store cannot resolve, `MCTL_BEAD_RELATION_UNVERIFIED` if the
  store records no edge at all. A relate that did not land is a FATAL abort with
  an `aborted` trace row, not a success message.

Preview first with `--dry-run` if you want to see the payload before it lands.

**Do not write one on path A.** There, `mctl work dispatch` has already written
the record after re-reading the bead; a second one asserts a claim nobody checked
and double-counts the dispatch.

### Direct `build-basic-briefed` dispatch (outside both paths)

When a bead is dispatched straight to `build-basic-briefed` rather than through
the router — a convoy build, or an approve continuation that names it — scope
`artifact_root` per bead. Never omit it and never pass the bare rig root, or
concurrent runs on the same rig silently overwrite each other's stage artifacts
(gsp-1bmxuz):

```
gc sling <rig>/gc.run-operator <bead> --on build-basic-briefed \
  --var interaction_mode=autonomous --var review_mode=agent \
  --var drain_policy=separate --var push=false --var open_pr=false \
  --var artifact_root=<rig-root>/.gc-builds/<bead>
```

## Commission Briefs

For fresh work, seeing a commission brief in `.pile/` is success for this
dispatch stage. The implementation has not started yet; the graph waits for
approval. The commission brief should show:

- original request and interpreted objective;
- existing work folded in or marked superseded;
- titled plaintext dispatch graph;
- formulas selected from the live catalog;
- test and brief gates;
- machine-readable `commission-dispatch.v1` continuation.

On APPROVE, the decision-dispatch path executes the continuation. On REVISE,
REJECT, or DEFER, the graph does not run.

## Slow Build Is Not Strand

Molecule roots stay open until terminal steps finish, and result briefs land
late. An open build root is not a strand by itself. Check step progress,
assignee state, and brief-pipeline evidence before declaring work lost.

Use `mathcity.check-work`, `mathcity.check-molecules`, or
`mathcity-dev.city-status` for broader health checks.
