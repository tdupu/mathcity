---
name: get-best-models
description: >
  Recommends the best open-weights / local LLM for a given hardware constraint and
  use case, using IFScale as the primary ranking metric and the memory-constraint
  formula (P*b <= available RAM) to filter candidates.

  Trigger when the human adjudicator asks: "what model should I run on my laptop", "what's the best
  model for 36GB", "which Ollama model should I pull", "what can I run locally",
  "best open-source model for coding", "what model fits in X GB", or any hardware-
  constrained model selection question. Use get-best-apis instead when the question
  is about API pricing or a full cross-provider comparison table.
---

Recommend the best locally-runnable model given the user's hardware and use case.
Reference `<repos-root>/agent-skills/llama-docs/SELECTING-MODELS.md` for the full
memory-constraint formula, quantization table, and recommended tiers.

## Step 1 — Clarify hardware and use case

Ask (or infer from context):
- **Available memory**: unified RAM (Apple Silicon) or VRAM (NVIDIA/AMD GPU)
- **Use case**: coding agent, general chat, math/reasoning, multilingual, etc.
- **Latency preference**: fastest response vs. best capability

## Step 2 — Compute the memory constraint

Apply the formula from SELECTING-MODELS.md:

```
M(P, b) ≈ P * b   (dominant term)
```

| Quantization | bytes/param |
|---|---|
| FP16 | 2.0 |
| Q8 | 1.0 |
| Q6 | 0.75 |
| Q5 | 0.625 |
| Q4 | 0.5 |

Leave ~20–25% headroom for KV cache, OS, and runtime buffers.
Preferred quant: Q5_K_M; fall back to Q4_K_M before choosing a smaller model.

Approximate sizes:

| Model size | Q5 | Q4 |
|---|---|---|
| 7–8B | ~5 GB | ~4 GB |
| 14B | ~9 GB | ~7 GB |
| 32B | ~21 GB | ~18 GB |
| 70B | ~44 GB | ~38 GB |

## Step 3 — Fetch the current IFScale leaderboard

Check `https://distylai.github.io/ifscale/` (WebFetch) for up-to-date rankings,
filtering to models that fit within the hardware budget. Fall back to a web search
(`IFScale leaderboard site:distylai.github.io` or `IFScale top models 2025`) if
the page is unavailable.

The IFScale paper: https://arxiv.org/pdf/2507.11538

## Step 4 — Recommend

Give 1–3 ranked recommendations in order of IFScale score. For each:

- **Model name** and parameter count
- **Recommended quantization** and estimated size in GB
- **Where to pull it**: Ollama command (`ollama pull <name>`) or Hugging Face link
- **IFScale score** (or note if unavailable)
- **One-line rationale**: why this model for this hardware/use-case

Format as a short numbered list, not a table — this is a quick answer, not a report.
Use get-best-apis if the human adjudicator wants the full cross-provider pricing table.

## Tier guidelines

| Tier | RAM | Target size | Examples |
|---|---|---|---|
| LOW | 8–16 GB | 7–14B Q5_K_M | Qwen3-8B, Llama-3.1-8B |
| MID | 24–40 GB | 30–35B Q5_K_M | Qwen3-32B, Qwen3-Coder-30B |
| HIGH | 64 GB+ | 70B+ Q4_K_M | Qwen-72B, Llama-3.3-70B |
