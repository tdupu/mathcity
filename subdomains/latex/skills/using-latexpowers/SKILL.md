---
name: using-latexpowers
description: Use for mathematical manuscripts, notes, .tex files, citations, referee reports, and research-file synthesis into a coherent presentation. Includes planning sections, writing claims, and resolving manuscript targets. Also accepts using-latex, using-latexskills and using-latexpower.
---

<SUBAGENT-STOP>
Assigned a bounded leaf task? Follow that brief and its writer/evidence gates; do not restart the top-level workflow.
</SUBAGENT-STOP>

**First invoke `using-superpowers`, then `math-workflow` in latex mode.** Reuse an active workflow; resolve contracts and dispatch before any edit. Announce the route; non-manuscript work returns to its domain skill.

Latex mode uses `using-mathpowers` for proofs/research and executes the requested declared-target artifact: `rapid-prototype` for unresolved claims, even with a blocked backend; writers for established results. Writer gates apply. Both routers share one coordinator and plan.

## Dispatch

| Situation | Route |
|---|---|
| Selected frontier dumps / research files → introduction to a topic or coherent presentation | `math-workflow`'s [synthesis sequence](../../../../skills/math-workflow/references/synthesis.md): gather context, prototype, review, fill, review, integrate |
| “make-outline” / audience-aware outline / theorem-first backfill | `rapid-prototype` — combined outline and skeleton stage; resume synthesis if already active |
| Missing contracts or requested cleanup | Run the LaTeX-power initialization pass: inventory the repository, apply explicit user dispositions automatically, ask only about genuinely ambiguous rows, and verify the canonical build. `init-repo-docs` is an implementation helper, not a separate adoption gate. |
| Layout health / “which file is real?” | `check-layout` |
| Undeclared sibling `.tex` | `triage-variants` — authorized per-file disposition before affected writing |
| Style / build / LaTeX hygiene / references / citations | `check-style` / `check-latex` / `check-latex-hygiene` / `check-labels-and-refs` / `check-citations` |
| Compare two manuscript source versions | `latex-diff` — resolve both `.tex` inputs, generate a disposable `latexdiff`, and report the exact sources and validation result |
| Formalize manuscript claims | `using-leanpowers` under the same coordinator and claim IDs; return exact checked statements, assumptions and fidelity evidence before writing |
| “Prove X” / research gap / suspect mathematics | `using-mathpowers` for that obligation, then return here for the requested artifact |
| Claim needs a source / suspect cite / verification marker | `track-down-reference`; `clean-citations` for citation-repair proposals |
| Evidenced statement / definition / connecting explanation | `write-proposition` / `write-definition` / `write-remark` |
| Break an existing proposition into separately proved enumerated items | `break-up-proposition` — the default whenever a proposition environment has multiple items; preserve the mathematics, give each item a stable `\label{item:<slug>}`, cite parts with `\eqref{item:<slug>}`, and signpost each proof as “Proof of `\eqref{item:<slug>}`”; adding items is optional and requires evidence. |
| Requested stub / discussion-to-skeleton / unresolved X | `rapid-prototype` — conjecture or definition, never a fake proof |
| Scratch computation → notes | `explain-experiment` |
| Computed graph / spectrum / mathematical plot | `generate-graphics` — Sage source, checked data, provenance, rendered preview |
| Existing graphic → explanatory manuscript figure | `add-figure` — verify meaning, caption and reference at the relevant passage |
| Worked case / finite example / counterexample | `write-example`; compose `add-figure` when a graphic explains it |
| “What does this proof use?” | `resolve-dependencies` |
| ACCEPTED report to apply | `revise` — item-to-edit map |
| “Referee our section” / “adversarial review of our manuscript” | `referee-report` — read-only self-review; do not use this route for a supplied referee report |
| Received referee report / “response to the referee” / “reply to reviewers” | `triage-referee-report` — use its artifact-only received-review mode for report/response TeX/PDF packages, or its four-round mode when substantive manuscript revision is authorized |
| Review-response attachments / report with responses / response-letter PDF | `triage-referee-report` artifact-only mode — preserve the supplied report as the black source, omit interleaved author comments from the report copy, and place one matching response below each item in `\color{red}` |
| Decision-record audit | `check-adr` |
| “Prep for arXiv” / editorial stripping | `garbage-collect` — approval of the concrete strip set |
| Methods / software / AI disclosure | `write-materials-and-methods` — to the repo's `AI-POLICY.md` contract |
| “Is the AI statement right?” / pre-submission disclosure audit | `latex-ai-statement` — per-rule verdict against `AI-POLICY.md` and the trail; routes repairs |
| Record an AI task's provenance / cost | `update-ai-usage` / `update-tokens` — sole write paths for the repo's master `ai-usage.md` and `tokens.md` |
| Amend the repo's AI-usage contract | `new-repo-ai-policy` — human-authorized amendment |
| Finished manuscript introduction/abstract request | `write-introduction` — readiness/refusal gates; an introductory topic prototype uses the synthesis route |
| Amend layout / LaTeX / style / decisions / agent contracts | `new-repo-layout-policy` / `new-repo-latex-policy` / `new-repo-style-policy` / `new-repo-adr-policy` / `new-repo-agents-policy` — human-authorized amendments |
| Amend LX rules | `new-latex-policy` — human-authorized amendment to the separate mathcity `subdomains/latex/POLICY.md`; this route does not govern global `using-latexpowers` guidance |
| Amend global LaTeX workflow guidance | Apply the requested change directly to this skill; do not route it through mathcity's `new-latex-policy` gate |
| Amend powers defaults | `new-powers-policy` — choose explicitly between a repository-local `POWERS.md` override and a global router amendment |
| Reorder within the current synthesis | Coordinator adjusts the plan, preserves item/source links and rechecks dependencies; unrelated section merges remain `merge-latex-sections` HOLD |
| Refuted claim / counterexample / failed expectation from prior work | State it as a result (LX11) — `write-proposition` or `write-example` for the refutation, `write-remark` for the intuition it corrects; never drop the claim and its refutation together |
| Rendering prior work into a new document (dump, digest, synthesis, revision, introduction, exposition, merge, handoff) | Carry the input's negative results forward first (LX12); list any excluded finding with its scope reason |

