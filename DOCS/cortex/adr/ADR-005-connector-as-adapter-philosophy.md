# ADR-005: Connector As Adapter Philosophy

- Status: Accepted
- Date: 2026-05-07

## Context
Keeping connectors thin prevents business logic fragmentation and keeps cognition centralized downstream.

## Decision
Connectors are ingestion adapters with no organizational intelligence.

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
