# Brief-System Defect Queue — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the defect queue that the 2026-08-19/20 rewrite exposed, so that every brief in the city is reachable, adjudicable, and correctly shaped — and so that adjudicating one leaves all four of its representations agreeing.

**Architecture:** `mctl` is a stdlib-only Python core with two adapters (a CLI shim and an 18-tool MCP server) over a Dolt-backed bead store plus three document sources on disk. Fixes are read-side wherever possible; writes go through the existing `EffectPlan` phased-trace pattern.

**Tech Stack:** Python 3 stdlib only · bash checks under `assets/scripts/checks/` · TOML formulas and orders · `bd` (Dolt) · `gc` (gascity control plane)

**Spec:** this document is the spec; each task cites the issue or bead that owns it.

## Global Constraints

- **Stdlib only.** No new dependencies, ever.
- **MCP tool count is 18 core / 16 dashboard**, dashboard a proper subset. A test asserts both. Moving either number is a deliberate act with justification, never a fix to make a test pass.
- **Absent means absent.** Never synthesize a field, a timestamp, or a count.
- **Anchor every string match.** Two shipped defects came from unanchored matching (`.replace('-brief','')`, a body substring). Suffix strips are `re.sub(r'-brief$', ...)`, never `.replace`.
- **Resolve pack assets via `pack_asset`**, never a cwd-relative literal. The ralph runner's cwd is an agent work dir.
- **Query the right store.** `bd` resolves against the store bound by the cwd. `mc-*` beads live in `~/gt/mathcity`, not `~/repos/mathcity` and not HQ.
- **Do not weaken a test to make new code pass.** If an assertion is wrong, say so explicitly and explain why.
- **Repair is not rejection.** Automated shape repair is permitted; automated *verdicts* are not. Every repair records that it happened and what arrived, so producer signal survives.

---

## Task 1: The city-root pile has no drain (B1)

**Owns:** clerk sweep B1. Five briefs (n=19–23) stuck in `~/gt/.beads/briefs/.pile/` since 2026-08-15.

**Files:**
- Modify: `orders/brief-shuffle-fast-drain.toml`
- Modify: `formulas/brief-shuffle-fast-drain.toml:38` (cwd-relative step command)
- Test: `tests/brief-pile-drain/smoke_test.sh` (create)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: a drain path that fires on the city root. Task 3 depends on the pile actually draining to observe an end-to-end adjudication.

**Measured facts to build against (re-verify before changing anything):**
```
brief-shuffle-pile          retired 2026-08-16, Check: false, can never fire
brief-shuffle-fast-drain    scope = "rig"
brief-*:rig:gt events       ZERO, ever, for any brief order
rigs with a .pile dir       3 of 13 (hecke 2, lmfdb 1, gascity-packs 4)
city-root pile              5 briefs, oldest 2026-08-15 22:07
```

- [ ] **Step 1: Reproduce — prove the order cannot fire on the city root**

```bash
grep -c 'brief-[a-z-]*:rig:gt\b' ~/gt/.gc/events.jsonl   # expect 0
grep -n 'scope' orders/brief-shuffle-fast-drain.toml     # expect scope = "rig"
ls ~/gt/.beads/briefs/.pile/*.md | wc -l                 # expect 5
```
Expected: zero city-root firings, `scope = "rig"`, five stuck briefs.

- [ ] **Step 2: Write the failing test**

```bash
# tests/brief-pile-drain/smoke_test.sh
# A pile at the CITY ROOT must be reachable by some order.
# Fails today because every brief order is rig-scoped.
city_scoped="$(grep -l 'scope *= *"city"' "$RIG_ROOT"/orders/brief-*.toml 2>/dev/null | wc -l)"
if [ "$city_scoped" -ge 1 ]; then
  ok "at least one brief order is city-scoped and can drain the city-root pile"
else
  no "every brief order is rig-scoped; the city-root pile has no drain path"
fi
```

- [ ] **Step 3: Run it and watch it fail**

Run: `bash tests/brief-pile-drain/smoke_test.sh`
Expected: FAIL, "every brief order is rig-scoped".

- [ ] **Step 4: Decide the fix — this is a judgment call, not a mechanical edit**

Two candidates. **Do not pick by taste; measure which is true.**

- **(a) Add a city-scoped drain order.** Correct if the city root is a legitimate pile location that rigs do not own.
- **(b) Stop depositing into the city-root pile.** Correct if the city root is itself the drift, and briefs should land in a rig's pile.

