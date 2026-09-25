# Check the statement against the source claim

Adversarial review of the statement, BEFORE anyone spends effort proving it.

## Ask, in this order

1. **Does the Lean type mean what the prose means?** Read them side by side. Name
   any divergence, however small — quantifier order, strictness of an inequality,
   an implicit finiteness assumption.
2. **Is it stronger or weaker than the source?** Weaker is the common failure: a
   gap became an extra hypothesis and the theorem now says less than claimed.
3. **Could it be vacuous?** If a hypothesis is unsatisfiable the theorem is
   trivially true and worthless. Check that the hypotheses are inhabitable.
4. **Does it match the base-ring constraint from stage 3?**
5. **Is it already in Mathlib?** If so, the correct outcome is reuse, not proof.

## Verdict

**APPROVING** or **NEEDS-REVISION** with specific items. Do not approve a statement
you have not compared to the source text line by line. This is the last gate before
proof effort is spent, and a wrong statement that passes here produces a green build
certifying a false claim.
