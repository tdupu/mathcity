# Mathcity Installation Guide

Parent: [../SETUP.md](../SETUP.md)

This guide installs the standalone `mathcity` pack into a Gas City city. The
pack provides the mathematical brief pipeline, review skills, gate policy,
orders, and math-domain subpacks.

## Prerequisites

Install these before importing the pack:

| Tool | Purpose |
|---|---|
| `gc` | Gas City command line and supervisor |
| `bd` | Beads issue tracker |
| Dolt | Beads storage backend |
| `tmux` | Agent session management |
| Git | Source and pack resolution |

Optional math capabilities may also need Magma, SageMath, or proof-assistant
tooling depending on which subdomain skills you use.

## Create A City

```sh
gc init <city-root>
cd <city-root>
gc start
bd init
gc doctor
```

Use `gc config show` to inspect the composed config. `gc config check` is not a
current command.

## Import Gas City Base Packs

Mathcity formulas extend the public Gas City base pack and route some work to
Gas City role agents. Add the city-scope base pack and the rig-scope roles pack:

```sh
cd <city-root>
gc import add --name gc https://github.com/gastownhall/gascity-packs/tree/main/gascity \
  --version sha:3b3b89f2011e06d84459aa7bea1552382f13930a
```

Then add the rig roles to `city.toml` so every rig has the `gc.*` worker
sessions available:

```toml
[defaults.rig.imports.gc]
source = "https://github.com/gastownhall/gascity-packs/tree/main/gascity/roles"
version = "sha:3b3b89f2011e06d84459aa7bea1552382f13930a"
```

## Import Mathcity

After the registry entry exists, prefer the registry handle:

```sh
gc pack registry refresh
gc import add --name mathcity mathcity
```

Until then, import the GitHub source directly:

```sh
gc import add --name mathcity https://github.com/<github-owner>/mathcity/tree/main
```

Mathcity also needs rig-scope coverage for orders that run once per rig. Add
the same pack source under `[defaults.rig.imports.mathcity]`:

```toml
[defaults.rig.imports.mathcity]
source = "https://github.com/<github-owner>/mathcity/tree/main"
```

Run the import installer after editing:

```sh
gc import install
gc import check
gc import status
```

## Add A Rig

Register each research repository as a rig:

```sh
git clone https://github.com/<github-owner>/<repo>.git <repo-root>
cd <repo-root>
gc rig add .
gc rig list
```

The default rig imports above compose mathcity and Gas City roles into new rigs.

## Verify The Brief Pipeline

From the city directory:

```sh
gc formula list | grep brief
gc order list | grep brief
gc session list
```

Expected mathcity surfaces include `brief-prep`, `math-brief-prep`,
`build-basic-briefed`, `brief-shuffle-fast-drain`, `brief-review-patrol`, and the
`mathcity.brief-operator` pool.

## Development Checkout

For pack development, point a test city at a local checkout instead of the
published source:

```toml
[imports.mathcity]
source = "/path/to/mathcity"

[defaults.rig.imports.mathcity]
source = "/path/to/mathcity"
```

After editing pack content, run:

```sh
gc import install
gc import check
```

Run the focused Python tests from the checkout:

```sh
python3 -m pytest \
  tests/stuck-bead-watch/test_stuck_bead_watch.py \
  tests/tail-end-detector/test_tail_end_detector.py
```

## Registry Publishing

The registry publish command follows the workflow at
<https://registry.gascity.com/publish>. It requires a clean Git checkout whose
current HEAD is committed and pushed to its upstream branch.

Authenticate once:

```sh
gc pack registry login
```

For headless or CI environments, provide `GC_REGISTRY_TOKEN` instead. GitHub
Actions can also publish through the registry's OIDC flow.

Dry-run the package before publishing:

```sh
gc pack registry publish /path/to/mathcity --name mathcity --dry-run
```

Then publish the same pushed commit:

```sh
gc pack registry publish /path/to/mathcity --name mathcity
```

The publish name must match `[pack].name` in `pack.toml`; this pack declares
`mathcity`.

## Troubleshooting

If formulas or orders are missing, run:

```sh
gc import status
gc import check
gc formula list
gc order list
```

If `build-basic-briefed` exists but worker sessions are missing, confirm the
rig-scope Gas City roles import is present in `city.toml` and run
`gc import install`.

If brief files remain in `.beads/briefs/.pile/`, inspect:

```sh
gc order show brief-shuffle-fast-drain
gc session list --template mathcity.brief-operator
gc order history | grep brief
```

No code should ship from the brief pipeline without an explicit human verdict.
