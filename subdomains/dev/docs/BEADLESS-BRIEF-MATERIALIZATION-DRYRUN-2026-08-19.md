# Beadless brief population — materialisation DRY RUN

**Nothing in this document has been executed.** No bead was created, updated,
closed, deleted, or linked in any live store while it was produced. Every `bd`
line below is text. The only `bd` verb run against the city was `list` (read);
each command *shape* was proved on a throwaway store created with `bd init`
under `mktemp -d` and deleted afterwards.

| Field | Value |
| --- | --- |
| Date | 2026-08-19 |
| Corpus | `<city-root>/.beads/briefs/stack/` — 89 `.md` files |
| Planner | `assets/scripts/mctl_core/materialize_plan.py` (read-only by construction) |
| Driver | `assets/scripts/plan_beadless_briefs.py --city ~/gt --format summary\|markdown\|json\|commands` |
| Outcome | **74 CREATE · 9 HOLD · 6 SKIP** across 9 stores |

---

## 0. Headline, and five numbers that were wrong

Every figure here was re-derived against the live stores. Five assumptions
this task inherited do not survive that, and one of them changes the shape of
the whole plan.

| Asserted | Measured | Why they differ |
|---|---|---|
| 89 files, **all** carrying `artifact:` | **85** carry it; **4** do not | 3 test canaries (`0000/0001/0002-task2a-live-*`) plus `producer-repair-unknown-…` have no `artifact:` key at all |
| 57 distinct references, **40 resolve** | **52** distinct bead ids, **52 of 52 resolve** | §2 |
| **15 unknown prefix** | **0** | `tgi`, `lm`, `ja`, `ho`, `gt` are live rigs with readable stores; §2 |
| **2 missing** | **0** | §2 |
| overlap "believed near-zero" | **6 files name their own bead**; **9 more collide** with an existing decision bead | §5 — this is the largest correction |

Re-derived counts (`plan_beadless_briefs.py --format summary`):

```
files                                        89
  CREATE                                     74
  HOLD  (existing decision bead collides)     9
  SKIP  (file names its own bead already)     6

artifact: resolves to >= 1 live bead         51
artifact: resolves to nothing                38   (29 "none", 4 absent, 5 non-bead strings)
cross-rig source links required               0   <- §4

tier A  verdict + authorizer + date          20   -> planned CLOSED, verdict recorded
tier B  disposition claimed, fields missing  28   -> planned OPEN, claim recorded as prose
tier C  no disposition at all                41   -> planned OPEN

target store  gt 41 · gascity-packs 22 · hecke 13 · agent_skills 4 ·
              gascity 3 · tdupu_github_io 3 · homog 1 · jacobi 1 · lmfdb 1
```

Cross-checks that agree with figures recorded elsewhere: **280** live
`type=decision` beads city-wide (hecke 114, gt 80, gascity-packs 69, gascity
11, agent_skills 5, differential_valuations 1); 89 `.md` in the stack (13 more
files there are `.bak*` and are correctly excluded).

---

## 1. Per-file plan — all 89 rows

`res` = does `artifact:` resolve to a live bead. `artifact type` is the
`issue_type` of the **referenced** bead (what the brief decides *about*); every
bead this plan would create is `type=decision`, per B2.1. `status` is the
proposed state of the new bead. `act` is CREATE / HOLD / SKIP.

Problem classes: **P1** unresolved artifact · **P2** cross-rig source
(count: zero) · **P3** carries a verdict · **P4** the file already names its own
bead · **P5** an existing decision bead already names this file's artifact.

