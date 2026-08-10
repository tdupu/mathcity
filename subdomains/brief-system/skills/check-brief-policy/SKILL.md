---
name: check-brief-policy
description: >-
  Audit the current brief pipeline state against the brief-system POLICY.md
  (PP1.1 trinity, B2.x structure/ordering/resurface/freshness, B3.x decision
  records, N5 kill-switch, PP4.1 gate registry). Per-brief rule checks
  (L.x, E.x, T.x, D.x, S.x) happen at gate time, not here. Use when the
  user says "check brief policy", "run check-brief-policy", "is the pipeline
  compliant", "audit brief pipeline", "does the current pipeline violate any
  rules", or before a major brief pipeline change. Read-only: reports drift but
  never mutates bead state, files, or config (PP1.3). Returns approve / revise /
  defer. Companion to new-brief-policy (write path). Policy home:
  mathcity/subdomains/brief-system/POLICY.md.
---

# check-brief-policy

Audit the live brief pipeline state against
[POLICY.md](../../POLICY.md). Read the policy first — it is the
authoritative source. This skill checks WHAT IS, not what was planned.

> **Status guard (PP2.1):** If `POLICY.md` header shows `Status: Draft`,
> the policy is not yet enforceable. Run this audit informally and flag any
> section that is clearly non-compliant, but do NOT issue "revise" verdicts
> for rules that haven't been adopted. For sections previously adopted
> (the 2026-07-11 adopted version), treat those rules as binding; flag
> draft-revision additions as informational only. Return **defer** on the
> overall verdict until the revision is adopted.

---

## Scope

Check the following dimensions in order:

### 1. Trinity completeness (PP1.1)

- Is `mathcity/subdomains/brief-system/POLICY.md` present and at a known status?
- Does `check-brief-policy` skill exist and point to this policy?
- Does `new-brief-policy` skill exist?

```bash
ls <mathcity-pack-root>/subdomains/brief-system/POLICY.md
ls ~/.claude/skills/check-brief-policy
ls ~/.claude/skills/new-brief-policy
```

### 2. Brief pipeline structure (B2.4, B2.8)

Pipeline paths come from `paths.toml` and are RIG-RELATIVE (resolve against
the rig root; live pilot: `<city-root>/hecke`). Per B2.4/B2.8, canonical pile/stack
MEMBERSHIP is a bead query (open `type=decision` brief beads with no active
defer window — one-bead model); the filesystem layout audited here is an
implementation-detail cache regenerable from bead state — on disagreement
the bead store wins and the filesystem is repaired to match.

```bash
PATHS_TOML=<mathcity-pack-root>/assets/brief-pipeline/paths.toml
cat "$PATHS_TOML"
RIG_ROOT=<city-root>/hecke
PILE_DIR="$RIG_ROOT/$(grep '^pile ' "$PATHS_TOML" | awk -F'"' '{print $2}')"
STACK_DIR="$RIG_ROOT/$(grep '^stack ' "$PATHS_TOML" | awk -F'"' '{print $2}')"
ls "$PILE_DIR" "$STACK_DIR"
```

Check: pile = `<rig_root>/.beads/briefs/.pile/`, stack =
`<rig_root>/.beads/briefs/stack/`. Both must exist; neither may be an
ad-hoc location. Flag any filesystem/bead-store mismatch as cache drift to
regenerate — never treat the files as the source of truth.

### 3. Ordering (B2.5)

Examine `stack/manifest.jsonl`. Every entry must have an `unlock_count`
field. Verify that higher-count entries appear earlier in the stack (the
single-writer `brief-shuffle` should sort on promote).

```bash
cat <city-root>/.beads/briefs/stack/manifest.jsonl | \
  python3 -c "
import sys,json
rows = [json.loads(l) for l in sys.stdin if l.strip()]
print([(r.get('slug','?'), r.get('unlock_count',0)) for r in rows])
"
```

Flag any manifest where a lower-count brief appears before a higher-count
one — ordering violation (B2.5 drift).

### 4. No-resurface invariant (B2.3)

