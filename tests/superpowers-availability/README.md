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
RUN_LIVE_GC=1 bash tests/superpowers-availability/smoke_test.sh
```

The static check proves the source pack and import declaration are present.
The live check proves dispatch readiness: imported formulas must appear in
`gc formula list`, and every `superpowers.*` run target used by those formulas
must appear in `gc agent list`.

Defaults:
- `SUPERPOWERS_PACK=../gascity-packs/superpowers`
- `GC_CITY_PATH=/Users/tdupuy/gt`
- `GC_RIG_NAME=hecke`

The local-path import is an interim availability mechanism. The hygienic,
pinned pack-import design remains tracked separately by `mc-fe7.1`. If the
live check fails while the static check passes, the MathCity source import is
present but the live city is not yet safe to dispatch onto Superpowers
formulas.
