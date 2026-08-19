"""The city-root HQ store is addressable — and only it, never its aliases.

`<city-root>/.beads` is a real bead store: it has a `config.yaml`, its own Dolt
database, and on the live city 80 decision beads (53 closed), including the
process-policy briefs. It was invisible to every `--all-rigs` read because
`registered_rigs()` enumerated `city.toml`'s rig list and the HQ store is not
in it — `mctl briefs list --rig gt` answered `MCTL_CONTEXT_UNKNOWN_RIG`.

It is made addressable under a **reserved** identifier rather than by adding it
to `city.toml`: that file is owned by pack updates, not hand-edits, and the HQ
store is not a rig — it is the city's own store. Calling it a rig in
configuration would be a lie that the next pack update would overwrite.

**The trap this file exists to close.** Several `.beads` directories under the
city root are not stores at all — they hold a `briefs/` directory and nothing
else, no `config.yaml` and no database — so a `bd` invocation inside them walks
up and reads the HQ store. On the live city there are five of these
(`mathcity.brief-operator`, `-1`, `-3`, `-5`, `-8`), and a prior audit that
enumerated directories rather than configuration counted HQ's 80 beads six
times over. Reaching 280 that way would look exactly like reaching it
correctly. So the tests below assert both halves: the total gains the HQ
store's briefs *once*, and creating any number of alias directories does not
move the roster or the total by a single row.

Note that "has a `config.yaml`" is a precondition, not a sufficient discriminator
for aliasing in general — the live city also has `gascity-packs-briefpath/.beads`,
which *does* carry a `config.yaml` yet reads the gascity-packs rig's store. That
is why enumeration here is configuration-driven (the `city.toml` roster plus the
single reserved city-root entry) and never a filesystem walk.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import multi_rig
from mctl_core.context import HQ_RIG_ID, ContextError, resolve_city, resolve_context
from mctl_core.mcp_server import MctlMcpServer

MCTL = SCRIPTS_ROOT / "mctl.py"

#: Bead ids in the HQ store get their own prefix so a row's store is provable
#: from the row itself — the same reason multi_rig gives each rig one.
HQ_PREFIX = "hq-"

#: The live shapes: a `.beads` holding only `briefs/`, with no `config.yaml`
#: and no database, which therefore reads whatever store lies above it.
ALIAS_DIRECTORIES = (
    "mathcity.brief-operator",
    "mathcity.brief-operator-1",
    "mathcity.brief-operator-3",
    "mathcity.brief-operator-5",
    "mathcity.brief-operator-8",
    "gascity-packs-briefpath",
)

#: Deliberately without `dolt.mode: server`: liveness probing is a separate
#: contract with its own tests, and declaring server mode here would make every
#: test in this file depend on a running data plane.
HQ_CONFIG = "prefix: hq\nissue-prefix: gt\n"


def with_hq_store(fixture: multi_rig.MultiRigCity) -> multi_rig.MultiRigCity:
    """Give the fixture city its own city-root bead store, as ~/gt has."""
    multi_rig._populate(fixture.city_root, HQ_PREFIX)
    (fixture.city_root / ".beads" / "config.yaml").write_text(HQ_CONFIG, encoding="utf-8")
    fixture.env[f"MCTL_BEADS_FIXTURE_{HQ_RIG_ID}"] = str(
        fixture.city_root / ".beads" / "issues.jsonl"
    )
    return fixture


def with_alias_directories(fixture: multi_rig.MultiRigCity) -> multi_rig.MultiRigCity:
    """Reproduce the config-less `.beads` directories that alias the HQ store."""
    for name in ALIAS_DIRECTORIES:
        alias = fixture.city_root / name / ".beads" / "briefs"
        alias.mkdir(parents=True, exist_ok=True)
        (alias / "placeholder.md").write_text("# not a store\n", encoding="utf-8")
    return fixture


def roster(fixture: multi_rig.MultiRigCity) -> tuple[str, ...]:
    scope = resolve_city(
        fixture.city_root, city=fixture.city_root, require_runtime_city=True, env=fixture.env
    )
    return tuple(rig.name for rig in scope.rigs)


def server(fixture: multi_rig.MultiRigCity) -> MctlMcpServer:
    instance = MctlMcpServer(
        default_city=fixture.city_root,
        default_rig=None,
        client_class="internal",
        env=dict(fixture.env),
        cwd=fixture.city_root,
    )
    instance.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
    return instance


_CALL_ID = [500]


def payload(instance: MctlMcpServer, name: str, arguments: dict | None = None) -> dict:
    _CALL_ID[0] += 1
    response = instance.handle(
        {
            "jsonrpc": "2.0",
            "id": _CALL_ID[0],
            "method": "tools/call",
            "params": {"name": name, "arguments": dict(arguments or {})},
        }
    )
    return response["result"]["structuredContent"]


def rig_entry(city: dict, rig_id: str) -> dict:
    for entry in city["rigs"]:
        if entry["rig_id"] == rig_id:
            return entry
    raise AssertionError(f"{rig_id} is absent from the city-wide answer: {city['rigs']}")


def run_mctl(fixture: multi_rig.MultiRigCity, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(fixture.env)
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=fixture.city_root,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def read_jsonl(path: Path) -> dict[str, dict]:
    return {
        json.loads(line)["id"]: json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    }


# --- the store becomes addressable ------------------------------------------


def test_the_city_root_store_is_enumerated_under_the_reserved_id(tmp_path: Path):
    fixture = with_hq_store(multi_rig.build(tmp_path))

    assert roster(fixture) == (*multi_rig.ALL_RIGS, HQ_RIG_ID)


def test_resolving_the_reserved_id_yields_a_context_rooted_at_the_city_root(tmp_path: Path):
    fixture = with_hq_store(multi_rig.build(tmp_path))

    context = resolve_context(
        fixture.city_root,
        city=fixture.city_root,
        rig=HQ_RIG_ID,
        require_runtime_city=True,
        env=fixture.env,
    )

    assert context.rig_id == HQ_RIG_ID
    assert context.rig_root == fixture.city_root
    assert context.city_root == fixture.city_root
    assert HQ_RIG_ID in context.registered_rigs


def test_the_city_wide_total_gains_exactly_the_hq_stores_briefs(tmp_path: Path):
    """280, not 200 — and by one store's contribution, not six copies of it."""
    without = multi_rig.build(tmp_path / "without")
    with_hq = with_hq_store(multi_rig.build(tmp_path / "with"))

    before = payload(server(without), "briefs_list", {"all_rigs": True})
    after = payload(server(with_hq), "briefs_list", {"all_rigs": True})

    hq_only = payload(server(with_hq), "briefs_list", {"rig": HQ_RIG_ID})
    assert hq_only["briefs"], "the HQ fixture store must hold briefs to be worth counting"
    assert len(after["briefs"]) == len(before["briefs"]) + len(hq_only["briefs"])
    assert rig_entry(after, HQ_RIG_ID)["counts"]["briefs"] == len(hq_only["briefs"])


