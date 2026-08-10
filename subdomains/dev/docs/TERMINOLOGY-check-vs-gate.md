# Terminology: check vs gate (native gascity)

**Date:** 2026-07-21
**Status:** Authoritative — supersedes the "GC reserves 'gate' for `[steps.check]`"
claim in `HURDLES-RENAME-PLAN-2026-07-08.md` and `EXPANDED-STRUCTURE-DRAFT-2026-07-08.md`.
**Evidence:** gascity source (`<repos-root>/gascity/internal/formula/types.go`) + cross-pack
survey (gascity, ops, bmad, gstack, pr-pipeline, compound-engineering), 2026-07-21.

## Correction

`HURDLES-RENAME-PLAN-2026-07-08.md` states: *"GC uses 'gate' for `[steps.check]`
blocks in formula TOML."* **This is incorrect.** In the gascity source the
`[steps.check]` block's canonical public spelling is **`check`**, not "gate."
The gate→hurdle rename was built on this misreading and is **not needed** — the
mathcity brief-policy terms are already native. Do not rename "gate" → "hurdle."

## The two native concepts

### `check` — the mechanism
A `[steps.check]` block: a mechanical, executable pass/fail validation on a step,
with `mode = "exec"`, a script `path`, `timeout`, and bounded `max_attempts`.
Check scripts live in `<pack>/assets/scripts/checks/`. This is the substrate that
enforces a validation. Confirmed native across the source and every methodology
pack (gascity, bmad, gstack, pr-pipeline, compound-engineering).

### `gate` — the control-flow *role*
A checkpoint that governs whether/how execution proceeds. A gate is **realized
through** a check or an explicit graph step — per gascity requirement
**GC-METH-BR-029**: *"WHEN a gate controls execution, THE gate SHALL live in
formula checks or explicit graph steps; prompt rubrics SHALL be limited to
qualitative guidance."* Native "gate" appears in three flavors:

- **mechanical gate** — ops `kind = "gate"` formulas (`iteration-must-be-approving`,
  `wall-time-gate`): deterministic reject / terminate on a condition.
- **human-approval gate** — `human-gate-*` steps, `post_mode = "human_gate"`
  (passive-wait + mail for a human decision).
- **routing gate** — `-gate`-suffixed selector steps that branch on metadata.

(Separately, the source has a narrow `[steps.gate]` primitive for **async wait
conditions** — type/id/timeout. Distinct from the checkpoint-role sense above;
rarely used in packs.)

## How this maps to the mathcity brief-policy registry (G1–G16)

The registry entries **are gates** (policy control-flow checkpoints a brief must
clear) — the same sense as ops `kind = "gate"`. Each is **enforced by a check**
(the `check-*.sh` scripts already under `assets/scripts/checks/`). So mathcity is
already using both native words correctly: **gate** = the checkpoint, **check** =
the enforcing mechanism. The registry `kind` column refines the checkpoint:

| `kind` | What it is | Native reading |
|---|---|---|
| `mechanical` | pure exec pass/fail (G1 test-evidence, G13 stale-claim, G14 test-execution) | a **check** doing the enforcement; the registry row is the **gate** it satisfies |
| `stop` | fail-closed, needs human sign-off (G5 server-touching, G12) | a **human-approval gate** |
| `manual` | needs a specific human artifact (G6 latex approval) | a **human-approval gate** (artifact-satisfied) |
| `review` | routed to a reviewer agent; the verdict is the evidence (G2, G4, G9) | a **gate** whose check is a judgment step, not a script |

## Rule of thumb

- Writing/naming an exec validation script → it's a **check** (`checks/…sh`,
  `[steps.check]`).
- Referring to the policy checkpoint a brief must clear → it's a **gate**.
- Never call either a "hurdle" (non-native coinage) or a "step" (collides with
  `[[steps]]`, the core formula primitive).
