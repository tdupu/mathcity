# Derivation pass — mathcity pending briefs, batch mc2 (38 briefs) — 2026-09-26

Derivation RECORD for the Mayor. Read-only: no verdict recorded, no bead/brief/cache written. ADR 0006 is Proposed, so nothing here is authority to record.
Adopted corpus re-measured 2026-09-26 (status lines): POLICY-POLICY.md, POLICY-beads.md, POLICY-formulas.md, subdomains/brief-system/POLICY.md, subdomains/dev/POLICY.md, subdomains/dev/POLICY-city.md, subdomains/dev/POLICY-documentation.md. All other policy files: Draft or no Status row.
Bodies read via `bd -C ~/gt/mathcity show <id>`. The work was split into four sub-passes (A, B, C, D), and their sections are concatenated below.
Process note: sub-pass D ran one `git fetch -q` in ~/repos/mathcity. That only moves remote-tracking refs, but ~/repos/mathcity is BART's lane.
Parent spot-check: B2.16 text at subdomains/brief-system/POLICY.md:604-627 was re-read by the parent. The title carries no PROPOSED or JUDGEMENT marker, and the mc-snxym quotes match.

<!-- sub-pass A -->
# mc2 derivation pass — part A (10 briefs, rig mathcity)

Read-only derivation record, 2026-09-26. Nothing recorded, closed, commented or written to any bead.
Adopted docs re-checked by `grep -m1 '^| Status |'`: POLICY-POLICY, POLICY-beads, POLICY-formulas,
brief-system/POLICY, dev/POLICY, dev/POLICY-city, dev/POLICY-documentation (all others Draft / no status row).
Brief bodies read via `bd -C ~/gt/mathcity show <id>` (dumped to scratchpad/derive/mc2/).

