# Skills mirrored from agent-skills

Parent: [../README-skills.md](../README-skills.md)

Some skills are maintained in the owner's private `agent-skills` repository and
mirrored here so that papers can cite a public, version-pinned copy. The
private repository stays the working source; the copy here is a deliberate
mirror (owner's direction, 2026-10-04), not an adoption under P1.9 of
[subdomains/dev/POLICY.md](../subdomains/dev/POLICY.md). Do not replace the
source copies with symlinks to these.

To cite one of these skills, cite this repository at a commit that contains it.
The table records which source commit each mirror was taken from.

## Mirrored skills

Source commit: `agent-skills` `76230b62375beedaaf4cc7bf2f058f2bf357c409`
(2026-10-04). "Identical" means the git tree of the skill directory here equals
the tree of `skills/<name>` at that commit.

| Skill | Path here | Relation to source |
| --- | --- | --- |
| `frontier-dump` | `skills/frontier-dump` | identical |
| `domain-modeling` | `skills/domain-modeling` | `SKILL.md` identical; adds upstream `ADR-FORMAT.md` (see [LICENSES](../LICENSES/README.md)) |
| `adjust-behavior` | `subdomains/dev/skills/adjust-behavior` | identical |
| `behavior-repro` | `subdomains/dev/skills/behavior-repro` | identical |
| `behavior-cause` | `subdomains/dev/skills/behavior-cause` | identical |
| `behavior-verify` | `subdomains/dev/skills/behavior-verify` | identical |
| `using-leanpowers` | `subdomains/lean/skills/using-leanpowers` | identical |
| `lean-workflow` and the 24 `lean-*` leaves | `subdomains/lean/skills/<name>` | identical |

The lean family was first published here in `8f38fd6` (2026-09-23); the table
records that it still matches the source commit above. `lean-frontier-dump`
exists only here.

`domain-modeling` is adapted from
[mattpocock/skills](https://github.com/mattpocock/skills) (MIT); its notice is
retained in [LICENSES/](../LICENSES/README.md). The other skills are original.

## Checking for drift

A mirror drifts when the source changes. With both checkouts side by side:

```bash
git -C agent-skills rev-parse <commit>:skills/<name>
git -C mathcity rev-parse HEAD:<path here>
```

Equal hashes mean an identical tree. To refresh a mirror, copy the source
directory at a committed state, rerun the P1.10 scrub, and update the source
commit above in the same commit.
