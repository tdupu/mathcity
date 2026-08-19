# Malformed-brief triage — all 74, live city, 2026-08-19

**Status:** analysis only. **Nothing in the bead store was mutated to produce
this document.** Every `bd` invocation below was a read (`bd list --readonly`,
`bd show`, `bd dep list`, `mctl briefs list|show|options|doctor|validate`).
The repair commands in §5 are *proposed*; none was run.

**Scope:** the 74 briefs mctl reports as `decision_state = malformed` across
`hecke`, `gascity-packs`, and `agent_skills`.

---

## 0. The premise of this investigation was wrong, and that is the finding

The task was framed as: *74 briefs are malformed, the dominant diagnostic is
`MBRF004` (no source dependency), so 40% of the queue is stuck on a missing
source link.*

**`MBRF004` is not why any of the 74 are malformed.** The two facts are
independent, and conflating them would have produced a 74-bead bulk `bd dep
add` that repaired nothing.

`assets/scripts/mctl_core/briefs.py:610-616` is the whole state machine:

```python
def _decision_state(bead: Bead) -> str:
    status = bead.status.lower()
    if status in {"closed", "done"}:
        return "adjudicated" if _has_verdict(bead) else "malformed"
    if status == "deferred" or _defer_until(bead):
        return "deferred"
    return "pending"
```

`source_dependencies` is not consulted. `malformed` means exactly:

> **the bead is `closed`, and `_verdict()` found no verdict field.**

Measured against the live stores, this holds without exception:

| | closed | open |
|---|---|---|
| `malformed` | **74** | 0 |
| `adjudicated` | 7 | 0 |
| `pending` | 0 | 104 |

