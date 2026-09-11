#!/usr/bin/env python3
"""Switch a city's Claude provider without hand-editing city.toml.

WHY THIS EXISTS. P1.2 ("Config flows through imports") forbids one-off
hand-edits to city.toml, and P1.1's replay litmus rejects "run this command I
ran manually that one time". But switching the fleet's Claude account is a
routine operational act, and until now the only way to do it WAS a hand-edit.
POLICY-city.md Open Question 1 names the gap directly: concurrency and similar
settings "live in city.toml patches -- but P1.2 says city behavior flows
through imports. Candidate: a mathcity-owned config fragment that the patch
mechanism materializes, keeping city.toml hand-edit-free."

This is the narrow first instance of that mechanism: one declared operation,
repeatable, validated, backed up, and verified. A switch performed by this
script is reproducible from the command line alone -- which is what P1.1
actually asks for.

FAILS CLOSED. It refuses to select a provider whose CLAUDE_CONFIG_DIR is
missing or not authenticated, because the failure mode it exists to prevent is
pointing a whole fleet at an account that cannot log in -- silent, fleet-wide,
and discovered only when every agent starts failing.

FORMAT-PRESERVING. It rewrites exactly one `provider =` line under
[workspace]. It never round-trips the document through a TOML dumper, which
would discard the comments that carry every standing justification in
kolchin's city.toml.

Usage:
    city_provider.py --city ~/HQ --list
    city_provider.py --city ~/HQ --set claude-primary
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import tomllib
from pathlib import Path

OK, FAILED, CANNOT_VERIFY = 0, 1, 2


def load(city: Path):
    p = city / "city.toml"
    if not p.is_file():
        print(f"I'm sorry, I can't do that -- no city.toml at {city}.", file=sys.stderr)
        raise SystemExit(CANNOT_VERIFY)
    try:
        return p, tomllib.loads(p.read_text())
    except tomllib.TOMLDecodeError as exc:
        print(f"I'm sorry, I can't do that -- {p} is not valid TOML: {exc}", file=sys.stderr)
        raise SystemExit(CANNOT_VERIFY)


def account_of(cfg_dir: Path):
    """(status, email) for a CLAUDE_CONFIG_DIR. status: ok | no-dir | no-auth."""
    if not cfg_dir.is_dir():
        return "no-dir", None
    j = cfg_dir / ".claude.json"
    if not j.is_file():
        return "no-auth", None
    try:
        acct = (json.loads(j.read_text()).get("oauthAccount") or {})
    except (OSError, json.JSONDecodeError):
        return "no-auth", None
    email = acct.get("emailAddress")
    return ("ok", email) if email else ("no-auth", None)


def providers(data):
    out = {}
    for name, blk in (data.get("providers") or {}).items():
        env = (blk.get("env") or {})
        out[name] = {
            "display": blk.get("display_name") or name,
            "config_dir": env.get("CLAUDE_CONFIG_DIR"),
        }
    return out


def current(data):
    return ((data.get("workspace") or {}).get("provider") or "").strip()


def cmd_list(city):
    _, data = load(city)
    cur, provs = current(data), providers(city_data := data)
    if not provs:
        print("no [providers.*] blocks declared", file=sys.stderr)
        return CANNOT_VERIFY
    print(f"city: {city}")
    for name, meta in sorted(provs.items()):
        cd = meta["config_dir"]
        if cd:
            status, email = account_of(Path(cd).expanduser())
        else:
            status, email = "n/a", None
        mark = "*" if name == cur else " "
        detail = email or {"no-dir": "CONFIG DIR MISSING",
                           "no-auth": "NOT AUTHENTICATED",
                           "n/a": "no CLAUDE_CONFIG_DIR"}.get(status, status)
        print(f"  {mark} {name:<22} {detail}")
    print(f"\n  * = active ({cur or 'none set'})")
    return OK


def cmd_set(city, target):
    path, data = load(city)
    provs = providers(data)
    if target not in provs:
        print(f"I'm sorry, I can't do that -- no [providers.{target}] in {path}.",
              file=sys.stderr)
        print(f"Declared: {', '.join(sorted(provs)) or '(none)'}", file=sys.stderr)
        return FAILED

    cur = current(data)
    if cur == target:
        print(f"already on {target} -- nothing to do.")
        return OK

    cd = provs[target]["config_dir"]
    if not cd:
        print(f"I'm sorry, I can't do that -- [providers.{target}] declares no "
              f"CLAUDE_CONFIG_DIR, so its account cannot be verified.", file=sys.stderr)
        return FAILED
    status, email = account_of(Path(cd).expanduser())
    if status != "ok":
        reason = {"no-dir": f"{cd} does not exist",
                  "no-auth": f"{cd} has no authenticated account"}[status]
        print(f"I'm sorry, I can't do that -- {reason}.", file=sys.stderr)
        print("Refusing to point the fleet at an account that cannot log in.",
              file=sys.stderr)
        return FAILED

    text = path.read_text()
    # Only the provider line inside [workspace]; never a providers.* heading.
    ws = re.search(r'(?ms)^\[workspace\]\s*$(.*?)(?=^\[|\Z)', text)
    if not ws:
        print(f"I'm sorry, I can't do that -- no [workspace] section in {path}.",
              file=sys.stderr)
        return CANNOT_VERIFY
    block = ws.group(1)
    new_block, n = re.subn(r'(?m)^(\s*provider\s*=\s*)"[^"]*"',
                           lambda m: m.group(1) + f'"{target}"', block, count=1)
    if n != 1:
        print(f"I'm sorry, I can't do that -- expected exactly one provider "
              f"assignment under [workspace], found {n}.", file=sys.stderr)
        return CANNOT_VERIFY

    backup = path.with_name(f"city.toml.bak-provider-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(path, backup)
    path.write_text(text[:ws.start(1)] + new_block + text[ws.end(1):])

    # Verify by re-reading, not by trusting the write (P-rule: verify after write).
    _, after = load(city)
    if current(after) != target:
        shutil.copy2(backup, path)
        print("I'm sorry, I can't do that -- post-write verification failed; "
              "restored from backup.", file=sys.stderr)
        return CANNOT_VERIFY

    print(f"provider: {cur or '(none)'} -> {target}   [{email}]")
    print(f"backup:   {backup.name}")
    print("\nRunning sessions keep their old provider; new sessions pick this up.")
    return OK


def main(argv):
    ap = argparse.ArgumentParser(description="Switch a city's Claude provider.")
    ap.add_argument("--city", default="~/HQ")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--set", metavar="PROVIDER")
    a = ap.parse_args(argv[1:])
    city = Path(a.city).expanduser()
    return cmd_list(city) if a.list else cmd_set(city, a.set)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
