# mathcity-lean

Parent: [../../README-subdomains.md](../../README-subdomains.md)

Lean 4 and Mathlib formalization. This subdomain holds the `using-leanpowers`
router and its 26 leaves.

The governing distinction: **compilation and source fidelity are separate
gates.** A build that succeeds establishes that a formal statement typechecks,
not that it says what the manuscript says. `lean-verify` answers the first and
`lean-fidelity` the second, and neither substitutes for the other. A declaration
count is not a measure of mathematical progress.

## Using the workflow

Start with `using-leanpowers`, which routes by observable request or condition.
Multi-phase work goes through `lean-workflow`; informal mathematics stays in
`using-mathpowers` and manuscript writing in `using-latexpowers`, with one plan
shared across all three.

Before planning, a repository-root `POWERS.md` (when present) tightens these
defaults for that repository only; `new-powers-policy` is the sole route for
amending either a local `POWERS.md` or a global default.

## Credits and prior art

The leaf decomposition in this subdomain covers substantially the same ground as
**[mathlib-quality](https://github.com/CBirkbeck/mathlib-quality)** by
[@CBirkbeck](https://github.com/CBirkbeck) — a Claude Code plugin for developing,
proving, cleaning up and bringing Lean 4 code up to Mathlib standards, with
phase-numbered gated workflows in which mathematical judgement is enforced
through required evidence rather than post-hoc review. That project is prior art
here and is credited accordingly.

The correspondence is close enough to be worth naming explicitly:

| mathlib-quality | this subdomain |
|---|---|
| `/decompose-proof` | `lean-decompose` |
| `/generalise` | `lean-generalize` |
| `/self-review` | `lean-review` |
| `/mathlibable` | `lean-mathlib-fit` |
| `/blueprint` | `lean-blueprint` |
| `/buzz` (performance) | `lean-profile` |
| `/overview` | `lean-status` |
| golfing patterns | `lean-golf` |
| style and naming rules | `lean-style` |
| Mathlib search methodology | `lean-search` |

`mathlib-quality` is **MIT licensed**. If any text in these leaves is derived
from it rather than independently written, MIT requires the copyright notice and
permission notice to be retained — a stronger obligation than attribution. That
has not been established file by file, so it is recorded here as an open item
rather than asserted either way.
