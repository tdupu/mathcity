Produce a decision BRIEF for this build instead of publishing.

This is the `build-basic-briefed` terminal slot (Mechanism D2). Publishing —
pushing a branch, opening a PR, merging — is NOT this step's job and MUST NOT
happen here. Shipping occurs later, on APPROVE, when the
brief-decision-dispatch verdict edge reassigns the source bead to
`<rig>/gc.publisher` and the real publish flow runs.

## Identify the source

Read the workflow root bead of this molecule. The build's source bead id is
its `gc.source_bead_id` metadata; the final report path is
`gc.build.final_report_path`. If `gc.source_bead_id` is absent, treat the
workflow root itself as the source and say so in the brief header.

## Produce the brief

1. Run the **brief-prep SKILL** on the source bead (spawn an agent that
   invokes `brief-prep` with the source id, or invoke the skill directly if
   your session can). Use the SKILL path — do NOT `bd mol pour brief-prep`
   and do NOT sling the brief-prep formula from this step.
2. Give the brief the build's evidence: cite the final report
   (`gc.build.final_report_path`), the review artifact, and the
   implementation summary in the brief's evidence section.
3. Route the classification through **catch-no-brainer** as brief-prep
   directs. Do not pre-trim: every resolved build gets a brief; the
   no-brainer machinery downstream decides what reaches a human.
4. The deposited brief is `gc.brief.*`-stamped by brief-prep. Never strip
   those keys — they are the self-exclusion filter that keeps brief
   molecules from re-entering brief-firing mechanisms.
5. The deposited brief must include this producer provenance frontmatter:

   ```yaml
   producer_contract: brief-producer.v1
   source_formula: build-basic-briefed
   source_step: publish
   routing_path: "{{routing_path}}"
   ```

## Record the outcome

`gc.outcome` is the workflow step outcome, not the publish mode. Never set
`gc.outcome=noop`. A successful brief deposit is a successful publish step:

```bash
gc bd update "$CLAIMED_BEAD_ID" \
  --set-metadata 'gc.outcome=pass' \
  --set-metadata 'gc.publish_outcome=brief' \
  --set-metadata 'gc.publish_mode=brief' \
  --set-metadata 'gc.build_outcome=pass' \
  --set-metadata 'gc.final_report=<final report path>' \
  --set-metadata 'gc.brief.slug=<brief slug>' \
  --set-metadata 'gc.brief.path=<deposited brief path>' \
  --set-metadata 'gc.brief.source_formula=build-basic-briefed' \
  --set-metadata 'gc.brief.source_step=publish' \
  --set-metadata 'gc.brief.routing_path={{routing_path}}' \
  --set-metadata 'gc.brief.producer_contract=brief-producer.v1'
gc bd close "$CLAIMED_BEAD_ID" --reason 'Decision brief deposited; shipping deferred to the APPROVE verdict edge.'
```

Close only after the brief is deposited and its path is recorded. If
brief-prep fails, do NOT close this step as passed — record the failure on
the step bead (`gc.outcome` unset, WARN in the notes) and escalate to the
mayor (`gc mail send mayor`) rather than silently no-op'ing; a silently
skipped brief is an invisible false-negative (the failure class this
mechanism exists to eliminate).
