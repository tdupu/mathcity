---
name: write-materials-and-methods
description: Draft the Software / Acknowledgements / AI-disclosure section of a manuscript from the repo's ai-usage.md and tokens.md trail — factual claims ONLY from the trail, structure per the declared house precedents. Use when the user says "write the software section", "add the AI disclosure", "draft acknowledgements scaffolding". Grants, hospitality, and personal thanks are supplied by the human, never invented.
---

# write-materials-and-methods

Runs `subdomains/latex/WRITERS.md` preamble and postamble in full (manuscript-tier
target). This leaf's middle:

## Sources and structure

- Sources: the repo's ai-usage.md / tokens.md trail (scratch dumps and
  root records). Every named tool, model string, and usage claim must
  appear in the trail — no memory, no inference from vibes; missing
  telemetry is stated plainly, never estimated (astra-dump's rule).
- Reader access: use internal logs as drafting evidence, not as substitutes
  for disclosure. The manuscript must itself state the relevant tools/models,
  concrete contributions, review performed, and any material limits of the
  record. Do not direct readers to local paths, scratch files, private chats,
  ai-usage.md, tokens.md, or similar records they will not receive. A supplement
  may be cited only if it will actually accompany the paper or has a verified
  public, stable location; summarize the essential information in the paper
  even then. Include token counts only when relevant to the methods, with their
  scope and limitations; otherwise omit them rather than exporting an internal
  bookkeeping dependency. Do not infer human verification from agent review.
- Before delivery, read the disclosure as a reader who has only the submitted
  paper and its declared public supplements. Replace each inaccessible-file
  reference with the supported substantive information it was meant to convey.
- Structure per the house precedents the design record declares:
  an unnumbered **Software and AI assistance** subsection at the **end of
  the Introduction**, before the first substantive mathematical section.
  This is the default for both manuscripts and notes; in notes with an
  unsectioned opening overview, put it after that overview. Do not append
  it at the end of the paper. Follow an explicit user or journal placement
  requirement when one is given. Keep Acknowledgements distinct; never
  invent grants, hospitality, or personal thanks.
- House examples: Jacobi manuscript 1
  (`jacobi/1-generic-smoothness-implies-JBC-paper/arxiv-1/jbc-generically-reduced-arxiv-1.tex`)
  and manuscript 2
  (`jacobi/2-dimension-conjecture-implies-JBC paper/arxiv-1/dc-implies-jbc-arxiv-1.tex`)
  place software at the end of the Introduction. The second gives
  contribution-specific AI disclosure with an OpenAI bibliography citation.
  Consult the actual files where available; copy their structure, never
  their project-specific usage, authorship, or human-verification claims.
  Older precedents include `orderone2/AJMv2.tex` and `jacobi/dc2.tex`;
  verify locations instead of relying on historical line numbers.
- Placeholders (`<grant numbers>`, `<host institutions>`) for
  everything only the human knows, listed for them explicitly.

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
- When used, cite Dupuy's **latexpowers** and **mathpowers** workflow
  collections from the public `mathcity` repository, in addition to the AI
  provider: [LaTeX workflows](https://github.com/tdupu/mathcity/tree/main/subdomains/latex)
  and [mathematics workflows](https://github.com/tdupu/mathcity/tree/main/subdomains/proof-assist).
  Verify those locations at drafting time. Prefer an accessible versioned
  release or commit when it actually contains the version used. A local
  checkout or a private `agent-skills` mirror does not establish that a
  particular router file or commit is publicly available. If only the public
  collection is available, cite that collection honestly and describe the
  relevant procedures in the paper; do not imply that it archives the exact
  local snapshot. If no public source is available, state that limitation
  and include the essential procedures in the paper or an accompanying
  supplement. Never make an inaccessible file the reader's source of the
  methods.

## Delivery check

Read the finished Introduction and bibliography together. Confirm placement,
self-contained contribution descriptions, provider citations (OpenAI when
used), citations for every named software system, actual version evidence,
public accessibility, and separation of agent review from human verification.

## Red flags

| Thought | Reality |
|---|---|
| "Presumably Magma was used" | The trail says what was used. Presumably ships lies. |
| "Copy the acknowledgements from the template paper" | Structure transfers; gratitude does not. |
| "Naming OpenAI in the prose is enough" | Add the provider/product bibliography citation. |
| "The software subsection belongs just before the bibliography" | Default to the end of the Introduction. |
| "The local skill path is a reproducibility reference" | Readers need the procedures in the paper and an accessible public citation. |
