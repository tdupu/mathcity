# Superpowers Availability Smoke Test

This test verifies the MathCity side of GitHub issue #4: Superpowers remains
owned by its upstream pack, MathCity imports that pack, and the expected
formula, skill, and run-target surfaces are present.

Run the static check from the MathCity pack root:

```sh
bash tests/superpowers-availability/smoke_test.sh
```

Run the live city check when `gc` is available and the rig catalog should
include imported formulas and agent targets:

```sh
RUN_LIVE_GC=1 GC_CITY_PATH=<city-root> bash tests/superpowers-availability/smoke_test.sh
```

The static check proves the import declaration is the pinned GitHub source —
`[imports.superpowers]` in `pack.toml` names
`https://github.com/gastownhall/gascity-packs/tree/main/superpowers` with a
`sha:`-pinned version, and `packs.lock` carries a matching entry — and that the
expected formula, skill, and agent surfaces are present in a local copy of the
Superpowers pack. The live check proves dispatch readiness: imported formulas
must appear in `gc formula list`, and every `superpowers.*` run target used by
those formulas must appear in `gc agent list`.

Defaults:
- `SUPERPOWERS_PACK` — where the static check reads pack *contents*, since it
  runs offline rather than fetching the pinned source. Defaults to
  `gascity-packs/superpowers` as a sibling of the **primary checkout**. The
  script resolves that sibling from the git common dir rather than from its own
  location, so the default is correct both in the primary checkout and in a git
  worktree under `.claude/worktrees/`. Keep that checkout at (or containing)
  the commit pinned in `packs.lock`; it stands in for the pinned source.
- `GC_CITY_PATH` — **no default.** A machine-specific absolute path must not be
  baked into a tracked file (`subdomains/dev/POLICY.md` P1.10). Only the live
  check reads it, and `RUN_LIVE_GC=1` fails fast when it is unset.
- `GC_RIG_NAME=hecke`

The pinned GitHub import replaced the interim local-path import
(`../gascity-packs/superpowers`), which resolved only next to a sibling
checkout and broke registry installs. If the live check fails while the static
check passes, the MathCity source import is present but the live city is not
yet safe to dispatch onto Superpowers formulas.
