---
name: behavior-cause
description: >-
  Use when a reproduced agent behavior has to be traced to the artifacts whose
  text produced it.
---

# Behavior cause

Input: a confirmed repro. Output: an ordered candidate list with the evidence
and an ownership finding for each — or **no-candidate** or **all-refused**.

## Candidates, not a culprit

Enumerate candidates from what the repro run itself can be made to report as
read; when that inventory cannot be recovered, report **no-candidate** rather
than guessing. Report each candidate together with the words in it that would
produce this behavior. Being loaded during a bad run makes nothing responsible;
the whole context was loaded together. Collapse to one candidate only when the
evidence collapses.

Two artifacts that both explain the behavior is a finding, not a licence to
edit both. Escalate through [[adjust-behavior]] for a recommendation and repair
the single candidate it names; if that repair comes back `failed` from
[[behavior-verify]], the next candidate is the next hypothesis.

## Ownership is detected, never assumed

**Resolve the path first, then classify what it resolved to, and let the
classification govern.** A symlink is not a licence: the real copy is the only
thing worth editing, and only if the real copy is editable. Editing through the
link yields a change lost on the next sync or silently duplicated.

Probes that hardcode no layout, all run from the resolved path: resolve links
(`readlink -f` or equivalent); ask whether the real copy sits inside its own
version-control root (`git rev-parse --show-toplevel`); ask whether a dependency
manifest, vendor directory, or installed-plugin cache above it claims it.

**Vendored, third-party, and installed-plugin artifacts are not edited.** An
edit there is overwritten on the next update or is an unattributed fork. Report
the behavior upstream, naming the artifact, its origin, and the evidence that
placed it there. A candidate in no version-control root and claimed by nothing
is refused the same way: editable only where local ownership is shown.

Refusal is per candidate, not per run. A refused candidate is reported and
dropped, and repair continues on the remaining candidates under the rule above,
never on an arbitrary pick. Only when every candidate is refused does the run
end as **all-refused**: the upstream report and no repair. Never compensate for
a refused candidate by hardening a local artifact; a note recording the upstream
defect is allowed, and the test is operational — if deleting the addition would
leave some agent out of compliance, it is a rule, not a note.

## Absence is not evidence

A search returning nothing may mean the thing is absent or the query was wrong.
Before reporting "not found", run the same search for something you know is
present.
