# Mayor Onboarding — operate the Gas City the way it's working now

Parent: [../README-mayor.md](../README-mayor.md)

> Canonical, regression-proofing onboarding for every Mayor session (the math-city Mayor).
> This context was derived painfully over 11 generations — it is gold; do not
> throw it away. When something here proves wrong at source, correct it here in
> the same pass (P5.4). Home: `mathcity/docs/`.

## Reference docs — mandatory vs on-demand

**Read at every startup (mandatory):**

1. **[CITY-RESTART-CHECKLIST.md](./CITY-RESTART-CHECKLIST.md)** — Phase 0–6 step-by-step
   to bring the city up from cold and verify orders/formulas/events actually fire.
   *The single most valuable doc — it has restarted the city for 11 Mayor sessions.*

**Read on-demand only — NOT at startup. Each doc carries its own integrity guard; obey it.**

2. **[CITY-OPERATION-REFERENCE.md](./CITY-OPERATION-REFERENCE.md)** — system architecture,
   pools/agents/workers, brief-pipeline lifecycle, no-brainer system, correct command surface.
   *Trigger: verifying a command exists, diagnosing fleet/brief-pipeline issues.*
3. **[TEST-CYCLE-GUIDE.md](./TEST-CYCLE-GUIDE.md)** — dogfood/test cycle, two-layer
   system-under-test, test matrix, fix-at-source (P5.4) triage.
   *Trigger: before running any test or triaging a pipeline failure.*
4. **[DOGFOOD-WORKFLOW.md](./DOGFOOD-WORKFLOW.md)** — <city-root>↔<repos-root> duality and how a
   change actually reaches the running city.
   *Trigger: before applying a hotfix, making a pack change, or deploying anything.*

The live trust record is per-session shards in `<city-root>/mathcity-tests/run-log/`.
Write each session to `run-log/S{N}.md` (new file). KEEP AND EXPAND — the human adjudicator
values the command→result log highly. Full archive at `run-log/archive-S1-S15.md`.

## S11-corrected operational truths (the hard-won gold)

These are the things a fresh Mayor session must know to operate the city well.

**Restart & health**
- A cold or wedged city is fixed by **`gc restart`** — it gives a fresh tmux server and
  respawns the fleet (S8/S9: the "0 agents" wedge was a missing tmux server, not a spawn bug).
- **`gc status` "0/N agents" is a SLOW-API ARTIFACT** (the /status endpoint is slow cold).
  Do NOT trust the count. Verify fleet health via `tmux -L gt ls` + pane capture +
  `gc order history` + counting open "briefed publish slot" beads.
- Verify Dolt with `gc dolt health` (or a direct `bd list` timing), not the count.

**Verify at source (P5.4) — the discipline behind every S6–S11 win**
- Do NOT inherit behavioral claims from handoffs/plans/narratives. Ground every claim in
  the code / TOML / running behavior. S11 wins: caught the server running a STALE incomplete
  fix; a SHA-mismatch that was a false alarm (fix content present under a rebased SHA);
  a gate that could pass VACUOUSLY. Narrative docs are orientation, presumed stale.

**Server operations (aia-s27) — S11 policy `gsp-zgfq`**
- The server must NEVER have uncommitted changes. Author fixes LOCALLY (commit+push to
  master), then deploy ONLY via **`push-to-server`** (fetch + ff-merge). Pull data ONLY via
  **`pull-data-from-server`**. Never edit files directly on the server.
- ALWAYS verify the server code is correct BEFORE any live-write (the verify-first guard
  caught the incomplete-fix near-disaster in S11).
- Every server LIVE-WRITE = its own explicit per-node the human adjudicator authorization (dry-runs need none).
  Take a fresh backup before writes; the backup is the recovery point.

**The brief/work pipeline (trusted, D2-primary)**
- Dispatch work through **`build-basic-briefed`** (`gc sling <rig>/gc.run-operator <bead> --on
  build-basic-briefed --var interaction_mode=autonomous --var review_mode=agent --var
  drain_policy=separate --var push=false --var open_pr=false`). It runs the full build and
  fires a **decision brief** at the terminal slot instead of publishing — `push=false` means
  nothing ships; briefs accumulate on the human adjudicator's stack.
- Flow: work → build-basic-briefed → brief → catch-no-brainer → `.pile` → brief-shuffle →
  `stack` -> `/present-briefs` -> adjudication -> verdict edge -> `gc.publisher` -> repo-side landing agent lands.
