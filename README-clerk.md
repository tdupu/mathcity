# Clerk Operation

Parent: [README.md](./README.md)

The clerk is an outside session assigned to the adjudication phase. It reads
briefs to the human, records verdicts, and dispatches approved follow-up work
through the front door. It does not edit code or policy as part of presentation.

## Core Loop

```text
present-briefs
  -> human verdict
  -> adjudicate-brief
  -> mathcity.work for approved follow-up when needed
  -> next brief
```

## Key Skills

| Skill | Purpose |
| --- | --- |
| `prime-clerk` | Orient a fresh clerk session. |
| `present-briefs` | Drain the stack and present briefs in priority/unlock order. |
| `adjudicate-brief` | Record the human verdict on the brief bead. |
| `work` | Dispatch approved follow-up work through the standard front door. |
| `check-plan-hygiene` | Check any sling command copied from a brief before execution. |

## Boundaries

- The clerk presents and records; it does not silently merge, push, or open PRs.
- A brief can recommend work, but the clerk still checks the command surface.
- Questions about sequencing or city state go to the Mayor or a dedicated
  city-status check.

## Related Docs

- [README-mayor.md](./README-mayor.md)
- [docs/TECHNICAL-SPEC.md](./docs/TECHNICAL-SPEC.md)
- [subdomains/brief-system/README.md](./subdomains/brief-system/README.md)
