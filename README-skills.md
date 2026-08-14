# mathcity — skills index

Parent: [README.md](./README.md)

**Single canonical cross-pack index of every skill in the mathcity pack family.**

134 skills across the parent pack and 7 subdomain child packs (ADR 0002). This file is the ONE complete list; the `## Skills` table in `README.md` and the tables in each `subdomains/*/README.md` are pack-local views of the same skills — do not treat them as competing indexes. When they disagree, **this file wins**.

**Maintenance (single source of truth — no competing updater):**
- `skill-creator-math` appends the new skill's row here as the last step of creating a skill.
- `update-README` reconciles this file against the `skills/` trees on any pack change (full drift-sync).
- Both target THIS file; neither writes a parallel index. Alias form: `mathcity.<name>` (parent), `mathcity-<sub>.<name>` (subdomain) per ADR 0002.

_Regenerate/verify with `/update-README`._

### Parent pack — `mathcity/skills/`  (56)

| Skill | Alias | What it does |
|---|---|---|
| `adjudicate-brief` | `mathcity.adjudicate-brief` | Use whenever a STANDALONE decision needs to be recorded persistently in a bd-managed rig — human adjudications, architecture choices, policy locks, gate-criterion additions |
| `authorize-git-operation` | `mathcity.authorize-git-operation` | Explicit human-authorization gate for irreversible git operations — push, force-push, merge, PR creation, branch deletion, release tag |
| `bead-check` | `mathcity.bead-check` | Use when the disposition of a specific bead is in question — stale, possibly superseded, mis-filed, orphaned, or in the wrong rig — and a recommendation is needed before anyone acts on it |
| `brief-prep` | `mathcity.brief-prep` | Specialized worker that owns the brief-prep pipeline end-to-end |
| `check-briefs` | `mathcity.check-briefs` | Report the current brief stack — compact table (Rig, Artifact, unlock_count, Age, Epic/linked) sorted by unlock_count descending |
| `check-claims` | `mathcity.check-claims` | Provenance triage on an artifact about to be acted on — finds the claims that are BOTH load-bearing (negating them changes a recommended action) AND unsourced or proxy-sourced (the instrument that produced them does not entail them), names the independent instrument that would re-derive each, and runs a whole-artifact coherence pass that re-derivation structurally cannot do |
| `check-mayor-mail` | `mathcity.check-mayor-mail` | Mayor-facing mail triage routine — scan the gc mail inbox, surface [ESCALATE CRITICAL/HIGH] first, and catch escalations the fleet raised into a void |
| `check-molecules` | `mathcity.check-molecules` | Complete molecule accounting across all rigs, by status and in order — BEING WORKED ON (live worker), STRANDED (in_progress, no worker — reclaim backlog), READY (dispatchable, priority-ranked); writes the full accounting to the configured city-side molecules directory and prints a capped per-status summary |
| `check-on-agent` | `mathcity.check-on-agent` | Check in on ONE running gc-managed worker session to answer what it is doing, whether its artifact landed, or whether it is stalled; observe first and only message after activity genuinely stops |
| `check-work` | `mathcity.check-work` | Decide whether the fleet is ACTUALLY doing work — the signal-trust hierarchy and anti-patterns for reading fleet state, plus routing to the right per-purpose checker |
| `catch-no-brainer` | `mathcity.catch-no-brainer` | PRELIMINARY v0.2 — classify a brief against the he-lele 5-criterion no-brainer test, plus recognize the capability-blocker shape (would-be no-brainer stalled by a permission/capability gap) and signal compact-form eligibility to downstre… |
| `communicate-with-other-agent` | `mathcity.communicate-with-other-agent` | Send and read messages between concurrent Claude Code agents via the shared city agent inbox |
| `compare-artifacts` | `mathcity.compare-artifacts` | Semantic-diff between two text artifacts |
| `create-bead-manifest` | `mathcity.create-bead-manifest` | Snapshot all genuine open beads (noise-filtered) into a dated hierarchical triage table under the configured city-side bead-manifests directory with 11 action categories and epic/convoy grouping |
| `coordinate-review` | `mathcity.coordinate-review` | Run an artifact through an iterative create/review loop until it converges to an approved state |
| `create-artifact` | `mathcity.create-artifact` | Dispatched by coordinate-review (payload contains a spec field and an optional artifact_type field, no action_items field) to produce a new artifact from a spec, or triggered directly by user phrases like "draft a skill for X", "draft a… |
| `create-brief` | `mathcity.create-brief` | Produce the durable, gated `.md` brief artifact for the brief stack from a code artifact (branch, bead-id, PR, diff, GH-issue-N) |
| `create-convoy` | `mathcity.create-convoy` | Create a properly configured OWNED convoy for an epic bead — the fan-out container for one WIP-dispatcher slot |
| `critical-review` | `mathcity.critical-review` | Act as a rigorous, adversarial reviewer of any artifact — SKILL.md files, plans, theorems, LaTeX, code, or any LLM-generated output |
| `dolt-init` | `mathcity.dolt-init` | Initialize the bd (beads) Dolt database and set the dolt remote in both the city-side rig and repo-side working copy |
| `dolt-pull` | `mathcity.dolt-pull` | Commit any pending beads changes locally, then pull from the Dolt remote |
| `dolt-push` | `mathcity.dolt-push` | Commit any pending beads changes and push to the Dolt remote |
| `doubt` | `mathcity.doubt` | Adversarial background fact-checker — forks a subagent told the current agent is WRONG, tasked with finding falsehoods in any claim the session makes. Non-blocking; surfaces verdict inline when fork completes. |
| `fan-out` | `mathcity.fan-out` | Fan an epic bead out into sub-beads (convoy members) WITHOUT consuming additional WIP-dispatcher slots |
| `file-briefs` | `mathcity.file-briefs` | Async brief-filing variant of grill-with-docs for Mayor onboarding |
| `formula-creator` | `mathcity.formula-creator` | Create a new formula TOML in a Gas City pack and validate gc/bd command surface before committing |
| `fp-finder-skill` | `mathcity.fp-finder-skill` | Fixed-point convergence engine for SKILL.md files |
| `gate-test-execution-silent` | `mathcity.gate-test-execution-silent` | G14 gate (test-execution-silent) |
| `gc-recycle-bead` | `mathcity.gc-recycle-bead` | Handle graceful lifecycle transitions for research beads — beads that contain mathematical decisions, session notes, or research context rather than purely actionable task steps |
| `get-best-apis` | `mathcity.get-best-apis` | Fetches live LLM benchmark rankings (IFScale / AA Intelligence Index) and current API pricing (input $/1M, output $/1M) across OpenRouter, Ollama, OpenCode, Anthropic, and OpenAI, then renders a self-contained HTML table sorted by score… |
| `get-best-models` | `mathcity.get-best-models` | Recommends the best open-weights / local LLM for a given hardware constraint and use case, using IFScale as the primary ranking metric and the memory-constraint formula (P*b <= available RAM) to filter candidates |
| `grill-and-present` | `mathcity.grill-and-present` | Produce decision-ready brief(s) on artifact(s) (branch, bead, PR, diff) by gathering all present-it sections, grilling the decision-maker on ambiguity one question at a time, running the artifact's tests (divide-and-conquer in parallel),… |
| `immediate-work` | `mathcity.immediate-work` | In-session synchronous dispatch — spawn the right agent NOW in the current session to complete a specific bead or task |
| `improve-test-execution-silent` | `mathcity.improve-test-execution-silent` | G14 improve step (test-execution-silent) |
| `intercept-bead` | `mathcity.intercept-bead` | Coordinator/Mayor-side skill for catching an INFLIGHT bead — a new bead that may supersede or affect an existing (old) bead — before it lands and gets lost, duplicated, or auto-dispatched |
| `is-good-experiment` | `mathcity.is-good-experiment` | Critical-review variant specialized for experiment proposals |
| `is-good-test` | `mathcity.is-good-test` | Thin wrapper around is-good-experiment specialized for test files |
| `mayor-math-handoff` | `mathcity.mayor-math-handoff` | Session-end handoff for the math-city Mayor: writes the chained handoff bead, run-log expansion, session-catalog entry, and restart prompt update |
| `mayor-math-prime` | `mathcity.mayor-math-prime` | Prime a fresh math-city Mayor session from the restart prompt, durable operation docs, session catalog, and handoff bead |
| `mayor-math-restart` | `mathcity.mayor-math-restart` | Full Mayor session orientation |
| `mayor-math` | `mathcity.mayor-math` | Supplement to gc.mayor for Gas Town (gt HQ) context |
| `nudge-city` | `mathcity.nudge-city` | Revive city workers that are stalled/asleep after a usage-limit reset by nudging each one to resume, finish its task, and free its run-operator slot |
| `present-briefs` | `mathcity.present-briefs` | Batch-present N briefs in parallel and maintain a hot queue (≥2 pre-presented at all times) |
| `present-it` | `mathcity.present-it` | Dump decision-ready context into the CURRENT conversation for ONE specific question about a code artifact (branch, bead, PR, diff, GH-issue), so the decision-maker can decide with no prior knowledge |
| `prime-clerk` | `mathcity.prime-clerk` | Prime a clerk session on its job as an outside agent in a Gas City — brief-reading duty under the one-bead model, verdict recording, and the mandatory agent-inbox channel to the mayor for questions |
| `prime-outsider` | `mathcity.prime-outsider` | Prime an outside (non-gascity) agent after compaction or a new session |
| `priority-work` | `mathcity.priority-work` | Async targeted dispatch — bump a bead to P0 and dispatch it explicitly to a NAMED agent (polecat or codex target) immediately, bypassing queue order |
| `remember-this` | `mathcity.remember-this` | Route an important mid-session insight to the right DURABLE store so it survives session death and is retrievable by ANY agent (Claude, Codex, future LLMs) |
| `repo-to-city` | `mathcity.repo-to-city` | Reference skill mapping repository names to their city-side rig, repo-side working copy, and beads prefix |
| `refine-bead-manifest` | `mathcity.refine-bead-manifest` | Convert a bead manifest into a partition B of work beads + one brief per b', where every bead in S is acted on by exactly one b'; approving b' triggers the corresponding dispatch action via mathcity.work |
| `revise-artifact` | `mathcity.revise-artifact` | Apply a set of action items to an artifact (SKILL.md, plan, code, LaTeX, theorem, etc.) and produce a revised version |
| `simple-work` | `mathcity.simple-work` | Dispatch a bounded, well-scoped task via simple-work-briefed (execute → file brief → finalize) when the work is a single operation (script run, repair, verification) and does not need the full build-basic-briefed lifecycle |
| `wake-city` | `mathcity.wake-city` | Actually WAKE a stalled Gas City — diagnose WHY the fleet is dead (tmux down, Dolt down, suspended rig, dead dispatcher, session- vs weekly-limit zombies), apply the correct revival per cause, and VERIFY work resumes; unlike nudge-city, handles weekly-limit-dead zombies (close-to-free-slot) and fails loud on capacity blocks |
| `write-issue-targeted` | `mathcity.write-issue-targeted` | File a high-quality GitHub issue against an explicitly targeted repo (default `tdupu/mathcity`), running the shared investigation standard and stopping at a human approval gate before anything is filed |
| `work` | `mathcity.work` | Feed a bead into the math-city fleet through the work router: continue known work directly, or commission fresh/ambiguous work through an approval brief before dispatch |
| `xkcd-927` | `mathcity.xkcd-927` | Reconcile or fix an issue that is spread across several beads / plans / PERTs / policy docs that duplicate, contradict, or prose-supersede each other — by CONSOLIDATING into the single existing source of truth, NEVER by writing a fresh a… |

