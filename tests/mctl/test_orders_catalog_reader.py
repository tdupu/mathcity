"""WI-001 (mc-6lte): the bounded order catalog reader.

`orders_status` gets its catalog from `gc order list --json`, measured in-city
at 28.34s / 43.10s / 42.84s / 46.72s / 89s. No request path can pay that, so
`_event_log_only` serves outcomes and reports the catalog `unreachable` --
the catalog half of the tool has never been servable at all.

Order definitions are local TOML files. Reading them is bounded by the
filesystem, so these tests pin a reader that never spawns a subprocess.

ROOT SELECTION IS EXPLICIT, NEVER GUESSED. The fixture carries root orders AND
`subdomains/dev/orders/*.toml`, and a case where `source_checkout` differs from
`rig_root`. A reader that silently picks a root reports a confidently
incomplete catalog -- the exact failure this module already corrected once for
outcomes (#156). Disagreement is a typed diagnostic, and a root that cannot be
materialized is `unreachable` with `total=None`, never zero rows.

The row shape follows gc's own `orderToJSON` (cmd/gc/cmd_order.go:562) and
`Order.ScopedName` (internal/orders/order.go:141): `type` is `exec` when the
order execs and `formula` otherwise, `enabled` defaults to true when the key is
absent (`IsEnabled`), `trigger` falls back to `gate`, and a rig-scoped order
scopes as `<name>:rig:<rig>`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.orders import read_order_catalog  # noqa: E402


ROOT_CITY_ORDER = """\
[order]
description = "Archive sent-back brief artifacts as soon as routing requests it"
scope = "city"
formula = "brief-archive-sweep"
trigger = "event"
on = "brief.archive_requested"
timeout = "60s"
"""

ROOT_RIG_ORDER = """\
[order]
description = "Patrol briefs awaiting review"
scope = "rig"
formula = "brief-review-patrol"
trigger = "cooldown"
interval = "15m"
"""

SUBDOMAIN_ORDER = """\
[order]
description = "Reclaim stale leases"
scope = "city"
trigger = "cooldown"
interval = "30m"
exec = "bash $PACK_DIR/scripts/reclaim-stale-leases.sh"
"""

DISABLED_ORDER = """\
[order]
description = "Parked order"
scope = "city"
formula = "parked"
trigger = "cooldown"
interval = "1h"
enabled = false
"""

GATE_ONLY_ORDER = """\
[order]
description = "Trigger spelled as gate"
scope = "city"
formula = "gated"
gate = "cooldown"
interval = "5m"
"""


def _checkout(root: Path) -> Path:
    """A source checkout with root orders and a `subdomains/dev` sub-pack."""
    (root / "orders").mkdir(parents=True, exist_ok=True)
    (root / "orders" / "brief-archive-on-request.toml").write_text(ROOT_CITY_ORDER)
    (root / "orders" / "brief-review-patrol.toml").write_text(ROOT_RIG_ORDER)
    (root / "orders" / "parked.toml").write_text(DISABLED_ORDER)
    (root / "orders" / "gated.toml").write_text(GATE_ONLY_ORDER)
    (root / "subdomains" / "dev" / "orders").mkdir(parents=True, exist_ok=True)
    (root / "subdomains" / "dev" / "orders" / "reclaim-stale-leases.toml").write_text(
        SUBDOMAIN_ORDER
    )
    return root


def _rows(out) -> dict[str, dict]:
    return {row["name"]: row for row in out["orders"]}


def test_the_reader_returns_registered_rows_from_local_toml(tmp_path):
    """Acceptance 1: a fixture of order TOML yields registered rows."""
    out = read_order_catalog(source_checkout=_checkout(tmp_path / "src"), rig_name="mathcity")

    assert out["state"] == "healthy"
    assert out["total"] >= 1
    assert out["total"] == len(out["orders"])


def test_root_and_subdomain_orders_are_both_included(tmp_path):
    """Acceptance 2: `orders/*.toml` AND `subdomains/*/orders/*.toml`.

    A reader that scans only the root silently drops every sub-pack order and
    still reports a total, which reads as a complete catalog.
    """
    rows = _rows(read_order_catalog(source_checkout=_checkout(tmp_path / "src"), rig_name="mathcity"))

    assert "brief-archive-on-request" in rows, "root orders/ must be scanned"
    assert "reclaim-stale-leases" in rows, "subdomains/*/orders/ must be scanned"


def test_the_name_comes_from_the_filename(tmp_path):
    rows = _rows(read_order_catalog(source_checkout=_checkout(tmp_path / "src"), rig_name="mathcity"))

    # The TOML body carries no `name` key; the filename stem is the name.
    assert rows["brief-archive-on-request"]["description"].startswith("Archive sent-back")


def test_a_rig_scoped_order_derives_its_scoped_name(tmp_path):
    """Acceptance 3, against gc's own convention: `<name>:rig:<rig>`."""
    rows = _rows(read_order_catalog(source_checkout=_checkout(tmp_path / "src"), rig_name="mathcity"))

    assert rows["brief-review-patrol"]["scope"] == "rig"
    assert rows["brief-review-patrol"]["scoped_name"] == "brief-review-patrol:rig:mathcity"


