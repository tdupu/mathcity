# Review the claim inventory for completeness

You are reviewing the inventory from the previous step. Be adversarial: your job
is to find what it MISSED, not to agree with it.

## Check

1. **Coverage** — walk the bounded section independently. Does every mathematical
   assertion appear in the inventory? Name any that do not.
2. **Dependency honesty** — does any claim depend on something absent from both the
   inventory and the named externals?
3. **Gap honesty** — the most common failure is a gap silently repaired into a
   hypothesis that the source does not state. Flag every such repair.
4. **Scope** — does the inventory stay inside `scope_box`, or has it drifted?

## Verdict

Return **APPROVING** or **NEEDS-REVISION** with a prioritized list of specific,
actionable items. An inventory that is merely plausible is not approved — it must
be checked against the source text.
