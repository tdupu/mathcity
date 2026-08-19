repo: tdupu/mathcity
branch: main
path: subdomains/dev/docs/plans/mcp

## Last sync
date: 2026-08-19T18:22:19Z

### Updated in this project
- Confirmed the briefs dashboard does not exist in the repo (no HTML/CSS/JS UI files); designed it from the spec instead.
- Rebuilt every brief to the `present-it` full-form shape: 7 grill-ordered sections, Decision-at-Top invariant, compact form for no-brainers, required-gates summary.
- Added error briefs as their own auto-filed class (MC-E207 / MC-E113), blocking the brief they concern.
- Sidebar vocabulary now follows the pipeline: pile → stack, with queues as personal orderings; no-brainers shown as auto-processing.

## Screen map
| Screen | Built from |
| --- | --- |
| Brief stack table, sortable columns | `README-development.md` (mctl briefs list), `GLOSSARY.md` (unlock_count, pile, stack) |
| Brief detail, 7 sections + options | `skills/present-it/SKILL.md` (full-form template, Decision-at-Top, §4 alternatives incl. option E) |
| Compact form on no-brainers | `skills/present-it/SKILL.md` (Compact form), `skills/catch-no-brainer/SKILL.md` (compact_eligible, N5 kill-switch) |
| Error briefs + diagnostics | `MCTL-MCP-PLANNING-PROMPT.md` (failure philosophy, severity model, diagnostics fields), `subdomains/brief-system/POLICY.md` (B2.4, B3.4) |
| Pile view, gate states | `README-formulas.md` (brief-shuffle, fast-drain, producer-failure-record), `README-clerk.md` |
| Adjudication panel, effect plan | `MCTL-MCP-IMPLEMENTATION-PLAN.md` (EffectPlan, dry-run preview), `README-beads.md` (interaction_mode) |
| Trace / provenance block | `MCTL-MCP-PLANNING-PROMPT.md` (Traceability dream fields) |
| Visual style | `roed314/lmfdb` → `lmfdb/templates/style.css` (sidebar, `.ntdata` tables, knowl pattern, properties box) |