def test_a_city_scoped_order_keeps_its_bare_name(tmp_path):
    """`ScopedName()` returns the bare name when the order carries no rig."""
    rows = _rows(read_order_catalog(source_checkout=_checkout(tmp_path / "src"), rig_name="mathcity"))

    assert rows["brief-archive-on-request"]["scoped_name"] == "brief-archive-on-request"


def test_source_paths_are_repo_relative(tmp_path):
    """Acceptance 4: `source` locates the file within the scanned root."""
    rows = _rows(read_order_catalog(source_checkout=_checkout(tmp_path / "src"), rig_name="mathcity"))

    assert rows["brief-archive-on-request"]["source"] == "orders/brief-archive-on-request.toml"
    assert rows["reclaim-stale-leases"]["source"] == (
        "subdomains/dev/orders/reclaim-stale-leases.toml"
    )
    assert not Path(rows["reclaim-stale-leases"]["source"]).is_absolute()


def test_the_reader_never_shells_out(tmp_path, monkeypatch):
    """Acceptance 5: no bounded-reader path spawns `gc order list --json`.

    The whole point is to stop paying a measured 89s inside a request. A
    subprocess that is merely *fast in the fixture* would still reintroduce it
    in the city, so the probe forbids the call outright rather than timing it.
    """
    import subprocess

    def explode(*args, **kwargs):  # pragma: no cover - the assertion is that this never runs
        raise AssertionError(f"the bounded reader shelled out: {args!r}")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "check_output", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)

    out = read_order_catalog(source_checkout=_checkout(tmp_path / "src"), rig_name="mathcity")

    assert out["total"] >= 1


def test_source_checkout_is_preferred_over_rig_root(tmp_path):
    """The bead's explicit precedence: prefer `source_checkout` when resolved.

    The two roots carry DIFFERENT orders, so the assertion distinguishes which
    root was actually read -- a test where both roots hold the same files
    cannot fail and would not be a check at all (P6.2).
    """
    source = _checkout(tmp_path / "src")
    rig_root = tmp_path / "rig"
    (rig_root / "orders").mkdir(parents=True)
    (rig_root / "orders" / "only-in-rig-root.toml").write_text(ROOT_CITY_ORDER)

    rows = _rows(read_order_catalog(source_checkout=source, rig_root=rig_root, rig_name="mathcity"))

    assert "brief-archive-on-request" in rows, "the source checkout must win"
    assert "only-in-rig-root" not in rows, "rig_root must not be scanned when a source checkout resolved"


def test_rig_root_is_the_fallback_when_no_source_checkout_resolves(tmp_path):
    rig_root = _checkout(tmp_path / "rig")

    rows = _rows(read_order_catalog(rig_root=rig_root, rig_name="mathcity"))

    assert "brief-archive-on-request" in rows


def test_pack_root_can_stand_in_for_the_source_checkout(tmp_path):
    rows = _rows(read_order_catalog(pack_root=_checkout(tmp_path / "pack"), rig_name="mathcity"))

    assert "brief-archive-on-request" in rows


