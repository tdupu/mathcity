# PROVERS.md — harness-conditional prover backend

Parent: [README.md](./README.md). ADR 0005: no leaf hard-requires
fable; frontier-dump is the degradation path. Heavy proving/finding
dispatch cites this file, never a backend inline.

## The branch

| Harness | Backend | Contract |
| --- | --- | --- |
| Claude (fable available) | `fable-prompt` → `execute-fable-package` → `harvest-fable-package` | the fable package's own contract |
| No fable access | `frontier-dump` (best available frontier model, decided at run time — never hardcoded) | dump triple: `report.md` + `ai-usage.md` + `tokens.md` |

Detect observably: fable skills listed → fable; absent or erroring →
frontier-dump. `ai-usage.md` records WHICH backend ran and WHICH
concrete model it actually used (exact model strings); never label a
run without runtime confirmation.

## Output discipline

- frontier-dump lands the dated scratch dump triple natively; the
  fable pipeline writes its own package per its contract, and the
  CONSUMING LEAF normalizes it into the triple (proved→proved,
  sketched→conditional, cited→imported, conjectural→conjectural,
  refutations→refuted). The dump is the uniform ledger-facing contract
  on every path; no dispatch, no triple owed.
- Never a `.tex`. `report.md` claims carry frontier-dump's five-way
  taxonomy; ledger rows are six-way (`refuted` enters at harvest —
  `subdomains/repo-docs/LEDGER.md`).
- A proof is NOT promotable until its recorded `doubt` run exists
  (ledger `doubt` column) and `contradiction-check` passes — the
  consuming writer enforces both (WRITERS.md preamble).
