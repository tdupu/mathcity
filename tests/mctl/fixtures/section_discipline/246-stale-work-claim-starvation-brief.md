---
artifact: none
status: ready-for-adjudication
form: full
track: city-infra
unlock_count: 7
shape: named options
gates: test-evidence N/A (decision-shaped, no runnable artifact)
---

## §1 — What is being decided (INVARIANT)

**Fresh work appears to get claimed while identical older work sits unclaimed indefinitely. Do we investigate claim ordering, and how?**

**Recommended: (B) measure before theorising — one targeted observation, no build.**

## §2 — The observation, measured not inferred

Two route steps exist for the SAME source bead `mc-hs3`, created hours apart:

```
mc-nd3  Route mc-hs3 through mathcity.work   open, assignee=NONE     (pre-existing, hours old)
mc-pyn  Route mc-hs3 through mathcity.work   in_progress,
                                             assignee=gc__run-operator-gt-l1e567   (~40min old)
```

**The newer one claimed. The older one did not.** Both were in `bd ready`. Both name the same target. Both carry `gc.run_target = gc.run-operator`.

At the time of measurement: **16 items in `bd ready`, 16 active run-operators, and the older items had been sitting for hours.**

## §3 — Why this matters beyond one bead

If stale ready-work is systematically passed over, then **re-slinging becomes the de facto remedy for anything that sits**, which is exactly what happened here — and it silently doubles the graph each time. This session produced one duplicate molecule (`mc-poj`/`mc-pyn`/`mc-8tk`) as a direct consequence, and the duplicate is the copy that ran.

It also means "N items ready" is not a meaningful health signal: a queue can be simultaneously full and starved.

## §4 — What is NOT established

- **That there is any ordering bias at all.** Two observations is not a pattern. The claim may have been coincidental timing, a pool slot freeing, or a lease cycle.
- **Whether `mc-nd3` is claimable at all** — it may carry a defect the newer molecule lacks (different metadata, a broken dep edge, an expired lease). **Not checked.**
- **Whether the ~40min claim latency is normal.** I twice today declared "stalled" on elapsed time and was twice wrong. 40 minutes may simply be the cycle time under a 14-30 pane fleet.

## §5 — Options

- **(A) Assume starvation, re-sling stale work as policy.** Cheap, and it is what already happened by accident. Doubles the graph on every application and treats the symptom.
- **(B) One targeted observation.** *(recommended)* Diff `mc-nd3` against `mc-pyn` — metadata, dep edges, lease state — and watch whether `mc-nd3` ever claims. Answers "is it ordering, or is `mc-nd3` broken?" which is the actual fork. Cheap, read-only.
- **(C) Read the claim-selection code.** Definitive, and settles it for every rig rather than this bead. Larger, and the checkout may be stale relative to the running binary (see #235).
- **(D) Nothing.** Accept that stale work needs a human to notice and re-sling.

## §6 — Risks

**(A) is the trap.** It converts an unexplained delay into a standing practice of duplicating work, and duplicates are indistinguishable from legitimate parallel dispatch once they exist.

**Cleanup is pending either way:** `mc-poj`/`mc-pyn`/`mc-8tk` vs `mc-nd3` — one set should be retired, and which one depends on this answer. `mc-pyn` is the live one, so retiring the *newer* set would kill running work.

**The other three beads (`mc-b4t`, `mc-55t`, `mc-9f3`) are in the same state** and have not been re-slung, deliberately — pending this.

## §7 — ACTION-BLOCK

```yaml
action_block:
  on_approve: [{"type": "external-reminder", "target": "quimby", "note": "State the option. If (B): diff mc-nd3 vs mc-pyn (metadata, deps, lease) and watch whether mc-nd3 ever claims, BEFORE re-slinging mc-b4t/mc-55t/mc-9f3. Do not retire mc-pyn \u2014 it is the live one."}]
  on_reject: [{"type": "external-reminder", "target": "quimby", "note": "No investigation; stale ready-work continues to require a human to notice, and re-slinging remains the ad-hoc remedy."}]
  on_defer: [{"type": "snooze", "interval": "7d"}]
```
