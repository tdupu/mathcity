# Amendment — AI-POLICY.md (pack template): AI20 (proposed as AI20 + AI21)

| Field | Value |
| --- | --- |
| Target | `subdomains/repo-docs/templates/AI-POLICY.md` (pack template) |
| Date | 2026-09-19 |
| Proposed by | reviewer02 session, at QUIMBY 72's direction |
| Status | **APPLIED as a single rule AI20** — see Resolution below |
| Gate | Pack-side change. Taylor delegated the decision to agents on 2026-09-19 ("agents are free to decide this") and imposed a rule-budget instead, so this did not need his textual sign-off. `new-repo-ai-policy`'s routing table was corrected in the same change, since it still claimed the old rule. |

## Resolution — proposed as two rules, landed as one

The split below argued AI20 and AI21 on the grounds that they are checked at
different moments: identity when a record is **written**, type when records are
**consolidated**. That reasoning is sound but uses the wrong axis. The house
separates rules by **obligation**, not by check moment — AI12 spans the abstract
and the body, AI15 spans root-uniqueness, sole write paths and retention. "A
record says what it is" is one obligation with two facets, so it landed as a
single **AI20 — Records are self-describing [R][F]**.

A rule budget (24, recorded in the template header and enforced by
`check-ai-coverage.py`) makes wording scarce and sharpened the re-read, but the
merge is defensible on the house's own convention independently of the budget.
Nothing mechanical was lost: both facets keep their pass/fail clauses, and both
are enforced by the same two owners.

**Do not re-split without a new argument.** The reasoning is in the template's
Change Log so the next reader does not relitigate it.

The two-rule text below is retained as the record of what was proposed and why.

## Recommendation: TWO rules, not one

Asked whether this is one artifact type or two, my answer is **two**, and the
deciding test is not subject matter but *when and how each is checked*:

| | AI20 — task ID | AI21 — index vs record |
| --- | --- | --- |
| Checked when | a record is **written** | records are **consolidated** |
| Asks | does this record have a well-formed, unique identity? | is this thing a record at all? |
| Fails as | the two ledgers cannot be joined, deduped, or mirror-checked | a double-count that is silent and leaves every row correct |

Different moments, different criteria, different failure modes. `AMENDMENT.md`
requires each rule carry its own mechanical pass/fail criterion; one rule with
two unrelated criteria is the sprawl AI15 already suffers from and should not
be repeated. They are presented together because they land together, not
because they are one obligation.

## The concrete failure this prevents

Not hypothetical. `usage.md` reached **64 files across the estate** (231
`ai-usage.md` records) with no owner in any contract. Consequences already
observed, all in one day:

1. It was **silently dropped** from `fp-finder-latex`'s contract during a
   refactor — the skill went from naming three artifacts to naming two, and
   nobody noticed, because no contract said the third existed.
2. A well-intentioned proposal to "complete" the two-name provenance detector
   by adding `usage.md` would have **counted every indexed record twice**.
   Caught only because someone read the files rather than the filename.
3. A cross-repo run mirrored across three repositories would have **tripled a
   cost figure** while every individual row stayed correct.

The task-ID format is now in exactly the same position `usage.md` was in:
spreading unprompted, useful, and named in no contract. It is currently
confined to one file. This claims it while that is still cheap.

## AI20 — proposed text

> **AI20 — Every record carries a task identifier [R][F].**
> The identifier has the form
> `<ISO-8601-datetime-with-offset>__<skill>__<slug>`; the offset is required
> so agents in different zones cannot mint colliding keys, and the double
> underscore separates fields because `-` occurs inside all three. It is
> minted once, by `update-ai-usage`, and is the join between `ai-usage.md`
> and `tokens.md`. A caller that prices a task without a provenance entry
> mints a provisional identifier and marks the row as lacking provenance.
> Pass: every entry and every priced block names a well-formed identifier.
> Fail: a record with no identifier, a malformed one, or a provisional one
> never reconciled.

## AI21 — proposed text

> **AI21 — An index is not a record [R][F].**
> A roll-up index over records (the established name is `usage.md`) links to
> the records it covers and is never consolidated; consolidating one counts
> every record it indexes a second time. An index declares itself on its
> first line. An unlabelled file carrying an index signal — an H1 naming it
> an index, or links to a sibling `ai-usage.md` / `tokens.md` — is reported
> as ambiguous and left unconsolidated pending a human disposition, never
> guessed at: guessing "record" double-counts silently while every row still
> reads as correct, whereas guessing "index" under-counts and surfaces later.
> Pass: every index declares itself; no index appears as a consolidation
> source; ambiguous files are reported, not consumed.
> Fail: an undeclared index consolidated as a record, or an ambiguous file
> resolved by guess.

## Why [R][F] on both

`[R]` because both are checked in the records at write and consolidation time,
not in the manuscript — there is no `.tex` face.

`[F]` because AI15's and AI16's existing floors depend on them. Mirror-skip is
only decidable if identifiers are globally unique and well-formed (AI20), and
"never invent a cost" (AI16) is only enforceable if an index cannot be consumed
as a record (AI21). A repo that weakened either would silently reopen the
floors above it. If Taylor judges this floor-inflation, downgrading both to
`[R]` costs the cross-repo guarantees and nothing else.

## Enforcement ships with the rules — required edits in the same change

Per the standard this subsystem was repaired into: a rule lands with a marker,
an owner that names it, and a coverage-script line, or it lands unenforced.
Both mechanisms **already exist and are already committed** — this documents
shipped machinery rather than promising new machinery. But
`check-ai-coverage.py` requires the owner to name the rule *by number*, so the
amendment is incomplete without these four edits:

| File | Edit |
| --- | --- |
| `templates/AI-POLICY.md` | add AI20 and AI21 as above; Change Log row |
| `skills/update-ai-usage/SKILL.md` | tag the ID-minting paragraph `(AI20)` and the index paragraph `(AI21)` |
| `skills/update-tokens/SKILL.md` | tag the Task ID section `(AI20)` and the index paragraph `(AI21)` |
| `templates/AI-POLICY-SHORT.md` | two index lines (below) and add AI20, AI21 to the floor line |

No change to `check-ai-coverage.py` itself: it parses markers and owners
generically, so it picks both rules up automatically — and **will fail** until
the four edits above are all made, which is the intended behaviour.

## AI-POLICY-SHORT.md companion lines

DO table:

| Give every record a task identifier — ISO datetime with offset, `__skill__slug` — minted once by `update-ai-usage`, joining `ai-usage.md` to `tokens.md` | AI20 |

DON'T table:

| Consolidate an index as if it were a record, or resolve an unlabelled file by guessing — an index declares itself on its first line, and an ambiguous one is reported | AI21 |

Floor line becomes: `Floors (never weakened): AI5, AI6, AI9, AI11, AI15, AI16, AI20, AI21.`

## Floor check

Adds two floors; weakens nothing. AI1–AI19 unchanged in text and markers.

## Downstream

No repo is in violation: no instantiated `AI-POLICY.md` exists yet, and the
estate audit found **zero** ambiguous files (64 `usage.md` candidates resolve
to 7 declared indexes and 57 records). AI21 is therefore preventive, not
remedial. AI20 is near-vacuous today — 1 minted identifier across 231 records
— and becomes load-bearing as the format spreads, which is precisely why it
should be claimed now rather than after.
