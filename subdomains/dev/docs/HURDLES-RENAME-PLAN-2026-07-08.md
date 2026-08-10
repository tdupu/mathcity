# Hurdles Rename Plan — 2026-07-08

> ⚠️ **SUPERSEDED / DO NOT ACT ON (2026-07-21).** This plan's premise — *"GC uses
> 'gate' for `[steps.check]` blocks"* — is **factually wrong** (verified against
> the gascity source: `[steps.check]` is canonically a **check**; "gate" is the
> control-flow checkpoint role). The gate→"hurdle" rename is **not needed** and
> was not executed. See **`TERMINOLOGY-check-vs-gate.md`** for the correct native
> terminology. Kept for history only.

Bead: gsp-2c0

## Context

GC uses "gate" for `[steps.check]` blocks in formula TOML — workflow-control
checks executed by the GC control dispatcher at step boundaries. The mathcity
pack uses "gate" for brief-policy checklist entries (G1–G16 registry, pass/fail
checks that a brief must clear before advancing). These are different concepts.

**Rename:** every mathcity-owned "gate" → "hurdle" throughout, to eliminate the
collision. The word "hurdle" is used for all domain-policy checklist entries;
`[steps.check]` blocks in formula TOML remain untouched (those ARE real GC
gates).

---

## Files Needing Changes

### 1. Directory rename

```
mathematics/gates/   →   mathematics/hurdles/
```

Contents (5 files):
- `gates/latex-gate.toml`
- `gates/server-touching-safety-override.toml`
- `gates/stale-claim.toml`
- `gates/test-evidence.toml`
- `gates/test-execution.toml`

### 2. Files under mathematics/ with "gate" content references

**Core pack files:**
- `mathematics/pack.toml`

**Asset pipeline files:**
- `mathematics/assets/brief-pipeline/gates.toml`  (the registry file itself)
- `mathematics/assets/brief-pipeline/file-or-sendback-log-spec.md`

**Check scripts:**
- `mathematics/assets/scripts/brief-drain-manifest.sh`
- `mathematics/assets/scripts/checks/brief-mechanical-gates-required.sh`
- `mathematics/assets/scripts/checks/brief-server-touching-safety.sh`
- `mathematics/assets/scripts/checks/brief-stack-low-check.sh`
- `mathematics/assets/scripts/checks/gate-test-evidence.sh`
- `mathematics/assets/scripts/checks/gate-test-execution-declaration.sh`
- `mathematics/assets/scripts/checks/gate-test-execution-evidence.sh`
- `mathematics/assets/scripts/checks/latex-gate-approval-required.sh`

**Formula files:**
- `mathematics/formulas/brief-gate-keep.toml`
- `mathematics/formulas/brief-prep.toml`
- `mathematics/formulas/brief-review-patrol.toml`
- `mathematics/formulas/brief-shuffle.toml`
- `mathematics/formulas/brief-present-next.toml`
- `mathematics/formulas/brief-watchdog-refill.toml`
- `mathematics/formulas/brief-record-decision.toml`
- `mathematics/formulas/decision-enforce.toml`
- `mathematics/formulas/file-or-sendback-route.toml`
- `mathematics/formulas/no-brainer-classify.toml`

**Gates/ formula files (the 5 files that move to hurdles/):**
- `mathematics/gates/latex-gate.toml`
- `mathematics/gates/server-touching-safety-override.toml`
- `mathematics/gates/stale-claim.toml`
- `mathematics/gates/test-evidence.toml`
- `mathematics/gates/test-execution.toml`