Checks precede affected writes. Definitions, constructions, and new notation precede theorem-class statements (LX10), even without a local ST10. Once a definition is introduced, later sections may explain or specialize it but may not silently change its meaning; revise the first definition and its dependents together if the semantics must change. Review statement bodies; compilation alone does not verify this.

For received-review response artifacts, the supplied report is the authoritative
source text. The report artifact must preserve its item order and review wording
while omitting author-response comments. The response artifact must reproduce
that same review text and place one corresponding author response below each
item in `\color{red}`; use a prior response-letter template when one is
available. Do not synthesize a new adversarial review or substitute a
resolution ledger for the received report. Keep the `.tex` sources and their
compiled PDFs together in the declared scratch or revision root.

The received-review trigger takes precedence over the self-review trigger when
the user supplies an existing report or asks for a response to one. Phrases
such as “response to the referee,” “reply to reviewers,” “report with
responses,” “review-response attachments,” and “convert the attached review to
TeX/PDF” all select `triage-referee-report` artifact-only mode unless the user
also authorizes substantive manuscript revision.

## Online references and link macros

When a reader should consult an HTML page—such as a Stacks Project tag, an
LMFDB record, or a GitHub repository—give both a bibliography citation and an
explicit hyperlink to that page. The citation remains the source attribution;
the hyperlink is a navigation aid and must not replace the citation. For
repeated links, define a site- or project-specific macro in the document
preamble whose expansion emits the citation first and the hyperlink second,
with a compact displayed label or short URL. Keep a source comment immediately
beside the macro recording the URL template, for example:

```tex
% URL: https://www.lmfdb.org/Variety/Abelian/Fq/<label>
\newcommand{\avlink}[2]{\cite[#1]{LMFDB}\,\href{https://www.lmfdb.org/Variety/Abelian/Fq/#2}{\textsf{#2}}}
```

Use the same pattern for Stacks, GitHub, and other reader-facing HTML
references; adapt the BibTeX key and pinpoint locator to the actual source.
The pass criterion is mechanical: every such macro has a resolving `\cite`, an
explicit `\href`, and a nearby URL comment, and every use presents both the
citation and the link. A bare URL, a hyperlink without a bibliography entry,
or a bibliography entry without the reader-facing link fails and must be
revised.

## Definition layout

When a definition introduces multiple words, put them in a dedicated
`enumerate` environment with one `\item` per word; do not hide separate
definitions in running prose. If an immediate consequence follows two or more
definitions, close the `definition` environment first and state the
consequence in prose, a remark, or a theorem-class environment outside it.
The definition environment contains definitions only. Pass requires every
multi-word definition to have an explicit enumeration and every immediate
consequence to occur after the closing `\end{definition}`.

The same rule governs **every theorem-class environment**, not only
`definition`: the environment carries hypotheses and conclusion and nothing
else. Unpacking ("Explicitly, for every $y$ there is ..."), explication of
what the statement means, and secondary conclusions imported from a cited
source go after the closing tag, each introduced by its own connective
sentence. Test: a sentence that a reader who trusts the statement could skip
without losing the statement belongs outside the environment. Verify by
reading the body, never by compiling — a consequence sentence inside an
environment compiles exactly as well as one outside it, so no build
diagnostic exists for this defect and reviewers reliably miss it.

## Default for multi-item propositions

