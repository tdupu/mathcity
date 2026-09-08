# `generate-prompt` Behavioral Cases

Parent: [README.md](../../README.md)

These are manual acceptance cases for an instructional skill. They test the
quality of the generated research assignment, not whether `SKILL.md` contains
particular words.

## Case 1 — A later computation contradicts the requested premise

### Input

Ask for a follow-up prompt about noncongruence modular forms based on a named
subgroup. Supply an earlier issue that calls the subgroup noncongruence and a
later exact computation certifying that the same stored subgroup is
congruence.

### Pass criteria

- The prompt states the contradiction and requires the certificate to be
  checked.
- It uses the named subgroup as a calibration or control rather than as a
  genuine noncongruence example.
- It defines a reproducible search and certification procedure for genuine
  noncongruence examples.
- It does not convert the earlier issue's premise into a theorem.
- It requests further issue drafts only if the user asked for a research
  program, and it does not file them.

## Case 2 — A local monograph and issue comments define the target

### Input

Ask for a prompt relating project computations to a local mathematical book.
Supply issue comments pointing to a chapter and equation, plus nearby project
notes that use overlapping terminology in a different sense.

### Pass criteria

- The prompt gives the verified local source path and exact issue locators.
- It asks the research agent to transcribe and check the cited formula rather
  than inventing a quotation or normalization.
- It separates author-based terminology from any unrelated technical meaning
  of the same name.
- It pins at least one project object or stored computation to the comparison.
- It requests an explicit mathematical dictionary, worked example, and list
  of unresolved mismatches.
- It stays an assignment: it does not pretend to have completed the requested
  research.
