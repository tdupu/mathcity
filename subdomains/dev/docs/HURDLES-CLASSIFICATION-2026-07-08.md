# Hurdle Classification and Disposition

Review date: 2026-07-08. Pack: `<mathcity-pack-root>`.
Scope: classify every gate/hurdle currently defined, decide what each becomes in
a GC-native (formula-step + check-script) structure, and stress-test the mapping
table proposed in `HURDLES-RENAME-PLAN-2026-07-08.md`.

## Two populations of "gates"

There are two distinct populations, and conflating them is the main source of
ambiguity in the rename plan:

1. **Runnable gate formulas** — the 5 `.toml` files in `gates/`. Each is already
   a real GC formula with `[[steps]]` and (mostly) `[steps.check]` exec scripts.
   These are near-native already; the "rename" is mostly cosmetic plus fixing the
   `formula = "gate"` naming.

2. **Registry entries** — the 16 rows (G1–G16, incl. G5b) in
   `assets/brief-pipeline/gates.toml`. These are declarative rows with a `kind`,
   an `evidence_key`, and sometimes a `policy` pointer. Most have NO runnable
   formula of their own; they are enforced inside `brief-gate-keep.toml`'s
   mechanical/judgment steps. The `kind` column here (`mechanical`/`review`/
   `stop`/`manual`) is the authoritative classification source.

The specific examples in the task (G1, G4, G5, G6) come from population 2.
The files physically in `gates/` are population 1. I classify both below.

## Population 1 — runnable gate formula files (gates/*.toml)

| ID | Name | Current form | Classification | GC-native form |
|---|---|---|---|---|
| G1 | test-evidence | `gates/test-evidence.toml` | Mechanical | Already native: single step `check-evidence-block` with `[steps.check]` → `gate-test-evidence.sh`. Becomes a `[steps.check]` on the "attach test evidence" step of `brief-prep`. |
| G14 | test-execution | `gates/test-execution.toml` | Mechanical (2-stage) | Already native: 2 steps, `check-declaration` → `gate-test-execution-declaration.sh`, `verify-evidence` → `gate-test-execution-evidence.sh`. Checks on the test-run step of `brief-prep`. |
| G13 | stale-claim | `gates/stale-claim.toml` | Mechanical (+ routed follow-up) | Already native: `check-stale-claim` → `stale-claim-check.sh`; conditional `route-for-redispatch` step to Mayor. Mechanical check; the routing tail is a Stop-style redispatch, not judgment. |
| G5 | server-touching-safety-override | `gates/server-touching-safety-override.toml` | Stop | Already native: single step `check-server-touching` → `brief-server-touching-safety.sh`. Poka-yoke frontmatter grep that BLOCKS auto-dispatch; only the human adjudicator can bypass (cited in §7). |
| G6 | latex-gate | `gates/latex-gate.toml` | Stop (built on a Mechanical check) — registry says "manual" | Already native: 3 steps. Step 1 `check-latex-evidence` (mechanical evidence gen), Step 2 `latex-hard-gate` STOP with `[steps.check]` → `latex-gate-approval-required.sh`, Step 3 `gate-disposition` (bookkeeping). |

Note: the `formula =` field inside these files is inconsistent — `test-evidence`,
`test-execution`, `stale-claim`, `latex-gate` name themselves, but
`server-touching-safety-override.toml` has `formula = "gate"`. The rename to
`hurdles/` should normalize this.

### Per-file rationale (population 1)

