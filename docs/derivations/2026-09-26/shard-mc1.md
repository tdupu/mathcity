# Derivation pass — mc1 batch (38 mathcity briefs), 2026-09-26

**This is a derivation RECORD for the Mayor, not a set of verdicts.** Nothing was written to any bead, brief, cache or git ref.
ADR 0006 is still Proposed, so none of this may be recorded as a verdict without a real adjudicator.

**Corpus re-checked live** (`grep -m1 '^| Status |'` over the 16 policy files). Adopted: POLICY-POLICY.md, POLICY-beads.md,
POLICY-formulas.md, subdomains/brief-system/POLICY.md, subdomains/dev/POLICY.md, subdomains/dev/POLICY-city.md,
subdomains/dev/POLICY-documentation.md. That is the same 7 as on 2026-09-18 and 2026-09-25. Everything else is Draft or has no Status row.
Checkouts: ~/gt/mathcity HEAD b4f09ac. ~/repos/mathcity HEAD b792059 (origin/main 2026-09-25 16:10). ~/repos/gascity 4bafc941b.

**Bodies read with** `bd -C ~/gt/mathcity show <id>` (read-only), dumped to scratchpad/derive/mc1b/.

**Result: 0 DERIVED.** No Adopted, citable, mechanically-evaluable rule removes all options but one on any brief in this batch.
What did the work was premise measurement:
- 5 briefs are MOOT.
- 4 are DUPLICATE.
- 2 are DERIVED-OUT under the standing instruction.
- 27 remain UNDETERMINED. Several of these have stale premises, noted on each.

---

## MOOT

### mc-2ju8s — MOOT
Question/options: a hecke `DOLT_PUSH --force` had been running 7.7 h. Options: {A leave it, B authorize a read-only progress probe, C bounce the data plane}.
Premise probes:
- `gc dolt sql -q "SHOW FULL PROCESSLIST"` → one row, my own `SHOW FULL PROCESSLIST` query. No DOLT_PUSH. [measured] Control: the probe lists live queries, since it listed itself.
- `gc dolt health --json` → server pid **1693**. The brief measured pid 13490, so the server has restarted since. [measured]
- `gh api repos/tdupu/hecke-dolt --jq .pushed_at` → 2026-09-11T01:38:40Z. [measured]
- `bd show mc-t628i` → OPEN. It still carries the separate `commits=0` health-reporting defect.
Grounds: the operation the three options act on no longer exists. Every option is void.
Surviving option: none needed. Residual: the health `commits: 0` false-zero reporting defect lives on mc-t628i, a defect bead, not a decision. Today's health reads hecke commits=34099, so that symptom was also not reproduced now.

### mc-55dlr — MOOT
Question/options: the `bd update --notes` clobber in the create-issue-briefed step. Options: {A fix the template, B also sweep the 75 beads carrying the instruction, C change bd upstream}. Recommended: A plus B limited to open beads.
Premise probes:
- `grep -c -E -- '--notes\b' ~/repos/mathcity/formulas/create-issue-briefed.formula.toml` → 0. `--append-notes` → 5. The same holds for ~/gt/mathcity and all 19 rig `.beads/formulas` copies. [measured]
- `git log -S'--append-notes' -- formulas/create-issue-briefed.formula.toml` → 97097f7, **2026-08-28**. The brief was filed 2026-09-08, 11 days later. [measured]
- `bd show mc-ahtqn` → the step bead that reproduced the clobber was created **2026-08-27**, poured before the fix. `bd show mc-ahtqn | grep -- --notes` → line 63 carries the old `--notes` text. [measured] The reproduction was a stale pour, not the live template.
- The only copies still carrying `--notes` are the deprecated ~/repos/gascity-packs/mathcity and ~/gt/gascity-packs/mathcity trees. `grep gascity-packs/mathcity` over city.toml and pack.toml → not imported. [measured]
- `SELECT status,COUNT(*) FROM mc.issues WHERE description LIKE '%bd update%--notes%' AND NOT LIKE '%append-notes%'` → closed 69, blocked 5, open 1. [measured] The control fired: the query returned rows.
Grounds: option A, the recommended action, was already done before the brief existed. The brief's claim that the damage "recurs on every run" is false for new pours. B shrinks to 6 non-closed beads, which is execution bookkeeping. C, the upstream bd change, was already advised as a separate upstream filing.
Surviving option: none needed as a decision. Residual for the Mayor: patch the 6 non-closed beads (1 open, 5 blocked). Optionally delete or mark the dead gascity-packs/mathcity copies.

