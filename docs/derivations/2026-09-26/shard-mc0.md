# Derivation pass — shard mc0 (37 mathcity briefs), 2026-09-26

**Derivation record only. Nothing was written to any bead, brief, cache or ref.** ADR 0006 is Proposed, not Adopted.
Method: premise-testing per `mathcity/skills/derive-verdict/SKILL.md`. Brief bodies were read with `bd -C ~/gt/mathcity show <id>` (read-only). Source was read at `~/repos/mathcity` `origin/main` = `7de4478` (2026-09-25) and `~/repos/gascity`; bead state came from `bd show --json`.
Corpus status, re-measured with `grep -m1 '^| Status |'`: all 7 of the expected docs are Adopted (POLICY-POLICY, POLICY-beads, POLICY-formulas, brief-system/POLICY, dev/POLICY, dev/POLICY-city, dev/POLICY-documentation).
Referenced-bead census: 319 `mc-` ids (148 closed, 166 open, 5 blocked) and 100 `gt-`/`gsp-`/`he-` ids, each queried one by one.

---

### mc-0xqwi — UNDETERMINED
Question/options: should the defect-bead minting surface refuse to leave a bead unrouted? {A guard at the surface, B orphan sweep, C a separate handoff-bead verb, D accept the gap and correct the doc}
Premise probes: `bd show mc-17a98` → OPEN (the 28%-orphan defect). `git log origin/main --since=2026-09-17 | grep -iE 'defect|orphan|route'` → no hits [measured]. The premise is live.
Grounds: this is a design choice. No Adopted rule picks the mechanism.

