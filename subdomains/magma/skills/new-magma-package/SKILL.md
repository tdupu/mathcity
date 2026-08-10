---
name: new-magma-package
description: Scaffold a new Magma package compliant with the Magma Packages Policy (mathcity/subdomains/magma/POLICY.md) — the package-<topic>.mag file with header block, the spec entry in dependency order, a README section stub (Purpose/Functions/Dependencies/Usage/Tests), a README test stub with project boilerplate, and a tracking bead. Use when the user says "new magma package", "start a package for X", "scaffold package-X.mag", "make a new .mag package", or when code in a notebook/script has outgrown its file and needs to become a package (pair with notebook-to-package for the code-moving leg). Companion of check-magma-hygiene, which audits what this skill creates.
---

# new-magma-package

Create a new Magma package that is born compliant with
[POLICY.md](../../POLICY.md): M1.3 (header), M1.5 (spec entry), M2.1–M2.2
(README section), M3.1/M3.3 (test stub), M4.1 (tracking bead) hold by
construction. The scaffold is deliberately minimal — real intrinsics,
examples, and asserts are filled in by later work, gated by
`check-magma-hygiene`.

## Inputs

Collect (ask if not given):

1. **Topic** — short lowercase hyphenated noun (`cusp`, `relation-finder`).
   Becomes `package-<topic>.mag`.
2. **Purpose** — one paragraph: what the package computes, its principal
   type(s) if it declares any.
3. **Dependencies** — which existing packages it needs (fixes its spec
   position), plus any external requirements (data, Magma version).
4. **Project** — which repo/rig (default: the current working project).

## Procedure

### Step 0 — Discover project conventions (never invent)

```bash
ls <proj>/magma/*.spec <proj>/*.spec
cat <spec-file>
ls <proj>/magma/test/README-tests/ | tail -5     # next NN
head -40 <an existing package-*.mag>              # header style
head -20 <an existing test-NN-*.mag>              # test boilerplate
grep -n "^#\|^##\|^###" <proj README(s)> | head -40
```

Extract: spec path and load order, next free test number `NN`, the exact
test boilerplate (AttachSpec path, `SetLMFDBRootFolder`, verbose
settings), README file + coverage-table location. If the project has no
Magma layout yet, stop and confirm the intended layout with the user
before creating one.

Refuse (with the reason) if `package-<topic>.mag` already exists — extend
it via `improve-package-README` instead.

### Step 1 — Package file `magma/package-<topic>.mag`

```magma
/*

<Title: topic, capitalized, human-readable>.

Authors: <from git config / ask>, <YYYY>

<Purpose paragraph. Name the principal types. Cite the paper/reference
this implements, if any.>

WARNING: <known sharp edges, or delete this line>

*/

// declare verbose <Topic>, 6;          // uncomment if the package logs
// declare type <TypeName>[<EltName>];  // uncomment if it owns a type

Z := Integers();
Q := Rationals();

//#############################
intrinsic <first_intrinsic>(x::<Type>) -> <RetType>
//#############################
{One-line description shown by Magma's help.}
    require <precondition>: "<message>";
    // ...
    return <value>;
end intrinsic;
```

No top-level computation (M1.4). Follow the surrounding packages' comment
banner style.

### Step 2 — Spec entry (dependency order, M1.5/M7.1)

Insert `package-<topic>.mag` into the spec file **after** every declared
dependency and before anything that will depend on it. If the project's
CLAUDE.md documents the load order, add the one-line entry there in the
same change.

### Step 3 — README section stub (M2.2)

Add to the project README (or the appropriate `README-<area>.md`), and a
TOC entry if the file has one:

```markdown
### <Topic Section Title>

<Purpose paragraph.>

**Depends on:** <sibling packages; external requirements or "stock Magma">.

Load via the project spec (see "Attaching The Package"); no extra setup.
<!-- or state the extra setup -->

​```magma
> <first_intrinsic>(<realistic input>);
<expected output>
​```

Covered by `test-NN-<topic>.mag`.
```

Add the coverage-table row `| test-NN-<topic>.mag | <Topic Section Title> |`
in file-number order (M2.4).

### Step 4 — Test stub `magma/test/README-tests/test-NN-<topic>.mag` (M3.3)

```magma
// test-NN-<topic>.mag
// Covers README section: "<Topic Section Title>"
// Under test: package-<topic>.mag (<first_intrinsic>, ...)
// Run from magma/test/README-tests/:  magma test-NN-<topic>.mag

<boilerplate copied verbatim from a sibling test — never invented>

// ------- <Topic Section Title> -------
result := <first_intrinsic>(<realistic input>);
assert <concrete expected-value check>;   // no tautologies; add a second input

printf "test-NN-<topic>.mag: OK\n";
```

Run it once (`magma test-NN-<topic>.mag`) and confirm the `OK` line before
declaring the scaffold done. If Magma is not available in this session,
say so explicitly and leave the run as the first item on the bead.

### Step 5 — Tracking bead (M4.1)

```bash
cd <proj> && bd create -t task \
  "[package-<topic>] new Magma package: <one-line purpose>" \
  -d "$(cat <<'EOF'
Scaffolded by new-magma-package on <date>.
- Package: magma/package-<topic>.mag (spec position: after <deps>)
- README: <readme-file> § "<Topic Section Title>"
- Test: magma/test/README-tests/test-NN-<topic>.mag
Remaining: <first-run confirmation if unrun>; fill in intrinsics + examples;
close per POLICY.md M4.3 (code merged + README current + test passing).
EOF
)"
```

Report the bead ID. Do not claim or close it here.

### Step 6 — Hand off

Report all created/modified paths, the spec position chosen, the bead ID,
and whether the test stub was executed. Do NOT commit or push — leave git
actions to the user (conservative profile). Suggest running
`check-magma-hygiene` on the diff once the first real intrinsic lands.

## What this skill does NOT do

- Does not write the mathematics — intrinsics beyond the first stub are
  the follow-on work tracked by the bead.
- Does not move existing code — use `notebook-to-package` /
  `notebook-to-mag` for promotion from notebooks.
- Does not audit — that is `check-magma-hygiene`.
- Does not commit, push, or close beads.

## Cross-references

- [[POLICY.md]] (this subdomain) — the rules this scaffold satisfies.
- [[check-magma-hygiene]] — audit gate for the result.
- [[improve-package-README]] — grows the README section as intrinsics land.
- [[is-good-test]] — design review once the test has real asserts.
- [[notebook-to-package]] — promotion path from exploratory notebooks.