One-bead model: the brief bead IS the decision bead. Adjudicated = the brief
bead is CLOSED with verdict fields recorded on it; pending = the brief bead
is still open. The no-resurface check is therefore a simple state check:
no closed brief bead may appear in the stack or pile.

```bash
STACK_DIR=<city-root>/.beads/briefs/stack
for f in "$STACK_DIR"/*.md; do
  slug=$(basename "$f" .md)
  # derive bead ID from slug; check its status
  BEAD_ID=$(echo "$slug" | sed 's/-brief$//')   # rough extraction
  # bd show "$BEAD_ID" | grep -i 'status.*closed' && echo "VIOLATION: $slug"
done
```

### 5. No-brainer kill switch (N5)

Audit the two-level kill-switch hierarchy (POLICY.md N5, Adopted
2026-07-12). Auto-execute is the DEFAULT; a kill switch is a safety brake
that halts automation only when its flag file EXISTS and reads `false`
(absent or `true` → automation proceeds). Check city-wide first, then
rig-level; city-wide takes precedence:

```bash
RIG_ROOT=<city-root>/hecke
check_flag() {
  f="$1"; label="$2"
  if [ -f "$f" ] && [ "$(head -n 1 "$f" | tr -d '[:space:]')" = "false" ]; then
    echo "$label: ENGAGED (auto-execution halted) — $f reads false"
  elif [ -f "$f" ]; then
    echo "$label: RELEASED — $f present, reads: $(head -n 1 "$f")"
  else
    echo "$label: RELEASED (auto-execute active, the default) — $f absent"
  fi
}
check_flag <city-root>/.beads/auto_merge_enabled        "City-wide switch"
check_flag "$RIG_ROOT/.beads/auto_merge_enabled" "Rig-level switch"
```

Report each level as ENGAGED (halted) or RELEASED (auto-execute active,
the default). Engaging or releasing a switch requires explicit the human adjudicator
authorization recorded as a STANDALONE decision bead — a kill-switch
authorization record, which is its own bead and NOT a brief bead's verdict
(kill-switch decision beads are unaffected by the one-bead model). If
either switch is ENGAGED, verify the authorizing decision bead exists and
flag its absence.

Drift check: any lingering reference to the superseded opt-in
`ALLOW_NO_BRAINER_AUTO_EXECUTE` file (whose EXISTENCE used to enable
automation — inverted relative to N5) is drift; flag it:

```bash
grep -rn "ALLOW_NO_BRAINER" <mathcity-pack-root>/ | \
  grep -v 'subdomains/dev/docs/'   # dated planning docs are historical
```

This audit is read-only: report switch state; never create, edit, or
remove a kill-switch file.

### 6. Stack freshness (B2.7 / B2.9)

Check for briefs older than 7 days in the stack without a presented-at
record in `presentations/`:

```bash
ls -lt <city-root>/.beads/briefs/stack/*.md | head
# Compare with presentations/ directory mtime
ls <city-root>/.beads/briefs/presentations/ | head
```

Flag any brief with a stack entry and no corresponding `*-presented.toml`
that is more than 7 days old.

### 7. Decision record integrity (B3.x)

Per B2.2 (one-bead model) the verdict recorded ON the brief bead is the
canonical adjudication record: a brief bead closed with verdict fields
(verdict + authorizer + one-line rationale + date, plus
confidence/category for auto-executions) = adjudicated; an open brief bead
= pending. Verify state consistency: every closed brief bead carries its
verdict fields (a closed brief bead with no recorded verdict is a
B2.2/B3.8 violation), and no open brief bead claims a verdict. The files
checked here are redundancy channels. Check that `decisions.jsonl` (the
ledger at the briefs root) is non-empty if any briefs have been
adjudicated; the `decisions/` directory holds optional per-decision records
and may be empty:

```bash
bd list --type decision --all --json | head   # brief beads; closed = adjudicated
wc -l <city-root>/.beads/briefs/decisions.jsonl
ls <city-root>/.beads/briefs/decisions/ | wc -l
```

### 8. Gate registry join-layer (PP1.7, PP4.1)