**Skill files** (these also contain "gate" in prose/doc context):
- `mathematics/skills/authorize-git-operation/SKILL.md`
- `mathematics/skills/brief-prep/SKILL.md`
- `mathematics/skills/catch-no-brainer/SKILL.md`
- `mathematics/skills/catch-no-brainer/fixtures/novel-shape.md`
- `mathematics/skills/check-latex/SKILL.md`
- `mathematics/skills/coordinate-review/SKILL.md`
- `mathematics/skills/formula-creator/SKILL.md`
- `mathematics/skills/grill-and-present/SKILL.md`
- `mathematics/skills/immediate-work/SKILL.md`
- `mathematics/skills/is-good-experiment/SKILL.md`
- `mathematics/skills/present-briefs/SKILL.md`
- `mathematics/skills/present-it/SKILL.md`
- `mathematics/skills/record-decision/SKILL.md`

**Agent prompt:**
- `mathematics/agents/codex-worker/prompt.template.md`

**Order files:**
- `mathematics/orders/brief-review-patrol.toml`
- `mathematics/orders/post-decision-file-or-sendback.toml`

**Template fragments:**
- `mathematics/template-fragments/escalation-protocol.md`

**Review/verdict docs (non-pack, reference only — rename prose but low priority):**
- `mathematics/CODEX-REVIEW-RESPONSE-2026-07-08.md`
- `mathematics/METHODOLOGY-PACK-VERDICT-2026-07-08.md`
- `mathcity/README.md`

**Pack-level file — the registry asset itself gets renamed:**
- `mathematics/assets/brief-pipeline/gates.toml`  →  `mathematics/assets/brief-pipeline/hurdles.toml`

---

## Substitution Categories

### A. Formula `formula =` field values to rename

In the `gates/` formula files, the `formula =` field names the formula kind.
These use the word "gate" as a domain label:

```toml
# server-touching-safety-override.toml
formula = "gate"          →   formula = "hurdle"

# test-evidence.toml
kind = "gate"             →   kind = "hurdle"

# test-execution.toml
tags = ["gate", ...]      →   tags = ["hurdle", ...]
```

**Exception (do NOT change):** `[steps.check]` blocks inside these files are
real GC gate primitives. Those blocks remain exactly as-is. The TOML keys
`[steps.check]`, `mode = "exec"`, `max_attempts`, `timeout` are GC runtime
fields — do not rename them.

### B. TOML metadata keys using "gc.gate"

In gate formula files, step metadata carries `gc.gate.*` keys:

```toml
metadata = { "gc.gate" = "G1-test-evidence", "gc.gate.kind" = "mechanical" }
metadata = { ..., "gc.gate.kind" = "stop", "gc.gate.blocks" = "..." }
```

These become:
```toml
metadata = { "gc.hurdle" = "G1-test-evidence", "gc.hurdle.kind" = "mechanical" }
metadata = { ..., "gc.hurdle.kind" = "stop", "gc.hurdle.blocks" = "..." }
```

### C. TOML var names and description text in formula files

```toml
[vars.gate_profile]       →   [vars.hurdle_profile]
```

And all references to `{{gate_profile}}` in step metadata and descriptions:
```toml
"gc.brief.gate_profile" = "{{gate_profile}}"   →   "gc.brief.hurdle_profile" = "{{hurdle_profile}}"
```

### D. Asset registry file rename + contents

```
assets/brief-pipeline/gates.toml   →   assets/brief-pipeline/hurdles.toml
```

Inside the file:
```toml
name = "brief-pipeline-gates"    →   name = "brief-pipeline-hurdles"
[[gates]]                         →   [[hurdles]]
gates = [...]   (in profiles)     →   hurdles = [...]
```

### E. Script filenames to rename

```
assets/scripts/checks/gate-test-evidence.sh           →   hurdle-test-evidence.sh
assets/scripts/checks/gate-test-execution-declaration.sh  →   hurdle-test-execution-declaration.sh
assets/scripts/checks/gate-test-execution-evidence.sh     →   hurdle-test-execution-evidence.sh
assets/scripts/checks/latex-gate-approval-required.sh     →   latex-hurdle-approval-required.sh
```

### F. Script internal references

Inside renamed scripts, update `echo` / stderr messages that say "gate":
```sh
echo "gate-test-evidence: ..."   →   echo "hurdle-test-evidence: ..."
echo "gate-test-execution-..."   →   echo "hurdle-test-execution-..."
echo "latex-gate: ..."           →   echo "latex-hurdle: ..."
```

