# Derivation pass — rig `hq`, 45 pending decision briefs — 2026-09-26

**Derivation record for the Mayor, not recorded verdicts.** ADR 0006 is Proposed. Nothing was written
to any bead, brief, cache or ref. Read-only throughout.

Side effects I caused, stated so nobody has to guess:
- one `git fetch -q origin` in `~/repos/mathcity` (updates remote-tracking refs only; no HEAD/index/work-tree change). Arguably inside LP1's "history-mutating" fence; flagged.
- one in-process pytest run in `~/repos/mathcity` (`PYTHONDONTWRITEBYTECODE=1 -p no:cacheprovider`); `git status` afterwards shows only changes that pre-existed (the `roadmap-draft` → `draft-roadmap` rename).

## Corpus, re-measured

Status rows re-read with `grep -m1 '^| Status |'` over 16 files in `~/gt/mathcity` (HEAD `b4f09ac`, 2026-09-25).
**Adopted (7):** `POLICY-POLICY.md`, `POLICY-beads.md`, `POLICY-formulas.md`, `subdomains/brief-system/POLICY.md`,
`subdomains/dev/POLICY.md`, `subdomains/dev/POLICY-city.md`, `subdomains/dev/POLICY-documentation.md`.
Draft/no status row (9, not cited): `POLICY-skills.md`, `POLICY-BEAD-REVIVAL.md` (no row), brief-system `POLICY-DRIFT-AUDIT-2026-08-19.md` (no row), `computing`, `latex`, `lmfdb`, `magma`, `mayor`, `policies`.
Rules discarded at the rule-level gate: **CT12.4** (`POLICY-city.md:660`, marked PROPOSED — the only Adopted-document rule about `rm -rf`) and **PP1.13** (`POLICY-POLICY.md:42`, PROPOSED). JUDGEMENT RULEs present: B2.13 (`:501`), B2.14 (`:531`).

Bodies read with `bd -C ~/gt show <id>` (read-only).

---

### gt-024lxi — UNDETERMINED (one half is policy-derived)
Question/options: Gate Evidence heading regex is prefix-blind. Repair: A narrow widening (optional `§N —` prefix), B broad widening, C pin the heading spelling; plus disposition of 3 false-rejected briefs (re-pile vs leave).
Premise probes:
- `grep -n GATE_EVIDENCE_HEADING ~/repos/mathcity/assets/scripts/brief-shuffle-fast-drain.py` → line 41 still `^(?:#{1,6}\s+)?Gate Evidence\s*$` [measured]. Unchanged in `~/gt/mathcity` too.
- `ls ~/gt/.beads/briefs/.pile/.rejected/` → `gt-e8sh8h`, `44-no-brainer-curate-duplicate-category-briefs-brief`, `46-launch-repair-review-not-idempotent-brief` all still there [measured]. Premise live.
Grounds: **B2.16** (`subdomains/brief-system/POLICY.md:606`, Adopted, not PROPOSED): "A form-, schema-, or gate-mechanical rejection of a brief is a **defect signal about the PRODUCER**, never a disposition of the brief. It MUST flag the brief" (606-608) … "Fail: a mechanical / form / schema failure removes a brief from any queue or view, is recorded as a verdict, or strands it where nothing reads it → **fail**" (626-628). **Kills "leave the 3 in .rejected/".** The disposition half is not the human's.
The repair half (A/B/C) is a design choice no Adopted rule reaches.
Surviving option: disposition = the 3 must be made adjudicable again (B2.16). Repair: A/B/C, human.

### gt-052ovf — UNDETERMINED
Question/options: retarget the `gc hook --claim` stall repair from Dolt to client pack-loading — A retarget now, B probe first then retarget, C other.
Premise probes: `bd show` on the claim-cluster beads gt-nc6sni, gt-fb7g64, gt-82so12, gt-hu35w1, gt-us8ayq, gt-yycykx, gt-0zrhb6, gt-19s6i2, gt-0jsh5o → all OPEN [measured]. Box rebooted ~22 min before this pass (`uptime`), so no claim-latency measurement was taken; one taken now would not be comparable [measured].
Grounds: diagnostic-direction choice; no rule reaches it. Note: CT2.5 (`POLICY-city.md:242-244`) itself attributes the gt-fb7g64 livelock to the identity mismatch, which is a third causal story beside this brief's and gt-shud5h's. Three competing hypotheses, none reproduced.

