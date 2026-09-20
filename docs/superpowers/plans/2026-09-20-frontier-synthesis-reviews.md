# Selected research synthesis: critic reports

Parent: [validation record](2026-09-20-frontier-synthesis-validation.md).

Independent read-only reports from native Codex agents. Local worktree prefixes
are replaced with relative repository paths; review conclusions and hashes are
unchanged. Each report covers one frozen file plus interface checks, not a live
execution certificate. Initial findings remain part of the history.

## frontier-dumpReview1

Section-by-section review, N=1: all 122 nonblank lines reviewed, including accounting delegates, policy references, and consumer interfaces. No edits, dispatch, or git writes.

Reviewed SHA-256, unchanged after review:
`8d64eb5db9181c73daf4419632fcce0a5e4eee93f2bee3dae1f3a71fc20174f2`

1. **BLOCKING — Required accounting contradicts the write boundary.** [Lines 50–53](https://github.com/tdupu/agent-skills/blob/main/skills/frontier-dump/SKILL.md#L50) require confirming that this workflow changed nothing outside the dump. Lines 81–85 require consolidation into repository master records. The actual delegates write [`ai/ai-usage.md`](../../../skills/update-ai-usage/SKILL.md#L31) and [`ai/tokens.md`](../../../skills/update-tokens/SKILL.md#L41), outside the dated folder. A successful run cannot satisfy both requirements. Give accounting delegates an explicit, bounded exception and make validation distinguish those writes from unauthorized changes.

2. **MAJOR — Valid research with no negative findings is rejected.** [Lines 67–69](https://github.com/tdupu/agent-skills/blob/main/skills/frontier-dump/SKILL.md#L67) declare any dump returning “only positive results” incomplete. A run can correctly establish its claims without discovering a refutation. ST11/LX11/LX12 require preserving negative findings that exist; they do not require inventing one. Permit an explicit “none found” section after checking inputs, with zero counts, while continuing to reject omitted findings.

Required references resolve; historical names and generated/caller paths were not treated as missing dependencies. The consumer route supports selected evidence, audience-aware prototypes, separate prototype and filled-presentation reviews, and integration defaulting to `notes.tex`. The leaf explicitly ends without synthesis or browser priming. The full coherence pass found the accounting conflict above.

    ---REVIEW-VERDICT---
    verdict: NEEDS-REVISION
    blocking_count: 1
    major_count: 1
    minor_count: 0
    ---ACTION-ITEMS---
    [BLOCKING] Reconcile dump-only write validation with required master-ledger consolidation using an explicit accounting exception.
    [MAJOR] Accept an explicit zero-negative-findings report when no refutations or failed expectations were found.
    ---END-REVIEW---

## fp-finder-latexReview1

Section-by-section review completed: all 217 nonblank lines of [the target](../../../subdomains/latex/skills/fp-finder-latex/SKILL.md), with no sections skipped.

SHA-256, unchanged:
`53466eb0600ce8345954ad02a038ac977ef3047d9fc41c5982784f8268bf93b4`

No actionable findings.

- **Outline acceptance:** lines 22–27 explicitly exclude named research gaps from proof verification. Lines 115–130 preserve the distinction: missing gap accounting remains blocking; properly scoped obligations do not require invented mathematical closure.
- **Presentation versus integration:** lines 28–42 and 194–198 prevent source-only approval from becoming integrated acceptance. The inspected synthesis handoff now requires full canonical WRITERS mechanics and independent review of the integrated diff, interfaces and PDF.
- **Version invalidation:** lines 40–41 and 164–178 require renewed review of changed inputs and affected dependencies while preserving historical acceptance.
- **Ordinary manuscripts:** final build/PDF requirements remain explicit. Independent review, revision authorization, finding closure, permitted imports, bounded stopping and negative-result retention remain intact.

Verified referenced resources against their actual roots and inspected the reviewer, writer, ledger, accounting and policy interfaces. Illustrative output paths were treated as future artifacts. Fixtures were inspected, not executed. No edits, dispatch or git writes.

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 0
    minor_count: 0
    ---ACTION-ITEMS---
    ---END-REVIEW---

## rapid-prototypeReview1

Section-by-section review, N=1: all 61 nonblank lines of the [frozen file](../../../subdomains/latex/skills/rapid-prototype/SKILL.md) reviewed. No actionable issues found.

Coverage:

- All four linked contracts exist and were read. Referenced writer/fill skills resolve; `make-outline` describes the merger, not a required invocation. Stable policy interfaces match the real sibling repository.
- Selection/context, audience-aware topic introduction, complete dependency outline, and theorem-first prerequisite backfill agree with the synthesis contract. Finished-paper introduction gates are not imposed on prototypes.
- Direct outline requests stop after applicable review. Authorized synthesis continues through filling, presentation review, integration, and independent integrated diff/interface/PDF checks.
- Scratch drafting excludes canonical writer execution. Integration retains full writer gates, definition discipline, attribution, tags, and ledger reconciliation.
- Unsupported claims remain explicit obligations; known refutations cannot become conjectures. Negative findings and authorized exclusions remain accounted for. The provenance and whole-file coherence passes found no conflict.

No edits, dispatch, or git operations.

SHA-256: `9ffbe9b1b552b7c6a693202d0896be79785febc511dedfe601d3d756a92e620d`

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 0
    minor_count: 0
    ---ACTION-ITEMS---
    ---END-REVIEW---

## create-expositionReview1

No actionable issues found in the [candidate](../../../subdomains/proof-assist/skills/create-exposition/SKILL.md).

SHA256: `59c949f83992e52adfa1a02b1fcea24fa242ae3d7a2e2e89477d7112e5b16290`

N=1 critic pass, section-by-section tier: all 52 nonblank lines reviewed; file matches the pasted candidate.

Coverage:

- All three relative document links resolve. Checked the named skill interfaces and LX11/LX12 against their actual definitions.
- Selection boundaries are explicit; excluded dependencies remain gaps. Partial reading cannot masquerade as complete coverage.
- Negative findings retain their corrected expectations, hypotheses, evidence and locators; omissions require individual authorized reasons.
- Direct invocation ends at the spec. Local source verification avoids accidentally invoking fresh research.
- The shared contract continues through audience/dependency-aware prototyping, theorem-first backfill where requested, separate outline and filled-presentation reviews, and integration into `notes.tex` or the declared target.
- Scratch drafting and canonical writer execution are explicitly separated. Full writer gates and independent integrated-manuscript review remain required.
- Provenance and whole-file coherence checks found no conflicting obligations or unsupported interface assumptions. Existing workflow and ledger are reused.

Static interface review only; no edits, dispatch, workflow execution or git operations.

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 0
    minor_count: 0
    ---ACTION-ITEMS---
    ---END-REVIEW---

## fill-in-prototypeReview1

N=1, section-by-section review of the full [candidate](<../../../subdomains/proof-assist/skills/fill-in-prototype/SKILL.md>): 76 nonblank lines. Matches the pasted text; SHA256 unchanged after review:

`b4382e8c52dab730b36f9b70487564fb346b5f4d3ab24d6dd9daff600d7cf488`

No actionable issues found. Coverage:

- All direct references exist; checked their actual contracts and the shared synthesis/workflow interfaces.
- Selected-source boundaries, explicit dependency gaps, retained originals, and per-finding exclusion reasons preserve negative results without silently expanding selection.
- Named-conjecture and partial requests remain scoped. Audience-aware presentation and theorem-first backfill come from the shared contract.
- Scratch drafting explicitly excludes canonical mutations/postambles; integration invokes full writer gates. Topic introductions preserve the finished-paper introduction gates.
- Prover harvesting retains evidence and failed attempts. Recorded SOUND verdicts gate promotion; missing capabilities leave explicit obligations.
- Returns continue through distinct presentation and integrated-manuscript reviews, including affected dependencies and actual PDF checks. Source acceptance cannot substitute for final acceptance.

Static review only; no edits, dispatch, git operations, or workflow execution.

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 0
    minor_count: 0
    ---ACTION-ITEMS---
    ---END-REVIEW---

## math-workflowReview1

N=1, section-by-section review: all 70 lines checked (58 nonblank). Verdict covers only the target; dependencies were read for compatibility.

Coverage: both powers and aliases reach the common workflow. `synthesis.md` owns context → audience-aware prototype → FP → fill → FP → integration. Coordinator continuity, theorem-first backfill, provenance/refutations, bounded reviews, existing authorization, and contract-controlled `notes.tex` targeting are consistent. All concrete resources directly referenced by the target exist; output paths were not treated as prerequisites.

One MINOR finding: [line 34](../../../skills/math-workflow/SKILL.md#L34) says “five-template copy,” but [init-repo-docs line 14](../../../subdomains/repo-docs/skills/init-repo-docs/SKILL.md#L14) specifies six contracts plus companion files. Replace it with “unconditional template copy.” The surrounding preservation rule remains effective.

SHA-256, unchanged:
`f9ccd29476d533572d833d4ae5a610450aac8facedb34ddf946ddabbedca83b4`

No edits, dispatch, or git writes.

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 0
    minor_count: 1
    ---ACTION-ITEMS---
    [MINOR] SKILL.md:34: Remove the stale “five-template” count; init-repo-docs now specifies six contracts plus companion files.
    ---END-REVIEW---

## using-latexpowersReview1

N=1, section-by-section review of the full [target](../../../subdomains/latex/skills/using-latexpowers/SKILL.md): 66 nonblank lines, 6,958 bytes. No actionable issue found.

Coverage:

- Verified actual referenced resources and the shared synthesis path; caller-supplied manuscript filenames were not treated as missing dependencies.
- Confirmed `using-latex` forwarding and `using-latexskills` trigger compatibility.
- Traced selected-file synthesis, combined outline/prototype, partial-request stopping points, and topic introduction versus finished-manuscript introduction gates.
- Confirmed scoped reordering preserves dependency/source links while unrelated merges remain on HOLD.
- Checked preservation of writer, doubt, ledger, policy, negative-result, and AI-accounting contracts.

Static contract review only; no edits, dispatch, or git operations. Target hash remained unchanged.

SHA256: `8e2974994ac0b9ee213d1195e3a3ded34b7d528e72140bf98238e5b67b074b2b`

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 0
    minor_count: 0
    ---ACTION-ITEMS---
    ---END-REVIEW---

## using-mathpowersReview1

N=1, full line-by-line review of [SKILL.md](../../../subdomains/proof-assist/skills/using-mathpowers/SKILL.md): 42 nonblank lines. No actionable issues found.

Verified dependencies and actual synthesis, proof, writer, and ledger interfaces. The shared coordinator preserves selected-source gathering, audience-aware introductory prototyping, separate reviews, theorem-first backfill, scoped invocations, and declared-target integration defaulting to `notes.tex`. Doubt, independent review, human data, and unintegrated evidence remain protected. Aliases preserve context; no redundant browser priming or permission restart is required. Caller placeholders were treated as such.

No edits, dispatch, or git operations. SHA256 unchanged:
`5a8de4cf8f4071e2021144e525a494e170ef4c5e2fa5861def0ea86897e8b355`

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 0
    minor_count: 0
    ---ACTION-ITEMS---
    ---END-REVIEW---

## executionReview1

N=1 critic pass, section-by-section: reviewed all 138 lines (116 nonblank) of [execution.md](../../../skills/math-workflow/references/execution.md). No sections skipped or actual issues found.

Coverage:

- Checked referenced resources and actual coordinator, synthesis, powers/alias, proof, writer, and ledger interfaces; caller-dependent destinations were treated as placeholders.
- Confirmed selected-source gathering → audience-aware introductory prototype → FP → filled review → canonical integration, defaulting to declared `notes.tex`. Theorem-first planning, prerequisite backfill, partial invocations, and coordinator reuse remain compatible, without browser priming or artificial permission restarts.
- Verified doubt and independent-review gates, changed-proof invalidation, unavailable-backend handling, truthful completion, and preservation of human content and unintegrated branch/worktree evidence.

Read-only review; no edits, dispatch, or git operations.

SHA256: `77dd229e75f06424f86ff1d402de2280c2d536fa2ab92fac8fd0d96255808321`

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 0
    minor_count: 0
    ---ACTION-ITEMS---
    ---END-REVIEW---

## synthesisReview2

Section-by-section re-review of [synthesis.md](../../../skills/math-workflow/references/synthesis.md): both MAJOR findings are resolved; no new issues found.

- Lines 67–75 explicitly require scratch-only candidate returns. Lines 92–94 reserve full writer execution and its gates for integration, preserving separate human acceptance.
- Lines 99–105 require independent acceptance of the exact integrated version, retain pending-review status until acceptance, and preserve audit limits when reusing unchanged proof reviews.
- Rechecked selection boundaries, evidence provenance, negative-result retention, theorem-first dependencies, stage-specific acceptance, target declarations, rerun behavior, and legacy preservation. These remain coherent: unresolved mathematics stays explicit, evidence survives consolidation, and no competing claim-status system is introduced.
- Referenced resources exist; the writer, ledger, and current FP contracts support these handoffs.

Verified on disk: **7,481 bytes**. SHA-256: `af054739d6cc3ddbc9b0644b4cc0440ba4d6d462adde43349a6f52c3f2fb5817`.

This verdict covers the synthesis reference only. No edits, dispatch, or git writes.

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 0
    minor_count: 0
    ---ACTION-ITEMS---
    ---END-REVIEW---


## Gate revision

Modified only:

- [frontier-dump/SKILL.md](https://github.com/tdupu/agent-skills/blob/main/skills/frontier-dump/SKILL.md): 7,896 → 7,874 bytes.
- [math-workflow/SKILL.md](../../../skills/math-workflow/SKILL.md): 4,086 → 4,081 bytes.

Both pass Rule (a), with substantive changes. No siblings, dispatch, or git operations. Transport, provenance, negative-result transfer, and consumer routing remain complete.

```text
---REVISION-SUMMARY---
items_total: 3
items_resolved: 3
items_partial: 0
items_skipped: 0
self_review: CLEAN
---RESOLUTIONS---
[RESOLVED] [BLOCKING] Reconcile dump-only write validation with required master-ledger consolidation using an explicit accounting exception. :: Aligned write restrictions and validation with required accounting-delegate consolidation into the two master ledgers, preserving unrelated entries and per-dump evidence.
[RESOLVED] [MAJOR] Accept an explicit zero-negative-findings report when no refutations or failed expectations were found. :: Accepts explicit zero findings when neither work nor inputs contain them; retains the required section and follow-up for missing or buried findings.
[RESOLVED] [MINOR] SKILL.md:34: Remove the stale “five-template” count; init-repo-docs now specifies six contracts plus companion files. :: Read the linked contract and removed only “five-”.
---END-REVISION---
```

## frontier-dumpReview2

Section-by-section review: all 121 nonblank lines of the exact [target](https://github.com/tdupu/agent-skills/blob/main/skills/frontier-dump/SKILL.md) reviewed; no sections skipped.

Both prior findings are closed:

- Lines 34–36, 50–52 and 80–84 consistently permit task-specific accounting consolidation while preserving unrelated entries and per-dump evidence.
- Lines 62–68 accept explicit zero negative findings while retaining follow-up for missing sections or omitted findings.

Checked triggering, delegation boundaries, collision handling, bounded follow-up, accounting/provenance interfaces, negative-result transfer, and completion scope. Consumer interfaces retain selected-source gathering, audience-aware prototypes, separate reviews, and declared-target integration. Referenced resources resolve; materialized consumer/delegate files match their canonical copies. Full coherence pass found no target conflicts or regressions.

Static review only; no edits, dispatch, or git execution. SHA-256 unchanged before/after:

`ab73fd7a7aaef9ad828d568747614e12ea64e7966036591ff3cc8f3267a791ce`

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 0
    minor_count: 0
    ---ACTION-ITEMS---
    ---END-REVIEW---

## math-workflowReview2

Section-by-section review: all 70 lines checked (58 nonblank). Verdict covers only [math-workflow/SKILL.md](../../../skills/math-workflow/SKILL.md).

The prior MINOR finding is closed: line 34 says “unconditional template copy.” Restoring only `five-` in the hashing pipeline reproduces the prior SHA-256 exactly, confirming the five-byte deletion is the entire change.

Coverage: all directly referenced resources exist. Read the three workflow references, routers/aliases, and relevant leaf/contracts for compatibility. Coordinator continuity, stage ownership, theorem-first backfill, provenance/refutation retention, bounded reviews, declared destinations, and authorization gates remain consistent. Full coherence pass completed; no regressions or new findings.

Current size: 4,081 bytes. SHA-256:
`a16dee7a71d0b20cc8db09487fa8cbe084018acf66321c02c6df99a172f2bbdb`

No edits, dispatch, or git operations.

    ---REVIEW-VERDICT---
    verdict: APPROVING
    blocking_count: 0
    major_count: 0
    minor_count: 0
    ---ACTION-ITEMS---
    ---END-REVIEW---


## Final tuple and mutual termination

# Driver aggregate: independent skill critics

Scope: ten instruction files across the existing eight skill roots.
Each has an independent zero-finding APPROVING report in the companion
critic report. Initial findings were resolved by strictly shrinking the
changed files and rechecking them; unchanged approvals retain exact hashes.
This is a skill-contract review, not mathematical or workflow execution proof.

- mathcity/skills/math-workflow/SKILL.md: 4081 bytes; SHA-256 a16dee7a71d0b20cc8db09487fa8cbe084018acf66321c02c6df99a172f2bbdb; APPROVING (0/0/0).
- mathcity/subdomains/latex/skills/rapid-prototype/SKILL.md: 4525 bytes; SHA-256 9ffbe9b1b552b7c6a693202d0896be79785febc511dedfe601d3d756a92e620d; APPROVING (0/0/0).
- mathcity/subdomains/proof-assist/skills/create-exposition/SKILL.md: 3758 bytes; SHA-256 59c949f83992e52adfa1a02b1fcea24fa242ae3d7a2e2e89477d7112e5b16290; APPROVING (0/0/0).
- mathcity/subdomains/proof-assist/skills/fill-in-prototype/SKILL.md: 5603 bytes; SHA-256 b4382e8c52dab730b36f9b70487564fb346b5f4d3ab24d6dd9daff600d7cf488; APPROVING (0/0/0).
- mathcity/subdomains/latex/skills/using-latexpowers/SKILL.md: 6958 bytes; SHA-256 8e2974994ac0b9ee213d1195e3a3ded34b7d528e72140bf98238e5b67b074b2b; APPROVING (0/0/0).
- mathcity/subdomains/proof-assist/skills/using-mathpowers/SKILL.md: 4403 bytes; SHA-256 5a8de4cf8f4071e2021144e525a494e170ef4c5e2fa5861def0ea86897e8b355; APPROVING (0/0/0).
- mathcity/subdomains/latex/skills/fp-finder-latex/SKILL.md: 15623 bytes; SHA-256 53466eb0600ce8345954ad02a038ac977ef3047d9fc41c5982784f8268bf93b4; APPROVING (0/0/0).
- mathcity/skills/math-workflow/references/execution.md: 8860 bytes; SHA-256 77dd229e75f06424f86ff1d402de2280c2d536fa2ab92fac8fd0d96255808321; APPROVING (0/0/0).
- mathcity/skills/math-workflow/references/synthesis.md: 7481 bytes; SHA-256 af054739d6cc3ddbc9b0644b4cc0440ba4d6d462adde43349a6f52c3f2fb5817; APPROVING (0/0/0).
- agent-skills/skills/frontier-dump/SKILL.md: 7874 bytes; SHA-256 ab73fd7a7aaef9ad828d568747614e12ea64e7966036591ff3cc8f3267a791ce; APPROVING (0/0/0).

---REVIEW-VERDICT---
verdict: APPROVING
blocking_count: 0
major_count: 0
minor_count: 0
---ACTION-ITEMS---
---END-REVIEW---

The independent whole-tuple revisor's complete response was:

```text
NO
```

The driver checked substantive per-file shrink (no factoring) and verified
structured fp-receipt records for all eight real skill roots. Aggregate
approval is derived from the individual reports above, not a substitute
for them. No skill changed after this frozen tuple.