Also in `latex-gate-approval-required.sh`:
```sh
block() { echo "latex-gate: BLOCK — $*"  →  "latex-hurdle: BLOCK — $*"
ok()    { echo "latex-gate: PASS — $*"   →  "latex-hurdle: PASS — $*"
```

The `brief-check.sh` wrapper:
```sh
exec "$(dirname "$0")/brief-check.sh" mechanical-gates "$@"
→  exec "$(dirname "$0")/brief-check.sh" mechanical-hurdles "$@"
```
And `brief-check.sh` must accept `mechanical-hurdles` as a command name.

### G. Formula paths referencing scripts

Every formula `path =` that points to a renamed script:
```toml
path = ".../checks/gate-test-evidence.sh"      →   .../hurdle-test-evidence.sh
path = ".../checks/gate-test-execution-declaration.sh"  →   .../hurdle-test-execution-declaration.sh
path = ".../checks/gate-test-execution-evidence.sh"     →   .../hurdle-test-execution-evidence.sh
path = ".../checks/latex-gate-approval-required.sh"     →   .../latex-hurdle-approval-required.sh
```

Also the registry reference inside formula catalog blocks:
```toml
registry = "assets/brief-pipeline/gates.toml"   →   "assets/brief-pipeline/hurdles.toml"
```

### H. Latex-gate formula name

`gates/latex-gate.toml` has:
```toml
formula = "latex-gate"     →   formula = "latex-hurdle"
name = "latex-gate"        →   name = "latex-hurdle"
```

And the `gate-disposition` step:
```toml
id = "gate-disposition"    →   id = "hurdle-disposition"
title = "Record LaTeX-gate disposition"   →   "Record LaTeX-hurdle disposition"
```

Evidence strings in step bodies:
```
G6 LaTeX-gate: PASS        →   G6 LaTeX-hurdle: PASS
G6 LaTeX-gate: N/A         →   G6 LaTeX-hurdle: N/A
G6 LaTeX-gate: BLOCKED     →   G6 LaTeX-hurdle: BLOCKED
```

### I. Registry gate entry for G6

In `assets/brief-pipeline/hurdles.toml` (formerly gates.toml):
```toml
name = "latex-gate"        →   name = "latex-hurdle"
evidence_key = "G6 LaTeX-gate"   →   "G6 LaTeX-hurdle"
policy = "latex-gate-policy.md"  →   "latex-hurdle-policy.md"
description = "LaTeX-bearing work needs the LaTeX gate outcome..."
             →  "LaTeX-bearing work needs the LaTeX hurdle outcome..."
```

### J. Prose and documentation text

All free-form prose occurrences of "gate" meaning the mathcity brief-policy
concept. Replace in descriptions, titles, README, skill docs. Examples:
```
"gate policy registry"     →   "hurdle policy registry"
"gate evidence"            →   "hurdle evidence"
"Gate Evidence"            →   "Hurdle Evidence"  (the section heading)
"gate registry"            →   "hurdle registry"
"gate-keep"                →   "hurdle-keep"
"gate profile"             →   "hurdle profile"
"gate passes"/"gate fails" →   "hurdle passes"/"hurdle fails"
"stop gate"                →   "stop hurdle"
"hard gate"                →   "hard hurdle"
"judgment gates"           →   "judgment hurdles"
"mechanical gates"         →   "mechanical hurdles"
```

### K. Bead titles/descriptions with "gate" (gascity-packs beads)

```
gsp-eqk  — "F1 — LaTeX gates (check-latex SKILL + latex-gate.toml formula)"
             →  "F1 — LaTeX hurdles (check-latex SKILL + latex-hurdle.toml formula)"
gsp-eqk.2 — "F1b latex-gate.toml at gascity-packs/mathematics/gates/latex-gate.toml"
              →  "F1b latex-hurdle.toml at gascity-packs/mathematics/hurdles/latex-hurdle.toml"
gsp-7lc  — "brief-gated merge" — this is incidental prose, not a mathcity gate; LEAVE.
```

