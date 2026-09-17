# research-SOH — the literature-review recipe

"Research in the sense of the humanities": what is known, what is open,
delivered as a report. A composed workflow over existing skills — no
new machinery (design ADR 0002). Loaded by using-mathpowers when the
literature-review predicate fires.

## Recipe

1. **Frame.** One paragraph: the question, the objects, what would
   count as an answer. Unclear → grill-with-docs, not guessing (D5).
2. **Wheel check** (only if building something is contemplated):
   `check-zero`.
3. **Sweep, in parallel, as fits the question:** `search-arxiv`,
   `search-stacks`, `search-scholar`, `search-mathlib` (lookup only —
   formalization is a non-goal), `search-lmfdb` (for objects/data);
   `find-the-technique` when the question is method-shaped ("how does
   one usually prove things like this").
4. **Deep synthesis:** `astra-dump` with the framed question and the
   sweep's leads — the dated scratch dump triple is the deliverable
   container; claims split per astra-dump's contract.
5. **Verify what the answer rests on:** every load-bearing citation in
   the report goes through `track-down-reference` (opened source,
   pinpoint) before anyone cites it onward. Unverified leads are
   labeled as such, never silently trusted.
6. **Ledger:** rows for claims worth tracking (`imported` with the
   verification as evidence; `conjectural` for open items), per
   `subdomains/repo-docs/LEDGER.md`.

## Boundaries

- Output is scratch + ledger; NOTHING enters a `.tex` from here —
  exposition goes through `create-exposition` → the writers, each with
  its gates.
- Notes-tier self-containedness (ST6) applies downstream: once a source
  is found and opened, the eventual write-up includes the proof with
  pinpoint provenance, not a bare citation.
- A survey that finds a contradiction with the repo's recorded claims
  routes it through `contradiction-check` — a literature result never
  silently supersedes a project claim.
