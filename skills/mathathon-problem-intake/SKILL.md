---
name: mathathon-problem-intake
description: Pull an open problem from MathDB (mathdb.com) into mathcity as a source bead, so a Mathathon attempt runs on the brief pipeline instead of in a chat window. Use when the user says "intake MathDB problem N", "pull problem N from mathdb", "start a mathathon attempt on N", "bring this open problem into the city", or names a mathdb.com/p/<n>/ URL. Produces a bead carrying the canonical statement and its provenance; does NOT attempt the mathematics.
---

# mathathon-problem-intake

Bring one MathDB open problem into mathcity as a bead, with its statement and
provenance attached, so everything after it — briefs, gates, verdicts, traces —
is the machinery the city already has.

## Why this exists

The Caltech Mathathon's task is to **"solve and explain an open problem in
mathematics"**, judged by independent academics on two axes its FAQ names:

> **Understanding** — participants "present their results orally and answer
> questions from our judges"
> **Verification** — "publication of results for community review"

Both are things mathcity already does. A brief IS a structured explanation with
§1–§7; a gate IS mechanical verification; a bead IS the durable record. The gap
is only at the front: nothing pulls the *problem* in.

The FAQ also states: **"We will record and open source all AI chat logs
produced at this event."** Work done through the city produces traces and events
by construction, which is a better provenance record than a chat transcript and
is already how the city works.

## What this does and does not do

**Does:** fetch one problem's canonical statement from MathDB's schema.org
JSON-LD, create a bead carrying it with the source URL, and stop.

**Does not:** attempt the mathematics, claim a solution, write to MathDB, or
decide whether the problem is a good target. Those are separate and at least one
of them is a human's.

## The access contract — read this before widening anything

MathDB grants crawler access **conditionally**. From its robots.txt:

> Search and AI crawlers are welcome on public, read-only pages: the site exists
> to make open problems findable. Please identify your crawler, use a reasonable
> request rate, and follow the Terms of Service.
>
> Disallow: /new · /bookmarks · /moderation

`assets/scripts/mathdb-fetch.py` implements exactly that: read-only, an
identifying User-Agent naming the project and a contact route, a non-zero
default delay, sitemap enumeration rather than id-guessing, and the three
Disallow prefixes **refused in code** rather than avoided by habit.

Do not widen this without re-reading their Terms. Access is granted on terms,
and a tool that drifts off them costs the project a source it wants to keep.

## Steps

**1. Fetch the problem.**

```bash
python3 assets/scripts/mathdb-fetch.py --problem <N>
```

Returns the canonical `name` and `statement` from JSON-LD, plus the resolved
URL. Exit 0 fetched, 1 not found, 2 could not ask.

**2. Read what came back, including what did not.**

`status` and `tags` come back `null` with `html_fields_parsed: false`. That is
deliberate. Those fields render in HTML, not in the JSON-LD, and a wrong
"solved" on an open problem is worse than no answer. **If the attempt depends on
the problem's status, a human checks the page.** Do not infer it.

**3. Create the source bead.**

```bash
bd create --type=task --priority=2 \
  --title="MathDB #<N>: <name>" \
  --description="<statement>

Source: <url>
Retrieved: <date> via assets/scripts/mathdb-fetch.py (schema.org JSON-LD)
Status on MathDB: NOT READ — renders in HTML, not in the JSON-LD. Check the page
before treating this as open." \
  --acceptance="<what would count as a result, stated before starting>"
```

**Write the acceptance criterion before attempting anything.** For an open
problem the honest one is usually not "prove it" — it is a bounded claim: a
special case, a computational search to a stated bound, a counterexample
search, or a formalization of the statement itself. B3.1 requires closure to be
verifiable, and "made progress" is not.

**4. Hand off to the brief pipeline.**

The bead is now an ordinary mathcity source bead. `brief-prep` or
`commission-work-briefed` take it from here, and the §1–§7 form is what the
judges' "Understanding" axis is asking for.

## What to watch

- **Do not let the tool's silence read as "open".** `answer_count: 0` in the
  JSON-LD is not the same as unsolved; it is the count of answers *posted to
  MathDB*.
- **87,155 problems are indexed.** Choosing which to attempt is a mathematical
  judgment, not a search-ranking one, and this skill deliberately does not rank.
- **The $500 in Erdős Problem #1's statement is part of the quoted text**, not
  an offer from anyone here.