---

## What NOT to Change

The following uses of "gate" are GC-native concepts and must NOT be renamed:

1. **`[steps.check]` TOML blocks** in any formula file. These ARE real GC gates.
   The block header `[steps.check]`, `[steps.check.check]`, and their fields
   (`mode`, `path`, `timeout`, `max_attempts`) are GC runtime primitives.

2. **`formula = "gate"` in `server-touching-safety-override.toml`** — this
   declares the formula's GC kind, which should be left as "gate" if it
   matches a GC-native formula type. **Needs verification:** if GC recognizes
   `formula = "gate"` as a built-in type, leave it; if it's free-text domain
   labeling, change to `"hurdle"`. (Check with `gc help formula-kinds` or GC
   docs before touching.)

3. **`gsp-7lc` description: "brief-gated merge"** — "gated" here is natural
   English (meaning controlled/guarded), not the mathcity policy concept.
   Leave it.

4. **External bead IDs in he-* namespace** (polecat/hecke beads referenced in
   prose like `he-jwmy`, `he-86wu`). Do not update those external references
   to a different repo's beads.

5. **`review_gate: pending / approved`** frontmatter field in brief markdown
   files. This is a brief-state field, not a policy-registry entry. Leave as-is
   or rename to `review_hurdle:` — **needs a deliberate decision** before
   touching.

---

## Order of Operations

Execute in this order to avoid broken path references:

### Phase 1 — Script renames (no content deps yet)

```sh
cd <repos-root>/gascity-packs/mathematics

mv -f assets/scripts/checks/gate-test-evidence.sh \
      assets/scripts/checks/hurdle-test-evidence.sh

mv -f assets/scripts/checks/gate-test-execution-declaration.sh \
      assets/scripts/checks/hurdle-test-execution-declaration.sh

mv -f assets/scripts/checks/gate-test-execution-evidence.sh \
      assets/scripts/checks/hurdle-test-execution-evidence.sh

mv -f assets/scripts/checks/latex-gate-approval-required.sh \
      assets/scripts/checks/latex-hurdle-approval-required.sh
```

### Phase 2 — Update script internals

Apply sed to each newly renamed script:

```sh
# hurdle-test-evidence.sh
sed -i '' 's/gate-test-evidence/hurdle-test-evidence/g; s/gate passes/hurdle passes/g; s/gate fails/hurdle fails/g; s/gate FAIL/hurdle FAIL/g; s/gate blocked/hurdle blocked/g; s/judgment gates/judgment hurdles/g; s/human\/Mayor gate/human\/Mayor hurdle/g' \
  assets/scripts/checks/hurdle-test-evidence.sh

# hurdle-test-execution-declaration.sh
sed -i '' 's/gate-test-execution-declaration/hurdle-test-execution-declaration/g; s/gate-block/hurdle-block/g; s/gate spec/hurdle spec/g' \
  assets/scripts/checks/hurdle-test-execution-declaration.sh

# hurdle-test-execution-evidence.sh
sed -i '' 's/gate-test-execution-evidence/hurdle-test-execution-evidence/g; s/gate spec/hurdle spec/g' \
  assets/scripts/checks/hurdle-test-execution-evidence.sh

# latex-hurdle-approval-required.sh
sed -i '' 's/latex-gate/latex-hurdle/g' \
  assets/scripts/checks/latex-hurdle-approval-required.sh
```

### Phase 3 — Registry asset rename + contents

```sh
mv -f assets/brief-pipeline/gates.toml assets/brief-pipeline/hurdles.toml
```

