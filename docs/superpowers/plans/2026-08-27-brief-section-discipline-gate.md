# Plan — G17 brief section discipline (`mc-qbs6j`, P1)

**Execution context (P3.5).** All work happens in `~/gt/mathcity`, which is
this side's lane, on branch `work/mc-qbs6j-brief-s1-gate`. Nothing is written
inside `~/repos/*` (LP1). No upstream PR is involved: mathcity is an owned
set, so P3.1/P3.2 do not fire. No `Co-Authored-By` trailer (P5.5).

## The defect, measured

`mc-67snh` carried every mandated heading and still hid its findings. Measured
on the live bead body (6022 chars, 9 headings):

| Misfiled item | Filed under | Belongs in |
| --- | --- | --- |
| `graphroute.go:562-588` | `## §1 — What is being decided` | §6 |
| `runtime.go:297` | `## §1` | §6 |
| `#2763` (twice) | `## §1` | §6 |
| `~35`, `24 of 25` | `## §1` | §6 |
| `kindsets.go:113-118` | the SECOND `## §4` | §6 |

Adjudicated REVISE 18:16:09Z, reason *"We need evidence. We need a
recommendation"* — both present, both misfiled. Nine minutes later `mc-wg331`
approved one of the directions this brief was still deciding; that approval was
refuted at source and rejected. The cascade traces to evidence under the wrong
heading.

## The three conditions

1. **C1 — §1 carries no evidence.** A `file.ext:NNN` citation, a commit sha, an
   issue reference, or a measured count inside §1 is a fail. §1 states the
   question.
2. **C2 — section numbers are unique.** Two `## §4` headings in one body is a
   fail.
3. **C3 — §2 is a recommendation.** Present, non-empty, not a null answer
   (`None recorded`, `NOT SUPPLIED`, `TBD`, …), and naming a decision verb.

Each is observably falsifiable against `mc-67snh` as filed, which is why that
brief is the fixture rather than a synthetic body (P6.2 at construction).

## What already exists (P1.20 wheel check)

Surveyed `docs/SURFACE-STATUS.md`, `docs/superpowers/plans/`, `formulas/`,
`skills/`, `assets/scripts/checks/`, and the mctl core.

