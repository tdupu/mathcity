# Derivation pass — rigs gascity-packs, gascity, lmfdb, agent_skills (27 briefs) — 2026-09-26

This is a derivation RECORD for the Mayor. Nothing was recorded, closed, or commented. ADR 0006 is Proposed, not Adopted.
Every bead read used `bd -C ~/gt/<rig> show` and no write commands. `~/repos/*` was only read: grep, git log, cat-file, branch --contains.

**Corpus check [measured]:** `grep -m1 '^| Status |'` over 16 policy files. 7 are Adopted: POLICY-POLICY, POLICY-beads, POLICY-formulas, brief-system/POLICY, dev/POLICY, dev/POLICY-city, dev/POLICY-documentation. The PROPOSED-rule grep returns **27** hits, the same as the skill's count. The JUDGEMENT RULE markers in Adopted documents are B2.13 and B2.14 (brief-system/POLICY.md:501 and :531).

**Rules quoted (verified with `grep -n -F`):**
- **B2.4**, `subdomains/brief-system/POLICY.md:296`, Adopted, not PROPOSED: *"Unadjudicated briefs accumulate in exactly one pile. Canonical membership is the bead query: open `type=decision` brief beads with no active defer window."*
- **P5.4**, `subdomains/dev/POLICY.md:497`: *"When a doc's behavioral claim contradicts the code, **the code wins**"*. Its scope is gascity, brief-system and workflow **behavior**. It was a candidate for as-43bwa and was **discarded**, because an avatar file path is not a behavioral claim about gascity.

No brief below comes out DERIVED. Every non-UNDETERMINED outcome rests on a measurement, a duplicate finding, or the standing instruction, not on a policy rule that settles the choice.

---

### as-43bwa — UNDETERMINED
**Question and options:** authorize-git-operation Step 1 names `mayor-agent.png`. Should we (A) repoint the references to `taylor-mayor-agent.png`, (B) create or alias the file, or (C) drop the step?

**Premise probes:**
- `ls ~/repos/agent-skills/assets/avatars/` → `taylor-mayor-agent.png` exists and `mayor-agent.png` does not [measured]
- `grep -n agent.png ~/repos/mathcity/skills/authorize-git-operation/SKILL.md` → lines 29, 210 and 248 still name `mayor-agent.png` [measured]. The same text is in `~/gt/mathcity` and in 2 worktrees.
- `bd show as-hikdh` → OPEN

**Grounds:** The premise is live. P5.4 was considered and discarded: it covers gascity behavior claims, not asset paths. No Adopted rule reaches the choice between A, B and C.

**Note:** The references live in the **mathcity** skill copy, not only in the agent-skills repo that the brief names as the lane.

### gs-2h0q — UNDETERMINED (premise partly moved)
**Question and options:** gc hook --claim hands workflow-root latches to role workers (gs-4mjl). Options: ship the SDK topology guard, patch the role prompts, do both, or keep releasing latches by hand.

**Premise probes:**
- `bd show gs-4mjl` → OPEN, P1 [measured]
- `~/repos/gascity cmd/gc/cmd_hook_claim.go:2969 hookClaimMatchesRoute` → still has no `IsWorkflowTopologyKind` guard on the `routedTo == target` path [measured, at HEAD 4bafc941b]
- An upstream #5900-shaped change now blocks the **run_target fallback** for expanded workflow roots (`workflowRunTargetFallbackEligible`, :2961) [measured]
- `graphroute.go:662` and `:768` skip topology kinds during routing [measured]. Whether roots still receive `gc.routed_to` at all is **not established** [inferred].

**Grounds:** The premise is partly live. No Adopted rule chooses the repair.

### gs-3ula — UNDETERMINED
**Question and options:** Approve, revise, reject or defer the commission continuation graph for gs-ab5v. That work is a PR to gastownhall/gascity adding `.repo.git/` to `rigGitignoreEntries`.

**Premise probes:**
- `bd show gs-ab5v` → OPEN [measured]
- `grep repo.git ~/repos/gascity/cmd/gc/gitignore.go` → no match, so the change has not landed [measured]

**Grounds:** The premise is live. The brief asks Taylor to judge whether the fail-closed branch and credential blockers are acceptable, which no Adopted rule settles. It is close to routing of already-approved work, but it is not purely that.

