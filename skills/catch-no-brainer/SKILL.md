---
name: catch-no-brainer
description: PRELIMINARY v0.2 — classify a brief against the he-lele 5-criterion no-brainer test, plus recognize the capability-blocker shape (would-be no-brainer stalled by a permission/capability gap) and signal compact-form eligibility to downstream present-it consumers (DRY-RUN). Emits one JSON-line verdict to stdout per brief; copies no-brainer matches into <city-root>/.beads/briefs/.pile/.no-brainer/ and novel-shape descriptors into <city-root>/.beads/.gates-candidate-pile/. NEVER edits bead he-xkq3, NEVER auto-merges, NEVER closes briefs, NEVER runs `bd update`. Triggers triaging a brief that just landed in the main stack for the human adjudicator-bypass eligibility (stale-scratch cleanup, mechanical promotion, sibling-PASS); architecture-class briefs (deep design, coupling, judgment-load) bypass this skill and go straight to Mayor/the human adjudicator.
---

> **Canonical copy**: `mathcity.catch-no-brainer` in this mathcity pack. Materialized agent-skills copies are fallback only.

> **PRELIMINARY v0.2 — DRY-RUN ONLY.** Emits proposed verdicts + proposed gates-registry extensions + compact-form eligibility signal.
> NEVER writes to [[he-xkq3]], NEVER auto-merges, NEVER closes briefs, NEVER calls `bd update`/`bd close`/`bd link`.
> Allowed side effects: `mkdir -p` + file write in `.pile/.no-brainer/` and `.gates-candidate-pile/`. Nothing else.

## Purpose
Triage briefs so non-architecture cleanups bypass human adjudication. Composes by reference (does not re-implement): [[he-lele]] (5-criterion legacy classes), [[he-xkq3]] G5 (cat-E server-touching) + G9 (no-brainer), [[he-9czp]] gate-order, [[he-cnat]] preliminary-skill-first.

Also signals [[present-it]] consumers whether the brief may be output in **compact form** (`DECISION` + `CONTEXT` + `RECOMMEND` + `CONFIRM y/n/grill-me-further`) or MUST be full-form.

The he-lele `cat-A`/`cat-B`/`cat-C`/`cat-D` labels are policy-class aliases,
not emitted category IDs. Emitted category IDs must match
`assets/brief-pipeline/no-brainer-categories.toml`.

## Classification rule
Given a brief at `<path>` (frontmatter + body + diff summary inside the brief):

1. **Server-touching first** ([[he-xkq3]] G5 fires before G9). If diff/disposition touches any path in [[he-lele]] §"Safety override" server set (`magma/scripts/dispatch.sh`, `magma/make/dispatch/*`, `gt-dolt*`/`gt-upf*`, `<city-root>/.gc/daemon*`, `<city-root>/.dolt-data/*`/`~/.dolt-data/*`, `.gc/agent-bridge/*`, ssh-writes to `aia-s27`): emit `{no_brainer:false, reason:"cat-E-server-touching", compact_eligible:false}` and STOP.

2. **User-skill-touching** ([[as-wjv]] SAFETY OVERRIDE). If diff/disposition touches any path in `~/.claude/skills/<name>/` or `<repos-root>/agent-skills/skills/<name>/` (SKILL.md or references): emit `{no_brainer:false, reason:"user-skill-touching-override", compact_eligible:false}` and STOP.

3. **Capability-blocker shape.** If the brief's recommended disposition WOULD satisfy the [[he-lele]] 5-criterion no-brainer test but for a permission/capability gap the polecat could not resolve in-session (`gh auth` missing, credentials not provisioned, external service unreachable, sandbox denies a required syscall, etc.) — detect via explicit `capability_blocker: <description>` frontmatter field OR body text pattern `BLOCKED-ON: <capability>` — emit `{no_brainer:false, category:"capability-blocker", reason:"resolve <blocker>, then re-classify", compact_eligible:false, requires_human_adjudication:false}` and STOP.

   *Rationale:* the shape IS a known no-brainer; only the capability gap blocks the mechanical disposition. Routing as "resolve the blocker, then re-run this classifier" produces cleaner throughput than presenting a full A/B/C/D brief to the human adjudicator. Data point: he-gu79 (n=5+ per [[feedback_no_brainer_class_under_flagged]]).

