# Brief-system rework — state of play, 2026-08-19

**Purpose.** A safety net, written because the work sprawled across a long
session and the owner said: *"We have a lot of unresolved issues and I'm worried
we are getting lost in it all… I don't want to forget."* Optimised for nothing
falling through, not for elegance.

**Epistemic rule for this document.** Items are marked **DECIDED** (a person
ruled), **PROPOSED** (someone suggested, nobody ruled), or **OBSERVED** (measured
against the live system, with the measurement shown). Several figures asserted
during the session were later found wrong; where a number survives here it was
re-checked, and where it could not be it says so. Conflating these three is the
specific failure that made this document necessary.

---

## 0. Where this is going

The goal, in the owner's terms: **make agent behaviour rigid, predictable and
reproducible** — *"act like python and less like chat bots"* — and give a human a
brief manager they can actually adjudicate through.

Two concrete expressions of that:

- **Typed tool calls replace prose commands.** Arguments validate before
  execution, there is no shell, and therefore no quoting bugs, no `$VAR`
  surprises, no cwd sensitivity. (cwd sensitivity caused two real failures on
  2026-08-19 alone.) Umbrella: **#59**.
- **A brief manager a human uses.** 200 briefs across 16 rigs currently readable
  only as JSON from a CLI. Superseding design: **mc-vdl.2**.

Everything below serves one of those or is explicitly triaged out in §7.

---

## 1. DECIDED — safe to build on

Ruled by the owner on 2026-08-19 unless noted.

| # | Decision | Notes |
|---|---|---|
| D1 | **A brief is an abstract thing with four representations** — Python instance, `.md` form, JSON form, bead+metadata — all mutually convertible. | The court analogy: printouts are not the case. |
| D2 | **The bead id is the docket number** — canonical identity. | |
| D3 | **Bead-first.** From the system's perspective a stray document does not exist; only process briefs starting from their bead. | |
| D4 | **From a policy perspective every stray document must be migrated in.** Migration is a deliberate operation, never a runtime matcher. | Runtime matching is what currently fails. |
| D5 | **Adjudication state is binary** — adjudicated or not. Richness lives in the verdict, not in extra states. | Already POLICY's own wording; the 8-state model proposed earlier was drift. |
| D6 | **Verdicts: approve / reject / revise**, plus defer. | `VALID_VERDICTS` already holds the first three. **defer is NOT among them** — it is a separate operation. (OBSERVED) |
| D7 | **Disposition is required — no bare verdict.** APPROVE carries sub-options **proposed by the brief itself** (A/B/C/D), not a fixed enum. | Corpus agrees: real verdicts are option codes, e.g. `A-DISPATCH-NOW-WITH-Q-DEFAULTS`. |
| D8 | **`Other` is a disposition in the UI and a REVISE in the backend.** | Both prior positions were right about different layers. Bob renders E·Other; the write path records revise. |
| D9 | **Revise closes and supersedes** — by **duplicating the bead then editing**, so work is not redone. | Reversal of an earlier "stays open" ruling, made after it was shown to break POLICY's *adjudicated iff verdict AND closed*. `bd supersede` links and closes but **does not copy content** (OBSERVED) — the clone is ours to implement. |
| D10 | **No-brainer is an orthogonal tick-box**, not a verdict value. | Does not exist in the current dashboard. |
| D11 | **Acceptance criteria are never forced.** The no-brainer system is the safety net; tests/experiments/plans already carry the verifiable part. | Makes the no-brainer classifier load-bearing for *quality*, which nothing currently documents. |
| D12 | **Preview is surface-dependent** — none on the CLI, kept on the web. | |
| D13 | **Chips over dropdowns**, and more generally **fidelity to the working prototype beats any verbal spec.** | *"I LOVED the way the webpage was working."* |
| D14 | **Q5: storage is per-rig, reporting is city-wide.** | `paths.toml` and `artifact_layout()` are correct as designed; the live city-root layout is the drift. Migration deliberately deferred → **#58**. |
| D15 | **The Claude Design mockup supersedes the existing dashboard.** | **mc-vdl.2**. Constraints that survive: stdlib only, no JS required, no build step, loopback only, and the four honesty properties. |
| D16 | **mctl adapts to serve the brief manager.** Where design and backend disagree, the backend bends. | *"If there is a square peg and a round hole something needs to be adjusted."* |
| D17 | **D1–D5 of the MCP conversion**: MCP is the target and `bin/mctl` the bridge; audit every skill one by one; the Mayor gets tools for everything mechanical and the clerk the same treatment; wrap rather than replace; mathcity-owned skills only, with imported-pack wrappers erroring loudly if the pack is absent. | Recorded on **#60**. |

---

## 2. OPEN — blocking work

