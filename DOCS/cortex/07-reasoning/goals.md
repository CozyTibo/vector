# Temporal/Causal Intelligence Layer Goals

## Phase Objectives
- Produce contract-valid outputs for downstream phases.
- Preserve provenance and tenant boundaries.
- Maintain deterministic behavior for replay.

## Must Hold True
- Inputs are validated against explicit contract versions.
- Outputs are versioned and lineage-linked.
- Failures produce diagnosable artifacts, not silent drops.

## Explicit Anti-Goals
- No canonical fact rewriting
- No certainty claims without confidence support
- No connector-specific semantic logic