and the diagnostic counts confirm it — `MBRF005` ("Closed brief bead has no
recorded verdict", B2.2) fires **43 + 30 + 1 = 74** times, exactly matching the
malformed population, while `MBRF004` fires **82 + 60 + 4 = 146** times across
*both* malformed and pending briefs.

So the real question is not "where did the source link go" but **"where did the
verdict go"** — and the answer is that it never went anywhere. It is sitting in
`close_reason` on all 74 of them.

`MBRF004` is separately real and separately serious — it blocks adjudication on
**146 of 185** briefs, including 88 that are `pending` and otherwise healthy.
It is analysed on its own terms in §4. The two must not be merged.

---

## 1. Headline counts

### 1.1 Population

| rig | `type=decision` beads | adjudicated | pending | **malformed** |
|---|---|---|---|---|
| hecke | 114 | 7 | 64 | **43** |
| gascity-packs | 66 | 0 | 36 | **30** |
| agent_skills | 5 | 0 | 4 | **1** |
| **total** | **185** | **7** | **104** | **74** |

### 1.2 The 74, by class

Classes are named for *why the verdict is not machine-readable*, which is the
actual malformed cause. The task's five suggested classes were written for the
source-link question; they are applied to that question in §4 instead, and the
mapping is noted per class below.

| class | what it is | n | hecke | gsp | as | task-class analogue |
|---|---|---|---|---|---|---|
| **C1** | **Never was a brief** — 25 `authorize-git-operation` push/merge/delete receipts + 3 policy adoptions/ratifications | **28** | 5 | 22 | 1 | class 4 |
| **C2** | Verdict is in `close_reason`, in a parseable form | **21** | 20 | 1 | 0 | class 3 |
| **C3** | Verdict is in `notes`, in the canonical `VERDICT: … \| AUTHORIZER: …` shape | **6** | 2 | 4 | 0 | class 3 |
| **C4** | Superseded / cancelled — decision lives on a successor bead | **6** | 6 | 0 | 0 | class 5 |
| **C5** | `close_reason` is a narrative execution report, not a verdict | **13** | 10 | 3 | 0 | — (new) |
| | **total** | **74** | 43 | 30 | 1 | |

### 1.3 A cross-cutting count that matters more than the classes

**39 of the 74 (53%) are not briefs at all.** That is C1's 28 authorization
receipts plus 11 standalone decision beads (policy ratifications, mathematical
conventions, engineering decisions) that were never routed through the brief
pipeline. B2.1's own glossary says so explicitly:

> Decision beads created for OTHER purposes (push authorizations, kill-switch
> engagement/release, non-brief adjudications) remain their own standalone
> beads; only the brief/decision-bead pairing is collapsed.
> — `subdomains/brief-system/POLICY.md`, Definitions

mctl has no discriminator. `Bead.is_brief` (`beads.py:52-54`) is:

```python
    @property
    def is_brief(self) -> bool:
        return self.issue_type == "decision"
```

Every `type=decision` bead in the rig is a brief as far as mctl is concerned.
The 11 non-receipt standalone decisions are:

`he-hljdhx`, `he-3a4rsi`, `he-qbrp`, `he-3309`, `he-yoe2`, `he-vqah`,
`he-tgiizb`, `he-sx3o`, `gsp-mnfj`, `gsp-b7ov`, `gsp-pgt`.

---

## 2. Do any of the 74 turn out not to be malformed?

Three different answers, depending on which document you hold as authority.
This is a policy call for Taylor, not one an implementer should make.

1. **By mctl's implemented rule** (`_verdict()` finds no field): all 74 are
   genuinely malformed. The field really is absent.
2. **By B2.2's text** — *"adjudicated ⇔ the brief bead carries recorded verdict
   fields and is closed"* — **27 of the 74 (C2 + C3) carry a recorded verdict**
   in a bd-native field that a human reads instantly. Whether `close_reason`
   and `notes` count as "recorded verdict fields" is undecided. B2.2 also
   requires verdict + rationale + authorizer + date; C3's six carry all four,
   C2's twenty-one carry verdict and rationale but not always authorizer/date.
3. **By B2.1's definition of a brief**: **39 of the 74 are outside the brief
   population entirely**, so "malformed brief" is a category error for them.

The most defensible reading: **at most 35 of the 74 are malformed briefs**, and
of those 35, 27 have a legible human verdict that was simply written to the
wrong field.

---

## 3. The full table — all 74

`bead shape` distinguishes real briefs from beads mctl merely swept in.
`source recoverable from` is the independent `MBRF004` axis (§4); `dep-edge`
means the bead has an outgoing dependency and does *not* raise `MBRF004`.

| # | id | rig | title (truncated) | class | bead shape | source recoverable from | close_reason (truncated) |
|---|---|---|---|---|---|---|---|
| 1 | `as-coq0` | agent_skills | Taylor authorized git PUSH: agent-skills origin/main (3844 | **C1** | authorization-record | — | Push executed and verified: origin/main at 3844867. |
| 2 | `gsp-136z` | gascity-packs | Taylor authorized git PUSH x2: 10-skill mathcity adoption  | **C1** | authorization-record | — | Push authorization receipt — action completed; closing complet |
| 3 | `gsp-16js` | gascity-packs | Taylor authorized git PUSH: gascity-packs->fork + agent-sk | **C1** | authorization-record | — | Push authorization receipt — action completed; closing complet |
| 4 | `gsp-317y` | gascity-packs | Taylor authorized git PUSH: fork/main (mayor-math + prime- | **C1** | authorization-record | — | Push executed: b695312 to fork/main, gitleaks clean |
| 5 | `gsp-558u` | gascity-packs | Taylor authorized: gsp dolt-init (item #3) — 2026-07-11 | **C1** | authorization-record | — | Permanently blocked: Taylor has no DoltHub account; bd backup  |
| 6 | `gsp-6iks` | gascity-packs | Taylor authorized git PUSH + dolt push: gascity-packs batc | **C1** | authorization-record | — | Published: git 96034d2 (fixes) + 2f8b418 (PR204 merge) on fork |
| 7 | `gsp-84ca` | gascity-packs | Taylor authorized PUSH: gascity-packs fork/main (d06e042)  | **C1** | authorization-record | — | Push authorization receipt — action completed; closing complet |
| 8 | `gsp-8qvk` | gascity-packs | Taylor authorized git PUSH: gascity-packs fork/main (0f342 | **C1** | authorization-record | description text | Both pushes executed and verified: fork/main at 158463f, agent |
| 9 | `gsp-afvh` | gascity-packs | Taylor authorized (via Mayor) dolt+git PUSH: gascity-packs | **C1** | authorization-record | — | Executed: dolt refs/dolt/data 988428e6, git a7adcb4 to fork/ma |
| 10 | `gsp-cd8g` | gascity-packs | Taylor authorized commit-city wave: gsp 2bcdf0f (LMFDB pip | **C1** | authorization-record | — | Push authorization receipt — action completed; closing complet |
| 11 | `gsp-edafo` | gascity-packs | Taylor authorized git push: origin/main gascity-packs (che | **C1** | authorization-record | — | Closed |
| 12 | `gsp-hjbz` | gascity-packs | Taylor adopted brief-system POLICY.md self-contained rewri | **C1** | authorization-record | description text | Decision recorded; adoption already in force (POLICY.md header |
| 13 | `gsp-hl4t` | gascity-packs | Taylor authorized git PUSH x2: Magma dev-loop adoption (gs | **C1** | authorization-record | — | Push authorization receipt — action completed; closing complet |
| 14 | `gsp-k6y2` | gascity-packs | Taylor authorized build remediation: declare gascity .clau | **C1** | authorization-record | — | Push authorization receipt — action completed; closing complet |
| 15 | `gsp-l1pn` | gascity-packs | Taylor authorized PUSH: gascity-packs fork/main (9a049bd)  | **C1** | authorization-record | — | Push authorization receipt — action completed; closing complet |
| 16 | `gsp-mjv4` | gascity-packs | Taylor authorized git PUSH x2: gascity-packs fork main (d0 | **C1** | authorization-record | description text | Both pushes executed and verified: fork/main at 0800113, agent |
| 17 | `gsp-nx3v` | gascity-packs | Taylor authorized git PUSH x2: README-fork output (gsp 17f | **C1** | authorization-record | — | Push authorization receipt — action completed; closing complet |
| 18 | `gsp-pc0dqg` | gascity-packs | Taylor authorized git MERGE+PUSH: gascity-packs filter E2E | **C1** | authorization-record | — | Authorized merge/push completed: codex/filter-e2e-integration  |
| 19 | `gsp-pxcu` | gascity-packs | Taylor adopted 4 policy amendments: PP1.10 + PP6.3 fix + P | **C1** | authorization-record | description text | All four amendments applied: PP1.10 + PP6.3 fix + PP1.8 concis |
| 20 | `gsp-u4f6` | gascity-packs | Taylor authorized git PUSH: gascity-packs fork main (190c5 | **C1** | authorization-record | title text | Push executed and verified: fork/main at 190c559. |
| 21 | `gsp-vf5w` | gascity-packs | Taylor authorized git PUSH: fork/main gascity-packs (3e2b8 | **C1** | authorization-record | — | Push executed and verified: fork/main at a39567b |
| 22 | `gsp-vp9j` | gascity-packs | Taylor authorized git PUSH x3 (claude-commit-city): rig gs | **C1** | authorization-record | — | Push authorization receipt — action completed; closing complet |
| 23 | `gsp-xo48` | gascity-packs | Taylor authorized git PUSH: gascity-packs fork/main (3c154 | **C1** | authorization-record | — | Push executed and verified: fork/main at 3bc074d. |
| 24 | `he-am9lk` | hecke | Taylor authorized git PUSH: tdupu/hecke master c23c404..03 | **C1** | authorization-record | title text | Bookkeeping correction: BART decision beads belong in the gsp  |
| 25 | `he-hjw2y` | hecke | Taylor authorized git push: origin/master (d637d3b) | **C1** | authorization-record | — | Push authorization record — action already completed; bulk tri |
| 26 | `he-knox` | hecke | Taylor ratified W2.4 lineage audit: he-9czp canonical; he- | **C1** | authorization-record | title text | Taylor ratified W2.4 lineage audit recorded; decision complete |
| 27 | `he-mgdb9` | hecke | Taylor authorized git PUSH: origin/master (57a1ca1..f7bb1d | **C1** | authorization-record | — | Push authorization record — action already completed; bulk tri |
| 28 | `he-tz158` | hecke | Taylor authorized git DELETE: 12 remote branches on tdupu/ | **C1** | authorization-record | — | Executed: 12 branches + 1 shadow tag deleted from tdupu/hecke. |
| 29 | `gsp-mnfj` | gascity-packs | POLICY [mayor]: default SLING, fork only for in-session ou | **C2** | plain-decision-bead | description text | approve: fork-vs-sling rule codified; Taylor approved 2026-07- |
| 30 | `he-02yq` | hecke | [brief-record] he-7fmw cohort A (Hecke theory + algebra st | **C2** | brief-shaped-title | dep-edge | legacy verdict backfill: PER-ITEM-VERBATIM-PASSED-TO-MAYOR-FOR |
| 31 | `he-0gq3` | hecke | [brief-record] he-1iru — verdict GREENLIGHT (iter-3 mechan | **C2** | brief-shaped-title | metadata.source_bead/brief_for | legacy verdict backfill: A-GREENLIGHT-WITH-Q-DEFAULTS-AND-ENVE |
| 32 | `he-1j77` | hecke | [brief-record] he-us1q Sigma18 cohort dispatch — verdict D | **C2** | brief-shaped-title | dep-edge | legacy verdict backfill: B-first-wave-on-UPF-with-artifacts-po |
| 33 | `he-2jp5` | hecke | [brief-record] he-hsoc check-latex-umbrella — verdict DISP | **C2** | brief-shaped-title | metadata.brief_path filename | legacy verdict backfill: REVERSE-B-TO-A-DUE-TO-CHAIN-COLLAPSE  |
| 34 | `he-35x2` | hecke | [brief-record] he-p4x5 — verdict INVESTIGATE | **C2** | brief-shaped-title | title text | Taylor verdict 2026-07-22: APPROVE (B) — theoretical proof via |
| 35 | `he-7owd` | hecke | [brief-record] cohort C — verdict APPROVE-WITH-DISPOSITION | **C2** | brief-shaped-title | metadata.source_bead/brief_for | legacy verdict backfill: PER-ITEM-VERBATIM-PASSED-INITIAL-REAC |
| 36 | `he-8a4r` | hecke | [brief-record] he-rg5r impl-dispatch — verdict DISPATCH-NO | **C2** | brief-shaped-title | dep-edge | legacy verdict backfill: A-dispatch-overnight-parallel per dec |
| 37 | `he-ckjf` | hecke | [brief-record] he-l6ak — cohort G (12 items) — verdict PEN | **C2** | brief-shaped-title | dep-edge | legacy verdict backfill: PER-ITEM-VERBATIM-WITH-HE-CE4-CRITICA |
| 38 | `he-f1lt` | hecke | [brief-record] hecke#232 worker-parallelism — verdict A (C | **C2** | brief-shaped-title | dep-edge | legacy verdict backfill: A-CLOSE-DONE per decisions.jsonl 2026 |
| 39 | `he-fgsf` | hecke | [brief-record] he-btnx halfspace-master-merge — verdict DI | **C2** | brief-shaped-title | metadata.brief_path filename | legacy verdict backfill: A-DISPATCH-NOW-WITH-FOCUSED-TESTS-AUT |
| 40 | `he-hbyr` | hecke | [brief-record] hecke#308 conductor REDO — verdict pending  | **C2** | brief-shaped-title | dep-edge | legacy verdict backfill: A (implicit approval) per decisions.j |
| 41 | `he-jl8z` | hecke | [brief-record] he-zqhu sandbox-runner-impl — verdict DISPA | **C2** | brief-shaped-title | metadata.brief_path filename | legacy verdict backfill: E-REJECT-AND-SUPERSEDE-SPEC per decis |
| 42 | `he-l88x` | hecke | [brief-record] he-qlv6 cohort B (7 GH issues, cohomology + | **C2** | brief-shaped-title | metadata.source_bead/brief_for | legacy verdict backfill: PER-ITEM-SPLIT-VERBATIM-PASSED-TO-MAY |
| 43 | `he-ldav4g` | hecke | [onboarding-decision] gamma0-aia-s27: authorize in-session | **C2** | brief-shaped-title | description text | approve: YES, this is a no-brainer. he-m7iuh is sufficient aut |
| 44 | `he-sd96` | hecke | [brief-record] he-rxm8 cohort F (7 GH issues, Magma intrin | **C2** | brief-shaped-title | metadata.source_bead/brief_for | legacy verdict backfill: PER-ITEM-SPLIT-WITH-LMFDB-DISPLAY-EPI |
| 45 | `he-sjb9` | hecke | [brief-record] he-38y8 check-citations + clean-citations ( | **C2** | brief-shaped-title | dep-edge | legacy verdict backfill: A-GREENLIGHT-AS-PAIRED-WITH-Q-DEFAULT |
| 46 | `he-skli` | hecke | [brief-record] he-i9gt — cohort I (9 items) — verdict PEND | **C2** | brief-shaped-title | dep-edge | legacy verdict backfill: APPROVE-BRIEF-AS-RECOMMENDED-3A-5C-1N |
| 47 | `he-slp1` | hecke | [brief-record] he-jwmy LaTeX-gate decomposition — verdict  | **C2** | brief-shaped-title | dep-edge | legacy verdict backfill: B+preliminary-skill-first-global-work |
| 48 | `he-v3ti` | hecke | [brief-record] he-t1om — Cohort E Magma bugs (P2+P3) — ver | **C2** | brief-shaped-title | dep-edge | legacy verdict backfill: PER-ITEM-VERBATIM-REPRODUCE-THEN-DISP |
| 49 | `he-wwky` | hecke | [brief-record] he-1ix — verdict PENDING-TAYLOR (recommende | **C2** | brief-shaped-title | metadata.source_bead/brief_for | legacy verdict backfill: E-HYBRID-B-FIRST-THEN-A-PLUS-C-PARALL |
| 50 | `gsp-34n2` | gascity-packs | BRIEF: Adopt LX0 typo-pass rule into latex POLICY.md (PP1. | **C3** | brief-shaped-title | — | Taylor verdict: approve — adopt LX0 typo-pass rule as drafted |
| 51 | `gsp-4dhp` | gascity-packs | BRIEF: bd routing-fix upstream path — fresh issue vs PR #4 | **C3** | brief-shaped-title | dep-edge | Taylor verdict: revise — research beads contributing docs + em |
| 52 | `gsp-t1oa` | gascity-packs | BRIEF: Resolve 'gate' vs gascity-formula terminology confl | **C3** | brief-shaped-title | — | Taylor verdict: revise — rename 'gate' → 'check' (gascity nati |
| 53 | `gsp-un6x` | gascity-packs | BRIEF: Adopt P3.6 — handoff beads ride the pr-pipeline (de | **C3** | brief-shaped-title | description text | Taylor verdict: revise — P3.6 scope too narrow; must cover ful |
| 54 | `he-496ab` | hecke | [brief-record] he-i2k91 — build-basic-briefed dogfood-he-a | **C3** | brief-shaped-title | title text | Closed |
| 55 | `he-naqz3` | hecke | [brief] DECIDE: authorize 95-item SNF canonicalization dis | **C3** | brief-shaped-title | title text | Closed |
| 56 | `he-3a4rsi` | hecke | Boundary sign convention: are d_k coefficients always +1 f | **C4** | plain-decision-bead | description text | superseded by he-0us2q3 (B1 decision recorded there) |
| 57 | `he-79xo` | hecke | [brief-record] he-gu79 — unblock-path verdict pending (rec | **C4** | brief-shaped-title | dep-edge | Brief-record resolved by events: pending verdict (recommended  |
| 58 | `he-hljdhx` | hecke | b_1 convention: b_1(X) vs b_1(Y) in Phase A chain complex  | **C4** | plain-decision-bead | — | superseded by he-saeno4 (B4 decision recorded there) |
| 59 | `he-tgiizb` | hecke | Cusp-stabilizer-infinity boundary contribution in Phase A  | **C4** | plain-decision-bead | description text | superseded by he-uhkeno (B3 decision recorded there) |
| 60 | `he-ujs8` | hecke | [brief-record] he-bajb inline-gamma0-ranks — verdict DISPA | **C4** | brief-shaped-title | dep-edge | Brief CANCEL-CLOSED per Taylor 2026-06-23 11:52 −10; he-bajb c |
| 61 | `he-xght` | hecke | [brief-record] he-tqze Hurwitz Gamma0(alpha) re-run — verd | **C4** | brief-shaped-title | dep-edge | Brief he-tqze KILLED (cozy 2026-06-23 12:04 -10) — jumbled; re |
| 62 | `gsp-b7ov` | gascity-packs | dup-agent boot blocker: Candidate 5 selected (delete fork  | **C5** | plain-decision-bead | — | Verified: fix described by this decision (delete fork-only gas |
| 63 | `gsp-pgt` | gascity-packs | Store repair: quarantine stray dolt-server artifacts + res | **C5** | plain-decision-bead | description text | Repair complete and proven end-to-end: quarantine executed 202 |
| 64 | `gsp-y28e4q` | gascity-packs | [formula-repair] Decision: promote/reject step must update | **C5** | brief-shaped-title | dep-edge | APPROVED -- see comment. Follow-up beads filed per action_bloc |
| 65 | `he-3309` | hecke | Sources of truth for rank / cusp-form verification (canoni | **C5** | plain-decision-bead | dep-edge | Decision fully documented: canonical 6-source hierarchy for ra |
| 66 | `he-76iej` | hecke | [decision] #335 repair sequencing: matrix_generators-permu | **C5** | brief-shaped-title | — | Sequencing resolved (permutation-first -> SNF-second); F1/F2 s |
| 67 | `he-ijn5` | hecke | [brief-record] he-pswh cohort P3-γ (SNF storage + LMFDB di | **C5** | brief-shaped-title | metadata.source_bead/brief_for | transferred to lmfdb rig |
| 68 | `he-jqsz` | hecke | [brief-record] he-p2vg autonomous-loop dispatch — verdict  | **C5** | brief-shaped-title | dep-edge | Brief-record closed by Mayor: he-p2vg dispatch decision fully  |
| 69 | `he-ktj1` | hecke | [brief-record] he-0rk2 Sigma18-bundle ACCEPTED — beadify+s | **C5** | brief-shaped-title | title text | Verdict executed 2026-07-08 ~16:15Z by mayor. 8 children under |
| 70 | `he-qbrp` | hecke | Magma trap: Generators(GrpFP) iterates in set-hash order,  | **C5** | plain-decision-bead | description text | Root cause diagnosed + fix deployed: Generators(GrpFP) set-has |
| 71 | `he-sx3o` | hecke | Policy: keep computing while improving the algorithm (Suth | **C5** | plain-decision-bead | description text | Policy ratified (Sutherland rule) — already in effect; bulk tr |
| 72 | `he-u7m5` | hecke | [brief-record] he-17np cliff-harvest ACCEPTED — staggered  | **C5** | brief-shaped-title | title text | decision executed: 16 beads verified, unlock analysis on he-pb |
| 73 | `he-vqah` | hecke | Dispatch memory governor: free-memory gate + newest-victim | **C5** | plain-decision-bead | description text | All five decisions implemented: memory governor (gate/reaper/i |
| 74 | `he-yoe2` | hecke | Ranks must never recompute coset tables: loud-fail load +  | **C5** | plain-decision-bead | — | All 3 implementation items from the decision are now in master |

---

## 4. `MBRF004` on its own terms — and two checker defects

This section answers the source-link question the task actually posed. It is
independent of everything above.

**146 of 185 briefs raise `MBRF004`** (hecke 82, gascity-packs 60,
agent_skills 4) — 57 of the malformed 74, 88 of the 104 pending, and 1 of the
7 adjudicated.

This *is* blocking, and I confirmed it against the live city rather than
inferring it. `mctl briefs options he-ldav4g --city ~/gt --rig hecke`:

```
validate       | enabled=True
adjudicate     | enabled=False  <- MBRF004
defer          | enabled=False  <- MBRF004
dispatch-work  | enabled=False  <- MBRF004
```

`plan_adjudication` (`effects.py:320`) blocks on every `ERROR`/`FATAL`
diagnostic doctor emits, and `MBRF004` is `Severity.ERROR`. So the 88 healthy
*pending* briefs raising `MBRF004` are the genuinely stuck population — not
the 74. **That is the bigger queue problem, and it was not what I was asked to
look at.**

### 4.1 The task's five classes, applied to the 146

| class | n | basis |
|---|---|---|
| 1 — genuinely source-less | **79** | no source id recoverable from metadata, brief_path, title, or the first 1500 chars of description |
| 2 — source exists, wrong link type | **0** (but see 4.3) | mctl rejects *no* dependency type; nothing fails for type reasons |
| 3 — source recorded elsewhere | **67** | title text 29, description text 27, `metadata.source_bead`/`brief_for` 7, `metadata.brief_path` filename 4 |
| 4 — genuinely not a brief | **≥39** | counted only within the 74; the pending 88 were not shape-classified |
| 5 — obsolete | **6** | the C4 superseded set |

Classes 1 and 3 are disjoint and cover the 146. Classes 4 and 5 overlap them.

Recovered ids were validated against the rig's full bead-id set, so each
proposed source is a bead that actually exists — but *plausible* is not
*correct*, and a title mention is much weaker evidence than
`metadata.source_bead`. See §6.

### 4.2 Checker defect A — mctl's B2.1 check is *looser* than the policy text

**Policy** (`subdomains/brief-system/POLICY.md:191-196`):

> **B2.1 A brief is a `type=decision` bead with a source link.** Every brief
> is materialized as a bead created with bd `type=decision`, linked to its
> **source** bead(s) via the dependency graph. Mechanical check: the brief bead
> has `type=decision` and lists at least one **source** dependency.

**Implementation** (`briefs.py:529-530`):

```python
        if not bead.source_dependencies:
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF004", "Brief bead has no source dependency.", ...))
```

and `source_dependencies` (`beads.py:383-384` → `_dependency_ids`,
`beads.py:398-423`) applies **no type filter at all**. Any edge counts. The
dependency types actually present on these 185 beads are `related` (41),
`relates-to` (15), `parent-child` (1), `supersedes` (1), `discovered-from` (1).
A `supersedes` edge is the opposite of a source link, and `parent-child` may be
either — both satisfy mctl's B2.1.

This means the check cannot be tightened without deciding which types *are*
source links. `effects.py:184` already picks a convention for new briefs
(`source_link_type: str = "related"`), which is not written down in POLICY.md.

### 4.3 Checker defect B — the check is also *narrower* than the store

`bd list --json` emits only a bead's **outgoing** dependency rows. Reverse
edges are invisible to mctl, and `dependency_count` / `dependent_count` are
never consulted. Demonstration on `he-ldav4g`:

```
$ bd dep list he-ldav4g
he-ldav4g has no dependencies

$ bd show he-ldav4g | tail -2
BLOCKS
  ← ✓ he-jrr9t7: Execute repair-gamma0-labels.mag on server DATA ...
```

`dependencies: []`, `dependent_count: 1`, and mctl raises `MBRF004`. The edge
exists in the store; mctl's reader cannot see it.

**Scope: 3 of the 146.** This is a real defect, not a mass exoneration — I
checked, and it does not rescue the population. Note also that a `blocks` edge
points *downstream* (brief → work bead), so even when visible it would not be a
*source* link under B2.1's wording. Both defects are the same underlying gap:
nobody has written down which edges are source edges.

### 4.4 Checker defect C — `_verdict()` reads fields bd does not emit

This is the one that produced the 74.

```python
def _verdict(bead: Bead) -> str | None:
    for key in ("verdict", "decision", "recorded_verdict"):
        value = bead.raw.get(key)
        if isinstance(value, str) and value:
            return value
    metadata = bead.raw.get("metadata")
    if isinstance(metadata, dict):
        for key in ("verdict", "decision", "recorded_verdict"):
            ...
```

`bd list --all --limit 0 --json --readonly` emits none of `verdict`,
`decision`, or `recorded_verdict` at top level for any bead in any of the three
rigs. What it *does* emit, and `_verdict()` never reads, is **`close_reason`**
and **`notes`**.

- `close_reason` is non-empty on **74 of 74** malformed beads.
- `notes` is non-empty on **42 of 74**.

The 7 beads that read as `adjudicated` are precisely the 7 that received a
`metadata.verdict` key from a one-off backfill. **18 further beads carry
`legacy verdict backfill: <VERDICT>` in `close_reason` from what is evidently
the same campaign but never got the metadata key.** Same backfill, two write
shapes, opposite mctl verdicts. Compare:

```
he-36ou   (adjudicated)  metadata.verdict = "A-RESUBMIT-WITH-TARGET-MASTER"
                         close_reason     = "legacy verdict backfill: A-RESUBMIT-WITH-CORRECT-TARGET-NAME per decisions.jsonl"
he-f1lt   (malformed)    metadata         = {brief_path, brief_status, cohort, ...}   # no verdict key
                         close_reason     = "legacy verdict backfill: A-CLOSE-DONE per decisions.jsonl 2026-06-25T14:14-1000"
```

Note also that the two `close_reason` strings on `he-36ou` disagree with each
other about the verdict token — evidence that the backfill's two write paths
were not derived from one source, and a reason to prefer per-bead review over a
blind re-run of it.

**If `_verdict()` also read `close_reason`, the malformed count would fall from
74 to roughly 13** (C5) plus whatever of C1/C4 policy decides is out of scope.
That is a two-line change to a reader, with no bead mutation at all — see §5.0.

---

## 5. Repair plans

### 5.0 The repair I actually recommend: fix the reader, not the 74 beads

Three of the five classes exist only because `_verdict()` looks in the wrong
place. Teaching it to read `close_reason` — the field `bd close` writes, and
the field 74/74 of these beads populate — resolves C2 and C3 (27 beads) with
**zero writes to Taylor's live stores**, and is trivially reversible.

`assets/scripts/mctl_core/briefs.py:623`:

```python
def _verdict(bead: Bead) -> str | None:
    for key in ("verdict", "decision", "recorded_verdict", "close_reason"):
        ...
```

**This is a policy question before it is a code change.** B2.2 says a verdict
must carry verdict + rationale + authorizer + date; `close_reason` is free
text and carries all four only sometimes. Accepting it wholesale weakens B2.2
into "closed with any prose". The honest options are (a) accept `close_reason`
as a verdict field and relax B2.2, (b) accept it only when it matches a
recognised verdict grammar, or (c) keep B2.2 strict and backfill
`metadata.verdict` per §5.2. **Taylor picks.** Do not let an implementer pick
by editing the tuple.

Everything below assumes option (c), the store-side repair.

### 5.1 C1 — never was a brief (28) · **bulk-safe, but repair mctl, not the store**

The defect is classification, not data. These beads are correct as they stand;
mctl is wrong to call them briefs.

**Preferred — no bead mutation.** Give `Bead.is_brief` a negative
discriminator. I tested one against all 74 and it is exact:

- rule: `title` matches `^Taylor (authorized|adopted|ratified)\b`
- **matches 28 of 28 C1 beads; matches 0 of the other 46; 0 of the 28 carry
  `brief_path`, `cohort`, or `brief_status` metadata.**

Zero false positives and zero false negatives *on this population*. It is
still a title regex, so it is a stopgap, not a contract. The durable fix is a
positive marker written at creation time — which needs a design decision, and
should be filed as a new open question rather than improvised here.

**Fallback if a store-side marker is wanted** (additive, reversible,
non-destructive — `--add-label` does not touch status, verdict, or existing
labels):

```bash
# gascity-packs (22)
for id in gsp-136z gsp-16js gsp-317y gsp-558u gsp-6iks gsp-84ca gsp-8qvk \
          gsp-afvh gsp-cd8g gsp-edafo gsp-hjbz gsp-hl4t gsp-k6y2 gsp-l1pn \
          gsp-mjv4 gsp-nx3v gsp-pc0dqg gsp-pxcu gsp-u4f6 gsp-vf5w gsp-vp9j \
          gsp-xo48; do
  bd -C /Users/tdupuy/gt/gascity-packs update "$id" --add-label not-a-brief
done

# hecke (5)
for id in he-am9lk he-hjw2y he-knox he-mgdb9 he-tz158; do
  bd -C /Users/tdupuy/gt/hecke update "$id" --add-label not-a-brief
done

# agent_skills (1)
bd -C /Users/tdupuy/gt/agent_skills update as-coq0 --add-label not-a-brief
```

**Safe because** it adds a label and nothing else; it changes no status, no
verdict, no dependency; and it is undone by `--remove-label`.

### 5.2 C2 — verdict in `close_reason` (21) · **mechanical, but review the tokens first**

I extracted a verdict token from **21 of 21** by this grammar, in order:
`^legacy verdict backfill:\s*(\S+)` · `^(approve|reject|revise|defer)\b` ·
`^Taylor verdict[^:]*:\s*(\S+)`.

```bash
bd -C /Users/tdupuy/gt/hecke update he-f1lt \
  --set-metadata verdict=A-CLOSE-DONE \
  --set-metadata verdict_source=close_reason \
  --set-metadata verdict_backfilled=2026-08-19
```

`--set-metadata` is additive and per-key; it will **not** clobber the
`brief_path` / `cohort` / `unlock_count` keys that 23 of these beads carry.
`--metadata` would replace the whole dict — **do not use it here.**

**Not blindly bulk-safe.** Three reasons, each observed:

1. The token is lossy. `he-35x2` yields `APPROVE` from *"Taylor verdict
   2026-07-22: APPROVE (B) — theoretical proof via adversarial codex loop"*;
   the option letter `(B)` is dropped, and B2.2 §MOPT001 treats a verdict
   without its option as a decision against nothing.
2. Eleven tokens are 40+ character sentences
   (`PER-ITEM-VERBATIM-PASSED-INITIAL-REACTIONS-WITH-ADAM-CONSULT-CARVE-OUT`).
   Storing those as `metadata.verdict` matches what the 7 adjudicated beads
   already hold, so it is at least consistent — but it is not a verdict
   vocabulary and nothing downstream can branch on it.
3. `he-36ou` shows the backfill's two channels disagreeing about the token
   (§4.4). Re-running its logic reproduces that risk.

**Recommended shape:** generate all 21 proposed `--set-metadata` lines as a
reviewable file, have a human scan the 21 token/`close_reason` pairs — a
ten-minute job — then apply. Do not generate and apply in one step.

### 5.3 C3 — verdict in `notes` (6) · **the only genuinely bulk-safe backfill**

Six beads carry the canonical B2.2 shape verbatim in `notes`:

```
VERDICT: revise | AUTHORIZER: Taylor | RATIONALE: Research beads contributing
docs + determine embedded-vs-server misconfiguration ... before upstream filing.
```

`he-naqz3`, `he-496ab`, `gsp-4dhp`, `gsp-34n2`, `gsp-t1oa`, `gsp-un6x`.

```bash
bd -C /Users/tdupuy/gt/gascity-packs update gsp-4dhp \
  --set-metadata verdict=revise \
  --set-metadata verdict_authorizer=Taylor \
  --set-metadata verdict_source=notes \
  --set-metadata verdict_backfilled=2026-08-19
```

**Safe because** the source field is already in B2.2's own four-part grammar
(verdict / authorizer / rationale, and date on four of the six); the token
comes from a labelled `VERDICT:` slot rather than from prose; the verdict
vocabulary is closed (`approve` 1, `revise` 4, `reject` 1); and the write is
additive metadata that alters no status and no dependency.

A seventh bead, **`gsp-b7ov`, was excluded from this class and moved to C5**:
the same regex extracts `Candidate` from *"check-plan-hygiene gate verdict:
Candidate 1 … rejected per Taylor 'no workarounds'; Candidate 5 dictated by
P1.17"*, which is a false positive. One in seven is exactly why this class
needs its extraction reviewed even though the write is safe.

### 5.4 C4 — superseded (6) · **needs one policy decision, then bulk-safe**

`he-hljdhx`, `he-3a4rsi`, `he-tgiizb` name a successor explicitly
(*"superseded by he-saeno4 (B4 decision recorded there)"*); `he-79xo`,
`he-xght`, `he-ujs8` were resolved by events or cancelled.

The blocker is not data, it is B2.3, which says the remedy for changed
circumstances is *"a NEW brief bead (linking the old brief bead as a source),
never reopening the old one"* — but says nothing about how the superseded bead
itself should read. **Is `superseded` a verdict?** Until that is answered,
these six cannot be backfilled without inventing policy.

Once answered, the write is mechanical for all six:

```bash
bd -C /Users/tdupuy/gt/hecke update he-hljdhx \
  --set-metadata verdict=superseded \
  --set-metadata superseded_by=he-saeno4 \
  --set-metadata verdict_backfilled=2026-08-19
bd -C /Users/tdupuy/gt/hecke dep add he-hljdhx he-saeno4 --type supersedes
```

The `dep add` also clears `MBRF004` on these beads — though per §4.2 a
`supersedes` edge is not a source link, so this papers over the check rather
than satisfying B2.1. Flagging that rather than quietly using it.

### 5.5 C5 — opaque (13) · **per-bead human judgement; no bulk path exists**

Thirteen beads whose `close_reason` is a narrative execution report. Example
(`he-yoe2`): *"All 3 implementation items from the decision are now in master:
(1) make_gamma0_ranks_single load_Gamma0_fp only + loud-fail (9f8d55c) …"* —
that says the work shipped. It does not say what was decided, and no regex will
recover it.

`he-76iej` · `he-ktj1` · `he-u7m5` · `he-qbrp` · `he-3309` · `he-yoe2` ·
`he-vqah` · `he-ijn5` · `he-jqsz` · `he-sx3o` · `gsp-b7ov` · `gsp-y28e4q` ·
`gsp-pgt`

Two shortcuts exist and both should be checked before anyone reads all
thirteen: `he-76iej` and `gsp-y28e4q` say *"see verdict comment"* / *"APPROVED
-- see comment"*, and five of the thirteen have `comment_count > 0`. I did not
read the comment bodies (§6). Six of the thirteen are standalone decision
beads, not briefs, so for those the answer may be C1's answer rather than a
verdict at all.

### 5.6 Summary of what is bulk-safe

| class | n | bulk-safe? | gate |
|---|---|---|---|
| C1 | 28 | yes — as an **mctl** change; label fallback also safe | none |
| C2 | 21 | **no** — generate, human-review 21 tokens, then apply | token review |
| C3 | 6 | **yes** | none |
| C4 | 6 | yes, *after* a policy answer | is `superseded` a verdict? |
| C5 | 13 | **no** | per-bead human read |

**27 of 74 are mechanically repairable** (C2 + C3), 6 more once one policy
question is answered, 28 are misclassification rather than damage, and 13 need
a human. Or — one reader fix in §5.0 makes 27 of them moot.

---

## 6. What I could not determine

- **Whether `close_reason` counts as a "recorded verdict field" under B2.2.**
  This is the hinge of the whole report and it is a policy question. I have
  deliberately not resolved it.
- **Whether the 67 "source recorded elsewhere" beads have the *right* source.**
  I validated that each recovered id exists in the rig, not that it is the bead
  the brief was written to decide. A `title text` match (29 of the 67) is a
  weak signal — a title can mention a bead for context. **Do not bulk-apply
  `bd dep add` from this column.** `metadata.source_bead` (7) and
  `metadata.brief_path` (4) are strong; the other 56 are hypotheses.
- **The comment bodies.** 25 of the 74 have `comment_count > 0` and two
  explicitly point at a "verdict comment". I read only `bd list --json`, which
  does not carry comment text. Reading them could move several C5 beads into
  C2/C3 and is the highest-value next read.
- **Brief-shape classification of the 104 pending briefs.** I classified
  brief-vs-not only within the 74. If ~15% of the pending population is also
  authorization receipts, the "185 briefs" figure is materially overstated.
- **Whether the 88 stuck *pending* briefs matter more than these 74.** They
  raise `MBRF004`, so `adjudicate` / `defer` / `dispatch-work` are all disabled
  on them — and unlike the 74 they are live, open work. I did not triage them;
  on the evidence here that is the larger queue problem.
- **What the 24 dead `metadata.brief_path` values imply.** All 24 point into
  `<rig>/.beads/briefs/`, and **0 of 24 files exist** — consistent with Q5's
  finding that the per-rig trees are gone. I did not search the archives for
  the missing files.

### A bounded note on Q5, kept separate on purpose

`MBRF021` was excluded from this analysis as instructed and none of the
classification above depends on it. One measurement is worth recording because
it narrows Q5's remedy rather than widening it: **`OPEN-DESIGN-QUESTIONS.md`
Q5 states the live pile holds 68 files named `<NN>-<slug>-brief.md` carrying
the bead id in an `artifact:` frontmatter key. Measured today, the pile holds
5 such `.md` files; the other 63 entries are `.bak` archives, `manifest.jsonl`,
and `classification.log`.** Walking all 572 brief-ish files under
`~/gt/.beads/briefs/` and matching by both `artifact:` frontmatter and filename
prefix, **only 3 of the 185 decision beads have any artifact file at all.**

The reason is structural: brief filenames embed the **source** bead id
(`he-1ix-magma-eval-escape-brief.md`), not the **brief/decision** bead id. So
Q5's proposed fix — "scan frontmatter for `artifact:`" — would not resolve the
lookup either. That is a fact about Q5's remedy, not a resolution of Q5, and it
belongs to Q5's owner.

---

## Method

```
bin/mctl briefs validate --all --city /Users/tdupuy/gt --rig <rig> --json
bd -C /Users/tdupuy/gt/<rig> list --all --limit 0 --json --readonly
bd -C /Users/tdupuy/gt/hecke show he-ldav4g
bd -C /Users/tdupuy/gt/hecke dep list he-ldav4g
bin/mctl briefs options he-ldav4g --city /Users/tdupuy/gt --rig hecke --json
```

City up, Dolt managed at `127.0.0.1:58506`, supervisor running. All reads.
Classification was scripted over the raw `bd` JSON and hand-checked against the
`close_reason` / `notes` text of all 74.

**Index:** `subdomains/dev/docs/` has no index file. The only index-shaped
document there, `ARCHIVED-DESIGNS-INDEX-2026-08-14.md`, is scoped to the four
`ARCHIVED-*.md` design documents and is not a directory index. This report is
therefore not linked from one; no index was invented for it.