**G1 test-evidence — Mechanical.** The file's own step metadata already declares
`gc.gate.kind = "mechanical"`, and its description is explicit: "This step is
poka-yoke / binary: the check script exits 0 or 1. No judgment is applied here;
anything requiring human assessment belongs in the G2 Good-test or G4
Critical-review judgment gates." It asserts five structural fields
(path/command/exit-code/pass-fail/wall-time) exist, or an explicit N/A+reason.
That is pure string/structure validation. GC-native form: a `[steps.check]` with
`mode = "exec"` calling `gate-test-evidence.sh` hung on the brief-prep step that
attaches test evidence (the mapping table's row-1 target exactly). No ambiguity.

**G14 test-execution — Mechanical.** Tagged `["gate","test","evidence",
"mechanical"]`. Two mechanical sub-checks: a tri-state declaration grep
(`gate-test-execution-declaration.sh`) and, only when PASSED is claimed, an
evidence-field grep (`gate-test-execution-evidence.sh`). The
server-unreachable fallback (a `test-execution-request` record) is itself an
auditable file the script resolves — still mechanical. GC-native: two chained
`[steps.check]`s (the second `needs` the first), attached to brief-prep's
test-run step. No judgment; no ambiguity.

**G13 stale-claim — Mechanical, with a routed tail.** The description is emphatic
that liveness is decided ONLY from `bd show --json` timestamps
(`lease_expires_at`, `heartbeat_at`, `bd stale`): "all decisions are
binary/mechanical ... Judgment calls (e.g. 'agent is paused, not dead') route to
the Mayor gate rather than being made here." So the gate itself is Mechanical
(`stale-claim-check.sh`, exit 0/1/2 with fail-closed on unknown). The second step
`route-for-redispatch` is conditional on nonzero exit and hands off to the Mayor
— that is a routing/dispatch action, NOT a classification-changing judgment. GC-
native: a `[steps.check]` on a claim-freshness step, plus a conditional routing
step. Classify the gate as Mechanical.

**G5 server-touching-safety-override — Stop.** The step's own description ends
"This gate is STOP-class: a FAIL must never be silently overridden by an agent.
Only the human adjudicator can grant an explicit adjudication bypass." The check itself
(`brief-server-touching-safety.sh`) is a mechanical frontmatter grep for
`server_touching: true` / `G5 ... FAIL`, but the CONSEQUENCE is unconditional
blocking of auto-dispatch/auto-approve pending the human adjudicator adjudication. That
block-and-route-to-human semantics is exactly the "Stop" row of the mapping
table. GC-native: a blocking `[steps.check]` (fail-closed) whose failure routes
the brief to the human adjudicator; bypass only via a cited authorization in brief §7. This is a
mechanically-checked Stop — the check is mechanical, the disposition is Stop.

**G6 latex-gate — Stop (registry mislabels it "manual").** See the dedicated G6
discussion below; it is the single genuinely-ambiguous case.

## Population 2 — registry rows (assets/brief-pipeline/gates.toml)

The `kind` column here is authoritative. Reproduced with the GC-native target for
each. Rows already covered by a population-1 file are cross-referenced.

| ID | Name | Registry kind | Classification (this review) | GC-native form |
|---|---|---|---|---|
| G1 | test-evidence | mechanical | Mechanical | `[steps.check]` gate-test-evidence.sh (population-1 file exists) |
| G2 | good-test | review | Review | Formula step routed to reviewer agent via `is-good-test/SKILL.md`; runs in brief-gate-keep `judgment-gates` step (review_target = mayor) |
| G3 | shell-scripts-testable | mechanical | Mechanical | `[steps.check]` (needs a `gate-shell-scripts-testable.sh`; not yet present) |
| G4 | critical-review | review | Review | Formula step routed to reviewer agent via `critical-review/SKILL.md`; the `coordinate-review` FP loop is the producer of this evidence |
| G5 | server-touching-exclusion | stop | Stop | Blocking `[steps.check]` brief-server-touching-safety.sh (population-1 file exists) |
| G5b | user-skill-touching-exclusion | stop | Stop | Blocking check, sibling of G5 (no dedicated script yet; enforced in brief-gate-keep) |
| G6 | latex-gate | manual | Stop (see discussion) | 3-step formula: mechanical evidence + STOP hard-gate + disposition (population-1 file exists) |
| G7 | artifacts-staging | mechanical | Mechanical | `[steps.check]` on the staging step (enforced via brief-mechanical-gates-required.sh) |
| G8 | brief-record-bookkeeping | mechanical | Mechanical | `[steps.check]` (brief-manifest-current.sh / brief-mechanical-gates-required.sh) |
| G9 | no-brainer-filter | review | Review | Formula step via `catch-no-brainer` / `no-brainer-brief-filter.md`; runs in judgment-gates step |
| G10 | improve-readme | mechanical | Mechanical | `[steps.check]` on a README-improvement step |
| G11 | breadcrumb | mechanical | Mechanical | `[steps.check]` brief-breadcrumb-required.sh |
| G12 | auto-merge-kill-switch | stop | Stop | Blocking `[steps.check]` — fail-closed unless `ALLOW_NO_BRAINER_AUTO_EXECUTE` kill-switch file present (brief-no-brainer-execute-safety.sh) |
| G13 | stale-claim | mechanical | Mechanical | `[steps.check]` stale-claim-check.sh (population-1 file exists) |
| G14 | test-execution-silent | mechanical | Mechanical | `[steps.check]` gate-test-execution-*.sh (population-1 file exists as `test-execution.toml`) |
| G15 | improve-readme-silent | mechanical | Mechanical | `[steps.check]` (pairs with G10; silence-detector) |
| G16 | master-current-for-test-evidence | mechanical | Mechanical | `[steps.check]` asserting base-ref recorded |

### Per-row rationale (registry rows without a population-1 file)

**G2 good-test — Review.** Description: "A reviewer must judge whether the
evidence is a meaningful test of the claimed behavior." This is inherently
judgment (is this test meaningful?), backed by a policy SKILL (`is-good-test`).
GC-native: a normal formula step routed to a reviewer agent — the mapping table's
"Review" row. Handled today by the `judgment-gates` step of `brief-gate-keep`
with `review_target = gastown.mayor`. No check script; the reviewer's verdict IS
the evidence.

**G4 critical-review — Review.** Adversarial correctness/policy/evidence pass,
backed by `critical-review/SKILL.md`. This matches the task's own example ("G4
critical-review → workflow step (agent does judgment work)"). GC-native: a
formula step where a reviewer agent (or the `coordinate-review` create/review FP
loop) runs and emits an APPROVING / NEEDS-REVISION verdict. Review, unambiguous.

**G5b user-skill-touching-exclusion — Stop.** Exact sibling of G5 but for user
skill changes. Same fail-closed-unless-the human adjudicator semantics. GC-native: blocking
check; currently enforced within brief-gate-keep rather than a standalone
formula. Recommend giving it its own script mirroring
`brief-server-touching-safety.sh` when the rename lands.

**G9 no-brainer-filter — Review.** Registry kind is `review`; the classifier
decides whether a brief is a legitimate no-brainer AND critically "cannot
override stop gates or the human adjudicator-only decisions." The judgment part (is this really
a no-brainer?) is Review; the "cannot override stop gates" part is enforced by
the stop gates themselves, not here. GC-native: reviewer step via
`catch-no-brainer`. Borderline mechanical (the 5-criterion checklist is fairly
mechanical) but registry deliberately marks it review because misclassification
is high-cost — keep as Review.