### gt-0sm9im — MOOT (a record of a verdict already given)
Question/options: none. The body records Taylor's authorization of `bd dolt push` to tdupu/hecke-dolt and tdupu/jacobi-dolt, and explicitly excludes the other two remotes.
Premise probes: `bd show gt-0sm9im --json` → status open, type decision, labels/metadata null [measured]. Whether the push actually ran: **not verified** (would need a remote fetch in a `~/repos` store; skipped) [unknown].
Grounds: no open question, so nothing to present. The ruling is in the body verbatim. Closing it is recording work (adjudicate-brief, adjudicator = Taylor per the body), not a decision. Execution state is still unknown.

### gt-1mgmgq — DUPLICATE of gt-624ew1
Question/options: same decision, same title, same source bead gt-khj26y.
Premise probes: gt-624ew1 §3 says "This supersedes gt-1mgmgq" (1mgmgq was gate-rejected on form, G9) [measured in body].
Survivor: **gt-624ew1**.

### gt-1tytnk — MOOT (a task, not a decision; handler-level answer measured)
Question/options: none. The body says only "Route status is currently unknown, not broken and not fixed." The title is an instruction to run a probe.
Premise probes:
- `grep -n /preview ~/repos/mathcity/assets/scripts/mctl_dashboard/app.py` → `POST /preview  dry-run an operation. Writes nothing.` (line 18); `MUTATION_ROUTES = ("/preview", "/apply")` (line 450) [measured].
- `pytest tests/mctl/test_dashboard_mutation_safety.py tests/mctl/test_adjudication_form_conditionality.py` → **39 passed**. These drive `dashboard.handle(Request.post("/preview", …))` in-process [measured]. They could have failed.
Grounds: at the handler level the route exists and answers POST. **Not done:** a POST against a live served instance (I did not start a dashboard). A read-only probe settles this; it was never a human decision.

### gt-25ep8l — UNDETERMINED (survivor of the mol-dog-stale-db cluster)
Question/options: stale local `mol-dog-stale-db.formula.toml` tells agents to `rm -rf` inside `~/gt/.dolt-data`. A repair/remove it now, B guard the read path, C diagnose resolution order first.
Premise probes:
- `ls -la ~/gt/.beads/formulas/mol-dog-stale-db*` → `mol-dog-stale-db.formula.toml` (Jun 21, 5981 B) still beside a `mol-dog-stale-db.toml` symlink into the gc pack cache [measured].
- `grep -n 'rm -rf' …formula.toml` → line 111 `cd ~/gt/.dolt-data && rm -rf testdb_* beads_t* …` [measured]. **Premise live and dangerous.**
- The same `.formula.toml` shadow exists in the hecke, agent_skills, mathcity, dupuy_cv and diff_alg_public rig `.beads/formulas/` too [measured by `find`]. The briefs name only `~/gt`, so the blast radius is wider than any of the three briefs states.
- Source beads gt-beukhh, gt-y92fe6, gt-vethd, gt-p1fzn, gt-4feew, gt-fphwj → all OPEN [measured].
Grounds: the only Adopted-document rule about `rm -rf`-class operations is **CT12.4**, marked **(PROPOSED)** (`POLICY-city.md:660`), so it can't be cited. The `~/gt/CLAUDE.md` hard guard is not a policy document. Genuine choice. It is also the most safety-relevant live item in this rig.

### gt-4t2d0y — UNDETERMINED
Question/options: `gc runtime drain-ack` spins when no drain was requested. A fix the wait (gascity), B guard the call in the formula, C accept.
Premise probes: none run. The only reproduction is a live dog run, and I did not execute a formula.
Grounds: repair-shape choice; no rule reaches it.

### gt-5cls5j — MOOT (a record of a verdict already given)
Question/options: none. This is Taylor's architectural directive quoted verbatim.
Premise probes: `grep -n PP1.13 POLICY-POLICY.md` → line 42, codified as **PP1.13 (PROPOSED — direction, not design)** by commit 2294e72 (on `origin/main` [measured]).
Grounds: no open question. The only follow-on human act is adopting PP1.13, which runs through `new-policy-policy` (PP1.4) and is not what this bead asks.

### gt-624ew1 — UNDETERMINED
Question/options: the `.md` brief cache drops `verdict_option`. A fix the write-back, B stop operators reading verdicts from the cache, C both, D fold into the stalled design question.
Premise probes: source bead `gt-khj26y` → OPEN [measured]. `git log --grep verdict_option` → only `eec2dc8` (2026-08-29), which carries the option into the **bead**/dashboard `Verdict`, not the cache frontmatter. That predates the brief, so it is not the fix [measured].
Grounds: **B2.8** (`subdomains/brief-system/POLICY.md:346`, Adopted): "On any disagreement between filesystem and bead store, the bead store wins" (lines 351-352). It points toward bead-canonical reads, but it does not eliminate options cleanly: B2.8a (`:355`) records B2.8's "regenerated" clause as "false as written", and the write-back half falls under **B2.14, a JUDGEMENT RULE** (`:531`). Not derivable without interpretation.

