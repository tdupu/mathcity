# Response to Codex Review of the Mathematics Pack — 2026-07-08

**Reviewer's thesis:** "This pack uses 'gates' as a brief-policy checklist/registry, while
Gas City gates are workflow-control checks attached to formula steps and executed by the
control dispatcher."

**Verdict after file-level verification:** The thesis is **half right**. The reviewer
correctly spotted two genuine conventions gaps (absolute paths; exit-code-driven branching)
but built the rest of the review on the **wrong reference pack**. The reviewer compared the
mathematics pack against `gascity/` — the first-party *build-methodology* pack — and treated
its conventions as "the Gas City way." They are not. The operational packs (`gastown/`,
`github/`, `ops/`, `oversight-rig/`) share the mathematics pack's conventions almost exactly:
inline descriptions, `orders/` directories, per-domain gate formulas. The mathematics pack is
an **operational/domain pack**, not a build-methodology pack, and belongs in that second
family.

This aligns with the human adjudicator's standing rule ([[bead reference]] "gascity-packs owns substrate
codification"): the math pack intentionally codifies its own brief pipeline
(brief-prep → decision → dispatch → record) as first-class gascity formulas, orders, and gate
formulas. That is by design, not drift.

Below: each finding rated **accurate / partially-accurate / wrong**, with severity
**P0 (blocking runtime)**, **P1 (should-fix technical debt)**, **P2 (nice-to-have)**, or
**deferred/reject**.

---

## Evidence base (what was actually verified)

- `mathematics/gates/*.toml` are **runnable formulas**, not catalog entries. Each has
  `[[steps]]` with a `[steps.check]` block using `mode = "exec"` and a `path` to a real
  shell script. Example: `gates/test-evidence.toml` → `check-evidence-block` step →
  `assets/scripts/checks/gate-test-evidence.sh` (which exists; 27 scripts present in
  `assets/scripts/checks/`).
- `mathematics/orders/*.toml` use genuine gascity event/cooldown-order syntax
  (`[order]`, `trigger`, `on`, `scope`, `pool`, `idempotent`). **Identical shape** to
  `gastown/orders/digest-generate.toml`.
- **Other packs with `orders/`:** `gastown`, `github`, `ops`, `oversight-rig`. The
  `gascity/` build pack is the *only* one without `orders/`. `ops/` even has a
  `formulas/gates/` directory.
- **`gastown/` formulas use inline `description = """..."""`**, not `description_file`.
  The `description_file` + `assets/workflows/<formula>/<step>.md` split is a `gascity/`-pack
  choice, not a universal GC rule.
- **`gascity/` `condition=` conditions on `{{vars}}`** (`{{drain_policy}} == separate`,
  `{{pr_mode}} != none`) — **never** on `{{steps.X.exit_code}}`.
- Absolute private-checkout paths appeared in **19 files**
  (all formulas + 4 gates); now replaced with `~/` or repo-relative paths. `gascity/` uses installed-runtime `.gc/scripts/checks/*.sh`.
- `mathematics/agents/codex-worker/{prompt.template.md, agent.toml}` is structurally
  identical to `gascity/roles/agents/<role>/{prompt.template.md, agent.toml}` — only the
  parent dir name differs (`agents/` vs `roles/agents/`).

---

## Finding-by-finding assessment

### Finding 1 — "`gates/` directory misunderstands Gas City gates" — **PARTIALLY ACCURATE / P1**

**What's wrong with the finding:** The claim that these files are "written like standalone
formulas or policy gates" rather than real gates *misreads the mechanism*. They ARE real
GC gate formulas — `[steps.check]` blocks with `mode = "exec"` running check scripts. That
is exactly the GC gate primitive the reviewer says is missing. `gates/latex-gate.toml`
even self-documents as "the runnable form of gate G6."

**What's right about the finding:** The *packaging* diverges. In `gascity/`, a gate-check is
`[steps.check]` **attached to the producer step it guards** (e.g. `build-artifact-valid.sh`
hangs off the build-finalize step inside `build-basic-review.formula.toml`). The math pack
instead ships gates as **standalone single-purpose formulas** in a dedicated `gates/`
directory, then *also* invokes the same check scripts inline inside `brief-prep.toml`
(see `attach-test-evidence` → `brief-test-evidence-required.sh`). So the checks are
correctly attached *where they run in the pipeline*; the `gates/*.toml` files are a parallel
**standalone-invocable + documentation** surface.

This is a defensible design (each gate is independently runnable and independently
documented), but it is a divergence worth making explicit, and it risks the two surfaces
drifting apart.

**Severity: P1 (should-fix, not blocking).** Nothing breaks at runtime — the check scripts
exist and are wired into the pipeline formulas. This is a documentation + naming clarity
issue.

