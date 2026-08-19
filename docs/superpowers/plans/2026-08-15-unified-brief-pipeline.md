# Unified Brief Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route artifact, decision, lost-bead-filter, and producer-repair briefs through one `.beads/briefs/.pile -> brief-shuffle -> .beads/briefs/stack -> present-briefs` lifecycle with typed gate profiles, shared no-brainer evidence, and shared feedback events.

**Architecture:** Keep one user-facing stack and one presentation doorway. Preserve specialized source behavior with `brief_kind` and `gate_profile` metadata, plus profile-specific checks in `assets/scripts/checks/brief-check.sh` and executable wiring in `assets/brief-pipeline/gates.toml`. Migrate decisions-track with a copy-first inventory and dry-run tool so legacy records are counted, mapped, and never deleted in the first change.

**Tech Stack:** Shell fixtures, Python 3.11+ for JSONL/frontmatter inventory tooling, TOML formula/config docs, markdown skill and policy docs.

## Global Constraints

- Work in `<repos-root>/mathcity`, not `<city-root>/mathcity`.
- Branch name for this implementation is `unified-brief-pipeline-gate-profiles`.
- Do not commit or push from this outside-agent session unless Taylor explicitly authorizes it.
- Do not delete or move existing `.beads/decisions-track` files in this implementation.
- Policy edits to `subdomains/brief-system/POLICY.md` and `subdomains/dev/POLICY-city.md` require explicit approval of exact rule text through `new-brief-policy` and `new-city-policy` before editing those files.
- Canonical brief state remains the bead store; markdown files and JSONL manifests are cache/rendering state.
- `present-briefs` default queue source is `.beads/briefs/stack`; decisions-track is legacy fallback only.
- Every promoted brief must carry `brief_kind`, `gate_profile`, no-brainer classifier evidence, and `feedback_sink`.
- Shared rejection feedback schema is `brief_quality_failure.v1`; producer-origin rejects still populate the legacy `brief-producer-failure.v1` cache for compatibility.
- Initial migration is copy-first and count-proving: old decisions-track files remain in place and terminal records do not re-enter pile or stack.
- The 2026-08-15 #38 ruling is Option A: fail closed toward visibility. Only confidently terminal legacy statuses are preserved; any other decisions-track manifest row with an existing legacy file is migration-visible.
- Bulk live `.beads` migration remains held until proof 5 reports zero non-terminal preserved rows on the live decisions-track inventory.
- Rig-local `.beads/briefs` residue is a separate follow-up from #38. #38 handles decisions-track invisibility; rig-vs-city scope proof handles cross-rig queue invisibility.

---

## File Structure

- Create `assets/scripts/brief-decisions-track-inventory.py`: read-only inventory and copy-first dry-run planner for legacy decisions-track rows/files.
- Create `tests/decisions-track-migration/smoke_test.sh`: fixture coverage for ready, deferred, adjudicated, missing-file, malformed, and file-without-manifest cases.
- Create `tests/decisions-track-migration/proof5_no_nonterminal_unmapped.py`: canary that fails if any non-terminal decisions-track manifest row with a presentable file is preserved instead of copied to the unified pile/review path.
- Modify `assets/scripts/checks/brief-check.sh`: add profile-specific checks for `decision`, `lost_bead_filter`, `producer_repair`, and shared `brief_quality_failure` cache/event payload validation.
- Modify `assets/brief-pipeline/gates.toml`: add `decision`, `lost_bead_filter`, and `producer_repair` profiles using the existing gate IDs that can apply without fake artifact evidence.
- Create `tests/unified-brief-gate-profiles/smoke_test.sh`: fixture coverage for profile checks and metadata failures.
- Modify `subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`: update decision-only output contract from active decisions-track queue to `.beads/briefs/.pile` plus legacy pointer/mapping records.
- Modify `skills/present-briefs/SKILL.md`: make stack/index the default queue source and convert decisions-track scanning to explicit/migration-absent legacy fallback.
- Create `tests/present-briefs-unified-source/smoke_test.sh`: extract and run the selector snippets, proving stack-first behavior, legacy fallback opt-in, duplicate suppression, and defer preservation.
- Modify `formulas/brief-shuffle.toml`: require rejected briefs to record enough fields for `brief_quality_failure.v1` and keep the existing remediation bead/event behavior.
- Modify `formulas/brief-producer-failure-record.toml`: broaden the formula to record `brief_quality_failure.v1` for all rejected brief kinds while preserving `.producer-failure-pile` for producer-origin rejects.
- Create `tests/brief-quality-failure/smoke_test.sh`: static and fixture checks for the new feedback payload and producer-compatibility path.
- Modify docs after policy approval: `subdomains/brief-system/POLICY.md`, `subdomains/dev/POLICY-city.md`, `subdomains/brief-system/README.md`, `README-clerk.md`, `skills/prime-clerk/SKILL.md`, `docs/testing-guide.md`.

