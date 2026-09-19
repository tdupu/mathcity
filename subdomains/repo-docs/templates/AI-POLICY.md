# AI-POLICY.md — AI-usage and software-citation contract

<!-- TEMPLATE (mathcity-repo-docs). Instantiate into a repo root, fill the
     header and the declared-tools table, delete this comment. Owned by the
     repo: amend only through new-repo-ai-policy. Briefing companion:
     AI-POLICY-SHORT.md. -->

| Field | Value |
| --- | --- |
| Repo | `<repo-name>` |
| Status | Draft |
| Date | `<YYYY-MM-DD>` |
| Approved by | `<human name>` |
| Prefix | AI |
| Checked by | `latex-ai-statement` (manuscript, `[C]`); `update-ai-usage` / `update-tokens` (records, `[R]`) |
| Amended by | `new-repo-ai-policy` |
| Rule budget | 24 — wording is scarce; a new rule must displace or earn its slot |
| Transcript retention | `<default location for session transcripts and telemetry>` |

How this repo discloses AI assistance and cites software.

**Floors.** Rules marked `[F]` may be tightened by a repo's copy, never
weakened or deleted, and bind repos whose copy predates them. An amendment
lowering one is refused, not presented.

**Markers.** `[C]` — checked in the manuscript by `latex-ai-statement`.
`[R]` — checked in the records at write time by `update-ai-usage` /
`update-tokens`. `[F]` — a template floor (see the **Floors** paragraph above). A rule may carry both `[C]` and
`[R]`: manuscript and record are different enforcement points for one
obligation, and a record writer may refuse a write that would put the record
below a rule it carries. Unmarked rules are judgment obligations, surfaced
but not gated.