def test_disagreeing_roots_are_reported_rather_than_silently_resolved(tmp_path):
    """Selecting a root is a decision the caller is entitled to see.

    The reader picks the source checkout, and says so -- it never claims a
    complete catalog while quietly ignoring the other root.
    """
    source = _checkout(tmp_path / "src")
    rig_root = tmp_path / "rig"
    (rig_root / "orders").mkdir(parents=True)

    out = read_order_catalog(source_checkout=source, rig_root=rig_root, rig_name="mathcity")

    codes = {d["code"] for d in out["diagnostics"]}
    assert "MORD_CATALOG_ROOT_MISMATCH" in codes


def test_agreeing_roots_raise_no_mismatch(tmp_path):
    root = _checkout(tmp_path / "src")

    out = read_order_catalog(source_checkout=root, rig_root=root, rig_name="mathcity")

    codes = {d["code"] for d in out["diagnostics"]}
    assert "MORD_CATALOG_ROOT_MISMATCH" not in codes


def test_an_unmaterialized_root_is_unreachable_and_never_zero(tmp_path):
    """Three-valued, per this module's standing discipline.

    "We could not look" and "there are none" are different facts. An import
    root that was never materialized must not render as an empty catalog.
    """
    out = read_order_catalog(source_checkout=tmp_path / "does-not-exist", rig_name="mathcity")

    assert out["state"] == "unreachable"
    assert out["total"] is None, "an unread catalog reports None, never 0"
    assert {d["code"] for d in out["diagnostics"]} & {
        "MORD_CATALOG_ROOT_UNAVAILABLE"
    }


def test_no_root_at_all_is_unreachable(tmp_path):
    out = read_order_catalog(rig_name="mathcity")

    assert out["state"] == "unreachable"
    assert out["total"] is None


def test_enabled_defaults_to_true_and_an_explicit_false_is_honored(tmp_path):
    """`IsEnabled()` defaults to true when the key is absent."""
    rows = _rows(read_order_catalog(source_checkout=_checkout(tmp_path / "src"), rig_name="mathcity"))

    assert rows["brief-archive-on-request"]["enabled"] is True
    assert rows["parked"]["enabled"] is False


def test_type_is_exec_when_the_order_execs_and_formula_otherwise(tmp_path):
    rows = _rows(read_order_catalog(source_checkout=_checkout(tmp_path / "src"), rig_name="mathcity"))

    assert rows["reclaim-stale-leases"]["type"] == "exec"
    assert rows["brief-archive-on-request"]["type"] == "formula"


def test_trigger_falls_back_to_gate(tmp_path):
    """gc's `normalized()` reads `gate` when `trigger` is absent."""
    rows = _rows(read_order_catalog(source_checkout=_checkout(tmp_path / "src"), rig_name="mathcity"))

    assert rows["gated"]["trigger"] == "cooldown"


def test_a_malformed_toml_is_reported_without_killing_the_catalog(tmp_path):
    """One bad file is not a dead catalog -- the same stance the event log takes."""
    root = _checkout(tmp_path / "src")
    (root / "orders" / "broken.toml").write_text("[order\nthis is not toml")

    out = read_order_catalog(source_checkout=root, rig_name="mathcity")

    assert out["total"] >= 1, "the readable orders still come back"
    assert "broken" not in _rows(out)
    assert "MORD_CATALOG_FILE_UNREADABLE" in {d["code"] for d in out["diagnostics"]}


def test_every_row_carries_the_declared_fields(tmp_path):
    required = {
        "name", "scoped_name", "description", "type",
        "trigger", "interval", "enabled", "source", "scope",
    }
    out = read_order_catalog(source_checkout=_checkout(tmp_path / "src"), rig_name="mathcity")

    for row in out["orders"]:
        assert required <= set(row), f"{row.get('name')} is missing {required - set(row)}"


def test_diagnostics_are_objects_not_strings(tmp_path):
    """#203: a string diagnostic dies FATAL against the declared object schema."""
    out = read_order_catalog(source_checkout=tmp_path / "missing", rig_name="mathcity")

    assert out["diagnostics"]
    for diagnostic in out["diagnostics"]:
        assert isinstance(diagnostic, dict)
        assert {"code", "message", "severity"} <= set(diagnostic)
