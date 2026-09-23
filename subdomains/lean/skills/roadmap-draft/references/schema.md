# The roadmap representation — specification

Parent: [create-roadmap](../SKILL.md). Incident catalogue:
[failure-modes.md](failure-modes.md).

`math-roadmap:v1`. This is a **specification**: everything below is pinned
tightly enough to implement without guessing, and two implementations that follow
it must agree on every file. An earlier version described the representation
instead of specifying it, and a review found eight blocking gaps — no evidence
vocabulary, no transition table, no hash algorithm, no id regex. Each is closed
here.

The prover-flavoured names in `EvidenceKind` and `FormalStatus` are neutral in
this spec; the mapping to the reference implementation's Lean-specific spellings
is in §11.

## 1. Canonical form and revision

JSON is canonical. A rendered view is regenerated from it; nothing parses the view
back. A **builder program** constructs the JSON through typed records and ships
the validator of §10. Never hand-edit the JSON.

`revision` is computed as:

```
body    := the whole document with revision set to the empty string ""
          (the key is present, its value is "")
strings := every string value normalised to Unicode NFC, unconditionally
serial  := JSON with sort_keys=true, separators=(",", ":"), ensure_ascii=true
revision:= lowercase hex SHA-256 of serial encoded UTF-8, all 64 characters
```

NFC is unconditional. Making it content-dependent lets two implementers disagree
on the same file.

Pins in prose cite the first 12 hex characters; comparisons are on all 64.
Refreshing pins by search-and-replace is forbidden: a live pin and a historical
record are indistinguishable to a regex (FM-24).

## 2. Objects and fields

`req` = required. Unknown keys are an error, not a silent drop (§10).

**Roadmap**: `schema` str req · `revision` str req · `name` str req · `slug` str
req · `repos` map[str,str] req · `layers` list req · `targets` list req · `edges`
list req · `tex_metadata_allowed` bool req · `input_manifest` str|null ·
`notes` str.

**Layer**: `id` str req · `title` str req · `purpose` str req · `entry` str ·
`exit` str.

**Target**: `id` str req · `title` str req · `layer` str req · `kind` str req ·
`statement` str req · `inputs` list[str] · `outputs` list[str] ·
`public_imports` list[str] · `checks` list · `assumptions` list · `status` str
req · `formal_status` str req · `strength` str req · `strength_witness` str ·
`grade` str req · `grade_reason` str · `evidence` list · `source_refs` list[str]
· `ledger_ids` list[str] · `notes` str.

**Check**: `id` str req · `description` str req · `command` str · `expects` str ·
`kind` str req · `fidelity_source` str — required when `kind == "fidelity"`,
naming the source statement compared against; empty otherwise.

**Evidence**: `kind` str req · `locator` object req · `establishes` str req ·
`does_not_establish` str req (§10 enforces non-empty) · `conditional_on`
list[str] · `verified_by` str|null · `date` str|null.

**Locator**: `repo` str|null · `path` str req · `anchor` str|null · `sha256`
str|null · `repo_head` str|null. A locator without `sha256` pins a commit, not
bytes; §10 counts and reports how many evidence locators are byte-pinned.

**Assumption**: `id` str req · `text` str req · `kind` str req ·
`blocks_status` bool req · `clears_when` str · `upstream` str|null.

**Edge**: `src` str req · `type` str req · `dst` str req · `citation` str ·
`note` str. Edges have no id; `(src, type, dst)` is the key.

### Id grammar

```
target id  ^[A-Z]{2,4}-(\d{2})\.[A-Za-z][A-Za-z0-9]*$
```

The prefix is constant across one roadmap. The two digits are the **layer
decade**: a target in the `n`-th layer (0-based) has `NN` in `[10n, 10n+9]`, so
layer 0 is `00`–`09`, layer 1 is `10`–`19`. §10 checks that a target's decade
matches its `layer` field — otherwise the id and the field can disagree silently.