Whenever a proposition environment contains multiple `\item`s, invoke
`break-up-proposition` by default. The standard result is one proposition
environment whose items have stable semantic labels and one separately
signposted proof block per item, with item references written as
`\eqref{item:<slug>}`. This default applies during ordinary manuscript
cleanup as well as when the user explicitly asks to break up a proposition.

Do not add mathematical items merely because this default is active: preserve
the existing conclusions and add an item only when the user requests it or
the evidence supports it. If the parts are actually separate named theorem
statements, write separate theorem-class environments instead. A user request
to preserve the existing form overrides this layout default for that target.

## Choosing the environment

When it is unclear whether a fact should be a definition, a proposition, or a
remark, ask how it would be formalized. The discriminator matches how these
documents are consumed downstream, including by any Lean development built
from them:

| The fact, formalized | The environment here |
|---|---|
| a `def` — names an object or fixes notation | definition |
| a `theorem`/`lemma` — has a proof and is applied elsewhere | proposition |
| a `have` inside one proof, used nowhere else | prose in that proof; do not promote |
| several separately named theorems | several statements, not one with parts |
| nothing — no formal counterpart exists | remark, subject to write-remark's limits |

A fact cited more than once earns a number and a label; a fact cited zero
times is prose, or is deleted; a statement whose parts would be separate
theorems is written as separate statements. A statement's enumerated parts
are an interface — cite them by `\eqref{item:...}`, never by a literal "(1)",
which survives the deletion of the part it names with no diagnostic. Repair a
broken part-citation by giving each consumed part its own labelled statement,
not by restoring an enumeration the author has rejected.

The table is silent on motivation, intuition, and worked examples. Those have
no formal counterpart and are governed by exposition, not by it.

## Process belongs to the disclosure section

The mathematical body states results, never the route to them. No statement,
proof, or remark says "an earlier draft asserted", "in a previous version",
or "we initially believed". Where the process itself must be recorded, it
goes in the repository's AI-assistance/disclosure section and the `ai/` work
records. This bounds, and does not weaken, the negative-results floor below:
a refutation survives as mathematics, while the draft that held the refuted
expectation does not survive at all.

## Segregating imported results

A result imported from the literature is segregated into its own section when
it is **not immediately obvious to the reader** — a substantial theorem the
argument leans on, stated so it can be cited and checked. An obvious or
routine standard fact stays inline where it is used; hoisting it costs the
reader a lookup for nothing. A section of imported results holds only
imported results: a statement the paper proves itself does not belong there,
however technical.

Negative results are results (LX11). When the work behind a document refuted a
claim, disproved an expectation, found a counterexample, or showed a proposed
definition ill-posed, that finding is stated in the document as a numbered
theorem-class statement — or, when unproved, as a labelled question or
conjecture — with the expectation it corrects named in the text: "it is
natural to expect $X$; in fact $Y$". Never delete a wrong claim together with
its refutation; the refutation is the surviving result, and in a subject whose
intuition is imported from a neighbouring theory it is often the most valuable
one. Any artifact produced from previous work carries that previous work's
negative results forward (LX12) — before, not after, its positive results —
and records a scope reason for every finding deliberately left out. Both are
document-quality floors: enumerate the evidence trail, match findings to
statements, and report counts; a keyword scan does not discharge them.

AI disclosure is a document-quality floor, not an optional courtesy. The
repo's `AI-POLICY.md` governs what any manuscript must say about models,
software, and AI-results, and requires one master `ai/ai-usage.md` and one
master `ai/tokens.md`, with dated call folders for supporting material. Every
AI-result carries a literature search and a derivation account;
software—including AI providers and workflow skills—is cited like Magma or
SageMath; agents are never authors and never the source of a mathematical
claim.

## Initialization and hygiene

When the user asks to initialize or hygienize a LaTeX repository, this skill
owns the pass. Preserve the user's named canonical manuscript and declared
folder structure. Treat explicit instructions to move, retain, ignore, or
delete named files as dispositions already approved by the user; execute them
without a second adoption gate. Ask one question only for an artifact whose
disposition is genuinely ambiguous. Put AI outputs in dated directories under
`ai/`, keep the two master records directly under `ai/`, keep references in
the declared references directory, and keep generated LaTeX output ignored
and out of the canonical tree. Verify the resulting manuscript and
bibliography before committing the cleanup. Only after that commit should a
requested review or grilling workflow begin.

User instructions and repository contracts take precedence over skills, subject to LaTeX policy floors. Preserve leaf gates and report unresolved conflicts explicitly.

## Repository-local powers policy

Before planning, read the repository-root `POWERS.md` when it exists. Apply
the section for `latexpowers` as a repository-local addition or tightening of
these defaults; it does not replace global floors and must not be propagated
to another repository. Use `new-powers-policy` when the user asks to create or
amend this file, or when the user asks to change the global default instead.