### gs-b9ja — UNDETERMINED (survivor of a 3-brief duplicate cluster)
**Question and options:** Which identity is canonical in the claim protocol: session ID (stamped by hook --claim) or session NAME (compared by bd close)? Options: (A) stamp the NAME, plus alternatives that loosen the check or touch the runtime.

**Premise probes:** Not re-probed at source. The brief's own evidence is the bead metadata carrying both `gc.session_id` and `gc.session_name`, from a live session. I did not audit the assignee consumers.

**Grounds:** Genuine design choice.

**Survives over** gsp-pqtyvl and lm-0ggn (below). gs-b9ja sits in the rig that owns the claim code and names the concrete choice. Fold into it lm-0ggn's cheap "probe reclaim first" step and gsp-pqtyvl's "tighten, don't widen" constraint.

### gs-b9rs — UNDETERMINED
**Question and options:** How should the brief-shuffle-fast-drain trigger clear when `.pile` holds files for closed beads? (A) let the drain move or delete them, (B) make the trigger membership-aware, (C) clear the files by hand once.

**Premise probes:**
- `ls ~/gt/gascity/.beads/briefs/.pile/` → `gs-1vtf.md` (Aug 23) and `gs-xve9.md` (Aug 24) are still present [measured]
- `grep check ~/gt/mathcity/orders/brief-shuffle-fast-drain.toml:6` → the trigger is still a bare `find … -name '*.md' | grep -q .` [measured]

**Grounds:** The premise is live. B2.4 makes the bead query canonical, which favours B, but it does not forbid A or C. Policy narrows the choice without determining it.

### gs-bdqv — UNDETERMINED (premise incomplete)
**Question and options:** Ship the gs-1pm3 fast path by raising an unowned, expiring test-census ratchet (Approve), take an offset pass instead (Approve with offset), or leave it unintegrated (Reject).

**Premise probes:**
- `bd show gs-47cb` → OPEN; `bd show gs-1pm3` → OPEN [measured]
- `git -C ~/gt/gascity branch -a --contains 0287212f3` → the tip commit exists on **no branch** [measured]
- `gh issue view 32 -R tdupu/gascity` → OPEN [measured]
- ~/repos/gascity has a **separate, competing fix for #32**: `91892dac2` "#32: skip the eager revision snapshot on one-shot CLI config loads". It is on branch `fix/gc-event-emit-startup`, is **not** in origin/main, and the brief never mentions it [measured].

**Grounds:** The decision is a judgement about how much authority an orphaned control keeps. The brief's picture of "the fix" is incomplete, and the Mayor should reconcile the two fix lines before this is presented.

### gs-j70s — UNDETERMINED
**Question and options:** Which of 4 remedies stops `make test` running zero tests (and reporting red) in worktrees nested under a go.work?

**Premise probes:**
- `cat ~/gt/gascity/go.work` → still `use (. ../gascity-packs)` [measured]
- `Makefile:433` → `GOWORK="$${GOWORK-}"` in TEST_ENV is unchanged [measured]
- `bd show gs-of5i` → OPEN [measured]

**Grounds:** The premise is live. This is an engineering trade-off with no Adopted rule selecting a remedy.

### gs-jdc8 — UNDETERMINED (premise partly stale)
**Question and options:** Order of backup remediation. (A) remediate the data first and restore the interim JSONL leg, (B) fix the monitor first, (C) skip the monitor, (D) accept the exposure.

