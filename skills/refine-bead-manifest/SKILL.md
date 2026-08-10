---
name: refine-bead-manifest
description: |
  Given a bead manifest (S beads), produce a partition B of work beads to
  dispatch + one brief per b' in B. Every bead in S is "acted on" by exactly
  one b' in B. Approving b' triggers the corresponding action (dispatch,
  close-moot, triage, etc.) via mathcity.work. The output is a pile of
  briefs under <city-root>/.beads/decisions-track/ + a summary table.
  Use after /create-bead-manifest when you want to convert a triage snapshot
  into an actionable dispatch plan that the human adjudicator can approve batch-by-batch.
  Trigger phrases: "refine bead manifest", "convert manifest to dispatch plan",
  "make briefs for the manifest beads", "dispatch the manifest".
---

# refine-bead-manifest

Convert a bead manifest (output of [[create-bead-manifest]]) into an
actionable set B of work beads + one brief per b' in B, satisfying the
**partition property**: every bead b in S is acted on by exactly one b' in B.

## Pre-flight (check-zero)

```bash
gc dolt health >/dev/null 2>&1 || {
  echo "I'm sorry, I can't do that — Dolt is unreachable."
  echo "Run 'gc dolt start' and retry."
  exit 1
}
```

## xkcd-927 guard (run first)

Before creating any new beads, check:
1. Does `bd search "batch-dispatch"` return existing batch-dispatch beads covering the same manifest date?
2. Does `bd search "triage"` return open triage beads that duplicate this scope?

If overlaps exist, list them and ask: "These existing beads may overlap with the proposed B. Proceed anyway, reuse them, or abort?"

Never create a new b' for scope already covered by an open in-progress bead. Prefer extending existing beads over creating new ones (xkcd-927 principle).

## Step 1 — Load the manifest

**Input options (in priority order):**
1. Explicit path arg: `/refine-bead-manifest <city-root>/bead-manifests/manifest-2026-07-18-01.md`
2. Most recent manifest: `ls -t <city-root>/bead-manifests/manifest-*.md | head -1`
3. Fallback: run `/create-bead-manifest` first, then use its output.