### Brief-system — `subdomains/brief-system/skills/`  (3)

| Skill | Alias | What it does |
|---|---|---|
| `check-brief-policy` | `mathcity-brief-system.check-brief-policy` | Audit the current brief pipeline state against the brief-system POLICY.md (PP1.1 trinity, B2.x structure/ordering/resurface/freshness, B3.x decision records, N5 kill-switch, PP4.1 gate registry) |
| `decisions-to-briefs` | `mathcity-brief-system.decisions-to-briefs` | Convert pending decisions from conversation, a running list, or a durable decision inbox into adjudicable brief artifacts with machine-readable consequence blocks |
| `new-brief-policy` | `mathcity-brief-system.new-brief-policy` | Propose and apply an amendment to the brief-system POLICY.md (mathcity/subdomains/brief-system/POLICY.md) |

### Computing — `subdomains/computing/skills/`  (9)

| Skill | Alias | What it does |
|---|---|---|
| `check-computing-policy` | `mathcity-computing.check-computing-policy` | Audit computation code, a diff, or a project against the Computing Policy (mathcity/subdomains/computing/POLICY.md, C1.x–C4.x rules) |
| `check-mre` | `mathcity-computing.check-mre` | Check whether an MRE (Minimum Reproducible Example) file submitted by an agent satisfies the project's MRE policy at .claude/MRE-POLICY.md |
| `improve-package-README` | `mathcity-computing.improve-package-README` | Add or update documentation in a Magma or Sage project's README files and the corresponding README test files |
| `mag-to-notebook` | `mathcity-computing.mag-to-notebook` | Convert a Magma .mag test/script file into a Jupyter notebook (.ipynb) with a Magma kernel so the user can run and iterate on it interactively |
| `new-computing-policy` | `mathcity-computing.new-computing-policy` | Propose and apply an amendment to the Computing Policy (mathcity/subdomains/computing/POLICY.md, C1.x–C4.x rules) |
| `notebook-to-mag` | `mathcity-computing.notebook-to-mag` | Pull fixes and new code from a modified Jupyter notebook back into a versioned .mag file with an incremented index, then git add it |
| `notebook-to-package` | `mathcity-computing.notebook-to-package` | Promote Magma functions from a Jupyter notebook into proper package intrinsics in the appropriate package-*.mag file |
| `profile-magma` | `mathcity-computing.profile-magma` | Wrap the Magma code the user is working on in a profiling harness to find bottlenecks (slow intrinsics, memory hogs) |
| `update-issue` | `mathcity-computing.update-issue` | Replace a GitHub issue's body with a single up-to-date canonical statement, consolidating all prior body versions into ONE archive comment per issue (folded via HTML <details> blocks) |

