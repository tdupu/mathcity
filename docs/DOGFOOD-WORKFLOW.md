# DOGFOOD-WORKFLOW — mathcity hotfix → hygienic loop (authoritative)

> **DO NOT ABRIDGE OR TRUNCATE THE CONTENTS OF THIS FILE WITHOUT EXPLICIT USER AUTHORIZATION.**
> Correct errors in place (P5.4); every section has been verified correct across multiple Mayor sessions.

**Owners:** Mayor session (<city-root> lane) + repo-side landing agent (<repos-root> lane). Read this before applying
any hotfix or promoting any pack fix. This is the process the whole team follows.

the human adjudicator's pattern, verbatim:
> (Experiment / HOTFIX) → (make the hygienic change to mathcity in
> `<city-root>/gascity-packs`) → (commit + push) → (repo-side landing agent stops the city + rebuilds
> from the good changes, which undoes the hotfixes) → meanwhile we LOG the
> hotfixes to test whether the city actually works.

---

## 0. GROUND TRUTH — what the running city actually reads (verified 2026-07-15, P5.4)

The city loads mathcity **pack content directly from `<mathcity-pack-root>/`** —
NOT from `<city-root>/gascity-packs`. Editing `<city-root>/gascity-packs` has **ZERO live effect**
on the running city. Evidence (each item was checked, not assumed):

1. **`city.toml` import is a local path into `<repos-root>`** —
   `<city-root>/city.toml:34`:
   ```toml
   [defaults.rig.imports.mathcity]
   source = "<mathcity-pack-root>"
   ```
   (also `[rigs.imports.mathcity]` at line 233, same source.)

2. **`gc order show brief-review-patrol` → `Source:` is under `<repos-root>`:**
   ```
   Source: <mathcity-pack-root>/orders/brief-review-patrol.toml
   ```

3. **`ls -l <city-root>/.claude/skills/` → every mathcity skill symlink points into `<repos-root>`:**
   ```
   mathcity-dev.check-build-hygiene -> <mathcity-pack-root>/subdomains/dev/skills/check-build-hygiene
   mathcity-computing.mag-to-notebook -> <mathcity-pack-root>/subdomains/computing/skills/mag-to-notebook
   ...
   ```
   (Contrast: `core.*` skills symlink into `~/.gc/cache/repos/<hash>/…`. Those are
   **git-URL imports**, which DO get cached under `~/.gc/cache/repos/<hash>/`.
   Local-path imports like mathcity do **NOT** cache — the running city reads the
   working tree at `<mathcity-pack-root>` on every load.)

**Consequence:** the only way a *content* change (skill text, formula body, order
field with no override key) goes live is to edit the active file under `<repos-root>`.

### Reconciling with parallel-repos-policy
`bd recall parallel-repos-policy`: `<repos-root>` is the repo-side landing lane; the Mayor session works in `<city-root>`
and syncs via GitHub. The awkward truth is that the **ACTIVE files are in
`<repos-root>` (the repo-side landing lane)**, while the Mayor session authors the hygienic fix in `<city-root>`. That is
exactly why this is a two-lane loop: the Mayor session authors + commits + pushes from `<city-root>`;
**repo-side landing agent** pulls into `<repos-root>` and is the only one who makes it live. Mayor session does
**not** hand-edit `<repos-root>`; content only reaches the running city through the repo-side pull.

---

## 1. TWO HOTFIX MECHANISMS — and which is LIVE from the <city-root> side

### (a) ORDER / AGENT-field hotfixes → `city.toml` (Mayor session / <city-root> lane) — **LIVE**
`city.toml` is **runtime config**, read on `gc start` reload. A hotfix here is live
immediately after the reload — no `<repos-root>`, no repo-side landing agent, no rebuild.

