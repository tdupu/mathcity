#!/usr/bin/env python3
"""Sweep every catalogued formula through formula_dispatch on ONE live MCP session.

Dry-run only: proves each formula NAME resolves and plans a real `gc sling`
argv, without dispatching anything into the city.
"""
import json
import os
import subprocess
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
MCTL_BIN = REPO_ROOT / "bin" / "mctl"


CMD = [str(MCTL_BIN), "mcp", "serve", "--city", os.environ["MCTL_CITY"]]
if os.environ.get("MCTL_RIG"):
    CMD += ["--rig", os.environ["MCTL_RIG"]]

p = subprocess.Popen(CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, text=True, bufsize=1)
_id = [0]


def call(method, params):
    _id[0] += 1
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": _id[0],
                              "method": method, "params": params}) + "\n")
    p.stdin.flush()
    while True:
        line = p.stdout.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == _id[0]:
            return msg


def tool(name, args):
    r = call("tools/call", {"name": name, "arguments": args})
    if r is None:
        return None, "no-response"
    if "error" in r:
        return None, "rpc:" + str(r["error"].get("data", {}).get("schema_errors")
                                  or r["error"].get("message"))[:150]
    txt = "".join(c.get("text", "") for c in r.get("result", {}).get("content", []))
    try:
        return json.loads(txt), None
    except json.JSONDecodeError:
        return None, "unparseable:" + txt[:120]


call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "sweep", "version": "1"}})
p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized",
                          "params": {}}) + "\n")
p.stdin.flush()

cat, err = tool("formulas_catalog", {})
if cat is None:
    print("CATALOG FAILED:", err)
    sys.exit(1)

formulas = cat.get("formulas") or cat.get("catalog") or []
names = [f.get("name") for f in formulas if isinstance(f, dict) and f.get("name")]
print("catalogued formulas: %d" % len(names))

ok, refused, broke = [], [], []
for n in names:
    res, err = tool("formula_dispatch", {"formula": n, "dry_run": True})
    if err:
        broke.append((n, err))
        continue
    diags = res.get("diagnostics") or []
    fatal = [d for d in diags if d.get("severity") in ("FATAL", "ERROR")]
    if fatal:
        refused.append((n, fatal[0].get("code"), str(fatal[0].get("message"))[:90]))
    else:
        ok.append(n)

print("\n=== RESULT ===")
print("planned cleanly : %d" % len(ok))
print("refused (diag)  : %d" % len(refused))
print("broke (no plan) : %d" % len(broke))
for n, code, msg in refused[:25]:
    print("  REFUSED %-34s %-26s %s" % (n[:34], str(code)[:26], msg))
for n, e in broke[:15]:
    print("  BROKE   %-34s %s" % (n[:34], e))

p.stdin.close()
try:
    p.wait(timeout=10)
except subprocess.TimeoutExpired:
    p.kill()