**Remediation:**
- Rename `gates/` → `gate-formulas/` **or** add a `gates/README.md` stating: "These are
  standalone-invocable gate formulas. Each wraps a check script in `assets/scripts/checks/`
  that is ALSO attached inline to the relevant producer step in `formulas/`. The registry
  in `assets/brief-pipeline/gates.toml` is the policy index; these are the runnable form."
- In each gate formula's `[catalog]`, keep the existing `registry =` / `gate_id =`
  back-pointer (test-evidence.toml already does this well — replicate on all five).

---

### Finding 2 — "16-gate `gates.toml` is domain policy, not GC runtime gates" — **ACCURATE / P2 (mostly documentation)**

**Correct.** `assets/brief-pipeline/gates.toml` is a `[registry]` with 16 `[[gates]]`
entries carrying `kind = "mechanical|review|stop|manual"` + profiles. This is a
**brief-acceptance policy index**, not a runtime workflow object. The reviewer's read is
right.

**But the finding overstates the problem.** The registry already distinguishes kinds
(`mechanical` / `review` / `stop` / `manual`), and the mechanical ones already HAVE runnable
counterparts (G1→test-evidence.toml, G6→latex-gate.toml, G13→stale-claim.toml, G14→
test-execution.toml, G5→server-touching-safety-override.toml). The registry-plus-runnable-
form split is intentional and internally consistent.

**Severity: P2.** Rename-for-clarity only. Do not restructure.

**Remediation (optional):**
- Add a header comment to `gates.toml`: "This is the brief-acceptance POLICY registry
  (which gates apply to which brief profile). `kind=mechanical` gates have runnable formulas
  in `gates/`; `kind=review/manual` gates are satisfied by workflow steps in
  `formulas/brief-prep.toml`; `kind=stop` gates are hard STOP decisions routed to the human adjudicator."
- Do NOT rename the file or the G1–G16 evidence keys — briefs, check scripts, and the
  `create-brief`/`brief-prep` skills all reference them by ID.

---

### Finding 3 — "Absolute local paths break portability" — **ACCURATE / P0 (blocking for portability)**

**Fully correct and the most important finding.** 19 files hard-code
`.gc/scripts/checks/...` in `[steps.check]
path =`. `gascity/` uses installed-runtime relative paths (`.gc/scripts/checks/*.sh`). The
absolute paths mean these formulas **only run on the human adjudicator's laptop at that exact checkout path**
— they break the moment the pack is materialized into a city's `.gc/` tree, run from a twin
(`<city-root>/`), or used on any other rig.

**Severity: P0.** This is the one finding that genuinely breaks runtime portability. Every
other rig/city that installs this pack gets non-executing checks.

**Remediation (specific, mechanical):**
- Rewrite all `path = ".gc/scripts/checks/X.sh"`
  → `path = ".gc/scripts/checks/X.sh"` (matching the `gascity/` convention), across:
  - `formulas/`: brief-prep, brief-gate-keep, brief-present-next, brief-record-decision,
    brief-shuffle, brief-watchdog-refill, brief-review-patrol, brief-decision-dispatch,
    codex-dispatch, test-execution-request, file-or-sendback-route, no-brainer-classify,
    upf-experiment-dispatch, decision-enforce
  - `gates/`: server-touching-safety-override, stale-claim, test-execution, test-evidence,
    latex-gate
- Confirm the pack's materialization step copies `assets/scripts/checks/*` into the target
  `.gc/scripts/checks/`. (The scripts already live at
  `mathematics/assets/scripts/checks/` — 27 of them — so only the reference path needs to
  change, not the script locations.)
- The `latex-gate.toml` check reads inputs from env vars (`GC_BEAD_ID`, `LATEX_GATE_*`) —
  that part is already portable; only its `path =` needs the `.gc/` fix.

This can be done as a single find-and-replace pass with per-file verification. **Do this
first.**

---

### Finding 4 — "Formula layout doesn't match Gas City pack style" — **WRONG (wrong reference pack) / mostly reject; P2 for the agents/ nit**

**The reviewer compared against the wrong pack.** They assert "upstream gascity uses
`formulas/*.formula.toml` + `assets/workflows/<formula>/<step>.md` + `roles/agents/*`." That
describes the `gascity/` **build-methodology** pack only. Verified counter-evidence:

- **Inline descriptions are standard in operational packs.** `gastown/formulas/*.toml` (all 8
  mol-* formulas) use inline `description = """..."""` with **zero** `description_file`. The
  math pack matches `gastown`, not `gascity`.
- **`formulas/*.toml` vs `formulas/*.formula.toml`** is a naming-suffix cosmetic difference,
  not a structural one. Operational packs vary here.