Read the manifest. Extract:
- S = list of all bead IDs in the triage table
- Action category for each bead (from the manifest's "Action" column)
- Current rig for each bead

Verify the manifest is not stale (generated > 48h ago → warn, but proceed unless the human adjudicator says abort).

## Step 2 — Define the partition B

B is a small set of "work beads" (likely 3–8), each covering a natural cluster of S-beads. The partition must be **complete** (every s ∈ S has exactly one b' ∈ B that acts on it) and **non-overlapping** (no s ∈ S appears in two b's).

**Recommended partition shape** (adjust to actual manifest content):

| b' in B | Covers S-beads with Action | Recommended b' type | On approval |
|---------|---------------------------|---------------------|-------------|
| `CLOSE-MOOT` | 🗑️ CLOSE_MOOT | task | Force-close all moot beads (with reasons) via mathcity.work |
| `DISPATCH-NOW` | 🚀 DISPATCH_NOW | task | Sling all DISPATCH_NOW beads immediately via mathcity.work |
| `BUG-CONVOY` | 🐛 DISPATCH_BUG | task | Create a bug-fix convoy + sling all bug beads into it |
| `DISPATCH-BATCH` | 📦 DISPATCH | task | Queue all DISPATCH beads for the fleet via mathcity.work (batch) |
| `TRIAGE-P1` | ⚠️ TRIAGE_P1 | decision | Present TRIAGE_P1 beads to the human adjudicator one-by-one for verdict |
| `TRIAGE-OLD` | 🕰️ TRIAGE_OLD | decision | Present TRIAGE_OLD beads: close/defer/re-dispatch each |
| `TRIAGE-VERIFY` | 🔍 TRIAGE_VERIFY | decision | Verify each TRIAGE_VERIFY bead is still live; re-dispatch or close |
| `DECISIONS` | 🤔 DECISION_NEEDED | decision | Route decision beads through decisions-to-briefs pipeline |
| `DESIGN-WORK` | 📐 DESIGN_WORK | task | Sling design beads to gc.design workers |
| `EPIC-TRACK` | 🗺️ TRACK_EPIC | task | Add heartbeat comment to each epic/convoy (no dispatch needed) |
| `BACKBURNER` | ❄️ BACKBURNER | task | Label all backburner beads with `parked` and snooze 30d |

**SAFETY INVARIANT (from [[decisions-to-briefs]]):**
- `CLOSE-MOOT` actions MUST list each bead ID + reason in the brief body.
- `DISPATCH-NOW` and `DISPATCH-BATCH` are reversible (slung beads can be recalled).
- `TRIAGE-*` and `DECISIONS` are human-gate actions — their briefs are `external-reminder` shaped.
- No b' in B may auto-execute: irreversible, server-live-write, or user-skill-touching actions.
- If any b' would trigger a git push or Dolt write, downgrade to `external-reminder` shape.

## Step 3 — Create the B beads in bd

For each b' in B, file a new bead with:
```bash
bd create "<b'-title>" --type task --priority P2 \
  --description "$(cat <<'EOF'
## Scope
Acts on S-beads: <comma-separated list of bead IDs>

## On Approval
<one-paragraph description of what mathcity.work does when this bead is dispatched>

## Partition
Every s acted on by this b' will be: <dispatched | closed | triaged | tracked>
EOF
)"
```

Record the new bead ID for each b'. Print a mapping table: `b' ID → action category → bead IDs acted on`.

## Step 4 — Create one brief per b'

For each b' in B, create a brief file at
`<city-root>/.beads/decisions-track/<N>-<b'-slug>-brief.md`
using the [[decisions-to-briefs]] compact or full form:

**compact form** (for CLOSE-MOOT, DISPATCH-NOW, BUG-CONVOY, DISPATCH-BATCH, EPIC-TRACK, BACKBURNER):
```
DECISION:  Should we <action> the <N> <category> beads in this cohort?
CONTEXT:   These beads were classified as <category> in manifest <manifest-file>.
RECOMMEND: <approve-verb> — <one-line reason why action is safe>
CONFIRM:   y / n / grill-me-further

action_block:
  on_approve:
    - type: sling-bead  # or close-supersede, wire, etc.
      targets: [<b' ID>]  # the b' bead itself gets dispatched
  on_reject:
    - type: file-follow-up-brief
      note: "the human adjudicator chose not to <action>; re-triage these beads individually"
  on_defer:
    - type: snooze
      interval: 7d
```

**full form** (for TRIAGE-P1, TRIAGE-OLD, TRIAGE-VERIFY, DECISIONS):
- §1 Decision: "Should the following <N> beads be individually triaged?"
- §2 Recommended: "YES — present each bead individually via /present-it"
- §3 Assumptions: list the beads and their ages
- §4 Alternatives: batch-close vs individual triage vs defer
- §5 Risks: stale bead may have been superseded; re-check bd show before acting
- §6 Evidence: bead list with titles from manifest
- §7 Gates: test-evidence N/A (decision-shaped)

## Step 5 — Update manifest.jsonl

Append one line per b' to `<city-root>/.beads/decisions-track/manifest.jsonl`:
```json
{"n": <N>, "slug": "<b'-slug>", "source_bead": "<b'-id>", "form": "compact|full",
 "track": "bead-manifest-<date>", "status": "ready",
 "acts_on": [<list of S-bead IDs>]}
```

### Lost-bead classification bridge

When a manifest row carries lost-bead filter fields, create or reuse one
linked `type=event` bead per classified source bead before filing the cluster
brief. Each cluster brief must include a `Classification Records` section with
the event bead IDs and one TOML printout per bead:

```toml
schema = "lost-bead-classification.v1"
bead_id = "example-bead-id"
observed_at = "2026-07-25T00:00:00Z"
observer = "refine-bead-manifest"

[finding]
lost_class = "hidden_blocker"
evidence = ["manifest classification evidence"]

[disposition]
recommendation = "encode_dependency"
rationale = "The blocker should be encoded mechanically."
reversible = true

[root_cause]
class = "hidden_human_decision_dependency"
suspected_source = "manual"
repair_candidate = true
fingerprint = "ready_but_prose_blocked"
```

When writing `<city-root>/.beads/decisions-track/manifest.jsonl`, include
`classification_event_id`, `classification_schema`, `lost_class`,
`recommended_disposition`, `root_cause`, and `fingerprint` for each bead or
cluster when known. The manifest row is a cache pointer; the linked event bead
is the canonical classification record and remains visible through `bd list`,
`bd show`, and dependency traversal.

## Step 6 — check-zero + partition verification

Verify the partition is complete:
```python
# Pseudocode
all_acted = set()
for b_prime in B:
    for s in b_prime.acts_on:
        assert s not in all_acted, f"OVERLAP: {s} appears in two b' beads"
        all_acted.add(s)
missing = set(S) - all_acted
assert not missing, f"INCOMPLETE PARTITION: {missing} not covered"
```

Report any violation as an ERROR. Do not write output until the partition is valid.

## Step 7 — Output summary

Print:
```
refine-bead-manifest complete
Manifest: <path>
S = <N> beads
B = <M> work beads

Partition:
  b'1 (CLOSE-MOOT, <id>): <K1> beads
  b'2 (DISPATCH-NOW, <id>): <K2> beads
  ...

Briefs written to <city-root>/.beads/decisions-track/
Next step: /present-briefs to drain the pile
```

## What this skill does NOT do

- ❌ Execute any dispatch — it creates beads + briefs; approval via /present-briefs triggers dispatch
- ❌ Close any bead in S directly — closes happen when b' (CLOSE-MOOT) is approved and dispatched
- ❌ Push any commits
- ❌ Override the xkcd-927 guard if overlapping beads exist
- ❌ Auto-approve any brief — every b' requires human adjudication via /present-briefs
