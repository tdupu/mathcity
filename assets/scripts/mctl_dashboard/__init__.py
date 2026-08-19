"""The MathCity operator dashboard (plan Slice 8).

A browser front end for the queue the repo owner actually asked about: 185
briefs, 7 ever adjudicated, 104 pending, readable only as raw JSON from a CLI.

It is a *client* of the Slice 6 typed MCP surface and nothing else. It holds no
domain logic, parses no bead store, and reads no brief file. Every fact on
every page arrived through `tools/call`, which is what makes "the dashboard is
not a second parser" (plan §2) true rather than aspirational.

Layout:

    client.py   the MCP client -- stdio subprocess or in-process, one allowlist
    review.py   which diagnostic codes may not be presented as actionable
    preview.py  dry-run previews, their fingerprints, and staleness
    render.py   HTML
    app.py      routes
    server.py   http.server glue
"""

__all__ = ["app", "client", "preview", "render", "review", "server"]
