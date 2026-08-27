# Brief-System POLICY.md — drift audit, 2026-08-19

> ### ⚠ SUPERSEDED IN PART — `MBRF004` severity, corrected 2026-08-27
>
> This audit is a **dated snapshot and is preserved unedited below.** One of
> its findings has since been overtaken by the code and must not be quoted as
> current:
>
> **§B2.1 row (line 79) and §"Blast radius" (line 196) state that `MBRF004` is
> `Severity.ERROR` and therefore gates `adjudicate` / `defer` /
> `dispatch-work` on 88 healthy pending briefs. That is no longer true.**
> `#137` downgraded it. `mctl_core/briefs.py:1652` emits `MBRF004` at
> **`Severity.WARN`**, and `_blocking_diagnostic` (`briefs.py:2124`) selects
> only `ERROR`/`FATAL`, so no mutation blocks on it. Measured 2026-08-27 across
> all 18 registered rigs: `MBRF004` fires on **149 distinct brief beads** and
> blocks **0**. On the same day, **17** bead-backed briefs across 4 rigs
> returned `adjudicate: enabled=true, disabled_reason=null`.
>
> The audit's open question 3 (line 533) — *"whether `MBRF004` blocks
> adjudication on exactly 88 pending briefs"* — is therefore **answered: it
> blocks none.** Its other findings were not re-verified in this pass and
> retain whatever status they had.
>
> A session that treats `MBRF004` as a queue filter on the strength of this
> document will empty the queue and wrongly report nothing to adjudicate. See
> `tdupu/mathcity#234` and the correction comment on bead `mc-nywhr`.

**Status:** analysis only, uncommitted. **Nothing was mutated** — no bead, no
POLICY.md edit, no file in `<city-root>/.beads/`, no service touched. Every
`bd` invocation was a read (`bd list`, `bd show`, `bd export`); every
filesystem operation was a read or a count.

**Target:** `subdomains/brief-system/POLICY.md` (770 lines, header
`Status: Adopted (2026-07-12)`, last content commit `37b0413` 2026-08-16),
read in full before any measurement.

---

## 0. Method, and what "measured" means here

Three evidence classes are used, and every claim below is tagged:

- **MEASURED** — I ran the count/regex/query myself in this session and can
  reproduce the command.
- **CORROBORATED** — measured independently by a second agent in this session
  (bead-store population) or by a pre-existing dated analysis in-tree
  (`subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md`), and I did not
  re-derive it a third time.
- **INFERRED** — reasoning over code I read, not an observation of runtime.
  Called out inline every time.

**Live population snapshots taken 2026-08-19:**

