---
name: fill-in-prototype
description: Work a prototype's gaps: for each conjectural item in a skeleton or spec, dispatch a prover-level attempt at proof or counterexample; harvest results to ai/ and the ledger (doubt run before any promotion); successful items become write-proposition candidates. Use when the user says "fill in the prototype", "attack the skeleton", "work the conjectures". NOT for generating new candidates (find-proposition) or writing results into tex (write-proposition, gated).
---

# fill-in-prototype

## Procedure

1. Enumerate the prototype's open items (conjecture envs in the
   canonical file's tagged skeleton regions, or spec entries), each
   with its ledger row; report the count.
2. Per item, dispatch per `subdomains/proof-assist/PROVERS.md`: mandate BOTH directions — prove
   it and hunt a counterexample; partials (special cases, reductions)
   are results, labeled as such.
3. Harvest per backend contract into
   `ai/<date>-fill-in-<slug>/`; update ledger rows: status
   transitions (`conjectural` → `proved` / `conditional` /
   `computational` / `refuted`, counterexample path in evidence),
   evidence paths, depends-on edges.
4. Refuted or contradicted items: route through contradiction-check
   against anything already recorded (silent supersession prohibited —
   mechanism 2); the tex skeleton is NOT edited here.
5. Per proved item: recommend a doubt run (required before promotion)
   and hand to write-proposition — dispatch neither yourself.

## Red flags

| Thought | Reality |
|---|---|
| "Proved by the backend = done" | Backend output is a draft. Doubt run, then the writer's gates. |
| "Flip the conjecture env to proposition while here" | Tex edits belong to the writers, gated. |