| # | stack file | `artifact:` | res | target rig | artifact type | proposed title | status | verdict | act | classes |
|---:|---|---|:-:|---|---|---|---|---|---|---|
| 1 | `0000-task2a-live-standard-canary.md` | *(absent)* | N | `gt` | — | [brief] 0000 task2a live standard canary | open | — | CREATE | P1 |
| 2 | `0001-task2a-live-decision-canary.md` | *(absent)* | N | `gt` | — | [brief] 0001 task2a live decision canary | open | — | CREATE | P1 |
| 3 | `0002-task2a-live-producer-repair-canary.md` | *(absent)* | N | `gt` | — | [brief] 0002 task2a live producer repair canary | open | — | CREATE | P1 |
| 4 | `01-gh-auth-login-brief.md` | `none (blocks gt-g2e + brief 04)` | N | `gt` | — | [brief] 01 gh auth login | open | — | CREATE | P1 |
| 5 | `02-crons-durable-vs-session-brief.md` | `none` | N | `gt` | — | [brief] 02 crons durable vs session | open | — | CREATE | P1 P3 |
| 6 | `03-n2s-server-writeback-brief.md` | `gh-issue-335` | N | `gt` | — | [brief] 03 n2s server writeback | open | — | CREATE | P1 P3 |
| 7 | `04-gh-111-closure-reason-brief.md` | `gh-issue-111` | N | `gt` | — | [brief] 04 gh 111 closure reason | open | — | CREATE | P1 |
| 8 | `10-gsp-atev-plan-review-brief.md` | `gsp-atev` | Y | `gascity-packs` | epic | [brief] 10 gsp atev plan review | open | — | CREATE | — |
| 9 | `100-gsp-kseid2-resling-brief.md` | `gsp-kseid2` | Y | `gascity-packs` | task | [brief] 100 gsp kseid2 resling | open | — | CREATE | — |
| 10 | `104-city-toml-timeout-packification-brief.md` | `none` | N | `gt` | — | [brief] 104 city toml timeout packification | open | — | CREATE | P1 |
| 11 | `105-mathcity-new-beads-policy-disposition-brief.md` | `none` | N | `gt` | — | [brief] 105 mathcity new beads policy disposition | open | — | CREATE | P1 |
| 12 | `11-gsp-d50d-skill-home-brief.md` | `gsp-d50d` | Y | `gascity-packs` | task | [brief] 11 gsp d50d skill home | open | — | CREATE | P3 |
| 13 | `114-stale-telemetry-mail-archive-brief.md` | `none` | N | `gt` | — | [brief] 114 stale telemetry mail archive | open | — | CREATE | P1 |
| 14 | `12-brief-queue-hygiene-brief.md` | `gsp-9v59 (closed audit) + plans/brief-queue-hygiene-2026-07-16.md` | Y | `gascity-packs` | task | [brief] 12 brief queue hygiene | open | — | CREATE | — |
| 15 | `13-pipeline-fix-pass-brief.md` | `gsp-0s20, gsp-99s6, gsp-06gg` | Y | `gascity-packs` | bug/bug/task | [brief] 13 pipeline fix pass | open | — | HOLD | P3 P5 |
| 16 | `14-plan-reviews-cohort-brief.md` | `gsp-geuo, gsp-5n5l, gsp-wjrr, gsp-5egy` | Y | `gascity-packs` | feature/feature/feature/task | [brief] 14 plan reviews cohort | open | — | CREATE | P3 |
| 17 | `143-diff-alg-examples-identity-mismatch-brief.md` | `none` | N | `gt` | — | [brief] 143 diff alg examples identity mismatch | open | — | CREATE | P1 |
| 18 | `16-hq-compaction-quarantine-disposition-brief.md` | `gt-1fne2g` | Y | `gt` | bug | [brief] 16 hq compaction quarantine disposition | open | — | HOLD | P5 |
| 19 | `201-mathcity-create-issue-work-commit-disposition-brief.md` | `none` | N | `gt` | — | [brief] 201 mathcity create issue work commit disposition | open | — | CREATE | P1 |
| 20 | `208-hold-label-detector-after-gt-zln3z-close-brief.md` | `none` | N | `gt` | — | [brief] 208 hold label detector after gt zln3z close | open | — | CREATE | P1 |
| 21 | `214-issue-to-pr-pipeline-design-brief.md` | `none` | N | `gt` | — | [brief] 214 issue to pr pipeline design | open | — | CREATE | P1 |
| 22 | `226-bd-gate-adoption-not-build-brief.md` | `none` | N | `gt` | — | [brief] 226 bd gate adoption not build | open | — | CREATE | P1 |
| 23 | `227-verdict-action-binding-redesign-brief.md` | `none` | N | `gt` | — | [brief] 227 verdict action binding redesign | open | — | CREATE | P1 P3 |
| 24 | `229-fix-report-discriminator-validity-brief.md` | `none` | N | `gt` | — | [brief] 229 fix report discriminator validity | open | — | CREATE | P1 |
| 25 | `231-f4f72ed-push-gate-brief.md` | `f4f72ed` | N | `gt` | — | [brief] 231 f4f72ed push gate | open | — | CREATE | P1 |
| 26 | `232-brief-operator-redispatch-loop-brief.md` | `none` | N | `gt` | — | [brief] 232 brief operator redispatch loop | open | — | CREATE | P1 |
| 27 | `234-order-failed-has-no-durable-consumer-brief.md` | `none` | N | `gt` | — | [brief] 234 order failed has no durable consumer | open | — | CREATE | P1 |
| 28 | `237-gascity22-fork-vs-upstream-destination-brief.md` | `none` | N | `gt` | — | [brief] 237 gascity22 fork vs upstream destination | open | — | CREATE | P1 P3 |
| 29 | `240-dolt-quarantine-retain-verdict-blocks-222-step2-brief.md` | `none` | N | `gt` | — | [brief] 240 dolt quarantine retain verdict blocks 222 step2 | open | — | CREATE | P1 P3 |
| 30 | `243-worktree-isolation-shares-git-config-brief.md` | `none` | N | `gt` | — | [brief] 243 worktree isolation shares git config | open | — | CREATE | P1 |
| 31 | `246-stale-work-claim-starvation-brief.md` | `none` | N | `gt` | — | [brief] 246 stale work claim starvation | open | — | CREATE | P1 |
| 32 | `248-premature-slow-to-broken-escalation-brief.md` | `none` | N | `gt` | — | [brief] 248 premature slow to broken escalation | open | — | CREATE | P1 |
| 33 | `250-superpowers-systematic-debugging-credential-echo-brief.md` | `none` | N | `gt` | — | [brief] 250 superpowers systematic debugging credential echo | open | — | CREATE | P1 |
| 34 | `252-fork-recorded-verbatim-unverifiable-brief.md` | `none` | N | `gt` | — | [brief] 252 fork recorded verbatim unverifiable | open | — | CREATE | P1 |
| 35 | `255-gt-mathcity-residual-work-disposition-brief.md` | `none` | N | `gt` | — | [brief] 255 gt mathcity residual work disposition | open | — | CREATE | P1 |
| 36 | `256-section-1-framing-rule-spec-brief.md` | `none` | N | `gt` | — | [brief] 256 section 1 framing rule spec | open | — | CREATE | P1 |
| 37 | `257-decision-brief-gate-profile-brief.md` | `none` | N | `gt` | — | [brief] 257 decision brief gate profile | open | — | CREATE | P1 P3 |
| 38 | `45-sandbox-deny-list-scope-brief.md` | `gsp-0bf29` | Y | `gascity-packs` | feature | [brief] 45 sandbox deny list scope | open | — | HOLD | P5 |
| 39 | `47-sandbox-sling-verify-timeout-brief.md` | `gsp-0bf29` | Y | `gascity-packs` | feature | [brief] 47 sandbox sling verify timeout | open | — | HOLD | P5 |
| 40 | `66-skill-policy-amendment-a-l2-essentials-brief.md` | `none` | N | `gt` | — | [brief] 66 skill policy amendment a l2 essentials | open | — | CREATE | P1 P3 |
| 41 | `69-amendment-a-revision-path-brief.md` | `none` | N | `gt` | — | [brief] 69 amendment a revision path | open | — | CREATE | P1 P3 |
| 42 | `70-sandbox-remaining-reject-moot-batch-brief.md` | `gsp-0bf29` | Y | `gascity-packs` | feature | [brief] 70 sandbox remaining reject moot batch | open | — | HOLD | P3 P5 |
| 43 | `71-sandbox-quality-incident-brief.md` | `gsp-0bf29` | Y | `gascity-packs` | feature | [brief] 71 sandbox quality incident | open | — | HOLD | P3 P5 |
| 44 | `77-gt-y1gwuy-bd-cleanup-authorize-brief.md` | `gt-y1gwuy` | Y | `gt` | task | [brief] 77 gt y1gwuy bd cleanup authorize | open | — | CREATE | P3 |
| 45 | `78-fp-finder-skill-refactor-brief.md` | `none` | N | `gt` | — | [brief] 78 fp finder skill refactor | open | — | CREATE | P1 |
| 46 | `97-gsp-12rf-routing-disposition-brief.md` | `gsp-12rf` | Y | `gascity-packs` | bug | [brief] 97 gsp 12rf routing disposition | open | — | CREATE | — |
| 47 | `98-he-v34t-deferred-status-brief.md` | `he-v34t` | Y | `hecke` | task | [brief] 98 he v34t deferred status | open | — | CREATE | — |
| 48 | `as-3p6o-build-basic-briefed-brief.md` | `as-3p6o` | Y | `agent_skills` | task | [brief] as 3p6o build basic briefed | closed | SUPERSEDE | CREATE | P3 |
| 49 | `as-a5wlh-agent-skills-census-audit-brief.md` | `as-a5wlh` | Y | `agent_skills` | convoy | [brief] as a5wlh agent skills census audit | closed | ACCEPT | CREATE | P3 |
| 50 | `as-npcp1-harvest-latex-exercises-stabilize-brief.md` | `as-npcp.1` | Y | `agent_skills` | task | [brief] as npcp1 harvest latex exercises stabilize | open | — | CREATE | P3 |
| 51 | `as-vhz4-build-basic-briefed-brief.md` | `as-vhz4` | Y | `agent_skills` | task | [brief] as vhz4 build basic briefed | closed | ACCEPT | CREATE | P3 |
| 52 | `build-basic-worktree-gated-gsp-5lum7-brief.md` | `gsp-5lum7` | Y | `gascity-packs` | task | [brief] build basic worktree gated gsp 5lum7 | closed | FIX-THEN-MERGE | CREATE | P3 |
| 53 | `gc-rig-add-repo-dot-git-gitignore-gs-ab5v-brief.md` | `gs-ab5v` | Y | `gascity` | task | [brief] gc rig add repo dot git gitignore gs ab5v | closed | APPROVE | CREATE | P3 |
| 54 | `gh-38-decisions-track-classifier-verify-close-brief.md` | `gh-issue-38` | N | `gt` | — | [brief] gh 38 decisions track classifier verify close | open | — | CREATE | P1 |
| 55 | `gs-8oix-build-briefed-fix-rig-gitignore-brief.md` | `gs-8oix` | Y | `gascity` | task | [brief] gs 8oix build briefed fix rig gitignore | open | APPROVE-via-PR-pipeline | CREATE | P3 |
| 56 | `gs-nduq-investigate-brief.md` | `gs-nduq` | Y | `gascity` | feature | [brief] gs nduq investigate | open | — | SKIP | P3 P5 P4 |
| 57 | `gsp-3sbra-mathlib-quality-adjudication-brief.md` | `gsp-3sbra` | Y | `gascity-packs` | task | [brief] gsp 3sbra mathlib quality adjudication | open | — | CREATE | P3 |
| 58 | `gsp-71p9fz-approach-a-blast-radius.md` | `gsp-71p9fz` | Y | `gascity-packs` | task | [brief] gsp 71p9fz approach a blast radius | open | — | SKIP | P3 P4 |
| 59 | `gsp-78owq-catch-no-brainer-v02-fixture-briefs-789-brief.md` | `gsp-78owq` | Y | `gascity-packs` | task | [brief] gsp 78owq catch no brainer v02 fixture briefs 789 | closed | DEFER-POLICY-FIRST | CREATE | P3 |
| 60 | `gsp-kmtpl-quimby-prompt-standing-rules-brief.md` | `gsp-kmtpl` | Y | `gascity-packs` | task | [brief] gsp kmtpl quimby prompt standing rules | closed | SUPERSEDE | CREATE | P3 |
| 61 | `gsp-nq3ut1-brief.md` | `gsp-nq3ut1` | Y | `gascity-packs` | task | [brief] gsp nq3ut1 | open | — | SKIP | P3 P5 P4 |
| 62 | `gsp-r0ju5-recover-quimby-standing-rules-brief.md` | `gsp-r0ju5` | Y | `gascity-packs` | feature | [brief] gsp r0ju5 recover quimby standing rules | closed | APPROVE | CREATE | P3 |
| 63 | `gsp-wgfty-q5q6q7-design-brief.md` | `gsp-wgfty` | Y | `gascity-packs` | task | [brief] gsp wgfty q5q6q7 design | open | — | CREATE | — |
| 64 | `gsp-wmvvs-manifest-triage-filter-brief.md` | `gsp-wmvvs` | Y | `gascity-packs` | task | [brief] gsp wmvvs manifest triage filter | closed | APPROVE | CREATE | P3 |
| 65 | `gsp-z4u0i-brief.md` | `gsp-z4u0i` | Y | `gascity-packs` | task | [brief] gsp z4u0i | open | — | CREATE | — |
| 66 | `gt-1f2781-downstream-filter-rule-empty-assignee-after-verified-sling-brief.md` | `none` | N | `gt` | — | [brief] gt 1f2781 downstream filter rule empty assignee after verified sling | open | — | SKIP | P1 P4 |
| 67 | `gt-2vv2u0-upstream-repair-empty-assignee-after-verified-sling-brief.md` | `none` | N | `gt` | — | [brief] gt 2vv2u0 upstream repair empty assignee after verified sling | open | — | SKIP | P1 P4 |
| 68 | `gt-ggcuot-build-repair-formula-design.md` | `gt-ggcuot` | Y | `gt` | spec | [brief] gt ggcuot build repair formula design | open | — | CREATE | — |
| 69 | `he-1fl30-readme-tests-bart-brief.md` | `he-1fl30` | Y | `hecke` | task | [brief] he 1fl30 readme tests bart | closed | ACCEPT | CREATE | P3 |
| 70 | `he-3w0eu-delete-bad-snf-gamma0-brief.md` | `he-3w0eu` | Y | `hecke` | task | [brief] he 3w0eu delete bad snf gamma0 | open | — | CREATE | P3 |
| 71 | `he-a9cfa-brief.md` | `he-a9cfa` | Y | `hecke` | feature | [brief] he a9cfa | closed | C | CREATE | P3 |
| 72 | `he-ckilh-dispatch-gate.md` | `he-ckilh` | Y | `hecke` | task | [brief] he ckilh dispatch gate | open | — | CREATE | — |
| 73 | `he-el1s5-gamma0-backup-n0-brief.md` | `he-el1s5` | Y | `hecke` | task | [brief] he el1s5 gamma0 backup n0 | closed | CLOSE-CONFIRMED | CREATE | P3 |
| 74 | `he-g6uo7-n1-5-dry-run-snf-audit-build-brief.md` | `he-g6uo7` | Y | `hecke` | task | [brief] he g6uo7 n1 5 dry run snf audit build | closed | ARCHIVE+FILE-RECOVERY-TASK | CREATE | P3 |
| 75 | `he-hsoc-check-latex-acceptance-brief.md` | `he-hsoc` | Y | `hecke` | task | [brief] he hsoc check latex acceptance | open | — | HOLD | P3 P5 |
| 76 | `he-ipwws-brief.md` | `he-ipwws` | Y | `hecke` | task | [brief] he ipwws | open | — | HOLD | P3 P5 |
| 77 | `he-q5nah-gamma0-repair-hold-brief.md` | `he-q5nah` | Y | `hecke` | task | [brief] he q5nah gamma0 repair hold | open | — | CREATE | P3 |
| 78 | `he-sraxz-gamma0-snf-audit-brief.md` | `he-sraxz` | Y | `hecke` | task | [brief] he sraxz gamma0 snf audit | open | — | CREATE | P3 |
| 79 | `he-wjfo2-n1-5gate-smoke-test-brief.md` | `he-wjfo2` | Y | `hecke` | task | [brief] he wjfo2 n1 5gate smoke test | closed | CLOSE-CONFIRMED | CREATE | P3 |
| 80 | `he-xkm7u-335-repair-dispatch-inject-brief.md` | `he-xkm7u` | Y | `hecke` | task | [brief] he xkm7u 335 repair dispatch inject | open | — | CREATE | P3 |
| 81 | `ho-6vx-git-hygiene-cleanup-brief.md` | `ho-6vx` | Y | `homog` | task | [brief] ho 6vx git hygiene cleanup | closed | APPROVE | CREATE | P3 |
| 82 | `ja-frp-git-hygiene-cleanup-brief.md` | `ja-frp` | Y | `jacobi` | task | [brief] ja frp git hygiene cleanup | closed | APPROVE | CREATE | P3 |
| 83 | `lm-p0z-gitignore-gascity-block-build-result-brief.md` | `lm-p0z` | Y | `lmfdb` | task | [brief] lm p0z gitignore gascity block build result | closed | APPROVE | CREATE | P3 |
| 84 | `producer-repair-unknown-unknown-unknown-rejection-reason-not-machine-extractable-from-rejection.md` | *(absent)* | N | `gt` | — | [brief] producer repair unknown unknown unknown rejection reason not machine extractable from rejection | open | — | SKIP | P1 P4 |
| 85 | `sandbox-shell-commands-in-steps.md` | `gsp-0bf29` | Y | `gascity-packs` | feature | [brief] sandbox shell commands in steps | open | C — omit scope-audit; follow bmad | HOLD | P3 P5 |
| 86 | `skill-invocation-contract-policy-skills.md` | `72-skill-invocation-contract-policy-skills-brief.md` | N | `gt` | — | [brief] skill invocation contract policy skills | open | — | CREATE | P1 P3 |
| 87 | `tgi-30g-brief.md` | `tgi-30g` | Y | `tdupu_github_io` | task | [brief] tgi 30g | closed | ACCEPT | CREATE | P3 |
| 88 | `tgi-30qh-untrack-gascity-brief.md` | `tgi-30qh` | Y | `tdupu_github_io` | task | [brief] tgi 30qh untrack gascity | closed | APPROVE | CREATE | P3 |
| 89 | `tgi-d1k-brief.md` | `tgi-d1k` | Y | `tdupu_github_io` | task | [brief] tgi d1k | closed | SUPERSEDE | CREATE | P3 |

