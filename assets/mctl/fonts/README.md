# Dashboard fonts

The adopted briefs-dashboard design specifies **Cormorant Garamond** (headings,
600 weight) and **Lora** (body). Neither is installed on a typical machine and
neither shipped with the design handoff, so the dashboard vendors them here and
serves them from the loopback server.

**This directory is currently empty**, which is a supported state: the
dashboard renders in Georgia, which leads the fallback list in
`mctl_dashboard/theme.py`. Nothing is broken; the typography is simply an
approximation of the design rather than the design.

## Adding them

Drop these three files in:

```
CormorantGaramond-SemiBold.woff2
Lora-Regular.woff2
Lora-Italic.woff2
```

No code change is needed. `theme.font_faces()` emits an `@font-face` rule only
for files that are actually present, so the typography appears on the next page
load — and, equally, an absent file never puts a 404 in the server log.

Both families are licensed under the **SIL Open Font License 1.1**, which
permits redistribution. Add the upstream `OFL.txt` for each alongside the
`.woff2` files when you add them.

## Why vendored rather than fetched

`GC1` forbids a build step or a CDN and `GC2` keeps the dashboard bound to
`127.0.0.1`. A remote font URL would quietly break both — and would leak which
rig is being read to whoever serves the font, on a tool whose entire premise is
that it reads a local bead store and talks to nobody.
