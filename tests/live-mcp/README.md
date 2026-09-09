# live-mcp — exercise the mctl MCP surface against a RUNNING city

These are not pytest tests. They talk JSON-RPC over stdio to a real
`bin/mctl mcp serve`, against a real city, so they can catch things a fixture
cannot: a rig root that does not exist, a store that will not open, a formula
that plans in isolation but is not catalogued on the host.

## The one thing that will waste your afternoon

    MCTL_MCP_CLIENT_CLASS=internal

`visible_tools()` returns `()` for an unarmed **external** client, and
`tools/list` then reports `{"tools": []}` with **no diagnostic**. That is
indistinguishable from a server whose registry failed to load. The Mayor's
projected MCP sets this env var; an ad-hoc probe must set it too, or it will
see zero of the 56 registered tools and look broken.

## Usage

    export MCTL_MCP_CLIENT_CLASS=internal
    export MCTL_CITY="$HOME/HQ"          # --city
    export MCTL_RIG=mathcity             # --rig  (omit for city scope)

    python3 mcpcall.py --list                          # tool roster
    python3 mcpcall.py beads_list '{"status":["open"]}'
    python3 mcpcall.py formula_dispatch '{"formula":"brief-archive-sweep","dry_run":true}'

    python3 sweep.py                     # every catalogued formula, dry-run

`sweep.py` keeps ONE session open for the whole sweep, so a failure is
attributable to the formula rather than to server startup.

Mutating tools are dry-run by default. `sweep.py` never leaves dry-run.

See [../../docs/KOLCHIN-TRACKER-CAMPAIGN.md](../../docs/KOLCHIN-TRACKER-CAMPAIGN.md)
for what these found on kolchin.
