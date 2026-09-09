#!/usr/bin/env python3
"""Read open problems from MathDB (https://mathdb.com) into mathcity.

MathDB is "a community database of open problems in mathematics, designed to
keep track of the rapid growth of AI-assisted mathematical breakthroughs" —
87,155 problems indexed as of 2026-09-09. It is the natural problem source for
the Caltech Mathathon, whose main task is "solve and explain an open problem in
mathematics".

THE ACCESS CONTRACT, quoted from the site rather than assumed. robots.txt:

    Search and AI crawlers are welcome on public, read-only pages: the site
    exists to make open problems findable. Please identify your crawler, use a
    reasonable request rate, and follow the Terms of Service.

    Disallow: /new
    Disallow: /bookmarks
    Disallow: /moderation

and the Terms (effective 2026-09-02):

    Search and AI crawlers may access public pages when they follow our
    robots.txt, identify themselves accurately, and use a reasonable request
    rate. Do not overload the service or evade technical measures.

This tool implements exactly that and nothing wider:

  - READ ONLY. There is no write path here, and the three Disallow prefixes are
    refused in code rather than merely avoided by habit -- see `_refuse_if_disallowed`.
  - IDENTIFIES ITSELF. A real User-Agent naming the project and a contact route.
    An honest UA is a term of access, not a nicety.
  - RATE LIMITED by default, from policy (assets/mctl/limits.toml), not a
    constant baked in here.
  - ENUMERATES VIA SITEMAP, never by guessing ids. /sitemap.xml indexes five
    problem sitemaps; walking those is cheaper for them and for us than probing.

WHAT IT READS. Problem pages carry schema.org JSON-LD:

    mainEntity @type Question
      name          "Erdős Problem #1 — Maximum size of sets with distinct subset sums"
      text          the problem statement
      answerCount   0
      upvoteCount   0

That is the canonical, machine-readable surface and it is what this tool
returns. It is also THIN -- status ("solved" / "claimed solved" / "claimed
progress"), age and provenance are rendered in HTML and are NOT in the JSON-LD.
Those are reported as `null` with `html_fields_parsed: false` rather than
scraped by regex: a wrong status on an open problem is exactly the kind of
confident-wrong answer this codebase keeps finding, and "I did not read it" is
a better answer than a guess.

Exit codes (P6.2): 0 fetched, 1 not found / not a problem page, 2 the request
could not be made (network, timeout, refusal) -- distinct from "found nothing".
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mctl_limits import resolve as _resolve_limit  # noqa: E402

BASE = "https://mathdb.com"

#: Identify accurately — a term of access, quoted above. If this project moves,
#: this string moves with it.
USER_AGENT = (
    "mathcity-research-bot/0.1 "
    "(+https://github.com/tdupu/mathcity; contact: repo issues) "
    "read-only; respects robots.txt"
)

#: robots.txt Disallow prefixes, refused in code. Keeping them as data rather
#: than as a comment means a future caller cannot reach them by accident.
DISALLOWED_PREFIXES = ("/new", "/bookmarks", "/moderation")

PROBLEM_PATH = re.compile(r"^/p/(\d+)/([a-z0-9-]+)$")
JSONLD = re.compile(
    r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S
)


class Refused(RuntimeError):
    """This tool declined to make the request."""


def _refuse_if_disallowed(path: str) -> None:
    for prefix in DISALLOWED_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            raise Refused(
                f"{path} is Disallow'd by https://mathdb.com/robots.txt "
                f"(prefix {prefix}). This tool does not fetch it."
            )


#: CA bundles to try when the interpreter's own trust path is broken. Ordered
#: most-specific first. Every entry was verified to exist on at least one
#: machine in this fleet.
CA_BUNDLE_CANDIDATES = (
    "/usr/local/etc/ca-certificates/cert.pem",   # Homebrew (kolchin)
    "/opt/homebrew/etc/ca-certificates/cert.pem",  # Homebrew (arm)
    "/etc/ssl/cert.pem",                          # macOS system
    "/private/etc/ssl/cert.pem",
)


def _ssl_context():
    """A verifying SSL context that works on every python3 in this fleet.

    NOT a convenience, and NOT theoretical -- BOTH machines ship a python3
    whose OpenSSL trust path points at a file that does not exist, for
    different reasons, while `curl` on the same machine succeeds:

        laptop   default python3 is SageMath's; openssl_cafile is
                 /var/tmp/sage-10.8-current/local/ssl/cert.pem   -> absent
        kolchin  /usr/local/bin/python3; openssl_cafile is
                 /usr/local/etc/openssl@3/cert.pem               -> absent
                 and `certifi` is not importable there at all

    An earlier version of this function used `certifi` with a plain
    `create_default_context()` fallback and asserted in its own docstring that
    "kolchin's python3 has a working store". Running it on kolchin disproved
    that in one command. The fleet has no interpreter that is right by default.

    Order: certifi if importable, else the first CA bundle on disk, else the
    interpreter default (which may work on a machine neither of these covers).

    VERIFICATION IS NEVER DISABLED. An unverified fetch is how a tool ends up
    trusting content it cannot attribute, and this tool exists to carry outside
    text into a decision record.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    for bundle in CA_BUNDLE_CANDIDATES:
        if os.path.exists(bundle):
            return ssl.create_default_context(cafile=bundle)
    return ssl.create_default_context()


