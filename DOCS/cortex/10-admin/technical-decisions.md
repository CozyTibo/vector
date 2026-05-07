# 10-admin Technical Decisions

## Required Decisions Before Implementation
- replay authorization model
- operator action audit schema
- tenant-level policy override boundaries
- alert severity taxonomy and escalation paths

## Decision Constraints
- Decisions must preserve deterministic replay semantics.
- Decisions must not violate phase ownership boundaries.
- Cross-phase impact requires ADR linkage and contract versioning.
