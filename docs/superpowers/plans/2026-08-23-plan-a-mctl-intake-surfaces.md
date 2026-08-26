# Plan A — mctl Intake Surfaces (#185) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking. Landings are repo-side (BART) behind
> `authorize-git-operation`; run `check-plan-hygiene` before dispatching this plan.

**Goal:** Give the typed surface the three intake tools scoped under #185 — `create_github_issue`
(defect → issue, removing the accidental human gate at loop step 1), `create_defect_bead`
(defect → bead when no issue exists yet), and `standardize_github_issue` (make an existing issue
hygienic in place, additive-only per #52) — so a Mayor that finds a defect can file it without a
human carrying it.

**Architecture:** All three follow the existing mctl effect-plan pattern (`dry_run=true` default
returning an EffectPlan; `dry_run=false` applies), emit typed diagnostics registered in
`assets/mctl/diagnostics.toml` (new `MGHW_*` family — GitHub-write), and go through the shared
GitHub write layer added to `mctl_core/github_issues.py` (today read-only: `fetch_issue`,
`rig_for_issue`, `IssueSnapshot`). GitHub writes shell out to `gh` exactly as `orders.py` shells
to `gc`. Issue bodies are drafted against the LIVE `.github/ISSUE_TEMPLATE/*.yml` of the target
repo (the `create-issue` skill's rule: the repo's template is the enforcement point).

**Tech Stack:** Python (mctl_core), `gh` CLI subprocess, pytest with the #203 served-response
schema-validation pattern (`tests/mctl/test_orders_status_schema.py` is the worked example).

**Premises (S50-measured; re-verify if stale):** Alternative A is refuted — `work_dispatch`
hardcodes `work-briefed` (`work.py:987–1008`), so no formula sling can substitute for these
tools. `github_issues.py` has no write path. `create_issue_bead` maps no priority (issue label
`priority/p1` → P2 bead) — Task 2 fixes that as part of `create_defect_bead`'s shared mapper.

---

### Task 1: GitHub write layer + `create_github_issue`

**Files:**
- Modify: `assets/scripts/mctl_core/github_issues.py` (add write functions below the read ones)
- Modify: `assets/scripts/mctl_core/mcp_server.py` (register tool — all six rosters, see #199)
- Modify: `assets/mctl/diagnostics.toml` (new `MGHW_*` entries)
- Test: `tests/mctl/test_create_github_issue.py`

- [ ] **Step 1: Write the failing tests** — three behaviors: (a) dry_run returns an EffectPlan
  containing the fully rendered issue body and NO `gh` subprocess ran (assert via a recording
  fake); (b) live run invokes `gh issue create --repo <repo> --title <t> --body-file -` once and
  returns the issue URL; (c) a body that omits a REQUIRED section of the target repo's live
  template is refused with `MGHW_TEMPLATE_SECTION_MISSING` (FATAL) before any subprocess runs.

```python
def test_dry_run_plans_without_posting(gh_recorder, ctx):
    out = plan_create_github_issue(ctx, repo="tdupu/mathcity",
        title="bug: x", body=VALID_BODY, dry_run=True)
    assert out["applied"] is False
    assert gh_recorder.calls == []
    assert "bug: x" in out["effect_plan"]["github_writes"][0]["title"]

def test_missing_required_template_section_refused(gh_recorder, ctx):
    with template_fixture(required=["Summary", "Root cause"]):
        out = plan_create_github_issue(ctx, repo="tdupu/mathcity",
            title="bug: x", body="### Summary\nonly this", dry_run=False)
    assert out["diagnostics"][0]["code"] == "MGHW_TEMPLATE_SECTION_MISSING"
    assert gh_recorder.calls == []
```

- [ ] **Step 2: Run tests, verify they fail** — `pytest tests/mctl/test_create_github_issue.py -v`
  → FAIL (`plan_create_github_issue` not defined).
- [ ] **Step 3: Implement** — `create_issue(repo, title, body, labels)` in `github_issues.py`
  (subprocess `gh issue create`, timeout 30s, error → `MGHW_GH_UNAVAILABLE` diagnostic object via
  the `diagnostics.py` constructors — never a bare string, that was #203); template check reads
  the live template with the same fetch pattern as `fetch_issue`; handler + ToolSpec in
  `mcp_server.py` with output schema declaring the standard envelope.
- [ ] **Step 4: Run the tests green**, then the #203-pattern schema test: validate the SERVED
  response (dispatcher envelope reproduced) against the declared output schema on BOTH the
  success and the gh-unavailable paths.
- [ ] **Step 5: Update all six rosters** (#199 names them; grep `orders_status` across the repo
  for the roster list and mirror it) and run the roster-consistency test.
- [ ] **Step 6: Commit** — `feat(mctl): create_github_issue — typed defect→issue intake (#185)`.

### Task 2: `create_defect_bead` + shared priority mapper

**Files:**
- Create: `assets/scripts/mctl_core/defect_beads.py`
- Modify: `assets/scripts/mctl_core/beads.py` or the module `create_issue_bead` lives in —
  extract `priority_from_labels()` so BOTH tools share it (fixes the documented p1→P2 defect)
- Test: `tests/mctl/test_create_defect_bead.py`

- [ ] **Step 1: Failing tests** — (a) mints an OPEN task bead with `metadata.defect_report=true`
  and NO `gh.issue` key (this is the "not conversely" case: issues are always paired with beads,
  beads need not have issues); (b) `priority_from_labels(["priority/p1"]) == 1` and
  `create_issue_bead` now mints P1 from a `priority/p1` issue (regression pins the S49/S50
  ledger defect); (c) refuses to mint when an identical-title open defect bead exists
  (`MGHW_DUPLICATE_DEFECT`, per §4's "should refuse to mint orphans at scale").
- [ ] **Step 2: Verify RED.**
- [ ] **Step 3: Implement minimal** — reuse the `_apply_bd_create` path, one error boundary per
  create (do not reproduce #192's create-then-link split).
- [ ] **Step 4: Green + served-schema test + rosters ×6.**
- [ ] **Step 5: Commit** — `feat(mctl): create_defect_bead + label→priority mapping (#185)`.

### Task 3: `standardize_github_issue` — additive, never consolidating

**Files:**
- Create: `assets/scripts/mctl_core/issue_standardize.py`
- Test: `tests/mctl/test_standardize_github_issue.py`

**Design constraint (#52, hard):** the tool APPENDS a `## Standardized restatement` section
carrying the template-shaped restatement and leaves every existing byte of the body in place.
On an agent-maintained tracker the history of an issue is evidence; `update-issue`'s
consolidation semantics are the anti-pattern.

- [ ] **Step 1: Failing tests** — (a) output body == original body + appended section (assert
  prefix-preservation byte-for-byte); (b) idempotent: a second run detects the marker and
  no-ops with `applied:false` + advisory; (c) dry_run posts nothing.
- [ ] **Step 2: RED → Step 3: implement (`gh issue edit --body-file -` with the composed body)
  → Step 4: green + schema + rosters → Step 5: commit.**
- [ ] **Step 6 (measurement, not code):** run dry_run against 5 of the ~102 template-headingless
  issues and attach the rendered plans to the PR as evidence the majority case works.

### Acceptance (whole plan)

- A fresh MCP session can: find a defect → `create_defect_bead` (no issue yet) →
  `create_github_issue` → `create_issue_bead` pairing — loop step 1 no longer requires a human.
- Full `pytest tests/mctl` green; every new tool passes the served-response schema test.
- SURFACE-STATUS §1 row 1 flips to WORKS with the probe transcript, §4 rows A1–A3 promoted
  into §2 and deleted from §4 (the §4 house rule).
