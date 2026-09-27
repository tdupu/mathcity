# ADR 0008 — AI-authored formalizations do not go to Mathlib

Date: 2026-09-23 · Status: accepted (Taylor, in-session ruling, S74)

## Context

`goedel` (PCF formalization, Lean 4.34 / Mathlib v4.34.0) identified one
upstreamable declaration absent from both Mathlib and Tau Ceti:

```lean
theorem isStandardEtale_adjoinRoot_of_separable {f : R[X]}
    (hf : f.Monic) (hs : f.Separable) : Algebra.IsStandardEtale R (AdjoinRoot f)
```

The Mayor put "Mathlib or Tau Ceti" to Taylor as a decision and **recommended
Mathlib** — "connective tissue between two Mathlib APIs with no PCF or Tau Ceti
dependency, so it belongs upstream, and the cheapest possible first
contribution." Taylor ruled **Tau Ceti**. The Mayor recorded the outcome and did
not ask for the reason, so a standing principle was missed and only surfaced an
hour later when `goedel` relayed it.

## Decision

**AI-authored formalizations do not go to Mathlib.** Taylor, confirming the
rule directly: *"That's true."*

For this city that is a routing rule, not a quality judgement. The sequence for
work of this kind is:

1. a formalization for **Palomar** — a registry/provenance entry against a full
   immutable commit of `tdupu/pcf`, recording the exact formal statement,
   dependencies, toolchain and verification result;
2. then a **clean-up of that formalization for Tau Ceti**.

A declaration like `isStandardEtale_adjoinRoot_of_separable` is a Tau Ceti
candidate reached via step 2. It is never a standalone Mathlib PR.

## Why the city rule is stricter than the upstream policy

Read at source, 2026-09-23, `leanprover-community.github.io/contribute/` —
**Mathlib does NOT categorically exclude AI-authored contributions.** It permits
them under conditions:

- AI tool use must be **disclosed** in the PR description: which tools, and how.
- Substantial LLM-generated code requires the **`LLM-generated` label**.
- *"It is essential that you understand all the content written by an AI"* —
  including design decisions, justified to reviewers **without** AI assistance.
- *"Code written by an AI without the supervision of a Lean subject expert fails
  to meet that bar by a large margin"* (stated as of mid-2026).
- *"Getting code to mathlib's standards requires understanding and writing Lean
  code by hand."* Contributors must show genuine learning effort.
- Using an LLM for GitHub or Zulip **comments** is not allowed at all.
- Low-quality LLM PRs are closed summarily; repeat offenders are suspended or
  banned from PRs and Zulip.

So the upstream bar is not "no AI" — it is **a human expert who has done the
understanding, will justify it unaided, and will engage in public under their
own name.** An autonomous agent pipeline cannot clear that bar, because the bar
is precisely the human standing behind the work. A human contributor working
with AI assistance can.

The two rules therefore reach the same destination by different routes, and the
difference matters when either is cited:

| | upstream Mathlib policy | this city's rule |
| --- | --- | --- |
| AI-authored content | permitted under conditions | routed to Palomar → Tau Ceti |
| binding constraint | human understanding + supervision + public engagement | authorship provenance |
| who could satisfy it | a human working with AI | — |

**Do not cite this ADR as "Mathlib bans AI."** That is false, and a false
premise inside a gate is the `as-iq5gk` defect — `privacy-rulings.json`
asserted `tdupu/mathcity` was private when it is public, and that file is a
gate. Cite the city rule as the city's, and the upstream policy as what it
actually says.

## Consequences

- `goedel`'s pitch framing still holds, for a different reviewer: present it as
  the **Separable → IsStandardEtale bridge**, citing
  `HasMap.isUnit_derivative_f` at `StandardEtale.lean:92` and the class at
  `:379`. `Polynomial.Separable` is `IsCoprime f (derivative f)`; the file's
  machinery runs through `IsUnit (derivative f)`. It is connective tissue
  between two existing formulations — an argument that works anywhere.
- Nothing here licenses a Mathlib PR by any agent in this city.
- If Taylor ever wants to upstream something personally, the upstream policy —
  not this ADR — governs, and it permits AI assistance under the conditions
  quoted above.

## Open, and NOT decided here

Whether a new declaration entering Tau Ceti must cite an exact roadmap target in
the PR body, or may qualify as `Roadmap: none`. Raised by `kolchin-monitor`,
confirmed unresolved by `goedel`, and it **gates step 2**. Both declined to
answer it on Taylor's behalf, correctly.

One consideration for whoever puts it to him: `roadhog` ran two no-guidance
controls on roadmap construction tonight and **both failed**, one declaring a
proof *unnecessary* on the strength of `MonomialOrder.lex` when the pin ships
only `degLex`. A false *present*-claim attached to "this is now unnecessary"
deletes an obligation, and Palomar's provenance entry is exactly where such a
claim would be frozen into a permanent record. That argues for requiring the
citation rather than allowing `Roadmap: none` — but it is an argument, not a
ruling.

## Method note

The Mayor recommended Mathlib while unaware of this rule, so the recommendation
argued for something operationally unavailable. The rule was then relayed by
`goedel` as "Mathlib is for human-only formalizations"; the Mayor declined to
record it on a peer's relay, put it to Taylor, and read the upstream policy at
source on his instruction. The relayed form turned out to be an approximation —
directionally right, categorically wrong. **Recording the relay verbatim would
have put a false premise in a gate.**

[autogenerated by Claude Opus 5 v2.1.231 (Claude Code) on 2026-09-23]