---

### Task 1: Decisions-Track Inventory Tool

**Files:**
- Create: `assets/scripts/brief-decisions-track-inventory.py`
- Create: `tests/decisions-track-migration/smoke_test.sh`

**Interfaces:**
- Consumes: a rig root with `.beads/decisions-track/manifest.jsonl`, legacy `*-brief.md` files, and optional `.beads/briefs/stack/.index.jsonl`.
- Produces: JSONL rows with keys `kind`, `legacy_n`, `legacy_slug`, `legacy_file`, `manifest_status`, `file_status`, `defer_until`, `unlock_count`, `mapped_unified_path`, `migration_action`, and `reason`.

- [ ] **Step 1: Write the failing fixture test**

```sh
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$ROOT/assets/scripts/brief-decisions-track-inventory.py"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/decisions-track-migration.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/.beads/decisions-track" "$TMP/.beads/briefs/stack"

cat >"$TMP/.beads/decisions-track/manifest.jsonl" <<'JSONL'
{"n":1,"slug":"ready-one","status":"ready","unlock_count":4}
{"n":2,"slug":"deferred-one","status":"ready","defer_until":"2999-01-01","unlock_count":3}
{"n":3,"slug":"done-one","status":"adjudicated","unlock_count":2}
{"n":4,"slug":"missing-file","status":"ready","unlock_count":1}
{bad json
JSONL

cat >"$TMP/.beads/decisions-track/01-ready-one-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Ready
MD
cat >"$TMP/.beads/decisions-track/02-deferred-one-brief.md" <<'MD'
---
status: ready-for-adjudication
defer_until: 2999-01-01
---
# Deferred
MD
cat >"$TMP/.beads/decisions-track/03-done-one-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Done
MD
cat >"$TMP/.beads/decisions-track/99-orphan-brief.md" <<'MD'
---
status: ready-for-adjudication
---
# Orphan
MD

python3 "$SCRIPT" inventory --rig-root "$TMP" --output "$TMP/out.jsonl"
python3 - "$TMP/out.jsonl" <<'PY'
import json, sys
rows=[json.loads(line) for line in open(sys.argv[1]) if line.strip()]
actions={(r.get("legacy_n"), r.get("legacy_slug")): r["migration_action"] for r in rows if r["kind"] != "malformed_manifest_row"}
assert actions[(1,"ready-one")] == "copy_to_pile"
assert actions[(2,"deferred-one")] == "copy_to_pile_deferred"
assert actions[(3,"done-one")] == "preserve_terminal"
assert actions[(4,"missing-file")] == "preserve_missing_file"
assert actions[(99,"orphan")] == "preserve_file_without_manifest"
assert any(r["kind"] == "malformed_manifest_row" for r in rows)
print("decisions-track migration inventory: ok")
PY
```

- [ ] **Step 2: Run the test and confirm it fails because the script is missing**

Run: `bash tests/decisions-track-migration/smoke_test.sh`

Expected: FAIL with `brief-decisions-track-inventory.py` missing.

- [ ] **Step 3: Implement the inventory script**

Create `assets/scripts/brief-decisions-track-inventory.py` with:

