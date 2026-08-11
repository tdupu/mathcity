# Skills Materialization

Parent: [../README-development.md](../README-development.md)

Mathcity skill source lives in the pack:

- parent skills: `skills/<name>/SKILL.md`
- subdomain skills: `subdomains/<sub>/skills/<name>/SKILL.md`

Agent-facing skill directories are sinks. They should contain relative
symlinks to pack source, not copied skill directories. Copying a skill forks
the source of truth and creates drift.

## Repo-Side Exposure

Outside-agent sessions discover mathcity skills through symlinks in the shared
agent-skills checkout:

```text
agent-skills/skills/<name> -> ../../mathcity/skills/<name>
agent-skills/skills/<name> -> ../../mathcity/subdomains/<sub>/skills/<name>
```

## City-Side Exposure

City-side skill sinks use the ADR 0002 alias convention:

```text
<city-root>/.claude/skills/mathcity.<name>
<city-root>/.claude/skills/mathcity-<sub>.<name>
```

Do not create or edit sink copies directly. Change the pack source, then
refresh or materialize the links through the approved pack-development path.
