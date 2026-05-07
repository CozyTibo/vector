# 07-reasoning Technical Decisions

## Required Decisions Before Implementation
- deterministic vs inferred reasoning boundary
- causal hypothesis schema and contradiction semantics
- confidence threshold policy per inference type
- AI model version pinning strategy

## Decision Constraints
- Decisions must preserve deterministic replay semantics.
- Decisions must not violate phase ownership boundaries.
- Cross-phase impact requires ADR linkage and contract versioning.
