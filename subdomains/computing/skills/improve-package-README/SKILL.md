---
name: improve-package-README
description: Add or update documentation in a Magma or Sage project's README files and the corresponding README test files. Use this skill whenever the user says "improve the README", "add to README", "document this intrinsic/function", "README-test for X", "add a section to README", "update README-tests", "README coverage", "add an example for", "add a regression test", or "generate a regression artifact". Also trigger when the user has just implemented a new intrinsic or function and wants it documented. Works with any Magma or Sage project — discovers README structure and test conventions from the project layout rather than assuming a fixed directory tree.
---

# improve-README Skill

## Overview

This skill guides adding or updating documentation in a Magma or Sage project, keeping README examples and README test files in sync. It discovers conventions from the project rather than assuming a fixed layout, so it works for any project in either language.

## Step 0 — Discover project structure (do this first on a new project)

Before adding content, understand the layout by reading these indicators:

**README files**:
```bash
ls *.md README* 2>/dev/null | head -20
```

**Test directory** — where `.mag`, `.m`, or `.sage` test files live:
```bash
find . -maxdepth 4 \( -name "*.mag" -o -name "*.m" -o -name "*.sage" -o -name "test_*.py" \) \
  | grep -i "test" | head -20
```

**Spec/entry-point file** (Magma):
```bash
ls *.spec *.m 2>/dev/null | head -10
```

**README-test convention** — dedicated folder or table in a README:
```bash
ls -d test/README-tests README-tests tests/README-tests 2>/dev/null
grep -rl "README.*test\|test.*README" *.md 2>/dev/null
```

From these outputs determine:
- Which README file(s) to update
- Where README test files live (create a new subdirectory if none exists yet)
- The test-file naming convention (`test-NN-name.mag`, `readme_section.sage`, `test_section.py`, etc.)
- The boilerplate the test files need (language, spec loading, setup imports)

If the project layout is ambiguous, ask the user before proceeding.

## Step 1 — Identify where to add

Decide which README file the new content belongs in. For multi-file setups, read the existing structure to find the best fit.

Within the target file decide:
- **Existing section**: find the right heading and add below it.
- **New section**: pick a logical position, add a heading, and add a TOC entry if the file has one.

For Magma projects with a test-coverage table: note which test file covers the target section, or that a new test file is needed.

## Step 2 — Write the README example

Write a minimal, self-contained code block. Follow the project's existing style — mirror the formatting of nearby examples.

**Magma style**:
```magma
> IntrinsicName(input);
Output
```

**Sage/Python interactive style**:
```python
>>> function_name(input)
output
```

**Sage/Python script style**:
```python
result = function_name(input)
print(result)  # Output
```

Conventions:
- Show realistic inputs — avoid trivial scalar-only examples where possible.
- Show the expected output as a comment or separate block immediately after.
- Keep examples short: demonstrate usage, not a tutorial.
- Name variables clearly; do not add prose comments explaining what self-documenting code already says.

Insert the example in the correct section. Add a TOC entry if the file has one.

## Step 3 — Write or update the README test

README tests exercise every code example in their corresponding README section. Use one test file per README section (or one per README for simpler projects).

### Discover boilerplate from the project

Read an existing test file from the same project before writing a new one to extract:
- The exact boilerplate (spec attachment, setup, imports, verbose settings)
- Path conventions (relative paths from the test file's location)
- The assertion pattern (`assert`, `assertEqual`, `printf "OK"`, etc.)
- Whether regression artifacts (`.expected` files) are used

**Magma template** (fill in boilerplate from an existing test — never invent paths or spec names):
```magma
// test-NN-section-name.mag — README coverage for: <Section Name>
// Run from <test-directory>/:  magma test-NN-section-name.mag

<boilerplate copied from existing test in this project>

// --- <subsection name> ---
<code from README example>;
assert <expected>;  // or: printf "%o\n", <result>;

printf "test-NN-section-name.mag: OK\n";
```

**Sage/pytest template** (adapt from existing tests):
```python
# test_section_name.py — README coverage for: <Section Name>
# Run:  sage -python test_section_name.py   (or: pytest test_section_name.py)

<imports copied from existing test in this project>

def test_section_name():
    # --- <subsection name> ---
    <code from README example>
    assert <result> == <expected>

if __name__ == "__main__":
    test_section_name()
    print("test_section_name.py: OK")
```

**Rules**:
- Copy boilerplate from an existing test — never invent paths.
- If data files may be absent, guard with a graceful skip rather than hard-failing.
- If the example is slow (>30 s), mark with `// SLOW` (Magma) or `# SLOW` (Sage/Python) and print timing before and after.
- End with a clear `OK` print so test runners can detect success without parsing assertions.

If the section's test file already exists, **add** the new example to it rather than creating a new file.

### Regression artifacts

Regression artifacts are files that capture expected output for later comparison, useful when the output is too large or complex to inline as an assertion.

**To generate a regression artifact**:
1. Run the test once and capture stdout to a file:
   ```bash
   # Magma
   magma test-NN-section-name.mag > expected/test-NN-section-name.expected
   # Sage/Python
   sage -python test_section_name.py > expected/test_section_name.expected
   ```
2. Save the artifact at `<test-dir>/expected/<test-file-base>.expected` (or follow the existing convention if the project already has one).
3. If the project's test runner compares against artifacts automatically, no test-file changes are needed. Otherwise, add a comparison step:
   ```magma
   // Compare stdout against expected/test-NN-section-name.expected
   // (add comparison logic matching the project's existing helper, if any)
   ```

Check whether an `expected/` subdirectory already exists before creating one. If no regression-artifact pattern exists yet, propose creating `<test-dir>/expected/` and note it in the PR description.

## Step 4 — Update the test table (if applicable)

If the project's README includes a test-coverage table, add or update the row:

```markdown
| `test-NN-section-name.mag` | Section Name |
```

Keep the table sorted in the same order as existing entries (usually by file number). If no test table exists, skip this step.

## Quick-start for first use on a new project

If you have never run this skill on a particular project before, do Step 0 first and ask:

> "To set up README test coverage for this project I need to know:
> 1. Which file(s) contain the README documentation?
> 2. Where do README test files live (or should they live)?
> 3. Can you show me an existing test file so I can copy the boilerplate?"

Once answered, proceed with Steps 1–4. You can skip Step 0 on future uses in the same project.

## Common cases

**New Magma intrinsic in an existing package**: Find the section in the relevant README. Add example. Update or create the test file for that section. Update the test table if the README has one.

**New Sage function in an existing module**: Find the relevant README section. Add a doctest-style or script-style example. Update the corresponding test file (or create one if none covers that section).

**New data-generation script or infrastructure step**: Add to whichever README covers infrastructure (e.g., a separate data-generation README). No README-test required if the operation needs external resources — note this clearly in the README.

**Entirely new package or feature**: Create a new top-level `##` section in the relevant README. Create a new test file. Add the test to the coverage table if one exists.

**Example is too slow for CI**: Add to the README with a note about runtime. Add to the test file with a `// SLOW` / `# SLOW` marker and explicit timing print. Do not skip it — slow tests can be gated separately by a CI filter.

**Regression artifact needed**: Run the code, capture stdout, save as `.expected`, and update the test to compare against it. If the project does not yet have an expected-output pattern, propose creating `<test-dir>/expected/` and note it in the PR description.
