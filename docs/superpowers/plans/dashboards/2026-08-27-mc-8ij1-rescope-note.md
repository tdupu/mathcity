# Re-scope note — mc-8ij1 ("/city never renders in 90s")

**Author:** WP-TRIAGE (repair/triage). **Date:** 2026-08-27.
**Recommendation: CLOSE mc-8ij1 as superseded / stale.** BART performs the
actual bead + GH close; this note is the evidence and the recommendation only.

---

## The bead's premise is refuted, and its symptom no longer reproduces

`mc-8ij1` (GH context; open, priority 2) asserts a **route-specific** defect:
`GET /city` *"never renders — no response in 90s"* while `/briefs` answers in
3.6s on the same process. Two independent findings retire that claim:

1. **The route-specific premise is REFUTED and already superseded.** The closed
   decision **`mc-5ir2`** — *"Root-cause the mctl dashboard's whole-server
   latency instability (supersedes the route-specific premise in mc-8ij1, which
   is REFUTED)"* — measured both routes directly and found **both swing 10–30×**
   (`/city` 200 in 35.3s with a full 209,605-byte render; `/briefs` 200 in
   31.8s; `/` 1.74s → 58.4s on the same process, same commit, no restart). That
   is **whole-server latency instability, not a dead route.** `mc-5ir2` exists
   precisely because no MCP tool could amend `mc-8ij1` in place; it *is* the
   correction, and it is already closed.

2. **BART re-measured on 2026-08-27: `/city` = HTTP 200 in ~24.7s.** The page
   renders. It is **slow, not dead.** This matches `mc-5ir2`'s reading and
   contradicts the bead title's "never renders / no response in 90s."

The one sample behind the "never renders" title was also shown by `mc-5ir2` to
be an **instrument error**, not a datum: an earlier `/city` "HTTP 000 / titled
page" reading came from a probe loop that reused one temp file, so curl wrote
nothing on timeout and the title was read from the previous URL's body.

## The part of the latency that was *ours* has been removed

The ~90s load `mc-8ij1` shipped with came partly from the `/city` handler
running its three independent reads (`fleet_sessions`, `city_health`,
`gates_status`) in sequence. That serialization is gone: the city page now fans
those reads out concurrently (`mctl_dashboard/fanout.py`; guarded by
`tests/mctl/test_city_reads_concurrently.py::test_the_city_page_does_not_serialize_its_three_reads`,
green on `74eeac0`). The residual latency is the backend — `gc`/`fleet_sessions`
timing out (tracked separately as #159) and general whole-server instability
(`mc-5ir2`) — neither of which is the route-specific defect `mc-8ij1` describes.

## Recommendation

- **Close `mc-8ij1`** with reason *superseded by `mc-5ir2` (refuted premise) and
  stale (symptom no longer reproduces: `/city` = 200 in ~24.7s, 2026-08-27)*.
- Any residual latency work is already owned by `mc-5ir2` (whole-server
  instability, option A: instrument the per-tool fan-out and difference timings)
  and #159 (`gc` probe timeout). No new bead is needed for `mc-8ij1`; it should
  not be re-aimed, only closed, because its distinguishing claim — that `/city`
  is broken *relative to* other routes — does not exist.

This note recommends only; it writes no bead lifecycle and no GH close (P3.1;
bead lifecycle is BART's, per the master plan).