4. **[[he-lele]] 5-criterion** (all 5 must hold): (1) branch regex `^(polecat|nux|<role>)/(<role>/)?<bead>(@<token>)?$`; (2) parent bead CLOSED with documented supersession (close-reason names a `bd`-resolvable artifact / merged PR / fs path); (3) diff vs `origin/master` touches ONLY scratch/transient files (no `magma/`, `latex/`, `notes.tex`, schema, `DATA/`, package files, `.beads/` except briefs themselves); (4) no downstream beads reference the branch; (5) brief verdict is `DELETE` or `INVESTIGATE`. → emit `{no_brainer:true, category:"stale-branch", compact_eligible:true}` (`stale-branch` is the registry ID for the legacy he-lele stale-cleanup class).

5. **DEFER-ratify-existing-HELD** (no-brainer DEFER). **Safety overrides apply first** — if steps 1 or 2 fired, this step is not reached. Trigger: (a) the brief's recommended disposition is `DEFER`; AND (b) the brief body or frontmatter indicates the current state is already HELD/standing (e.g., `status: HELD`, `existing_state: HELD`, or body text `already HELD` / `ratify existing hold` / `no-op: already deferred`); AND (c) the only action required is to ratify (record) that existing state — no new work, no file changes, no server interaction. → emit `{no_brainer:true, category:"defer-ratify-held", compact_eligible:true}` and copy brief into `.pile/.no-brainer/`.

   *Rationale:* a brief whose decision merely confirms an already-deferred/held state carries zero adjudication load — the status quo IS the decision. Per [[feedback_no_brainer_class_under_flagged]] n=3 miss pattern.

6. **CLOSE-DONE-cited-commit** (no-brainer CLOSE). **Safety overrides apply first** — if steps 1 or 2 fired, this step is not reached. Trigger: (a) the brief's recommended disposition is `CLOSE` with reason `DONE`; AND (b) a specific commit SHA (40-hex or abbreviated ≥7 chars) is cited in the brief body or frontmatter as evidence the work is already merged (e.g., `merged_commit:`, `evidence_sha:`, or inline `SHA: <hex>`); AND (c) the diff or body confirms the referenced commit is already present on `origin/master` (or the brief asserts "already merged"). → emit `{no_brainer:true, category:"close-done-cited-commit", compact_eligible:true}` and copy brief into `.pile/.no-brainer/`.

   *Rationale:* if the work is provably merged (commit on record), closing is a mechanical record-keeping act. The SHA is the cryptographic receipt. Per [[feedback_no_brainer_class_under_flagged]] n=3 miss pattern.

7. **EXECUTION-CONFIRMATION-with-cryptographic-proof** (no-brainer CONFIRM). **Safety overrides apply first** — if steps 1 or 2 fired, this step is not reached. Trigger: (a) the brief's recommended disposition is `CONFIRM` or `RATIFY-EXECUTION`; AND (b) the brief carries mechanically-verifiable proof that the execution already occurred — one or more of: a commit SHA, a signed artifact reference, an exit-code record (`exit_code: 0`), or a `bd`-resolvable artifact path; AND (c) the brief does NOT require the human adjudicator to make any new judgment — it only asks for acknowledgment of a completed, provable act. → emit `{no_brainer:true, category:"execution-confirmation-proof", compact_eligible:true}` and copy brief into `.pile/.no-brainer/`.

   *Rationale:* confirmation of an already-executed, provably-complete action is mechanical. The cryptographic/mechanical proof (SHA, signed artifact, exit record) substitutes for the human adjudicator inspection. Per [[feedback_no_brainer_class_under_flagged]] n=3 miss pattern.

8. **Else** (shape not in A/B/C/D, not steps 5/6/7, and not a capability-blocker) → emit `{no_brainer:"candidate", proposed_registry_extension:"<one-line gate criterion>", requires_human_adjudication:true, compact_eligible:false}`.

