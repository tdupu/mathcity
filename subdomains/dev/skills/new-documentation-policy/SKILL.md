---
name: new-documentation-policy
description: >-
  Propose and apply human-approved amendments to
  mathcity/subdomains/dev/POLICY-documentation.md. Use when
  check-documentation-policy finds an uncovered documentation drift case, a DOC
  rule is ambiguous, or documentation workflow requirements need to change.
  Sole write path for DOC rules.
companion: "[[check-documentation-policy]]"
---

# new-documentation-policy

Propose and apply amendments to
[POLICY-documentation.md](../../POLICY-documentation.md). This is the sole
write path for DOC rules.

## Step 0 — Read Current Policy

```bash
cat <mathcity-pack-root>/subdomains/dev/POLICY-documentation.md
grep '| DOC |' <mathcity-pack-root>/docs/rule-prefix-registry.md
```

Record the policy status, date, and highest DOC rule ID.

## Step 1 — Draft Amendment

Present this before editing:

```text
PROPOSED DOCUMENTATION POLICY AMENDMENT — <date>

Pillar: <DOC1 truth/no-slop | DOC2 navigation | DOC3 examples/tests | DOC4 planned work | DOC5 setup/ops | DOC6 workflow | new>
Rule ID: <DOC<N>.<M>>
Rule title: <short title>
Trigger: <user directive, checker miss, incident, or drift finding>

Proposed rule text:
  <one paragraph with checkable requirement>

Pass criterion:
  <what check-documentation-policy can verify>

Fail criterion:
  <what triggers a finding>

Downstream impact:
  - Current docs in violation: <list or none>
  - Remediation: <needed or none>
```

## Step 2 — Human Gate

Ask:

```text
DECISION: Add/amend DOC<N>.<M> ("<rule title>")?
CONTEXT: <why>
RECOMMEND: APPROVE — <reason>
CONFIRM: y / n / grill-me-further
```

Do not edit until the human approves in the current conversation.

## Step 3 — Apply

After approval:

1. Edit `subdomains/dev/POLICY-documentation.md`.
2. Update the Date line.
3. Add a Change Log entry.
4. Run `check-documentation-policy` on the touched scope.
5. Run a local/private path scan on public docs.

Outside agents do not commit or push unless explicitly asked.

## Hard Rules

- Never change a DOC rule to excuse an existing violation.
- DOC rule IDs are permanent.
- Every new rule must have a checkable pass/fail criterion.
- Keep examples in policy only when they clarify an otherwise ambiguous rule.
- If the checker cannot enforce the proposed rule, write guidance in a doc
  instead of adding a numbered rule.
