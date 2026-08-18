> ## ARCHIVED — UNADJUDICATED DESIGN, NOT ADOPTED POLICY
>
> **This document was never adjudicated and nothing in it is in force.** It
> describes a proposal, not a decision. Do not cite it as policy, precedent,
> or an approved plan.
>
> - **Source commit:** `c94cd9d1ebee9e28c09284a39d91e222d178767a` (legacy `~/gt/gascity-packs` detached-HEAD worktree
>   population — the `#121` 56-commit salvage set), 2026-08-04, 237 lines.
> - **Archived:** 2026-08-14 under decisions-track brief **#148**, Option (A).
>   Taylor's verdict: *"unadjudicated-design-docs-disposition, do they have any
>   value at all? If not then file them away."*
> - **Value assessment (brief #148):** **GENUINELY VALUABLE — PARTLY LANDED, PARTLY STILL ACTIONABLE** — the best of the four as an artifact. Its 11-skill inventory is still ~85% accurate against today's surface. Two of its recommendations LANDED (the incumbent was renamed — to `mathcity.work`, not `feed-the-machine`; `mayor-math-prime` \S6 was updated). Three did NOT and are still true today: `mayor-math` still duplicates the sling command inline, the `core.gc-work` fleet-sling gap is unfilled, and the concrete `sling-new-bead` transport bug it found is still live.
> - Nothing was deleted from the legacy tree; retirement is separately gated
>   under `gt-0g9die`. Full comparative assessment:
>   [`ARCHIVED-DESIGNS-INDEX-2026-08-14.md`](./ARCHIVED-DESIGNS-INDEX-2026-08-14.md).

---

# Feed-the-Machine Refactor — Design Proposal

**Source:** `gsp-vpry` (Taylor, 2026-07-15) · build-basic-briefed root `gsp-pwe09x` / requirements `gsp-4nb10b` · authored on item `gsp-iojh4t`
**Status:** **PROPOSAL ONLY** — decision-ready. No skill is created, renamed, merged, or retired by this build (REQ-007 / AC-7).
**Scope:** mathcity-owned skills (plus one upstream-PR option for `core.gc-work`). Deliverable = this document + the terminal decision brief this build deposits.
**Acceptance criterion (Taylor, hard, REQ-005):** *"a new QUIMBY boots already knowing how to feed the machine."*

> Open questions **OQ-1…OQ-6** from the requirements are carried into the sections where they
> bite, each marked `[OPEN]` with a recommendation. None is silently resolved — every one is a
> Taylor call restated in §8.

---

## §1. The decision being surfaced (REQ-007)

**What Taylor must decide:** the *shape and names* of the Mayor's work-dispatch skill family — specifically whether to **consolidate the "feed the machine" common case onto the existing `math-city-work` incumbent (renamed for discoverability)** rather than mint a new skill, and how to name the sharpened siblings.

**What this document does NOT decide / does NOT do:** it creates, renames, merges, or retires **nothing**. Every disposition below is a *recommendation*; the naming/structure choice returns to Mayor → Taylor before any execution build.

**One-paragraph recommendation.** The "missing common case" the charge describes — *"bead this + sling it to the fleet at normal priority"* — **is not actually missing**. It already exists as **`math-city-work`**, whose trigger phrases literally include *"feed the machine"* and *"feed this bead to the fleet"*, and its batch form **`push-the-fleet`**. The family "hasn't worked" not because the skill is absent but because it is (a) **named after the domain (`math-city-work`), not the action**, so a Mayor asking *"how do I dispatch to the fleet?"* never reaches for it; (b) **invisible from the upstream `core.gc-work`** skill the Mayor loads first, which teaches only bead CRUD and never `gc sling`; and (c) **duplicated, not referenced** — `mayor-math` copies the sling command inline instead of pointing at the owning skill. The right move is therefore a **rename + reference-consolidation + priming** job, **not a new-skill job**. Concretely: **rename `math-city-work` → `feed-the-machine`** (keeping the old name and all current triggers as aliases), point `mayor-math`, `core.gc-work` (via a supplement or upstream PR), and the priming skills at it, and sharpen — but keep — the genuinely-distinct siblings `immediate-work` (in-session) and `priority-work` (named-agent, P0). This **consolidates around the incumbent** and explicitly **avoids minting a 15th competing "dispatch" skill** (xkcd-927). Full family in §4; names are a recommendation, not a lock (**OQ-1**).

---

## §2. Inventory & behavior map (REQ-001 / AC-1)

Per-skill map for all eleven skills in the dispatch family, each grounded in reading its `SKILL.md`. Columns: **Claims** (frontmatter) · **Actually does** (body) · **Observed failure / overlap**.

| # | Skill (pack) | Claims | Actually does | Observed failure / overlap |
|---|---|---|---|---|
| 1 | **core.gc-work** (core, **upstream**) | "Finding, creating, claiming, and closing work items (beads)." | Low-level `gc bd` CRUD reference: `gc bd create/list/ready/show/update --claim/close`, plus `gc hook --claim`. Teaches rig-scoped bead DBs. **Mentions "sling" only in passing; never teaches `gc sling <rig>/<agent> <bead>` or the auto-convoy/fleet behavior.** | The Mayor loads this first expecting "how to dispatch work" and gets only bead management — the sling step is entirely absent. Uses `gc bd …`; the mathcity skills use bare `bd …` (divergent surface). **Root of the "missing common case" illusion.** |
| 2 | **immediate-work** (mathcity) | "In-session synchronous dispatch — spawn the right agent NOW … no pool, no queue, no sling." | 4-step in-session protocol: optionally beads the work, picks a model (Haiku/Sonnet/Fable), **uses the `Agent` tool inline**, closes the bead on return. Result lands in the *current* conversation. | Near-twin of `priority-work` (both carry the identical "immediate-work vs priority-work" contrast table). Name conflates *urgency* with *in-session scope*; this is **not** "feeding the machine" (never touches the fleet). |
| 3 | **priority-work** (mathcity) | "Async targeted dispatch — bump a bead to P0 and dispatch it to a NAMED agent … bypassing queue order." | Makes the bead a self-sufficient spec, sets `--priority 0`, tags `dispatch_target`, dispatches to a **named** agent (`gc sling <bead> <named-target>` or background `Agent`), records a `dispatch-provenance.v1` event, does **not** wait. | Twin of `immediate-work`. Conflates **two** axes (P0-priority *and* named-agent). A Mayor wanting "fleet, pool, normal priority" gets neither. Its sling recipe overlaps `math-city-work`/`push-the-fleet`/`sling-new-bead`. |
| 4 | **sling-new-bead** (**agent-skills**, not mathcity) | Thin orchestrator over `communicate-with-mayor` that relays a user's NEW-bead idea to the Mayor to file + dispatch. | Packages the idea into a 3-section Mayor instruction and (step 3) sends it **via `gc sling mayor --stdin`**, plus a long "sling mechanics the Mayor will use" reference block. | **Direction confusion** (user→Mayor, not Mayor→fleet) *and* a **concrete bug**: it calls `gc sling mayor --stdin`, but its declared dependency `communicate-with-mayor` states `gc sling mayor` for asks "was wrong (Taylor 2026-06-24)" — corrected to `gc mail send mayor`, which "does NOT accept `--stdin`." Wrong pack ownership (agent-skills). |
| 5 | **mayor-math** (mathcity) | "Supplement to gc.mayor … correct rig-scoped sling mechanics for build-basic convoy workflows." | Carries the rig-prefix→coordinator table (`gsp-`→`gascity-packs/gc.run-operator`, etc.), Rule 0 fork-vs-sling, build-basic convoy rules — **and a "Current dispatch pattern" block that copies the full `gc sling … --on build-basic-briefed` command verbatim.** | The fleet-sling mechanics are **buried in a Mayor orientation supplement**, not a dispatch skill, and the command is **duplicated** from `math-city-work` (drift risk). Not discoverable via "how do I dispatch to the fleet?" |
| 6 | **math-city-work** (mathcity) — *incumbent* | "Feed a bead … into the math-city fleet the correct, S14-verified way … **'feed the machine', 'feed this bead to the fleet'** …" | **THE common-case skill.** Pre-flight (`tmux -L gt ls`, Dolt health), Rule 0 (queue-health-not-hand-dispatch), live formula enumeration, then `gc sling <rig>/gc.run-operator <bead> --on <briefed-formula> …` (**briefed → fires a decision brief for adjudication**), the mandatory **verify-assignee gate**, dispatch-provenance event, and slow-build-≠-strand doctrine. | Not broken — **just not discovered.** Named after the *city/domain*, not the *action*, so a Mayor never reaches for it despite its triggers already covering "feed the machine." This is the incumbent the refactor should consolidate *onto*, not compete *with*. |
| 7 | **fan-out** (mathcity) | "Fan an epic bead out into sub-beads … WITHOUT consuming additional WIP slots." | Treats an epic as one dispatcher slot; creates an owned convoy + sub-beads carrying tree metadata (`dispatch.slot=free`), dispatches sub-beads, lands after N/N closed. | **Post-dispatch decomposition** — distinct scope (not confusable with the dispatch trigger), but its `gc sling … --no-convoy` mechanics overlap the general dispatch recipes. A *referenced neighbor*, not a dispatch member. |
| 8 | **coordinate-agents** (**agent-skills**) | "Act as the coordinator in a multi-agent session — route messages, assign reviewers, drive review/merge cascades." | Pure routing/assignment role over a **V1 shared-file inbox** (`<project>/.claude/.agent-inbox.md`) via `agent-send.sh`; "no self-review"; "you don't do the work." | Not dispatch at all (coordinator role). **Collides with `communicate-with-other-agent`**: same script name `agent-send.sh`, incompatible inbox semantics. A *referenced neighbor*. |
| 9 | **communicate-with-mayor** (**agent-skills**) | "Route an addressed message UP to the Mayor via `gc mail send mayor`." | Wraps `( cd ~/gt && gc mail send mayor -s … -m … )`; states `gc mail send` "does NOT accept `--stdin`"; covers clerk identity, restart handshake, receive-via-hook. **mail = up, sling = down.** | Infrastructure, not dispatch. It is the **authority that `sling-new-bead` violates** (§ row 4). Easily conflated with `communicate-with-other-agent` (mail-up vs peer-inbox). A *referenced neighbor*. |
| 10 | **communicate-with-other-agent** (mathcity) | "Send/read messages between concurrent agents via the V2 daily-folder inbox under `~/gt/.claude/inbox/`." | V2 per-message file layout, sender UUID `$CLAUDE_CODE_SESSION_ID`, `agent-send.sh` writes canonical + flat backward-compat paths; ACK-before-acting convention. | Infrastructure, not dispatch. **Shares `agent-send.sh` name with `coordinate-agents`** but a completely different inbox root/layout — a real collision surface. A *referenced neighbor*. |
| 11 | **push-the-fleet** (mathcity, `subdomains/dev`) — *incumbent* | "Saturate the city fleet with ready, unblocked work … dispatch everything ready … until active workers ≥ TARGET." | **The batch form of `math-city-work`** — "same formula, same vars, same verify-assignee doctrine — but it sweeps the whole queue instead of one bead." Priority filter, parallel `--on build-basic-briefed` dispatch, verify-assignee, report. | Not broken; correctly composes with `math-city-work`. Different **granularity** (saturate-to-N, not sling-*this*-bead) — must stay distinct from the single-bead common case. |

### §2.1 Incumbent quarantine (OQ-3 — family boundary) `[OPEN]`

**`math-city-work` (single-bead) and `push-the-fleet` (batch)** are the **working incumbents** of the "feed the machine" job. They are *quarantined* from the "these skills haven't worked" framing: they already implement the correct fleet-sling doctrine (briefed formula → adjudication brief, verify-assignee gate, slow-build-≠-strand). The refactor **builds on them**, it does not replace them.

The **referenced neighbors** — `fan-out` (post-dispatch decomposition) and the three messaging skills `coordinate-agents` / `communicate-with-mayor` / `communicate-with-other-agent` — are **out of the dispatch family**: they are mapped here for completeness and cross-referenced, but are **not** renamed or restructured by this proposal.

> **OQ-3 recommendation:** treat `fan-out` + the three messaging skills as **referenced neighbors, not members**; keep the refactored family limited to the five dispatch skills (rows 1–6, 11 minus the neighbors). Rationale: the messaging skills have their own overlap problem (rows 8/9/10) that is a *separate* refactor; folding them in here would balloon scope past the proposal's charge.

---

## §3. Diagnosis — why the family "hasn't worked" (REQ-002 / AC-2)

Five root causes, plus the residual gap.

- **RC-1 — Overlap / redundancy.** `immediate-work` and `priority-work` carry the *identical* contrast table and are near-twins; the fleet-sling command is copied verbatim into `mayor-math`, `math-city-work`, and `push-the-fleet` (drift risk, confirmed by the differing "direct vs briefed" forms in circulation). Several skills teach subtly different `gc sling` recipes.
- **RC-2 — Poor / ambiguous naming (wrong axes).** Names map to *urgency intuitions* ("immediate", "priority"), not to the real dispatch axes. A Mayor maps *"I want this done now"* → `immediate-work` (in-session) when the fleet path is a different skill entirely. The incumbent common-case skill is named after the *domain* (`math-city-work`), not the *action*.
- **RC-3 — The fleet-sling common case is "missing until you know it's `math-city-work`."** No skill *surfaces* "bead + sling to fleet at normal priority" under a name a fresh Mayor would guess. It exists (`math-city-work`) but is reachable only if you already know its name — so the Mayor rediscovers `gc sling` by hand each session.
- **RC-4 — Upstream-vs-owned confusion (`core.gc-work`).** The skill the Mayor loads first for "work" is the **upstream** `core.gc-work`, which teaches only bead CRUD and never the sling action. The owned skill that *does* teach it is invisible from there — and `core.gc-work` cannot be hand-edited (it is a cached upstream import; P1.3 / DOGFOOD §0).
- **RC-5 — Discoverability.** With no verb-consistent naming and no pointer from the upstream entry point, the family is a *lookup-by-prior-knowledge* set, not a *discover-by-intent* set. Trigger phrases like "feed the machine" *do* resolve (to `math-city-work`) but nothing advertises that.

**Residual gap.** Even though the common case *exists* and is *already loaded at priming* (`mayor-math-prime` §6 lists `math-city-work`), it remains **invisible from `core.gc-work`** and **hidden behind a domain-scoped name inside a Mayor supplement**. Priming has therefore only **partially converged**: the skill is loaded, but a Mayor reasoning from *"how do I dispatch?"* (i.e., from `core.gc-work`) still can't find it. The fix is naming + an upstream/supplement pointer + de-duplication, not a new capability.

---

## §4. Proposed family (REQ-003 / AC-3)

### §4.1 The three real axes

| Axis | Values |
|---|---|
| **Execution context** | *in-session* (Agent tool, result in this conversation) · *fleet* (`gc sling` → worker executes) |
| **Target selection** | *pool* (dispatcher auto-pulls a ready bead) · *named-agent* (dispatch to a specific session) |
| **Queue priority** | *normal* (normal queue order) · *jump-queue* (P0-bumped, ahead of others) |

The **common case** = **fleet · pool · normal** at single-bead granularity. That is exactly what `math-city-work` does today.

### §4.2 Recommended family (Scheme A — action-verb names, consolidate on incumbents)

Per member: candidate name · one-line description · trigger phrases · **disposition** (`NEW` / `RENAMED old→new` / `MERGED` / `RETIRED` / `KEPT`).

| Member (candidate name) | One-line description | Trigger phrases | Disposition |
|---|---|---|---|
| **`feed-the-machine`** | **The common case:** bead → `gc sling <rig>/gc.run-operator <bead> --on <briefed-formula>` → fleet **pool**, **normal** priority, single bead; fires a decision brief for adjudication. | "feed the machine", "feed this bead to the fleet", "sling this to the fleet", "dispatch this the right way", "put this through the fleet" | **RENAMED** (`math-city-work` → `feed-the-machine`); old name + all current triggers kept as **aliases** (OQ-6). |
| **`push-the-fleet`** | **Batch/saturate:** sweep the whole ready queue and dispatch via the same briefed formula until active workers ≥ TARGET. | "push the fleet", "fire more things", "get N things running" | **KEPT** (incumbent; batch form of `feed-the-machine`). |
| **`immediate-work`** | **In-session:** run the work now via the `Agent` tool; result returns in *this* conversation. No fleet, no pool, no sling. | "immediate work", "do this now", "in-session", "right now" | **KEPT** + description sharpened to the *in-session* axis. |
| **`priority-work`** | **Named-agent, jump-queue:** bump to P0 and dispatch to a *specific* agent, bypassing queue order; async. | "priority work", "bump this to the front", "dispatch this to \<agent\> now", "jump the queue" | **KEPT** + description sharpened (named-agent **and** P0 are its two axes). Optional rename `→ jump-the-queue` (OQ-1). |
| **`sling-idea-to-mayor`** | **User→Mayor relay:** user has an idea; Mayor files + dispatches it. Corrected transport: `gc mail send mayor` (not `gc sling mayor --stdin`). | "sling a new bead", "have the mayor file X", "ask the mayor to sling X" | **RENAMED + MOVED** (`sling-new-bead` → mathcity `sling-idea-to-mayor`); the old agent-skills `sling-new-bead` path is **RETIRED** (leave a redirect/stub). |
| **`core.gc-work` dispatch supplement** | A mathcity-owned pointer that fills the fleet-sling gap in the upstream `core.gc-work` (or an upstream PR that adds the section). | (loaded alongside `core.gc-work`; references `feed-the-machine`) | **NEW** mathcity supplement **OR** upstream PR (OQ-2). Never a cache hand-edit. |
| **`mayor-math`** | rig-prefix→coordinator table + build-basic convoy rules + fork-vs-sling Rule 0. | (Mayor supplement) | **KEPT** + **de-duplicated**: drop the copied sling command, replace with `[[feed-the-machine]]` reference. |

**Referenced neighbors (unchanged):** `fan-out`, `coordinate-agents`, `communicate-with-mayor`, `communicate-with-other-agent` — **KEPT**, not restructured here (see §2.1 / OQ-3).

**Exactly one member owns "bead + sling to fleet at normal priority": `feed-the-machine`** (single-bead, pool, normal). `push-the-fleet` is a *different granularity* (batch saturate-to-N), and `priority-work` is a *different priority + target* (P0, named). No two members claim the same axis-triple.

### §4.3 OQ-1 — names are a recommendation, not a lock `[OPEN]`

- **Recommended (Scheme A):** `feed-the-machine` for the common case (it is already the trigger phrase; action-named; maximally discoverable).
- **Alternative naming candidates:** `dispatch-to-fleet`, `sling-to-fleet`, `fleet-work` — all action-named; pick by taste.
- **Alternative structure (Scheme B — minimal blast radius):** **do not rename**; keep `math-city-work` (it is load-bearing — referenced by `push-the-fleet`, `mayor-math-prime` §6, policy `gsp-fhdnu`, and `bd recall great-regression-misdiagnosis-s14`) and fix *only* discoverability (add "how do I dispatch?" triggers, the `core.gc-work` pointer, and de-duplication). Lower risk; weaker discoverability payoff.
- **Recommendation:** Scheme A (rename to `feed-the-machine`, old name as alias) — the discoverability win is the whole point of the charge, and the alias carries the load-bearing references. **Taylor's call (OQ-1).**

### §4.4 OQ-5 — merge vs keep `immediate-work` / `priority-work` `[OPEN]`

Explicit option pair:

- **Option A (recommended) — KEEP distinct.** `immediate-work` (in-session) and `priority-work` (named-agent/P0) sit on *genuinely different axes* from `feed-the-machine` (fleet/pool/normal). Keeping them distinct preserves single-purpose discoverability; only their descriptions need sharpening to the axis vocabulary.
- **Option B — MERGE into one flagged skill.** Collapse `immediate-work` + `priority-work` + `feed-the-machine` into a single `dispatch-work` skill with `--mode in-session|fleet-pool|named-p0` flags. **Rejected** as the recommendation: a flag-mode mega-skill re-hides the axes behind parameters (the very RC-2 failure), and a mis-set flag silently changes execution context. Merging is the *more* error-prone shape here, not less.
- **Recommendation:** **Option A (KEEP distinct, sharpen descriptions).** **Taylor's call (OQ-5).**

---

## §5. Migration (REQ-004 / AC-4)

### §5.1 Trigger-phrase continuity (OQ-6) `[OPEN]`

Renames must not break existing Mayor muscle memory or resolution. Legacy phrases carry forward as aliases on the renamed skill's trigger list.

| Legacy phrase | Was → resolves to | Post-rename |
|---|---|---|
| "math-city-work", "feed this bead to the fleet", "put this through the fleet" | `math-city-work` | carried as **aliases** on `feed-the-machine` |
| "feed the machine" | `math-city-work` | native trigger of `feed-the-machine` (no change to the phrase) |
| "sling a new bead", "have the mayor file X" | `sling-new-bead` | carried as aliases on `sling-idea-to-mayor`; old dir left as a **redirect stub** |
| "immediate work" / "priority work" / "jump the queue" | `immediate-work` / `priority-work` | unchanged (skills kept) |

> **OQ-6 recommendation:** carry **every** current `math-city-work` and `sling-new-bead` trigger phrase as an alias on the renamed skill for at least one deprecation cycle; never drop a phrase in the same change that renames the skill.

### §5.2 Symlink / sink continuity (P1.3)

Skills are consumed through **generated symlink sinks** (`~/gt/.claude/skills/mathcity.<name> → ~/repos/gascity-packs/mathcity/skills/<name>`); the running city **loads mathcity content directly from `~/repos/gascity-packs/mathcity/`** (local-path import — *not* cached; DOGFOOD §0). A rename therefore means:

1. Create the **new** source dir under the pack: `~/repos/gascity-packs/mathcity/skills/feed-the-machine/SKILL.md` (and `mathcity/skills/sling-idea-to-mayor/SKILL.md`). `push-the-fleet` lives under `mathcity/subdomains/dev/skills/` — its refresh, if referenced, follows the same rule.
2. **Refresh the sink** — regenerate the `~/gt/.claude/skills/` symlink to the new dir via `gc pack refresh` / next supervisor tick. **Never hand-create or hand-edit a file inside the sink** — P1.3: *"Never edit a materialized skill sink … Creating or modifying files in a sink → fail."*
3. Add/adjust the **README rows** (§7 / P1.13) in the *same commit* as the rename.
4. Leave the old `math-city-work` source dir as a thin alias/redirect for one cycle (its triggers already carried in §5.1).

### §5.3 The `core.gc-work` gap — supplement vs upstream PR (OQ-2) `[OPEN]`

`core.gc-work` is **upstream** (`~/repos/gascity/internal/bootstrap/packs/core/skills/gc-work/SKILL.md`, git-URL import → cached under `~/.gc/cache/repos/<hash>/…`). It must **never** be hand-edited in the cache (P1.3 / Out-of-Scope). Two ways to fill the fleet-sling gap, **both developed**:

- **Option A — mathcity supplement (recommended for now).** Ship a small owned skill (e.g. `mathcity/skills/feed-the-machine/` itself, or a thin `gc-work-fleet` pointer) that supplements `core.gc-work` with the fleet-sling idiom and is loaded alongside it. **No upstream dependency; lands this week through the dogfood loop.**
- **Option B — upstream PR.** Add a "Dispatching work to the fleet" section to `gastownhall/gascity` at `internal/bootstrap/packs/core/skills/gc-work/SKILL.md`. **Correct long-term home** (every city benefits), but requires BART to submit and a maintainer to merge, then a cache re-import.
- **Recommendation:** **A now, B as follow-up** — ship the mathcity supplement immediately so the Mayor is unblocked, and open the upstream PR so the fix eventually lives where it belongs. **Taylor's call (OQ-2).**

### §5.4 Landing path (dogfood — DOGFOOD §0, LP1, authorize-git-operation)

All execution (a later build, not this one) follows the two-lane dogfood path:

1. Author/renaming staged in **`~/gt/gascity-packs/mathcity/…`** (staging lane; *zero* live effect — the city reads `~/repos`).
2. Bead the change; commit + push `~/gt/gascity-packs` to the `tdupu` fork **through Taylor's `authorize-git-operation` gate**.
3. **Hand off to BART**, the repo-side landing agent, who reconciles and pulls into **`~/repos/gascity-packs`** — *the only lane that makes it live*. **No `~/gt` agent runs git inside `~/repos/*`** (LP1); no `~/gt` agent hand-edits `~/repos`.
4. `gc pack refresh` / supervisor tick regenerates the skill sinks; stop/rebuild/restart the city to re-import.

*(This build itself commits only the design doc on the rig work branch, `push=false`; the BART-land step is **named here, not executed**.)*

---

## §6. Priming integration (REQ-005 / AC-5 — Taylor hard requirement)

**Acceptance criterion (verbatim):** *"a new QUIMBY boots already knowing how to feed the machine."*

Priming has **partially converged**: `mayor-math-prime` already loads the incumbent. The exact edits below (anchors quoted from current file text) close the gap; if the rename lands, they update the name — otherwise they add the missing pointer. **Do not assume a green field.**

### §6.1 `mayor-math-prime` — §6 Session toolkit (already loads it; update name on rename)

Current anchor line (mayor-math-prime `SKILL.md`, §6 "Session toolkit"):

> **`math-city-work`** — Dispatch work to the fleet. Use this after every brief approval or user request for work.

**Edit:** on rename, change to `**`feed-the-machine`** — Dispatch work to the fleet …`. If Scheme B (no rename), **no change** — this line already primes the skill. Also update the "Standing dispatch rule (MR1.x)" note (§2 of the same file) that currently points only at `[[mayor-math]] Rule 0` to additionally name the dispatch skill.

### §6.2 `mayor-math` — the "Current dispatch pattern" block (de-duplicate)

Current anchor lines (mayor-math `SKILL.md`):

> **Current dispatch pattern:** sling `--on build-basic-briefed` (fires a decision brief at the terminal step; `push=false` ships nothing) …

followed by the copied ```gc sling <rig>/gc.run-operator <bead> --on build-basic-briefed …``` block.

**Edit:** replace the *duplicated command block* with a one-line reference — *"To feed the machine, use `[[feed-the-machine]]` (the owning skill); this supplement keeps only the rig-prefix→coordinator table and convoy rules."* This removes the drift risk (RC-1) and makes `mayor-math` a *rig-table + fleet-rules* skill, with `feed-the-machine` owning the invocation.

### §6.3 `mayor-math-restart` — §3 dispatch reminder (HOMER's skill; name, don't clobber)

Current anchor line (mayor-math-restart `SKILL.md`, §3 "Orient and confirm"):

> **Dispatch reminder (authority: gsp-mnfj, supersedes gsp-geuo "always fork"):** Default dispatch is **SLING** … See [[mayor-math]] Rule 0 for the full decision table.

**Edit:** extend the reminder to load the dispatch skill at orientation — *"Default dispatch is **SLING** via `[[feed-the-machine]]` — the canonical 'bead + sling to fleet' skill. See [[mayor-math]] Rule 0 for the fork-vs-sling decision table."* This is what makes a fresh QUIMBY boot *already knowing how to feed the machine*.

### §6.4 HOMER coordination (OQ-4) `[OPEN]`

`mayor-math-restart` is **HOMER's in-progress work**. This proposal **names** the §6.3 edit but **does not implement it** and must **not clobber** HOMER's working tree.

> **OQ-4 recommendation:** sequence the `mayor-math-restart` edit **after** Taylor approves the naming (OQ-1) and **hand it to HOMER** (or a follow-up loop) to land in HOMER's lane — the `mayor-math` (§6.2) and `mayor-math-prime` (§6.1) edits can land independently since they are not HOMER-owned. **Taylor's call on timing (OQ-4).**

### §6.5 Verification of the acceptance criterion

After the refactor lands, a fresh QUIMBY running `mayor-math-restart` will: (1) read the dispatch reminder → sees `[[feed-the-machine]]`; (2) have it in the §6 priming toolkit; (3) on *"sling this to the fleet"* → resolve to `feed-the-machine` → hold the canonical `gc sling … --on <briefed-formula>` command **with no hand-rediscovery**. Criterion met.

---

## §7. Hygiene & boundary (REQ-006 / AC-6)

- **Owned-only edits.** Every proposed change is **mathcity-owned** (`math-city-work`→`feed-the-machine`, `sling-new-bead`→mathcity `sling-idea-to-mayor`, `mayor-math`, `mayor-math-prime`, and — HOMER-owned but mathcity — `mayor-math-restart`) **or an upstream PR** (`core.gc-work`, OQ-2). **No non-owned surface is edited.**
- **No cache / sink edits (P1.3).** `core.gc-work` is filled by a supplement or PR, **never** by editing `~/.gc/cache/…`. No file is created or modified inside a materialized `.claude/skills/**` / `.codex/skills/**` sink — *"Creating or modifying files in a sink → fail."* Renames edit the **pack source under `~/repos`** and let materialization propagate.
- **No gastown-vocab-as-identity.** No proposed skill adopts a gastown role/identity as its name; names describe the *dispatch action* only.
- **P1.13 README rows** — *"Every skill directory in a pack appears exactly once in that pack's README skills table"*, enforced same-commit by `update-README`. Rows required for every proposed NEW / RENAMED / RETIRED member:

  | Skill dir | README action | One-line purpose |
  |---|---|---|
  | `feed-the-machine` | **ADD** row (RENAMED from `math-city-work`) | Feed a single bead to the fleet pool at normal priority (briefed → decision brief). |
  | `math-city-work` | **UPDATE/REMOVE** row | Mark as alias/redirect to `feed-the-machine`, or remove after the deprecation cycle (no ghost rows). |
  | `sling-idea-to-mayor` | **ADD** row (RENAMED+MOVED from agent-skills `sling-new-bead`) | Relay a user's new-bead idea up to the Mayor to file + dispatch (`gc mail send mayor`). |
  | `sling-new-bead` (agent-skills) | **REMOVE/redirect** row in agent-skills README | Retired; points at mathcity `sling-idea-to-mayor`. |
  | `core.gc-work` supplement (if Option A) | **ADD** row | Supplements upstream `core.gc-work` with the fleet-sling idiom. |
  | `immediate-work`, `priority-work` | **UPDATE** description text only | Sharpen to the in-session / named-agent-P0 axes (no new rows). |

- **check-plan-hygiene applied to *this migration plan*.** The plan claims work **inside `mathcity/`** (owned) and one **upstream PR** (not a cache edit) — passes the Pack Portability & Boundary rules: owned-set edits, no sink writes (P1.3), README rows enumerated (P1.13), dogfood landing via `~/gt`→BART→`~/repos` (§5.4). No P-rule violation is introduced by the proposed migration.

---

## §8. Decision & next steps (REQ-007 / AC-7)

**Decision block for Taylor** — each choice with a recommendation + one-line rationale:

| # | Open question | Recommendation | Rationale |
|---|---|---|---|
| **OQ-1** | Final names / verb set | **Rename `math-city-work` → `feed-the-machine`** (old name as alias); keep `immediate-work` / `priority-work`; optional `priority-work → jump-the-queue`. | Action-named + already the trigger = maximal discoverability, which is the charge's whole point. |
| **OQ-2** | `core.gc-work` gap: supplement vs upstream PR | **Mathcity supplement now + upstream PR as follow-up.** | Unblocks the Mayor immediately; puts the durable fix where every city benefits. |
| **OQ-3** | Family boundary (adjacents) | **Referenced neighbors, not members** — limit the refactor to the 5 dispatch skills. | The messaging-skill overlap is a *separate* refactor; folding it in overruns the charge. |
| **OQ-4** | HOMER coordination timing | **Land `mayor-math`/`-prime` edits now; hand the `mayor-math-restart` edit to HOMER after OQ-1.** | Avoids clobbering HOMER's in-progress tree; the non-HOMER edits are independent. |
| **OQ-5** | Merge vs keep `immediate-work` / `priority-work` | **KEEP distinct, sharpen descriptions.** | They sit on different axes; a flag-mode mega-skill re-hides the axes (the RC-2 failure). |
| **OQ-6** | Trigger-phrase continuity | **Carry every legacy phrase as an alias for ≥1 deprecation cycle.** | Preserves Mayor muscle memory and symlink/trigger resolution through the rename. |

**Downstream path.** This build deposits its **terminal decision brief** (surfacing exactly the table above) → **Taylor adjudicates** the naming/structure → **only then** an execution build lands the renames/supplement/priming edits via the dogfood loop (§5.4). 

**Nothing was executed by this build.** No skill was created, renamed, merged, or retired; the sole artifact is this proposal document (plus the `.gc-builds` build artifacts). The naming/structure decision is now surfaced for Mayor → Taylor.