### mc-aj15r — MOOT (residual belongs to mc-psb7t)
Question/options: the claim wrapper retries forever on a status outside open|in_progress. Options: {probe it, repair the wrapper, codify the park-with-unassign workaround}.
Premise probes:
- `grep -rln 'open|in_progress) ;;'` over ~/repos/{mathcity,gascity,gascity-packs} → no hits. [measured]
- `git log -S'CLAIM_REJECTED unexpected status' -- gascity/roles/agents/run-operator/prompt.template.md` → removed at 4c2e982, **2026-07-15**. [measured]
- `~/repos/gascity-packs/gascity/commands/claim/run.sh:207-210` → the unexpected-status branch now `break`s, and the retry is bounded (max_attempts). [measured]
- `gc-role-worker.template.md`: `while true` 0, `EXPECTED_ASSIGNEE` 0, `gc gc claim` 2. [measured]
- The only on-disk copy of the unbounded loop is the stale pack cache `~/gt/.gc/cache/repos/9bce37ba…/gascity/roles/agents/*/prompt.template.md`, mtime 2026-08-05. [measured] The live city.toml imports the local ~/repos/gascity-packs/gascity/roles source instead. [measured]
Grounds: "repair the claim wrapper" was done at source six weeks before this brief. The brief itself says the hanging call was a bare `gc hook --claim`, not the wrapper, so the causal link was never established. What remains is the running fleet executing a stale prompt. That is exactly mc-psb7t's question, and mc-psb7t is the fuller brief.
Surviving option: none here. Fold into mc-psb7t. mc-t9aop (defect bead) stays OPEN for the Mayor to relate or close.

### mc-t8zeo — MOOT
Question/options: approve the commission graph for mc-csr, i.e. run brief-prep to produce a brief on "should B2.1 let a brief declare no bead subject". Options: {approve the graph, reject}.
Premise probes:
- `grep -n -F 'B2.1a Scope of B2.1: a brief may DECLARE that it has no bead subject.' subdomains/brief-system/POLICY.md` → **line 223**. The document is Adopted. B2.1a carries no (PROPOSED) marker: the PROPOSED grep for B2.1a returned 0. [measured]
- Line 1138 of the same file (change log), verbatim: "Add B2.1a: a brief may declare it has no bead subject (`MBRF056`) … the human adjudicator ruled YES on the principle (bead `mc-csr`, workflow `mc-sxz`)", dated 2026-08-20. [measured]
- `grep -rln MBRF056 assets/scripts` → briefs.py, verdicts.py, brief-stack-index.py. The rule is implemented in code. [measured]
- The commission was deposited 2026-08-26, six days after the question was ruled and written into Adopted policy.
Grounds: the policy question the commission would brief was already decided and adopted. Running brief-prep on it would re-ask a settled question.
Surviving option: none needed. Bookkeeping: mc-csr is still OPEN (task) and its convoys mc-cce and mc-m8q are open, so they can be closed citing B2.1a (POLICY.md:223).

