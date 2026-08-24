"""#192 — one error boundary per commission create.

`_apply_bd_create` mints a decision bead with `bd create`, then links each
source with a SEPARATE `bd link`. When a link fails the bead has already been
written, so the pre-#192 code raised and left an UNLINKED, UNMARKED decision
bead behind. A retry could not tell that partial from a fresh request, so it
minted a SECOND brief -- the orphan-brick class `mc-7po` is the standing
evidence for.

The fix makes a sourced create a recoverable transaction: the bead is marked
`commission_incomplete=true` until every link lands, and a retry ADOPTS that
partial instead of duplicating it. These tests drive the real subprocess
adapter through a stateful `bd` shim that can be told to fail the first link.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core.beads import (  # noqa: E402
    BeadCreate,
    BeadWriteError,
    apply_bead_create,
    read_beads,
)

SOURCE_ID = "mc-src-7"


def _stateful_bd(tmp_path: Path, *, link_failures: int) -> tuple[Path, Path]:
    """A `bd` shim backed by a JSON store that can fail the first N `link` calls.

    Unlike the argv-recording shims elsewhere, this one PERSISTS what it creates
    and links, so `bd list` afterwards reflects the writes -- which is what the
    adopt-on-retry path reads. `link_failures` link calls exit 1 before any
    succeed, reproducing the transient failure that stranded a partial brief.
    """
    store = tmp_path / "store.json"
    store.write_text("[]", encoding="utf-8")
    linkfail = tmp_path / "link_failures_remaining"
    linkfail.write_text(str(link_failures), encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "bd"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"STORE = {str(store)!r}\n"
        f"LINKFAIL = {str(linkfail)!r}\n"
        "argv = sys.argv[1:]\n"
        "def load():\n"
        "    try: return json.load(open(STORE))\n"
        "    except Exception: return []\n"
        "def save(rows): json.dump(rows, open(STORE, 'w'))\n"
        "def opt(flag):\n"
        "    return argv[argv.index(flag) + 1] if flag in argv else None\n"
        "cmd = argv[0] if argv else ''\n"
        "if cmd == 'create':\n"
        "    rows = load()\n"
        "    bid = 'mc-%02d' % (len(rows) + 1)\n"
        "    meta = json.loads(opt('--metadata')) if '--metadata' in argv else {}\n"
        "    labels = [x for x in (opt('--labels') or '').split(',') if x]\n"
        "    rows.append({'id': bid, 'title': argv[1], 'status': 'open',\n"
        "                 'issue_type': opt('--type') or 'task', 'labels': labels,\n"
        "                 'metadata': meta, 'dependencies': [],\n"
        "                 'description': opt('--description') or ''})\n"
        "    save(rows)\n"
        "    sys.stdout.write(json.dumps({'id': bid, 'status': 'open'}))\n"
        "elif cmd == 'link':\n"
        "    bead, source = argv[1], argv[2]\n"
        "    try: n = int((open(LINKFAIL).read() or '0').strip())\n"
        "    except Exception: n = 0\n"
        "    if n > 0:\n"
        "        open(LINKFAIL, 'w').write(str(n - 1))\n"
        "        sys.stderr.write('bd link boom (injected)\\n'); sys.exit(1)\n"
        "    rows = load()\n"
        "    ltype = opt('--type') or 'related'\n"
        "    for r in rows:\n"
        "        if r['id'] == bead:\n"
        "            r.setdefault('dependencies', []).append(\n"
        "                {'issue_id': bead, 'depends_on_id': source, 'type': ltype})\n"
        "    save(rows)\n"
        "    sys.stdout.write('Linked %s <-> %s\\n' % (bead, source))\n"
        "elif cmd == 'update':\n"
        "    bid = rows_id = argv[1]\n"
        "    rows = load()\n"
        "    for r in rows:\n"
        "        if r['id'] == bid:\n"
        "            meta = r.get('metadata') or {}\n"
        "            for j, a in enumerate(argv):\n"
        "                if a == '--set-metadata':\n"
        "                    k, _, v = argv[j + 1].partition('=')\n"
        "                    meta[k] = v\n"
        "            r['metadata'] = meta\n"
        "            if '--status' in argv: r['status'] = opt('--status')\n"
        "    save(rows)\n"
        "    sys.stdout.write(json.dumps({'id': bid}))\n"
        "elif cmd == 'list':\n"
        "    rows = load()\n"
        "    if '--type' in argv:\n"
        "        t = opt('--type')\n"
        "        rows = [r for r in rows if r.get('issue_type') == t]\n"
        "    sys.stdout.write(json.dumps(rows))\n"
        "else:\n"
        "    sys.stdout.write('[]')\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    rig_root = tmp_path / "rig"
    rig_root.mkdir()
    return bin_dir, rig_root


def _commission() -> BeadCreate:
    return BeadCreate(
        placeholder_id="(pending)",
        title="Commission: decide gh#7",
        body="## What is being decided\n\nCommission the planning for gh#7.\n",
        issue_type="decision",
        labels=("commission",),
        sources=(SOURCE_ID,),
        source_link_type="related",
    )


def _decisions(rig_root: Path) -> tuple:
    return read_beads(rig_root, issue_type="decision")


def test_a_failed_link_leaves_an_adoptable_partial_not_an_orphan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A link failure must not strand an unmarked, duplicate-prone orphan.

    The bead the failed attempt leaves behind carries
    `commission_incomplete=true`, which is exactly what a retry keys on. That
    marker is the difference between an adoptable partial and the orphan brick
    `mc-7po`.
    """
    bin_dir, rig_root = _stateful_bd(tmp_path, link_failures=1)
    monkeypatch.setenv("PATH", f"{bin_dir}:{__import__('os').environ['PATH']}")

    with pytest.raises(BeadWriteError):
        apply_bead_create(rig_root, _commission())

    decisions = _decisions(rig_root)
    assert len(decisions) == 1, f"expected one partial, saw {[b.id for b in decisions]}"
    partial = decisions[0]
    assert partial.raw.get("metadata", {}).get("commission_incomplete") == "true", (
        "the stranded bead is unmarked -- a retry cannot tell it from a fresh "
        "request and will mint a duplicate brief"
    )
    assert SOURCE_ID not in partial.source_dependencies, "the link never landed"


