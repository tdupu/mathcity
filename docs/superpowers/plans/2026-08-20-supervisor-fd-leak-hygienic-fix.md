# Supervisor File-Descriptor Leak — Hygienic Fix Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the gascity supervisor from exhausting `kern.maxfilesperproc`, and make the next occurrence detectable before it takes the city down.

**Architecture:** Three separable pieces. (1) The **amplifier** is confirmed in gascity core and is not ours to patch — it becomes an upstream issue. (2) The **opener** cannot currently be named, so the first task is instrumentation that recovers it rather than a fix aimed at a guess. (3) A **level-driven local mitigation** bounds the damage in the meantime, deliberately not timer-driven.

**Tech Stack:** Go (gascity core, read-only to us), Python 3 + `mctl_core`, shell smoke tests, launchd.

**Spec:** This plan's inputs are three measurements, each attributed:
- Amplifier confirmed at source — stick-dog (`deadpath-agent`), re-verified independently by brad before writing.
- fd counts and leak rate — QUIMBY and pink. **They disagree, and this plan does NOT resolve it by precedence.** QUIMBY raised the objection against its own number: ranking one measurement over another without stating the counting method is a judgement dressed as a fact. **PID 20711 is dead, so the disagreement is now unresolvable on the original evidence.** `fd-census.sh` defines the method; restate prior figures in it or leave them marked method-unknown.
- Consequence chain — lumby's brief of 2026-08-20 22:33.

## Global Constraints

- **P3.1: no direct edits to gascity core.** `internal/beads/native_dolt_store.go` is upstream. Any change there is an issue against `gastownhall/gascity`, never a local patch.
- **`kern.maxfilesperproc` = 138,240.** **Do not cite a single "measured" fd count in this plan.** Three methods produced three values — 138,244 (`-Fn` name records, four *over* a cap a process cannot exceed, so it counts non-descriptors), 138,234 (`lsof | wc -l`, six *under*), and whatever `fd-census.sh` will produce. **All pre-census figures are method-unknown and are marked so.** Every conclusion here needs only "at the wall", which all three support.
- **The leak rate is NOT constant.** The amplifier makes it rise as exhaustion nears. **Any bound must be driven by a measured level, never by a timer.**
- **Do not blame `reconnect()`.** stick-dog cleared it: handles are closed on all four exit paths (`:553-578`).
- **`[SYN]` values are invented; never cite one as a measurement.**

---

## What is established, and what is not

**CONFIRMED — the amplifier.** `internal/beads/native_dolt_store.go`:

```
:562  nativeDoltTransientReadErrorSignatures = []string{ ..., "dial tcp", ... }
:576  isNativeDoltTransientReadError -> strings.Contains(lower(err), sig)
:494  if isNativeDoltTransientReadError(opErr) -> s.reconnect(ctx, gen)
```

EMFILE surfaces as `dial tcp 127.0.0.1:58506: socket: too many open files`. It **contains** `dial tcp`, so **running out of file descriptors is classified as a transient network blip and answered by opening another connection.** Per read, per rig, re-arming on its own failure.

**Provenance:** `"dial tcp"` entered in `6e6e3c916` (2026-07-12), a correct fix for a managed-Dolt rebind whose predicate was one notch too wide. **This is not a returning bug** — it is an unhandled case in a good fix. Say so upstream.

**NOT ESTABLISHED — the opener.** ~96k descriptors were pinned to `~/repos/mathcity/.claude` (95,067) and `.git` (27,756). But `.claude/worktrees/` is a **Claude Code harness** construct; gascity's own worktrees live at `<repo>/.gc/worktrees/<id>` (`internal/runtime/import_trust.go:13`). stick-dog found no supervisor-side code that walks `.claude`. **PID 20711 is dead, so the fd table that would name the opener no longer exists.**

**Do not infer an opener from the dead process.** Task 1 recovers it.

**A conflation to avoid, corrected by stick-dog before it entered this plan:** the ~96k descriptors are in `~/repos/mathcity/.claude`. creek's 14 orphaned worktrees / 119.7 GB are in `~/gt/hecke/`. **Different trees, found separately, hours apart, in different repositories.** The only thing linking them is the word "worktree." **The `~/gt/hecke` freeze does not obviously constrain this work**, and no task here assumes it does.

---

## File Structure