def test_every_hq_row_is_tagged_with_the_store_it_came_from(tmp_path: Path):
    fixture = with_hq_store(multi_rig.build(tmp_path))

    city = payload(server(fixture), "briefs_list", {"all_rigs": True})

    hq_rows = [brief for brief in city["briefs"] if brief["rig_id"] == HQ_RIG_ID]
    assert hq_rows, "the HQ store contributed no rows"
    for brief in hq_rows:
        assert brief["bead_id"].startswith(HQ_PREFIX)


# --- the aliases must never inflate anything --------------------------------


def test_alias_directories_are_not_enumerated(tmp_path: Path):
    fixture = with_alias_directories(with_hq_store(multi_rig.build(tmp_path)))

    names = roster(fixture)

    assert names == (*multi_rig.ALL_RIGS, HQ_RIG_ID)
    for alias in ALIAS_DIRECTORIES:
        assert alias not in names


def test_alias_directories_do_not_inflate_the_city_wide_total(tmp_path: Path):
    """Six aliases each reporting HQ's beads is how 280 gets reached by accident."""
    plain = with_hq_store(multi_rig.build(tmp_path / "plain"))
    aliased = with_alias_directories(with_hq_store(multi_rig.build(tmp_path / "aliased")))

    without_aliases = payload(server(plain), "briefs_list", {"all_rigs": True})
    with_aliases = payload(server(aliased), "briefs_list", {"all_rigs": True})

    assert len(with_aliases["rigs"]) == len(without_aliases["rigs"])
    assert len(with_aliases["briefs"]) == len(without_aliases["briefs"])


def test_an_alias_directory_is_not_addressable_as_a_rig(tmp_path: Path):
    fixture = with_alias_directories(with_hq_store(multi_rig.build(tmp_path)))

    try:
        resolve_context(
            fixture.city_root,
            city=fixture.city_root,
            rig=ALIAS_DIRECTORIES[0],
            require_runtime_city=True,
            env=fixture.env,
        )
    except ContextError as error:
        assert error.code == "MCTL_CONTEXT_UNKNOWN_RIG"
    else:
        raise AssertionError("an alias directory resolved as a rig")


# --- the reserved id stays reserved, and stays honest ------------------------


