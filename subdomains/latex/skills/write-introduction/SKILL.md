---
name: write-introduction
description: Use when a manuscript needs its introduction or abstract written or rewritten — on an explicit human ask for this document ("write the introduction now"), or when the human says yes to using-latexpowers' final-stage question after every body section, check, review and the AI disclosure are done. Not for introductory topic prototypes (math-workflow's synthesis route) and never before the body is finished.
---

# write-introduction

The introduction is written **last**, from a **fresh document**: a new draft
made from the finished body by an agent that has not seen the old
introduction or the conversation that produced the paper. Rewriting the
existing introduction anchors the new one on claims the body may no longer
support; reading only part of the body loosens the statements it reports.
The gate below is the skill's other half: the introduction states in public
what the paper proves, so it is refused while the body is unsettled.

Runs `subdomains/latex/WRITERS.md` preamble and postamble in full. This
leaf's middle:

## The gate (check all eight; any failure = one loud refusal naming every failing item)

1. **Initiation.** Quote the human's words from this conversation: either
   an ask for the introduction of THIS document, or a yes to the question
   `using-latexpowers` asks at its final stage. Introductions stay
   human-initiated (ST9, design D6); no router or writer starts this skill
   without one of the two.
2. **Body settled.** In every section outside the introduction and
   abstract, zero `\taylor{}` / `\todo{}` outside comments, and zero
   `% VERIFY`-class flags except on superseded lines (two or more leading
   `%` inside an ST5 block). Count and report either way.
3. **Old introduction clear.** The introduction and abstract being replaced
   (excluding the layout-2 disclosure subsection and the abstract's
   AI-disclosure sentence) contain no `\taylor{}`,
   `\todo{}`, `\agentreply{}` and no human comment lines, commented out or
   not. Replacing them would edit human text, which WRITERS.md forbids;
   list locations and let the human clear them. The coordinator may grep
   the old introduction for this gate; it does not read its prose yet.
4. **LX4.** Enumerate the theorem-class statements outside the
   introduction and abstract being replaced, plus those frozen under
   step 1; for each, quote its
   proof location, pinpoint citation or textbook note. Any gap fails.
   `check-latex` must pass (build), and `check-latex-hygiene` too when the
   repo is LX-bead-governed.
5. **Consistency.** A `contradiction-check` over every section outside the
   introduction and abstract being replaced is clean (the preamble's
   targeted run does not discharge this).
6. **Ledger.** Every theorem-class statement in the body has a current
   ledger row (missing or stale rows: rescan per LEDGER.md first).
7. **Disclosure.** The document has its AI disclosure in one of the two
   layouts of `write-materials-and-methods`; otherwise refuse, naming that
   skill as the next route.
8. **Negative results.** Every `refuted` ledger row and every negative
   finding in `ai-usage.md` is stated in the body; otherwise refuse,
   routing to `write-proposition` / `write-example`.

Receipt: ai-paper.tex — a polished abstract asserting an unproved formula
while the human draft carried 26 unresolved queries.

## Dos and don'ts

Resolve the taste list per [references/dos-and-donts.md](references/dos-and-donts.md)
and hand the drafter the resolved list verbatim. The list lives there, not
here. The gate, the accuracy floor (step 3) and the negative-results floor
are not list items, and no list edit removes them.

## Drafting from a fresh document (gate passed)

1. **Freeze the inputs** into `scratch/intro-inputs-<date>-<slug>.md` (Markdown,
   so no undeclared `.tex` sibling): the body with the introduction and
   abstract removed, read in full; the ledger rows; the bibliography keys
   and entries; the document preamble's macros; the repo `STYLE.md` style
   variables; the resolved list; the disclosure layout. Three things cross
   from the old introduction, verbatim and without surrounding prose: a
   theorem-class statement that occurs only there and is `\ref`'d from
   the body (environment, label, statement), frozen as a body statement;
   the list of other labels defined there that the body references, with
   their environment type; and the abstract's AI-disclosure sentence
   (AI12). Nothing else from the old introduction, earlier drafts or this
   conversation goes in.
