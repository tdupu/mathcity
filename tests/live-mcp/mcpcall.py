#!/usr/bin/env python3
"""Call one mctl MCP tool over real stdio JSON-RPC and print the result.

Usage:  mcpcall.py <tool_name> '<json-args>'
        mcpcall.py --list
Runs against the live server exactly as an agent would reach it.
"""
import json
import subprocess
import sys

import os

CMD = ["./bin/mctl", "mcp", "serve"]
if os.environ.get("MCTL_CITY"):
    CMD += ["--city", os.environ["MCTL_CITY"]]
if os.environ.get("MCTL_RIG"):
    CMD += ["--rig", os.environ["MCTL_RIG"]]


def main():
    if len(sys.argv) < 2:
        print("usage: mcpcall.py <tool>|--list [json-args]")
        return 2
    tool = sys.argv[1]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}

    p = subprocess.Popen(
        CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1,
    )

    def send(obj):
        p.stdin.write(json.dumps(obj) + "\n")
        p.stdin.flush()

    def recv():
        while True:
            line = p.stdout.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                     "clientInfo": {"name": "mcpcall", "version": "1"}}})
    recv()
    send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    if tool == "--list":
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        r = recv() or {}
        names = [t["name"] for t in r.get("result", {}).get("tools", [])]
        print("TOOLS(%d): %s" % (len(names), ", ".join(sorted(names))))
    else:
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
              "params": {"name": tool, "arguments": args}})
        r = recv() or {}
        if "error" in r:
            print("RPC-ERROR:", json.dumps(r["error"])[:1500])
        else:
            res = r.get("result", {})
            if res.get("isError"):
                print("TOOL-ERROR:")
            for c in res.get("content", []):
                print(c.get("text", ""))

    p.stdin.close()
    try:
        p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        p.kill()
    err = p.stderr.read()
    if err.strip():
        print("--- stderr ---")
        print(err[-800:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