### Pack development / hygiene — `subdomains/dev/skills/`  (26)

| Skill | Alias | What it does |
|---|---|---|
| `adjust-workers` | `mathcity-dev.adjust-workers` | Scale the number of concurrent run-operators on a Gas City rig — reads live session counts, proposes a max_active_sessions patch, and routes it through the briefed pack-change path (city-toml-via-packs-not-hand policy). |
| `audit-recent-work` | `mathcity-dev.audit-recent-work` | Produce a full accounting of work adjudicated in a session or date range — brief-record beads, decision beads, stack archives, and in-flight molecules — across all rigs. Distinguishes mid-flight build-basic-briefed molecules from genuine dispatch gaps. |
| `city-status` | `mathcity-dev.city-status` | Read-only Gas City fleet and work-queue snapshot — checks tmux liveness, active sessions, in-progress beads (with lease/heartbeat status), molecule step tables (steps done, +1h change, start/completion times), brief pipeline state (.pile/.stack counts, shuffler lock), and Dolt health. |
| `formula-creator-math` | `mathcity-dev.formula-creator-math` | Create a MathCity-owned briefed/work-boundary formula TOML with the enforced briefed-terminal-step convention |
| `formula-work` | `mathcity-dev.formula-work` | Dispatch a bead to the formula-creator-math formula, which drafts a mathcity formula TOML and gates it behind a human decision brief |
| `check-build-formulas-and-skills` | `mathcity-dev.check-build-formulas-and-skills` | Completeness audit for the mathcity formula and skill catalogs — checks formula/skill indexes and F-rule hygiene for MathCity-owned briefed/work-boundary formulas |
| `check-build-hygiene` | `mathcity-dev.check-build-hygiene` | Audit the CURRENT live install — gc/bd binaries, the three source repos, pack imports, and skill sinks — against the Pack Portability & Boundary Policy (mathcity/subdomains/dev/POLICY.md) |
| `check-city-policy` | `mathcity-dev.check-city-policy` | Audit a plan, diff, or the live running-city state against the City Operations Policy (mathcity/subdomains/dev/POLICY-city.md, CT-rules); reports PASS/PASS-WITH-NOTES/FAIL per CT-rule |
| `check-documentation-policy` | `mathcity-dev.check-documentation-policy` | Audit mathcity documentation against POLICY-documentation.md; reports stale behavior, local/private path leaks, missing parent links, missing examples/tests, and index drift |
| `check-formula-hygiene` | `mathcity-dev.check-formula-hygiene` | Audit a formula TOML or formula-creation skill against POLICY-formulas.md (mathcity formula policy); reports PASS/FAIL for each F-rule |
| `check-plan-hygiene` | `mathcity-dev.check-plan-hygiene` | Gate a plan doc or beads convoy against the Pack Portability & Boundary Policy (mathcity/subdomains/dev/POLICY.md) BEFORE any build starts |
| `check-wheel` | `mathcity-dev.check-wheel` | Gate a plan, implementation, or data artifact against the "no reinventing the wheel" invariant — detects existing resources that cover the proposed work, then produces a hygienic import recommendation via check-plan-hygiene when reinvention is found. |
| `check-zero` | `mathcity-dev.check-zero` | Wheel-check — survey existing gascity formulas/skills/orders, prior beads, code, Magma intrinsics, math databases (LMFDB, Stacks), Python packages, and known theorems before building anything from scratch. |
| `check-defer` | `mathcity-dev.check-defer` | Framework-cognition compliance checker — scans a skill, formula, or pipeline artifact and flags every place a framework makes a reasoning decision that should be a model call. |
| `hourly-check` | `mathcity-dev.hourly-check` | 12-hour city health watchdog — fires every hour, shows fleet/molecule/brief/Dolt snapshot, raises a prominent inline alert to the invoking session if stalls or usage limits are detected. |
| `improve-documentation` | `mathcity-dev.improve-documentation` | Update mathcity documentation hygienically after user-facing feature, formula, skill, policy, setup, or workflow changes; keeps examples, tests, parent links, and indexes aligned |
| `new-city-policy` | `mathcity-dev.new-city-policy` | Propose and apply an amendment to the City Operations Policy (mathcity/subdomains/dev/POLICY-city.md, CT-rules) — sole write path, human-gated |
| `new-documentation-policy` | `mathcity-dev.new-documentation-policy` | Propose and apply human-approved amendments to POLICY-documentation.md; sole write path for DOC rules |
| `new-formula-policy` | `mathcity-dev.new-formula-policy` | Propose and apply an amendment to the mathcity formula policy (mathcity/README-formulas.md + formula-creator-math hygiene gate) |
| `new-hygiene-policy` | `mathcity-dev.new-hygiene-policy` | Propose and apply an amendment to the mathcity hygiene policy (mathcity/subdomains/dev/POLICY.md) |
| `push-the-fleet` | `mathcity-dev.push-the-fleet` | Saturate the city fleet — finds all ready, unblocked beads across rigs and dispatches them via build-basic-briefed (mathcity.work pattern) until active workers reach TARGET (default 10). |
| `skill-creator-math` | `mathcity-dev.skill-creator-math` | Create a new skill in the mathcity pack family (parent `skills/` or a subdomain child pack per ADR 0002) and expose it to plain sessions and city agents through the configured skill materialization paths |
| `strand-sweep` | `mathcity-dev.strand-sweep` | Find beads and molecules slung but never run — detects immediate strands (empty assignee), dead formula run_target addresses, prose-only-blocked beads bd ready can't see, orphaned wisps (pool absent), and deadlocked molecules via flat step-count. |
| `switch-city-worker-provider` | `mathcity-dev.switch-city-worker-provider` | Controlled runbook for temporarily switching selected Gas City worker sessions between Claude-backed and Codex-backed providers and rolling them back. |
| `testing-work` | `mathcity-dev.testing-work` | Dispatch a bead to the smoke-test-briefed formula for lightweight test execution with a brief at the end |
| `update-README` | `mathcity-dev.update-README` | Keep the mathcity pack family's READMEs and skill exposure in sync after ANY owned-pack change — the pack-dev sibling of improve-package-README (which serves Magma/Sage packages) |