- **`agents/codex-worker/` vs `roles/agents/`:** structurally identical contents
  (`prompt.template.md` + `agent.toml`). Only the wrapper dir name differs.

**Severity: mostly REJECT.** The math pack is a legitimate member of the operational-pack
family and follows its conventions. Forcing it into the `gascity/` build-pack mold (extract
every inline description into `assets/workflows/*.md`) would be churn for churn's sake and
would make the pack *less* like its actual peers (`gastown`, `ops`).

**One small P2:** For cross-pack consistency, consider moving
`agents/codex-worker/` → `roles/agents/codex-worker/` to match the `roles/agents/`
convention shared by `gascity/`. Low value; defer unless touching that area anyway.

---

### Finding 5 — "Routing assumes a specific local city" — **PARTIALLY ACCURATE / P1**

**The finding is softer than stated but points at a real thing.** The reviewer claims defaults
"target `gastown.dog`, `gastown.mayor`, `codex:codex-worker`." Verified: the math pack's
run-targets are **all `{{var}}`-parameterized** (`{{operator_target}}`, `{{review_target}}`,
`{{mayor_target}}`, `{{prep_target}}`, etc.) — they are NOT hard-coded. The *defaults* for
those vars are `gastown.dog` / `gastown.mayor`, and `codex-dispatch` defaults to
`codex:codex-worker`.

So routing is already overridable per-invocation. But two real issues remain:
1. **Default values are city-specific** (`gastown.*`). On a different city these defaults are
   wrong until every caller overrides them.
2. **Pool targets vs role targets.** `gascity/` routes to **pack-local role names**
   (`gc.run-operator`, `gc.requirements-planner`) backed by `roles/agents/`, which resolve
   through the pack's own role definitions and are city-agnostic. The math pack routes to
   **pool/agent addresses** (`gastown.dog`, `codex:codex-worker`), which are deployment-
   specific.

