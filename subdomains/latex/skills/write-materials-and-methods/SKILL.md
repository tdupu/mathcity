---
name: write-materials-and-methods
description: Draft the Software / Acknowledgements / AI-disclosure section of a manuscript from the repo's ai-usage.md and tokens.md trail, to the contract in the repo's AI-POLICY.md (AI-rules) — factual claims ONLY from the trail, in one of two human-chosen layouts (a section right after the introduction, or a short closing subsection of the introduction pointing to an appendix section) with thirteen PCF-derived subsections and a token appendix. Use when the user says "write the software section", "add the AI disclosure", "draft acknowledgements scaffolding", or when latex-ai-statement routes a failed rule here for repair. Grants, hospitality, and personal thanks are supplied by the human, never invented. NOT for auditing an existing disclosure (that is latex-ai-statement) and NOT for writing the trail itself (update-ai-usage, update-tokens).
---

# write-materials-and-methods

Runs `subdomains/latex/WRITERS.md` preamble and postamble in full (manuscript-tier
target). This leaf's middle:

## Sources and placement

- Contract: the repo's `AI-POLICY.md` (AI-rules), resolved repo-local-first
  per `subdomains/repo-docs/RESOLUTION.md`. On a miss, **stop and route to
  `new-repo-ai-policy`** — never fall back to the pack template, and never
  instantiate: RESOLUTION §2's instantiate-and-interrupt is carved out for
  `check-*` skills, and a drafter creating the contract it will then be
  judged against defeats the trinity. It governs what the disclosure must
  contain; this skill governs how it is written. Do not restate or widen it.
- Sources: the repo's master `ai-usage.md` / `tokens.md` trail and the
  per-folder working records they consolidate. Those files are written by
  [[update-ai-usage]] and [[update-tokens]], never by this skill; a gap in
  the trail is fixed there and the drafting waits. Every named tool, model
  string, and usage claim must appear in the trail — no memory, no
  inference from vibes; missing telemetry is stated plainly, never
  estimated.
- Reader access: use internal logs as drafting evidence, not as substitutes
  for disclosure. The manuscript must itself state the relevant tools/models,
  concrete contributions, review performed, and any material limits of the
  record. Do not direct readers to local paths, scratch files, private chats,
  ai-usage.md, tokens.md, or similar records they will not receive. A supplement
  may be cited only if it will actually accompany the paper or has a verified
  public, stable location; summarize the essential information in the paper
  even then. Token usage is reported in the paper itself, as the appendix
  table under **Structure**, unless a venue requirement recorded with the
  manuscript excludes it. Do not infer human verification from agent review.
- Before delivery, read the disclosure as a reader who has only the submitted
  paper and its declared public supplements. Replace each inaccessible-file
  reference with the supported substantive information it was meant to convey.
- Placement and heading follow **Layout** below; the repo's AI12 is
  checked for conflict there, not obeyed blindly. **Where the document has
  an abstract, draft its one-sentence disclosure too** (AI12) — factual, no
  marketing: what assisted, which model and harness, and that the authors
  are responsible; without it the auditor's abstract finding has no repair
  path. Keep Acknowledgements distinct; never invent grants, hospitality,
  or thanks.
- Placeholders (`<grant numbers>`, `<host institutions>`, `<author check>`)
  for everything only the human knows, listed for them explicitly.

## Layout: ask the human

Two layouts are acceptable, and the choice is the human's:

1. **Section after the introduction.** A numbered
   `\section{Software and AI assistance}\label{sec:ai}` immediately after
   the Introduction, holding the thirteen subsections below.
2. **Pointer in the introduction, section in the appendix.** A short
   numbered `\subsection{Software and AI assistance}\label{sec:ai}` as the
   last subsection of the Introduction, and an appendix
   `\section{Software and AI assistance}\label{app:ai}` holding the
   thirteen subsections.

The short subsection of layout 2 is one paragraph, with no lower-level
headings, tables or derivation accounts, that a reader can stop at. It
states, in order:

- (a) each AI system used, with model identifier, harness, the dates AI1
  requires, its `\cite`, and the kinds of work it did;
- (b) the numbered results an AI produced or first found, refutations and
  counterexamples first (AI14), each by `\ref` and attributed to a system
  named in (a); if there are none, one sentence saying so;
- (c) that this subsection and Appendix~\ref{app:ai} were drafted by AI
  (model, harness, date) and how the authors reviewed them — an
  `<author check>` placeholder unless the record shows human review (AI10);
- (d) the AI9 sentence: responsibility for every argument, result and
  citation rests with the human authors;
- (e) a pointer: see Appendix~\ref{app:ai} for methods, provenance and due
  diligence.

