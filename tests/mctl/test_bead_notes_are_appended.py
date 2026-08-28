"""Every `bd update` the pack tells an agent to run must PRESERVE existing notes.

`bd update <id> --notes X` **replaces** the notes column ("Additional notes
(replaces existing notes; use --append-notes to append)" -- `bd update --help`).
The warning bd prints arrives *after* the write, when the previous text is
already gone. On 2026-08-23 that destroyed one agent's refutation on `gt-murbwd`
when another agent recorded its own status on the same bead.

`--append-notes` is the non-destructive verb, and mathcity POLICY P1.19
("append, don't edit beads") is the rule these call sites have to satisfy.

WHAT THIS ASSERTS -- the consequence, not the spelling. Each `bd update`
invocation the pack embeds is really executed, as a subprocess, against a fake
`bd` that implements bd's documented notes contract over a seeded store. The
assertion is that note text written *before* the invocation is still readable
*after* it. A test that merely grepped the sources for the string
"--append-notes" could not fail for the right reason, so it is not the test.

`test_control_*` below proves the harness is not vacuous: it feeds the harness
the pre-fix form of a real pack file and asserts the harness reports the loss.

Only `bd update` is in scope. `bd create --notes` *sets* notes on a bead that
did not exist a moment earlier -- there is nothing to destroy, `bd create` has
no `--append-notes` flag, and those call sites are correct as they stand.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]

#: Where the pack keeps shell an agent is instructed to run. `docs/` and the
#: two script trees carry copy-pasteable runbook commands too, so they are swept
#: on the same terms -- they hold no `bd update` note site today, and the point
#: of listing them is that a new one lands inside the sweep rather than outside
#: it. `subdomains/**` is deliberately excluded: its POLICY/archive prose
#: *discusses* `bd update --notes` as the thing not to do, and sweeping prose
#: would trade a real check for a brittle one.
CALL_SITE_GLOBS = (
    "formulas/**/*.toml",
    "skills/**/*.md",
    "docs/**/*.md",
    "assets/**/*.sh",
    "scripts/**/*.sh",
)

#: Guards against a silently-empty sweep. If the scanner or the layout changes
#: so that far fewer call sites are found, the sweep would "pass" without having
#: checked anything -- that is the failure mode this floor exists to catch.
MIN_EXPECTED_UPDATE_INVOCATIONS = 60
MIN_EXPECTED_NOTES_INVOCATIONS = 40

SEEDED_NOTE = "PRE-EXISTING NOTE: the refutation another agent recorded here."

#: Neutralize the pack's prompt placeholders so shlex sees an ordinary word.
_PLACEHOLDER_PATTERNS = (
    (re.compile(r"\{\{[^{}\n]*\}\}"), "TEMPLATE_VAR"),
    (re.compile(r"<[^<>\n]*>"), "PLACEHOLDER"),
)


def extract_bd_update_invocations(text: str) -> list[tuple[int, str]]:
    """Return (line number, command text) for each `bd update ...` in `text`.

    Quote-aware rather than line-based: several call sites pass a `--notes`
    argument whose double-quoted string spans many lines, and a line-based
    reader would truncate them mid-argument and miss the flag entirely.
    """
    found: list[tuple[int, str]] = []
    for match in re.finditer(r"\bbd update\b", text):
        start = match.start()
        cursor = start
        end = len(text)
        quote: str | None = None
        while cursor < end:
            char = text[cursor]
            if quote is not None:
                if char == "\\" and quote == '"':
                    cursor += 2
                    continue
                if char == quote:
                    quote = None
                cursor += 1
                continue
            if char in "\"'":
                quote = char
                cursor += 1
                continue
            # A backslash-newline is a line continuation: the invocation goes on.
            if text[cursor:cursor + 2] == "\\\n":
                cursor += 2
                continue
            # An unquoted newline or shell separator ends the invocation.
            if char in ";\n" or text[cursor:cursor + 2] in ("&&", "||"):
                break
            cursor += 1
        found.append((text.count("\n", 0, start) + 1, text[start:cursor].strip()))
    return found


def invocation_argv(command: str) -> list[str]:
    """Tokenize an extracted invocation into argv the fake `bd` can be handed."""
    neutralized = command
    for pattern, replacement in _PLACEHOLDER_PATTERNS:
        neutralized = pattern.sub(replacement, neutralized)
    return shlex.split(neutralized)[1:]


def carries_a_notes_flag(argv: list[str]) -> bool:
    return "--notes" in argv or "--append-notes" in argv


def make_fake_bd(tmp_path: Path) -> tuple[Path, Path, Path]:
    """A `bd` that implements the documented notes contract over a real store.

    `--notes` replaces; `--append-notes` appends after a newline. Both halves
    are pinned against the installed binary's own `--help` by
    `test_installed_bd_still_documents_the_two_notes_verbs`.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    store = tmp_path / "notes-store.json"
    argv_log = tmp_path / "bd-argv.jsonl"
    argv_log.write_text("", encoding="utf-8")

    shim = bin_dir / "bd"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"STORE = {str(store)!r}\n"
        f"LOG = {str(argv_log)!r}\n"
        "argv = sys.argv[1:]\n"
        "open(LOG, 'a').write(json.dumps(argv) + '\\n')\n"
        "if argv and argv[0] == 'update':\n"
        "    data = json.load(open(STORE))\n"
        "    i = 1\n"
        "    while i < len(argv):\n"
        "        if argv[i] == '--notes' and i + 1 < len(argv):\n"
        "            data['notes'] = argv[i + 1]\n"
        "            i += 2\n"
        "            continue\n"
        "        if argv[i] == '--append-notes' and i + 1 < len(argv):\n"
        "            prior = data.get('notes') or ''\n"
        "            data['notes'] = (prior + '\\n' + argv[i + 1]) if prior else argv[i + 1]\n"
        "            i += 2\n"
        "            continue\n"
        "        i += 1\n"
        "    json.dump(data, open(STORE, 'w'))\n"
        "sys.stdout.write('{}')\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    return bin_dir, store, argv_log


