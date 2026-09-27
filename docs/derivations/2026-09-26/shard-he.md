# Derivation pass — hecke rig, 27 pending decision briefs (2026-09-26)

READ-ONLY derivation record for the Mayor. Nothing here is a recorded verdict. ADR 0006 is Proposed,
so no bead, brief or cache was written, and no git mutation or mctl write ran.

**Method:** derive-verdict (mathcity/skills/derive-verdict/SKILL.md), using premise-testing.
Brief bodies were read with `bd -C ~/gt/hecke show <id>`, which is read-only. Git probes ran
against `~/gt/hecke` (it holds the brief branches) and `~/repos/hecke` (`origin/master` = `cca126a6`,
2026-09-22), and both used read-only commands only. Remote state was read with
`git ls-remote --heads origin` (22 heads returned, so the probe could have matched) and `gh pr view`.

**Corpus status (re-measured):** 7 Adopted documents: POLICY-POLICY, POLICY-beads, POLICY-formulas,
brief-system/POLICY, dev/POLICY, dev/POLICY-city and dev/POLICY-documentation. The other 9 are
Draft or have no Status row, so none of them is cited.

**Rules consulted and not cited:**
- B2.4 was not needed for any brief.
- brief-system/POLICY.md gate table (lines 94–116) has no gate-evidence *format* rule, so it does
  not reach he-0axq43.
- dev/POLICY.md P6.1/P6.2/P6.3 (lines ~520–615):
  - P6.2 is about checks that *pass* blindly and P6.3 is about deadlines, so neither covers
    he-7e99tr defect 2 (a check that could not run was recorded as *fail*).
  - P6.1 might reach he-epsj8v option C, but only by interpreting a "code on error" rule as a
    "decision to defer a fix". That is not mechanical, so it is not cited.

**No brief was DERIVED by policy.** Every non-UNDETERMINED result below rests on measurement or
on the standing instruction.

---