**Severity: P1.** Not blocking (vars are overridable, and there's exactly one deployment
today — the human adjudicator's), but it's real portability debt and the correct GC idiom is role targets.

**Remediation:**
- Define pack-local roles under `roles/agents/` (or reuse the existing `agents/codex-worker/`
  by promoting it) and switch defaults from `gastown.dog`/`gastown.mayor` to role targets
  like `math.brief-operator` / `math.brief-reviewer`, mirroring `gc.run-operator`.
- Keep the vars parameterized (they already are) so a city can still override.
- Lower-effort interim: change the *default values* only, from `gastown.*` to city-neutral
  role targets, leaving var names intact. This is a small, safe change.
- `codex:codex-worker` is legitimately provider-specific (the pack declares
  `[providers.codex]` in `pack.toml`); leave it, but source its target from the
  `agent.toml` rather than a bare literal.

---

### Finding 6 — "Some checks used as branch conditions incorrectly" — **ACCURATE / P1 (sharpest technical finding)**

**The single most technically correct finding.** `gates/stale-claim.toml` step
`route-for-redispatch` has:

```
condition = "{{steps.check-stale-claim.exit_code}} != 0"
```

Verified against `gascity/`: every `condition=` in the build pack keys off **workflow vars**
(`{{drain_policy}} == separate`, `{{pr_mode}} != none`) — **never** off a check step's
`exit_code`. In the GC model, `[steps.check]` is a **validate/retry/fail** guard on its own
producer step: it decides whether that step passes, not which branch the graph takes. Using
`{{steps.X.exit_code}}` to fan a routing branch conflates the check-guard mechanism with
metadata-driven branching, and depends on the compiler exposing `steps.X.exit_code` — which
is not an established GC contract (the reviewer's caution here is warranted).

**Severity: P1.** May work today if this compiler happens to expose `exit_code`, but it's
fragile, undocumented, and non-idiomatic. If the contract isn't guaranteed, it could be
**latently broken** — worth confirming whether it currently resolves.

**Remediation (specific):**
- Refactor `stale-claim.toml`: make `check-stale-claim` a **normal step** that runs the
  stale-check script and **emits a metadata verdict** (e.g. `gc.claim.stale = "true|false"`),
  rather than relying on its exit code as a branch driver. Then gate
  `route-for-redispatch` on `condition = "{{steps.check-stale-claim.stale}} == true"` (or the
  compiler's supported metadata-read form used elsewhere in operational packs).
- Alternatively, if staleness should *block* rather than *branch*, model it as a
  `[steps.check]` guard on the work step (fail-closed = block), matching the pattern the
  other four gates already use — none of which branch on exit_code.
- Audit the other gates for the same pattern: `test-evidence`, `test-execution`,
  `server-touching-safety-override`, `latex-gate` all use `[steps.check]` as a pass/fail
  guard (correct) — **only `stale-claim` uses the exit_code-branch anti-pattern.** So this is
  a one-file fix.

---

### Finding 7 — "`orders/` appears outside the current Gas City pack workflow model" — **WRONG / REJECT**

**Verified false.** The reviewer's evidence is "the local gascity-packs/gascity pack doesn't
use an `orders/` directory." True — but irrelevant. `orders/` is a **widely-used gascity
convention**; four other packs have it:

- `gastown/orders/`, `github/orders/`, `ops/orders/`, `oversight-rig/orders/`

And the math pack's order files use **exactly** the canonical `[order]` schema —
`scope`, `formula`, `trigger` (`event`/`cooldown`), `on`, `pool`, `interval`, `idempotent` —
byte-for-byte the same shape as `gastown/orders/digest-generate.toml`. The
`brief-decision-dispatch.toml` order is a textbook event-triggered order
(`trigger = "event"`, `on = "brief.decided"`, `scope = "city"`, idempotent with a dispatch
ledger).

The `gascity/` build pack simply has no standing/triggered work to schedule, so it needs no
orders. Its absence there is not a prohibition.

**Severity: REJECT.** No change. The `orders/` directory is correct, idiomatic, and
necessary for the brief pipeline's event-driven mechanics (shuffle-on-pile,
dispatch-on-decision, refill-on-low-stack). Removing or restructuring it would break the
pipeline's automation.

---

## Prioritized remediation plan

### P0 — Blocking (do first)
1. **Finding 3 — De-absolutize check paths.** Replace all 19
   `.gc/scripts/checks/X.sh` with
   `.gc/scripts/checks/X.sh` across `formulas/*.toml` and `gates/*.toml`. Verify the pack
   materialization copies `assets/scripts/checks/*` into `.gc/scripts/checks/`. Single
   find-replace pass + verify.

### P1 — Should-fix (technical debt, do next)
2. **Finding 6 — Fix the exit_code-branch anti-pattern in `gates/stale-claim.toml`.** Convert
   `check-stale-claim` to emit a metadata verdict and branch `route-for-redispatch` on that
   metadata (or convert to a fail-closed `[steps.check]` guard). One-file fix. First confirm
   whether `{{steps.X.exit_code}}` currently resolves in this compiler — if not, this is
   latently broken, not just non-idiomatic.
3. **Finding 5 — Move routing defaults to city-neutral role targets.** Introduce
   `roles/agents/` role targets (e.g. `math.brief-operator`, `math.brief-reviewer`) and
   change the var *defaults* from `gastown.dog`/`gastown.mayor`. Keep vars parameterized.
   Source `codex-worker` target from `agent.toml`.
4. **Finding 1 — Disambiguate the `gates/` surface.** Add `gates/README.md` (or rename to
   `gate-formulas/`) documenting that these are standalone-invocable runnable forms of the
   registry gates, and ensure all five carry the `registry`/`gate_id` back-pointer that
   `test-evidence.toml` already has.

### P2 — Nice-to-have (defer)
5. **Finding 2 — Add a clarifying header** to `assets/brief-pipeline/gates.toml` calling it
   the brief-acceptance policy registry. Do NOT rename the file or G1–G16 keys.
6. **Finding 4 (partial) — Optionally** move `agents/codex-worker/` → `roles/agents/codex-worker/`
   for cross-pack consistency. Low value.

### Reject / defer indefinitely
- **Finding 7 (orders/):** Reject. `orders/` is idiomatic and shared by four other packs.
- **Finding 4 (main claim — extract inline descriptions to `assets/workflows/*.md`):**
  Reject. The math pack correctly follows the *operational*-pack convention (matching
  `gastown`), not the `gascity/` build-pack convention. Inline descriptions are the norm for
  this pack family.

---

## Bottom line

The reviewer did real work and caught two things that matter — **Finding 3 (P0 portability
break)** and **Finding 6 (P1 non-idiomatic branching)** — plus a soft-but-real routing point
(**Finding 5**). Those are worth fixing.

But the review's central framing — that the math pack "misunderstands Gas City gates" and
diverges from "the Gas City pack model" — rests on comparing against the `gascity/`
build-methodology pack as if it were the sole reference. It is not. Measured against its
actual peers (`gastown`, `github`, `ops`, `oversight-rig`), the math pack is a well-formed
**operational/domain pack**: runnable gate formulas, event-driven orders, inline
descriptions, a domain-specific brief pipeline. That is exactly the shape the human adjudicator's
"gascity-packs owns substrate codification" directive calls for. **Findings 1, 2, 4, and 7
should be softened or rejected on that basis.**