## Compact-form eligibility signal

`compact_eligible: true` means the downstream [[present-it]] consumer MAY output the brief in compact form (`DECISION` / `CONTEXT` / `RECOMMEND` / `CONFIRM y/n/grill-me-further`) instead of the full 7-section grill-ordered brief. Necessary but not sufficient — [[brief-prep]] also requires BOTH safety-override booleans (`server_touching`, `user_skill_touching_override`) to be `false` before compact form ships.

`compact_eligible: false` means the brief MUST be full-form. Applies to: server-touching, user-skill-touching, capability-blocker, and novel-shape (candidate) outputs. The three new path categories (defer-ratify-held, close-done-cited-commit, execution-confirmation-proof) emit `compact_eligible:true` when their trigger conditions are met — but ONLY because the safety overrides (steps 1 and 2) were already checked and did not fire.

`capability-blocker` shape is a hard "not compact, not full-form-yet" — the brief should not be presented in either shape until the blocker is resolved. Mayor / dispatcher's job to route the blocker for resolution.

## Output schema (one JSON-line per brief, to stdout)
```json
{"brief_path":"<abs>","bead_id":"<id|null>","no_brainer":true|false|"candidate",
 "category":"stale-branch|capability-blocker|defer-ratify-held|close-done-cited-commit|execution-confirmation-proof|null",
 "reason":"cat-E-server-touching|user-skill-touching-override|resolve <blocker>|null",
 "compact_eligible":true|false,
 "confidence":0.0,
 "proposed_registry_extension":"<text|null>","requires_human_adjudication":true|false,
 "classified_at":"<ISO-8601-utc>"}
```

`confidence` is a float in [0.0, 1.0] expressing the classifier's certainty in the emitted `category`. Always emit it — even stop-gate outputs (server-touching, user-skill-touching) emit `confidence:1.0` because those are deterministic rule checks. "Confident" threshold for N2/N5 auto-execution eligibility is `confidence >= 0.85`; below that, treat as non-no-brainer regardless of category. The verdict recorded on the brief bead at auto-execution (B2.9 / N7 — one-bead model: the brief bead IS the decision bead; no separate bead is created) must include this value so the empirical wrong rate α can be estimated from the audit ledger (N8).

Category IDs must be present in `assets/brief-pipeline/no-brainer-categories.toml` unless the output is `candidate` or a stop-gate `no_brainer:false` result. The registry is the machine-readable category contract; `POLICY.md` remains authoritative for rule semantics.

## Side effects (v0.2)
- `no_brainer:true` (any category: stale-branch, defer-ratify-held, close-done-cited-commit, execution-confirmation-proof) → `mkdir -p` + copy brief into `.pile/.no-brainer/`. Consumed by pile-processor ([[he-x3se]], not-yet-shipped); until then the file is inert.
- `no_brainer:"candidate"` → write `.gates-candidate-pile/<brief-slug>-candidate.md` with `pattern_fingerprint`, `originating_brief`, `why_classified_candidate`, `suggested_gate_criterion`. Curator promotion to [[he-xkq3]] is OUT of scope (see [[he-xxwb]]).
- `category:"capability-blocker"` → stdout only. Do NOT deposit in `.pile/.no-brainer/` (the disposition can't be executed) or `.gates-candidate-pile/` (the shape isn't novel). Mayor consumes the stdout signal and dispatches capability resolution (e.g., token-pass-outer / credential provisioning); when resolved, the brief is re-classified.
- `no_brainer:false` (server-touching / user-skill-touching) → stdout only.

## Tool restrictions (self-discipline contract)
- ALLOWED: `Read`, `Bash` (grep/find/jq/regex), `Write`/`mkdir` inside the two named dirs.
- FORBIDDEN: `Edit`/`Write` outside those dirs; `bd update`/`bd close`/`bd link`/`bd remember`; `git push`/`git merge`/`git commit`; any read/write touching [[he-xkq3]] or any other bead.
- Self-refuse → log `{verdict:"REFUSED", reason:"..."}` to stdout.

## Fixture (pass-bar: all classify correctly)
Run `bash fixtures/run.sh`:

| # | Fixture | Expected verdict |
|---|---|---|
| 1 | `stale-branch-A.md` | `{no_brainer:true, category:"stale-branch", compact_eligible:true, confidence:>=0.85}` |
| 2 | `stale-branch-B.md` | `{no_brainer:true, category:"stale-branch", compact_eligible:true, confidence:>=0.85}` |
| 3 | `stale-branch-C.md` | `{no_brainer:true, category:"stale-branch", compact_eligible:true, confidence:>=0.85}` |
| 4 | `server-touching.md` | `{no_brainer:false, reason:"cat-E-server-touching", compact_eligible:false, confidence:1.0}` |
| 5 | `novel-shape.md` | `{no_brainer:"candidate", requires_human_adjudication:true, compact_eligible:false, confidence:<0.85}` |
| 6 | `capability-blocker.md` | `{no_brainer:false, category:"capability-blocker", compact_eligible:false, confidence:1.0}` |
| 7 | `defer-ratify-held.md` | `{no_brainer:true, category:"defer-ratify-held", compact_eligible:true, confidence:>=0.85}` |
| 8 | `close-done-cited-commit.md` | `{no_brainer:true, category:"close-done-cited-commit", compact_eligible:true, confidence:>=0.85}` |
| 9 | `execution-confirmation-proof.md` | `{no_brainer:true, category:"execution-confirmation-proof", compact_eligible:true, confidence:>=0.85}` |

Pass iff `fixtures/run.sh` exits 0.

## Status
PRELIMINARY v0.2 under [[he-cnat]]. FP-converge follow-up [[he-ahfr]] (gated on ≥3 dogfood examples). Self-bead [[he-6wej]]. Sling [[he-h3p2]].

## Versioning
- **v0.0 — PRELIMINARY DRY-RUN** (2026-06-24): initial 5-criterion classifier + cat-E override + fixture harness (5 fixtures).
- **v0.1 — capability-blocker shape + compact-form signal** (2026-06-30, per as-niek per the human adjudicator "better briefs" epic): added step 2 (user-skill-touching-override consistency with [[as-wjv]]); added step 3 (capability-blocker shape — would-be no-brainer stalled by permission/capability gap; route as "resolve, then re-classify" rather than presenting A/B/C/D; data point he-gu79 n=5+); added `compact_eligible` output field consumed by [[present-it]] for compact-form eligibility; added capability-blocker.md fixture (6th case).
- **v0.3 — confidence field + α-measurement substrate** (2026-07-12): added `confidence` float [0.0, 1.0] to output schema; all stop-gate outputs emit `confidence:1.0` (deterministic); auto-execution threshold set at `confidence >= 0.85`; fixture expected verdicts updated to assert confidence presence; N7 audit trail now requires confidence value so empirical wrong rate α can be estimated from the decision bead ledger (N8).
- **v0.2 — 3 missing rubric paths** (2026-07-08, per [[feedback_no_brainer_class_under_flagged]] n=3 miss pattern, W2.6 triage plan): added steps 5, 6, 7 for three previously under-flagged no-brainer shapes — (a) DEFER-ratify-existing-HELD (step 5, category `defer-ratify-held`): brief disposition is DEFER and the current state is already HELD/standing, so the decision is a mechanical ratification; (b) CLOSE-DONE-cited-commit (step 6, category `close-done-cited-commit`): brief closes as DONE with a cited commit SHA confirming work is already merged, making closure a record-keeping act; (c) EXECUTION-CONFIRMATION-with-cryptographic-proof (step 7, category `execution-confirmation-proof`): brief only asks for acknowledgment of an already-executed act carrying mechanically-verifiable proof (commit SHA, signed artifact, exit-code record). All three: emit `no_brainer:true`, copy to `.pile/.no-brainer/`, `compact_eligible:true`. Safety overrides (steps 1+2: server-touching, user-skill-touching) remain absolute predecessors — a brief triggering those overrides CANNOT reach steps 5/6/7. Added fixtures 7/8/9 to fixture table. Updated output schema `category` enum and side effects header.