### gt-6rtuox — UNDETERMINED
Question/options: fix `extract_failed_gate()` to recover a gate id from a bare `reason`, and whether to backfill the 2 degraded G0/Unknown records.
Premise probes: `sed -n 104,130p ~/repos/mathcity/assets/scripts/brief-quality-failure-record.py` → the reason-regex still requires `FAIL|BLOCKED`. Last touched 2026-08-16 (`25caa92`). Gap live [measured].
Grounds: P6.1 (`dev/POLICY.md:516`) arguably reaches the "fallback to Unknown" behaviour, but whether an `Unknown` label counts as a "visible signal" is interpretation. The backfill half is a genuine choice.

### gt-6x491h — UNDETERMINED
Question/options: retire the recurring lost-bead rollup orders (A), vs reroute (C) or authorize (D).
Premise probes: `ls ~/repos/mathcity/orders` → `lost-bead-classification-rollup.toml` and `lost-bead-upstream-repair-rollup.toml` still present, last touched 2026-08-20. Escalations gt-onxa2i and gt-0d73xl are OPEN. The upstream question gt-2vv2u0 is CLOSED [measured]. Premise live.
Grounds: retirement is a design choice. B2.3 is about re-presenting a closed brief bead and doesn't reach an order re-deriving a question.

### gt-7s1rwg — UNDETERMINED
Question/options: rig-scoped `no-brainer-candidate-curate` order — A retire, B re-root, C leave.
Premise probes: `orders/no-brainer-candidate-curate.toml` still `scope = "rig"`, condition `find .beads/.gates-candidate-pile … | grep -q .`. The city-scoped sibling exists. Last change 2026-08-20 (`6f2ef61`) [measured]. The file comment says the rig-scoped order is "kept rather than re-scoped" on purpose, which is the B-vs-A tension the brief names.
Grounds: design choice.

### gt-8tdj5a — MOOT (the action is done and verified)
Question/options: none. The record says Taylor authorized the push of `e2e7bf3`, `2294e72` to tdupu/mathcity main.
Premise probes: `git merge-base --is-ancestor e2e7bf3 origin/main` and the same for `2294e72` → both on `origin/main` [measured].
Grounds: pushed and verified. Recording and closing it is bookkeeping.

### gt-9c29t5 — REFUSED_CONTESTED
Question/options: were B2.4/B2.10 written to correct rig-pile drift, or blind to rig piles that already existed? The repair direction depends on the answer.
Premise probes:
- `git log -S'Canonical membership is the bead query'` → present since `7715c4f` (2026-08-10, first commit) [measured]. B2.4 has always defined the pile as a **bead query**, not a directory.
- In gt-w9l481's comment (2026-09-06), `briefs_create --rig mathcity` planned its deposit into `~/gt/mathcity/.beads/briefs/.pile/` [measured in body]. So the canonical typed surface (B2.11) itself writes rig piles.
Grounds: two live readings of **B2.4** (`:296`) / **B2.10** (`:395`): (i) "one pile" means one bead-query membership, and per-rig `.pile` directories are caches, so there is no violation; (ii) `.pile` in B2.10 means the city-root directory, so rig piles are side-piles. The brief itself exists to dispute which reading holds. PP1.7 (`POLICY-POLICY.md:36`) says the text wins over artifacts, but it can't choose between two readings of the text. The skill forbids freezing a reading.

### gt-9o7kzd — UNDETERMINED
Question/options: garbage-collection backstop for `.staging/<slug>/` dirs with no `brief.md` — pick the repair shape.
Premise probes: `ls ~/gt/.beads/briefs/.staging` → still only `gh-38-decisions-track-classifier/` (mtime 2026-08-19). `ls archive/staging` → absent. `formulas/brief-archive-sweep.toml:94-114` is unchanged in shape (`skipped (neither in stack nor pile)`) [measured]. Premise live, and the instance is now 38 days stale.
Grounds: design choice. The gt-m50xwa record says ruling 1 "Resolves … gt-9o7kzd", but a keystone ruling is not citable authority for this skill, and B2.16 (the codified ruling 1) is about gate failures, not brief-less staging dirs.

### gt-asb6od — UNDETERMINED
Question/options: launch-repair-review — A disarm the sling and keep the bookkeeping, B fix idempotency after reproduction, D keep slinging.
Premise probes: `formulas/brief-producer-failure-rollup.toml:188` still runs `gc sling gascity-packs/gc.run-operator …`. gt-t2ztn1 is OPEN [measured].
Grounds: the candidate rule **F7.1** (`POLICY-formulas.md:291`, pre-dispatch assignee check) **is satisfied**: the step checks `assignee` and prints `ALREADY DISPATCHED` (lines 170-175). So F7.1 kills nothing. Genuine choice.

