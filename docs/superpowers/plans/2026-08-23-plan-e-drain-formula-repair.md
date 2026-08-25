# Plan E — Drain Formula Repair (#73) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or
> superpowers:executing-plans. Repo-side (BART's fork lane), mathcity pack formulas.
> **Scope ruling status:** bug 2 is GO now; bug 1 is HELD for Taylor's adjudication (its step
> currently FAILS and would start SUCCEEDING — a real behavior change to the stack index,
> per mc-quq's own framing). Build bug 2; prepare bug 1 behind the ruling.

**Goal:** Make `brief-shuffle-fast-drain` actually able to run when it fires — the wall the
#204 unlatch hits next. Its formula invokes `python3 assets/scripts/brief-shuffle-fast-drain.py
--gate-config assets/brief-pipeline/gates.toml` cwd-relative (`formulas/
brief-shuffle-fast-drain.toml:36`), and the agent cwd is a per-bead work dir, so both the
script and the gate config fail to resolve. Same shape as the brief-check.sh bug fixed in
`d3ec6d7`.

**Architecture:** Convert the invocation to the pack-root form with the resolution recipe
already proven in `formulas/brief-present-next.toml` (read that file first and copy its
mechanism exactly — do not invent a second resolution pattern). Bug 1 (held): `$PACK_DIR` in
`formulas/brief-record-decision.toml:209` is injected only for order dispatch and gc custom
commands, never for formula-step agents, so the stack-index remove step expands to
`/assets/...` and fails.

**Premises (verify at execution):** mc-quq (P1, open) carries both bugs with file:line;
the #204 latch means the order has not fired since 08-17, so no live run will race the edit.

---

### Task 1: bug 2 — pack-root path in brief-shuffle-fast-drain.toml

- [ ] **Step 1: Read `formulas/brief-present-next.toml`'s path-resolution recipe** and quote it
  into the working notes (it is the spec; `check-plan-hygiene` will reject a novel mechanism).
- [ ] **Step 2: Failing test.** The pack ships no formula-execution harness, so the test is a
  RESOLUTION test: a pytest that parses `brief-shuffle-fast-drain.toml`, extracts every
  `python3`-invoked path from step commands, and asserts each resolves to an existing file
  when interpreted per the pack-root recipe FROM A cwd THAT IS NOT THE PACK ROOT (tmp dir).
  Current TOML → FAIL on both the script and the gate-config path.
- [ ] **Step 3: Apply the pack-root form** to line 36 (script AND `--gate-config` argument).
- [ ] **Step 4: GREEN**, plus `check-formula-hygiene` on the touched formula.
- [ ] **Step 5: Commit** — `fix(formulas): brief-shuffle-fast-drain resolves its script from
  the pack root, not the per-bead cwd (#73 bug 2)`. Push behind Taylor's gate.

### Task 2 (HELD — do not start without Taylor's ruling on #73 bug 1)

- [ ] Same recipe applied to `brief-record-decision.toml:209` (`$PACK_DIR` → pack-root form),
  PLUS the check mc-quq demands before priority is even set: inspect the live
  `stack/.index.jsonl` for archived-but-listed rows, because this step succeeding for the
  first time will start REMOVING rows. Report findings to QUIMBY before landing.

### Live acceptance (after the #204 unlatch lands and the fleet is up)

- [ ] Watch one `brief-shuffle-fast-drain` firing on mathcity: the formula's exec step must
  run its script (exit 0 or a REAL gate verdict) instead of `python3: can't open file`.
  Record the event seq + outcome in SURFACE-STATUS §5. **This is also #204's prediction test.**
