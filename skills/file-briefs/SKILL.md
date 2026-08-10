---
name: file-briefs
description: Async brief-filing variant of grill-with-docs for Mayor onboarding. Given the restart PROMPT + canonical onboarding docs + the charge, enumerates open questions/decision points and files one brief per question via the brief pipeline (brief-prep / create-brief), then surfaces the batch via present-briefs. Replaces the synchronous grill-with-docs interview with a doctrine-compliant async brief-stack workflow. Trigger on "file-briefs", "/file-briefs", "file my onboarding briefs", "async grill", or at the start of a Mayor session after mayor-math-restart.
---

# file-briefs

Async onboarding alternative to `/grill-with-docs`: same decision-sharpening
goal — resolve the open questions the charge + canonical docs surface — but
batched, async, and recorded on the brief stack instead of typed into chat.

**Doctrine:** [[grills-here-briefs-there]] + [[mayor-no-direct-grilling]] —
Mayor routes decisions through the brief stack, not inline chat.

## When to use

- At Mayor onboarding (invoked by `mayor-math-restart` or the restart PROMPT)
  instead of `/grill-with-docs`
- Whenever the Mayor would have grilled the human adjudicator on onboarding docs or the charge
- Keep `/grill-with-docs` for genuine interactive design sessions where
  real-time back-and-forth is intentional; this skill is the onboarding default

## Inputs

Read in Phase 1:
- `~/Documents/misc/PROMPT-mayor-restart.txt` — background, standing rules,
  city state, and charge
- `<mathcity-pack-root>/docs/MAYOR-ONBOARDING.md` — the doc index
  (points to CITY-RESTART-CHECKLIST.md, CITY-OPERATION-REFERENCE.md,
  TEST-CYCLE-GUIDE.md, DOGFOOD-WORKFLOW.md)
- The **handoff bead** named in the PROMPT (`bd show <id>`)
- The **charge** (current session priority) from the PROMPT

## Procedure

### Phase 1 — Read and enumerate decision points

1. Read the restart PROMPT and the onboarding docs it indexes.
2. **Enumerate** every open question or decision point visible in those docs:
   - Ambiguous or conflicting standing rules
   - Outstanding work items that require human adjudication
   - Architecture or policy questions the charge raises
   - Any question the Mayor would have put to the human adjudicator in a grilling session
3. Deduplicate: same question surfaced by multiple docs → one brief.
4. Assign each a `slug` (kebab-case, max 40 chars) and a `priority` (P0–P4)
   based on the charge emphasis.
5. If enumeration yields 0 items: report "No open decision points — onboarding
   context is complete." and exit.

### Phase 2 — Create one decision bead per question

For each enumerated decision point, create a `decision` bead:

```bash
bd create \
  --title "[onboarding-decision] <one-line statement of what is being decided>" \
  --type decision \
  --priority <P0..P4> \
  --description "$(cat <<'EOF'
## What is being decided

<concise statement of the open question, framed as a binary or small-enumerated choice>

## Context from onboarding docs

<relevant quote or pointer — e.g., "CITY-OPERATION-REFERENCE.md §pool-architecture states X; the charge says Y; these may conflict.">

## Why this needs human adjudication

<one sentence — why the Mayor cannot resolve this alone>
EOF
)"
```

Note each returned `bead_id`. Proceed immediately — do not wait for the human adjudicator
before filing all beads.

### Phase 3 — File one brief per bead (in parallel where possible)

For each `bead_id` from Phase 2, invoke `/brief-prep` with the bead-id as the
artifact and a reviewer persona specific to onboarding decisions:

```
reviewer_persona = "Mayor onboarding reviewer checking that this decision
  point is well-scoped and the recommended answer is actionable for the human adjudicator"
```

Use the Workflow tool with `parallel()` when available:

```javascript
const BEAD_IDS = [...]; // from Phase 2
await parallel(
  BEAD_IDS.map(id => () =>
    agent(`Run /brief-prep on bead-id "${id}". reviewer_persona: "Mayor session
onboarding reviewer checking that this decision point is well-scoped and
the recommended answer is actionable for the human adjudicator". No tests apply — this
is a policy/standing-rule bead.`,
          { label: `file-brief:${id}` })
  )
);
```

If workflow fan-out is unavailable (polecat / stripped session): file briefs
sequentially, one bead at a time.

**Do NOT wait for the human adjudicator's response before filing the next brief.** The entire
batch goes in first; answers come back via present-briefs later.

### Phase 4 — Present the filed briefs

After all briefs are deposited, invoke `/present-briefs` to surface them in a
batch hot queue. `/adjudicate-brief` records each verdict on the brief bead
(one-bead model).

```bash
# Verify briefs landed before presenting:
ls <city-root>/.beads/briefs/.pile/*-brief.md | head -10
/present-briefs
```

### Phase 5 — Feed verdicts back (passive)

As adjudication happens, verdicts are recorded on the brief beads. The Mayor
reads closed/adjudicated briefs in the next session via:

```bash
bd list --status closed --type decision --limit 10 --json \
  | jq '.[] | {id, title, metadata}'
```

No active step required from this skill — the brief pipeline handles
persistence. The Mayor's next Mayor session starts with those verdicts
already on the record.

## Comparison with grill-with-docs

| Dimension | `/grill-with-docs` | `/file-briefs` |
|-----------|-------------------|----------------|
| Mode | Synchronous, one Q at a time | Async, all Qs filed at once |
| Durability | Ephemeral chat transcript | Gated `.md` brief artifacts on the stack |
| the human adjudicator's time | Blocked until each answer is given | Reviews batch at convenience |
| Doctrine | OK for interactive design sessions | Required for Mayor onboarding |

## Hard rules

- **NO inline grilling.** All questions go through briefs. Do not ask the human adjudicator
  questions in the Mayor's terminal while filing. If context is missing that
  would be needed to enumerate decision points, report the gap and stop.
- **NO `bd close` on brief beads.** Adjudication
  closes the bead.
- **Composes, never duplicates.** Delegate to `/brief-prep` for each brief;
  do NOT re-implement brief-pipeline machinery.
- **Credential discipline** per [[never-echo-credentials]].

## Cross-references

- [[brief-prep]] — the per-brief pipeline worker (Phase 3 calls this)
- [[create-brief]] — the gated `.md`-artifact producer (called by brief-prep)
- [[present-briefs]] — batch-present tool for human adjudication (Phase 4)
- [[adjudicate-brief]] — the human adjudicator's verdict tool (downstream consumer)
- [[mayor-math-restart]] — onboarding orientation skill; ends with this skill
- [[grills-here-briefs-there]] — the doctrine this skill enforces
- [[mayor-no-direct-grilling]] — why the Mayor routes through briefs
- [[two-skill-split]] — brief-prep + present-briefs as the pipeline split
- [[grill-with-docs]] — the synchronous alternative for design sessions
- [[grilling]] — the underlying interview technique (used by grill-with-docs)