| thing | count | how |
|---|---|---|
| `type=decision` beads, 4 stores (`<city-root>` HQ, hecke, gascity-packs, differential_valuations) | 264 | `bd -C <dir> list --type decision --all --flat --limit 0 --json`, cross-checked against `bd export` |
| …closed | 137 | same |
| …closed **with** a typed verdict field | **9** (7 non-test) | `metadata.verdict`; **zero** top-level `verdict`/`decision`/`recorded_verdict` exist in the schema at all |
| …closed with non-empty `close_reason` | **137 / 137** | same |
| decision beads with ≥1 dependency edge of *any* type | 60 / 264 | per-bead `bd show --json` (`bd list --json`'s `dependency_count` scalar is broken; its `dependencies` array is not) |
| …with a blocking/depends-on-type edge | **1 / 264** | edge-type histogram: `related` 508, `relates-to` 15, `parent-child` 3, `supersedes` 1, `discovered-from` 1 |
| `<city-root>/.beads/briefs/stack/*.md` | 89 | `ls` |
| `<city-root>/.beads/briefs/stack/.index.jsonl` rows | 88 (0 malformed) | `wc -l` + json parse |
| stack files **absent from** the index | **41** | set difference |
| index rows pointing at a **missing** file | **40** | set difference |
| stack files with a canonical `Gate Evidence` heading | 43 | `brief-shuffle-fast-drain.py`'s own `GATE_EVIDENCE_HEADING` regex |
| `<city-root>/.beads/briefs/.pile/` entries | 68 total = **5** `*.md` + **56** `*.md.bak` + 7 dirs | `ls` |
| `.pile/.rejected/` entries | 63 | `ls` (most recent 2026-08-17, G9 failure) |

---

## 1. Rule-by-rule table

Enforcer shorthand:

| tag | what it is | where it runs |
|---|---|---|
| `fast-drain` | `assets/scripts/brief-shuffle-fast-drain.py` — fail-closed `.pile → stack` gate evaluator | order `brief-shuffle-fast-drain`, pool `mathcity.brief-operator`, live (63 rejections on disk) |
| `mctl-doctor` | `mctl_core/briefs.py::_doctor_briefs` → `MBRF001–008/020/021` | `mctl briefs doctor/validate`; **also blocks** `adjudicate`/`defer`/`dispatch-work` via `_blocking_preconditions` |
| `mctl-create` | `mctl_core/briefs.py::validate_brief_input` + `effects.py` → `MBRF030–035` | `mctl briefs create` |
| `mctl-adjudicate` | `effects.py::plan_adjudication` — writes `metadata.verdict`, `verdict_reason`, `adjudicated_at`, sets `status=closed` | `mctl briefs adjudicate` |
| `brief-check` | `assets/scripts/checks/brief-check.sh`, reached via `brief-mechanical-gates-required.sh` from `formulas/brief-gate-keep.toml` | **hecke only** — `.gc/scripts/checks/` exists in no other rig and not at `<city-root>` |
| `check-brief-policy` | on-demand agent skill, `subdomains/brief-system/skills/check-brief-policy/` | only when a human/agent invokes it |
| `presenter` | `skills/present-briefs` selector + mandatory bead filter | only when a human/agent invokes it |
| **NONE** | prose in a SKILL.md instructing an agent to self-reject | no machine ever checks it |

### Pillar 1 — production (B1.x)

| rule | still true? | enforced by | contradicted by | conf |
|---|---|---|---|---|
| **B1.1** Decision-at-Top | **mostly** — 79/89 stack files open with "what is being decided"/`DECISION:` (heuristic regex; 10 misses are mostly test canaries) | **NONE mechanical.** `MBRF030` carries `policy_ref="B1.1"` but only checks *empty title* — the label is aspirational | — | HIGH (measured) |
| **B1.2** One decision per brief | unverifiable at scale | **NONE** | — | LOW |
| **B1.3** Compact form is gated | **NO.** 19 stack files are `form: compact`; **18 of them carry zero no-brainer classifier evidence** (no `classifier_state`, no `no_brainer*` key) | **NONE** for files that never went through `fast-drain` — and 41/89 didn't | live stack | HIGH (measured) |
| **B1.4** All profile gates have evidence or N/A | **NO.** 46/89 stack files have no `Gate Evidence` section at all | `fast-drain` (fail-closed, real) + `brief-check` (hecke) — but only on the `.pile → stack` path | 41 stack files that bypassed that path | HIGH (measured) |
| **B1.5** No follow-up questions / fresh claims | unverifiable at scale | `stale-claim-check.sh` exists for G13; `MBRF031` claims `policy_ref="B1.5"` but only checks *empty body* | — | MED |
| **B1.6** External review before deposit (G4) | unknown | `fast-drain` for `standard` profile only; **G4 is absent from the `decision`, `lost_bead_filter`, `producer_repair` profiles**, which is most live traffic | gates.toml profiles | MED |
| **B1.7** Bookkeeping (G8) | **NO.** **1 of 89** stack files carries `brief_bead:`. The file↔bead join B1.7/G8 asserts is effectively absent from the live stack | `mctl-doctor` on the bead side; `fast-drain`/`brief-check` only check that a `G8 …: PASS` *string* is present | live stack | HIGH (measured) |
| **B1.8** Specialized evidence per rule set | partial | gate-level only | — | LOW |

### Pillar 2 — lifecycle (B2.x)

| rule | still true? | enforced by | contradicted by | conf |
|---|---|---|---|---|
| **B2.1** brief = `type=decision` + source link | **The definition is wrong in both directions.** (a) `Bead.is_brief` is literally `issue_type == "decision"` with no discriminator, so 88 push-authorization receipts, 44 policy decisions, 6 handoff records and 1 throwaway test bead are all "briefs" to the implementation — only **44/264 (16.7%)** carry any `brief_*` metadata. (b) 204/264 have zero dependency edges; **1/264** has a blocking-type edge | `mctl-doctor` `MBRF004` (ERROR, fires 146×) + `mctl-create` `MBRF034` (WARN) | POLICY.md's own Definitions paragraph exempts push authorizations — the implementation has no way to apply that exemption | HIGH (corroborated) |
| **B2.2** adjudicated ⇔ verdict fields recorded **and** closed | **NO, by a wide margin.** 137 closed; **9 (6.6%)** carry a typed verdict, 7 non-test. 100% carry `close_reason`, which `_verdict()` does not read. Of the 7 real typed verdicts, **2 are wrong**: `he-9bma` outright contradicts its cited `close_reason`; `he-an64` holds a superseded *initial* verdict. (`he-8hoo` is **lossy, not contradictory** — the pre-audit report was wrong about that one.) B2.2 also names **authorizer** as a required field; `mctl-adjudicate` never writes one | `mctl-doctor` `MBRF005`; `mctl-adjudicate` writes the fields going forward | the entire historical population; `close_reason` as de-facto verdict channel | HIGH (corroborated) |
| **B2.3** No resurface after adjudication | **nominally enforced, inert in practice.** `present-briefs` mandates a canonical bead filter keyed on `brief_bead:` else `artifact:` — but **1/89** files carry `brief_bead:`, and an `artifact:` is usually a *work* bead, which the skill's own rule says to **keep** when unknown. So the bead filter is a no-op for ~88/89. Meanwhile **33 stack files carry `status: adjudicated`** and are dropped only by a hardcoded frontmatter-string blocklist | `presenter` (string blocklist, real); `mctl-doctor` `MBRF006` | present-briefs' own "keep unknown ids" rule | HIGH (measured) |
| **B2.4** One fixed pile | **NO.** At least 4 concurrent pile locations hold `*.md`: `<city-root>/.beads/briefs/.pile` (5), `<city-root>/lmfdb/.beads/briefs/.pile` (1), `<city-root>/gascity-packs/.beads/briefs/.pile` (4), plus `.pile/.no-brainer` (6). `create-brief` additionally sanctions `<city-root>/.beads/briefs/.escalation-drop/` (does not currently exist) | `mctl-create` `MBRF032` blocks *label*-requested side piles only | Q5 resolution (per-rig storage) — which makes multiple piles **correct** and B2.4 the stale text | HIGH (measured) |
| **B2.5** Ordering = unlock_count computed live | **NO.** Both `check-briefs` and `present-briefs` read `unlock_count` from **frontmatter**, defaulting to 0. B2.5's own mechanical check ("computes unlock_count from live dependency data at presentation time") is not implemented anywhere. 29/89 stack files have no `unlock_count` at all; 27 more have `0` | `presenter` sorts, but on a static field | B2.5's stated mechanical check | HIGH (measured) |
| **B2.6** Clump like a court docket (≥3 → cohort) | **NO.** Zero occurrences of `cohort` or `docket` in any `.py`, `.sh`, `.toml` under `assets/`, `formulas/`, `orders/`, and none in `present-briefs` | **NONE** | present-briefs presents strictly one at a time | HIGH (measured) |
| **B2.7** Defer is first-class and timed | **YES.** `mctl briefs defer` writes `defer_until` + `status: deferred`; `_defer_until()` and `_decision_state()` honour it; presenter skips future `defer_until` | `mctl` + `presenter` + `MBRF007` | — | HIGH |
| **B2.8** Bead canonical, files regenerable cache | **the principle holds in mctl; the filesystem is far out of sync.** 41 stack files not in the index, 40 index rows with no file, 56 `.md.bak` in a 68-entry pile. `effects.py::_require_brief_root` refuses to create under an unresolvable root (`MBRF035`) and its docstring **states the contradiction in the source**: *"the live city keeps its brief tree at the city root, and the shuffler never reads paths.toml at all… which root is correct is an open policy question"* | `mctl-doctor` `MBRF001/011/020/021`; `mctl-create` `MBRF035` | `paths.toml` (rig-relative) vs live tree (city-root) vs `check-briefs`/`present-briefs` (hardcode `$CITY_ROOT`/`$HOME/gt`) | HIGH (measured) |
| **B2.9** Auto-executed briefs are still adjudicated | **vacuously true — nothing auto-executes.** No executor anywhere reads `auto_merge_enabled`; the only readers are `brief-check.sh` and the `check-brief-policy` skill, both of which *audit* rather than execute | **NONE** (no executor exists) | N5's "executor check order" names a component that does not exist | HIGH (measured) |
| **B2.10** Unified pipeline, `fast-drain` sole `.pile → stack` writer | **half true.** The legacy `brief-shuffle-pile` order is retired (`check = "false"`), so there is one *registered* writer. But **41/89 stack files have neither an index row nor a Gate Evidence section**, so they cannot have come through `fast-drain` — and `create-brief`'s escalation lane **explicitly instructs** "Write the file to the stack path directly" | `fast-drain` (for traffic that uses it); `mctl-doctor` `MBRF008/013` for legacy-track suppression | `create-brief` escalation lane; 41 live files | HIGH (measured) |

### Pillar 3 — closure (B3.x) and Pillar 4 — Magma (B4.x)

| rule | still true? | enforced by | contradicted by | conf |
|---|---|---|---|---|
| **B3.1** Closure requires verifiable acceptance | unverifiable | **NONE** | — | LOW |
| **B3.2** `HUMAN_OK_REQUIRED` authorization **before** close | plausible (88 authorization receipts exist as standalone beads) | **NONE mechanical**; `authorize-git-operation` skill records the bead | — | LOW |
| **B3.3** Don't orphan downstream on close | **NONE** — and note `bd list --json` cannot see reverse edges at all, so the check is not currently constructible from mctl's reader | **NONE** | mctl's reader limitation | MED |
| **B3.4** Cross-repo self-close | — | **NONE** | — | LOW |
| **B3.5** Convoy close requires all members terminal | — | **NONE** in this pack | — | LOW |
| **B3.6** All-closed check never skipped for auto-merge | vacuous — no auto-merge executor | **NONE** | — | HIGH |
| **B3.7** Research beads never destructively closed | — | **NONE** in this pack (bead-policy may cover it; PP6.1 assigns taxonomy there) | — | LOW |
| **B3.8** Adjudicated briefs close with their verdict | **NO** — same population as B2.2 | `mctl-doctor` `MBRF005` | 128/137 closed beads | HIGH |
| **B4.1–B4.6** Magma package discipline | surfaces are real (1235 `package-*.mag` under hecke; all four B4.4 certify intrinsics exist in `package-certify.mag`) | **NONE** in this pack — no check script, formula, or test references B4.1/2/4/5/6 | — | MED |

### N-rules

| rule | still true? | enforced by | contradicted by | conf |
|---|---|---|---|---|
| **N1** Classifier, not producer, classifies | **NO** on the live stack — 18/19 compact briefs have no classifier evidence at all. `create-brief` also grants an explicit self-classification exemption ("You ARE authorized to self-classify G9 in this lane") | `fast-drain::classifier_error` (strict, real) for pile traffic | `create-brief` escalation lane | HIGH (measured) |
| **N2** Four categories + confidence | enforced where G9 runs — `fast-drain` validates the category against `no-brainer-categories.toml` and `confidence >= 0.85` | `fast-drain` | — | HIGH |
| **N3** Stop gates trump classification | enforced where G9 runs (`safety_blocked` must name `stop_gate=G5|G5b|L4`) | `fast-drain`, `brief-server-touching-safety.sh` | — | HIGH |
| **N4** Capability-blocker routes to resolution | **contradicted in writing.** `create-brief` §"Two input lanes" says: *"This resolves a standing conflict with catch-no-brainer… In this lane, `capability-blocker` means deposit here in full form"* — i.e. deposit, not route-to-resolution | `fast-drain` accepts `classifier_state=capability_blocker` as a valid promotable state | `create-brief` | HIGH (measured) |
| **N5** Auto-execute is the DEFAULT; kill switches are brakes | **NO — nothing auto-executes.** City switch `<city-root>/.beads/auto_merge_enabled` exists and reads `true` (= proceed); **no rig-level switch exists in any of 8 rigs** (= proceed). So by N5's own semantics automation is ON everywhere — and 19 compact-eligible briefs are sitting on the stack unexecuted. The "executor check order (1)(2)(3)" describes a component that does not exist | **NONE** (auditors only) | reality | HIGH (measured) |
| **N6** Surfacing a no-brainer is a regression; durable leak record | leak records exist (`no_brainer_leak` appears 1132× across `<city-root>/.beads/decisions-track/`) but only inside `manifest.jsonl` and its `.bak-*` snapshots | schema-level only | — | MED |
| **N7** Full audit trail incl. `confidence`/`category` on the bead | **NO** — `mctl-adjudicate` writes `verdict`, `verdict_reason`, `adjudicated_at`, `mctl_trace_id`, optional `verdict_option`. It writes neither `confidence` nor `category` nor an authorizer | **NONE** | `mctl-adjudicate`'s own metadata dict | HIGH (measured) |
| **N8** α measured from the ledger | **cannot be** — the ledger N8 depends on (N7's `confidence`/`category` on adjudicated brief beads) is never written | **NONE**; N8 itself says "once a replay harness exists" | N7's non-implementation | HIGH |
| **N9** Classifier evidence for every profile before stack promotion | true for `fast-drain` traffic; false for the 41 bypass files | `fast-drain` | 41 stack files | HIGH |

### L / E / T / D / S

| rule | still true? | enforced by | contradicted by | conf |
|---|---|---|---|---|
| **L1–L3** LaTeX gate fires / N/A / compile+review | plausible | `latex-gate-approval-required.sh` + `gates/latex-gate.toml` (hecke-installed) | — | MED |
| **L4** notes.tex never a no-brainer | enforced as a G9 `stop_gate=L4` token | `fast-drain` | — | HIGH |
| **T1** Test evidence = command+scope+result+date | enforced where the gate runs | `gate-test-evidence.sh`, `gates/test-evidence.toml`, `brief-check` `require_gate "G1 Test-evidence"` | — | HIGH |
| **T2** Base ref (G16) | enforced as a token only (`G16 Master-current: PASS|N/A`) — no checker reads an actual commit hash | `brief-check` token check | — | MED |
| **T3** Unrunnable tests declared | token-level | as T1 | — | MED |
| **T4** Test files name what they test | — | **NONE** | — | HIGH |
| **T5** PASS and FAIL both meaningful | — | **NONE** mechanical (`is-good-test` is a judgment skill) | — | HIGH |
| **T6** Good-test verdict (G2) | enforced in `standard`/`test_execution`/`experiment` profiles; **absent from `decision`, `lost_bead_filter`, `producer_repair`** | `fast-drain` for the profiles that include it | gates.toml profiles | HIGH |
| **T7** Tri-state never silent: `PASSED`/`NOT APPLICABLE`/`REQUIRED` | **NO — the mandated vocabulary is unrepresentable to both enforcers.** `fast-drain`'s `STATUS_PATTERN` matches `(PASS\|N/A\|FAIL\|BLOCKED\|PENDING)\b`; `brief-check`'s `require_gate` matches `(PASS\|N/A)\b`. Verified: `PASSED` fails the word boundary, `NOT APPLICABLE` matches nothing, `REQUIRED` matches nothing. A T7-conformant G14 entry is rejected as "missing required gate G14" | `fast-drain` + `brief-check` — enforcing a *different* vocabulary than T7 states | T7 vs both enforcers; `create-brief` documents the conflict and tells authors to write the failing token anyway | **HIGH (measured — regex executed)** |
| **D1/D2** README coverage + never silent | token-level (G10/G15) | `brief-check` | — | MED |
| **D3** README lands with the change | — | **NONE** | — | HIGH |
| **D4** Breadcrumbs (G11) | token-level | `brief-breadcrumb-required.sh` | — | MED |
| **S1–S6** Server-touching procedure | — | **NONE** mechanical for S2/S3/S4/S5/S6 | — | MED |
| **S7** G5 stops server-touching at the brief | enforced — `server_touching: true` makes `brief-server-touching-safety.sh` exit non-zero by design | `fast-drain`, `brief-server-touching-safety.sh` | — | HIGH |
| **PP6.1** brief-system ↔ bead-policy precedence | text-only | **NONE** | — | LOW |

---

## 2. Drift list — most consequential first

### D1. B2.2's "recorded verdict field" describes a channel almost nothing uses (**MEASURED / CORROBORATED**)

137 closed decision beads. **9** carry `metadata.verdict` (7 excluding self-labelled throwaway test artifacts); **137** carry `close_reason`. There is **no top-level `verdict`/`decision`/`recorded_verdict` field in the bd schema at all** — `_verdict()`'s first three lookups can never hit.

Consequence: `_decision_state()` classifies **74 closed brief beads as `malformed`** across hecke/gascity-packs/agent_skills, which is what `MBRF005` fires on. But per the in-tree triage
(`subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md`, §1.2–§2) **27 of those 74 carry a human-legible verdict in `close_reason` or `notes`**, and **39 of the 74 are not briefs at all** — 28 `authorize-git-operation` push receipts plus 11 standalone policy/math decisions, exactly the population B2.2's own Definitions section exempts.

And where the typed field *does* exist it is unreliable: of the 7 real ones, `he-9bma`'s `metadata.verdict` (`DISPATCH-AFTER-SANDBOX-RUNNER`) reverses its cited `close_reason` (`A-DISPATCH-NOW-WITH-Q-DEFAULTS`), and `he-an64` holds a superseded *initial* verdict. **Correction to the pre-audit report: `he-8hoo` is not a contradiction** — both sides say approve/Option A; the typed field is merely lossy.

**INFERRED root cause** (from bead descriptions, not from a code path): `metadata.verdict` appears to have been populated at brief-*creation* time from the brief's *recommendation*, while `close_reason` carries the later adjudicated verdict — the schema also carries a separate `metadata.recommended_verdict` (14 uses), so the two are conflated.

**Also measured:** `mctl briefs adjudicate` — the one compliant writer — records `verdict`, `verdict_reason`, `adjudicated_at`, `mctl_trace_id`. B2.2 requires four fields including **authorizer**. mctl never writes one. So even the conformant path is partially non-conformant with the rule it implements.

### D2. T7/G14's mandated vocabulary is rejected by every enforcer (**MEASURED — regex executed**)

```
STATUS_PATTERN = ^(.+?):\s*(PASS|N/A|FAIL|BLOCKED|PENDING)\b     # fast-drain
require_gate   = (PASS|N/A)\b                                     # brief-check.sh:220
```

`G14 Test-execution-silent: PASSED` → **NO MATCH** (word boundary).
`G14 Test-execution-silent: NOT APPLICABLE` → **NO MATCH**.
`G14 Test-execution-silent: REQUIRED` → **NO MATCH**.

A T7-conformant brief is therefore rejected as "missing required gate G14 Test-execution-silent". `create-brief` SKILL.md:139 already names this as a known defect and instructs authors to write the failing token anyway. The live stack shows the resulting deformation directly — one file reads:

`G14 Test-execution-silent: PASS** — **PASSED** (literal …`

i.e. an author writing both tokens to satisfy the machine and the policy at once. This is the single cheapest fix in the audit and it is a POLICY.md edit, not a code edit.

### D3. 41 of 89 stack files bypassed the pipeline entirely, and `create-brief` sanctions it (**MEASURED**)

Cross-tab of `<city-root>/.beads/briefs/stack/`:

| in `.index.jsonl` | canonical `Gate Evidence` | n |
|---|---|---|
| no | no | **41** |
| yes | no | 7 |
| yes | yes | 41 |

`fast-drain` writes both the file *and* the index row and refuses anything without a Gate Evidence section, so the 41 in row 1 cannot have come through it. Separately, 40 index rows point at files that no longer exist.

This is not only historical residue. `create-brief` §"Escalation lane — delivery" instructs, in the current tree: **"Write the file to the stack path directly."** B2.10 says "producers still write only to `.pile`". Both are current, both are authoritative to their readers, and they are opposites.

### D4. B2.1's brief-population is not the implementation's brief-population (**CORROBORATED**)

`Bead.is_brief` is `issue_type == "decision"`, full stop. Measured over 264 decision beads: **88 are git push/merge/branch authorization receipts (43% of the 204 with no dependency edge)**, 44 are policy/architecture decisions, 18 are `[brief-record]` tracker beads, 6 are session handoffs, 1 is a throwaway e2e artifact. Only **44/264 (16.7%)** carry any `brief_*` metadata.

POLICY.md's Definitions paragraph explicitly exempts push authorizations and kill-switch records from the one-bead model. **The implementation has no field on which to apply that exemption.** Until one exists, `MBRF004`/`MBRF005` will keep firing on beads the policy itself says are out of scope.

Two further checker defects, from the in-tree triage (§4.2, §4.3), which I read but did not re-derive:
- `source_dependencies` applies **no type filter**, so a `supersedes` edge — the opposite of a source link — satisfies B2.1's "source dependency". I *did* measure the edge-type histogram independently: 508 `related`, 15 `relates-to`, 3 `parent-child`, 1 `supersedes`, 1 `discovered-from`. Exactly **one** decision bead in 264 has a blocking-type edge.
- `bd list --json` emits only outgoing edges, so reverse (`BLOCKS ←`) links are invisible to mctl.

Blast radius: `MBRF004` is `Severity.ERROR`, and `plan_adjudication` blocks on every ERROR. So it gates `adjudicate`/`defer`/`dispatch-work` on **88 healthy pending briefs**. That figure is CORROBORATED (the triage doc verified it live via `mctl briefs options he-ldav4g`); I did not re-run it.

### D5. Where brief state lives: three answers, one of them now settled against the live tree (**MEASURED**)

| component | resolves to | live? |
|---|---|---|
| `paths.toml` + `mctl_core/redundant_state.py::artifact_layout` | `<rig_root>/.beads/briefs` | rig dirs of that name exist in 7 rigs but hold **implementation-summary / review-report artifacts, not briefs** — `stack/` exists in **none**, `.pile/*.md` in two (lmfdb 1, gascity-packs 4) |
| `check-briefs` SKILL.md:41, `present-briefs` SKILL.md:43 | `$CITY_ROOT/.beads/briefs/stack`, `$HOME/gt/.beads/briefs/stack` | **this is where the 89 files are** |
| `brief-prep` SKILL.md | line 24 `<city-root>/.beads/briefs/`; lines 84/181/224 `<rig-root>/.beads/briefs/.staging/` | internally inconsistent |

**Correction to the pre-audit report on two points:**
1. `create-brief` no longer says line 37 `<city-root>/.beads/briefs/` and no longer contains the line-82 "pick a path at runtime and record which one you chose" text. Commit `9b451d7` (2026-08-19, *"skills: route brief workflows through mctl"*) replaced it with **"Path: you no longer choose one… This retires the standing three-way path conflict."** Issue #65's quotation of SKILL.md:82 is now stale.
2. `<rig_root>/.beads/briefs/` is **not** absent — it exists in 7 rigs. What is absent is any rig-side `stack/`. The path collision is worse than non-existence: `paths.toml`'s `root` points at a directory that already exists for a *different* purpose.

The design question is **RESOLVED**: `subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md` Q5, decided 2026-08-19 — *"Storage is per-rig. Reporting is city-wide."* — which makes `paths.toml` correct and the city-root tree the drift.

**POLICY.md says nothing about location at all.** B2.4 says "exactly one pile" and B2.8 says "any filesystem layout is an implementation detail". Under the Q5 ruling, "exactly one pile" is now *wrong as stated* — storage is per-rig, so there are legitimately N piles and one *aggregated view*. This is the largest gap where POLICY.md is silent and should not be.

### D6. N5's auto-execute default has no executor (**MEASURED**)

Grepped the whole tree for `auto_merge_enabled`: the only readers are `brief-check.sh:497-503` and the `check-brief-policy` skill — both auditors. `brief-shuffle-fast-drain.py` does not read it; it treats G12 as a text token in the Gate Evidence section. No formula or order executes an approved no-brainer.

Current switch state: city flag exists and reads `true`; **no rig flag exists in any of 8 rigs checked**. By N5's own semantics that is "automation active everywhere". Yet 19 compact briefs sit unexecuted on the stack. N5, B2.9, N7, N8 and G12's "Executor check order" all describe a subsystem that does not exist.

### D7. gates.toml carries 3 live profiles POLICY.md does not mention (**MEASURED**)

I ran `check-brief-policy`'s own PP4.1 join-layer script:

```
JOIN-LAYER CLEAN: 17 gates match the policy table
POLICY profiles named: ['standard', 'no_brainer', 'test_execution', 'experiment']
gates.toml profiles:   ['decision', 'experiment', 'lost_bead_filter', 'no_brainer',
                        'producer_repair', 'standard', 'test_execution']
```

Gate *definitions* are clean. **Profiles are not.** `decision`, `lost_bead_filter` and `producer_repair` are live, enforced by `fast-drain::profile_error` with per-profile required metadata, and referenced by B2.10's own `gate_profile` sentence — but never defined in POLICY.md.

This is where the Authority section's remediation rule breaks: it says "gates.toml is repaired to match the table (never the reverse)". Applied literally here, that deletes three working profiles. **The direction of repair is wrong for this class of drift**, and the rule has no exception for "the registry grew a capability the policy has not caught up to".

Note also: all three new profiles **omit G2 (good-test) and G4 (critical-review)**, so B1.6's "every full-form brief passes an external critical review" and T6 do not apply to most current traffic.

### D8. The pile is 82% `.bak` and nothing reaps it (**MEASURED**)

`<city-root>/.beads/briefs/.pile/`: 5 `*.md`, **56 `*.md.bak`**, 7 directories.
`selected_pile_items()` filters `path.suffix == ".md"`, and `.md.bak` has suffix `.bak` — so the 56 are structurally invisible, exactly as issue #20 states. The `brief-shuffle-pile` order's condition (`find … -name '*.md'`) has the same blind spot.

`paths.toml` declares `bak_archive = ".beads/briefs/.pile/.bak-archive"`. **Grep across all `.py`/`.sh`/`.toml`/`.md` returns exactly one hit: the declaration itself.** No code reads it. The directory exists at city-root with 17 entries, last written 2026-07-16. Confirmed as reported.

### D9. Enforcement is installed in exactly one rig (**MEASURED**)

Formulas exec checks at `.gc/scripts/checks/…`. That directory exists in **hecke only** — not at `<city-root>` (where the live brief tree is), not in any other rig. Four formula-referenced checks are missing even from hecke: `brief-drain-manifest.sh`, `brief-no-brainer-classification-evidence.sh`, `brief-quality-failure-record-backfill.sh`, `brief-staging-clear.sh`.

`DOGFOOD.md:39` flagged this on 2026-07-11. It is still true 5 weeks later. Every gate whose only enforcer is a check script is therefore unenforced everywhere except hecke.

**RESOLVED 2026-08-19 — and the diagnosis above is wrong in its second half.**
Re-measured and then tested by execution:

- *The rig count was a category error.* `mathcity.brief-operator{,-1,-3,-5,-8}` are
  not rigs. `gc rig list` knows one rig here, `mathcity` at `<city-root>/mathcity`;
  the `mathcity.brief-operator*` directories are agent session homes holding
  per-bead work dirs. `<city-root>/hecke/.gc/scripts/checks` is the only such
  directory anywhere under the city root.
- *There is no install mechanism to be behind on.* gascity contains no code that
  materializes pack `assets/scripts/checks/*` into any `.gc/scripts/checks/`.
  The only `.gc/scripts` staging is `cmd/gc/template_resolve.go`, which copies
  the **city-level** `<city-root>/.gc/scripts` into agent runtimes; that
  directory holds only `gc-beads-bd.sh`. Hecke's 28 files are a hand-install
  dated 2026-07-11 that matches no committed pack revision and had drifted five
  weeks stale (`brief-check.sh`: 9,093 B installed vs 38,801 B shipped). An
  installed-but-stale enforcer is worse than an absent one, because it reports
  PASS under superseded rules. The belief that a copy happens traces to
  `subdomains/dev/docs/CODEX-REVIEW-RESPONSE-2026-07-08.md`, which recorded it
  as a to-be-verified assumption ("Verify the pack materialization copies
  `assets/scripts/checks/*` into `.gc/scripts/checks/`") and it was never
  verified.
- *The supported mechanism is a path form, not an install.* `path =
  "../assets/scripts/checks/<name>.sh"` is resolved by
  `internal/formula/parser.go::resolveCheckPaths` at cook time to the absolute
  path of the highest-priority formula layer that ships the script, and the
  ralph runner trusts it via `FormulaSearchPaths`. Under the v2 graph compiler
  a path no layer ships is a **compile error**, surfacing at cook time instead
  of as a runtime resolution failure. gascity's own test names this "the chain
  the brittle `.gc/scripts/checks/...` references are migrating to".
- *Fail-closed is now measured, not inferred.* With the check script absent,
  `runRalphCheck` returns `resolving check path: … no such file or directory`
  and an empty `GateResult`; `processRalphCheck` propagates that error, reports
  no `pass` action, and leaves the logical bead open with no `gc.outcome`. The
  same harness returns `pass` for a present script exiting 0 and `fail` for one
  exiting 1, so the absent case is distinguishable from both. (Executed against
  `internal/dispatch` with an injected test; the go-icu-regex build blocker is
  not real — `icu4c@78` is installed and `CGO_CXXFLAGS=-I$(brew --prefix
  icu4c@78)/include` builds the module.)

**Remediation applied:** all 28 check-path declarations in `formulas/` and
`gates/` migrated from `.gc/scripts/checks/…` to `../assets/scripts/checks/…`.
Verified by compiling every affected formula through the live `gc` binary: each
`gc.check_path` is now an absolute path to a script that exists, and the real
`brief-no-brainer-execute-safety.sh` was executed through the ralph runner in a
rig with no `.gc/scripts/checks` at all, returning a genuine refusal. Test 31 in
`tests/brief-no-brainer-arming/` was updated to assert the new form and to fail
on any regression to the legacy one.

**Open, NOT fixed — read before arming anything.** `check_no_brainer_execute_safety`
resolves the category registry as the CWD-relative literal
`assets/brief-pipeline/no-brainer-categories.toml` (`brief-check.sh`). The check
runs with CWD set to the agent work dir, not the pack root, so that file is
absent and every candidate refuses `classifier_evidence_invalid` no matter how
well-classified it is. The direction is safe — it refuses, never permits — but
it means the ARMED gate cannot currently PERMIT at all, and the refusal reason
misdescribes the cause. Deliberately left unfixed here: making a safety gate
newly capable of permitting is an adjudicated change, not a drive-by.

### D10. B2.5's ordering rule is not what the presenters do (**MEASURED**)

B2.5: *"the presenter computes unlock_count from live dependency data at presentation time."* Both `check-briefs` and `present-briefs` read `unlock_count` from frontmatter, `0` if absent. 29/89 stack files carry no `unlock_count`; 27 more carry `0`. Given that only 60/264 decision beads have any dependency edge at all, a live computation would return 0 for nearly everything anyway — so the rule is both unimplemented and, as written, not currently computable to a useful value.

### D11. POLICY.md's own hygiene (**MEASURED**)

- The **Gate** definition contains an unresolved inline editorial note: *"[This has been changed to "checkpoint" or since this conflicts with terminology in gascity formulas. ]"* — ungrammatical, undated, and **not applied** (the document says "Gate" throughout; so does `gates.toml`). It traces to bead `gsp-t1oa` (*"Taylor verdict: revise — rename 'gate' → 'check'"*), which is itself superseded by `subdomains/dev/docs/TERMINOLOGY-check-vs-gate.md` (2026-07-21, marked **Authoritative**), which concludes "gate" is native gascity vocabulary and **should not be renamed**.
- The header still reads `Status: Adopted (2026-07-12) · Date 2026-07-12` although content changed 2026-08-15 and 2026-08-16.
- Commit `37b0413` (2026-08-16) added B2.10's `brief-shuffle-fast-drain` sentence — a normative addition — with **no Change Log row**. The Change Log's last entry is 2026-08-15.
- The Known-drift section's **ARCHIVED lifecycle state** entry says it is "tracked as its own bead" without naming the bead. Not verifiable as written.

---

## 3. Decorative rules — no enforcer anywhere

These differ in kind from the drift above: nothing contradicts them, and nothing checks them either. A **NONE** here means I grepped `assets/`, `formulas/`, `orders/`, `gates/`, `tests/` for any `.py`/`.sh`/`.toml` referencing the rule or its behaviour and found no check.

| rule | note |
|---|---|
| **B1.2** one decision per brief | no splitter, no linter |
| **B2.6** cohort docket at ≥3 | zero occurrences of `cohort`/`docket` in any executable artifact; `present-briefs` presents strictly one at a time |
| **B3.1** closure requires verifiable acceptance | |
| **B3.2** authorization before close | the `authorize-git-operation` skill produces the receipt; nothing verifies ordering |
| **B3.3** downstream not orphaned | *and currently unimplementable* — `bd list --json` cannot see reverse edges |
| **B3.4** cross-repo self-close | |
| **B3.5** convoy close requires all members terminal | |
| **B3.6** all-closed check for auto-merge | vacuous — no auto-merge executor |
| **B3.7** research beads never destructively closed | may live in bead-policy per PP6.1; not in this pack |
| **B4.1, B4.2, B4.4, B4.5, B4.6** | Magma package discipline — the surfaces are real (1235 `package-*.mag`, all four certify intrinsics present) but no gate, script, or test touches these rules |
| **E1–E5, E7** | experiment design rules; `is-good-experiment` is a judgment skill, not a check. Only E6 has a gate (G7/G11) |
| **T4** test files name what they test | |
| **T5** PASS and FAIL both meaningful | |
| **D3** README lands with the change | |
| **S2, S3, S4, S5, S6** | dry-run → smoke → per-item OK → batch; transversal preference. Only S7/G5 is mechanized |
| **N8** α measurement | self-describes as blocked on a replay harness; also blocked on N7 never writing `confidence`/`category` |
| **PP6.1** precedence clause | prose |

**Count: 30 of ~70 rules have no enforcer of any kind.** That is not automatically wrong — some are genuinely judgment rules — but B3.5, B4.4 and S2–S4 are mechanically checkable and are being asserted as if enforced.

---

## 4. Proposed amendments (**DO NOT APPLY** — drafted for adjudication)

### A1 — T7 / G14 (highest value, lowest cost)

Replace T7's second sentence and G14's "Demands" cell.

> **T7 Tri-state declaration is never silent (G14).** Every brief carries an
> explicit test-execution declaration in the Gate Evidence section, written in
> the token vocabulary every gate entry uses: `PASS` (tests were executed), or
> `N/A` (no test surface — one-sentence reason required). Where execution is
> owed before adjudication, the entry is `PASS` **only** if the execution has
> happened; otherwise the brief is not deposit-eligible and the owing party is
> named in §6. Silent or absent declaration → auto-throwback.
>
> *(Amended 2026-08-19: the prior wording mandated `PASSED` / `NOT APPLICABLE`
> / `REQUIRED`, which no enforcer can parse —
> `brief-shuffle-fast-drain.py::STATUS_PATTERN` and `brief-check.sh::require_gate`
> both match `(PASS|N/A)\b`. A conformant brief was mechanically rejected.)*

If instead the intent is to keep the tri-state, the amendment must be to the
two regexes and to `create-brief` — but then `REQUIRED` needs a defined
promotion semantics, which does not currently exist. **Recommendation: amend
the policy, not the code.**

### A2 — B2.2 verdict channel

> **B2.2 Adjudication records the verdict on the brief bead.** …Mechanical
> check: adjudicated ⇔ the brief bead is closed **and** carries
> `metadata.verdict`, `metadata.verdict_reason`, `metadata.adjudicated_at`,
> and `metadata.authorizer`. `close_reason` MUST additionally restate the
> verdict in its first clause (B3.8) but is **not** the canonical field: it is
> free text and unparseable.
>
> **Legacy population.** Brief beads closed before 2026-08-19 predate the
> typed-field convention; their verdict lives in `close_reason` or `notes`.
> They are `legacy-adjudicated`, not `malformed`, and are exempt from
> `MBRF005` until a backfill is separately adjudicated. `MBRF005` applies to
> closures dated on or after the adoption of this amendment.

Companion (code, not policy): `plan_adjudication` must write `authorizer`, or
B2.2 must drop it from the required set. Today it names a field nothing writes.

### A3 — B2.1 brief discriminator

> **B2.1 A brief is a `type=decision` bead carrying `metadata.brief_kind`,
> plus a source link.** …A `type=decision` bead **without** `brief_kind` is a
> standalone decision record (push authorization, kill-switch engagement,
> policy ratification, session handoff) and is **outside the brief
> population**: it is not piled, not presented, not gated, and B2.2/B2.3/B3.8
> do not apply to it. Mechanical check: `issue_type == "decision"` **and**
> `metadata.brief_kind` is present.
>
> **Source link.** "Source dependency" means an outgoing edge of type
> `related` (the convention `effects.py::source_link_type` already applies) or
> `parent-child`. `supersedes` and `discovered-from` edges do **not** satisfy
> B2.1.

This is the amendment with the largest downstream effect: it takes ~220 of 264
beads out of `MBRF004`/`MBRF005` scope in one line, and it is exactly what
POLICY.md's own Definitions paragraph already says in prose but gives no field
to express.

### A4 — B2.4 / B2.8 storage location (implements Q5)

Replace B2.4's first sentence and add a location clause to B2.8.

> **B2.4 One pile per rig; one view across the city.** Unadjudicated briefs
> accumulate in exactly one pile **per rig**, rooted at the path
> `assets/brief-pipeline/paths.toml` declares, resolved rig-relative. There
> are no side-piles, per-agent piles, or "urgent" bypass piles **within a
> rig**; urgency is expressed through ordering (B2.5), not location. The
> human-facing pile is the **union across registered rigs**, computed at
> presentation time — storage is per-rig, reporting is city-wide.
>
> **B2.8 … Location.** `paths.toml` is the single declaration of where the
> cache lives, and every producer and reader resolves through one resolver
> (`mctl_core/redundant_state.py::artifact_layout`). A component that takes a
> brief root by argument, hardcodes `<city-root>`, or picks a path at runtime
> is in violation regardless of whether the path happens to work.

*(Adopted per Q5, `subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md`, decided
2026-08-19. The existing `<city-root>/.beads/briefs/` tree is drift and its
migration is a separate, separately-adjudicated bead — this amendment does not
authorize moving 89 files.)*

### A5 — B2.10 single writer, and closing the escalation hole

> **B2.10 …** `brief-shuffle-fast-drain` is the **only** writer to `stack/`
> and to `stack/.index.jsonl`; producers write only to `.pile`. A file that
> appears in `stack/` without a matching `.index.jsonl` row is a B2.10
> violation and is quarantined, not presented.
>
> **Escalation exception.** A worker blocked from reaching the bead store MAY
> write directly to `<brief-root>/.escalation-drop/`, which is **not** the
> stack and is never presented from. Draining `.escalation-drop` into `.pile`
> is a human or supervisor action. No producer writes `stack/` under any
> circumstance.

Companion: `create-brief` §"Escalation lane — delivery" step 1 must change
from "Write the file to the stack path directly" to the `.escalation-drop`
path, and step 2's fallback ordering inverts accordingly.

### A6 — Gate inventory: add the three missing profiles

Add to the **Profiles** paragraph:

> `decision` = G5, G5b, G8, G9, G11, G12, G13 (decision-track briefs;
> requires `brief_kind: decision`, `feedback_sink: brief_quality_failure`, a
> source or legacy-source link, and an `action_block` with `on_approve` /
> `on_reject` / `on_defer`).
> `lost_bead_filter` = same gate set (requires `brief_kind: lost_bead_filter`
> plus `fingerprint`, `threshold_count`, `distinct_bead_count`,
> `replay_command`, `false_positive_risk`).
> `producer_repair` = same gate set (requires `brief_kind: producer_repair`,
> `producer_contract: brief-producer-repair.v1`, `repair_source_formula`,
> `repair_failed_gate`, `repair_failure_fingerprint`, `replay_command`).
>
> **These three profiles omit G2 and G4.** B1.6's external-review requirement
> therefore binds only the `standard`, `test_execution` and `experiment`
> profiles; T6 likewise. That narrowing is deliberate and is recorded here
> rather than left implicit in `gates.toml`.

And amend the **Authority** section's remediation rule:

> Any mismatch is PP1.7 drift. Where the mismatch is a *definition*
> disagreement, `gates.toml` is repaired to match the table. Where
> `gates.toml` carries an **executable capability the table does not describe**
> (a profile, a required-metadata contract), the capability is not deleted:
> the table is amended to describe it, through `new-brief-policy`, within one
> session of detection. Deleting working configuration to satisfy a document
> is never the remedy.

### A7 — N5 / B2.9 / N7 / N8: say that auto-execution is not built

Add to **Known drift and upstream requests**:

> - **No-brainer auto-execution is specified but not implemented.** N5's
>   executor check order, B2.9's auto-adjudication, N7's audit trail and N8's
>   α measurement all describe a component that does not exist: no formula,
>   order, or script reads `auto_merge_enabled` to decide whether to execute.
>   The only readers are auditors (`brief-check.sh`, `check-brief-policy`).
>   Until an executor ships, **every** classified no-brainer surfaces, and
>   N6's "surfacing a no-brainer is a regression" does **not** apply to
>   surfacing caused by the missing executor. Tracked as its own bead.

### A8 — B2.5 ordering

> **B2.5 Ordering = unlock count.** …Mechanical check: the presenter reads
> `unlock_count` from the stack index row, and recomputes it from live
> dependency data whenever the row is absent, is `0`, or is older than the
> brief's last modification. A brief with `unlock_count: UNKNOWN-NOT-COMPUTED`
> sorts by `priority`, not to the bottom.

*(The current text asserts a live computation no presenter performs. Either
the presenters change or the rule does; this wording is the cheaper of the
two and preserves the `UNKNOWN-NOT-COMPUTED` contract `create-brief` already
mandates.)*

### A9 — housekeeping

- Delete the bracketed "[This has been changed to "checkpoint"…]" note from the
  **Gate** definition. Per `TERMINOLOGY-check-vs-gate.md` (2026-07-21,
  Authoritative) "gate" is native gascity vocabulary and the rename is not
  needed. Record the resolution in the Change Log rather than inline.
- Update the header to `Status: Adopted (2026-07-12), last amended <date>`.
- Add the missing Change Log row for commit `37b0413` (2026-08-16, B2.10
  fast-drain sentence).
- Name the bead in the Known-drift **ARCHIVED lifecycle state** entry.

---

## 5. What I could not determine, and why

1. **Whether B1.2, B1.5, B1.6, B1.8, B3.1, B3.4, E1–E5, T4, T5 are *observed***.
   These are judgments about brief content. Establishing compliance means
   reading 89 briefs on their merits, which is a different task and would have
   made this audit an estimate rather than a measurement. What I can state is
   the enforcement fact: nothing mechanical checks them.

2. **Whether the 41 index-less stack files were ever presented.** There is no
   presentation log I could find; `presentations/` exists as a `paths.toml`
   entry. I did not determine whether any B2.3 violation actually reached a
   human, only that the filter that should prevent it is inert for ~88/89 files.

3. **Whether `MBRF004` blocks adjudication on exactly 88 pending briefs.** The
   figure comes from `MALFORMED-BRIEF-TRIAGE-2026-08-19.md` §4, which verified
   it live via `mctl briefs options`. I read that verification but did not
   re-run it — running `mctl briefs options` across 185 beads was outside the
   read-only budget I set. **CORROBORATED, not independently measured.**

4. **Whether B3.7 is covered by the bead policy.** PP6.1 assigns bead taxonomy
   to `POLICY-beads.md`. I did not audit that document; "no enforcer in this
   pack" is all I can support.

5. **Whether `he-9bma`'s contradiction is representative.** n=7 is too small
   for a rate. "2 of 7 typed verdicts are wrong" is an exact count of a tiny
   population, not an error rate; the pre-audit report's "wrong ~22% of the
   time" over-reads it.

6. **Whether `<city-root>/gt/mathcity` (the imported pack copy) is what agents
   actually load.** `~/.claude/skills/create-brief` resolves to the
   `<repos-root>/mathcity` checkout, so outside agents read the repo. But
   `<city-root>/mathcity` is a *second* checkout at a different commit
   (`9523700` vs `f0ccd3b`) and its `create-brief/SKILL.md` differs. Which one
   an inside (gascity-dispatched) agent loads depends on `city.toml` import
   resolution, which I did not trace. If inside agents read the city copy,
   several of the "already fixed" findings in §D5 may still be live for them.

7. **The pre-audit report's "85 closed / ~40 free narrative / ~27
   verdict-buried / 6 opening-with-verdict / 3 supersession" breakdown.** I
   could not reproduce those exact numbers under any scoping. Independent
   measurement over 4 stores gives 137 closed with buckets 94 / 15 / 11 / 17;
   over the 3 rig stores only (excluding the `<city-root>` HQ store) the
   in-tree triage gives 81 closed. The **9 typed verdicts** figure reproduces
   exactly. The bucket proportions are sensitive to the verdict vocabulary
   used: this corpus's real verdict tokens are option codes
   (`A-DISPATCH-NOW-WITH-Q-DEFAULTS`, `E-HYBRID-B-FIRST-THEN-A-PLUS-C-PARALLEL`),
   not the words APPROVE/REJECT, and 25 close_reasons begin literally with
   `legacy verdict backfill:`. Any bucketing that does not treat option codes
   as verdict tokens will overcount "free narrative" — mine does, and I am
   flagging it rather than hiding it.

---

## Appendix — reproduction commands

```bash
# stack cross-tab (index membership × Gate Evidence)
cd <city-root>/.beads/briefs/stack && python3 -c "
import json,pathlib,re,collections
slugs={json.loads(l)['slug'] for l in open('.index.jsonl') if l.strip()}
ge=re.compile(r'^(?:#{1,6}\s+)?Gate Evidence\s*\$', re.M)
c=collections.Counter((p.stem in slugs, bool(ge.search(p.read_text(errors='replace'))))
                      for p in pathlib.Path('.').glob('*.md'))
print(c)"

# T7 vs the enforcers
python3 -c "
import re
P=re.compile(r'^(.+?):\s*(PASS|N/A|FAIL|BLOCKED|PENDING)\b',re.M)
for s in ['G14 X: PASSED','G14 X: NOT APPLICABLE','G14 X: REQUIRED','G14 X: PASS']:
    m=P.search(s); print(repr(s),'->',m.group(2) if m else 'NO MATCH')"

# PP4.1 join-layer + profiles  (from check-brief-policy §8, extended)
MATHCITY_PACK_ROOT=<repos-root>/mathcity  # then run the script in that SKILL.md

# bead population (read-only; --limit 0 is required, default 50 truncates)
bd -C <store-dir> list --type decision --all --flat --limit 0 --json
```

**Cited in-tree analyses** (read, not re-derived):
`subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md` (§1.2, §2, §4.2, §4.3);
`subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md` Q5;
`subdomains/dev/docs/TERMINOLOGY-check-vs-gate.md`;
`subdomains/brief-system/DOGFOOD.md` §39;
issues #20, #65.
