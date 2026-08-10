---
name: skill-creator-math
description: Create a new skill in the standalone mathcity pack family under <mathcity-pack-root>/skills or <mathcity-pack-root>/subdomains/*/skills, then update indexes and validate exposure. Use whenever the user says "create a math skill", "add a skill to the mathcity pack", "pack skill for X", "skill-creator-math", or asks to make a brief-cycle, math-workflow, or pack-dev skill available to Gas City agents.
---

# skill-creator-math

Create a skill in the **mathcity pack family** and make it discoverable through
the pack. Mathcity is a standalone repository; do not assume it lives inside a
larger pack monorepo.

## Pick The Destination

Set `<mathcity-pack-root>` to the checkout or imported pack root containing
`pack.toml`, then choose exactly one destination:

| Domain | Destination | Skill alias |
|---|---|---|
| Cross-domain or brief-cycle core | `<mathcity-pack-root>/skills/<name>/` | `mathcity.<name>` |
| Brief-system pipeline internals | `<mathcity-pack-root>/subdomains/brief-system/skills/<name>/` | `mathcity-brief-system.<name>` |
| Computing | `<mathcity-pack-root>/subdomains/computing/skills/<name>/` | `mathcity-computing.<name>` |
| Proof assistants | `<mathcity-pack-root>/subdomains/proof-assist/skills/<name>/` | `mathcity-proof-assist.<name>` |
| LaTeX and notes screening | `<mathcity-pack-root>/subdomains/latex/skills/<name>/` | `mathcity-latex.<name>` |
| LMFDB workflows | `<mathcity-pack-root>/subdomains/lmfdb/skills/<name>/` | `mathcity-lmfdb.<name>` |
| Pack development, hygiene, policy gates | `<mathcity-pack-root>/subdomains/dev/skills/<name>/` | `mathcity-dev.<name>` |

Default to the parent `skills/` directory only when the skill genuinely spans
domains.

## Pre-Flight

1. Run a wheel check on the proposed name and one-line purpose. If an existing
   skill, formula, command, MCP, or policy already covers the need, stop and
   adapt the existing surface instead of creating a duplicate.
2. Confirm the target directory is in the mathcity pack root and not in a
   materialized skill sink.
3. Identify any external dependency the skill needs: config files, network
   service, CLI, database, or MCP server.

## Author The Skill

Create:

```text
<destination>/SKILL.md
```

The file must contain YAML frontmatter:

```md
---
name: <name>
description: <when to use this skill, including trigger phrases>
---
```

Then write the body with:

- A clear task boundary.
- Required pre-flight checks before any expensive, external, or mutating step.
- Exact commands only where the command surface is known.
- Pack-relative references such as `skills/...` or `subdomains/...`; do not use
  machine-specific absolute paths.
- Supporting scripts or fixtures in the skill directory when needed.

If a dependency can be missing, fail early with:

```text
I'm sorry, I can't do that — <what is missing>.
Run /<setup-skill> or <specific setup action> to configure it.
<One sentence explaining what the dependency enables.>
```

## Update Indexes

Update `README-skills.md` in the pack root:

- Add one row in the correct section.
- Keep rows alphabetized by skill name within that section.
- Bump the section count and total count if the file carries counts.
- Use the same alias shown in the destination table above.

Update the relevant subdomain `README.md` only if it keeps a local skill table.

## Validate

Run from `<mathcity-pack-root>`:

```bash
# Skill file exists and has frontmatter
test -r <destination>/SKILL.md

# No machine-local paths or private workstation names
rg -n '(<absolute-user-path>|<private-checkout-root>|<personal-name>|local-only)' <destination>/SKILL.md && exit 1 || true

# Secret scan
gitleaks detect --no-git --source <destination>
```

Then validate pack exposure in a test city that imports this checkout:

```bash
cd <city-root>
gc import install
gc import check
```

If an outside-agent local skill sink is used in the operator's environment,
that sink is local context. Keep its setup instructions out of the shipped
skill unless the repository owner explicitly wants them documented here.

## Commit

Show the diff before committing:

```bash
cd <mathcity-pack-root>
git add <destination>/SKILL.md README-skills.md
git diff --cached
git commit -m "feat(mathcity): add <name> skill"
```

Push only to an authorized remote and branch.

## Hard Stops

- Do not create a duplicate skill when an existing one can be extended.
- Do not edit materialized skill copies as source of truth.
- Do not add personal paths, workstation names, or private workflow notes to
  shipped README or skill text.
- Do not claim exposure is working until `gc import install` and
  `gc import check` pass in a city importing the pack.