The gate-inventory table in POLICY.md is **authoritative for gate
definitions**; `mathcity/assets/brief-pipeline/gates.toml` is the machine
join-layer and must match it. Mechanically diff the two — per gate:
(a) the gate exists on both sides, (b) `kind` matches, (c) the `rules`
field matches the table's rules column ("Enforces"). Any mismatch →
**revise**, citing PP1.7; the remediation is always "repair gates.toml to
match the policy table" — never the reverse.

```bash
python3 - <<'EOF'
import os, re, tomllib, pathlib
pack = pathlib.Path(os.environ.get("MATHCITY_PACK_ROOT", ".")).resolve()
policy = (pack / "subdomains/brief-system/POLICY.md").read_text()
reg = tomllib.loads((pack / "assets/brief-pipeline/gates.toml").read_text())

def expand(cell):
    # "T1, T3" -> [T1, T3]; "L1-L4" / "L1–L4" -> [L1, L2, L3, L4]
    out = []
    for part in re.split(r"[,;]", cell):
        part = part.strip()
        m = re.fullmatch(r"([A-Z]+)(\d+)[–-]\1?(\d+)", part)
        if m:
            out += [f"{m.group(1)}{i}" for i in range(int(m.group(2)), int(m.group(3)) + 1)]
        elif part:
            out.append(part)
    return sorted(out)

table = {}
for row in re.finditer(r"^\| (G\d+b?) \| ([\w-]+) \| (\w+) \| (.*?) \| ([^|]+) \|\s*$", policy, re.M):
    table[row.group(1)] = {"name": row.group(2), "kind": row.group(3), "rules": expand(row.group(5))}

toml_gates = {g["id"]: g for g in reg["gates"]}
drift = []
for gid in sorted(set(table) | set(toml_gates)):
    p, t = table.get(gid), toml_gates.get(gid)
    if p is None:
        drift.append(f"{gid}: in gates.toml but NOT in the POLICY.md table"); continue
    if t is None:
        drift.append(f"{gid}: in the POLICY.md table but NOT in gates.toml"); continue
    if t.get("name") != p["name"]:
        drift.append(f"{gid}: name {t.get('name')!r} != table {p['name']!r}")
    if t.get("kind") != p["kind"]:
        drift.append(f"{gid}: kind {t.get('kind')!r} != table {p['kind']!r}")
    if sorted(t.get("rules", [])) != p["rules"]:
        drift.append(f"{gid}: rules {sorted(t.get('rules', []))} != table {p['rules']}")
print("\n".join(drift) if drift else f"JOIN-LAYER CLEAN: {len(table)} gates match the policy table")
EOF
```

Also spot-check gate *purpose* wording (table "Demands" column vs the toml
`description`) for semantic drift — this is a judgment read, flagged the
same way — and confirm the **Profiles** paragraph in POLICY.md lists the
same gate sets as `[profiles.*]` in gates.toml. Report every mismatch as
revise citing PP1.7. This audit is read-only: never edit gates.toml or
POLICY.md here; the repair goes through `new-brief-policy`.

---

## Verdict

After each check, emit one of:
- **approve (section)** — no drift found
- **revise (section)** — specific rules violated; cite rule ID + one-line
  remediation per item
- **defer (section)** — a human call is needed; state the open question

Overall verdict = worst of per-section verdicts. **Never emit "reject"** —
that applies only to artifacts, not audits.

Report format:

```
## check-brief-policy audit — <date>

### Trinity (PP1.1)
verdict: approve | revise | defer
[items if revise/defer]

### Pipeline structure (B2.4, B2.8)
...

### Ordering (B2.5)
...

### No-resurface invariant (B2.3)
...

### No-brainer kill switch
...

### Stack freshness
...

### Decision records (B3.x)
...

### Gate registry join-layer (PP1.7, PP4.1)
...

## Overall: approve | revise | defer
[Summary of all revise/defer items]
```

This skill is **read-only**. Never run `bd close`, `bd update`, `git commit`,
or any state-mutating command during an audit. If you find a problem, describe
it and propose the fix — let the user or `new-brief-policy` apply it.
