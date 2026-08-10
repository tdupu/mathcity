---
name: check-zero
description: Wheel-check — before building anything, survey what already exists that could be used instead. Surfaces existing gascity formulas/skills/orders, prior beads, code in this project, Magma intrinsics, math databases (LMFDB, Stacks), Python packages, and known theorems that bear on the problem. Use when the user says "check-wheel", "check-zero", "are we reinventing the wheel", "what already exists for this", "is this already done", "what can we use", "are we making this harder than it needs to be", "check for existing solutions", or "ZFC wheel check". Reports found resources vs. genuine gaps. Recommended model: Sonnet.
---

# check-zero

Survey what already exists before building from scratch. The goal: zero
unnecessary new work. If something exists, use it. If nothing exists,
confirm that before committing to building it.

## When to run this

- Before writing a new formula, skill, order, or workflow
- Before implementing math code when a Magma intrinsic or LMFDB query might suffice
- When a brief or plan description feels over-complicated
- When someone says "we need to build X" — check first

## Inputs

One of:
- A brief, plan, or bead description (paste inline or give a bead ID: `bd show <id>`)
- A proposed approach in plain text
- A task description

## Step 1 — Extract the core problem

State the essential goal in one sentence, stripped of all implementation detail:

> "We need to [do/compute/check X] given [inputs Y], producing [output Z]."

If the goal requires more than one sentence to state, it may have multiple
sub-problems — check each one independently.

## Step 2 — Check gascity substrate

Before building a new formula, skill, or order, search for existing ones:

```bash
gc formula list 2>/dev/null
gc order list 2>/dev/null
ls <city-root>/.claude/skills/
ls <repos-root>/agent-skills/skills/ 2>/dev/null
ls <mathcity-pack-root>/skills/ 2>/dev/null
ls <mathcity-pack-root>/subdomains/*/skills/ 2>/dev/null
ls <gascity-pack-root>/skills/ 2>/dev/null
```

Filter by keyword:
```bash
gc formula list 2>/dev/null | grep -i "<keyword>"
ls <city-root>/.claude/skills/ | grep -i "<keyword>"
```

Also check if the task is already an order (periodic job) or formula step:
```bash
gc order list 2>/dev/null | grep -i "<keyword>"
gc formula list 2>/dev/null | grep -i "<keyword>"
```

## Step 3 — Check prior beads and closed work

Search for beads that already tracked this problem (may have been solved
and closed, or have notes about prior attempts):

```bash
# Search in the relevant rig and globally
cd <city-root>/hecke && bd search "<keyword>" 2>/dev/null
cd <city-root>/gascity-packs && bd search "<keyword>" 2>/dev/null
cd <city-root> && bd search "<keyword>" 2>/dev/null
```

Also worth checking for closed beads on the same topic:
```bash
bd list --all | grep -i "<keyword>"
```

## Step 4 — Check existing code in this project

Before writing new code, search what's already in the repos:

```bash
# Magma scripts
find <repos-root>/hecke/magma -name "*.mag" | xargs grep -li "<keyword>" 2>/dev/null

# Shell/make scripts
find <repos-root>/hecke -name "*.sh" -o -name "Makefile" | xargs grep -li "<keyword>" 2>/dev/null

# Python scripts
find <repos-root> -name "*.py" | xargs grep -li "<keyword>" 2>/dev/null

# One-off scripts (often contain prior attempts at hard problems)
ls <repos-root>/hecke/magma/make/one-offs/ 2>/dev/null | grep -i "<keyword>"

# gascity-packs scripts and configs
find <repos-root>/gascity-packs -name "*.sh" -o -name "*.toml" | xargs grep -li "<keyword>" 2>/dev/null
```

## Step 5 — Check Magma intrinsics

Before writing a Magma function, check if a built-in does it:

