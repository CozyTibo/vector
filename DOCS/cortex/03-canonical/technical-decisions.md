# 03-canonical Technical Decisions

## Required Decisions Before Implementation
- canonical event type taxonomy boundaries
- supersession rules for edited/deleted source events
- field-level normalization precedence when sources disagree
- canonical id derivation strategy

## Decision Constraints
- Decisions must preserve deterministic replay semantics.
- Decisions must not violate phase ownership boundaries.
- Cross-phase impact requires ADR linkage and contract versioning.