**G12 auto-merge-kill-switch — Stop.** Fail-closed unless a local kill-switch
file (`ALLOW_NO_BRAINER_AUTO_EXECUTE`) is present. The file-existence test is
mechanical, but the semantics are Stop: automation is blocked by default. Same
"mechanically-checked Stop" pattern as G5. GC-native: blocking `[steps.check]`
that passes only when the kill-switch artifact exists.

**Remaining mechanical rows (G3, G7, G8, G10, G11, G15, G16).** All are
deterministic presence/consistency checks (artifact staged? manifest consistent?
README-improvement line present or N/A? breadcrumb present? base-ref recorded?).
Each becomes a `[steps.check]` exec on the corresponding brief-prep step. Several
are enforced today by the aggregate `brief-mechanical-gates-required.sh` rather
than individual scripts.

## The G6 latex-gate ambiguity (the crux)

G6 is the one case where the sources disagree with each other:

- The registry row (`gates.toml`) says **kind = "manual"**.
- The runnable file (`gates/latex-gate.toml`) describes itself as a **STOP gate**
  ("The gate is a STOP gate. It blocks auto-dispatch and auto-merge ... It fails
  CLOSED") and its step-2 metadata literally sets `gc.gate.kind = "stop"`, while
  its header comment says "kind=manual" in the registry lineage note.

So the same gate is tagged manual, stop, AND contains a mechanical check. Both
interpretations the task raises are real and BOTH are present in the file:

1. **Mechanical-check interpretation.** Step 1 (`check-latex-evidence`) and the
   step-2 `[steps.check]` (`latex-gate-approval-required.sh`) are mechanical: the
   script verifies that (a) a check-latex evidence block exists and (b) a
   `latex-approval.toml` names the human adjudicator with an `approved_diff_sha` matching the
   diff's sha. Pure file/sha comparison — no judgment.

2. **Review/manual interpretation.** The APPROVAL itself — the human adjudicator eyeballing the
   mathematical typesetting of a specific `notes.tex` diff and saying yes — is a
   human judgment. That is what makes the registry call it "manual."

Resolution: G6 is best modeled as **a Stop gate whose satisfaction condition is a
mechanical check over a human-produced approval artifact** — i.e. the mapping
table's "Manual" row ("a normal step requiring human output, then a check
validates it") realized THROUGH a Stop block. The file already does exactly this:
generate evidence (mechanical) → BLOCK pending a per-diff human approval
artifact (stop) → mechanical check validates the artifact's sha (mechanical) →
record disposition. It is NOT a "review step routed to a reviewer agent," because
no agent may substitute for the human adjudicator here; the human is structurally required. So
of the two interpretations the task floats, the **mechanical-check-over-human-
approval (Stop/Manual)** reading is correct and the pure-"review step" reading is
wrong for this gate — an agent judging typesetting would violate the standing
latex-gate policy (he-jwmy / he-86wu / he-hsoc).

Recommendation for G6: keep the runnable 3-step structure as-is; reconcile the
label to **Stop** (the file's own step metadata already says so) and drop the
stale "manual" registry kind, OR keep "manual" as a synonym meaning "Stop that
requires a specific human artifact, not just any authorization." Do not downgrade
it to a Review step.

## Summary

### Count by type (union of both populations, 17 distinct IDs G1–G16 + G5b)

- **Mechanical (10):** G1, G3, G7, G8, G10, G11, G13, G14, G15, G16
- **Review (3):** G2, G4, G9
- **Stop (4):** G5, G5b, G12, and G6 (reclassified from "manual")
- **Manual (0–1):** G6 only, and only if "manual" is retained as a distinct kind;
  this review folds it into Stop.

Runnable files in `gates/` today (5): G1 (mechanical), G14 (mechanical),
G13 (mechanical), G5 (stop), G6 (stop/manual). The other 12 registry rows are
enforced inside `brief-gate-keep.toml` (mechanical bundle + judgment step), not
as standalone files.

### Where the G6 two-interpretation situation applies

Only G6 (latex-gate) genuinely carries both interpretations, because it is the
only gate that (a) is registry-tagged `manual`, (b) self-declares `stop`, and
(c) is satisfied by a mechanical check. No other gate has this three-way tension:
G2/G4/G9 are cleanly Review (agent judgment, no blocking-on-human-artifact);
G5/G5b/G12 are cleanly Stop (block-until-the human adjudicator, no per-artifact sha match). G5
and G12 share G6's "mechanical check, Stop consequence" shape but lack the
human-approval-artifact requirement, so they are unambiguously Stop.

### Recommendation on ambiguous cases

1. **Adopt the proposed mapping table, with one refinement to the "Stop" and
   "Manual" rows.** The table's four rows are sound, but "Stop" and "Manual"
   overlap in practice: every Stop gate here is checked mechanically and blocks
   pending a human artifact. Treat "Manual" as the special case of "Stop" where
   the blocking condition is satisfied by a *specific* human-produced artifact
   (a per-diff approval), not merely by any authorization line. Under that
   reading G6 is Manual-flavored-Stop; G5/G5b/G12 are plain Stop.

2. **"Mechanically-checked Stop" is a first-class shape, not a contradiction.**
   G5, G12, and G6 all have a mechanical `[steps.check]` whose PURPOSE is to
   enforce a Stop. Classify by consequence (does it block pending human sign-off?
   → Stop), not by whether a script runs. Do not reclassify these to Mechanical
   just because a script decides pass/fail.

3. **Normalize the runnable files during the rename.** Fix
   `server-touching-safety-override.toml`'s `formula = "gate"` to a proper name;
   reconcile G6's registry `kind = "manual"` against its `gc.gate.kind = "stop"`
   metadata; and consider promoting G5b to its own script for parity with G5.

4. **Preserve the population split.** Do not try to turn all 16 registry rows
   into 16 standalone hurdle files. The mechanical bundle (G3/G7/G8/G10/G11/
   G15/G16) is legitimately enforced as one aggregate check inside
   `brief-gate-keep`; only gates with non-trivial multi-step logic or
   independent reuse (G1, G13, G14, G5, G6) warrant standalone `hurdles/*.toml`.
