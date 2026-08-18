# Issue Investigation Standard

The single, target-parameterized statement of the investigation a maintainer would
otherwise have to redo. Both MathCity issue-filing surfaces read **this file** —
they do not restate it:

| Surface | Kind | Reads this file |
| --- | --- | --- |
| `create-issue` | skill (interactive) | walks stages 1–9 with a human in the loop |
| `mathcity-issue-briefed` | formula (dispatchable) | gates `intake` on stages 1–7, then drafts and briefs |

Ported from [`contributing/skills/write-issue`](https://github.com/gastownhall/gascity-packs/tree/main/contributing/skills/write-issue)
(gascity-packs-owned, read-only to us — `subdomains/dev/POLICY.md` P2.1). The
discipline is preserved at full rigor. The one substantive change is **targeting**:
upstream hardcodes `gastownhall/gascity` throughout, which has to be mentally
re-substituted on every use. Here the target repo is a declared parameter.

---

## Stage 0 — Resolve the target repo (REQUIRED, FIRST)

`$TARGET_REPO` is an **input**, not an assumption. Resolve it before anything else
and echo it back to the human so a wrong target is caught at the start rather than
at `gh issue create`.

| `$TARGET_REPO` | When | Design/policy corpus for stage 4 | Templates |
| --- | --- | --- | --- |
| `tdupu/mathcity` **(DEFAULT)** | Anything in this pack — skills, formulas, orders, gates, agent configs, and the docs describing them | `POLICY-*.md` at pack root, `subdomains/*/POLICY.md`, `docs/adr/*.md` | `.github/ISSUE_TEMPLATE/{bug_report,feature_request,docs_report}.yml` |
| `gastownhall/gascity` | Bugs and features in the `gc` / `bd` **binaries** themselves | `engdocs/design/*.md` | that repo's live `.github/ISSUE_TEMPLATE/` |
| `tdupu/gascity-packs` | Fork-local pack content that is not upstream-owned | pack-local `REQUIREMENTS.md` / `README.md` | that repo's live `.github/ISSUE_TEMPLATE/` |

**Routing rules:**

- **Default to `tdupu/mathcity`.** Filing here is the common case; the other two are
  explicit, less-common alternatives selected by passing the target.
- **Upstream-owned `gascity-packs` content routes to `gastownhall/gascity`.**
  `subdomains/dev/POLICY.md` P3.2: "All upstream issues for `gastownhall/gascity`
  and `gastownhall/gascity-packs` are filed on `gastownhall/gascity`."
  `tdupu/gascity-packs` is selectable for genuinely fork-local content only.
- **Split issues get split filings.** When a MathCity skill misreads something `gc`
  reports, the `gc` half is a `gastownhall/gascity` issue and the skill half is a
  `tdupu/mathcity` issue. File both and cross-link them
  (`.github/ISSUE_TEMPLATE/bug_report.yml`).
- **Not upstream-relevant at all?** If the behavior is specific to one local
  deployment or config, stop — do not file it anywhere.

If the target cannot be resolved, **stop and say so** (P6.1 — fail loud):

```
I'm sorry, I can't do that — the target repo for this issue is unresolved.
Pass it explicitly (skill: state the repo; formula: --var target_repo=owner/name).
(The target decides which duplicate list, which main branch, which design corpus,
and which issue templates this investigation runs against.)
```

Everything below runs **against `$TARGET_REPO`**.

---

## Stage 1 — Triage the observation

Decide three things:

- **In scope for `$TARGET_REPO`?** Per the stage 0 routing rules. Local-only → stop.
- **Kind:** `bug` / `feature` / `docs`. This selects the issue template in stage 8.
- **Rough priority:** P1 (breaks many users / data loss / unrecoverable) / P2
  (significant friction, workaround exists) / P3 (polish, nice-to-have). Priority is
  about how many users hit it and how recoverable it is — **not** how loud it was
  for you. Most ergonomics issues are P3.

## Stage 2 — Search for duplicates (REQUIRED — do not skip)

Before any investigation. Three searches minimum, different keyword combinations:

```bash
gh issue list --repo "$TARGET_REPO" --state all --search "<core-symptom-keywords>" --limit 20
gh issue list --repo "$TARGET_REPO" --state all --search "<file-or-component-name>" --limit 20
gh pr list    --repo "$TARGET_REPO" --state all --search "<core-symptom-keywords>" --limit 20
```

If you find a match:

- **Open issue, no resolution:** add your repro / extra context as a comment. Done —
  do not open a second issue.
- **Open issue, already in flight (assignee or recent activity):** same — comment and
  link. Done.
- **Closed-fixed:** check whether the fix is in the version you observed the bug on.
  If the fix shipped and you still hit it, that is a *regression* — file a NEW issue
  and reference the original.
- **Closed-wontfix / not-planned:** read the discussion first. There may be a
  deliberate decision you are missing. Do not silently refile.

## Stage 3 — Verify the problem exists on current main (REQUIRED)

The most common failure mode: a bug seen on an old version or a feature branch is
reported as if it is on `main`, but `main` already fixed it (or never had the buggy
code). Verify against an up-to-date checkout of `$TARGET_REPO`'s main.

> **Which remote?** If you cloned `$TARGET_REPO` directly, its main is `origin/main`.
> If you forked first and cloned the fork, your `origin` is the fork — add the
> upstream once (`git remote add upstream https://github.com/$TARGET_REPO && git
> fetch upstream`) and read `upstream/main` everywhere `origin/main` appears below.
> For `tdupu/mathcity` the standalone source checkout's `origin` **is** the target
> (P1.7), so `origin/main` is correct.

```bash
git fetch origin && git log -1 origin/main --oneline    # confirm the tree is current
git checkout origin/main

# locate the symptom in code
grep -rn "<error-string-or-symbol>" --include="*.go" --include="*.py" --include="*.toml" --include="*.md"

# read the relevant function(s)/section(s) and confirm the buggy path is on main
sed -n '<line-range>p' <file>

# look for recent fixes that might already be in flight
git log --oneline -20 -- <affected-files>
git log --oneline -S "<key-symbol-or-comment>" -20
```

| Finding | Action |
| --- | --- |
| Buggy code path present on main | Continue to stage 4 |
| Buggy code path absent on main (already refactored) | Find the commit that fixed it (`git log`). Do not file — the fix is already in. If it has not been released/installed yet, note that on the relevant PR instead |
| Buggy code path present, but a recent commit/PR already addresses it | Reference that PR in your issue, or comment on it — do not duplicate |

For a `feature` or `docs` issue the same gate applies in its natural form: confirm
the capability is genuinely absent, or the documentation genuinely wrong, **on
current main** — not merely on the version installed locally. For `tdupu/mathcity`
specifically, the installed pack and `origin/main` diverge routinely; the deployed
commit is what you *observed*, `origin/main` is what you *file against*, and
`.github/ISSUE_TEMPLATE/bug_report.yml` asks you to confirm both.

## Stage 4 — Check architectural alignment (REQUIRED — do not skip)

The area you are touching may already be governed by an accepted design document.
Fix candidates that contradict an accepted design waste a maintainer's review.
Which corpus to read is set by `$TARGET_REPO` in the stage 0 table.

```bash
# --- gastownhall/gascity ---
grep -lE "^\| Status \|.*\b(Accepted|Implementing|Implemented)\b" engdocs/design/*.md
grep -nE '<symptom-keyword>' engdocs/design/<candidate>.md

# --- tdupu/mathcity ---
grep -nE '<symptom-keyword>' POLICY-*.md subdomains/*/POLICY.md docs/adr/*.md

# either target: is an open PR already continuing the refactor in this area?
gh pr list --repo "$TARGET_REPO" --state open --search "<area-keyword>" --limit 20
```

For `tdupu/mathcity` the "design corpus" is the P-rules (`subdomains/dev/POLICY.md`),
the domain policies (`POLICY-formulas.md` F-rules, `POLICY-beads.md`,
`POLICY-POLICY.md`), and the ADRs. A proposal that violates a P-rule or an F-rule is
not a proposal — it is a policy-amendment request, and it routes through the
relevant `new-*-policy` skill instead.

| Finding | Action |
| --- | --- |
| No design doc or policy covers the area | Continue to stage 5 |
| A doc covers the area and describes a DIFFERENT paradigm than your fix implies | Do not draft fix candidates from scratch. Read the section. Either revise your candidates to align, or state in the body that the symptom contradicts invariant `<X>` (with file/line ref) and ask which way to fix |
| A doc covers the area and your fix lands in the SAME paradigm | Cite the section in "Root cause" — frame the bug as "violates §X of doc Y". Signals you did the homework |
| A doc covers the area and the relevant phase is queued | Your candidates may be superseded. Propose a narrow point-fix the upcoming work can absorb, or comment on the design discussion instead of filing fresh |

## Stage 5 — Reduce to a minimum reproduction

Distill the observation to the smallest reproduction someone else can run:

- The exact command, `gc` subcommand, skill invocation, or API call that triggers it
- The city/rig state required (running, supervisor mode, which pack version deployed)
- Expected vs. actual behavior
- If timing-sensitive: the race window

**An MRE is NOT a filing gate.** Reduction is often the hardest part of the work,
and some real defects resist it for a long time — blocking the filing on a clean
repro loses the report and the investigation that went with it. A bug may be filed
without one.

What is required instead is that the gap be **visible rather than silent**. When you
cannot reduce it, write the reproduction field as exactly:

> `not yet reduced — reduction is step 1`

plus what you did try and why it resisted. Reducing it then becomes the **first work
step** when the issue is picked up, not a precondition for recording it.

Still prefer reduction when it is achievable: an MRE is the single most useful thing
in a bug report, and inability to write one usually means the defect is not yet
understood. The change here is that "not yet understood" is a thing to record, not a
reason to stay silent.

For Magma-language MREs specifically, the MRE file itself is validated separately by
[`check-mre`](../subdomains/computing/skills/check-mre/SKILL.md) against the
project's `.claude/MRE-POLICY.md` — run it before attaching.

## Stage 6 — Map blast radius (for non-trivial bugs)

For anything touching a reconciler, controller, lifecycle, dispatcher, the brief
pipeline, or any subsystem with cross-cutting effects:

- Who calls the affected function/skill/formula? Are any on hot paths (tick loops,
  reconciler loops, supervisor ticks, hot HTTP routes)?
- Does it interact with config reload? Session lifecycle? Shared state? The Dolt
  data plane?
- What test layer would catch it (unit, smoke, acceptance, integration)? Does any
  existing test cover the path? For this pack that means: is there a
  `tests/<name>/smoke_test.sh`, and does it assert the broken property?

This feeds the "Root cause" and "Fix candidates" fields.

## Stage 7 — Draft fix candidates (≥ 2)

Name **at least two** fix candidates before writing the body. A single-candidate
issue forecloses the discussion. Two candidates expose the trade-offs (correctness
vs. backwards-compat, complexity vs. blast radius, point-fix vs. structural).

Each candidate gets:

- A one-line description
- A rough scope (LOC, files touched)
- The trade-off it represents

Mark which one you would recommend and why — but leave the decision to the
maintainer.

## Stage 8 — Fill the target repo's live issue template

**Do not compose a body from memory, and do not restate a template that lives in the
repo.** Read the template off `$TARGET_REPO` at draft time — it is the enforcement
point, and it changes without telling you.

```bash
# from a checkout of $TARGET_REPO
ls .github/ISSUE_TEMPLATE/
# or, without a checkout:
gh api "repos/$TARGET_REPO/contents/.github/ISSUE_TEMPLATE" --jq '.[].name'
```

Pick the template by the stage 1 kind (`bug` → `bug_report.yml`, `feature` →
`feature_request.yml`, `docs` → `docs_report.yml` — names vary per repo; use what is
actually there). Then:

- **`.yml` GitHub form:** map your investigation onto each form field's label, in the
  template's order. Every field marked `validations: required: true` must be filled.
  Required checkboxes are assertions — tick them only if they are **true** (on
  `tdupu/mathcity` they assert the duplicate search of stage 2 and the
  verify-on-main of stage 3 actually happened).
- **`.md` template:** fill its sections in order.
- **No template in the repo:** produce a plain `## Summary` / `## Details` body.

**Never invent** reproduction steps, versions, line numbers, or evidence the
investigation did not produce. Mark an unknown field `<unknown — needs input>` and
surface it for the human to fill. A fabricated root cause attached to a real symptom
is harder to unpick than no root cause at all.

**Title conventions** (match the target's existing issue list; `tdupu/mathcity`'s
templates prefill the prefix):

- `bug: <surface>: <symptom>`
- `feat: <surface>: <capability>`
- `docs: <area>: <correction>`

## Stage 9 — Approval gate, then file

**Nothing files an issue before a human approves the exact body.** This is the
`create-issue-briefed` property (P3.2) and it survives every composition:

1. Present the paste-ready body — through the brief pipeline for the formula
   surface, or in-conversation for the skill surface.
2. Wait for a verdict. APPROVE files it; REVISE returns to stage 8; REJECT drops it.
3. Only after APPROVE:

```bash
gh issue create --repo "$TARGET_REPO" \
  --title "<kind: surface: short imperative title>" \
  --body-file <approved-body-file> \
  --label "kind/<bug|feature|docs>,priority/p<1|2|3>,status/needs-triage"
```

The `.yml` templates already apply `kind/*` and `status/needs-triage` when a human
files through the web form; `gh issue create --body-file` bypasses the form, so pass
the labels explicitly. On `tdupu/mathcity` the `priority/*` and `status/*` labels may
not exist yet (`.github/LABELS.md`) — GitHub silently drops unknown label names, so
the issue still files, just unlabeled.

---

## Anti-patterns

- ❌ **Assuming the target repo.** The defect this standard exists to fix. Nine
  hardcoded `gastownhall/gascity` references in upstream `write-issue` had to be
  mentally re-substituted on every use; issues #7–#11 on `tdupu/mathcity` were only
  filed correctly because each subagent was *told* in its prompt to substitute. Load-
  bearing instructions that live in a prompt are instructions that get forgotten.
- ❌ **Filing without verifying the problem still exists on current main.** Stage 3.
- ❌ **Filing without a duplicate search.** Stage 2. Wastes everyone's time when it is
  already tracked.
- ❌ **Filing without checking the design/policy corpus.** Stage 4. Candidates that
  contradict an accepted invariant get retracted on the first maintainer pass — even
  when you "already know the fix".
- ❌ **Symptoms-only body, no root-cause `file:line` refs.** The maintainer has to
  redo your investigation. P3 at minimum, or write the refs.
- ❌ **Single fix candidate.** Forecloses the design space.
- ❌ **A missing MRE left implicit.** Stage 5. Filing a bug without a reproduction is
  allowed; leaving the reader to *discover* that it has none is not. Write
  `not yet reduced — reduction is step 1` in the reproduction field.
- ❌ **Restating the issue template inside the issue body.** The template in the repo
  is the enforcement point; a hand-copied version drifts silently.
- ❌ **Skipping "out of scope" / "adjacent".** Adjacent-looking issues that are not
  part of the fix cause scope creep; naming them upfront prevents it.
- ❌ **Filing as P1 because it felt big.** Priority is reach and recoverability.
- ❌ **Calling `gh issue create` before the approval verdict.** Stage 9.

## Pre-flight checklist

- [ ] `$TARGET_REPO` resolved **explicitly** and echoed back — not assumed (stage 0)
- [ ] Routing checked: is this actually a `gc`/`bd` binary issue that belongs on
      `gastownhall/gascity`, or a split issue needing two cross-linked filings?
- [ ] Searched duplicates, 3+ searches, open **and** closed — none matching (stage 2)
- [ ] Confirmed the problem exists on `$TARGET_REPO`'s current main today
      (`git rev-parse origin/main`, or `upstream/main` if origin is your fork)
- [ ] Checked the target's design/policy corpus; cited the relevant section OR
      confirmed none applies (stage 4)
- [ ] Have `file:line` refs for the root cause
- [ ] MRE present (REQUIRED for `kind/bug`), or the kind was re-chosen (stage 5)
- [ ] Have ≥ 2 fix candidates with trade-offs named, and they do not contradict an
      active invariant (stage 7)
- [ ] Body fills the target repo's **live** template; every required field complete;
      required checkboxes true; no invented evidence (stage 8)
- [ ] Human APPROVE verdict recorded **before** `gh issue create` (stage 9)