def get(url: str, timeout: int | None) -> str:
    if url.startswith(BASE):
        _refuse_if_disallowed(url[len(BASE):].split("?", 1)[0] or "/")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout,
                                context=_ssl_context()) as response:
        return response.read().decode("utf-8", errors="replace")


def problem(number: int, timeout: int | None) -> dict:
    """Fetch one problem by its MathDB number.

    The slug is resolved from the sitemap rather than constructed: a guessed
    slug that 404s is indistinguishable from a problem that does not exist, and
    those need different answers.
    """
    for index in range(1, 6):
        xml = get(f"{BASE}/sitemap-problems-{index}.xml", timeout)
        match = re.search(
            rf"<loc>({re.escape(BASE)}/p/{number}/[a-z0-9-]+)</loc>", xml
        )
        if match:
            url = match.group(1)
            break
    else:
        return {"number": number, "found": False,
                "why": "no /p/<n>/ entry in any of the five problem sitemaps"}

    html = get(url, timeout)
    blob = JSONLD.search(html)
    if not blob:
        return {"number": number, "url": url, "found": False,
                "why": "page carries no application/ld+json block"}

    entity = (json.loads(blob.group(1)) or {}).get("mainEntity") or {}
    return {
        "number": number,
        "url": url,
        "found": True,
        "type": entity.get("@type"),
        "name": entity.get("name"),
        "statement": entity.get("text"),
        "answer_count": entity.get("answerCount"),
        "upvote_count": entity.get("upvoteCount"),
        # HONEST ABSENCE. status/tags/age render in HTML, not in the JSON-LD.
        # Reported as null with the flag below rather than regex-scraped -- a
        # wrong "solved" on an open problem is worse than no answer.
        "status": None,
        "tags": None,
        "html_fields_parsed": False,
        "source": "schema.org JSON-LD (mainEntity)",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="read open problems from MathDB")
    ap.add_argument("--problem", type=int, action="append", default=[],
                    metavar="N", help="MathDB problem number; repeatable")
    ap.add_argument("--count-index", action="store_true",
                    help="report how many problems the sitemaps list")
    ap.add_argument("--timeout", type=int, default=None,
                    help="seconds; 0 = no deadline. Default from "
                         "assets/mctl/limits.toml [remote_query_seconds].")
    ap.add_argument("--delay", type=float, default=1.0,
                    help="seconds between requests (a reasonable rate is a "
                         "term of access; do not set this to 0 for bulk reads)")
    args = ap.parse_args()

    args.timeout, source = _resolve_limit("remote_query_seconds", args.timeout)
    if source == "fallback":
        print(f"NOTE: limits.toml unreadable; using built-in {args.timeout}s",
              file=sys.stderr)

    try:
        if args.count_index:
            total = 0
            for index in range(1, 6):
                xml = get(f"{BASE}/sitemap-problems-{index}.xml", args.timeout)
                n = xml.count("<loc>")
                total += n
                print(f"  sitemap-problems-{index}.xml  {n:>6} problems")
                time.sleep(args.delay)
            print(f"  {'total':<24} {total:>6}")
            return 0

        if not args.problem:
            ap.error("give --problem N or --count-index")

        out = []
        for i, number in enumerate(args.problem):
            if i:
                time.sleep(args.delay)
            out.append(problem(number, args.timeout))
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if all(r.get("found") for r in out) else 1

    except Refused as exc:
        print(f"MATHDB: REFUSED -- {exc}", file=sys.stderr)
        return 2
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # Could not ask. NOT the same as asked-and-found-nothing.
        print(f"MATHDB: UNREACHABLE -- {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