def test_a_full_retry_after_a_transient_link_failure_yields_exactly_one_brief(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Attempt, fail the link, retry the identical create -> ONE brief, linked."""
    bin_dir, rig_root = _stateful_bd(tmp_path, link_failures=1)
    monkeypatch.setenv("PATH", f"{bin_dir}:{__import__('os').environ['PATH']}")

    with pytest.raises(BeadWriteError):
        apply_bead_create(rig_root, _commission())

    # The retry adopts the partial instead of minting a twin.
    apply_bead_create(rig_root, _commission())

    decisions = _decisions(rig_root)
    assert len(decisions) == 1, f"retry duplicated the brief: {[b.id for b in decisions]}"
    brief = decisions[0]
    assert SOURCE_ID in brief.source_dependencies, "the adopted brief must be linked"
    assert brief.raw.get("metadata", {}).get("commission_incomplete") != "true", (
        "a completed brief must not still advertise itself as an adoptable partial"
    )


def test_a_clean_create_links_the_source_and_marks_the_brief_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The happy path: one create, the link lands, the marker is cleared."""
    bin_dir, rig_root = _stateful_bd(tmp_path, link_failures=0)
    monkeypatch.setenv("PATH", f"{bin_dir}:{__import__('os').environ['PATH']}")

    apply_bead_create(rig_root, _commission())

    decisions = _decisions(rig_root)
    assert len(decisions) == 1
    brief = decisions[0]
    assert SOURCE_ID in brief.source_dependencies
    assert brief.raw.get("metadata", {}).get("commission_incomplete") == "false"