Evidence to gather first: what wrote those five briefs, and where do current producers deposit? Check `deposited_by` in each of the five, and `assets/brief-pipeline/paths.toml` for the canonical pile root. **Report the evidence and the choice before implementing.**

- [ ] **Step 5: Fix the cwd-relative step command (same root cause as #73)**

`formulas/brief-shuffle-fast-drain.toml:38` runs `python3 assets/scripts/brief-shuffle-fast-drain.py` with a cwd that is never the pack root. Resolve it the way `brief-check.sh` now does — anchored on the pack, not the cwd.

- [ ] **Step 6: Run the test, confirm it passes, and confirm the pile actually drains**

Live check: after the fix, the five briefs must move. `ls ~/gt/.beads/briefs/.pile/*.md` should shrink. If it does not, the order still is not firing — say so rather than declaring the config fix sufficient.

- [ ] **Step 7: Commit**

```bash
git add orders/ formulas/ tests/brief-pile-drain/
git commit -m "briefs: the city-root pile gets a drain path"
```

---

## Task 2: `.index.jsonl` has no rebuild path (B2)

**Owns:** clerk sweep B2. 89 files on disk, 88 index rows, one orphan.

**Files:**
- Modify: `assets/scripts/brief-stack-index.py` (add a subcommand)
- Test: `tests/mctl/test_stack_index_rebuild.py` (create)

**Interfaces:**
- Consumes: nothing.
- Produces: `brief-stack-index.py add-missing-rows` — later tasks may call it.

**Measured facts:**
```
stack/*.md                89
stack/.index.jsonl        88 rows
orphan                    gh-38-decisions-track-classifier-verify-close-brief.md
path serializations       45 '.beads/…'  ·  40 absolute  ·  3 bare 'stack/…'
subcommands today         reconcile-archive, remove-archived-row  (both REMOVE only)
```

- [ ] **Step 1: Write the failing test**

```python
def test_a_stack_file_with_no_index_row_can_be_repaired(tmp_path):
    stack = tmp_path / "stack"; stack.mkdir()
    (stack / "01-orphan-brief.md").write_text("---\nstatus: present-it-pending\n---\nbody\n")
    (stack / ".index.jsonl").write_text("")
    rc = run_index_tool("add-missing-rows", "--brief-root", str(tmp_path), "--apply")
    assert rc == 0
    rows = [json.loads(l) for l in (stack / ".index.jsonl").read_text().splitlines() if l.strip()]
    assert len(rows) == 1
    assert Path(rows[0]["path"]).name == "01-orphan-brief.md"
```

- [ ] **Step 2: Run it, confirm it fails** — the subcommand does not exist.

- [ ] **Step 3: Implement `add-missing-rows`**

Glob `stack/*.md`, diff against index rows by filename, append a row per missing file. **Write one serialization only** — pick the `.beads/…` relative form (45 of 88 rows, the plurality) and document why in the code. Dry-run by default; `--apply` to write.

- [ ] **Step 4: Add the serialization-consistency test**

```python
def test_added_rows_use_one_serialization():
    # brief 22 (index-jsonl-two-serialization-producers) is now three producers.
    # Whatever we add must not become the fourth.
```

- [ ] **Step 5: Run against the live index in dry-run and report**

```bash
python3 assets/scripts/brief-stack-index.py add-missing-rows --brief-root ~/gt/.beads/briefs
```
Expected: exactly one row proposed, for `gh-38-…`. **If it proposes more, stop and report** — that means the orphan count is not 1 and the earlier measurement was wrong.

- [ ] **Step 6: Commit**

---

## Task 3: Adjudication does not write the brief file's frontmatter (B3)

**Owns:** clerk sweep B3. `gh-38` is simultaneously decided (GitHub), `present-it-pending` (frontmatter), and absent (index).

**Files:**
- Modify: `assets/scripts/mctl_core/effects.py` (the adjudication effect)
- Test: `tests/mctl/test_adjudication_writes_frontmatter.py` (create)

**Interfaces:**
- Consumes: Task 2's index repair, for the case where the brief has no index row.
- Produces: an adjudication that leaves bead, `decisions/<id>.toml`, `.index.jsonl`, and the brief's own frontmatter all agreeing.

**The structural fact:** `mctl` owns the bead, `decisions/<id>.toml`, and `.index.jsonl`. `adjudicate-brief` step 2b's two-record scope is a declared legacy exemption. **The brief file's frontmatter `status:` is owned by nobody.** This is the write-side corollary of POLICY B2.8a — the bead is a serial number, the state lives in the file, and every write path targets the serial number.

- [ ] **Step 1: Write the failing test**

```python
def test_adjudication_writes_the_briefs_own_frontmatter(brief_fixture):
    adjudicate(brief_fixture.id, verdict="approve", reason="ok", apply=True)
    fm = read_frontmatter(brief_fixture.path)
    assert fm["status"].startswith("adjudicated")
    assert fm["verdict"] == "approve"
```

- [ ] **Step 2: Run it, confirm it fails** — nothing writes frontmatter today.

- [ ] **Step 3: Extend the EffectPlan with a frontmatter write**

Follow the existing idiom in `effects.py` — per-step `try/except` with `append_aborted`, `append_applied` at the end. **Do not** invent a `finally` pattern that the neighbouring writes do not use.

The write must be **idempotent** and must not clobber unknown keys: read the frontmatter, set `status` and `verdict`, preserve everything else byte-for-byte including key order.

- [ ] **Step 4: Test the four-way agreement**

```python
def test_all_four_representations_agree_after_adjudication(brief_fixture):
    adjudicate(brief_fixture.id, verdict="approve", reason="ok", apply=True)
    assert bead_status(brief_fixture.id) == "closed"
    assert decision_toml_exists(brief_fixture.id)
    assert index_row_status(brief_fixture.id).startswith("adjudicated")
    assert read_frontmatter(brief_fixture.path)["status"].startswith("adjudicated")
```

- [ ] **Step 5: Repair `gh-38` specifically, as the acceptance case**

It is the live instance. After the fix, adjudicating it must bring all four into agreement. **Do not hand-patch the file before the fix exists** — that would hide whether the fix works.

- [ ] **Step 6: Commit**

---

## Task 4: Queue size depends on the caller's working directory (B4)

**Owns:** clerk sweep B4. 34 entries from `~/gt`, 63 from elsewhere — same selector, same data.

**Files:**
- Modify: `skills/present-briefs/SKILL.md` (path resolution)
- Test: `tests/mctl/test_index_path_resolution.py` (create)

**NOT YET INDEPENDENTLY VERIFIED.** Every other clerk figure verified exactly, but this one I did not reproduce. **Reproduce it first.** If it does not reproduce, say so and close the task as not-a-defect rather than fixing a phantom.

- [ ] **Step 1: Reproduce, from two directories**

```bash
cd ~/gt        && <selector> | wc -l    # clerk measured 34
cd /tmp        && <selector> | wc -l    # clerk measured 63
```

- [ ] **Step 2: If it reproduces — write the failing test**

Resolve index paths against the **brief root**, not `Path.cwd()`. The three bare `stack/…` rows are the ones that break.

- [ ] **Step 3: Fix `frontmatter_status()` failing open**

It returns "not terminal" on `OSError`, so an unreadable file counts as pending. That is fail-open on a filter whose job is to *hide* resolved briefs — it re-presents adjudicated work. Make it fail closed, or surface the error; do not leave it silent.

- [ ] **Step 4: Commit**

---

## Task 5: `$PACK_DIR` and cwd-relative paths in formula descriptions (#73 / mc-quq)

**Owns:** GitHub #73, bead `mc-quq`, workflow `mc-wpi`.

**Files:**
- Modify: `formulas/brief-record-decision.toml:209`
- Modify: `formulas/brief-shuffle-fast-drain.toml:36`
- Test: extend `tests/brief-no-brainer-arming/test_no_brainer_arming.sh` (test 36 already asserts no cwd-relative literals in `brief-check.sh`; generalise to formulas)

**This is the fifth instance of one root cause.** A path that assumes a working directory the runtime never provides. Sally found two in `brief-check.sh` (fixed, `310b15a`); these two are in `description = """` blocks, which are **agent-executed instructions, not prose**.

```
brief-record-decision.toml:209   python3 "$PACK_DIR/assets/scripts/brief-stack-index.py" …
```
`PACK_DIR`/`GC_PACK_DIR` are injected only for order dispatch and `gc` custom commands — never for a formula-step agent. gascity's own test asserts the variable is absent. So it expands to `python3 "/assets/…"` and fails.

**Bug 1 changes pipeline behaviour, so it needs adjudication, not just a fix.** That step removes a decided brief from `stack/.index.jsonl`; its own prose says "an archived brief must not remain in the authoritative presentation queue". If it has never succeeded, decided briefs may be lingering. **Measure `.index.jsonl` for archived-but-listed rows before choosing a fix.**

- [ ] **Step 1: Measure the consequence first**

```bash
# how many index rows point at briefs that are archived?
python3 - <<'PY'
# compare stack/.index.jsonl rows against .adjudicated-archive/
PY
```
Report the count. Zero means the defect is latent; nonzero means it has been silently corrupting the queue.

- [ ] **Step 2: Write the failing test** — no formula step may reference `$PACK_DIR` or a cwd-relative `assets/` path.

- [ ] **Step 3: Fix both call sites** the way `brief-check.sh` does.

- [ ] **Step 4: Run, commit, and close #73** with the measurement from step 1.

---

## Task 6: Dead `escalate.sh` references (#69 / mc-3yh)

**Owns:** GitHub #69, bead `mc-3yh`, workflow `mc-tsz`. Nine references to a script nothing installs.

**Blocked on a decision:** which of the two divergent copies to target. **Resolve that before writing code** — measure both copies, report the difference, and pick with evidence.

- [ ] **Step 1: Locate both copies and diff them.**
- [ ] **Step 2: Determine which (if either) is reachable at runtime**, the same way the `.gc/scripts/checks` question was settled: check the symlink farm, `city.toml`, and any installed snapshot.
- [ ] **Step 3: Report the evidence and the recommendation. Do not delete anything yet.**
- [ ] **Step 4: Once decided — fix the nine references, test, commit, close #69.**

---

## Task 7: Detection surface for dead agent-facing paths (#71 / mc-rjd)

**Owns:** GitHub #71, bead `mc-rjd`, workflow `mc-arv`. The prototype found two live bugs (which became #73).

**Blocked on three decisions in the issue comment.** Read them, form a recommendation on each with evidence, and put them to Taylor **as one batch** rather than three separate asks.

The value is already proven: this detector found #73, and #73 turned out to be the fifth instance of the most common root cause in the system. **That argues for building it, and the argument should be in the recommendation.**

- [ ] **Step 1: Read #71's three open decisions and form a recommendation on each.**
- [ ] **Step 2: Present all three to Taylor at once.**
- [ ] **Step 3: Build per the ruling. Test against the known-bad corpus** — it must find the two #73 bugs and the two `brief-check.sh` ones already fixed.

---

## Task 8: B1.3 compact-brief repair (#74 / mc-0ka) — TAYLOR'S DOGFOOD TARGET

**Owns:** GitHub #74, bead `mc-0ka`, workflow `mc-cg0`.

**This one is Taylor's to drive.** He said he will dogfood it. **Do not implement it ahead of him.** Keep the issue current, answer questions, and have the measurements ready:

```
19 compact briefs · 18 with NO no_brainer_classification -> B1.3 violations
1 compliant (gh-38, close-done-cited-commit, 0.95)
39 of 89 briefs carry no `form` key at all — larger than the compact population,
   and NOT yet established as violations. Measure before assuming.
```

**The constraint that shapes it:** repair may be automated; rejection may not. Taylor rejects by hand so the producer signal is captured. Each repair records that it happened and what shape arrived, or the signal is destroyed exactly as an auto-reject would destroy it.

- [ ] **Step 1: Measure the 39 no-`form` briefs and report what they actually are.**
- [ ] **Step 2: Stand by. Support Taylor's run; do not pre-empt it.**

---

## Task 9: B2.1 "no bead subject" (mc-csr / mc-sxz)

**Owns:** bead `mc-csr`, workflow `mc-sxz`. Should B2.1 let a brief declare "no bead subject" instead of failing as MBRF004?

**This is a policy question, not a code task.** 42 briefs are `malformed` and 105 of 158 manifest rows have no `source_bead`. The question is whether "this brief is about no bead" is a legitimate declaration or always an error.

- [ ] **Step 1: Measure the population that would be affected** — how many MBRF004 briefs would a `source: none` declaration legitimise, and how many of those look like genuine no-subject briefs versus genuine omissions? Sample and classify.
- [ ] **Step 2: Write the recommendation with the measurement. Taylor decides.**
- [ ] **Step 3: Implement per the ruling.**

---

## Task 10: `global_fragments` drift

**Owns:** no issue yet — **file one.**

`city.toml:3` declares `global_fragments = ["command-glossary", "operational-awareness"]`. Neither ships in any imported pack; both are gastown vestige in `.gc/cache/repos/`. So every prime in the city silently drops them.

**The silent drop is closer to correct than restoring would be:**
- `command-glossary` points at six `/gc-*` slash commands, **none of which exist**.
- `operational-awareness` says *"Your identity and role are set by `gc prime`… Your role is determined by the `GC_AGENT` environment variable"* — correct for inside agents, **wrong for outside agents**, and it is injected into both. The Mayor is an outside agent. CLAUDE.md says outside agents never run `gc prime`.

- [ ] **Step 1: File the issue with the above evidence.**
- [ ] **Step 2: Recommend removing both names from `global_fragments`**, and if `operational-awareness` is wanted for inside agents, re-scoping it to a per-role fragment.
- [ ] **Step 3: `city.toml` is pack-managed — the fix is a pack update, not a hand-edit.** Route accordingly.

---

## Testing Plan

### Per-task (every task, no exceptions)

1. Failing test first, run it, confirm it fails **for the stated reason** — not for a typo.
2. Minimal fix.
3. Test passes.
4. **Full suite**: `python3 -m pytest -q` (751 baseline) and `bash scripts/run-local-tests.sh` (35 shell tests).
5. Commit.

### Live-city tests — required, not optional

Fixture tests did not catch a single one of tonight's defects. Every one came from measuring the live city. So each task ends with a live check, and **the live check is the acceptance criterion**, not the unit test.

```bash
# 1. Population — the top-line invariant
cd ~/repos/mathcity
bin/mctl briefs list --all-rigs --city ~/gt --json \
  | python3 -c "import sys,json,collections; b=json.load(sys.stdin)['briefs']; \
    print(len(b), dict(collections.Counter(x.get('source') for x in b)))"
# expect 442 = 197 bead + 158 manifest + 87 stack_file

# 2. No document is silently dropped
#    documents on disk minus folded == emitted; 293 - 48 == 245

# 3. Partial degradation still works
MCTL_BD_TIMEOUT_SECONDS=1 bin/mctl briefs list --all-rigs --city ~/gt --json \
  | python3 -c "import sys,json; print(len(json.load(sys.stdin)['briefs']))"
# expect ~290, exit 1 — file-sourced briefs survive a dead bead store

# 4. The specific brief that started this
bin/mctl briefs list --all-rigs --city ~/gt --json | grep -c gh-38   # expect >= 1

# 5. The no-brainer gate is still dormant
find ~/gt -name 'no-brainer-execution.jsonl'    # expect NO matches
# If this ever returns a file, the gate has begun evaluating. Tell Taylor and bob
# immediately — both were told it is dormant.

# 6. Pack assets resolve from a foreign cwd
cd /tmp && bash ~/repos/mathcity/assets/scripts/checks/brief-check.sh no-brainer-mode
# expect a clean ARMED report, no "missing" errors
```

### Regression corpus

Every fixed defect gets a test pinned to the **literal artefact** that exposed it, so the class cannot silently return:

| defect | pinned artefact |
| --- | --- |
| unanchored suffix strip | `257-decision-brief-gate-profile-brief.md` |
| cwd-relative pack asset | `grep -c '="assets/' brief-check.sh` == 0 |
| cross-store edge loss | a real `bd dep add` against two real stores |
| dashboard subset boundary | `dashboard ALLOWED_TOOLS < core TOOLS` |

### What testing cannot cover, and must be said out loud

- A supervisor restart is required to reclaim ~71k pinned descriptors. Until then `gc status` latency is unstable — measured at 92s, 16s, 3.2s and 49s **on the same process**. Any single latency measurement is a sample, not a value.
- Live-city numbers move under other agents. Assert **invariants** (`emitted + folded == read`), not frozen counts.

---

## Ordering

**1 → 2 → 3** are a chain: the pile must drain before an end-to-end adjudication can be observed, and adjudication needs the index repairable.

**4, 5, 10** are independent and can run in parallel.

**6, 7, 9** are blocked on decisions — gather evidence, present, then build.

**8 is Taylor's.** Support, do not pre-empt.