### gt-d8ljdq — DUPLICATE of gt-fbucam
gt-fbucam's body: "raised as brief gt-d8ljdq … REJECTED 2026-09-10T14:20:47Z for … action_block missing on_approve — a SCHEMA bounce … This brief re-files it" [measured]. Survivor: **gt-fbucam**.

### gt-e8sh8h — UNDETERMINED (premise partly stale)
Question/options: disposition of already-minted, unrunnable `brief-shuffle-fast-drain` order-runs. A void them in bulk via gt-6vp6b1, others.
Premise probes:
- `bd show gt-79v0j9` → **CLOSED 2026-09-22T22:28:30Z**, reason "Drain executed successfully … Brief root existed as of Sep 20" [measured]. The flagship pinned run is gone.
- `bd list --status open,in_progress` filtered on fast-drain → **gt-kbxweq** (created 2026-08-28, label `order-run:brief-shuffle-fast-drain`, no `:rig:` suffix; blocker gt-d16kg3 OPEN) and gt-7rtk6f (city order) remain in the hq store. gt-6vp6b1 is OPEN [measured]. Other rigs' stores were not scanned.
Grounds: at least one unrunnable run survives, so the question stands, but at a much smaller scale than filed. A disposition semantics that Taylor explicitly reserved is a human decision.

### gt-ej3hwk — UNDETERMINED
Question/options: encode the `feedback_required: false` exclusion in both step descriptions (A), at the write point only (B), reproduce first (C), or leave alone (D).
Premise probes: `grep feedback_required formulas/brief-producer-failure-record.toml` → no hit. The field is honoured in code (`brief-quality-failure-record.py:161`) [measured]. The documentation gap is live and latent.
Grounds: no rule reaches step-description completeness to the point of eliminating options.

### gt-fbucam — UNDETERMINED
Question/options: three stale per-rig-only revise verdicts (gsp-n898, he-6mi84, gsp-oyq4e). A terminalize as overtaken-by-events, B re-deposit, C per-slug mix, D code fix only.
Premise probes: `sed -n 188,198p ~/repos/mathcity/formulas/revise-return.toml` → line 194 still `rec="$ROOT/decisions/$slug.toml"`, so the three still cannot settle. gt-7ybdht is OPEN [measured].
Grounds: BP4.5 ("Doubt defers", `POLICY-beads.md:106`) was considered and **does not reach**: its trigger is a reaper sweep closing beads, not a human disposition of ledger lines. gt-hmj8ha §3 flags that A's "already hand-carried" premise is **[inferred, never verified]**. A genuine decision.

### gt-ftq6wn — DUPLICATE of gt-pnq9im
Question/options: "repair the sweep, or redefine 'drained'?" The same B2.15-archiving decision as gt-pnq9im, which carries the enumerated A-D options and the source bead gt-x6i7lb. The mathcity-rig brief **mc-up5vd** asks it a third time.
Premise probes: see gt-pnq9im. `.adjudicated-archive/` newest entry is still `261-shadowed-formula-copy-brief.md`, 2026-08-28 [measured].
Survivor: **gt-pnq9im**. The "redefine drained" branch is an amendment of Adopted B2.15 (`:569`), and B2.15's own text says it "was decided, not inherited" (owner decision `mc-g4k`).

### gt-g8q7tq — UNDETERMINED (policy amendment)
Question/options: amend P1.6 to accept ldflags provenance where `-buildvcs=false` is deliberate.
Premise probes: `~/repos/gascity/Makefile:111` → `go build -buildvcs=false …` [measured]. `dev/POLICY.md:74-76` still requires `vcs.revision` equal to HEAD and `vcs.modified=false` [measured]. Premise live.
Grounds: amending a rule runs through `new-X-policy` (PP1.4) and needs the owner's adoption. Not derivable.

### gt-h99fc9 — UNDETERMINED
Question/options: retire or update the obsolete Codex browser-use 0.1.0-alpha2 plugin after the macOS revoked-certificate block.
Premise probes: none. This is local installed software and was out of scope for reads.
Grounds: no rule reaches it. The brief's own §1 says it is not approval to change installed software.

### gt-hgwu3m — MOOT (the action is done and verified)
Question/options: none. The record says Taylor authorized the batch push of mathcity `438845a`, `0c4d19e` and beads `eabeb78b1`.
Premise probes: `merge-base --is-ancestor 438845a|0c4d19e origin/main` → both on main. `git ls-remote https://github.com/tdupu/beads.git refs/heads/main` → `eabeb78b1e7c9…` [measured].
Grounds: pushed and verified. Bookkeeping only.