Then edit `hurdles.toml`:
```sh
sed -i '' 's/brief-pipeline-gates/brief-pipeline-hurdles/g; s/\[\[gates\]\]/[[hurdles]]/g; s/^gates = \[/hurdles = [/g; s/latex-gate/latex-hurdle/g; s/LaTeX-gate/LaTeX-hurdle/g; s/latex-gate-policy/latex-hurdle-policy/g; s/stop gates/stop hurdles/g' \
  assets/brief-pipeline/hurdles.toml
```

### Phase 4 — Gates/ formula files (before directory rename)

Edit each file in `gates/` to update content, then rename the directory last.

```sh
# latex-gate.toml: most intensive rename
sed -i '' 's/latex-gate/latex-hurdle/g; s/LaTeX-gate/LaTeX-hurdle/g; s/gate-disposition/hurdle-disposition/g; s|checks/latex-gate-approval-required\.sh|checks/latex-hurdle-approval-required.sh|g; s|assets/brief-pipeline/gates\.toml|assets/brief-pipeline/hurdles.toml|g; s/gate G6/hurdle G6/g; s/"gc\.gate\.kind"/"gc.hurdle.kind"/g; s/"gc\.gate\.blocks"/"gc.hurdle.blocks"/g; s/gate is a STOP gate/hurdle is a STOP hurdle/g; s/gate is satisfied/hurdle is satisfied/g; s/gate passes/hurdle passes/g; s/STOP gate/STOP hurdle/g' \
  gates/latex-gate.toml

# test-evidence.toml
sed -i '' 's/kind = "gate"/kind = "hurdle"/g; s/gate_id/hurdle_id/g; s|assets/brief-pipeline/gates\.toml|assets/brief-pipeline/hurdles.toml|g; s/"gc\.gate"/"gc.hurdle"/g; s/"gc\.gate\.kind"/"gc.hurdle.kind"/g; s|checks/gate-test-evidence\.sh|checks/hurdle-test-evidence.sh|g; s/gate FAIL/hurdle FAIL/g; s/gate passes/hurdle passes/g; s/gate fails/hurdle fails/g; s/judgment gates/judgment hurdles/g; s/gate evidence/hurdle evidence/g; s/gate-silent/hurdle-silent/g' \
  gates/test-evidence.toml

# test-execution.toml
sed -i '' 's/tags = \["gate"/tags = ["hurdle"/g; s|checks/gate-test-execution-declaration\.sh|checks/hurdle-test-execution-declaration.sh|g; s|checks/gate-test-execution-evidence\.sh|checks/hurdle-test-execution-evidence.sh|g; s/gate fails/hurdle fails/g; s/gate spec/hurdle spec/g; s/gate-block/hurdle-block/g; s/gate enforcement/hurdle enforcement/g; s/gate fails/hurdle fails/g' \
  gates/test-execution.toml

# server-touching-safety-override.toml
# NOTE: 'formula = "gate"' — verify GC kind before changing (see "What NOT to Change")
sed -i '' 's/tags = \["gate"/tags = ["hurdle"/g; s/gate-check time/hurdle-check time/g; s/the gate check/the hurdle check/g; s/the gate is satisfied/the hurdle is satisfied/g; s/the gate is poka-yoke/the hurdle is poka-yoke/g; s/sibling gate/sibling hurdle/g; s/gate evidence/hurdle evidence/g; s/STOP-class/STOP-class/g; s/Hard gate/Hard hurdle/g; s/this gate/this hurdle/g' \
  gates/server-touching-safety-override.toml

# stale-claim.toml
sed -i '' 's/the gate exits/the hurdle exits/g; s/the gate never/the hurdle never/g; s/Mayor gate/Mayor hurdle/g' \
  gates/stale-claim.toml
```

### Phase 5 — Rename the gates/ directory

```sh
mv -f gates/ hurdles/
```

### Phase 6 — Formula files (reference hurdles/ and new script names)

Apply broad substitution across all formula files:

