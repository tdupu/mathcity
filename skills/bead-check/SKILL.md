---
name: bead-check
description: >-
  Use when the disposition of a specific bead is in question — stale, possibly
  superseded, mis-filed, orphaned, or in the wrong rig — and a recommendation
  is needed before anyone acts on it. Trigger phrases: "bead-check <id>",
  "check this bead", "is this bead stale", "is this bead still valid",
  "triage this bead", "should this bead be closed", "should this bead be
  re-homed", "what should happen to <bead-id>", "audit bead <id>", "is this
  bead superseded", "does this bead belong in this rig". Also use during
  backlog sweeps when old beads (stale `updated` dates, no parent, no labels)
  surface in `bd ready` or `bd list`. NOT for executing dispositions — this
  skill only diagnoses and proposes; execution routes to gc-recycle-bead,
  intercept-bead, handoff-bead, or the Mayor's dispatch pipeline.
---

# bead-check

Diagnose ONE bead against all current policies and in-flight work, and emit a
structured **recommendation** for what should happen to it. This is the
diagnostic front-end of the bead-lifecycle toolset: it never changes anything.

**Core principle: agents propose, the human adjudicator/Mayor disposes** (human-final-judge-sort,
the human adjudicator 2026-06-22). A bead-check that mutates the store is a failed bead-check.

## Pre-flight (P1.14)

bead-check depends on the live bead store. Before anything else, probe it:

```bash
bd show <bead-id>
```

If `bd` hangs, errors, or the connection is refused:

```
I'm sorry, I can't do that — the bd bead store is unreachable (Dolt server down or bd misconfigured).
Run `gc dolt status` (then `gc dolt start` if stopped) to bring the data plane up.
(bead-check diagnoses live bead state; without the store there is nothing to check.)
```

If the store is up but the bead id does not exist:

```
I'm sorry, I can't do that — bead <bead-id> was not found in this store.
Run `bd search "<keywords>"` to locate it, or check the rig: cross-side beads only appear after a dolt-remote sync.
(A bead absent here may live in another rig's store — see D4.)
```

Never proceed past a failed probe; never diagnose from `.beads/issues.jsonl`
alone (it is a passive export — the bead store is canonical, B2.8).

## Read-only contract

| Allowed (evidence gathering) | NEVER (execution — refuse, propose instead) |
| --- | --- |
| `bd show`, `bd list`, `bd search`, `bd ready`, `bd dep tree`, `bd epic list`, `bd comments`, `bd recall` | `bd update`, `bd close`, `bd create`, `bd delete`, `bd label`, `bd reopen`, any `--claim` |
| `git log`, `git branch -a`, `git show`, `ls`, `grep`, `gh issue/pr view` | `bd defer`, `bd dolt push`, `bd backup`, `bd import` |
| `gc dolt status`, `gc agent list` (context only) | `gc sling`, `gc mail send` (dispatch), `git commit`, `git push` |

**Red flags — STOP, you are about to execute, not check:**
- You typed `bd update` or `bd close` "to save a round trip."
- "the human adjudicator said *sort it out / handle it / deal with it*" — that is a request
  for a recommendation plus a handoff, not authority to mutate. Produce the
  mini-brief; the named executor skill runs as a separate, authorized step.
- "It's obviously superseded, closing is a no-brainer" — no-brainer execution
  is the pipeline's call (catch-no-brainer → auto-execute lane), never
  bead-check's.
- You are drafting a `gc sling` command to run rather than to quote.

## Output contract — the recommendation mini-brief

The output IS this shape, in this order. The recommendation comes FIRST
(Decision-at-Top invariant, same as [[present-it]]); the five determinations
follow as evidence. All five are REQUIRED slots — a determination that does
not apply is stated as `n/a — <one-line reason>`, never silently omitted.

```
BEAD-CHECK <bead-id> — <title>
RECOMMENDATION: <disposition from D5 table> — <one-line rationale> (confidence: high|med|low)

D1 Out of date? <yes|no|partial> — <evidence>
D2 Filed correctly? <yes|no> — <type/priority/labels/body/prefix findings>
D3 Epic/convoy membership? <ok|orphan|wrong-parent> — <evidence>
D4 Appropriate rig? <yes|no → rig X> — <evidence>
D5 Disposition & routing: <executor skill or actor> ; proposed command (NOT run): `<exact command>`
```

