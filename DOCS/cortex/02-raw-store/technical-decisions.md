# 02-raw-store Technical Decisions

## Required Decisions Before Implementation
- raw table partitioning by tenant/time
- immutable record key strategy
- retention metadata model vs hard-delete markers
- replay index granularity (event-level vs batch-level)

## Decision Constraints
- Decisions must preserve deterministic replay semantics.
- Decisions must not violate phase ownership boundaries.
- Cross-phase impact requires ADR linkage and contract versioning.