### mc-1hni3 — UNDETERMINED
Question/options: bead_hold/bead_release are broken. {A fix only the verb's argv order, B also fix hold:* exclusion from work_query}
Premise probes: `git show origin/main:assets/scripts/mctl_core/beads.py | grep '"bd", "label"'` → line 511 still has `["bd", "label", change.action, change.label, change.bead_id]` (transposed) [measured]. `bd show mc-3n9vy mc-hs3 mc-esew` → all OPEN [measured].
Grounds: both premises are live. The choice is about scope. No rule reaches it.

### mc-2bih3 — UNDETERMINED
Question/options: prepare-worktree creates worktrees detached. {A name the branch at creation (an upstream PR), B protect at close-source-anchor, C salvage sweep}
Premise probes: `grep -- '--detach' ~/repos/gascity/.../mol-polecat-commit.toml:73, mol-scoped-work.toml:102` → both still say `git worktree add ... --detach origin/{{base_branch}}` [measured]. `mc-b0gx8` → OPEN.
Grounds: the premise is live. A vs B is a real trade: the correct fix sits upstream, the workaround sits in our lane. P3.1 only sets how A would be routed (PR-only). It does not choose A.

### mc-31rml — UNDETERMINED
Question/options: how should tracker hygiene reach template conformance? {A restatement with stamped gaps, B redefine hygiene, C bounce to the author, D hybrid}
Premise probes: `git grep 'not stated in the original' origin/main -- assets` → no hits, so A is not implemented [measured]. `mc-cows4` → closed (superseded, as the brief says).
Grounds: this is a design choice. It also involves writes to a public GitHub repo.

### mc-37mgc — UNDETERMINED
Question/options: how should create_issue_bead resolve a repo to a rig? {A via the rig's configured remote, B name normalisation, C rename rigs, D a hand map}
Premise probes: `effects.py:817-835 @origin/main` → MISS005 still compares `rig_for_issue(issue_url)` against `ctx.rig_id` [measured]. `mc-dedra` → OPEN, P0. No fix commit since 2026-09-22 [measured].
Grounds: the premise is live. The design choice is open.

### mc-42szv — UNDETERMINED
Question/options: the live beadless-brief repair (77 irreversible mints into hq). {A halt and wire the gates, B fresh backup then run, C run now, D abandon}
Premise probes: `bd show mc-db424` → OPEN ("executor calls neither mandated pre-write gate"). `bd show mc-nquaf` → OPEN, P0 (hq has no off-box backup). `mc-wgy09` (Unit 2, live execution) → OPEN [measured]. The gate commits 680dfdb and cc900bc are on no ref in `~/gt/mathcity` (`git branch -a --contains` → empty) [measured].
Grounds: both blockers are live. Irreversible writes plus a backup policy make this a human call.

### mc-4ysop — UNDETERMINED
Question/options: brief_quality_failure.v1 has no no-gate sentinel. {A add a sentinel, B split profile errors into their own record shape, C force a real gate id}
Premise probes: `brief-check.sh:226 @origin/main` → `failed_gate` is still a required key. `git grep 'no.gate|G0' gates.toml brief-check.sh` → no hits [measured].
Grounds: the premise is live. This is a contract-design choice.

### mc-7iiuj — UNDETERMINED (premise partly stale)
Question/options: which decision-record root is canonical, and what happens to the 11 stranded records? {A repoint both straggler formulas to .beads/briefs plus a guard and hand-triage, B finish W2 to the global root, C repoint only, D defer}
Premise probes:
- `git log -- formulas/brief-decision-dispatch.toml` → `c9a86eb 2026-08-29 fix(formulas): point brief.decided consumers at the aggregated root`. The default is now `~/.gc/mathcity/aggregated-briefs`, not the `~/.gc/mathcity/briefs` the brief describes [measured].
- `wc -l ~/.gc/mathcity/aggregated-briefs/decisions-dispatched.jsonl` → 58 lines; the last dispatch was 2026-09-16 [measured].
- `ls ~/gt/.beads/briefs/decisions | wc -l` → 45 (the writer's root, formerly 11), with still no ledger there. `aggregated-briefs/decisions` → 2 records [measured].
- `bd show gt-5yxup1` → OPEN, titled "fix blocked on root-choice decision" [measured].
Grounds: the literal "dead root" has been repointed, but the writer/consumer split survives (45 records the dispatcher does not read). The root choice is still open. Coupled with mc-a7chj and mc-thwni (same root decision); they should be decided as one cohort.

### mc-7zybv — UNDETERMINED (option C partly measured here)
Question/options: cross-rig adjudication from a pinned briefs dashboard. {A build it, B leave the boundary, C measure first}
Premise probes: `app.py:486-498 @origin/main` → `_rig_for` returns the pinned rig when not city_wide. `app.py:1168-1173` → "the adjudication panel rendered below emits the viewed rig as its explicit `name="rig"` field" [measured]. So controls do render on a switched view, and the write routes to the pinned rig. Whether that write mis-attributes or fails closed was not exercised [inferred].
Grounds: C is now half done. A vs B remains a product choice.

### mc-8crp4 — UNDETERMINED
Question/options: publish the queue_status city-wide build, or hold it? {approve/publish, hold}
Premise probes: `git -C ~/gt/mathcity rev-parse work/mc-413q-consolidated` → 35001f8. `git -C ~/repos/mathcity cat-file -t 35001f8` → not present, so it has not landed on main [measured].
Grounds: this is a genuine approve/hold verdict on shippable work.

### mc-91uqp — UNDETERMINED (audit fact added)
Question/options: work_dispatch appears in both ALLOWED_TOOLS and DELIBERATELY_UNREACHABLE. {A revoke, B grant, C audit first}
Premise probes:
- `client.py:87 @origin/main` → `work_dispatch` is in ALLOWED_TOOLS.
- `tests/mctl/test_dashboard_tool_reachability.py:~63` → `"work_dispatch": "mutating dispatch is not driven from the dashboard"`. The double-listing is live [measured].
- For C: `app.py:194` → `"dispatch": Operation("dispatch", "work_dispatch", ...)`, and `app.py:1452` mentions the work_dispatch dry-run rung. So a dashboard path does call it [measured].
Grounds: the C audit is partly answered (the dashboard does wire it). A vs B is a safety/product choice.

### mc-a7chj — UNDETERMINED (premise partly stale)
Question/options: brief-archive-sweep's root. {A repoint and re-key the decisions branch, B repoint only, C make the aggregate real, D defer}
Premise probes: `brief-archive-sweep.toml:17-19` → default is still `~/.gc/mathcity/aggregated-briefs`. `ls -a aggregated-briefs` → no `.pile/`, `.staging/` or `stack/`. The `decisions-dispatched.jsonl` the brief called ABSENT now exists (58 lines) [measured]. `ls ~/gt/mathcity/.beads/briefs/.pile/.rejected | wc -l` → 67 (was 24), still unseen by the sweep [measured].
Grounds: the root mismatch is live. Same root decision as mc-7iiuj and mc-thwni; decide them together.

### mc-aoasm — DERIVED-OUT (standing instruction; option A measurably dead)
Question/options: dispatchers were absent after `gc resume` (2026-09-09). {A 45-minute wait-out probe, B controlled repeat, C escalate to BART, D session reset}
Premise probes: `gc session list | grep dispatch` → 14 control-dispatcher sessions (13 asleep, 1 start-pending). `bd -C ~/gt show gt-jl3xas` → mathcity dispatcher created 2026-09-10T17:00Z. The brief's resume was around 2026-09-09T01:23Z [measured]. The live post-resume state that A and D were meant to preserve or probe no longer exists.
Grounds: what remains is a choice of diagnostic procedure and whether to route to BART. That is sequencing and routing. Standing instruction, `~/gt/CLAUDE.md:360`: "**Staffing, routing, and sequencing are NOT his.** Who does what, who reviews…". No policy rule is cited.
Surviving option: coordinator's call (B, the controlled repeat, is the only probe still runnable).

### mc-bitc0 — UNDETERMINED
Question/options: a typed work-bead creator for the MCP. {A one create_work_bead with issue_type plus an edge verb, B separate verbs, C a compound graph tool, D hold}
Premise probes: `git grep 'name="create_' origin/main` → only create_issue_bead, create_github_issue and create_defect_bead [measured]. The premise is live.
Grounds: this is API design.

### mc-bzsv6 — UNDETERMINED
Question/options: rollup closure key. {A key on the triple, B filter the fingerprint search, C coarsen grouping, D accept the drops}
Premise probes: `formulas/brief-producer-failure-rollup.toml:44-60 @origin/main` → groups by the triple, and `group_repair_status() # $1 = failure_fingerprint`. Last commit was 2026-08-27 [measured]. The premise is live.
Grounds: this is a design choice. B2.8 (bead state is not derived from a file) is satisfied by every option.

### mc-cwz0w — UNDETERMINED (premise partly stale)
Question/options: disposition of the work_claim→work_claim_state rename campaign. {A integrate the 6 commits, B re-dispatch, C park and reopen the beads}
Premise probes:
- `git -C ~/gt/mathcity for-each-ref --contains <c>` for 5b6212c, c66d035, 189596a, ff83ba7, e88ac53, 53fea4b, 3ce5548 and 79933d2 → every one is now reachable from `salvage/*` refs [measured]. "Zero branches contain any of them" is stale; the loss risk is gone.
- `origin/main:mcp_server.py:4627` → `name="work_claim"`, so the rename is not on main [measured].
Grounds: the urgency premise is dead but the A/B/C disposition is still owed. Coupled with mc-o11rc.

### mc-dm4k0 — UNDETERMINED
Question/options: the backfill wrapper drops `--dry-run`. {A forward "$@", B fence with an error, C leave as-is}
Premise probes: `git show origin/main:assets/scripts/checks/brief-quality-failure-record-backfill.sh` → the exec line has no `"$@"` [measured].
Grounds: I considered P6.1 (`subdomains/dev/POLICY.md:516`, which is about error/timeout paths) and CT13.4 (`POLICY-city.md:716`, about typed MCP tool refusals). Neither reaches a shell wrapper dropping arguments without interpretation, so no elimination is claimed. The brief's own §6 notes 15 of 34 wrappers share the defect, which bears on P1.17 (root cause vs instance).

### mc-f6a2e — MOOT
Question/options: commission mc-mivv's file-brief step would overwrite an adjudicated brief. {A repoint the step at a fresh slug, B dispatch on the existing approve, C re-adjudicate}
Premise probes: `bd show mc-keaw --json` → closed 2026-08-29T06:12:11Z: "Filed … at .beads/briefs/.pile/mc-mivv-commission.md … Filed under the distinct slug mc-mivv-commission … .pile/mc-66dw.md verified untouched" [measured]. The brief was created at 05:04:55Z, 67 minutes earlier. `ls -la .pile/mc-mivv-commission.md` → exists, 40,919 bytes, header `brief_slug: mc-mivv-commission` [measured].
Grounds: option A was executed after the brief was filed, and the collision premise is dead. Whether to dispatch mc-mivv (still OPEN) belongs to the mc-mivv-commission brief, not this one. The class fix is mc-mg1n4.

### mc-ji6mp — UNDETERMINED
Question/options: scan-rejected ignores `feedback_required`. {A honour feedback_required:false, B skip "blocked", C move to its own lane, D exclude by hand}
Premise probes: `git show origin/main:formulas/brief-producer-failure-record.toml | grep feedback_required` → no hits; last commit 2026-08-19 [measured]. The premise is live.
Grounds: this is a design choice.

### mc-kevm0 — MOOT (partial)
Question/options: four briefs refused on form. {A fix the matcher for numbered headings, B edit the bodies, C rewrite §1 of the two content violators, D leave all stranded}
Premise probes: `git log -- assets/brief-pipeline/required-sections.toml` → `31c8ac2 2026-08-29 Match a numbered Gate Evidence heading (mc-ntxi0)`, committed 2026-08-29T02:03Z. The brief was created at 01:09Z. The live regex is `'^##*[[:space:]]+([^A-Za-z]*[[:space:]])?Gate Evidence\b|…'` [measured].
Grounds: option A (the checker half, two briefs) has landed on main. What remains is C vs D for the two briefs whose §1 carries evidence, now also subject to the full-form create gate (`5cd7f1e`, 2026-09-09). That small residue is a genuine decision. The rest is moot. Note: mc-ntxi0 is still OPEN although its fix is on main.

### mc-kum3m — UNDETERMINED (premise inconsistency found, not reconciled)
Question/options: producer formulas inherit a gate profile they cannot satisfy. {A dispatch a real critical-review, B use the decision profile, C a new upstream_draft profile, D drafting-only; plus E from the comments}
Premise probes: `mc-uvg` → OPEN, P1. But `origin/main:formulas/pr-pipeline-briefed.formula.toml:293` and `brief-briefed-base.formula.toml:157` both already require `gate_profile: decision` frontmatter, added in `477de61 2026-08-16` [measured]. `33207a2` (2026-08-29) declares gate_profile on briefs_create pile documents [measured].
Grounds: the brief's own derivation leaves A and C standing, and it eliminates B and D using decision beads (gt-m50xwa) and a standing rule, not Adopted policy text. This skill may not derive from those. The measured frontmatter suggests the "inherits standard" premise may be partly stale. Whoever presents this should reconcile it first.

### mc-mg1n4 — UNDETERMINED
Question/options: commission slug rule. {A fix the derivation at dispatch, B existence guard only, C `<source>-commission` as the standing slug, D park and dispatch on approvals}
Premise probes: of the 7 roots, `mc-4nt1` is closed and mc-8ply, mc-anrg, mc-d0b5, mc-gfkr, mc-qvy4 and mc-xu4n are OPEN [measured]. The only commission-work-briefed commit since is `dda1868` (§1-§7 naming) [measured]. The premise is live for 6 of 7.
Grounds: this is a design choice.

### mc-nhz1n — REFUSED_CONTESTED
Question/options: B1.9(c) "§2 names a recommendation" vs #194 "decisions_to_briefs deposits UNDECIDED". Which moves?
Premise probes: `subdomains/brief-system/POLICY.md` (Adopted). B1.9 is not marked PROPOSED [measured].
Grounds: the governing rule's own text declares its reading unsettled. `subdomains/brief-system/POLICY.md:195-197`: "decision UNDECIDED and forbids inventing a recommendation — are both adopted" / "and cannot both hold. Measured: making (c) fatal turns 9 tests red, four of" / "which assert #194 directly. Which rule moves is an open adjudication on". Skill constraint 2 applies: a contested rule is adjudicated before it is derived from. PP6.1(a) has no precedence clause (B1.9 names the tie itself). PP6.1(b) fails too: #194 has no Adopted rule text of its own (`grep -F '#194'` over the policy corpus → only these B1.9 lines), and "which rule moves" is a policy-amendment question.
Surviving option: none by derivation. It goes to Taylor as a refusal.

### mc-o11rc — UNDETERMINED (premise partly stale)
Question/options: work_claim_state compatibility posture. {A revise mc-ikxz to a hard rename, B alias per the recorded verdict, C a third posture, D defer}
Premise probes: `origin/main:assets/scripts/mctl_core/mcp_server.py:4627` → `name="work_claim"` (not renamed). The same holds on `~/gt/mathcity` origin/main. The live MCP roster exposes `work_claim` [measured]. So "Option A shipped" is false for main: it exists only on the stranded (now salvage-anchored) commits of mc-cwz0w.
Grounds: the "unshipping working code" cost argument for A is dead. The posture choice survives and should be decided together with mc-cwz0w.

### mc-p21l9 — UNDETERMINED (survivor of a DUPLICATE pair with mc-xlcqm)
Question/options: worker identity namespace. {A verify against GC_SESSION_ID plus bound the loop, B BEADS_ACTOR=session id, C bd accepts either, D bound only}
Premise probes: `gascity/cmd/gc/cmd_hook.go:859-860` → `firstNonEmptyHookValue(alias, sessionID, …, sessionName)`, which prefers the session ID. The claim block in `.gc/cache/.../design-author/prompt.template.md:34` is `EXPECTED_ASSIGNEE="${BEADS_ACTOR:-${GC_SESSION_NAME:-${GC_SESSION_ID:-…}}}"`, which prefers the name. The inversion is live [measured].
Grounds: this is a design choice.

### mc-pmrjc — MOOT
Question/options: repair order. {A protect the commits first, B repair the brief.decided consumers first, C hand-apply the 6 verdicts, D diagnose}
Premise probes:
- The mc-rd086 commits 31992c0, a5799e8, b381ac1, bee885e, eade457, fb7393a and ff081cf → each is now contained by a `salvage/*` or `work/*` ref (`git for-each-ref --contains`) [measured]. The clock premise is dead.
- `aggregated-briefs/decisions-dispatched.jsonl` → dispatches at 2026-09-11T07:04Z and 2026-09-16T16:43Z [measured]. "Neither consumer has fired since" is stale.
Grounds: both facts that set the two repairs against each other are gone. What remains is ordinary repair work (mc-6hgcm OPEN) and its order, which is the coordinator's per `~/gt/CLAUDE.md:360`.

### mc-qn40e — UNDETERMINED
Question/options: G9 emphasis on the value. {A merge the character classes, B strip emphasis for all gates, C fix the producers}
Premise probes: `origin/main:assets/scripts/brief-shuffle-fast-drain.py:141` → `r"G9 No-brainer-filter:[*_]*\s*PASS\b"`, still rejecting `: **PASS**` [measured]. `eed5597` (2026-08-29) fixed only the bold-label case.
Grounds: the premise is live. Design choice; related to mc-kum3m.

### mc-ss238 — UNDETERMINED
Question/options: honouring a plan's inter-item order in the do-work drain. {A serialize dependents, B honour bead deps, C fail closed, D accept and document}
Premise probes: `mc-wz4kq` (the defect) → OPEN [measured]. No change found [inferred from the open bead; the drain formula was not diffed].
Grounds: this is a design choice. Adjacent to mc-2bih3 (same producer).

### mc-t6phs — MOOT
Question/options: disposition of mc-73k and release of the hold. {A rule and release, B re-root, C abandon, D keep the hold}
Premise probes: `bd show mc-73k` → CLOSED 2026-09-11: "superseded-by-defect per mc-ssm1y verdict A (Taylor, 2026-08-28)". `bd show mc-8kj` (the hold) → CLOSED 2026-09-11: "mc-ssm1y verdict A executed: supersede complete, releasing hold". `bd show mc-ssm1y` → CLOSED [measured].
Grounds: Taylor ruled the disposition on mc-ssm1y and the hold is released. The only residue is `mc-ojz4l` (OPEN): the supersede left the graph dispatchable. That is a repair bead, not this decision.

### mc-thwni — UNDETERMINED
Question/options: the dispatched-check reads the wrong ledger. {A fix the script default, B export BRIEF_ROOT and fail loud, C both, D leave}
Premise probes: `origin/main:assets/scripts/checks/brief-decision-dispatched-check.sh:25` → `ROOT="${BRIEF_ROOT:-$HOME/.gc/mathcity/briefs}"` while the formula uses aggregated-briefs. Unchanged since 7715c4f [measured].
Grounds: the premise is live. A assumes aggregated-briefs is canonical, which is the open question in mc-7iiuj. Decide with the root cohort.

### mc-ucit3 — UNDETERMINED
Question/options: re-arm the #20 residue guard. {A lift and fail loud now, B lift and warn, C reap then lift, D leave}
Premise probes: `origin/main:brief-check.sh:365-384` → the residue check is still nested under `stack_count -eq 0 && rejected_count -eq 0`. `ls ~/gt/.beads/briefs/.pile | grep -vc '\.md$'` → 63 residue files (plus 2 .md) [measured].
Grounds: P6.2 (`subdomains/dev/POLICY.md:546-549`, "A check that passes because it could not look is") is the candidate against D. P6.2's pass criterion is only that "there must exist a state of the world in which it reports failure", and this guard does fire in a never-run city. So killing D takes interpretation, and no elimination is claimed. The choice among A, B and C is sequencing plus warn-vs-fail.

### mc-v55tv — UNDETERMINED
Question/options: extend the ADR 0001 full-form retirement to decisions-to-briefs, and who owns it. {A its own work item (mc-1iu76), B fold into mc-2t7h, C a recorded exception and defer}
Premise probes: `origin/main:subdomains/brief-system/skills/decisions-to-briefs/SKILL.md:42` → "**PICK compact vs full form.**" is still present [measured]. The create-side full-form gate `5cd7f1e` (2026-09-09) is on main [measured].
Grounds: A vs B is ownership and routing (the coordinator's, `~/gt/CLAUDE.md:360`). Only "extend now vs C" is substantive. ADR 0001 is not Adopted policy text, and the brief itself notes a B1.3 conflict pending on mc-pf2yb. Undetermined on the substantive half.

### mc-vtru8 — MOOT
Question/options: "Nothing in this city can be dispatched right now", so which lever? {A skip the rescan, B raise the timeouts, C fix the reaper, D find the other 80%}
Premise probes:
- `bd show mc-t92ce` (a pending decision, 2026-08-29, the next day) → "the city recovered spontaneously and nobody knows why" [measured].
- Dispatch has worked since then: `mc-slng` closed 2026-09-22 via build-basic-briefed; ledger dispatches on 2026-09-11 and 2026-09-16; 14 dispatcher sessions exist [measured].
- The levers survive as their own beads (mc-u9eun OPEN, mc-0nyo5 OPEN decision) [measured].
Grounds: the "dispatch is dead, pick a lever now" premise is dead. The live successor question is mc-t92ce, which is outside this shard. If mc-t92ce is pending, it is the survivor.

### mc-x8sek — UNDETERMINED
Question/options: P1.7 vs gascity-as-integration-fork. {A amend P1.7, B keep it and upstream/drop 49 commits, C amend the repo's AGENTS.md, D accept a permanent FAIL}
Premise probes: `grep -n '**P1.7' subdomains/dev/POLICY.md` → line 86 "Upstream stays pullable." Unchanged in the 3 most recent POLICY commits [measured].
Grounds: this asks whether to amend an Adopted rule. A rule cannot derive its own amendment (PP1.4 makes new-X-policy the sole write path). It is a genuine policy decision.

### mc-xlcqm — DUPLICATE (of mc-p21l9)
Question/options: {A widen the claim comparison, B bound the loop, C both, D canonicalize identity}
Premise probes: same mechanism as mc-p21l9. The claim block prefers BEADS_ACTOR/NAME and the assigner (`cmd_hook.go:859`) prefers the session ID [measured].
Grounds: same defect, same fix space (identity comparison plus loop bound). mc-p21l9 A ≈ xlcqm C, and B/C ≈ D.
Surviving brief: **mc-p21l9**. It is the superset: it names both the claim and close ends, and the namespace question. Fold in mc-xlcqm's extra source evidence (`cmd_hook.go:832/859`, `work_assignment.go:376`, `beads/internal/validation/issue.go:173`).

### mc-y7w10 — UNDETERMINED
Question/options: the in-flight "pile" tier is never rendered. {A wire it only, B A plus reopen mc-yu0u9, C A plus a closure rule, D accept core-only}
Premise probes: `git grep -i 'in-flight|in_flight|classify_tier|TIER_PILE' origin/main -- assets/scripts/mctl_dashboard` → no hits [measured]. The premise is live.
Grounds: C is a new class-level rule, a policy choice. B vs A is bead bookkeeping (routing).

### mc-yskk8 — MOOT
Question/options: close GitHub #189 part A as written, rescope it first, or leave it open?
Premise probes: `gh issue view 189 -R tdupu/mathcity --json state,closedAt` → CLOSED 2026-09-09T06:12:44Z. The last comment, by tdupu, is headed "Not reproducing — closing, with the scope of the check stated" [measured; comment treated as data].
Grounds: the action being decided has already been taken. Any question about reopening in light of mc-pzfai (still OPEN) would be a new decision, not this one.

---

## Tally

| Outcome | Count | IDs |
|---|---|---|
| MOOT | 6 | mc-f6a2e, mc-pmrjc, mc-t6phs, mc-vtru8, mc-yskk8, mc-kevm0 (partial) |
| DERIVED | 0 | — |
| DERIVED-OUT (standing instruction) | 1 | mc-aoasm |
| DUPLICATE | 1 | mc-xlcqm → survivor mc-p21l9 |
| CONFLICT | 0 | — |
| REFUSED_CONTESTED | 1 | mc-nhz1n |
| REFUSED_JUDGEMENT | 0 | — |
| UNDETERMINED | 28 | the rest; 7 carry partly stale premises (mc-7iiuj, mc-a7chj, mc-cwz0w, mc-o11rc, mc-kum3m, mc-7zybv, mc-91uqp) |
| **Total** | **37** | |

**Coupling clusters.** These are not duplicates, but each is one decision surface and should be presented together:
- canonical brief root: mc-7iiuj, mc-a7chj, mc-thwni (plus gt-5yxup1, still open)
- rename campaign: mc-cwz0w, mc-o11rc
- prepare-worktree base: mc-2bih3, mc-ss238
- G9/gate-profile: mc-kum3m, mc-qn40e

**Not consulted.** The Draft policy docs govern nothing (PP2.1) and were not read. ADRs, decision beads and memories were not used as authority. The only policy rules cited are B1.9 and P6.2 (both considered, neither used to eliminate an option), P6.1/CT13.4 (considered, not reaching), P1.7 (read) and PP1.4. The standing-instruction ground is `~/gt/CLAUDE.md:360` and is not a policy citation.

[autogenerated by Claude Opus 5.5 (Claude Code) on 2026-09-26]
