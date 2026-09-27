"""#83: an mctl adjudication must not destroy a decision record's nested tables.

`_update_simple_toml` parsed the whole decision TOML and re-emitted every key as
a flat `key = value` line. A `[continuation]` section therefore became a
stringified Python repr, because `_toml_value` falls through to `str(value)`:

    [continuation]                ->  continuation = "{'formula': 'do-the-thing',
    formula = "do-the-thing"                           'vars': {'target': 'hecke'}}"
    [continuation.vars]
    target = "hecke"

Single-quoted, not valid TOML, not valid JSON, **and written with no error**.

Why it mattered rather than being untidy: `brief-record-decision.toml` says the
continuation block is what "makes APPROVE executable by
`brief-decision-dispatch`", and that formula keys the approve path on it. So one
mctl adjudication of a commission brief silently broke its own approve path --
the failure looks like "approve did nothing", with a decision record that still
appears to carry a continuation.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.effects import _update_simple_toml  # noqa: E402

RECORD = '''brief_id = "mc-x1"
decision = "approve"
source_bead = "mc-src"
continuation_contract = "commission-dispatch.v1"

[continuation]
formula = "do-the-thing"

[continuation.vars]
target = "hecke"
depth = 3
'''


def _record(tmp_path: Path) -> Path:
    path = tmp_path / "mc-x1.toml"
    path.write_text(RECORD, encoding="utf-8")
    return path


def test_the_continuation_block_survives_an_adjudication_sync(tmp_path: Path):
    """THE regression. Before the fix this value was a stringified dict."""
    path = _record(tmp_path)

    _update_simple_toml(path, {"status": "adjudicated", "verdict": "approve"})

    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert isinstance(parsed["continuation"], dict), (
        "continuation must stay a TABLE; a stringified repr is what broke the "
        "approve path"
    )
    assert parsed["continuation"]["formula"] == "do-the-thing"
    assert isinstance(parsed["continuation"]["vars"], dict)
    assert parsed["continuation"]["vars"]["target"] == "hecke"


def test_non_string_types_inside_a_nested_table_keep_their_type(tmp_path: Path):
    """`depth = 3` must not come back as `"3"`.

    A consumer doing arithmetic on a var would fail on a quoted number, and the
    old flat re-emit stringified everything it touched.
    """
    path = _record(tmp_path)

    _update_simple_toml(path, {"status": "adjudicated"})

    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["continuation"]["vars"]["depth"] == 3
    assert not isinstance(parsed["continuation"]["vars"]["depth"], str)


def test_scalars_are_emitted_before_any_section_header(tmp_path: Path):
    """A scalar written after `[continuation]` would be parsed as a member OF it.

    That is the same corruption one level quieter: `verdict` would silently
    become `continuation.verdict` and every reader of the top-level key would
    see it as absent.
    """
    path = _record(tmp_path)

    _update_simple_toml(path, {"verdict": "approve", "status": "adjudicated"})

    text = path.read_text(encoding="utf-8")
    first_section = text.index("[continuation]")
    assert text.index('verdict = ') < first_section
    assert text.index('status = ') < first_section

    parsed = tomllib.loads(text)
    assert parsed["verdict"] == "approve", "verdict must stay top-level"
    assert "verdict" not in parsed["continuation"]


def test_the_new_fields_are_actually_applied(tmp_path: Path):
    """Preserving structure must not come at the cost of the write itself."""
    path = _record(tmp_path)

    _update_simple_toml(path, {"status": "adjudicated", "verdict": "approve"})

    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["status"] == "adjudicated"
    assert parsed["verdict"] == "approve"
    assert parsed["source_bead"] == "mc-src"
    assert parsed["continuation_contract"] == "commission-dispatch.v1"


def test_a_flat_record_is_unchanged_in_shape(tmp_path: Path):
    """The overwhelmingly common case has no tables and must gain no sections."""
    path = tmp_path / "mc-flat.toml"
    path.write_text('brief_id = "mc-flat"\nstatus = "open"\n', encoding="utf-8")

    _update_simple_toml(path, {"status": "adjudicated", "verdict": "approve"})

    text = path.read_text(encoding="utf-8")
    assert "[" not in text, f"a flat record must stay flat, got:\n{text}"
    assert tomllib.loads(text)["verdict"] == "approve"


def test_the_write_is_idempotent_across_two_syncs(tmp_path: Path):
    """Two adjudication syncs must not nest deeper or duplicate a section.

    A writer that re-parsed its own output incorrectly would drift on the second
    pass, which is the shape that hides until a brief is touched twice.
    """
    path = _record(tmp_path)

    _update_simple_toml(path, {"status": "adjudicated"})
    once = path.read_text(encoding="utf-8")
    _update_simple_toml(path, {"status": "adjudicated"})
    twice = path.read_text(encoding="utf-8")

    assert once == twice, "the second sync changed the file"
    assert twice.count("[continuation]") == 1
    assert twice.count("[continuation.vars]") == 1
