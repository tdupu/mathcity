# A1 — what exists ONLY on kolchin's `ma` replica

Measured 2026-09-10, read-only. This is audit item A1's deliverable and the
input to R1 (preserve + transport).

## Method, and its one limitation

Compared kolchin's `~/repos/mathcity` bead store against the laptop's
`~/gt/mathcity`. **Both declare the same dolt remote**
(`git+ssh://git@github.com/./tdupu/mathcity-dolt.git`), so the laptop replica is
the syncable counterpart of the flattened one.

*Limitation, stated because it bounds the claim:* the laptop replica is a proxy
for the remote, not the remote itself. If the laptop is itself behind the
remote, a bead present on the remote but absent from BOTH would be
misclassified. Nothing in the result depends on that case — the kolchin-only set
is machine-generated steps, and the comments are datable to this campaign.

## Result

    kolchin ma beads    1,476
    laptop  ma beads    1,835
    ------------------------------
    ONLY on kolchin         9   bead records
    only on laptop        368
    in both             1,467

    shared beads whose comment_count differs        55
      ...with MORE comments on kolchin              11   <- local-only content

## The 9 kolchin-only bead records

All `ma-*` prefixed, all `open`, all machine-generated brief-shuffle workflow
steps. No human decision content.

    ma-20u   Step spec for Apply gates and write disposition
    ma-7uq   Claim one pile item (atomic mv)
    ma-7xw   Confirm staging cleared, no lock to release
    ma-9be   Finalize workflow
    ma-b68   Apply gates and write disposition for the claimed item
    ma-kqi   Confirm staging cleared, no lock to release
    ma-v7h   brief-shuffle
    ma-vcu   Step spec for Confirm staging cleared
    ma-yk7   Apply gates and write disposition for the claimed item

These are the stranded steps #274 describes: routed to pools capped at `max=0`,
so nothing could ever claim them. **They are a symptom to clear, not content to
preserve** — recreating them is what running brief-shuffle does.

## The 11 local-only comments — this is the content that matters

Each is a `#267` BP4.2(b)/(c) audit annotation written 2026-09-09, present on
kolchin and absent from the laptop:

    mc-3yh    mc-4al9   mc-82t2   mc-9vq    mc-ji9m   mc-ju7c
    mc-kfhx   mc-mn8o   mc-quq    mc-rjd    mc-w15d

Full text captured in `kolchin-local-only-content-2026-09-10.txt` (448 lines,
20 sections).

They are non-destructive audit notes recording that a bead was closed as a
duplicate with no open survivor, or superseded naming no absorbing bead. Losing
them loses the audit trail, not the beads.

## What this means for R2

**The preservation problem is much smaller than the framing implied.** Nine
regenerable step beads and eleven comments — not a large body of stranded work.

That materially lowers the risk of the replica repair: if `ma` were re-cloned
from the remote, the recoverable loss is 11 comments whose full text is in this
directory, and 9 beads that a brief-shuffle run recreates.

**It does not by itself authorise a re-clone.** A1 answers "what is local-only",
not "is re-cloning correct" — that is R2, and it still needs A2 (does the push
actually fail) and A3 (does the remote hold pre-flatten lineage) first.
