---
name: decisions-to-briefs
description: Use when pending decisions are piling up OUTSIDE the brief pipeline — a running decision list in conversation, a batch of "the human adjudicator needs to decide X" items, a decision tally the Mayor is carrying in his head, or a durable decision-inbox directory — and they need to become adjudicable brief artifacts on a pile. Trigger phrases "decisions to briefs", "pile these decisions", "convert the decision list into briefs", "file my pending decisions", "brief my decision inbox". NOT for a single code artifact with runnable tests (use create-brief or brief-prep directly) and NOT for presenting briefs (use present-briefs).
---

# decisions-to-briefs

Convert pending decisions into adjudicable briefs with machine-readable
consequences.

## Overview

**A decision you need to make IS an unfiled brief.** Under the one-bead
model (brief-system POLICY B2.2), a brief bead *is* a decision bead — so a
"running decision list" living in conversation or in the Mayor's tally is
pipeline-invisible debt. This skill drains that debt: each decision becomes
one brief with §1 decision-at-top, a recommended verdict, and an
**ACTION-BLOCK** declaring what happens on each verdict.

Input shapes accepted:

- **one decision** ("should we flip gh-111's closure reason?"),
- **a batch** (the Mayor's 14-item list),
- **a durable decision-inbox** (a directory such as `<city-root>/.beads/decisions/`
  or a `decisions-track` pile — drain everything not yet briefed).

## Procedure

1. **CLASSIFY input type.** Inspect each input item:
   - **`branch-artifact`** — matches `feat/*`, `he-*`, or `gsp-*` prefixes (with a
     live branch), or is a commit hash (40-char hex string, or short 7–12-char hex).
     Route to the branch pipeline ([[create-brief]] / [[brief-prep]]); skip steps 2–6.
   - **`policy-disposition`** — everything else (no git artifact). Continue with
     steps 2–6. New policy-disposition briefs enter the unified pile; they do
     not enter decisions-track as an active presentation lane.
   - Emit one `<item-id>  <class>  pending` line to `classification.log` per
     item immediately after classifying it (before any brief is produced). Write to
     `<CWD>/classification.log` unless an explicit path is provided by the caller.
2. **CLASSIFY the decision shape** (table below). This is the load-bearing
   step: shape determines form, action-block content, and whether any
   auto-action is permitted at all.
3. **PICK compact vs full form.** Same rules as [[present-it]] /
   [[catch-no-brainer]]: compact ONLY for y/n-shaped decisions with no
   safety override; named-options, judgment-heavy, math-content, or
   safety-flagged decisions are full-form. Either way the brief must fit
   **one terminal screen** — full-form here means "carries §options and
   §risks", not "long".
4. **DRAFT the brief**: frontmatter, then §1 "What is being decided" as the
   FIRST body content (Decision-at-Top INVARIANT), then the recommended
   verdict with a one-line rationale.
5. **ATTACH the ACTION-BLOCK** (schema below) as a fenced `yaml` block in
   the brief. Apply the safety invariant BEFORE writing any auto-action.
6. **DEPOSIT on the unified pile via [[create-brief]] conventions** — for a
   policy-disposition, write one file per decision to
   `<city-root>/.beads/briefs/.pile/` as `NN-<slug>-brief.md`, plus one line
   in that pile's `manifest.jsonl`. Never present in the Mayor's terminal;
   `brief-shuffle` promotes gate-clean briefs to the stack and the clerk /
   present-briefs channel drains the stack. Do not file new presentation
   briefs in decisions-track.

## Branch-artifact pipeline

When step 1 routes an item as `branch-artifact`, execute this pipeline instead
of steps 2–6. All git research runs here — before the adjudication session
starts — so present-briefs never issues git calls (REQ-004).

Execute in document order: TS-5 (overlap pre-computation) → TS-2 → TS-3 → TS-3.5 → TS-4 → TS-6 → TS-7.

### TS-5 — Overlap detection (batch of ≥2 branches)

Before generating any brief, compute pairwise file overlap for all
branch-artifacts in the batch:

1. For each branch, compute its changed-file set vs `origin/master` (default
   base — this gives files each branch changes relative to the integration
   target; two branches modifying the same file relative to master will
   conflict on merge):
   `git diff --name-only origin/master..<branch>`
2. Exclude `*.spec` files and `CLAUDE.md` from each set (noise-inducing;
   Q1 resolution).
3. For any pair (A, B) with |intersection| ≥ 1 file, prepare this §6 note
   for injection into each affected brief:
   `Joint evaluation required: shares [<files>] with <other-branch>.
   Regression-test requirement: [relevant test] must pass after merging either branch.`

Single-item batches skip this step.

### TS-2 — Full brief via [[create-brief]]

For each branch-artifact, invoke [[create-brief]] synchronously (inline, same
session). Required sections:

| Section | Content |
|---|---|
| **§1 decision-at-top** | `Keep / delete / merge <branch>?` |
| **§2 origin** | branch creation date; source bead if traceable from name pattern (e.g. `feat/he-XXXX`) |
| **§3 math/content** | file types changed; Magma intrinsics added/modified; `.ipynb` summary if present |
| **§4 git evidence** | `git log --oneline <base>..<branch>`; `git diff --stat <base>..<branch>` |
| **§5 test evidence** | `test-*.mag` files touched; pass/fail if available; `no test evidence` if none |
| **§6 risks** | file-overlap notes from TS-5 (pre-injected); improve-README gate result (record `REVISION REQUIRED — <reason>` but do not block adjudication) |
| **§7 action-block** | `branch-disposition` shape — keep / delete / merge verdict edges |

### TS-3 — Brief stack deposit

After [[create-brief]] produces the brief:

1. Deposit to the brief stack pile as `NN-<slug>-brief.md`. Verify the correct
   pile root against existing create-brief depositions before hardcoding the path.
2. Append one line to `manifest.jsonl` beside the pile:
   `{"n": NN, "slug": "<slug>", "source_bead": "<branch>", "form": "full", "track": "branch-disposition", "status": "ready"}`
3. Do NOT write an inline condensed record to the decisions-track for branch-artifact
   items (see TS-6 for the pointer format written after TS-4).

### TS-3.5 — Pre-compute gate (REQ-004)

Before advancing to the no-brainer filter, assert that every batch item has a
produced brief on disk:

- For each item, verify a brief file `<NN>-<slug>-brief.md` exists in the
  brief stack pile root.
- If any brief is missing (e.g. [[create-brief]] returned a failure), mark
  that item `brief-failed` in `classification.log` and add a note to its
  §risks slot (or create a stub brief containing only the failure reason).
- Do not advance to TS-4 until every item either has a brief file or an
  explicit `brief-failed` annotation.

### TS-4 — catch-no-brainer filtering

After all briefs in the batch are deposited (TS-3 complete), filter each
brief through [[catch-no-brainer]]:

1. Invoke `catch-no-brainer` on the brief file.
2. **If no-brainer criteria are met:** Move the brief file to the no-brainer
   pile directory (`<city-root>/.beads/briefs/.pile/.no-brainer/`) and update the
   corresponding `manifest.jsonl` entry to `"status": "auto-dispatched"`.
   SAFETY NOTE: moving to the no-brainer pile does NOT execute branch
   deletion or any irreversible action. The HARD SAFETY INVARIANT governs —
   auto-dispatch of a brief is not authorization to act on its verdict.
3. **If not a no-brainer:** Leave the brief in the adjudication queue
   (status stays `"ready"` from TS-3).

No-brainer items never reach the human adjudicator's adjudication queue.

### TS-6 — Decisions-track pointer format

After TS-3 deposit and TS-4 filtering, append one pointer entry per
branch-artifact to the decisions-track (e.g.
`<city-root>/.beads/decisions-track/`). Use the pointer format — no inline brief
content:

```yaml
type: pointer
brief_stack_path: <city-root>/.beads/briefs/stack/<NN-slug>-brief.md
status: filed
branch: <branch-name>
```

`brief_stack_path` is the full path to the brief file deposited in TS-3
(e.g. `<city-root>/.beads/briefs/stack/07-feat-he-abc-brief.md`).
`branch` is the branch name (e.g. `feat/he-abc`).

### TS-7 — Classification log finalization

After TS-6, update every `classification.log` entry with its final
disposition:

| Disposition | Meaning |
|---|---|
| `brief-stack` | brief in adjudication queue (normal outcome) |
| `brief-failed` | [[create-brief]] failed; routed to policy-disposition fallback |
| `auto-dispatched` | moved to `.pile/.no-brainer/` by TS-4 |
| `filed` | decisions-track pointer written by TS-6 |

One finalized line per item; overwrite the `pending` placeholder written
in Procedure step 1. Final format: `<item-id>  <class>  <disposition>`.

## Shape classification

| Shape | Symptoms | Form | Auto-action allowed? |
|---|---|---|---|
| **compact y/n** | one reversible dispatch hangs on approval ("sling X?") | compact | yes — `sling-bead`, `wire`, `file-follow-up-brief` |
| **named options** | genuine alternatives a/b/c to weigh | full | yes, per chosen option, if reversible |
| **human-manual-math** | verdict requires the human adjudicator's mathematical judgment (done-vs-residual, proof content) | full, flagged | **NO** — `external-reminder` only |
| **external-reminder** | only a human can act (interactive auth, credential entry, physical/console step) | compact | **NO** — `external-reminder` only |
| **stays-out** | irreversible, server-live-write, or user-skill-touching consequence | full | **NEVER** — explicit human gate, per-node auth where applicable |

When unsure between two shapes, take the more restrictive row.

## ACTION-BLOCK schema

Every brief carries exactly one `action_block`, a fenced `yaml` block. Each
verdict key maps to an ordered list of action items:

```yaml
action_block:
  on_approve: [ {type: <action-type>, target: <bead-id|slug|path>, ...} ]
  on_reject:  [ {type: <action-type>, target: ..., ...} ]
  on_defer:   [ {type: snooze, interval: <e.g. 7d>} ]
```

Rules:

- All three keys REQUIRED. An empty list `[]` is valid and means "record
  the verdict, do nothing else".
- `on_defer` is always exactly `[{type: snooze, interval: ...}]` — defer is
  not an adjudication (POLICY verdict vocabulary); the brief resurfaces
  after the interval.
- Extra keys per item are type-specific (e.g. `worker:` for sling-bead,
  `note:` for external-reminder).
- The block is *declarative*: this skill only writes it. Execution belongs
  to the brief-record-decision verdict edge (part b of gsp-ft64, not yet
  live) or to the Mayor acting on the recorded verdict.

### Action-item types

| type | Meaning | Reversible? |
|---|---|---|
| `sling-bead` | dispatch `target` bead to a convoy/worker (`worker:` optional) | yes — a slung bead can be recalled/closed |
| `file-follow-up-brief` | create a successor brief for the next decision this one exposes | yes |
| `wire` | graph surgery: `op: dep-add \| attach-epic \| create-epic`, plus `target` | yes |
| `close-supersede` | close `target` bead(s) with a supersede reason naming the winner | yes (reopenable) |
| `run-skill` | run a named audit/hygiene skill (e.g. `bead-check`) on `target` | yes (read-only skills only) |
| `external-reminder` | CANNOT automate — re-surface `note:` to the human; the verdict edge must ping, never act | n/a |

For `sling-bead`, include provenance fields so the brief-system dispatch edge
produces the same canonical event as work-system dispatch:

```yaml
provenance:
  dispatch_source: decisions-track
  source_decision: manifest-entry-or-brief-path
  expected_provenance_schema: dispatch-provenance.v1
  canonical_record: linked type=event bead
```

The verdict executor must create or reuse that linked `type=event` bead before
presenting any table or file export as dispatch evidence.

## HARD SAFETY INVARIANT

**Action-blocks auto-execute ONLY reversible dispatch** (`sling-bead`,
`file-follow-up-brief`, `wire`, `close-supersede`, read-only `run-skill`).

**Irreversible, server-live-write, or user-skill-touching decisions carry
NO auto-action.** Their action-block entries are `external-reminder` (or
nothing), and the brief is full-form with the hazard named in §risks. The
human gate is the action. Canonical example: **#335 N2s/N2 server
writeback must NEVER be an auto-slinging brief** — it stays
external-reminder with explicit per-node authorization.

Concretely, NO auto-action for: git push / force-push / merge / branch or
tag deletion ([[authorize-git-operation]] territory), `gh issue close` or
other live GitHub writes, database/server writebacks, edits to user-scope
skills (`user_skill_touching_override`), credential operations, deletion of
non-regenerable data.

Red flags — if you catch yourself writing any of these, STOP and downgrade
the item to `external-reminder`:

| Rationalization | Reality |
|---|---|
| "The approve verdict already authorizes the push" | A verdict on a brief is not [[authorize-git-operation]]. Two different gates. |
| "It's a tiny server write, easily undone" | Server-live-write is a category, not a size. Per-node auth or nothing. |
| "The worker will re-check before acting" | The action-block IS the check. Downstream re-checks are backstops, not permission. |
| "Wrapping it in a slung bead makes it reversible" | Slinging a bead whose *content* is irreversible launders the hazard. Classify by the terminal effect. |

## Decision briefs vs the create-brief gates

These briefs decide *dispositions*, not code artifacts: [[create-brief]]'s
test-evidence and good-test gates are **N/A by construction** — declare
`gates: test-evidence N/A (decision-shaped, no runnable artifact)` rather
than silently skipping. The Decision-at-Top INVARIANT and critical-review
hygiene still apply in full.

## Pile + manifest conventions

- Policy-disposition files: `<city-root>/.beads/briefs/.pile/NN-<slug>-brief.md`,
  zero-padded, one decision each. The unified pile is the only active intake
  lane; `brief-shuffle` owns promotion to `stack/`.
- Frontmatter (minimum):
  ```yaml
  artifact: <bead-id-or-none>
  brief_kind: decision
  gate_profile: decision
  feedback_sink: brief_quality_failure
  classifier_state: known_non_no_brainer
  legacy_source: null
  status: ready-for-adjudication
  form: compact|full
  track: policy-disposition
  ```
- `manifest.jsonl` beside the briefs, one line per brief:
  `{"n": 1, "slug": "...", "source_bead": "...", "form": "compact",
  "track": "...", "status": "ready"}` — so the presenter can count and
  order without opening files.
- decisions-track records are legacy compatibility/migration mappings only:
  write pointer records when migration compatibility requires them, never a
  new ready-to-present policy-disposition brief.
- Verify freshness before drafting: `bd show` every source bead — a closed
  or deferred source changes the decision (e.g. "approve the audit" becomes
  "approve the delivered plan"). Record any such reclassification in the
  brief.

## Cross-references

- [[create-brief]] — artifact format, frontmatter schema, clerk-channel
  delivery this skill deposits through.
- [[catch-no-brainer]] / [[present-it]] — compact-eligibility rules and
  both body templates.
- [[present-briefs]] / [[adjudicate-brief]] — how the pile drains.
- [[brief-prep]] — safety-override mechanics (`server_touching`,
  `user_skill_touching_override`).
- `brief-record-decision` formula — the verdict edge that part (b) of
  gsp-ft64 extends to parse and execute action-blocks.
- [[file-briefs]] (gsp-geuo) — the onboarding sibling this skill
  generalizes; wire as related, do not compete.

## Example Mapping

**Example D — Policy question (policy-disposition):**
- Input: `'should we extend the Dolt retention window to 90 days?'` (no branch, no
  commit hash)
- Artifact type: `policy-disposition` → continues through steps 2–6
- Shape: **named options** (yes / no / defer on the retention window)
- Form: compact (reversible y/n scope)
- Outcome: condensed brief produced via the existing procedure; no
  [[create-brief]] skill invocation; deposited to the unified brief-stack
  `.pile` per §Pile conventions

## Versioning

- **v0.1 — MVP** (2026-07-16, epic gsp-ft64): classification + form pick +
  action-block schema + safety invariant + pile deposit. Calibration run =
  the 14-item decision list piled at `<city-root>/.beads/decisions-track/`; per
  gsp-ft64 notes, after 10 adjudications the accumulated verdict data
  triggers part (b) — the full 3-part design (skill + schema + verdict-edge
  execution).
- **v0.2 — branch-artifact pipeline** (2026-07-20, he-timtb): TS-5 overlap
  detection, TS-2 full brief via [[create-brief]], TS-3 brief stack deposit.
- **v0.3 — no-brainer filtering + pointer format** (2026-07-20, he-19qmt):
  TS-4 catch-no-brainer pass post-deposit; TS-6 decisions-track pointer
  format (no inline content).
- **v0.4 — pre-compute gate + classification log + origin/master base**
  (2026-07-20, he-3szhj, fixes he-ipwws): REQ-004 pre-compute gate
  (TS-3.5) requiring every batch item to have a brief before advancing;
  classification.log per-item tracking (Procedure step 1 + TS-7); TS-5
  overlap detection now uses `origin/master` as default base (F-001)
  instead of `git merge-base`.
- **v0.5 — review fix: field name, disposition labels, execution order, patterns**
  (2026-07-20, he-sy68y): RF-1 rename `brief_stack_ref` → `brief_stack_path` with
  full path in TS-6; RF-2 align TS-7 disposition labels (`brief-ready` →
  `brief-stack`, `no-brainer` → `auto-dispatched`) with REQ-005/AC-7; RF-3 add
  execution-order sentence to branch-artifact pipeline; RR-1 add `gsp-*` classification
  pattern; RR-2 document `classification.log` default path convention.
