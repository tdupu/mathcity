# Fleet and checker measurements, policy-derived — 2026-09-27

A measurement record, not a set of decisions. Every number below was obtained
first-hand and is re-runnable from the command given; nothing is inferred from a
prior session's notes. Written because these took real work to obtain and three
of them contradict what the tracker currently records.

Companion to the same day's commits (`65841a7`..`c8a8870`) and to two issues
filed through the typed surface (#284, #285).

## Method

Each claim below was measured, not read off an earlier report. Where a finding
contradicts an existing issue or an in-tree comment, the contradiction is stated
and the prior text corrected in place rather than left standing. Three of these
findings are corrections to **my own** earlier claims in the same session; those
are marked, because a measurement record whose errors are silently dropped is
worth less than one that shows which way it moved.

---

## 1. The dolt remote is malformed fleet-wide — 7 of 7 stores

```bash
for d in ~/repos/{mathcity,hecke,gascity-packs} ~/gt ~/gt/{mathcity,hecke,gascity-packs}; do
  (cd "$d" && bd dolt remote list | awk '/^origin/{print $2}')
done
```

Every store returns a URL of the form:

```
git+ssh://git@github.com/./tdupu/<repo>-dolt.git
                         ^^^
```

GitHub rejects it: `./tdupu/mathcity-dolt is not a valid repository name`. The
normalized URL resolves and returns 4 refs. **All four targets exist and are
PRIVATE** (`gh repo view <t> --json isPrivate`), so P1.11's verified-private
condition is satisfiable; only the path is wrong.

Two upstream beads let it through:

- `beads/internal/doltremote/remote.go:57-60` converts SCP-style `git@host:path`
  to `git+ssh://git@host/path` by concatenation, carrying a `./` prefix verbatim.
- `beads/internal/remotecache/url.go:150` validates `git+ssh` by checking only
  that the HOST is non-empty. `github.com` is non-empty, so the URL validates, is
  stored, and fails at the transport — where the error names the repository, not
  the config.

Gate added: `assets/scripts/checks/dolt-remote-check.py` (exit 0/1/2). It reads
the remote from `bd dolt remote list`, **never** from `config.yaml` — the two
disagree, and correcting the YAML on the laptop left bd still using the old
value, because the remote is registered inside the Dolt database.

## 2. That URL caused a schema fork

```bash
for d in ~/repos/mathcity ~/repos/hecke ~/repos/gascity-packs ~/gt ~/gt/mathcity; do
  (cd "$d" && bd list --readonly --limit 1 2>&1 | grep -oE 'database is at v[0-9]+, binary expects v[0-9]+')
done
```

| store | schema |
| --- | --- |
| `~/repos/mathcity` | **v64** |
| `~/repos/hecke`, `~/repos/gascity-packs`, `~/gt`, `~/gt/mathcity` | **v67** |
| remote `tdupu/mathcity-dolt` | **v64** |

bd refuses to auto-migrate a *remote-backed* database, and the discriminator is
**whether the remote is registered inside the Dolt DB** — not whether
`config.yaml` names one. Stores whose remote was never registered were not
recognised as remote-backed, so bd migrated them to v67, forking them from their
v64 remotes. The one store bd protected is the only one still able to agree with
its remote.

So the fork bd warns about **has already happened**, on four stores, silently, as
a consequence of finding 1.

**Not reconciled deliberately.** Standardising on v67 requires migrating the
remote, after which kolchin's bd cannot open its own store; standardising on v64
forward-drifts four stores including HQ, which bd refuses to open. Either choice
breaks something and one of them breaks the running city.

## 3. `ma` is kolchin's database, and it has no skew

```
~/repos/mathcity   Database: mc   (embedded)       <- the v64/v67 skew is HERE
~/gt/mathcity      Database: mc   (per-project)
kolchin            Database: ma   (per-project), reads clean
```

**Correction to my own earlier claim in this session.** I had reported P1.11 as
blocked on the schema fork. It is not: `ma` lives only on kolchin, kolchin's
store and binary agree, and its remote fix is two commands. The laptop's skew is
a separate problem on a different database.

## 4. A pool capped in `city.toml` cannot be raised by an import

Measured on a throwaway city — a base pack owning an agent at
`max_active_sessions = 0`, a consumer pack importing and patching it:

```
pack-level patch only            -> gc config show: max_active_sessions = 4
pack-level 4 + city-level 0      -> gc config show: max_active_sessions = 0
```

pack-spec §2.6's order is (2) pack-level patches, then (4) city-level patches, so
city-level wins. **kolchin's five zero caps are `city.toml` `[[patches.agent]]`
entries**, i.e. step 4.

Two consequences:

- **A pack-level patch DOES reach another pack's agent.**
  `orders/on-merge-brief-record.toml` recorded the opposite ("only pack-local
  agents can be patched at pack-level per pack-spec §2.6"). That was wrong and is
  corrected in place, with the fixture described.
- **There is no import-shaped way to lift those caps.** Making them
  import-governed requires removing the `city.toml` patches, which is the
  hand-edit P1.2 forbids.

**Correction to my own earlier claim.** I had listed the pool ceilings among
things P1.2 made "derivable". I asserted that mechanism without testing it; it is
measured false.

## 5. `review_gate` has no bead representation

```bash
cd ~/gt/mathcity && bd list --all --limit 0 --json | \
  python3 -c "…count metadata keys…"
```

**`review_gate` appears in 0 of 2,364 bead metadata records**, against 20 files
at `pending`, 16 `approved`, 2 `review-failed`, 2 `escalation-self-checked`.

B2.8a scopes the bead to "identity, status, timestamps and labels, and little
else". A pre-adjudication field is none of those, so a bead-first repair would
resolve `review_gate` by **deleting** it. `briefs_review_gate` therefore writes
frontmatter and no bead.

**A rule declaring this (B2.8b) was drafted and withdrawn.** PP1.4 reserves rule
changes for a `new-X-policy` proposal approved by the human adjudicator; I had
hand-edited the Adopted policy, which is a violation "even for typo fixes". The
proposal text stands ready; the code cites only Adopted rules (B2.8a, B2.11,
B2.14).

## 6. MBRF005 has a 1-in-3 true-positive rate, and cannot be narrowed

`briefs_doctor` against `~/gt/mathcity`: 28 diagnostics — MBRF004 ×10,
MBRF002 ×6, MBRF001 ×5, MBRF054 ×4, MBRF005 ×3.

| code | verdict |
| --- | --- |
| **MBRF021** | **verified** — 0 firings, down from the reported "66 of 70" |
| **MBRF004** | **verified** — all 10 are `type=decision`; B2.1a makes silence a true positive |
| **MBRF005** | **unverified** — 2 of 3 are legitimate no-verdict closes |

B2.2's check is a biconditional on *adjudicated*; a withdrawn or superseded brief
was never adjudicated, so B2.2 never binds it. The checker tests
`closed ∧ ¬verdict`, a strictly wider set.

**It cannot be narrowed with what exists.** The only signal is prose in
`close_reason`, and B2.1a forbids exactly that for the sibling code ("Silence is
never a declaration… only a structured marker the author had to write on
purpose"). All three beads are `status: closed` with no labels; the two
non-violations share a `commission_incomplete` metadata set and the genuine
violation carries no metadata at all. Filed as **#285** per P7.3.

## 7. Two latent defects found by reading, not by a failure

- **`_update_simple_toml` destroyed nested tables, silently.** A `[continuation]`
  section became a stringified Python repr with no error raised. Since
  `brief-decision-dispatch` keys the approve path on that block, one mctl
  adjudication of a commission brief broke its own approve path. Fixed
  (`c10a51b`); the absence of a *writer* for that block is **#284**.
- **An unknown `GithubWrite` kind filed an issue.** The applier's dispatch was
  `if kind == "edit" … else: create_issue(...)`, so any future kind without a
  branch would post to GitHub. #253 proposes two such kinds. Fixed (`c8a8870`)
  with the known-kind set pinned by a test.

## 8. The mctl suite leaks one dolt sql-server per full run

`pgrep -fl 'dolt sql-server'` after `pytest tests/mctl/` names the producer in
its own config path: `tests/mctl/test_dashboard_rig_switcher_briefs.py`. One per
run, deterministic (observed as `pytest-23` and again as `pytest-59`). Tracked in
#269, which is QUIMBY's; recorded here only because it makes full-suite runs
costly and is the reason test selections in this day's commits are scoped.

---

## The `ma` repair, as commands (re-verified 2026-09-29)

`assets/scripts/dolt-remote-repair.py` automates this, but **it is not on
kolchin**: kolchin's checkout sits on `fix/lean-gate-check-paths` at `247560a`
while these commits are on `main`, and the script is absent from its pack cache
too. Getting it there is itself a write to kolchin. So the sequence is recorded
here in full, for whoever has access:

```bash
# on kolchin, in ~/repos/mathcity
# 1. the file half — drop the "/." (config.yaml is gitignored, so it cannot
#    arrive through the code repo; P1.10 keeps machine values out of pack content)
#    .beads/config.yaml:13   remote: "git+ssh://git@github.com/tdupu/mathcity-dolt.git"

# 2. the database half — kolchin's Dolt server has NO remote registered
#    ("Remotes: (none)"), which is why bd falls back to config.yaml today.
bd dolt remote remove origin   # harmless if absent
bd dolt remote add origin 'git+ssh://git@github.com/tdupu/mathcity-dolt.git'

# 3. verify
bd dolt show                   # expect origin, with no /./
bd dolt pull && bd dolt push
```

**The target was verified from the laptop on 2026-09-27 and re-verified
2026-09-29:** `tdupu/mathcity-dolt` resolves (4 refs) and `isPrivate: true`, so
P1.11's verified-private condition holds before the write rather than after.

**Both commands should succeed on kolchin**, because kolchin has no schema skew
(finding 3) — the same two commands are refused on `~/repos/mathcity`, whose
`mc` store is blocked at v64/v67. That asymmetry is the whole reason this is a
kolchin-side repair and not a laptop-side one.

---

## What is blocked, and on what

| item | blocked on |
| --- | --- |
| P1.11 — the `ma` remote reaching its target | **writes to kolchin**, denied by the permission classifier |
| P1.2 — pools off zero via `[imports.*]` | **impossible as worded** (finding 4); needs a different approach |
| Dispatching tracker work to the city | P1.2, then the pools |
| B2.8b | **a `new-brief-policy` proposal approved by the human adjudicator** (PP1.4) |
| Schema fork reconciliation | a fleet decision; either direction breaks something (finding 2) |

None of these is blocked on further investigation.
