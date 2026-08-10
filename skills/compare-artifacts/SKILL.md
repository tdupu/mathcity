---
name: compare-artifacts
description: Semantic-diff between two text artifacts. Given two strings or file paths, return a similarity score (and, when asked, a token-level overlap signal) so the caller can decide "are these effectively the same, meaningfully different, or contradictory?" Use whenever the caller wants to quantify "how much did v2 differ from v1?" (fixed-point-finder round-to-round comparison), "are these two SKILL.md / notes / brief drafts near-duplicates?", or "which of these prose candidates is closest to a target?". Trigger on phrases like "compare-artifacts X Y", "are these duplicates", "semantic diff", "similarity between A and B", "did v1 and v2 diverge much". Not for math/logic correctness — embeddings WILL agree on a wrong proof; escalate to a build (Lean) or `coordinate-review` (prose math) for that.
---

# compare-artifacts

Quantify the similarity between two text artifacts. Three metrics are available; the skill's job is to tell future agents **which one to reach for given the task**, not to teach embeddings from scratch.

Per the human adjudicator (2026-06-22): cheap-baseline → BERTScore → LLM-judge, in that order. Don't pay BERTScore's cost when cosine answers the question; don't trust either when the question is "is this proof correct?".

## When to use

- **Fixed-point-finder convergence check.** `coordinate-review` produced v2 of a SKILL.md / plan / brief. Did v2 actually move, or is the loop oscillating in place? Cosine on embeddings gives a single scalar per round.
- **Near-duplicate detection across drafts.** Two SKILL.md drafts, two issue-sort verdict bodies, two grilled briefs on related beads. Are they redundant?
- **Prose candidate comparison.** The Lean plan ([[gt-pr6]]) generates multiple prose-solution candidates per problem; pick the one closest to a reference solution (or furthest, if you want diversity).
- **Drift detection over time.** Same artifact at t=0 and t=N. How much has it semantically drifted?

If the question is "is this proof / program / theorem statement *correct*?", stop. Use `lake build` for Lean, the test suite for code, `coordinate-review` for prose math. Cosine and BERTScore are blind to truth — two contradictory statements about the same topic look near-identical to them.

## Inputs

- **a, b** (required): the two artifacts. Each is either an absolute path or an inline string. Mixed (one path, one inline) is fine.
- **metric** (optional): `cosine` (default), `bertscore`, or `both`. Picked by the decision tree below if omitted.
- **task** (optional, recommended): one of `prose`, `code`, `math-claim`, `skill-md`. Lets the skill route to the right metric and surface a `math-claim` warning.

## Output

A short report containing:

- the chosen metric(s) and why,
- the raw scalar(s) — cosine `s ∈ [-1, 1]` and/or BERTScore `(P, R, F1)` triple,
- a one-line verdict from the interpretation thresholds (see below),
- if `task=math-claim`: a **warning** that this skill cannot answer correctness, with a pointer to the right gate.

## Procedure

### 1. Route to a metric

If `metric` is given, honor it. Otherwise:

- `task ∈ {prose, skill-md}` or omitted → **cosine** (cheap, scalar, good for "did it move").
- Caller asks "what overlaps vs what diverges" or wants per-token detail → **bertscore**.
- `metric=both` → run cosine first; only run BERTScore if cosine is in the ambiguous band `0.5 ≤ s ≤ 0.85` (saves wall time on obvious cases).
- `task=math-claim` → still run cosine for the diff signal, but **prepend the correctness warning** in the report and tell the caller to escalate.

### 2. Cheap baseline — cosine on sentence-transformer embeddings

```python
from sentence_transformers import SentenceTransformer, util

# BAAI/bge-large-en-v1.5 is the quality default; switch to
# all-MiniLM-L6-v2 if you need 10x faster encode at modest cost.
m = SentenceTransformer("BAAI/bge-large-en-v1.5")
e1, e2 = m.encode([a, b], convert_to_tensor=True)
score = util.cos_sim(e1, e2).item()  # scalar in [-1, 1]
```

PyTorch is loaded transitively by `sentence-transformers`; no separate `pip install torch` needed if `sentence-transformers` is already on PATH. Embedding both artifacts once costs one forward pass each — cheap enough to run inside an FP-finder loop without instrumentation.

Stay on the same `SentenceTransformer` model across a comparison set. Different models live in different vector spaces; scores from `bge-large` and `MiniLM` are not interchangeable.

