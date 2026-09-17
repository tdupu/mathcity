# PROVERS.md — harness-conditional prover/finder backend

Parent: [README.md](./README.md). Design ADR 0005: no leaf
hard-requires fable; astra is the degradation path everywhere. Every
leaf that dispatches heavy proving/finding work cites this file
instead of naming a backend inline.

## The branch

| Harness | Backend | Contract |
| --- | --- | --- |
| Claude Code (fable/opus/sonnet available) | `fable-prompt` → `execute-fable-package` → `harvest-fable-package` | the fable package's own artifact contract |
| Codex or any harness without fable access | `astra-dump` (primary model `gpt-6-astra`) | dated scratch dump: `report.md` + `ai-usage.md` + `tokens.md` |

Detection is observable, not guessed: a Claude harness lists the three
fable skills in its available-skills set; if they are absent or their
invocation errors, use the astra path. Record WHICH backend ran (exact
model strings) in the dump's `ai-usage.md` — never label a run "fable"
or "astra" without runtime confirmation (astra-dump's own provenance
rule).

## Output discipline (both paths)

- Everything lands in `scratch/` (dated dump dir); never a `.tex`.
- Claims in `report.md` carry the five-way status taxonomy
  (proved / conditional / computational / conjectural / imported) and
  become ledger rows (`subdomains/repo-docs/LEDGER.md`).
- A produced proof is NOT promotable until its recorded `doubt` run
  exists (ledger `doubt` column) and `contradiction-check` passes —
  the consuming writer enforces both (WRITERS.md preamble).