### mc-up5vd — MOOT (one residual)
Question/options: should mctl gain a typed archive effect (stack/<slug>.md → .adjudicated-archive/, de-index), and should stack/*.md be registered with mctl as its sole writer? Options: {A build it in mctl, B extend brief-shuffle, C extend brief-archive-sweep, D leave it}.
Premise probes:
- `git log -S'brief_archive' -- assets/scripts/mctl_core/effects.py` → **900e76a, 2026-09-09 10:49, "mctl: add the brief_archive effect -- the move mctl could not do (#95, mc-up5vd)"**. [measured]
- `git merge-base --is-ancestor 900e76a origin/main` → true. [measured]
- `effects.py:2491-2545` → the `brief_archive` kind and `_archive_brief` exist, with refuse-on-different-content. [measured]
- `grep '^path' assets/brief-pipeline/brief-writers.toml` → 4 artifacts registered: stack/.index.jsonl, .pile/manifest.jsonl, decisions/<id>.toml, decisions-track/manifest.jsonl. **stack/*.md is not registered.** [measured]
Grounds: option A was built and landed on main, and the commit names this brief. B, C and D are superseded.
Surviving option: none needed for the main question. Residual: the register half, adding stack/*.md to brief-writers.toml, did not land. That is follow-through on A, not a new decision.

## DUPLICATE

### mc-027dz — DUPLICATE of mc-jq637 (survivor: mc-jq637)
Both ask the same thing, filed the same day by the same author: per-subdomain imports vs upstream recursive discovery for the 82 subdomain skills. mc-027dz is a compact body with no §1–§7. mc-jq637 is full-form per ADR 0001 and carries the options A–D.
Premise probes (for the survivor):
- `~/repos/gascity/internal/config/skill_discovery.go:22` → `skillsDir := filepath.Join(packDir, "skills")`. Still no recursion. [measured]
- `ls ~/gt/.claude/skills | grep -c '^mathcity-'` → **73** on this laptop. That breaks down as dev 30, lmfdb 25, computing 7, proof-assist 5, brief-system 3, latex 3. [measured]
- Only `[imports.mathcity-dev]` is in ~/gt/pack.toml. The non-dev subdomain symlinks are dated 2026-08-13 and point at ~/repos/mathcity/subdomains/*/skills. They look hand-placed, not import-discovered. [inferred from mtime and absent imports]
- The brief's "0 reachable" was measured on kolchin (~/HQ), which I did not probe.
- GH tdupu/mathcity#270 is open.

### mc-19zky — DUPLICATE of mc-nq1cn (survivor: mc-nq1cn)
mc-19zky's author appended "RECOMMENDATION WITHDRAWN — §2 OF THIS BRIEF IS ACTIVELY WRONG" (comment 2026-08-29 03:12). The comment says the private `<X>-dolt` remotes already exist, and restates the real question as "the remotes are configured and stale — what, if anything, should be done". That restated question is mc-nq1cn's §1 (diagnose / repair / accept local-only). The freshness table in both was later refuted by the same author (04:19), who replaced it with a ref/size census.
Premise probes (for the survivor):
- `git ls-remote …/gascity-HQ-dolt | wc -l` → 4 refs. `gh api …/gascity-HQ-dolt` → pushed_at **2026-07-15**, 754 MB. The hq remote is still stale. [measured]
- `…/mathcity-dolt` → pushed_at 2026-09-25, 62 MB. It was EMPTY on 08-29 and is now populated. [measured]
- Negative control: a nonexistent repo gives "Repository not found". [measured]
The same-disk file:// backup_url part of mc-19zky overlaps mc-c441c, which stays separate (see below).

### mc-tj7sy — DUPLICATE of mc-y9reo (survivor: mc-y9reo)
Same decision: where build-basic exec checks find `.gc/scripts/checks/build-artifact-valid.sh`, which does not exist in rig mathcity. mc-y9reo is earlier (09-06) and broader. Its options cover repoint / vendor / fix resolution upstream / accept-visible, plus the "mark the workflow root when a gate cannot run" sub-question. mc-tj7sy's A/B/C are a subset.
Premise probes:
- `ls ~/gt/mathcity/.gc/` → settings.json, tmp, work. No scripts/. [measured]
- mc-56tn8 is OPEN. [measured]

### mc-b02eq — DUPLICATE of mc-v7rhw (survivor: mc-v7rhw, taking b02eq's option A)
Both were filed 2026-08-29 and both ask what to do about MASTER PERT §12's 51.17 critical path running through the unbuilt, unowned D5 via an unexplained D1→D5 edge. mc-v7rhw: {re-derive §12, patch citations, halt Phase 1, accept}. mc-b02eq: {file the D5 upstream brief, drop the edge and re-derive, both, accept as advisory}. They are one decision. The survivor should carry b02eq's "file the missing D5 upstream brief" option. v7rhw's warning that two documents are both called "MASTER PERT" should also carry over.
Premise probe:
- `docs/superpowers/plans/dashboards/2026-08-28-MASTER-pipeline-return-path-and-drain-PERT.md:311,316` → still "S0 → D1 → D5 … = 51.17" and "driver in Phase 1 is D5". It was last touched at 97097f7 (08-28). [measured] The premise is live.

