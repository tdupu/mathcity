---
name: latex-ai-statement
description: Read-only audit of a specified .tex file's Software and AI assistance disclosure against the repo's AI-POLICY.md (AI rules) and against the ai-usage.md / tokens.md trail — placement, abstract sentence, model and harness naming, software and skill citations with hyperlinked pinpoint locators, AI-result declarations with literature-search outcomes, human-responsibility statement, and absence of agent-as-warrant or prompt residue. Emits a structured verdict block with per-rule PASS/FAIL/DEFER, counts, and quoted evidence; routes repairs, never applies them. Use on "check the AI statement", "latex-ai-statement", "check-ai-statement", "is the disclosure correct", "audit the software section", before arXiv submission, or as the AI19 gate before any manuscript promotion. NOT for writing the disclosure (write-materials-and-methods) and NOT for the master records themselves (update-ai-usage, update-tokens).
---

# latex-ai-statement

Read-only (AI19 gate). Reports; never fixes, never edits the docs it enforces,
never creates files except the RESOLUTION.md §2 instantiation and its own
report under `ai/`. Also answers to **check-ai-statement** — it is a
member of the `check-*` family and runs their shared preamble.

The disclosure is checked against two things at once: the **policy** (what it
must contain) and the **trail** (what is actually true). A disclosure that
satisfies the policy but overstates the trail is the worse failure.

## Preamble — mandatory

Run `subdomains/repo-docs/RESOLUTION.md` in full before the first finding:
§1 resolve repo-local-first (`AGENTS.md` declarations, then `<repo>/AI-POLICY.md`);
§2 on a miss **instantiate and interrupt the human** — never silently fall
back to the pack template, whose declared-tools table is empty and would make
AI2 pass vacuously. Instantiation also lands `AI-POLICY-SHORT.md`,
`ai/ai-usage.md` and `ai/tokens.md`; the interrupt must carry prerequisite
LAYOUT and AGENTS amendments so `check-layout` still passes; §3 floor semantics — compare the repo's copy against the template's `[F]`
rules and raise `FLOOR-BREACH` on any that is missing or weakened, reported
against the repo doc and never downgraded to advisory; §4 read the policy's
own `Status` (`Adopted` → binding; `Draft` → full check, verdict prefixed
`ADVISORY`; absent → `MALFORMED-POLICY`, proceed as Adopted); §5 the check
must be able to fail.

## Inputs

- **target**: the `.tex` file (with its input closure and `.bib`). In
  **policy-verification mode** — invoked by `new-repo-ai-policy` after an
  amendment — the target is the amended `AI-POLICY.md`: check its rule
  numbering, floor set, `[C]`/`[R]`/`[F]` markers, and Change Log row, then
  audit each manuscript in the repo. A repo with no manuscript reports
  "checked 0 manuscripts", never a silent pass. AI15/AI16 amendments verify
  against `update-ai-usage` / `update-tokens` instead.
- **trail**: `<repo>/ai/ai-usage.md`, `<repo>/ai/tokens.md`, unless the repo
  policy explicitly declares other locations.

## Checks

Derive rule inventory and counts from the resolved policy's markers, in numeric
order: check `[C]` faces here; report every `[R]` face as **delegated**, including
AI20. `[R]`-only rules are records' write-time gates; for `[C][R]`, check the
manuscript and delegate the record face. Name the failing face; omit no rule.

| Rule | Check |
| --- | --- |
| AI1 | Model id, harness, date on every AI mention; reasoning-effort/temperature where the trail records them. |
| AI2 | Enumerate from the policy's **declared-tools table**, not from what the `.tex` happens to name — a tool used and never named is the dominant violation. Each has a `.bib` entry and a pinpoint `\cite`; unpaginated sources use AI3's hyperlink locator; no dead entries. **An empty declared-tools table is `EVIDENCE-ABSENT`, never PASS** — a freshly instantiated policy ships it empty, so a vacuous pass here is the likeliest false clear. |
| AI3 | Skills/packs cited to a public URL pinned at the version used, hyperlinked locator, not a local path. |
| AI4 | Every trail AI-result declared, with model, harness, and producing skill — drafted prose included. |
| AI5 | Per AI-result: hits with pinpoint locators **and** method comparison, or an explicit no-hits statement. |
| AI6 | Three clauses: no AI system in the author block; no model `\cite` inside a sentence making a mathematical assertion; and no claim whose **stated support is a model** — the third catches "the model proved Lemma 4.2" where no `\cite` appears at all. Origin is fine, warrant is not. |
| AI7 | Starting material stated, human vs AI provenance distinguished. |
| AI8 | Each AI-result has a derivation account. |
| AI9 | Explicit human-responsibility statement present. |
| AI11 | No unverified AI-proposed reference **in the `.bib`**; a surfaced-then-discarded reference is not a finding. |
| AI12 | Unnumbered **Software and AI assistance** subsection at the first admitted position: end of introduction; else after opening overview; else first unnumbered subsection before first numbered section; else immediately after front matter. Abstract disclosure sentence **iff an abstract exists**. Honour a recorded manuscript placement override; name its location. |
| AI13 | Computational claims attributed to a system actually run; "model asserted" not worded as "system computed". |
| AI14 | Negative findings exhibited with their numbered statement and both locators, **before** the positives, each naming the expectation it corrects; counts carried and excluded reported. A keyword scan does not discharge this. |
| AI18 | No prompt residue; no reader directed to `ai-usage.md`, `tokens.md`, scratch paths, or private chats. |
| AI19 | Report whether this exact version is clear to submit. |

