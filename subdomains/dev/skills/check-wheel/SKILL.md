---
name: check-wheel
description: Gate a plan, implementation, or data artifact against the "no reinventing the wheel" invariant. Determines if an existing codebase, formula, skill, or resource already does what is being proposed; when reinvention is detected, produces a hygienic import recommendation via check-plan-hygiene. Use when the user says "check-wheel", "check wheel", "is this reinventing the wheel", "does this already exist", "should we import instead of build", "check for existing solutions before building", or when a plan description feels over-complicated for the stated goal.
---

# check-wheel

Gate any plan, implementation, or data artifact against the "no reinventing the wheel" invariant: determine whether something that already exists covers the proposed work, and if so, produce the hygienic path to use it instead.

**This skill is a composition gate** — it chains check-zero (detection) with check-plan-hygiene (hygiene recommendation) into one focused verdict. check-zero alone surveys what exists; check-wheel additionally decides whether the specific artifact constitutes a wheel reinvention and what to do about it.

## When to use

- "Check-wheel this plan before we start"
- "Is this already done somewhere?"
- "Should we just import X instead of building it?"
- When a plan description feels over-complicated for the stated goal
- Before committing to a new skill, formula, Magma function, or workflow
- After check-zero returns findings — to turn the survey into a decision

## Inputs

One of:
- A plan document or bead ID (`bd show <id>`)
- A code implementation or diff
- A data artifact or task description
- A proposed approach in plain text

## Step 1 — State the core object

Extract what is being proposed in one sentence:

> "We are proposing to build/create/implement [X] which [does/computes/checks Y] given [inputs Z]."

If the goal contains multiple sub-problems, check each independently.

## Step 2 — Survey existing resources

For each layer, probe with the relevant tools. Substitute the actual keyword for `<keyword>`:

### Layer 1 — gascity substrate (formulas, skills, orders)

```bash
gc formula list 2>/dev/null | grep -i "<keyword>"
gc order list 2>/dev/null | grep -i "<keyword>"
ls <city-root>/.claude/skills/ | grep -i "<keyword>"
ls <repos-root>/agent-skills/skills/ 2>/dev/null | grep -i "<keyword>"
ls <mathcity-pack-root>/skills/ 2>/dev/null | grep -i "<keyword>"
ls <mathcity-pack-root>/subdomains/*/skills/ 2>/dev/null | grep -i "<keyword>"
```

### Layer 2 — prior beads (solved and closed)

```bash
bd search "<keyword>" 2>/dev/null
bd list --all 2>/dev/null | grep -i "<keyword>"
```

### Layer 3 — existing code in project repos

```bash
find <repos-root> -name "*.mag" -o -name "*.py" -o -name "*.sh" | xargs grep -li "<keyword>" 2>/dev/null
find <repos-root>/gascity-packs -name "*.toml" | xargs grep -li "<keyword>" 2>/dev/null
```

### Layer 4 — Magma intrinsics and classical algorithms

Think through relevant built-in areas: arithmetic, algebra, quaternion algebras, hecke operators, lattices, number fields, groups, elliptic curves. Check the Magma handbook if the proposed computation falls in any of these.

### Layer 5 — Mathematical databases

- LMFDB (`mcp__lmfdb__search_knowls("<keyword>")`) — precomputed tables
- Stacks Project (`mcp__stacks__search_stacks("<keyword>")`) — theorems and algebra
- Standard references (Serre, Neukirch, Diamond-Shurman, Cassels-Fröhlich)

### Layer 6 — Python/SageMath ecosystem

Check sagemath, pari/cypari2, sympy, numpy/scipy, and the standard library before implementing in Python.

## Step 3 — Wheel determination

For each resource found, assess coverage:

| Resource | Location | Coverage |
|----------|----------|----------|
| (found items) | (path/package) | covers all / partial / none |

Then assign one of:

