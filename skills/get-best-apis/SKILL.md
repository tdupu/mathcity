---
name: get-best-apis
description: >
  Fetches live LLM benchmark rankings (IFScale / AA Intelligence Index) and current
  API pricing (input $/1M, output $/1M) across OpenRouter, Ollama, OpenCode, Anthropic,
  and OpenAI, then renders a self-contained HTML table sorted by score with a per-vendor
  price matrix.

  Trigger whenever the human adjudicator asks about the best or cheapest LLMs, wants a model comparison
  table, asks "what's the best model for $200/month", wants to compare OpenRouter vs
  Ollama vs OpenCode pricing, asks about IFScale or AA Intelligence Index scores, or says
  "get me the latest API prices", "what should I be using for cheap inference", or
  "compare prices across vendors". Also trigger when a model comparison table is pasted
  and the human adjudicator asks to refresh it with live data.
---

Produce a live, up-to-date HTML comparison table of the top LLM models by benchmark
score with current API pricing from competing providers. Save as
`llm-comparison-YYYY-MM-DD.html` using today's date.

## Step 1 — Gather benchmark rankings

Search for the current AA Intelligence Index (what the human adjudicator calls "IFScale") from
Artificial Analysis. This is the primary sorting metric.

Good search queries:
- `site:artificialanalysis.ai intelligence index leaderboard 2025`
- `"AA intelligence index" top models ranking`
- WebFetch `artificialanalysis.ai/models`

Also check IFScale directly:
- `https://distylai.github.io/ifscale/` (WebFetch)
- `IFScale leaderboard 2025 site:distylai.github.io`

Use the AA Intelligence Index as the primary sort; use IFScale as a secondary signal
for instruction-following quality. Aim for 10–14 models. Include a mix of proprietary
and open-weights models.

## Step 2 — Gather per-vendor pricing

For each model, look up input $/1M and output $/1M on each platform:

| Platform | Where to look | Notes |
|---|---|---|
| OpenRouter | `openrouter.ai/models` | Best source for open-source model prices; covers DeepSeek, Qwen, Llama, Kimi, etc. |
| Ollama | `ollama.com/library/<model>` | Local/free — weights download, no API cost |
| OpenCode | `opencode.ai` or search "opencode LLM pricing" | Open-source terminal coding agent (SST/sst.dev); passes through to provider APIs — show effective provider rate |
| Anthropic | `anthropic.com/pricing` | Claude models only |
| OpenAI | `platform.openai.com/docs/pricing` | GPT / o-series only |
| Google | `ai.google.dev/pricing` | Gemini models only |

Goal: fill a price cell for every platform where the model is available. Use "—" when
unavailable and "Free / local" for Ollama entries.

## Step 3 — Classify open-source vs proprietary

**Open-weights / open-source → bold blue row (#dbeeff, font-weight: 600):**
DeepSeek, Qwen (Alibaba), Llama (Meta), Mistral, Kimi/Moonshot (if weights released),
GLM (Zhipu), Phi (Microsoft open weights), Command R (Cohere open weights), Gemma
(Google open-weights release).

**Proprietary → plain white row:**
Claude (Anthropic), GPT / o-series (OpenAI), Gemini API-only (Google), any model
whose weights are not publicly downloadable.

the human adjudicator's convention: apply proprietary styling to any model maintained primarily by
Anthropic, OpenAI, or Google — even when weights are technically downloadable (e.g.
Gemma).

## Step 4 — Build the HTML table

Single self-contained HTML file, all CSS inline, no CDN links.

### Required columns (left to right)

1. **#** — rank badge (gold/silver/bronze top 3, grey circle for the rest)
2. **Model** — bold model name + maker in smaller grey text below
3. **IFScale (AA Index)** — numeric score + small proportional bar (max width = top score)
4. **Released** — 4-digit year
5. **OpenRouter** — `In: $X.XX / Out: $X.XX per 1M`, linked `↗` to the OpenRouter model page, or "—"
6. **Ollama** — `Free / local ↗` (linked to `ollama.com/library/<model>`) or "—"
7. **OpenCode** — effective cost via OpenCode, e.g. `via Anthropic $3/$15` in small text, linked to `opencode.ai`, or "—"
8. **Direct API** — cheapest direct-provider price with a small linked label (Anthropic / OpenAI / Google / DeepSeek); omit if OpenRouter is already cheapest by more than 20%
9. **Buy / Download** — pill buttons: blue `#0071e3` for paid API (OpenRouter preferred), green `#28a745` for Ollama/free
10. **Typical Strengths** — 1–2 sentence summary, smaller font

Use a `<colgroup>` or column header separator to group columns 5–8 under a
**"Price by Platform"** super-header.

### Style rules

- Dark header row: background `#1c1c1e`, white text, font-size 11px uppercase labels
- Open-source rows: background `#dbeeff`, font-weight 600
- Proprietary rows: background white, normal weight
- Hover: slightly darker tint per row type
- Rank 1: `#ffd700`; rank 2: `#c0c0c0`; rank 3: `#b87333` — all with white text
- Buy buttons: border-radius 5px, white text
- Disclaimer box at bottom: yellow left-border, states sources, fetch date, and that
  prices may lag real-time changes

## Step 5 — Deliver

After saving the HTML file, deliver it via SendUserFile.

If `mcp__remote-devices__create_artifact` is available (Cowork / remote session),
also call it with the returned file_uuid to persist the table as a sidebar artifact.

## Tips

- If a model has no hosted API, note "Self-host" and link to HuggingFace or Ollama.
- If the AA Intelligence Index is unavailable, fall back to LMSYS Elo and note the
  source in the disclaimer.
- Prefer concrete numbers; use "≈" only when the source gives a range.
- Keep the table to 10–14 rows.
- Verify every "Buy / Download" link goes to a page where the human adjudicator can actually sign up
  or pull the model, not just a blog post.
