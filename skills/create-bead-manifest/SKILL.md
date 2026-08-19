---
name: create-bead-manifest
description: |
  Snapshot all genuine open beads (filtering noise) into a dated manifest
  at <city-root>/bead-manifests/manifest-<date>-<ordinal>.md. The manifest is a
  hierarchical triage table with 11 action categories, epic/convoy grouping,
  age/rig/moot columns, and in-flight cross-references. Use when you need a
  clean inventory of dispatchable work — before /refine-bead-manifest, before
  a new session's work-queue review, or when the human adjudicator asks "how many open beads
  do we have?". Trigger phrases: "create bead manifest", "bead inventory",
  "snapshot the queue", "what's in the queue".
---

# create-bead-manifest

Produce a dated, noise-filtered bead manifest at
`<city-root>/bead-manifests/manifest-<date>-<ordinal>.md`.

## Pre-flight (check-zero)

Before doing anything, confirm Dolt is reachable and the bd CLI works. Use the
canonical three-valued Dolt probe (`template-fragments/dolt-preflight.md`) — a
`gc dolt health` exit of **2** means "reachable, compaction quarantined", which
is **non-fatal**; only exit 1 (or a missing `gc`) means Dolt is down:

```bash
# `gc dolt health` is THREE-valued: 0 healthy, 2 reachable-but-quarantined
# (non-fatal), 1/other unreachable. See template-fragments/dolt-preflight.md.
_dolt_out=$(gc dolt health 2>&1); _dolt_rc=$?
case "$_dolt_rc" in
  0) ;;
  2) ;;   # reachable; auto-GC blocked by a standing compaction quarantine.
          # NON-FATAL and NOT this skill's business: bd resolves beads normally.
          # Proceed SILENTLY — the reporting skills surface it (Variant B).
  *) echo "I'm sorry, I can't do that — Dolt is unreachable."
     echo "Run 'gc dolt status' / 'gc dolt start' to bring Dolt up, then retry."
     echo "(create-bead-manifest needs Dolt to resolve bead metadata.)"
     exit 1 ;;
esac
bd list --help >/dev/null 2>&1 || {
  echo "I'm sorry, I can't do that — the bd CLI is not functional."
  echo "Run the Beads install/update step and retry."
  echo "(create-bead-manifest enumerates open beads via bd.)"
  exit 1
}
```

## Step 1 — Determine output path

```bash
DATE=$(date +%Y-%m-%d)
OUTDIR="$HOME/gt/bead-manifests"
mkdir -p "$OUTDIR"
# Find next ordinal (01, 02, …)
ORDINAL=$(printf "%02d" $(( $(ls "$OUTDIR"/manifest-${DATE}-*.md 2>/dev/null | wc -l) + 1 )))
OUTFILE="$OUTDIR/manifest-${DATE}-${ORDINAL}.md"
```

## Step 2 — Fetch all open beads

```bash
bd list --status open --limit 0 --json 2>/dev/null > /tmp/bead-manifest-raw.json
```

If the JSON is empty or bd errors, report and exit.

## Step 3 — Filter noise

