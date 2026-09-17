---
name: create-exposition
description: Gather a topic's definitions and theorems into a LINKED markdown spec in scratch — per item: statement, verified source, dependency links — the staging artifact writers move into notes.tex. Use when the user says "create an exposition spec", "gather the background on X", "build the linked spec". NOT for writing the tex (write-* / explain-experiment) or open-question research (the research-SOH recipe: astra-dump + the search-* skills).
---

# create-exposition

## Procedure

1. Scope: topic and audience (per subdomains/repo-docs/RESOLUTION.md
   → the repo's STYLE.md variables).
2. Collect the item graph: definitions, theorems, examples needed,
   each a spec entry: statement (verbatim or faithfully normalized),
   source — verified via track-down-reference for every import
   (opened source, pinpoint) — and [[wiki-style]] dependency links
   between entries (mechanism 10's antidote).
3. Heavy gathering may dispatch per `subdomains/proof-assist/PROVERS.md`; output lands in the
   spec whatever the backend.
4. Deliver `scratch/<date>-exposition-<slug>/spec.md` always; the
   dump triple only when a Step-3 dispatch happened;
   ledger rows for imported claims (status `imported`, evidence = the
   verification).
5. Hand off: the spec feeds write-definition / write-proposition /
   write-remark per item, each via its own gates.

## Red flags

| Thought | Reality |
|---|---|
| "I know this theorem, no need to open it" | Unopened sources are mechanism 7. Verify each import. |
| "Write it straight into notes.tex, skip the spec" | The spec IS the review surface. Writers come second. |