**Quality floor.** `mathcity/subdomains/latex/POLICY.md` (LX-rules) and the repo's
`STYLE.md` (ST-rules). This file tightens them and never loosens them; AI2/AI3
specialize LX2 and LX6. Community anchors: the
[Leiden Declaration](https://leidendeclaration.ai/) (June 2026, IMU-endorsed),
the [AMS AI policy](https://www.ams.org/publications/journals/policies/UseofArtificialIntelligence),
and arXiv's 2026 sanction for hallucinated citations.

**Instantiation prerequisite.** This contract adds four tracked root files —
`AI-POLICY.md`, its `AI-POLICY-SHORT.md` companion, `ai-usage.md`, and
`tokens.md`. Before instantiating, amend `LAYOUT.md` through
`new-repo-layout-policy` (tree rows for all four; LY1/LY2/LY5 doc set; an LY3
carve-out for the two root ledgers; and LY6's per-doc cap, which binds this
file only once LY5 lists it) and the `AGENTS.md` contracts table through
`new-repo-agents-policy`. Skipping this leaves the four files undeclared,
which `check-layout` reports against LY2's tree diff.

## Declared tools

Every row needs a `.bib` key; a tool with no key is a disclosure the reader
cannot follow (AI2).

| Tool | Kind | Version / model id | `.bib` key | Access date | Refs verified |
| --- | --- | --- | --- | --- | --- |

## Rules

**AI1 — AI is never mentioned without its model and harness [C][R].**
The model identifier actually used (`claude-opus-5`, not "an LLM"), the harness
(Claude Code, Codex CLI, web chat, API), the date, and reasoning-effort or
temperature when the harness exposes them.
Pass: every AI mention carries model + harness + date. Fail: a bare "AI",
"an LLM", or an unversioned product name.

**AI2 — Every software system used substantively is cited [C].**
CAS, languages, libraries, databases, build tools, AI products and providers
all get a BibTeX entry and a pinpoint `\cite` (LX2). AI providers are cited as
software, exactly as Magma or SageMath are. Where the source is unpaginated —
a provider page, a model card, a CAS home page — the locator is AI3's
hyperlink form. Give the version actually used and a stable public URL.
Pass: every declared-tools row has a key, an entry, and a pinpoint citation;
no dead entries (LX6). Fail: a tool used and not cited, or a bare `\cite{key}`.

**AI3 — Skills and workflow software are cited to their source, with a link [C].**
The repository or README is the cited object and the locator is a hyperlink:
`\cite[\href{https://github.com/<org>/<repo>/blob/<ref>/README.md}{README}]{Author1938}`,
pinned to a tag or commit that contains the version used. A local checkout or
private mirror does not establish public availability.
Pass: a keyed entry and a hyperlinked locator resolving to a public URL.
Fail: a skill named in prose only, or a locator pointing at a local path.

**AI4 — AI-results are declared as such [C][R].**
An **AI-result** is anything from an AI session that, had a fellow
mathematician supplied it, would have required acknowledgement: a statement,
counterexample, proof strategy, reference, reformulation, computation, **or
drafted mathematical prose**. Each is identified with the model, harness, and
named skill that produced it (`frontier-dump`, `fable-prompt`).
Pass: each AI-result is attributed to a concrete tool chain.
Fail: an AI-derived contribution with no provenance, or provenance given only
as "AI assistance was used".

**AI5 — Every AI-result gets a literature search, and the search is reported [C][R][F].**
Agent output is frequently already known, and Leiden makes proactive
attribution an obligation, not a courtesy. For each AI-result: search; report
each **hit** — a pinpoint reference (LX2) the result is equivalent to, follows
from, or could reasonably have been derived from — and state the relation;
**compare and contrast the methods**, not merely priority; say plainly when
the technique was clearly available even if no one reference states the
result; and report the AI-result **even when the search returns nothing**,
saying the search was run and came back empty. Attribution that cannot be
resolved is stated as unresolved, not omitted.
Pass: every AI-result has hits with locators and a method comparison, or an
explicit no-hits statement. Fail: no search, or a hit with no comparison.

**AI6 — Agents are cited as software, never as mathematical warrant [C][F].**
The distinction is **origin versus warrant**. Naming a model as the *origin*
of an AI-result is required (AI4), and the AI2 provider citation belongs in
that same provenance or methods sentence. Offering a model as the *warrant*
for a mathematical claim is forbidden: a model is never an author, never a
corresponding author, and never the authority a statement rests on. Do not
write "the model proved"; do not present a transcript as an argument.
Pass: no AI system in the author block, and every model `\cite` sits in a
sentence asserting provenance or method rather than mathematics.
Fail: an AI system in the author block; a model `\cite` in a sentence making a
mathematical assertion; or a claim whose stated support is a model.

**AI7 — The starting material is disclosed [C].**
What was available to the agents before the searches — definitions,
conjectures, drafts, prior notes, computations — and for each, whether it was
human-generated or AI-generated.
Pass: inputs named with their human/AI provenance.
Fail: results reported with no account of what they were built on.

**AI8 — No blind credit [C][R].**
Never "the model found it". State what was asked, what the search or
derivation did, and what the human did to turn it into the claim as stated.
Pass: each AI-result has a derivation account. Fail: bare attribution.

**AI9 — Responsibility stays with the human authors [C][F].**
Responsibility for the correctness and adequacy of every argument, result, and
citation remains exclusively with the human authors, whatever produced the
draft, and the disclosure says so. Every coauthor is told of the AI use and
assents to the disclosure before submission.
Pass: an explicit human-responsibility statement is present.
Fail: language that shares or defers responsibility to a tool.

**AI10 — The expert-talk gate [R].**
Nothing ships that the authors could not present in an expert talk and defend
under questioning without further AI assistance. Agent review is never
disclosed as human verification.
Pass: every shipped claim is independently understood by a human author.
Fail: a result retained because the model was convincing.

**AI11 — AI-surfaced references are verified before use [C][R][F].**
Every reference an AI proposed is checked against the actual source — it
exists, the numbering matches, it says what it is claimed to say — before it
enters the bibliography. Fabricated citations are sanctionable under arXiv's
2026 policy.
Pass: every AI-surfaced entry in the `.bib` is marked verified in the records.
Fail: an unverified AI-proposed reference in the `.bib`. (A reference surfaced,
checked, and correctly discarded is not a finding.)

**AI12 — Placement is fixed [C].**
The unnumbered **Software and AI assistance** subsection goes at the end of
the introduction; in a document with no introduction, immediately after the
opening overview; in a document with neither, as the first unnumbered
subsection before the first numbered section; failing all three, immediately
after the front matter. A document that has an abstract
also carries one factual disclosure sentence in it; a document with no
abstract owes no abstract sentence. Acknowledgements stay separate — no
invented grants, hospitality, or thanks. A journal or user placement
requirement overrides this rule when recorded with the manuscript.
Pass: the subsection is present, unnumbered, correctly headed, at the first
of those four positions the document admits; and the abstract carries the
disclosure sentence whenever the document has an abstract.
Fail: subsection absent, misheaded, numbered, placed later than the position
the document admits, or an abstract without the sentence.

**AI13 — Computations are recomputed, not quoted [C][R].**
Numeric, algebraic, and combinatorial claims originating in an AI session are
re-derived in a real system (Magma, SageMath, Macaulay2, Python) and reported
as that system's output, cited per AI2. "The model asserted" and "the system
computed" are different claims and are worded differently.
Pass: each computational claim traces to a rerunnable computation.
Fail: a model transcript standing in for a system run.

**AI14 — AI sessions owe a record even when they produced only a refutation [C][R].**
ST11/LX11/LX12 already require negative results to be stated and carried
forward; this rule adds what they do not cover — a session whose only output
was a refutation, counterexample, or ill-posed proposal still gets an
`ai-usage.md` entry and an AI5 search. Discharge is by the floor's own test:
exhibit each finding as a numbered statement with both locators, **before**
the positive results, naming the expectation it corrects ("it is natural to
expect $X$; in fact $Y$"). A keyword scan does not discharge it. ST11 and LX12 grant a
scope-reason escape to *derived* artifacts; the canonical document is not one,
so the escape does not apply here.
Pass: every negative finding in the records is exhibited in the document with
its locators, in that order and framing; counts reported.
Fail: a refuted claim deleted together with its refutation, a finding recorded
but not exhibited, or a refutation-only session with no `ai-usage.md` entry.

**AI15 — One master `ai-usage.md` and one `tokens.md` per repository [R][F].**
Both at the repository root, covering the whole repo. Subdirectory artifacts
keep working records; those are sources consolidated upward, never competing
ledgers. `update-ai-usage` is the sole write path for `ai-usage.md`,
`update-tokens` for `tokens.md`. Session transcripts and raw telemetry behind an
entry are retained for the life of the submission as the primary evidence
beneath the AI4/AI5/AI8 accounts. The repo declares the default location in
this file's header; an entry names its own only when it differs.
Pass: exactly one of each at the root; the header's retention location
resolves, and any entry-level override resolves too.
Fail: a root-level duplicate, an unconsolidated orphan, or an account with no
surviving evidence.

**AI16 — Token usage is priced and dated [R][F].**
Per task: token counts, the model spent on, the rates applied, the cost, the
task date, and the rate's own as-of date. Exact telemetry where available.
Where attribution is impossible, say so and record the raw observations and
why they cannot be separated. A labelled estimate of a **magnitude** is
permitted; a fabricated **attribution** across inseparable aggregates is not.
Totals mark which rows are measured and which estimated.
Pass: every row carries tokens, model, rates, cost, date, rate-as-of, and a
source label. Fail: an unlabelled estimate, an invented figure, or a total
mixing measured and estimated rows silently.

**AI17 — Confidential material stays out of third-party models [R].**
Unpublished third-party work — referee reports, submissions under review,
private communications — is not sent to a third-party model without the
owner's permission. Where a workflow step is skipped for this reason, record
what was withheld.
Pass: no confidential third-party content in any recorded session.
Fail: a referee report or submission under review sent to a model.

**AI18 — No residual AI artifacts in the manuscript [C].**
No leftover prompts, model chatter, hedging boilerplate, placeholder
citations, or chat scaffolding. Readers are never directed to local paths,
scratch files, private chats, `ai-usage.md`, or `tokens.md`; the manuscript
states the substance itself. A supplement may be cited only if it will
accompany the paper or has a verified, stable public location.
Pass: the document reads as a self-contained mathematical text.
Fail: prompt residue, or a reader pointed at a file they will not receive.

**AI19 — Submission gate [C].**
A manuscript is not submitted, posted, or promoted to a higher tier until
`latex-ai-statement` has run against **that exact revision** — identified by
commit hash or version string — and returned no FAIL, with every DEFER either
resolved or accepted in writing by a named human. The audit report is
retained with the submission — `latex-ai-statement` writes it under `ai/`,
which travels with the repository. An `ADVISORY` verdict
from a `Status: Draft` policy does **not** clear this gate; adopt the policy
or record the named human's acceptance.
Pass: a retained audit names the submitted revision and carries no FAIL and no
unaccepted DEFER.
Fail: no audit, an audit of a different revision, an unresolved FAIL, or an
unaccepted DEFER.

**AI20 — Records are self-describing [R][F].**
A record says which task it belongs to and what kind of file it is.
*Identity:* every record carries the task identifier
`<ISO-8601-datetime-with-offset>__<skill>__<slug>` — the offset so agents in
different zones cannot mint colliding keys, the double underscore because `-`
occurs inside all three fields. It is minted once, by `update-ai-usage`, and
joins `ai-usage.md` to `tokens.md`; a caller pricing a task with no provenance
entry mints a provisional identifier and marks the row as lacking provenance.
*Type:* a roll-up index over records (the established name is `usage.md`)
declares itself on its first line and is never consolidated — consolidating one
counts every record it indexes a second time. An unlabelled file carrying an
index signal is reported as ambiguous and left unconsolidated, never guessed
at: guessing "record" double-counts silently while every row still reads as
correct, whereas guessing "index" under-counts and surfaces later.
Pass: every record names a well-formed identifier; every index declares itself;
ambiguous files are reported, not consumed.
Fail: a missing, malformed, or never-reconciled provisional identifier; an
undeclared index consolidated as a record; or an ambiguity resolved by guess.

## Change Log

| Date | Change | Approved by |
| --- | --- | --- |
| 2026-09-19 | Add AI20 (records are self-describing: task identifier + index-vs-record). Proposed as two rules, AI20 and AI21, split on when each is checked — written versus consolidated. Merged to one on re-read: the house separates rules by **obligation**, not by check moment (AI12 spans abstract and body, AI15 spans uniqueness, write paths and retention), and "a record says what it is" is one obligation with two facets. Do not re-split without a new argument. Both mechanisms shipped before the rule. | Taylor Dupuy (decision delegated to agents, 2026-09-19) |
| `<YYYY-MM-DD>` | Instantiated from the mathcity repo-docs template. | `<human name>` |