```python
#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)

def parse_frontmatter(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = path.read_text(errors="replace")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    data = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip().strip('"')
    return data

def slug_from_file(path: Path) -> tuple[int | None, str]:
    stem = path.name.removesuffix("-brief.md")
    match = re.match(r"^0*(\d+)-(.+)$", stem)
    if not match:
        return None, stem
    return int(match.group(1)), match.group(2)

def action_for(status: str, defer_until: str | None, has_file: bool) -> str:
    if not has_file:
        return "preserve_missing_file"
    if status == "ready" and defer_until:
        return "copy_to_pile_deferred"
    if status == "ready":
        return "copy_to_pile"
    if status in {"adjudicated", "rescinded", "auto-dispatched"}:
        return "preserve_terminal"
    return "preserve_unknown_status"

def inventory(rig_root: Path) -> list[dict]:
    ddir = rig_root / ".beads/decisions-track"
    manifest = ddir / "manifest.jsonl"
    rows = []
    seen_files = set()
    if manifest.exists():
        for line_no, line in enumerate(manifest.read_text(errors="replace").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                rows.append({"kind":"malformed_manifest_row","line":line_no,"migration_action":"preserve_malformed_manifest","reason":str(exc)})
                continue
            n = row.get("n")
            slug = row.get("slug")
            candidates = sorted(ddir.glob(f"{int(n):02d}-*-brief.md")) + sorted(ddir.glob(f"{int(n)}-*-brief.md")) if isinstance(n, int) else []
            legacy_file = candidates[0] if candidates else ddir / f"{n}-{slug}-brief.md"
            if legacy_file.exists():
                seen_files.add(legacy_file.resolve())
            fm = parse_frontmatter(legacy_file)
            defer_until = row.get("defer_until") or fm.get("defer_until")
            action = action_for(str(row.get("status","")), defer_until, legacy_file.exists())
            rows.append({
                "kind":"manifest_row",
                "legacy_n":n,
                "legacy_slug":slug,
                "legacy_file":str(legacy_file),
                "manifest_status":row.get("status"),
                "file_status":fm.get("status"),
                "defer_until":defer_until,
                "unlock_count":row.get("unlock_count",0),
                "mapped_unified_path":None,
                "migration_action":action,
                "reason":"manifest_status_and_file_presence",
            })
    for path in sorted(ddir.glob("*-brief.md")):
        if path.resolve() in seen_files:
            continue
        n, slug = slug_from_file(path)
        fm = parse_frontmatter(path)
        rows.append({
            "kind":"file_without_manifest",
            "legacy_n":n,
            "legacy_slug":slug,
            "legacy_file":str(path),
            "manifest_status":None,
            "file_status":fm.get("status"),
            "defer_until":fm.get("defer_until"),
            "unlock_count":0,
            "mapped_unified_path":None,
            "migration_action":"preserve_file_without_manifest",
            "reason":"no_manifest_row",
        })
    return rows

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory")
    inv.add_argument("--rig-root", required=True)
    inv.add_argument("--output", required=True)
    args = parser.parse_args()
    rows = inventory(Path(args.rig_root))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(row, sort_keys=True, separators=(",",":")) + "\n" for row in rows))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `bash tests/decisions-track-migration/smoke_test.sh`

Expected: PASS with `decisions-track migration inventory: ok`.

### Task 2: Typed Gate Profiles And Profile Checks

**Files:**
- Modify: `assets/brief-pipeline/gates.toml`
- Modify: `assets/scripts/checks/brief-check.sh`
- Create: `tests/unified-brief-gate-profiles/smoke_test.sh`

**Interfaces:**
- Consumes: markdown briefs via `GC_BRIEF_PATH`.
- Produces: new `brief-check.sh` subcommands `decision-profile`, `lost-bead-filter-profile`, `producer-repair-profile`, and `brief-quality-failure-record`.

- [ ] **Step 1: Write profile fixture test**

Create `tests/unified-brief-gate-profiles/smoke_test.sh` with fixture cases that assert:

```sh
GC_BRIEF_PATH="$valid_decision" sh assets/scripts/checks/brief-check.sh decision-profile
GC_BRIEF_PATH="$missing_g9" sh assets/scripts/checks/brief-check.sh decision-profile
GC_BRIEF_PATH="$valid_lost" sh assets/scripts/checks/brief-check.sh lost-bead-filter-profile
GC_BRIEF_PATH="$missing_provenance" sh assets/scripts/checks/brief-check.sh lost-bead-filter-profile
GC_BRIEF_PATH="$valid_repair" sh assets/scripts/checks/brief-check.sh producer-repair-profile
```

The valid decision fixture must include:

```yaml
brief_kind: decision
gate_profile: decision
legacy_source: decisions-track/01-ready-one-brief.md
feedback_sink: brief_quality_failure
```

and one line:

```text
G9 No-brainer-filter: PASS classifier_state=known_non_no_brainer reason=decision-profile-fixture classified_at=2026-08-15T00:00:00Z
```

- [ ] **Step 2: Run the test and confirm it fails because the subcommands are missing**

Run: `bash tests/unified-brief-gate-profiles/smoke_test.sh`

Expected: FAIL with `unknown check: decision-profile`.

- [ ] **Step 3: Add profile wiring to gates.toml**

Add:

```toml
[profiles.decision]
gates = ["G5", "G5b", "G8", "G9", "G11", "G12", "G13"]

