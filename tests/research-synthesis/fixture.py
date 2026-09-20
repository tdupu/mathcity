#!/usr/bin/env python3
"""Prepare blind fixture projects; check packaging, never agent behavior."""

import argparse
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil


ROOT = Path(__file__).resolve().parent


def relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise ValueError(f"Not a portable relative path: {value!r}")
    return path


def files(directory):
    if not directory.is_dir():
        raise ValueError(f"Missing input directory: {directory}")
    result = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Fixture inputs must not be symlinks: {path}")
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = path
    return result


def project_files(case):
    result = files(ROOT / "common")
    for name in case.get("omit", []):
        relative(name)
        if name not in result:
            raise ValueError(f"Omitted file does not exist: {name}")
        del result[name]
    result.update(files(ROOT / "inputs" / relative(case["input"])))
    return result


def check(cases):
    if [case["id"] for case in cases] != [f"{i:02}" for i in range(1, 9)]:
        raise ValueError("Expected eight unique cases, 01 through 08")
    expected = (ROOT / "expected.md").read_text(encoding="utf-8")
    expected_ids = re.findall(r"^## (\d{2})\s+\u2014", expected, re.MULTILINE)
    if expected_ids != [case["id"] for case in cases]:
        raise ValueError("Expected-outcome sections do not match the eight cases")
    if set(cases[3].get("variants", {})) != {"beginner", "advanced"}:
        raise ValueError("Case 04 needs both audience variants")
    if [turn["turn"] for turn in cases[7].get("followups", [])] != [2, 3]:
        raise ValueError("Case 08 needs the two ordered follow-up turns")
    for case in cases:
        source_files = project_files(case)
        for name in case["selected"]:
            relative(name)
            if name not in source_files:
                raise ValueError(f"Case {case['id']}: missing selected file {name}")
        canonical = case.get("canonical", "notes.tex")
        allowed_tex = {canonical, *case.get("archival_tex", [])}
        actual_tex = {name for name in source_files if name.endswith(".tex")}
        if actual_tex != allowed_tex:
            raise ValueError(f"Case {case['id']}: TeX inventory mismatch")
        if not case.get("request") and not case.get("variants"):
            raise ValueError(f"Case {case['id']}: missing request")
        for turn in case.get("followups", []):
            if not turn.get("request"):
                raise ValueError("Follow-up is missing a request")
            if "overlay" in turn:
                files(ROOT / "followups" / relative(turn["overlay"]))
        for name, source in source_files.items():
            relative(name)
            # Every input is a small UTF-8 text source, not a binary dependency.
            content = source.read_text(encoding="utf-8")
            if source.suffix == ".md":
                for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
                    local = link.split("#", 1)[0]
                    if not local or "://" in local:
                        continue
                    target = posixpath.normpath(
                        str(PurePosixPath(name).parent / local)
                    )
                    relative(target)
                    if target not in source_files:
                        raise ValueError(f"Case {case['id']}: broken link {name}: {link}")
    original = ROOT / "inputs/08-rerun/research/bounds.md"
    retained = ROOT / "inputs/08-rerun/ai/prior/bounds-v1.md"
    if original.read_bytes() != retained.read_bytes():
        raise ValueError("Case 08's retained R1 differs from its starting source")


def copy_files(source_files, destination):
    for name, source in source_files.items():
        target = destination / relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def prepare(case, destination, variant):
    variants = case.get("variants", {})
    if variants:
        if variant not in variants:
            raise ValueError(f"Choose one variant: {', '.join(variants)}")
        request = variants[variant]
    else:
        if variant:
            raise ValueError("This case has no audience variants")
        request = case["request"]
    # Refuse any existing path, including a dangling symlink. Never merge trials.
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Destination already exists: {destination}")
    destination.mkdir(parents=True, exist_ok=False)
    copy_files(project_files(case), destination / "project")
    (destination / "request.txt").write_text(request + "\n", encoding="utf-8")
    for turn in case.get("followups", []):
        driver = destination / "driver"
        driver.mkdir(exist_ok=True)
        (driver / f"next-request-{turn['turn']}.txt").write_text(
            turn["request"] + "\n", encoding="utf-8"
        )
        if "overlay" in turn:
            copy_files(
                files(ROOT / "followups" / relative(turn["overlay"])),
                driver / f"turn-{turn['turn']}",
            )
    print(f"Prepared {destination / 'project'}")
    print("Expose only project/ to the worker; send request.txt as its request.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="read-only input packaging checks")
    export = commands.add_parser("prepare", help="create a new blind trial")
    export.add_argument("case", choices=[f"{i:02}" for i in range(1, 9)])
    export.add_argument("destination", type=Path)
    export.add_argument("variant", nargs="?")
    args = parser.parse_args()
    try:
        cases = json.loads((ROOT / "scenarios.json").read_text(encoding="utf-8"))["cases"]
        check(cases)
        if args.command == "check":
            print("PASS: 8 input/oracle pairs, selected paths and local attachments")
            print("PASS: TeX inventories, audience variants, follow-ups, retained R1")
            print("No model behavior or review outcome has been tested.")
        else:
            case = next(case for case in cases if case["id"] == args.case)
            prepare(case, args.destination, args.variant)
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
