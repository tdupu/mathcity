# STYLE.md — mathematical writing contract

<!-- TEMPLATE (mathcity-repo-docs). Instantiate into a repo root, set
     the style variables, delete this comment. The repo's copy is owned
     by the repo: amend only through new-repo-style-policy. Checked by
     check-style. -->

| Field | Value |
| --- | --- |
| Repo | `<repo-name>` |
| Status | Draft |
| Date | `<YYYY-MM-DD>` |
| Approved by | `<human name>` |
| Checked by | `check-style` |
| Amended by | `new-repo-style-policy` |

What prose and statements in this repo's `.tex` files must look like.
The rules below ship with this template and bind on their own, whether or
not any pack is installed alongside the repo; where a mathcity pack IS
present its `subdomains/latex/POLICY.md` (LX-rules) is the shared floor
and this file tightens it, never loosens it. Style authority for exposition:
[Stacks Project Tag 02BZ](https://stacks.math.columbia.edu/tag/02BZ).

## Style variables

Declared per repo; defaults below. Skills read these before writing a
word. (Finer axes from exemplar corpora — Serre, Sutherland, Voight,
Harris, stacks-project — are a separate research bead; until it lands,
these three axes are the contract.)

| Variable | Value | Allowed |
| --- | --- | --- |
| document kind | `<notes>` | notes / paper / textbook-chapter / survey |
| terseness | `<stacks>` | serre-terse / stacks / harris-expansive |
| audience | `<expert>` | expert / graduate / mixed |

## Repo-specific standing conventions

Optional pointer table a repo fills in: where its notation contract
lives (a plan document, a conventions section, a glossary). Writers
scan it — plus the document's own preamble and existing definitions —
before introducing notation (write-definition's collision gate). May
be empty in a fresh repo.

| Concern | Where it lives |
| --- | --- |

## Rules

**ST1 — Proposition-only [C].** New numbered statements use
`proposition`, `definition`, `remark`, `conjecture`, or `theorem`
environments; no new `lemma` or `corollary`.
Pass: no `\begin{lemma}` / `\begin{corollary}` added since last check.

**ST2 — Explicit hypotheses [C].** Every statement environment opens by
naming its standing objects and hypotheses ("Let $K$ be a field of
characteristic zero…"); no hypothesis lives only in surrounding prose.
Pass: each statement's first sentence introduces its objects. (Judgment
clause; checker quotes violations rather than counting.)

**ST3 — 80-character source lines [C].** LaTeX source lines are at most
80 characters. Pass/Fail: mechanical scan, comments included.

**ST4 — Marker channel.** `\taylor{…}` (author queries) and `\todo{…}`
are the human marker macros. Only humans create or delete them. Agents
answer a query **adjacent** to it with the agent reply macro
`\agentreply{…}` (define once in the preamble:
`\newcommand{\agentreply}[1]{\textcolor{gray}{[agent: #1]}}`), used only
next to the marker being answered, deletable by any human at any time,
stripped at garbage collection.

**ST5 — Comment-out-and-tag cycle [C].** Revisions follow the house
protocol: comment out the old material, write the fix, wrap the changed
region in tag lines. Machine tag format (defined HERE; no prior format
exists):

```
% >>> [<author> <YYYY-MM-DD> <slug>]
…replacement text (live) and/or superseded text (commented out)…
% <<< [<author> <YYYY-MM-DD> <slug>]
```

`<author>` is the human's short name, or `agent-<harness>` (e.g.
`agent-claude`) — agents ALWAYS tag as agents. Acceptance,
acknowledgement, and adjudication are human acts: on acceptance the
human removes superseded commented-out text; tag lines are retained as
low-tech version control until garbage collection. Agents never delete
a marker, a human comment, or another author's tag.
Pass: every agent edit to a canonical `.tex` sits inside `agent-*` tag
lines. Fail: untagged agent edits, or agent edits to human tags/markers.

**ST6 — Notes-tier self-containedness.** In `notes`-tier documents an
imported result whose actual source has been found and opened is written
out with its proof and pinpoint provenance (per LX2), not cited bare.
Bare pinpoint citations are the manuscript-tier default.

**ST7 — Statements are proved or not; no status metadata in tex [C].**
A statement either has a proof/reference per LX4 or it does not. No
agent-generated status comments (proved/conditional/…) may demand human
attention in the source; agent bookkeeping lives in agent-side markdown
(design ADR 0004). Pass: no status-taxonomy comments above statements.

**ST8 — Commit discipline [C].** Commits touching `.tex` carry an
AI-assisted disclosure line when applicable and never a `Co-Authored-By`
trailer. Pass/Fail: `git log` scan.

**ST9 — Introductions and titles last.** No introduction or abstract is
drafted for a document whose results sections still carry unresolved
`\taylor{}` markers or undischarged proofs; introductions are
manuscript-tier and human-initiated (design D6). Titles are likewise
written last and kept short; until then documents go by their
lowercase-hyphen working slugs (LAYOUT.md LY7).

**ST10 — Definitions outside statements.** Apply the global LX10 rule
and its review procedure (`subdomains/latex/definition-separation.md`):
new terms, objects, constructions, and notation precede theorem-class
statements. Quantified hypotheses and mathematical conclusions stay in
statements. Pass: report all statement bodies checked and zero embedded
definitions; fail: quote each violation and extract it without changing
the claim. This floor also binds repos whose STYLE.md predates ST10.

**ST11 — Negative results are stated as results.** When the work behind a
document refuted a claim, disproved an expectation, showed a proposed
definition ill-posed, found a counterexample, or closed off an approach, the
document states that finding as a numbered statement environment — or, when
it is not proved, as a labelled `question` or `conjecture` — with the
corrected expectation named in the text: "it is natural to expect $X$; in
fact $Y$". Deleting a wrong claim together with its refutation is the
failure this rule exists to prevent: the refutation is the result that
survives, and in a subject whose working intuition is imported from a
neighbouring theory it is often the most valuable thing the work produced.
The rule binds the document's own earlier claims symmetrically: a statement
this repo once asserted and later disproved is recorded as a refutation, not
quietly dropped. It also binds derived artifacts — any synthesis, digest,
exposition, introduction, merge, handoff, or dump produced from this repo's
documents or its agent-side evidence carries their negative results forward,
before the positive ones, or records per finding the authorized reason it is
out of that artifact's scope.

Write the finding at the strength it has. An intuition-correcting result is
neither softened into an unnumbered aside nor inflated into a general
theorem, and a refutation of a specific claim says which claim, in the words
the claim was made in.

Pass: enumerate the refutations, counterexamples, ill-posed proposals, and
failed expectations recorded in this repo's agent-side evidence (`scratch/`
reports and ledgers, review packages, superseded drafts) and exhibit, for
each, the numbered statement, question, or conjecture in the canonical
document that carries it, with both locators; report the number enumerated
and the number carried. A keyword scan cannot discharge this check. Fail:
quote each finding present in the evidence and absent from the document; the
remediation is to write it, not to delete the evidence. (Pack counterpart
where a mathcity pack is installed: LX11 and LX12.)

## Change Log

| Date | Change | Approved by |
| --- | --- | --- |
| `2026-09-19` | Add ST11: negative results are stated as results, and derived artifacts carry them forward; written self-contained so an instantiated repo does not depend on a pack being present | `Taylor, explicit conversation request` |
| `2026-09-17` | Add ST10 pointer to global LX10 definition-separation floor | `Taylor, explicit conversation request` |
| `<YYYY-MM-DD>` | Instantiated from mathcity-repo-docs template | `<name>` |
