# check-build-hygiene: corrected P1.12 and P1.13 mechanisms

**Date:** 2026-08-19
**Origin:** the 2026-08-19 `check-build-hygiene` audit returned **revise**. Two
of its own findings were artifacts of stale check mechanisms rather than real
drift, so the audit's own shell needed fixing before its verdict could be
trusted.

---

## Correction to the premise of this note

This note was commissioned on the understanding that the skill file lives
**outside** the mathcity repo — at `~/.claude/skills/check-build-hygiene/SKILL.md`
— and therefore could only be reported on, not modified.

**That is not the case, and the note would be wrong to say so.** The sink entry
is a symlink into this repository:

```
~/.claude/skills/check-build-hygiene
  -> ../../mathcity/subdomains/dev/skills/check-build-hygiene
```

which resolves to `<repos-root>/mathcity/subdomains/dev/skills/check-build-hygiene/SKILL.md`.
That path is tracked here (`git ls-files subdomains/dev/skills/check-build-hygiene/`
returns `SKILL.md`). Editing the tracked file *is* editing the skill the sink
serves; there is no second copy to keep in sync.

**Consequently the corrected shell below was applied directly** to
`subdomains/dev/skills/check-build-hygiene/SKILL.md` (section 7, the P1.12/P1.13
code fence) rather than only being described. This note remains the rationale
record and is still precise enough to re-apply verbatim.

---

## P1.13 — the canonical skills index moved

### Symptom

The audit reported **56 false failures** — every skill in the parent pack
reported as having no index row.

### Cause

The check greps *each pack's own* `README.md` for a row per skill directory:

```bash
# P1.13 — every skill dir has a README table row, no ghost rows        [BEFORE]
for pack in <mathcity-pack-root> <mathcity-pack-root>/subdomains/*; do
  [ -d "$pack/skills" ] || continue
  for s in "$pack"/skills/*/; do n=$(basename "$s")
    grep -q "\`$n\`" "$pack/README.md" 2>/dev/null || echo "NO README ROW: $pack -> $n"
  done
done
```

In the standalone layout the canonical index is a single top-level
`README-skills.md` covering the parent pack **and** every subdomain in
per-subdomain sections (`### Parent pack — mathcity/skills/ (56)`,
`### LMFDB — subdomains/lmfdb/skills/ (27)`, and so on). The parent pack's
`README.md` is no longer a skills index at all, so all 56 parent-pack skills
missed. Most subdomain `README.md` files have no skills table either — for
example `subdomains/brief-system/README.md` has no `## Skills` section — so the
same form under-reports there for any subdomain whose prose happens not to
mention a skill by name.

The `2>/dev/null` also silently swallowed the missing-index case, so a pack with
no index at all looked identical to a pack whose skills were all unindexed.

### Corrected shell

```bash
# P1.13 — every skill dir is indexed, no ghost rows                     [AFTER]
INDEX="<mathcity-pack-root>/README-skills.md"
[ -f "$INDEX" ] || echo "P1.13 FAIL: no canonical skills index at $INDEX"
known=$(ls -d <mathcity-pack-root>/skills/*/ \
  <mathcity-pack-root>/subdomains/*/skills/*/ 2>/dev/null \
  | xargs -n1 basename | sort -u)
printf '%s\n' "$known" | while read -r n; do
  [ -n "$n" ] || continue
  grep -q "\`$n\`" "$INDEX" || echo "NO INDEX ROW: $n"
done
grep -oE '^\| *`[a-z0-9][a-z0-9._-]*`' "$INDEX" | tr -d '|` ' | while read -r n; do
  [ -n "$n" ] || continue
  printf '%s\n' "$known" | grep -Fxq "$n" || echo "GHOST ROW: $INDEX -> $n"
