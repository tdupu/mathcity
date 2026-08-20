# ADR 0003: Beads Migrated From a Retired Store Keep Their Origin Prefix

Parent: [../TECHNICAL-SPEC.md](../TECHNICAL-SPEC.md)

## Status

Adopted (2026-08-19, Taylor).

## Context

`tdupu/gascity-packs/mathcity` is being retired in favour of `tdupu/mathcity`
(see [0002](./0002-mathcity-subdomain-pack-model.md) for the pack model the
work lands in). Retirement is blocked on the bead side, not the file side:
mathcity work was tracked in the **gascity-packs** bead store, and that work
has to reach mathcity's store before the tree can go.

At the time of writing the gascity-packs store holds 9,583 beads (3,924 open),
of which roughly 66 open beads are mathcity work. Mathcity's own store holds 36.

A bead ID is an **address**: the prefix names the store the bead lives in.
`gsp-nq3ut1` says "gascity-packs". Moving the bead breaks that correspondence
one way or the other, so the choice is which breakage to take.

Two mechanical facts constrain the options:

- `bd import` **upserts by ID**. It preserves IDs, timestamps, dependencies,
  comments, and metadata verbatim. Preserving the original ID is the default,
  not extra work.
- `bd rename-prefix` operates on a **whole database**. It cannot re-prefix a
  66-of-3,924 subset, so "move and re-prefix" is not available as one step.

## Decision

Migrated beads **keep their `gsp-*` IDs** in the mathcity store, and each
records its origin in `external_ref` / `metadata` so the foreign prefix is
explained rather than mysterious.

## Rationale

Referential integrity beats prefix hygiene at this scale.

Every existing reference to a `gsp-*` ID keeps resolving: dependency edges
inside a 9,583-bead store, plus references living outside any store entirely —
in brief markdown, in documentation, in commit messages. Minting fresh `mc-*`
IDs would leave every one of those dangling, and there is no automatic way to
repair references that live outside the database.

The cost is real and permanent: mathcity's store holds beads whose prefix does
not name their home, so the prefix stops being a reliable indicator of which
store a bead lives in. The provenance stamp is what keeps that from being a
mystery to a future reader.

## Consequences

- **A bead prefix indicates origin, not current location.** Any tooling that
  infers a bead's store from its prefix is wrong for migrated beads. The
  prefix-to-rig maps used by reporting skills are affected — see
  `skills/check-briefs/SKILL.md`, whose prefix map is display-only for exactly
  this class of reason.
- **`bd rename-prefix` must not be run against the mathcity store** after
  migration. It rewrites every ID in the database, which would re-break the
  references this decision exists to preserve.
- Migration is export → import → close the originals in gascity-packs. The
  originals are closed rather than deleted, so the old store keeps a record of
  where the work went.
- The 31 untracked files in `~/gt/gascity-packs/mathcity` are a **separate**
  problem from the beads. They are unrecoverable if that tree is deleted (they
  are in no git history anywhere) and must be committed before any deletion.
  Bead migration does not address them.

## Alternatives considered

**Mint fresh `mc-*` IDs.** Clean prefixes matching the store. Rejected:
`rename-prefix` cannot do a subset, so this means new IDs, and every `gsp-*`
reference outside the moved set dangles with no automatic repair path.

**Close in gascity-packs and re-file fresh mathcity beads.** Cleanest end
state and smallest store. Rejected: discards history, comments, and dependency
structure on beads carrying months of context.

**Leave the beads and retire only the tree.** Unblocks the file work
immediately. Rejected: the work itself belongs to mathcity, and leaving it
addressed to a retired pack is what created this problem.