---

## 2. Question 1 — the "17 references that do not resolve"

**Finding: there are none. All 52 distinct bead references resolve, in live,
readable stores.** The earlier "15 unknown prefix + 2 missing" is an artefact of
what was being read, not of the corpus.

### What the prefixes actually are

`rigs.json` registers 9 rigs and is **not** the list of bead stores: it omits
`gt`, `gsp`, `gs`, `mc` and `cp2` entirely. The authoritative mapping is each
store's own `.beads/config.yaml`:

| prefix | store | live beads | prefix | store | live beads |
|---|---|---:|---|---|---:|
| `gt` / `hq` | `<city-root>` (HQ) | 30 201 | `ho` | `homog` | 181 |
| `he` | `hecke` | 10 566 | `lm` | `lmfdb` | 197 |
| `gsp` | `gascity-packs` | 9 580 | `ja` | `jacobi` | 292 |
| `gs` | `gascity` | 429 | `tgi` | `tdupu_github_io` | 393 |
| `as` | `agent_skills` | 1 163 | `mc` | `mathcity` | 87 |
| `dv` | `differential_valuations` | 50 | `cp2` | `cliff-part2` | 13 |

The 9 ids that an earlier pass could not place — `gt-1fne2g`, `gt-ggcuot`,
`gt-y1gwuy`, `ho-6vx`, `ja-frp`, `lm-p0z`, `tgi-30g`, `tgi-30qh`, `tgi-d1k` —
are exactly the ids **outside the five rigs the corpus snapshot covers**. The
snapshot at `~/Downloads/mathcity-corpus-snapshot-2026-08-19/` holds 200 beads
from 5 rigs and, crucially, only `type=decision` ones. Resolved against it,
every `artifact:` looks missing (they are `task`/`feature`/`bug`, not
decisions) and every non-hecke/gsp/gs/as/dv prefix looks unknown. **The
snapshot is the wrong instrument for this question** and is not used here
except as a cross-check on the 280 decision-bead total.

Reference breakdown, re-derived:

```
52 distinct bead ids   -> 52 resolve  (gsp 23 · he 13 · as 4 · gs 3 · gt 3 · tgi 3 · ho 1 · ja 1 · lm 1)
 5 non-bead strings    -> gh-issue-335, gh-issue-111, gh-issue-38, f4f72ed,
                          72-skill-invocation-contract-policy-skills-brief.md
29 literal "none"      -> 28 bare, 1 as "none (blocks gt-g2e + brief 04)"
 4 no artifact: key
```

Referenced-bead types (56 references from 51 files; two files name several):
`task` 38 · `feature` 11 · `bug` 4 · `epic` 1 · `convoy` 1 · `spec` 1. **No
artifact is itself a `decision` bead** — the "decision 1" in the earlier
tally has no counterpart here.

### Recommendation — create, with the unresolved reference recorded, and no invented link

For the 38 files whose artifact resolves to nothing:

1. **Create the brief bead**, in HQ (`gt`), the store that owns the stack
   directory. D4 requires every stray document to be migrated in; skipping 38
   of 89 would leave the largest single class outside the system, which is the
   state D4 exists to end.