## DERIVED-OUT (standing instruction, not policy)

Ground for both, quoted from ~/gt/CLAUDE.md:360-361: *"Staffing, routing, and sequencing are NOT his. Who does what, who reviews whom, what order things merge in — the coordinator owns all of it."* This is Taylor's standing instruction, not an Adopted policy rule. No policy is cited.

### mc-vynt6 — DERIVED-OUT
Question: does the finished mc-vzx0 build branch ship now, or hold until mc-1wls8 is adjudicated? The brief says it does not re-ask mc-1wls8's question.
Premise probes:
- `git merge-base --is-ancestor work/mc-h8j7-compose-order-health origin/main` (~/gt/mathcity) → NOT merged. [measured]
- `git diff --stat branch origin/main` → the branch's tests (e.g. test_orders_status_bounded_catalog.py) are absent on main, so it was not squash-landed either. [measured]
- mc-1wls8 is OPEN. mc-vzx0 is CLOSED. [measured]
Grounds: the question is purely merge order relative to another item. Caveat: the eventual merge or push to tdupu/mathcity still goes through BART and Taylor's `authorize-git-operation` gate (LP1). That gate is a separate authorization, not this decision.

### mc-sw2a7 — DERIVED-OUT
Question: a plan-time scope record ("DEFERRED"; metadata `build.decision_kind: scope-deferral`). It records that the 32 hq decisions-track manifest rows are excluded from the mc-3fayz repair and carried by follow-up mc-geumh. The brief states it "is a scope decision, not a verdict on the manifest rows' fate". It offers no closed option set to Taylor.
Premise probes:
- mc-2juir (the gate work item that required this record) is CLOSED. mc-geumh is OPEN and linked. mc-3fayz is OPEN. [measured]
Grounds: this is build scoping and sequencing, meaning what lands in this build versus a follow-up. That is the coordinator's call. The substantive question, the fate of the 32 rows, is explicitly left to mc-geumh / gt-57lvej and the mc-e19t-gated workstream D. I did not use mc-e19t as authority: it is a decision bead, not policy.

## UNDETERMINED

