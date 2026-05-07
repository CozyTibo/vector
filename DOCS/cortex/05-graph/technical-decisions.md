# 05-graph Technical Decisions

## Required Decisions Before Implementation
- edge type taxonomy and directionality
- temporal validity encoding for edges
- superseded edge retention policy
- lineage traversal depth constraints

## Decision Constraints
- Decisions must preserve deterministic replay semantics.
- Decisions must not violate phase ownership boundaries.
- Cross-phase impact requires ADR linkage and contract versioning.