| Question | Blocks | Why a person must decide |
|---|---|---|
| **Compound / per-item verdicts.** 12 of 86 closed briefs carry one — `APPROVE-…-3A-5C-1NORELITIGATE-PLUS-NOT-ALL-CUSP-SYMBOLS-NOTE`; `PASSED-TO-MAYOR-FOR-DECOMPOSITION-PLUS-DEPENDENCY-GRAPH-REJECTED` (part approved, part rejected, one verdict). (OBSERVED) | The verdict dataclass **and** bob's adjudication panel. No single-value control expresses one. | It changes what a verdict *is*, not how it is stored. |
| **Does `close_reason` satisfy B2.2's "recorded verdict fields"?** | Whether ~76 briefs read as adjudicated or malformed; whether the dashboard shows 10 or ~85. | A policy question about what counts as a verdict. |
| **What to do with the closed-bead corpus.** 137 closed decision beads (8 stores) / 86 (4 rigs). Verdicts sit in five different shapes. | The migration; the dashboard's Adjudicated view. | 40 have no recoverable verdict; 3 are supersessions that were never adjudications. Cannot be inferred. |
| **Is #65 rewritten or closed?** It quotes `create-brief` text replaced by `9b451d7` hours before filing. (OBSERVED) | trans's next step. | |
| **Verdict immutability.** 4 of 86 are reversals (`REVERSE-B-TO-A-DUE-TO-CHAIN-COLLAPSE`). (OBSERVED) | Whether the verdict field is append-only or mutable. | |

---

## 3. IN FLIGHT — by owner

| Owner | Work | Status |
|---|---|---|
| **bob** (`2022c563`) | `render.py` / `app.py` — the superseding dashboard | Building. Branch is `main`, pushed at `f0ccd3b`. Filed **mc-vdl.3** for the backend surface he needs. |
| **trans** (`fdd99db3`) | **#65** (state-location contradictions), **#38** (verified fixed, brief deposited recommending closure) | Awaiting owner y/n on #38. #65 needs rewrite — see §2. |
| **creek** (`76d1d8fc`) | **#6** commissioning contract | Recommends close-as-done; verified against commits `41319b1`/`2600053`. Declined to close it themselves. One change (`477de61`) touches contract text and is in their scope to judge. |
| **brad** (`3d751549`) | `check-briefs` → `mctl briefs list --all-rigs` | **Uncommitted** in the working tree; declined to fold into the authorized push; routed to the owner as a separate authorization. |
| **pink** (`fdd0a72d`) | City lifecycle, adversarial e2e | e2e complete — one real bug found and fixed (control-plane gate). Holding on `gc stop` pending bob. |
| **me** (`36db5d4e`) | mctl core / MCP backend | §4 below. |

---

## 4. BACKEND GAPS — what the new dashboard needs

Derived from the design's own fixture-mapping table plus bob's list. Owner: me, unless noted.

**Already exists — do not rebuild:**

- `EffectPlan` + 3 `plan_*` builders, phased traces — bob's "Review verdict →" can render it directly.
- Diagnostic code registry — `assets/mctl/diagnostics.toml`, **72 codes**, consistency-tested. (OBSERVED)
- Defer windows — `_defer_until()`, `decision_state == "deferred"`.
- `decision_options()` + `BriefDecisionOption` — exists but **resolves 0 of 25 sampled briefs** (see below).
- `context_resolve` already hard-errors on source-checkout invocation.

**Missing:**

| Gap | Note |
|---|---|
| **Gate evaluation** (PROMOTABLE / WAITING / GATE REJECT) | Largest gap. Nothing in `mctl_core` evaluates a gate; the logic is in `assets/scripts/checks/brief-check.sh` (`require_gate`). **Porting it faithfully ports its bug** — see §5. |
| **Typed §4 options on the bead** | Currently regex-parsed from a `.md` at a path that does not resolve, and **fails open silently by design**. Measured: **0 of 25** sampled hecke briefs return options. (OBSERVED) The design's §4 screen has no data source today. |
| **PolicyIndex: rule → file, line, text** | `PolicyReference` carries `reference` + `description` only. Needed for the knowl pattern. |
| **defer as a verdict** | Not in `VALID_VERDICTS`; a separate operation. The design has it as a fourth chip. |
| **Adjudicated history with the verdict** | Closed briefs list fine; the verdict itself is the unsolved problem in §2. |
| **Dependency-edge reason** | Edges already carry a `metadata` field (currently `{}`) — **no bd schema change needed**, it is a write-path question. (OBSERVED) |
| **Draft persistence** | Owner confirmed wanted. Client-side is bob's; server-side is mine. Undecided which. |
| **Priority list / pairwise ranking** | Probably client-side; flagged as schema the design assumes. |

**Naming trap for bob:** `mctl briefs options` returns the **action** options
(validate/adjudicate/defer), not the §4 alternatives. Two different things, one
command name — the `BriefOption` / `BriefDecisionOption` collision.