### 3. Token-level — BERTScore

```python
from bert_score import score

# microsoft/deberta-xlarge-mnli is the strongest English default;
# pin lang="en" or it will autodetect on every call.
P, R, F1 = score([b], [a], lang="en", model_type="microsoft/deberta-xlarge-mnli")
```

Returns precision/recall/F1 over BERT-aligned tokens between the two artifacts. The F1 scalar is the headline; the P-vs-R split tells you *which side* has extra material (R < P → reference `a` has content `b` lacks; P < R → `b` has content not in `a`). Use when "how similar" isn't enough and you need "which spans diverged".

Heavier than cosine: a deberta-xlarge forward pass per artifact pair. Don't put this inside a tight FP-finder loop; use it as a closer on the rounds cosine flagged as ambiguous.

### 4. Correctness gate — when embeddings lie

Embeddings encode *topic* and *register*, not *truth value*. Two of the cleanest failure modes the human adjudicator has seen:

- "The Riemann hypothesis is true" vs "The Riemann hypothesis is false" — cosine ≈ 0.99.
- A correct proof and a wrong proof of the same theorem, in the same notation — BERTScore F1 ≈ 0.95.

Whenever the task is `math-claim` (or the caller asks "are these the same theorem"), do not let the scalar settle the question. Escalate to a real correctness oracle:

- **Lean**: `lake build` on both candidates; same theorem name compiles or it doesn't.
- **Code**: run the test suite against both; identical pass set ≈ behavioral equivalence.
- **Prose math**: hand both to `coordinate-review` with a `critical-review` reviewer persona; let the FP-loop adjudicate.

This skill stays silent on correctness; it only flags the risk.

## Interpretation thresholds

For cosine on `bge-large-en-v1.5` (rough bands — calibrate per corpus):

- `s > 0.95` → near-duplicate. Treat as "same artifact" unless `task=math-claim`.
- `0.85 < s ≤ 0.95` → same content, surface differences (wording, ordering, one section moved).
- `0.5 ≤ s ≤ 0.85` → same topic, real divergence. Run BERTScore for the per-span detail.
- `s < 0.5` → different artifacts. Cosine is doing its job; no escalation needed.

BERTScore F1 on deberta-xlarge runs higher (it baselines on alignment quality, not topical centroid distance). `F1 > 0.97` is the "looks identical" floor; `F1 < 0.85` is meaningful divergence.

## Pitfalls

1. **Comparing across models / versions.** A v1 embedded with `bge-large` and a v2 embedded with `MiniLM` is meaningless. Pin the model in the report.
2. **Length asymmetry.** A 50-line SKILL.md vs a 500-line one will score lower in cosine even if the 50-line is a strict subset. For "is A a subset of B?", use BERTScore Recall, not cosine.
3. **Tokenizer drift.** BERTScore's per-token alignment depends on the tokenizer of `model_type`. Don't compare F1 across `model_type` choices.
4. **Treating cosine as a probability.** It's not. `0.85` doesn't mean "85% chance of being the same"; it means "cosine of the angle is 0.85". Apply the bands above, don't invent new ones.
5. **Running inside `coordinate-review` without budget.** BERTScore inside a 10-round FP-loop is ~10 deberta-xlarge passes. Default cosine; only escalate to BERTScore at the loop's tail.

## Cross-references

- **[[gt-pr6]]** — Lean plan; `solve-problem` / `solve-in-lean` will call this to compare candidate solutions before voting.
- **[[he-yvw]]** — issue-sort cohort; use cosine to flag duplicate verdict bodies before presenting to the human adjudicator.
- **`coordinate-review`** — the convergence check on its FP-loop is "did cosine(v_n, v_{n-1}) cross the threshold?". This skill is that check.
- **`critical-review`** — the parent reviewer for the correctness-escalation path described in step 4.

## What this skill does NOT do

- **Does not judge correctness.** Same-topic ≠ same-truth-value. See step 4.
- **Does not install models.** Caller is expected to have `sentence-transformers` and `bert-score` on PATH; if not, surface the missing dep, don't silently fall back to a weaker metric.
- **Does not pre-tokenize.** Pass artifacts as-is; the libraries handle tokenization.

## Versioning

v1, pending the fixed-point-finder pass. Expect the interpretation bands and the cosine-then-BERTScore escalation policy to tighten once this has been used on real FP-finder rounds.
