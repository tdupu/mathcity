---
brief_for: he-gu79-fake
branch: polecat/he-gu79-fake
parent_bead_closed: true
parent_bead_supersession_documented: true
diff_files:
  - scratch/notes/some-scratch.md
downstream_beads_reference: false
verdict: DELETE
brief_no_brainer: false
capability_blocker: "need gh auth to verify parent PR closure; token missing in this sandbox"
---
# Brief: capability-blocker fixture (would be no-brainer but for an auth gap)

Would classify as stale-branch (all 5 he-lele criteria hold) BUT the polecat cannot verify the parent PR's merged status because `gh auth` is unavailable in this session. Once auth is restored (via token-pass-outer or credential provisioning), re-run the classifier and expect stale-branch. Data point: n=5+ per feedback_no_brainer_class_under_flagged (he-gu79 is the canonical example).

Downstream signal: `compact_eligible:false` and `category:"capability-blocker"` — Mayor dispatches the capability-resolution path, not the brief-presentation path.