- **NO REINVENTION** — the proposed work is genuinely new; no resource covers it
- **PARTIAL REINVENTION** — an existing resource covers part of the goal; a genuine gap remains
- **FULL REINVENTION** — an existing resource covers the entire goal; the proposed work is unnecessary

**Tie-breaking rule:** If coverage is uncertain, lean toward NO REINVENTION — false positives waste time by blocking work that should proceed. A genuine wheel reinvention should be obvious, not speculative.

## Step 4 — If PARTIAL or FULL REINVENTION: hygienic import recommendation

When reinvention is detected, produce a concrete import recommendation. Run check-plan-hygiene on the revised plan that uses the import.

### 4a — Identify the existing resource

State exactly:
- Name and version (if versioned)
- Location (rig, pack, repo, upstream URL, package name)
- Which part of the goal it covers
- What (if anything) remains as a genuine gap

### 4b — Hygiene classification

| Case | Import method |
|------|---------------|
| Resource is in `mathcity/` or an owned rig | Use directly — no import step needed |
| Resource is in another pack (`gascity/`, `pr-pipeline/`) | Import via `pack.toml` + `gc import add` (never copy-paste) |
| Resource is upstream code (`gastownhall/gascity-packs`) | File a PR via pr-pipeline; do not fork-patch |
| Resource is a Python/Magma package | Add as a declared dependency in the project; document the dep |

Flag these hygiene concerns if present:
- **P1.9** — adoption without dedup (existing copy in a repo must become a symlink or be removed)
- **P1.10** — privacy scrub needed (hostname, key, or schema name in pack content)
- **P2.3** — cross-pack composition by copy-paste instead of `pack.toml` import
- **P1.13** — README table update required if the adopted resource adds/renames a skill

### 4c — Revised plan

State the revised approach in plain language:

```
Instead of building <X> from scratch:
  Use <existing-resource> for <sub-goal>.
  [Build <remaining-gap> as new work.]

Hygiene steps required:
  1. <import method or dedup step>
  2. Run /check-plan-hygiene on the revised plan before proceeding.
```

## Step 5 — Output

```
check-wheel: <core object in one sentence>

Verdict: NO REINVENTION | PARTIAL REINVENTION | FULL REINVENTION

Resources surveyed:
  Layer 1 (gascity) — <found / nothing relevant>
  Layer 2 (beads)   — <found / nothing relevant>
  Layer 3 (code)    — <found / nothing relevant>
  Layer 4 (Magma)   — <found / nothing relevant>
  Layer 5 (math DB) — <found / nothing relevant>
  Layer 6 (Python)  — <found / nothing relevant>

Coverage:
  <resource name> — <covers: all / partial / none> — <one-line note>

Recommendation:
  [Proceed — no wheel found. The proposed approach is non-redundant.
   OR
   Import <X> from <location> instead of building from scratch.
   Remaining gap (build new): <gap description or "none">
   Hygiene flags: <P-rule violations or "none">
   Next step: /check-plan-hygiene on the revised plan.
   OR
   Eliminate: <X> already exists as <Y>. Use <Y> directly — no build needed.]
```

## What this skill does NOT do

- Does not make the final build/import decision — that is the human adjudicator's call
- Does not run tests or execute code
- Does not modify any files — reports only
- Does not replace `/check-plan-hygiene` (which audits all 4 policy pillars); check-wheel is only the "does this already exist?" gate followed by the import path when yes
- Does not replace `/check-zero` for general open-ended resource surveys; this skill targets a specific artifact
- Does not search the internet (use a web search tool separately if needed)
- Does not audit the CURRENT build for hygiene violations (that is `/check-build-hygiene`)

## Composes with

- **`/check-zero`** — upstream survey skill this gate relies on for Layer 1–6 detection
- **`/check-plan-hygiene`** — downstream gate that verifies the revised (import-based) plan satisfies all 4 policy pillars
- **`/check-build-hygiene`** — sibling gate that audits the live install (not a plan)