def test_a_city_root_without_a_bead_store_has_no_hq_entry(tmp_path: Path):
    """A city with no store of its own must not grow a phantom rig."""
    fixture = multi_rig.build(tmp_path)

    assert roster(fixture) == multi_rig.ALL_RIGS


def test_a_city_root_beads_directory_without_a_config_is_not_a_store(tmp_path: Path):
    """`config.yaml` is the precondition — a bare `.beads/` is not a store."""
    fixture = multi_rig.build(tmp_path)
    (fixture.city_root / ".beads" / "briefs").mkdir(parents=True)

    assert roster(fixture) == multi_rig.ALL_RIGS


def test_a_registered_rig_named_hq_wins_and_is_not_duplicated(tmp_path: Path):
    """If configuration ever claims the id, configuration wins — exactly once."""
    fixture = with_hq_store(multi_rig.build(tmp_path))
    (fixture.city_root / "city.toml").write_text(
        multi_rig.CITY_TOML + f'\n[[rigs]]\nname = "{HQ_RIG_ID}"\ndb = "configured_hq"\n',
        encoding="utf-8",
    )

    names = roster(fixture)

    assert names.count(HQ_RIG_ID) == 1
    scope = resolve_city(
        fixture.city_root, city=fixture.city_root, require_runtime_city=True, env=fixture.env
    )
    entry = next(rig for rig in scope.rigs if rig.name == HQ_RIG_ID)
    assert entry.db == "configured_hq"


def test_a_degraded_hq_store_is_a_named_row_not_a_smaller_total(tmp_path: Path):
    """A city-wide answer that silently drops HQ is worse than no answer."""
    fixture = with_hq_store(multi_rig.build(tmp_path))
    fixture.env[f"MCTL_BEADS_FIXTURE_{HQ_RIG_ID}"] = str(tmp_path / "no-such-hq-store.jsonl")

    city = payload(server(fixture), "briefs_list", {"all_rigs": True})

    entry = rig_entry(city, HQ_RIG_ID)
    assert entry["ok"] is False
    assert entry["reason"], "a degraded store must say why"
    assert entry["rig_root"] == str(fixture.city_root)
    for rig in multi_rig.READABLE_RIGS:
        assert rig_entry(city, rig)["ok"] is True
    codes = {item["code"] for item in city["diagnostics"]}
    rigs_named = {
        item.get("facts", {}).get("rig_name") for item in city["diagnostics"]
    }
    assert codes, "the degraded store must carry a typed diagnostic"
    assert HQ_RIG_ID in rigs_named


# --- mutation stays scoped to the store that owns the brief ------------------


def test_adjudicating_an_hq_brief_writes_only_to_the_city_root_store(tmp_path: Path):
    fixture = with_hq_store(multi_rig.build(tmp_path))
    hq_store = fixture.city_root / ".beads" / "issues.jsonl"
    rig_store = fixture.rig_root("mathcity") / ".beads" / "issues.jsonl"
    rig_before = rig_store.read_bytes()

    result = run_mctl(
        fixture,
        "briefs",
        "adjudicate",
        f"{HQ_PREFIX}open",
        "--verdict",
        "approve",
        "--reason",
        "ready",
        "--json",
        "--city",
        str(fixture.city_root),
        "--rig",
        HQ_RIG_ID,
    )

    assert result.returncode == 0, result.stderr
    assert read_jsonl(hq_store)[f"{HQ_PREFIX}open"]["status"] == "closed"
    assert rig_store.read_bytes() == rig_before, "a mutation crossed into another store"


def test_an_hq_brief_is_not_mutable_through_another_rig(tmp_path: Path):
    """A brief in the HQ store belongs to the HQ store."""
    fixture = with_hq_store(multi_rig.build(tmp_path))
    hq_before = (fixture.city_root / ".beads" / "issues.jsonl").read_bytes()

    result = run_mctl(
        fixture,
        "briefs",
        "adjudicate",
        f"{HQ_PREFIX}open",
        "--verdict",
        "approve",
        "--reason",
        "ready",
        "--json",
        "--city",
        str(fixture.city_root),
        "--rig",
        "mathcity",
    )

    assert result.returncode != 0
    assert (fixture.city_root / ".beads" / "issues.jsonl").read_bytes() == hq_before


def test_no_cross_rig_mutation_became_reachable(tmp_path: Path):
    """Adding a store must not add a way to write to all of them at once."""
    from mctl_core import mcp_server

    for tool in mcp_server.TOOLS:
        if tool.mutating:
            assert "all_rigs" not in tool.input_schema["properties"], tool.name
            assert not tool.cross_rig, tool.name