```sh
for f in formulas/*.toml; do
  sed -i '' \
    's|mathematics/gates/|mathematics/hurdles/|g; \
     s|"gc\.brief\.gate_profile"|"gc.brief.hurdle_profile"|g; \
     s/\[vars\.gate_profile\]/[vars.hurdle_profile]/g; \
     s/{{gate_profile}}/{{hurdle_profile}}/g; \
     s|assets/brief-pipeline/gates\.toml|assets/brief-pipeline/hurdles.toml|g; \
     s/gate_profile/hurdle_profile/g; \
     s/gate registry/hurdle registry/g; \
     s/gate evidence/hurdle evidence/g; \
     s/Gate Evidence/Hurdle Evidence/g; \
     s/judgment gates/judgment hurdles/g; \
     s/mechanical gates/mechanical hurdles/g; \
     s/stop gates/stop hurdles/g; \
     s/gate-keep/hurdle-keep/g; \
     s/gate passes/hurdle passes/g; \
     s/gate fails/hurdle fails/g; \
     s/stop\/manual gate/stop\/manual hurdle/g; \
     s/LaTeX-gate/LaTeX-hurdle/g; \
     s/latex-gate/latex-hurdle/g' \
    "$f"
done
```

Special cases in formula files:
- `formulas/brief-gate-keep.toml` → rename to `formulas/brief-hurdle-keep.toml`
  and update `formula = "brief-gate-keep"` → `"brief-hurdle-keep"`.

```sh
mv -f formulas/brief-gate-keep.toml formulas/brief-hurdle-keep.toml
sed -i '' 's/brief-gate-keep/brief-hurdle-keep/g' formulas/brief-hurdle-keep.toml
# Also fix any reference to brief-gate-keep in other formulas:
grep -rl "brief-gate-keep" formulas/ | xargs sed -i '' 's/brief-gate-keep/brief-hurdle-keep/g'
```

### Phase 7 — Skill files (prose rename)

```sh
for f in skills/*/SKILL.md skills/*/fixtures/*.md; do
  sed -i '' \
    's/gate evidence/hurdle evidence/g; \
     s/Gate Evidence/Hurdle Evidence/g; \
     s/gate registry/hurdle registry/g; \
     s/gate runner/hurdle runner/g; \
     s/gate policy/hurdle policy/g; \
     s/gate profile/hurdle profile/g; \
     s/gate passes/hurdle passes/g; \
     s/gate fails/hurdle fails/g; \
     s/stop gates/stop hurdles/g; \
     s/hard gate/hard hurdle/g; \
     s/LaTeX gate/LaTeX hurdle/g; \
     s/LaTeX-gate/LaTeX-hurdle/g; \
     s/latex-gate/latex-hurdle/g; \
     s/gate-keep/hurdle-keep/g; \
     s|mathematics/gates/|mathematics/hurdles/|g; \
     s|assets/brief-pipeline/gates\.toml|assets/brief-pipeline/hurdles.toml|g; \
     s/mechanical gates/mechanical hurdles/g; \
     s/judgment gates/judgment hurdles/g; \
     s/review gate/review hurdle/g; \
     s/gates-candidate-pile/hurdles-candidate-pile/g; \
     s/gates-registry/hurdles-registry/g' \
    "$f" 2>/dev/null || true
done
```

### Phase 8 — Agent prompt

```sh
sed -i '' 's/gate registry/hurdle registry/g; s/gate evidence/hurdle evidence/g; s/policy gate/policy hurdle/g' \
  agents/codex-worker/prompt.template.md
```

### Phase 9 — Orders, assets prose, template-fragments

```sh
sed -i '' 's/gate evidence/hurdle evidence/g; s/gate registry/hurdle registry/g; s/gate-keep/hurdle-keep/g; s/post-decision gate/post-decision hurdle/g' \
  assets/brief-pipeline/file-or-sendback-log-spec.md \
  template-fragments/escalation-protocol.md

# orders/ 
for f in orders/*.toml; do
  sed -i '' 's/gate/hurdle/g' "$f"
done
```

### Phase 10 — pack.toml

```sh
sed -i '' 's/gate policy registry/hurdle policy registry/g' pack.toml
```