## Lost-Bead Classification Output

When the checked bead may be lost, stale, stranded, blocked, superseded, or
no-fire, append a fenced TOML block using
`schema = "lost-bead-classification.v1"`.

```toml
schema = "lost-bead-classification.v1"
bead_id = "example-bead-id"
observed_at = "2026-07-25T00:00:00Z"
observer = "bead-check"

[finding]
lost_class = "immediate_strand"
evidence = ["specific command output or observation"]

[disposition]
recommendation = "resling"
rationale = "The bead is still valid, but no worker claimed the dispatch."
reversible = true

[root_cause]
class = "no_worker_claimed"
suspected_source = "mathcity.work"
repair_candidate = true
fingerprint = "empty_assignee_after_verified_sling"
```

Use only categories from `assets/bead-filter/lost-bead-schema.toml`. Set
`repair_candidate = true` only when the evidence points to a repeatable
upstream process failure. This block is observation output only; `bead-check`
remains read-only and must not mutate bead state. To persist it, a caller
creates a linked `type=event` bead using this TOML as the event description or
attached evidence.

## The five determinations

### D1 — Out of date?

Is the bead stale or superseded? **Verify at source — the truth is in the
code, not in the bead body or any plan narrative** (P5.4,
`mathcity/subdomains/dev/POLICY.md`):

- `updated` date vs. rig activity since (`git log --since=<updated>` on the
  target repo; `bd list` for younger sibling beads).
- Do the referenced files, branches, commits, beads still exist? (`ls`,
  `git branch -a`, `git show <sha>`, `bd show <ref-id>`.)
- Do the bead's premises/claims still hold in current source? A claim
  contradicted by the code = stale, regardless of the bead's age.
- Has newer work superseded it? `bd search` on the bead's keywords; check
  in-flight branches and open PRs (`gh pr list`). If a superseding bead is
  still **in flight** (created on the other side of a dolt remote, not yet
  synced), that is [[intercept-bead]] territory — say so in D5.

### D2 — Filed correctly?

- **Type** is a real documented bd type — `bug`, `feature`, `task`, `epic`,
  `chore`, `decision`, `spike`, `story`, `milestone`, `event` (P5.3; no
  hallucinated types). Is it the *right* one (decision for verdicts, epic for
  containers, spike for research probes)?
- **Priority and labels** present and sane; body structured (context /
  acceptance / references), the human adjudicator-verbatim anchor preserved for math content.
- **Rig prefix — Rule 4** (`mayor-math` SKILL.md): the prefix must match the
  work's target repo:

  | Work targets... | Prefix |
  |---|---|
  | `gastownhall/gascity` core | `gs-` |
  | `gastownhall/gascity-packs` | `gsp-` |
  | `gastownhall/agent-skills` | `as-` |
  | `<city-root>` config repo | `gt-` |
  | hecke math repo | `he-` |

  A prefix/target mismatch is a mis-filing → D4 decides the rig, D5 proposes
  the re-home.