Noise categories (exclude from the manifest):
- **wisps / nudges**: title matches `^(wisp|nudge|gt-wisp|gt-nudge)` or has label `wisp` or `nudge`
- **handoff beads**: title matches `handoff` (case-insensitive) or has label `handoff`
- **brief-pipeline internal**: title matches `(brief-shuffle|brief-record|brief-patrol|on-merge|brief-watchdog|brief-archive-sweep|file-or-sendback)` (these are order-run steps, not human-dispatchable work). The `write-disposition` alternative was dropped (gsp-89yli lockless rewrite retired that step id in favor of `claim-item`/`process-item`/`finalize`, and empirically neither the old nor the new brief-shuffle step-bead titles ever embed their hyphenated step id as a literal substring — e.g. the formula's static `title` field for the `claim-item` step reads "Claim one pile item (atomic mv)" (no live `claim-item` step bead has run yet as of this edit, so this is read from `formulas/brief-shuffle.toml`, not an observed live bead — but old-vocabulary step beads that HAVE run confirm the same pattern: e.g. a live `brief-shuffle.select-pile-item` bead is titled "Select one pile item", with neither the hyphenated step id nor "brief-shuffle" appearing in the title) — so a title-based alternative for the new ids would very likely never fire either; the `brief-shuffle` alternative already covers the order-level and escalation-bead titles that actually do carry that substring, e.g. `order:brief-shuffle-pile:...` and `[brief-shuffle] gate-rejected: ...`).

After filtering, the remaining beads are **genuine work beads** (count = S).

## Step 4 — Classify each bead into an action category

Apply these rules in order (first match wins):

| Priority | Rule | Category |
|----------|------|----------|
| 1 | Epic or convoy type AND age ≥ 10d AND no clear dispatch path | `🗺️ TRACK_EPIC` |
| 2 | Type = `epic` or `convoy` (any age) | `🗺️ TRACK_EPIC` |
| 3 | Type = `decision` AND age ≤ 5d AND moot = ✅ | `🚀 DISPATCH_NOW` |
| 4 | Type = `decision` AND (age > 5d OR moot ≠ ✅) | `🤔 DECISION_NEEDED` |
| 5 | Type = `spec` | `📐 DESIGN_WORK` |
| 6 | Priority = P1 AND age ≥ 7d AND no assignee | `⚠️ TRIAGE_P1` |
| 7 | Priority = P1 AND age < 7d | `🚀 DISPATCH_NOW` |
| 8 | Type = `bug` AND priority = P1 AND age ≥ 7d | `⚠️ TRIAGE_P1` |
| 9 | Type = `bug` AND (priority = P2 OR age < 7d) | `🐛 DISPATCH_BUG` |
| 10 | Priority = P3 | `❄️ BACKBURNER` |
| 11 | Age ≥ 10d AND moot = ❓ | `🕰️ TRIAGE_OLD` |
| 12 | Structural (title contains STRUCTURAL, DESIGN, or WATCHDOG) AND age ≥ 14d | `🔍 TRIAGE_VERIFY` |
| 13 | Moot assessment = moot (title suggests superseded, escalation resolved) | `🗑️ CLOSE_MOOT` |
| 14 | Default (P2, fresh, non-bug) | `📦 DISPATCH` |

### Lost-bead filter fields

For beads that look lost, stale, stranded, blocked, superseded, or no-fire,
add these columns to the manifest row. Persisted classification events use
`schema = "lost-bead-classification.v1"`.

- `lost_class`: one of `assets/bead-filter/lost-bead-schema.toml` `lost_classes`.
- `recommended_disposition`: one of the schema dispositions.
- `root_cause`: one root-cause class from the schema.
- `fingerprint`: a stable grouping key.
- `classification_evidence`: command output references or quoted observations.

Preserve the broad action category such as `DISPATCH_NOW`, `TRIAGE_OLD`, or
`CLOSE_MOOT`; the lost-bead fields are additional classifier evidence, not
replacements for the manifest partition. Manifest rows are snapshots. Durable
classifications are linked `type=event` beads created during refinement or
dispatch provenance capture.

**Moot assessment heuristic:**
- `✅` = recent (≤ 3d) OR explicitly resolved OR type=decision with clear verdict recorded
- `🔍 check` = structural/old needs human verify before dispatch
- `⚠️ moot?` = title suggests an escalation/storm that may have resolved
- `❓` = unknown, assume not moot

**In-flight cross-references:** For each bead, check `bd dep tree <id>` for directly related beads that are currently `in_progress`. List up to 3 IDs + "+N" for remainder.

**Rig mismatch detection:** Compare bead prefix (first 2 letters) to the expected rig:
- `he-` → hecke
- `as-` → agent_skills
- `gsp-` → gascity-packs
- `hq-` → hq
- `gt-` → root (no mismatch if filed in root)
If the bead title references a specific rig and the prefix is `gt-`, flag as `~~root~~ → **<rig>**`.

## Step 5 — Group hierarchically

Order:
1. Epics and convoys (type = epic or convoy), sorted P1 → P2 → P3, then age descending
2. Decision beads
3. Spec/design beads
4. Bug beads (P1 bugs first, then P2)
5. Series groups (beads with `.N` suffix — show parent row then indented children)
6. Standalone tasks/features (everything else), sorted P1 → P2 → P3, then age descending

## Step 6 — Write the manifest

```markdown
# Bead Manifest — <DATE> (<ORDINAL>)

**Total genuine work beads:** <S>
**Generated:** <timestamp>
**Source:** bd list --status open (noise-filtered)

## Action Partition Summary

| Action | Count | Description |
|--------|-------|-------------|
| 🚀 DISPATCH_NOW | N | P1 fresh — send to fleet now |
| 📦 DISPATCH | N | Ready work — queue it |
| 🐛 DISPATCH_BUG | N | Bugs — dispatch to bug-fix convoy |
| ⚠️ TRIAGE_P1 | N | P1 but old/unclear — human triage |
| 🕰️ TRIAGE_OLD | N | Old (≥10d) — review or close |
| 🔍 TRIAGE_VERIFY | N | Old + structural — verify still live |
| 🤔 DECISION_NEEDED | N | Decision beads — need human verdict |
| 🗺️ TRACK_EPIC | N | Epic/convoy — just track |
| 📐 DESIGN_WORK | N | Spec beads — design work |
| ❄️ BACKBURNER | N | P3 — park for later |
| 🗑️ CLOSE_MOOT | N | Moot — close without work |

## Full Triage Table

Grouped: epics/convoys → decisions → specs → bugs → series → standalone. Indent = sub-item.

| ID | Type | P | Age | Rig (current→expected) | Moot? | Action | In-flight related | Labels | Title |
|----|------|---|-----|------------------------|-------|--------|-------------------|--------|-------|
<rows>

## Hygiene & Policy Findings

### H1 — Rig mismatches (bead filed in wrong rig)
<list of gt- beads with expected non-root rig>

### H2 — Moot candidates (close without work)
<list>

### H3 — Old unassigned P1 beads (>7 days, no assignee)
<list>
```

## Step 7 — check-zero verification

Before writing the file, verify:
1. Every bead from Step 3 appears in exactly one row of the manifest (partition property).
2. The summary counts sum to S.
3. No noise bead appears in the manifest.

Report any discrepancy as a WARNING in the manifest header, not a silent failure.

## Step 8 — Output path

Write to `$OUTFILE`. Print the path to stdout:
```
Manifest written: <city-root>/bead-manifests/manifest-<date>-<ordinal>.md
Total genuine beads: <S>
```

## xkcd-927 guard

Before implementing, check:
- `bd audit` or `beads:audit` skill — does it already produce an equivalent inventory?
- `<city-root>/plans/bead-triage-*.md` — is there a recent manifest from the same day?

If a same-day manifest exists, ask: "A manifest already exists at `<path>`. Create a new one anyway? (y/N)"

If `beads:audit` covers the same ground, prefer extending it. Only create a new manifest if the hierarchical epic/convoy grouping or the 11-category action partition are NOT produced by the existing tool.

## What this skill does NOT do

- ❌ Dispatch any beads — it only creates the manifest
- ❌ Close or modify any beads
- ❌ Replace `beads:audit` (this is a higher-level triage layer, not a raw audit)
- ❌ Run `gc status` to check fleet health (bug gs-0cy2 — use `tmux -L gt ls`)
