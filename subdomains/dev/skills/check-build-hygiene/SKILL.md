---
name: check-build-hygiene
description: Audit the CURRENT live install — gc/bd binaries, source repos including standalone mathcity, pack imports, and skill sinks — against the Pack Portability & Boundary Policy (mathcity/subdomains/dev/POLICY.md). Use when the user says "check build hygiene", "run check-build-hygiene", "is my install reproducible", "can I share this setup", "audit the city against the policy", or before sharing the setup with a collaborator / rebuilding on another machine. Returns approve / revise / defer with a drift list and per-item remediation. Current-state counterpart of check-plan-hygiene (which gates plans/convoys before build).
---

# check-build-hygiene

Audit the live install against [POLICY.md](../../POLICY.md): could the human adjudicator
(or a collaborator) recreate what is running on this machine from pushed
source, and can upstream still be pulled?

**Read [POLICY.md](../../POLICY.md) in full first.** It is the source of
truth; this skill is its audit procedure. Rule definitions live there — do
not rely on memory or cached context. The numbered checks below provide the
*executable mechanisms* for audit areas that have shell-level verification
steps; they do NOT reproduce rule prose. For P-rules not covered by a
numbered check, apply them as judgment-call observations at the end of the
audit. Every finding cites the P-rule and comes with a remediation.

Read-only by default: this skill **reports** drift; it repairs only when
the user explicitly asks.

## Checks

**1. Binaries match source (P1.6).**

```bash
# gc against <repos-root>/gascity
go version -m "$(which gc)" | grep -E 'vcs\.(revision|modified)'
git -C <repos-root>/gascity rev-parse HEAD
# bd against <repos-root>/beads
go version -m "$(which bd)" | grep -E 'vcs\.(revision|modified)'
git -C <repos-root>/beads rev-parse HEAD
# stale shadows
which -a gc; which -a bd
```

Fail if: `vcs.modified=true`; `vcs.revision` ≠ the repo's HEAD; or an
unexpected `$PATH` location shadows the sanctioned install. Remediation:
the matching `update-*-from-source` skill (they rebuild, clean stale
binaries, and re-verify).

**2. Working trees clean, deviations declared (P1.6).**

```bash
for r in <repos-root>/gascity <repos-root>/beads <repos-root>/gascity-packs <repos-root>/mathcity; do
  echo "== $r"; git -C "$r" status --porcelain; cat "$r/.git/info/exclude"
done
```

