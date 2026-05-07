# 08-retrieval Technical Decisions

## Required Decisions Before Implementation
- query planner priority order (deterministic first)
- context-pack size and token budget policy
- access-control filter position in pipeline
- semantic recall vs precision tradeoff policy

## Decision Constraints
- Decisions must preserve deterministic replay semantics.
- Decisions must not violate phase ownership boundaries.
- Cross-phase impact requires ADR linkage and contract versioning.