### gt-hmj8ha — UNDETERMINED
Question/options: fix revise-return line 194, and in what order relative to gt-fbucam. A fix now, B fix after gt-fbucam is ruled, C fix with a staleness guard, D revert to a global-only scan.
Premise probes: line 194 unchanged. gt-7ybdht OPEN (P1). The bead now sits in `.pile/.rejected/gt-hmj8ha/` while the bead is still OPEN [measured].
Grounds: **P6.1** (`dev/POLICY.md:516`, "dropping work with no log → **fail**", lines 523-524) kills leaving the bug in place, but none of A-D is that. A vs B is ordering. It is not *pure* sequencing, though, because landing first auto-re-deposits three stale verdicts, which is gt-fbucam's substance. Once gt-fbucam is ruled, the A/B distinction collapses into coordinator sequencing. **Recommend the Mayor treat this as dependent on gt-fbucam, not as a separate human decision.** C and D stay human.

### gt-k888o0 — DUPLICATE of gt-25ep8l
Same defect (stale `mol-dog-stale-db.formula.toml` with `rm -rf` on `.dolt-data`, dead `gt` CLI), same fix pass. Survivor: **gt-25ep8l**, the newest and full-form, source bead gt-beukhh. Its four source beads (gt-vethd, gt-p1fzn, gt-4feew, gt-fphwj) are OPEN [measured].

### gt-kzca38 — MOOT (a record of a verdict already given)
Question/options: none. The body records Taylor's ruling PROMOTE, verbatim "yes, we can. If there are enough tests we can approve such a thing."
Grounds: already decided. Implementing the category is follow-on work, not a question for Taylor.

### gt-m50xwa — UNDETERMINED (record with one live residual)
Question/options: a record of four keystone rulings. Rulings 1 and 3 are codified as B2.16 and P1.22, ruling 2 as CT2.5, and ruling 4 is explicitly unruled.
Premise probes: the bead's 2026-09-16 comment (QUIMBY 70) argues that ruling 2 as recorded ("Settled: assignee is the SESSION ID") over-specifies the utterance ("I would say session id. It really doesn't matter as long as you are consistent"). It records that two derivations citing it (gs-b9ja, mc-cns3c) were refuted and withdrawn, and names the unstick: "Taylor picks the assignee spelling as a DECISION rather than a preference" [measured in body].
Grounds: that residual question has no rule to derive from; it is the question itself. The record parts need no decision.

### gt-myrjav — UNDETERMINED (policy narrows to 2 of 4)
Question/options: the record-signals check passes while scanning nothing. A fix both, B resolution only, C failure mode only, D neither.
Premise probes: `assets/scripts/checks/brief-quality-failure-record-backfill.sh` → `ROOT="${BRIEF_ROOT:-.beads/briefs}"`, cwd-relative. Last change 2026-08-16 [measured]. Premise live.
Grounds: **P6.2** (`dev/POLICY.md:546`, Adopted): "(a) a **scan whose operand may not / resolve**, where an empty result is read as "no violations" — a cwd-relative / `find`/`grep`/`ls` in a script whose working directory is not guaranteed" (554-556) and "Fail: a check whose passing state is indistinguishable from "could not / evaluate"" (568-569).
- **Kills D.** The status quo is exactly shape (a).
- **Kills B.** Resolution alone leaves a missing root still reporting exit 0, a passing state indistinguishable from "could not evaluate".
- A and C both satisfy P6.2. C alone leaves the step failing on every run, and no Adopted rule forbids that.
Surviving options: A, C. Human picks, with the policy narrowing stated.

### gt-n9271k — MOOT
Question/options: what disposition for the pinned, unrunnable gt-79v0j9?
Premise probes: `bd show gt-79v0j9 --json` → **CLOSED 2026-09-22T22:28:30Z**, close_reason "Drain executed successfully 2026-09-22: exit 0 … Brief root existed as of Sep 20" [measured].
Grounds: the bead the question is about no longer exists in the state the question assumes. Nothing left to dispose of.

### gt-nbh1qv — MOOT (record: one-pass delegation anchor)
Question/options: none. This is the anchor for six verdicts recorded under Taylor's one-pass delegation of 2026-09-07.
Grounds: an anchor, not a question. The pass was single-use (per the body). Closing it doesn't break citations to it.