### Phase 11 — README and review docs (prose)

```sh
sed -i '' \
  's/gate evidence/hurdle evidence/g; \
   s/Gate Evidence/Hurdle Evidence/g; \
   s/gate registry/hurdle registry/g; \
   s/gate policy/hurdle policy/g; \
   s/gate runner/hurdle runner/g; \
   s/gate profile/hurdle profile/g; \
   s/gate-keep/hurdle-keep/g; \
   s/stop gates/stop hurdles/g; \
   s/hard gate/hard hurdle/g; \
   s/LaTeX gate/LaTeX hurdle/g; \
   s/LaTeX-gate/LaTeX-hurdle/g; \
   s/latex-gate/latex-hurdle/g; \
   s|mathematics/gates/|mathematics/hurdles/|g; \
   s|assets/brief-pipeline/gates\.toml|assets/brief-pipeline/hurdles.toml|g; \
   s/judgment gate/judgment hurdle/g; \
   s/mechanical gate/mechanical hurdle/g; \
   s/the brief gate/the brief hurdle/g; \
   s/brief-gated/brief-hurdled/g' \
  README.md

# Review/verdict docs — lower priority, same treatment
sed -i '' 's/gate/hurdle/g; s/gates/hurdles/g' \
  CODEX-REVIEW-RESPONSE-2026-07-08.md \
  METHODOLOGY-PACK-VERDICT-2026-07-08.md
```

### Phase 12 — Bead metadata updates

```sh
# Update gsp-eqk (LaTeX gates epic)
bd update gsp-eqk --title="F1 — LaTeX hurdles (check-latex SKILL + latex-hurdle.toml formula)" \
  -C <repos-root>/gascity-packs/

# Update gsp-eqk.2 (latex-gate.toml task)
bd update gsp-eqk.2 \
  --title="F1b latex-hurdle.toml at gascity-packs/mathematics/hurdles/latex-hurdle.toml (calls F1a); blocks polecat/he-d4l per he-86wu" \
  -C <repos-root>/gascity-packs/
```

---

## Decisions Needed Before Executing

1. **`formula = "gate"` in `server-touching-safety-override.toml`**: Is this a
   GC-recognized formula kind or free-text domain labeling? If GC requires
   `formula = "gate"` for its control dispatcher, leave it. If it's arbitrary
   domain text, rename to `"hurdle"`.

2. **`review_gate:` frontmatter field** in brief markdown files (e.g.
   `review_gate: pending`): rename to `review_hurdle:` or keep? This field is
   read by `brief-review-patrol.toml`. Renaming requires updating the formula
   and scripts that read it.

3. **`gc.brief.gate_profile` metadata key**: This is carried in GC step
   metadata. If GC runtime recognizes this as a reserved key, do NOT rename it.
   If it is purely passed through to agent context, rename to
   `gc.brief.hurdle_profile`.

4. **`.beads/.gates-candidate-pile/`** (referenced in catch-no-brainer SKILL.md):
   Rename the directory path to `.beads/.hurdles-candidate-pile/` or leave?
   If the directory exists on disk it needs a `mv` too.

---

## Verification After Rename

```sh
# Should return zero results from pack files (excluding review docs if desired):
grep -r "\bgate\b" <repos-root>/gascity-packs/mathematics/ \
  --include="*.toml" --include="*.sh" \
  --exclude="CODEX-REVIEW-RESPONSE-*" --exclude="METHODOLOGY-PACK-VERDICT-*" \
  -l

# Confirm hurdles/ directory exists and gates/ is gone:
ls <repos-root>/gascity-packs/mathematics/hurdles/
ls <repos-root>/gascity-packs/mathematics/gates/ 2>&1  # should say: no such file or directory

# Confirm registry file renamed:
ls <repos-root>/gascity-packs/mathematics/assets/brief-pipeline/hurdles.toml

# Confirm script renames:
ls <repos-root>/gascity-packs/mathematics/assets/scripts/checks/ | grep hurdle
```
