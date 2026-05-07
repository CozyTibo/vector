# 04-entity-resolution Technical Decisions

## Required Decisions Before Implementation
- identity merge thresholds and confidence bands
- split strategy for previously merged identities
- source precedence for actor identity conflicts
- human override policy and audit representation

## Decision Constraints
- Decisions must preserve deterministic replay semantics.
- Decisions must not violate phase ownership boundaries.
- Cross-phase impact requires ADR linkage and contract versioning.
