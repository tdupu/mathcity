# mathcity-teaching

Parent: [../../README-subdomains.md](../../README-subdomains.md)

Course materials and teaching work: whole offerings, syllabi, assessments and
keys, course webpages, transcription of scanned notes, and lecture-note
publication.

## Using the workflow

Start with `using-teaching`, which routes by request. `using-teachingpowers` is a
compatibility entry point that delegates to it — it starts no second workflow.

Two constraints the router enforces and that callers should not work around:
multiple deliverables share **one** dependency-ordered plan rather than competing
controllers, and **routing confers no publication authority** — a leaf that
prepares material does not thereby gain permission to publish it.

Leaves call the mathematics and LaTeX workflows for relevant work
(`using-mathpowers`, `using-latexpowers`) without restarting this router.

Before planning, a repository-root `POWERS.md` (when present) tightens these
defaults for that repository only; amend it or a global default only through
`new-powers-policy`.

## Not in this subdomain

`update-job-materials` and `update-job-materials-workspace` are **not** teaching
skills and are deliberately absent. They are personal career tooling, they are
not reachable from the `using-teaching` dispatch table, and their workspace
configuration carries personal identifiers that do not belong in a public pack.