[profiles.lost_bead_filter]
gates = ["G5", "G5b", "G8", "G9", "G11", "G12", "G13"]

[profiles.producer_repair]
gates = ["G5", "G5b", "G8", "G9", "G11", "G12", "G13"]
```

- [ ] **Step 4: Add profile subcommands to brief-check.sh**

Add helper `require_frontmatter_key_value` and subcommands that require:

```text
decision-profile:
  brief_kind=decision
  gate_profile=decision
  feedback_sink=brief_quality_failure
  source_bead or legacy_source
  action_block
  G9 classifier evidence

lost-bead-filter-profile:
  brief_kind=lost_bead_filter
  gate_profile=lost_bead_filter
  feedback_sink=brief_quality_failure
  source_bead
  fingerprint
  threshold_count
  distinct_bead_count
  replay_command
  false_positive_risk
  G9 classifier evidence

producer-repair-profile:
  brief_kind=producer_repair
  gate_profile=producer_repair
  feedback_sink=brief_quality_failure
  producer_contract=brief-producer-repair.v1
  repair_source_formula
  repair_failed_gate
  repair_failure_fingerprint
  replay_command
  G9 classifier evidence
```

- [ ] **Step 5: Run profile tests**

Run: `bash tests/unified-brief-gate-profiles/smoke_test.sh`

Expected: PASS.

### Task 3: Stack-First Presentation And Decision Intake Docs

**Files:**
- Modify: `skills/present-briefs/SKILL.md`
- Modify: `subdomains/brief-system/skills/decisions-to-briefs/SKILL.md`
- Create: `tests/present-briefs-unified-source/smoke_test.sh`
- Update: `tests/present-briefs-defer-filter/test_defer_filter.sh`

**Interfaces:**
- Consumes: stack `.index.jsonl` and optional decisions-track manifest.
- Produces: embedded selector snippets that prefer stack, suppress legacy duplicates by `legacy_source`, and only scan decisions-track with `--include-legacy-decisions` or absent migration marker.

- [ ] **Step 1: Write selector fixture test**

Create a shell test that extracts the stack selector and legacy selector snippets from `skills/present-briefs/SKILL.md`. The fixture must assert:

```text
stack entry with defer_until future is skipped
stack entry with no defer is printed
legacy decisions-track entry is skipped when a migration marker exists and fallback flag is absent
legacy decisions-track entry is printed when fallback flag is present
legacy decisions-track entry is skipped when stack index has legacy_source pointing at it
```

- [ ] **Step 2: Run the new and existing defer selector tests**

Run:

```bash
bash tests/present-briefs-unified-source/smoke_test.sh
bash tests/present-briefs-defer-filter/test_defer_filter.sh
```

Expected: the new test fails before the skill docs contain the stack selector; the existing defer test still passes.

- [ ] **Step 3: Update present-briefs queue discovery**

Replace the current "union of two brief sources" language with:

```text
The default ripe queue is the unified brief stack at <rig-root>/.beads/briefs/stack.
The decisions-track scan is legacy fallback only. Run it only when
--include-legacy-decisions is passed or when no migration marker exists.
If a decisions-track item appears in stack/.index.jsonl as legacy_source, suppress
the legacy copy.
```

Add a stack selector heredoc that reads `stack/.index.jsonl`, filters future `defer_until`, prints `unlock_count path`, and preserves malformed defer as fail-open for existing behavior.

- [ ] **Step 4: Update decisions-to-briefs deposit contract**

Change decision-only Procedure step 6 and pile conventions so new policy-disposition briefs deposit into `.beads/briefs/.pile`, not the active decisions-track queue, with minimum frontmatter:

```yaml
brief_kind: decision
gate_profile: decision
feedback_sink: brief_quality_failure
classifier_state: known_non_no_brainer
legacy_source: null
status: ready-for-adjudication
```

Keep decisions-track pointer records only as legacy compatibility/migration mapping.

- [ ] **Step 5: Run selector tests again**

Run:

```bash
bash tests/present-briefs-unified-source/smoke_test.sh
bash tests/present-briefs-defer-filter/test_defer_filter.sh
```

Expected: PASS.

### Task 4: Shared Brief-Quality Failure Feedback

**Files:**
- Modify: `formulas/brief-shuffle.toml`
- Modify: `formulas/brief-producer-failure-record.toml`
- Modify: `assets/scripts/checks/brief-check.sh`
- Create: `tests/brief-quality-failure/smoke_test.sh`

**Interfaces:**
- Consumes: rejected brief under `.beads/briefs/.pile/.rejected/<slug>/brief.md`.
- Produces: cache/event schema `brief_quality_failure.v1` for all rejects; legacy producer cache remains for producer-origin rejects.

- [ ] **Step 1: Write the feedback fixture test**

Create a shell test that checks:

```text
brief-shuffle.toml names brief_quality_failure.v1 on reject
brief-producer-failure-record.toml writes .brief-quality-failure-pile
brief-producer-failure-record.toml still writes .producer-failure-pile for producer-origin compatibility
brief-check.sh accepts a TOML fixture with schema = "brief_quality_failure.v1"
```

- [ ] **Step 2: Run the test and confirm it fails before implementation**

Run: `bash tests/brief-quality-failure/smoke_test.sh`

Expected: FAIL because the schema/path/subcommand is absent.

- [ ] **Step 3: Update formula wording**

In `brief-shuffle.toml`, extend reject behavior to say every rejected/blocked item must write enough rejection metadata for `brief_quality_failure.v1`: `brief_kind`, `gate_profile`, `source_bead`, `source_surface`, `failed_gate`, `failure_summary`, `failure_fingerprint`.

In `brief-producer-failure-record.toml`, broaden scan/record language from "producer failures" to "brief quality failures", write `{{artifact_root}}/.brief-quality-failure-pile/<slug>.toml`, create linked event bead with `--event-category brief.quality_failure`, and only also populate `.producer-failure-pile` when the rejected brief has `producer_contract: brief-producer.v1` or explicit producer-origin metadata.

- [ ] **Step 4: Add `brief-quality-failure-record` check**

Require these TOML fields:

```toml
schema = "brief_quality_failure.v1"
brief_id = "..."
brief_kind = "..."
gate_profile = "..."
source_surface = "..."
failed_gate = "..."
failure_summary = "..."
failure_fingerprint = "..."
status = "untriaged"
```

- [ ] **Step 5: Run feedback tests**

Run: `bash tests/brief-quality-failure/smoke_test.sh`

Expected: PASS.

### Task 5: Documentation Updates And Policy Approval Gate

**Files:**
- Modify after approval: `subdomains/brief-system/POLICY.md`
- Modify after approval: `subdomains/dev/POLICY-city.md`
- Modify: `subdomains/brief-system/README.md`
- Modify: `README-clerk.md`
- Modify: `skills/prime-clerk/SKILL.md`
- Modify: `docs/testing-guide.md`

**Interfaces:**
- Consumes: approved exact policy amendments.
- Produces: docs matching the unified pipeline, migration, BART deployment, and hygienic issue behavior.

- [ ] **Step 1: Present exact brief-system policy amendment for approval**

Propose a new B2 rule:

```markdown
**B2.<next> Unified presentation pipeline.** Every adjudicable brief source must enter the shared `.beads/briefs/.pile -> brief-shuffle -> stack -> present-briefs` lifecycle before it reaches the human adjudicator. Source-specific behavior is expressed by `brief_kind` and `gate_profile`; it must not create an active side presentation lane. Legacy decisions-track records may be read only as migration fallback and must be duplicate-suppressed when a unified-pile mapping exists.
```

Propose a new N rule:

```markdown
**N<next> Classifier evidence for every profile.** Every promoted brief, including decision-only, lost-bead-filter, and producer-repair briefs, must record exactly one no-brainer classifier state before stack promotion. Human-identified obvious briefs that reached presentation must record a durable `no_brainer_leak` linked to the classifier evidence.
```

Do not edit `POLICY.md` until Taylor approves the exact text.

- [ ] **Step 2: Present exact city-policy amendment for approval**

Propose a CT rule:

```markdown
**CT<next> Hygienic issues for lifecycle blockers.** When a live workflow is blocked by substrate, lifecycle, deployment, or policy/runtime mismatch rather than by the artifact under review, the operator must file or link a durable hygienic issue before treating the brief as resolved. The issue must name the failed command or lifecycle point, the affected rig or source path, and the recovery owner.
```

Do not edit `POLICY-city.md` until Taylor approves the exact text.

- [ ] **Step 3: Update non-policy docs**

Update the README/testing/clerk docs to say:

```text
present-briefs drains one stack.
decisions-track is legacy intake/migration fallback, not an active lane.
Every source has filter + no-brainer evidence + feedback sink.
BART must verify live-resolved source path before migration.
```

- [ ] **Step 4: After approval, apply policy edits through the policy skills**

Use `new-brief-policy` and `new-city-policy` requirements:

```text
append rule text in numeric order
update change log
run check-brief-policy and check-city-policy
do not commit or push without explicit authorization
```

### Task 6: Validation And Handoff

**Files:**
- No new source files unless a test exposes a missed fixture or doc reference.

**Interfaces:**
- Produces: final status with changed files, tests run, tests not run, and BART deployment notes.

- [ ] **Step 1: Run source-local smoke tests**

Run:

```bash
bash tests/decisions-track-migration/smoke_test.sh
python3 assets/scripts/brief-decisions-track-inventory.py inventory --rig-root <city-root> --output /private/tmp/codex-proof5-live-inventory.jsonl
python3 tests/decisions-track-migration/proof5_no_nonterminal_unmapped.py /private/tmp/codex-proof5-live-inventory.jsonl
bash tests/unified-brief-gate-profiles/smoke_test.sh
bash tests/present-briefs-unified-source/smoke_test.sh
bash tests/present-briefs-defer-filter/test_defer_filter.sh
bash tests/brief-quality-failure/smoke_test.sh
bash tests/lost-bead-filter/smoke_test.sh
bash skills/catch-no-brainer/fixtures/run.sh
bash tests/brief-no-brainer-gate/test_brief_check_no_brainer.sh
bash tests/lockless-brief-shuffle/smoke_test.sh
bash tests/producer-failure-rollup-routing/smoke_test.sh
python3 -m pytest tests/stuck-bead-watch tests/tail-end-detector
```

- [ ] **Step 2: Run policy checks if policy files changed**

Run `check-brief-policy` and `check-city-policy` procedures from their skills after approved policy edits.

- [ ] **Step 3: Report branch state and BART sequence**

Report:

```text
branch: unified-brief-pipeline-gate-profiles
source path: <repos-root>/mathcity
do not run live migration until BART verifies live-resolved present-briefs, decisions-to-briefs, gates.toml, and check-brief-policy match this branch/merge commit
do not run live migration unless proof 5 is green on the live decisions-track inventory
track rig-local .beads/briefs residue separately; do not declare the pipeline fully unified across registered rigs until that follow-up has its own inventory/migration/proof
pull-only is sufficient only if live gc resolves pack files directly from <repos-root>/mathcity; otherwise BART must run the existing pack import/build/install step
```

---

## Self-Review Notes

- Spec coverage: migration inventory, typed profiles, decision intake, stack-first presentation, feedback, docs, BART deployment, rollback-safe migration, and tests are represented.
- Follow-up scope coverage: rig-local `.beads/briefs` residue is intentionally tracked outside #38 so the decisions-track classifier/proof patch stays narrow.
- Placeholder scan target: no task uses deferred-work marker language.
- Type consistency: `brief_kind`, `gate_profile`, `feedback_sink`, `legacy_source`, `defer_until`, `unlock_count`, and `brief_quality_failure.v1` match the design spec.