2. **Dispatch a fresh drafter**: a new subagent, not a fork, whose prompt is
   the inputs path, steps 2–3 of this section, and the sections "The AI
   disclosure and the introduction" and "Negative results travel with the
   positive ones". The coordinator adds no commentary, emphasis or
   summary. Before prose, the drafter writes a
   claim map: each result the introduction will state, the label of the
   body (or frozen) statement it comes from, and whether it is stated
   verbatim, as a special case, or labelled informal. Map by ledger
   status: `proved` with doubt SOUND is stated as proved; `conditional`
   with its condition; `imported` as cited, at its pinpoint; `conjectural`
   as a labelled conjecture; `refuted` as refuted, with the `\ref` to its
   refutation. A mapped claim whose row reads `proved` without SOUND stops
   the run with a loud refusal naming `doubt` for that row; it is never
   relabelled.
3. **Draft against the map (accuracy floor).** The abstract and the
   introduction assert exactly the mapped claims in the body's own
   hypotheses: no strengthening, no "for all" beyond the proof, no
   hypothesis silently dropped. Cite only entries in the frozen
   bibliography; a needed new citation is listed as a
   `track-down-reference` request, not written. Structure follows the
   resolved list and the declared style authority (Tag 02BZ); where the
   list and the repo's style variables disagree, the style variables win
   and the conflict is reported. Titles remain working slugs unless the
   human sets one (ST9).
4. **Fresh review.** A second new subagent runs `critical-review` on the
   draft with the claim map, the resolved list and the inputs file. It
   checks each claim against its statement and each list item. The
   coordinator forwards the verdict block verbatim, with no commentary, to
   the drafter or a new fresh drafter with the inputs path, and does not
   edit the draft. Stop at an APPROVING verdict with no MAJOR items; open
   BLOCKING or MAJOR items after the third round are a loud refusal; MINOR
   items are reported with the draft.
5. **Install in place.** Comment out the old introduction and abstract
   inside ST5 tags (superseded text is never deleted) and insert the new
   ones inside their own tags, keeping every label the body references. A
   layout-2 disclosure subsection and its tags are not touched: insert the
   new introduction above it and comment out only the lines above it.
   Likewise keep the abstract's AI-disclosure sentence and its tags
   untouched, as the abstract's last sentence.
6. **Coverage diff.** Now, and only now, the coordinator reads the old
   introduction and lists every substantive point the new one lacks: each
   dropped citation, literature comparison, convention or stated
   limitation. It reports the list to the human and does not edit the
   draft. Restorations the human approves go to a fresh drafter as new
   inputs and through step 4 again. Then run the WRITERS.md postamble.
7. **Declare the introduction (AI4).** The introduction and abstract are
   AI-drafted prose: record the task through `update-ai-usage`, have
   `write-materials-and-methods` add it to the disclosure (in layout 2,
   to the closing subsection where its elements need it), and run
   `latex-ai-statement`.

## The AI disclosure and the introduction

`write-materials-and-methods` owns the disclosure and settles its layout
with the human; this skill owns neither its text nor the choice. In layout
1 the disclosure section follows the introduction; in layout 2 its short
subsection stays the introduction's last subsection, verbatim. If the
resolved list calls for a roadmap, the roadmap names the disclosure section
(layout 1) or the appendix section (layout 2).

## Negative results travel with the positive ones (LX11, LX12)

Every refutation, counterexample or failed expectation stated in the body
is mentioned in the introduction with a `\ref` to its body statement,
naming the expectation it corrects: "it is natural to expect $X$; in fact
$Y$". Report the count carried and the scope reason for any left out. A
negative finding in the trail that the body does not state is a body
defect: refuse and route it to the body writer
(`write-proposition`/`write-example`). Dropping a refuted claim together
with its refutation is a revise-level violation.

## Red flags

| Thought | Reality |
|---|---|
| "The draft is basically done, the intro will motivate finishing" | Introduction-first is the failure this skill exists to refuse. |
| "One open marker is minor" | One marker is one unresolved question stated in public. Refuse. |
| "The old intro is good, I'll tighten it" | Tightening is rewriting from the old text. Draft fresh; diff afterwards. |
| "I'll pass the drafter the .tex, it can skip the intro" | It will read it. Hand it the frozen inputs file only. |
| "I read the main theorems; the rest won't change the intro" | Unread sections hold the limits and counterexamples the intro owes. Read all of it. |
| "The theorem is clearer stated a bit more loosely" | A looser statement is a different theorem. Map it or label it informal. |