Layer, Check and Assumption ids encode no layer; they match
`^[A-Za-z][A-Za-z0-9_-]*$` and are unique within their parent. Target ids are
unique across the roadmap.

Target ids are **append-only**: never reused, never renumbered. A single-file
validator cannot detect reuse across revisions, so this is an authoring
discipline, not an enforced property — see §10's honesty note.

## 3. Two independent status axes

Conflating them is the failure the split prevents. A written theorem can be
`established` with `formal_status: absent`; a compiled declaration can be
`proved-conditional` while its claim is only `candidate`.

**`status`** (ClaimStatus), 9 values: `candidate` · `supported` ·
`formalization-ready` · `established` · `refuted` · `retracted` · `blocked` ·
`superseded` · `out-of-scope`.

**`formal_status`** (FormalStatus), 8 values: `absent` · `stated` · `assumed` ·
`restated` · `proved-conditional` · `proved-unconditional` ·
`proved-not-wired` · `refuted-formally`.

`restated` (re-phrased an assumption, reduced nothing) and `proved-not-wired`
(correct mathematics nothing consumes) exist because a census needs them.

The axes are independent **except** for these rejected combinations:

| `status` in | `formal_status` in | why |
|---|---|---|
| `refuted`, `retracted` | any `proved-*` | a refuted claim cannot also be formally proved |
| `established` | `refuted-formally` | an established claim cannot have its negation proved |
| `out-of-scope` | `proved-conditional`, `proved-unconditional` | out-of-scope should not carry a proof |

## 4. Evidence kinds

12 values: `proof-checked` · `proof-assumed` · `proof-negative` ·
`manuscript-proof` · `literature` · `literature-unverified` · `computation` ·
`database` · `adversarial-review` · `referee-report` · `counterexample` ·
`absent`.

`absent` records that evidence was looked for and is missing. It satisfies no
requirement.

## 5. The evidence gate

```
requirements : dict[ClaimStatus, list[set[EvidenceKind]]]
satisfied(target) :=
    for every S in requirements[target.status]:
        S ∩ { e.kind for e in target.evidence }  ≠  ∅
```

**Every set must be intersected non-emptily.** Per-set intersection is the correct
primitive; the historical bug (FM-01) was having only *one* set where two were
needed, which let a single review row with no proof reach `established`.

| `status` | requirements |
|---|---|
| `candidate` | `[]` |
| `supported` | `[{computation, database, literature, manuscript-proof, proof-checked}]` |
| **`established`** | `[{manuscript-proof, proof-checked}, {adversarial-review, referee-report}]` |
| `formalization-ready` | `[{proof-checked, literature, manuscript-proof}]` |
| `refuted` | `[{adversarial-review, counterexample, proof-negative}]` |
| `retracted` | `[{adversarial-review, counterexample, proof-negative}]` |
| `blocked`, `superseded`, `out-of-scope` | `[]` |

`established` is the only two-set row, and that is the point: **a proof kind and a
review kind**. `formal_status` is not gated.

## 6. Interface strength

5 values: `not-an-interface` · `reduces` · `restates` ·
`equivalent-to-conclusion` · `unassessed`.

The **assessed** values are `reduces`, `restates` and `equivalent-to-conclusion`;
each requires a non-empty `strength_witness` naming the theorem that establishes
it. `not-an-interface` and `unassessed` require none.

- `reduces` — strictly weaker than the conclusion. The only value that is progress.
- `restates` — interderivable with the *field it replaced*. The original
  assumption still carries content.
- `equivalent-to-conclusion` — inhabited exactly when the conclusion holds. Worse
  than `restates`, and what the iff test of §12 diagnoses.

## 7. Typed edges

