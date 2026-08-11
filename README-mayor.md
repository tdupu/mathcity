# Mayor Operation

Parent: [README.md](./README.md)

The Mayor is the city coordination role. It watches city progress, dispatches
or retargets work when authorized, and keeps the city moving through beads,
briefs, orders, and formulas. It is not the same as the outside clerk.

## Responsibilities

| Responsibility | Surface |
| --- | --- |
| Orientation after restart | `mayor-math-prime`, `mayor-math-restart` |
| City work coordination | `mayor-math`, `work`, `push-the-fleet`, `city-status` |
| Brief awareness | `check-briefs`, `present-briefs` when explicitly serving as presenter |
| Worker health | `check-work`, `check-molecules`, `check-on-agent`, `wake-city`, `nudge-city` |
| Handoff | `mayor-math-handoff` |

## Boundaries

- Do not start or restart the Mayor unless explicitly requested.
- Mayor coordination does not replace human adjudication.
- Presentation can be done by the Mayor, but it is usually the clerk's job.
- Source changes still obey policy, brief, and documentation gates.

## Related Docs

- [README-clerk.md](./README-clerk.md)
- [docs/TECHNICAL-SPEC.md](./docs/TECHNICAL-SPEC.md)
- [subdomains/dev/POLICY-city.md](./subdomains/dev/POLICY-city.md)
