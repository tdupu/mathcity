# Introduction dos and don'ts

The default taste list for `write-introduction`. This file is data, not the
skill; the skill reads it at run time and hands the resolved list to the
drafter. Refer to items by ID; never reuse a retired ID.

**Resolving.** Start from this file. Then apply the items in the
`latexpowers` section of the repository's `POWERS.md` that name
`write-introduction`, in order, one per line:

    - write-introduction: drop DONT5
    - write-introduction: amend DO8: <replacement text>
    - write-introduction: add LOCAL1: <rule>

**Changing the defaults.** A rule the human dictates ("add Tao's advice
on organisation") goes through `new-powers-policy`: global scope edits this
file, local scope edits `POWERS.md`; no repro is needed. When an
introduction came out wrong and the list is the suspected cause, run
`adjust-behavior` (it needs a repro); its repair edits this file. Never add
these rules to `SKILL.md`.

Items marked *(floor)* restate a floor of `SKILL.md`; dropping or amending
them changes nothing.

## Do

- **DO1 — State the main results as theorems.** Put the main theorem(s) in
  theorem environments in the introduction, so an expert who reads only the
  introduction knows what the paper proves. When the precise statement needs
  too many definitions, state a special case or a version labelled informal,
  and point to the numbered statement it comes from. [Etnyre; Tao, sell]
- **DO2 — Open with the specific problem.** The first paragraph says what
  question the paper answers and where the question comes from. [Kleiman;
  Berndt]
- **DO3 — Explain why it matters.** Place the problem in the larger
  programme it belongs to; do not assume the reader knows how it fits.
  Readers at the junction of two fields will know at most one of them.
  [Etnyre]
- **DO4 — Compare with prior work.** Say which earlier results and
  techniques this paper extends, and how its results or methods differ from
  them. Cite the closest work at pinpoint locators and a survey where one
  exists. [Tao, sell; Kleiman]
- **DO5 — Name what is new.** Say which ideas, techniques, or difficulties
  are new, and which obstacle absent from earlier work had to be overcome.
  [Tao, sell; Etnyre]
- **DO6 — Show sharpness and limits.** When counterexamples show that a
  hypothesis cannot be dropped or a conclusion cannot be strengthened, say
  so next to the theorem. State plainly which hypotheses may be stronger
  than needed and which questions remain open. [Tao, sell; Tao, accurate]
- **DO7 — Sketch the proof strategy.** Give the main idea of the proof and
  say where each step is carried out; a simple special case first if it
  shows the mechanism. [Tao, motivate; Tao, sell]
- **DO8 — Break a long introduction into pieces.** Past a page or two, use
  subsections and theorem-led paragraphs so that a reader can find the part
  they need and skip the rest. [Etnyre]
- **DO9 — End with a roadmap.** The last paragraph before any closing
  disclosure subsection says what each section contains, by section number.
  [Kleiman; Mann]
- **DO10 — Label what is not proved.** A heuristic, an expectation, or a
  non-trivial claim given without proof or citation is labelled as such.
  *(floor)* [Tao, accurate; Tao, motivate]

## Don't

- **DONT1 — No pile of notation.** Do not open with notation or
  definitions. Use standard terms without defining them; defer non-standard
  ones to the section that needs them. [Berndt; Etnyre; Mann]
- **DONT2 — No generic opener.** Not "X is an important area of
  mathematics" or "hard problems have long attracted attention". Start with
  the problem. [house default]
- **DONT3 — No scavenger hunt.** Do not replace the statement of results
  with references to numbered statements scattered through the paper.
  [Etnyre]
- **DONT4 — No false advertising.** Do not invoke a famous conjecture
  unless the text says honestly how far this paper gets toward it. Do not
  overstate or understate a result. *(floor)* [Tao, accurate]
- **DONT5 — No citation padding.** Cite what the reader needs, not every
  paper by the authors or their colleagues. [house default]
- **DONT6 — No tangents.** Keep the introduction as short as it can be
  while doing its job; background needed only in one section goes in that
  section. [Etnyre; Kleiman]
- **DONT7 — No process narrative.** Do not describe drafts, abandoned
  approaches, or how a model or an author found a result. That belongs in
  the Software and AI assistance disclosure.
  [using-latexpowers, "Process belongs to the disclosure section"]
- **DONT8 — No promotional adjectives.** Not "novel", "remarkable",
  "powerful", "elegant". Let the comparison with prior work show the
  contribution. [house default; `purge-claudisms`]

## Abstract and title

- **ABS1 — Abstract summarises, it does not set up.** Name the subject,
  state the main result in words, and say what is new, in a few lines. No
  background paragraph, and preferably no symbols. [Kleiman]
- **ABS2 — Title names the area and the distinctive result.** Concise, no
  symbols, no secondary details. Titles remain working slugs unless the
  human sets one (ST9). [Kleiman; Tao, sell]

## Sources

- Tao, sell: T. Tao, "Use the introduction to 'sell' the key points of your
  paper", <https://terrytao.wordpress.com/advice-on-writing-papers/use-the-introduction-to-%E2%80%9Csell%E2%80%9D-the-key-points-of-your-paper/>
- Tao, accurate: T. Tao, "Describe the results accurately",
  <https://terrytao.wordpress.com/advice-on-writing-papers/describe-the-results-accurately/>
- Tao, motivate: T. Tao, "Motivate the paper",
  <https://terrytao.wordpress.com/advice-on-writing-papers/motivate-the-paper/>
- Etnyre: J. Etnyre, "The art of writing introductions", Notices AMS 66
  (2019), 361–362, <https://doi.org/10.1090/noti1816>
- Kleiman: S. Kleiman, "Writing a math phase two paper", MIT,
  <https://math.mit.edu/classes/18.704/piiUJM2.pdf>, §2
- Berndt: B. C. Berndt, "How to write mathematical papers", §§1–2,
  <https://math.illinois.edu/document/1199>
- Mann: K. Mann, writing advice for a Berkeley course,
  <https://e.math.cornell.edu/people/mann/classes/berkeley/writingadvice.pdf>

All sources above were opened and checked against their items on
2026-10-15.