### LaTeX — `subdomains/latex/skills/`  (6)

| Skill | Alias | What it does |
|---|---|---|
| `check-labels-and-refs` | `mathcity-latex.check-labels-and-refs` | Scan LaTeX files for label/reference consistency, orphan labels/refs, and non-pinpoint cross-references |
| `check-latex-hygiene` | `mathcity-latex.check-latex-hygiene` | Audit LaTeX beads, branches, or .tex diffs against the LaTeX Subdomain Policy (mathcity/subdomains/latex/POLICY.md, LX-rules) |
| `check-latex` | `mathcity-latex.check-latex` | Produce the evidence block a human reviewer needs to approve or reject a notes.tex (or any notes-tier .tex) change before push/merge |
| `merge-latex-sections` | `mathcity-latex.merge-latex-sections` | STATUS: PLACEHOLDER — full F2 implementation deferred until F1 (latex-hurdle five-hurdle formula) is complete |
| `new-latex-bead` | `mathcity-latex.new-latex-bead` | Create a new LaTeX work bead that is well-formed under the LaTeX Subdomain Policy (mathcity/subdomains/latex/POLICY.md, LX-rules) and POLICY-beads.md BP7 from birth - real bd type (never an invented type, P5.3), [LATEX] label plus exactly… |
| `new-latex-policy` | `mathcity-latex.new-latex-policy` | Propose and apply an amendment to the LaTeX Subdomain Policy (mathcity/subdomains/latex/POLICY.md, LX-rules) |