**Trail cross-check.** Report four lists with counts: claims with no trail
support (**overstatement**), trail entries with no disclosure (**omission**),
agent review written up as human verification (**AI10**), and confidential
third-party material appearing in a recorded session or a withheld step with
no record (**AI17**). AI10 and AI17 are `[R]` — report them as findings
against the records, not against the manuscript.

**Self-verification (§5).** Every enumeration reports its count. Zero matches
where the repo plausibly has such objects is `EVIDENCE-ABSENT`, never PASS —
"checked N, 0 violations", never bare "no violations". On first run in a repo,
confirm the check can fail against a known-violating synthetic in `scratch/`
(throwaway, not evidence — the report itself goes to `ai/`).

**DEFER** applies only to rules whose evidence is absent, and only to the
face that needs it. Decidable from the `.tex` alone, so never DEFERred for a
missing trail: AI1's textual face (a bare "AI" or unversioned product name
fails outright), AI2, AI3, AI6, AI9, AI12, AI18, AI19. Trail-dependent:
AI4, AI5, AI7, AI8, AI11, AI13, AI14, and AI1's completeness face. Name what
is missing per DEFER, and report the DEFER count in the verdict.

## Report

    CHECK-AI-STATEMENT <repo> <target> <date>
    Policy: <path> (Status: <status>)   Trail: <paths, or ABSENT>
    Verdict: PASS | ADVISORY-PASS | FAIL | ADVISORY-FAIL | DEFER
    Cycle: <n> of 3   Prior report: <path, or none — first run>
    Scope: <n> manuscripts checked   Revision: <commit or version string>
    Rules: <n> checked, <n> delegated [R], <n> DEFER
    Findings: <code> <rule> <quoted evidence>

Finding codes: `FAIL`, `DEFER`, `EVIDENCE-ABSENT`, `FLOOR-BREACH`,
`MALFORMED-POLICY`, `OVERSTATEMENT`, `OMISSION`.

## Routing

Report first, always. On authorization, route — never apply:
failed content rules inside the disclosure → `write-materials-and-methods`,
carrying the **exact required heading string and rule numbers**; an AI6
author-block failure or AI18 residue **outside** the disclosure is not its
property — report those to the human, naming the location; citation
repairs → `clean-citations`; unverified references → `track-down-reference`;
stale or absent trail → `update-ai-usage` / `update-tokens`; a finding no
AI-rule covers → `new-repo-ai-policy`, never by writing past the policy.

**Termination.** Cycle state lives in the report, not in memory: write each run to
`ai/<date>-ai-statement/<target-slug>/report-<n>.md` — keyed on the
target, so two manuscripts audited the same day do not share a cycle counter
— and **read the latest prior report for THIS target before routing**. Stop when a rule FAILs twice with the same
finding, or at cycle 3. Escalate to the human with both verdicts rather than
routing a fourth time — a rule that will not clear is a policy or drafter
defect, not a drafting defect. Absence of a prior report for this target marks
the first run for §5's can-it-fail check.

**AI19 retention.** The report lands in `ai/`, which is durable and travels
with the repository — so the audit IS retained, and AI19's requirement is met
by writing it, not by a human remembering to copy it. Name the report path and
the audited revision in the report and in Report back so the retained artifact
is findable. (This closed a documented gap: while check reports lived in
`scratch/`, AI19's "retained with the submission" was unsatisfiable by the only
skill that could satisfy it.)

Never resolve a FAIL by deleting the disclosure, and never invent a fact to
satisfy a rule.
