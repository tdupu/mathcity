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
Quality floor: `mathcity/subdomains/latex/POLICY.md` (LX-rules) — this
file tightens it, never loosens it. Style authority for exposition:
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

**ST9 — Introductions last.** No introduction or abstract is drafted
for a document whose results sections still carry unresolved `\taylor{}`
markers or undischarged proofs; introductions are manuscript-tier and
human-initiated (design D6).

## Change Log

| Date | Change | Approved by |
| --- | --- | --- |
| `<YYYY-MM-DD>` | Instantiated from mathcity-repo-docs template | `<name>` |
