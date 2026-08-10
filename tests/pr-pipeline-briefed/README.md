# pr-pipeline-briefed smoke test (F6.1)

`smoke_test.sh` is the F6.1 gate for `mathcity/formulas/pr-pipeline-briefed.formula.toml`.

Run from the rig root:

```bash
bash mathcity/tests/pr-pipeline-briefed/smoke_test.sh
```

It is a structural happy-path smoke test (no fleet dispatch): file exists, TOML
parses, catalog fields present, steps are `intake → compose-body → file-brief`
with a briefed terminal, the terminal step carries the `brief-producer.v1`
contract metadata, required vars (`source_bead`, `brief_slug` with pattern) are
declared, no model names appear in `run_target`s (F1.3/F3.3), and the formula
never *executes* `git push` / `gh pr create` (prose mentions are allowed).

Latest run: see `results.txt` (PASS 8/8; check 9 `gc formula show` SKIPs until
the pack is installed into the live city).
