# ADR 0001 — Always full-form briefs, and the two-catch model

Date: 2026-08-24 · Status: accepted (Taylor, in-session ruling, S51 grilling)

## Context

The #208 p3 composer rebuild made typed decision briefs compose the present-it
full form (§1–§7, Decision-at-Top). The corpus does not look like that (measured
2026-08-19: of 25 pending hecke briefs, 9 had no headings, none had all seven),
and `mctl_dashboard/screens/brief.py` was built to tolerate that reality
(preserve document order, render unmapped sections, never draw absent sections
as empty slots). Meanwhile `catch-no-brainer` and `present-it --compact` carry a
second, compact brief form. The question: is §1–§7 a per-type convention, a
universal gate, or a render-only shape — and where does nonconformance get
caught?

## Decision

1. **Every brief is full-form §1–§7. The compact form is retired.** There is
   one brief shape. "I never liked the compact ones." Producers of every brief
   class (decision, commission, result, plan) must compose the full form; the
   composer's `### Gate Evidence` under §7 satisfies the existing structural
   rule.

2. **The prototype/visual system is a SPEC on the backend, not a mirror of the
   corpus.** The dashboard is deliberately a constraint that forces fields and
   sections into existence. `brief.py`'s adapt-to-reality rules are a
   transitional accommodation for the legacy corpus, not the architecture.
   (Constraint CONTENT stays negotiable — "this doesn't mean I didn't get some
   of the constraints wrong" — the mechanism is not.)

3. **Nonconformance is caught by the two-catch model** (Taylor's words,
   glossary-canonical):
   - **Catch #1 — at the stack, by the adjudicator.** He sees a brief, the
     decision is obvious, he clicks a verdict with a reason and flags "I should
     never see something like this again" (`no_brainer=true`). These verdicts
     ACCUMULATE; when a pattern accumulates, a NEW GATE is minted from it.
   - **Catch #2 — at a gate.** A brief failing an existing gate is caught at a
     known failure point and SENT BACK FOR EXTRA WORK (revise-return) — never
     auto-rejected, never escalated to the adjudicator.

4. **The full-form section gate is hereby justified by catch-#1 evidence**: six
   identical form-revises on 2026-08-23/24 (mc-bavv, mc-5ncp, mc-bmmr, mc-bj2n,
   mc-diuc, mc-ti9j — same reason, no_brainer=true). Minting it means:
   `required-sections.toml` grows the seven `§N` sections for ALL briefs;
   failure routes to revise-return with the missing sections named.

   **Precedent (correction, Taylor 2026-08-24): this loop is ESTABLISHED, not
   new.** Existing gates were minted the same way — #169/`06d13a6` (body
   structure validation, after #96 measured the pile auto-reject drain 5→0),
   MOPT001/MOPT002 (from Taylor's live S50 dashboard complaints), MISS005
   (from his mc-60j ruling, later enforced against his own re-target). The
   commits are the record; tonight is one more iteration.

5. **Legacy corpus GRANDFATHERED** (Taylor, Q4): the ~170 pre-gate pending
   briefs (hecke 45, hq 107, gascity-packs 16) render as legacy and are
   adjudicable as-is. The full-form gate binds NEW deposits and anything
   re-entering the pile via revise-return. A deliberate triage sweep may
   upgrade the backlog later, batched, after the producers' full-form passes
   land. Never a mass send-back against old-shape producers (gsp-12rf churn
   shape).

## Consequences

- `catch-no-brainer`'s compact-eligibility signal and `present-it --compact`
  are retired surfaces (compact classification ≠ compact FORM; the no-brainer
  FLAG on verdicts survives — it is catch #1's accumulator).
- Every brief producer (commission-work-briefed, simple-work-briefed,
  build-basic-briefed terminal, brief-prep skill) needs a full-form pass;
  until each lands, its briefs will be caught at the new gate and
  revise-returned — that churn is the mechanism working, not a bug wave.
- `brief.py`'s three reality-rules stay as legacy-corpus handling but stop
  being load-bearing for NEW briefs; the briefs-visual port builds to the spec.
- Open (not decided here): disposition of the ~170 legacy pending briefs
  (hecke 45, hq 107, gsp 16) under the new gate.

## Alternatives considered

- Per-type section registry (proposed in-session): rejected — one form for all.
- Renderer-adapts-forever (brief.py's docstring position): rejected as
  architecture; kept only as legacy accommodation.
- Auto-reject on gate failure: rejected — destroys work; send-back converges.