- **Order fields:** `[[orders.overrides]]` — matched by `name` (+ optional `rig`;
  empty `rig` matches city-level orders). Overridable fields, verified against the
  `OrderOverride` struct (`<repos-root>/gascity/internal/config/config.go:1977`):

  | TOML key | meaning |
  |---|---|
  | `enabled` | turn an order on/off (the patrol PAUSE hotfixes) |
  | `trigger` (`gate` = deprecated alias) | trigger type — e.g. `condition` (Fix-2 gate) |
  | `check` | condition-trigger check command (Fix-2 gate body) |
  | `on` | event-trigger event type |
  | `interval` / `interval_min` / `interval_max` | cooldown + dynamic-interval bounds |
  | `alert_after` / `critical_after` | doctor warn/critical thresholds |
  | `schedule` | cron expression |
  | `pool` | target session/pool (the `mathcity.brief-operator` re-pointing) |
  | `timeout` | per-order timeout |
  | `idempotent` | is dispatch safe to repeat (Fix-1 = `false` → fail-closed on gate timeout) |
  | `env` | env vars for exec orders |

- **Agent/pool fields:** `[[patches.agent]]` → `PoolOverride` (`Max *int`, etc.).
  (Note: the S6.13 `max=6` pool-cap hotfix is in this family; it did NOT show the
  desired behavior under a graceful reload — see hotfix-ledger #8. Being LIVE-capable
  is not the same as being effective.)

This is the family that makes the current churn containment live: patrol pauses
(`enabled=false`), Fix-1 (`idempotent=false`), Fix-2 (condition-gate via `trigger`+`check`).

### (b) CONTENT hotfixes (skill text, formula body, order field with NO override key) — **NOT live-hotfixable from <city-root>**
If the change is to file *content* — a skill's SKILL.md, a formula body, an order
field that `OrderOverride` doesn't expose — there is **no `city.toml` lever**. The
only live path is editing the active file under `<repos-root>`, which is **the repo-side landing lane**.

From the `<city-root>` side these go **straight to the hygienic path** (section 2). You
CANNOT hotfix them by editing `<city-root>/gascity-packs` — that tree is not read by the
running city (section 0). Editing it only *stages* the hygienic fix.

**Decision rule:** Is the change expressible as an `OrderOverride`/`AgentPatch` key?
→ yes: `city.toml` hotfix, live now. → no: it is a content change; skip straight to
"author hygienic in `<city-root>`, repo-side landing agent lands it."

---

## 2. THE FULL DOGFOOD LOOP (the human adjudicator's pattern), step by step

| # | Step | Owner | Where | Live effect |
|---|---|---|---|---|
| 1 | **HOTFIX** — apply `city.toml [[orders.overrides]]` / `[[patches.agent]]`, `gc start` reload | Mayor session | `<city-root>/city.toml` | LIVE now (if override-expressible). If it's a content change, **skip to step 3** and note "cannot hotfix from <city-root>" in the ledger. |
| 2 | **LOG the hotfix** | Mayor session | `<city-root>/mathcity-tests/hotfix-ledger.md` + run-log | — |
| 3 | **Author the HYGIENIC change** in the pack | Mayor session | `<mathcity-pack-root>/…` | STAGED, not live |
| 4 | **Bead it** — one bead per hygienic fix (gsp-*) | Mayor session | bd | — |
| 5 | **Commit + push** `<city-root>/gascity-packs` to the example-owner fork | Mayor session (the human adjudicator-authorized) | `git@github.com:example-owner/gascity-packs.git` | — |
| 6 | **RECONCILE + pull** into `<repos-root>/gascity-packs` (see §3 hazard) | repo-side landing agent | `<repos-root>` | — |
| 7 | **Stop the city, rebuild / re-import, restart** | repo-side landing agent | `gc stop` → re-import → `gc start` | Hygienic fix is now LIVE. **The rebuild undoes the hotfixes** (city.toml is not touched by the pack pull, but the hygienic fix now supersedes it). |
| 8 | **REMOVE the redundant `city.toml` hotfix overrides** | Mayor session | `<city-root>/city.toml` | The override is now redundant with the landed hygienic fix; leaving it is drift. Use the ledger's "remove-after-rebuild" column as the checklist. |
| 9 | **Verify + close beads** | Mayor session/repo-side landing agent | bd | — |