### LMFDB — `subdomains/lmfdb/skills/`  (27)

| Skill | Alias | What it does |
|---|---|---|
| `check-lmfdb-hygiene` | `mathcity-lmfdb.check-lmfdb-hygiene` | Audit an LMFDB-type bead, diff, experiment proposal, or live type against the LMFDB Subdomain Policy (mathcity/subdomains/lmfdb/POLICY.md) — labels valid, experiment reproducible, server operations authorized, type fully wired |
| `configure-database` | `mathcity-lmfdb.configure-database` | Interactively create the project-local lmfdb-pipeline.conf by walking through each value one at a time (PGDATABASE, PGSCHEMA, DATA_DIR, SCHEMA_MD) |
| `configure-server` | `mathcity-lmfdb.configure-server` | Interactively create the project-local lmfdb-server.conf by walking through each SSH and compute-server connection value one at a time (REMOTE_HOST, REMOTE_USER, REMOTE_REPO, SSH_JUMP, SSH_KEY, MAX_PARALLEL, ALERT_EMAILS) |
| `create-lmfdb-type` | `mathcity-lmfdb.create-lmfdb-type` | Scaffold a new LMFDB data type in the Clifford-Bianchi Magma codebase (package-LMFDB.mag, package-IO.mag, schema.md) |
| `database-to-lmfdb-object` | `mathcity-lmfdb.database-to-lmfdb-object` | Restore an LMFDB wrapper object from PostgreSQL instead of a flat file |
| `database-to-magma` | `mathcity-lmfdb.database-to-magma` | Restore a native Magma object (CliffOrd, GrpPSL2Cliff, etc.) directly from the PostgreSQL lmfdb schema |
| `database-to-textfile` | `mathcity-lmfdb.database-to-textfile` | Export one or more objects from the lmfdb PostgreSQL tables back to DATA/ flat files |
| `database-update` | `mathcity-lmfdb.database-update` | Update a stored object in the lmfdb database by pulling it into Magma, applying user-specified recomputations or field changes, and writing it back |
| `lmfdb-object-to-database` | `mathcity-lmfdb.lmfdb-object-to-database` | Insert or update an LMFDB wrapper object directly into the lmfdb PostgreSQL schema, bypassing the DATA/ flat-file step |
| `lmfdb-object-to-string` | `mathcity-lmfdb.lmfdb-object-to-string` | Serialize an LMFDB wrapper object (or list of objects) to a pipe-delimited string |
| `lmfdb-object-to-textfile` | `mathcity-lmfdb.lmfdb-object-to-textfile` | Write an LMFDB wrapper object directly to its data file in one step |
| `magma-to-lmfdb-object` | `mathcity-lmfdb.magma-to-lmfdb-object` | Convert a native Magma object (CliffOrd, GrpPSL2Cliff, Gamma0, etc.) into its LMFDB wrapper type |
| `magma-to-textfile` | `mathcity-lmfdb.magma-to-textfile` | Serialize a raw Magma object (CliffOrd, GrpPSL2Cliff, etc.) all the way to disk in one pipeline |
| `new-lmfdb-type-policy` | `mathcity-lmfdb.new-lmfdb-type-policy` | Create a new LMFDB type the policy-conformant way — gate the justification (LM4.1), design and freeze the label scheme first (LM1.x, LM4.4), then drive create-lmfdb-type + update-schema, record the webpage decision, and finish with a che… |
| `plan-an-lmfdb-webpage` | `mathcity-lmfdb.plan-an-lmfdb-webpage` | Plan the full task breakdown and PERT chart for adding a new mathematical object type to the LMFDB website |
| `pull-data-from-server` | `mathcity-lmfdb.pull-data-from-server` | Pull computed flat files from the remote server to local disk — rsync into a timestamped snapshot under magma/DATA/snapshots/, then replace canonical local DATA/ working dirs from the most recent snapshot |
| `push-data-to-server` | `mathcity-lmfdb.push-data-to-server` | rsync canonical local magma/DATA/ working folders to the remote compute server, skipping all snapshot directories (data-*/) |
| `push-to-server` | `mathcity-lmfdb.push-to-server` | SSH into the remote compute server and git pull the latest master branch |
| `search-lmfdb` | `mathcity-lmfdb.search-lmfdb` | Query the LMFDB (L-functions and Modular Forms Database) via its MCP server |
| `setup-lmfdb-pipeline` | `mathcity-lmfdb.setup-lmfdb-pipeline` | Meta-setup skill: runs configure-database then configure-server to create both project-root confs the LMFDB skills need |
| `string-to-lmfdb-object` | `mathcity-lmfdb.string-to-lmfdb-object` | Restore an LMFDB wrapper object from a pipe-delimited string |
| `string-to-textfile` | `mathcity-lmfdb.string-to-textfile` | Write a pipe-delimited LMFDB string to the correct data file on disk |
| `textfile-to-database` | `mathcity-lmfdb.textfile-to-database` | Load DATA/ flat files into the local PostgreSQL database (clifford_bianchi_local) |
| `textfile-to-lmfdb-object` | `mathcity-lmfdb.textfile-to-lmfdb-object` | Restore an LMFDB wrapper object directly from disk in one step |
| `textfile-to-magma` | `mathcity-lmfdb.textfile-to-magma` | Restore a native Magma object directly from DATA/ in one pipeline |
| `textfile-to-string` | `mathcity-lmfdb.textfile-to-string` | Read raw pipe-delimited LMFDB strings from disk |
| `update-schema` | `mathcity-lmfdb.update-schema` | Update the LMFDB database schema across ALL affected files for the hecke/Clifford-Bianchi codebase |