### he-iqh4a9 — MOOT
Question/options: merge `fix/275-coset-table-exists-crash`? A merge all 4 files / B merge the 2 code hunks only, keep MREs out (recommended) / C defer.
Premise probes:
- `git -C ~/gt/hecke merge-base --is-ancestor fix/275-… cca126a6` → not an ancestor; `git cherry` → 1 unmerged commit (cd9336f5)
- `git diff --quiet fix/275-… cca126a6 -- magma/package-magma-fixes.mag` → **identical** [measured]
- `git log cca126a6 -- magma/package-magma-fixes.mag` → `ee571653 fix(#340,#347): patch coset_table/coset_table_matrices exists{...} crash sites` (PR #356, merged 2026-09-10T20:14:50Z per `gh pr view 356`)
- `git ls-tree -r cca126a6 -- .beads` → only .gitignore/README.md/config.yaml; the `.beads/mres/he-1ix/` MREs are **not** on master [measured]
- the branch is absent from remote (ls-remote) and present locally in ~/gt/hecke only
Grounds: option B (the brief's recommendation) has already happened. The two code hunks landed byte-identically via PR #356 and the MREs stayed out. The branch's only remaining delta is the MRE files that the brief itself excluded.
Surviving option: none needed. The action is done. The local branch is residue.

### he-8yn93f — MOOT
Question/options: close `fix/side-pairing-wrapper-bug` without merging and delete it from the remote. approve / reject (keep) / defer.
Premise probes:
- `git ls-remote --heads origin | grep side-pairing` → no match (22 heads listed) [measured]
- `git for-each-ref refs/heads` in ~/gt/hecke and ~/repos/hecke → absent [measured]
- `refs/salvage/hecke-prune-20260919/fix-side-pairing-wrapper-bug` → 75f59b93 (the brief's tip), not an ancestor of master [measured]
- ~/repos/hecke `ai/2026-09-19-branch-disposition/DOSSIER.md` postscript records it among "the stale branches pruned local+remote earlier tonight" [measured, the doc's own claim]
Grounds: the requested action (delete without merging) is already done, and the tip is anchored in salvage. "Reject/keep" would now mean restoring the branch from the salvage ref.
Surviving option: approve is already executed. Who authorized the deletion was not traced.

### he-brzl49 — MOOT
Question/options: DROP `feat/280-step1-polredabs-hecke-field-poly`. approve / reject / defer.
Premise probes: `git ls-remote` → absent; local refs → absent; `refs/salvage/hecke-prune-20260919/feat-280-step1-polredabs-hecke-field-poly` → b6b305bf (the brief's tip), not in master [measured]. The 2026-09-19 dossier lists it as anchored with "NO BRANCH DELETED", so the deletion happened after 09-19. The actor was not traced.
Grounds: the branch was already deleted without merging, and the content is preserved in the salvage ref. The follow-ups (he-ed5q8w, he-upi1kj) were not checked.
Surviving option: approve is already executed.

### he-equ713 — MOOT
Question/options: DROP `fix/extremal-rays-docstring`. approve / reject / defer.
Premise probes: ls-remote → absent; local → absent; the salvage ref `fix-extremal-rays-docstring` → b64d6bda [measured].
Grounds: already deleted without merging, and anchored.
Surviving option: approve is already executed.

### he-sojlhr — MOOT
Question/options: DROP `fix/270-n1-case`. approve / reject / defer.
Premise probes: ls-remote → absent; local → absent; the salvage ref `fix-270-n1-case` → 5870db00 (the brief's tip), not in master [measured].
Grounds: already deleted without merging, and anchored.
Surviving option: approve is already executed.

### he-x9xi5p — MOOT
Question/options: delete `origin/feat/snfs-scaling-test` as substantially merged (recommended), or merge first to take v01. Also defer.
Premise probes: ls-remote → absent; local → absent; the salvage ref `feat-snfs-scaling-test` → 530a8fbc; `git ls-tree cca126a6 magma/test/` → `test-snfs-up-to-scaling-02.mag` blob 1b32bac6 (matches the brief) and no v01 file [measured].
Grounds: the recommended deletion is done. v01 survives only in the salvage ref, which matches the recommendation ("v01 is not added").
Surviving option: approve is already executed.

### he-bphri0 — MOOT
Question/options: this bead *records* Taylor's 2026-09-10 grill verdicts on PRs #351–358. It is not an open question.
Premise probes (`gh pr view N --repo tdupu/hecke`):
- 351 CLOSED/unmerged, 352 CLOSED/unmerged
- 353/354/355/356/358 MERGED 2026-09-10T20:14Z
- 357 MERGED 2026-09-11T01:04:29Z
- he-26wwxg comment 2026-09-11 01:03 says "the repair was ALREADY APPLIED and pushed" (re-verified 1 minute before the #357 merge); he-iaqvhy CLOSED [measured]
Grounds: the verdict was given by Taylor and executed exactly as ruled, including the #357 hold condition. It remains open only as a record bead. Note that he-26wwxg itself is still OPEN even though its fix landed. That is bookkeeping drift, not a decision.
Surviving option: n/a. Close as recorded or executed.

### he-ltvno1 — MOOT
Question/options: this bead *records* Taylor's 2026-08-27 approval (option A) of hecke worktree and branch cleanup, with execution blocked on a fresh census.
Premise probes: the 2026-08-29 comment on the bead measured that the cleanup was already executed (worktrees 65→3; tags `salvage/wt-*` = 21). Today: `git -C ~/gt/hecke tag -l 'salvage/wt-*' | wc -l` → 21 (reproduces); `git worktree list | wc -l` → 8 (new worktrees since then, which is expected) [measured].
Grounds: the approval was already given, and the approved action was already executed with the tag-first discipline honoured. Nothing is left to decide.
Surviving option: n/a.

### he-inh88z — MOOT
Question/options: dispatcher CPU saturation. A evidence first (probe one live spinning dispatcher) / B relief first (recycle, losing the evidence) / C relieve 13 and freeze 1.
Premise probes: `ps -Ao pid,etime,pcpu,command | grep 'convoy control'` → **0 processes**; `sysctl -n vm.loadavg` → 8.41 7.81 7.52 (the brief reported 14 spinning dispatchers and load 51 on 2026-09-11) [measured]. The grep could have matched: it would have listed any `gc convoy control --serve --follow` process.
Grounds: the state the brief wanted to preserve as evidence no longer exists, so A and C are impossible, and the relief B would bring has already occurred through some path. The causal question may still deserve a bead. The A/B/C choice is dead.
Surviving option: none. If the saturation recurs, that is a new brief.

### he-9g84vd — DERIVED-OUT
Question/options: route the repos-bound GH #350 drain members. A hand to BART / B build a repos-lane execution surface / C converge the code lines.
Premise probes:
- `gh issue view 350` → CLOSED; PR #353 (size guard) MERGED 2026-09-10 [measured]
- he-0qscpf (T1) CLOSED; `git log -S MAX_EIGENVALUE_CELL cca126a6 -- magma/scripts/gen-tables.py` → d6edab56 (2026-09-10) "Serialize Hecke eigenvalues in the block field", so T1 landed on master [measured]
- gen-tables.py on master already bounds the raw cell (`MAX_EIGENVALUE_CELL = 200`, line 439), but he-9u2qab is still OPEN and its spec asked for 10 KB plus a stderr warning [measured]. That is a partial overlap, and I have not checked whether it satisfies the spec.
- he-ejzuwp (packet regen), he-o5i23t, he-2z38pe and he-8gx78e are OPEN [measured]
Grounds: the question is purely about routing, i.e. who executes the remaining repos-bound members. That is removed by Taylor's standing instruction (/Users/tdupuy/gt/CLAUDE.md:360): *"Staffing, routing, and sequencing are NOT his. Who does what, who reviews whom, what order things merge in — the coordinator owns all of it."* This is a standing instruction, not policy. Its premise is also half-dead, because T1 and a form of T2-Python have landed.
Surviving option: the coordinator's call.

### he-xucfdq — DUPLICATE (survivor: he-8oku2r)
Question/options: repair path for the assignee-convention skew. A operator-unstick latch he-nl8l1b now / B pack-level convention fix / C cancel and re-sling.
Premise probes:
- the claim script still compares a bare assignee: `~/gt/gascity-packs/gascity/commands/claim/run.sh:112` `EXPECTED_ASSIGNEE="${BEADS_ACTOR:-${GC_SESSION_NAME:-…}}"`, :212 `elif [ "$claim_assignee" != "$EXPECTED_ASSIGNEE" ]` [measured]. The defect is live.
- "the stranded build workflow is the delivery vehicle for #338": `gh pr view 357` headRef = `fix/338-rank-dispatch-stage`, commits 54abc5f2 and f8106d9e; `git merge-base --is-ancestor 54abc5f2 cca126a6` → true [measured]. **The #338 code has already landed on master.** The stranded latch he-nl8l1b (OPEN) blocks only bookkeeping.
Grounds: the design half (which side of the assignee contract is authoritative) is the same decision as he-8oku2r's call (a), and he-8oku2r frames it more completely (it also covers containment). The unstick half's stated stake, delivering #338, is already met. What remains is latch hygiene, which is operator bookkeeping.
Surviving brief: **he-8oku2r**.

### he-8oku2r — UNDETERMINED
Question/options: (a) is the consumer or the producer authoritative for assignee (id vs name)? (b) do the containment fixes land now? The brief's options are A/B/C/D.
Premise probes: the claim-script comparison is unchanged (see he-xucfdq); he-ikecba, he-dwbl1d and he-nl8l1b are all OPEN [measured].
Grounds: this is a genuine design choice about the gc/pack identity contract. No Adopted rule reaches it. The premise is live. It is the survivor for he-xucfdq and for he-7e99tr's defect-1 half.

### he-7e99tr — UNDETERMINED
Question/options: authorize remediation of two defects, and in what order. A fix both / B defect 1 only / C defer both.
Premise probes: he-ikecba OPEN, he-1yivla OPEN; `ls ~/gt/hecke/.gc/scripts/checks` → absent (the directory holds only gc-beads-bd.sh) [measured]. Both defects are live.
Grounds:
- The ordering half is DERIVED-OUT under the standing instruction (CLAUDE.md:360), as he-2w4hdc already was in the 09-25 pass.
- The defect-1 half duplicates he-8oku2r.
- The defect-2 half (reclassify an unresolvable gate path as `unknown`, and provision the scripts) is a fleet-wide outcome-taxonomy change. P6.2 and P6.3 do not reach it mechanically. It is a genuine decision.
- Recommend narrowing this brief to defect 2 only.

### he-epsj8v — UNDETERMINED (premise not reproduced)
Question/options: fix route for the `gc bd --actor` store misroute. A fix the routing / B refuse loudly / C document only.
Premise probes (read path, `show` only), all against he-gsn20h:
- from ~/gt: `gc bd show he-gsn20h --actor derive-probe` → `gc bd: answering from the rig "hecke" store`, and the bead renders
- the same from ~/gt/hecke and from ~/gt/mathcity.brief-operator-2 (the original cwd) → the rig store in every case
- controls matched [measured]
**The misroute did NOT reproduce today.** I did not test the write path (`close`), and my env lacks the pool session's `GC_RIG_ROOT`/`GC_BEADS_SCOPE_ROOT`. The probe could have failed, because it prints the store it answers from.
Grounds: this may be fixed (~/go/bin/gc was rebuilt 2026-09-19) or it may depend on the environment. If it is live, choosing A vs B vs C is a design call.
Recommendation to the Mayor: re-probe in a pool env before presenting this brief.

### he-0axq43 — UNDETERMINED
Question/options: gate-evidence format authority. A widen the parser / B enforce machine form at write time / C both / D neither.
Premise probes: `~/repos/mathcity/assets/scripts/brief-shuffle-fast-drain.py:28` STATUS_PATTERN; its last change was eed5597 (2026-08-29), before the brief, so the parser is unchanged [measured]. The brief-system gate table (POLICY.md:94–116) names the gates but prescribes no line format [measured].
Grounds: no Adopted rule fixes the format. This is a genuine contract choice.

### he-768to5 — UNDETERMINED
Question/options: parallel-agent isolation in hecke. A replace the `.claude` symlink / B guard the dispatchers / C serial-only / D investigate a guard override.
Premise probes: `git ls-files -s .claude` in both hecke lanes → `120000 79f2b981… .claude`; the symlink points to `.agents/claude`; he-ycfcai is OPEN [measured]. The premise is live.
Grounds: this changes the repo layout and city dispatch. No Adopted rule decides it.

### he-cc1vqe — UNDETERMINED (premise partly shifted)
Question/options: fix root resolution for rig-scoped brief-shuffle. A absolute artifact_root in the order / B export BRIEF_ROOT / C formula resolves from the rig label / D gascity dispatch change. There is also a drain-vs-triage of the backlog.
Premise probes:
- `orders/brief-shuffle-on-submit.toml` in ~/repos/mathcity @ b792059 is now `scope = "city"`, with a header saying it was "fixed 2026-09-10" for a *different* fan-out defect. So option A's target (a rig-scoped on-submit order) no longer exists in that form [measured].
- `formulas/brief-shuffle.toml` artifact_root default is still `.beads/briefs` (rig-relative), and `brief-check.sh:12` still has `ROOT="${BRIEF_ROOT:-.beads/briefs}"` [measured].
- he-l6ffjr is OPEN.
Grounds: the cwd-relative root still exists, but the order the brief proposes patching has changed shape. This is a design choice, and the brief needs a refresh before presentation.

### he-iy7mi8 — UNDETERMINED
Question/options: fix shape for the fast-drain idle loop. A eligibility-aware check / B restore archive-sweep eviction / C, D.
Premise probes: `orders/brief-shuffle-fast-drain.toml` is still `scope = "rig"` with `check = "find .beads/briefs/.pile … | grep -q ."` (last change 37b0413, 2026-08-16); `ls ~/gt/hecke/.beads/briefs/.pile | wc -l` → 13 [measured]. The premise is live.
Grounds: this is a genuine design choice.

### he-k8l3sa — UNDETERMINED
Question/options: five hecke hygiene defects. A fix items 1 and 2 now, triage 3–5 / B triage all / C item 2 only / D defer all.
Premise probes:
- `git grep '^<<<<<<< ' cca126a6 -- magma/` → `magma/make/old/make-sub-from-conjugate-subgroups-1-1.mag:4` (item 1 is live)
- `magma/DATA/torsion-experiments` exists only in ~/gt/hecke; there are 0 tracked files on master; `.gitignore:23: magma/DATA/*` ignores it by design (item 2 is live) [measured]
Grounds: tracking DATA cuts against the repo's own `.gitignore` convention, which is a hecke repo policy and not an Adopted city rule. Items 3–5 are data and math judgements. Genuine decision.

### he-bsdu5c — UNDETERMINED (premise partly stale)
Question/options: accept the acceptance-step-1 datum and approve publish propagation. approve / reject-rerun / defer / approve-with-conditions.
Premise probes: `bd show he-eq4h4o --json` → CLOSED 2026-09-09T18:46:00Z, `gc.outcome=fail` (13 minutes after the brief was deposited); he-mza8mc OPEN; he-3jkemh OPEN [measured].
Grounds: accepting a math-acceptance datum is Taylor's call. However, the "deferred publish lane" this brief would release belongs to a workflow root that has since closed with outcome=fail, so an approval may have no lane to propagate through [inferred]. The Mayor should re-measure before presenting.

### he-o1mq6p — UNDETERMINED (premise partly stale)
Question/options: #243 CamelCase rename. A do it before the big move / B kill it / C price it first / D defer.
Premise probes: `gh pr view 358` → MERGED 2026-09-10, "#243 step 1: derive the intrinsic -> CamelCase mapping table"; `gh pr view 362` → OPEN, "#243 Phase 1: boundary closure table + certification harness"; issue #243 OPEN; he-v2hw OPEN [measured].
Grounds: the premise that "nobody has ever measured the cost" is stale, because option C's pricing work has partly landed (the mapping table) and phase-1 is in flight. A vs B is still a genuine human call, and Taylor's merge of #358 suggests the work is proceeding [inferred]. The brief needs a refresh.

### he-q2qjmu — UNDETERMINED
Question/options: recover 23 open epics into the brief system. A all / B epics plus a read-only orphan census / C sample-gate / D rejected.
Premise probes: I did not measure the current epic count precisely. The census counts date from 2026-08-29 and have probably drifted [inferred].
Grounds: scope and priority judgement. No rule reaches it.

### he-c6evty — UNDETERMINED
Question/options: merge `feat/he-rpuri-sigma18-t7ab`? merge after the LaTeX sign-off / not.
Premise probes: branch a17e2415 exists only locally in ~/gt/hecke (absent from remote); it is not in master and `git cherry` shows 1 unmerged; `latex/notes/notes.tex` differs from master and the data/.mag files are absent on master [measured]. The premise is live.
Grounds: the LaTeX hard gate needs Taylor's sign-off, which is a math judgement.

### he-q54447 — UNDETERMINED
Question/options: merge `feat/he-0rk2-sigma18-eisenstein-lattice` (e1dafe92), paired with rpuri and a derivation.md fix?
Premise probes: local-only, not in master, and all 6 files are absent on master [measured]. The premise is live.
Grounds: math and data judgement. It is coupled to he-c6evty but is a separate decision (a different branch), so it is not a duplicate.

### he-njmz59 — UNDETERMINED
Question/options: merge `fix/he-jlc6y-certify-subgroup-prewrite-gate` (21d72912) with the 3-line hardening?
Premise probes: local-only, not in master. `git diff` between the branch and master on `make-canonicalize-gamma0-snf.mag` shows that the pre-write `ok_subgroup` gate is **not** on master (later master commits 5fecb766 and 09e5a642 touched the file without adding it) [measured]. The premise is live.
Grounds: a code and math correctness judgement.

### he-yyhogb — UNDETERMINED
Question/options: merge `fix/he-b3hnc-hyppol-redundant-halfspace` (77bf2316), conditional on a follow-up test?
Premise probes: local-only, not in master, cherry +1; `package-polyhedra.mag` differs and the test file is absent on master [measured]. The premise is live.
Grounds: code judgement.

### he-tsktoh — UNDETERMINED
Question/options: merge `feat/he-tu7e4-p137-eigenforms-script` (6c6f798f)? The recommendation was "not yet, master broken at package-modular-symbols.mag:928". The brief also carries an open math question on #68.
Premise probes: local-only, not in master, and the script is absent on master [measured]. I did not test whether the master regression persists.
Grounds: math judgement (manin_rank 3 vs 2). The "master is broken" premise was not re-tested.

---

## Tally

| Outcome | Count | IDs |
|---|---|---|
| MOOT | 9 | he-iqh4a9, he-8yn93f, he-brzl49, he-equ713, he-sojlhr, he-x9xi5p, he-bphri0, he-ltvno1, he-inh88z |
| DERIVED | 0 | — |
| DERIVED-OUT | 1 | he-9g84vd |
| DUPLICATE | 1 | he-xucfdq (survivor he-8oku2r) |
| CONFLICT | 0 | — |
| REFUSED_JUDGEMENT / REFUSED_CONTESTED | 0 | — |
| UNDETERMINED | 16 | he-8oku2r, he-7e99tr, he-epsj8v, he-0axq43, he-768to5, he-cc1vqe, he-iy7mi8, he-k8l3sa, he-bsdu5c, he-o1mq6p, he-q2qjmu, he-c6evty, he-q54447, he-njmz59, he-yyhogb, he-tsktoh |
| **Total** | **27** | |

**Stale-premise flags among the UNDETERMINED briefs.** Refresh these before presenting:
- he-epsj8v: the misroute did not reproduce.
- he-bsdu5c: the workflow root is closed with outcome=fail.
- he-cc1vqe: the on-submit order is now city-scoped.
- he-o1mq6p: pricing is partly done.
- he-7e99tr: narrow it to defect 2.

**Branch deletions behind four of the MOOT briefs.** he-brzl49, he-equ713, he-sojlhr and he-x9xi5p were deleted after the 2026-09-19 "NO BRANCH DELETED" anchoring. I did not trace who authorized the deletions. All the tips are preserved under `refs/salvage/hecke-prune-20260919/`.