**Why hotfix first, then promote:** the human adjudicator's rule (top of hotfix-ledger.md):
"hotfix now for testing; promote to the hygienic pack fix only once the hotfix shows
the desired behavior." Steps 3–8 fire ONLY after the step-1 hotfix demonstrates the
desired behavior in the live city. If a hotfix fails (e.g. ledger #8), do NOT promote;
revert the inert override and re-test.

---

## 3. THE DIVERGENCE HAZARD — `<city-root>/gascity-packs` vs `<repos-root>/gascity-packs`

These are **two SEPARATE clones of the same example-owner fork** — not one working tree.
Changes in one are invisible to the other until pushed to GitHub and pulled.
**Current status (checked 2026-07-15, they ARE diverged):**

| | `<city-root>/gascity-packs` | `<repos-root>/gascity-packs` |
|---|---|---|
| remote | `origin → example-owner/gascity-packs` | `fork → example-owner/gascity-packs`, `upstream → gastownhall/…` |
| branch | **`hurdle-rename-integration`** | **`main`** (ahead 1 of `fork/main`) |
| HEAD | `6b3d743` "fix(hurdle-rename): apply RF-004…" | `717b9fb` "docs(mathcity): Rig wiring section…" |
| shares other's HEAD? | **NO** — `717b9fb` is not a known object here | **NO** — `6b3d743` is not a known object here |
| dirty | 8 files (5 skill SKILL.md staged edits + metadata + 2 untracked) | 2 untracked (`nudge-city/`, `packs.lock`) |

**The two HEADs do not share history** — different branches, and neither clone even
has the other's tip commit fetched. Uncommitted work differs on both sides
(`<city-root>` has staged skill edits incl. brief-prep/catch-no-brainer/create-brief/
mayor-math/present-briefs; `<repos-root>` has an untracked `nudge-city/` skill and
`packs.lock`).

**Hazard:** if Mayor session pushes `<city-root>`'s `hurdle-rename-integration` and repo-side landing agent naively
pulls into `<repos-root>`'s `main`, they will NOT fast-forward — conflicts and/or
lost/untracked work (`nudge-city/`, `packs.lock`) on the `<repos-root>` side.

**Reconciliation rule (do this BEFORE / AT step 6):**
1. Both agents state their branch + HEAD (`git rev-parse HEAD`, `--abbrev-ref HEAD`).
2. Agree on the target branch for the hygienic fix (likely merge/rebase
   `hurdle-rename-integration` → `main`, or cherry-pick the specific hygienic commit).
3. Preserve `<repos-root>` untracked work (`nudge-city/`, `packs.lock`) — don't let a
   checkout/clean blow it away.
4. Only then does repo-side landing agent pull + rebuild (step 7). A hygienic fix authored in `<city-root>`
   must be reconciled with `<repos-root>` before it can land, or the pull conflicts.

---

## 4. LOGGING DISCIPLINE — the rebuild is a checklist, not a memory test

Every hotfix MUST be recorded so that step 7's "undo the hotfixes" is mechanical.
Two channels minimum (per decision-recording-discipline):

1. **`<city-root>/mathcity-tests/hotfix-ledger.md`** — the table row: *what + where*,
   *Live?* (🟢 live / 🟡 staged-not-live / 🔵 designed / ❌ failed / ✅ done),
   *hygienic fix* (durable, `<repos-root>` unless noted), *bead*, *doc*. The "hygienic
   fix" column IS the remove-after-rebuild note — once that fix lands, the hotfix
   row's `city.toml` override is deleted (step 8).
2. **`<city-root>/mathcity-tests/run-log.md`** — the chronological S6.x narrative
   (mechanism, expected, actual, verdict).

**Each hotfix maps to its hygienic bead.** A hotfix with no hygienic bead is either
(a) an intended runtime control (mark N/A, e.g. ledger #5 auto_merge flag) or
(b) an untracked leak — file the bead. When repo-side landing agent rebuilds, the ledger's `Live?`
column tells exactly which `city.toml` overrides are now redundant and must be
removed; nothing relies on memory.

---

## TL;DR
- Running city reads mathcity from **`<repos-root>`**, not `<city-root>`. Editing `<city-root>/gascity-packs` is STAGING only.
- **`city.toml` overrides = LIVE hotfix** (Mayor session, <city-root>). **Content = NOT hotfixable from <city-root> → hygienic path only.**
- Loop: hotfix+log → author hygienic in `<city-root>` → bead → commit/push → repo-side landing agent reconcile+pull+rebuild → remove now-redundant overrides.
- The two `gascity-packs` clones are **diverged** (`hurdle-rename-integration`@`6b3d743` vs `main`@`717b9fb`, non-shared history) — RECONCILE before repo-side landing agent pulls or you get conflicts.
