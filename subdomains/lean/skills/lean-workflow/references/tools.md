# Lean tools and reproducible commands

Run commands from the selected Lake workspace. Read `lean-toolchain`, lakefile,
manifest and local instructions first. Record versions and actual output:

```sh
lean --version
lake --version
lake build
lake build Project.Target
```

Resolve `Project.Target` from the project's configured library/source roots;
do not assume a filename-to-module conversion works in every layout. Build
every selected module explicitly as well as the project's declared validation
targets. Record exit codes directly; a pipe ending in `tee` can hide failure.

For a missing toolchain, use the official [Lean installation instructions](https://lean-lang.org/install/manual/).
Prefer an existing elan installation. An isolated experiment can set `ELAN_HOME`
to a run-local directory and install without modifying PATH files. Preserve
existing pins. New Mathlib projects choose a specific compatible release or
commit and record both `lean-toolchain` and `lake-manifest.json`; do not write
`latest` into a reproducibility claim. Check `lake init --help` before using a
version-dependent template. Read the [Lake manual](https://lean-lang.org/doc/reference/latest/Build-Tools-and-Distribution/Lake/)
for the installed version's behavior. Fetch available precompiled Mathlib
artifacts with its supported cache command before a costly source build.

## Search and incremental checks

Available Lean LSP tools can inspect goals, diagnostics and candidate tactics.
Discover real tool names; these skills do not assume an MCP server is installed.
Use [search-tools.md](search-tools.md) for LeanSearch/Loogle queries, Stacks
retrieval, setup and version compatibility. Keep the target toolchain pinned.
Without one, use local source searches and small compiled probes:

```sh
rg -n 'candidate|relevantConcept' .lake/packages/mathlib/Mathlib
lake env lean /absolute/path/to/run/Probe.lean
```

The probe imports the selected modules and checks both name and applicability:

```lean
import Mathlib.Logic.Function.Basic
#check @Function.Injective
example {α : Type*} (f : α → α) (hi : Function.Injective f)
    (he : ∀ x, f (f x) = f x) (x : α) : f x = x := hi (he x)
```

On newer Lean module-system projects, raw `lake env lean` can lack module setup.
Check the installed `lake lean --help` and use its supported file driver (commonly
`lake lean Path/To/File.lean -- <lean-options>`), or the configured module build.
Do not misclassify missing setup as a failed mathematical proof. Scratch probes
must use the same workspace, imports and settings as their target.

## Types and axioms

After building targets, compile a run-local probe importing them:

```lean
import Project.Target
set_option pp.universes true
set_option pp.explicit true
#check @Project.main
#print Project.main
#print axioms Project.main
```

Repeat for every selected declaration, not just the headline theorem. Check
definitions the printed type depends on; a harmless-looking predicate name can
hide changed meaning. Lexical searches for `sorry`, `admit`, `axiom` and
`native_decide` are triage only: comments can match and imported admissions can
be invisible. Use compiler diagnostics and the actual axiom output.

## Profiling

On a compatible ordinary-module project:

```sh
lake env lean -Dprofiler=true -Dprofiler.threshold=100 Path/To/File.lean
```

Use the module-aware driver above when required. Measure on the same pinned
environment with comparable caches. Optional `Mathlib.Util.CountHeartbeats`
instrumentation and trace options are version-specific: verify their existence
locally and remove temporary wrappers from delivered source.
