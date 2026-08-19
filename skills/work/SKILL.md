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

The Mayor-facing dispatch skill. Keep this skill thin: it starts the
`work-briefed` router and verifies that the city claimed the bead. Formula
selection and dispatch-plan design belong to the formulas, not to Mayor prompt
lore.

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

## Sling

Run from the source bead's rig directory so `bd` resolves the bead correctly.
Use a bead-scoped artifact root; never use a shared bare rig root.
For build paths, the required shape is
`artifact_root=<rig-root>/.gc-builds/<bead>`; when running from the rig root,
`.gc-builds/$SOURCE_BEAD` is that same per-bead path.

```bash
SOURCE_BEAD=<bead-id>
BRIEF_SLUG="$SOURCE_BEAD-work"
ARTIFACT_ROOT=".gc-builds/$SOURCE_BEAD"

gc formula list 2>/dev/null | awk '{print $1}' | grep -qx 'work-briefed' || {
  echo "I'm sorry, I can't do that — work-briefed is not in the live formula catalog."
  exit 1
}

gc sling <owning-rig>/gc.run-operator "$SOURCE_BEAD" --on work-briefed \
  --var source_bead="$SOURCE_BEAD" \
  --var brief_slug="$BRIEF_SLUG" \
  --var artifact_root="$ARTIFACT_ROOT" \
  --var child_run_target=auto \
  --var routing_path="mathcity.work"
```

If you have extra context that must not be lost in translation, pass it through:

```bash
--var context="<paths, issue URLs, or user notes>"
```

## Verify Assignment

A sling you did not verify may have stranded. Immediately confirm the worker
claimed the source bead:

```bash
sleep 5
bd show "$SOURCE_BEAD" | grep -i assignee
```

The assignee must be non-empty. If it is still empty after 30-60 seconds, do
not assume the fleet is healthy. Record a dispatch-provenance event and
escalate or run the appropriate city-status/check-work skill.

## Dispatch Provenance Event

Every `gc sling` outcome gets a linked event bead. Use
`dispatch-provenance.v1` so downstream lost-bead filters can distinguish a
healthy claim from an immediate strand.

Healthy claim:

```toml
schema = "dispatch-provenance.v1"
source_bead = "<bead>"
dispatch_command = "gc sling <rig>/gc.run-operator <bead> --on work-briefed ..."
formula = "work-briefed"
verified_assignee = true
assignee_state = "non_empty"
classification_hint = "healthy"
fingerprint = "verified_sling_claimed"
observed_at = "YYYY-MM-DDTHH:MM:SSZ"
```

Empty assignee after the verification window:

```toml
schema = "dispatch-provenance.v1"
source_bead = "<bead>"
dispatch_command = "gc sling <rig>/gc.run-operator <bead> --on work-briefed ..."
formula = "work-briefed"
verified_assignee = false
assignee_state = "empty_after_60s"
classification_hint = "immediate_strand"
fingerprint = "empty_assignee_after_verified_sling"
observed_at = "YYYY-MM-DDTHH:MM:SSZ"
```

Create and relate the event before escalating:

```bash
event_bead="$(bd create "dispatch provenance for <bead>" --type event --event-category dispatch.provenance --event-target <bead> --event-payload '<dispatch-provenance.v1 TOML or JSON>' --silent)"
bd dep relate "$event_bead" <bead>
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
