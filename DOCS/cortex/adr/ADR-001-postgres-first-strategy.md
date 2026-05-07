# ADR-001: Postgres First Strategy

- Status: Accepted
- Date: 2026-05-07

## Context
Postgres is already available on AWS RDS, supports JSONB + relational constraints, and avoids premature operational complexity while preserving migration paths.

## Decision
Choose PostgreSQL as the initial Cortex persistence foundation.

## Alternatives Considered
- Defer decision until later implementation phase.
- Use AI-first interpretation pipeline.
- Use source-specific logic as the primary model.

## Consequences
### Positive
- Strong architecture coherence from day one.
- Lower strategic drift risk.
- Clear implementation constraints for contributors.

### Negative
- Requires disciplined schema and version management.
- Slower short-term prototyping velocity in some areas.

### Follow-Up
- Validate this ADR against phase-specific technical decisions as implementation planning deepens.