Derivation accounts (AI8), literature hits (AI5), and skill and software
lists belong only in the appendix section.

Token accounting is its own `\section{Token accounting}\label{app:tokens}`
and the last appendix section; in layout 2 the disclosure section
immediately precedes it. Never append the disclosure at the end of the body
or leave it as `\subsubsection`s of the introduction. When the document
has no Introduction, the question has two options instead: layout 1 placed
after the opening overview, or after front matter if there is none (AI12);
or a `\section{Introduction}` stub, after which both layouts are open.
Never add a stub unasked. `write-introduction` keeps a layout-2 subsection
verbatim.

**Recording.** Before drafting, open or amend this task's `update-ai-usage`
entry; its Agents table is the trail source for item 7 and element (c).
The layout choice lives in an entry's **Prompt** field as
`Layout choice (AI12): layout <n>, <who>, <date>, "<their words>"`.

**Venue override.** When a journal placement requirement is recorded with
the manuscript (AI12) or in an `update-ai-usage` entry, follow it instead of
either layout and do not ask. Keep the thirteen subsections and the token
appendix unless the requirement excludes them, and name the requirement's
location in the delivery report.

**Asking.** Skip the question only when a `Layout choice (AI12)` line exists
for this manuscript; if the manuscript's current layout differs from it,
migrate the existing text into the recorded layout, keeping its content.
When the manuscript already has one layout but no recorded choice, confirm
it in one yes/no question; on no, ask the two-option question. Otherwise
ask which layout they want — one question, the two layouts as its options,
before drafting — and wait. Record the answer in the Prompt field. An
answer relayed by a caller counts only if it quotes the human's words and
names who gave them. When you cannot reach the human
(subagent, scheduled run), stop before drafting and return the question to
your caller as a blocking item. Never choose a default, and never infer the
answer from the repository's `AI-POLICY.md`, an older manuscript, or the
PCF paper.

**Stale policy.** When the repository's AI12 admits only one layout, or
neither (the former unnumbered-subsection rule), ask anyway; then report
the stale rule and route its amendment to `new-repo-ai-policy`, then draft
in the chosen layout without waiting for it; `latex-ai-statement` grades
against the two layouts and reports POLICY-STALE. Never edit the policy
from here.

## Structure

The reader is a referee deciding how far to trust the paper. They need to
know how the work was produced, what the machines found, what was done with
each finding, and what was checked — not the order in which sessions ran.
Session-by-session narration buries those answers, so organize by question.
Session dates and identifiers belong to the `ai/` records; where the repo's
AI1 requires a date on an AI mention, put it inside the item it dates.
In either layout, use these thirteen `\subsection` headings in order: the
PCF paper's thirteen `\subsubsection`s, promoted to `\subsection`s. Each answers one
question; a category with nothing to report gets one factual sentence,
never silence. Copy the structure, not the PCF paper's project history.

1. **Methods: typesetting** — editing phases; what the router does and
   which `check-*` skills it actually runs.
