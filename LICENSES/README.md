# Licensing

The mathcity pack is licensed **GPL-3.0-or-later**. Full text: [../LICENSE](../LICENSE).

```
SPDX-License-Identifier: GPL-3.0-or-later
```

This covers everything in the pack — skill definitions, references, policies,
formulas, scripts, and the MCP servers under `subdomains/lean/mcp/`.

## Third-party material

### mathlib-quality (MIT)

[github.com/CBirkbeck/mathlib-quality](https://github.com/CBirkbeck/mathlib-quality),
a Claude Code plugin for bringing Lean 4 code up to Mathlib standards. Its notice
is retained verbatim at [mathlib-quality-MIT.txt](./mathlib-quality-MIT.txt) and
the project is credited in
[../subdomains/lean/README.md](../subdomains/lean/README.md).

MIT and GPL-3.0 are compatible in this direction: MIT-licensed material may be
incorporated into a GPL-licensed work, provided the MIT copyright and permission
notice are retained. They are, above.

Two notes on the upstream notice, recorded because neither should be quietly
tidied:

- It reads `Copyright (c) 2024` with **no named holder**. That is how upstream
  ships it and it is reproduced unchanged. The apparent author is
  [@CBirkbeck](https://github.com/CBirkbeck); that attribution is made here and
  in the lean README, and deliberately **not** inserted into the copyright line,
  which is not ours to complete.
- MIT's retention obligation attaches to copied expression, not to ideas.

## What was actually established, and what was not

The notice above is retained **by the repository owner's direction**, as
acknowledgment of design influence and as the conservative choice. It is not the
result of a finding that text was copied. The distinction is recorded rather than
blurred, because a licensing file's whole value is that it is accurate.

What is established:

- **Structural correspondence is real.** The Lean leaf set covers substantially
  the same decomposition as mathlib-quality's command set — the mapping table in
  the lean README lists ten correspondences. Two are specific enough to be worth
  naming: their `mathlibable-verdicts.md` defines five verdict buckets and our
  `lean-mathlib-fit` returns one of five verdicts; and their reference set
  includes a `tauceti.md`, while our `using-leanpowers` carries a Tau Ceti route.
- **Textual derivation was not found where it was checked.** Two pairs were
  compared directly against the upstream `main` branch:

  | upstream | ours | shared 4-grams |
  |---|---|---|
  | `references/golfing-rules.md` | `lean-golf/SKILL.md` | 0 |
  | `references/mathlibable-verdicts.md` | `lean-mathlib-fit/SKILL.md` | 0 |

  The two bodies are different genres — upstream writes numbered transformation
  checklists with Lean code blocks; these leaves write abstract process prose with
  no code. On this evidence the expression is independent and the influence is
  conceptual.

What is **not** established: the remaining leaves were not compared file by file,
so no claim is made either way about them. If a line-level comparison is ever
run and finds copied expression, the obligation was already discharged by
retaining the notice; if it finds none, the notice remains a courtesy and costs
nothing.

## Contributing

Contributions are accepted under GPL-3.0-or-later. Material under another licence
must be declared so it can be inventoried here rather than discovered later.