### Magma — `subdomains/magma/skills/`  (2)

| Skill | Alias | What it does |
|---|---|---|
| `check-magma-hygiene` | `mathcity-magma.check-magma-hygiene` | Audit a Magma package, a diff, or a whole Magma project against the Magma Packages Policy (mathcity/subdomains/magma/POLICY.md) |
| `new-magma-package` | `mathcity-magma.new-magma-package` | Scaffold a new Magma package compliant with the Magma Packages Policy (mathcity/subdomains/magma/POLICY.md) — the package-<topic>.mag file with header block, the spec entry in dependency order, a README section stub (Purpose/Functions/De… |

### Proof assistants — `subdomains/proof-assist/skills/`  (5)

| Skill | Alias | What it does |
|---|---|---|
| `install-loogle` | `mathcity-proof-assist.install-loogle` | Install and configure a Loogle / Mathlib4 search MCP server (canonical: mathlas) so Lean 4 lemma lookup works through a connected MCP tool instead of only the raw web API |
| `search-arxiv` | `mathcity-proof-assist.search-arxiv` | Search arXiv by paper ID or keyword and return title, abstract, authors, and BibTeX |
| `search-mathlib` | `mathcity-proof-assist.search-mathlib` | Search Lean 4 / Mathlib4 declarations via the Loogle search engine — by name, type signature, subexpression, or conclusion pattern |
| `search-scholar` | `mathcity-proof-assist.search-scholar` | Search Google Scholar / Semantic Scholar for papers via MCP and return citations and metadata |
| `search-stacks` | `mathcity-proof-assist.search-stacks` | Query the Stacks Project (algebraic geometry / commutative algebra) by tag or keyword via its MCP server |
