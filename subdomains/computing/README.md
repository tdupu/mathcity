# mathcity-computing

[Magma](http://magma.maths.usyd.edu.au/magma/) (and Sage/PARI) computation
workflow: the notebook⇄mag⇄package development loop, profiling and
dispatching heavy runs (including UPF rig jobs), and maintaining the Magma
packages that come out of it.

Import alias convention (ADR 0002): skills materialize as
`mathcity-computing.<skill>`.

## The Magma development loop

The core workflow these skills implement — a human mathematician iterates between a
Jupyter notebook (running the
[edgarcosta/magma_kernel](https://github.com/edgarcosta/magma_kernel)) and
versioned `.mag` files, with agents doing the in-between work:

1. **Notebook** — the mathematician writes or edits code in a Jupyter notebook.
2. **`notebook-to-mag`** — the notebook's code is pulled into a versioned
   `.mag` file (incremented index), where agents edit, modify, and add
   examples.
3. **`mag-to-notebook`** — the improved `.mag` file is sent back into the
   notebook for human review.
4. **Iterate** steps 1–3 until the functions are good.
5. **`notebook-to-package`** — good functions are promoted to package
   intrinsics in the appropriate `package-*.mag` file.
6. **Re-test as intrinsics** — the last testfile is redone with the plain
   functions replaced by the new intrinsics, proving they still perform as
   before promotion.
7. **`improve-package-README`** — commits the new tests into the README
   test files (regression protection) and adds the new intrinsics to the
   package documentation.

`check-mre` gates steps 2–6: any MRE an agent produces along the way must
satisfy the consuming project's `.claude/MRE-POLICY.md` before it enters
the test corpus. `profile-magma` diagnoses any step that gets slow.

## Skills

| Skill | Purpose |
| --- | --- |
| `notebook-to-mag` | Pull code from a modified Jupyter notebook into a versioned `.mag` file (incremented index) for agent iteration |
| `mag-to-notebook` | Send an improved `.mag` file back into the notebook for review — the return leg of the loop |
| `notebook-to-package` | Promote good Magma functions from the notebook into package intrinsics in the right `package-*.mag` |
| `check-mre` | Gate an MRE file against the project's `.claude/MRE-POLICY.md` — APPROVED or REJECTED with the missing requirements |
| `improve-package-README` | Add/update package documentation + README test files, keeping examples and regression tests in sync (formerly `improve-README`) |
| `profile-magma` | Wrap Magma code in a profiling harness to find bottlenecks (slow intrinsics, memory hogs) |
| `update-issue` | Replace a GitHub issue's body with one canonical statement, consolidating prior versions into a single archive comment |
| `check-computing-policy` | Audit computation code, a diff, or a project against the Computing Policy (C1.x–C4.x rules) — returns approve / revise / fail with violated rule IDs and triggering files; read-only companion to `new-computing-policy` |
| `new-computing-policy` | Propose and apply an amendment to the Computing Policy (C1.x–C4.x rules) — sole write path for computing domain rules; every change is gated on human approval and recorded in the policy Change Log |

## Maintained packages

This workflow is meant for Magma and Sage packages that use notebook-driven
experimentation, versioned `.mag` files, and README-backed regression examples.
Repository-specific package names belong in local context, not in this public
README.

Notebook workflows run on the Jupyter Magma kernel:

- [edgarcosta/magma_kernel](https://github.com/edgarcosta/magma_kernel)

## Pipeline integration

Heavy-run dispatch wraps `upf-experiment-dispatch` and
`test-execution-request`. Computation results are collected as
`brief_type = experiment` briefs and fed back into the brief pipeline via
`math-brief-prep`.
