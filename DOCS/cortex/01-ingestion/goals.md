# Connector & Ingestion Layer Goals

## Phase Objectives
- Produce contract-valid outputs for downstream phases.
- Preserve provenance and tenant boundaries.
- Maintain deterministic behavior for replay.
- **Acquire organizational exhaust at declared depth** — Phase 01 is an **organizational exhaust ingestion engine**: fetch → paginate → cursor → backfill → store raw rows. **Not** connector maturity tooling or shallow connectivity (see **`phase-01-organizational-exhaust-spec.md`**, `real-ingestion-definition.md`, `../implementation/organizational-exhaust-execution-track.md`, `../connectors/organizational-exhaust-definition.md`, `../MASTER_TRACKER.md` §2.5).

## Must Hold True
- Inputs are validated against explicit contract versions.
- Outputs are versioned and lineage-linked.
- Failures produce diagnosable artifacts, not silent drops.

## Explicit Anti-Goals
- No organizational meaning inference
- No topic/concern/decision summarization
- No causal or risk classification