def run_against_fake_bd(argv: list[str], *, bin_dir: Path, store: Path) -> subprocess.CompletedProcess[str]:
    """Seed the store with SEEDED_NOTE, then really run `bd` with this argv."""
    store.write_text(json.dumps({"id": "gt-murbwd", "notes": SEEDED_NOTE}), encoding="utf-8")
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [str(bin_dir / "bd"), *argv],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def notes_after(store: Path) -> str:
    return json.loads(store.read_text(encoding="utf-8")).get("notes") or ""


def call_sites() -> list[tuple[str, int, str]]:
    """(relative path, line, command) for every `bd update` the pack embeds."""
    files: list[Path] = []
    for glob in CALL_SITE_GLOBS:
        files.extend(REPO_ROOT.glob(glob))
    sites: list[tuple[str, int, str]] = []
    for path in sorted(set(files)):
        text = path.read_text(encoding="utf-8")
        for line, command in extract_bd_update_invocations(text):
            sites.append((str(path.relative_to(REPO_ROOT)), line, command))
    return sites


# --------------------------------------------------------------------------
# The sweep
# --------------------------------------------------------------------------


def test_the_sweep_actually_found_the_call_sites():
    """A sweep that found nothing would pass every assertion below vacuously."""
    sites = call_sites()
    assert len(sites) >= MIN_EXPECTED_UPDATE_INVOCATIONS, (
        f"only {len(sites)} `bd update` invocations found; the scanner or the "
        f"pack layout changed and the sweep below would be vacuous"
    )
    with_notes = [s for s in sites if carries_a_notes_flag(invocation_argv(s[2]))]
    assert len(with_notes) >= MIN_EXPECTED_NOTES_INVOCATIONS, (
        f"only {len(with_notes)} note-writing invocations found"
    )


def test_every_extracted_invocation_is_tokenizable():
    """An invocation we cannot parse is unchecked, not passing."""
    unparsable = []
    for rel, line, command in call_sites():
        try:
            invocation_argv(command)
        except ValueError as exc:  # unbalanced quotes
            unparsable.append(f"{rel}:{line}: {exc}")
    assert not unparsable, "could not tokenize:\n" + "\n".join(unparsable)