| File | Responsibility |
|---|---|
| `assets/scripts/checks/fd-pressure.sh` (create) | Level-driven probe: reads the supervisor's fd count against the cap, three-valued |
| `tests/fd-pressure/smoke_test.sh` (create) | Proves the probe fires — including that it can fail |
| `docs/superpowers/plans/2026-08-20-supervisor-fd-leak-hygienic-fix.md` | This plan |
| upstream issue (no local file) | The amplifier fix — `gastownhall/gascity` |

---

### Task 1: Recover the opener under instrumentation

> **EXTERNAL PRECONDITION — not a step anyone here can take.** Tasks 1 and 5 need a **live supervisor pid**. PID 20711 is dead and the city's lifecycle is Taylor's. **If no supervisor is running, stop and report — do not improvise a substitute pid.** Flagged by QUIMBY; without it a worker picks this up, finds nothing to measure, and invents something.

**Files:**
- Create: `assets/scripts/checks/fd-census.sh`
- Test: `tests/fd-pressure/smoke_test.sh`

**Interfaces:**
- Produces: `fd-census.sh <pid>` → JSON `{"pid":N,"total":N,"cap":N,"by_prefix":{path:count},"classified_count":N,"unclassified_count":N,"sampled_at":"ISO8601"}`
  where `classified_count + unclassified_count == total` — see C2.
- Consumes: nothing. This task is first precisely because nothing downstream can be written without its output.

- [ ] **Step 1: Write the failing test**

```bash
# tests/fd-pressure/smoke_test.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"          # up TWO — see #113/656f3d7
CENSUS="$REPO/assets/scripts/checks/fd-census.sh"
[ -x "$CENSUS" ] || { echo "FAIL: fd-census.sh missing or not executable"; exit 1; }
out="$("$CENSUS" $$)" || { echo "FAIL: census exited nonzero on a live pid"; exit 1; }
echo "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["total"]>0; assert d["cap"]>0; assert d["by_prefix"]' \
  || { echo "FAIL: census output lacks total/cap/by_prefix"; exit 1; }
echo "PASS: census reports total, cap and a prefix breakdown"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `bash tests/fd-pressure/smoke_test.sh`
Expected: `FAIL: fd-census.sh missing or not executable`

- [ ] **Step 3: Write the minimal implementation**

```bash
#!/usr/bin/env bash
# assets/scripts/checks/fd-census.sh — read-only fd census for one pid.
set -euo pipefail
PID="${1:?usage: fd-census.sh <pid>}"
CAP="$(sysctl -n kern.maxfilesperproc)"
TMP="$(mktemp -t fd-census)"; trap 'rm -f "$TMP"' EXIT INT TERM
lsof -p "$PID" -Fn 2>/dev/null | sed -n 's/^n//p' > "$TMP" || true
TOTAL="$(wc -l < "$TMP" | tr -d ' ')"
python3 - "$TOTAL" "$CAP" "$PID" "$TMP" <<'PY'
import sys, json, collections, datetime
total, cap, pid, src = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
counts = collections.Counter()
for line in open(src, errors="replace"):
    p = line.strip()
    if not p.startswith("/"):
        continue
    counts["/".join(p.split("/")[:5])] += 1
