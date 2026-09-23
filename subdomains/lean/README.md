# mathcity-lean

Parent: [../../README-subdomains.md](../../README-subdomains.md)

Lean 4 and Mathlib formalization, together with the proof-assistant and search
surfaces that feed it. This subdomain absorbed the former `proof-assist`
subdomain: one folder now holds the formal work and the search/verification
surfaces it depends on, rather than splitting them across two.

The governing distinction: **compilation and source fidelity are separate
gates.** A successful build establishes that a formal statement typechecks, not
that it says what the manuscript says. `lean-verify` answers the first and
`lean-fidelity` the second; neither substitutes for the other, and a declaration
count is not a measure of mathematical progress. This subdomain is the escalation
target for prose-math correctness that embeddings and reviewers cannot settle,
and a passing build is the strongest evidence it can produce — of the formal
statement, and of nothing else.

## Using the workflows

Two routers live here and share one plan:

- `using-leanpowers` — formal artifacts. Routes by observable request or
  condition; multi-phase work goes through `lean-workflow`.
- `using-mathpowers` (alias `using-math`) — informal mathematics, research and
  proof. Both entry points use [math-workflow](../../skills/math-workflow/SKILL.md).

Manuscript writing stays in `using-latexpowers`. Requested `.tex` output routes
there within the same plan rather than starting a second intake.

Formulas: `proof-check` (mechanical hurdle) and `formalize-claim` (agent → build
gate). Proof-assistant doctrine is in [PROVERS.md](./PROVERS.md). The `mcp/`
directory ships the Stacks and Scholar MCP servers that `search-stacks` and
`search-scholar` drive.

Before planning, a repository-root `POWERS.md` (when present) tightens these
defaults for that repository only. `new-powers-policy` is the sole route for
amending either a local `POWERS.md` or a global default.

## Credits and prior art

The Lean leaf decomposition here covers substantially the same ground as
**[mathlib-quality](https://github.com/CBirkbeck/mathlib-quality)** by
[@CBirkbeck](https://github.com/CBirkbeck) — a Claude Code plugin for developing,
proving, cleaning up and bringing Lean 4 code up to Mathlib standards, with
phase-numbered gated workflows in which mathematical judgement is enforced
through required evidence rather than post-hoc review. That project is prior art
here and is credited accordingly.

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

`mathlib-quality` is MIT licensed; see the repository-root `LICENSES/` notes for
how that interacts with this pack's licence.
