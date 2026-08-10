---
name: update-README
description: Keep the mathcity pack family's READMEs and skill exposure in sync after ANY owned-pack change — the pack-dev sibling of improve-package-README (which serves Magma/Sage packages). Run after adding, moving, renaming, or removing a skill; after a policy (POLICY.md) change; after a subdomain is created; or whenever a README's skills table might have drifted from the skills/ tree. Trigger phrases: "update-README", "run update-README", "sync the pack READMEs", "readme drift check". Every skill-move or pack-change session ends by running this — README drift is a gate failure (POLICY.md P1.8 companion), not a cosmetic issue.
---

# update-README (mathcity-dev)

After any change to the owned pack family, bring documentation and exposure
back in sync. This is the pack-dev analogue of
`improve-package-README`: that skill keeps a *Magma/Sage package's* README
+ README-tests in sync with its intrinsics; this one keeps the *pack
family's* READMEs + exposure in sync with its skills.

Scope: the owned pack set (POLICY.md § Scope) — `mathcity/` and its
subdomain child packs.

## Procedure

For every pack root touched by the change (parent and/or subdomain):

1. **Skills table sync.** Diff the pack's `skills/` directory listing
   against its README's skills table. Every skill dir appears exactly once
   with a one-line purpose distilled from its frontmatter description;
   no table row names a skill that no longer exists. Renames (e.g.
   `improve-README` → `improve-package-README`) must not leave the old
   name anywhere in the README.
2. **Alias check.** The README states the correct materialization alias
   per ADR 0002: `mathcity.<skill>` for the parent, `mathcity-<sub>.<skill>`
   for a subdomain. Three-segment aliases (`mathcity.latex.*`) are
   aspirational and must not appear as if real.
3. **Exposure check (P1.8).** For each skill in the table, verify both
   exposure routes exist and resolve:
   ```bash
   sh <repos-root>/agent-skills/scripts/check-skill-symlinks.sh
   for l in <city-root>/.claude/skills/*; do [ -L "$l" ] && [ ! -e "$l" ] && echo "DANGLING: $l"; done
   ```
   plus one `ls` per new skill on its `<city-root>/.claude/skills/<alias>.<name>`
   entry.
4. **Cross-README consistency.** If a skill moved between pack roots,
   update BOTH READMEs (removed from one table, added to the other) in the
   same change. If the move changes a workflow another README narrates
   (e.g. the computing development loop), update that narrative too.
5. **Policy hooks.** If the change added/renamed a rule in
   `mathcity/subdomains/dev/POLICY.md`, confirm the skills that cite
   P-rules (`check-plan-hygiene`, `check-build-hygiene`) still cite
   existing rule IDs.
6. **Same-commit rule.** README updates land in the SAME commit as the
   change they document (mirrors upstream's "update the pack README in the
   same PR" convention in README-contributing.md).

## Output

Report per pack root: `in-sync` or the list of fixes applied
(table rows added/removed, aliases corrected, exposure links created).
Anything you cannot fix mechanically (a skill with no description
frontmatter, an ambiguous placement) → flag for the human adjudicator, don't guess.

## See also

- `improve-package-README` (mathcity-computing) — the Magma/Sage package
  sibling this skill is modeled on
- `skill-creator-math` (mathcity-dev) — creation procedure whose step this
  effectively re-runs
- `POLICY.md` P1.8 — the exposure rule this enforces
