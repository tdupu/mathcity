# Mathlib and Stacks search tools

Discover tools and their input schemas in the current host/session before use.
Server registration or a CLI's “Connected” label is not proof that this session
can call it. Keep the selected workspace, claim IDs and searched channels in the
handoff; never bounce between `lean-search` and `search-mathlib` after a channel
has failed. Installation is a separate requested operation via `install-loogle`
when installed; ordinary proof/search work uses available tools or falls back.

## LeanSearch, Loogle and local Lean

[lean-lsp-mcp](https://github.com/oOo0oOo/lean-lsp-mcp) supplies these observed
tools; host prefixes and versioned schemas may differ:

| Purpose | Tool and example arguments |
|---|---|
| Natural-language candidate search | `lean_leansearch(query="An injective idempotent map is the identity", num_results=5)` |
| Name/type-pattern search | `lean_loogle(query="add_comm", num_results=8)` |
| Inspect the actual goal | `lean_goal(file_path="/absolute/project/Target.lean", line=4, column=3)` |
| Compiler diagnostics | `lean_diagnostic_messages(file_path="/absolute/project/Target.lean")` |

Use schema-defined positions and read tool payload errors, partial flags and
diagnostic severities. An MCP transport success alone is not Lean success. A
clean diagnostic response does not certify target coverage, trust or fidelity.

For a requested setup, configure the host's stdio MCP entry with command `uvx`,
arguments `["lean-lsp-mcp"]`, and `LEAN_PROJECT_PATH` pointing at the chosen Lake
workspace; consult the current server documentation and record its resolved
version. The tested 0.30.0 server with leanclient 0.13.2 requires Lean >=4.24 for
LSP. Do not upgrade an older project's pin to satisfy optional tooling. Use its
working Lean CLI instead; a separate compatible search workspace must never be
reported as validation of the older target.

Without MCP, use local source search and compiled probes in [tools.md](tools.md).
Hosted Loogle also exposes `https://loogle.lean-lang.org/json?q=<encoded-query>`.
The tested LeanSearch API accepts POST `https://leansearch.net/search` with JSON
`{"query":["your mathematical query"],"num_results":"5"}`. Validate actual response
shape; report service/schema failures separately from a successful empty search.
Do not claim exhaustive coverage or novelty from either result. Search hits may
target a newer Mathlib: inspect their actual types and compile applications under
the target pin before reuse.

## Palomar Registry

Palomar is a public registry of Lean-verified formalizations. Its human-facing
site is a JavaScript explorer; machine searches must use the public data origin
described by `https://palomar-registry.org/llms.txt`:

- `https://data.palomar-registry.org/recent.json` is a bounded newest-results
  projection, useful for browsing but not exhaustive search.
- `https://data.palomar-registry.org/schema-v3.json` describes the registered
  record contract.
- `https://data.palomar-registry.org/search/stopwords.json` and
  `/search/t/{word}/head.json` provide the word-index search surface after
  query normalization and stopword removal.
- `/entries/PALOMAR-YYYY-MM-DD-NNNNNN-vN.json` and
  `/versions/PALOMAR-YYYY-MM-DD-NNNNNN.json` provide versioned records. Use
  an explicit integer version in citations; an id-only lookup floats.

Keep Palomar queries bounded: the public search contract limits a query to 4,096
characters and 20 distinct normalized words. Follow the advertised index or
record links instead of inventing posting-page paths, and treat transport,
schema, stale-data and zero-result cases separately. Preserve the permanent id,
integer version, title, theorem names, status/trust, source repository, source
commit, project path and the exact record URL. Do not scrape the browser UI or
claim that a registered theorem is available under the target project's imports.

After selecting a result, inspect the recorded source at its pinned commit and
compile a small application under the target Lean/Mathlib pin. If the source
cannot be checked out or the dependency pin differs, return the Palomar record
as an external candidate with the mismatch recorded.

## Tau Ceti

Tau Ceti is a downstream Lean library, not a Mathlib search index. Search its
source at an exact Git commit, preferably from a local checkout, and read its
`lean-toolchain`, `lake-manifest.json`, and repository instructions before
using a declaration. The primary repositories are:

- `https://github.com/TauCetiProject/TauCeti` for AI-authored Lean code;
- `https://github.com/TauCetiProject/TauCetiRoadmap` for human-owned roadmap
  specifications and targets;
- `https://github.com/TauCetiProject/TauCetiReview` for review rubrics and
  review machinery, not theorem statements.

Use exact file/module paths and `git rev-parse HEAD` receipts for source hits.
The generated API site at `https://taucetiproject.github.io/TauCeti/docs` is
best-effort navigation; when using it, read `/docs/SOURCE_SHA` and keep that
SHA with the result. A roadmap item, generated documentation page or review
verdict is not a Lean certificate. For a declaration intended for reuse,
inspect the source snapshot and compile a focused application under the target
workspace. Tau Ceti's Mathlib dependency can move independently, so a passing
check in a current Tau Ceti checkout does not validate an older target pin.

For Tau Ceti contribution work, hand the source result to `using-taucetipowers`
and preserve its roadmap, coordination and review gates. Search evidence alone
does not authorize a branch, issue, pull request or roadmap edit.

## Stacks Project

Installed `search-stacks` owns Stacks lookup and optional server setup. Discover
`get_tag(tag, include_proof)`, `search_stacks(query, max_results)` and
`tag_info(tag)` on the connected Stacks MCP. Search bounded keywords, then fetch
the selected tag's statement and, when present, proof. For example, `00N3` is a
definition, `0BBY` a lemma with proof; not every tag denotes a theorem.

If MCP or its setup skill is absent, retrieve public HTML directly:

- `https://stacks.math.columbia.edu/data/tag/00N3/content/statement`
- `https://stacks.math.columbia.edu/data/tag/0BBY/content/full`
- `https://stacks.math.columbia.edu/search?query=<encoded-query>`

Check content, not just HTTP status. Search previews may identify an enclosing
section, and parsed result counts can be incomplete. Verify the selected tag's
actual title/type, statement, hypotheses and proof; preserve tag URL, retrieval
date and source snapshot. A missing proof is reported, never inferred.
The local Stacks server can encode network or parsing failures in a successful
tool response. Confirm an explicit zero-result page through direct HTTP before
accepting an empty search; otherwise report retrieval/parse uncertainty.

Stacks provides informal source evidence, not a Lean certificate or Mathlib name.
Pass the retrieved claim through `lean-extract-claims`, `lean-align-statement`
and `lean-search`; record any missing formal prerequisites. Only `lean-verify`
plus `lean-fidelity` can promote its checked translation to FORMALIZED.
