# Pack Portability & Boundary Policy

Parent: [README.md](./README.md)

| Field | Value |
| --- | --- |
| Status | Adopted |
| Date | 2026-07-10 (amended 2026-07-12: P5.1 vocabulary/terminology; P5.2 workspace context files; P1.18 city root named-session fleet; P5.3 real bd types only; amended 2026-07-14: P5.4 truth-is-in-the-code; amended 2026-07-15: P1.19 append-don't-edit beads; amended 2026-07-20: P3.2 upstream issue template required before pr-pipeline; amended 2026-07-22: P1.20 check-wheel before design/skill dispatch; P5.5 Claude not a co-author; amended 2026-07-23: P1.21 dispatch idempotency; amended 2026-08-10: standalone mathcity source checkout; amended 2026-08-11: documentation workflow) |
| Decided | the pack owner, via grilling session (three open questions resolved; record at bottom) |
| Applies to | All packs the human adjudicator owns in this repo — the **owned pack set** (§ Scope) |
| Consumers | `check-hygiene` skill (to be built via skill-creator); mayor priming (`mayor-math`); any agent planning work in this repo |

Governs how work on an owned pack is planned, executed, and audited inside
the standalone `mathcity` source checkout — and, more broadly, how the whole local gascity install
(`gc`/`bd` binaries, pack content, city config) stays **reproducible on a
fresh machine, shareable with collaborators, and mergeable with upstream**.
Written as the source-of-truth for a plan/convoy/audit gate: every rule has
an ID and a pass/fail criterion a skill can cite.

## Scope

**Owned pack set** (the directories these rules call "yours"):

- `mathcity/` and every nested child pack under it — currently
  `mathcity/subdomains/{brief-system,computing,proof-assist,latex,lmfdb}/`
  (per [ADR 0002](../../docs/adr/0002-mathcity-subdomain-pack-model.md)).
- Any future pack the human adjudicator creates in this repo, added by amending this list.

The `check-hygiene` skill takes the owned-pack roots as input; it does not
hardcode `mathcity/`.

**Input shapes** — the same four pillars apply to all three:

1. **Plan doc** — checked on its stated file/dir touches and import changes.
2. **Beads convoy** — checked per-bead on each bead's declared scope, plus
   one whole-convoy aggregate pass (a convoy can violate Pillar 4 in
   aggregate even when each bead looks clean).
3. **Current-state audit** — the live repo/city/binaries checked directly
   against the P-rules (is what's running now re-derivable and shareable?).

## Pillar 1 — Reproducibility & portability

*A fresh install must reproduce your city; a collaborator must be able to
recreate what you're running; upstream must remain pullable.*

- **P1.1 Replay litmus.** If you `gc init` a scratch city and replay only
  the declared imports, you get the same behavior. Any step of the form
  "also run this command I ran manually that one time" → **fail**.
- **P1.2 Config flows through imports.** Changes to city behavior go through
  `gc import add` / `[imports.*]` entries + `gc import install` — never a
  one-off hand-edit to `city.toml`, or to a `pack.toml` outside the owned
  set. (Standing directive: city.toml changes come from pack updates, not
  hand-edits.)
- **P1.3 Never edit a materialized skill sink.** `.claude/skills/**` and
  `.codex/skills/**` are generated symlinks
  ([docs/skills-materialization.md](../../docs/skills-materialization.md)).
  Edit the pack source under the owned set and let materialization
  propagate (`gc pack refresh` / next supervisor tick). Creating or
  modifying files *in* a sink → **fail**.
- **P1.4 Local-path imports must be remote-backed.** Local-path imports
  (decision gt-ths6) are legitimate standing config, not just a dev-loop
  hack — **provided** the import target is a clean git checkout whose HEAD
  is pushed to the canonical remote (`<github-owner>/mathcity` for mathcity;
  `<github-owner>` fork for non-mathcity `gascity-packs` content).
  Then another machine reproduces the city by cloning the fork at that
  commit and using the same import. A local-path import whose target has
  uncommitted or unpushed content that the city depends on → **fail**.
- **P1.5 Published packs prove it.** For packs meant for third parties,
  reproducibility is proven by the registry machinery: a
  `validate_registry.py` content-hash-validated release plus the
  release-compatibility gates
  ([docs/INSTALL.md](../../docs/INSTALL.md)). A plan that claims
  "published" while skipping these → **fail**.
- **P1.6 Binaries match source.** The installed `gc` and `bd` must be clean
  builds of a synced HEAD: `go version -m <binary>` shows `vcs.revision`
  equal to the checkout's HEAD and `vcs.modified=false`. Builds and updates
  go through the sanctioned skills — `update-gascity-from-source`,
  `update-beads-from-source`, `update-gascity-packs-from-source`, and
  `update-mathcity-from-source` — which
  enforce exactly this. A dirty build, a binary from an untracked patch, or
  a stale binary shadowing the install on `$PATH` → **fail**. A
  working-tree artifact the build genuinely needs is legal **only if
  declared** — encoded in the corresponding update skill and listed in
  `.git/info/exclude` (precedent: the `go.work` beads-lockstep file in
  `<repos-root>/gascity`). Undeclared local patches → **fail**.
- **P1.7 Upstream stays pullable.** The per-repo reference invariants must
  hold or be restorable by the update skills:
  `<repos-root>/gascity` origin = fork = local main;
  `<repos-root>/beads` origin = local main;
  `<repos-root>/mathcity` origin = local main;
  `<repos-root>/gascity-packs` **fork-canonical** — the fork is deliberately
  ahead of upstream (gt-5cye); upstream is *merged in*, never mirrored over.
  Work that would make a future upstream merge structurally impossible —
  e.g. rewriting upstream-owned files in the fork — → **fail**. (This is
  the reproducibility face of Pillar 2: edits outside the owned set create
  permanent merge conflicts.)
- **P1.8 Skill exposure is symlinked, named, and complete.** Every skill an
  owned pack ships is exposed exactly two ways: (a) a **relative symlink**
  in `<repos-root>/agent-skills/skills/<name>` (never a real-directory copy —
  a copy forks the pack source), and (b) a hand-placed city-sink symlink
  `<city-root>/.claude/skills/<alias>.<name>` using the ADR 0002 alias
  (`mathcity.<name>` for the parent pack, `mathcity-<sub>.<name>` for a
  subdomain child pack). The sanctioned procedure is `skill-creator-math`.
  A dangling symlink, a real-dir duplicate, or a pack skill missing either
  exposure → **fail**. After any skill add/move/rename, run the
  `update-README` skill (mathcity-dev) — README drift is part of this rule,
  and README updates land in the same commit as the change.
- **P1.9 One real copy anywhere — adoption completes with origin dedup.**
  When a skill is adopted into the pack from another repo (agent-skills,
  hecke, any project repo), the pack copy becomes the **single real copy**;
  every consuming repo's copy becomes a relative symlink or is removed.
  P1.8 states this for agent-skills; this rule extends it to ALL repos.
  Duplicate real copies across repos → **fail** — unless the duplicate
  carries a tracked follow-up bead for its conversion (transition state,
  not an end state). (Origin: the 2026-07-10 hecke adoptions left 25
  duplicates pending exactly such a pass.)
- **P1.10 No private values in pack content.** Hostnames, usernames, SSH
  keys/jump hosts, database/schema names, alert emails, and absolute
  home-directory paths never enter pack content. Server- or
  database-touching skills read a **project-local, gitignored conf**; the
  pack ships only a placeholder `.conf.example` (model:
  `mathcity-lmfdb/assets/lmfdb-pipeline.conf.example`, inherited from
  hecke's `data-generation.conf`). Every adoption runs a scrub before
  commit: `gitleaks detect --no-git` on the adopted paths plus a targeted
  grep for IPs, `user@host`, `ssh` targets, key material, and absolute
  paths. Any hit → **fail**.
- **P1.11 Beads data plane syncs only to dedicated private repos.** A rig's
  bd `sync.remote` must be a dedicated `<github-owner>/<repo>-dolt` repo (the
  `dolt-init` naming invariant — never the code repo), and its
  `isPrivate=true` must be verified (`gh repo view`) before any data push.
  A public target or a code-repo target → **fail and HALT the sync** for
  that rig, never push-then-fix. (Origin: the gascity-packs rig's
  `sync.remote` was found pointing at the public code repo, 2026-07-10.)
- **P1.12 Every conf-driven skill ships a setup skill.** If a skill reads a
  project-local configuration file (a `.conf`, env file, or similar), the
  pack must ship a companion `setup-<name>` skill that creates that file
  interactively from the `.example` (copy, prompt for values, gitignore
  the copy, verify) — a fresh machine must go from `git clone` to a
  working skill without reverse-engineering the conf. A conf-reading
  skill with no setup skill → **fail**. (First instance:
  `setup-lmfdb-pipeline` for the lmfdb pipeline conf.)
- **P1.13 Every skill has a README table row.** Every skill directory in a
  pack appears exactly once in that pack's README skills table, with a
  one-line purpose. A skill with no row, or a row naming a skill that no
  longer exists, → **fail**. Enforced by the `update-README` procedure
  (same-commit rule) and audited by `check-build-hygiene`.
- **P1.14 Dependency pre-flight: graceful failure with actionable error.**
  Every skill that depends on an external resource — a project-local conf
  file, a tool (Magma, PostgreSQL), a database connection, an SSH server —
  MUST probe for that resource at the very start of its body and exit
  immediately if it is absent, with a human-readable error in this form:
  ```
  I'm sorry, I can't do that — <what is missing>.
  Run /<setup-skill> (or <fix action>) to set it up.
  (<One sentence on what the dependency enables.>)
  ```
  Silent fallback to defaults, partial execution past a missing dep, bare
  filesystem errors ("No such file or directory"), or a hard crash with no
  actionable message → **fail**. A dependency that is present but never
  checked → **fail** (an unchecked missing dep produces the same bad UX as
  a silent failure). For conf files specifically: probe the file exists
  *before* sourcing it; never let the shell error on `source` directly.
  (Named after the HAL 9000 pattern: "I'm sorry Dave, I can't do that" —
  but followed by a fix, not a refusal.)
- **P1.15 Dolt remotes are named after the repo, nowhere else.** Dolt
  storage is always a *separate, dedicated* GitHub repo; its name is
  mechanically derived: a code repo named `X` uses `<github-owner>/X-dolt` and
  nothing else. Dolt repos are never reused across code repos, renamed for
  convenience, or aliased to the code remote. Gascity-root mapping (the human adjudicator
  2026-07-13): the `gascity` rig (`<city-root>/gascity` — controls the binary,
  hosts upstream-PR work) follows the main rule with `<github-owner>/gascity-dolt`;
  the city HQ store (`<city-root>`, hq beads — management and cleanup of the city
  instance itself) syncs to the dedicated `<github-owner>/gascity-HQ-dolt`. When initialising a new rig's bead sync, derive the
  remote name as `<rig-name>-dolt` **using the DoltHub slug form** — DoltHub
  normalizes underscores to hyphens, so rig names with underscores use
  hyphens in the remote (e.g., `agent_skills` → `<github-owner>/agent-skills-dolt`,
  `magma_diff_alg` → `<github-owner>/magma-diff-alg-dolt`). Verify `isPrivate=true`
  (P1.11), then run `bd backup init`. A dolt remote whose name deviates from
  `<github-owner>/<rig-slug>-dolt` (outside the `<city-root>` exception) → **fail**.
- **P1.16 Repo-local skills stay repo-accessible.** Work for a repository
  must assume that collaborators of that repo do **not** have mathcity (or
  any the human adjudicator-owned pack) installed. A skill that repo collaborators use must
  remain discoverable inside that repo's own `.claude/skills/` directory
  without requiring mathcity — either as a real copy in the repo or via a
  mechanism the repo commits directly. Adoption into mathcity (P1.9) is only
  valid for such a skill when one of the following holds: (a) every current
  collaborator of the repo has mathcity installed, or (b) the repo retains a
  non-mathcity-dependent copy (a justified exception to P1.9's single-real-
  copy rule, noted in the commit). A plan that migrates a collaborator-facing
  skill *exclusively* to mathcity and removes the repo-local copy — making
  collaborators silently lose the skill — → **fail**. (Origin: 2026-07-11,
  hecke `textfile-to-magma` migration; Adam does not have mathcity.)
- **P1.17 Plans fix root causes; workarounds must be named and tracked.**
  A "hack" is a one-off fix that addresses a symptom without removing the
  mechanism that produces it — so the same class of problem can resurface
  without a new root-cause change. Plans **must never** present a hack as a
  fix. The test: can the plan state the invariant the fix establishes that
  prevents recurrence? If not, the plan is a hack.
  *Allowed exception — named workaround:* a temporary measure is permitted
  only when (a) the root cause is explicitly identified in the plan text,
  (b) a follow-up bead is filed or included in the convoy for the root-cause
  fix, and (c) the measure is explicitly labeled "workaround" (not "fix") in
  the plan. An unnamed workaround presented as a fix → **fail**. A resolution
  with no stated recurrence-prevention invariant → **revise** (state the
  invariant, or reclassify under the named-workaround path with a root-cause
  bead).
- **P1.18 City root imports the named-session fleet.** When the city is
  expected to process city-scope work (e.g. `gt-` prefix beads assigned to
  build-basic workers), the city root `pack.toml` (`<city-root>/pack.toml`) must
  explicitly import a pack that provides `[[named_session]]` entries for the
  build-basic worker fleet (implementation-worker, requirements-planner,
  task-decomposer, design-author, implementation-reviewer, and peers). Child
  rigs receive this fleet via `defaults.rig.imports` in `city.toml`; the root
  pack is separate and not covered by that default — it requires its own
  `[imports.*]` entry. A city root missing this import will show 0 named
  worker sessions in the root scope: `bd ready` accumulates `gt-` beads with
  no consumers indefinitely, silently. *Allowed exception:* a city that
  deliberately routes ALL work to child rigs and has no city-scope build-basic
  usage may omit the import — but must declare this in `pack.toml` with a
  comment: `# No city-scope build-basic — HQ worker fleet intentionally
  omitted.` Pass: `<city-root>/pack.toml` contains an import whose resolved
  `pack.toml` has at least one `[[named_session]] template =
  "implementation-worker"`. Fail: no such import exists AND `gc session list`
  shows 0 HQ-scope named worker sessions → **revise**.
- **P1.19 Append, don't edit beads.** When new information arrives about an
  existing bead, a plan/convoy must **append a new linked bead** — never
  rewrite the original's recorded content. New info about bead X → `bd create`
  a new bead and link it: `bd dep relate <new> <X>` (bidirectional
  `relates_to`), `--parent=<X>`, or `bd supersede <X> --with=<new>` when the
  new bead fully replaces X. Do **not** `bd update <X> --notes/--description`,
  perform description surgery, or delete X to carry new information — the
  appended chain **is** the update history. Correspondingly (read side): before
  acting on bead X, walk `bd dep tree X` + children and read every attached
  bead created **after** X — the newest attached beads carry current truth; X
  alone may be stale. Rationale: in the multi-clone Dolt setup (`<city-root>/<rig>` ↔
  `<repos-root>/<rig>` ↔ `<github-owner>/<rig>-dolt`) a row-write to a shared bead is the
  merge-conflict surface, while an additive insert merges cleanly; immutable
  beads are also a better audit trail (supersede records, never rewrite them —
  cf. decision-recording discipline and P5.4). *Allowed exceptions (precise):*
  (a) **status lifecycle on a bead you solo-own** — `bd update --claim`,
  `bd close --reason`, open/close transitions — is allowed (it does not rewrite
  recorded content); (b) an **immediate typo fix on a bead you just created and
  have not yet synced**; (c) in a **diverged store**, even lifecycle writes stay
  single-writer-per-side. Pass: every plan/convoy step that records new
  information about an existing bead does so by appending a new linked bead;
  content-bearing writes to an existing bead appear only under the carve-outs.
  Fail: any plan/convoy step that rewrites an existing bead's content
  (`bd update --notes/--description`, description surgery, or deletion) to carry
  new information, outside the carve-outs → **revise**. (Origin: the human adjudicator
  directive 2026-07-15, after a `bd update --notes` on a shared bead deepened a
  live Dolt row-conflict in the multi-clone setup.)

- **P1.21 Dispatch idempotency: pre-sling assignee check required.** Any agent,
  skill, or formula that dispatches work via `gc sling` (or equivalent) must
  verify the target bead has no active, non-stale assignee BEFORE dispatching.
  The check: `bd show <bead_id>` must return an empty Assignee field OR a stale
  claim (per `mathcity/gates/stale-claim.toml` criteria: lease expired OR
  heartbeat older than `STALE_CLAIM_WINDOW_SECONDS`). If the bead has an active
  non-stale assignee, the agent must abort cleanly with a visible signal
  ("ALREADY DISPATCHED — bead `<id>` has active assignee; aborting") and NOT
  re-sling. Competing workers that both pass the pre-sling check (a genuine
  race) must rely on `bd update --claim` atomicity at the substrate level —
  only the first claimant proceeds; the second sees a claim failure and backs
  off with a visible log entry. The post-sling verify-assignee gate (from
  `mathcity.work` doctrine, bead `he-uz9fg`) remains mandatory and is NOT
  superseded by this pre-sling check — both gates are required.
  *Allowed exceptions (precise):* (a) re-slinging is explicitly authorized by
  the human adjudicator in a current-session directive that names the bead and the reason for
  the re-dispatch; (b) the stale-claim gate confirmed staleness in the same
  dispatch step and the bead was released before re-slinging.
  Pass: every dispatch decision in a plan, skill, or formula includes a
  documented pre-sling assignee check with a stated abort path if non-empty
  and non-stale.
  Fail: any plan, skill, or formula that dispatches work via gc sling without a
  documented pre-sling assignee check → **revise**. Silent re-dispatch of an
  already-assigned bead → **fail** (P6.1 overlap: swallowed duplicate is a
  silent failure). (Origin: the human adjudicator directive 2026-07-23 Mayor session Q27; triggered
  by recognition that double-dispatch creates competing workers that consume
  duplicate fleet resources with no graceful resolution. Existing stale-claim
  gate covers recovery; this rule covers prevention.)

- **P1.20 Check-wheel before dispatching design or skill work.** Any plan,
  convoy, or dispatch for **formula design, methodology design, or skill
  design** must include a documented check-wheel pass before the dispatch step.
  The pass result is recorded in the plan doc's §E alternatives/check-zero
  section — at minimum one entry per alternative surveyed, each noting why it
  was adopted, adapted, or ruled out, and a stated verdict (adopt / adapt /
  rule-out). *Allowed exceptions (precise):* (a) trivial prose edits to an
  existing skill (typo, wording) where no architectural alternatives apply;
  (b) a skill that is a pure wrapper over a single uniquely-specified upstream
  tool with no meaningful alternative (the exception must be stated inline).
  Pass: the plan or design doc submitted for dispatch includes a §E
  check-zero/wheel-check section with at least one surveyed alternative and a
  stated verdict. Fail: any plan dispatched for formula, methodology, or skill
  build work without a §E wheel-check section → **revise**. (Origin: the human adjudicator
  directive 2026-07-22; triggered by Opus fork finding 5 missing wheel-check
  entries in design-master-methodology.md; filed via new-hygiene-policy.)

## Pillar 2 — Ownership boundary

*You own the owned pack set, nothing else.*

- **P2.1 Direct edits only inside the owned set.** Everything else —
  `gascity/`, `bmad/`, `pr-pipeline/`, `contributing/`, any other pack,
  gascity core, beads — is read-only. This matches the outside-agent scope
  boundary documented in operator-local context.
- **P2.2 Never edit under any `vendor/**` tree.** Vendored trees mirror an
  upstream project (Superpowers, bmad-method, gstack,
  compound-engineering-plugin); hand edits create silent fork drift the
  next vendor sync clobbers.
- **P2.3 Compose through imports.** Cross-pack composition happens through
  `pack.toml` imports, not copy-paste or file surgery into a pack you don't
  own.
- **P2.4 Scope discipline (= review rule B10).** Inside the owned set, fix
  what the plan scopes; note adjacent refactors as out-of-scope follow-ups.
  This is the same rule as
  [`contributing/skills/review`](https://github.com/gastownhall/gascity-packs/tree/main/contributing/skills/review)
  B10 — that skill enforces it at PR time; this policy enforces it at plan
  time. One rule, two gates.

## Pillar 3 — Upstream-change discipline

*Sometimes gascity core or another pack genuinely must change to unblock
you. Allowed — through the front door only.*

- **P3.1 PR only, never direct push** to anything outside the owned set —
  even trivial-looking fixes (per OUTSIDE-AGENTS.md).
- **P3.2 All upstream issue and PR handoffs go through briefed formulas.**
  `create-issue-briefed` is the correct mechanism for drafting upstream issue
  bodies. `pr-pipeline-briefed` is the correct mechanism for drafting upstream
  PR bodies. Both route the final text through the brief pipeline before
  anything is published to GitHub. The process is always:

  **Step 1 — File a GitHub issue using the appropriate template.**
  All upstream issues for `gastownhall/gascity` and `gastownhall/gascity-packs`
  are filed on `gastownhall/gascity`. Available templates (use the one that
  matches the work):
  - `bug_report.yml` — reproducible bugs and regressions
  - `docs_report.yml` — documentation problems
  - `feature_request.yml` — new capabilities
  - (`config.yml` is the chooser config, not a submission template)

  Every required field in the chosen template must be filled out completely
  before submitting.

  **Step 2 — Draft and adjudicate the issue body.**
  ```
  gc sling <rig>/<agent> create-issue-briefed --formula \
    --var source_bead=<bead-id> --var brief_slug=<bead-id>-issue
  ```
  The formula files a paste-ready issue body as a decision brief. After an
  APPROVE verdict, the authorized filing step creates the issue with the
  approved text.

  **Step 3 — Draft and adjudicate the PR body.**
  ```
  gc sling <rig>/<agent> pr-pipeline-briefed --formula \
    --var source_bead=<bead-id> --var issue_number=<N> \
    --var brief_slug=<bead-id>-pr-body
  ```
  The formula never pushes and never opens the PR. It files a template-complete
  PR body as a decision brief. After an APPROVE verdict, the authorized filing
  step opens the PR with the approved body.

  An upstream issue filed without a completed template and approved
  `create-issue-briefed` brief, or an upstream PR opened without a corresponding
  fully-completed issue and approved `pr-pipeline-briefed` brief → **fail**.
  No scattershot exploratory diffs against someone else's pack.
- **P3.3 Features: adoption-review bar.** README updated in the same PR, a
  `contributing/skills/review` scorecard pass, and — if it touches the
  `build-base` workflow contract — checked against
  [`gascity/REQUIREMENTS.md`](https://github.com/gastownhall/gascity-packs/tree/main/gascity/REQUIREMENTS.md), since
  methodology packs are a shared contract other packs stand on.
- **P3.4 Tracked as a bead.** "Just this once, outside the PR record" is
  the failure mode this policy exists to prevent.
- **P3.5 Agent context is explicit.** A plan states whether it runs as an
  *inside worker* (`GT_ROLE` set, city-dispatched, operates inside its
  assigned scope) or an *outside agent* (conservative git policy, never
  commits/pushes without explicit say-so, never pushes outside the owned
  set). Ambiguity about which context executes the plan → **revise**.
- **P3.6 Feature work runs improve-documentation.** Any feature, formula,
  skill, policy, setup, or user-facing workflow change must run
  `improve-documentation` before completion. The documentation pass updates
  the right README surface, examples, tests, formula/skill/subdomain indexes,
  parent links, and planned-issue links, or records a precise N/A reason.
  Pass: the brief, PR body, or handoff names the documentation pass and its
  result. Fail: a user-facing change lands with no documentation pass, no
  examples/tests where required by `POLICY-documentation.md`, or no explicit
  N/A reason → **revise**.

## Pillar 4 — Impact review at plan time

*Answer both directions explicitly before building. Complements
`contributing/skills/map-blast-radius` (which maps Go-code blast radius
inside gascity core); this is the pack-level, plan-time analogue.*

- **P4.1 Upstream impact.** Does the plan touch anything outside the owned
  set (gascity core, another pack, a vendor tree, beads)? If yes, is that
  edit already routed through Pillar 3, or is the plan quietly assuming a
  local patch "for now"? A silent local-patch assumption → **fail** (it
  also breaks P1.6/P1.7).
- **P4.2 Downstream impact.** If this ships, does it change a contract
  other consumers rely on: the `build-base` contract, a materialization
  assumption, an import key/alias another pack's formula references, a
  file another pack reads? And the mirror image: does the plan make
  something outside the owned set depend on an owned-pack-internal detail
  without going through a declared import? Either direction of leak breaks
  isolation even when nothing looks "hacked" locally.
- **P4.3 Convoy aggregate pass.** For a convoy, run P4.1/P4.2 per bead
  *and* once over the union of all beads' scopes — cross-bead interactions
  count.

## Pillar 5 — Vocabulary & terminology

- **P5.1 "gascity" is the name.** All plans, skill docs, AGENTS.md/CONTEXT.md,
  formulas, orders, and agent identities use "Gas City"/"gascity"/`gc.*`. The
  string "gastown" is permitted only as: (a) the GitHub org `gastownhall/*` in
  URLs, remotes, and import sources — never rewrite; (b) the upstream community
  pack name `gascity-packs/gastown/` and the CLI literal `--template gastown` —
  may be referenced as the upstream pack, never adopted; (c) upstream public-docs
  migration pages (`coming-from-gastown`, `gastown-*`) per the gc-docs style guide;
  (d) read-only historical artifacts (git history, `usage.jsonl`,
  `.gc/agents/dogs/gastown.*` state, forensic `rigs.json`/`town.json`).
  `gastown.*` agent identities (e.g. `gastown.polecat`, `gastown.mayor`) are NOT
  a runtime contract — the gastown pack import was removed 2026-07-09 (ba2ff381)
  and no `gastown.*` agent exists. Any `pool=`, run-target `default=`, assignee,
  or `$GC_AGENT` example using `gastown.*` is a dangling reference tracked in
  `mathcity/subdomains/dev/docs/IMPORTS-GC-MIGRATION-PLAN-2026-07-08.md`.
  Pass: no "gastown" in plan prose, skill docs, formulas, orders, or agent
  identity strings outside exceptions (a)–(d). Fail: any usage of `gastown.*`
  as a live identity or routing target → **revise**.

- **P5.2 Workspace context files reflect live CLI and runtime state.**
  Workspace context files — `AGENTS.md`, `CONTEXT.md`, `CLAUDE.md`, and any
  file loaded automatically into agent context — must describe only the *current*
  CLI surface and live runtime state. Specifically:
  (a) Every shell command block must resolve against the live `gc`/`bd` CLI
      (`gc <subcmd> --help` exits 0). Dead `gt` CLI verbs → **revise**.
  (b) No assertion about agent identity, pack import, or runtime infrastructure
      may contradict `gc agent list` / `gc prime` output.
  (c) The inside/outside agent distinction must be explicit: inside (GC) agents
      prime with `gc prime`; outside agents (Claude Code session, helping the human adjudicator)
      prime with `/prime-outsider`. Files that conflate the two → **revise**.
  (d) Paths to pack directories must resolve on disk. A path that moved
      (e.g. `mathematics/` → `mathcity/`) → **revise**.
  Scope: `<city-root>/AGENTS.md`, `<city-root>/CONTEXT.md`, `<city-root>/CLAUDE.md`, and any rig
  `AGENTS.md` that agents in this workspace read automatically.
  Allowed exceptions: historical content explicitly fenced with a "Historical"
  heading or `DEPRECATED — <date>` marker is exempt from (a)–(c).
  Pass: every command block uses live `gc`/`bd` verbs; no identity claim
  contradicts live agent list; inside/outside distinction present; all paths exist.
  Fail: any dead CLI verb, contradicted identity assertion, missing
  inside/outside distinction, or broken path → **revise**.

- **P5.3 Use only real, documented bd types.** Any policy document, skill file, AGENTS.md, plan, or bead-touching code that references a bead type must use only the types documented in `bd create --help` (`--type` flag): `bug`, `feature`, `task`, `epic`, `chore`, `decision`, `spike`, `story`, `milestone`, `event`. Undocumented types (e.g., `research-journal`, `brief`) are hallucinated — they cannot be executed and produce silent failures when passed to `bd create -t`. Custom types require explicit `types.custom` configuration in bd and a documented approval bead before they may appear in any policy pass/fail criterion. The canonical check: `bd create --help | grep -- '--type'` lists the live type set; any type string not in that list with no corresponding `types.custom` config entry → **fail**. (Origin: 2026-07-12 grilling — `type: research-journal` appeared in brief-system POLICY.md B3.7; replaced with `type: spike` + `[RESEARCH_JOURNAL]` label.)

- **P5.4 Behavioral claims are verified against source ("truth is in the code").** Any plan, skill doc, model, README, or workspace context file describing gascity / brief-system / workflow **behavior** must ground each behavioral claim in the authoritative source — the gascity Go source (`<repos-root>/gascity`), the workflow assets (`gascity/assets/workflows/**`), and the formula/order TOMLs — **not** in plan narratives or prior human summaries. Narrative/plan docs (e.g. `plans/*.md`) are orientation only and are presumed stale until checked. When a doc's behavioral claim contradicts the code, **the code wins**: the claim is corrected in the same pass (ties to P1.17 root-cause discipline and the fix-docs-inline habit). Pass: every non-trivial behavioral claim in a checked doc is traceable to a source file (Go/asset/TOML) and none contradicts current source. Fail: a plan/skill/model asserts gascity behavior that is unsourced **and** contradicted by the code, or repeats a known-stale narrative claim without re-verification. Exception: prose explicitly labeled non-normative ("conceptual overview") needn't cite source line-by-line but still may not contradict it. (Origin: 2026-07-14 grilling — `plans/gascity-restart-context.md` claimed `gc.publisher` "merges branch to main" — VERIFIED FALSE against code, no build/publish path merges to main; and carried command-drift bugs `gc config check` / `gc convoy show` / `gc dolt sql --db`, none of which exist in the binary. The human adjudicator: "the truth is in the code." Cross-ref bd memory `truth-is-in-the-code`.)

- **P5.5 Claude is not a co-author; its use is cited, not attributed.** Commits
  produced with AI assistance must NOT include `Co-Authored-By: Claude ...`
  trailers — Claude is not a legal author and the trailer falsely implies
  authorship on GitHub. Instead, cite AI assistance via the
  `[autogenerated by Claude <model> v<version> on <datetime>]` footer, per the
  `claude-commit` skill. *Allowed exceptions (precise):* none — the distinction
  (citation vs. authorship) applies universally. Pass: commit messages that use
  the `[autogenerated by ...]` footer form (or omit AI attribution entirely when
  only light assistance was used). Fail: any commit message containing a
  `Co-Authored-By: Claude` or `Co-Authored-By: claude-*` trailer → **revise**
  (remove the trailer; add the `[autogenerated by ...]` footer if AI wrote
  substantive content). (Origin: the human adjudicator directive 2026-07-22; grounded in
  `agent-skills/skills/claude-commit/SKILL.md` line: "Do NOT add
  `Co-Authored-By` lines.")

## Pillar 6 — Observability & fail-loud

- **P6.1 "Fail loud, never silent."** A plan, skill, order, formula, or code
  change must make failure **visible at the point of failure**. Every
  error / timeout / limit path must propagate loudly — a non-zero exit, a
  raised error, an escalation (mail / nudge to the mayor), or an explicit loud
  health signal. Catching an error and continuing in a degraded, partial, or
  frozen state **without emitting a visible signal** is prohibited: swallowed
  exceptions, silent retries that never escalate, freezing or stubbing state on
  a read/write timeout, silently bounding or truncating coverage, or dropping
  work with no log → **fail**. A passive check that only reveals the problem
  when someone runs a diagnostic (e.g. a `gc doctor` flag) does **not** satisfy
  this rule — the failure must announce itself when it happens.
  Allowed exceptions (precise): (a) expected, documented **no-ops are not
  failures** (a clean empty result — "no ready work", "nothing to sync" — needs
  no alarm); (b) **declared graceful degradation** is allowed only if it
  (i) emits a loud signal at the point of degradation and (ii) names the
  escalation target — "degrade quietly and hope someone notices" is never
  allowed; (c) **coalesced / rate-limited alerting** (to avoid an alarm
  firehose) is allowed only if it preserves the signal — first occurrence plus
  a periodic summary must still surface; it must not drop the signal.
  Pass: every error / timeout / degradation path either propagates loudly or
  emits an explicit escalation + log at the point of failure, with a named
  escalation target. Fail: any plan / skill / order / code that on
  error/timeout/limit catches-and-continues, freezes or stubs, truncates, or
  drops work **without a visible signal at the point of failure** — including
  "surfaced only via a passive diagnostic" → **fail**. (Origin: 2026-07-13
  incident `gs-8b3` — the `gc` order dispatcher swallowed a Dolt read-timeout
  every tick, froze order history at 02:05, degraded scheduling, and surfaced
  only a passive `gc doctor` flag; the one loud signal — the dolt-health
  firehose `gt-5xh` — was noise. Observability was inverted.)

- **P6.2 "A check must be able to fail."** Every check, gate, validator, or test
  must be **falsifiable against the condition it claims to detect**: there must
  exist a state of the world in which it reports failure, and its author must
  have observed it do so. A check that passes because it could not look is
  **worse than an absent one** — an absent check is a known gap, while a check
  that cannot fail is a false assurance that stops anyone looking again. This is
  the inverse of P6.1: P6.1 forbids failing silently, P6.2 forbids **passing
  blindly**.
  Three recurring shapes, all prohibited: (a) a **scan whose operand may not
  resolve**, where an empty result is read as "no violations" — a cwd-relative
  `find`/`grep`/`ls` in a script whose working directory is not guaranteed;
  (b) a **guard satisfied by prose**, where the check greps for a string that
  documentation keeps true forever regardless of behaviour; (c) a **validator
  that claims coverage it does not have**, whose name or description asserts
  agreement across N representations while it compares fewer.
  Pass: **for each condition the check claims to detect** — not for each
  assertion it makes — the check's own suite contains a case that **fails before
  the fix and passes after**, or the author records an observed failing run
  (fixture, injection, or reproduction) against that condition. A guard that
  correctly passes both before and after a fix is not thereby non-compliant; the
  requirement attaches to the claim, not to the line; a validator
  enumerates exactly the artifacts it compares, and its description claims no
  more. Fail: a check whose passing state is indistinguishable from "could not
  evaluate"; a guard whose condition is satisfied by a comment or by prose; a
  validator whose stated scope exceeds its compared set; any check shipped
  without an observed failing case → **fail**.
  (Origin: 2026-08-20, four instances in one file-family in one day —
  `brief-check.sh` running `find formulas` cwd-relative, matching nothing off
  the pack root and reporting PASS; `brief-manifest-current` unable to detect a
  stale index; the shim suite's legacy exemption guard, satisfied permanently by
  the twelve prose mentions of `decisions-track` that survive removing every
  write; and `mctl briefs validate`, whose help text promises to "prove
  canonical and redundant state agree" and which **exits 0 while reporting 318
  ERRORs and 1 FATAL** — measured on the `hq` store alone, 2026-08-20. Anything
  reading its exit code is told the city is clean. Two narrower holes sit under
  that: `_strict_invariants`' content comparison `MBRF020` fires **zero** times,
  because the artifact it compares against is absent city-wide and `_read_toml`
  cannot distinguish absent from corrupt; and a brief with **no index row at
  all** is invisible, because the stack-index loop branches only on `stale` and
  `inconsistent`, never on `missing`.
  An earlier draft of this rule asserted that `validate` had "no diagnostic code
  for legacy-manifest divergence at all." **That was false** — `MBRF008` and
  `MBRF013` both exist and `MBRF008` fires 84 times on `hq` alone. The claim came
  from a case-sensitive `grep "legacy"` against a registry that writes "Legacy",
  and it was caught in review. It is recorded here rather than quietly deleted
  because a rule about checks that cannot fail, drafted on the back of a search
  that could not find, is the most useful worked example this pillar has.)

## Pillar 7 — Interface discipline

The city has one interface. `mctl` is where repeated work lives, and it is the
**single point of failure by design**: work scattered across open bash in many
skills fails in many ways, quietly and differently each time, while the same
work behind one interface fails in one place, loudly, with an error code. A
central failure point is a thing that can be debugged once and fixed once.

**Rule kinds.** P7.1-P7.3 are **factual**: a call site either goes through `mctl`
or it does not, and a grep can say which. P7.1's *exemption* clause and P7.4 are
**judgement**: they ask an agent to weigh whether a reach-around is justified and
whether a group of skills has earned a surface. Judgement rules are enforced by an
agent reasoning and citing evidence, not by a pattern match — squeezing them into
a grep would produce a proxy that passes confidently on the cases it cannot see
(PP/`check-zero`).

- **P7.1 "Repeated work goes behind the interface."** Any operation `mctl`
  exposes must be performed **through** `mctl`. A skill, formula, order, gate,
  or check that shells out to `bd`, `git`, `dolt`, or the filesystem to do
  something `mctl` already does is a **violation, not a shortcut** — including
  when it is faster, when the caller "only reads", and when it runs *after* the
  canonical write to patch an artifact `mctl` did not update.
  Pass: every write to a canonical or redundant brief artifact is made by
  `mctl`. **There are five representations of a verdict, and a spec built on four
  is short one** (measured 2026-08-20): (1) the **bead**; (2) `decisions/<id>.toml`
  on the stack track; (3) `stack/.index.jsonl`; (4) the **brief file
  frontmatter**; (5) the **decisions-track manifest row** — which `mctl` does not
  write at all today, so it is the one that cannot agree by construction. (2) and
  (5) are the same decision record split across two tracks; count them separately,
  because checking one has never implied the other. The pile `.md` is `mctl`'s
  too, exemption or not.
  A non-`mctl` writer exists only under a **declared, named
  exemption**. *Granting one is a judgement call, not a checkbox*: a reasoned
  verdict must name the artifact, state why `mctl` cannot own it **today**, cite
  what would have to change for the exemption to lapse, and name who removes it
  then. **The lapse condition must be machine-checkable — a date or a testable
  state, not a narrative intention** — on the model of the no-brainer dry-run pin,
  which carries `expires=<ISO-8601-utc>` and auto-resumes the safe default when it
  lapses; an exemption whose expiry depends on someone remembering to revisit it
  will not expire. **Any check enforcing an exemption is itself bound by P6.2**
  and must ship an observed failing case: a guard satisfied permanently by prose
  is not a guard. An exemption that cites none of these is not declared, it is
  asserted.
  Fail: a wired skill or formula that writes such an artifact directly (`sed -i`, a
  shell redirect, a Python `.write()`/`open(...,"w")`, a bare `bd`/`dolt`
  mutation) without a declared exemption → **fail**; an exemption whose
  justification no longer holds → **fail**.
  (Origin: 2026-08-20 — `adjudicate-brief` declared `mctl` the canonical writer
  and then performed a second write of its own to the brief frontmatter and the
  decisions-track manifest. The consequence is that a verdict entered anywhere
  other than that skill leaves two representations stale; the same divergence
  was measured on 2026-08-04 across 17 briefs, whose manifest read `adjudicated`
  while their files read `ready-for-adjudication`, causing decided decisions to
  be re-presented.)

- **P7.2 "Consumers are siblings, never chains."** Every consumer of the city —
  the dashboard, the MCP surface, a skill, a human at a terminal — talks to
  `mctl` **directly**. A consumer must not reach the interface *through* another
  consumer's transport.
  Pass: each consumer's call path terminates in `mctl`; removing any one
  consumer leaves the others functioning unchanged. Fail: a consumer whose only
  path to `mctl` runs through a second consumer's protocol or process → **fail**.
  (Origin: 2026-08-20 — the dashboard reached `mctl` exclusively over the MCP
  stdio transport, with no direct path in existence: both of its clients,
  including the "in-process" one, construct `MctlMcpServer` and speak the full
  JSON-RPC protocol. A dashboard defect and an MCP defect were therefore
  indistinguishable from the outside.)

- **P7.3 "An interface gap is filed, never routed around."** When `mctl` cannot
  do what a caller needs, the deficiency is **the finding**. File it against
  `mctl`; do not implement the capability somewhere else.
  Pass: a capability `mctl` lacks is recorded as a tracked `mctl` gap, and the
  caller waits or is unblocked through `mctl`. Fail: any new direct store,
  filesystem, or `bd`/`dolt` access added because `mctl` did not expose it,
  without a filed gap it cites → **fail**; a "temporary" bypass with no tracked
  removal → **fail**.
  (Origin: 2026-08-20 — front-end requirements that `mctl` did not expose were
  initially carried as a dashboard wishlist rather than as interface
  incompleteness, which is what they were.)

- **P7.4 "Repeated skill work earns a surface."** *(Judgement rule.)* When
  several skills repeatedly perform the same operation through open bash, that
  work belongs behind a typed interface — an `mctl` subcommand or an MCP tool —
  rather than being restated in each skill. There is no threshold that decides
  this, and inventing one would be a bad proxy: two skills sharing a fragile
  multi-step `bd` incantation may warrant a surface, while ten sharing a single
  `ls` do not.
  **What an agent must weigh:** how many skills perform the operation; whether
  they perform it *identically* or have already drifted; what breaks silently
  when one copy is wrong; whether the operation writes or only reads; and whether
  `mctl` already exposes something adjacent that should simply be extended (run
  `check-zero` before proposing a new surface — an existing subcommand beats a
  new one).
  **What a reasoned verdict must cite:** the call sites by file and line, the
  observed drift between them if any, and either the `mctl`/MCP surface proposed
  or the reason the duplication is acceptable. **For an agent-facing operation,
  "leave it in open bash" is not an available verdict** — skills-as-agent-control
  is deprecated, so the judgement there is *which* surface and *when*, never
  *whether*; "acceptable" remains available only for duplication that is not
  agent-facing. Pass: a verdict citing those.
  Fail: duplication asserted to be fine with no survey, or a new surface proposed
  without `check-zero` — **fail**. Both directions are failures; this rule is not
  a mandate to build surfaces, it is a mandate to decide deliberately.
  (Origin: 2026-08-20, Taylor — *"groups of repeatedly used agent skills should be
  factored into an MCP rather than leaving an open bash for agents to mess up."*
  Written as a judgement rule per the same day's correction: a rule requiring
  judgement is enforced by an agent exercising it, which is a capability this city
  has and a grep does not.)


## Non-negotiables (quick checklist)

- No hand-edited `city.toml`, and no hand-edited `pack.toml` outside the
  owned set (P1.2).
- No silent failures — every error / timeout / degradation path surfaces
  loudly at the point of failure, never only via a passive diagnostic (P6.1).
- No check that cannot fail — every gate/validator ships with an observed
  failing case, and claims no coverage beyond the artifacts it compares (P6.2).
- No writer but `mctl` for a canonical or redundant brief artifact, absent a
  declared and still-valid exemption (P7.1).
- No consumer reaching `mctl` through another consumer's transport — the
  dashboard and the MCP surface are siblings, not a chain (P7.2).
- No bypass for a missing `mctl` capability — file the interface gap (P7.3).
- No repeated skill work left in open bash undecided — survey it and record
  a reasoned verdict either way (P7.4).
- No edits under any `vendor/**` tree, ever (P2.2).
- No edits inside a materialized `.claude/skills/**` / `.codex/skills/**`
  sink (P1.3).
- No direct push outside the owned set — PR only (P3.1).
- No upstream PR without a corresponding GitHub issue filed first using the
  appropriate template (`bug_report.yml` / `docs_report.yml` /
  `feature_request.yml`) with every required field completed (P3.2).
- No upstream issue filed without an approved `create-issue-briefed` brief
  (P3.2).
- No upstream PR opened without an approved `pr-pipeline-briefed` brief (P3.2).
- Docs+scorecard review for features (P3.3).
- No undeclared working-tree patches feeding a build; no dirty binaries
  (`vcs.modified=false` or it doesn't ship) (P1.6).
- No state the city depends on that exists only on this machine —
  committed and pushed to the canonical remote, or it isn't real (P1.4).
- No real-directory copies of pack skills in agent-skills, no dangling
  exposure symlinks, no un-exposed pack skills (P1.8).
- No duplicate real copies of a pack skill in ANY repo — adoption isn't
  done until the origin is a symlink or gone (P1.9).
- No hostnames, keys, schema names, or other private values in pack
  content — conf.example only, scrub on adoption (P1.10).
- No bead-data push to anything but a verified-private `<repo>-dolt`
  target (P1.11).
- No conf-driven skill without a companion `setup-*` skill (P1.12).
- No skill without a README table row — and no ghost rows (P1.13).
- No skill whose external dependencies are unchecked — every dep gets a
  pre-flight probe with a "I'm sorry, I can't do that" error block (P1.14).
- No migration of a collaborator-facing repo skill exclusively to mathcity
  without a repo-local fallback or confirmed mathcity adoption by every
  collaborator (P1.16).
- No plan that presents a hack as a fix — every resolution must state the
  invariant that prevents recurrence, or be explicitly named a workaround
  with a root-cause follow-up bead (P1.17).
- City root `pack.toml` must import a pack providing the named-session fleet
  (implementation-worker etc.) when city-scope (gt-) build-basic work is
  expected; omission silently starves the gt- queue (P1.18).
- No dispatch via `gc sling` without a pre-sling assignee check; active
  non-stale assignee → abort with visible signal, never re-sling silently;
  post-sling verify-assignee gate also mandatory (P1.21).
- No drive-by scope creep, even inside the owned set (P2.4 / B10).
- No "gastown" as a live agent identity, routing target, or plan vocabulary —
  `gastown.*` agents are dead; use `gc.*` / `mathcity.*` replacements (P5.1).
- No dead CLI verbs (`gt`), broken pack paths, or missing inside/outside agent
  distinction in workspace context files (`AGENTS.md`, `CONTEXT.md`) — P5.2.
- No hallucinated bd types in policy prose, skill docs, or mechanical checks —
  only documented types (`bug|feature|task|epic|chore|decision|spike|story|milestone|event`);
  custom types require `types.custom` config + approval bead (P5.3).

## Verdict vocabulary

Reuses the brief-cycle Decision vocabulary ([CONTEXT.md](../../../CONTEXT.md)) —
no parallel vocabulary is introduced:

- **approve** — no P-rule violations; plan/convoy is clean to build (audit
  mode: current state is compliant).
- **revise** — fixable violations; the verdict names the specific P-rule(s)
  broken, the file/directory that triggered each, and a compact brief that
  can seed a fresh brainstorming session to re-derive the plan around the
  constraint (audit mode: a drift list with per-item remediation).
- **reject** — the plan's core approach requires violating a pillar with no
  workaround (e.g. the goal is unreachable without editing gascity core
  outside the PR path). Send back for a different approach, not a patch.
  (Audit mode: not applicable — audits produce approve/revise/defer.)
- **defer** — needs a human call: ambiguous ownership, a genuinely
  contested "is this upstream's problem or mine". Escalate, don't guess.

## Resolved questions (2026-07-10 grilling)

1. **Scope:** all owned packs, not `mathcity/` alone — ADR 0002's subdomain
   child packs already make "your pack" a set; the skill parameterizes on
   owned-pack roots.
2. **Input shape:** plan docs *and* convoys *and* current-state audits —
   the policy's real subject is being able to pull from upstream, rebuild
   this install on another machine, and share it with collaborators; a
   binary or config that diverges from pushed source can't be shared or
   recreated.
3. **Placement:** this file, `mathcity/subdomains/dev/POLICY.md` — the
   normative doc of the `mathcity-dev` child pack (ADR 0002 nested-pack
   model), created in the same session. Pack development is its own
   functional domain, sibling of brief-system/computing/etc.; the future
   `check-hygiene` skill lives here too (materializing as
   `mathcity-dev.check-hygiene`), and the policy is also intended to prime
   the mathcity mayor.

## References

- Operator-local context files — outside-agent role, git authority, and scope boundary this policy extends
- [docs/adr/0002](../../docs/adr/0002-mathcity-subdomain-pack-model.md) — owned pack set layout
- [docs/skills-materialization.md](../../docs/skills-materialization.md) — why sinks are generated, not source
- [docs/INSTALL.md](../../docs/INSTALL.md) — registry publishing and import checks
- [gascity/REQUIREMENTS.md](https://github.com/gastownhall/gascity-packs/tree/main/gascity/REQUIREMENTS.md) — the `build-base` contract (Pillar 3/4 downstream surface)
- [contributing/skills/review](https://github.com/gastownhall/gascity-packs/tree/main/contributing/skills/review) (B10) and [map-blast-radius](https://github.com/gastownhall/gascity-packs/tree/main/contributing/skills/map-blast-radius) — the PR-time gates this plan-time gate complements
- The update-from-source skills — the sanctioned update procedures whose invariants P1.6/P1.7 encode

---

## Change Log

### 2026-08-11 — P3.6 added: feature work runs improve-documentation
Feature, formula, skill, policy, setup, and user-facing workflow changes must
run `improve-documentation` before completion. Triggered by: the human
adjudicator directive that docs must stay source-aligned, example-backed, and
not drift into slop. Exceptions: precise N/A reason recorded in the brief or
handoff.

### 2026-08-10 — P1.4/P1.6/P1.7 clarified: standalone mathcity source checkout
Mathcity pack imports now source from the standalone `<repos-root>/mathcity`
checkout, backed by `<github-owner>/mathcity`, rather than from the legacy
nested checkout path. The sanctioned update path includes
`update-mathcity-from-source`, and reproducibility checks include the
`<repos-root>/mathcity` origin/local-main invariant. Triggered by: the human
adjudicator directive to import from mathcity, not gascity-packs. Exceptions:
none.

### 2026-08-11 — P3.2 updated: upstream issue and PR text are briefed handoffs
Upstream issue bodies now route through `create-issue-briefed`, and upstream PR
bodies route through `pr-pipeline-briefed`. Both formulas file decision briefs
and never publish to GitHub directly; an authorized filing step uses the
approved body after adjudication. The older unbriefed handoff rule was replaced
so issue and PR text share the same human-adjudicated boundary.

### 2026-07-15 — P1.19 added: append, don't edit beads
New information about an existing bead is recorded by appending a new linked
bead (`bd dep relate` / `--parent` / `bd supersede`), never by rewriting the
original (`bd update --notes/--description`); readers walk `bd dep tree` for
newer attached beads. Triggered by: the human adjudicator directive 2026-07-15 — row-writes to
shared beads are the merge-conflict surface in the multi-clone Dolt setup;
additive inserts merge cleanly and give a better audit trail. Exceptions: status
lifecycle on solo-owned beads; typo fix on a just-created unsynced bead;
single-writer-per-side in a diverged store.

### 2026-07-14 — P5.4 added: truth is in the code
Behavioral claims about gascity/brief-system/workflow must be grounded in source
(Go source, workflow assets, formula/order TOMLs), not plan narratives; code wins
on contradiction and the doc is fixed in the same pass. Triggered by: 2026-07-14
mayor-math grilling — `plans/gascity-restart-context.md` asserted `gc.publisher`
"merges branch to main" (verified FALSE: no build/publish path merges to main; the
gastown refinery was removed 2026-07-09/ba2ff381) and carried three non-existent
`gc` commands. Exceptions: prose explicitly fenced as non-normative "conceptual
overview" (still may not contradict source). Cross-ref: bd memory `truth-is-in-the-code`.

### 2026-07-12 — P1.18 added: city root imports the named-session fleet
City root `pack.toml` must explicitly import a pack providing `[[named_session]]`
entries for the build-basic worker fleet when city-scope work is expected.
Triggered by: gastown pack removal (ba2ff381) silently dropped named sessions from
HQ; 99 gt- beads accumulated with 0 consumer sessions. Child rigs get the fleet
via `defaults.rig.imports` in `city.toml`; root pack requires its own import.
Exception: cities with no city-scope build-basic usage may omit with a comment.

### 2026-07-12 — P5.2 added: workspace context files reflect live CLI
Opens P5.2. Codifies that AGENTS.md/CONTEXT.md must use live `gc`/`bd` verbs,
must not contradict `gc agent list`, must include inside/outside agent distinction
(inside→`gc prime`; outside→`/prime-outsider`), and must have valid pack paths.
Triggered by: Fable structural audit + the human adjudicator directive that check-build-hygiene
must cover workspace context files. Enforcement: check-build-hygiene §11 (gs- bead
filed by Fable agent). Exceptions: explicitly fenced historical sections.

### 2026-07-22 — P5.5 added: Claude is not a co-author
Commits with AI assistance use `[autogenerated by Claude <model> ...]` footer,
never `Co-Authored-By: Claude`. Grounded in `claude-commit` skill (line: "Do NOT
add Co-Authored-By lines"). Triggered by: the human adjudicator directive 2026-07-22.
Exceptions: none.

### 2026-07-22 — P1.20 added: check-wheel before design/skill dispatch
Any plan or convoy for formula design, methodology design, or skill design must
document a check-wheel pass in a §E alternatives/check-zero section before
dispatch. At minimum one alternative surveyed per plan, with a stated verdict.
Triggered by: Opus fork finding 5 missing wheel-check entries in
design-master-methodology.md + the human adjudicator directive 2026-07-22 (new-hygiene-policy).
Exceptions: (a) trivial prose edits; (b) pure wrappers over uniquely-specified
upstream tools (stated inline). 5 follow-up beads filed: gsp-7wpbz, gsp-z4u0i,
gsp-n018o, gsp-6qydb, gsp-lxp6h.

### 2026-07-12 — P5.1 added: "gascity is the name" (vocabulary & terminology)
Opens Pillar 5. Codifies that "gastown" is no longer a valid runtime identity or
plan vocabulary — the gastown pack was removed 2026-07-09 (ba2ff381) and all
`gastown.*` agents are dangling references. Triggered by: Fable terminology audit
that found the `reference.gc-cli` memory was stale (incorrectly asserted "gastown.*
is a runtime contract"). Exceptions: (a) `gastownhall/*` org in URLs, (b) upstream
pack/template name as a proper noun, (c) gc-docs migration pages, (d) read-only
historical artifacts. Migration tracked in `mathcity/subdomains/dev/docs/IMPORTS-GC-MIGRATION-PLAN-2026-07-08.md`.
| 2026-07-13 | P1.15: gascity-root mapping rewritten — `gascity` rig (binary/upstream-PR work) uses `<github-owner>/gascity-dolt` per the main rule; city HQ store (`<city-root>`, instance management) uses dedicated `<github-owner>/gascity-HQ-dolt` | human verdict (hq canon question): HQ-dolt canonical; supersedes the old `<city-root> uses gascity-dolt` exception set by ecc11604 |

### 2026-07-23 — P1.21 added: dispatch idempotency (pre-sling assignee check)
Any agent, skill, or formula dispatching via `gc sling` must verify the target
bead has no active non-stale assignee before dispatching. Active assignee →
abort cleanly with visible signal ("ALREADY DISPATCHED"); do not re-sling.
Competing workers that race past the pre-sling check resolve via `bd update
--claim` atomicity (second claimant backs off). Post-sling verify-assignee gate
(mathcity.work doctrine) remains mandatory alongside this rule. Triggered by:
the human adjudicator directive 2026-07-23 Mayor session Q27: "Dispatching work should be idempotent.
If we deploy the same work twice the city structure should be such that it
doesn't matter. We will not do extra compute, we will not do duplicate compute.
Tasks which are competing should resolve gracefully." Existing stale-claim gate
covers recovery; this rule covers prevention. Exceptions: (a) explicit the human adjudicator
in-session re-dispatch authorization naming the bead and reason; (b) stale-claim
gate confirmed staleness and bead was released before re-slinging.