2. **Write no source dependency at all.** Not a guess, not a placeholder. The
   bead then fails B2.1's mechanical check and `MBRF004` fires on it — which is
   the *visible* failure, and exactly the direction
   `verdicts.py::is_git_authorization_receipt` already chose ("an unexempted
   receipt is visible … a real brief wrongly exempted disappears").
3. **Record the raw string** in `mathcity.brief.unresolved_artifact`, so the 38
   are one query away and a human can resolve them in a later, separate pass.

Two sub-cases deserve a named follow-up rather than being lumped in:

- **`none (blocks gt-g2e + brief 04)`** (file 4). The parenthetical names real
  beads, but they are what this brief *blocks*, not what it decides about.
  Linking them would attach the adjudication to the wrong work. Left
  unresolved deliberately.
- **The 3 `gh-issue-N` files and 1 git-sha file.** `bd create` has a purpose-built
  `--external-ref` flag whose own help text gives `gh-9` as the example. These
  four should carry `--external-ref gh-issue-335` (etc.) so the pointer is
  typed rather than buried in metadata. This is **not** in the emitted commands
  below, because `--external-ref` semantics were not exercised on the throwaway
  store and I will not propose an unverified flag in a script meant to be run
  verbatim. It is a one-line addition once someone checks it.

---

## 3. Question 3 — verdicts (taken before §4, because it changes what §4 creates)

**48 of 89 files claim a disposition. Only 20 carry what B2.2 requires.**

B2.2: "Adjudication records the verdict fields ON the brief bead itself —
verdict, authorizer, one-line rationale, date — and then closes the bead."
Splitting the 89 by whether those fields are actually present:

| tier | test | count | plan |
|---|---|---:|---|
| **A** | typed `verdict:` **and** `adjudicated_by:` **and** `adjudicated_at:` | **20** | **closed**, verdict recorded on the bead |
| **B** | claims a disposition but is missing at least one of those | **28** | **open**, claim recorded as labelled prose |
| **C** | no disposition claimed | **41** | **open** |

A number worth flagging: an earlier count of "58 adjudicated" comes from
substring-matching `adjudic` in the `status:` field, which also matches the 23
files whose status is `ready-for-adjudication` — the *opposite* state. The
planner anchors on prefixes and excludes `ready*` explicitly; a regression test
pins it.

### Recommendation — close the 20, open the 28, and never infer

**The 20 tier-A files are materialised closed**, with `--notes` written in the
exact shape `verdicts.py::_NOTES_CANONICAL` already parses:

```
VERDICT: APPROVE | AUTHORIZER: Taylor (Q18) | RATIONALE: <verdict_note or "recorded in <file>">
```

`read_verdict_reading()` then resolves them at `confidence=high`,
`source=notes` — no new verdict format is invented, and a test round-trips a
planned bead through the live adapter to prove it. All 20 name a human
authorizer (19 × "Taylor (Q18/Q19)", 1 × "QUIMBY 18 (Taylor)"), so closing them
asserts nothing that the file does not already assert with all three fields.
Their verdicts are recorded verbatim, never normalised: `SUPERSEDE`, `ACCEPT`,
`FIX-THEN-MERGE`, `DEFER-POLICY-FIRST`, `ARCHIVE+FILE-RECOVERY-TASK`,
`CLOSE-CONFIRMED`, `C`.

**The 28 tier-B files are materialised open.** 26 of the 28 have no typed
verdict at all — their only evidence is a `status:` string such as `approved`,
`approved-slung`, `adjudicated`, `mixed-partial`, or the remarkable
`needs-revision(check-zero-ZFC-partial:V5-pipeline-membership-is-semantic;…)`.
Their claim is copied verbatim into a note that deliberately does **not** begin
`VERDICT:`, so the adapter reads it as prose and reports the brief as
unadjudicated rather than manufacturing one:

```
UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete)
| stack_file: … | claimed status: adjudicated | recorded verdict: (no typed verdict field)
```

**The reasoning, not a coin flip.** The two errors are not symmetric.

- Materialise open when it was in fact decided → the brief surfaces once, a
  human says "already settled", and closes it with a real verdict. Cost: one
  presentation. Fully recoverable, and the recovery *improves* the record.
- Materialise closed with an asserted verdict that is wrong → B2.3 says an
  adjudicated brief "can NEVER be presented again … the remedy is a NEW brief
  bead, never reopening the old one". The wrong verdict is unreachable by
  design and invisible on every surface. Cost: unrecoverable.

That is the same asymmetry `verdicts.py` was written around, and the same
one that produced `MBRF021`'s mass false positives when it was ignored. The
28 are also the population where the evidence is weakest, so they are exactly
the wrong place to spend an irreversible action.

There is a real cost to opening 28 settled-looking questions, and it is not
dismissed: the plan makes them findable in one query
(`metadata."mathcity.brief.materialized_by"` + a `UNVERIFIED-PRIOR-DISPOSITION`
note), so a human can sweep them as a batch and close them properly — which
is a better outcome than 28 machine-asserted verdicts nobody can audit.

---

## 4. Question 2 — cross-rig source links

**Count: 0 of 89. It does not block the approach — but only because of a choice
that has to be made deliberately, and the live corpus contains the
counterexample that proves it.**

### The measurement

Every stack file's `artifact:` resolves within a **single** store. The two
multi-reference files are both single-store:

- `13-pipeline-fix-pass-brief.md` → `gsp-0s20`, `gsp-99s6`, `gsp-06gg` — all `gascity-packs`
- `14-plan-reviews-cohort-brief.md` → `gsp-geuo`, `gsp-5n5l`, `gsp-wjrr`, `gsp-5egy` — all `gascity-packs`

So **if the brief bead is created in the store its artifact already lives in,
every source edge is intra-store and the problem does not arise.** That is what
this plan does: 41 rows land in `gt`, 22 in `gascity-packs`, 13 in `hecke`, and
the rest in the five smaller rigs. POLICY permits it — B2.1 requires a source
link in the dependency graph and says nothing about location — and D14 states
the principle outright: *"storage is per-rig, reporting is city-wide."*

The alternative reading, "all brief beads live in HQ", would make 48 of the 51
resolving files cross-rig and would indeed sink the whole approach. The
difference between 0 and 48 is entirely the placement rule, so the rule is
stated explicitly rather than left to a default.

### `bd` behaviour, measured on a throwaway store

`he-tbmq0` was described in `MBRF004-TRIAGE-2026-08-19.md` as needing "a design
answer, not a link" because a bd dependency edge "cannot" cross rigs. Measured,
the truth is worse than "cannot":

| command | result |
|---|---|
| `bd dep add <local> <foreign-id>` | **exit 0**, prints `✓ Added dependency`, `dependency_count` increments — and the edge appears in **no** listing: not `bd dep list`, not `bd dep tree`, not the `dependencies` array that `Bead.source_dependencies` is built from |
| `bd dep relate <local> <foreign-id>` | exit 1, `failed to resolve …: no issue found` |
| `bd create --deps <foreign-id>` | exit 1, `Error: resolving --deps target "…": no issue found matching "…"` |
| `bd create --id he-probe1` in a `zz9` store | exit 1, `prefix mismatch … (use --force to override)` |

So a cross-store link written with `bd dep add` is **silent data loss that
still satisfies a naive `dependency_count >= 1` reading of B2.1** while
`mctl_core`'s own reader sees no source at all. Every source link in this plan
is therefore written with `bd create --deps`, which fails loudly, and **`bd dep
add` appears nowhere in the emitted commands**. A test asserts that.

### The live counterexample, found while checking overlap

`he-tbmq0` is an open `type=decision` bead in **hecke** titled
`gsp-0bf29: omit scope-audit step; follow bmad patterns for formula steps`.
The stack file `sandbox-shell-commands-in-steps.md` has
`artifact: gsp-0bf29`, `status: adjudicated`, and
`verdict: C — omit scope-audit; follow bmad`.

**That file is `he-tbmq0`'s brief document.** Its cross-rig source problem was
not inherent: the brief bead was put in `hecke` while its subject lives in
`gascity-packs`. Placing brief beads with their artifacts is precisely the rule
that would have prevented it — which is corroboration for the placement choice,
and a reason `sandbox-shell-commands-in-steps.md` is on **HOLD** rather than
CREATE (§5).

### Recommendation

1. Create each brief bead in the store its artifact lives in. Cross-rig count
   drops to 0 by construction, and a test pins it.
2. Write source links only via `bd create --deps`; forbid `bd dep add` in this
   migration and, separately, file the silent-success behaviour as a bd defect
   — it is a footgun well beyond this task.
3. For the 38 unresolved rows, write no link at all (§2).

---

## 5. Overlap — the largest correction, and the reason for HOLD

Overlap is **not** near-zero. Two independent mechanical checks:

### 5a. Files that name their own bead in frontmatter — 6, planned **SKIP**

| stack file | field | bead | type / status |
|---|---|---|---|
| `gs-nduq-investigate-brief.md` | `brief_bead` | `gs-0hd8` | decision / open |
| `gsp-71p9fz-approach-a-blast-radius.md` | `brief_record_bead` | `gsp-9sf5io` | task / open |
| `gsp-nq3ut1-brief.md` | `brief_record_bead` | `gsp-ficcsn` | decision / open |
| `gt-1f2781-…-brief.md` | `decision_bead` | `gt-1f2781` | decision / closed |
| `gt-2vv2u0-…-brief.md` | `decision_bead` | `gt-2vv2u0` | decision / closed |
| `producer-repair-unknown-…md` | `repair_review_bead` | `gsp-hlr8d5` | decision / open |

Note `gt-1f2781` and `gt-2vv2u0`: the file is named after its own already-closed
decision bead while `artifact:` reads `none`. These two are already fully
materialised; creating anything for them would be a straight duplicate.

The earlier "1 of 89 stack files carries `brief_bead:`" is right about that one
key and misses the other three key spellings; the planner checks all four.

### 5b. An existing decision bead already names the file's artifact — 9 more, planned **HOLD**

Rule: a `type=decision` bead whose **title** contains this file's `artifact:`
id. Mechanical, no fuzzy matching.

| stack file | colliding decision bead |
|---|---|
| `13-pipeline-fix-pass-brief.md` | `gsp-eejju` (open) — `[authorize-git] gsp-06gg local merge …` |
| `16-hq-compaction-quarantine-disposition-brief.md` | `gt-57dccr` (open) — `BRIEF #16 — hq compaction quarantine disposition (gt-1fne2g)` |
| `45-sandbox-deny-list-scope-brief.md` | `he-tbmq0` (open) |
| `47-sandbox-sling-verify-timeout-brief.md` | `he-tbmq0` (open) |
| `70-sandbox-remaining-reject-moot-batch-brief.md` | `he-tbmq0` (open) |
| `71-sandbox-quality-incident-brief.md` | `he-tbmq0` (open) |
| `sandbox-shell-commands-in-steps.md` | `he-tbmq0` (open) |
| `he-hsoc-check-latex-acceptance-brief.md` | `he-2jp5` (closed) — `[brief-record] he-hsoc check-latex-umbrella` |
| `he-ipwws-brief.md` | `gt-6sta0h` (open) — a QUIMBY session handoff |

Not all are duplicates. `gt-57dccr` almost certainly is — its title carries
both the same subject id and the same "BRIEF #16" number as the filename.
`sandbox-shell-commands-in-steps.md` / `he-tbmq0` almost certainly is —
matching verdict text (§4). `gsp-eejju` is a git-auth receipt and `gt-6sta0h` is
a session handoff; those two are probably *not* duplicates. The other five all
turn on the single subject `gsp-0bf29`, which five stack files share, and only
a human knows whether that is one decision or five.

**So HOLD, not SKIP and not CREATE.** A title collision is evidence, not proof;
creating a duplicate brief is stated in the task as the worst outcome, and
`bd create` will happily mint two beads with identical titles (verified). These
9 rows emit a `# HOLD …` comment instead of a command and need a human line
before any of them runs.

### Overlap checks that came back clean

- `metadata.brief_path` pointing into `stack/`: 15 beads, of which **1** names a
  file that still exists (`as-286u0` → `as-3p6o-build-basic-briefed-brief.md`,
  a `task` brief-record, not a brief bead). The other 14 point at files that
  are gone.
- Only **1 of 280** decision beads city-wide has any dependency at all
  (`dependency_count > 0`), so no existing brief bead's source link collides
  with anything this plan would write.
- `gc.brief.slug`: see §6 — it looks like an identity key and is not one.

---

## 6. Idempotency and reversal

### Idempotency

`bd create` mints a random id and does **not** deduplicate on title — verified:
two `bd create DUPTITLE` calls produced `zz9-crt` and `zz9-2vc`. So idempotency
has to be carried by a key the run writes and the next run reads.

Every created bead carries:

```json
{"mathcity.brief.stack_file":    "<basename>.md",
 "mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19"}
```

A re-run is guarded by, per target store:

```sh
bd -C "$RIG" list --json --status all \
  | jq -r '.[] | select(.issue_type=="decision")
                 | .metadata."mathcity.brief.stack_file" // empty'
```

and skipping any stack file whose basename appears. `--metadata` round-trips
through `bd create` unchanged (verified on the throwaway store).

**The key is deliberately not `gc.brief.slug`.** That key already exists on
**826 live beads** written by the gascity formula machinery, **74** of which
carry the slug of a stack file in this very corpus (e.g. 10 beads carry
`he-ckilh-dispatch-gate`, 8 carry `skill-invocation-contract-policy-skills`).
Re-using it would make a re-run skip files that were never materialised — a
silent partial migration that looks complete. A test pins the distinction.

`bd dep add` is separately idempotent (repeating it does not double the edge),
but this plan does not use it.

### Reversal

Three layers, in order of preference:

1. **Append-a-line-per-create manifest.** The executing script writes
   `<store> <bead-id> <stack-file>` to
   `subdomains/dev/docs/materialization-receipt-2026-08-19.tsv` and flushes
   after every single `bd create`, so an abort or crash mid-batch still leaves
   a complete list of everything that exists. This is the primary undo input
   and costs nothing.
2. **Query-based undo**, if the manifest is lost. One query per touched store
   on the single literal batch marker:

```sh
bd -C "$RIG" list --json --status all \
  | jq -r '.[] | select(.metadata."mathcity.brief.materialized_by"
                        == "beadless-brief-materialization-2026-08-19") | .id' \
  | xargs -r -n1 bd -C "$RIG" delete --force
```

   `bd delete --force` was verified on the throwaway store to remove the bead
   **and** its dependency links (`✓ Deleted zz9-aqb / Removed 2 dependency
   link(s)`). Nothing else in the city carries that marker value, so the query
   cannot over-select.
3. **Pre-run baseline.** Before the first write, snapshot
   `bd -C "$RIG" list --json --status all` for each of the 9 target stores to a
   dated directory. If both layers above fail, the set difference identifies
   every stray bead. This is also the only way to detect a bead created by
   *something else* during the run.

Two further safety properties worth stating:

- **The batch is store-partitioned.** Running one store at a time (9 batches,
  largest 41) bounds the blast radius of any single mistake, and each store's
  undo is independent.
- **Nothing existing is modified.** The plan issues no `bd update`, and its
  only `bd close` calls are against beads the same run just created. No live
  bead's state changes, so there is nothing to restore — only things to delete.

**Deferred-verdict variant, if the reversal story is judged not strong enough:**
run the 74 CREATE rows with tier-A files also planned **open**, and record the
20 verdicts in a second, separately-reviewable pass. That makes the entire
first run undoable by deletion alone, with no `bd close` to reverse. It costs
one extra pass and is the safer sequencing if the owner wants a smaller first
irreversible step.

---

## 7. The exact commands

Generated by `plan_beadless_briefs.py --format commands`; reproduce with that
command rather than copying by hand. `$CITY` is the city root (`~/gt`).
`<NEW-ID>` in a `close` line is the id printed by the `create` line above it —
the executing script substitutes it; it is left symbolic here because bd mints
it.

Read before running:

- `# SKIP` (6) and `# HOLD` (9) lines are **comments**, not commands. They are
  in the list so the count reconciles to 89 and so a human sees why a file has
  no command.
- Source links use `--deps` only. `bd dep add` appears nowhere (§4).
- The 20 `close` lines apply only to tier-A rows (§3).

```sh
bd -C '$CITY' create '[brief] 0000 task2a live standard canary' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "0000-task2a-live-standard-canary.md", "mathcity.brief.unresolved_artifact": "(absent)"}' --silent
bd -C '$CITY' create '[brief] 0001 task2a live decision canary' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "0001-task2a-live-decision-canary.md", "mathcity.brief.unresolved_artifact": "(absent)"}' --silent
bd -C '$CITY' create '[brief] 0002 task2a live producer repair canary' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "0002-task2a-live-producer-repair-canary.md", "mathcity.brief.unresolved_artifact": "(absent)"}' --silent
bd -C '$CITY' create '[brief] 01 gh auth login' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "01-gh-auth-login-brief.md", "mathcity.brief.unresolved_artifact": "none (blocks gt-g2e + brief 04)"}' --silent
bd -C '$CITY' create '[brief] 02 crons durable vs session' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "02-crons-durable-vs-session-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: 02-crons-durable-vs-session-brief.md | claimed status: approved | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY' create '[brief] 03 n2s server writeback' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "03-n2s-server-writeback-brief.md", "mathcity.brief.unresolved_artifact": "gh-issue-335"}' --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: 03-n2s-server-writeback-brief.md | claimed status: approved-slung | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY' create '[brief] 04 gh 111 closure reason' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "04-gh-111-closure-reason-brief.md", "mathcity.brief.unresolved_artifact": "gh-issue-111"}' --silent
bd -C '$CITY/gascity-packs' create '[brief] 10 gsp atev plan review' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "10-gsp-atev-plan-review-brief.md"}' --deps gsp-atev --silent
bd -C '$CITY/gascity-packs' create '[brief] 100 gsp kseid2 resling' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "100-gsp-kseid2-resling-brief.md"}' --deps gsp-kseid2 --silent
bd -C '$CITY' create '[brief] 104 city toml timeout packification' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "104-city-toml-timeout-packification-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 105 mathcity new beads policy disposition' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "105-mathcity-new-beads-policy-disposition-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY/gascity-packs' create '[brief] 11 gsp d50d skill home' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "11-gsp-d50d-skill-home-brief.md"}' --deps gsp-d50d --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: 11-gsp-d50d-skill-home-brief.md | claimed status: approved-slung | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY' create '[brief] 114 stale telemetry mail archive' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "114-stale-telemetry-mail-archive-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY/gascity-packs' create '[brief] 12 brief queue hygiene' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "12-brief-queue-hygiene-brief.md"}' --deps gsp-9v59 --silent
# HOLD 13-pipeline-fix-pass-brief.md: decision bead(s) gsp-eejju already name this file's artifact in their title -- confirm before creating
bd -C '$CITY/gascity-packs' create '[brief] 14 plan reviews cohort' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "14-plan-reviews-cohort-brief.md"}' --deps gsp-geuo --deps gsp-5n5l --deps gsp-wjrr --deps gsp-5egy --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: 14-plan-reviews-cohort-brief.md | claimed status: mixed-partial | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY' create '[brief] 143 diff alg examples identity mismatch' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "143-diff-alg-examples-identity-mismatch-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
# HOLD 16-hq-compaction-quarantine-disposition-brief.md: decision bead(s) gt-57dccr already name this file's artifact in their title -- confirm before creating
bd -C '$CITY' create '[brief] 201 mathcity create issue work commit disposition' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "201-mathcity-create-issue-work-commit-disposition-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 208 hold label detector after gt zln3z close' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "208-hold-label-detector-after-gt-zln3z-close-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 214 issue to pr pipeline design' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "214-issue-to-pr-pipeline-design-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 226 bd gate adoption not build' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "226-bd-gate-adoption-not-build-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 227 verdict action binding redesign' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "227-verdict-action-binding-redesign-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: 227-verdict-action-binding-redesign-brief.md | claimed status: adjudicated | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY' create '[brief] 229 fix report discriminator validity' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "229-fix-report-discriminator-validity-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 231 f4f72ed push gate' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "231-f4f72ed-push-gate-brief.md", "mathcity.brief.unresolved_artifact": "f4f72ed"}' --silent
bd -C '$CITY' create '[brief] 232 brief operator redispatch loop' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "232-brief-operator-redispatch-loop-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 234 order failed has no durable consumer' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "234-order-failed-has-no-durable-consumer-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 237 gascity22 fork vs upstream destination' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "237-gascity22-fork-vs-upstream-destination-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: 237-gascity22-fork-vs-upstream-destination-brief.md | claimed status: adjudicated | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY' create '[brief] 240 dolt quarantine retain verdict blocks 222 step2' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "240-dolt-quarantine-retain-verdict-blocks-222-step2-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: 240-dolt-quarantine-retain-verdict-blocks-222-step2-brief.md | claimed status: adjudicated | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY' create '[brief] 243 worktree isolation shares git config' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "243-worktree-isolation-shares-git-config-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 246 stale work claim starvation' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "246-stale-work-claim-starvation-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 248 premature slow to broken escalation' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "248-premature-slow-to-broken-escalation-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 250 superpowers systematic debugging credential echo' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "250-superpowers-systematic-debugging-credential-echo-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 252 fork recorded verbatim unverifiable' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "252-fork-recorded-verbatim-unverifiable-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 255 gt mathcity residual work disposition' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "255-gt-mathcity-residual-work-disposition-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 256 section 1 framing rule spec' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "256-section-1-framing-rule-spec-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY' create '[brief] 257 decision brief gate profile' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "257-decision-brief-gate-profile-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: 257-decision-brief-gate-profile-brief.md | claimed status: adjudicated | recorded verdict: (no typed verdict field)' --silent
# HOLD 45-sandbox-deny-list-scope-brief.md: decision bead(s) he-tbmq0 already name this file's artifact in their title -- confirm before creating
# HOLD 47-sandbox-sling-verify-timeout-brief.md: decision bead(s) he-tbmq0 already name this file's artifact in their title -- confirm before creating
bd -C '$CITY' create '[brief] 66 skill policy amendment a l2 essentials' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "66-skill-policy-amendment-a-l2-essentials-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: 66-skill-policy-amendment-a-l2-essentials-brief.md | claimed status: needs-revision(check-zero-ZFC-partial:V5-pipeline-membership-is-semantic;option-A=add-model-call-language;option-B=normative-TOML-registry) | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY' create '[brief] 69 amendment a revision path' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "69-amendment-a-revision-path-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: 69-amendment-a-revision-path-brief.md | claimed status: adjudicated | recorded verdict: (no typed verdict field)' --silent
# HOLD 70-sandbox-remaining-reject-moot-batch-brief.md: decision bead(s) he-tbmq0 already name this file's artifact in their title -- confirm before creating
# HOLD 71-sandbox-quality-incident-brief.md: decision bead(s) he-tbmq0 already name this file's artifact in their title -- confirm before creating
bd -C '$CITY' create '[brief] 77 gt y1gwuy bd cleanup authorize' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "77-gt-y1gwuy-bd-cleanup-authorize-brief.md"}' --deps gt-y1gwuy --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: 77-gt-y1gwuy-bd-cleanup-authorize-brief.md | claimed status: adjudicated | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY' create '[brief] 78 fp finder skill refactor' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "78-fp-finder-skill-refactor-brief.md", "mathcity.brief.unresolved_artifact": "none"}' --silent
bd -C '$CITY/gascity-packs' create '[brief] 97 gsp 12rf routing disposition' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "97-gsp-12rf-routing-disposition-brief.md"}' --deps gsp-12rf --silent
bd -C '$CITY/hecke' create '[brief] 98 he v34t deferred status' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "98-he-v34t-deferred-status-brief.md"}' --deps he-v34t --silent
bd -C '$CITY/agent_skills' create '[brief] as 3p6o build basic briefed' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "as-3p6o-build-basic-briefed-brief.md"}' --deps as-3p6o --notes 'VERDICT: SUPERSEDE | AUTHORIZER: Taylor (Q18) | RATIONALE: SUPERSEDE — duplicate census build of as-vhz4 (both ran build-basic-briefed on ~/gt/agent_skills with identical artifact root). as-vhz4 ACCEPTED (Taylor Q18 2026-07-18); as-3p6o'"'"'s simplicity lane + synthesis stamps on as-vhz4'"'"'s artifacts confirm race condition. xkcd-927 instance: competing parallel builds with cross-workflow stamp contamination. Source bead as-3p6o closed by Q18 fork 5d30. Systemic fix (uniqueness constraint, convoy-kill, no concurrent duplicate launches) tracked in gsp-tlr5l. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/agent_skills' close '<NEW-ID>' --reason 'SUPERSEDE (migrated verbatim from as-3p6o-build-basic-briefed-brief.md)'
bd -C '$CITY/agent_skills' create '[brief] as a5wlh agent skills census audit' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "as-a5wlh-agent-skills-census-audit-brief.md"}' --deps as-a5wlh --notes 'VERDICT: ACCEPT | AUTHORIZER: Taylor (Q18) | RATIONALE: ACCEPT — repair in place. Taylor: '"'"'Ok then. Repair it.'"'"' (Q18 2026-07-18). Sub-verdicts: (1) 114 gastown narrative references accepted as-is (contextually appropriate, no cleanup required); (2) 9 gt-pr6 refs in skill/plan files require cleanup per §2 task table; (3) repair tasks to be filed as follow-up beads (sync AGENTS.md, sync CLAUDE.md, remove gt-pr6 refs, .gitignore sync) — wait for as-bkuw to drain before executing. as-dira closes after post-repair validation gate passes.' --silent
bd -C '$CITY/agent_skills' close '<NEW-ID>' --reason 'ACCEPT (migrated verbatim from as-a5wlh-agent-skills-census-audit-brief.md)'
bd -C '$CITY/agent_skills' create '[brief] as npcp1 harvest latex exercises stabilize' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "as-npcp1-harvest-latex-exercises-stabilize-brief.md"}' --deps as-npcp.1 --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: as-npcp1-harvest-latex-exercises-stabilize-brief.md | claimed status: deferred | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY/agent_skills' create '[brief] as vhz4 build basic briefed' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "as-vhz4-build-basic-briefed-brief.md"}' --deps as-vhz4 --notes 'VERDICT: ACCEPT | AUTHORIZER: Taylor (Q18) | RATIONALE: ACCEPT — read-only census delivered all 6 REQs; G4 cross-workflow (as-3p6o stamps) accepted. Key finding: rig is 960MB vs 64MB in repos; 181 drained dirs + 304 skills missing from gt; wipe-vs-clean-restore decision deferred to Taylor with fresh evidence. as-3p6o/as-zjn0 should be cancelled. Follow-up beads needed: hygiene violations, port drift, AGENTS lag, gt-pr6. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/agent_skills' close '<NEW-ID>' --reason 'ACCEPT (migrated verbatim from as-vhz4-build-basic-briefed-brief.md)'
bd -C '$CITY/gascity-packs' create '[brief] build basic worktree gated gsp 5lum7' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "build-basic-worktree-gated-gsp-5lum7-brief.md"}' --deps gsp-5lum7 --notes 'VERDICT: FIX-THEN-MERGE | AUTHORIZER: Taylor (Q18) | RATIONALE: A — FIX-THEN-MERGE: (1) fix RR-6: all 5 $WORKTREE/.git/hooks/pre-commit occurrences in prepare-worktree.md → resolve via ACTUAL_GIT_DIR=$(git -C \"$WORKTREE\" rev-parse --git-dir); (2) add brief-emission terminal step like build-basic-briefed; (3) add linked-worktree test case; then merge. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/gascity-packs' close '<NEW-ID>' --reason 'FIX-THEN-MERGE (migrated verbatim from build-basic-worktree-gated-gsp-5lum7-brief.md)'
bd -C '$CITY/gascity' create '[brief] gc rig add repo dot git gitignore gs ab5v' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "gc-rig-add-repo-dot-git-gitignore-gs-ab5v-brief.md"}' --deps gs-ab5v --notes 'VERDICT: APPROVE | AUTHORIZER: Taylor (Q19) | RATIONALE: APPROVE — but route through PR pipeline, not manual Taylor filing. Branch needs rebase onto upstream first (90 commits behind; gitignore.go clean in those commits). Use mol-pr-from-issue or PR pipeline formula. (Taylor Q19 2026-07-19)' --silent
bd -C '$CITY/gascity' close '<NEW-ID>' --reason 'APPROVE (migrated verbatim from gc-rig-add-repo-dot-git-gitignore-gs-ab5v-brief.md)'
bd -C '$CITY' create '[brief] gh 38 decisions track classifier verify close' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "gh-38-decisions-track-classifier-verify-close-brief.md", "mathcity.brief.unresolved_artifact": "gh-issue-38"}' --silent
bd -C '$CITY/gascity' create '[brief] gs 8oix build briefed fix rig gitignore' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "gs-8oix-build-briefed-fix-rig-gitignore-brief.md"}' --deps gs-8oix --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: gs-8oix-build-briefed-fix-rig-gitignore-brief.md | claimed status: adjudicated | recorded verdict: APPROVE-via-PR-pipeline' --silent
# SKIP gs-nduq-investigate-brief.md: bead gs-0hd8 already exists (frontmatter names it)
bd -C '$CITY/gascity-packs' create '[brief] gsp 3sbra mathlib quality adjudication' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "gsp-3sbra-mathlib-quality-adjudication-brief.md"}' --deps gsp-3sbra --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: gsp-3sbra-mathlib-quality-adjudication-brief.md | claimed status: adjudicated | recorded verdict: (no typed verdict field)' --silent
# SKIP gsp-71p9fz-approach-a-blast-radius.md: bead gsp-9sf5io already exists (frontmatter names it)
bd -C '$CITY/gascity-packs' create '[brief] gsp 78owq catch no brainer v02 fixture briefs 789' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "gsp-78owq-catch-no-brainer-v02-fixture-briefs-789-brief.md"}' --deps gsp-78owq --notes 'VERDICT: DEFER-POLICY-FIRST | AUTHORIZER: Taylor (Q19) | RATIONALE: DEFER — build a no-brainer policy from Q18/Q19 session collection first, then build formula/skill off it. Track today'"'"'s no-brainers as we go. Approve after policy is codified. (Taylor Q19 2026-07-19)' --silent
bd -C '$CITY/gascity-packs' close '<NEW-ID>' --reason 'DEFER-POLICY-FIRST (migrated verbatim from gsp-78owq-catch-no-brainer-v02-fixture-briefs-789-brief.md)'
bd -C '$CITY/gascity-packs' create '[brief] gsp kmtpl quimby prompt standing rules' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "gsp-kmtpl-quimby-prompt-standing-rules-brief.md"}' --deps gsp-kmtpl --notes 'VERDICT: SUPERSEDE | AUTHORIZER: Taylor (Q18) | RATIONALE: SUPERSEDE — duplicate of gsp-r0ju5 (already APPROVED Q18 2026-07-18, assigned to gc.publisher). Same push scope; two publishers would conflict. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/gascity-packs' close '<NEW-ID>' --reason 'SUPERSEDE (migrated verbatim from gsp-kmtpl-quimby-prompt-standing-rules-brief.md)'
# SKIP gsp-nq3ut1-brief.md: bead gsp-ficcsn already exists (frontmatter names it)
bd -C '$CITY/gascity-packs' create '[brief] gsp r0ju5 recover quimby standing rules' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "gsp-r0ju5-recover-quimby-standing-rules-brief.md"}' --deps gsp-r0ju5 --notes 'VERDICT: APPROVE | AUTHORIZER: Taylor (Q18) | RATIONALE: APPROVE — push mathcity-mayor (6 commits) and merge/push hecke polecat/he-tu7e.4. Pre-push backup saved at restart/PROMPT-mayor-restart.j2.bak-pre-standing-rules. NOTE: hecke push requires gt-njkknn clearance — publisher should verify gt-pvx status before pushing hecke remote. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/gascity-packs' close '<NEW-ID>' --reason 'APPROVE (migrated verbatim from gsp-r0ju5-recover-quimby-standing-rules-brief.md)'
bd -C '$CITY/gascity-packs' create '[brief] gsp wgfty q5q6q7 design' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "gsp-wgfty-q5q6q7-design-brief.md"}' --deps gsp-wgfty --silent
bd -C '$CITY/gascity-packs' create '[brief] gsp wmvvs manifest triage filter' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "gsp-wmvvs-manifest-triage-filter-brief.md"}' --deps gsp-wmvvs --notes 'VERDICT: APPROVE | AUTHORIZER: Taylor (Q19) | RATIONALE: APPROVE — ship manifest-triage-filter. Note: skill must live under mathcity subdomain (not bare mathcity root). user_skill_touching_override acknowledged. (Taylor Q18/Q19 2026-07-19)' --silent
bd -C '$CITY/gascity-packs' close '<NEW-ID>' --reason 'APPROVE (migrated verbatim from gsp-wmvvs-manifest-triage-filter-brief.md)'
bd -C '$CITY/gascity-packs' create '[brief] gsp z4u0i' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "gsp-z4u0i-brief.md"}' --deps gsp-z4u0i --silent
# SKIP gt-1f2781-downstream-filter-rule-empty-assignee-after-verified-sling-brief.md: bead gt-1f2781 already exists (frontmatter names it)
# SKIP gt-2vv2u0-upstream-repair-empty-assignee-after-verified-sling-brief.md: bead gt-2vv2u0 already exists (frontmatter names it)
bd -C '$CITY' create '[brief] gt ggcuot build repair formula design' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "gt-ggcuot-build-repair-formula-design.md"}' --deps gt-ggcuot --silent
bd -C '$CITY/hecke' create '[brief] he 1fl30 readme tests bart' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "he-1fl30-readme-tests-bart-brief.md"}' --deps he-1fl30 --notes 'VERDICT: ACCEPT | AUTHORIZER: Taylor (Q18) | RATIONALE: ACCEPT — 49/50 README-tests PASS on polecat/he-tu7e.4 (f55dfc7c); BART 10-commit series touched zero Magma source files; 1 FAIL = test-32-cremona pre-existing hang. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/hecke' close '<NEW-ID>' --reason 'ACCEPT (migrated verbatim from he-1fl30-readme-tests-bart-brief.md)'
bd -C '$CITY/hecke' create '[brief] he 3w0eu delete bad snf gamma0' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "he-3w0eu-delete-bad-snf-gamma0-brief.md"}' --deps he-3w0eu --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: he-3w0eu-delete-bad-snf-gamma0-brief.md | claimed status: adjudicated-approved-option-b | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY/hecke' create '[brief] he a9cfa' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "he-a9cfa-brief.md"}' --deps he-a9cfa --notes 'VERDICT: C | AUTHORIZER: QUIMBY 18 (Taylor) | RATIONALE: CHANGES REQUIRED — pre-dispatch-check.sh line 112 calls `gt mail send` (deprecated gastown CLI); must be `gc mail send`. Hygiene policy violation caught by /check-plan-hygiene. Fix and re-submit.' --silent
bd -C '$CITY/hecke' close '<NEW-ID>' --reason 'C (migrated verbatim from he-a9cfa-brief.md)'
bd -C '$CITY/hecke' create '[brief] he ckilh dispatch gate' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "he-ckilh-dispatch-gate.md"}' --deps he-ckilh --silent
bd -C '$CITY/hecke' create '[brief] he el1s5 gamma0 backup n0' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "he-el1s5-gamma0-backup-n0-brief.md"}' --deps he-el1s5 --notes 'VERDICT: CLOSE-CONFIRMED | AUTHORIZER: Taylor (Q18) | RATIONALE: recorded in he-el1s5-gamma0-backup-n0-brief.md' --silent
bd -C '$CITY/hecke' close '<NEW-ID>' --reason 'CLOSE-CONFIRMED (migrated verbatim from he-el1s5-gamma0-backup-n0-brief.md)'
bd -C '$CITY/hecke' create '[brief] he g6uo7 n1 5 dry run snf audit build' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "he-g6uo7-n1-5-dry-run-snf-audit-build-brief.md"}' --deps he-g6uo7 --notes 'VERDICT: ARCHIVE+FILE-RECOVERY-TASK | AUTHORIZER: Taylor (Q18) | RATIONALE: Option B: archive N1.5 as complete; file recovery bead for dangling commits 515a4904+0b3dfed6 (xargs-P dry-run script) before git gc prunes them. Recovery bead he-ze1hy filed; dispatched via build-basic-briefed workflow he-71r0l. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/hecke' close '<NEW-ID>' --reason 'ARCHIVE+FILE-RECOVERY-TASK (migrated verbatim from he-g6uo7-n1-5-dry-run-snf-audit-build-brief.md)'
# HOLD he-hsoc-check-latex-acceptance-brief.md: decision bead(s) he-2jp5 already name this file's artifact in their title -- confirm before creating
# HOLD he-ipwws-brief.md: decision bead(s) gt-6sta0h already name this file's artifact in their title -- confirm before creating
bd -C '$CITY/hecke' create '[brief] he q5nah gamma0 repair hold' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "he-q5nah-gamma0-repair-hold-brief.md"}' --deps he-q5nah --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: he-q5nah-gamma0-repair-hold-brief.md | claimed status: adjudicated | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY/hecke' create '[brief] he sraxz gamma0 snf audit' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "he-sraxz-gamma0-snf-audit-brief.md"}' --deps he-sraxz --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: he-sraxz-gamma0-snf-audit-brief.md | claimed status: adjudicated | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY/hecke' create '[brief] he wjfo2 n1 5gate smoke test' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "he-wjfo2-n1-5gate-smoke-test-brief.md"}' --deps he-wjfo2 --notes 'VERDICT: CLOSE-CONFIRMED | AUTHORIZER: Taylor (Q18) | RATIONALE: CLOSE-CONFIRMED no-brainer — he-wjfo2 already CLOSED; sub-questions A1/A5 moot post-delete (bad-SNF Z[i] 2.1 records deleted via he-vdcjs); canonical PERT has moved past N2s. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/hecke' close '<NEW-ID>' --reason 'CLOSE-CONFIRMED (migrated verbatim from he-wjfo2-n1-5gate-smoke-test-brief.md)'
bd -C '$CITY/hecke' create '[brief] he xkm7u 335 repair dispatch inject' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "he-xkm7u-335-repair-dispatch-inject-brief.md"}' --deps he-xkm7u --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: he-xkm7u-335-repair-dispatch-inject-brief.md | claimed status: adjudicated-close-confirmed-pending-sample | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY/homog' create '[brief] ho 6vx git hygiene cleanup' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "ho-6vx-git-hygiene-cleanup-brief.md"}' --deps ho-6vx --notes 'VERDICT: APPROVE | AUTHORIZER: Taylor (Q18) | RATIONALE: APPROVE — no-brainer; edf867a already on origin/master, all 3 review lanes PASS, push=false/open_pr=false. Close ho-6vx. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/homog' close '<NEW-ID>' --reason 'APPROVE (migrated verbatim from ho-6vx-git-hygiene-cleanup-brief.md)'
bd -C '$CITY/jacobi' create '[brief] ja frp git hygiene cleanup' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "ja-frp-git-hygiene-cleanup-brief.md"}' --deps ja-frp --notes 'VERDICT: APPROVE | AUTHORIZER: Taylor (Q18) | RATIONALE: recorded in ja-frp-git-hygiene-cleanup-brief.md' --silent
bd -C '$CITY/jacobi' close '<NEW-ID>' --reason 'APPROVE (migrated verbatim from ja-frp-git-hygiene-cleanup-brief.md)'
bd -C '$CITY/lmfdb' create '[brief] lm p0z gitignore gascity block build result' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "lm-p0z-gitignore-gascity-block-build-result-brief.md"}' --deps lm-p0z --notes 'VERDICT: APPROVE | AUTHORIZER: Taylor (Q18) | RATIONALE: recorded in lm-p0z-gitignore-gascity-block-build-result-brief.md' --silent
bd -C '$CITY/lmfdb' close '<NEW-ID>' --reason 'APPROVE (migrated verbatim from lm-p0z-gitignore-gascity-block-build-result-brief.md)'
# SKIP producer-repair-unknown-unknown-unknown-rejection-reason-not-machine-extractable-from-rejection.md: bead gsp-hlr8d5 already exists (frontmatter names it)
# HOLD sandbox-shell-commands-in-steps.md: decision bead(s) he-tbmq0 already name this file's artifact in their title -- confirm before creating
bd -C '$CITY' create '[brief] skill invocation contract policy skills' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "skill-invocation-contract-policy-skills.md", "mathcity.brief.unresolved_artifact": "72-skill-invocation-contract-policy-skills-brief.md"}' --notes 'UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) | stack_file: skill-invocation-contract-policy-skills.md | claimed status: revise | recorded verdict: (no typed verdict field)' --silent
bd -C '$CITY/tdupu_github_io' create '[brief] tgi 30g' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "tgi-30g-brief.md"}' --deps tgi-30g --notes 'VERDICT: ACCEPT | AUTHORIZER: Taylor (Q18) | RATIONALE: ACCEPT — no-brainer; build tgi-k9gy is redundant confirmation; tgi-30g already CLOSED via tgi-30qh (commits 84b08f4 + 8b8d423). tgi-n5jp credential rotation P1 still open. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/tdupu_github_io' close '<NEW-ID>' --reason 'ACCEPT (migrated verbatim from tgi-30g-brief.md)'
bd -C '$CITY/tdupu_github_io' create '[brief] tgi 30qh untrack gascity' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "tgi-30qh-untrack-gascity-brief.md"}' --deps tgi-30qh --notes 'VERDICT: APPROVE | AUTHORIZER: Taylor (Q18) | RATIONALE: APPROVE — execution confirmed; commits 84b08f4 + 8b8d423 verified on origin/master. Privacy fix live. tgi-30g closes. OQ-1 (filter-repo) and OQ-2 (credential rotation tgi-n5jp) tracked as follow-up. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/tdupu_github_io' close '<NEW-ID>' --reason 'APPROVE (migrated verbatim from tgi-30qh-untrack-gascity-brief.md)'
bd -C '$CITY/tdupu_github_io' create '[brief] tgi d1k' -t decision --metadata '{"mathcity.brief.materialized_by": "beadless-brief-materialization-2026-08-19", "mathcity.brief.stack_file": "tgi-d1k-brief.md"}' --deps tgi-d1k --notes 'VERDICT: SUPERSEDE | AUTHORIZER: Taylor (Q18) | RATIONALE: SUPERSEDE — verified live: origin/master already at 8b8d423 (tgi-30qh pushed first). tgi-d1k push base 15a387d is 2 commits behind; push would fail non-fast-forward. Privacy fix already live via tgi-30qh. 557-file course removal (7bce233) was out-of-scope; defer separately if needed. (Taylor Q18 2026-07-18)' --silent
bd -C '$CITY/tdupu_github_io' close '<NEW-ID>' --reason 'SUPERSEDE (migrated verbatim from tgi-d1k-brief.md)'

# rollback
# bd -C $CITY/agent_skills list --json --status all | jq -r '.[] | select(.metadata."mathcity.brief.materialized_by" == "beadless-brief-materialization-2026-08-19") | .id' | xargs -r -n1 bd -C $CITY/agent_skills delete --force
# bd -C $CITY/gascity list --json --status all | jq -r '.[] | select(.metadata."mathcity.brief.materialized_by" == "beadless-brief-materialization-2026-08-19") | .id' | xargs -r -n1 bd -C $CITY/gascity delete --force
# bd -C $CITY/gascity-packs list --json --status all | jq -r '.[] | select(.metadata."mathcity.brief.materialized_by" == "beadless-brief-materialization-2026-08-19") | .id' | xargs -r -n1 bd -C $CITY/gascity-packs delete --force
# bd -C $CITY list --json --status all | jq -r '.[] | select(.metadata."mathcity.brief.materialized_by" == "beadless-brief-materialization-2026-08-19") | .id' | xargs -r -n1 bd -C $CITY delete --force
# bd -C $CITY/hecke list --json --status all | jq -r '.[] | select(.metadata."mathcity.brief.materialized_by" == "beadless-brief-materialization-2026-08-19") | .id' | xargs -r -n1 bd -C $CITY/hecke delete --force
# bd -C $CITY/homog list --json --status all | jq -r '.[] | select(.metadata."mathcity.brief.materialized_by" == "beadless-brief-materialization-2026-08-19") | .id' | xargs -r -n1 bd -C $CITY/homog delete --force
# bd -C $CITY/jacobi list --json --status all | jq -r '.[] | select(.metadata."mathcity.brief.materialized_by" == "beadless-brief-materialization-2026-08-19") | .id' | xargs -r -n1 bd -C $CITY/jacobi delete --force
# bd -C $CITY/lmfdb list --json --status all | jq -r '.[] | select(.metadata."mathcity.brief.materialized_by" == "beadless-brief-materialization-2026-08-19") | .id' | xargs -r -n1 bd -C $CITY/lmfdb delete --force
# bd -C $CITY/tdupu_github_io list --json --status all | jq -r '.[] | select(.metadata."mathcity.brief.materialized_by" == "beadless-brief-materialization-2026-08-19") | .id' | xargs -r -n1 bd -C $CITY/tdupu_github_io delete --force
```

---

## 8. What I could not determine

1. **Whether the 9 HOLD rows are duplicates.** §5b gives the evidence per row.
   `gt-57dccr` and `he-tbmq0` read as near-certain duplicates; `gsp-eejju` and
   `gt-6sta0h` read as near-certain non-duplicates; the five sharing
   `gsp-0bf29` are genuinely undecidable from here — five stack files name one
   subject, and whether that is one decision or five is a judgement about the
   work, not about the data.
2. **Whether the 28 tier-B claims are true adjudications.** A `status:
   adjudicated` with no authorizer and no date could be a real verdict whose
   fields were never written, or a producer's optimistic default. Nothing in
   the file distinguishes them. This is the same open question §2 of
   `BRIEF-SYSTEM-REWORK-STATE-2026-08-19.md` records for `close_reason`, and it
   needs the same ruling.
3. **The right title format.** Titles are derived from the slug
   (`[brief] he xkm7u 335 repair`) because 81 of 89 files open with the identical
   heading `§1 What is being decided` and 3 more with a shared `[UNPREPPED …]`
   banner — bodies identify almost nothing. A slug-derived title is
   machine-stable but reads poorly. If the owner wants readable titles,
   that is a per-file human pass, not something to infer.
4. **Whether `--external-ref` is the right home for the 3 `gh-issue-N` files and
   the 1 git-sha file.** The flag exists and its help text gives `gh-9` as the
   example, but I did not exercise it, so it is a recommendation and not in the
   emitted commands (§2).
5. **`priority`.** 47 files carry a `priority:` and 60 an `unlock_count:`, and
   B2.5 orders the pile by unlock count computed live from the dependency
   graph. Whether the file's stale recorded values should be transcribed onto
   the bead, or recomputed after the links exist, is a design question for the
   presenter, not a migration question. The plan writes neither; every bead is
   created at bd's default P2.
6. **Whether the 3 `task2a-live-*` canaries and the `producer-repair-unknown-…`
   file should be materialised at all.** They are test fixtures
   (`test_only: true`, `runtime_canary: true`) that D4 nonetheless says to
   migrate in. They are planned as CREATE, but a ruling to exclude fixtures
   would be reasonable and would take the count to 70 CREATE.
7. **Which store `mathcity`/`cliff-part2`/`magma_*`/`differential_valuations`
   briefs would go to.** No stack file references them, so the placement rule
   is untested for those prefixes. It is written to work; it is not measured.

---

## 9. Provenance

Measured 2026-08-19 against the live city (`gc dolt` up; `bd list` reads only)
across 19 candidate store paths, 53 195 beads read. The corpus snapshot at
`~/Downloads/mathcity-corpus-snapshot-2026-08-19/` was used only to cross-check
the 280 decision-bead total; it covers 5 rigs and decision beads only, and §2
explains why resolving `artifact:` references against it produces the wrong
answer.

Command shapes were verified on throwaway stores created by `bd init` under
`mktemp -d` (embedded Dolt, no server) and deleted immediately; the probes
covered `dep add` cross-store behaviour, `create --deps`, `--metadata`
round-trip, `--notes` round-trip through `verdicts.read_verdict_reading`,
duplicate-title creation, and `delete --force`.

**No live bead was created, updated, closed, deleted, or linked.**

Planner: `assets/scripts/mctl_core/materialize_plan.py` — no `subprocess`, no
`os`, no import of `mctl_core.beads` (which carries a write path), no file-write
call; `tests/mctl/test_materialize_plan.py` asserts each of those by parsing the
module's AST rather than grepping it.
