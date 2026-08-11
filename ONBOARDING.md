# Getting Started with Gas City: Field Notes for New Users

These are practical notes from a first real build with Gas City (`gascity`), `beads`, `gascity-packs`, and `mathcity`. They're written for someone about to set up their first city from scratch. Nothing here is official Gas City documentation — it's one user's hard-won lessons, written up so the next person doesn't have to relearn them. A few items are flagged below as unverified and worth an independent fact-check before you treat them as gospel.

## 1. Build from source, and keep your build separate

Build `gascity`, `beads`, `gascity-packs`, and `mathcity` from source rather than relying on whatever version a package manager hands you. Keep the source checkouts in their own repo/directory that you manage yourself, separate from any city you actually run.

Two traps to avoid on your first city:

- **Don't run Gas City on itself to start.** Bootstrapping your first city inside the `gascity` repo itself adds a layer of confusion you don't need while you're still learning the tool.
- **Don't create your own beads inside `gascity` to start.** Let Gas City manage its own beads (the issues it creates for its own internal work) and keep those separate from any beads you create for your own projects. Don't try to transport or merge beads between the two. This matters because a `bd` (beads) install from Homebrew, apt, or similar may already be on your `PATH` — be deliberate about which `beads` binary and which beads database your city is actually pointing at, or you can end up mixing state you didn't mean to mix.

### Suggested skills: automate your "from source" updates

Rather than re-running the build steps by hand, create four skills:

- `update-gascity-from-source`
- `update-beads-from-source`
- `update-gascity-packs-from-source`
- `update-mathcity-from-source`

The binary skills should clear out old binaries before rebuilding (so you're
never accidentally running a stale binary alongside a fresh one). The pack
skills should verify the city imports the intended local source checkout:
`gascity-packs` for non-mathcity packs, `mathcity` for the standalone mathcity
pack.

## 2. Read the docs — all of them — before your first run

Have an agent read through the documentation carefully before you kick off your first real run. In particular:

- **`gascity/REQUIREMENTS.md`** — this is the normative requirements document for the base build methodology (the `build-base` workflow contract that every methodology pack builds on top of). It's easy to miss on a first pass; point your agents at it explicitly.
- **The various `REQUIREMENTS.md` files scattered through the repos** — several packs ship their own, and they're easy to miss the first time through. Worth a deliberate sweep rather than assuming the top-level README covers everything.
- **The `README.md` for the `gascity-packs/gascity` pack** and the top-level `gascity-packs/README.md`.

If you have access to an active development fork of `gascity`/`gascity-packs`, read that version of the docs too. The released docs can lag behind the current development workflow.

### A note on naming, because it will confuse you

The naming in this ecosystem is genuinely confusing, so go in aware of it:

- There is a pack literally called **`gascity`** inside the `gascity-packs` repo. This is essential — it's the base build methodology pack (`build-base` / `build-basic`) that almost everything else builds on. Don't confuse "Gas City the product" with "the `gascity` pack."
- The main `gascity` repository also has its own hidden **"base pack"** layer (Gas City's builtin core pack, providing mechanical housekeeping orders) that's separate again from the `gascity` pack in `gascity-packs`.

Expect to say "gascity" three different ways in one sentence and mean three different things. It gets easier once you've internalized the layering, but budget time for it.

## 3. Start with the `gascity` pack, and only that pack

Your first import should be the base **`gascity`** pack (`gc import add --name gc https://github.com/gastownhall/gascity-packs.git//gascity`) and nothing else. It's the most seasoned, best-documented code in the ecosystem, and every other build-methodology pack (bmad, compound-engineering, superpowers, gstack) is built as an extension of it.

**Avoid the `gastown` pack when you're starting out.** It is an emulator layer for older Gas Town-style coordination, and field reports indicate it can be confusing or fragile for first-time setup. Treat it as an advanced compatibility pack until its current status is independently verified.

## 4. Suggested directory layout

A structure that worked well:

```
~/mygascity/
├── mygascity-innards/       # `gascity` itself installs here — assets, state,
│                             #  and other internals unrelated to any repo
└── mygascity-repos/
    ├── repo1/                # adopted via `gc rig add` / `gc adopt`
    ├── repo2/                # adopted
    └── ...
```

Keeping the Gas City internals (`-innards`) separate from the actual repos you're working on (`-repos`) makes it much easier to reason about what's a Gas City artifact versus what's your actual project.

## 5. Hooking up a repository

To do anything useful, you need to hook up a repository — this is done with `gc rig add` in current documentation. A repo doesn't need to be anything special to be adopted.

**Warning:** adopting a repo rewrites working files and introduces an unusual worktree structure. Consider adopting a throwaway clone rather than a repo you care about, at least the first time, until you understand the current rig layout.

## 6. Starting the city

Bring the city up with `gc start`. Skip `gc dashboard` — as of this writing it's broken and not worth relying on.

Once the city is running, start a Claude Code session at the city root and run the `/mayor` skill (all Gas City packs ship skills that are symlinked into your user-level `.claude/skills` folder, so `/mayor` should be available once the `gascity` pack is imported). From there, work through `gascity/README.md` again and do a small "hello world" build to confirm everything is wired up correctly before attempting real work.

## 7. Configuration

Don't hand-edit `.toml` files (`city.toml`, `pack.toml`, and friends). Do all configuration changes through the `gc` CLI. More generally: prefer the `gc` command line tool over manual file edits for essentially everything.

## Open questions / to verify

A few things above come from field experience rather than the documentation and are worth an independent pass:

- Exact command name and current behavior of the repo-adoption step (`gc rig add` vs. `gc adopt`) and whether the worktree/file-rewriting behavior described above is expected or a known issue.
- Current status of `gc dashboard` — confirm it's still broken before pointing new users away from it.
- Current status/reputation of the `gastown` pack — confirm whether it's still considered broken or has since been fixed or deprecated.

---

*Adapted from internal onboarding notes. Corrections and clarifications welcome.*