- **No meta-sequencing** (the human adjudicator 2026-06-23): a bead must not prescribe
  install-order or composition-order between work items ("install X before
  Y") — composition happens at runtime via registry discovery. Sequencing
  language in the body → recommend re-scope.
- Brief beads: under the **one-bead model** (brief-system POLICY.md B2.2) the
  brief bead IS the decision bead — verdict recorded on it, then closed. A
  second decision bead attached to a brief, or an adjudicated brief bead
  still open, is a filing defect. Never recommend reopening an adjudicated
  brief — circumstances changed means a NEW bead linking the old (B2.3).

### D3 — Epic/convoy membership?

- Parent set? If not: does an open epic or owned convoy naturally contain
  this work? (`bd epic list`, `bd dep tree <candidates>`, `bd search` on the
  feature area.) An orphan that belongs to a live epic → attach.
- **Child inherits parent disposition** (the human adjudicator 2026-06-22): children of
  move-beads move, children of stay-beads stay. If the parent was re-homed,
  closed, or archived, this bead presumptively follows — flag explicit
  exceptions rather than silently diverging.

### D4 — Appropriate rig?

Determine where the work actually lands: **which repo's files would change**,
and whose worker fleet would execute it. That question alone decides the rig —
not where the idea originated, who filed it, which workspace "owns the topic,"
or where related beads live. A bead whose body names paths in repo X belongs
to repo X's rig, full stop (Rule 4 table as the map). If the bead sits in the
wrong rig's store:

- Recommend **re-home to rig X**. Cross-side bead flow happens ONLY through
  the rig's dedicated dolt remote `<github-owner>/<X>-dolt` (`bd recall
  dolt-remote-topology`; P1.15) — never by copying jsonl, never through the
  code remote.
- Every DoltHub/dolt remote involved must be **private** (P1.11; the human adjudicator hard
  guard 2026-06-25: all `<github-owner>/*` DoltHub repos PRIVATE — a public target
  means HALT the sync recommendation and flag it as its own finding).

### D5 — Recommendation & routing

Pick ONE primary disposition and name who executes it. Reference executors —
do not perform their job here:

| Disposition | When | Route to |
| --- | --- | --- |
| **close-superseded** | Done/obsolete, no unique content | Propose `bd close <id> --reason ...` for the human adjudicator/Mayor to run |
| **recycle** (absorb / archive / materialize) | Superseded but carries unique findings, research context, or long notes | [[gc-recycle-bead]] |
| **reconcile-inflight** | A new bead in flight supersedes/affects this one | [[intercept-bead]] |
| **re-home to rig X** | D4 mismatch | [[handoff-bead]] (cross-rig, via `<github-owner>/<X>-dolt`) |
| **re-scope** | Premises partly hold; goal valid but body stale, over-broad, or carries meta-sequencing | Propose replacement body/scope text for the human adjudicator/Mayor; new bead if the old one is adjudicated |
| **fix-filing** | Wrong type/priority/labels/body only | Propose exact `bd update` flags, not run |
| **attach to epic Y** | D3 orphan with a live parent | Propose the dep/parent command, not run |
| **keep-and-dispatch** | Valid, ready, right rig — feed it to that rig's machine | Name the sling target: `gc sling <rig>/<agent> ...`; route via the Mayor or [[sling-new-bead]] |
| **defer** | Valid but blocked/not-yet | Propose a timed defer window |

If the check itself surfaces a verdict worth preserving (a policy call, an
architecture judgment), route it to [[adjudicate-brief]] — bead-check does
not record decisions either.

## Policy checklist (cite what you judged against)

| Policy | Source | Bears on |
| --- | --- | --- |
| P5.4 verify-at-source | `mathcity/subdomains/dev/POLICY.md` | D1 |
| P5.3 real bd types only | same | D2 |
| Rule 4 rig prefix | `mathcity/skills/mayor-math/SKILL.md` | D2, D4 |
| B2.2 one-bead model, B2.3 no-resurface, B2.8 bead store canonical | `mathcity/subdomains/brief-system/POLICY.md` | D2, pre-flight |
| child-inherits-parent-disposition (the human adjudicator 2026-06-22) | bd memory index | D3 |
| no-meta-sequencing (the human adjudicator 2026-06-23) | bd memory index | D2 |
| dolt-remote-topology (`bd recall dolt-remote-topology`), P1.15 | bd memory + dev POLICY.md | D4 |
| P1.11 / DoltHub-all-private (the human adjudicator 2026-06-25) | dev POLICY.md + bd memory index | D4 |
| human-final-judge-sort (the human adjudicator 2026-06-22) | bd memory index | whole skill |

## Common mistakes

- **Checking only staleness.** Baseline agents answer "is it stale?" and
  stop — missing the wrong prefix, the orphanhood, the sequencing language in
  the body. All five determinations, every time; `n/a` needs a reason.
- **Executing the recommendation.** See the read-only contract. The
  recommendation names the executor; it is not the execution.
- **Trusting the bead body over the code** (P5.4) — bodies rot; re-verify
  branches, files, and claims at source before calling anything current.
- **Burying the verdict.** The RECOMMENDATION line is the first line after
  the header — evidence follows it, never precedes it.
- **Judging the rig by topic instead of file targets.** "It's filed where
  that policy area lives" is the standard rationalization for a Rule 4
  mismatch — the rig follows the files the work changes, nothing else.
- **Recommending reopen of a closed brief bead** — B2.3: new bead, link the
  old one as source.
