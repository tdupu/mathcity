"""Screen renderers for the briefs dashboard.

One module per screen, because that is how they change. Each exports pure
functions returning HTML strings; none of them calls `mctl_core` or the MCP
client directly -- `app.py` fetches, screens render.
"""
