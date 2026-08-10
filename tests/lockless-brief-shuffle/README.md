# lockless-brief-shuffle smoke test

Static regression test for gsp-89yli (replace brief-shuffle's persistent
`.shuffle.lock` with atomic-mv per-item claiming into `.staging/`).

Run:

    sh smoke_test.sh

This is a structural/text check against the formula TOML and check-script
source — it proves the SHAPE of the fix is present (3-step graph, atomic
mv, rescue-sweep language, bounded flock, wired staging-clear check). It
does **not** prove the fix works under real concurrent dispatch — that is
covered by `docs/superpowers/plans/2026-07-28-lockless-brief-shuffle.md`
Task 4, which dispatches against the live pool.
