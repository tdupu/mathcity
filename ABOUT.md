# Mathcity

**A shared toolkit for AI-assisted mathematics research — skills, formulas, MCPs, and workflows you can plug into your own setup.**

Mathcity is a [Gas City](https://github.com/gastownhall/gascity) pack built specifically for working mathematicians. If you haven't encountered Gas City before, the quickest orientation is Steve Yegge's [Welcome to Gas Town](https://steve-yegge.medium.com/welcome-to-gas-town-4f25ee16dd04). The short version: Gas City is an orchestrator — a team of agents that coordinate to carry out work, with human oversight, and "slop prevention". The building blocks are **skills**, **formulas** (TOML workflow templates that compose skills and agents into structured sequences: plan → implement → review → brief), and **orchestration** (the coordination layer that routes work between agents, tracks state, handles crashes, and surfaces decisions that need a human). A **pack** is a composable bundle of these — agents, skills, formulas, hooks, and configuration — that you can import into any Gas City setup. 

Math research involves a lot of structured, repetitive work around computation, formalization, literature search, and database management. Mathcity encodes those workflows as shareable packs and skills so you don't have to reinvent them.

Because [Gas City](https://github.com/gastownhall/gascity) lets you choose the model powering each agent, Mathcity is not tied to any particular harness or provider. It works with [OpenCode](https://opencode.ai/), [oh-my-pi](https://github.com/can1357/oh-my-pi), [Ollama](https://ollama.com/), and other open-source agent harnesses as cheaper or self-hosted alternatives to Codex and Claude Code, and you can route through [OpenRouter](https://openrouter.ai/) to swap in whatever model fits your budget or needs.

Mathcity is also designed to be modular. You don't have to import all of it — you can pull in only the subdomains you actually use (just LMFDB, just proof-assist, just the brief system, etc.) and ignore the rest. And if you don't like the way something is done, you can import your own version of that piece instead; packs compose, so swapping out a subdomain or overriding a skill doesn't require forking the whole thing. Some of this composability will have growing pains at first, but that's part of what early testing is for.

It is early, actively under construction, and looking for people to test what's here and contribute their own workflows.

---

## What's already here

### Automated review

One of the more distinctive things in Mathcity is the automated review pipeline. Before a piece of work goes to you for a decision, it gets checked:

- **Code gates**: Was the code actually tested? Is there evidence of a test run?
- **Experiment gates**: Is the experiment well-specified? Is there a clear question being asked and a sensible methodology?
- **LaTeX gates**: Does every claim have a pinpoint citation? If not, the reviewer searches for the correct citation and fills it in.

This is done through a *brief system* — a structured decision pipeline where agents produce a document summarizing what they did and what decision you need to make, which you adjudicate. The underlying insight is that *we are the bottleneck* in research. There are many decisions to be made — about branches, experiments, conjectures, proofs — and the system's job is to bring only the ones that genuinely require judgment to the human, and to automatically reject or return anything that isn't ready. If code comes back untested, it goes back without reaching you. If an experiment only checked a conjecture on trivial examples, or on examples that aren't properly in scope, it goes back. These are the no-brainers — cases where the right answer is obvious and the decision shouldn't consume your attention.

No-brainer decisions are collapsed into a single one-line block so they're visible but not demanding. Substantive ones get a full presentation. And crucially, after accumulating N no-brainers of the same kind, the system adapts: the pattern becomes a gate, the gate becomes policy, and future work of that shape gets caught earlier. The no-brainer system is also how the workflow improves — each cluster of repetitive throwbacks is a signal that a gate is missing, and you can file a PR to add it.

The upshot is that by the time something reaches you, the mechanical checks have already run. You're making research decisions, not playing gatekeeper on whether tests were written.

### Computational tools

The **Magma subdomain** has skills for creating and maintaining Magma packages, converting Magma scripts to and from Jupyter notebooks, profiling code, and managing issue tracking for computational experiments.

The **LMFDB subdomain** is probably the most developed. It has skills for creating new LMFDB object types, managing the full data pipeline (Magma → text → database → LMFDB webpage), configuring servers and pipelines, searching the LMFDB, and pushing/pulling data from the server. If you maintain a dataset in the LMFDB or are thinking about adding one, this is the part to look at.

### Proof assistant tools

The **proof-assist subdomain** wraps Lean 4 / Mathlib4 search via [Loogle](https://loogle.lean-lang.org), the Stacks Project (tag lookup and keyword search), arXiv (ID or keyword → title / abstract / BibTeX), and Semantic Scholar (paper search by keyword or title). These are available as skills you can invoke from your own agent workflows.

Work in progress: adapting the UCLA TEAM and IMProof systems for proof assistant formalization workflows, integrating [Patcher](https://github.com/Patcher/span)'s span tool for converting between LaTeX and Lean blueprints, and connecting [firstproof](https://github.com/Tomodovodoo/firstproof) — an autonomous subagent/orchestrator system using lean-lsp-mcp and Aristotle for proof solving.

### Dev tools

The dev subdomain has skills for auditing recent work, checking build hygiene, checking that plans are well-formed, and a math-specific skill creator for extending the system.

---

## What we're looking for

Mathcity is most useful if it has workflows for the things mathematicians actually do. Right now the coverage skews toward Magma + LMFDB because that's what's been built so far. Gaps include:

- **SageMath users** — there's no Sage subdomain yet
- **Macaulay2 developers** — no M2 subdomain yet either
- **Blueprint contributors** — [Patcherlab Span](https://github.com/Patcher/span) integration and other LaTeX ↔ Lean blueprint tooling improvements are works in progress and could use people with experience in this space
- **Lean / Mathlib contributors** — the proof-assist tools exist but need people to use and stress-test them, and the formalization workflow integrations are works in progress
- **Number theorists with LMFDB datasets** — the pipeline is there; does it work for your data type?
- **Anyone with a workflow they keep redoing by hand** — if you have a structured task you do repeatedly (reformatting bibliography entries, converting Magma output to LaTeX tables, checking referee report citations, whatever), it's probably wrappable as a skill

To contribute a workflow, you don't need to understand the full Gas City stack. A skill is just a `SKILL.md` file describing what an agent should do when invoked. The existing skills in `mathcity/subdomains/*/skills/` are good examples of the format. The dev skill `skill-creator-math` exists specifically to help you write new ones.

---

## Getting started

**Prerequisites:** [Gas City](https://github.com/gastownhall/gascity) installed and a city running.

**Import mathcity:**

```sh
gc pack registry refresh
gc import add --name mathcity tdupu/mathcity
gc import install
```

Full setup — including the brief pipeline, pool configuration, and subdomain selection — is in [docs/INSTALL.md](./docs/INSTALL.md). The onboarding walkthrough (for using the system once it's running) is in [ONBOARDING.md](./ONBOARDING.md).

If you want to contribute a skill or try out an existing workflow and run into friction, please file an issue. The whole point of this phase is to find out where things break.

---

## Architecture in one paragraph

Mathcity extends the gascity `build-basic` factory with a `build-basic-briefed` variant that replaces the publish step with brief production. When a branch or experiment closes, an agent prepares a brief, gates are checked, and the brief goes into a stack for human adjudication. On approve, the normal publish path runs; on reject or revise, a follow-up bead is created. The brief system is in `mathcity/subdomains/brief-system/`; the math-domain tools (Magma, LMFDB, proof-assist, LaTeX) are in `mathcity/subdomains/`. See [README-skills.md](./README-skills.md) for a complete skill inventory.
