# create-issue-briefed smoke test (F6.1)

`smoke_test.sh` is the F6.1 gate for `mathcity/formulas/create-issue-briefed.formula.toml`.

Run from the rig root:

```bash
bash mathcity/tests/create-issue-briefed/smoke_test.sh
```

Same structural happy-path checks as the `pr-pipeline-briefed` smoke test, with
the never-execute guard checking `gh issue create`.

Latest run: see `results.txt` (PASS 8/8; check 9 `gc formula show` SKIPs until
the pack is installed into the live city).