---

## 5. FINDINGS not yet actioned

Each is measured unless marked. None has an owner yet.

1. **T7/G14 mandates vocabulary every enforcer rejects.** `require_gate` and the fast-drain `STATUS_PATTERN` both match `(PASS|N/A)\b`, so `PASSED` fails the word boundary and `NOT APPLICABLE` matches nothing. **A policy-conformant brief is mechanically rejected as "missing required gate G14."** A live stack file writes `PASS** — **PASSED**` to satisfy both at once. Cheapest sharp fix available.
2. **41 of 89 stack files have neither an index row nor a Gate Evidence section** — they bypassed the shuffler. And `create-brief`'s escalation lane still *instructs* writing directly to the stack, against B2.10.
3. **1 of 89 stack files carries `brief_bead:`** — so `present-briefs`' mandatory canonical-bead filter is a no-op for ~88 of 89 candidates. This is the identity problem D2 is meant to fix.
4. **~30 of ~70 POLICY rules have no enforcer of any kind.** Distinct from rules that are contradicted; a rule nothing checks drifts silently by construction.
5. **`<city-root>/mathcity` is a second pack checkout at a different commit**, whose `create-brief` differs. If gascity-dispatched agents load that copy, several "already fixed" findings are still live for them. (Flagged by the POLICY audit; not independently re-verified.)
6. **`MBRF004` refuses adjudication on 88 of 114 pending briefs.** Correct behaviour, and the most common state a user will see — so it needs real design, not an error box.
7. **The shared `artifact_root` defect.** `mctl_core/work.py::_formula_invocation` passes a rig-level root while `work-briefed.toml` documents per-bead scoping — two concurrent dispatches in one rig share a stage-artifact root. **That is gsp-1bmxuz, recreated inside the typed command meant to remove it.** Found by Slice 7; skills now say to serialise approvals per rig.
8. **`.mcp.json` is untracked and not gitignored** — a later `git add -A` sweeps it into a public repo.
9. **`gc dolt <subcommand>` needs real cwd inside a city**; `--city` does not register the command group, despite its own `--help` implying otherwise. (pink)
10. **`gc dolt restart`'s exit is not a readiness signal** — connections keep refusing for seconds after it returns. (pink)
11. **The 9 typed `metadata.verdict` values are backfill artifacts**, and 2 of 7 checked disagree with the `close_reason` they cite as source.

---

## 6. HOUSEKEEPING

| Item | Owner |
|---|---|
| `.mcp.json` — commit, gitignore, or delete. Written and verified (handshake, 16 tools) but inert until a session restart. | owner decision |
| `POLICY-DRIFT-AUDIT-2026-08-19.md` — uncommitted, carries **nine drafted amendments**, unapplied | owner |
| `DASHBOARD-DESIGN-HANDOFF.md` — **superseded** by mc-vdl.2 on every interaction question; keep only for the honesty properties and data shapes | me |
| brad's `check-briefs` change — uncommitted, needs its own authorization | owner |
| `gsp-v971oa` — test artifact in the live gascity-packs corpus. **pink's, not mine** (I misattributed it) | pink |
| Snapshot the 86-bead corpus before any long `gc stop` — it is what the verdict rework is being designed against | me |
| P5.5 footer form drift: we emit `[autogenerated by Claude Opus 5 on <date>]`; POLICY specifies `[… v<version> on <datetime>]` | owner |
| The harness-vs-P5.5 `Co-Authored-By` conflict — hand-warning every subagent is not durable; the harness config is the fix | owner |

---

## 7. NOT part of this rework

Open issues that are real but unrelated — triage separately rather than carrying:

- **#49, #53, #54, #55, #56** — the First Proof / Lean / mathlib-quality / Tau Ceti toolchain cluster.
- **#16** — 784k orphaned wisp rows.
- **#11** — `bd.dog` provider_error. **Answered 2026-08-19: not moot, 436 occurrences, byte-identical to #10's signature** on an agent whose `min_active_sessions = 0`. (OBSERVED)
- **#29** — roll deployed gc forward.
- **#1, #2, #3, #5** — older feature work.
- **#25** — *"16 false load-bearing claims in one session, none caught by their author."* Not part of the rework, but directly relevant to how this session went; several claims here were wrong and corrected only because someone asked for examples.

---

## Provenance

Session `36db5d4e`, 2026-08-19. Refreshed against `gh issue list` (38 open),
`bd list --status open`, and `git log origin/main` at `f0ccd3b` before writing.

**Corrections absorbed:** the "32 `Co-Authored-By` commits" (0 outgoing, 3
repo-wide); 85-vs-264 decision-bead scope; "the stack is uniformly compact"
(false — 43 of 89 carry Gate Evidence); "rig brief trees are absent" (they exist
with different content); `gsp-v971oa` attribution; #65's stale quotation.