### gt-o6e12s — MOOT in its options, but raises a possible data loss — ESCALATE
Question/options: where the 1.6 MB `gascity-hq-strays-2026-09-06.bundle` should live durably. A commit to tdupu/gascity `archive/`, B …, C off-box backup, D A+B.
Premise probes:
- `git ls-remote https://github.com/tdupu/gascity-dolt.git` → 4 refs only (`HEAD`, `refs/dolt/data`, `__dolt_remote_info__`, `main`). The 7 strays are deleted from the remote, as the brief says [measured].
- `find /private/tmp ~/gt ~/repos ~/.claude -name gascity-hq-strays-2026-09-06.bundle` → **no hit**. `mdfind -name gascity-hq-strays` → **no hit** [measured]. A broader `find ~ -name '*strays*.bundle'` (excluding `~/Library`), plus any 1-3 MB `*.bundle` under `~`, → **no hit** [measured].
- `uptime` → up 22 min, so the box rebooted today. `/private/tmp/claude-501/` holds only today's session directories [measured]. The Sep-6 session scratchpad the brief names is gone [inferred: macOS clears /private/tmp on boot].
- The unique blob `5c5fa8ba` (DATA/sigma18/label.txt) is not in `~/repos/hecke`, `~/gt/hecke` or `~/repos/gascity` object stores [measured].
Grounds: the brief's own §1 warned: "If it is cleaned up before it is moved, the salvage is silently undone and the one unique artifact is gone for good." All four destination options assume a bundle that could not be found. The real question is now "is there any surviving copy (off-box backup, another session's dir)?", and that is a recovery/incident question, not this brief's question. **This is the one item in hq that looks on fire.**

### gt-ojaijt — UNDETERMINED
Question/options: where fleet Dolt escalations go now that `gc mail send mayor` resolves to nothing. A restore a mayor session, B route to human, C resolver fallback mayor→human.
Premise probes: `gc session list | grep -i mayor` → no mayor session (rc=1) [measured]. `~/gt/CLAUDE.md` still prescribes `gc mail send mayor …` [measured]. I did not send mail (mutation), so "unknown recipient" was not re-observed [not probed].
Grounds: routing *design*, not staffing; no rule reaches it.

### gt-p581kw — UNDETERMINED
Question/options: leaked pytest `dolt sql-server` processes. A widen the reaper allowlist, B fix the test teardown, C both, D neither.
Premise probes: `pgrep -fl 'dolt sql-server'` → only 2 servers, neither under `pytest-of-*` [measured]. That is because of today's reboot, not a fix [inferred]. `test_a_pinned_city_dashboard_still_shows_no_switcher` is unchanged since 2026-08-28 (`967b0f2`) [measured]. Source unchanged.
Grounds: option A widens what an unattended process may kill, which is a safety-authority choice. No citable rule (CT12.4 is PROPOSED).

### gt-pnq9im — UNDETERMINED (premise partly stale; C and D dead by measurement)
Question/options: A build the archiver + backfill `brief_bead` into the stack index rows, B archiver only, C keep archiving by hand, D defer until the pile-root question is settled.
Premise probes:
- `git show 900e76a` → "mctl: add the brief_archive effect -- the move mctl could not do (#95, mc-up5vd)". The message records "Owner decision 2026-09-10: build it in mctl (option A)". On `origin/main` [measured]. **The "component has never existed" premise is dead.**
- `ls -lt ~/gt/.beads/briefs/.adjudicated-archive | head` → newest entry is still 2026-08-28 [measured]. The effect exists but has not been applied to the live city stack.
- `stack/.index.jsonl` → 101 rows, **0 with `brief_bead`** [measured]. The backfill half has not been done.
- gt-x6i7lb OPEN, mc-up5vd OPEN, GH tdupu/mathcity#95 OPEN [measured].
Grounds: by measurement, C and D are overtaken: the owner chose to build, and it is built. A vs B (backfill or not) is still open and no rule decides it. **Also: applying the built archive effect to the live stack is execution, not a decision** (B2.15 `:569` already requires "Both halves, or neither").

### gt-qwdf3y — UNDETERMINED (symptom not reproduced in this probe)
Question/options: `gc dolt status` reports a live server as "not running". Fix the command, mark it untrusted in the runbook, or both.
Premise probes: `gc dolt status` → `Dolt server: running (managed, 127.0.0.1:58506)` while `pgrep` shows the managed server pid 1693 live [measured]. It reported correctly this time. One correct reading can't tell "fixed" from "intermittent". gascity `2e101dbae` (2026-09-08, after the brief), "probe the alternate managed-Dolt port during recovery", is a plausible fix [inferred, not verified]. gt-x4uiyq is OPEN.
Grounds: recommend re-probing before presenting. If it cannot be reproduced, this becomes MOOT.

