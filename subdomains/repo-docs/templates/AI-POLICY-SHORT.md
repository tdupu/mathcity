# AI-POLICY-SHORT.md — the briefing

<!-- TEMPLATE (mathcity-repo-docs). Companion to AI-POLICY.md, which is the
     contract. This file is a scannable index, never a second source of
     truth: every line carries its rule number, and any conflict is resolved
     in favour of AI-POLICY.md. Amended alongside it by new-repo-ai-policy. -->

| Field | Value |
| --- | --- |
| Indexes | `AI-POLICY.md` as of Change Log `<YYYY-MM-DD>` |
| Status | mirrors `AI-POLICY.md` |
| Amended by | `new-repo-ai-policy`, in the same amendment as the contract |

The rules in one screen. `AI-POLICY.md` governs; this is the index. When the
stamp above lags the contract's newest Change Log row, this file is stale and
is not to be relied on. Floors (never weakened): AI5, AI6, AI9, AI11, AI15,
AI16, AI20.

## DO

| Do this | Rule |
| --- | --- |
| Name the model **and** the harness, with a date — plus reasoning-effort or temperature where exposed | AI1 |
| Give every tool — CAS, language, library, database, build tool, AI product **and provider** — a BibTeX entry and a pinpoint citation | AI2 |
| Cite skills and workflow packs to their public source with a hyperlinked locator, pinned to the version used | AI3 |
| Declare each AI-result, naming the model, harness, and skill that produced it — drafted prose included | AI4 |
| Run a literature search on every AI-result; report hits with locators **and** a method comparison, or say it came back empty; say when the technique was simply available; state unresolved attribution rather than omitting it | AI5 |
| Say what was on the table before the search, and whether it was human- or AI-generated | AI7 |
| Explain how the result was derived, not just that a model produced it | AI8 |
| State that responsibility stays with the human authors, and make sure every coauthor assents | AI9 |
| Verify every AI-surfaced reference against the real source before it enters the `.bib` | AI11 |
| Put the unnumbered **Software and AI assistance** subsection at the end of the introduction — else after the opening overview, else first before the first numbered section; add the abstract sentence iff the document has an abstract | AI12 |
| Re-derive AI-originated computations in a real system and report them as that system's output | AI13 |
| Record refutation-only sessions too, and carry the refutation into the document | AI14 |
| Keep one master `ai/ai-usage.md` and one `ai/tokens.md` — written only by `update-ai-usage` / `update-tokens` — with the evidence behind them retained at a named location | AI15 |
| Price tokens per task: counts, model, rates, cost, task date, rate as-of date | AI16 |
| Give every record a task identifier — ISO datetime with offset, `__skill__slug` — minted once by `update-ai-usage`, joining `ai-usage.md` to `tokens.md` | AI20 |
| Clear `latex-ai-statement` on the exact submitted revision, every DEFER resolved or accepted by a named human, the audit retained with the submission — an ADVISORY verdict does not clear the gate | AI19 |

## DON'T

| Never do this | Rule |
| --- | --- |
| Put a model `\cite` in a sentence making a mathematical assertion, or list a model as an author — naming it as the **origin** of an AI-result, in a provenance or methods sentence, is required | AI6 |
| Credit AI for a result with no derivation account | AI8 |
| Ship a claim you could not present and defend in an expert talk unaided | AI10 |
| Pass agent review off as human verification | AI10 |
| Let an unverified AI-proposed reference into the bibliography | AI11 |
| Quote a model's computation in place of a real system run | AI13 |
| Delete a wrong claim together with its refutation, or leave a refutation-only session unrecorded; negatives go **before** the positives, each naming the expectation it corrects | AI14 |
| Invent or silently estimate a token count, a rate, or a cost | AI16 |
| Send referee reports or submissions under review to a third-party model — and where a step is skipped for this reason, record what was withheld | AI17 |
| Consolidate an index as if it were a record, or resolve an unlabelled file by guessing — an index declares itself on its first line, an ambiguous one is reported | AI20 |
| Leave prompt residue in the manuscript, or point readers at files they will not receive | AI18 |