Think through these areas:
- **Arithmetic**: `Factorization`, `IsPrime`, `Valuation`, `CRT`, `XGCD`
- **Algebra**: `IsIsomorphic`, `MaximalOrder`, `UnitGroup`, `ClassGroup`, `Norm`, `Trace`
- **Quaternion algebras**: `QuaternionAlgebra`, `MaximalOrder`, `Generators`, `NormForm`, `IsRamified`
- **Hecke**: `HeckeOperator`, `NewForms`, `ModularSymbols`, `CuspForms`
- **Lattices**: `LLL`, `ShortestVectors`, `CosetEnum`
- **Number fields**: `NumberField`, `RingOfIntegers`, `Discriminant`, `Signature`
- **Groups**: `NormalSubgroups`, `MaximalSubgroups`, `DerivedGroup`, `AbelianQuotient`
- **Elliptic curves**: `EllipticCurve`, `Rank`, `TorsionSubgroup`, `MordellWeilGroup`

If the problem is in one of these areas, check the Magma handbook before implementing.

## Step 6 — Check mathematical databases

For math research: check if the answer is already computed.

**LMFDB** (via MCP):
```
mcp__lmfdb__search_knowls("<keyword>")  — definitions, documentation
mcp__lmfdb__list_tables()               — find the right table
mcp__lmfdb__describe_table("<table>")   — schema
mcp__lmfdb__run_sql("SELECT ...")       — query for specific data
```

Useful LMFDB tables: `ec_curvedata`, `nf_fields`, `mf_newforms`, `g2c_curves`,
`lfunc_instances`, `gps_groups`, `av_fqisog`

**Stacks Project** (algebraic geometry and commutative algebra):
```
mcp__stacks__search_stacks("<keyword>")  — find relevant tags
mcp__stacks__get_tag("<tag>")            — get theorem/definition
```

**Standard references to check:**
- Is this a standard exercise (Serre, Neukirch, Diamond-Shurman, Cassels-Fröhlich)?
- Is this a classical algorithm (LLL, Cornacchia, Tonelli-Shanks, Baby-step-giant-step)?
- Is this a known theorem with a name? Check for it.

## Step 7 — Check Python ecosystem

Before writing Python:
- `sagemath` — enormous overlap with Magma; may already have what you need
- `cypari2` / `pari` — number theory
- `python-flint` — fast number theory
- `sympy` — symbolic math, polynomial rings, modular arithmetic
- `networkx` — graph theory
- `numpy` / `scipy` — numerical computation
- Standard library: `itertools`, `functools`, `math`, `decimal`

## Step 8 — Simplicity gut-check

Ask explicitly:

1. **What's the dumbest solution that works?** Could this be a 3-line shell
   script instead of a formula? A single Dolt query instead of a pipeline?
2. **What's the throwaway cost if we get it wrong?** Higher cost = more reason
   to verify existing solutions exist before building.
3. **Is the complexity in the problem or in the proposed solution?** If the
   proposed solution is more complex than the problem statement, it's
   probably over-engineered.
4. **Does a `gc` or `bd` built-in already handle this?**
   - `gc doctor` — system health diagnostics
   - `bd ready` — next available work
   - `bd search` — content search
   - `bd show` — bead detail
   - `gc session list` — fleet state
   Many operational needs are already met by CLI builtins.

## Step 9 — Output

Produce a concise structured report:

---

**check-zero: `<one-sentence problem statement>`**

**Found (use these)**

| Category | Resource | Notes |
|---|---|---|
| Formula | `build-basic-briefed` | handles X already |
| Bead | `gsp-abc` (closed) | prior attempt; result: Y |
| Code | `hecke/magma/make/one-offs/foo.mag` | does Z |
| LMFDB | `ec_curvedata.conductor` | precomputed for rank ≤ 3 |
| Magma | `HeckeOperator(M, n)` | computes this directly |
| Theorem | Hensel's Lemma (Neukirch I.2.3) | handles the lifting step |

**Gaps (still need to build)**

| Gap | Complexity | Notes |
|---|---|---|
| X | trivial / small / medium / large | no existing solution found |

**Recommendation**

`[Use <existing> for <sub-problem>. Build <gap> from scratch. OR: No build needed — use <existing> directly. OR: Re-scope: the problem as stated is harder than needed; simplify to <simpler formulation>.]`

---

If nothing relevant is found, say explicitly:
> "No existing solutions found for this problem. The proposed approach appears non-redundant. Proceed."

## What this skill does NOT do

- Does not evaluate whether existing solutions are good enough (reports only — judgment is the human's)
- Does not test or run existing code
- Does not search the internet (use a web search separately if needed)
- Does not replace `/mathcity.work` or brief dispatch
- Does not make the implementation decision