classified = sum(counts.values())
print(json.dumps({"pid": pid, "total": total, "cap": cap,
                  "by_prefix": dict(counts.most_common(20)),
                  "classified_count": classified,
                  "unclassified_count": total - classified,
                  "sampled_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}))
PY
```

- [ ] **Step 4: Run it to verify it passes**

Run: `bash tests/fd-pressure/smoke_test.sh`
Expected: `PASS: census reports total, cap and a prefix breakdown`

- [ ] **Step 5: State how the check could have failed**

Delete `by_prefix` from the JSON and re-run. Expected: `FAIL: census output lacks total/cap/by_prefix`. Restore. **Record both runs in the commit message** — a smoke test whose failure nobody has seen is not evidence.

- [ ] **Step 6: Commit**

```bash
git add assets/scripts/checks/fd-census.sh tests/fd-pressure/smoke_test.sh
git commit -m "checks: fd census, to recover the leak's opener under instrumentation"
```

---

### Task 2: File the amplifier upstream

**Files:** none local. Issue against `gastownhall/gascity`.

**Interfaces:**
- Consumes: nothing.
- Produces: an upstream issue number, to be linked from local `#70`.

- [ ] **Step 1: Confirm the remote before filing**

```bash
git -C ~/repos/gascity remote -v | grep upstream
```
Expected: `upstream  …gastownhall/gascity…`. **If it is not, stop** — do not file against `tdupu/gascity`, which is our fork.

- [ ] **Step 2: File it, with this body**

The issue must carry, verbatim:
- `nativeDoltTransientReadErrorSignatures` includes `"dial tcp"` (`native_dolt_store.go:562`), matched by `strings.Contains` (`:576`).
- EMFILE surfaces as `dial tcp …: socket: too many open files`, therefore matches, therefore `reconnect()` opens another connection (`:494`).
- **The failure mode is self-amplifying**: the response to exhaustion consumes the exhausted resource.
- Provenance: `6e6e3c916` (2026-07-12) — a correct rebind fix whose predicate was one notch too wide. **Not a regression.**
- **`reconnect()` itself is clean** (`:553-578`); do not let a fixer chase it.
- Consequence chain: supervisor cannot open a socket → `gc dashboard serve` prints a URL nothing listens on → `gc` calls hang 30s+ → `gc start` refuses because it cannot determine hosting mode → three status commands give three answers. **A user cannot start their city and nothing tells them why.**
- **Credit what is right:** `gc start` refused rather than guessing. That is correct behaviour under uncertainty and should survive the fix.
- Suggested direction (theirs to accept): EMFILE is not transient. Either exclude `too many open files` explicitly, or match on typed errors rather than substrings.

- [ ] **Step 3: Link, do not close, local `#70`**

`#70` stays open as the local record.

---

### Task 3: Level-driven mitigation

**Files:**
- Create: `assets/scripts/checks/fd-pressure.sh`
- Modify: `tests/fd-pressure/smoke_test.sh`

**Interfaces:**
- Consumes: `fd-census.sh` from Task 1 — exact output contract above.
- Produces: exit `0` healthy, `1` degraded, `2` unreachable. **Three-valued, never boolean** (§5.1).

- [ ] **Step 1: Write the failing test**

```bash
# appended to tests/fd-pressure/smoke_test.sh
PRESSURE="$REPO/assets/scripts/checks/fd-pressure.sh"
[ -x "$PRESSURE" ] || { echo "FAIL: fd-pressure.sh missing"; exit 1; }
FD_PRESSURE_FORCE_RATIO=0.99 "$PRESSURE" $$ >/dev/null 2>&1
[ $? -eq 1 ] || { echo "FAIL: 99% of cap did not report degraded"; exit 1; }
FD_PRESSURE_FORCE_RATIO=0.01 "$PRESSURE" $$ >/dev/null 2>&1
[ $? -eq 0 ] || { echo "FAIL: 1% of cap did not report healthy"; exit 1; }
"$PRESSURE" 999999 >/dev/null 2>&1
[ $? -eq 2 ] || { echo "FAIL: a dead pid did not report unreachable"; exit 1; }
# C1: every assertion above forces the ratio, so the CENSUS path is never run.
# This one must NOT force it -- it is the only assertion that can detect a
# broken measurement, which is the entire risk. Without it fd-census.sh could
# be deleted and this suite would still print PASS.
ratio="$("$PRESSURE" $$ 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["ratio"])')" \
  || { echo "FAIL: census path did not produce a ratio"; exit 1; }
python3 -c "import sys; r=float(sys.argv[1]); sys.exit(0 if 0.0 < r < 1.0 else 1)" "$ratio" \
  || { echo "FAIL: census ratio $ratio is not in (0,1) -- measurement is broken"; exit 1; }
echo "PASS: fd-pressure is three-valued, fires at the threshold, and its census path measures"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `bash tests/fd-pressure/smoke_test.sh`
Expected: `FAIL: fd-pressure.sh missing`

- [ ] **Step 3: Implement**

```bash
#!/usr/bin/env bash
# assets/scripts/checks/fd-pressure.sh — level-driven, NOT timer-driven.
# The leak rate rises as exhaustion nears (the reconnect amplifier), so an
# interval computed from an average is too slow at the wall. Threshold on level.
set -uo pipefail
PID="${1:?usage: fd-pressure.sh <pid>}"
THRESH="${FD_PRESSURE_THRESHOLD:-0.80}"
kill -0 "$PID" 2>/dev/null || { echo '{"state":"unreachable","reason":"pid not running"}'; exit 2; }
if [ -n "${FD_PRESSURE_FORCE_RATIO:-}" ]; then RATIO="$FD_PRESSURE_FORCE_RATIO"; else
  HERE="$(cd "$(dirname "$0")" && pwd)"
  RATIO="$("$HERE/fd-census.sh" "$PID" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["total"]/d["cap"])')"
fi
python3 - "$RATIO" "$THRESH" <<'PY'
import sys, json
ratio, thresh = float(sys.argv[1]), float(sys.argv[2])
state = "degraded" if ratio >= thresh else "healthy"
print(json.dumps({"state": state, "ratio": round(ratio, 4), "threshold": thresh}))
sys.exit(1 if state == "degraded" else 0)
PY
```

- [ ] **Step 4: Run it to verify it passes**

Run: `bash tests/fd-pressure/smoke_test.sh`
Expected: `PASS: fd-pressure is three-valued and fires at the threshold`

- [ ] **Step 5: State how the check could have failed** — REQUIRED, and its absence is what let C1 through

```bash
mv assets/scripts/checks/fd-census.sh /tmp/   # break the measurement
bash tests/fd-pressure/smoke_test.sh          # expect: FAIL: census path did not produce a ratio
mv /tmp/fd-census.sh assets/scripts/checks/   # restore
```

**Record both runs in the commit.** If deleting `fd-census.sh` does not turn this suite red, the suite is testing arithmetic nobody doubted and not the measurement that is actually at risk.

- [ ] **Step 6: Commit**

```bash
git add assets/scripts/checks/fd-pressure.sh tests/fd-pressure/smoke_test.sh
git commit -m "checks: level-driven fd pressure probe, three-valued"
```

---

### Task 4: Wire detection to pink's `#114` flood alarm

**Files:**
- Modify: whichever file `#114` lands the flood alarm in — **read `#114` before starting; do not guess the path.**

**Interfaces:**
- Consumes: `fd-pressure.sh` exit codes from Task 3.
- Produces: a `flood_conditions` entry naming fd pressure, with its ratio and threshold as inputs (§5.5 — derived states carry their inputs).

- [ ] **Step 1: Read `#114` and record the actual integration point** in this task before writing code. If `#114` has not landed, **stop and report** — this task has a hard dependency and guessing its shape would produce exactly the placeholder this plan forbids.

- [ ] **Step 2–5:** mirror Task 3's cycle — failing test, verify red, implement, verify green, state how it could have failed, commit.

**Why this is a task and not a footnote:** pink's flood alarm **fired for real while being built.** A bound nobody watches is not a bound.

---

### Task 5: Decide the fate of the ~96k stale descriptors

**Files:** none until Task 1 reports.

- [ ] **Step 1: Run `fd-census.sh` against the live supervisor** once launchd has restarted it, and record `by_prefix`.

- [ ] **Step 2: Answer one question** — are the descriptors reclaimed when the process is replaced, or do they re-accumulate against paths that no longer exist? The census answers it directly.

- [ ] **Step 3: If they re-accumulate, this becomes a new task and a likely second upstream issue.** If they do not, **say so and close this task** — "the restart reclaims them" is a legitimate finding and needs no sweep.

**Do not write a sweep before Step 2.** A sweep aimed at a population that clears itself is wasted work, and one aimed at the wrong tree is worse.

---

## Self-Review

**Spec coverage.** lumby asked for five things: what closes the descriptors (Task 1 — recovers the opener, because it is not currently nameable); upstream or local (Task 2 — upstream, confirmed via remotes); what a bound looks like (Task 3 — level-driven, with the reason the timer form is wrong); how we detect it next time (Task 4 — `#114`); and what to do about the ~96k (Task 5 — measure first). **All five have a task.**

**Placeholder scan.** Task 4 Step 2 is deliberately deferred to `#114`'s landed shape and **says so with a stop condition** rather than inventing a path — the one place this plan declines to specify, and it is marked. No "TBD", no "add error handling", no "similar to Task N".

**Type consistency.** `fd-census.sh` emits `{pid,total,cap,by_prefix,sampled_at}` in Task 1 and is consumed under exactly those names in Tasks 3 and 5. Exit codes `0/1/2` are defined once in Task 3 and referenced in Task 4.

**Known gap, stated rather than hidden:** the opener is unknown, so **no task in this plan fixes the leak.** Tasks 1–5 bound it, detect it, and recover the information needed to fix it. **If that is not acceptable, the alternative is a fix aimed at a guess**, and the day this plan was written produced eight instances of confident wrong answers from exactly that move.