### gt-s72c2a — UNDETERMINED (malformed: no option set)
Question/options: none enumerable. The body is two lines ("3 reopens + 1 gate-disposal never ran; 10 carrier beads did…"), with no bead IDs, no options and no evidence.
Grounds: the skill stops at step 1 when options can't be enumerated. The brief needs its evidence restored before anyone can decide or derive anything. This is not a policy gap.

### gt-shud5h — UNDETERMINED
Question/options: `gc convoy control` dispatchers burn CPU while idle. A run the stop-and-measure probe, B/C accept the load or stop tracking.
Premise probes: `pgrep -fl 'convoy control'` → none running; box up 22 min; load average 6.5-7.4 [measured]. The condition described is not currently present, so it can't be assessed now.
Grounds: the probe stops dispatchers, which is not read-only. It overlaps the gt-052ovf claim-latency cluster; the Mayor may want to fold both into one probe decision.

### gt-tv66gp — UNDETERMINED (instance stale)
Question/options: how the `.staging` rescue sweep should decide claim ownership (A key on the claiming step bead, …), and whether gt-hmj8ha is recovered now.
Premise probes: `ls ~/gt/.beads/briefs/.staging` → gt-hmj8ha is **no longer there**. It is in `.pile/.rejected/gt-hmj8ha/` with the bead OPEN and in this pending list [measured]. The "recover gt-hmj8ha now" half is overtaken.
Grounds: the ownership-signal design half is a genuine choice.

### gt-vvl33s — UNDETERMINED (policy amendment)
Question/options: amend P6.3 so a deadline handler must terminate what it stopped waiting on.
Premise probes: `dev/POLICY.md:594-615` (P6.3) still governs reporting only; `grep -n terminat` finds no termination clause in P6.3 [measured]. Premise live.
Grounds: an amendment is the owner's (PP1.4). Body is two lines; no option set beyond adopt/decline.

### gt-w126z9 — DUPLICATE of gt-25ep8l
The same stale-formula `rm -rf` defect. This one is the oldest (2026-08-29) and names consolidation of 13 dog beads into gt-y92fe6 (OPEN). Survivor: **gt-25ep8l**. The consolidation sub-question should be folded into it as a note; it is bookkeeping (duplicate beads, BP4.2(c)), not a human decision.

### gt-w9l481 — UNDETERMINED (instance stale)
Question/options: may a brief-operator pool member close a step bead held by a peer whose lease expired, and should `.staging` → disposition get its own guard?
Premise probes: workflow root `gt-wwvw7t` → **CLOSED 2026-09-06T17:21:24Z**, 20 minutes after this brief was deposited [measured]. The pinning incident resolved itself. gt-arm75u is still OPEN.
Grounds: F7.1 (`POLICY-formulas.md:291`) covers stale-claim checks before *dispatch*, not closing a peer's step bead. It doesn't reach. The general permission question is genuine.

### gt-xd161g — UNDETERMINED (one half is policy-derived)
Question/options: hecke brief rejections are all schema/gate failures. Fix the producer, or relax the gate?
Premise probes: `ls ~/gt/hecke/.beads/briefs/.pile/.rejected` → **36 dirs**, and every `rejection.*` reason is mechanical (missing gate G5/G2/G8/G17, G9 line form, missing action_block/on_approve, frontmatter, provenance). There is still no `stack/` [measured]. The premise has **worsened**: 8/8 → 36/36. The list includes he-gdiujl, which the 2026-09-25 pass DERIVED as "recover into the single pile".
Grounds: **B2.16** (`brief-system/POLICY.md:606`) makes the *current* handling a failure under either option. A mechanically rejected brief "remains adjudicable" and "MUST NOT" be removed from "any pile, index, queue, view, or presentation surface" (lines 610-611). So returning the 36 to adjudicability is derived, not a choice. Producer-vs-gate is not determined: B2.16 calls the rejection a "defect signal about the PRODUCER" but does not forbid correcting a wrong gate, and gt-024lxi shows gates can be wrong.
Surviving option: the non-removal half is derived. Producer vs gate is human, or case by case.

### gt-y650td — MOOT (record: one-session delegation anchor)
Question/options: none. This is the anchor for QUIMBY 69's overnight delegation of 2026-09-10/11. The body scopes it to "one session, this one".
Grounds: the session has ended, and it is an anchor, not a question.

