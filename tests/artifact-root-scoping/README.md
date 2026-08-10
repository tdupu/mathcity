# artifact-root-scoping smoke test

Regression test for gsp-1bmxuz (concurrent `build-basic-briefed` workflows on
the same rig silently overwrite each other's stage artifacts because they
share one unsuffixed `artifact_root`).

Run:

    sh smoke_test.sh

Checks:

1. `push-the-fleet` SKILL.md no longer documents the old bare rig-root
   `artifact_root=<rig-artifact-root>` dispatch form.
2. `push-the-fleet` SKILL.md documents the scoped
   `artifact_root=<rig-root>/.gc-builds/<bead-id>` form.
3. `mathcity.work` SKILL.md documents the same scoped form for its
   `build-basic-briefed` branch.
4. `mayor-math-prime` SKILL.md documents the scoped
   `artifact_root=<rig-root>/.gc-builds/<artifact-bead>` form for its
   `build-basic-briefed` dispatch.
5. `prime-clerk` SKILL.md documents the scoped
   `artifact_root=<rig-root>/.gc-builds/<artifact-bead>` form for its
   `build-basic-briefed` dispatch.
6. `mayor-math` SKILL.md documents the scoped
   `artifact_root=<rig-root>/.gc-builds/<bead>` form for its
   `build-basic-briefed` dispatch.
7. `adjudicate-brief` SKILL.md documents the scoped
   `artifact_root=<rig-root>/.gc-builds/<ARTIFACT>` form for its
   `build-basic-briefed` dispatch.

This is a static text check — each check greps a specific skill doc for a
specific scoped-artifact_root substring — it does not require a live city,
matching the convention of the other `mathcity/tests/*/smoke_test.sh`
fixtures (e.g. `lost-bead-filter`, `producer-failure-rollup-routing`).