2. **Methods: agent management** — each repo contract file present and
   its writer skill (`new-repo-*-policy`; CONTEXT.md is
   [[domain-modeling]]'s).
3. **Methods: record keeping** — master `ai-usage.md` / `tokens.md`,
   what each records and its writer; point to the token appendix.
4. **Methods: natural language proofs** — when [[frontier-dump]] was
   used and what its package records. If explaining the workflow's
   model-selection rationale, cite Sutton's bitter lesson and distinguish
   the source's claim from the workflow's design choice.
5. **Methods: adversarial reviews** — when reviews ran and which skills.
6. **Methods: AI assisted computations** — computations and source
   checks, each with system and version.
7. **Methods: AI statement** — an explicit sentence that this statement
   (and, in layout 2, the closing introduction subsection) was drafted by
   AI, with model, harness and date; the skills executed versus only
   consulted; AI drafting versus human review and acceptance; and the AI9
   sentence.
8. **Proofreading and adversarial review** — each review skill run, the
   model and harness that ran it, and the errors caught, with where the
   paper corrects each.
9. **Literature review** — the skill that located references
   ([[track-down-reference]]) and what it accepts, how searches were run and
   their limits (per-result hits go under Provenance), and whether the human authors checked the references (only what
   the record shows; otherwise a placeholder for them).
10. **AI findings and procedure** — an itemized sequence: per item, what was
   found (with its numbered statement), the model, harness and setting that
   found it, and what was done next. Starting material (AI7) opens it;
   negative findings are items in it, placed first where AI14 says so.
11. **Provenance** — the AI5 search for each AI-result, techniques and
   counterexamples alike. First Proof Second Batch (arXiv:2606.18119,
   p.~5; locate it with [[track-down-reference]]) gives evidence of related
   source retrieval by models, which is why the search is owed even when
   nothing looks borrowed. One item per prior source, with pinpoint and
   method comparison.
12. **Due diligence** — one item per related frontier-dump, one sentence of
   result each.
13. **Formalization** — what was formalized, in which system and revision,
   with which skills, or that there is none.

Token usage is a table in the token-accounting appendix section (task,
model and harness, tokens by class, cost), preceded by the counting scope,
the rates and their as-of date; Methods points to it. Unrecorded or unpriced rows say so.

## Software citations (default, not optional)

- **Cite all software used substantively in the work.** Every software
  system named in this subsection needs a bibliography entry and an in-text
  citation: computational systems, packages, AI systems and interfaces,
  workflow packages, and named document-build tools. Acknowledgement prose
  alone is not a citation. Audit the software-name/citation pairs before
  delivery; do not infer that a package's citation also credits its host
  system, or conversely.
- For OpenAI assistance, cite **OpenAI as the corporate author** and the
  actual product used (for example, Codex at <https://openai.com/codex/>).
  State the model identifier and interface in the disclosure when evidenced
  by the usage trail. Apply the same rule to other AI providers. Use verified
  official product pages or provider-recommended citations. Do not cite
  ChatGPT when the recorded interface was Codex; do not turn a website into
  an invented journal article or copy malformed bibliography metadata from
  a precedent. The provider citation identifies the system, not evidence of
  the project's usage; the contribution account still belongs in the text.
- Prefer the software author's `CITATION.cff`, official recommended citation,
  archived release DOI, or associated software/algorithm paper. Give author,
  title, the version actually used when known, and a stable public URL or DOI.
  For a live website, include an access date. Do not replace a recorded older
  version with the latest version shown on the website, or invent a release
  date. Use the appropriate version or documented section as a citation
  locator; do not manufacture page or theorem numbers for software.
- Follow Drew Sutherland's software-citation practice as a model: identify
  the actual implementation and host system, and credit the associated
  research paper when requested by its author. His
  [galrep software page](https://math.mit.edu/~drew/galrep.html) identifies the
  Magma implementation and asks users to cite the associated paper. This is
  a citation-practice example, not a reason to cite galrep, Magma, or
  Sutherland in a project that did not use them.
- **Name and cite every skill the statement mentions**, executed or
  reviewing, to the repository that holds it. `readlink -f
  ~/.claude/skills/<name>` finds the repository and the skill's directory
  (the locator); the commit comes from the trail or the declared-tools
  table, never from the checkout's current HEAD. A local checkout does not
  establish public availability. A skill in a private repository is still
  named and cited to that repository, marked private; its AI3 gap is stated
  in the text and reported to the human, never hidden by dropping the skill. The paper still describes each procedure it
  relies on; never make an inaccessible file the reader's source of the
  methods.

## Delivery check

Read the disclosure, token appendix and bibliography together, and the Introduction once `write-introduction` has run. Confirm the chosen layout,
self-contained contribution descriptions, provider citations (OpenAI when
used), citations for every named software system, actual version evidence,
public accessibility, and separation of agent review from human verification.

Then hand the file to [[latex-ai-statement]] for the per-rule audit against
`AI-POLICY.md` and the trail. Drafting is not self-certifying: this skill
writes the disclosure, that one decides whether it passes.

## Red flags

| Thought | Reality |
|---|---|
| "Presumably Magma was used" | The trail says what was used. Presumably ships lies. |
| "Copy the acknowledgements from the template paper" | Structure transfers; gratitude does not. |
| "Naming OpenAI in the prose is enough" | Add the provider/product bibliography citation. |
| "The software section belongs just before the bibliography" | Only the two layouts: right after the Introduction, or a closing Introduction subsection pointing to the appendix. |
| "The repo policy says section-after-intro, so I won't ask" | The layout is the human's choice. Ask; report a policy conflict if their answer differs. |
| "The local skill path is a reproducibility reference" | Readers need the procedures in the paper and an accessible public citation. |

## Negative results travel with the positive ones (LX11, LX12)

This skill renders previous work into a new artifact, so the negative-result
floor of `mathcity/subdomains/latex/POLICY.md` (LX11, LX12) applies even
outside the latex subdomain. Before finishing, enumerate the inputs'
refutations, counterexamples, ill-posed proposals, and failed expectations, and
carry each into the output, naming the expectation it corrects: "it is natural
to expect X; in fact Y". Report the count carried and, for anything
deliberately left out, the scope reason. Dropping a refuted claim together with
its refutation loses the finding that survived: the refutation is the result.