- **FINDING #1 (every build)**: the build's commits live in DETACHED-HEAD worktrees that
  `gc.publisher` will NOT auto-recover — they must be cherry-picked/anchored before publish
  or the ship omits them. repo-side landing agent handles this on landing; always flag it.
- Finalize `control_quarantine` on a missing `.gc/scripts` path recurs every build — cosmetic.

**The <city-root> ↔ <repos-root> duality**
- **mathcity content is CANONICAL in `tdupu/mathcity` — `gascity-packs/mathcity` is DEPRECATED**
  (the human adjudicator, 2026-08-15). Verified at source: `city.toml` imports
  `<repos-root>/mathcity`, plus `<repos-root>/gascity-packs/{gascity,gascity/roles,contributing}`.
  `<repos-root>/gascity-packs/mathcity` is imported NOWHERE. Formula provenance agrees — a live
  molecule's `gc.formula_source` reads `<repos-root>/mathcity/formulas/work-briefed.toml`.
  Do NOT edit, mirror, or "sync" the `gascity-packs/mathcity` copies; a fix landed only there is
  a fix that never runs. (Concrete instance: the #149 store-scope fix is absent from both
  `gascity-packs/mathcity` copies of `work-briefed.toml` and this is CORRECT, not drift.)
- The running city loads non-mathcity pack content from `<repos-root>/gascity-packs`
  (local-path import). Pack-FILE edits under `<city-root>/gascity-packs` are STAGED-not-live;
  durable pack/skill/binary changes go through repo-side landing agent (<repos-root>) + a
  rebuild/reload. Beads sync via the Dolt remotes.
- The repo-side landing agent does git landings (push/merge/branch-delete), each behind a fresh
  the human adjudicator `authorize-git-operation`. Consensus with the repo-side landing agent before major work. Contact via
  `communicate-with-other-agent` (shared inbox `<city-root>/.claude/.agent-inbox.md`).

**Command-surface corrections (do NOT use — they don't exist)**
- `gc.publisher` does NOT merge to main (no build/publish path merges to master automatically).
- Non-existent verbs seen in old narratives: `gc config check`, `gc convoy show`,
  `gc dolt sql --db`, `gc event log`, and the `timeout` shell command (not on this mac).
  Use the Bash tool's own timeout, not `timeout`.

**Session hygiene**
- Farm out execution to forked workers (Fable/Opus plan; Haiku/Sonnet execute).
- Mail vs nudge: `gc mail` persists (handoffs/escalations); `gc nudge` is ephemeral. Default nudge.
- The mail inbox is a firehose of stale escalations — verify live before believing any
  (esp. Dolt-down escalations: check `gc dolt health` first).
- At session end: write a handoff bead, add a `session-catalog.json` entry, expand the run-log,
  and update `PROMPT-mayor-restart.txt`.

## Handoff-bead chain (each holds that session's full arc)
S1 gt-gnh7m · S2 gt-v6azs · S3 gt-a6ty4 · S4 gt-shezv · S5 gt-yygvi · S6 gt-n587i ·
S7 gt-00snc · S8 gt-mvq3s · S9 gt-qion7 · S10 gt-49683 · S11 gt-h16p88.

## Policies

Meta-policy governance (how policies work, lifecycle, cross-domain precedence):
**[POLICY-POLICY.md](../POLICY-POLICY.md)**

Canonical prefix + status registry for all domains:
**[docs/rule-prefix-registry.md](./rule-prefix-registry.md)**

| Domain | POLICY.md | Prefixes | Status |
| --- | --- | --- | --- |
| Meta-policy | [POLICY-POLICY.md](../POLICY-POLICY.md) | PP | Adopted |
| Brief system | [subdomains/brief-system/POLICY.md](../subdomains/brief-system/POLICY.md) | B N L E T D S | Adopted |
| Dev / build hygiene | [subdomains/dev/POLICY.md](../subdomains/dev/POLICY.md) | P | Adopted |
| LaTeX | [subdomains/latex/POLICY.md](../subdomains/latex/POLICY.md) | LX | Draft |
| Magma packages | [subdomains/magma/POLICY.md](../subdomains/magma/POLICY.md) | M | Draft |
| LMFDB | [subdomains/lmfdb/POLICY.md](../subdomains/lmfdb/POLICY.md) | LM | Draft |
| Computing | [subdomains/computing/POLICY.md](../subdomains/computing/POLICY.md) | C | Draft |

When citing a rule in a bead or skill, use the rule ID (e.g., `P1.6`, `B3.7`), not prose.
Adopted policies govern over any conflicting skill or implementation (PP1.7).