| Existing | Reused how |
| --- | --- |
| `mctl_core/briefs.py::parse_brief_sections` | The section parser. Already fence-aware, already classifies `§N` headings `explicit` vs `heading` vs `unmapped`. Not reimplemented. |
| `assets/brief-pipeline/required-sections.toml` + `mctl_core/structure.py` | The one-rule-one-place precedent (#169). The new rule lands in the same module, reading a sibling data file. |
| `validate_brief_input` (`briefs.py`) | The creation-time refusal seam every brief creation path funnels through — including `decisions_to_briefs`, which is how `mc-67snh` entered. |
| `assets/brief-pipeline/gates.toml` + brief-system `POLICY.md` gate-inventory | Gate registration (PP4.1: the table is authoritative, `gates.toml` must match). |
| `tests/mctl/test_briefs_create_structural_validation.py` | The test shape, including its positive control. |

Nothing existing checks section discipline. `parse_decision_options` *works
around* the duplicate §4 (`seen_labels` de-dup) instead of refusing it.

## Enforcement point

`validate_brief_input`, i.e. brief creation. Chosen over the drain-time shell
gate because that is where `mc-67snh` entered, and because #169 already paid
for the CT13.4 lesson: a refusal at shuffle time reaches an author who was
told the write succeeded.

## Blast radius, measured before building

Prototype run over the 178 live brief markdown files in `~/gt/.beads/briefs`,
`~/gt/mathcity/.beads/briefs`, `~/gt/hecke/.beads/briefs`,
`~/gt/gascity-packs/.beads/briefs`:

- 119 in scope (body carries an explicit `§1` heading); 59 out of scope
  (compact-form and unnumbered bodies).
- **29 pass, 90 fail** — the gate discriminates on real artifacts in both
  directions.
- C1 67, C2 59, C3 33.
- 49 of the 59 C2 failures are one generator defect: `decisions_to_briefs`
  composes `## §4 — Alternatives named` and then appends `## §4 — Options`.
  All 11 in-scope `decisions_to_briefs` briefs fail C2; 7 of 11 also fail C1.

So the gate ships with the generator fix, or it bricks the main automated
producer on its first call.

**What shipped, re-measured against the built gate:** 119 in scope, 29 pass,
**81 refused on C1/C2**, 9 advisory-only (C3 and nothing else). Per condition:
C1 108 findings, C2 60, C3 33.

## Steps

1. `assets/brief-pipeline/section-discipline.toml` — evidence classes, §2
   null-answer patterns, §2 decision-verb vocabulary, as data.
2. `mctl_core/structure.py` — `section_discipline_violations(sections)`, taking
   already-parsed sections so `structure.py` keeps no import of `briefs.py`.
3. `briefs.py::validate_brief_input` — refuse with `MBRF037` (C1) and
   `MBRF038` (C2), each naming the offending text and a remedy. `MBRF039` (C3)
   is reported by `effects.py::plan_create_brief` as a WARN advisory: see the
   conflict below. Codes allocated from `assets/mctl/diagnostics.toml`; the
   first draft of this plan reused `MBRF042`, which is already live with a
   different meaning (`check-plan-hygiene` caught it, P5.4).
4. `mcp_server.py` / `decisions.py` — stop emitting two `§4` headings.
5. `assets/scripts/checks/brief-section-discipline.sh` — run the same rule over
   a brief file, for corpus sweeps and the drain layer. One implementation.
6. Register **G17 section-discipline** in the `POLICY.md` gate-inventory table
   and in `gates.toml`, in that order (PP4.1).
7. `tests/mctl/test_brief_section_discipline.py` — `mc-67snh` as the failing
   fixture, a real passing brief as the positive control, plus a corpus test
   asserting both outcomes occur.

## P3.6 — documentation

`improve-documentation` applies: the gate-inventory table in
`subdomains/brief-system/POLICY.md` and the rationale header of the new data
file are the documentation surface, and both are edited by step 1/6 above.
No README in this pack describes individual gates, so no README change is
owed — recorded here rather than left silent (D2/G15 shape).

## The conflict C3 exposed

B1.9(c) says §2 must name a recommended action. #194 says `decisions_to_briefs`
deposits a transported decision UNDECIDED and must not invent a recommendation
nobody gave; its composer's §2 reads *"None recorded…"*, which is exactly the
null answer C3 refuses. Both are adopted rules and they cannot both hold.

Measured: making C3 fatal turns **9 tests red** across
`test_decisions_to_briefs_tool.py`, `test_decision_options_authoring.py` and
`test_no_brainer_carrier.py`; four assert #194 directly. So C3 ships as a
declared WARN advisory — computed, printed by the check script, surfaced on the
creation result, never silent — and the adjudication is `mc-nhz1n`. `mc-67snh`
is refused on C1 and C2 regardless of how that lands.

Rejected: rewording the composer's §2 into something verb-bearing. `mc-67snh`'s
§2 already said "None recorded. This brief transports a question to be
decided"; a reword to "Defer to the adjudicator" would pass C3 while changing
nothing about the brief Taylor sent back. A gate a machine can satisfy by
rephrasing is not a gate.

## Producers this gate refuses (P4.2)

Four paths reach `plan_create_brief`, and the refusal sits on all of them:

| Producer | Body comes from | C1/C2 exposure |
| --- | --- | --- |
| `mctl briefs create` (`cli.py:610`) | caller-authored | the author fixes it |
| `briefs_create` MCP tool (`mcp_server.py:1169`) | caller-authored | the author fixes it |
| `commission_brief` (`effects.py:883`) | caller-authored | the author fixes it |
| `decisions_to_briefs` (`mcp_server.py:1091`) | machine-composed | C2 **fixed here**; C1 tracked as `mc-rfsxy` |

## Out of scope — workarounds, with beads (P1.17)

- The dashboard half (surface §2 and §6 above §1 on the brief card). Separate,
  rides with the briefs-dashboard work.
- **WORKAROUND:** the `decisions_to_briefs` composer still files the whole
  decision statement under §1, so an evidence-bearing statement is refused on
  C1 and the caller must split it by hand. Bead **`mc-rfsxy`**.
- **WORKAROUND:** C3 does not refuse. Bead **`mc-nhz1n`**.

## Reach beyond this checkout

`~/gt/city.toml` and `~/gt/pack.toml` import mathcity from
`<repos-root>/mathcity`, not from `~/gt/mathcity`. G17 does not take
effect in the running city until that checkout advances, which under LP1 routes
through BART. `unknown`: whether anything else pins an older mathcity.
