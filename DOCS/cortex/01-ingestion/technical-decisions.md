# 01-ingestion Technical Decisions

## Required Decisions Before Implementation
- poll watermark strategy per connector
- idempotency key construction (tenant+source+object+event version)
- connector auth token failure handling and backoff policy
- envelope validation rejection classes

## Decision Constraints
- Decisions must preserve deterministic replay semantics.
- Decisions must not violate phase ownership boundaries.
- Cross-phase impact requires ADR linkage and contract versioning.
