# Lost-Bead Filter Smoke Tests

This directory contains a self-contained smoke test for the BEADS downstream
classification rollup and upstream provenance-repair rollup.

The test exercises:

- `lost-bead-classification.v1` cache records produced from linked event beads.
- `dispatch-provenance.v1` cache records produced from dispatch event beads.
- Downstream rollup threshold behavior for repeated immediate strands.
- Upstream rollup behavior for known dispatch sources and unknown provenance.
- Formula and order TOML parseability.
- Skill documentation contracts for classification and dispatch provenance.

Canonical records live in linked `type=event` beads. TOML files in this test
tree are fixtures and cache-format examples, not a second source of truth.