done
```

Two details that matter:

- The ghost-row scan anchors on `^\|` so it reads only the **first cell** of a
  table row. Without the anchor it picks up every backticked token in the file —
  invocation names like `mathcity-lmfdb.configure-server`, formula names, and
  prose — and reports hundreds of spurious ghosts.
- Skill names are resolved **pack-wide**, not per-pack. `README-skills.md` lists
  subdomain skills whose directories live under `subdomains/*/skills/`, so a
  per-pack existence test would call every subdomain row a ghost.

### Result against the real index

```
TOTAL skill-dirs=134 missing=0 ghosts=0
```

134 = 56 parent-pack + 78 subdomain (brief-system 3, computing 9, dev 26,
latex 6, lmfdb 27, magma 2, proof-assist 5). All 56 top-level skills and every
subdomain skill are indexed, with zero ghost rows — so all 56 reported failures
were false.

---

## P1.12 — "conf" as a word, not as a dependency

### Symptom

Two hits, both false: `check-computing-policy` and `check-build-hygiene`.

### Cause

The check greps for the *word*:

```bash
# P1.12 — conf-reading skills must have a setup-* companion            [BEFORE]
grep -rl '\.conf\b\|data-generation\.conf\|conf.example' \
  <mathcity-pack-root>/*/skills/*/SKILL.md \
  <mathcity-pack-root>/subdomains/*/skills/*/SKILL.md 2>/dev/null \
  | grep -v '/setup-' | while read f; do
    pack=$(dirname $(dirname $(dirname "$f")))
    ls "$pack"/skills/setup-* >/dev/null 2>&1 || echo "NO SETUP SKILL: $f"
  done
```

The two hits are the only matching lines in those files:

- `subdomains/computing/skills/check-computing-policy/SKILL.md:302` —
  `> server process (e.g., priority.conf, queue files, server job registries).`
  A parenthetical example on a blockquote line. The skill reads no conf.
- `subdomains/dev/skills/check-build-hygiene/SKILL.md:177` — the `grep -rl` line
  **above**. The auditor contains its own search pattern, so it matches itself
  on every run. This is a self-reference bug, not drift.

Neither pack ships a conf, so neither can have a `setup-*` companion, so both
fail unconditionally and permanently.

### Corrected shell

The fix is to stop asking "does this file contain the string `conf`" and start
asking the question the rule is actually about: **does this skill depend on a
conf that the pack is responsible for providing?** A pack advertises that
responsibility by shipping `<pack>/assets/<name>.conf.example`.

```bash
# P1.12 — conf-reading skills must have a setup-* companion             [AFTER]
for pack in <mathcity-pack-root> <mathcity-pack-root>/subdomains/*; do
  [ -d "$pack/skills" ] || continue
  confs=$(ls "$pack"/assets/*.conf.example 2>/dev/null \
    | xargs -n1 basename 2>/dev/null | sed 's/\.example$//')
  [ -n "$confs" ] || continue
  for f in "$pack"/skills/*/SKILL.md; do
    [ -f "$f" ] || continue
    case "$f" in */setup-*/SKILL.md) continue ;; esac
    hit=0
    for c in $confs; do grep -qF "$c" "$f" && hit=1; done
    [ "$hit" -eq 1 ] || continue
    ls "$pack"/skills/setup-* >/dev/null 2>&1 \
      || echo "NO SETUP SKILL: $f"
  done
done
```

`[ -n "$confs" ] || continue` is what retires both false positives: the dev and
computing packs ship no `*.conf.example`, so they are never scanned, and the
auditor can no longer match its own pattern.

### Result, and a note on not over-correcting

```
P1.12 fails=0
```

The check still classifies **16** genuine conf-readers, all in `subdomains/lmfdb`
(which ships `lmfdb-server.conf.example` and `lmfdb-pipeline.conf.example`); they
pass because `subdomains/lmfdb/skills/setup-lmfdb-pipeline/` exists.

An earlier candidate fix — restrict the grep to fenced code blocks — also
produced zero false positives, but it was **rejected as unsafe**: it dropped
`subdomains/lmfdb/skills/pull-data-from-server/SKILL.md`, a real conf-reader
whose `lmfdb-server.conf` references all sit in frontmatter and prose rather
than inside a fence. That variant would have silently under-reported if the
lmfdb pack ever lost its setup skill. The shipped fix keeps all 16.

---

## Verification performed

Each corrected block was extracted and run standalone against this checkout
before being written into the skill. Both were checked for vacuity: P1.13 was
confirmed to enumerate 134 real skill directories rather than passing on an
empty set, and P1.12 was confirmed to still classify all 16 lmfdb conf-readers
rather than passing by scanning nothing.

Not re-run: the full `check-build-hygiene` audit end to end. This note covers
mechanisms 7 (P1.12/P1.13) only; the audit's other findings are untouched, and
whether the overall verdict moves off **revise** is not established here.