### gt-ycps03 — REFUSED_CONTESTED
Question/options: `bd close` fails when the assignee is a session ID and the actor is a session name. (1) record the assignee as the session name, (2) bd accepts either form, (3) formulas export `BEADS_ACTOR=$GC_SESSION_ID`.
Premise probes: gt-c18u91 OPEN (P1). gt-79v0j9's close reason (2026-09-22) says "--force only bridges the session-id/session-name actor mismatch", so the mismatch is still live [measured].
Grounds: **CT2.5** (`POLICY-city.md:230`, Adopted, not PROPOSED) reads as deciding it: "`assignee` is the **session / ID**, in one canonical form used by **every** writer, comparator, and / verifier in the claim path … A tolerant compare is / permitted **only during migration**" (230-234). Read literally it kills (1) and permanent (2), leaving (3). **But that reading is disputed on record.** The gt-m50xwa comment of 2026-09-16 argues the session-ID choice CT2.5 encodes was a preference ("I would say session id. It really doesn't matter as long as you are consistent"), and that two derivations citing it (gs-b9ja, mc-cns3c) were refuted and withdrawn. It also argues consistency "arguably favours the option those derivations ELIMINATED", i.e. option (1) here. There is a second open question too: whether the close path counts as the "claim path". Under the skill's step 6 this is REFUSED_CONTESTED. **It unblocks as soon as Taylor makes the spelling a decision** (gt-m50xwa residual). One answer settles this brief and the rest of the identity family.

---

## Tally

| Outcome | Count | IDs |
|---|---|---|
| MOOT | 10 | gt-n9271k (subject bead closed); gt-8tdj5a, gt-hgwu3m (pushes verified); gt-0sm9im†, gt-5cls5j†, gt-kzca38†, gt-nbh1qv†, gt-y650td† (records of verdicts already given); gt-1tytnk (task; handler-level probe passes); gt-o6e12s‡ |
| DUPLICATE | 5 | gt-1mgmgq→gt-624ew1 · gt-d8ljdq→gt-fbucam · gt-ftq6wn→gt-pnq9im · gt-k888o0→gt-25ep8l · gt-w126z9→gt-25ep8l |
| REFUSED_CONTESTED | 2 | gt-9c29t5 (two live readings of B2.4/B2.10) · gt-ycps03 (CT2.5 basis disputed on gt-m50xwa) |
| UNDETERMINED | 28 | gt-024lxi\*, 052ovf, 25ep8l, 4t2d0y, 624ew1, 6rtuox, 6x491h, 7s1rwg, 9o7kzd, asb6od, e8sh8h, ej3hwk, fbucam, g8q7tq, h99fc9, hmj8ha, m50xwa, myrjav\*, ojaijt, p581kw, pnq9im, qwdf3y, s72c2a, shud5h, tv66gp, vvl33s, w9l481, xd161g\* |
| DERIVED | 0 | — |
| DERIVED-OUT | 0 | — (gt-hmj8ha's ordering half becomes coordinator sequencing once gt-fbucam is ruled) |
| CONFLICT | 0 | — |
| REFUSED_JUDGEMENT | 0 | — (B2.14 reaches half of gt-624ew1; noted there) |
| **Total** | **45** | |

† a record of a verdict Taylor already gave: open `type=decision` bead, no option set. It sits in the B2.4 pile only because it is open. Closing it is adjudicate-brief bookkeeping with Taylor as the adjudicator, named in the body.
‡ its options are dead because the object cannot be found anywhere under `~`. Escalated as a possible loss, not "done".
\* partly derived: gt-024lxi and gt-xd161g (B2.16 non-removal half); gt-myrjav (P6.2 kills B and D, leaving A or C).

UNDETERMINED with a stale or partly stale premise: gt-e8sh8h (gt-79v0j9 closed), gt-pnq9im (archiver built; options C and D dead), gt-tv66gp and gt-w9l481 (their instances resolved), gt-qwdf3y (symptom not reproduced once).

## What the pass shows

- **Seven rules did the work:** B2.16, P6.2, P6.1, B2.8, CT2.5 (refused as contested), F7.1 (checked; kills nothing), BP4.5 (checked; does not reach). No brief is fully DERIVED. Three are partly derived, and those halves can leave the human queue now.
- **Seven items are records, not questions** (gt-0sm9im, 5cls5j, kzca38, nbh1qv, y650td, 8tdj5a, hgwu3m), and clog the pile only because they stay open. The Mayor can move all seven out through recording without spending a Taylor decision.
- **One unblocking decision stands out:** make the session-ID vs session-name spelling a *decision* (gt-m50xwa residual). That unfreezes gt-ycps03 and the worker-identity family.
- **Fire:** gt-o6e12s. The only copy of 7 deliberately deleted refs appears to have lived in a now-wiped /private/tmp scratchpad.
- **Danger, still live:** a Jun-21 `mol-dog-stale-db.formula.toml` with `rm -rf` inside `~/gt/.dolt-data` is on disk in `~/gt` **and in five rig `.beads/formulas/` dirs**. The three briefs about it name only `~/gt`.

[autogenerated by Claude Opus 5.5 (Claude Code) on 2026-09-26]
