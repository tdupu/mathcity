---
name: write-materials-and-methods
description: Draft the Software / Acknowledgements / AI-disclosure section of a manuscript from the repo's ai-usage.md and tokens.md trail, to the contract in the repo's AI-POLICY.md (AI-rules) — factual claims ONLY from the trail, organized by the house structure (Methods, review, literature, findings, provenance, due diligence, formalization; token appendix). Use when the user says "write the software section", "add the AI disclosure", "draft acknowledgements scaffolding", or when latex-ai-statement routes a failed rule here for repair. Grants, hospitality, and personal thanks are supplied by the human, never invented. NOT for auditing an existing disclosure (that is latex-ai-statement) and NOT for writing the trail itself (update-ai-usage, update-tokens).
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
- Placement and heading are AI12's in the repo's copy; do not append the
  subsection at the end of the paper. **Where the document has an abstract,
  draft its one-sentence disclosure too** (AI12) — factual, no marketing:
  what assisted, which model and harness, and that the authors are
  responsible; without it the auditor's abstract finding has no repair path.
  Follow a user or journal placement requirement **only when it is recorded
  with the manuscript** — an override given only in conversation FAILs AI12
  and routes straight back here, so ask for it to be recorded first. Keep
  Acknowledgements distinct; never invent grants, hospitality, or thanks.
- Placeholders (`<grant numbers>`, `<host institutions>`, `<author check>`)
  for everything only the human knows, listed for them explicitly.

## Structure

The reader is a referee deciding how far to trust the paper. They need to
know how the work was produced, what the machines found, what was done with
each finding, and what was checked — not the order in which sessions ran.
Session-by-session narration buries those answers, so organize by question.
Session dates and identifiers belong to the `ai/` records; where the repo's
AI1 still requires a date on an AI mention, put it inside the item it dates.
Use these subsubsections, in order (unnumbered, referred to by name, when
AI12 makes the parent unnumbered). Each answers one question; a question
with nothing to report gets one sentence saying so, never silence.

1. **Methods** — how the manuscript was produced: the editing phases; the
   repo contract files present and the skill that writes each
   (`new-repo-*-policy`; CONTEXT.md is [[domain-modeling]]'s); the master
   records `ai-usage.md` and `tokens.md`, what each records, and their
   writers; what the router does and which `check-*` skills it runs; when
   adversarial reviews run and with which skills; when [[frontier-dump]]
   was used, what a package records, with a footnote on why it is
   bitter-lesson-proof (Sutton's lesson in one cited sentence; in one more,
   that the skill fixes the question and the record, not the model); the
   computations and source checks, each with system and version; and how
   this statement was drafted and audited — executed versus consulted
   skills, AI drafting versus human review, and the AI9 sentence.
2. **Proofreading and adversarial review** — each review skill run, the
   model and harness that ran it, and the errors caught, with where the
   paper corrects each.
3. **Literature review** — the skill that located references
   ([[track-down-reference]]) and what it accepts, how searches were run and
   their limits (per-result hits go under Provenance), and whether the human authors checked the references (only what
   the record shows; otherwise a placeholder for them).
4. **AI findings and procedure** — an itemized sequence: per item, what was
   found (with its numbered statement), the model, harness and setting that
   found it, and what was done next. Starting material (AI7) opens it;
   negative findings are items in it, placed first where AI14 says so.
5. **Provenance** — the AI5 search for each AI-result, techniques and
   counterexamples alike. First Proof Second Batch (arXiv:2606.18119,
   p.~5; locate it with [[track-down-reference]]) gives evidence of related
   source retrieval by models, which is why the search is owed even when
   nothing looks borrowed. One item per prior source, with pinpoint and
   method comparison.
6. **Due diligence** — one item per related frontier-dump, one sentence of
   result each.
7. **Formalization** — what was formalized, in which system and revision,
   with which skills, or that there is none.

Token usage is a table in an appendix (task, model and harness, tokens by
class, cost), preceded by the counting scope, the rates and their as-of
date; Methods points to it. Unrecorded or unpriced rows say so.

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

Read the finished Introduction, token appendix and bibliography together. Confirm placement,
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
| "The software subsection belongs just before the bibliography" | Default to the end of the Introduction. |
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