| type | meaning | logical? | acyclic? |
|---|---|---|---|
| `needs` | cannot be *stated* without it | | ✓ |
| `depends-on` | cannot be *proved* without it | | ✓ |
| `discharges` | turns an assumption of `dst` into a theorem | ✓ | |
| `restates` | re-phrases an assumption of `dst`; reduces nothing | ✓ | |
| `refutes` | `src` refutes `dst` | ✓ | |
| `equiv` | mutually derivable | ✓ | |
| `implies` / `implied-by` | one-directional; `implies` is canonical, `implied-by` is its inverse and may be omitted | ✓ | |
| `special-case-of` / `generalizes` | containment | ✓ | |
| `supersedes` | `src` replaces `dst` | ✓ | |
| `imports` | literature or library input; `dst` may be an external id | | |
| `inhabits` | `src` is a non-vacuity witness for `dst` | | |
| `tests` | a computation that would falsify `dst` | | |
| `blocks` | `src` prevents work on `dst` until `src` leaves a terminal status | | |

**Every type marked logical requires a non-empty `citation`.** All of them, not a
subset: requiring it for four types meant retyping `implies` → `refutes` silently
dropped the citation (FM-01's sibling, FD-01).

**Cycle rule.** `DEPENDENCY_TYPES := {needs, depends-on}`. The **union** of those
edge types must be acyclic, directed `src → dst`. Per-type acyclicity is
insufficient: `A --needs--> B --depends-on--> A` is invisible per type and present
in the union. Self-loops are an error.

`dst` resolves to a target id, or to an external reference prefixed
`stacks:` / `mathlib:` / `lit:`.

## 8. Status transitions

17 legal, 4 forbidden, everything else rejected. **Enforcement is honest about
itself**: the JSON stores no prior status, so a single-file validator cannot check
a transition. This table is an authoring discipline plus a query (`transition
<id> <status>` answers legality and cost); it is not a validated invariant.

| from → to | cost |
|---|---|
| candidate → supported | evidence of a kind the `supported` row accepts |
| candidate → refuted | a counterexample, with the expectation it corrects |
| candidate → blocked | a named unresolved dependency edge |
| candidate → out-of-scope | a human scope decision |
| supported → formalization-ready | every hypothesis literal, every input named, **no unresolved assumption of kind `statement`** |
| supported → established | a complete proof **and** an independent review; a passing build never suffices |
| supported → refuted | a counterexample |
| supported → candidate | the supporting evidence was withdrawn or failed an admissibility gate |
| formalization-ready → established | a proof plus an independent review; f-ready is about the STATEMENT |
| formalization-ready → candidate | formalization exposed an ambiguity in the statement |
| formalization-ready → refuted | a counterexample |
| established → retracted | a review defeated the proof; claim and defeat BOTH retained |
| established → refuted | a counterexample to a claim believed proved; retain both |
| blocked → candidate | the blocking dependency resolved |
| blocked → out-of-scope | a human scope decision |
| refuted → superseded | a corrected statement exists as its own target; the refutation stays on file |
| retracted → candidate | a corrected statement; the retraction record is not deleted |

Forbidden, with the reason a tool should print:

| from → to | why |
|---|---|
| candidate → established | no path from no evidence to a reviewed proof in one step |
| candidate → formalization-ready | a statement with no evidence has not been pinned; go through `supported` |
| refuted → established | a refutation is retired only by defeating the counterexample, which is a **new target** |
| refuted → supported | same |

## 9. A–E grading and target kinds

`kind` ∈ `{definition, theorem, interface, example, counterexample, data,
tooling, audit}`.
`Assumption.kind` ∈ `{statement, mathematical, library, policy, data}`.
`Check.kind` ∈ `{machine, fidelity, review, human}`.

All three are closed. Free text plus rules that key on exact spelling is one typo
from silent (FM-03).

A grade is a **dispatch decision**, not a quality scale, so there is no ordering —
but the cap of §10 needs one, so define `A > B > C > D > E` for that rule alone.

| grade | deliverable | acceptance, by check kind | self-close |
|---|---|---|---|
| A | the finished change | ≥1 `machine` check with a command | yes — the run may close its own target |
| B | the change plus a fidelity argument | ≥1 `machine` check with a command **and** ≥1 `fidelity` check | no |
| C | a candidate, its evidence, its limits | ≥1 `review` check; it may confirm **or refute**, either closes the unit | no |
| D | a map of the question and what was settled | ≥1 `review` check; the report separates proved / conditional / computational / refuted and states the literature outcome including "no hits" | no |
| E | a blocking report naming the missing decision | ≥1 `human` check | no |

`self-close` governs whether the bounded run that does the work may mark its own
target done, or whether a second party must.

## 10. Validation — the complete list

A conforming validator emits `[C]` (blocking) or `[W]` findings for:

1. Target ids well-formed per §2 and unique; prefix constant.
2. Every target's id decade matches its `layer`.
3. Layer ids unique; every `target.layer` resolves.
4. `statement`, `grade_reason`, and every evidence `does_not_establish` non-empty.
5. `kind`, `Assumption.kind`, `Check.kind` in their closed vocabularies (§9).
6. `status`, `formal_status`, `strength`, `grade`, evidence `kind`, edge `type` in
   their vocabularies (§3–§7).
7. The evidence gate of §5 satisfied for `status`.
8. No rejected status/formal_status combination (§3).
9. `established` carries no assumption with `blocks_status: true`.
10. `formalization-ready` carries no `blocks_status: true` assumption of kind
    `statement`.
11. Every assessed `strength` (§6) has a non-empty `strength_witness`.
12. **The interface cap**: a target with `kind == "interface"` whose `strength` is
    `restates`, `equivalent-to-conclusion` or `unassessed` must be graded C, D or
    E.
13. Grade acceptance per §9: A needs a `machine` check *with a command*; B needs
    that plus a `fidelity` check; C/D need `review`; E needs `human`.
14. Every `fidelity` check has a non-empty `fidelity_source`.
15. `status: blocked` is justified: an inbound `blocks` edge from a non-terminal
    target, **or** a `blocks_status: true` assumption, **or** a dependency edge to
    a target whose status is `blocked`.
16. Every `assumption.upstream` resolves to a target **and** is backed by an edge
    in one direction: `upstream --discharges--> this`, or `this
    --needs|depends-on--> upstream`.
17. Every target id named in another target's `inputs` is backed by a dependency
    edge from that target.
18. If two targets each appear in the other's `inputs`, that is a `[C]`
    mis-scoping error regardless of edge types.
19. Edge `src` resolves; `dst` resolves or carries an external prefix (§7).
20. Every logical edge type (§7) has a non-empty `citation`.
21. The union of `DEPENDENCY_TYPES` is acyclic; no self-loops.
22. `status: superseded` has an outbound or inbound `supersedes` edge.
23. The recorded `revision` equals the recomputation of §1.
24. Unknown keys on any object are `[C]`.
25. `[W]` only: count evidence locators lacking `sha256` and report the ratio.

**Not enforced, and said so rather than implied**: transition legality (§8), id
append-only-ness (§2), and whether a cited locator's content says what the
evidence row claims. The first two need history the file does not carry; the third
needs a reader.

## 11. Mapping to the reference implementation

The reference implementation predates this spec's neutral naming:

| spec | implementation |
|---|---|
| `proof-checked` | `lean-proved` |
| `proof-assumed` | `lean-assumed` |
| `proof-negative` | `lean-negative` |
| `refuted-formally` | `refuted-in-lean` |

Semantics are identical. A new implementation should use the neutral names; the
mapping exists so the two can be compared.

## 12. The iff test

Before shipping any hypothesis interface, attempt to prove

```
Nonempty (YourInterface i) ↔ <the conclusion the interface is meant to supply>
```

where `i` is whatever the interface is indexed by. If that goes through with no
hypotheses and no domain content, the interface is
**`equivalent-to-conclusion`** — not `restates` — and it reduces nothing.

Record the iff as a theorem either way. It is the cheapest honest artifact this
representation asks for, and three interfaces in the source catalogue were
shipped as reductions without it.