### mc-370v3 — MOOT
Question/options: finish the verdict-A supersede of mc-73k by closing its open residue (A), patch the dispatcher to refuse superseded-stamped work (B), or re-freeze the frontier behind a hold gate (C).
Premise probes:
`bd show mc-73k` → CLOSED, close reason "superseded-by-defect per mc-ssm1y verdict A (Taylor, 2026-08-28)" [measured]
`bd show mc-1x3 / mc-2zi / mc-w40 / mc-6xo / mc-tj6` → all CLOSED (the brief's named "stamped-but-open" and "unstamped" beads) [measured]
`bd dep tree mc-73k | grep -vc '(closed)'` → 0 non-closed nodes in the whole graph (only header lines) [measured]
`bd show mc-wze` → OPEN (orphan input convoy); `bd show mc-t6phs` → OPEN (stale decision bead) [measured]
Grounds: The load-bearing premise — "the graph is open and dispatchable" — is measurably dead: root and every descendant are closed. Option A's core act (close root + open descendants) is already done; B and C exist only to contain an open, dispatchable graph, which no longer exists. The brief's own A-step says "re-measure the mc-73k residue; if still open, close" — re-measured, not open. Residue is bookkeeping only: dispose convoy mc-wze and close/answer decision bead mc-t6phs (itself not in this list; its hold-gate premise is likely also dead [inferred]).
Surviving option (if any): none needed; A is executed. Residual bookkeeping (mc-wze, mc-t6phs) is not a human decision.

### mc-0nyo5 — UNDETERMINED
Question/options: reaper has not completed a run since ≥2026-08-23 — A restore Dolt backup (unblocks prune leg), B fix timing-out CTE query, C both backup-first (recommended), D accept and defer.
Premise probes:
`tail events.jsonl | grep '"subject":"reaper"'` → latest fire 2026-09-22T01:25 `order.failed` "context deadline exceeded" [measured]
`gc dolt health --json` → backups.dolt_measured=true, dolt_freshness "2081h3m", dolt_stale=true [measured]
`git -C ~/repos/gascity grep` of the CTE rewrite marker ("Mechanism A (workflow mc-ye1w1") in reaper.sh → 0 hits; fix commit 3e69cfd0f exists only in ~/gt/gascity on branch fix/reaper-cte-materialize-mc-3yrly [measured]
`bd show mc-cfgd` → CLOSED, verdict approve option A (commission the CTE fix), 2026-08-25 [measured]
Grounds: Both legs' premises are live (reaper still fails; backup still stale). Leg B (query) was already commissioned by decision mc-cfgd before this brief was filed, and its outcome is the subject of mc-b87er — so options B/C's query half overlap an in-flight decision [measured]; the backup-restore leg is untouched. Recorded decision beads are not policy authority (skill: "Derive from a recorded decision bead" is out of scope), so this narrows nothing formally. No Adopted rule chooses between restore-backup / accept-defer. Also stop-gated: body declares `server_touching: true` (backup restore is a live-server write), which would itself block a derivation.
Surviving option (if any): — (genuine decision; effectively reduces to "authorize the backup restore, yes/no", since the query leg is already commissioned [inferred])

### mc-b87er — UNDETERMINED
Question/options: reaper CTE fix is correct but misses its bar on hecke/other stuck rig — land the partial fix, apply the staged follow-on mechanism, reopen the mechanism choice, or do nothing / close as not-worth-it.
Premise probes:
`git -C ~/gt/gascity show --stat 3e69cfd0f` → exists, "perf(reaper): materialize workflow-root join keys ahead of the recursion", branch fix/reaper-cte-materialize-mc-3yrly only [measured]
`git -C ~/repos/gascity cat-file -t 3e69cfd0f` → not a valid object; reaper.sh on ~/repos/gascity main (4bafc941b, 2026-09-19) lacks the rewrite marker [measured]
latest reaper fire 2026-09-22 → failed, context deadline exceeded [measured]
Grounds: Premise live — the fix has not landed and the reaper still times out. Choice among land/partial/follow-on/reopen is an engineering-and-risk judgement; no Adopted rule reaches it. Body `server_touching: true`. Not a duplicate of mc-0nyo5: mc-0nyo5 is the parent question (both legs + backup); this is the outcome of the query leg only.
Surviving option (if any): —

### mc-ogwa8 — UNDETERMINED
Question/options: repair drain-ack's slow return by (A) extending gascity's pack-hash skip list to worktrees/, codex-worktrees/, .claude-wt-*; (B) removing the uncached provenance snapshot from the credential-provider path; (A+B) A now, B filed; (D) wontfix mc-0usge.
Premise probes:
`sed -n 3049,3090p ~/repos/gascity/internal/config/pack.go` → isIgnoredPackRuntimePath skips .beads/.cache/.gc/.git/state/tmp, __pycache__/node_modules/.pytest_cache, and `.claude/worktrees` only — NOT bare worktrees/, codex-worktrees/, .claude-wt-* [measured]
`bd show mc-0usge` → OPEN; `bd show mc-6e4y2` → OPEN [measured]
comment on mc-whfov (2026-09-16, review-synthesizer) → one drain-ack run returned exit 0 after ≥5:46 at ~42% CPU, state R — consistent with this brief's cause [measured by that session, recorded; not re-run here because running drain-ack is itself an action]
Grounds: Premise live — option A has not landed. Choosing among A / B / A+B / D is a design and risk call (B touches a deliberate correctness guard per the brief); no Adopted rule reaches it.
Surviving option (if any): — . Cluster note: of the three drain-ack briefs (mc-ogwa8, mc-whfov, mc-qi4o3), this is the one whose premise survives measurement intact; the other two should be read against it.

### mc-whfov — UNDETERMINED (premise partly stale)
Question/options: unwedge "non-returning" drain-ack by (A) evidence-first operation on the live supervisor, (B) protocol hardening (client timeout + idempotent retry + drained-but-unacked sweep), or (C) A then B.
Premise probes:
`bd comments mc-whfov` (2026-09-16 06:01) → "REFUTES THIS BEAD'S PREMISE … gc runtime drain-ack DOES return. It is a slow busy-wait, not a hang" — exit 0, "Drain acknowledged", ≥5:46 elapsed, state R [measured by that session, recorded]
mc-qi4o3 title carries "[CORRECTED: it does return]" [measured]
`bd show mc-6e4y2` (source) → still OPEN, title still "non-returning" [measured]
Grounds: The "hangs forever / unwedge" framing is contradicted by a recorded one-run measurement; the same comment explicitly declines to say hangs never occur on other hosts. That is not enough to call the premise dead, so not MOOT. A prior comment on this bead argues it is NOT a duplicate of mc-ogwa8 (different prescribed work: supervisor/protocol vs gascity pack-hash cause); a later comment suggests closing it as superseded by mc-ogwa8. That conflict between two agents' readings is itself a reason not to call DUPLICATE here. No Adopted rule reaches the choice.
Surviving option (if any): — (recommend the Mayor present it only together with mc-ogwa8, or ask whether it survives mc-ogwa8's repair)

### mc-qi4o3 — UNDETERMINED
Question/options: operating posture while drain-ack is diagnosed — (A) diagnose first, keep draining; (B) amend protocol to skip drain-ack; (C) accept and monitor.
Premise probes:
title "[CORRECTED: it does return]"; body line 463: "returning" / "hangs forever" (mc-6e4y2, mc-whfov) are too strong [measured]
body line 492/542: "Does not re-derive mc-ogwa8's pack-SHA-256 root cause" [measured]
pack.go skip list unchanged (see mc-ogwa8) → cost still being paid [measured]
Grounds: Premise ("no cause has been reproduced, nothing to repair yet") is partly stale — mc-ogwa8 claims a source-level root cause, which this brief inherits without re-deriving. The posture question is interim-only; if mc-ogwa8 is decided and lands, this becomes moot [inferred]. Not formally a duplicate (different option set: posture vs repair). No Adopted rule reaches it.
Surviving option (if any): — (natural candidate to defer behind mc-ogwa8)

### mc-7fwku — UNDETERMINED
Question/options: approved claim-guard fix (mc-ix0c3, verdict approve A, 2026-09-08) has not landed; (1) where to land it, (2) patch the inline claim block (A) or delete it and delegate to `gc gc claim` (B), (3) release latch mc-kbb.
Premise probes:
`bd show mc-ix0c3` → CLOSED (adjudicated approve) [measured]
`grep -c 'while true'` in cached role templates `~/gt/.gc/cache/repos/9bce37…/gascity/{template-fragments/gc-role-worker.template.md, roles/agents/run-operator/prompt.template.md}` → 1 each, 239/237 lines, mtime 2026-08-05 — unbounded inline loop still present [measured]; that this cache is what dispatches prompts is [inferred]
`git -C ~/repos/gascity-packs log -1 -- gascity/template-fragments/gc-role-worker.template.md` → a8d8907 2026-07-14, unchanged [measured]
`bd show mc-kbb --json` → status open, assignee null, updated 2026-09-21 [measured]
cache: `.beads/briefs/.pile/.rejected/mc-7fwku/rejection.json` → rejected 2026-09-16 for "G9 evidence must contain exactly one G9 No-brainer-filter line" (formatting); canonical bead remains OPEN [measured]
Grounds: Calls (1)–(2) are live: the fix has not landed. Call (3) is stale — mc-kbb is no longer pinned in_progress; it has been returned to the pool (open, unassigned) [measured], which was what "release" asked for. Patch-vs-delete is a design call; no Adopted rule reaches it. (Recorded decision mc-ix0c3 approved a fix but is not policy authority for this skill.)
Surviving option (if any): — ; item 3 can be dropped from the question.

### mc-uwyhb — DUPLICATE (of mc-7fwku; mc-7fwku should survive)
Question/options: (1) unwedge mc-kbb — (A) close as completed, (B) reset to open/unassigned, (C) leave pinned; (2) whether to re-drive the twice-approved claim-guard fix.
Premise probes:
`bd show mc-kbb --json` → status open, assignee null, updated 2026-09-21 — no longer "stranded in_progress" [measured]
`bd dep tree mc-kbb` per body → mc-98s, mc-nd3 CLOSED; `bd show mc-98s`, `bd show mc-nd3` → both CLOSED [measured]
`bd comments mc-kbb` (2026-09-16 18:31) → latch returned "UNCLOSED and unassigned per Taylor's adjudicated verdict on mc-2dlh5 … worker-side release only" [measured]
cached role template still has unbounded `while true` claim loop [measured; see mc-7fwku]
Grounds: Half (2) is the same decision as mc-7fwku §1(1)–(2) (re-drive / land the approved claim-guard fix); mc-7fwku is the more specific of the two (it names the fix site: inline template vs run.sh). Half (1)'s premise is stale: option B is now the measured state and option C ("leave pinned") no longer exists. What remains of half (1) is "close mc-kbb as completed, or leave it open for re-offer" — the same bead mc-7fwku §1(3) addresses. No Adopted rule settles close-vs-leave: BP4.2(a) lists orphaned step titles ("Finalize workflow", …) and mc-kbb's title is "work-briefed", so fitting it needs judgement.
Surviving option (if any): keep mc-7fwku; fold uwyhb's residual "close mc-kbb (A) vs leave open" into it.

### mc-cns3c — UNDETERMINED
Question/options: which layer normalises session-ID vs session-name identity — (A) gc hook --claim / worker env, (B) role-prompt claim block precedence, (C) bd accepts any identity spelling.
Premise probes:
`bd show mc-rcttx` → OPEN (same mechanism) [measured]
`bd show mc-ix0c3` → CLOSED, approve option A "identity-agnostic match + bounded retry" at the claim block (2026-09-08) [measured]
cached role template still has the inline claim loop [measured; see mc-7fwku]
Grounds: Premise live (defect unfixed). A prior recorded verdict (mc-ix0c3) already chose a claim-block fix, which overlaps this brief's option B. That verdict is not policy authority for this skill, so it cannot derive B. Choosing a layer is a design decision no Adopted rule reaches. Cluster: mc-7fwku / mc-uwyhb / mc-cns3c / mc-rcttx all belong to one claim-identity defect family.
Surviving option (if any): —

### mc-k6tmt — UNDETERMINED (premise hollow)
Question/options: approve (execute) the proposed mc-0ka closure/reconciliation graph (simple-work-briefed N1+N2, which re-verifies read-only and files a close/keep brief), or not; plus confirm the scope-line reading of the B1.3 acceptance tension.
Premise probes:
`git -C ~/repos/mathcity cat-file -t 1d84564 / 4ed2a7c` → both commits, both ancestors of origin/main [measured]
`gh issue view 74 -R tdupu/mathcity` → CLOSED 2026-08-22T05:22:25Z [measured]
`bd show mc-0ka` → OPEN [measured]
Grounds: The brief's own premise holds: the commissioned work is already merged and its GitHub issue is closed. What it asks is to authorize a verification pass whose only output is a further "close mc-0ka or keep it?" brief, so the graph produces one more decision without doing any repair. No Adopted rule closes a bead because its mirrored GH issue closed (searched POLICY-beads, brief-system, dev, city, formulas for GH-issue closure rules: none). BP4.2(b)/(c) do not fit (not superseded, not a duplicate). So this cannot be derived. Mayor option: offer the close/keep question on mc-0ka directly instead of commissioning a graph to generate it [inferred].
Surviving option (if any): —

## Tally

| Outcome | Count | IDs |
|---|---|---|
| MOOT | 1 | mc-370v3 |
| DERIVED | 0 | — |
| DERIVED-OUT | 0 | — |
| DUPLICATE | 1 | mc-uwyhb (→ mc-7fwku) |
| CONFLICT | 0 | — |
| REFUSED_JUDGEMENT / CONTESTED | 0 | — |
| UNDETERMINED | 8 | mc-0nyo5, mc-b87er, mc-ogwa8, mc-whfov, mc-qi4o3, mc-7fwku, mc-cns3c, mc-k6tmt |

Clusters for the Mayor, not formal duplicates: reaper (mc-0nyo5 parent, mc-b87er query-leg outcome); drain-ack (mc-ogwa8 is the surviving root-cause brief, while mc-whfov's premise is contested and mc-qi4o3 is an interim posture); claim-identity (mc-7fwku, mc-cns3c, plus the absorbed mc-uwyhb). Stale sub-premises: mc-7fwku item 3 and mc-uwyhb half 1 (mc-kbb is already released, open and unassigned), and mc-whfov "hangs forever". mc-0nyo5 and mc-b87er are marked server_touching:true.

<!-- sub-pass B -->
# mc2 derivation pass — part B (10 briefs, rig mathcity)

Derivation record only. Nothing written to any bead, brief, cache or ref. ADR 0006 is Proposed.
Brief bodies read via `bd -C ~/gt/mathcity show <id>` (read-only). Policy text read from
`~/gt/mathcity` and confirmed byte-identical to `~/repos/mathcity` origin/main (`7de4478`) for
`subdomains/brief-system/POLICY.md` and `subdomains/dev/POLICY.md` (`git show origin/main:<f> | diff -q -` → same) [measured].
Document status re-checked: the 7 Adopted docs match the task list; the rest are Draft or have no Status row [measured].

### mc-1h6r4 — REFUSED_STOP_GATE
Question/options: should brief-prep SKILL.md's Gate Evidence instructions be repaired? {APPROVE data-reading fix, APPROVE prose correction, HOLD until sibling parser fix lands, REJECT}.
Premise probes:
- `grep -n '17 entries' skills/brief-prep/SKILL.md` in ~/gt/mathcity, ~/repos/mathcity, ~/.claude/skills/brief-prep (symlink → mathcity) → line 118 `(G1–G16 **plus G5b** — 17 entries)` in all three [measured]: stale count still present.
- `sed -n 236,256p assets/brief-pipeline/gates.toml` → `[profiles.standard]` lists G1..G16, G5b, **G17** = 18 gates [measured]. Premise live.
- `grep -n action_block skills/brief-prep/SKILL.md` → no hit [measured]; the undocumented-section defect is live.
Grounds: the brief self-declares `user_skill_touching_override: true` (the fix edits `~/.claude/skills/brief-prep/SKILL.md`). derive-verdict step 0 refuses user-skill-touching questions ("a derivation is not a route around a gate"). Note for the human: P5.4 (code wins, doc corrected in same pass) would kill REJECT if the gate were not in the way, but it does not choose between the data-reading and prose options.
Surviving option: none derived. Goes to Taylor as a stop-gated decision; premise is fully live.

### mc-31b8c — DERIVED-OUT
Question/options: what order are five reproduced adjudication-UX defects fixed in, and who builds them (Mayor in-session vs fleet through BART's lane)? The defects themselves are stated as already ruled by Taylor.
Premise probes: `bd show mc-x8uox / mc-pf5pm / mc-5fo2a / mc-lre5h / mc-q3m5q` → all OPEN [measured]. The premise is live, but the question is only about sequencing and ownership.
Grounds: this is a standing instruction, not a policy rule. `~/gt/CLAUDE.md:360`: "Staffing, routing, and sequencing are NOT his. Who does what, who reviews whom, what order things merge in — the coordinator owns all of it." Both halves (fix order; who builds) are in that class. No Adopted rule cited. The SPEC-recording part is bookkeeping and needs no decision.
Surviving option: the coordinator decides the order and routing. The five defect beads stay open as work.

### mc-3gj9n — UNDETERMINED
Question/options: three brief-shuffle defects. (A) fix all three; (B) disposition rule for adjudicated artifacts only; (C) move mc-f045 by hand and defer the rules; (D) defer.
Premise probes:
- `ls .beads/briefs/.pile/mc-f045.md` → absent; `ls .pile/.rejected/mc-f045/` → brief.md plus rejection.json, mtime Aug 29 08:07 [measured]. The pile-head instance (defect 2) is gone: the artifact was rejected into `.rejected/`, which is the harm the brief warned about. `bd show mc-f045` → CLOSED [measured].
- Defect 1: `bd show gt-ilcalm / gt-lk1no1 / gt-kuxg48 / gt-isxvvc` → all CLOSED [measured]. The observed duplicate pairs are finished. Whether the compiler still emits both step_id forms was not measured.
- Defect 3: `ls mathcity/.beads/briefs/.staging/` → mc-99jj-, mc-jvqq-, mc-h9zl- flat files still present, same sizes and mtimes as the brief states [measured]. Live. Their subjects: mc-99jj OPEN task, mc-jvqq OPEN task, mc-h9zl CLOSED decision [measured].
- Source bead mc-gojmg → OPEN [measured].
Grounds: the defect-2 half has been overtaken. Its general rule question (how an adjudicated artifact is dispositioned) is the one mc-zp1fs asks with fuller evidence, and B2.16 already kills the "reject" disposition for mechanical failures (see mc-zp1fs). Defect 1 is engineering. For defect 3, B2.4 (one pile) could reach the stranded files, but only 1 of the 3 has a decision bead and that one is closed, so applying B2.4's bead-query membership requires interpretation. Not derived.
Surviving option: none derived. Premise partly stale: the mc-f045 head-of-queue wall is gone, and the defect-2 half duplicates mc-zp1fs. Recommend re-scoping to defect 3 (plus a survey for defect 1).

### mc-4bo0m — UNDETERMINED
Question/options: publish the self-adjudication gate (mc-x7tl) {publish after the 2-key provenance repair, publish as-is then repair, hold for re-derivation, reject/abandon}.
Premise probes:
- `bd show mc-x7tl` → CLOSED (build workflow) [measured].
- `git -C ~/gt/mathcity merge-base --is-ancestor <c> origin/main` for WI commits 816d64f, 22481da, 60e746f, cf36bc2, d85c542, 2909c9c → all NOT in origin/main (7de4478). None exist in ~/repos/mathcity [measured].
- `grep -n self.adjudicat ~/repos/mathcity/assets/scripts/mctl_core/effects.py` → only the #152 note "This does NOT refuse self-adjudication" (line 1160) [measured].
Premise live: the gate is still unpublished and the hole is still open.
Grounds: no Adopted rule chooses between publish orderings for a security fix. This is a genuine risk trade-off.
Surviving option: none derived. Premise fully live.

### mc-snxym — DERIVED
Question/options: when a brief fails a structural gate, does it keep being moved off the stack into `.pile/.rejected/` (status quo), or does the disposition change? Options: (A) fail soft, meaning the brief stays visible and flagged, or bounces back to the producer; (B) shape-only auto-repair normalizer; (C) fix producer skills; (D) triage and drain the already-stranded rejected briefs. Recommended A+D.
Premise probes:
- `ls .beads/briefs/.pile/.rejected | wc -l` → 67; rejection.json mtimes by date include 2026-09-17 ×9 and **2026-09-20 ×2** [measured]. Removal is still happening after the brief was filed.
- `git -C ~/repos/mathcity log origin/main --since=2026-09-16 | grep -iE 'reject|fail.soft|B2.16|malformed'` → no hits [measured]. The fix has not landed, so this is not MOOT.
- `git log -S'B2.16 A mechanical gate failure'` → added in `2294e72` on **2026-09-07**, ten days before this brief (2026-09-17) was filed [measured].
- mc-7fwku (the "dropped" P0 escalation) is an OPEN decision bead and is in the current pending list [measured]. The canonical bead pile still holds it; what it lost is the filesystem presentation view.
Grounds: B2.16, `subdomains/brief-system/POLICY.md`, Adopted, not PROPOSED, not marked JUDGEMENT. Quotes verified with `grep -n -F`:
- :609-610 "a mechanical failure MUST" / "NOT remove the brief from any pile, index, queue, view, or presentation" (line 610 reproduces with `grep -n -F`)
- :624 "mechanically-rejected brief stays in its pile/index and adjudicable, carries"
- :627 "queue or view, is recorded as a verdict, or strands it where nothing reads it"

What the rule kills:
- Status quo (move to `.rejected/`): killed by :610 and :627.
- A's "bounce back to producer" variant: killed, because it removes the brief from the adjudicator's view (:610).
- B alone and C alone: killed as *substitutes*, because any brief they fail to fix is still removed (:610). The rule delegates producer repair to city/dev ("the repair is raised through the owning (city/dev) surface", :624-626), so B and C remain open as coordinator-routed repairs. They are not a disposition choice.
- "Do not triage the stranded population": killed by :627, since the existing `.rejected/` briefs are in the "strands it where nothing reads it" fail state.
Surviving option: **A in its flag-in-place form, plus the restore-to-adjudicable half of D.** Per-brief content rulings on the restored briefs are then ordinary adjudications. The choice among B and C is repair routing (coordinator). This brief is a PP1.10 surfacing of a question B2.16 already answered.

### mc-zp1fs — UNDETERMINED
Question/options: how to enforce the adjudicated-brief guard (mc-8ehd0) across all writers to `.pile/.rejected/`. (A) one write boundary; (B) extend the drift test to every writer; (C) remove the agent writer's path; (D) the guard is wrong, so stop promoting adjudicated briefs.
Premise probes:
- `bd show mc-8ehd0` → OPEN P0; `mc-mhq8x` → OPEN P1; `mc-xkd2s` (restore) → CLOSED [measured].
- `.pile/.rejected/mc-f045/rejection.json` exists; mc-f045 is CLOSED/adjudicated [measured]. The live instance matches the brief.
Grounds: B2.16 (`subdomains/brief-system/POLICY.md:610`, quoted above) **kills D**. The mc-f045 rejection was for missing provenance metadata, which is a mechanical failure, and it removed the brief and wrote a rejection record, contrary to "MUST NOT remove the brief from any pile, index, queue, view, or presentation". B2.3 (:289-292, "Presenters / and any pile-reading process MUST filter to open brief beads") makes the brief's unverified "presenters filter terminal briefs" assumption a *required* property. That removes D's supporting argument but does not choose among A, B and C. P7.1 (sole writer) might disfavour B-alone, but whether rejection.json is a "brief artifact" under P7.1 is interpretive. Not used.
Surviving option: A, B and C all survive. This is a design choice. Policy has already eliminated D.

### mc-kqmj1 — REFUSED_JUDGEMENT
Question/options: two shipped scripts write brief artifacts directly. (A) refactor through mctl; (B) declared exemption with machine-checkable lapse; (C) survey all scripts first; (D) amend P7.3.
Premise probes: `git show origin/main:assets/scripts/brief-shuffle-fast-drain.py | grep -n 'write_text|.write(|fdopen'` → lines 519/520, 539/540, 652, 729, 763; `brief-stack-index.py` → 78/80; `grep -c -i exempt` → 0 in both [measured, origin/main 7de4478]. Premise live (line numbers shifted by about 6 since 998b4bc).
Grounds: the reaching rule is P7.1, and its exemption clause is declared judgement-kind. `subdomains/dev/POLICY.md:643`: "or it does not, and a grep can say which. P7.1's *exemption* clause and P7.4 are" (continuing "**judgement**"). :666 "exemption**. *Granting one is a judgement call, not a checkbox*: a reasoned". Option D is a policy amendment and cannot be a brief verdict (PP1.4 path). QUIMBY 70's 2026-09-16 comment on the bead already recorded "No option is eliminated" among A, B and C.
Surviving option: none derived. Goes to Taylor as a refusal. The judgement clause governs A vs B vs C.

### mc-anjnx — MOOT
Question/options: 19 test fixtures in `~/.gc/mathcity/aggregated-briefs/decisions/` that brief-decision-dispatch would act on. The options were quarantine, stop the writer, guard, or a combination, plus whether the two records mc-7a98s and mc-wbwel are genuine.
Premise probes:
- `ls ~/.gc/mathcity/aggregated-briefs/decisions/` → 2 files (gsp-duj6y8.toml, mc-q0nby.toml). None are the 21 cited [measured].
- `ls archive/decisions/` → includes mc-body.toml, mc-declared.toml, mc-7a98s.toml … [measured]. The fixtures were consumed and archived.
- `decisions-dispatched.jsonl` now exists: 58 lines, 47 by `gt-lmj5va`, dispatched_at 2026-09-09T08:06Z to 2026-09-16 [measured]. The run the brief withheld has executed. Its rows include mc-body→follow-up gt-tfh3cg, mc-legacy→mc-aeznu, mc-declared→escalation gt-83e84h, and mc-7a98s/mc-wbwel→"approve-recorded … no publisher handoff".
- `bd show gt-tfh3cg / mc-aeznu / gt-83e84h` → all OPEN [measured]: the spurious beads the brief predicted now exist.
- `bd show mc-7a98s / mc-wbwel` → both CLOSED [measured].
Grounds: the requested action (decide before the literal run) is dead. The run happened, and the fixtures are no longer in the root.
Residue, not part of this brief: (1) three spurious open beads from fixture residue need cleanup. That is a new question, per B2.3's "the remedy is a NEW brief bead". (2) The guard or stop-the-writer half lives on mc-w5v0b (OPEN P1) as engineering. The writer was not traced.

### mc-dbhgm — MOOT
Question/options: two open briefs prescribe different fixes for latch defect mc-k4t1s. (A) mc-y88p0 governs; (B) mc-kjot0 governs; (C) present both and rule once.
Premise probes:
- `bd show mc-kjot0 --json` → CLOSED 2026-08-27T22:48Z, close_reason "Superseded by mc-y88p0 (P0)…" [measured].
- `bd show mc-y88p0 --json` → CLOSED, verdict approve / option A, adjudicated_by Taylor Dupuy 2026-08-28T23:32Z [measured].
- `bd show mc-k4t1s` → still OPEN (the defect itself) [measured].
Grounds: the premise "two OPEN briefs" is dead. One was superseded and the other was adjudicated by Taylor (option A). The question has been answered.
Surviving option: none needed. mc-y88p0 governs by Taylor's recorded verdict.

### mc-n3bih — UNDETERMINED
Question/options: stop no-brainer-candidate-curate from concurrent re-firing. (A) self-clearing condition by draining descriptors; (B) pacing; (C) single-flight lock; (D) revert to manual. A and C compose.
Premise probes:
- `git show origin/main:orders/no-brainer-candidate-curate.toml` → still `trigger = "condition"`, no cooldown, max-attempts or singleton; last change 6f2ef61 (2026-08-20) [measured]. The design defect is live.
- `grep no-brainer-candidate-curate ~/gt/.gc/events.jsonl` → 971 hits, latest 2026-09-19T15:19 [measured].
- Candidate piles `.beads/.gates-candidate-pile` and `.beads/briefs/.gates-candidate-pile` in the mathcity rig → 0 `*-candidate.md` [measured]. The condition is false in this rig right now. Other rigs were not checked.
Grounds: F2.3 (shared paths must not be silently modified) bears on the overwrite symptom but does not select a mechanism. No Adopted rule chooses among trigger, pacing and lock designs.
Surviving option: none derived. Premise partly stale: nothing is re-firing in mathcity right now because the pile is empty, but the design flaw is unchanged.

## Tally (part B)

| Outcome | Count | IDs |
|---|---|---|
| DERIVED | 1 | mc-snxym |
| DERIVED-OUT | 1 | mc-31b8c |
| MOOT | 2 | mc-anjnx, mc-dbhgm |
| DUPLICATE | 0 | (mc-3gj9n's defect-2 half duplicates mc-zp1fs; recorded under UNDETERMINED) |
| REFUSED_JUDGEMENT | 1 | mc-kqmj1 |
| REFUSED_STOP_GATE | 1 | mc-1h6r4 |
| UNDETERMINED | 4 | mc-3gj9n, mc-4bo0m, mc-zp1fs (D eliminated by B2.16), mc-n3bih |
| **Total** | **10** | |

<!-- sub-pass C -->
## Part C — 9 briefs (mathcity rig). Derivation record only; nothing written to any bead.

Doc status re-measured 2026-09-26 (`grep -m1 '^| Status |'`): the 7 Adopted docs match the task list; all others Draft or no Status row.

### mc-897zw — DUPLICATE (of mc-9cr72), and its (a) half is MOOT
Question/options: (a) may decomposition on mc-slng be dispatched as-is / repointed; (b) structural fix: A suffix defaults with workflow id, B per-workflow subdir, C fail closed on collision, D repair mc-slng only.
Premise probes:
- `bd -C ~/gt/mathcity show mc-slng` → CLOSED [measured]; `mc-ekq5`, `mc-m083` ("Create task beads", the consumers) → both CLOSED [measured]
- `ls -la ~/gt/mathcity/.beads/briefs/` → `decomposition-mc-slng.md` (Sep 15), `implementation-plan-mc-slng.md`, `factory-run-mc-slng.md` exist [measured] — mc-slng ran to completion on suffixed paths
- same `ls` → unsuffixed `review-report.md` (Sep 15), `implementation-summary.md` (Sep 12), `factory-run.md` (Sep 12) still being written after the brief [measured]; `bd show mc-yl3pn` (source defect) → OPEN [measured]. So the default is [inferred] still unsuffixed.
Grounds: (a) is dead — the workflow it gates is closed. (b) is the same decision as mc-9cr72 with the same option set (A suffix / B subdir / C fail-closed guard; D here = "do nothing structural"), same source bead mc-yl3pn.
Surviving brief: **mc-9cr72** (single question, cleaner option framing). Carry mc-897zw's 2026-09-15 comment (three roots mc-vzx0/mc-slng/mc-fhv3 claiming the same `factory-run.md`, one write away from destroying a closed workflow's artifact) into it as evidence.

### mc-9cr72 — UNDETERMINED
Question/options: which discriminator is canonical for build-basic artifact path defaults: A suffix with workflow root id, B per-workflow subdirectory, C fail-closed guard (composes with A or B).
Premise probes:
- `bd show mc-yl3pn` → OPEN [measured]; unsuffixed artifacts still written after 2026-09-06 (see mc-897zw) [measured]; the collision is live [inferred: default unchanged]
- `grep -rn 'implementation-plan|decomposition\.md|factory-run' ~/repos/gascity-packs/gascity/{formulas/build-basic.formula.toml,assets/workflows/build-basic}` → only prose ("normally `factory-run.md`") [measured]; where the defaults are computed was not located, so "unchanged in code" is [inferred] from the files on disk.
Grounds: no Adopted rule chooses between suffixing and subdirectories. Candidate discarded: F2.3 (`POLICY-formulas.md:113`, "Shared paths must not be silently modified") — whether POLICY-formulas reaches an imported gascity-pack formula (F8.3 calls those "capabilities") and whether a step writing to its *declared* recorded path is "silent" are both readings I would have to pick → not usable. Even read generously it only kills "accept the risk", not A vs B.
Surviving option: none determined; A/B/C all live. Survivor of the mc-897zw/mc-9cr72 pair.

### mc-7xn6p — MOOT
Question/options: dangling `{{summary_path}}` in do-work close-source-anchor template: A drop the slot, B define `summary_path` as a do-work formula variable, C leave it.
Premise probes:
- load-bearing premise: "`{{summary_path}}`, which is not a defined do-work variable"
- `sed -n 20,28p ~/repos/gascity-packs/gascity/formulas/do-work.formula.toml` → `[vars.summary_path]` / `description = "Optional per-item summary path."` / `default = ""` [measured]
- same block in the cached formula the root actually ran (`~/.gc/cache/repos/af5bc…/gascity/formulas/do-work.formula.toml:26-28`, the `gc.formula_source` of mc-amzb4) [measured]
- `git log -S'vars.summary_path' -- gascity/formulas/do-work.formula.toml` → `b19d181 2026-05-30` [measured] — defined 3.5 months before the brief
- template line 3-4: "Write per-item summary to {{summary_path}} when set. If `summary_path` is not set, first use …" [measured] — the empty render is the designed optional-var path, and the next sentence is the fallback chain.
Grounds: the premise is measurably false. Option B is already the state of the code; the "undefined variable" diagnosis is actually "optional variable left at its empty default". What is left is a cosmetic A-vs-C wording choice ("to  when set" reads oddly) that nothing blocks on — not a human decision. Source defect mc-iqjzi (P3, OPEN) carries the same wrong premise and should be corrected, not fixed.
Surviving option: none needed; at most a prose tidy (A) as coordinator bookkeeping.

### mc-f23sb — UNDETERMINED
Question/options: `$GC_WORK_DIR` in brief-pipeline formula prose: A change prose to an existing variable, B export GC_WORK_DIR in agent sessions (gascity), C sanction the `${GC_WORK_DIR:-$GC_DIR}` fallback.
Premise probes:
- `grep -rln GC_WORK_DIR ~/repos/mathcity/formulas` (HEAD b792059, 2026-09-25) → 7 files now, up from the brief's 4 (adds brief-briefed-base, report-fix-briefed, commission-work-briefed) [measured]; all bare `$GC_WORK_DIR`, no fallback form [measured]
- `grep -n GC_WORK_DIR ~/repos/gascity/internal/convergence/condition.go` → line 159 exports it only in the convergence-condition env [measured]
- `bd show mc-qwqmr` → OPEN [measured]
Grounds: premise live and wider than stated. No Adopted rule picks the fix layer. Scope correction for whoever adjudicates: 7 formulas, not 4.
Surviving option: none determined.

### mc-yre1s — UNDETERMINED (premise partly stale)
Question/options: layer to repair the four brief-pipeline vapor terminal-contract defects (mc-gqtlh): A mathcity formula TOMLs only, B gascity dispatch contract, C split (B for D2/D3, A for D1/D4), D report-only now.
Premise probes:
- `bd show mc-gqtlh` → OPEN [measured]; `bd -C ~/gt/hecke show he-cc1vqe` → OPEN [measured]
- D1 (literal tilde): `grep -n HOME ~/repos/mathcity/formulas/brief-archive-sweep.toml` → line 35 `ROOT="${ROOT/#\\~/$HOME}"`, landed in `4498824 2026-09-07 "fix brief-archive-sweep tilde"` [measured]; `brief-decision-dispatch.toml:554` has the same expansion [measured]. **D1 is fixed at the formula layer** (i.e. option A was executed for D1).
- D2 (GC_BEAD_ID): archive-sweep line 36 still `WORK_BEAD="${GC_BEAD_ID:-}"`, line 123 closes only if set [measured] — still dependent on an export the brief says never arrives (export not re-measured → [inferred] still live)
- D4 (0/0 reporting): line 120 still prints `archived=$archived skipped=$skipped` with no `unknown` path [measured]
Grounds: the D1 half is done; D2/D3/D4 and the layer choice for D2/D3 remain. No Adopted rule chooses the layer. P6.2 (`subdomains/dev/POLICY.md:546`, "**P6.2 "A check must be able to fail."**") requires D4 be fixed in any option, so it kills nothing among A/B/C except weakly D's "defer" of the rest — not enough to leave one option.
Surviving option: none determined; tell the adjudicator D1 is already done and C collapses to "B for D2/D3 + A for D4".

### mc-izq9q — MOOT
Question/options: magma_diff_alg: A add a gc.run-operator pool AND a zero-slot dispatch guard, B pool only, C guard only (rig deliberately pool-less), (+ both halves).
Premise probes:
- `grep -n -A3 magma_diff_alg ~/gt/city.toml` → lines 189-193 `[[patches.agent]] dir = "magma_diff_alg" name = "gc.run-operator" max_active_sessions = 12 min_active_sessions = 2` [measured] (file mtime Sep 25). The brief said only hecke and gascity-packs had one.
- `sed -n 100,128p ~/repos/mathcity/assets/scripts/mctl_core/formula_dispatch.py` → refusal `UNROUTABLE_TARGET`: "has no configured sessions in this city, so a dispatch to it would attach and then wait for a worker that cannot exist"; unreadable roster also refuses [measured]
- `git log -- …/formula_dispatch.py` → `b792059 2026-09-25 "Refuse a dispatch to an agent with no configured sessions (mc-6hv87)"`; `git branch -r --contains b792059` → origin/main [measured]
- `bd -C ~/gt/magma_diff_alg list --status in_progress` → mda-2tm, mda-6ha, mda-jkj still IN_PROGRESS [measured]; no step closed after 2026-09-15 [measured]. Live run-operator sessions for the rig: not measured → unknown.
Grounds: both halves of option A are on disk (pool config and guard, the guard on origin/main). The decision was executed. Residual is bookkeeping: confirm the pool actually spawns and the three inert molecules move, and close mc-6hv87 (still OPEN P0). Whether the city.toml line came through the pack pipeline (the brief's `why_taylor`) was not audited.
Surviving option: A, already done.

### mc-1wls8 — UNDETERMINED (premise partly stale)
Question/options: WI-004 remainder (dashboard `/orders` reads through the slow `gc order list` subprocess, not the bounded reader): A re-dispatch narrowed, B descope, C carry to a follow-up build.
Premise probes:
- `bd show mc-0mhh` → CLOSED, reason "workflow cleanup: subtree bead force-closed via skip directive" [measured] — closed by cleanup, not by a fix
- `sed -n 765,780p ~/repos/mathcity/assets/scripts/mctl_dashboard/app.py` → `_default_orders_reader` still returns `orders.city_reader`, docstring "shells out to `gc order list`/`history` (slow -- ~33-89s measured)" [measured]; last app.py commit 6253e8c 2026-08-29 [measured]
- `bd show mc-vzx0` → CLOSED [measured]
Grounds: the remainder is still unbuilt. The anchor bead is now closed, so "re-dispatch mc-0mhh" (A as worded) would need a new bead. Scope/descoping is a product call; no Adopted rule reaches it.
Surviving option: none determined.

### mc-lw18s — UNDETERMINED (narrowed: C eliminated)
Question/options: encode decomposition cross-WI ordering as bd dependencies between drain units: A decomposition producer writes edges, B drain creation derives edges, C status quo + mandatory worker-side sibling probe.
Premise probes:
- `bd show mc-tv4sz` → OPEN [measured]. The settling probe the brief names (do edges exist and the scheduler ignores them?) was not run by me or by the brief → unknown.
Grounds: CT3.1 (`subdomains/dev/POLICY-city.md:258`, Adopted doc, entry not PROPOSED, not JUDGEMENT): "**CT3.1 Work is automatically structured as PERT.** Accepted work is decomposed into a dependency DAG — tasks with explicit predecessor edges (bd dependencies) … Fail: a multi-step job executed as one opaque blob, or dependencies discovered mid-flight that decomposition should have surfaced → **revise**." Option C leaves the ordering as prose that each worker finds mid-flight, so **CT3.1 kills C**. A and B both produce bd edges and both survive. (CT3.3, the critical path driving scheduling, is PROPOSED → discarded.)
Surviving options: A or B. Human or design decision still owed; Taylor should not be offered C.

### mc-xz8ea — UNDETERMINED
Question/options: (a) Phase 1 of the idle-controller build after the Phase 0 gate returned `unknown`: A re-run the gate by the gc-hook-empty route, B authorize Phase 1 as branch-independent, C ship report-only and drop the gate, D hold the whole build; (b) how a gate signals "not cleared" to the graph (mc-d8qkx), with no enumerated options.
Premise probes:
- `bd show mc-pvmam` → OPEN [measured] (Phase 1 still pending, so still dispatchable; not re-measured whether held)
- `bd show mc-cutri` → CLOSED [measured]; `bd show mc-d8qkx` → OPEN [measured]
Grounds: premise live. (a) is a risk trade-off: B needs a human to take an assumption, and C discards a branch. No Adopted rule picks among A–D. P6.2 (`subdomains/dev/POLICY.md:546`) bears on (b): a gate that could not run must not render as pass. But (b) has no closed option set, so nothing can be derived there.
Surviving option: none determined. The live risk stands as the brief says: mc-pvmam stays dispatchable.

| Outcome | Count | IDs |
|---|---|---|
| MOOT | 2 | mc-7xn6p, mc-izq9q |
| DUPLICATE | 1 | mc-897zw (→ mc-9cr72; its (a) half also moot) |
| UNDETERMINED | 6 | mc-9cr72, mc-f23sb, mc-yre1s*, mc-1wls8*, mc-lw18s (C killed by CT3.1), mc-xz8ea |
| DERIVED / DERIVED-OUT / CONFLICT / REFUSED | 0 | — |

*premise partly stale

<!-- sub-pass D -->
# mc2 — part D (9 briefs) — derivation record, NOT recorded verdicts

Read-only pass, 2026-09-26/27Z. Bodies read from `bd -C ~/gt/mathcity show <id>` dumps.
Adopted-doc status re-checked live (7 Adopted, as listed in the task). Rules consulted in
`subdomains/dev/POLICY.md` (P1.7, P6.1, P6.2) carry no `(PROPOSED)` and no `JUDGEMENT RULE`
marker [measured: `grep -nE '^\- \*\*P6\.[12][^*]*PROPOSED|^\- \*\*P1\.7[^*]*PROPOSED'` → 0 hits;
`grep -n 'JUDGEMENT RULE' subdomains/dev/POLICY.md` → 0 hits].

Process note: one `git fetch -q` was run in `~/repos/mathcity` early in the pass (updates
remote-tracking refs only; no commit/add/push/rebase). Not repeated. Flagged for honesty under LP1.

---

### mc-8t7of — UNDETERMINED
Question/options: how to repair mathdb-fetch.py's lossy intake — A rewire onto mathdb-mcp SSR parser + add `/search` robots prefix; B robots line only; C defer to the adopt-connector adjudication.
Premise probes:
`bd show mc-wxkmc` → OPEN (P1) [measured]
`git show origin/main:assets/scripts/mathdb-fetch.py | grep -n DISALLOWED_PREFIXES` → line 84 `("/new", "/bookmarks", "/moderation")` — `/search` still absent [measured]
same file `grep -n JSONLD` → still parses `application/ld+json` (lines 37, 87–88, 202) [measured]
`git log origin/main -- '*mathdb*'` → last touch 016c8e2 (CA resolution), no SSR rewire [measured]
Grounds: premise live; nothing landed. No Adopted rule reaches parser choice or the dependency on the pending mathdb-mcp adoption. (Note [inferred]: the `/search` robots fix is common to A and B, so only C leaves the robots violation in place — but no Adopted rule on robots compliance was found to kill C.)
Surviving option: A, B, C all stand.

### mc-biyv7 — UNDETERMINED
Question/options: should an unresolvable `git:` pin become a mechanical failure — A accept one-off; B fail closed at consumer `do-work.close-source-anchor`; C gate at producer (inert until mc-56tn8); D both.
Premise probes:
`bd show mc-56tn8` → OPEN (P1) — producer-side validator still cannot run [measured]
`grep -c cat-file` on all 4 cached `gascity/formulas/do-work.formula.toml` + `~/repos/gascity-packs/gascity/formulas/do-work.formula.toml` → 0 in every copy (no pin-resolution check has landed) [measured]
Grounds: premise live. P6.2 (`subdomains/dev/POLICY.md:547`, "must be **falsifiable against the condition it claims to detect**: there must") narrows but does not decide: a C gate installed while mc-56tn8 is open could not produce the "observed failing run" P6.2's pass criterion requires — that is a reading, not a mechanical kill, and it leaves A/B/D. P1.7 (`:94`, "e.g. rewriting upstream-owned files in the fork — → **fail**") may bear on B because `do-work.formula.toml` lives in the upstream-owned `gascity/` subtree of gascity-packs [measured location], but B could be implemented by overlay/override; which applies is contested → not cited as a kill. Whether the pin is load-bearing (brief §3.1) is a design judgement.
Surviving option: A, B, D (C weakened, not eliminated).

### mc-nxpgd — UNDETERMINED
Question/options: pool-worker comms gap — A/B repair channel variants, C document the limit, D both (recommended).
Premise probes:
`git show origin/main:skills/communicate-with-other-agent/SKILL.md | grep -niE 'pool|unreach'` → only line 47 (non-Claude harnesses unreachable); no pool-session limit documented [measured]
`git log -3 origin/main -- skills/communicate-with-other-agent/SKILL.md` → 4ddafad / 998b4bc / d3df044, none about pools [measured]
Grounds: premise live; neither the doc fix nor a channel repair has landed. The brief's own §3.1 states the load-bearing unknown ("whether pool sessions are *supposed* to be reachable ... nobody I asked knew") — a genuine design decision. P6.1 (`:520`, "Catching an error and continuing in a degraded, partial, or") concerns change artifacts failing silently; applying it to choose between doc-only and repair would require interpretation → not cited.
Surviving option: all stand.

### mc-pf7dd — UNDETERMINED (premise half-dead: redaction half MOOT)
Question/options: (1) authorize redacting 16 home-path leaks in comments on gastownhall/gascity + tdupu/gascity; (2) authorize sweeping the 4 unmeasured surfaces.
Premise probes:
`bd comments mc-pzqoj` → clark 2 (2026-08-29 01:46) measured all 16 authored by `tdupu` [measured, their probe]
`gh api repos/gastownhall/gascity/issues/comments/<id>` for all 14 ids, and `repos/tdupu/gascity/...` for both ids → every one: author `tdupu`, `test("tdupuy";"i")` = **false**, `test("<home>|<city-root>|<repos-root>")` = **true**, body length 677–4448, `updated_at` 2026-08-29T01:47:06–01:47:30Z [measured]
Control: `echo '/Users/tdupuy/x' | jq -R 'test("tdupuy";"i")'` → true (probe can detect the string) [measured]
`gh search prs --repo gastownhall/gascity tdupuy` → 1 hit, PR #5346 (author tdupu, open); issues 0; tdupu/gascity PRs 0 / issues 0; control query returned 5 [measured]
Grounds: Half (1) is **MOOT** — all 16 comments were edited to the standing placeholders one minute after the bead's last comment [measured]. Half (2) is live: at least one residual on the PR surface (#5346) and the other surfaces (review comments, file contents, release/wiki) remain unswept [measured floor; search tokenization makes this a floor, not a total — inferred]. Authorizing an outward-facing public edit by Taylor's account is not reached by any Adopted rule.
Surviving option: only the sweep question remains, for Taylor. Brief should be re-scoped or re-filed to the sweep alone.

### mc-t2wce — UNDETERMINED (premise half-dead: S67 half MOOT)
Question/options: A document only (`gc suspend` as night-stop, warn on `gc stop`); B run read-only probe to settle S67, then document; C change `gc stop` upstream; D accept as-is.
Premise probes:
`bd comments mc-iiur4` → 2026-09-08 03:38 author RETRACTION: probe run, S67 attribution REFUTED [measured, their probe]
Re-verified: `gzcat ~/.gc/supervisor.log.archive-20260927T030746Z.gz | grep -n 'Unregistered city'` → lines 12748 and ~74196 only, preceded by 2026/08/26 13:25 and 2026/08/27 21:22 timestamps; 66,765 lines dated 2026/09/07 present, none unregistering [measured]
`git show origin/main:docs/CITY-RESTART-CHECKLIST.md` → line 71 still instructs a bare `gc stop` with no unregister/Dolt warning; `MAYOR-ONBOARDING.md` has no hit for gc stop/suspend [measured]
Grounds: B's probe half is **MOOT** (already run, negative, re-verified). B therefore collapses into A. The live question is A vs C vs D (document, change upstream, or accept). Whether `gc stop`'s teardown is a trap or a contract is the brief's own §6 "gascity-core judgement". No Adopted rule decides it; P5.4 does not reach — the checklist makes no false behavioural claim about `gc stop`, it just omits side effects [inferred reading].
Surviving option: A, C, D.

### mc-t92ce — UNDETERMINED
Question/options: slow dispatch after killing the JSON_EXTRACT hypothesis — A instrument gc itself; B fix the reaper and re-measure; C accept slow dispatch; D keep investigating with current tools.
Premise probes:
`bd -C ~/gt show gt-us8ayq` → OPEN [measured]
Grounds: an investment-allocation judgement on an n=1 measurement (brief §3), 28 days old. No Adopted rule allocates investigation effort. Option B overlaps the reaper briefs mc-0nyo5 / mc-b87er (other fork) but asks a different question — not a DUPLICATE.
Surviving option: all stand.

### mc-u8kl7 — UNDETERMINED
Question/options: formula-health view — A bounded read-only spike to find the run-outcome signal first; B build directly on orders/molecules; C defer behind a new run-outcome record.
Premise probes:
`bd show mc-ksnw3` → OPEN (P1) [measured]
`git show origin/main:assets/scripts/mctl_dashboard/app.py | grep -ni formula` → only the `/orders` "Orders & Formulas" page (lines 782–799); no `/formulas` route or health view [measured]
Grounds: premise live. Where the health signal comes from is a design choice (brief §2), and no Adopted rule decides it. It is not pure sequencing (C changes scope), so it is not DERIVED-OUT.
Surviving option: all stand.

### mc-vmcc5 — REFUSED_STOP_GATE (premises partly stale)
Question/options: hq off-box durability — A establish backup state, then unblock compaction; B Git LFS; C shard hq.jsonl; D stop exporting hq.
Premise probes:
`gc dolt health --json` (read-only) → `quarantine` hq `post-flatten table value hash changed…` age 6,549,819 s (~75.8 days): compaction still blocked [measured]; `backups.dolt_databases` hq age 53,778 s (~14h56m), `stale: true` — the brief's "Backups: none found" premise is **stale** (health now reports an hq backup ~15h old) [measured]; whether that backup is off-box is not established [inferred unknown]
`du -sh ~/gt/.beads` → 26G (brief: 24 GB) [measured]
mc-0nyo5 comment (other fork's brief) claims the JSONL leg was changed by commit b50c274 (hq.jsonl → hq.jsonl.gz, 11.0 MiB) on 2026-08-27T01:55Z — **not verified** here; `gh api repos/tdupu/jsonl-archive/contents` shows an uncompressed `hq.jsonl` 1,617,992 bytes, last default-branch commit 2026-07-05, so that repo is likely not the live archive target [measured / inferred]
`bd show mc-9rno7` → OPEN [measured]
Grounds: derive-verdict step 0 — the question touches a stop-gated surface: option A requires Dolt compaction, and the brief itself flags "G5 Server-touching: … FLAGGED for execution". A derivation is not a route around that gate. Separately, the 101 MB-export premise should be re-measured before presentation.
Surviving option: n/a (refused). Route to Taylor with the stale-premise note.

### mc-xf2d5 — UNDETERMINED (premise partly stale)
Question/options: scopeless wisp gt-kbxweq — cancel, re-stamp with a rig, or define a default rig.
Premise probes:
`bd -C ~/gt show gt-kbxweq --json` → status open, assignee none, updated_at 2026-08-28T15:39:42Z, `gc.claimed_at` 2026-08-28T14:12Z [measured]. The "re-claimed and re-diagnosed indefinitely" premise is **stale**: no claim or update in 29 days.
`bd -C ~/gt show gt-d16kg3` → OPEN [measured]
Duplicate scan: `grep -l kbxweq mc2/*.txt` → only mc-xf2d5 [measured]; mc-3gj9n (brief-shuffle drain defects, other fork) does not cite this wisp.
Grounds: no Adopted rule selects cancel, re-stamp, or default rig. The churn cost that made this urgent has stopped [measured]. A cancel would be low-stakes. "Define a default rig" is a design change.
Surviving option: all three stand.

---

## Tally (part D)

| Outcome | Count | Ids |
|---|---|---|
| MOOT | 0 (2 half-moot) | half: mc-pf7dd (redaction done), mc-t2wce (S67 probe done) |
| DERIVED | 0 | — |
| DERIVED-OUT | 0 | — |
| DUPLICATE | 0 | — |
| CONFLICT | 0 | — |
| REFUSED_STOP_GATE | 1 | mc-vmcc5 |
| UNDETERMINED | 8 | mc-8t7of, mc-biyv7, mc-nxpgd, mc-pf7dd, mc-t2wce, mc-t92ce, mc-u8kl7, mc-xf2d5 |


## Tally (38)

| Outcome | Count | IDs |
|---|---|---|
| MOOT | 5 | mc-370v3, mc-7xn6p, mc-izq9q, mc-anjnx, mc-dbhgm |
| DERIVED | 1 | mc-snxym (B2.16) |
| DERIVED-OUT (standing instruction) | 1 | mc-31b8c |
| DUPLICATE | 2 | mc-897zw (keep mc-9cr72), mc-uwyhb (keep mc-7fwku) |
| REFUSED_JUDGEMENT | 1 | mc-kqmj1 (P7.1 exemption clause is judgement-kind) |
| REFUSED_STOP_GATE | 2 | mc-1h6r4 (user-skill-touching), mc-vmcc5 (server-touching) |
| CONFLICT | 0 | — |
| UNDETERMINED | 26 | the rest. Partly stale: mc-3gj9n, mc-n3bih, mc-yre1s, mc-1wls8, mc-whfov, mc-7fwku (item 3), mc-k6tmt, mc-pf7dd (redaction half moot), mc-t2wce (S67 half moot), mc-xf2d5. Narrowed by policy: mc-lw18s (CT3.1 kills C), mc-zp1fs (B2.16 kills D). |

Clusters to present together, though not formal duplicates:
- **Drain-ack:** mc-ogwa8 (the survivor), mc-whfov, mc-qi4o3.
- **Reaper:** mc-0nyo5, mc-b87er, with mc-t92ce related.
- **Claim identity:** mc-7fwku, mc-cns3c.
- **Pile rejection:** mc-3gj9n (defect-2 half), mc-zp1fs.