Untracked/modified files that a build or the city depends on fail unless
declared (listed in `.git/info/exclude` AND encoded in the corresponding
update skill — precedent: the `go.work` beads-lockstep file in
`<repos-root>/gascity`). Uncommitted non-mathcity pack content in
`gascity-packs` or mathcity content in `mathcity` is work-in-progress, not a
violation — but flag it (P1.4: the city depends on it and it isn't pushed).

**3. Remote lockstep — upstream stays pullable (P1.7).**

```bash
git -C <repos-root>/gascity fetch origin fork -q &&
  git -C <repos-root>/gascity rev-parse main origin/main fork/main   # all equal
git -C <repos-root>/beads fetch origin -q &&
  git -C <repos-root>/beads rev-parse main origin/main               # equal
git -C <repos-root>/mathcity fetch origin -q &&
  git -C <repos-root>/mathcity rev-parse main origin/main            # equal
git -C <repos-root>/gascity-packs fetch upstream fork -q &&
  git -C <repos-root>/gascity-packs merge-base --is-ancestor upstream/main main \
  && echo "upstream contained" || echo "UPSTREAM NOT MERGED"
git -C <repos-root>/gascity-packs rev-list fork/main..main --count    # unpushed commits
```

gascity-packs is **fork-canonical** (gt-5cye): fork deliberately ahead of
upstream; upstream must be *contained in* main (merged), never mirrored
over it. Mathcity is a standalone source checkout backed by `tdupu/mathcity`;
`main` and `origin/main` must match for a reproducible city. Remediation: the
matching `update-*-from-source` skill, including `update-mathcity-from-source`;
never resolve divergence by force-push.

**3a. Upstream contribution hygiene — PRs and issues (P3.1, see `<city-root>/POLICY.md`).**

If the build under audit includes any recently created PR or issue targeting
`gastownhall/gascity`, `gastownhall/gascity-packs`, or `gastownhall/beads`:

- Every PR to those three repos must have been created via `mol-pr-from-issue`
  (pr-pipeline), NOT by a bare `gh pr create`. Check:
  ```bash
  gh pr list --repo gastownhall/gascity-packs --author @me --json title,body,url | head
  # Look for pipeline-generated body (linked bead, hygiene checklist)
  ```
  Hand-crafted PR bodies without the pipeline template → **revise** (P3.1).
  Reference: https://github.com/<github-owner>/gascity-packs/blob/main/pr-pipeline/README.md

- Every issue filed against those repos must have been created through the
  contributing skills, not `gh issue create` directly. A plain issue body
  missing contributing-skill metadata → flag for remediation (P3.4).
  Reference: https://github.com/<github-owner>/gascity-packs/tree/main/contributing

**4. Local-path imports are remote-backed (P1.4).**

```bash
grep -A1 'imports' <city-root>/city.toml | grep 'source'
grep -Hn 'source = ".*gascity-packs/mathcity' <city-root>/city.toml <city-root>/pack.toml \
  && echo "P1.4 FAIL: mathcity import uses stale gascity-packs path"
grep -Hn 'source = ".*repos/mathcity' <city-root>/city.toml <city-root>/pack.toml \
  || echo "P1.4 FAIL: no standalone mathcity import found"
```

For each local-path import target: its repo must be clean (check 2) and
its HEAD pushed to the canonical remote (check 3). A city standing on
unpushed content can't be recreated elsewhere. Mathcity imports specifically
must resolve to `<repos-root>/mathcity`; `<repos-root>/gascity-packs/mathcity`
is stale and fails P1.4 even if the directory still exists locally.

**5. Skill exposure hygiene (P1.8, P1.3).**

```bash
for l in <city-root>/.claude/skills/* <repos-root>/agent-skills/skills/*; do
  [ -L "$l" ] && [ ! -e "$l" ] && echo "DANGLING: $l -> $(readlink "$l")"
done
sh <repos-root>/agent-skills/scripts/check-skill-symlinks.sh
```

Findings: dangling symlinks (e.g. old `mathematics/*` targets → retarget
to `mathcity/`); real directories in agent-skills that duplicate pack
sources (fork drift — replace with a relative symlink); files hand-created
*inside* a materialized sink.

**6. Vendor trees untouched (P2.2).**

```bash
git -C <repos-root>/gascity-packs status --porcelain -- '*/vendor/' | head
```

Any modification under a `vendor/**` tree is a violation — no exceptions.

**7. Single source, no secrets, private data plane (P1.9–P1.11, P1.15).**

```bash
# P1.9 — duplicate real copies of pack skills in other repos
for s in <mathcity-pack-root>/skills/* <mathcity-pack-root>/subdomains/*/skills/*; do
  n=$(basename "$s")
  for r in <repos-root>/*/.claude/skills/$n <repos-root>/agent-skills/skills/$n; do
    [ -e "$r" ] && [ ! -L "$r" ] && echo "DUPLICATE REAL COPY: $r"
  done
done
# P1.10 — private values in pack content
gitleaks detect --no-git --source <mathcity-pack-root> | tail -1
grep -rInE '[a-z0-9_]+@[a-z0-9.-]+\.(edu|com|org|net)|ssh [a-z]+@|BEGIN.*KEY|/(Users|home)/[a-z]+/' <mathcity-pack-root> --include='*.md' --include='*.example' | grep -vi 'lmfdb.org\|example\.' | head
# P1.11 — bead sync targets: dedicated -dolt repos, verified private
for p in <city-root> <city-root>/*/; do [ -d "$p/.beads" ] || continue
  r=$(cd "$p" && bd config get sync.remote 2>/dev/null)
  case "$r" in *-dolt.git) ;; "") ;; *) echo "NON-DOLT SYNC TARGET: $p -> $r";; esac
done
# then per flagged/new target: gh repo view <github-owner>/<name>-dolt --json isPrivate (must be true)
# P1.15 — dolt remote name must be <github-owner>/<rig-slug>-dolt (exception: <city-root> → gascity-dolt)
# DoltHub normalizes underscores to hyphens — compare slug-normalized form
for p in <city-root> <city-root>/*/; do [ -d "$p/.beads" ] || continue
  r=$(cd "$p" && bd config get sync.remote 2>/dev/null)
  [ -z "$r" ] && continue
  rig=$(basename "$p")
  rig_slug="${rig//_/-}"   # normalize underscores to hyphens (DoltHub slug form)
  if [ "$p" = "$HOME/gt" ] || [ "$p" = "$HOME/gt/" ]; then
    expected="<github-owner>/gascity-dolt"
  else expected="<github-owner>/${rig_slug}-dolt"; fi
  r_base="${r%.git}"
  [ "$r_base" != "$expected" ] && echo "P1.15 WRONG NAME: $p -> sync.remote=$r (expected ${expected}.git)"
done
```

Duplicates without a tracked follow-up bead, any secret-scan hit, or a
non-`-dolt`/non-private sync target → **revise** (a P1.11 hit also HALTs
that rig's sync immediately).

```bash
# P1.12 — conf-reading skills must have a setup-* companion in the same pack
grep -rl '\.conf\b\|data-generation\.conf\|conf.example' \
  <mathcity-pack-root>/*/skills/*/SKILL.md \
  <mathcity-pack-root>/subdomains/*/skills/*/SKILL.md 2>/dev/null \
  | grep -v '/setup-' | while read f; do
    pack=$(dirname $(dirname $(dirname "$f")))
    ls "$pack"/skills/setup-* >/dev/null 2>&1 || echo "NO SETUP SKILL: $f"
  done
# P1.13 — every skill dir has a README table row, no ghost rows
for pack in <mathcity-pack-root> <mathcity-pack-root>/subdomains/*; do
  [ -d "$pack/skills" ] || continue
  for s in "$pack"/skills/*/; do n=$(basename "$s")
    grep -q "\`$n\`" "$pack/README.md" 2>/dev/null || echo "NO README ROW: $pack -> $n"
  done
done
```

A conf-reading skill with no setup companion, or a skill with no README
row → **revise**.

**8. Dependency pre-flight (P1.14).**

```bash
# For each conf-driven skill (including setup-* skills), look for the "I'm sorry" error pattern
for skill_dir in <mathcity-pack-root>/subdomains/lmfdb/skills/*/; do
  skill_name=$(basename "$skill_dir")
  skill_file="$skill_dir/SKILL.md"
  [ -f "$skill_file" ] || continue
  # Check all skills that reference a conf — setup-* skills included
  if grep -q 'conf\|CONF\|data-generation' "$skill_file"; then
    if ! grep -q "I'm sorry" "$skill_file"; then
      echo "P1.14 FAIL: $skill_name — conf-driven but no graceful error block"
    fi
  fi
done
```

Fail if any conf-driven skill (including `setup-*` skills — they also read or probe conf files)
is missing the `"I'm sorry, I can't do that"` error block.
Remediation: add the appropriate conf-discovery block with the P1.14 error format (server conf
→ `/configure-server`; pipeline conf → `/configure-database`).

**9. Repo-accessible skills (P1.16).**

For each mathcity skill that was adopted from a project repo (hecke, homog,
diff-alg, etc.), check whether that repo still has a non-mathcity-dependent
copy in its own `.claude/skills/` (real copy or repo-committed symlink that
does not point into `<mathcity-pack-root>`):

```bash
# List mathcity-adopted skills that came from project repos (convention: check
# agent-skills and then each known project repo for symlinks pointing into mathcity)
for repo in <repos-root>/hecke <repos-root>/homog <repos-root>/diff_alg_public; do
  [ -d "$repo/.claude/skills" ] || continue
  for l in "$repo/.claude/skills/"*; do
    [ -L "$l" ] || continue
    target=$(readlink -f "$l" 2>/dev/null)
    case "$target" in */mathcity/*)
      echo "MATHCITY-ONLY: $l -> $target (collaborators need a non-mathcity copy)";;
    esac
  done
done
```

For each hit: is every known collaborator of that repo confirmed to have
mathcity installed? If not, the symlink-only arrangement violates P1.16 —
the repo must also contain a real copy (or a symlink to a non-mathcity
location) so collaborators can run the skill without the human adjudicator's pack config.

Findings: symlinks in project repos that point exclusively into mathcity, where
no collaborator-facing fallback exists → **revise** (each listed with the repo,
the skill name, and the collaborators who would lose access).

**10. Replay litmus (P1.1) — judgment call.**

Given checks 1–9, answer: "if I `gc init` a scratch city and replay only
the declared imports on a fresh machine, do I get this city?" List every
piece of load-bearing state that would be missing (hand-placed sink
symlinks are fine — they're encoded in `skill-creator-math`; an
undocumented manual step is not).

**11. Workspace context files: live CLI only (P5.2).**

Scoped files: `<city-root>/AGENTS.md`, `<city-root>/CONTEXT.md`, `<city-root>/CLAUDE.md` (if
separate), and any AGENTS.md in any rig the workspace owns.

(a) Command-block probe:

```bash
# Extract all command blocks from scoped files and check each verb
for f in <city-root>/AGENTS.md <city-root>/CONTEXT.md; do
  grep -E '^\s+(gc|bd|gt|gt\s)' "$f" | grep -v '^\s*#' | while read -r line; do
    verb=$(echo "$line" | awk '{print $1, $2}')
    # Flag any gt verb (disabled CLI)
    echo "$line" | grep -qE '^\s*gt ' && echo "P5.2 FAIL dead CLI: $f: $line"
  done
done
```

(b) Identity assertion probe:

```bash
# Check if any gastown.* identity is asserted as live
grep -n 'gastown\.' <city-root>/AGENTS.md <city-root>/CONTEXT.md | grep -v '#.*historical\|HISTORICAL\|removed\|dead\|was formerly' \
  && echo "P5.2: check if any gastown.* claim contradicts gc agent list"
gc agent list 2>/dev/null | grep gastown && echo "P5.2 FAIL: live gastown agents found"
```

(c) Path probe:

```bash
grep -oE '<repos-root>/[a-z0-9_-]+' <city-root>/AGENTS.md <city-root>/CONTEXT.md | sort -u | while read p; do
  eval [ -d "$p" ] || echo "P5.2 FAIL broken path: $p"
done
```

(d) Inside/outside distinction present:

```bash
grep -q 'outside agent\|inside agent\|GC agent\|GASCITY AGENT' <city-root>/AGENTS.md \
  || echo "P5.2 FAIL: no inside/outside agent distinction in AGENTS.md"
```

Findings → revise. Add to the Non-negotiable checklist: "No dead CLI verbs
(gt) or broken pack paths in workspace context files — P5.2."

**12. Catch-all — remaining P-rules (POLICY.md §Pillars 1–5).**

After running checks 1–11, re-read POLICY.md and enumerate any P-rule not
yet covered by a numbered check above. Apply each as a judgment-call
observation: does the live install state violate that rule? Flag violations
with the P-rule ID and a one-line remediation. This step is how new rules
added to POLICY.md automatically enter the audit without requiring a skill
update.

## Output format

```
check-build-hygiene — <date>

Verdict: approve | revise | defer

Drift list (revise only):
  <P-rule> — <what drifted, file/path> — <remediation, one line>

Defer items:
  <anything needing a human call, with the question stated>
```

Verdict semantics: **approve** = current state compliant; **revise** =
drift found, each item fixable and listed with remediation; **defer** =
a human call is needed. (Per POLICY.md, **reject** does not apply to
audits.)
