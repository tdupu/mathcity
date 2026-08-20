---
name: new-beads-policy
description: >
  Pre-filing redundancy gate for new dispatch beads. Run before creating any
  bead that will enter the math-city-work dispatch queue (via build-basic-briefed
  or gc sling). Checks whether an existing open bead already covers the same
  problem — if so, signals MERGE or DROP instead of creating a new bead. Also
  the path for amendments to POLICY-beads.md (the rule-set for bead creation/lifecycle).
  Trigger on "new beads policy", "pre-dispatch check", "check before creating bead",
  "is there already a bead for X", "new-beads-policy", or automatically when
  math-city-work is about to create a new bead for dispatch.
---

# new-beads-policy

**Two distinct uses share this skill:**

1. **Pre-dispatch redundancy gate** — run BEFORE creating a new bead that will
   be slung via `math-city-work`. Checks existing open beads for overlap.
   Output: `PROCEED` / `MERGE` / `DROP`.

2. **POLICY-beads.md amendments** — the official path for adding or changing rules
   in `~/repos/gascity-packs/mathcity/POLICY-beads.md` (per `new-math-bead-policy`
   §Note, PP1.4). See "Amendment path" below.

---

## Use 1 — Pre-dispatch redundancy gate

### When to run

Mandatory before `bd create` for any bead that will be dispatched via
`math-city-work`. Optional but recommended for research/planning beads.

This is the pre-hook that prevents the dispatch queue from accumulating
redundant work items. The check is inexpensive; skipping it is not.

### Inputs

- **Proposed title** (required)
- **Proposed description** (recommended — improves semantic overlap detection)
- **Proposed rig** (optional; defaults to current rig)

### Procedure

**Step 1 — Extract keywords**

Identify 3–6 content-bearing keywords from the title + description (nouns,
technical terms, domain concepts). Exclude stop words ("fix", "add", "update",
"the", "for").

**Step 2 — Search existing open beads**

```bash
# From the rig root (e.g. cd ~/gt):
bd search "<keyword-1>" 2>&1 | head -40
bd search "<keyword-2>" 2>&1 | head -40
# For multi-keyword overlap:
bd list --status open --limit 0 2>&1 | grep -i "<keyword>" | head -20
```

Also check IN_PROGRESS and BLOCKED beads — a bead that is already being worked
on is a stronger conflict than one that is merely open.

**Step 3 — Semantic overlap assessment**

For each candidate returned, assess overlap on three dimensions:

| Dimension | High overlap | Low overlap |
|---|---|---|
| Problem | Same root cause or failure mode | Different system, different error |
| Scope | Same rig + same fix surface | Different rig or different code path |
| Goal | Same deliverable | Beads produce different artifacts |

**Step 4 — Classify and emit verdict**

```
VERDICT: PROCEED | MERGE | DROP
```

- **PROCEED** — no meaningful overlap found. Safe to create the new bead.
  Output the new `bd create` command to run.

- **MERGE** — an existing bead covers ≥ 2 of 3 dimensions at HIGH overlap.
  Do NOT create the new bead. Instead:
  1. Name the existing bead ID + title
  2. If the proposed bead adds detail not in the existing bead, add it as a
     comment: `bd comments add <existing-id> "<additional context>"`
  3. Output: `MERGE: <existing-id> — <one-line reason>`

- **DROP** — the problem is already fully covered AND the existing bead is
  either in_progress or has a recent note. No action needed.
  Output: `DROP: <existing-id> already covers this — <one-line reason>`

### Integration with math-city-work

The redundancy gate should run as a conceptual "Step 0" before any `gc sling`
or `bd create` for a new dispatch bead. The preferred invocation:

```
"Before I create [proposed-bead-title], /new-beads-policy to check for overlap."
```

Or inline in math-city-work dispatch flow: if the Mayor is about to file a new
bead and sling it, pause at Step 0 and run the redundancy check first.

### Hard rules

- **Never skip** when creating a bead that will be immediately slung.
- **MERGE wins over PROCEED** when in doubt — an added comment on an existing
  bead is lower cost than a parallel bead that strands.
- **Do not check closed beads** — closed beads are historical record, not live
  conflicts.
- **Do not check beads in a different rig** unless the fix surface explicitly
  crosses rigs (e.g., a city-level config change that affects all rigs).

---

## Use 2 — POLICY-beads.md amendment path (PP1.4)

To add or modify a rule in `POLICY-beads.md`:

1. **Identify the pillar** (BP1–BP9) or propose a new pillar.
2. **Draft the amendment** — state the rule, its rationale, and how
   `check-math-bead-hygiene` should detect violations.
3. **File a bead** for the amendment:
   ```bash
   bd create "POLICY-beads amendment: <short description>" --type task \
     -d "Pillar: BP<N>\nRule: <draft>\nRationale: <why>\nHygiene check: <how to detect>"
   ```
4. **Present to Taylor** via `present-it` before editing the file.
5. On Taylor approval, edit `~/repos/gascity-packs/mathcity/POLICY-beads.md`
   via the repo-side landing agent and push through the PR pipeline.

---

## Cross-references

- **[[math-city-work]]** — the dispatch skill this gates; redundancy check is
  Step 0 of any new-bead-then-sling flow
- **[[xkcd-927]]** — semantic overlap detection (this skill operationalizes
  xkcd-927 for the dispatch queue specifically)
- **[[bead-flight-precheck]]** — the post-creation pre-sling gate (P0–P9);
  this skill runs BEFORE bead creation, that skill runs AFTER
- **[[new-math-bead-policy]]** — the bead-creation skill for math research beads;
  both skills compose: run this first (redundancy check), then new-math-bead-policy
  (format + lifecycle metadata)
- **[[check-math-bead-hygiene]]** — the hygiene auditor that fires if a bead is
  created without running these checks
- `~/repos/gascity-packs/mathcity/POLICY-beads.md` — the rule file this skill
  governs for amendments (PP1.4)

## Versioning

- **v1.0** (2026-07-19): initial pre-dispatch redundancy gate + PP1.4 amendment
  path. Filed per Taylor Q19 directive: "pre-hook that checks for redundancy in
  the set of all beads currently written for dispatch before creating new beads
  that are to be dispatched for math-city-work."
