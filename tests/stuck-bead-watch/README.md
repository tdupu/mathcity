# Stuck-Bead Watch Smoke Test

Self-contained smoke test for the stuck-bead-watch detector
(`mathcity/assets/scripts/stuck-bead-watch.py`) and its `stuck-bead-watch`
order (`mathcity/orders/stuck-bead-watch.toml`).

Exercises the detector's pure-Python logic (candidate detection, grace-window
lookup, waiting-room cache roundtrip, escalation TOML generation) without
requiring a live gc/bd fleet — mirrors
`mathcity/tests/lost-bead-filter/smoke_test.sh`'s structure.

Run: `sh smoke_test.sh` from this directory, or via the repo's standard test
runner.

Live (non-smoke) verification requires a running gascity fleet — see
docs/superpowers/plans/2026-07-28-stuck-bead-waiting-room.md Task 4 Step 4.