def test_bd_update_call_sites_preserve_existing_notes(tmp_path: Path):
    """THE defect test: run each embedded invocation, demand the old note survives."""
    bin_dir, store, _log = make_fake_bd(tmp_path)

    destroyed = []
    for rel, line, command in call_sites():
        argv = invocation_argv(command)
        if not carries_a_notes_flag(argv):
            continue
        result = run_against_fake_bd(argv, bin_dir=bin_dir, store=store)
        assert result.returncode == 0, f"{rel}:{line}: fake bd failed: {result.stderr}"
        if SEEDED_NOTE not in notes_after(store):
            destroyed.append(f"{rel}:{line}: {command.splitlines()[0][:100]}")

    assert not destroyed, (
        f"{len(destroyed)} `bd update` call site(s) DESTROYED pre-existing notes.\n"
        "`--notes` replaces the column; use `--append-notes` (POLICY P1.19).\n"
        + "\n".join(destroyed)
    )


def test_note_writing_call_sites_also_record_their_own_text(tmp_path: Path):
    """Preserving the old note is not enough -- the new note must land too.

    Guards the opposite over-correction: dropping the flag entirely would keep
    the seeded note and silently stop recording anything.
    """
    bin_dir, store, _log = make_fake_bd(tmp_path)

    silent = []
    for rel, line, command in call_sites():
        argv = invocation_argv(command)
        if not carries_a_notes_flag(argv):
            continue
        flag = "--append-notes" if "--append-notes" in argv else "--notes"
        written = argv[argv.index(flag) + 1]
        run_against_fake_bd(argv, bin_dir=bin_dir, store=store)
        if written and written not in notes_after(store):
            silent.append(f"{rel}:{line}")

    assert not silent, "call sites wrote no note at all:\n" + "\n".join(silent)


# --------------------------------------------------------------------------
# Controls -- proof the harness above can fail
# --------------------------------------------------------------------------


def test_control_harness_detects_a_replacing_call_site(tmp_path: Path):
    """A synthetic `--notes` invocation must be caught destroying the note."""
    bin_dir, store, _log = make_fake_bd(tmp_path)
    argv = invocation_argv('bd update gt-murbwd --notes "status: step 3 done"')
    run_against_fake_bd(argv, bin_dir=bin_dir, store=store)
    assert SEEDED_NOTE not in notes_after(store), (
        "the fake bd does not model `--notes` as replacing, so the sweep above "
        "could never fail and proves nothing"
    )
    assert "status: step 3 done" in notes_after(store)


def test_control_harness_flags_the_pre_fix_form_of_a_real_pack_file(tmp_path: Path):
    """Re-introduce the defect in a real pack file's text; the sweep must catch it.

    Stronger than the synthetic control: it proves the harness would have
    reported the actual sources as they stood before this fix.
    """
    bin_dir, store, _log = make_fake_bd(tmp_path)
    path = REPO_ROOT / "formulas" / "commission-work-briefed.toml"
    pre_fix_text = path.read_text(encoding="utf-8").replace("--append-notes", "--notes")

    invocations = [
        argv
        for _line, command in extract_bd_update_invocations(pre_fix_text)
        for argv in [invocation_argv(command)]
        if carries_a_notes_flag(argv)
    ]
    assert invocations, "control found no note-writing invocation to regress"

    destroyed = []
    for argv in invocations:
        run_against_fake_bd(argv, bin_dir=bin_dir, store=store)
        if SEEDED_NOTE not in notes_after(store):
            destroyed.append(argv)
    assert destroyed, (
        "the harness did not flag the pre-fix form of commission-work-briefed.toml; "
        "it therefore cannot be trusted to have flagged the real defect"
    )


# --------------------------------------------------------------------------
# The fake's contract, pinned to the installed binary
# --------------------------------------------------------------------------


@pytest.mark.skipif(shutil.which("bd") is None, reason="bd is not installed")
def test_installed_bd_still_documents_the_two_notes_verbs():
    """The fake `bd` models a contract the real one must still advertise."""
    help_text = subprocess.run(
        ["bd", "update", "--help"], text=True, capture_output=True, check=False
    )
    advertised = help_text.stdout + help_text.stderr
    assert "--append-notes" in advertised, "installed bd no longer offers --append-notes"
    notes_line = next(
        (ln for ln in advertised.splitlines() if re.match(r"\s*--notes\b", ln)), ""
    )
    assert "replace" in notes_line.lower(), (
        f"installed bd no longer documents --notes as replacing: {notes_line!r}"
    )