**Premise probes:**
- `bd show gs-07cu` → OPEN, P0 [measured]
- `mol-dog-backup.sh:261` still auto-creates a `file://` remote, so D1 is live [measured]
- Upstream commits `6e7f06eff` (#5509, 2026-09-06, "make offsite backup failure visible") and `225211190` (#5329, 2026-09-12, "report backup failures … honestly") address D3 [measured]
- All 4 `.gc/cache/repos/*/…/mol-dog-backup.sh` copies now **differ** from the repos copy [measured]. The brief's "byte-identical" claim is stale.

**Grounds:** The sequencing part alone would fall under the standing instruction. The brief also asks for authorization to write to the remotes and for a temporary reversal of a Taylor ruling (restoring the JSONL leg). Both are his to decide.

### gs-wydl — UNDETERMINED
**Question and options:** Fix the producers (A), fix the gate (B), or make rejection visible (C) for the G9 gate-evidence parse mismatch.

**Premise probes:**
- `ls ~/gt/gascity/.beads/briefs/.pile/.rejected/` → 11 slugs, newest Sep 12 [measured]
- `brief-shuffle-fast-drain.py:131-141` still requires a literal `G9 No-brainer-filter:` line (tolerating bold) [measured]
- `bd show gs-xktf` → OPEN, P3 [measured]

**Grounds:** The mismatch is live. The title's "never reach an adjudicator" is **overstated** under B2.4: gs-b9ja, gs-b9rs, gs-2h0q, gs-3ula, gs-bdqv, gs-j70s and gs-jdc8 are all under `.rejected/` and are also all in this pending bead-query pile [measured]. The repair choice is still genuine.

### gsp-27atpf — UNDETERMINED (load-bearing premise contradicted at source, not reproduced)
**Question and options:** gc mail send exits 0 on undelivered mail. (A) exit non-zero, (B) exit non-zero and add a durable sink, (C) re-point the doctrine to bead+brief.

**Premise probes:**
- `~/repos/gascity/cmd/gc/cmd_mail.go:1838-1841`: when recipient resolution fails it prints exactly the observed message (`unknown recipient %q: %v`) and **`return 1`** [measured]
- `:1509` turns a non-zero code into `errExit`, and `main.go:127` maps `errExit` to exit 1 [measured]
- `git log -L1837,1842` → those lines last changed on 2026-08-19 (#5209), before the brief's 2026-09-16 observation [measured]
- `/Users/tdupuy/go/bin/gc` was built Sep 19 and carries no vcs stamp [measured]

**Grounds:** The source says exit 1 on exactly this path, which contradicts the brief's "mail exit: 0". I did not reproduce it with the binary, because a live send is a write-shaped command. Settling probe: `gc mail send zz-no-such-recipient probe; echo $?`. If that returns 1, the premise is dead and the brief is MOOT.

### gsp-2m3auw — MOOT
**Question and options:** Fix scope, narrow or wide, for 26 mathcity `[steps.check]` blocks that point at `.gc/scripts/checks/brief-*.sh`.

**Premise probes:**
- `git -C ~/repos/mathcity grep '.gc/scripts/checks' -- '*.toml'` → no brief-check hits. `formulas/brief-gate-keep.toml:64,89,115` use `../assets/scripts/checks/…` [measured]. This was fixed at `cc58a95` (2026-08-19, "resolve check scripts from the pack … (D9)").
- `git -C ~/gt/gascity-packs grep … '*.toml'` → 21 hits, but all in the **retired legacy vendored tree** `gascity-packs/mathcity` [measured]
- `grep source ~/gt/city.toml ~/gt/pack.toml`, plus the imported gascity-packs `gascity`, `gascity/roles` and `contributing` pack.toml files → **no import of `gascity-packs/mathcity`**. mathcity is imported only from `/Users/tdupuy/repos/mathcity` [measured]

**Grounds:** The broken gates are not loaded by the live city, and the canonical pack was already fixed. This completes the open question QUIMBY 70 left in the bead comments ("does anything execute formulas from the legacy tree?"), and the answer is no. Leftover work: delete or tombstone the legacy tree. That is hygiene on gsp-simshh, not this decision.

### gsp-3h3uit — DERIVED-OUT (standing instruction, not policy)
**Question and options:** None enumerable. The body is a machine-generated work order: "Review the batch, repair the producer path, and file a producer-repair brief".

**Premise probes:**
- The batch file `decision-decision-profile-decision-profile-action-block-missing-on-approve.md` exists [measured]
- Input convoys `gsp-1fxeo3` and `gsp-h9xo03` are both OPEN with no workflow, which matches the gsp-rqgc0l hang [measured]

**Grounds:** This is repair work typed as a decision, and routing it is the coordinator's job. Whatever happens to it follows the gsp-e8dlmf verdict (park or keep the repair-dispatch loop).

### gsp-5daxgf — MOOT
**Question and options:** Two questions: (1) is reinterpreting the blocker gsp-me6y39 as "produce a disposition brief" what Taylor meant, and (2) should the continuation be dispatched?

**Premise probes:**
- `git -C ~/repos/gascity-packs branch -r --contains 852285d` → `fork/main` [measured]
- `git diff --quiet 6f0af23 852285d -- pr-pipeline/formulas/mol-pr-from-issue.formula.toml` → identical [measured]
- `fork/main` still carries `pour = true` (line 70) [measured]

**Grounds:** The blocker's literal action, landing 6f0af23 on fork/main, is **already done**. The brief measured this itself and I re-measured it. The continuation would only produce a brief confirming that. What remains is to close gsp-me6y39 (still OPEN, P0) with this evidence, which is bookkeeping and needs no Taylor decision.

### gsp-5fe9x4 — UNDETERMINED
**Question and options:** Fix the unguarded ralph-gate cwd in gc-core, or keep hand-repairing `gc.work_dir` per root.

**Premise probes:**
- `~/repos/gascity/internal/convergence/condition.go:388-389` → `if env.WorkDir != "" { cmd.Dir = env.WorkDir }`, with no existence check [measured]
- `bd show gsp-5yjkak` → OPEN [measured]

**Grounds:** The premise is live. The choice is genuine.

### gsp-6vc51q — UNDETERMINED
**Question and options:** Execute the "remediation remainder" dispatch graph for gsp-pdbyqa? This depends on (1) whether that reading of the bead is right and (2) whether preparing diffs exceeds a read-only bead.

**Premise probes:** `bd show gsp-pdbyqa` → OPEN [measured]. The row count was not re-measured.

**Grounds:** Confirming intent and scope is Taylor's call.

### gsp-e8dlmf — UNDETERMINED (survivor of duplicate pair with gsp-ga5gbh)
**Question and options:** Park the brief-producer-failure-rollup repair-dispatch loop (A), keep it (reject), or defer.

**Premise probes:**
- `bd show gsp-rqgc0l` → OPEN; `gsp-hdtd9l` → OPEN; `gsp-k6jjoo` → OPEN [measured]
- The premise "gsp-ga5gbh was gate-rejected **out of the queue**; the adjudication cannot arrive" is **dead under B2.4**. gsp-ga5gbh is an open `type=decision` bead in this pending set [measured], so it is in the one canonical pile even though its file sits under `.pile/.rejected/`.

**Grounds:** The loop-parking question is live and genuine. Only the second half of the "stalled twice over" framing is dead.

### gsp-ga5gbh — DUPLICATE of gsp-e8dlmf
**Question:** Stop dispatching and fix the guard, or keep dispatching the same producer-repair loop. Same loop and decision as gsp-e8dlmf, which is newer, carries the later dispatch-hang evidence (gsp-rqgc0l), and has an action_block. **gsp-e8dlmf should survive.** Carry this brief's guard defects (gsp-hdtd9l) into it.

### gsp-izal2t — MOOT (also a duplicate of gsp-qtzu92)
**Question and options:** (a) Kill the 6 spinning drain-ack processes now? (b) Which fix should gascity land for drain-ack cost?

**Premise probes:**
- `pgrep -fl "gc runtime drain-ack" | wc -l` → **0** [measured], so (a) is moot
- `git -C ~/repos/gascity log origin/main`: `8773e732e` (#6401, 2026-09-21) "decline the revision snapshot in the hosted-credential probe" and `c0c60c11c` (#6526, 2026-09-23) "memoize the hosted-credential probe per city" [measured]. Both target `citySelectsHostedBeadsCredentialProvider → LoadWithIncludes`, which is exactly the frame in this brief's call stack (and gsp-9hjz5q's).

**Grounds:** Upstream has already chosen and landed the fix shape. Leftover work: the local checkout (HEAD 4bafc941b, Sep 19) and the installed binary predate it, so pull upstream by the routine gascity update procedure. That is not a Taylor decision. [inferred] I did not reproduce that the upstream fix removes the local stall.

### gsp-m150vb — UNDETERMINED
**Question and options:** Repair surface for the orphan sink entry `mathcity.check-mayor-objectives`. Its scripts/classify.py is the only copy.

**Premise probes:**
- `ls ~/gt/.claude/skills/mathcity.check-mayor-objectives/scripts` → `classify.py`, no SKILL.md [measured]
- `find ~/repos/mathcity ~/gt/mathcity -name classify.py` → none [measured]
- `bd show gsp-1lfkqj` → OPEN

**Grounds:** The premise is live. The choice is genuine.

### gsp-mkp5uq — UNDETERMINED
**Question and options:** Approve the commission graph that absorbs 4 superpowers-adoption attempts for gsp-47hj4l?

**Premise probes:** `bd show gsp-47hj4l` → OPEN, P0. The commission step beads (gsp-fiz6do and siblings) are CLOSED normally [measured].

**Grounds:** Confirming intent is Taylor's call.

### gsp-oodpqb — UNDETERMINED
**Question and options:** (A) accept conditional resolution of prefixed skill handles and narrow P1.8, or (B) dedupe the sinks.

**Grounds:** Option A amends an Adopted rule (P1.8). A policy amendment is a human act (PP1.4 write path), and no rule selects between A and B. Premise not re-probed.

### gsp-pqtyvl — DUPLICATE of gs-b9ja
**Question:** The same pool-worker claim/close identity mismatch (session_id vs session_name) and the same "fix or routine --force" decision. **gs-b9ja should survive.**

### gsp-qtzu92 — MOOT (duplicate of gsp-izal2t in subject)
**Question and options:** Which repair shape to authorize for the drain-ack stall, and whether to hand it to BART now.

**Premise probes:** Same as gsp-izal2t: 0 live drain-ack processes, and upstream #6401 and #6526 on origin/main fix the exact `citySelectsHostedBeadsCredentialProvider` frame [measured].

**Grounds:** Upstream has chosen and landed the shape. Handing it to BART reduces to a routine upstream pull, and routing is not Taylor's decision in any case.

### gsp-vp4xif — UNDETERMINED
**Question and options:** Approve the "verify-and-finish" reading and the build-basic-briefed dispatch for gsp-2bowrk?

**Premise probes:** `bd show gsp-2bowrk` → OPEN, P0 [measured].

**Grounds:** Confirming intent is Taylor's call.

### lm-0ggn — DUPLICATE of gs-b9ja
**Question:** The same claim/close identity-spelling mismatch. Its recommended option B, "probe whether reclaim permits an unforced close first", is a useful first step to fold into gs-b9ja. **gs-b9ja should survive.**

### lm-ckhb — UNDETERMINED (survivor of duplicate pair with lm-m9oo)
**Question and options:** Cadence for no-brainer-candidate-curate on lmfdb: (A) gate on an input-hash change … (D) leave as is.

**Premise probes:**
- `ls ~/gt/lmfdb/.beads/.gates-candidate-pile` → one file from Jul 18, so the inputs are static [measured]
- `bd show lm-h9nl` → OPEN [measured]

**Grounds:** The 2026-09-17 bead comment records a genuine A-vs-D tension (curation over static input doubles as an instrument self-test). This is a real judgement.

### lm-m9oo — DUPLICATE of lm-ckhb
lm-ckhb is the explicit re-file of this brief ("re-file of lm-m9oo, which a formatting gate rejected"), and both are OPEN [measured]. **lm-ckhb should survive.**

---

## Tally

| Outcome | Count | IDs |
|---|---|---|
| DERIVED | 0 | — |
| MOOT | 4 | gsp-2m3auw, gsp-5daxgf, gsp-izal2t, gsp-qtzu92 |
| DERIVED-OUT | 1 | gsp-3h3uit |
| DUPLICATE | 4 | gsp-ga5gbh→gsp-e8dlmf, gsp-pqtyvl→gs-b9ja, lm-0ggn→gs-b9ja, lm-m9oo→lm-ckhb |
| CONFLICT | 0 | — |
| REFUSED_JUDGEMENT / REFUSED_CONTESTED | 0 | — |
| UNDETERMINED | 18 | as-43bwa, gs-2h0q, gs-3ula, gs-b9ja, gs-b9rs, gs-bdqv, gs-j70s, gs-jdc8, gs-wydl, gsp-27atpf, gsp-5fe9x4, gsp-6vc51q, gsp-e8dlmf, gsp-m150vb, gsp-mkp5uq, gsp-oodpqb, gsp-vp4xif, lm-ckhb |
| **Total** | **27** | |

Stale or contradicted premises inside UNDETERMINED briefs, worth fixing before presentation:
- **gsp-27atpf:** the source says exit 1. A one-line probe would settle it, and if confirmed the brief is MOOT.
- **gs-bdqv:** the brief does not mention a competing #32 fix branch.
- **gs-jdc8:** upstream has changed the backup monitor since filing, and the cached copies no longer match.
- **gs-wydl and gsp-e8dlmf:** "never reaches an adjudicator" is false under B2.4.
- **gs-2h0q:** upstream partially guards the claim path.