### mc-jq637 — UNDETERMINED (survivor of mc-027dz)
Options: {A per-subdomain imports, B upstream recursive discovery, C hybrid, D leave}. No Adopted rule sets where subdomain-skill exposure is configured. POLICY-skills.md is Draft (it "claims to govern exposure and carries zero rules", per #272). Premise live at source (skill_discovery.go:22). The count differs by host: 73 reachable on the laptop, probably hand-placed; 0 on kolchin per the brief. Per its own §2, design intent has to be established first.

### mc-nq1cn — UNDETERMINED (survivor of mc-19zky)
Options: {A diagnose the push path, B repair now, C accept local-only}. Premise partly stale:
- The freshness table in §4 is refuted by its own author.
- mc remote now populated (pushed 2026-09-25). [measured]
- hq remote still last pushed 2026-07-15. [measured]
Whether hq needs an off-box copy is Taylor's durability call. No Adopted rule sets a backup requirement.

### mc-c441c — UNDETERMINED
Options: {A verify the 08-13 snapshot then re-enable, B re-enable now, C record as deliberately off, D investigate the 08-13 common cause}.
Premise probes:
- `bd -C ~/gt backup status` → enabled=false, last sync 2026-08-13T17:55:48Z (1065 h ago). Still live. [measured]
- New fact the brief lacked: `~/gt/.dolt-backup/hq/manifest` has mtime **2026-09-26 08:28**. A separate local backup leg (the mol-dog-backup first stage) is current, on the same disk (/dev/disk3s1). [measured]
- `gc dolt health` shows per-db backup age ~15 h, `dolt_stale: true`. [measured]
So "no recovery path" is overstated today. The file:// bd-backup leg is still off, and whether to re-enable a data-plane setting is Taylor's call (declared server_touching). Related to mc-nq1cn but a distinct mechanism.

### mc-1st8f — UNDETERMINED
Options: {A re-embed as a TOML ''' literal, B hand double-escape, C external script file}.
- `grep -c "'''" formulas/brief-decision-dispatch.toml` → 0. [measured]
- The `"""` description at :126 still holds `\b` at :282 and `set -euo pipefail` at :182. [measured]
- mc-pdxpb is OPEN.
Defect live. POLICY-formulas.md has no rule on embedding scripts: grep for literal/embed/escape found none relevant. Engineering choice.

### mc-35tez — UNDETERMINED
Options: {A all epics plus re-parent, B 23 epic briefs plus read-only orphan census, C sample-gated, D rejected}.
- `SELECT … FROM hecke.issues WHERE issue_type='epic'` → 24 open, 4 closed. The brief said 23. [measured] Premise live.
A scope and volume choice on Taylor's own request. No rule reaches it.

### mc-3fzhb — UNDETERMINED (premise partly stale)
Options: {fast-fail, raise window, profile first, defer}, plus a rule on operators bypassing claim via `bd update --if-status`.
- `cmd/gc/cmd_hook_claim.go:84,123` → the window is `hookWorkQueryTimeout + hookClaimMutationTimeout`, with an operator override `GC_HOOK_CLAIM_WINDOW`. It was introduced at 18a47daec (08-14), before this brief. [measured]
The brief's "no supported way / constant-or-configurable unknown" is therefore stale: raising the window is a config knob. The repair choice and the bypass-rule question remain Taylor's.

### mc-42yyt — UNDETERMINED (premise partly stale)
Options: {A per-fork scratch namespace, B id-bound filename, C content guard, D inline rationale}.
- `grep -n -E 'scratch|\$\(cat [^<]|rationale.*\.txt' skills/adjudicate-brief/SKILL.md` → none. The skill passes `--reason "$RATIONALE"` inline (:108, :124). [measured]
- The skill was last changed at 1929974 (08-27 23:30), before the 08-28 incident. [measured]
So the skill never prescribed a fixed staging file. The collision came from the forks improvising a scratch file, and D is effectively the skill text already. Still open: whether a hard guard against fork improvisation (C) is wanted, and whether to audit earlier adjudications. mc-jj7xg is OPEN.

### mc-7r65j — UNDETERMINED
Options: {A add a load alarm, B attribute first, C accept steady state}. A monitoring-policy design choice. No Adopted rule requires host-resource alarms.

### mc-87wyq — UNDETERMINED
Options: {A runtime export, B compiler default, C rewrite formulas, D document}.
- `grep GC_WORK_DIR ~/repos/gascity --include=*.go` → set only in internal/convergence/condition.go:159. cmd/gc/hook_session_claim.go:101 comments "GC_WORK_DIR is not in the env of a pool session". [measured]
- `grep -rl GC_WORK_DIR ~/repos/mathcity/formulas | wc -l` → 7. [measured]
- mc-9blxa is OPEN.
Premise live. The decision is where the contract lives. Not determined.

### mc-8hoah — UNDETERMINED
Options: fix `gc dolt status` false "not running" (A trust health, …, D load-dependent).
- 5 back-to-back `gc dolt status` + `gc dolt health --json` rounds → 5/5 agree "running". [measured]
The intermittent defect was **not reproduced today**. That is not evidence of a fix. mc-leh5t is OPEN. A repair choice in upstream gc.

### mc-9bvqq — UNDETERMINED
Options: {A fix the trigger, B relocate the files, C …, D accept}.
- `orders/brief-shuffle-fast-drain*.toml` check is still `find .beads/briefs/.pile … -name '*.md' | grep -q .`, unchanged since 37b0413 / c7d0521. [measured]
- `ls ~/gt/mathcity/.beads/briefs/.pile/*.md | wc -l` → 185. [measured]
Premise live and larger. B2.4 (canonical membership is the bead query) bears on this, but it does not mechanically pick A over B. That reading would need interpretation, so no derivation.

### mc-bixkc — UNDETERMINED
Options: {A finish verdict A's re-sling, B accept as dropped, C re-adjudicate}.
- mc-b4t, mc-55t, mc-9f3 → open, assignee '' (updated 08-14). mc-ae9v7 OPEN. mc-x6a CLOSED "mc-ssm1y verdict A executed". [measured]
Premise live. Whether a 30-day-old authorization still licenses the sling is a judgement. The execution contract itself ordered abort-to-brief on drift. No Adopted rule reaches it.

### mc-d4c91 — UNDETERMINED
Options: {A rig-root + pinned base, …, reject, defer}.
- `~/repos/gascity-packs/gascity/assets/workflows/do-work/prepare-worktree.md:21-22` → still `$(pwd)/worktrees/<source-anchor-id>` and `--detach HEAD`. [measured]
- mc-17ybs is OPEN.
Live. The file is in the upstream gascity pack (read-only lane), and the design choice is Taylor's.

### mc-dxpli — UNDETERMINED
Options: {A file on public tdupu/mathcity, …, D profile first}.
- `gh issue list -R tdupu/mathcity --search '/city in:title'` and `'latency dashboard'` → no /city-latency issue. Related: #244 (MCP lock serialization, OPEN) and #130 (closed). [measured]
Measurements are 30 days stale. Public filing is Taylor's.
Note for the Mayor: the QUIMBY 70 derivation comment on this bead (2026-09-17) cites **B2.13**, which is marked **(JUDGEMENT RULE)** at subdomains/brief-system/POLICY.md:501. Under derive-verdict constraint 3 it may not be cited as a derivation constraint. The comment eliminated no option, so no verdict rests on it, but the citation should not be reused.

### mc-inuhq — UNDETERMINED
Options: {A hazard-first prime ordering, B prime contract change, C voluntary read, D accept}. A delivery design in the bd/gascity layer. No rule reaches it.

### mc-kqew9 — UNDETERMINED
Options: {A audit gates first, B harden producers now, C fix the three only}. It is partly sequencing, but C is a scope choice and the brief frames A as a design direction toward a shared parser, so it is not pure sequencing. The three underlying instances were not re-measured.

### mc-lrgoc — UNDETERMINED
Options: {fix Step 8's check, fix the attach}.
- `formulas/work-briefed.toml` "Step 8 — Verify assignment" still checks `{{source_bead}}` assignee, unchanged since 97097f7 (08-28), before this 09-09 brief. [measured]
Neither reading has been reproduced. Per the ratified reproduce-before-repair standard, which is a CLAUDE.md rule and not Adopted policy, the next step is a probe, not a pick.

### mc-mjl2j — UNDETERMINED
Options: {A adopt the six-clause auto-adjudication rule, B narrow it, C …, D keep per-case escalation}. Adopting a rule needs the owner's sign-off (the PP2.2 adoption path), so this cannot be derived by construction. It also overlaps the scope of ADR 0006 (Proposed).

### mc-o5sdm — UNDETERMINED
Options: {fix the parser, audit past rejections, both, and whether `--apply` keeps running meanwhile}.
- `assets/scripts/brief-shuffle-fast-drain.py:28` STATUS_PATTERN is unchanged. `gate_statuses` (:123) keys on raw group(1). [measured]
- Python regex check: `'- G5 Server-touching: PASS'` → key `'- G5 Server-touching'`, while the unbulleted line → `'G5 Server-touching'`. [measured] The defect reproduces at HEAD.
The audit scope and the interim `--apply` question are Taylor's.

### mc-pf2yb — UNDETERMINED (premise partly stale)
Options: {A fold into the producer build, B build first then amend, C amend first and hold the build, D keep B1.3 as an exception}.
- mc-dx91 (the producer build) is CLOSED, which kills A and C as timing options. [measured]
- `grep -n -F 'B1.3 Compact form is gated, not default.'` → POLICY.md:140, still present and not amended. [measured]
The live choice is B vs D. That is an ADR-0001-vs-Adopted-POLICY authority question, and this skill may not derive from an ADR. Also, 9 files cite B1.3, including gates.toml G5/G5b bindings.

### mc-psb7t — UNDETERMINED
Options: {A treat as a delivery defect (re-materialize, bounce, verify by fresh spawn), B suspend the fleet, C sanction override, D defer}.
- The source template has the fix (`gc gc claim` ×2, no EXPECTED_ASSIGNEE). [measured]
- The six identity beads and mc-k4t1s (P0) are all OPEN. [measured]
- `ps -axww | grep EXPECTED_ASSIGNEE` → no live process argv carries it. [measured] That probe **could not fail** for prompts passed via file or stdin, so fleet delivery is **unknown**, not fixed.
It needs the settling probe named in the brief's §3.

### mc-s0a4j — UNDETERMINED (premise partly stale)
Options: {A prescribe the attributed path, B relax classify_tier, C both, D accept}.
- Option A has landed: 1929974 (2026-08-27 23:30) threads `--adjudicated-by` through adjudicate-brief. [measured]
- mctl still allows omission. It emits `MBRF_ADJUDICATOR_UNRECORDED` at WARN, not a refusal (effects.py:1171-1174, 1262-1268). [measured]
- `classify_tier` still exists at materialize_plan.py:310. [measured]
The residual choice is A-only (accept residue for direct relays) vs C (also relax tier). That is a semantic trade-off.

### mc-v7rhw — UNDETERMINED (survivor of mc-b02eq)
Premise live, as measured under mc-b02eq. Whether 51.17 is a commitment or advisory is exactly the ambiguity the brief names. No rule reaches plan-schedule status.

### mc-xbbyj — UNDETERMINED
Options: {A repair the read path, B retarget the contract to the member-side check, C B now and A tracked, D neither}.
- `gc convoy list --json` in ~/gt/mathcity → **0 bytes after 158 s**. I stopped my own probe process (not the Dolt PID). [measured] Control: `gc dolt status` returned promptly in the same session, so this is not gc-wide.
Reproduced today. Repair choice open.

### mc-xrxvt — UNDETERMINED
Options: {build claim CAS, partition the rigs, both}. I did not probe kolchin, so the shared-remote premise is not re-measured. An architecture choice.

### mc-y9reo — UNDETERMINED (survivor of mc-tj7sy)
Options: {A repoint at the pack, B vendor into the rig, C fix resolution upstream, D accept but make visible}, plus the root-marking sub-question. Premise live (`.gc/scripts` absent). Dev POLICY P1 (pack portability) is argued in the brief to disfavour B. I did not treat that as elimination, because it needs a reading of P1 against a specific vendoring pattern. Even if P1 eliminates B, three options remain, so it would be UNDETERMINED anyway.

### mc-z080m — UNDETERMINED
Options: {A wire this one consumer, B audit plus wire, C consumer registry, D accept unread events}. Design. No rule reaches it.

---

## Tally

| Outcome | Count | IDs |
|---|---|---|
| DERIVED | 0 | — |
| MOOT | 5 | mc-2ju8s, mc-55dlr, mc-aj15r, mc-t8zeo, mc-up5vd |
| DUPLICATE | 4 | mc-027dz→mc-jq637, mc-19zky→mc-nq1cn, mc-tj7sy→mc-y9reo, mc-b02eq→mc-v7rhw |
| DERIVED-OUT | 2 | mc-vynt6, mc-sw2a7 |
| CONFLICT | 0 | — |
| REFUSED_JUDGEMENT / REFUSED_CONTESTED | 0 | — |
| UNDETERMINED | 27 | the remainder (7 flagged as having partly stale premises: mc-3fzhb, mc-42yyt, mc-c441c, mc-nq1cn, mc-pf2yb, mc-s0a4j, mc-8hoah (not reproduced today)) |
| **Total** | **38** | |

Not consulted, all Draft or no Status row (so not citable under PP2.1): POLICY-BEAD-REVIVAL.md, POLICY-skills.md, subdomains/{computing,latex,lmfdb,magma,mayor,policies}/POLICY.md, and brief-system/POLICY-DRIFT-AUDIT-2026-08-19.md.

[autogenerated by Claude Opus 5.5 (Claude Code) on 2026-09-26]
